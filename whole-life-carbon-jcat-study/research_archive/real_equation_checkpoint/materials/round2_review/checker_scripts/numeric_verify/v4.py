from vh import *
from fractions import Fraction
print("=== NUM-3 self-consistent NF3 case ===")
s = mk(1, 60.0, composite_share=0.0, epd_share=0.0); eq = s.equipment[0]; eq.repair_rate = 0.02
rec = s.factors[eq.factor_id]; s.gwp["NF3"] = 0.0
rec.gas_amounts = {k: (5.0 if k == "NF3" else 0.0) for k in rec.gas_amounts}; rec.value = sum(s.gwp[k] * v for k, v in rec.gas_amounts.items())
r, f, t = three(s); print("  factor value", rec.value, "by_gas.NF3 ref", r["X-04"]["by_gas"]["NF3"], "full", f["X-04"]["by_gas"]["NF3"], "| X-04.value", r["X-04"]["value"], f["X-04"]["value"])
print("  study failures:", [(x[0], x[1], x[2]) for x in study_fails(s)])

print("=== NUM-10 (a) share 1, tiny fuels ===")
for sc in (1e-5, 1e-6, 1e-7):
    s = mk(3, 60.0, profile_kind="CONSTANT", grid_kind="CONSTANT"); s.operation.facility_management_ratio = 1.0
    for p in (s.operation.gas, s.operation.oil, s.operation.district_heat): p.base *= sc; p.table = [p.base] * len(p.table)
    r, f, t = three(s)
    # exact fuel-only value from the reference's own B6-02 series
    w = base.year_weights(60.0); fuel = sum(w[y] * r["B6-02"]["by_year"][y] for y in range(1, len(w)))
    print(f"  scale {sc}: by_stage.B6 ref {r['X-02']['by_stage']['B6']!r} full {f['X-02']['by_stage']['B6']!r}; fuel-only sum {fuel!r}; QA-01 ref {r['QA-01']} full {f['QA-01']['ok']}; fails {[(x[0], x[1], '%.1e' % x[2], x[3]) for x in study_fails(s)]}")

print("=== NUM-10 (b) T just above 1 ===")
for T in (1.000000001, 1.0 + 1e-12, 1e-8, 1e-10):
    if T > 1:
        s = mk(3, T, profile_kind="LINEAR_TREND", grid_kind="CONSTANT", included_stages=["B6"]); op = s.operation
        for p, (b_, sl) in ((op.electricity, (0.0, 1000.0)), (op.onsite_generation, (0.0, 0.0)), (op.onsite_export, (0.0, 0.0))):
            p.kind, p.base, p.slope = "LINEAR_TREND", b_, sl; p.table = [b_ + sl * k for k in range(len(p.table))]
        for p in (op.gas, op.oil, op.district_heat): p.kind, p.base, p.slope = "CONSTANT", 0.0, None; p.table = [0.0] * len(p.table)
    else:
        s = mk(3, T, profile_kind="CONSTANT", grid_kind="CONSTANT", included_stages=["B6"])
    r, f, t = three(s)
    print(f"  T={T!r}: B6-03 ref {g(r,'B6-03')!r} full {g(f,'B6-03')!r} rel {abs(g(f,'B6-03')-g(r,'B6-03'))/abs(g(r,'B6-03')):.2e}; study fails {[(x[0], '%.1e' % x[2]) for x in study_fails(s)][:4]}")
    if T > 1:
        # exact: w2 = T-1 (exact in float? T-1 is exact), value = w2 * 1000 * c_elec * grid
        gval = s.operation.grid.start; w2 = Fraction(T) - 1
        c = engine.aggregate(s, False).misc["c_elec"]
        exact = float(w2 * Fraction(1000.0) * Fraction(c) * Fraction(gval))
        print("     exact (rational) B6-03 =", repr(exact), " -> ref rel err %.2e, unified rel err %.2e" % (abs(g(r,'B6-03')-exact)/exact, abs(g(f,'B6-03')-exact)/exact))

