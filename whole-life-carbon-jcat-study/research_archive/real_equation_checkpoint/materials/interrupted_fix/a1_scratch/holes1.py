import sys, copy, math, json, re
import synth
from synth import population
from refcalc import registry, base
registry.load_all()
L = json.load(open("/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/01_LEDGER/units.json"))
norm = lambda s: re.sub(r"\s+", "", s or "")
# 0. ledger text == docstring, depends_on equal
nd = 0
for u in L["units"]:
    d = registry.UNITS.get(u["id"])
    if d is None:
        print("NOT REGISTERED", u["id"]); continue
    if norm(d.doc) != norm(u["reference_semantics"]):
        nd += 1; print("DOC DIFF", u["id"])
    if set(d.depends_on) != set(u["depends_on"]):
        print("DEPS DIFF", u["id"], sorted(set(d.depends_on) ^ set(u["depends_on"])))
print("doc diffs", nd, "registered", len(registry.UNITS), "ledger", len(L["units"]))

def small(seed=11, T=60.0, **o):
    opts = dict(n_materials=12, n_equipment=6, n_refrigerants=4); opts.update(o)
    return synth.make_scenario(seed, "RC", "office", "S", T, **opts)

def tot(res):
    return res["SUM-03"]["value"], res["X-02"]["complete"], res["X-02"]["incomplete_units"]

print("\n== H1: B3 / B5 only boundary with an upstream skipped row ==")
for sub in (["B3"], ["B5"], ["B3", "B5"], ["B2"], ["B4"], ["B1"]):
    s = small(included_stages=sub, replacement_cycle=25.0, reconstruction_scenario="REBUILD_IDENTICAL")
    r0 = registry.run_all(s)
    s2 = copy.deepcopy(s)
    # make the largest manufacturing rows uncomputable
    order = sorted(range(len(s2.materials)), key=lambda i: -(r0["A13-01"]["by_item"][i] + r0["A13-03"]["by_item"][i]))
    for i in order[:3]:
        s2.materials[i].quantity = None
    s2.equipment[0].factor_id = "F-NOT-IN-TABLE"
    r1 = registry.run_all(s2)
    print(sub, "clean", r0["SUM-03"]["value"], r0["X-02"]["complete"], "| defective", r1["SUM-03"]["value"], "complete", r1["X-02"]["complete"], r1["X-02"]["incomplete_units"],
          "| A13-01 n_skipped", r1["A13-01"]["n_skipped"], "X-01 n_skipped", r1["X-01"]["n_skipped"], "B3-01 n_skipped", r1["B3-01"]["n_skipped"], "B5 computed", r1["B5-01"]["computed"])

print("\n== H2: annual quantities negative / NaN are used silently ==")
s = small(profile_kind="CONSTANT")
r0 = registry.run_all(s)
s2 = copy.deepcopy(s); s2.operation.gas.base = -abs(s2.operation.gas.base); s2.operation.gas.table = [s2.operation.gas.base] * len(s2.operation.gas.table)
s2.water_waste.water.base = -abs(s2.water_waste.water.base); s2.water_waste.water.table = [s2.water_waste.water.base]*len(s2.water_waste.water.table)
r1 = registry.run_all(s2)
print("B6-03", r0["B6-03"]["value"], "->", r1["B6-03"]["value"], "B7-04", r0["B7-04"]["value"], "->", r1["B7-04"]["value"], "B6-02 n_skipped", r1["B6-02"]["n_skipped"],
      "complete", r1["X-02"]["complete"], r1["X-02"]["incomplete_units"], "SYS-01 ok", r1["SYS-01"]["ok"], "SYS-02 ok", r1["SYS-02"]["ok"], "by_stage B7", r1["X-02"]["by_stage"]["B7"], "SUM-07", r1["SUM-07"]["defined"])
s3 = copy.deepcopy(s); s3.operation.gas.base = float("nan")
r3 = registry.run_all(s3)
print("gas base NaN: SUM-03", r3["SUM-03"]["value"], "complete", r3["X-02"]["complete"], "SYS-01 ok", r3["SYS-01"]["ok"], "B6-02 n_skipped", r3["B6-02"]["n_skipped"], "match", r3["B6-02"]["descriptors_match_tables"])

