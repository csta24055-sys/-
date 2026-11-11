import json, collections, re, math, sys
sys.dont_write_bytecode=True
R='/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/'
L=lambda p: json.load(open(R+p))
from pathlib import Path
import tools.rank_axes as ra
units=L('01_LEDGER/units.json')['units']
fam={f["family_id"]: f["share_of_all_nodes"] for f in L('01_LEDGER/sheet_families.json')["families"]}
meas=L('02_RANKING/axis_a_measurements.json')
a=ra.rank_axis_a(units,fam,meas)
jf=sorted((Path(R)/'02_RANKING/axis_b_judges').glob('*.json'))
b=ra.rank_axis_b(units,jf)
sa=L('02_RANKING/axis_a.json'); sb=L('02_RANKING/axis_b.json'); pri=L('02_RANKING/research_priority.json')
# compare
dA=[(u,a['scores'][u],sa['scores'][u]) for u in a['scores'] if abs(a['scores'][u]-sa['scores'][u])>1e-12]
print('A score diffs vs stored:',len(dA)); 
for x in dA[:80]: print('  ',x)
ar={r['id']:r['rank'] for r in a['ranking']}; sar={r['id']:r['rank'] for r in sa['ranking']}
print('A rank diffs:',[(u,ar[u],sar[u]) for u in ar if ar[u]!=sar[u]])
print('A top30 main recomputed',len(a['reference_top30']['main']),'stored',len(sa['reference_top30']['main']), 'sens',len(a['reference_top30']['sensitivity_only']),len(sa['reference_top30']['sensitivity_only']))
print(' set diff main', set(a['reference_top30']['main'])^set(sa['reference_top30']['main']), 'sens diff', set(a['reference_top30']['sensitivity_only'])^set(sa['reference_top30']['sensitivity_only']))
dB=[(u,b['scores'][u],sb['scores'][u]) for u in b['scores'] if b['scores'][u]!=sb['scores'][u]]
print('B diffs',dB, 'B rank diffs',[(r['id']) for r,s in zip(b['ranking'],sb['ranking']) if r['id']!=s['id']])
print('B top30',len(b['reference_top30']['members']),len(sb['reference_top30']['members']), 'disputed',b['disputed_units'],sb['disputed_units'])
# static diffs: which static metric changed
for r in a['ranking']:
    s=[x for x in sa['ranking'] if x['id']==r['id']][0]
    if r['static']!=s['static']: print('static diff',r['id'],r['static'],s['static'])
