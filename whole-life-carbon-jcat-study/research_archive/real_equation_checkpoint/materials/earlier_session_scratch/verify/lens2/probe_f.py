import sys, os, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
OPT = {"generic_stage_check": True}
s0 = base(composite_share=0.0, epd_share=0.0)
ref0 = registry.run_all(s0)

def run(label, mut, units=None, opts=None, extra=None, src=None):
    s = copy.deepcopy(src or s0); mut(s)
    o = dict(OPT); o.update(opts or {})
    ref, me, bad = diff(s, opts=o, label=label, show=False, units=units)
    print(f"[{label}] diff={bad}")
    if extra and ref is not None and me is not None:
        extra(s, ref, me)
    return s, ref, me

# clean unit probe on a route with fraction 1.0
r0 = s0.materials[0]
fid = [x.factor_id for x in r0.end_of_life.routes if x.route == "PROCESSING"][0]
for unit in ("t", "m3"):
    s = copy.deepcopy(s0); s.factors[fid].unit = unit
    r = registry.run_all(s)
    print(f"C3 PROCESSING factor {fid} unit kg->{unit}: C3-01 value base {ref0['C3-01']['value']} ref {r['C3-01']['value']} row0 {r['C3-01']['by_item'][0]} n_skipped {r['C3-01']['n_skipped']} SYS-02 {r['SYS-02']['ok']} SYS-03 {r['SYS-03'].get('ok')}")
s = copy.deepcopy(s0); s.factors[fid].licence_status = "RESTRICTED"
r = registry.run_all(s)
print(f"C3 PROCESSING factor unlicensed: C3-01 value base {ref0['C3-01']['value']} ref {r['C3-01']['value']} row0 {r['C3-01']['by_item'][0]} n_skipped {r['C3-01']['n_skipped']} SYS-03 ok {r['SYS-03'].get('ok')}; QA-01 {r['QA-01'].get('ok')}")
print("   C3-01 keys", list(r["C3-01"].keys()))
fidh = r0.end_of_life.haul_factor_id
s = copy.deepcopy(s0); s.factors[fidh].licence_status = "RESTRICTED"
r = registry.run_all(s)
print(f"C2 haul factor unlicensed: C2-01 value base {ref0['C2-01']['value']} ref {r['C2-01']['value']} n_skipped {r['C2-01']['n_skipped']}")

# ---------------- X-06
g = s0.operation.grid
print("grid", g.kind, g.unit, g.start, g.annual_decline, g.floor, g.steps, g.table[:3], g.construction_value, g.licence_status)
def grid(**kw):
    def f(s):
        for k, v in kw.items():
            setattr(s.operation.grid, k, v)
    return f
def x6(s, r, m):
    print("   ref X-06", r["X-06"]["by_year"][:5], r["X-06"]["matches_table"], "| mine", m["X-06"]["by_year"][:5], m["X-06"]["matches_table"], "| B6-01", r["B6-01"]["by_year"][:3] if r["B6-01"]["by_year"] else r["B6-01"])
U6 = ["X-06", "B6-04", "B6-01", "B6-02", "B6-03", "B2-01", "X-02", "SUM-03", "SUM-07"]
run("STEPWISE first step from_index 2", grid(kind="STEPWISE", steps=[model.GridStep(2, 0.3), model.GridStep(5, 0.2)]), units=U6, extra=x6)
run("STEPWISE unsorted steps", grid(kind="STEPWISE", steps=[model.GridStep(5, 0.2), model.GridStep(0, 0.4), model.GridStep(2, 0.3)]), units=U6, extra=x6)
run("STEPWISE duplicate from_index", grid(kind="STEPWISE", steps=[model.GridStep(0, 0.4), model.GridStep(0, 0.1)]), units=U6, extra=x6)
run("CONSTANT but table differs (descriptor vs table)", grid(kind="CONSTANT", start=0.9), units=U6, extra=x6)
run("LINEAR floor > start", grid(kind="LINEAR_DECLINE_TO_FLOOR", start=0.4, floor=0.5, annual_decline=0.01), units=U6, extra=x6)
run("kind unknown 'FOO'", grid(kind="FOO"), units=U6, extra=x6)
run("grid unit 'kgCO2e/MWh'", grid(unit="kgCO2e/MWh"), units=U6, extra=x6)
run("grid unit 'tCO2e/kWh'", grid(unit="tCO2e/kWh"), units=U6, extra=x6)
def b6(s, r, m):
    print("   ref B6-01", {k: (v[:3] if isinstance(v, list) else v) for k, v in r["B6-01"].items()}, "B6-03", r["B6-03"]["value"], "B2-01", r["B2-01"], "X-02 B2,B6", r["X-02"]["by_stage_all"]["B2"], r["X-02"]["by_stage_all"]["B6"])
    print("   mine B6-03", m["B6-03"]["value"], "B2-01", m["B2-01"], "B2,B6", m["X-02"]["by_stage_all"]["B2"], m["X-02"]["by_stage_all"]["B6"])
