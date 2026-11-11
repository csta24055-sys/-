import json,sys,math
sys.dont_write_bytecode=True
from refcalc import registry
from refcalc.base import lookup, nonneg, periodic_events
from synth import population
registry.load_all()
b=population.standard_benchmark()[0]
r=registry.run_all(b)
st=r['X-02']['by_stage']
a4=a5=0.0
for eq in b.equipment:
    for fid,stage in ((eq.delivery_factor_id,'A4'),(eq.installation_factor_id,'A5')):
        if fid is None: continue
        hit=lookup(b,fid,stage,eq.quantity_unit)
        if hit is None or not nonneg(eq.quantity): continue
        v=eq.quantity*hit[1]*b.factors[fid].value
        if stage=='A4': a4+=v
        else: a5+=v
print('B-11: uncounted initial equipment delivery / A4 = %.3f%%, installation / A5 = %.2f%%'%(100*a4/st['A4'],100*a5/st['A5']))
print('B-10: B2/SUM-02 = %.2f%%'%(100*r['B2-01']['value']/r['SUM-02']['value']))
# B-7
ec=dict(population.edge_cases())
s=ec['rebuild_within_period']; T=s.boundary.study_period; C=s.boundary.replacement_cycle
print('T',T,'cycle',C,'scope',getattr(s.boundary,'reconstruction_scope_fraction',None), s.boundary.reconstruction_scenario)
rr=registry.run_all(s)
n0=n1=0; e0=e1=0.0
segs=[]; t=0.0
while t<T: segs.append(min(C,T-t)); t+=C
bm=rr['B4-02']
print({k:(v if not isinstance(v,(list,dict)) else type(v).__name__+str(len(v))) for k,v in bm.items()})
for i,row in enumerate(s.materials):
    ev=periodic_events(T,row.refresh_cycle) if rr['B4-03']['by_item'][i] else []
    alt=sum(len(periodic_events(L,row.refresh_cycle)) for L in segs) if rr['B4-03']['by_item'][i] else 0
    n0+=len(ev); n1+=alt
    by=bm.get('by_material') or bm.get('by_item_material') 
    if by and len(ev): u=by[i]/len(ev); e0+=by[i]; e1+=u*alt
print('materials: events',n0,'with reset',n1,'B4 mat',e0,'reset',e1)
keys=[k for k in bm if isinstance(bm[k],list)]; print(keys)
m0=n0;m1=n1
for j,eq in enumerate(s.equipment):
    ev=rr['B4-01']['events'][j]
    c=eq.service_life
    explicit=getattr(eq,'replacement_years',None)
    if explicit: alt=len(ev)
    else: alt=sum(len(periodic_events(L,c)) for L in segs)
    n0+=len(ev); n1+=alt
    by=bm.get('by_item_equipment')
    if by and len(ev): u=by[j]/len(ev); e0+=by[j]; e1+=u*alt
print('all: events',n0,'with reset',n1,'B4',bm['value'],'sum',e0,'reset',e1,'change %.1f%%'%(100*(e1/e0-1)),'WLC change %.2f%%'%(100*(e1-e0)/rr['SUM-03']['value']))
