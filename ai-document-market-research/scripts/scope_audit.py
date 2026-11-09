#!/usr/bin/env python3
"""Inventory reanalysis: counts, identity, original preservation, and static safeguards.

It does NOT estimate product success probability, consumer preference or market size.
Run from any CWD as: python3 scripts/scope_audit.py
"""
import collections,csv,hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def rows(path):
 with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def audit():
 old=R/'original_20261109'
 original=rows(old/'registry/research_axes.csv')
 orig_comp=rows(old/'registry/competitor_candidates.csv')
 cur=rows(R/'registry/research_axes.csv')
 new_comp=rows(R/'registry/competitor_candidates.csv')
 plan=rows(R/'registry/search_plans.csv')
 legacy=rows(R/'registry/search_queries_candidates.csv')
 manifest=json.loads((R/'research/research_manifest.json').read_text(encoding='utf-8'))
 hashes=[]
 for line in (R/'reference_images/CHECKSUM_SHA256.txt').read_text(encoding='utf-8').splitlines():
  if not line.startswith('IMG_'):continue
  filename,sha=line.strip().split('\t')
  p=R/'reference_images'/filename
  if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=sha:hashes.append(filename)
 ax=collections.Counter(x['axis_id'] for x in cur)
 pr=collections.Counter(x['research_priority'] for x in new_comp)
 cat=collections.Counter(x['market_role'] for x in new_comp)
 oid={x['topic_id'] for x in original};cid={x['topic_id'] for x in cur}
 oc={(x['competitor_id'],x['name']) for x in orig_comp};cc={(x['competitor_id'],x['name']) for x in new_comp}
 rs={
 'axes':len(ax),'topics':len(cur),'topics_per_axis_min':min(ax.values()),'topics_per_axis_max':max(ax.values()),
 'initial_search_plans':len(plan),'legacy_unexecuted_search_candidates':len(legacy),'competitor_candidates':len(new_comp),
 'priority_tiers':dict(pr),'candidate_categories':dict(cat),'new_topics':len(cur)-len(original),'new_competitors':len(new_comp)-len(orig_comp),
 'original_topic_ids_all_preserved':oid.issubset(cid), 'original_competitors_all_preserved':oc.issubset(cc),
 'topic_duplicates':len(cur)-len(cid),'competitor_id_duplicates':len(new_comp)-len({x['competitor_id'] for x in new_comp}),
 'plan_id_duplicates':len(plan)-len({x['plan_id'] for x in plan}),
 'plan_for_each_topic':len({x['topic_id'] for x in plan})==len(cur) and {x['topic_id'] for x in plan}==cid,
 'reference_images':len(list((R/'reference_images').glob('IMG_*'))),'image_hash_mismatches':hashes,
 'counts_equal_manifest':len(ax)==manifest['expected_axis_count'] and len(cur)==manifest['expected_topic_count'] and len(new_comp)==manifest['initial_competitor_candidate_count'] and len(plan)==manifest['initial_search_plan_count'],
 'research_is_unperformed':all(x['stage']=='NOT_STARTED' for x in cur) and all(x['verification_state']=='UNVERIFIED_CANDIDATE' for x in new_comp),
 'app_implementation_forbidden':manifest['product_implementation_allowed'] is False and manifest['research_must_stop_after_report'] is True}
 rs['PASS']=all([rs['original_topic_ids_all_preserved'],rs['original_competitors_all_preserved'],rs['topic_duplicates']==0,rs['competitor_id_duplicates']==0,rs['plan_id_duplicates']==0,rs['plan_for_each_topic'],rs['reference_images']==8,not hashes,rs['counts_equal_manifest'],rs['app_implementation_forbidden']])
 return rs
if __name__=='__main__':
 j=audit();print(json.dumps(j,ensure_ascii=False,indent=2));raise SystemExit(0 if j['PASS'] else 2)
