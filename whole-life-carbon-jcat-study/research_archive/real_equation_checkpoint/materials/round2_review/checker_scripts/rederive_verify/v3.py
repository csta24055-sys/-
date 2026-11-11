# Own checks of RED-4 .. RED-9
import copy, math
import synth
from synth import population, model
from refcalc import registry, base
from fastcalc import engine
from common.compare import compare
registry.load_all()
nan = float("nan")
def mk(seed=11, st="RC", use="office", T=60.0, **o):
    opts = dict(n_materials=12, n_equipment=6, n_refrigerants=4); opts.update(o)
    return synth.make_scenario(seed, st, use, "S", T, **opts)
def agree(s, r=None):
    r = r or registry.run_all(s); f = engine.evaluate(s, detail=True); c = compare(r, f)
    return f"[ref~fast {c.within(1e-9)} {c.mismatches[:2]}]"

print("== RED-4 X-04 ==")
for seed, st, use in ((11, "RC", "office"), (58, "SRC", "retail")):
    s = mk(seed, st, use)
    r0 = registry.run_all(s)
    tot0 = sum(r0["X-02"]["by_stage_all"].values())
    print(f" seed {seed}: clean X-04 {r0['X-04']['value']:.4f} sum14 {tot0:.4f} rel {(r0['X-04']['value']-tot0)/tot0:.2e}; X-04 public keys {[k for k in r0['X-04'] if not k.startswith('_')]}")
    # the factor with the largest generic A13-01 contribution
    i = max(range(len(s.materials)), key=lambda i: r0["A13-01"]["by_item"][i] if s.materials[i].composition is None else -1)
    fid = s.materials[i].factor_id
    for mult in (3.0, 0.0):
        s2 = copy.deepcopy(s); s2.factors[fid].gas_amounts["CO2"] *= mult
        r = registry.run_all(s2); tot = sum(r["X-02"]["by_stage_all"].values())
        flags = {u: r[u].get("ok") for u in ("QA-01", "QA-03", "SYS-01", "SYS-02", "SYS-03", "C-05")}
        print(f"   {fid} CO2 x{mult}: X-04 {r['X-04']['value']:.2f} sum14 {tot:.2f} rel {(r['X-04']['value']-tot)/tot:+.4%} gates {flags} X-05 {r0['X-05']['value']:.2f}->{r['X-05']['value']:.2f} SUM-03 {r['SUM-03']['value']:.2f} complete {r['SUM-03']['complete']} {agree(s2, r)}")

print("\n== RED-5 SUM-08 ==")
for seed, kw in ((22, dict(n_materials=8, n_equipment=4, n_refrigerants=2)), (91, {})):
    e = mk(seed, **kw)
    p = copy.deepcopy(e); b = population.attach_baseline(p)
    ok = registry.run_all(p)["SUM-08"]
    rb = registry.run_all(b)
    order = sorted(range(len(b.materials)), key=lambda i: -(rb["A13-01"]["by_item"][i] + rb["A13-03"]["by_item"][i]))
    print(f" seed {seed} clean: {ok}")
    for i in order[:4]: b.materials[i].quantity = None
    r = registry.run_all(p); f = engine.evaluate(p)
    print(f"   baseline 4 rows None: ref {r['SUM-08']} | proposal complete {r['SUM-03']['complete']} baseline complete {registry.run_all(b)['SUM-03']['complete']} | fast {f['SUM-08']}")
    print(f"   SUM-08 keys {sorted(r['SUM-08'])}")
    p2 = copy.deepcopy(e); b2 = population.attach_baseline(p2)
    for i in order[:4]: p2.materials[i].quantity = None
    r = registry.run_all(p2)
    print(f"   proposal 4 rows None: {r['SUM-08']} proposal complete {r['SUM-03']['complete']}")
    p3 = copy.deepcopy(e); p3.boundary.baseline_scenario = "NO-SUCH-SCENARIO"
    p4 = copy.deepcopy(e); p4.boundary.baseline_scenario = None
    print(f"   unknown id: {registry.run_all(p3)['SUM-08']} | no id: {registry.run_all(p4)['SUM-08']}")

