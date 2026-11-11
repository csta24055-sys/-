"""One short reproduction per finding (NUM-1 ... NUM-11). Read-only on the repository.
Run:  cd <study>/research_code && PYTHONPATH=.:<this folder> python3 -B <this folder>/repro_findings.py
"""
from h import *
from common.compare import compare
nan, inf = float("nan"), float("inf")
def three(s, held=None):
    return run3(s, held)
def val(x, u, k="value"):
    return repr(x)[:70] if isinstance(x, Exception) else x[u][k]

print("NUM-1  renewal period 1.000000001 (generator option only, no mutation)")
s = mk(1, 60.0, service_life_choices=[1.000000001], explicit_event_share=0.0, change_list_share=0.0)
r, f, t = three(s)
for u in ("B3-01", "SUM-02", "SUM-03"):
    print(f"   {u}: ref {r[u]['value']!r} unified {f[u]['value']!r} totals {t[u]['value']!r} rel {(f[u]['value']-r[u]['value'])/r[u]['value']:+.3e}")
print("   unified full output: sum(B3-01.by_year) =", sum(f["B3-01"]["by_year"]), "; X-07.value =", f["X-07"]["value"], "; QA-01 =", f["QA-01"])
from refcalc import base
for T in (7.0, 30.0, 60.0):
    ev = base.periodic_events(T, 1.000000001); w = base.year_weights(T)
    print(f"   T={T}: events {len(ev)}, distinct event years {len({base.event_year(x) for x in ev})}, loop skip weight {sum(w[y] for y in {base.event_year(x) for x in ev})}, closed form {cf.skip_weight_periodic(T, 1.000000001, len(ev))}")

print("NUM-2  NaN / inf in fields without a range guard")
s = mk(1, 60.0, grid_kind="LINEAR_DECLINE_TO_FLOOR"); s.operation.grid.annual_decline = nan
r, f, t = three(s); print("   grid.annual_decline=nan: ref X-06.source", val(r, "X-06", "source"), "SUM-03", val(r, "SUM-03"), "| unified", repr(f), "| totals", repr(t))
s = mk(1, 60.0, grid_kind="LINEAR_DECLINE_TO_FLOOR"); s.operation.grid.start = inf
r, f, t = three(s); print("   grid.start=inf: ref X-06.source", val(r, "X-06", "source"), "| unified", repr(f))
s = mk(1, 60.0, profile_kind="CONSTANT"); s.operation.gas.base = nan
r, f, t = three(s); print("   gas.base=nan: QA-01 ref", r["QA-01"], "unified", f["QA-01"], "totals", t["QA-01"])
s = mk(1, 60.0); s.operation.grid.construction_value = nan
r, f, t = three(s); print("   grid.construction_value=nan: B5-01.value ref", r["B5-01"]["value"], "unified", f["B5-01"]["value"], "| QA-01 ref ok", r["QA-01"]["ok"], "unified", f["QA-01"])
s = mk(1, 60.0, profile_kind="LINEAR_TREND"); s.operation.gas.slope = inf
r, f, t = three(s); print("   gas.slope=inf: B6-03 ref", r["B6-03"]["value"], "unified", f["B6-03"]["value"], "| SUM-03 ref", r["SUM-03"]["value"], "unified", f["SUM-03"]["value"])

print("NUM-3  factor value 0.0 with a non-zero gas vector")
s = mk(1, 60.0, composite_share=0.0, epd_share=0.0); eq = s.equipment[0]; eq.repair_rate = 0.02; s.factors[eq.factor_id].value = 0.0
r, f, t = three(s)
for u, k in (("X-04", "value"), ("X-05", "value"), ("SUM-03", "value")):
    print(f"   {u}.{k}: ref {r[u][k]!r} unified {f[u][k]!r} totals {t[u][k]!r} rel {(f[u][k]-r[u][k])/r[u][k]:+.3e}")
print("   X-05.by_stage_co2.B3: ref", r["X-05"]["by_stage_co2"]["B3"], "unified", f["X-05"]["by_stage_co2"]["B3"])

print("NUM-4  annual table shorter than the period AND unusable factor")
s = mk(1, 60.0, profile_kind="TABLE"); s.water_waste.water.table = s.water_waste.water.table[:59]; s.water_waste.water_factor_id = None
r, f, t = three(s); print("   ref:", repr(r)[:60], "| unified B7-01 n_skipped", val(f, "B7-01", "n_skipped"), "SUM-03", val(f, "SUM-03"), "| totals SUM-03", val(t, "SUM-03"))
s = mk(1, 60.0, profile_kind="TABLE"); s.operation.electricity.table = s.operation.electricity.table[:10]; s.operation.onsite_generation.unit = "kWh/day"
r, f, t = three(s); print("   short electricity table + generation in kWh/day: ref:", repr(r)[:60], "| unified SUM-03", val(f, "SUM-03"))

print("NUM-5  factor id equal to the pseudo ids")
for pid in ("GRID", "REFRIGERANT"):
    s = mk(1, 60.0, composite_share=0.0, epd_share=0.0); row = s.materials[0]
    rec = copy.deepcopy(s.factors[row.factor_id]); rec.factor_id = pid; s.factors[pid] = rec; row.factor_id = pid
    r, f, t = three(s)
    print(f"   id {pid}: A5-01 ref {r['A5-01']['value']!r} unified {f['A5-01']['value']!r} | SUM-03 ref {r['SUM-03']['value']!r} unified {f['SUM-03']['value']!r} totals {t['SUM-03']['value']!r} rel {(f['SUM-03']['value']-r['SUM-03']['value'])/r['SUM-03']['value']:+.3e} | X-02.by_stage.A1-A3 ref {r['X-02']['by_stage']['A1-A3']!r} unified {f['X-02']['by_stage']['A1-A3']!r}")

