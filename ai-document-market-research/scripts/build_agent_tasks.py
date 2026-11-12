#!/usr/bin/env python3
"""Build per-topic and per-competitor task files for research workers (research tooling only).

Task files are written OUTSIDE the repository (TASK_DIR). Each file carries everything a
worker needs for one unit: the registered topic, its search plan, every legacy query for
that topic (verbatim), and the evidence already in the ledger so nothing is re-fetched.

Usage: python3 scripts/build_agent_tasks.py TASK_DIR STAGING_DIR
"""
import csv, json, re, sys
from collections import defaultdict
from pathlib import Path
R = Path(__file__).resolve().parents[1]; REG = R / 'registry'
def rows(n):
    with (REG / n).open(encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))
def main():
    tdir, sdir = Path(sys.argv[1]), Path(sys.argv[2])
    for d in (tdir / 'topics', tdir / 'competitors', sdir / 'topics', sdir / 'competitors'): d.mkdir(parents=True, exist_ok=True)
    axes, plans, legacy = rows('research_axes.csv'), {p['topic_id']: p for p in rows('search_plans.csv')}, defaultdict(list)
    for q in rows('search_queries_candidates.csv'): legacy[q['topic_id']].append({'suggestion_id': q['suggestion_id'], 'target': q['target'], 'query': q['sample_query']})
    src, log = rows('source_evidence.csv'), rows('search_log.csv')
    by_topic = defaultdict(list)
    for s in src:
        if s['is_accepted'] != 'yes': continue
        entry = {'source_id': s['source_id'], 'url': s['url'], 'publisher': s['publisher'], 'claim': s['claim_text'][:260]}
        by_topic[s['topic_id']].append({**entry, 'relation': 'main topic of this source'})
        m = re.search(r'also:\s*([^。]*)', s['notes'])
        for t in (re.findall(r'AXIS_\d\d_T\d\d', m.group(1)) if m else []): by_topic[t].append({**entry, 'relation': 'also examined for this topic'})
    prior = defaultdict(list)
    for r in log:
        if 'same_action_as=' in r['notes']: continue
        prior[r['topic_id']].append({'query': r['query'][:160], 'status': r['retrieval_status'], 'note': r['notes'][:160]})
    extra = rows('additional_axes.csv') if (REG / 'additional_axes.csv').exists() else []
    for e in extra:
        plans[e['topic_id']] = {**e, 'escalation_rule': '証拠が欠ければ企業名/国/年/反証に分解して検索を追加;同じ起源の転載は増分に数えない'}
    for a in axes + extra:
        t = a['topic_id']; p = plans[t]
        task = {'topic_id': t, 'axis_id': a['axis_id'], 'axis_name': a['axis_name'], 'topic_name': a['topic_name'], 'priority': a['priority'],
                'origin': a['origin'], 'canonical_question': a['canonical_question'],
                'plan': {k: p[k] for k in ('first_primary_route', 'independent_route', 'counterexample_route', 'measurement_plan', 'escalation_rule')},
                'legacy_queries': legacy.get(t, []), 'existing_sources': by_topic.get(t, []), 'prior_attempts': prior.get(t, []),
                'output_file': str(sdir / 'topics' / f'{t}.json')}
        (tdir / 'topics' / f'{t}.json').write_text(json.dumps(task, ensure_ascii=False, indent=1), encoding='utf-8')
    comp_src = {s['source_id']: s for s in src}
    for c in rows('competitor_candidates.csv'):
        ex = [{'source_id': i, 'url': comp_src[i]['url'], 'claim': comp_src[i]['claim_text'][:300]} for i in c['sources'].split(';') if i in comp_src]
        task = {**{k: c[k] for k in ('competitor_id', 'name', 'category', 'official_url_candidate', 'market_role', 'research_priority', 'verification_state', 'claimed_features', 'pricing', 'limitations', 'verification_scope')},
                'existing_sources': ex, 'output_file': str(sdir / 'competitors' / f"{c['competitor_id']}.json")}
        (tdir / 'competitors' / f"{c['competitor_id']}.json").write_text(json.dumps(task, ensure_ascii=False, indent=1), encoding='utf-8')
    print('topics', len(axes), 'legacy queries', sum(len(v) for v in legacy.values()), 'competitors', len(rows('competitor_candidates.csv')))
if __name__ == '__main__': main()
