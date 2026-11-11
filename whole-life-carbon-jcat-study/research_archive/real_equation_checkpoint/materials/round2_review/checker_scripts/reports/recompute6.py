import json, collections, re
R='/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/'
L=lambda p: json.load(open(R+p))
cands=L('03_MODELS/candidates.json')['candidates']; ap=L('04_VERIFICATION/approximation_study.json'); AC=ap['candidates']
n=0; bad=0
def cmp(a,b,path):
    global n,bad
    if isinstance(a,dict) and isinstance(b,dict):
        for k in set(a)|set(b):
            if k not in a or k not in b: bad+=1; print('key missing',path,k, k in a, k in b); continue
            cmp(a[k],b[k],path+'/'+k)
    else:
        n+=1
        if a!=b: bad+=1; print('DIFF',path,a,b)
order=[c['candidate_id'] for c in cands]
print('order same as approx study', order==list(AC))
for c in cands:
    a=AC[c['candidate_id']]
    for k in ('stage_error','total_error','by_material_class','other_targets','under_estimates','within_stage_target','within_total_target','step','title'):
        if k in c or k in a:
            if k not in c or k not in a: print('missing',c['candidate_id'],k,k in c,k in a); continue
            cmp(c[k],a[k],c['candidate_id']+'/'+k)
    if c['measured_on']!=a.get('stage'): print('measured_on vs stage',c['candidate_id'],c['measured_on'],a.get('stage'))
    if sorted(c['units'])!=sorted(a['units']): print('units differ',c['candidate_id'],sorted(c['units']),sorted(a['units']))
print('compared',n,'bad',bad)
print({k:list(v.keys()) for k,v in AC.items() if k in('AP-20','AP-06b','AP-21','AP-22b','AP-09c','AP-14','AP-15')})
print(json.dumps(AC['AP-20'],ensure_ascii=False)[:1500])
