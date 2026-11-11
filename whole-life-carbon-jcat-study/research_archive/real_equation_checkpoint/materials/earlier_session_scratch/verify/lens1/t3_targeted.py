"""Part 3: targeted minimal reproductions."""
import copy
import math
import sys

sys.path.insert(0, "/tmp/claude-0/-home-user--/49c0bd7e-a786-5ae4-9a1e-e89e7996ede3/scratchpad/verify/lens1")
import h
import synth
from fastcalc import engine
from refcalc import registry
from synth import model, population

SMALL = dict(n_materials=12, n_equipment=6, n_refrigerants=4)


def show(title, scn, units=None, limit=6):
    st, fs = h.diff(scn)
    print(f"\n--- {title}: {st}, {len(fs)} findings")
    for f in fs[:limit]:
        if units and f.get("unit") not in units:
            continue
        print("    ", {k: v for k, v in f.items() if k != "scale"})
    return fs


# 1. self baseline
scn = synth.make_scenario(11, "RC", "office", "S", 60.0, **SMALL)
population.BASELINES[scn.meta.scenario_id] = scn
scn.boundary.baseline_scenario = scn.meta.scenario_id
ref = registry.run_all(scn)
print("1. self-baseline: reference SUM-08 =", ref["SUM-08"])
for d in (True, False):
    engine.clear_baseline_cache()
    try:
        print("   engine detail=%s SUM-08 =" % d, engine.evaluate(scn, detail=d)["SUM-08"])
    except RecursionError as exc:
        print("   engine detail=%s raises RecursionError" % d)

# 2. mutual baselines
a = synth.make_scenario(12, "RC", "office", "S", 60.0, scenario_id="MUT-A", **SMALL)
b = copy.deepcopy(a)
b.meta.scenario_id = "MUT-B"
b.materials[0].quantity *= 1.1
population.BASELINES["MUT-A"], population.BASELINES["MUT-B"] = a, b
a.boundary.baseline_scenario, b.boundary.baseline_scenario = "MUT-B", "MUT-A"
ref = registry.run_all(a)
print("2. mutual baselines: reference SUM-08 =", ref["SUM-08"])
engine.clear_baseline_cache()
try:
    print("   engine SUM-08 =", engine.evaluate(a, detail=False)["SUM-08"])
except RecursionError:
    print("   engine raises RecursionError")

# 2b. chain P -> B -> C (C comparable to B)
p = synth.make_scenario(13, "RC", "office", "S", 60.0, scenario_id="CH-P", **SMALL)
bb = population.attach_baseline(p)
cc = population.attach_baseline(bb)
show("2b. chain of baselines", p)

# 3. stale cache
p = synth.make_scenario(14, "RC", "office", "S", 60.0, scenario_id="STALE-P", **SMALL)
base = population.attach_baseline(p)
engine.clear_baseline_cache()
first = engine.evaluate(p, detail=False)["SUM-08"]
for row in base.materials:
    if row.quantity is not None:
        row.quantity *= 2.0
second = engine.evaluate(p, detail=False)["SUM-08"]            # no clear: stale
ref = registry.run_all(p)["SUM-08"]
engine.clear_baseline_cache()
third = engine.evaluate(p, detail=False)["SUM-08"]
print("3. stale baseline cache (baseline edited between two evaluate calls, cache not cleared)")
print("   reference after edit :", ref)
print("   engine without clear :", second)
print("   engine after clear   :", third)
# 3b. same id reused by a different baseline object (re-attach)
p2 = synth.make_scenario(14, "RC", "office", "S", 60.0, scenario_id="STALE-P", **SMALL)   # same id as p
p2.operation.facility_management_ratio = 0.0
for row in p2.materials:
    if row.quantity is not None:
        row.quantity *= 3.0
base2 = population.attach_baseline(p2)                       # registers "STALE-P-BASELINE" again
stale = engine.evaluate(p2, detail=False)["SUM-08"]
ref2 = registry.run_all(p2)["SUM-08"]
print("3b. new baseline registered under an id seen before (attach_baseline called for a new proposal with the same id)")
print("   reference:", ref2)
print("   engine   :", stale)

# 4. NaN cycle
scn = synth.make_scenario(15, "RC", "office", "S", 60.0, **SMALL)
scn.materials[0].refresh_cycle = float("nan")
st, fs = h.diff(scn)
print("\n4. NaN refresh_cycle:", st, fs[:1])
scn = synth.make_scenario(15, "RC", "office", "S", 60.0, **SMALL)
scn.materials[0].refresh_cycle = float("inf")
scn.equipment[0].service_life = float("inf")
scn.equipment[0].replacement_event_list = None
st, fs = h.diff(scn)
print("4b. inf refresh_cycle/service_life:", st, fs[:1])

# 5. SYS-03 label, minimal
scn = synth.make_scenario(16, "RC", "office", "S", 60.0, **SMALL)
scn.equipment[0].factor_id = "F-NOT-IN-TABLE"
scn.equipment[1].factor_id = "F-NOT-IN-TABLE"
ref = registry.run_all(scn)["SYS-03"]
engine.clear_baseline_cache()
cand = engine.evaluate(scn, detail=True)["SYS-03"]
print("\n5. dangling factor id on two equipment rows")
print("   reference:", ref)
print("   engine   :", cand)
scn = synth.make_scenario(16, "RC", "office", "S", 60.0, **SMALL)
scn.materials[0].end_of_life.routes[0].factor_id = None
scn.water_waste.waste_factor_id = None
ref = registry.run_all(scn)["SYS-03"]
cand = engine.evaluate(scn, detail=True)["SYS-03"]
print("5b. route factor None + water_waste.waste_factor_id None")
print("   reference:", ref)
print("   engine   :", cand)
scn = synth.make_scenario(16, "RC", "office", "S", 60.0, composite_share=1.0, epd_share=0.0, **SMALL)
scn.materials[0].composition[0].factor_id = None
scn.summary_quantities.concrete_uptake_factor_id = "F-NOT-IN-TABLE"
ref = registry.run_all(scn)["SYS-03"]
cand = engine.evaluate(scn, detail=True)["SYS-03"]
print("5c. composite component None + concrete uptake dangling")
print("   reference:", ref)
print("   engine   :", cand)

# 11. types
scn = synth.make_scenario(17, "RC", "office", "S", 60.0, **SMALL)
scn.boundary.study_period = 60
show("11. study_period given as int 60", scn)
scn = synth.make_scenario(17, "RC", "office", "S", 60.0, **SMALL)
scn.boundary.study_period = 61
scn.boundary.replacement_cycle = 20
scn.boundary.reconstruction_scenario = "REBUILD_IDENTICAL"
for m in scn.materials:
    m.refresh_cycle = 7
for e in scn.equipment:
    e.service_life = 13
    e.replacement_event_list = None
for d in scn.refrigerants:
    d.service_life = 9
    d.change_years = None
show("11b. all-int periods and cycles", scn)