# priority recompute
pa=ra.pct_rank(sa['scores']); pb=ra.pct_rank(sb['scores']); pu=ra.pct_rank(sb['unification_subscores'])
prio={u:0.35*pb[u]+0.30*pu[u]+0.35*pa[u] for u in pa}
order=sorted(prio,key=lambda u:(-prio[u],u))
st=[r['id'] for r in pri['units']]
print('order equal (from stored axes):',order==st)
print('prio diffs',[(r['id'],r['priority_score'],round(prio[r['id']],4)) for r in pri['units'] if abs(r['priority_score']-round(prio[r['id']],4))>1e-9])
print('waves',[len(v) for v in pri['waves'].values()], [ (r['order'],r['wave']) for r in pri['units'] if r['wave']!=min(3,(r['order']-1)//24+1)])
print('counts', pri['reference_top30_counts'])
A=set(sa['reference_top30']['main']); As=set(sa['reference_top30']['sensitivity_only']); B=set(sb['reference_top30']['members'])
print('A',len(A),'As',len(As),'B',len(B),'A|B',len(A|B),'A|As|B',len(A|As|B),'A&B',len(A&B))
# top30 tags in priority vs
for r in pri['units']:
    exp=[t for t,h in (('A',r['id'] in A),('A_SENSITIVITY',r['id'] in As),('B',r['id'] in B)) if h]
    if exp!=r['reference_top30']: print('tag diff',r['id'],exp,r['reference_top30'])
# progress ledger order/wave
prog=L('05_DECISIONS/progress_ledger.json')['units']
pm={r['id']:r for r in pri['units']}
print('progress order/wave mismatches',[(u['id'],u['order'],u['wave']) for u in prog if (u['order'],u['wave'])!=(pm[u['id']]['order'],pm[u['id']]['wave'])])
print('progress list order equals priority order', [u['id'] for u in prog]==st)
# a7 proxy check: uses sheet_family_links from units (current)
# README A table: check few rows
txt=open(R+'02_RANKING/README.md').read()
rowsA=re.findall(r'^\| (\d+) \| ([A-Z0-9\-]+) \| .+? \| (\d\.\d+) \| ([\d\.]+)％ \| ([\d\.]+) \| ([\d,]+) \| ([\d,]+) \| (\d+) \| (\d+) \| (\d+) \| ([\d\.]+)％ \|$',txt,flags=re.M)
print('README A rows',len(rowsA))
mm=0
sr={r['id']:r for r in sa['ranking']}
for rk,uid,sc,ts,tms,ops,mem,a4,a5,a6,a7 in rowsA:
    r=sr[uid]
    exp=(str(r['rank']),'%.3f'%r['a_score'],'%.2f'%(100*r['time_share']['L']),'%.2f'%(r['time_ns']['L']/1e6),'{:,}'.format(r['operations']['L']),'{:,}'.format(round(r['peak_memory_bytes']['L']/1024)),str(r['static']['a4']),str(r['static']['a5']),str(r['static']['a6']),'%.2f'%(100*r['static']['a7']))
    got=(rk,sc,ts,tms,ops,mem,a4,a5,a6,a7)
    if exp!=got: mm+=1; print('A row mismatch',uid,exp,got)
print('A README mismatches',mm,'(compared',len(rowsA)*10,'cells)')
rowsB=re.findall(r'^\| (\d+) \| ([A-Z0-9\-]+) \| .+? \| (\d+) \| (\d+) \| (\d) \| (\d) \| (\d) \| (\d) \| (\d) \| (\d) \| (\d) \| (\d) \| (\d+)/(\d+)/(\d+) \| (.*?) \|$',txt,flags=re.M)
print('README B rows',len(rowsB)); mm=0
sbr={r['id']:r for r in sb['ranking']}
for row in rowsB:
    uid=row[1]; r=sbr[uid]
    med=r['median_by_criterion']
    exp=(str(r['rank']),str(r['b_score']),str(r['unification_subscore']))+tuple(str(med['b%d'%i]) for i in range(1,9))
    got=(row[0],row[2],row[3])+row[4:12]
    tot=sorted(map(int,row[12:15])); et=sorted(r['judge_totals'].values())
    if exp!=got or tot!=et or (('あり' in row[15])!=r['disputed']): mm+=1; print('B mismatch',uid,exp,got,tot,et)
print('B README mismatches',mm)
print('judge order in README', [ (k) for k in sb['ranking'][0]['judge_totals']], sb['ranking'][0]['judge_totals'])
rowsP=re.findall(r'^\| (\d+) \| (\d) \| ([A-Z0-9\-]+) \| .+? \| (.+?) \| (\d\.\d+) \| (\d+) \| (\d+) \| (\d+) \| (.+?) \|$',txt,flags=re.M)
print('README P rows',len(rowsP)); mm=0
for o,w,uid,stg,ps,arn,brn,us,tag in rowsP:
    r=pm[uid]
    exp=(str(r['order']),str(r['wave']),r['stage'],'%.3f'%r['priority_score'],str(r['a_rank']),str(r['b_rank']),str(r['b_unification_subscore']),'・'.join(r['reference_top30']) or '—')
    if exp!=(o,w,stg,ps,arn,brn,us,tag): mm+=1; print('P mismatch',uid,exp,(o,w,stg,ps,arn,brn,us,tag))
print('P README mismatches',mm)
print('total time ns',meas['total_time_ns'], 'sum L', sum((u.get('time_ns') or {}).get('L',0) for u in meas['units'].values()))
print('sum time share L', sum((u.get('time_share') or {}).get('L',0) for u in meas['units'].values()))
print('measured count', sum(1 for u in meas['units'].values() if u.get('measured')))
print(list(meas['units']['B4-02'].keys()))
