# Own checks of RED-10 .. RED-12
import copy, math, time
import synth
from synth import population, model
from refcalc import registry, base
from fastcalc import engine
from common.compare import compare
registry.load_all()
nan, inf = float("nan"), float("inf")
def mk(seed=11, st="RC", use="office", T=60.0, **o):
    opts = dict(n_materials=12, n_equipment=6, n_refrigerants=4); opts.update(o)
    return synth.make_scenario(seed, st, use, "S", T, **opts)
def both(s):
    out = []
    for fn in (registry.run_all, lambda x: engine.evaluate(x, detail=True)):
        try: out.append(fn(s))
        except Exception as e: out.append(e)
    return out
def desc(x):
    return f"RAISED {type(x).__name__}: {x}" if isinstance(x, Exception) else "ok"

print("== RED-10 ==")
s = mk(47, "S", "school")
r0, f0 = both(s)
print(" clean C-05", r0["C-05"]["ok"], r0["C-05"]["n_mass_unchecked"], "under", len(r0["C-05"]["under_allocated"]))
cases = [
 ("route fraction None", lambda x: setattr(x.materials[0].end_of_life.routes[1], "fraction", None)),
 ("route fraction NaN", lambda x: setattr(x.materials[0].end_of_life.routes[1], "fraction", nan)),
 ("eol mass -1", lambda x: setattr(x.materials[0].end_of_life, "mass_kg", -1.0)),
 ("eol mass NaN", lambda x: setattr(x.materials[0].end_of_life, "mass_kg", nan)),
 ("eol mass None", lambda x: setattr(x.materials[0].end_of_life, "mass_kg", None)),
 ("grid.construction_value None", lambda x: setattr(x.operation.grid, "construction_value", None)),
 ("grid TABLE with None entry", lambda x: (setattr(x.operation.grid, "kind", "TABLE"), x.operation.grid.table.__setitem__(3, None))),
 ("factor value None", lambda x: setattr(x.factors[next(m.factor_id for m in x.materials if m.factor_id and m.composition is None and m.epd is None)], "value", None)),
 ("summary concrete_m3 None", lambda x: setattr(x.summary_quantities, "concrete_m3", None)),
 ("summary timber_m3 None", lambda x: setattr(x.summary_quantities, "timber_m3", None)),
 ("use_area_breakdown value None", lambda x: x.project.use_area_breakdown.__setitem__(sorted(x.project.use_area_breakdown)[0], None)),
 ("equipment replacement_event_list [None]", lambda x: setattr(x.equipment[0], "replacement_event_list", [None])),
 ("composite mass_fraction None", None),
]
for label, fn in cases:
    if fn is None: continue
    s2 = copy.deepcopy(s); fn(s2); r, f = both(s2)
    extra = ""
    if not isinstance(r, Exception):
        extra = f" C-05 {r['C-05']['ok']} viol {r['C-05']['violations']} under {len(r['C-05']['under_allocated'])} unchecked {r['C-05']['n_mass_unchecked']} | C3 n_skipped {r['C3-01']['n_skipped']} n_routes_skipped {r['C3-01']['n_routes_skipped']} complete {r['SUM-03']['complete']}"
        if not isinstance(f, Exception):
            c = compare(r, f); extra += f" [ref~fast {c.within(1e-9)} {c.mismatches[:2]}]"
    print(f"   {label}: ref {desc(r)} | fast {desc(f)} |{extra}")
for kind in ("TABLE",):
    s2 = mk(47, "S", "school", profile_kind="TABLE")
    s2.operation.gas.table = s2.operation.gas.table[:30]
    r, f = both(s2); print(f"   gas TABLE profile cut to 30 (T=60): ref {desc(r)} | fast {desc(f)}")
    s2 = mk(47, "S", "school", profile_kind="TABLE")
    s2.operation.grid.table = s2.operation.grid.table[:30]
    r, f = both(s2); print(f"   grid table cut to 30 (T=60): ref {desc(r)} | fast {desc(f)}")
    s2 = mk(47, "S", "school", profile_kind="CONSTANT")
    s2.operation.gas.table = s2.operation.gas.table[:30]
    r, f = both(s2); print(f"   gas CONSTANT profile, copy table cut to 30: ref {desc(r)} | fast {desc(f)}", "" if isinstance(r, Exception) else r["B6-02"]["descriptors_match_tables"])

