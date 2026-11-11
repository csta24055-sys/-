import json, collections, re
R='/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/'
L=lambda p: json.load(open(R+p))
ap=L('04_VERIFICATION/approximation_study.json'); AC=ap['candidates']
t4=open(R+'04_VERIFICATION/README.md').read()
def f(e): return 'n=%d mean=%+.2f p95=%.2f range %+.1f..%+.1f under_share=%.3f'%(e['n'],100*e['mean_signed'],100*e['p95_abs'],100*e['max_under'],100*e['max_over'],e['share_under_estimated'])
for cid in ['AP-01','AP-02','AP-03','AP-08','AP-09a','AP-05','AP-17','AP-09c','AP-18b','AP-18']:
    c=AC[cid]
    print('==',cid,[k for k in c if k not in('title','replaces','by_group','by_material_class','stage_error','total_error')])
    for k,v in (c.get('other_targets') or {}).items():
        if isinstance(v,dict) and 'stage_error' in v: print('   ',k,'stage:',f(v['stage_error']),'zero-ref-nonzero',v.get('n_reference_zero_candidate_nonzero'))
        elif isinstance(v,dict) and 'n' in v: print('   ',k,f(v))
        else: print('   ',k,str(v)[:200])
    for k in ('by_condition','conditions','by_profile','by_grid_kind','note','data_dependence','n_scenarios_computed_exactly'):
        if k in c:
            v=c[k]
            if isinstance(v,dict):
                for kk,vv in v.items(): print('   ',k,kk, f(vv) if isinstance(vv,dict) and 'n' in vv else str(vv)[:200])
            else: print('   ',k,str(v)[:300])
print(AC['AP-06b']['row_error'], AC['AP-06b']['note'])
# AP-04 group table
mm=0;n=0
for g,e in AC['AP-04']['by_group'].items():
    m=re.search(r'^\| '+re.escape(g)+r' \| (\d+) \| ([+\-][\d\.]+)％ \| ([\d\.]+)％ \| ([+\-][\d\.]+)％ \|$',t4,flags=re.M)
    exp=(str(e['n']),'%+.2f'%(100*e['mean_signed']),'%.2f'%(100*e['p95_abs']),'%+.2f'%(100*e['max_over']))
    n+=4
    if not m or m.groups()!=exp: mm+=1; print('AP-04 group mismatch',g,exp,m and m.groups())
# material table
for cid in ['AP-01','AP-06','AP-07a','AP-18a']:
    for k,e in AC[cid]['by_material_class'].items():
        m=re.search(r'^\| '+cid+r' \| '+k+r' \| (\d+) \| ([+\-][\d\.]+)％ \| ([\d\.]+)％ \| ([+\-][\d\.]+)％ \| ([+\-][\d\.]+)％ \|$',t4,flags=re.M)
        exp=(str(e['n']),'%+.1f'%(100*e['mean_signed']),'%.1f'%(100*e['p95_abs']),'%+.1f'%(100*e['max_over']),'%+.1f'%(100*e['max_under']))
        n+=5
        if not m or m.groups()!=exp: mm+=1; print('material mismatch',cid,k,exp,m and m.groups())
for k,e in AC['AP-15']['by_stage'].items():
    m=re.search(r'^\| '+k+r' \| (\d+) \| ([+\-]\d+)％ \| (\d+)％ \| ([+\-]\d+)％ \| ([+\-]\d+)％ \|$',t4,flags=re.M)
    exp=(str(e['n']),'%+.0f'%(100*e['mean_signed']),'%.0f'%(100*e['p95_abs']),'%+.0f'%(100*e['max_over']),'%+.0f'%(100*e['max_under']))
    n+=5
    if not m or m.groups()!=exp: mm+=1; print('AP-15 stage mismatch',k,exp,m and m.groups())
print('group/material/stage cells',n,'mismatch',mm)
# which candidates have by_material_class non-empty, by_group
print('by_material non-empty:',[k for k,c in AC.items() if c.get('by_material_class')])
print('by_group non-empty:',[k for k,c in AC.items() if c.get('by_group')])
print('no by_group:',[k for k,c in AC.items() if not c.get('by_group')])
