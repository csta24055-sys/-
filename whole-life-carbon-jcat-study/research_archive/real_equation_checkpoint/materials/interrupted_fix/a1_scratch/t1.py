from h import *
nan, inf = float("nan"), float("inf")
R = {}
def case(name, fn, seed=1, period=60.0, **opts):
    s = mk(seed, period, **opts)
    try:
        fn(s)
    except Exception as e:
        print(f"[{name}] setup failed: {e!r}"); return
    R[name] = check(s, name)
    if not R[name]:
        print(f"[{name}] no difference")

# E1 factor id collides with pseudo ids
def e1(s):
    row = next(r for r in s.materials if r.composition is None and r.epd is None)
    rec = s.factors[row.factor_id]; rec2 = copy.deepcopy(rec); rec2.factor_id = "GRID"
    s.factors["GRID"] = rec2; row.factor_id = "GRID"
case("factor_id_GRID", e1)
def e1b(s):
    row = next(r for r in s.materials if r.composition is None and r.epd is None)
    rec = s.factors[row.factor_id]; rec2 = copy.deepcopy(rec); rec2.factor_id = "REFRIGERANT"
    s.factors["REFRIGERANT"] = rec2; row.factor_id = "REFRIGERANT"
case("factor_id_REFRIGERANT", e1b)

# E7 short profile tables
def e7a(s):
    p = s.water_waste.water; p.kind, p.base, p.slope = "TABLE", None, None; p.table = p.table[:10]
    s.water_waste.water_factor_id = None
case("short_table_no_factor", e7a)
def e7b(s):
    p = s.water_waste.water; p.kind, p.base, p.slope = "TABLE", None, None; p.table = p.table[:10]
case("short_table_with_factor", e7b)
def e7c(s):
    p = s.operation.gas; p.kind, p.base, p.slope = "TABLE", None, None; p.table = p.table[:10]; p.unit = "m3/month"
case("short_table_bad_unit", e7c)
def e7d(s):
    p = s.operation.electricity; p.kind, p.base, p.slope = "TABLE", None, None; p.table = p.table[:10]
    s.operation.onsite_generation.unit = "kWh/day"
case("short_elec_table_net_not_ok", e7d)
def e7e(s):
    p = s.operation.electricity; p.kind = "CONSTANT"; p.base = 1000.0; p.table = p.table[:10]
case("short_table_constant_kind", e7e)
def e7f(s):
    p = s.operation.onsite_export; p.kind, p.base, p.slope = "TABLE", None, None; p.table = []
case("empty_export_table", e7f)

# E8 grid descriptor nan / inf / odd steps
def g_lin(s, **kw):
    g = s.operation.grid; g.kind = "LINEAR_DECLINE_TO_FLOOR"; g.steps = None
    g.start, g.floor, g.annual_decline = 0.5, 0.1, 0.01
    for k, v in kw.items(): setattr(g, k, v)
case("grid_decline_nan", lambda s: g_lin(s, annual_decline=nan))
case("grid_start_nan", lambda s: g_lin(s, start=nan))
case("grid_floor_nan", lambda s: g_lin(s, floor=nan))
case("grid_start_inf", lambda s: g_lin(s, start=inf))
case("grid_decline_inf", lambda s: g_lin(s, annual_decline=inf))
case("grid_floor_neg_inf", lambda s: g_lin(s, floor=-inf))
case("grid_decline_tiny", lambda s: g_lin(s, annual_decline=1e-300))
case("grid_decline_huge", lambda s: g_lin(s, annual_decline=1e300))
case("grid_floor_eq_start", lambda s: g_lin(s, floor=0.5))
case("grid_floor_exact_int", lambda s: g_lin(s, start=0.5, floor=0.25, annual_decline=0.0125))
def steps(s, lst):
    g = s.operation.grid; g.kind = "STEPWISE"; g.steps = [model.GridStep(a, b) for a, b in lst]
case("steps_float_index", lambda s: steps(s, [(0, 0.5), (2.5, 0.3), (10, 0.2)]))
case("steps_float_integral_index", lambda s: steps(s, [(0, 0.5), (3.0, 0.3), (10.0, 0.2)]))
case("steps_one", lambda s: steps(s, [(0, 0.4)]))
case("steps_beyond", lambda s: steps(s, [(0, 0.4), (59, 0.3), (60, 0.2), (61, 0.1), (500, 0.05)]))
case("steps_dup_index", lambda s: steps(s, [(0, 0.4), (5, 0.3), (5, 0.2)]))
case("steps_bool_index", lambda s: steps(s, [(False, 0.4), (True, 0.3)]))
case("steps_value_nan", lambda s: steps(s, [(0, 0.4), (5, nan)]))
case("steps_value_none", lambda s: steps(s, [(0, 0.4), (5, None)]))
case("steps_neg_first", lambda s: steps(s, [(-1, 0.4), (0, 0.3)]))
def gconst(s, v):
    g = s.operation.grid; g.kind = "CONSTANT"; g.start = v
case("grid_const_nan", lambda s: gconst(s, nan))
case("grid_const_inf", lambda s: gconst(s, inf))
case("grid_const_none", lambda s: gconst(s, None))
def gtab(s, k, v):
    g = s.operation.grid; g.kind = "TABLE"; g.table[k] = v
case("grid_table_nan", lambda s: gtab(s, 3, nan))
case("grid_table_none", lambda s: gtab(s, 3, None))

# E23 NaN in profile / factor value
def pset(p, kind, base, slope):
    p.kind, p.base, p.slope = kind, base, slope
case("gas_base_nan", lambda s: pset(s.operation.gas, "CONSTANT", nan, None))
case("gas_base_inf", lambda s: pset(s.operation.gas, "CONSTANT", inf, None))
case("water_slope_nan", lambda s: pset(s.water_waste.water, "LINEAR_TREND", 5.0, nan))
case("elec_base_nan", lambda s: pset(s.operation.electricity, "CONSTANT", nan, None))
case("elec_base_inf", lambda s: pset(s.operation.electricity, "CONSTANT", inf, None))
def fv(s, v):
    row = next(r for r in s.materials if r.composition is None and r.epd is None)
    s.factors[row.factor_id].value = v
case("factor_value_nan", lambda s: fv(s, nan))
case("factor_value_inf", lambda s: fv(s, inf))
case("factor_value_neg", lambda s: fv(s, -3.0))
case("factor_value_none", lambda s: fv(s, None))
def cv(s, v): s.operation.grid.construction_value = v
case("construction_value_nan", lambda s: cv(s, nan))
case("construction_value_none", lambda s: cv(s, None))

# E16 unit literally "None"
def none_unit(s):
    for p in (s.operation.electricity, s.operation.onsite_generation, s.operation.onsite_export):
        p.unit = "None/year"
case("unit_named_None", none_unit)
def none_unit2(s):
    none_unit(s); s.operation.grid.unit = "kgCO2e/None"
case("unit_named_None_grid_too", none_unit2)
def empty_unit(s):
    s.operation.gas.unit = "/year"
case("unit_empty_head", empty_unit)

import json
print("\nSUMMARY of cases with differences:", [k for k, v in R.items() if v])
