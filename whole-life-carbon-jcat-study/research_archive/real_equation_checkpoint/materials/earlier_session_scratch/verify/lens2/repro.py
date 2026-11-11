"""Self-contained reproduction of the lens-2 findings (reference results only; no repo file is modified)."""
import copy, math
from refcalc import registry
from synth import population, model
from synth.generate import make_scenario
registry.load_all()
run = registry.run_all

def small(period=60.0, **o):
    opts = dict(n_materials=12, n_equipment=6, n_refrigerants=4, composite_share=0.0, epd_share=0.0); opts.update(o)
    return make_scenario(7, "RC", "office", "S", period, scenario_id="PROBE", **opts)

print("F1  C3-01 / C4-01: unusable route factor is dropped but n_skipped stays 0")
s = make_scenario(903, "W", "hospital", "S", 60.0, dirty=True); r = run(s)
bad = [i for i, row in enumerate(s.materials) if any(rt.route != "LANDFILL" and rt.fraction > 0 and s.factors[rt.factor_id].licence_status != "PERMITTED_PUBLIC" for rt in row.end_of_life.routes)]
lost = sum(row.end_of_life.mass_kg * rt.fraction * s.factors[rt.factor_id].value for row in s.materials for rt in row.end_of_life.routes if rt.route != "LANDFILL" and s.factors[rt.factor_id].licence_status != "PERMITTED_PUBLIC")
print(f"    dirty seed 903: {len(bad)} rows have a non-licensed C3 route with fraction>0; C3-01 n_skipped={r['C3-01']['n_skipped']}; value={r['C3-01']['value']:.2f}; dropped route emission={lost:.2f}; C2-01 n_skipped={r['C2-01']['n_skipped']} X-14 n_skipped={r['X-14']['n_skipped']}")
s = make_scenario(913, "RC", "residential", "S", 50.0, dirty=True); r = run(s)
bad = [i for i, row in enumerate(s.materials) if any(rt.route == "LANDFILL" and s.factors[rt.factor_id].licence_status != "PERMITTED_PUBLIC" for rt in row.end_of_life.routes)]
print(f"    dirty seed 913: {len(bad)} rows have a non-licensed LANDFILL factor; C4-01 by_item of those rows={set(r['C4-01']['by_item'][i] for i in bad)}; C4-01 n_skipped={r['C4-01']['n_skipped']}")

print("F2  B6 = B6-03 - B2-01 even when B2 is outside the boundary")
s = dict(population.edge_cases())["stage_subset"]; r = run(s)
print(f"    edge 'stage_subset' included={s.boundary.included_lifecycle_stages}: by_stage B6={r['X-02']['by_stage']['B6']:.1f}  B6-03={r['B6-03']['value']:.1f}  B2-01={r['B2-01']['value']:.1f}  -> {100*r['B2-01']['value']/r['B6-03']['value']:.2f}% of operational-energy emission is in no reported stage; SUM-03={r['SUM-03']['value']:.1f}")

print("F3  factor units are not looked at in A4-01, C2-01, C3-01, C4-01, X-14 and B6-01; SYS-02 stays ok")
s0 = small(); r0 = run(s0)
def mut(label, f, pick):
    s = copy.deepcopy(s0); f(s); r = run(s)
    print(f"    {label}: before={pick(r0):.4f} after={pick(r):.4f} SYS-02 ok={r['SYS-02']['ok']}")
row0, e0 = s0.materials[0], s0.equipment[0]
proc = [x.factor_id for x in row0.end_of_life.routes if x.route == "PROCESSING"][0]
mut("X-14 eol factor unit kg -> t", lambda s: setattr(s.factors[e0.eol_factor_id], "unit", "t"), lambda r: r["X-14"]["value"])
mut("C3-01 route factor unit kg -> t", lambda s: setattr(s.factors[proc], "unit", "t"), lambda r: r["C3-01"]["value"])
mut("C2-01 haul factor unit tkm -> kgkm", lambda s: setattr(s.factors[row0.end_of_life.haul_factor_id], "unit", "kgkm"), lambda r: r["C2-01"]["value"])
mut("A4-01 transport factor unit tkm -> t", lambda s: setattr(s.factors[row0.transport.factor_id], "unit", "t"), lambda r: r["A4-01"]["value"])
mut("B6: electricity MWh/year, grid kgCO2e/MJ", lambda s: (setattr(s.operation.electricity, "unit", "MWh/year"), setattr(s.operation.grid, "unit", "kgCO2e/MJ")), lambda r: r["B6-03"]["value"])
mut("(contrast) X-01 equipment factor unit -> 'dozen' (no conversion)", lambda s: setattr(s.factors[e0.factor_id], "unit", "dozen"), lambda r: r["X-01"]["value"])

