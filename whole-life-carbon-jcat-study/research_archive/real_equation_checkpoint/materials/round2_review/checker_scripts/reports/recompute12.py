import json, collections, re
R='/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/'
L=lambda p: json.load(open(R+p))
C=collections.Counter
tr=L('03_MODELS/judge_proposal_trace.json'); b=L('02_RANKING/axis_b.json'); RR=L('03_MODELS/records/units.json')['records']
print(C((x['criterion'],x['step']) for x in tr['score_2_or_more']))
med={r['id']:r['median_by_criterion'] for r in b['ranking']}
for c in ['b5','b6','b7','b8']: print(c, sum(1 for u in med if med[u][c]>=2))
# verify measured flag
by=collections.defaultdict(list)
for r in RR: by[(r['unit_id'],r['step'])].append(r)
bad=0
for x in tr['score_2_or_more']:
    rs=by[(x['unit_id'],x['step'])]
    meas=any(r['outcome']!='NOT_APPLICABLE' for r in rs)
    if meas!=x['measured'] or sorted(r['candidate_id'] for r in rs)!=sorted(r['candidate_id'] for r in x['records']): bad+=1; print('trace mismatch',x['unit_id'],x['step'])
    if med[x['unit_id']][x['criterion']]!=x['median_score']: bad+=1; print('score mismatch',x)
print('trace bad',bad,'not measured',sum(1 for x in tr['score_2_or_more'] if not x['measured']), len(tr['not_measured']))
exp={(u,c) for u in med for c in ('b5','b6','b8') if med[u][c]>=2}
got={(x['unit_id'],x['criterion']) for x in tr['score_2_or_more']}
print('expected set size (b5,b6,b8>=2)',len(exp),'got',len(got),'diff',exp^got)
# b7 (inputs can be reduced) >=2: how handled?
b7=[u for u in med if med[u]['b7']>=2]; print('b7>=2 units',len(b7),b7)
# For 'measured' true entries: is the measured candidate really about that unit/criterion? list those whose only non-NA record is AP-15
only15=[(x['unit_id'],x['step']) for x in tr['score_2_or_more'] if x['measured'] and {r['candidate_id'] for r in x['records'] if r['outcome']!='NOT_APPLICABLE'}=={'AP-15'}]
print('measured only via AP-15:',len(only15),only15)
# units whose only M4 candidate is AP-15
PU=L('05_DECISIONS/progress_ledger.json')['units']
o=[u['id'] for u in PU if [c['candidate_id'] for c in u['steps']['M4']['candidates']]==['AP-15']]
print('units whose only M4 record is AP-15:',len(o),o)
o2=[u['id'] for u in PU if u['steps']['M4']['conclusion']=='HOLD']
print('M4 hold units',len(o2))
h=[u['id'] for u in PU if u['steps_on_hold']]
onlyAP15=[u['id'] for u in PU if u['steps_on_hold'] and all([c['candidate_id'] for c in u['steps'][s]['candidates'] if c['outcome']=='HOLD']==['AP-15'] for s in u['steps_on_hold'])]
print('units with holds',len(h),'whose holds are only AP-15',len(onlyAP15))
