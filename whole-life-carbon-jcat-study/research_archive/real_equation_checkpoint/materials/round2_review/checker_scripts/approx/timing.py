import time, sys
from refcalc import registry
from synth import population
registry.load_all()
t=time.time()
n=0
for scn in population.verification_population(20, seed=20261111, max_size="M"):
    res=registry.run_all(scn); n+=1
print(n, time.time()-t, len(scn.materials), len(scn.equipment), len(scn.refrigerants))
