import json, collections, re, math, sys
R='/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/'
L=lambda p: json.load(open(R+p))
C=collections.Counter
recs=L('03_MODELS/records/units.json'); RR=recs['records']
models=L('03_MODELS/models.json'); cands=L('03_MODELS/candidates.json')['candidates']
prog=L('05_DECISIONS/progress_ledger.json'); PU=prog['units']
units=L('01_LEDGER/units.json')['units']; uid=[u['id'] for u in units]
print('records',len(RR),recs['record_count'], C(r['outcome'] for r in RR))
tab=collections.defaultdict(C)
for r in RR: tab[r['step']][r['outcome']]+=1
for s in sorted(tab): print(' ',s,dict(tab[s]))
print('verification', C((r['outcome'],r['verification']) for r in RR))
# each unit has each step
by=collections.defaultdict(lambda: collections.defaultdict(list))
for r in RR: by[r['unit_id']][r['step']].append(r)
miss=[(u,s) for u in uid for s in ['M1','M2','M3','M4','M5','M6'] if not by[u][s]]
print('missing unit-steps',miss, 'units in records',len(by), set(by)-set(uid))
# models membership
MM={m['id']:m for m in models['models']}
mem={}
for m in models['models']:
    assert m['unit_count']==len(m['units']), m['id']
    for u in m['units']:
        if u in mem: print('unit in two models',u)
        mem[u]=m['id']
print('models',{k:len(v['units']) for k,v in MM.items()}, 'sum',len(mem),'not_unified',models['not_unified'], set(uid)-set(mem)-set(models['not_unified']))
# records unified_model vs models.json
rm={}
for r in RR:
    if r['unified_model']:
        if r['step']!='M2': print('unified_model on non-M2',r['unit_id'],r['step'],r['candidate_id'])
        if r['outcome']!='SUCCESS': print('unified_model but not success',r['candidate_id'])
        rm.setdefault(r['unit_id'],set()).add(r['unified_model'])
bad=[(u,rm.get(u),mem.get(u)) for u in uid if (rm.get(u) or set())!=({mem[u]} if u in mem else set())]
print('records vs models mismatch',bad)
# M2 success without unified_model
print('M2 success w/o model',[r['candidate_id'] for r in RR if r['step']=='M2' and r['outcome']=='SUCCESS' and not r['unified_model']])
# progress ledger vs records
pm={u['id']:u for u in PU}
bad=[]
PRI={'SUCCESS':3,'HOLD':2,'REJECTED':1,'NOT_APPLICABLE':0}
stepc=collections.defaultdict(C)
ncand=0
for u in uid:
    p=pm[u]
    if (p['unified_models'] or [])!=([mem[u]] if u in mem else []): bad.append(('model',u,p['unified_models'],mem.get(u)))
    for s in ['M1','M2','M3','M4','M5','M6']:
        rc=by[u][s]; pc=p['steps'][s]['candidates']; ncand+=len(pc)
        if sorted(c['candidate_id'] for c in pc)!=sorted(r['candidate_id'] for r in rc): bad.append(('cands',u,s))
        for c in pc:
            r=[x for x in rc if x['candidate_id']==c['candidate_id']][0]
            for k in ('outcome','verification','reason','title','data_needed'):
                if c[k]!=r[k]: bad.append(('field',u,s,c['candidate_id'],k))
        exp=max((r['outcome'] for r in rc), key=lambda o:PRI[o])
        if p['steps'][s]['conclusion']!=exp: bad.append(('concl',u,s,p['steps'][s]['conclusion'],exp))
        stepc[s][p['steps'][s]['conclusion']]+=1
print('progress vs records issues',bad[:10],len(bad),'ncand in progress',ncand)
for s in sorted(stepc): print(' units by step',s,dict(stepc[s]))
print('status',C(u['status'] for u in PU))
# recompute status by P10 rule
def status(p):
    con={s:p['steps'][s]['conclusion'] for s in p['steps']}
    if any(c=='NOT_DONE' for c in con.values()): return 'IN_PROGRESS'
    hasver=any(c['verification']!='NOT_VERIFIED' for s in p['steps'].values() for c in s['candidates'])
    if not hasver: return 'NOT_VERIFIED'
    if p.get('unit_hold'): return 'HOLD_DATA_OR_RIGHTS'
    if con['M2']=='SUCCESS' or con['M4']=='SUCCESS': return 'DONE_UNIFIED'
    if any(con[s]=='SUCCESS' for s in ('M1','M3','M5','M6')): return 'DONE_SIMPLIFIED'
    if any(c=='HOLD' for c in con.values()): return 'HOLD_DATA_OR_RIGHTS'
    return 'DONE_APPROX_REJECTED'
print('status mismatches',[(u['id'],u['status'],status(u)) for u in PU if u['status']!=status(u)])
print('unit_hold',[(u['id'],u['unit_hold_reason']) for u in PU if u['unit_hold']])
hold=[u['id'] for u in PU if u['status'].startswith('DONE') and u['steps_on_hold']]
print('done with steps on hold',len(hold))
for u in PU:
    exp=[s for s in ['M1','M2','M3','M4','M5','M6'] if u['steps'][s]['conclusion']=='HOLD']
    if exp!=u['steps_on_hold']: print('steps_on_hold mismatch',u['id'])
print('has_verified_record false',[u['id'] for u in PU if not u['has_verified_record']])
# STO-01 detail
p=pm['STO-01']; print('STO-01',p['status'],p['unit_hold'],p['unit_hold_reason'],{s:p['steps'][s]['conclusion'] for s in p['steps']}, p['status_note'])
for s in p['steps']:
    for c in p['steps'][s]['candidates']: print('   ',s,c['candidate_id'],c['outcome'],c['verification'],c['reason'][:150])
# candidates vs records
cm={c['candidate_id']:c for c in cands}
print('candidates',len(cm),C(c['outcome'] for c in cands), C(c['step'] for c in cands), C((c['step'],c['outcome']) for c in cands))
recAP=collections.defaultdict(list)
for r in RR:
    if r['candidate_id'].startswith('AP-'): recAP[r['candidate_id']].append(r)
print('AP in records',len(recAP), 'missing from records',set(cm)-set(recAP), 'extra',set(recAP)-set(cm))
for cid,c in cm.items():
    us=sorted(r['unit_id'] for r in recAP[cid])
    if us!=sorted(c['units']): print('units mismatch',cid,us,sorted(c['units']))
    for r in recAP[cid]:
        for k in ('step','outcome','verification','reason','title','data_needed'):
            if r[k]!=c[k]: print('field mismatch',cid,r['unit_id'],k)
# units with no AP candidate at all
print('units with any AP record', len({r['unit_id'] for r in RR if r['candidate_id'].startswith('AP-')}))
# record id prefixes
print(C(re.match(r'[A-Z]+',r['candidate_id']).group() for r in RR))
print('SUCCESS w/o derivation',C((r['verification'],bool(r['derivation'])) for r in RR if r['outcome']=='SUCCESS'))
print('mech',C(r.get('mechanism') for r in RR if r['outcome']=='SUCCESS'))
print('NA with evidence/verification',C((r['verification'],len(r['evidence'])>0) for r in RR if r['outcome']=='NOT_APPLICABLE'))
print('HOLD', C((r['verification'],bool(r['data_needed'])) for r in RR if r['outcome']=='HOLD'))
print('REJ', C((r['verification']) for r in RR if r['outcome']=='REJECTED'))
print('empty reasons',[r['candidate_id'] for r in RR if not r['reason']])
