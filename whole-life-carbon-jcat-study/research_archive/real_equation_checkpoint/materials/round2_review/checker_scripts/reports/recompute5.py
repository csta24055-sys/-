import json, collections, re
R='/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/'
L=lambda p: json.load(open(R+p))
C=collections.Counter
RR=L('03_MODELS/records/units.json')['records']
cands={c['candidate_id']:c for c in L('03_MODELS/candidates.json')['candidates']}
print('--- SUCCESS without mechanism')
for r in RR:
    if r['outcome']=='SUCCESS' and not r.get('mechanism'):
        print(r['unit_id'],r['step'],r['verification'],r['derivation'],'|',r['title'][:90],'|',r['reason'][:120])
print('--- SUCCESS without derivation')
for r in RR:
    if r['outcome']=='SUCCESS' and not r.get('derivation'):
        print(r['unit_id'],r['step'],r['verification'],r.get('mechanism'),'|',r['title'][:90])
print('--- AP-15 reasons')
print('cand:',cands['AP-15']['reason'])
print(C(r['reason'] for r in RR if r['candidate_id']=='AP-15').most_common(3))
print('--- M6 NA reason mentions M1 while M1 NA')
m1={r['unit_id']:r['outcome'] for r in RR if r['step']=='M1'}
x=[r['unit_id'] for r in RR if r['step']=='M6' and r['outcome']=='NOT_APPLICABLE' and 'M1 に記録した' in r['reason'] and m1[r['unit_id']]=='NOT_APPLICABLE']
print(len(x),x)
print('--- NA reason frequency')
for s in ['M1','M2','M3','M4','M5','M6']:
    cc=C(re.sub(r'\d+ 項目','N 項目',r['reason']) for r in RR if r['step']==s and r['outcome']=='NOT_APPLICABLE')
    print(s,len(cc),'distinct;', [(v,k[:110]) for k,v in cc.most_common(4)])
print('--- REJECTED records with SYNTHETIC_ONLY/ANALYTIC by candidate')
print(C((r['candidate_id'],r['verification']) for r in RR if r['outcome']=='REJECTED'))
print('--- rejected per-unit records: which units')
for cid in sorted({r['candidate_id'] for r in RR if r['candidate_id'].startswith('AP')}):
    us=[r['unit_id'] for r in RR if r['candidate_id']==cid]
    print(cid,cands[cid]['step'],cands[cid]['outcome'],cands[cid]['measured_on'],len(us),us)
