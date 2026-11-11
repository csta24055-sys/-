"""Part 6: further targeted probes."""
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


def show(title, scn, limit=5):
    st, fs = h.diff(scn)
    print(f"\n--- {title}: {st}, {len(fs)} findings")
    for f in fs[:limit]:
        print("    ", {k: v for k, v in f.items() if k != "scale"})
    return fs


# T <= 0 (SUM-05's definition anticipates "study period <= 0")
for T in (0.0, -5.0, 0):
    scn = synth.make_scenario(21, "RC", "office", "S", 60.0, **SMALL)
    scn.boundary.study_period = T
    show(f"study_period = {T!r}", scn, limit=3)

# T beyond the year tables
for kinds in (("CONSTANT", "CONSTANT"), ("TABLE", "TABLE"), ("LINEAR_TREND", "STEPWISE")):
    scn = synth.make_scenario(22, "RC", "office", "S", 60.0, profile_kind=kinds[0], grid_kind=kinds[1], **SMALL)
    scn.boundary.study_period = 200.0          # tables have 130 entries
    show(f"study_period 200 with 130-entry tables, profiles {kinds}", scn, limit=2)

# grid table disagrees with its descriptor (X-06 reports matches_table = False)
scn = synth.make_scenario(23, "RC", "office", "S", 60.0, profile_kind="LINEAR_TREND", grid_kind="LINEAR_DECLINE_TO_FLOOR", **SMALL)
scn.operation.grid.table[10] *= 2.0
ref = registry.run_all(scn)
full = engine.evaluate(scn, detail=True)
summ = engine.evaluate(scn, detail=False)
print("\n--- grid.table[10] doubled, descriptor unchanged (LINEAR_DECLINE_TO_FLOOR, LINEAR_TREND demand)")
print("    X-06.matches_table  ref/full:", ref["X-06"]["matches_table"], full["X-06"]["matches_table"])
print("    X-06.by_year[11]    ref/full:", ref["X-06"]["by_year"][11], full["X-06"]["by_year"][11], " table[10] =", scn.operation.grid.table[10])
print("    B6-01.by_year[11]   ref/full:", ref["B6-01"]["by_year"][11], full["B6-01"]["by_year"][11])
print("    B6-03.value         ref/full/summary:", ref["B6-03"]["value"], full["B6-03"]["value"], summ["B6-03"]["value"])
print("    X-11.value          ref/full:", ref["X-11"]["value"], full["X-11"]["value"])
print("    SUM-03.value        ref/full/summary:", ref["SUM-03"]["value"], full["SUM-03"]["value"], summ["SUM-03"]["value"])
# same with CONSTANT demand: the engine then switches to the descriptor
scn = synth.make_scenario(23, "RC", "office", "S", 60.0, profile_kind="CONSTANT", grid_kind="LINEAR_DECLINE_TO_FLOOR", **SMALL)
scn.operation.grid.table[10] *= 2.0
ref = registry.run_all(scn)
full = engine.evaluate(scn, detail=True)
print("--- same with CONSTANT demand profiles")
print("    B6-01.by_year[11]   ref/full:", ref["B6-01"]["by_year"][11], full["B6-01"]["by_year"][11])
print("    B6-03.value         ref/full:", ref["B6-03"]["value"], full["B6-03"]["value"], "  <- engine total no longer equals the weighted sum of its own B6-01 series")
w = [0.0] + [1.0] * 60
print("    engine: sum_y w_y*B6-01.by_year[y] + fuels =",
      sum(w[y] * (full["B6-01"]["by_year"][y] + full["B6-02"]["by_year"][y]) for y in range(1, 61)))

# profile table disagrees with its descriptor ("The table is authoritative")
scn = synth.make_scenario(24, "RC", "office", "S", 60.0, profile_kind="CONSTANT", grid_kind="CONSTANT", **SMALL)
scn.water_waste.water.table[5] *= 3.0
ref = registry.run_all(scn)
full = engine.evaluate(scn, detail=True)
print("\n--- water.table[5] tripled, kind CONSTANT / base unchanged")
print("    B7-01.by_year[6]  ref/full:", ref["B7-01"]["by_year"][6], full["B7-01"]["by_year"][6])
print("    B7-04.value       ref/full:", ref["B7-04"]["value"], full["B7-04"]["value"])
print("    SUM-03.value      ref/full:", ref["SUM-03"]["value"], full["SUM-03"]["value"])
print("    X-07.value        ref/full:", ref["X-07"]["value"], full["X-07"]["value"], " (engine X-07 follows the table, engine SUM-03 follows the descriptor)")
scn = synth.make_scenario(24, "RC", "office", "S", 60.0, profile_kind="CONSTANT", grid_kind="CONSTANT", **SMALL)
scn.operation.electricity.table[5] *= 3.0
ref = registry.run_all(scn)
full = engine.evaluate(scn, detail=True)
print("--- electricity.table[5] tripled, kind CONSTANT")
print("    B6-04.by_year[6]  ref/full:", ref["B6-04"]["by_year"][6], full["B6-04"]["by_year"][6])
print("    B6-03.value       ref/full:", ref["B6-03"]["value"], full["B6-03"]["value"])

# near-identical baseline: delta is a difference of two totals that agree to ~1e-10
p = synth.make_scenario(25, "RC", "office", "S", 60.0, scenario_id="NEAR-P", **SMALL)
b = copy.deepcopy(p)
b.meta.scenario_id = "NEAR-B"
b.materials[0].quantity *= 1.0 + 1e-8
population.BASELINES["NEAR-B"] = b
p.boundary.baseline_scenario = "NEAR-B"
ref = registry.run_all(p)["SUM-08"]
engine.clear_baseline_cache()
full = engine.evaluate(p, detail=True)["SUM-08"]
print("\n--- baseline differing from the proposal by 1e-8 in one quantity")
print("    reference:", ref)
print("    unified  :", full)
show("near-identical baseline", p)

# explicit list values just inside / at T, non-integer T
scn = synth.make_scenario(26, "RC", "office", "S", 62.5, **SMALL)
for e in scn.equipment:
    e.replacement_event_list = [62.5, 62.4999999, 62.0, 62.0000001, 61.9999999, 0.0000001, 0, 62]
for d in scn.refrigerants:
    d.change_years = [62.5, 62.4999999, 62.0, 62.0000001, 61.9999999, 0.0000001, 0, 62]
    d.top_up = False
show("events around the last partial year", scn)
