from vh import *
print("=== NUM-2 extra: grid TABLE with CONSTANT profiles, table[0]=inf ===")
s = mk(1, 60.0, profile_kind="CONSTANT", grid_kind="TABLE"); s.operation.grid.table[0] = inf
r, f, t = three(s); print("  B6-03", g(r, "B6-03"), g(f, "B6-03"), g(t, "B6-03"), "| B2-01", g(r, "B2-01"), g(f, "B2-01"))

print("=== NUM-3 ===")
s = mk(1, 60.0, composite_share=0.0, epd_share=0.0); eq = s.equipment[0]
print("  before: repair_rate", eq.repair_rate, "factor", eq.factor_id, s.factors[eq.factor_id].value, s.factors[eq.factor_id].gas_amounts)
print("  factor value == sum gwp*gas ?", sum(s.gwp[k] * v for k, v in s.factors[eq.factor_id].gas_amounts.items()), s.factors[eq.factor_id].value)
print("  clean scenario failures:", study_fails(s))
eq.repair_rate = 0.02; print("  repair only failures:", study_fails(s))
s.factors[eq.factor_id].value = 0.0
r, f, t = three(s)
for u, k in (("X-04", "value"), ("X-04", "co2e_from_gases"), ("X-05", "value"), ("SUM-03", "value"), ("B3-01", "value")):
    print(f"  {u}.{k}: ref {r[u][k]!r} full {f[u][k]!r} tot {t[u][k]!r}")
print("  X-05.by_stage_co2.B3", r["X-05"]["by_stage_co2"]["B3"], f["X-05"]["by_stage_co2"]["B3"])
print("  ref X-04 value vs ref SUM of by_stage_all:", r["X-04"]["value"], sum(r["X-02"]["by_stage_all"].values()), "| unified:", f["X-04"]["value"], sum(f["X-02"]["by_stage_all"].values()))
print("  study failures:", [(x[0], x[1], x[2]) for x in study_fails(s)])
# other stages with value 0: are A1-A3 lines kept in reference X-04 (asymmetry inside the reference itself)?
print("  ref by_gas CO2 A1-A3 contribution exists though value=0? ref X-05.by_stage_co2[A1-A3]", r["X-05"]["by_stage_co2"]["A1-A3"], "unified", f["X-05"]["by_stage_co2"]["A1-A3"])
# material row variant
s = mk(1, 60.0, composite_share=0.0, epd_share=0.0); row = s.materials[0]; row.repair_rate = 0.02; s.factors[row.factor_id].value = 0.0
print("  material variant failures:", [(x[0], x[1], x[2]) for x in study_fails(s)])
# self-consistent record: all gas amounts zero too -> no difference expected
s = mk(1, 60.0, composite_share=0.0, epd_share=0.0); eq = s.equipment[0]; eq.repair_rate = 0.02
rec = s.factors[eq.factor_id]; rec.value = 0.0; rec.gas_amounts = {k: 0.0 for k in rec.gas_amounts}
print("  value 0 AND gas vector 0 failures:", study_fails(s))
# quantity zero (e0 == 0 through activity 0): no difference expected
s = mk(1, 60.0, composite_share=0.0, epd_share=0.0); eq = s.equipment[0]; eq.repair_rate = 0.02; eq.quantity = 0.0
print("  quantity 0 failures:", study_fails(s))

print("=== NUM-4 ===")
s = mk(1, 60.0, profile_kind="TABLE"); s.water_waste.water.table = s.water_waste.water.table[:59]
r, f, t = three(s); print("  short water table only: ", [type(x).__name__ if isinstance(x, Exception) else "ok" for x in (r, f, t)])
s.water_waste.water_factor_id = None
r, f, t = three(s); print("  + factor None: ", [repr(x)[:50] if isinstance(x, Exception) else "ok SUM-03=%r" % x["SUM-03"]["value"] for x in (r, f, t)])
s = mk(1, 60.0, profile_kind="TABLE"); s.operation.electricity.table = s.operation.electricity.table[:10]
r, f, t = three(s); print("  short elec table only: ", [type(x).__name__ if isinstance(x, Exception) else "ok" for x in (r, f, t)])
s.operation.onsite_generation.unit = "kWh/day"
r, f, t = three(s); print("  + generation kWh/day: ", [repr(x)[:50] if isinstance(x, Exception) else "ok SUM-03=%r" % x["SUM-03"]["value"] for x in (r, f, t)])
s = mk(1, 60.0, profile_kind="TABLE"); s.operation.gas.table = s.operation.gas.table[:10]; s.operation.gas.unit = "m3/month"
r, f, t = three(s); print("  short gas table + m3/month: ", [repr(x)[:50] if isinstance(x, Exception) else "ok SUM-03=%r" % x["SUM-03"]["value"] for x in (r, f, t)])
s = mk(7, 60.0, profile_kind="TABLE"); b = population.attach_baseline(s); b.water_waste.water.table = b.water_waste.water.table[:59]; b.water_waste.water_factor_id = None
r, f, t = three(s); print("  baseline only: ", [repr(x)[:50] if isinstance(x, Exception) else "ok SUM-08=%r" % x["SUM-08"] for x in (r, f, t)])

