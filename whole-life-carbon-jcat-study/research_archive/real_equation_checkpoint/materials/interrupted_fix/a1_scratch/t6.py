"""SUM-08 / baselines; baseline_totals; state leakage; scenario mutation."""
from fuzzlib import *
nan, inf = float("nan"), float("inf")
def s08(s, held=None):
    out = []
    for fn in (lambda: registry.run_all(s, ids=["SUM-08"])["SUM-08"], lambda: engine.evaluate(s, detail=True, baseline_totals=held)["SUM-08"], lambda: engine.evaluate(s, detail=False, baseline_totals=held)["SUM-08"]):
        try: out.append(fn())
        except RecursionError as e: out.append(e)
        except Exception as e: out.append(e)
    return out
def rep(name, s, held=None):
    r, f, t = s08(s, held)
    def same(a, b):
        if isinstance(a, Exception) or isinstance(b, Exception): return isinstance(a, Exception) and isinstance(b, Exception) and type(a) is type(b)
        return not diffs(a, b, 1e-9, 0.0)
    ok = same(r, f) and same(r, t)
    print(f"[{name}] {'same' if ok else 'DIFFERENT'}: ref={r!r:.170} | full={f!r:.170} | tot={t!r:.170}")
    return ok

def pair(seed=51, **kw):
    s = mk(seed, 60.0, scenario_id=f"P{seed}-{len(population.BASELINES)}", **kw)
    b = population.attach_baseline(s)
    return s, b

# 1 defective baselines
s, b = pair(); b.materials[0].quantity = None; b.materials[1].factor_id = "NOPE"; b.equipment[0].replacement_event_list = [0, 70, 5, 5]; rep("baseline_with_defects", s)
s, b = pair(); b.boundary.study_period = 30.0; rep("baseline_other_period", s)
s, b = pair(); b.boundary.study_period = 60; rep("baseline_period_int_60", s)
s, b = pair(); b.boundary.study_period = nan; rep("baseline_period_nan", s)
s, b = pair(); b.boundary.study_period = None; rep("baseline_period_none", s)
s, b = pair(); b.project.gross_floor_area = None; rep("baseline_area_none", s)
s, b = pair(); b.project.gross_floor_area = None; s.project.gross_floor_area = None; rep("both_area_none", s)
s, b = pair(); b.project.gross_floor_area = nan; s.project.gross_floor_area = nan; rep("both_area_nan", s)
s, b = pair(); b.boundary.included_lifecycle_stages = list(reversed(b.boundary.included_lifecycle_stages)) + ["B6"]; rep("baseline_stage_order_dups", s)
s, b = pair(); b.boundary.included_lifecycle_stages = ["A1-A3"]; rep("baseline_stage_subset", s)
s, b = pair(); b.boundary.results_gas_scope = "CO2_ONLY"; rep("baseline_gas_scope", s)
s, b = pair(); next(iter(b.factors.values())).release_year += 1; rep("baseline_factor_version", s)
s, b = pair(); b.factors.clear(); rep("baseline_no_factors", s)
s, b = pair(); s.factors.clear(); b.factors.clear(); rep("both_no_factors", s)
s, b = pair(); b.operation.grid.table = b.operation.grid.table[:10]; rep("baseline_short_grid_table", s)
s, b = pair(); b.operation.grid.kind = "LINEAR_DECLINE_TO_FLOOR"; b.operation.grid.start, b.operation.grid.floor, b.operation.grid.annual_decline = 0.5, 0.1, nan; rep("baseline_grid_decline_nan", s)
s, b = pair(); b.water_waste.water.kind = "TABLE"; b.water_waste.water.table = []; b.water_waste.water_factor_id = None; rep("baseline_short_profile_no_factor", s)
s, b = pair(); b.boundary.included_lifecycle_stages = []; s.boundary.included_lifecycle_stages = []; rep("both_no_stages (baseline total 0)", s)
s, b = pair()
for r in b.materials: r.quantity = 0.0
rep("baseline_zero_quantities", s)
# negative baseline total
s, b = pair()
for f in b.factors.values(): f.value = -abs(f.value)
rep("baseline_negative_total", s)
# 2 chain and cycle
s, b = pair(); c = population.attach_baseline(b); rep("chain_of_baselines", s)
s, b = pair(); b.boundary.baseline_scenario = s.meta.scenario_id; population.BASELINES[s.meta.scenario_id] = s; rep("cycle_of_two", s)
s = mk(52, scenario_id="SELF-X"); population.BASELINES["SELF-X"] = s; s.boundary.baseline_scenario = "SELF-X"; rep("self_baseline", s)
s = mk(52, scenario_id="SELF-Y"); s.boundary.baseline_scenario = "NOT-REGISTERED"; rep("unregistered_baseline", s)
s = mk(52, scenario_id="SELF-Z"); population.BASELINES[None] = copy.deepcopy(s); s.boundary.baseline_scenario = None; rep("baseline_registered_under_None", s); population.BASELINES.pop(None)
# 3 held baseline totals
s, b = pair(); held = {}
rep("held_first", s, held)
for r in b.materials:
    if r.quantity is not None: r.quantity *= 3.0