print("\n== H3: grid factor negative / NaN / None ==")
s = small(grid_kind="CONSTANT")
for label, v in (("neg", -0.4), ("nan", float("nan"))):
    s2 = copy.deepcopy(s); s2.operation.grid.start = v; s2.operation.grid.table = [v] * len(s2.operation.grid.table)
    r = registry.run_all(s2)
    print(label, "B6-03", r["B6-03"]["value"], "B2-01", r["B2-01"], "SUM-03", r["SUM-03"]["value"], "complete", r["X-02"]["complete"], "matches_table", r["X-06"]["matches_table"], "SYS ok", r["SYS-01"]["ok"], r["SYS-02"]["ok"], r["SYS-03"]["ok"])
for label, fn in (("construction_value None", lambda g: setattr(g, "construction_value", None)), ("construction_value neg", lambda g: setattr(g, "construction_value", -1.0)),
                  ("table None TABLE kind", lambda g: (setattr(g, "kind", "TABLE"), g.table.__setitem__(3, None)))):
    s2 = copy.deepcopy(s); fn(s2.operation.grid)
    try:
        r = registry.run_all(s2)
        print(label, "A5-01", r["A5-01"]["value"], "SUM-03", r["SUM-03"]["value"], "complete", r["X-02"]["complete"])
    except Exception as e:
        print(label, "RAISED", type(e).__name__, e)

print("\n== H4: C-05 with None / NaN / negative fraction or mass ==")
s = small()
for label, fn in (("fraction None", lambda m: setattr(m.end_of_life.routes[1], "fraction", None)),
                  ("fraction NaN", lambda m: setattr(m.end_of_life.routes[1], "fraction", float("nan"))),
                  ("fraction 3.0 others kept", lambda m: setattr(m.end_of_life.routes[1], "fraction", 3.0)),
                  ("mass -1", lambda m: setattr(m.end_of_life, "mass_kg", -1.0)),
                  ("mass NaN", lambda m: setattr(m.end_of_life, "mass_kg", float("nan"))),
                  ("mass inf", lambda m: setattr(m.end_of_life, "mass_kg", float("inf")))):
    s2 = copy.deepcopy(s); fn(s2.materials[0])
    try:
        r = registry.run_all(s2)
        print(label, "C-05", r["C-05"], "| C3 n_routes_skipped", r["C3-01"]["n_routes_skipped"], "C3 n_skipped", r["C3-01"]["n_skipped"], "C3 by_item0", r["C3-01"]["by_item"][0], "complete", r["X-02"]["complete"])
    except Exception as e:
        print(label, "RAISED", type(e).__name__, e)

print("\n== H5: conversion factor / factor value never validated ==")
s = small(unit_variety=True)
r0 = registry.run_all(s)
idx = [i for i, m in enumerate(s.materials) if m.conversions and r0["A13-01"]["by_item"][i] > 0]
print("rows with row conversions", idx[:5])
if idx:
    i = idx[0]
    s2 = copy.deepcopy(s)
    for c in s2.materials[i].conversions: c.factor = -c.factor
    r = registry.run_all(s2)
    print("neg conversion row", i, "A13-01 by_item", r0["A13-01"]["by_item"][i], "->", r["A13-01"]["by_item"][i], "n_skipped", r["A13-01"]["n_skipped"], "complete", r["X-02"]["complete"], "SYS-02 ok", r["SYS-02"]["ok"], "C-05 ok", r["C-05"]["ok"])
