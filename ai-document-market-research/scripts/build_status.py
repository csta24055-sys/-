#!/usr/bin/env python3
"""Recompute the execution-status ledgers from the primary ledgers (research tooling only).

Nothing here is hand-set: writing "PASS" into a status file changes nothing, because the
gate script recomputes the same facts from search_log / source ledgers / unit records.

Writes:
  registry/query_execution_status.csv       896 legacy query ids, EXECUTED / ATTEMPTED_BLOCKED / NOT_EXECUTED
  registry/topic_execution_status.csv       325 topics, per-step state and blockers
  registry/competitor_execution_status.csv  80 candidates, per-attribute state and blockers
and refreshes research_axes.csv `stage`.
Usage: python3 scripts/build_status.py
"""
from __future__ import annotations
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

R = Path(__file__).resolve().parents[1]
REG = R / 'registry'
LEGACY_ROUTE = {'PRIMARY': 'PRIMARY', 'USER_VOICE': 'INDEPENDENT', 'COUNTEREXAMPLE': 'COUNTER', 'INTERNATIONAL': 'INDEPENDENT'}
ATTRS = ['official_site', 'features_processing', 'pricing_limits', 'io_formats', 'pptx_editability', 'speed_claims', 'quality_claims',
         'source_verification', 'data_handling', 'fit_school_work', 'free_alternative_strength']
DONE = ('FOUND', 'NOT_FOUND_AFTER_SEARCH')


def read(name):
    p = REG / name
    if not p.exists():
        return []
    with p.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def write(name, fields, rows):
    with (REG / name).open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)


def jsonl(name, key):
    p = REG / name
    out = {}
    if p.exists():
        for line in p.read_text(encoding='utf-8').splitlines():
            if line.strip():
                d = json.loads(line)
                out[d[key]] = d
    return out


def nonempty(x):
    return bool(x) and str(x).strip() not in ('', 'UNKNOWN')


