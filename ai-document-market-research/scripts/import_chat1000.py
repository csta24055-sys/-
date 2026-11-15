#!/usr/bin/env python3
"""Import the chat-side 1,000 URL candidates into the research pipeline (research tooling only).

The candidate files were written by another chat session. Nothing in them is trusted as
"read", "original" or "independent": the other session's labels are kept verbatim as CLAIMS,
and a candidate becomes S1 evidence only after a worker of THIS pipeline has fetched the page,
found a verbatim quote in it and the merge step has accepted it for the topic (see
merge_staging.py). This script only accounts, normalises, de-duplicates and plans.

Outputs
  registry/chat1000_candidate_review.csv   one row per candidate row of the nine files (original ids kept)
  research/CHAT1000_FULL_IMPORT_AUDIT.md   accounting, duplicates, collisions with the 38 scheduled-task rows, read-depth mix
  (stdout) JSON summary

Usage: python3 scripts/import_chat1000.py [--cache CACHE_DIR]
"""
from __future__ import annotations
import argparse
import csv
import io
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rules  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EXT, REG, RES = ROOT / 'external_handoff', ROOT / 'registry', ROOT / 'research'
FIRST = ['BROAD_POOL_20261113_PRIMARY_SOURCES_BATCH01.csv', 'BROAD_POOL_20261113_USER_EVIDENCE_BATCH02.csv', 'BROAD_POOL_20261114_VERIFIED_DISCOVERY_BATCH03.csv',
         'BROAD_POOL_20261114_POLICY_SURVEYS_METHODS_BATCH04.csv', 'CHAT500_WEB_ORIGINAL_SOURCES_20261114.csv', 'CHAT500_PRIOR_SEARCH_LOG_INDEXED_BATCH05_20261114.csv']
EXTRA = ['CHAT_EXTRA500_WEB_DISCOVERY_20261114.csv', 'CHAT_EXTRA500_WEB_DISCOVERY_BATCH02_20261114.csv', 'CHAT_EXTRA500_PRIOR_LOG_SCREENED_BATCH03_20261114.csv']
BASE_AUX = ['NEW_ORIGINAL_EVIDENCE_20261113_ADS_POLICY_RESEARCH.csv', 'NEW_ORIGINAL_EVIDENCE_20261113_OCR_UI_RISK.csv']
OTHER_AUX = ['NEW_ORIGINAL_EVIDENCE_20261113_UX_MOBILE_WORKBENCH.csv']  # not named in either accounting: checked separately
AUTO = ['BROAD_POOL_20261114_AUTOMATION_BATCH05.csv'] + [f'AUTOMATION500_BATCH0{i}_20261114.csv' for i in range(1, 10)]
BASE_COMMIT = '4af49d9'  # registry/source_evidence.csv had 464 rows at the commit the other session audited against
REVIEW_FIELDS = ['review_id', 'pool', 'origin_file', 'origin_row', 'original_id', 'url', 'url_key', 'paper_key', 'host', 'claimed_topic', 'claimed_topic_valid', 'competitor_match', 'assigned_units',
                 'claimed_source_class', 'claimed_origin_group', 'claimed_read_depth', 'read_depth_class', 'normalization_rule', 'origin_group',
                 'dup_in_base479', 'dup_in_chat1000', 'dup_auto38', 'current_ledger_source_ids', 'current_ledger_topics', 'cache_state',
                 'verified_topic', 'review_state', 's1_usable', 'validation_reason', 'next_action']


def load_text(text: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(text.lstrip('﻿'))))


def load(path: Path) -> list[dict]:
    return load_text(path.read_text(encoding='utf-8-sig')) if path.exists() else []


def git_show(rev: str, rel: str) -> str:
    return subprocess.run(['git', '-C', str(ROOT), 'show', f'{rev}:ai-document-market-research/{rel}'], capture_output=True, text=True, check=True).stdout


def url_of(r: dict) -> str:
    return (r.get('url') or r.get('source_url') or '').strip()


def id_of(r: dict) -> str:
    return r.get('candidate_id') or r.get('evidence_id') or r.get('source_id') or ''


def their_norm(url: str) -> str:
    """The other session's normalisation (scripts/audit_chat_only_1000.py), reproduced exactly."""
    p = urlsplit((url or '').strip())
    host = (p.hostname or '').lower().removeprefix('www.')
    path = p.path.rstrip('/') or '/'
    if host == 'web3.arxiv.org':
        host = 'arxiv.org'
    if host == 'arxiv.org':
        m = re.match(r'^/(?:abs|pdf|html)/(\d{4}\.\d{4,5})(?:v\d+)?(?:\.pdf)?(?:/.*)?$', path, re.I)
        if m:
            path = '/article/' + m.group(1)
    params = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if k in {'id', 'p', 'page'}]
    return host + path.lower() + (('?' + urlencode(sorted(params))) if params else '')


