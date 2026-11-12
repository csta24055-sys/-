#!/usr/bin/env python3
"""Merge staged worker outputs into the ledgers AFTER mechanical verification.

Trust model (research tooling only, no app code):
- "Was this search run?"  -> taken from the runtime transcript trace (transcript_audit.py),
  never from the worker's own report. The worker's report only labels an executed query
  (route, legacy id, note). A reported query that is absent from the trace is NOT logged.
- "Was this page read?"   -> taken from the trace + the fetch cache metadata (status, chars).
- "Does the source say this?" -> every proposed source must carry a verbatim quote that is
  found in the cached page text. Not found => the candidate is rejected, not accepted.
Semantic review of claim vs quote is a later stage (S2); rows enter as review_state=S2_PENDING.

Usage: python3 scripts/merge_staging.py STAGING_DIR CACHE_DIR TRACE_JSONL
Idempotent: re-running adds nothing that is already merged.
"""
from __future__ import annotations
import csv
import hashlib
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit

R = Path(__file__).resolve().parents[1]
REG = R / 'registry'
LOG_EXTRA = ['suggestion_id', 'route', 'followup_for', 'unit_kind', 'unit_id', 'executor', 'verified_by', 'candidate_urls']
SRC_EXTRA = ['quote', 'quote_check', 'statement_kind', 'origin_org', 'added_in', 'review_state', 'review_notes']
MAP_FIELDS = ['map_id', 'source_id', 'unit_kind', 'unit_id', 'role', 'claim_text', 'quote', 'quote_check', 'added_by', 'review_state', 'review_notes']
REJ_FIELDS = ['unit_kind', 'unit_id', 'url', 'reason', 'claimed_quote', 'executor']
SOURCE_TYPES = {'OFFICIAL_VENDOR', 'INDEPENDENT_REVIEW', 'SPONSORED', 'ACADEMIC', 'GOVERNMENT', 'CUSTOMER_FIRSTHAND', 'OTHER'}
ROLES = {'PRIMARY', 'INDEPENDENT', 'COUNTER'}
MULTI_ORIGIN_HOSTS = ('arxiv.org', 'prtimes.jp', 'digitalpr.jp', 'github.com', 'note.com', 'reddit.com', 'youtube.com', 'medium.com',
                      'qiita.com', 'zenn.dev', 'kyodonewsprwire.jp', 'researchgate.net', 'ssrn.com', 'nber.org', 'jst.go.jp', 'apple.com',
                      'google.com', 'acm.org', 'petsymposium.org', 'usenix.org', 'openreview.net', 'aclanthology.org', 'sciencedirect.com',
                      'springer.com', 'nature.com', 'mdpi.com', 'tandfonline.com', 'wiley.com', 'biorxiv.org', 'nih.gov', 'jsdelivr.net',
                      'semanticscholar.org', 'substack.com', 'hatenablog.com', 'speakerdeck.com', 'slideshare.net', 'ieee.org', 'cvf.com',
                      'thecvf.com', 'mlr.press', 'neurips.cc', 'huggingface.co', 'ac.jp', 'frontiersin.org', 'plos.org', 'sagepub.com',
                      'oup.com', 'cambridge.org', 'jmir.org', 'elsevier.com', 'ceur-ws.org', 'osf.io', 'zenodo.org', 'ipsj.or.jp', 'nii.ac.jp')
SECOND_LEVEL = ('co.jp', 'ac.jp', 'go.jp', 'or.jp', 'ne.jp', 'lg.jp', 'ed.jp', 'gr.jp', 'co.uk', 'ac.uk', 'gov.uk', 'org.uk', 'com.au', 'edu.au',
                'gov.au', 'co.kr', 'com.cn', 'edu.cn', 'co.nz', 'com.sg', 'edu.sg', 'co.in', 'ac.in', 'com.br', 'com.tw', 'edu.tw')