print("NUM-6  gas list defects with composite rows")
s = mk(1, 60.0, composite_share=0.5, epd_share=0.0); s.gases = list(s.gases) + ["CO2"]
r, f, t = three(s); print("   'CO2' twice: X-04.value ref", r["X-04"]["value"], "unified", f["X-04"]["value"], "totals", t["X-04"]["value"])
s = mk(1, 60.0, composite_share=0.5, epd_share=0.0); s.gases = [g for g in s.gases if g != "CO2"]
r, f, t = three(s); print("   no 'CO2': ref X-05.value", val(r, "X-05"), "| unified", repr(f), "| totals", repr(t))

print("NUM-7  STEPWISE step index given as float 3.0")
s = mk(1, 60.0, grid_kind="STEPWISE"); s.operation.grid.steps = [model.GridStep(0, 0.5), model.GridStep(3.0, 0.3)]
r, f, t = three(s); print("   ref X-06.source", val(r, "X-06", "source"), "SUM-03", val(r, "SUM-03"), "| unified", repr(f), "| totals", repr(t))

print("NUM-8  unit literally named 'None'")
s = mk(1, 60.0)
for p in (s.operation.electricity, s.operation.onsite_generation, s.operation.onsite_export): p.unit = "None/year"
s.operation.grid.unit = "kgCO2e/None"
r, f, t = three(s); print("   SYS-02.violations ref", r["SYS-02"]["violations"], "| unified", f["SYS-02"]["violations"], "| totals", t["SYS-02"]["violations"])

print("NUM-9  baseline_totals keyed by meta.scenario_id")
s1 = mk(61, 60.0, scenario_id="N9-A"); b1 = population.attach_baseline(s1)
s2 = mk(62, 60.0, scenario_id="N9-B"); b2 = population.attach_baseline(s2)
b2.meta.scenario_id = b1.meta.scenario_id
held = {}
for s in (s1, s2):
    rr = registry.run_all(s, ids=["SUM-08"])["SUM-08"]; ee = engine.evaluate(s, detail=False, baseline_totals=held)["SUM-08"]
    print(f"   {s.meta.scenario_id} (registry key {s.boundary.baseline_scenario}): baseline ref {rr['baseline']!r} unified {ee['baseline']!r}; saving ref {rr['saving']:.6f} unified {ee['saving']:.6f}")

print("NUM-10 ill-conditioned inputs (study's own comparison: floor 1e-9*|SUM-03|, tolerance 1e-9)")
def study(s):
    r, f, t = three(s); scale = abs(r["SUM-03"]["value"]) or 1.0; out = []
    for u in r:
        c = compare(r[u], f.get(u, {}), floor=1e-9 * scale); cs = compare(r[u], t.get(u, {}), floor=1e-9 * scale, ignore_missing=True)
        if not (c.within(1e-9) and not c.extra and cs.within(1e-9)): out.append((u, c.worst_path, f"{c.max_abs_rel_error:.2e}", c.mismatches[:1]))
    return out
s = mk(3, 60.0, profile_kind="CONSTANT", grid_kind="CONSTANT"); s.operation.facility_management_ratio = 1.0
for p in (s.operation.gas, s.operation.oil, s.operation.district_heat): p.base *= 1e-7; p.table = [p.base] * len(p.table)
print("   share 1.0, fuels x1e-7:", study(s))
s = mk(3, 1.000000001, profile_kind="LINEAR_TREND", grid_kind="CONSTANT", included_stages=["B6"]); op = s.operation
for p, (b_, sl) in ((op.electricity, (0.0, 1000.0)), (op.onsite_generation, (0.0, 0.0)), (op.onsite_export, (0.0, 0.0))):
    p.kind, p.base, p.slope = "LINEAR_TREND", b_, sl; p.table = [b_ + sl * k for k in range(len(p.table))]
for p in (op.gas, op.oil, op.district_heat): p.kind, p.base, p.slope = "CONSTANT", 0.0, None; p.table = [0.0] * len(p.table)
print("   T=1.000000001, electricity 0+1000k, only B6:", study(s)[:3])
s = mk(4, 60.0, composite_share=0.0, epd_share=0.0); rows = s.materials[:2]
for row in rows: row.factor_id = rows[0].factor_id; row.quantity_unit = rows[0].quantity_unit; row.conversions = rows[0].conversions; row.quantity = 1.2e308; row.waste_rate = 0.0
s.factors[rows[0].factor_id].value = 0.001
r, f, t = three(s); print("   two rows of 1.2e308 with factor 0.001: A13-01 ref", r["A13-01"]["value"], "unified", f["A13-01"]["value"], "| B5-01 ref", r["B5-01"]["value"], "unified", f["B5-01"]["value"])

print("NUM-11 comparison function")
for a, b_ in ((inf, 1.0), (inf, -inf), (-inf, 5.0)):
    c = compare({"value": a}, {"value": b_}, floor=1e-9); print(f"   compare(ref={a}, cand={b_}).within(1e-9) = {c.within(1e-9)}")