run("grid licence UNKNOWN", grid(licence_status="UNKNOWN"), units=U6, extra=b6)
# ---------------- profiles units
op = s0.operation
print("profiles:", [(n, p.kind, p.unit) for n, p in model.annual_profiles(s0)], "factors", [(f, s0.factors[f].unit) for f in (op.gas_factor_id, op.oil_factor_id, op.district_heat_factor_id)])
def prof(name, **kw):
    def f(s):
        p = getattr(s.operation, name)
        for k, v in kw.items():
            setattr(p, k, v)
    return f
def b62(s, r, m):
    print("   ref B6-02 y1", r["B6-02"]["by_year"][1], "n_skipped", r["B6-02"]["n_skipped"], "| mine", m["B6-02"]["by_year"][1], m["B6-02"]["n_skipped"], "| base", ref0["B6-02"]["by_year"][1], "| B6-01 y1 ref", r["B6-01"]["by_year"][1], "base", ref0["B6-01"]["by_year"][1])
run("gas unit 'L/year' (L->m3 exists)", prof("gas", unit="L/year"), units=U6, extra=b62)
run("gas unit 'm3' (no /year)", prof("gas", unit="m3"), units=U6, extra=b62)
run("gas unit 'm3/month'", prof("gas", unit="m3/month"), units=U6, extra=b62)
run("gas unit 'kg/year' (no conversion)", prof("gas", unit="kg/year"), units=U6, extra=b62)
run("district heat unit 'kWh/year' (kWh->MJ exists)", prof("district_heat", unit="kWh/year"), units=U6, extra=b62)
run("district heat unit 'GJ/year'", prof("district_heat", unit="GJ/year"), units=U6, extra=b62)
run("electricity unit 'MWh/year'", prof("electricity", unit="MWh/year"), units=U6, extra=b62)
run("generation unit 'MWh/year'", prof("onsite_generation", unit="MWh/year"), units=U6, extra=b62)
run("gas factor unlicensed", lambda s: s.factors[s.operation.gas_factor_id].__setattr__("licence_status", "UNKNOWN"), units=U6, extra=b62)
run("gas factor id None", lambda s: s.operation.__setattr__("gas_factor_id", None), units=U6, extra=b62)
run("gas factor stages ['A1-A3']", lambda s: s.factors[s.operation.gas_factor_id].__setattr__("stages", ["A1-A3"]), units=U6, extra=b62)
# ---------------- B6-04 edge
def tab(name, vals):
    def f(s):
        p = getattr(s.operation, name)
        p.kind, p.base, p.slope = "TABLE", None, None
        p.table = [vals] * len(p.table)
    return f
def chain(*fs):
    def f(s):
        for x in fs:
            x(s)
    return f
def b64(s, r, m):
    print("   ref B6-04 y1", r["B6-04"]["by_year"][1], "mine", m["B6-04"]["by_year"][1])
run("export > generation (c=100,g=50,x=80)", chain(tab("electricity", 100.0), tab("onsite_generation", 50.0), tab("onsite_export", 80.0)), units=U6, extra=b64)
run("generation >> consumption (c=100,g=500,x=0)", chain(tab("electricity", 100.0), tab("onsite_generation", 500.0), tab("onsite_export", 0.0)), units=U6, extra=b64)
run("descriptor/table mismatch: CONSTANT base=1 but table=100", lambda s: (tab("electricity", 100.0)(s), s.operation.electricity.__setattr__("kind", "CONSTANT"), s.operation.electricity.__setattr__("base", 1.0)), units=U6, extra=b64)
# ---------------- B2 ratio
def b2(s, r, m):
    print("   ref B2", r["B2-01"]["value"], "X-02 B2/B6", r["X-02"]["by_stage_all"]["B2"], r["X-02"]["by_stage_all"]["B6"], "SUM-07", r["SUM-07"]["defined"], "SUM-03", r["SUM-03"]["value"])
run("facility ratio 1.5", lambda s: s.operation.__setattr__("facility_management_ratio", 1.5), units=U6, extra=b2)
run("facility ratio 5 (B6 negative)", lambda s: s.operation.__setattr__("facility_management_ratio", 5.0), units=U6, extra=b2)
run("facility ratio -0.5", lambda s: s.operation.__setattr__("facility_management_ratio", -0.5), units=U6, extra=b2)
