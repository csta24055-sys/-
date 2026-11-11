"""Consolidated minimal reproductions of every finding (verifier lens 1).
Run: cd research_code && PYTHONPATH=. python3 -B <this file>
"""
import copy
import math
import sys
from types import SimpleNamespace as NS

sys.path.insert(0, "/tmp/claude-0/-home-user--/49c0bd7e-a786-5ae4-9a1e-e89e7996ede3/scratchpad/verify/lens1")
import synth
from common.compare import compare, flatten
from fastcalc import closed_forms as cf
from fastcalc import engine
from refcalc import registry
from synth import model, population

registry.load_all()
SMALL = dict(n_materials=12, n_equipment=6, n_refrigerants=4)


def both(scn):
    ref = registry.run_all(scn)
    engine.clear_baseline_cache()
    full = engine.evaluate(scn, detail=True)
    engine.clear_baseline_cache()
    summ = engine.evaluate(scn, detail=False)
    return ref, full, summ


def worst(ref, cand, uid, ign=False):
    scale = abs(ref["SUM-03"]["value"]) or 1.0
    c = compare(ref[uid], cand[uid], floor=1e-9 * scale, ignore_missing=ign)
    fr, fc = flatten(ref[uid]), flatten(cand[uid])
    return dict(unit=uid, path=c.worst_path, err=c.max_abs_rel_error, ref=fr.get(c.worst_path), cand=fc.get(c.worst_path),
                mismatches=c.mismatches[:3], missing=c.missing[:3])


print("=== F1  B3-01.by_year / X-07 on VALID scenarios (generator options only)")
scn = synth.make_scenario(8, "RC", "office", "S", 60.0, n_materials=12, n_equipment=6, n_refrigerants=2,
                          service_life_choices=[0.5, 1.0], explicit_event_share=0.0, change_list_share=0.0, included_stages=["B3"])
ref, full, summ = both(scn)
print("  stages [B3], T=60, lives [0.5, 1.0], seed 8:  WLC =", ref["SUM-03"]["value"])
print("   ", worst(ref, full, "B3-01"))
print("   ", worst(ref, full, "X-07"))
print("    by_year[1..3] reference:", ref["B3-01"]["by_year"][1:4], " unified:", full["B3-01"]["by_year"][1:4])
scn = synth.make_scenario(19, "RC", "office", "S", 1.5, n_materials=12, n_equipment=6, n_refrigerants=0,
                          service_life_choices=[1.0, 0.5, 0.75], explicit_event_share=0.0, change_list_share=0.0)
ref, full, summ = both(scn)
print("  ALL stages, T=1.5, lives [1.0, 0.5, 0.75], seed 19:  WLC =", ref["SUM-03"]["value"])
print("   ", worst(ref, full, "B3-01"))

print("\n=== F2  SYS-03 violation labels when a factor record is missing")
scn = synth.make_scenario(16, "RC", "office", "S", 60.0, **SMALL)
scn.equipment[0].factor_id = scn.equipment[1].factor_id = "F-NOT-IN-TABLE"
ref, full, summ = both(scn)
print("  two equipment rows -> unknown id:  ref", ref["SYS-03"]["violations"], " unified", full["SYS-03"]["violations"])
scn = synth.make_scenario(16, "RC", "office", "S", 60.0, composite_share=1.0, epd_share=0.0, **SMALL)
scn.materials[0].end_of_life.routes[0].factor_id = None
scn.water_waste.waste_factor_id = None
scn.materials[1].composition[0].factor_id = None
scn.summary_quantities.concrete_uptake_factor_id = "F-NOT-IN-TABLE"
ref, full, summ = both(scn)
print("  None in route / waste factor / composite component, unknown uptake id:")
print("    ref    ", ref["SYS-03"]["violations"])
print("    unified", full["SYS-03"]["violations"])

print("\n=== F3  grid table disagrees with its descriptor (X-06.matches_table = False)")
scn = synth.make_scenario(23, "RC", "office", "S", 60.0, profile_kind="LINEAR_TREND", grid_kind="LINEAR_DECLINE_TO_FLOOR", **SMALL)
scn.operation.grid.table[10] *= 2.0
ref, full, summ = both(scn)
for uid in ("X-06", "B6-01", "B6-03", "B2-01", "SUM-03"):
    print("   ", worst(ref, full, uid))
print("    unified X-06.by_year[11] =", full["X-06"]["by_year"][11], " but unified B6-01.by_year[11]/B6-04.by_year[11] =",
      full["B6-01"]["by_year"][11] / full["B6-04"]["by_year"][11])

print("\n=== F4  annual profile table disagrees with its descriptor (model: 'The table is authoritative')")
scn = synth.make_scenario(24, "RC", "office", "S", 60.0, profile_kind="CONSTANT", grid_kind="CONSTANT", **SMALL)
scn.water_waste.water.table[5] *= 3.0
ref, full, summ = both(scn)
for uid in ("B7-01", "B7-04", "SUM-03", "X-07"):
    print("   ", worst(ref, full, uid))
print("    unified detail: X-07.value =", full["X-07"]["value"], " SUM-03 =", full["SUM-03"]["value"], " unified summary X-07.value =", summ["X-07"]["value"])
scn = synth.make_scenario(24, "RC", "office", "S", 60.0, profile_kind="CONSTANT", grid_kind="CONSTANT", **SMALL)
scn.water_waste.water.slope = 5.0            # kind stays CONSTANT, table untouched
ref, full, summ = both(scn)
print("  CONSTANT profile with slope=5.0 set (table untouched):", worst(ref, full, "B7-04"))