print("F4  an event mathematically exactly at T is counted when T and the period are decimals")
s = small(period=99.9)
s.equipment[0].replacement_event_list = None; s.equipment[0].service_life = 33.3; s.materials[1].refresh_cycle = 33.3
s.boundary.reconstruction_scenario, s.boundary.replacement_cycle, s.boundary.reconstruction_scope_fraction = "REBUILD_IDENTICAL", 33.3, 1.0
r = run(s)
print(f"    T=99.9, period 33.3: B4-01 events={r['B4-01']['events'][0]} B4-03 count={r['B4-03']['by_item'][1]} B5-01 n_events={r['B5-01']['n_events']} (B5 per event {r['B5-01']['value']/r['B5-01']['n_events']:.1f}, SUM-03 {r['SUM-03']['value']:.1f})")
s = small(period=60.0)
s.equipment[0].replacement_event_list = None; s.equipment[0].service_life = 20.0; s.materials[1].refresh_cycle = 20.0
s.boundary.reconstruction_scenario, s.boundary.replacement_cycle, s.boundary.reconstruction_scope_fraction = "REBUILD_IDENTICAL", 20.0, 1.0
r = run(s)
print(f"    T=60,   period 20  : B4-01 events={r['B4-01']['events'][0]} B4-03 count={r['B4-03']['by_item'][1]} B5-01 n_events={r['B5-01']['n_events']}")
s = small(period=55.5); s.equipment[0].replacement_event_list = None; s.equipment[0].service_life = 2.2
r = run(s); ev = r["B4-01"]["events"][0]
print(f"    T=55.5, life 2.2: 25th event tau={ev[24]!r} -> year {math.ceil(ev[24])} (exact arithmetic: 55.0 -> year 55)")

print("F5  B6-02 unit suffix")
for u in ("m3/year", "m3", "m3/month", "L/year", "kg/year"):
    s = copy.deepcopy(s0); s.operation.gas.unit = u; r = run(s)
    print(f"    gas profile unit {u!r:11s}: B6-02 year1={r['B6-02']['by_year'][1]:.2f} n_skipped={r['B6-02']['n_skipped']}")

print("F6  X-15: unstated rules")
fid = s0.materials[0].factor_id
s = copy.deepcopy(s0); s.factors[fid].stages = ["A1-A3", "A4"]; r = run(s)
print(f"    generic factor with stages ['A1-A3','A4']: kind={r['X-15']['kind'][0]} A13-01 n_skipped={r['A13-01']['n_skipped']}")
se = small(epd_share=1.0, epd_inapplicable_share=0.0)
i = next(k for k, row in enumerate(se.materials) if row.epd is not None)
for label, f in (("declaration expired 2000-01-01, record valid", lambda s: setattr(s.materials[i].epd, "valid_until", "2000-01-01")),
                 ("declaration stages ['A1-A3','A4'], record ['A1-A3']", lambda s: setattr(s.materials[i].epd, "declared_stages", ["A1-A3", "A4"])),
                 ("declaration unit 'zzz', record unit ok", lambda s: setattr(s.materials[i].epd, "declared_unit", "zzz")),
                 ("record expired, declaration valid", lambda s: setattr(s.factors[s.materials[i].epd.factor_id], "valid_until", "2000-01-01"))):
    s = copy.deepcopy(se); f(s); r = run(s)
    print(f"    EPD {label}: kind={r['X-15']['kind'][i]}")

print("F7  A13-05: negative quantity is computed")
s = copy.deepcopy(s0); s.materials[1].quantity = -5.0; r = run(s)
print(f"    Q=-5: q_ord={r['A13-05']['q_ord'][1]} n_skipped={r['A13-05']['n_skipped']} A13-01 row={r['A13-01']['by_item'][1]:.2f}")

print("F8  time boundary between units / X-06")
s = copy.deepcopy(s0); s.equipment[0].replacement_event_list = [0, 30]; r = run(s)
print(f"    explicit event list [0, 30]: QA-02={r['QA-02']} B4-01 events={r['B4-01']['events'][0]}")
s = copy.deepcopy(s0); g = s.operation.grid; g.kind, g.steps = "STEPWISE", [model.GridStep(2, 0.3)]
try:
    run(s); print("    STEPWISE first step at index 2: ok")
except Exception as exc:
    print(f"    STEPWISE first step at index 2: reference raises {type(exc).__name__}: {exc}")

print("F9  partial renewal emission without any flag")
s = copy.deepcopy(s0); s.factors[e0.factor_id].licence_status = "UNKNOWN"; r = run(s)
print(f"    equipment[0] manufacturing factor not licensed: X-01 n_skipped={r['X-01']['n_skipped']}; B4-02 equipment[0] {r0['B4-02']['by_item_equipment'][0]:.2f} -> {r['B4-02']['by_item_equipment'][0]:.2f}; B4-02 keys={[k for k in r['B4-02'] if not k.startswith('_')]}")
print("    result keys without n_skipped:", {u: [k for k in r[u] if not k.startswith('_')] for u in ("B1-02", "B1-03", "B1-04", "B3-01", "B3-02", "B4-02", "B5-01")})
s = copy.deepcopy(s0); s.operation.grid.licence_status = "UNKNOWN"; r = run(s)
print(f"    grid scenario not licensed: B6-01 computed={r['B6-01']['computed']} by_year[1]={r['B6-01']['by_year'][1]} B2-01={r['B2-01']['value']} B6-03 {r0['B6-03']['value']:.1f} -> {r['B6-03']['value']:.1f}; SUM-03 {r0['SUM-03']['value']:.1f} -> {r['SUM-03']['value']:.1f}")

print("F10 C-05 bound is the ordered mass")
k = 0; row = s0.materials[k]
o, ins = r0["A13-05"]["q_ord"][k], r0["A13-05"]["q_inst"][k]
s = copy.deepcopy(s0); s.materials[k].end_of_life.mass_kg = 0.5 * (o + ins); r = run(s)
print(f"    row {k} unit {row.quantity_unit}: installed={ins:.1f} ordered={o:.1f} eol mass set to {0.5*(o+ins):.1f}: C-05 ok={r['C-05']['ok']} violations={r['C-05']['violations']}")
