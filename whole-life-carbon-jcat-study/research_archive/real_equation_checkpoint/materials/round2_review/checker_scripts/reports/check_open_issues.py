import json,sys,math
sys.dont_write_bytecode=True
from refcalc import registry
from synth import population
import synth
registry.load_all()
b=population.standard_benchmark()[0]
r=registry.run_all(b)
def short(d,n=400): 
    s=json.dumps(d,ensure_ascii=False,default=str); return s[:n]
for k in ('X-02','SUM-02','B2-01','A5-04','X-01','SUM-03'):
    print(k, {kk:(vv if not isinstance(vv,(list,dict)) or len(str(vv))<300 else type(vv).__name__) for kk,vv in r[k].items()})
