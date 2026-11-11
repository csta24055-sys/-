import copy, inspect, synth
from refcalc import registry
import fastcalc
from fastcalc import engine
registry.load_all()
def small(seed=11, T=60.0, **o):
    opts = dict(n_materials=12, n_equipment=6, n_refrigerants=4); opts.update(o)
    return synth.make_scenario(seed, "RC", "office", "S", T, **opts)
print("engine.evaluate signature:", inspect.signature(engine.evaluate))
for sub in (["B3"], ["B5"]):
    s = small(included_stages=sub, replacement_cycle=25.0, reconstruction_scenario="REBUILD_IDENTICAL")
    r0 = registry.run_all(s)
    order = sorted(range(len(s.materials)), key=lambda i: -(r0["A13-01"]["by_item"][i] + r0["A13-03"]["by_item"][i]))
    for i in order[:3]: s.materials[i].quantity = None
    s.equipment[0].factor_id = "F-NOT-IN-TABLE"
    r1 = registry.run_all(s)
    f = engine.evaluate(s, detail=True)
    print(sub, "ref SUM-03", r1["SUM-03"], "fast SUM-03", f["SUM-03"], "fast X-02 complete", f["X-02"]["complete"], f["X-02"]["incomplete_units"], "SYS-01 ok", r1["SYS-01"]["ok"], r1["SYS-01"]["violations"], "SYS-03 ok", r1["SYS-03"]["ok"])
print("\n-- negative electricity demand is clamped to 0 without a flag --")
s = small(profile_kind="CONSTANT")
r0 = registry.run_all(s)
s2 = copy.deepcopy(s); p = s2.operation.electricity; p.base = -abs(p.base); p.table = [p.base] * len(p.table)
r1 = registry.run_all(s2)
print("B6-01 total clean", sum(r0["B6-01"]["by_year"]), "negative demand", sum(r1["B6-01"]["by_year"]), "B6-04 computed", r1["B6-04"]["computed"], "match", r1["B6-04"]["descriptors_match_tables"], "complete", r1["X-02"]["complete"], "SYS-01", r1["SYS-01"]["ok"])
print("\n-- B2-01 'computed' when B6-01 is not computed --")
s2 = copy.deepcopy(s); s2.operation.grid.licence_status = "UNKNOWN"; s2.boundary.included_lifecycle_stages = ["B2"]
r1 = registry.run_all(s2)
print("B6-01 computed", r1["B6-01"]["computed"], "B2-01", r1["B2-01"], "X-02", r1["X-02"]["by_stage"], r1["X-02"]["complete"], r1["X-02"]["incomplete_units"])