def paper_key(url: str) -> str:
    """A key for the same paper published under different URLs (DOI, arXiv id, ACL Anthology id, OpenReview id)."""
    u = urlsplit(url.strip())
    s = (u.netloc + u.path).lower()
    m = re.search(r'(10\.\d{4,9}/[^\s?#]+)', s)
    if m:
        doi = re.sub(r'(\.pdf|/full|/abstract|/epdf|/pdf)$', '', m.group(1).rstrip('/'))
        m2 = re.match(r'10\.48550/arxiv\.(\d{4}\.\d{4,5})', doi)
        return f'arxiv:{m2.group(1)}' if m2 else f'doi:{doi}'
    m = re.search(r'arxiv\.org/(?:abs|pdf|html)/(\d{4}\.\d{4,5})', s)
    if m:
        return f'arxiv:{m.group(1)}'
    m = re.search(r'aclanthology\.org/([0-9a-z.\-]+?)(?:\.pdf)?$', s.rstrip('/'))
    if m:
        return f'acl:{m.group(1)}'
    m = re.search(r'openreview\.net/(?:forum|pdf)$', s)
    if m:
        q = dict(parse_qsl(u.query))
        return f"openreview:{q.get('id', '')}" if q.get('id') else ''
    return ''


def read_depth_class(raw: str) -> str:
    r = (raw or '').upper()
    if 'SEARCH_RESULT' in r or 'SNIPPET' in r or 'URL_ONLY' in r or 'SEARCH_LINK' in r:
        return 'SEARCH_RESULT_URL_ONLY'
    if 'PRIOR' in r or 'OLD_LOG' in r:
        return 'PRIOR_LOG_FETCH_NOT_RECHECKED'
    if 'FULL' in r and ('PDF' in r or 'TEXT' in r or 'QUESTIONNAIRE' in r):
        return 'CLAIMED_FULL_TEXT_READ'
    if any(x in r for x in ('ABSTRACT', 'LANDING', 'HTML', 'PAGE', 'ORIGINAL')):
        return 'CLAIMED_LANDING_OR_ABSTRACT_READ'
    return 'UNSTATED'


def topics_of(r: dict) -> list[str]:
    raw = r.get('candidate_topic_ids') or r.get('topic_ids') or r.get('target_topic_ids') or r.get('topic_candidates') or ''
    return [t.strip() for t in re.split(r'[;,\s]+', raw) if t.strip()]


NOT_A_SOURCE = re.compile(r'^((www\.)?(google|bing|duckduckgo|yahoo|search\.yahoo)\.[a-z.]+/(search|url)$|.*/sitemap[^/]*\.xml$|.*/(login|signin|signup|register)$)')
ASSESSED_STATE = {'OFF_TOPIC': 'REJECT_OFF_TOPIC', 'NOT_ORIGINAL': 'HOLD_NOT_ORIGINAL', 'VENDOR_PROMOTION': 'HOLD_VENDOR_PROMOTION', 'BLOCKED': 'BLOCKED_FETCH',
                  'EMPTY': 'BLOCKED_FETCH', 'DUPLICATE_ORIGIN': 'DUPLICATE_ORIGIN', 'USED_AS_SOURCE': 'HOLD_QUOTE_NOT_ACCEPTED'}
