import synth, json
from refcalc import registry
registry.load_all()
scn = synth.make_scenario(7,"RC","office","S",60.0, n_materials=4,n_equipment=3,n_refrigerants=2, dirty=True)
res = registry.run_all(scn)
def shape(v, depth=0):
    if isinstance(v, dict):
        return {k:(shape(x,depth+1)) for k,x in v.items()}
    if isinstance(v,(list,tuple)):
        if len(v)==0: return []
        return [shape(v[0],depth+1), f"...x{len(v)}"]
    if isinstance(v,float): return round(v,4)
    return v
for uid in sorted(res):
    print(uid, json.dumps(shape(res[uid]),ensure_ascii=False,default=str)[:900])
print([ (d.kind,d.path) for d in scn.meta.injected_defects])