fid = next(m.factor_id for m in s.materials if m.factor_id and m.epd is None)
for label, v in (("factor value NaN", float("nan")), ("factor value negative", -5.0), ("factor value None", None)):
    s2 = copy.deepcopy(s); s2.factors[fid].value = v
    try:
        r = registry.run_all(s2)
        print(label, fid, "A1-A3", r["X-02"]["by_stage"]["A1-A3"], "(clean", r0["X-02"]["by_stage"]["A1-A3"], ") SUM-03", r["SUM-03"]["value"], "complete", r["X-02"]["complete"], "SYS-01/02/03 ok", r["SYS-01"]["ok"], r["SYS-02"]["ok"], r["SYS-03"]["ok"], "QA-01", r["QA-01"]["ok"], "QA-03", r["QA-03"]["ok"], "SUM-07 defined", r["SUM-07"]["defined"])
    except Exception as e:
        print(label, "RAISED", type(e).__name__, e)

print("\n== H6: gas amounts inconsistent with the factor value: does anything check X-04's identity? ==")
s2 = copy.deepcopy(s); s2.factors[fid].gas_amounts["CO2"] *= 3.0
r = registry.run_all(s2)
stage_sum = sum(r["X-02"]["by_stage_all"].values())
print("X-04 value", r["X-04"]["value"], "sum of 14 stages", stage_sum, "rel diff", (r["X-04"]["value"] - stage_sum) / stage_sum, "X-04 keys", [k for k in r["X-04"] if not k.startswith("_")], "QA-01", r["QA-01"], "QA-03 ok", r["QA-03"]["ok"], "X-05", r["X-05"]["value"], "SUM-03", r["SUM-03"]["value"])

print("\n== H7: SYS-01 coverage ==")
s2 = copy.deepcopy(s)
s2.operation.facility_management_ratio = None
s2.boundary.reconstruction_scope_fraction = None; s2.boundary.reconstruction_scenario = "REBUILD_IDENTICAL"; s2.boundary.replacement_cycle = 25.0
s2.materials[0].unquantified_cost_ratio = None
s2.materials[1].quantity = float("nan")
s2.materials[2].transport.load_factor = None
if s2.cost_items: s2.cost_items[0].amount = None
r = registry.run_all(s2)
print("SYS-01", r["SYS-01"]["ok"], r["SYS-01"]["violations"], "| B2-01", r["B2-01"], "B5-01 computed", r["B5-01"]["computed"], "A13-05 n_skipped", r["A13-05"]["n_skipped"], "X-16 n_skipped", r["X-16"]["n_skipped"], "complete", r["X-02"]["complete"], r["X-02"]["incomplete_units"])

print("\n== H8: invalid periods / cycles give no events silently ==")
s = small(replacement_cycle=25.0, reconstruction_scenario="REBUILD_IDENTICAL")
r0 = registry.run_all(s)
s2 = copy.deepcopy(s)
s2.boundary.replacement_cycle = -25.0
for m in s2.materials: m.refresh_cycle = -abs(m.refresh_cycle) if m.refresh_cycle else float("nan")
for e in s2.equipment: e.replacement_event_list = None; e.service_life = float("nan")
for d in s2.refrigerants: d.change_years = None; d.service_life = -3.0
r = registry.run_all(s2)
print("clean B4", r0["X-02"]["by_stage"]["B4"], "B5", r0["X-02"]["by_stage"]["B5"], "B1", r0["X-02"]["by_stage"]["B1"], "SUM-03", r0["SUM-03"]["value"])
print("defect B4", r["X-02"]["by_stage"]["B4"], "B5", r["X-02"]["by_stage"]["B5"], "B1", r["X-02"]["by_stage"]["B1"], "SUM-03", r["SUM-03"]["value"], "complete", r["X-02"]["complete"], r["X-02"]["incomplete_units"],
      "SYS-01 ok", r["SYS-01"]["ok"], r["SYS-01"]["violations"][:4], "QA-02 ok", r["QA-02"]["ok"], "B5 computed", r["B5-01"]["computed"], "n_partial", r["B4-02"]["n_partial"])

print("\n== H9: short profile table ==")
s2 = small(profile_kind="TABLE"); s2.operation.gas.table = s2.operation.gas.table[:30]
try:
    registry.run_all(s2); print("no error")
except Exception as e:
    print("RAISED", type(e).__name__, e)
