import copy, time, collections
from refcalc import registry
from synth import population
registry.load_all()
t = collections.defaultdict(float); n = collections.Counter()
t0 = time.time()
sizes = collections.Counter()
for i, scn in enumerate(population.verification_population(40, seed=20261111, max_size="M")):
    sz = scn.meta.size_class; sizes[sz] += 1
    a = time.time(); res = registry.run_all(scn); t["full:" + sz] += time.time() - a
    a = time.time(); s2 = copy.deepcopy(scn); t["deepcopy:" + sz] += time.time() - a
    a = time.time(); registry.run_all(s2, ids=["X-02", "SUM-03"]); t["x02:" + sz] += time.time() - a
    s2.boundary.baseline_scenario = None
    a = time.time(); registry.run_all(s2, ids=["SUM-03"]); t["sum03:" + sz] += time.time() - a
print("total %.1fs (incl. generation)" % (time.time() - t0), dict(sizes))
for k in sorted(t):
    print("%-14s %.3f s per scenario" % (k, t[k] / sizes[k.split(":")[1]]))