def read(name: str) -> tuple[list[str], list[dict]]:
    p = REG / name
    if not p.exists():
        return [], []
    with p.open(encoding='utf-8-sig', newline='') as f:
        r = csv.DictReader(f)
        return list(r.fieldnames or []), list(r)


def write(name: str, fields: list[str], rows: list[dict]) -> None:
    with (REG / name).open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in fields})


def norm_url(u: str) -> str:
    s = urlsplit(u.strip())
    path = s.path.rstrip('/') or ''
    return f'{s.scheme.lower()}://{s.netloc.lower()}{path}' + (f'?{s.query}' if s.query else '')


def domain(u: str) -> str:
    host = urlsplit(u).netloc.lower().split(':')[0]
    parts = host.split('.')
    if len(parts) >= 3 and '.'.join(parts[-2:]) in SECOND_LEVEL:
        return '.'.join(parts[-3:])
    return '.'.join(parts[-2:]) if len(parts) >= 2 else host


def slug(s: str) -> str:
    s = unicodedata.normalize('NFKC', s or '').strip().upper()
    s = re.sub(r'[\s/|:;,.()（）「」『』・、。\'"]+', '_', s).strip('_')
    return s[:48] or 'UNKNOWN'


def squash(s: str) -> str:
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', s or ''))


class Cache:
    def __init__(self, d: Path):
        self.d = d
        self.meta = {}
        for p in d.glob('*.json'):
            try:
                m = json.loads(p.read_text(encoding='utf-8'))
            except ValueError:
                continue
            if isinstance(m, dict) and 'url' in m:
                m['key'] = p.stem
                self.meta[m['url']] = m
        self.by_norm = {norm_url(u): m for u, m in self.meta.items()}

    def get(self, url: str) -> dict | None:
        return self.meta.get(url) or self.by_norm.get(norm_url(url))

    def text(self, url: str) -> str:
        m = self.get(url)
        if not m:
            return ''
        p = self.d / f"{m['key']}.txt"
        return p.read_text(encoding='utf-8', errors='replace') if p.exists() else ''

    def has_quote(self, url: str, quote: str) -> bool:
        q = squash(quote)
        return len(q) >= 12 and q in squash(self.text(url))


def platform_for(url: str) -> str:
    d = domain(url)
    if d.endswith('go.jp') or d.endswith('.gov') or d.endswith('gov.uk') or d.endswith('lg.jp') or d in ('europa.eu', 'oecd.org'):
        return 'direct_fetch:government_site'
    if d.endswith('ac.jp') or d.endswith('.edu') or d.endswith('ac.uk') or d in ('arxiv.org', 'acm.org', 'nber.org', 'jst.go.jp', 'petsymposium.org', 'usenix.org', 'aclanthology.org', 'openreview.net'):
        return 'direct_fetch:academic_repository'
    if d in ('reddit.com', 'note.com', 'qiita.com', 'zenn.dev', 'github.com', 'medium.com', 'youtube.com'):
        return 'direct_fetch:community_forum'
    if d in ('g2.com', 'capterra.com', 'trustpilot.com', 'apple.com', 'itreview.jp'):
        return 'direct_fetch:review_site'
    return 'direct_fetch:web_page'


def lang(q: str) -> tuple[str, str]:
    return ('JP', 'ja') if re.search(r'[぀-ヿ一-鿿]', q) else ('GLOBAL', 'en')