print("\n=== F5  baseline cycles")
scn = synth.make_scenario(11, "RC", "office", "S", 60.0, **SMALL)
population.BASELINES[scn.meta.scenario_id] = scn
scn.boundary.baseline_scenario = scn.meta.scenario_id
print("  self as baseline: reference", registry.run_all(scn)["SUM-08"])
engine.clear_baseline_cache()
try:
    engine.evaluate(scn, detail=False)
    print("  unified: ok")
except RecursionError:
    print("  unified: RecursionError")

print("\n=== F6  baseline total cached by scenario id only")
p = synth.make_scenario(14, "RC", "office", "S", 60.0, scenario_id="STALE-P", **SMALL)
base = population.attach_baseline(p)
engine.clear_baseline_cache()
engine.evaluate(p, detail=False)
for row in base.materials:
    if row.quantity is not None:
        row.quantity *= 2.0
print("  reference after editing the baseline:", registry.run_all(p)["SUM-08"])
print("  unified (no cache clear)            :", engine.evaluate(p, detail=False)["SUM-08"])

print("\n=== F7  refrigerant closed form at small leak rates")
for rate in (1e-5, 1e-6, 1e-7, 1e-8, 1e-9, 1e-12):
    T, m0 = 60.0, 100.0
    m, leaked = m0, 0.0
    for y in range(60):
        leak = m * rate
        leaked += leak
        m -= leak
    a = cf.refrigerant_device(T, m0, rate, False, [])[0]
    print(f"  rate {rate:g}: loop {leaked!r} closed form {a!r} rel diff {abs(a - leaked) / leaked:.2e}")
scn = synth.make_scenario(31, "RC", "office", "S", 60.0, top_up=False, **SMALL)
for d in scn.refrigerants:
    d.annual_leak_rate = 1e-8
ref, full, summ = both(scn)
print("  scenario, all stages, leak rate 1e-8:", worst(ref, full, "B1-02"), worst(ref, summ, "B1-02", True)["err"])
scn.boundary.included_lifecycle_stages = ["B1"]
ref, full, summ = both(scn)
print("  same, stages [B1]:", worst(ref, summ, "B1-02", True), worst(ref, summ, "SUM-03", True)["err"])

print("\n=== F8  STEPWISE grid: unsorted steps / first step after year 0")
g = NS(kind="STEPWISE", start=None, annual_decline=None, floor=None, steps=[NS(from_index=10, value=0.2), NS(from_index=0, value=0.5)])
loop = []
for k in range(20):
    v = None
    for s in g.steps:
        if s.from_index <= k:
            v = s.value
    loop.append(v)
print("  steps [(10, 0.2), (0, 0.5)], T=20: loop sum =", sum(loop), " grid_cumulative =", cf.grid_cumulative(20.0, g))
scn = synth.make_scenario(41, "RC", "office", "S", 60.0, grid_kind="STEPWISE", profile_kind="CONSTANT", **SMALL)
scn.operation.grid.steps[0].from_index = 2
for name, fn in (("reference", lambda: registry.run_all(scn)), ("unified detail", lambda: engine.evaluate(scn, detail=True)),
                 ("unified summary", lambda: engine.evaluate(scn, detail=False))):
    try:
        fn()
        print(f"  first step from_index=2: {name}: returns a result")
    except Exception as exc:
        print(f"  first step from_index=2: {name}: {type(exc).__name__}")

print("\n=== F9  LINEAR_DECLINE_TO_FLOOR with annual_decline <= 0 and start < floor")
g = NS(kind="LINEAR_DECLINE_TO_FLOOR", start=0.3, annual_decline=-0.01, floor=0.5, steps=None)
print("  loop:", sum(max(g.floor, g.start - g.annual_decline * k) for k in range(30)), " grid_cumulative:", cf.grid_cumulative(30.0, g))

print("\n=== F10 crash asymmetries on extreme values")
scn = synth.make_scenario(15, "RC", "office", "S", 60.0, **SMALL)
scn.materials[0].refresh_cycle = float("nan")
for name, fn in (("reference", lambda: registry.run_all(scn)), ("unified", lambda: engine.evaluate(scn, detail=False))):
    try:
        fn()
        print(f"  NaN refresh_cycle: {name}: returns a result")
    except Exception as exc:
        print(f"  NaN refresh_cycle: {name}: {type(exc).__name__}: {exc}")
scn = synth.make_scenario(15, "RC", "office", "S", 60.0, top_up=False, **SMALL)
scn.refrigerants[0].annual_leak_rate = 1e12
scn.refrigerants[0].change_years = None
scn.refrigerants[0].service_life = None
for name, fn in (("reference", lambda: registry.run_all(scn)), ("unified", lambda: engine.evaluate(scn, detail=False))):
    try:
        r = fn()
        print(f"  leak rate 1e12: {name}: returns B1-02 =", r["B1-02"]["value"])
    except Exception as exc:
        print(f"  leak rate 1e12: {name}: {type(exc).__name__}: {exc}")
scn = synth.make_scenario(21, "RC", "office", "S", 60.0, **SMALL)
scn.boundary.study_period = -5.0
for name, fn in (("reference", lambda: registry.run_all(scn)), ("unified detail", lambda: engine.evaluate(scn, detail=True)),
                 ("unified summary", lambda: engine.evaluate(scn, detail=False))):
    try:
        r = fn()
        print(f"  study_period -5: {name}: returns SUM-03 =", r["SUM-03"]["value"])
    except Exception as exc:
        print(f"  study_period -5: {name}: {type(exc).__name__}")
