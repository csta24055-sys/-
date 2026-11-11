import json,re
R='/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/'
P=json.load(open(R+'05_DECISIONS/progress_ledger.json'))['units']
t=open(R+'05_DECISIONS/PROGRESS.md').read()
JA={"SUCCESS":"成功","REJECTED":"不採用","HOLD":"保留","NOT_APPLICABLE":"候補なし","NOT_DONE":"未実施"}
rows=re.findall(r'^\| (\d+) \| (\d) \| ([A-Z0-9\-]+) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \|$',t,flags=re.M)
pm={u['id']:u for u in P}; mm=0
for r in rows:
    u=pm[r[2]]
    exp=(str(u['order']),str(u['wave']),u['id'],u['name'],u['status_label'])+tuple(JA[u['steps'][s]['conclusion']] for s in ['M1','M2','M3','M4','M5','M6'])+(('、'.join(u['unified_models']) or '—'),(', '.join(u['steps_on_hold']) or '—'))
    if exp!=r: mm+=1; print('mismatch',r[2],exp,r)
print('rows',len(rows),'cells',len(rows)*13,'mismatch',mm)