OPEN_STATES = ('NOT_READ', 'READ_NOT_YET_ASSESSED', 'IN_LEDGER_OTHER_TOPIC')  # still owed to a worker


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache', default='')
    a = ap.parse_args()
    import merge_staging as ms  # noqa: E402  (Cache reader and URL normaliser of the merge step)
    cache = ms.Cache(Path(a.cache)) if a.cache else None
    topics = {r['topic_id'] for r in load(REG / 'research_axes.csv')} | {r['topic_id'] for r in load(REG / 'additional_axes.csv')}

    # ---------------------------------------------------------------- reproduce both accountings
    base464 = load_text(git_show(BASE_COMMIT, 'registry/source_evidence.csv'))
    base_aux = [(f, i, r) for f in BASE_AUX for i, r in enumerate(load(EXT / f), 1)]
    base479 = [('source_evidence.csv@' + BASE_COMMIT, i, r) for i, r in enumerate(base464, 1)] + base_aux
    B = defaultdict(list)
    for f, i, r in base479:
        B[their_norm(url_of(r))].append(f'{f}#{i}:{id_of(r)}')
    first = [(f, i, r) for f in FIRST for i, r in enumerate(load(EXT / f), 1)]
    extra = [(f, i, r) for f in EXTRA for i, r in enumerate(load(EXT / f), 1)]
    F, E = defaultdict(list), defaultdict(list)
    for f, i, r in first:
        F[their_norm(url_of(r))].append(f'{f}#{i}:{id_of(r)}')
    for f, i, r in extra:
        E[their_norm(url_of(r))].append(f'{f}#{i}:{id_of(r)}')
    first_new = set(F) - set(B)
    extra_new = set(E) - set(B) - set(F)
    # the earlier "502 rows / 2 overlaps" figure: the same files at the commit of that report
    early_rev = 'f4bc158'
    early = []
    for f in FIRST:
        try:
            early += [(f, i, r) for i, r in enumerate(load_text(git_show(early_rev, f'external_handoff/{f}')), 1)]
        except subprocess.CalledProcessError:
            pass
    early_keys = {their_norm(url_of(r)) for _, _, r in early}
    early_overlap_simple = sorted({url_of(r) for _, _, r in early if url_of(r) in {url_of(x) for _, _, x in base479}})

    # ---------------------------------------------------------------- 38 scheduled-task rows (reference / dedup only)
    auto = [(f, i, r) for f in AUTO for i, r in enumerate(load(EXT / f), 1)]
    A = defaultdict(list)
    Apaper, Aorigin = defaultdict(list), defaultdict(list)
    for f, i, r in auto:
        A[their_norm(url_of(r))].append(id_of(r))
        if paper_key(url_of(r)):
            Apaper[paper_key(url_of(r))].append(id_of(r))
        if r.get('origin_group'):
            Aorigin[r['origin_group'].strip().upper()].append(id_of(r))
    other_aux = [(f, i, r) for f in OTHER_AUX for i, r in enumerate(load(EXT / f), 1)]

    # ---------------------------------------------------------------- the current ledger (what this pipeline has verified so far)
    src = [s for s in load(REG / 'source_evidence.csv') if s.get('is_accepted') == 'yes']
    by_key = defaultdict(list)
    for s in src:
        by_key[their_norm(s['url'])].append(s['source_id'])
    smap = load(REG / 'source_topic_map.csv')
    topics_by_sid = defaultdict(set)
    for m in smap:
        if m.get('unit_kind') == 'TOPIC' and m.get('quote_check') in ('FOUND_IN_CACHE', 'PENDING_BACKFILL'):
            topics_by_sid[m['source_id']].add(m['unit_id'])
    base_paper = {paper_key(url_of(r)): f'{f}#{i}:{id_of(r)}' for f, i, r in base479 if paper_key(url_of(r))}
    off = rules.official_rules(REG)
    assessed = defaultdict(list)
    for x in load(REG / 'candidate_assessments.csv'):
        if x.get('opened_by_unit') == 'YES':
            assessed[x['review_id']].append(x)

    # ---------------------------------------------------------------- one review row per candidate row
    out, seen_key, seen_paper, seen_origin = [], {}, {}, {}
    n = 0
    for pool, rows_ in (('CHAT_FIRST', first), ('CHAT_EXTRA', extra)):
        for f, i, r in rows_:
            n += 1
            url = url_of(r)
            key, pk = their_norm(url), paper_key(url)
            ts = topics_of(r)
            og_claim = (r.get('origin_group') or r.get('origin_key_tentative') or r.get('origin_alias_key') or '').strip()
            og = pk or (og_claim.upper() if og_claim and not og_claim.upper().startswith('ORIGIN_NOT_VERIFIED') else '') or ('URL:' + key)
            rd_raw = r.get('read_depth', '')
            sids = by_key.get(key, [])
            vt = sorted(set().union(*[topics_by_sid[s] for s in sids]) & set(ts)) if sids else []
            cs = 'NOT_CHECKED'
            if cache is not None:
                m = cache.get(url)
                cs = 'NOT_IN_CACHE' if not m else ('HTTP_200_TEXT' if cache.page_ok(url) else f"BLOCKED_HTTP_{m.get('status')}_chars_{m.get('chars')}")
            dup_base = B.get(key, []) or ([base_paper[pk]] if pk in base_paper else [])
            dup_chat = seen_key.get(key) or (seen_paper.get(pk) if pk else None)
            dup_auto = A.get(key, []) or (Apaper.get(pk, []) if pk else []) or (Aorigin.get(og_claim.upper(), []) if og_claim and not og_claim.upper().startswith('ORIGIN_NOT_VERIFIED') else [])
            rid = f'CH1000_{n:04d}'
            if key not in seen_key:
                seen_key[key] = rid
            if pk and pk not in seen_paper:
                seen_paper[pk] = rid
            reasons, nxt = [], ''
            host = rules.host_of(url)
            if not url.startswith(('http://', 'https://')):
                state, reasons = 'REJECT_NO_URL', ['no usable URL']
            elif NOT_A_SOURCE.search(host + urlsplit(url).path.lower()):
                state, reasons = 'REJECT_NOT_A_SOURCE', ['search-engine result page, sitemap or login page']
            elif dup_chat:
                state, reasons = 'DUPLICATE_ORIGIN', [f'same URL key or paper as {dup_chat}']
            elif vt:
                state, reasons = 'IN_LEDGER_QUOTE_VERIFIED_FOR_TOPIC', [f'accepted by this pipeline as {";".join(sids)} with a quote found in the fetched page for {";".join(vt)} (S2 review pending)']
            elif sids:
                state, reasons = 'IN_LEDGER_OTHER_TOPIC', [f'accepted by this pipeline as {";".join(sids)} but not (yet) for the claimed topic(s)']
                nxt = 'topic worker: read page for the claimed topic and quote the passage that answers it, or record that it does not'
            elif cs.startswith('BLOCKED'):
                state, reasons = 'BLOCKED_FETCH', [f'this pipeline fetched it: {cs}']
                nxt = 'look for a lawful alternative copy (publisher PDF, repository) or keep blocked'
            elif cs == 'HTTP_200_TEXT':
                state, reasons = 'READ_NOT_YET_ASSESSED', ['page is in this pipeline\'s fetch cache but no quote was accepted for the claimed topic yet']
                nxt = 'topic worker: assess relevance and quote, or record REJECT_OFF_TOPIC with reason'
            else:
                state, reasons = 'NOT_READ', ['not fetched by this pipeline; the other session\'s read-depth label is a claim, not a record']
                nxt = 'topic worker: fetch page, quote the passage that answers the claimed topic, or record off-topic'
            if dup_base:
                reasons.append('URL/paper already in the 479 base records: ' + ', '.join(dup_base[:2]))
            if dup_auto:
                reasons.append('also in scheduled-task rows (reference only): ' + ','.join(dict.fromkeys(dup_auto)))
            comp = [c for c in sorted(off) if rules.is_official(off, c, url)]
            own = assessed.get(rid, [])
            if own and state in OPEN_STATES + ('BLOCKED_FETCH',):
                last = own[-1]
                state = ASSESSED_STATE.get(last['outcome'], state)
                reasons = [f"opened by worker for {last['unit_id']}: {last['outcome']} — {last['reason']}"] + reasons[1:]
                nxt = '' if state != 'HOLD_QUOTE_NOT_ACCEPTED' else 'quote was not found on the page: re-read and quote exactly, or reject'
            units_ = [t for t in ts if t in topics and not (t == 'AXIS_17_T08' and comp)] + comp
            bad_t = [t for t in ts if t not in topics]
            out.append({'review_id': rid, 'pool': pool, 'origin_file': f, 'origin_row': i, 'original_id': id_of(r), 'url': url, 'url_key': key, 'paper_key': pk, 'host': host,
                        'claimed_topic': ';'.join(ts), 'claimed_topic_valid': 'NO:' + ';'.join(bad_t) if bad_t else ('YES' if ts else 'NO_TOPIC'),
                        'competitor_match': ';'.join(comp), 'assigned_units': ';'.join(units_),
                        'claimed_source_class': r.get('source_class') or r.get('original_source_class') or '', 'claimed_origin_group': og_claim,
                        'claimed_read_depth': rd_raw, 'read_depth_class': read_depth_class(rd_raw),
                        'normalization_rule': 'host lower, www. dropped, trailing / dropped, arXiv abs|pdf|html+version -> /article/<id>, query kept only for id|p|page; paper key from DOI / arXiv / ACL id',
                        'origin_group': og, 'dup_in_base479': ' | '.join(dup_base[:3]), 'dup_in_chat1000': dup_chat or '', 'dup_auto38': ','.join(dict.fromkeys(dup_auto)),
                        'current_ledger_source_ids': ';'.join(sids), 'current_ledger_topics': ';'.join(sorted(set().union(*[topics_by_sid[s] for s in sids]))) if sids else '',
                        'cache_state': cs, 'verified_topic': ';'.join(vt), 'review_state': state, 's1_usable': 'YES_PENDING_S2' if state == 'IN_LEDGER_QUOTE_VERIFIED_FOR_TOPIC' else 'NO',
                        'validation_reason': ' / '.join(reasons), 'next_action': nxt})
    with (REG / 'chat1000_candidate_review.csv').open('w', encoding='utf-8-sig', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=REVIEW_FIELDS)
        w.writeheader()
        w.writerows(out)

    # ---------------------------------------------------------------- 38 scheduled-task rows against everything
    auto_rows = []
    allchat_paper = {x['paper_key']: x['review_id'] for x in out if x['paper_key']}
    allchat_key = {x['url_key']: x['review_id'] for x in out}
    allchat_origin = defaultdict(list)
    for x in out:
        if x['claimed_origin_group'] and not x['claimed_origin_group'].upper().startswith('ORIGIN_NOT_VERIFIED'):
            allchat_origin[x['claimed_origin_group'].upper()].append(x['review_id'])
    for f, i, r in auto:
        k, pk = their_norm(url_of(r)), paper_key(url_of(r))
        auto_rows.append({'id': id_of(r), 'file': f, 'row': i, 'url': url_of(r), 'in_base479': bool(B.get(k)) or pk in base_paper,
                          'in_chat1000_url': allchat_key.get(k, ''), 'in_chat1000_paper': allchat_paper.get(pk, '') if pk else '',
                          'in_chat1000_origin': ','.join(allchat_origin.get((r.get('origin_group') or '').upper(), [])), 'in_current_ledger': ';'.join(by_key.get(k, []))})

    summary = {
        'files_first': {f: len(load(EXT / f)) for f in FIRST}, 'files_extra': {f: len(load(EXT / f)) for f in EXTRA},
        'rows_first': len(first), 'rows_extra': len(extra), 'rows_total': len(first) + len(extra),
        'base479_rows': len(base479), 'base464_at_commit': BASE_COMMIT,
        'first_distinct_keys': len(F), 'first_keys_in_base479': len(set(F) & set(B)), 'first_internal_alias_keys': sum(len(v) > 1 for v in F.values()),
        'first_net_new_keys': len(first_new), 'extra_distinct_keys': len(E), 'extra_net_new_keys': len(extra_new),
        'extra_overlap_base_or_first': len(set(E) & (set(B) | set(F))), 'net_new_chat_keys_vs_base479': len(first_new) + len(extra_new),
        'early_report_rev': early_rev, 'early_rows_first': len(early), 'early_distinct_keys': len(early_keys),
        'early_keys_in_base479': len(early_keys & set(B)), 'early_exact_url_matches_in_base479': len(early_overlap_simple),
        'paper_level_duplicates_within_chat1000': sum(1 for x in out if x['dup_in_chat1000'] and x['paper_key']),
        'url_or_paper_duplicates_within_chat1000': sum(1 for x in out if x['dup_in_chat1000']),
        'paper_matches_base479_not_caught_by_url': sum(1 for x in out if x['paper_key'] in base_paper and not B.get(x['url_key'])),
        'auto38_rows': len(auto), 'auto38_ids': sorted(id_of(r) for _, _, r in auto),
        'auto38_collisions': [x for x in auto_rows if x['in_chat1000_url'] or x['in_chat1000_paper'] or x['in_chat1000_origin'] or x['in_base479']],
        'ux_mobile_workbench_rows': len(other_aux),
        'ux_mobile_in_chat1000_or_base': sum(1 for _, _, r in other_aux if allchat_key.get(their_norm(url_of(r))) or B.get(their_norm(url_of(r)))),
        'read_depth_class': dict(Counter(x['read_depth_class'] for x in out)),
        'review_state': dict(Counter(x['review_state'] for x in out)),
        'cache_state': dict(Counter(x['cache_state'].split('_chars')[0] for x in out)),
        'claimed_topic_valid': dict(Counter(x['claimed_topic_valid'][:3] for x in out)),
        'now_in_current_ledger': sum(1 for x in out if x['current_ledger_source_ids']),
        's1_usable_pending_s2': sum(1 for x in out if x['s1_usable'] != 'NO'),
        'distinct_origin_groups': len({x['origin_group'] for x in out if x['review_state'] not in ('DUPLICATE_ORIGIN', 'REJECT_NO_URL', 'REJECT_NOT_A_SOURCE')}),
        'current_ledger_accepted_sources': len(src),
    }
    (ROOT / 'research' / 'chat1000_import_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({k: v for k, v in summary.items() if k not in ('auto38_ids',)}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