def compute(reg: Path | None = None, write_files: bool = True) -> dict:
    """Recompute all status rows. With write_files=False nothing is written (used by the gate to detect hand-edited status files)."""
    global REG
    if reg is not None:
        REG = reg
    axes, legacy, log = read('research_axes.csv'), read('search_queries_candidates.csv'), read('search_log.csv')
    src = {s['source_id']: s for s in read('source_evidence.csv') if s.get('is_accepted') == 'yes'}
    smap, units, comps, cunits = read('source_topic_map.csv'), jsonl('topic_units.jsonl', 'topic_id'), read('competitor_candidates.csv'), jsonl('competitor_units.jsonl', 'competitor_id')
    calc = read('calculation_inventory.csv')
    plans = {p['topic_id'] for p in read('search_plans.csv')}

    # ---- legacy queries
    by_sid = defaultdict(list)
    for r in log:
        if r.get('suggestion_id'):
            by_sid[r['suggestion_id']].append(r)
    qrows = []
    for q in legacy:
        rs = [r for r in by_sid.get(q['suggestion_id'], []) if r.get('verified_by', '').startswith('TRANSCRIPT') and r['query'] == q['sample_query']]
        ok = [r for r in rs if r['retrieval_status'] == 'SNIPPET_ONLY']
        err = [r for r in rs if r['retrieval_status'] == 'ERROR']  # a refusal for budget reasons is not an execution and not a permanent block: it must be retried
        state = 'EXECUTED' if ok else ('ATTEMPTED_BLOCKED' if err else 'NOT_EXECUTED')
        first = (ok or err or rs or [{}])[0]
        qrows.append({'suggestion_id': q['suggestion_id'], 'axis_id': q['axis_id'], 'topic_id': q['topic_id'], 'target': q['target'], 'query_verbatim': q['sample_query'],
                      'state': state, 'executed_at': first.get('searched_at', ''), 'platform': first.get('platform', ''), 'results_found': first.get('results_found', ''),
                      'search_log_query_id': first.get('query_id', ''), 'executions': len(rs), 'candidate_urls': first.get('candidate_urls', ''),
                      'failure_reason': '' if ok else (first.get('blocked_reason', '') if rs else 'not executed yet'), 'refused_attempts': sum(r['retrieval_status'] == 'REFUSED_BUDGET' for r in rs),
                      'verified_by': first.get('verified_by', '')})
    if write_files:
        write('query_execution_status.csv', list(qrows[0].keys()) if qrows else ['suggestion_id'], qrows)
    qstate = defaultdict(Counter)
    for q in qrows:
        qstate[q['topic_id']][q['state']] += 1

    # ---- topics
    tlog = defaultdict(list)
    for r in log:
        if (r.get('unit_kind') or 'TOPIC') == 'TOPIC':
            tlog[r.get('unit_id') or r['topic_id']].append(r)
    legacy_target = {q['suggestion_id']: q['target'] for q in legacy}
    tmap = defaultdict(list)
    for m in smap:
        if m['unit_kind'] == 'TOPIC' and m['source_id'] in src:
            tmap[m['unit_id']].append(m)
    calc_by_topic = defaultdict(list)
    for c in calc:
        calc_by_topic[c.get('topic_id', '')].append(c)
    def topic_row(a):
        t = a['topic_id']
        rows = tlog.get(t, [])
        searches = [r for r in rows if r['platform'] == 'web_search_engine' and 'same_action_as=' not in r.get('notes', '')]
        route = Counter()
        for r in searches:
            if r['retrieval_status'] in ('ERROR', 'REFUSED_BUDGET'):
                continue
            rt = r.get('route', '')
            if rt == 'LEGACY':
                rt = LEGACY_ROUTE.get(legacy_target.get(r.get('suggestion_id', ''), ''), '')
            elif rt == 'FOLLOWUP':
                rt = r.get('followup_for', '')
            elif not rt and r.get('verified_by') == 'SESSION_RECORD':
                rt = 'PRIMARY'
            if rt in ('PRIMARY', 'INDEPENDENT', 'COUNTER'):
                route[rt] += 1
        fetches = [r for r in rows if r['query'].startswith('GET ') and 'same_action_as=' not in r.get('notes', '').replace('cache_read same_action_as=', 'cache_read ')]
        fetch_ok = [r for r in fetches if r['retrieval_status'] == 'RETRIEVED_FULL_TEXT']
        maps = tmap.get(t, [])
        prim = [m for m in maps if m['role'] in ('PRIMARY', 'MAIN', 'ALSO')]
        prim_groups = {src[m['source_id']]['origin_group_id'] for m in prim}
        indep = [m for m in maps if m['role'] == 'INDEPENDENT' and src[m['source_id']]['origin_group_id'] not in prim_groups]
        counter = [m for m in maps if m['role'] == 'COUNTER']
        u = units.get(t, {})
        d = u.get('definition') or {}
        unit_ok = all(nonempty(d.get(k)) for k in ('operational_definition', 'population_and_unit', 'business_question')) and bool(u.get('calculations_proposed') or u.get('non_identifiable'))

        def state(found, n_search, need_fetch=False):
            if found:
                return 'FOUND'
            if n_search >= 2 and (not need_fetch or fetches):
                return 'NOT_FOUND_AFTER_SEARCH'
            return 'ATTEMPTED_INSUFFICIENT' if n_search or fetches else 'NO'
        p_state, i_state, c_state = state(prim, route['PRIMARY'], True), state(indep, route['INDEPENDENT']), state(counter, route['COUNTER'])
        lt = sum(qstate[t].values())
        l_open = qstate[t]['NOT_EXECUTED']
        queried = l_open == 0 and route['PRIMARY'] >= 1
        cs = calc_by_topic.get(t, [])
        calc_ok = bool(cs) and all(c.get('status') in ('EXECUTED_AND_VERIFIED', 'NON_IDENTIFIABLE', 'BLOCKED_DATA', 'REJECTED_INVALID_METHOD') for c in cs)
        review_ok = bool(maps) and all(m.get('review_state') in ('S2_VERIFIED', 'S2_REJECTED') for m in maps)
        blockers = []
        if l_open:
            blockers.append(f'legacy queries not executed: {l_open}')
        if route['PRIMARY'] < 1:
            blockers.append('no primary-route search')
        for nm, st in (('primary', p_state), ('independent', i_state), ('counter', c_state)):
            if st not in DONE:
                blockers.append(f'{nm}: {st}')
        if not unit_ok:
            blockers.append('research unit record missing or incomplete')
        s1 = not blockers
        row = ({'topic_id': t, 'axis_id': a['axis_id'], 'priority': a['priority'], 'origin': a['origin'], 'planned': 'YES' if (t in plans or a.get('first_primary_route')) else 'NO',
                      'legacy_total': lt, 'legacy_executed': qstate[t]['EXECUTED'], 'legacy_blocked': qstate[t]['ATTEMPTED_BLOCKED'],
                      'searches_primary': route['PRIMARY'], 'searches_independent': route['INDEPENDENT'], 'searches_counter': route['COUNTER'],
                      'fetch_attempts': len(fetches), 'fetch_ok': len(fetch_ok), 'sources_mapped': len({m['source_id'] for m in maps}),
                      'queried': 'YES' if queried else 'NO', 'primary_checked': p_state, 'independent_checked': i_state, 'counter_checked': c_state,
                      'unit_recorded': 'YES' if unit_ok else 'NO', 'calculation_checked': 'YES' if calc_ok else 'NO', 'review_checked': 'YES' if review_ok else ('N/A_NO_SOURCES' if not maps else 'NO'),
                      'gate_state': 'S1_DONE' if s1 else 'S1_INCOMPLETE', 'blockers': '; '.join(blockers)})
        a['stage'] = 'EVIDENCE_ACCEPTED' if maps else ('ATTEMPTED_NO_ACCEPTED_SOURCE' if rows else 'NOT_STARTED')
        return row

    trows = [topic_row(a) for a in axes]
    extra = read('additional_axes.csv')
    arows = [topic_row(a) for a in extra]
    if write_files:
        write('topic_execution_status.csv', list(trows[0].keys()), trows)
        if arows:
            write('additional_topic_status.csv', list(arows[0].keys()), arows)
            with (REG / 'additional_axes.csv').open(encoding='utf-8-sig', newline='') as f:
                xfields = csv.DictReader(f).fieldnames
            write('additional_axes.csv', xfields, extra)
        with (REG / 'research_axes.csv').open(encoding='utf-8-sig', newline='') as f:
            afields = csv.DictReader(f).fieldnames
        write('research_axes.csv', afields, axes)

    # ---- competitors
    clog = defaultdict(list)
    for r in log:
        if r.get('unit_kind') == 'COMPETITOR':
            clog[r['unit_id']].append(r)
    cmap = defaultdict(list)
    for m in smap:
        if m['unit_kind'] == 'COMPETITOR' and m['source_id'] in src:
            cmap[m['unit_id']].append(m)
    crows = []
    for c in comps:
        cid = c['competitor_id']
        rows = clog.get(cid, [])
        searches = [r for r in rows if r['platform'] == 'web_search_engine' and r['retrieval_status'] not in ('ERROR', 'REFUSED_BUDGET')]
        fetches = [r for r in rows if r['query'].startswith('GET ')]
        u = cunits.get(cid, {})
        prof = u.get('profile') or {}
        maps = cmap.get(cid, [])
        official_sources = [m for m in maps if src[m['source_id']]['source_type'] == 'OFFICIAL_VENDOR']
        prior_official = c.get('verification_state') == 'VERIFIED_OFFICIAL' and all(i in src for i in c.get('sources', '').split(';') if i)
        row = {'competitor_id': cid, 'name': c['name'], 'research_priority': c['research_priority'], 'market_role': c['market_role'],
               'searches': len(searches), 'fetch_attempts': len(fetches), 'fetch_ok': sum(r['retrieval_status'] == 'RETRIEVED_FULL_TEXT' for r in fetches),
               'official_confirmed': 'YES' if (official_sources or prior_official) else 'NO', 'sources_mapped': len({m['source_id'] for m in maps})}
        missing = []
        for k in ATTRS:
            st = (prof.get(k) or {}).get('status', '') if isinstance(prof.get(k), dict) else ''
            row[k] = st or 'NOT_RECORDED'
            if not st:
                missing.append(k)
        counter_done = bool(u.get('counter_findings')) or any(r.get('route') in ('COUNTER', 'INDEPENDENT') or r.get('followup_for') in ('COUNTER', 'INDEPENDENT') for r in searches)
        row['counter_checked'] = 'YES' if counter_done else 'NO'
        confirmed = [k for k in ATTRS if str(row[k]).startswith('CONFIRMED')]
        row['comparability'] = 'COMPARABLE' if (row['official_confirmed'] == 'YES' and len(confirmed) >= 4) else 'NOT_COMPARABLE'
        blockers = []
        if not (fetches or len(searches) >= 2):
            blockers.append('no official-site attempt recorded')
        if missing:
            blockers.append('attributes not recorded: ' + ','.join(missing))
        if not counter_done:
            blockers.append('counter-evidence search missing')
        row['gate_state'] = 'S1_DONE' if not blockers else 'S1_INCOMPLETE'
        row['blockers'] = '; '.join(blockers)
        row['unverifiable_reason'] = str(u.get('blockers') or '')[:300]
        crows.append(row)
    if write_files:
        write('competitor_execution_status.csv', list(crows[0].keys()), crows)
    return {'qrows': qrows, 'trows': trows, 'crows': crows, 'arows': arows, 'additional': dict(Counter(t['gate_state'] for t in arows)),
            'legacy': dict(Counter(q['state'] for q in qrows)), 'topics': dict(Counter(t['gate_state'] for t in trows)),
            'competitors': dict(Counter(c['gate_state'] for c in crows)), 'official_confirmed': sum(c['official_confirmed'] == 'YES' for c in crows)}


if __name__ == '__main__':
    out = compute()
    print(json.dumps({k: v for k, v in out.items() if k not in ('qrows', 'trows', 'crows', 'arows')}, ensure_ascii=False))
