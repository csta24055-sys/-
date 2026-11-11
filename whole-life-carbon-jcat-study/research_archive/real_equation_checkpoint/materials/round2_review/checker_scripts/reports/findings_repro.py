"""Reproduces the evidence of findings REP-1 .. REP-18 (read-only; prints only)."""
import json, re, collections
R='/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/'
L=lambda p: json.load(open(R+p)); T=lambda p: open(R+p,encoding='utf-8').read()
C=collections.Counter
U=L('01_LEDGER/units.json'); units=U['units']; iu=L('04_VERIFICATION/input_usage.json'); F=iu['fields']
unl=L('01_LEDGER/unlinked_input_disposition.json'); RR=L('03_MODELS/records/units.json')['records']
PU=L('05_DECISIONS/progress_ledger.json')['units']; models=L('03_MODELS/models.json')
axb=L('02_RANKING/axis_b.json'); tr=L('03_MODELS/judge_proposal_trace.json'); cov=L('01_LEDGER/sheet_family_coverage.json')
cands=L('03_MODELS/candidates.json')['candidates']; ap=L('04_VERIFICATION/approximation_study.json')['candidates']
print('REP-1  04 README:', re.search(r'入力仕様 .*?使われない。',T('04_VERIFICATION/README.md')).group())
print('       spec inputs not read by the reference:',sum(1 for k,v in F.items() if not k.startswith('NEW:') and not v['reference_all_units']),'of',iu['inputs_in_specification'],
      '| ledger METADATA_ONLY:',sum(1 for i in unl['inputs'] if i['disposition']=='METADATA_ONLY'),'| input_usage.metadata_only_inputs:',iu['metadata_only_inputs'])
med={r['id']:r['median_by_criterion'] for r in axb['ranking']}; pm={u['id']:u for u in PU}
print('REP-2  trace criteria:',dict(C((x['criterion'],x['meaning'],x['step']) for x in tr['score_2_or_more'])))
b8=[u for u in med if med[u]['b8']>=2]; b6=[u for u in med if med[u]['b6']>=2]
print('       with b8 (protocol P5 "共通の代理モデル"): unit-steps',len(b6)+len(b8),'not measured',
      sum(pm[u]['steps']['M3']['conclusion']=='NOT_APPLICABLE' for u in b6)+sum(pm[u]['steps']['M4']['conclusion']=='NOT_APPLICABLE' for u in b8),'| reported 52 / 20')
suc=[r for r in RR if r['outcome']=='SUCCESS']
print('REP-3  SUCCESS records',len(suc),'without mechanism',sum(1 for r in suc if not r['mechanism']),'without derivation',sum(1 for r in suc if not r['derivation']),
      'neither',[r['candidate_id'] for r in suc if not r['mechanism'] and not r['derivation']])
print('       no-mechanism:',[r['candidate_id'] for r in suc if not r['mechanism']])
k5=[m for m in models['models'] if m['id']=='K5'][0]['units']
print('REP-4  K5 units',k5,'M1:',[pm[u]['steps']['M1']['conclusion'] for u in k5]); print('       rule:',models['membership_rule'])
only15=[u['id'] for u in PU if [c['candidate_id'] for c in u['steps']['M4']['candidates']]==['AP-15']]
hold=[u for u in PU if u['status'].startswith('DONE') and u['steps_on_hold']]
h15=[u['id'] for u in hold if all({c['candidate_id'] for c in u['steps'][s]['candidates'] if c['outcome']=='HOLD'}<={'AP-15'} for s in u['steps_on_hold'])]
print('REP-5  M4 HOLD units',sum(u['steps']['M4']['conclusion']=='HOLD' for u in PU),'only via AP-15',len(only15),'| DONE units with a hold',len(hold),'only via AP-15',len(h15),
      '| NA unit-steps M3..M6',sum(u['steps'][s]['conclusion']=='NOT_APPLICABLE' for u in PU for s in('M3','M4','M5','M6')),'of',4*len(PU),
      '| units with no measured approximation',sum(1 for u in PU if not any(c['candidate_id'].startswith('AP-') for s in u['steps'].values() for c in s['candidates'])))
keys=set().union(*[set(c) for c in ap.values()])
print('REP-6  load-related keys in approximation_study:',sorted(k for k in keys if re.search('time|memory|instruction|input',k)),'| by_material for',sum(1 for c in ap.values() if c.get('by_material_class')),'of',len(ap),
      '| reasons with 同じ手間:',[c['candidate_id'] for c in cands if '同じ手間' in c['reason']])
ins={i for u in units for i in u['inputs']}; ex={i for i in ins if not i.startswith('NEW:')}; new=ins-ex
print('REP-7  ledger inputs: existing',len(ex),'NEW',len(new),'| read by reference: existing',iu['summary']['reference_all_units']['existing_inputs_read'],'added',iu['summary']['reference_all_units']['added_inputs_read'],
      '| ledger-existing never read:',sorted(i for i in ex if not F[i]['reference_all_units']),'| ledger NEW names found in input_usage:',len(new&set(F)))
d={i['input_id']:i['disposition'] for i in unl['inputs']}
print('       dispositions not read by reference:',{k:[i for i,v in d.items() if v==k and not F[i]['reference_all_units']] for k in('NEEDS_NEW_UNIT','IMPLICIT_IN_EXISTING')})
print('REP-8  header',{k:U['structure_class_counts'][k] for k in('LINEAR_SUM_PRODUCT','RATIO')},'actual',{k:sum(u['structure_class']==k for u in units) for k in('LINEAR_SUM_PRODUCT','RATIO')})
chk=[u['id'] for u in units if u['structure_class']=='PREDICATE_GATE' or u['id']=='C-05']
mem={u:m['id'] for m in models['models'] for u in m['units']}
print('REP-9  check units',{u:mem.get(u,'not unified') for u in chk})
print('REP-13 units differ:',[c['candidate_id'] for c in cands if sorted(c['units'])!=sorted(ap[c['candidate_id']]['units'])])
m1={r['unit_id']:r['outcome'] for r in RR if r['step']=='M1'}
print('REP-14',sum(1 for r in RR if r['step']=='M6' and 'M1 に記録した' in r['reason'] and m1[r['unit_id']]=='NOT_APPLICABLE'),'M6 reasons cite M1 where M1 is NOT_APPLICABLE')
print('REP-16 sweep units',len(L('04_VERIFICATION/unified_model_exactness.json')['period_sweep']['units']))
print('REP-18',[(f['family'],f['status'],f['related_units']) for f in cov['families'] if (f['status']=='COVERED_BY_EXISTING' and any(r.startswith('X-') for r in f['related_units']))],
      'NON_CALCULATION with related units:',sum(1 for f in cov['families'] if f['status']=='NON_CALCULATION' and f['related_units']))
