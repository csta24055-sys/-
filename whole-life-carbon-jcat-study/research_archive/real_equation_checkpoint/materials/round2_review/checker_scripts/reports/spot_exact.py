import sys, json, copy
sys.dont_write_bytecode=True
from refcalc import registry
from fastcalc import engine
from synth import population
from common.compare import compare
registry.load_all()
R='/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/'
ex=json.load(open(R+'04_VERIFICATION/unified_model_exactness.json'))
def run(scns):
    worst=0.0; n=0; nn=0; fails=0; nscn=0
    for scn in scns:
        nscn+=1
        ref=registry.run_all(scn); full=engine.evaluate(scn,detail=True); summ=engine.evaluate(scn,detail=False)
        scale=abs(ref['SUM-03']['value']) or 1.0
        for uid,rv in ref.items():
            c=compare(rv,full.get(uid,{}),floor=1e-9*scale); cs=compare(rv,summ.get(uid,{}),floor=1e-9*scale,ignore_missing=True)
            n+=c.n_numeric; nn+=c.n_other; worst=max(worst,c.max_abs_rel_error)
            if not (c.within(1e-9) and not c.extra and cs.within(1e-9)): fails+=1
    return nscn,n,nn,worst,fails
e=run([s for _,s in population.edge_cases()])
print('edge: scenarios %d numeric %d other %d worst %.16e fails %d'%e, '| stored',ex['by_group']['edge'])
b=run(population.standard_benchmark()[:2])
print('benchmark S,M: scenarios %d numeric %d other %d worst %.16e fails %d'%b, '| stored (S,M,L)',ex['by_group']['benchmark'])
import itertools
p=run(itertools.islice(population.verification_population(400,seed=20261111,max_size='M'),60))
print('population first 60: scenarios %d numeric %d other %d worst %.3e fails %d'%p)
