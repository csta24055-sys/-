#!/usr/bin/env python3
"""Initialise / refresh registry/calculation_inventory.csv for EVERY topic (research tooling only).

Each topic (325 + added 7) gets its calculation ids from the research unit record:
  calculations_proposed  -> CALC_<topic>_Cnn   (target, formula, observed / assumed inputs as the worker listed them)
  non_identifiable       -> CALC_<topic>_Nnn   (quantity, reason, data needed, symbolic form)
  no unit record yet     -> CALC_<topic>_C00   placeholder (status NOT_STARTED)

Nothing is executed here. Rows enter as PLANNED / NOT_STARTED, which are NOT terminal states: the S5
gate passes only after every id is EXECUTED_AND_VERIFIED / NON_IDENTIFIABLE / BLOCKED_DATA /
REJECTED_INVALID_METHOD with a script, an independent check and verified sources. Rows that a later
stage has already moved to a terminal state (status column) are kept as they are.
Usage: python3 scripts/build_calc_inventory.py
"""
from __future__ import annotations
import csv
import json
from pathlib import Path

R = Path(__file__).resolve().parents[1]
REG = R / 'registry'
FIELDS = ['calc_id', 'topic_id', 'kind', 'target', 'formula', 'inputs_observed', 'inputs_assumed', 'script', 'result', 'independent_check', 'status', 'category',
          'source_ids', 'limits', 'expected_status_by_worker', 'worker_reason', 'data_needed', 'experiment', 'staleness', 'recorded_from']
TERMINAL = {'EXECUTED_AND_VERIFIED', 'NON_IDENTIFIABLE', 'BLOCKED_DATA', 'REJECTED_INVALID_METHOD'}


def rows(name):
    p = REG / name
    if not p.exists():
        return []
    with p.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def j(x) -> str:
    if isinstance(x, list):
        return ' ; '.join(str(i) for i in x)
    return '' if x is None else str(x)


def main() -> None:
    topics = [r['topic_id'] for r in rows('research_axes.csv')] + [r['topic_id'] for r in rows('additional_axes.csv')]
    units = {}
    p = REG / 'topic_units.jsonl'
    if p.exists():
        for line in p.read_text(encoding='utf-8').splitlines():
            if line.strip():
                u = json.loads(line)
                units[u['topic_id']] = u
    old = {r['calc_id']: r for r in rows('calculation_inventory.csv')}
    out = []
    for t in topics:
        u = units.get(t, {})
        cs = [c for c in (u.get('calculations_proposed') or []) if isinstance(c, dict)]
        ns = [n for n in (u.get('non_identifiable') or []) if isinstance(n, dict)]
        new = []
        for i, c in enumerate(cs, 1):
            new.append({'calc_id': f'CALC_{t}_C{i:02d}', 'topic_id': t, 'kind': 'CALCULATION', 'target': j(c.get('target')), 'formula': j(c.get('formula')),
                        'inputs_observed': j(c.get('inputs_observed')), 'inputs_assumed': j(c.get('inputs_assumed')), 'status': 'PLANNED',
                        'expected_status_by_worker': j(c.get('expected_status')), 'worker_reason': j(c.get('reason')),
                        'staleness': j(u.get('staleness_notes'))[:200], 'recorded_from': 'topic_units.jsonl:' + ','.join(u.get('worker_runs', [])[-1:])})
        for i, n in enumerate(ns, 1):
            new.append({'calc_id': f'CALC_{t}_N{i:02d}', 'topic_id': t, 'kind': 'UNIDENTIFIED_QUANTITY', 'target': j(n.get('quantity')), 'formula': j(n.get('symbolic_form')) or '記号式未記入',
                        'status': 'PLANNED', 'expected_status_by_worker': 'NON_IDENTIFIABLE', 'worker_reason': j(n.get('reason')), 'data_needed': j(n.get('data_needed')),
                        'experiment': j(n.get('experiment')), 'recorded_from': 'topic_units.jsonl:' + ','.join(u.get('worker_runs', [])[-1:])})
        if not new:
            new.append({'calc_id': f'CALC_{t}_C00', 'topic_id': t, 'kind': 'PLACEHOLDER', 'target': '（研究ユニット未記録のため計算対象は未定）', 'formula': '未定',
                        'status': 'NOT_STARTED', 'worker_reason': 'S1の研究ユニットが未記録', 'recorded_from': ''})
        for r in new:
            prev = old.get(r['calc_id'])
            if prev and prev.get('status') in TERMINAL:  # a later stage already settled it
                r = {**r, **{k: prev.get(k, '') for k in FIELDS if k in prev}}
            out.append(r)
    with (REG / 'calculation_inventory.csv').open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction='ignore')
        w.writeheader()
        for r in out:
            w.writerow({k: r.get(k, '') for k in FIELDS})
    from collections import Counter
    print(json.dumps({'calc_ids': len(out), 'topics': len(topics), 'by_kind': dict(Counter(r['kind'] for r in out)), 'by_status': dict(Counter(r['status'] for r in out))}, ensure_ascii=False))


if __name__ == '__main__':
    main()
