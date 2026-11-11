import json, collections, re
R='/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/'
L=lambda p: json.load(open(R+p))
cands=L('03_MODELS/candidates.json')['candidates']; ap=L('04_VERIFICATION/approximation_study.json'); AC=ap['candidates']
t3=open(R+'03_MODELS/README.md').read(); t4=open(R+'04_VERIFICATION/README.md').read(); t5=open(R+'05_DECISIONS/README.md').read()
JA={'REJECTED':'不採用','HOLD':'保留'}
def pc(x,d=1,sign=True):
    s=('%+.'+str(d)+'f')%(100*x) if sign else ('%.'+str(d)+'f')%(100*x)
    return s+'％'
nchk=0; mm=0
# 03 table
for c in cands:
    cid=c['candidate_id']
    m=re.search(r'^\| '+re.escape(cid)+r' \| (M\d) \| (.+?) \| (.+?) \| (不採用|保留) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \| (.+) \|$',t3,flags=re.M)
    if not m: print('03 row not found',cid); mm+=1; continue
    step,title,meas,out,mean,p95,mo,mu,tp95,reason=m.groups()
    se=c.get('stage_error') or AC[cid].get('row_error'); te=c.get('total_error')
    exp=[c['step'],c['title'],c['measured_on'],JA[c['outcome']]]
    got=[step,title,meas,out]
    if se:
        exp+=[pc(se['mean_signed']),pc(se['p95_abs'],sign=False),pc(se['max_over']),pc(se['max_under'])]
        got+=[mean,p95,mo,mu]
    if te and 'p95_abs' in te: exp.append(pc(te['p95_abs'],sign=False)); got.append(tp95)
    elif te: print('total_error w/o p95',cid,te)
    exp.append(c['reason']); got.append(reason)
    nchk+=len(exp)
    for e,g in zip(exp,got):
        if e!=g: mm+=1; print('03 mismatch',cid,repr(e)[:80],repr(g)[:80])
print('03 table cells checked',nchk,'mismatch',mm)
# 04 table
nchk=0; mm=0
for c in cands:
    cid=c['candidate_id']
    m=re.search(r'^\| '+re.escape(cid)+r' \| (.+?) \| (.+?) \| (\d+) 件、平均 ([+\-][\d\.]+)％、95％点 ([\d\.]+)％、範囲 ([+\-][\d\.]+)％〜([+\-][\d\.]+)％ \| (.+?) \| (.+?) \|$',t4,flags=re.M)
    if not m:
        print('04 row not found',cid); continue
    title,meas,n,mean,p95,lo,hi,tp,under=m.groups()
    se=c.get('stage_error') or AC[cid].get('row_error'); te=c.get('total_error')
    exp=[c['title'],c['measured_on'],str(se['n']),'%+.2f'%(100*se['mean_signed']),'%.2f'%(100*se['p95_abs']),'%+.1f'%(100*se['max_under']),'%+.1f'%(100*se['max_over'])]
    got=[title,meas,n,mean,p95,lo,hi]
    if te and 'p95_abs' in te: exp.append('%.2f％'%(100*te['p95_abs'])); got.append(tp)
    if 'under_estimates' in c: exp.append('あり' if c['under_estimates'] else 'なし'); got.append(under)
    nchk+=len(exp)
    for e,g in zip(exp,got):
        if e!=g: mm+=1; print('04 mismatch',cid,repr(e)[:80],repr(g)[:80])
print('04 table cells checked',nchk,'mismatch',mm)
# under_estimates semantics
for c in cands:
    se=c.get('stage_error')
    if se: 
        print(c['candidate_id'],c['outcome'],'under_flag',c['under_estimates'],'max_under %.4f'%se['max_under'],'share_under %.3f'%se['share_under_estimated'],'within_stage',c['within_stage_target'],'p95 %.4f'%se['p95_abs'],'within_total',c['within_total_target'],'tot p95 %.4f'%c['total_error']['p95_abs'] if (c.get('total_error') or {}).get('p95_abs') is not None else '')
