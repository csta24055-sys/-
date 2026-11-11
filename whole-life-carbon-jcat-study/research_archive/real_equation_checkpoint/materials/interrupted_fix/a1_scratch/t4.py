from h import *
from common.compare import compare
nan, inf = float("nan"), float("inf")

def study_fail(scn):
    """failures under the study's own comparison (floor = 1e-9*|SUM-03|, tol 1e-9)"""
    ref, full, tot = run3(scn)
    if any(isinstance(x, Exception) for x in (ref, full, tot)):
        return [("exception", repr(ref)[:80], repr(full)[:80], repr(tot)[:80])]
    scale = abs(ref["SUM-03"]["value"]) or 1.0
    out = []
    for uid in ref:
        c = compare(ref[uid], full.get(uid, {}), floor=1e-9 * scale)
        cs = compare(ref[uid], tot.get(uid, {}), floor=1e-9 * scale, ignore_missing=True)
        if not (c.within(1e-9) and not c.extra and cs.within(1e-9)):
            out.append((uid, c.worst_path, c.max_abs_rel_error, c.mismatches[:2], cs.max_abs_rel_error, cs.mismatches[:2]))
    return out

def show(name, s):
    strict = check(s, name, quiet=True)
    st = study_fail(s)
    print(f"[{name}] strict diffs {len(strict)}; fails under the study's comparison: {len(st)}")
    for r in strict[:5]: print("     strict", r)
    for r in st[:5]: print("     study ", r)

# --- A. SUM-08 with a baseline that differs only slightly
for frac in (1e-2, 1e-4, 1e-6, 1e-8):
    s = synth.make_scenario(101, "RC", "office", "S", 60.0, scenario_id=f"P-{frac}")
    base = copy.deepcopy(s); base.meta.scenario_id = f"B-{frac}"; base.boundary.baseline_scenario = None
    row = max((r for r in base.materials if r.quantity), key=lambda r: r.quantity)
    row.quantity *= (1 + frac)
    population.BASELINES[base.meta.scenario_id] = base
    s.boundary.baseline_scenario = base.meta.scenario_id
    ref = registry.run_all(s, ids=["SUM-08"])["SUM-08"]; eng = engine.evaluate(s, detail=False)["SUM-08"]
    print(f"baseline differs in one row by {frac}: ref delta {ref['delta']!r} eng delta {eng['delta']!r} rel {abs(ref['delta']-eng['delta'])/abs(ref['delta']):.2e}; saving ref {ref['saving']!r} eng {eng['saving']!r}")
    show(f"near_baseline_{frac}", s)

# --- B. B6 = B6-03 - B2-01 with share 1 and little fuel
s = mk(3, 60.0, profile_kind="CONSTANT", grid_kind="CONSTANT")
s.operation.facility_management_ratio = 1.0
for p in (s.operation.gas, s.operation.oil, s.operation.district_heat):
    p.base *= 1e-9; p.table = [p.base] * len(p.table)
show("share1_tiny_fuel", s)

# --- C. T just above 1 with zero base electricity
for T in (1.0000001, 1.000000001, 1.0 + 1e-12):
    s = mk(3, T, profile_kind="LINEAR_TREND", grid_kind="CONSTANT", included_stages=["B6"])
    op = s.operation
    for p, (b, sl) in ((op.electricity, (0.0, 1000.0)), (op.onsite_generation, (0.0, 0.0)), (op.onsite_export, (0.0, 0.0))):
        p.kind, p.base, p.slope = "LINEAR_TREND", b, sl; p.table = [b + sl * k for k in range(len(p.table))]
    for p in (op.gas, op.oil, op.district_heat):
        p.kind, p.base, p.slope = "CONSTANT", 0.0, None; p.table = [0.0] * len(p.table)
    show(f"T={T!r}_zero_base", s)
# --- D. tiny T with only B6
for T in (1e-6, 1e-8, 1e-10):
    s = mk(3, T, profile_kind="CONSTANT", grid_kind="CONSTANT", included_stages=["B6"])
    show(f"tinyT={T!r}", s)
# --- E. overflow of activities
s = mk(4, 60.0, composite_share=0.0, epd_share=0.0)
rows = [r for r in s.materials][:2]
for r in rows:
    r.factor_id = rows[0].factor_id; r.quantity_unit = rows[0].quantity_unit; r.conversions = rows[0].conversions; r.quantity = 1.2e308; r.waste_rate = 0.0
s.factors[rows[0].factor_id].value = 0.001
show("overflow_activity_sum", s)
# --- F. negative factors and cancellation
for seed in range(6):
    s = mk(10 + seed, 60.0, composite_share=0.0, epd_share=0.0)
    rows = s.materials[:2]
    f0 = copy.deepcopy(s.factors[rows[0].factor_id]); f0.factor_id = "F-POS"; f0.value = 1.1; f0.unit = "kg"; f0.gas_amounts = {g: (1.1 if g == "CO2" else 0.0) for g in f0.gas_amounts}
    f1 = copy.deepcopy(f0); f1.factor_id = "F-NEG"; f1.value = -1.1; f1.gas_amounts = {g: (-1.1 if g == "CO2" else 0.0) for g in f1.gas_amounts}
    s.factors["F-POS"], s.factors["F-NEG"] = f0, f1
    for r, fid in zip(rows, ("F-POS", "F-NEG")):
        r.factor_id, r.quantity_unit, r.conversions, r.quantity, r.waste_rate, r.epd, r.composition = fid, "kg", [], 1e13 * (1 + seed * 0.1), 0.03, None, None
    show(f"neg_factor_cancel_{seed}", s)
# --- G. refrigerant with leak rate 1-1e-8 and an event
s = mk(5, 60.0, n_refrigerants=1, included_stages=["B1"])
d = s.refrigerants[0]; d.annual_leak_rate = 1 - 1e-8; d.top_up = False; d.change_years = [2, 5]; d.service_life = None; d.replacement_loss_rate = 1.0; d.end_of_life_recovery_rate = 0.0
ref, full, tot = run3(s)
for u in ("B1-02", "B1-03", "B1-04"): print("  ", u, ref[u]["value"], full[u]["value"], tot[u]["value"])
show("leak_rate_1-1e-8", s)