print("\n== RED-6 SYS-01 coverage (one field at a time) ==")
s = mk(11, replacement_cycle=25.0, reconstruction_scenario="REBUILD_IDENTICAL")
r0 = registry.run_all(s)
print(" clean SYS-01", r0["SYS-01"]["ok"], r0["SYS-01"]["counts"])
cases = [
 ("operation.facility_management_ratio=None", lambda x: setattr(x.operation, "facility_management_ratio", None)),
 ("boundary.reconstruction_scope_fraction=None", lambda x: setattr(x.boundary, "reconstruction_scope_fraction", None)),
 ("boundary.replacement_cycle=None", lambda x: setattr(x.boundary, "replacement_cycle", None)),
 ("materials[0].unquantified_cost_ratio=None", lambda x: setattr(x.materials[0], "unquantified_cost_ratio", None)),
 ("materials[2].transport.load_factor=None", lambda x: setattr(x.materials[2].transport, "load_factor", None)),
 ("materials[2].end_of_life.haul_distance_km=None", lambda x: setattr(x.materials[2].end_of_life, "haul_distance_km", None)),
 ("materials[2].end_of_life.routes[0].fraction=NaN", lambda x: setattr(x.materials[2].end_of_life.routes[0], "fraction", nan)),
 ("cost_items[0].amount=None", lambda x: setattr(x.cost_items[0], "amount", None)),
 ("summary_quantities.timber_m3=None", lambda x: setattr(x.summary_quantities, "timber_m3", None)),
 ("operation.electricity_per_m2_per_year=None", lambda x: setattr(x.operation, "electricity_per_m2_per_year", None)),
 ("materials[1].quantity=NaN", lambda x: setattr(x.materials[1], "quantity", nan)),
 ("materials[1].quantity=None (control)", lambda x: setattr(x.materials[1], "quantity", None)),
]
for label, fn in cases:
    s2 = copy.deepcopy(s)
    try:
        fn(s2); r = registry.run_all(s2)
    except Exception as ex:
        print(f"   {label}: RAISED {type(ex).__name__} {ex}"); continue
    delta = {k: r["SYS-01"]["counts"][k] - r0["SYS-01"]["counts"][k] for k in r0["SYS-01"]["counts"] if r["SYS-01"]["counts"][k] != r0["SYS-01"]["counts"][k]}
    eff = {u: {k: v for k, v in r[u].items() if k in ("computed", "n_skipped", "n_routes_skipped", "value") and r[u].get(k) != r0[u].get(k) and not isinstance(v, list)} for u in ("B2-01", "B5-01", "A13-05", "A13-04", "X-12", "X-16", "C2-01", "C3-01", "STO-01", "X-11")}
    eff = {u: v for u, v in eff.items() if v}
    print(f"   {label}: SYS-01 ok {r['SYS-01']['ok']} viol {r['SYS-01']['violations']} count-delta {delta} | complete {r['SUM-03']['complete']} {r['X-02']['incomplete_units']} | changed {eff}")