print("\n== RED-11 ==")
e = synth.make_scenario(22, "RC", "office", "S", 60.0, n_materials=8, n_equipment=4, n_refrigerants=2, epd_share=1.0, epd_inapplicable_share=0.0, composite_share=0.0)
r0 = registry.run_all(e)
e2 = copy.deepcopy(e)
e2.factors[e2.materials[0].epd.factor_id].unit = "piece"; e2.materials[0].epd.declared_unit = "piece"
e2.factors[e2.materials[1].epd.factor_id].stages = ["A1-A3", "A4"]; e2.materials[1].epd.declared_stages = ["A1-A3", "A4"]
r = registry.run_all(e2)
print(f" (1) EPD unusable on rows 0,1: X-15 kind {r0['X-15']['kind'][:3]}->{r['X-15']['kind'][:3]} n_epd_declined {r['X-15']['n_epd_declined']} SYS-02 {r['SYS-02']['ok']} {r['SYS-02']['violations']} {r['SYS-02']['stage_mismatches']} SYS-03 {r['SYS-03']['ok']} complete {r['SUM-03']['complete']} A1-A3 {r0['X-02']['by_stage']['A1-A3']:.2f}->{r['X-02']['by_stage']['A1-A3']:.2f} n_skipped A13-01 {r['A13-01']['n_skipped']}")
e3 = copy.deepcopy(e); e3.factors[e3.materials[0].epd.factor_id].licence_status = "RESTRICTED"
r = registry.run_all(e3)
print(f"     EPD factor unlicensed: SYS-03 {r['SYS-03']['ok']} {r['SYS-03']['violations']} SYS-02 {r['SYS-02']['ok']} n_epd_declined {r['X-15']['n_epd_declined']} complete {r['SUM-03']['complete']}")
e4 = copy.deepcopy(e); e4.equipment[0].eol_factor_id = None
r = registry.run_all(e4)
print(f" (2) equipment[0].eol_factor_id None: SYS-03 {r['SYS-03']['ok']} {r['SYS-03']['violations']} SYS-02 {r['SYS-02']['ok']} X-14 n_skipped {r['X-14']['n_skipped']} complete {r['SUM-03']['complete']} {r['X-02']['incomplete_units']}")
n_none = n_all = 0
for sc in population.standard_benchmark():
    for q in sc.equipment: n_all += 1; n_none += q.eol_factor_id is None
print("     clean benchmark equipment rows with eol_factor_id None:", n_none, "of", n_all)
e5 = copy.deepcopy(e); rt = e5.materials[0].end_of_life.routes
k = next(j for j, x in enumerate(rt) if x.route != "LANDFILL"); k2 = next(j for j in range(len(rt)) if j != k)
rt[k2].fraction += rt[k].fraction; rt[k].fraction = 0.0; rt[k].factor_id = None
r = registry.run_all(e5)
print(f" (3) zero-fraction route without factor: C3 n_routes_skipped {r['C3-01']['n_routes_skipped']} C4 {r['C4-01']['n_routes_skipped']} complete {r['SUM-03']['complete']} {r['X-02']['incomplete_units']} SYS-03 {r['SYS-03']['violations']}")
e6 = synth.make_scenario(21, "RC", "office", "S", 60.0, n_materials=6, n_equipment=4, n_refrigerants=2, explicit_event_share=1.0)
ea = copy.deepcopy(e6); ea.equipment[0].replacement_event_list = [15]
eb = copy.deepcopy(e6); eb.equipment[0].replacement_event_list = [15, 15, 15]
ra, rb = registry.run_all(ea), registry.run_all(eb)
print(f" (4) [15] -> {ra['B4-02']['by_item_equipment'][0]:.3f}; [15,15,15] -> {rb['B4-02']['by_item_equipment'][0]:.3f}; B4-01 events {rb['B4-01']['events'][0]} QA-02 {rb['QA-02']}")

print("\n== RED-12 ==")
t = mk(11, included_stages=["A1-A3", "B6"])
r = registry.run_all(t)
print(f" (1) included {sorted(t.boundary.included_lifecycle_stages)}: by_stage keys {list(r['X-02']['by_stage'])} by_stage_all keys {len(r['X-02']['by_stage_all'])}; B6 by_stage {r['X-02']['by_stage']['B6']:.2f} by_stage_all {r['X-02']['by_stage_all']['B6']:.2f} diff {r['X-02']['by_stage']['B6']-r['X-02']['by_stage_all']['B6']:.2f} B2-01 {r['B2-01']['value']:.2f}; X-05.by_stage_co2 keys {len(r['X-05']['by_stage_co2'])}")
t2 = mk(11); t2.operation.grid.licence_status = "UNKNOWN"
r = registry.run_all(t2)
print(f" (2) grid licence UNKNOWN: B6-01 computed {r['B6-01']['computed']} B2-01 {r['B2-01']} incomplete_units {r['X-02']['incomplete_units']}")
t3 = mk(11); t3.boundary.study_period = 0.0
try: registry.run_all(t3, ids=["SUM-05"]); print(" (4) no error")
except Exception as ex: print(" (4) T=0 ->", type(ex).__name__, ex)
S = population.standard_benchmark()[0]
rs = registry.run_all(S, ids=["X-17"])
S2 = copy.deepcopy(S); S2.summary_quantities.concrete_m3 = 0.0
r2 = registry.run_all(S2, ids=["X-17"]); f2 = engine.evaluate(S2)
a, b = rs["A13-01"]["by_item"], rs["A13-03"]["by_item"]
from refcalc.units_pre_a import simple_class
resum = sum(a[i] + b[i] for i, m in enumerate(S.materials) if simple_class(m) is not None)
print(f" (5) X-17 clean {rs['X-17']['value']:.2f} (re-aggregated manufacturing of the 6 classes {resum:.2f}); concrete_m3=0 -> ref {r2['X-17']['value']:.2f} fast {f2['X-17']['value']:.2f}; CONCRETE {r2['X-17']['by_class']['CONCRETE']}")
t4 = mk(11); t4.materials[0].reuse_rate = 1.5
r = registry.run_all(t4, ids=["X-13"]); print(" (6) X-13 keys", sorted(r["X-13"]), "by_item[0]", r["X-13"]["by_item"][0])
t5 = synth.make_scenario(23, "RC", "office", "S", 60.0, n_materials=1, n_equipment=1, n_refrigerants=1); t5.materials[0].refresh_cycle = 1e-4
t0 = time.time(); r = registry.run_all(t5, ids=["B4-03"]); print(" (7) refresh_cycle 1e-4:", r["B4-03"]["by_item"], f"{time.time()-t0:.2f}s")
