#!/usr/bin/env python3
"""Plan the next collection batch under the per-turn web-search budget (research tooling only).

The search tool allows a fixed number of calls per turn, shared by all workers. This script
picks the next units (topics, additional topics, competitor candidates) that are not yet
S1_DONE, gives each one an explicit search allowance, and stops when the planned total
reaches the budget. Nothing is dropped: units that do not fit simply wait for a later batch.
Importance only decides ORDER.

It rewrites the task file of every selected unit with a `todo` block:
  legacy_queries_todo   legacy queries of this topic that were never really executed (verbatim)
  routes_todo           routes (PRIMARY / INDEPENDENT / COUNTER) that still need a search or a source
  max_searches          hard cap for this worker
  previous_search_results  links returned by earlier real searches for this unit (so they need not be repeated)
  previous_unit         the unit record merged so far, if any

Usage: python3 scripts/next_batch.py TASK_DIR STAGING_DIR BUDGET GROUPS  -> prints JSON {groups: [[kind:id,...],...]}
"""
from __future__ import annotations
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_status  # noqa: E402

R = Path(__file__).resolve().parents[1]
REG = R / 'registry'
DONE = ('FOUND', 'NOT_FOUND_AFTER_SEARCH')


def rows(n):
    p = REG / n
    if not p.exists():
        return []
    with p.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def main() -> None:
    tdir, sdir, budget, groups = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    st = build_status.compute(REG, write_files=False)
    qstate = defaultdict(list)
    for q in st['qrows']:
        if q['state'] == 'NOT_EXECUTED':
            qstate[q['topic_id']].append({'suggestion_id': q['suggestion_id'], 'target': q['target'], 'query': q['query_verbatim']})
    prev = defaultdict(list)
    trace = sdir / 'trace.jsonl'
    if trace.exists():
        for line in trace.read_text(encoding='utf-8').splitlines():
            if line.strip():
                t = json.loads(line)
                for s in t['searches']:
                    if s['ok']:
                        prev[(t['unit_kind'], t['unit_id'])].append({'query': s['query'], 'links': s['links'][:6]})
    units = {}
    up = REG / 'topic_units.jsonl'
    if up.exists():
        for line in up.read_text(encoding='utf-8').splitlines():
            if line.strip():
                u = json.loads(line)
                units[u['topic_id']] = u
    cunits = {}
    cp = REG / 'competitor_units.jsonl'
    if cp.exists():
        for line in cp.read_text(encoding='utf-8').splitlines():
            if line.strip():
                u = json.loads(line)
                cunits[u['competitor_id']] = u

    cand = []
    for t in st['trows'] + st['arows']:
        if t['gate_state'] == 'S1_DONE':
            continue
        routes = [nm for nm, key in (('PRIMARY', 'primary_checked'), ('INDEPENDENT', 'independent_checked'), ('COUNTER', 'counter_checked')) if t[key] not in DONE]
        legacy = qstate.get(t['topic_id'], [])
        need_open = t['primary_checked'] not in DONE and int(t['fetch_attempts']) == 0
        allowance = len(legacy) + len(routes) + (2 if routes else 0)
        cand.append({'kind': 'TOPIC', 'id': t['topic_id'], 'priority': t['priority'], 'allowance': allowance, 'legacy': legacy, 'routes': routes,
                     'need_unit': t['unit_recorded'] != 'YES', 'need_open': need_open})
    for c in st['crows']:
        if c['gate_state'] == 'S1_DONE':
            continue
        has_profile = bool((cunits.get(c['competitor_id'], {}).get('profile') or {}))
        # official pages are read directly; searches are needed for the independent/counter route (and to locate vendor pages when the direct route failed)
        allowance = 2 if (has_profile and c['official_confirmed'] == 'YES') else (3 if has_profile else 4)
        cand.append({'kind': 'COMPETITOR', 'id': c['competitor_id'], 'priority': c['research_priority'], 'allowance': allowance, 'legacy': [],
                     'routes': ['COUNTER'] if has_profile else ['PRIMARY', 'COUNTER'], 'need_unit': not has_profile, 'need_open': True})
    tops = sorted([c for c in cand if c['kind'] == 'TOPIC'], key=lambda c: (c['priority'], c['id']))
    cmps = sorted([c for c in cand if c['kind'] == 'COMPETITOR'], key=lambda c: (c['priority'], c['id']))
    order = []
    while tops or cmps:  # interleave: four topics, then one competitor
        for _ in range(4):
            if tops:
                order.append(tops.pop(0))
        if cmps:
            order.append(cmps.pop(0))
    picked, total = [], 0
    for c in order:
        if total + c['allowance'] > budget:
            continue
        picked.append(c)
        total += c['allowance']
    for c in picked:
        sub = 'topics' if c['kind'] == 'TOPIC' else 'competitors'
        p = tdir / sub / f"{c['id']}.json"
        task = json.loads(p.read_text(encoding='utf-8'))
        task['todo'] = {'legacy_queries_todo': c['legacy'], 'routes_todo': c['routes'], 'max_searches': c['allowance'],
                        'need_unit_record': c['need_unit'], 'need_to_open_originals': c['need_open'],
                        'previous_search_results': prev.get((c['kind'], c['id']), [])[:12]}
        if c['kind'] == 'TOPIC' and c['id'] in units:
            u = units[c['id']]
            task['previous_unit'] = {k: u.get(k) for k in ('definition', 'primary_status', 'independent_status', 'counter_status', 'absence_reason', 'source_ids')}
        if c['kind'] == 'COMPETITOR' and c['id'] in cunits:
            task['previous_unit'] = {'profile_status': {k: (v or {}).get('status') for k, v in (cunits[c['id']].get('profile') or {}).items()}}
        p.write_text(json.dumps(task, ensure_ascii=False, indent=1), encoding='utf-8')
    out = [[] for _ in range(groups)]
    for i, c in enumerate(picked):
        out[i % groups].append(f"{c['kind']}:{c['id']}")
    print(json.dumps({'planned_searches': total, 'units': len(picked), 'remaining_units_after': len(order) - len(picked),
                      'remaining_search_estimate': sum(c['allowance'] for c in order) - total, 'groups': out}, ensure_ascii=False))


if __name__ == '__main__':
    main()