print("=== NUM-10 (c) near-identical baseline ===")
s = synth.make_scenario(101, "RC", "office", "S", 60.0, scenario_id="V-P")
b = copy.deepcopy(s); b.meta.scenario_id = "V-B"; b.boundary.baseline_scenario = None
row = max((x for x in b.materials if x.quantity), key=lambda x: x.quantity); row.quantity *= (1 + 1e-8)
population.BASELINES["V-B"] = b; s.boundary.baseline_scenario = "V-B"
rr = registry.run_all(s, ids=["SUM-08"])["SUM-08"]; ee = engine.evaluate(s, detail=False)["SUM-08"]
print("  delta ref", rr["delta"], "unified", ee["delta"], "rel", abs(rr["delta"] - ee["delta"]) / abs(rr["delta"]), "| baselines", rr["baseline"], ee["baseline"], "rel", abs(rr["baseline"]-ee["baseline"])/rr["baseline"])
print("  study fails:", [(x[0], x[1], '%.2e' % x[2]) for x in study_fails(s)])

print("=== NUM-10 (d) overflow ===")
s = mk(4, 60.0, composite_share=0.0, epd_share=0.0); rows = s.materials[:2]
for row in rows: row.factor_id = rows[0].factor_id; row.quantity_unit = rows[0].quantity_unit; row.conversions = rows[0].conversions; row.quantity = 1.2e308; row.waste_rate = 0.0
s.factors[rows[0].factor_id].value = 0.001
r, f, t = three(s); print("  A13-01", g(r, "A13-01"), g(f, "A13-01"), "| B5-01", g(r, "B5-01"), g(f, "B5-01"), "| reconstruction", s.boundary.reconstruction_scenario)

print("=== NUM-10 (e) leak rate 1-1e-8 ===")
s = mk(5, 60.0, n_refrigerants=1, included_stages=["B1"]); d = s.refrigerants[0]
d.annual_leak_rate = 1 - 1e-8; d.top_up = False; d.change_years = None; d.service_life = None
r, f, t = three(s)
ry, fy = r["B1-02"]["by_year"], f["B1-02"]["by_year"]
print("  by_year[1..3] ref", ry[1:4], "full", fy[1:4], "rel[2] %.2e" % (abs(ry[2]-fy[2])/abs(ry[2]) if ry[2] else 0))
print("  B1-02 value", g(r, "B1-02"), g(f, "B1-02"), "study fails:", [(x[0], x[1], '%.2e' % x[2]) for x in study_fails(s)])

print("=== NUM-11 compare() ===")
for a, b_ in ((inf, 1.0), (inf, -inf), (-inf, 5.0), (1.0, inf), (5.0, -inf), (inf, inf)):
    c = compare({"value": a}, {"value": b_}, floor=1e-9); print(f"  ref={a} cand={b_}: within={c.within(1e-9)} max_abs={c.max_abs_rel_error} n_numeric={c.n_numeric}")
c = compare({"ok": True}, {"ok": 1}); print("  ref True vs cand 1:", c.within(1e-9), c.mismatches)
c = compare({"n": 1}, {"n": True}); print("  ref 1 vs cand True:", c.within(1e-9), c.mismatches)
c = compare({"a": 1.0}, {"a": 1.0, "b": 2.0}, ignore_missing=True); print("  extra key: within", c.within(1e-9), "extra", c.extra)
c = compare({"v": 3.629e-4}, {"v": 3.629e-4 * (1 + 1e-7)}, floor=0.105); print("  small leaf with floor 0.105, rel change 1e-7: within", c.within(1e-9), c.max_abs_rel_error)
# floor statistics on standard benchmark S and M
from common.compare import flatten
for scn in population.standard_benchmark()[:2]:
    r = registry.run_all(scn); scale = abs(r["SUM-03"]["value"]); fl = 1e-9 * scale
    n = below = 0
    for u, rv in r.items():
        for p, v in flatten(rv).items():
            if isinstance(v, (int, float)) and not isinstance(v, bool) and v != 0 and not math.isnan(v):
                n += 1; below += abs(v) < fl
    print(f"  size {scn.meta.size_class}: SUM-03 {scale:.4g} floor {fl:.3g}: nonzero numeric leaves {n}, below floor {below} ({100*below/n:.2f}%)")
    full = engine.evaluate(scn, detail=True); tot = engine.evaluate(scn, detail=False)
    # extras in totals mode vs reference
    extras = [u + ":" + e for u in r for e in compare(r[u], tot.get(u, {}), ignore_missing=True).extra]
    extra_units = [u for u in tot if u not in r and not u.startswith("_")]
    print("     extra leaves in totals mode:", len(extras), "extra units:", extra_units, "| extra in full:", sum(len(compare(r[u], full.get(u, {})).extra) for u in r))