print("=== NUM-5 ===")
for pid in ("GRID", "REFRIGERANT"):
    s = mk(1, 60.0, composite_share=0.0, epd_share=0.0); row = s.materials[0]
    rec = copy.deepcopy(s.factors[row.factor_id]); rec.factor_id = pid; s.factors[pid] = rec; row.factor_id = pid
    r, f, t = three(s)
    print(f"  id {pid}: factor value {rec.value!r}; A5-01 ref {g(r,'A5-01')!r} full {g(f,'A5-01')!r}; SUM-03 ref {g(r,'SUM-03')!r} full {g(f,'SUM-03')!r} tot {g(t,'SUM-03')!r}")
    print("     ref X-04.value", r["X-04"]["value"], "ref sum by_stage_all", sum(r["X-02"]["by_stage_all"].values()), "ref QA-01", r["QA-01"], "| full QA-01", f["QA-01"])
    print("     study failures:", [x[0] for x in study_fails(s)])

print("=== NUM-6 ===")
s = mk(1, 60.0, composite_share=0.5, epd_share=0.0); s.gases = list(s.gases) + ["CO2"]
r, f, t = three(s); print("  CO2 twice (composite 0.5): X-04", g(r, "X-04"), g(f, "X-04"), g(t, "X-04"), "by_gas CO2", r["X-04"]["by_gas"]["CO2"], f["X-04"]["by_gas"]["CO2"])
s = mk(1, 60.0, composite_share=0.0, epd_share=0.0); s.gases = list(s.gases) + ["CO2"]
print("  CO2 twice (no composite) failures:", study_fails(s))
s = mk(1, 60.0, composite_share=0.5, epd_share=0.0); s.gases = [x for x in s.gases if x != "CO2"]
r, f, t = three(s); print("  no CO2 (composite): ref X-05", g(r, "X-05"), "| full", repr(f)[:60], "| tot", repr(t)[:60])
s = mk(1, 60.0, composite_share=0.0, epd_share=0.0); s.gases = [x for x in s.gases if x != "CO2"]
print("  no CO2 (no composite) failures:", study_fails(s))

print("=== NUM-7 ===")
for idx in (3.0, 2.5):
    s = mk(1, 60.0, grid_kind="STEPWISE"); s.operation.grid.steps = [model.GridStep(0, 0.5), model.GridStep(idx, 0.3)]
    r, f, t = three(s); print(f"  from_index {idx}: ref X-06.source", g(r, "X-06", "source"), "| full", repr(f)[:80], "| tot", repr(t)[:80])
import inspect
print("  GridStep def:", inspect.getsource(model.GridStep)[:400])

print("=== NUM-8 ===")
s = mk(1, 60.0)
for p in (s.operation.electricity, s.operation.onsite_generation, s.operation.onsite_export): p.unit = "None/year"
s.operation.grid.unit = "kgCO2e/None"
r, f, t = three(s); print("  SYS-02 ref", r["SYS-02"]["violations"], "| full", f["SYS-02"]["violations"], "| B6-01.computed", r["B6-01"]["computed"], f["B6-01"]["computed"], "| A5-01.computed", r["A5-01"]["computed"], f["A5-01"]["computed"])
print("  study failures:", [(x[0], x[3]) for x in study_fails(s)])

print("=== NUM-9 ===")
s1 = mk(61, 60.0, scenario_id="N9-A"); b1 = population.attach_baseline(s1)
s2 = mk(62, 60.0, scenario_id="N9-B"); b2 = population.attach_baseline(s2)
print("  baseline ids:", b1.meta.scenario_id, b2.meta.scenario_id, "registry keys:", s1.boundary.baseline_scenario, s2.boundary.baseline_scenario)
held = {}
for s in (s1, s2):
    rr = registry.run_all(s, ids=["SUM-08"])["SUM-08"]; ee = engine.evaluate(s, detail=False, baseline_totals=held)["SUM-08"]
    print("  natural ids:", s.meta.scenario_id, rr["baseline"], ee["baseline"])
b2.meta.scenario_id = b1.meta.scenario_id
held = {}
for s in (s1, s2):
    rr = registry.run_all(s, ids=["SUM-08"])["SUM-08"]; ee = engine.evaluate(s, detail=False, baseline_totals=held)["SUM-08"]
    print("  colliding meta ids:", s.meta.scenario_id, rr["baseline"], ee["baseline"], rr["saving"], ee["saving"])
print("  ScenarioMeta doc:", (model.ScenarioMeta.__doc__ or "")[:400])
print("  attach_baseline src:"); print(inspect.getsource(population.attach_baseline))
