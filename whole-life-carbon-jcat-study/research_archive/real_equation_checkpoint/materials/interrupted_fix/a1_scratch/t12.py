from h import *
nan = float("nan")
# factor id equal to the pseudo ids
for pid in ("GRID", "REFRIGERANT"):
    s = mk(1, 60.0, composite_share=0.0, epd_share=0.0)
    row = s.materials[0]
    rec = copy.deepcopy(s.factors[row.factor_id]); rec.factor_id = pid
    s.factors[pid] = rec; row.factor_id = pid
    ref, full, tot = run3(s)
    print(f"factor id {pid!r} (value {rec.value}):")
    for u, k in (("A13-01", "value"), ("A5-01", "value"), ("B6-03", "value"), ("B1-02", "value"), ("SUM-03", "value"), ("X-04", "value"), ("X-04", "grid_co2e"), ("X-04", "refrigerant_co2e"), ("QA-01", "ok"), ("QA-03", "n_used")):
        if ref[u][k] != full[u][k]: print(f"    {u}.{k}: ref {ref[u][k]!r} unified {full[u][k]!r} totals {tot[u][k]!r}")
# unit literally named "None"
s = mk(1, 60.0)
for p in (s.operation.electricity, s.operation.onsite_generation, s.operation.onsite_export): p.unit = "None/year"
s.operation.grid.unit = "kgCO2e/None"
ref, full, tot = run3(s)
print("unit named 'None': SYS-02 ref", ref["SYS-02"]["ok"], ref["SYS-02"]["violations"], "| unified", full["SYS-02"]["ok"], full["SYS-02"]["violations"], "| B6-01 computed ref", ref["B6-01"]["computed"], "unified", full["B6-01"]["computed"])
# stepwise float index
s = mk(1, 60.0, grid_kind="STEPWISE")
s.operation.grid.steps = [model.GridStep(0, 0.5), model.GridStep(3.0, 0.3)]
ref, full, tot = run3(s)
print("STEPWISE from_index=3.0: ref X-06 source", ref["X-06"]["source"] if not isinstance(ref, Exception) else repr(ref), "| unified", repr(full)[:90])
# short profile table + unusable factor / unit
s = mk(1, 60.0, profile_kind="TABLE")
s.water_waste.water.table = s.water_waste.water.table[:59]; s.water_waste.water_factor_id = None
ref, full, tot = run3(s)
print("water table 59 entries (T=60) and no water factor: ref", repr(ref)[:60], "| unified B7-01", full["B7-01"] if not isinstance(full, Exception) else repr(full), "| SYS-01 ok", full["SYS-01"]["ok"], "SYS-03 violations", full["SYS-03"]["violations"])
s = mk(1, 60.0, profile_kind="TABLE")
s.water_waste.water.table = s.water_waste.water.table[:59]
ref, full, tot = run3(s)
print("same table, factor usable: ref", repr(ref)[:60], "| unified", repr(full)[:60])
# grid descriptor NaN
s = mk(1, 60.0, grid_kind="LINEAR_DECLINE_TO_FLOOR")
s.operation.grid.annual_decline = nan
ref, full, tot = run3(s)
print("grid annual_decline=nan: ref X-06", {k: v for k, v in ref["X-06"].items() if k != "by_year"}, "SUM-03", ref["SUM-03"], "| unified", repr(full), "| totals", repr(tot))
# gases
s = mk(1, 60.0, composite_share=0.5, epd_share=0.0); s.gases = list(s.gases) + ["CO2"]
ref, full, tot = run3(s)
print("gases list with 'CO2' twice: X-04 value ref", ref["X-04"]["value"], "unified", full["X-04"]["value"], "; by_gas.CO2 ref", ref["X-04"]["by_gas"]["CO2"], "unified", full["X-04"]["by_gas"]["CO2"], "; SUM-03 ref", ref["SUM-03"]["value"], "unified", full["SUM-03"]["value"])
s = mk(1, 60.0, composite_share=0.5, epd_share=0.0); s.gases = [g for g in s.gases if g != "CO2"]
ref, full, tot = run3(s)
print("gases list without 'CO2': ref X-05", ref["X-05"]["value"], "| unified", repr(full), repr(tot))
