import copy, synth
from synth import population
from refcalc import registry
registry.load_all()
e = synth.make_scenario(22, "RC", "office", "S", 60.0, n_materials=8, n_equipment=4, n_refrigerants=2)
e2 = copy.deepcopy(e); b = population.attach_baseline(e2)
r_ok = registry.run_all(e2)["SUM-08"]
r0 = registry.run_all(b)
order = sorted(range(len(b.materials)), key=lambda i: -(r0["A13-01"]["by_item"][i] + r0["A13-03"]["by_item"][i]))
for i in order[:4]: b.materials[i].quantity = None
r_bad = registry.run_all(e2)
print("complete baseline:", r_ok)
print("baseline with 4 largest rows uncomputable:", r_bad["SUM-08"], "| proposal complete", r_bad["X-02"]["complete"], "| baseline complete", registry.run_all(b)["X-02"]["complete"])
# proposal incomplete
e3 = copy.deepcopy(e); b3 = population.attach_baseline(e3)
for i in order[:4]: e3.materials[i].quantity = None
r3 = registry.run_all(e3)
print("proposal with 4 largest rows uncomputable:", r3["SUM-08"], "proposal complete", r3["X-02"]["complete"])
