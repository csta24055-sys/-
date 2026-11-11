import sys, json, statistics
sys.dont_write_bytecode=True
from refcalc import registry
from synth import population
from common.compare import percentile
registry.load_all()
R='/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/'
ap=json.load(open(R+'04_VERIFICATION/approximation_study.json'))['candidates']
e4=[]; t4=[]; e22=[]; struct={}
n=0
for scn in population.verification_population(400,seed=20261111,max_size='M'):
    n+=1
    r=registry.run_all(scn)
    b31=r['B3-01']['value']; b32=r['B3-02']['value']; wlc=r['SUM-03']['value']
    if b31:
        e=(b32-b31)/b31; e4.append(e); t4.append((b32-b31)/wlc); struct.setdefault(scn.project.structure_type,[]).append(e)
    co2=r['X-05']['value']
    if wlc: e22.append((co2-wlc)/wlc)
def st(x): return dict(n=len(x),mean=statistics.fmean(x),p95=percentile([abs(v) for v in x],95),mx=max(x),mn=min(x))
print('scenarios',n)
print('AP-04 mine ',st(e4)); s=ap['AP-04']['stage_error']; print('AP-04 store',{k:s[k] for k in('n','mean_signed','p95_abs','max_over','max_under')})
print('AP-04 total p95 mine',percentile([abs(v) for v in t4],95),'stored',ap['AP-04']['total_error']['p95_abs'])
for k,v in sorted(struct.items()): print('  structure',k,len(v),'%.4f'%statistics.fmean(v),'stored',ap['AP-04']['by_group']['structure='+k]['n'],'%.4f'%ap['AP-04']['by_group']['structure='+k]['mean_signed'])
print('AP-22a mine',st(e22)); s=ap['AP-22a']['stage_error']; print('AP-22a store',{k:s[k] for k in('n','mean_signed','p95_abs','max_over','max_under')})