rep("held_after_baseline_edit (stale value expected by design)", s, held)
# two different baselines whose meta.scenario_id is equal
s1, b1 = pair(61); s2, b2 = pair(62)
b2.meta.scenario_id = b1.meta.scenario_id            # registry keys remain different
held = {}
ok1 = rep("held_two_baselines_same_meta_id: scenario 1", s1, held)
ok2 = rep("held_two_baselines_same_meta_id: scenario 2", s2, held)
print("   BASELINES keys differ:", s1.boundary.baseline_scenario != s2.boundary.baseline_scenario, "; held dict:", held)
# proposal period changed while holding
s, b = pair(63); held = {}
rep("held_T60", s, held)
s.boundary.study_period = b.boundary.study_period = 30.0
rep("held_then_both_periods_changed_to_30", s, held)
# held value None / 0.0
# adaptation: a held entry is now {"value": total, "complete": bool}, keyed by boundary.baseline_scenario
s, b = pair(64); held = {s.boundary.baseline_scenario: {"value": 0.0, "complete": True}}; rep("held_zero_value_supplied (used as supplied, by design)", s, held)

# 4 state leakage and scenario mutation
import itertools
ss = [build(k)[0] for k in (5, 6, 7, 8, 9, 11)]
for x in ss: x.boundary.baseline_scenario = None
fresh = []
for x in ss:
    try: fresh.append(engine.evaluate(copy.deepcopy(x), detail=True))
    except Exception as e: fresh.append(e)
leak = 0
for order in itertools.permutations(range(len(ss)), 3):
    for i in order:
        try: r = engine.evaluate(ss[i], detail=True)
        except Exception as e: r = e
        if isinstance(r, Exception) != isinstance(fresh[i], Exception): leak += 1; continue
        if isinstance(r, Exception): continue
        for uid in r:
            if uid.startswith("_"): continue
            if diffs(fresh[i][uid], r[uid], 0.0, 0.0): leak += 1
print("state leakage across interleaved evaluations (bit-exact comparison):", leak)
mut = 0; nchk = 0
for seed in range(300, 420):
    s, T, log = build(seed)
    for fn in (lambda x: registry.run_all(x), lambda x: engine.evaluate(x, detail=True), lambda x: engine.evaluate(x, detail=False)):
        before = copy.deepcopy(s)
        try: fn(s)
        except Exception: pass
        try:
            nchk += 1
            if repr(before) != repr(s): mut += 1; print("scenario mutated, seed", seed)
        except Exception: pass
print("scenario mutated by a calculation:", mut, "of", nchk, "checks (repr comparison of deep copies)")