def main() -> None:
    staging, cache_dir, trace_path = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    cache = Cache(cache_dir)
    topics = {r['topic_id']: r['axis_id'] for r in read('research_axes.csv')[1]}
    additional = {r['topic_id']: r['axis_id'] for r in read('additional_axes.csv')[1]}
    topics.update(additional)
    comps = {r['competitor_id']: r for r in read('competitor_candidates.csv')[1]}
    legacy_by_topic = defaultdict(dict)
    for q in read('search_queries_candidates.csv')[1]:
        legacy_by_topic[q['topic_id']][q['sample_query']] = q['suggestion_id']

    lf, log = read('search_log.csv')
    for c in LOG_EXTRA:
        if c not in lf:
            lf.append(c)
    for r in log:
        r.setdefault('unit_kind', '') or r.__setitem__('unit_kind', 'TOPIC')
        if not r.get('unit_id'):
            r['unit_id'] = r['topic_id']
        if not r.get('executor'):
            r['executor'] = 'main_session_2026-11-09_10'
        if not r.get('verified_by'):
            r['verified_by'] = 'SESSION_RECORD'
    sf, src = read('source_evidence.csv')
    for c in SRC_EXTRA:
        if c not in sf:
            sf.append(c)
    for s in src:
        if not s.get('added_in'):
            s['added_in'] = 'session_2026-11-09_10'
        if not s.get('review_state'):
            s['review_state'] = 'S2_PENDING'
        if not s.get('quote_check'):
            s['quote_check'] = 'PENDING_BACKFILL'
    _, smap = read('source_topic_map.csv')
    if not smap:  # initialise from the first session's main / also mappings
        n = 0
        for s in src:
            n += 1
            smap.append({'map_id': f'M{n:05d}', 'source_id': s['source_id'], 'unit_kind': 'TOPIC', 'unit_id': s['topic_id'], 'role': 'MAIN',
                         'claim_text': s['claim_text'], 'quote': '', 'quote_check': 'PENDING_BACKFILL', 'added_by': 'session_2026-11-09_10', 'review_state': 'S2_PENDING'})
            m = re.search(r'also:\s*([^。]*)', s.get('notes', ''))
            for t in dict.fromkeys(re.findall(r'AXIS_\d\d_T\d\d', m.group(1)) if m else []):
                if t in topics and t != s['topic_id']:
                    n += 1
                    smap.append({'map_id': f'M{n:05d}', 'source_id': s['source_id'], 'unit_kind': 'TOPIC', 'unit_id': t, 'role': 'ALSO',
                                 'claim_text': '', 'quote': '', 'quote_check': 'PENDING_BACKFILL', 'added_by': 'session_2026-11-09_10', 'review_state': 'S2_PENDING'})
    _, rejected = read('rejected_candidates.csv')
    units_path = REG / 'topic_units.jsonl'
    units = {}
    if units_path.exists():
        for line in units_path.read_text(encoding='utf-8').splitlines():
            if line.strip():
                u = json.loads(line)
                units[u['topic_id']] = u
    cunits_path = REG / 'competitor_units.jsonl'
    cunits = {}
    if cunits_path.exists():
        for line in cunits_path.read_text(encoding='utf-8').splitlines():
            if line.strip():
                u = json.loads(line)
                cunits[u['competitor_id']] = u

    seen_exec = {(r.get('executor', ''), r.get('searched_at', ''), r.get('query', ''), r.get('unit_id', '')) for r in log}
    src_by_norm = {norm_url(s['url']): s for s in src}
    dom_group = {}
    for s in src:
        if not domain(s['url']).endswith(MULTI_ORIGIN_HOSTS):
            dom_group.setdefault(domain(s['url']), s['origin_group_id'])
    map_seen = {(m['source_id'], m['unit_kind'], m['unit_id'], m['role'], squash(m.get('quote', ''))[:60]) for m in smap}
    rej_seen = {(r['unit_kind'], r['unit_id'], r['url'], r['reason']) for r in rejected}
    first_fetch_qid = {}
    for r in log:
        if r['query'].startswith('GET ') and 'same_action_as=' not in r.get('notes', ''):
            first_fetch_qid.setdefault(norm_url(r['query'][4:]), r['query_id'])

    traces = defaultdict(list)
    for line in trace_path.read_text(encoding='utf-8').splitlines():
        if line.strip():
            t = json.loads(line)
            traces[(t['unit_kind'], t['unit_id'])].append(t)

    qn = max([int(r['query_id'][1:5]) for r in log if re.fullmatch(r'Q\d{4,}', r['query_id'])] + [0])
    qn = max(qn, max([int(re.sub(r'\D', '', r['query_id']) or 0) for r in log] + [0]))
    sn = max([int(s['source_id'][1:]) for s in src if re.fullmatch(r'S\d+', s['source_id'])] + [0])
    mn = len(smap)
    stats = defaultdict(int)

    def new_qid() -> str:
        nonlocal qn
        qn += 1
        return f'Q{qn:05d}' if qn > 9999 else f'Q{qn:04d}'

    for (kind, uid), runs in sorted(traces.items()):
        if kind not in ('TOPIC', 'COMPETITOR'):
            continue
        sub = 'topics' if kind == 'TOPIC' else 'competitors'
        sp = staging / sub / f'{uid}.json'
        report = {}
        if sp.exists():
            try:
                report = json.loads(sp.read_text(encoding='utf-8'))
            except ValueError:
                stats['invalid_json'] += 1
                report = {}
        if kind == 'TOPIC' and uid not in topics:
            continue
        if kind == 'COMPETITOR' and uid not in comps:
            continue
        topic_for_log = uid if kind == 'TOPIC' else 'AXIS_17_T08'  # competitor work is logged under the direct-competitor axis placeholder
        reported = {}
        for s in report.get('searches', []) if isinstance(report.get('searches'), list) else []:
            if isinstance(s, dict) and isinstance(s.get('query'), str):
                reported[s['query']] = s
        legacy = legacy_by_topic.get(uid, {}) if kind == 'TOPIC' else {}
        for run in runs:
            executor = f"worker:{run['run']}:{run['agent_id']}"
            for s in run['searches']:
                key = (executor, s['ts'], s['query'], uid)
                if key in seen_exec:
                    continue
                seen_exec.add(key)
                rep = reported.get(s['query'], {})
                sid = legacy.get(s['query'], '')
                route = 'LEGACY' if sid else str(rep.get('route') or 'UNREPORTED').upper()
                country, language = lang(s['query'])
                log.append({'query_id': new_qid(), 'searched_at': s['ts'], 'platform': 'web_search_engine', 'query': s['query'], 'country': country,
                            'language': language, 'results_found': str(s['n_links']) if s['ok'] else '0', 'accepted': '0', 'excluded': str(s['n_links']) if s['ok'] else '0',
                            'blocked_reason': '' if s['ok'] else (s.get('error') or 'search tool returned no result block'),
                            'notes': str(rep.get('note', ''))[:300], 'axis_id': topics[topic_for_log], 'topic_id': topic_for_log, 'origin_group_id': '',
                            'retrieval_status': 'SNIPPET_ONLY' if s['ok'] else ('REFUSED_BUDGET' if s.get('refused') else 'ERROR'), 'excluded_reason': '検索要約は証拠にしない' if s['ok'] else '',
                            'suggestion_id': sid, 'route': route, 'followup_for': str(rep.get('followup_for') or ''), 'unit_kind': kind, 'unit_id': uid,
                            'executor': executor, 'verified_by': 'TRANSCRIPT', 'candidate_urls': ' '.join(s['links'][:3])})
                stats['searches_logged'] += 1
            freport = {norm_url(f.get('url', '')): f for f in report.get('fetches', []) if isinstance(f, dict)} if isinstance(report.get('fetches'), list) else {}
            done_urls = set()
            for f in run['fetches']:
                nu = norm_url(f['url'])
                key = (executor, 'FETCH', 'GET ' + f['url'], uid)
                if key in seen_exec or nu in done_urls:
                    continue
                seen_exec.add(key)
                done_urls.add(nu)
                meta = cache.get(f['url']) or {}
                status, chars = int(meta.get('status', f['status']) or 0), int(meta.get('chars', f['chars']) or 0)
                ok = status == 200 and chars > 400
                rep = freport.get(nu, {})
                prior = first_fetch_qid.get(nu)
                qid = new_qid()
                note = str(rep.get('note', ''))[:200]
                if prior:
                    note = (note + f' cache_read same_action_as={prior}').strip()
                else:
                    first_fetch_qid[nu] = qid
                log.append({'query_id': qid, 'searched_at': meta.get('fetched_at') if not prior and meta.get('fetched_at') else f['ts'], 'platform': platform_for(f['url']),
                            'query': 'GET ' + f['url'], 'country': 'GLOBAL', 'language': '', 'results_found': '1' if ok else '0', 'accepted': '0', 'excluded': '0',
                            'blocked_reason': '' if ok else f'HTTP {status} / chars={chars}', 'notes': note, 'axis_id': topics[topic_for_log], 'topic_id': topic_for_log,
                            'origin_group_id': '', 'retrieval_status': 'RETRIEVED_FULL_TEXT' if ok else 'BLOCKED', 'excluded_reason': '',
                            'suggestion_id': '', 'route': str(rep.get('route') or '').upper(), 'followup_for': '', 'unit_kind': kind, 'unit_id': uid,
                            'executor': executor, 'verified_by': 'TRANSCRIPT+FETCH_CACHE', 'candidate_urls': ''})
                stats['fetches_logged'] += 1
        # ---- sources: quote must be found in the cached page
        fetched_norm = {norm_url(f['url']) for run in runs for f in run['fetches']}
        executor0 = f"worker:{runs[-1]['run']}:{runs[-1]['agent_id']}"
        accepted_here = []

        def accept_source(s: dict) -> str:
            """Return the ledger source_id if the candidate passes the mechanical checks, else '' (and record the rejection)."""
            nonlocal sn, mn
            if not isinstance(s, dict) or not str(s.get('url', '')).startswith(('http://', 'https://')):
                return ''
            url, nu, quote = s['url'], norm_url(s['url']), str(s.get('quote', ''))
            role = str(s.get('role', '')).upper()
            role = role if role in ROLES else 'PRIMARY'
            reason = ''
            existing = src_by_norm.get(nu)
            meta = cache.get(url)
            if not meta or int(meta.get('status', 0)) != 200:  # the page must be in the fetch cache; the quote check below is the real guarantee
                reason = 'page not retrieved (status != 200)'
            elif not cache.has_quote(url, quote):
                reason = 'quote not found in cached page text'
            if reason:
                rk = (kind, uid, url, reason)
                if rk not in rej_seen:
                    rej_seen.add(rk)
                    rejected.append({'unit_kind': kind, 'unit_id': uid, 'url': url, 'reason': reason, 'claimed_quote': quote[:300], 'executor': executor0})
                    stats['sources_rejected'] += 1
                return ''
            if not existing:
                d = domain(url)
                org = str(s.get('origin_org') or s.get('publisher') or '')
                if d.endswith(MULTI_ORIGIN_HOSTS):
                    og = f'OG_{slug(d)}__{slug(org)}'
                else:
                    og = dom_group.setdefault(d, f'OG_D_{slug(d)}')
                sn += 1
                st = str(s.get('source_type', 'OTHER')).upper()
                existing = {k: 'UNKNOWN' for k in sf}
                existing.update({'source_id': f'S{sn:03d}' if sn < 1000 else f'S{sn}', 'origin_group_id': og, 'url': url, 'publisher': str(s.get('publisher') or 'UNKNOWN'),
                                 'published_at': str(s.get('published_at') or 'UNKNOWN'), 'checked_at': meta.get('fetched_at', ''), 'source_type': st if st in SOURCE_TYPES else 'OTHER',
                                 'country': str(s.get('country') or 'UNKNOWN'), 'segment': str(s.get('segment') or 'UNKNOWN'),
                                 'axis_id': topics[topic_for_log], 'topic_id': topic_for_log, 'verified_state': 'DIRECT_ORIGINAL', 'is_accepted': 'yes',
                                 'claim_text': str(s.get('claim_text') or ''), 'page_or_section': str(s.get('page_or_section') or 'UNKNOWN'),
                                 'n': str(s.get('n') or 'UNKNOWN'), 'population': str(s.get('population') or 'UNKNOWN'), 'selection_method': str(s.get('selection_method') or 'UNKNOWN'),
                                 'method': str(s.get('method') or 'UNKNOWN'), 'unit': str(s.get('unit') or 'UNKNOWN'), 'counterevidence': 'UNKNOWN', 'bias': str(s.get('bias') or 'UNKNOWN'),
                                 'notes': f'collected by {executor0} for {kind} {uid}', 'quote': quote, 'quote_check': 'FOUND_IN_CACHE',
                                 'statement_kind': str(s.get('statement_kind') or 'UNKNOWN'), 'origin_org': org, 'added_in': 'sweep_2026-11-12', 'review_state': 'S2_PENDING', 'review_notes': ''})
                src.append(existing)
                src_by_norm[nu] = existing
                stats['sources_added'] += 1
            mk = (existing['source_id'], kind, uid, role, squash(quote)[:60])
            if mk not in map_seen:
                map_seen.add(mk)
                mn += 1
                smap.append({'map_id': f'M{mn:05d}', 'source_id': existing['source_id'], 'unit_kind': kind, 'unit_id': uid, 'role': role,
                             'claim_text': str(s.get('claim_text') or ''), 'quote': quote, 'quote_check': 'FOUND_IN_CACHE', 'added_by': executor0, 'review_state': 'S2_PENDING'})
                stats['mappings_added'] += 1
            return existing['source_id']

        for s in report.get('sources', []) if isinstance(report.get('sources'), list) else []:
            sid = accept_source(s)
            if sid:
                accepted_here.append(sid)
        verified_profile, verified_counter = {}, []
        if kind == 'COMPETITOR':
            prof = report.get('profile') if isinstance(report.get('profile'), dict) else {}
            for k, a in prof.items():
                if not isinstance(a, dict):
                    continue
                st = str(a.get('status', '')).upper()
                entry = {'status': st, 'value': str(a.get('value', ''))[:600], 'source_url': str(a.get('source_url', '')), 'quote': str(a.get('quote', ''))[:300], 'source_id': ''}
                if st.startswith('CONFIRMED'):
                    official = st == 'CONFIRMED_OFFICIAL'
                    sid = accept_source({'url': entry['source_url'], 'quote': entry['quote'], 'role': 'PRIMARY' if official else 'INDEPENDENT',
                                         'publisher': comps[uid]['name'] + '（公式）' if official else 'UNKNOWN', 'origin_org': comps[uid]['name'] if official else '',
                                         'source_type': 'OFFICIAL_VENDOR' if official else 'OTHER', 'statement_kind': 'VENDOR_CLAIM' if official else 'UNKNOWN',
                                         'claim_text': f"{k}: {entry['value']}"[:300], 'page_or_section': k, 'method': '公開ページ原文の直接確認（HTTP取得）', 'n': 'N/A', 'population': 'N/A', 'selection_method': 'N/A', 'unit': 'N/A',
                                         'bias': '当事者の表明' if official else '第三者ページ'})
                    if sid:
                        entry['source_id'] = sid
                        accepted_here.append(sid)
                    else:
                        entry['status'] = 'UNVERIFIED_QUOTE_NOT_FOUND'
                        stats['attributes_downgraded'] += 1
                verified_profile[k] = entry
            for cfd in report.get('counter_findings', []) if isinstance(report.get('counter_findings'), list) else []:
                if isinstance(cfd, dict) and cfd.get('source_url') and cache.has_quote(str(cfd['source_url']), str(cfd.get('quote', ''))):
                    verified_counter.append({'summary': str(cfd.get('summary', ''))[:400], 'source_url': cfd['source_url'], 'quote': str(cfd.get('quote', ''))[:300],
                                             'source_id': src_by_norm.get(norm_url(str(cfd['source_url'])), {}).get('source_id', '')})
                else:
                    stats['counter_findings_dropped_unverified'] += 1
        # ---- research unit record (narrative fields are the worker's; values are kept only when their quote is found)
        if report:
            vals = []
            for v in report.get('observed_values', []) if isinstance(report.get('observed_values'), list) else []:
                if isinstance(v, dict) and v.get('source_url') and cache.has_quote(str(v['source_url']), str(v.get('quote', ''))):
                    sid = src_by_norm.get(norm_url(str(v['source_url'])), {}).get('source_id', '')
                    vals.append({**{k: v.get(k, '') for k in ('metric', 'value', 'unit', 'n', 'period', 'geography', 'segment', 'quote')}, 'source_id': sid})
                else:
                    stats['values_dropped_unverified'] += 1
            keep = ('definition', 'primary_status', 'independent_status', 'counter_status', 'absence_reason', 'calculations_proposed', 'non_identifiable',
                    'cross_axis_links', 'contradictions', 'product_implication', 'staleness_notes', 'problems', 'started_at', 'finished_at')
            unit = {k: report.get(k) for k in keep if k in report}
            unit.update({'observed_values_verified': vals, 'source_ids': sorted(set(accepted_here)), 'worker_runs': sorted({f"{r['run']}:{r['agent_id']}" for r in runs})})
            if kind == 'TOPIC':
                prev = units.get(uid, {})
                merged = {**prev, **{k: v for k, v in unit.items() if v not in (None, '', [], {})}}
                for k in ('calculations_proposed', 'non_identifiable', 'cross_axis_links', 'contradictions', 'observed_values_verified'):
                    a = (prev.get(k) or []) + (unit.get(k) or [])
                    merged[k] = [json.loads(x) for x in dict.fromkeys(json.dumps(i, ensure_ascii=False, sort_keys=True) for i in a)]
                merged['source_ids'] = sorted(set(prev.get('source_ids', [])) | set(unit['source_ids']))
                merged['worker_runs'] = sorted(set(prev.get('worker_runs', [])) | set(unit['worker_runs']))
                merged['topic_id'] = uid
                units[uid] = merged
            else:
                ckeep = ('official_status', 'profile', 'counter_findings', 'comparability', 'blockers', 'problems', 'started_at', 'finished_at', 'absence_reason')
                prev = cunits.get(uid, {})
                cu = {**prev, **{k: report.get(k) for k in ckeep if report.get(k) not in (None, '', [], {})}}
                cu['profile'] = {**(prev.get('profile') or {}), **verified_profile}
                cu['counter_findings'] = verified_counter or prev.get('counter_findings', [])
                cu['counter_search_done'] = bool(report.get('searches')) and any(str(x.get('route', '')).upper() in ('COUNTER', 'INDEPENDENT') for x in report.get('searches', []) if isinstance(x, dict))
                cu['competitor_id'] = uid
                cu['source_ids'] = sorted(set(prev.get('source_ids', [])) | set(accepted_here))
                cu['worker_runs'] = sorted(set(prev.get('worker_runs', [])) | {f"{r['run']}:{r['agent_id']}" for r in runs})
                cunits[uid] = cu
            stats['units_recorded'] += 1

    write('search_log.csv', lf, log)
    write('source_evidence.csv', sf, src)
    write('source_topic_map.csv', MAP_FIELDS, smap)
    write('rejected_candidates.csv', REJ_FIELDS, rejected)
    units_path.write_text(''.join(json.dumps(units[k], ensure_ascii=False, sort_keys=True) + '\n' for k in sorted(units)), encoding='utf-8')
    cunits_path.write_text(''.join(json.dumps(cunits[k], ensure_ascii=False, sort_keys=True) + '\n' for k in sorted(cunits)), encoding='utf-8')
    print(json.dumps({**stats, 'search_log_rows': len(log), 'sources': len(src), 'mappings': len(smap), 'rejected': len(rejected),
                      'topic_units': len(units), 'competitor_units': len(cunits)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
