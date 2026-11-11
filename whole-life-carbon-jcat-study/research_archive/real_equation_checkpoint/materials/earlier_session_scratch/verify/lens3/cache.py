"""K8: the baseline total is cached by scenario id only. What happens when the baseline input changes?"""
import copy
import synth
from fastcalc import engine
from refcalc import registry
from synth import population
registry.load_all()

scn = synth.make_scenario(555, "RC", "office", "S", 60.0)
base = population.attach_baseline(scn)
engine.clear_baseline_cache()
ref1 = registry.run_all(scn)["SUM-08"]; fast1 = engine.evaluate(scn, detail=False)["SUM-08"]
print("first evaluation   ref:", ref1["status"], round(ref1["baseline"], 3), round(ref1["saving"], 6), "| fast:", fast1["status"], round(fast1["baseline"], 3), round(fast1["saving"], 6))
# the user revises the baseline design (same id, same area/period/stages/gas scope/factor versions => still comparable)
for row in base.materials:
    if row.quantity is not None:
        row.quantity *= 1.5
ref2 = registry.run_all(scn)["SUM-08"]; fast2 = engine.evaluate(scn, detail=False)["SUM-08"]
print("after baseline edit ref:", ref2["status"], round(ref2["baseline"], 3), round(ref2["saving"], 6), "| fast:", fast2["status"], round(fast2["baseline"], 3), round(fast2["saving"], 6))
print("   relative difference of baseline total fast vs ref: %+.3e ; saving ref %.4f vs fast %.4f" % ((fast2["baseline"] - ref2["baseline"]) / ref2["baseline"], ref2["saving"], fast2["saving"]))
engine.clear_baseline_cache()
fast3 = engine.evaluate(scn, detail=False)["SUM-08"]
print("after manual clear_baseline_cache(): fast baseline", round(fast3["baseline"], 3))

# does verify_unified ever compare a warm-cache evaluation with the reference?
import inspect
from bench import verify_unified
src = inspect.getsource(verify_unified.exactness)
print("clear_baseline_cache() calls inside exactness():", src.count("clear_baseline_cache"), "| evaluate() calls:", src.count("engine.evaluate"))

# scenario-id uniqueness across the verification inputs (cache key)
ids = []
for group, s in verify_unified.scenarios(400, 60):
    ids.append((group, s.meta.scenario_id, s.boundary.baseline_scenario))
import collections
c = collections.Counter(i for _, i, _ in ids)
print("scenarios:", len(ids), "duplicate scenario ids:", {k: v for k, v in c.items() if v > 1})
bc = collections.Counter(b for _, _, b in ids if b)
print("scenarios with a baseline:", sum(bc.values()), "duplicate baseline ids:", {k: v for k, v in bc.items() if v > 1})
print("by group with baseline:", collections.Counter(g.split(':')[0] for g, _, b in ids if b))
