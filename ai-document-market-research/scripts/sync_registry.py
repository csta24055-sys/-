#!/usr/bin/env python3
"""Synchronise registry status columns from the evidence ledger (research tooling only).

1. For every accepted source, each secondary topic listed in its notes ("also: ...")
   gets a search_log row tied to the original page access (`same_action_as=`),
   because the page was examined for that topic when it was read.
2. research_axes.csv `stage` is derived per topic:
   EVIDENCE_ACCEPTED (an accepted source addresses it) / ATTEMPTED_NO_ACCEPTED_SOURCE / NOT_STARTED.
3. competitor_candidates.csv is updated from scripts/competitor_findings.json
   (hand-written from the sources actually read). Nothing is inferred.
Idempotent: running twice adds nothing.
"""
import csv, json, re
from pathlib import Path
R = Path(__file__).resolve().parents[1]
REG = R / 'registry'

def read(name):
    with (REG / name).open(encoding='utf-8-sig', newline='') as f:
        r = csv.DictReader(f); return list(r.fieldnames), list(r)

def write(name, fields, rows):
    with (REG / name).open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)

af, axes = read('research_axes.csv')
topic_axis = {r['topic_id']: r['axis_id'] for r in axes}
sf, src = read('source_evidence.csv')
lf, log = read('search_log.csv')
by_url = {r['query'][4:]: r for r in log if r['query'].startswith('GET ') and 'same_action_as=' not in r['notes']}
existing = {(re.search(r'same_action_as=(Q\d+)', r['notes']).group(1), r['topic_id']) for r in log if 'same_action_as=' in r['notes']}
n = len(log); added = 0
secondary = {}
for s in src:
    if s['is_accepted'] != 'yes': continue
    m = re.search(r'also:\s*([^。]*)', s['notes'])
    topics = re.findall(r'AXIS_\d\d_T\d\d', m.group(1)) if m else []
    secondary[s['source_id']] = topics
    base = by_url.get(s['url'])
    if not base: continue
    for t in topics:
        if t not in topic_axis or (base['query_id'], t) in existing or t == base['topic_id']: continue
        n += 1; added += 1
        row = dict(base); row.update(query_id=f'Q{n:04d}', topic_id=t, axis_id=topic_axis[t], accepted='0', excluded='0',
                                     notes=f"{s['source_id']}の原文をこのテーマの観点でも確認 same_action_as={base['query_id']}")
        log.append(row); existing.add((base['query_id'], t))
write('search_log.csv', lf, log)

accepted_topics = set()
for s in src:
    if s['is_accepted'] == 'yes':
        accepted_topics.add(s['topic_id']); accepted_topics.update(t for t in secondary.get(s['source_id'], []) if t in topic_axis)
attempted = {r['topic_id'] for r in log}
for a in axes:
    t = a['topic_id']
    a['stage'] = 'EVIDENCE_ACCEPTED' if t in accepted_topics else ('ATTEMPTED_NO_ACCEPTED_SOURCE' if t in attempted else 'NOT_STARTED')
write('research_axes.csv', af, axes)

cf, comp = read('competitor_candidates.csv')
findings = json.loads((Path(__file__).parent / 'competitor_findings.json').read_text(encoding='utf-8'))
acc = {s['source_id'] for s in src if s['is_accepted'] == 'yes'}
for c in comp:
    f = findings.get(c['competitor_id'])
    if not f: continue
    ids = [x for x in f['sources'].split(';') if x]
    assert set(ids) <= acc, (c['competitor_id'], ids)
    c.update(verification_state=f['state'], claimed_features=f['features'], tested_features='NOT_TESTED（実機検証は未実施）',
             pricing=f['pricing'], sources=f['sources'], limitations=f['limits'], verification_scope=f['scope'])
write('competitor_candidates.csv', cf, comp)
from collections import Counter
print('same-action rows added:', added, '| stages:', dict(Counter(a['stage'] for a in axes)),
      '| competitors:', dict(Counter(c['verification_state'] for c in comp)))