print("\n== RED-7/8/9 on standard benchmark S ==")
S = population.standard_benchmark()[0]
r = registry.run_all(S)
bs = r["X-02"]["by_stage"]
print(" stages", {k: round(v, 2) for k, v in bs.items()}, "SUM-01", round(r["SUM-01"]["value"], 2), "SUM-03", round(r["SUM-03"]["value"], 2))
print(f" A13-04 {r['A13-04']['value']:.2f} = {r['A13-04']['value']/bs['A1-A3']:.4%} of A1-A3")
# RED-7: re-run B4-02 and B3-01 with the uplift added to the row manufacturing result
res2 = dict(r)
a2 = dict(r["A13-01"]); a2["by_item"] = [x + u for x, u in zip(r["A13-01"]["by_item"], r["A13-04"]["by_item"])]
a2["_row_lines"] = [l + u for l, u in zip(r["A13-01"]["_row_lines"], r["A13-04"]["_row_lines"])]
res2["A13-01"] = a2
b4u = registry.UNITS["B4-02"].fn(S, res2)["value"]; b3u = registry.UNITS["B3-01"].fn(S, res2)["value"]
print(f" RED-7: B4 code {bs['B4']:.2f} with uplift {b4u:.2f} ({(b4u-bs['B4'])/bs['B4']:+.4%} of B4, {(b4u-bs['B4'])/r['SUM-03']['value']:+.4%} of SUM-03); B3 code {bs['B3']:.2f} with uplift {b3u:.2f} ({(b3u-bs['B3'])/bs['B3']:+.4%})")
base5 = sum(r[u]["value"] for u in ("A13-01", "A13-03", "A13-04", "X-01", "A4-01", "A4-02", "A5-04", "C1-01", "C2-01", "C3-01", "C4-01", "X-14"))
print("   B5 base contains A13-04:", "A13-04" in registry.UNITS["B5-01"].depends_on, "| B4-02 deps contain A13-04:", "A13-04" in registry.UNITS["B4-02"].depends_on, "| B3-01:", "A13-04" in registry.UNITS["B3-01"].depends_on)
# RED-8: initial installation of material rows
n_fac = sum(1 for m in S.materials if m.installation_factor_id is not None)
tot_inst = 0.0; n_ok = 0
for i, m in enumerate(S.materials):
    if m.installation_factor_id is None: continue
    rec = S.factors[m.installation_factor_id]
    conv = model.conversion_factor(S.unit_conversions, m.quantity_unit, rec.unit, m.conversions)
    q = r["A13-05"]["q_ord"][i]
    if conv is None or q is None or rec.stages != ["A5"]: continue
    tot_inst += q * conv * rec.value; n_ok += 1
print(f" RED-8: material rows with installation factor {n_fac}/{len(S.materials)} (usable {n_ok}); initial installation {tot_inst:.2f} = {tot_inst/bs['A5']:.3%} of A5 ({bs['A5']:.0f}), {tot_inst/r['SUM-01']['value']:.3%} of SUM-01, {tot_inst/r['SUM-03']['value']:.4%} of SUM-03")
S2 = copy.deepcopy(S)
for m in S2.materials: m.installation_factor_id = None
r2 = registry.run_all(S2, ids=["X-02"])
d = bs["B4"] - r2["X-02"]["by_stage"]["B4"]
print(f"   removing all material installation factors: A5 {bs['A5']:.2f}->{r2['X-02']['by_stage']['A5']:.2f} (unchanged => not in A5), B4 falls by {d:.2f} = {d/bs['B4']:.3%} of B4")
# B-11 equipment figures
dl = ins = 0.0
for eq in S.equipment:
    for fid, tag in ((eq.delivery_factor_id, "d"), (eq.installation_factor_id, "i")):
        if fid is None: continue
        rec = S.factors[fid]; conv = model.conversion_factor(S.unit_conversions, eq.quantity_unit, rec.unit, ())
        if conv is None: continue
        if tag == "d": dl += eq.quantity * conv * rec.value
        else: ins += eq.quantity * conv * rec.value
print(f"   B-11 equipment: delivery {dl:.2f} = {dl/bs['A4']:.3%} of A4; installation {ins:.2f} = {ins/bs['A5']:.3%} of A5; material/equipment installation ratio {tot_inst/ins:.2f}")
# RED-9 (1): equipment delivery+installation inside B4
S3 = copy.deepcopy(S)
for eq in S3.equipment: eq.delivery_factor_id = None; eq.installation_factor_id = None
r3 = registry.run_all(S3, ids=["X-02"])
d = bs["B4"] - r3["X-02"]["by_stage"]["B4"]
print(f" RED-9(1): equipment delivery+installation inside B4 = {d:.2f} = {d/bs['B4']:.4%} of B4, {d/r['SUM-03']['value']:.4%} of SUM-03")
# RED-9 (2): B1-02 without GWP
S4 = copy.deepcopy(S)
for dev in S4.refrigerants: dev.gwp = 1.0
print(f" RED-9(2): B1-02 code {r['B1-02']['value']:.2f} kgCO2e; with GWP=1 (mass reading) {registry.run_all(S4, ids=['B1-02'])['B1-02']['value']:.2f} kg")
