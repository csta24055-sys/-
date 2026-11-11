"""Random multi-defect mutators (finite values, legal types unless stated)."""
from h import *
import random
nan, inf = float("nan"), float("inf")

import os
KNOWN_BAD = 1.000000001 if os.environ.get("WITH_KNOWN_BAD") else 1.0000000011
ODD_LIVES = [None, 0.0, -3.0, 1e-3 * 7, 0.1, 0.25, 0.3, 0.5, 0.75, 0.999999999, 1.0, 1.0000000005, KNOWN_BAD, 1.5, 2.0,
             3, 7.5, 10, 11.1, 12.0, 15.0, 19.999999, 20.0, 20.000000001, 29.9999999999, 30.0, 33.3, 59.99999999, 60.0, 60.00000001, 61, 200.0]
ODD_PERIODS = [0.3, 0.5, 1.0, 1.0000001, 1.5, 2.0, 7.0, 12.3, 29.999999999, 30.0, 42.5, 55.5, 59.9999999999, 60.0, 60.000001, 62.5, 99.9, 100.0, 120.0, 129.5]

def lives_for(T, rng):
    out = list(ODD_LIVES)
    for n in (1, 2, 3, 4, 7, 13, 60, 125):
        out += [T / n, T / n * (1 + 1e-10), T / n * (1 - 1e-10), T / n * (1 + 2e-9), T / n * (1 - 2e-9)]
    out += [T - 1e-12, T + 1e-12, T * (1 - 1e-9), T * (1 - 0.5e-9), T*(1-1.5e-9)]
    return out

def events_for(T, rng):
    pool = [0, 0.0, -2, 1, 1.0, 1.0000000005, 2, 2.5, 3, 3, 7, 7, 7, 10, 12.25, 25, T, T - 1e-12, T * (1 - 1e-9), T*(1-2e-9), T + 5, T / 2, T / 3, 0.5, 0.999999999, 1e-9, math.ceil(T) - 1, math.ceil(T) - 0.5, math.ceil(T)-1+1e-9]
    n = rng.choice([0, 1, 2, 3, 5, 8])
    return [rng.choice(pool) for _ in range(n)]

def fids(s, stage=None):
    return [k for k, f in s.factors.items() if stage is None or f.stages == [stage]]

def pick_fid(s, rng, stage):
    r = rng.random()
    if r < 0.25: return None
    if r < 0.4: return "F-NOT-THERE"
    if r < 0.7:
        c = fids(s, stage)
        return rng.choice(c) if c else None
    return rng.choice(list(s.factors))

def m_material(s, rng, T):
    if not s.materials: return
    row = rng.choice(s.materials)
    k = rng.randrange(24)
    if k == 0: row.quantity = rng.choice([None, -1.0, 0.0, 1e-300, 1e12, 5])
    elif k == 1: row.waste_rate = rng.choice([None, 0.0, 0.999999, 1.0, -0.1, 0.5])
    elif k == 2: row.reuse_rate = rng.choice([None, -0.1, 1.1, 0.0, 1.0])
    elif k == 3: row.repair_rate = rng.choice([None, -1.0, 0.0, 5.0, 1e-12])
    elif k == 4: row.refresh_cycle = rng.choice(lives_for(T, rng))
    elif k == 5: row.quantity_unit = rng.choice([None, "kg", "t", "piece", "m2", "m3", "g", ""])
    elif k == 6: row.quantity_basis = rng.choice(["DESIGN", "ORDERED", "AS_BUILT", "???"])
    elif k == 7: row.factor_id = pick_fid(s, rng, "A1-A3")
    elif k == 8:
        fid = pick_fid(s, rng, "A1-A3")
        rec = s.factors.get(fid)
        row.epd = model.EpdReference(fid, list(rec.stages) if rec else ["A1-A3"], rec.unit if rec else "kg",
                                     rng.choice([rec.valid_until if rec else None, "2000-01-01", s.project.assessment_date, None]))
        if rec and rng.random() < 0.5: rec.valid_until = rng.choice([s.project.assessment_date, "2999-01-01", None, row.epd.valid_until])
        if rec and rng.random() < 0.5: row.epd.valid_until = rec.valid_until
    elif k == 9:
        comp = [model.CompositeComponent(pick_fid(s, rng, "A1-A3"), rng.choice([0.5, 0.25, 1.0, 0.0, -0.25, 1e-7, 0.3333333])) for _ in range(rng.randrange(0, 4))]
        row.composition = comp
        if rng.random() < 0.5:
            tot_ = sum(c.mass_fraction for c in comp)
            if comp and tot_ > 0:
                for c in comp: c.mass_fraction = c.mass_fraction / tot_
    elif k == 10 and row.composition:
        c = rng.choice(row.composition)
        j = rng.randrange(5)
        if j == 0: c.mass_fraction += rng.choice([1e-6, 1.0000001e-6, -1e-6, 0.9e-6, 0.5])
        elif j == 1: c.factor_id = pick_fid(s, rng, "A1-A3")
        elif j == 2: row.composition.append(copy.deepcopy(c))
        elif j == 3: row.composition = list(reversed(row.composition))
        else:
            other = rng.choice(s.materials); other.composition = copy.deepcopy(row.composition)
    elif k == 11: row.unquantified_cost_ratio = rng.choice([None, 0.0, 0.5, 1.0, -0.1, 0.999999, 1e-9])
    elif k == 12: row.installation_factor_id = pick_fid(s, rng, "A5")
    elif k == 13:
        row.conversions = list(row.conversions) + [model.UnitConversion(rng.choice([row.quantity_unit, "piece", "m2", "kg"]), rng.choice(["kg", "t", "m3", "tkm", "piece", "unit"]), rng.choice([2.5, 0.0, -1.0, 1000.0, None]), "fuzz")]
    elif k == 14: row.transport.mass_t = rng.choice([None, -1.0, 0.0, 3.0])
    elif k == 15: row.transport.distance_km = rng.choice([None, -1.0, 0.0, 30.0])
    elif k == 16: row.transport.load_factor = rng.choice([None, 0.0, -1.0, 0.5, 2.0, 1e-9])
    elif k == 17: row.transport.factor_id = pick_fid(s, rng, "A4")
    elif k == 18: row.transport.delivery_factor_id = pick_fid(s, rng, "A4")
    elif k == 19: row.end_of_life.mass_kg = rng.choice([None, -1.0, 0.0, 1e15, 12.5])
    elif k == 20: row.end_of_life.haul_distance_km = rng.choice([None, -1.0, 0.0, 40.0])
    elif k == 21: row.end_of_life.haul_factor_id = pick_fid(s, rng, "C2")
    elif k == 22 and row.end_of_life.routes:
        r = rng.choice(row.end_of_life.routes)
        j = rng.randrange(6)
        if j == 0: r.fraction = rng.choice([-0.2, 0.0, 1.0, 0.5, 1e-7, 2.0])
        elif j == 1: r.factor_id = pick_fid(s, rng, "C4" if r.route == "LANDFILL" else "C3")
        elif j == 2: row.end_of_life.routes = row.end_of_life.routes[:rng.randrange(0, 4)]
        elif j == 3: row.end_of_life.routes.append(copy.deepcopy(r))
        elif j == 4: r.route = rng.choice(list(model.EOL_ROUTES))
        else: r.fraction += rng.choice([1e-6, 1.1e-6, -1e-6, -1.1e-6])
    elif k == 23:
        row.material_class = rng.choice(["REBAR", "STRUCTURAL_STEEL", "CONCRETE", "TIMBER", "GLASS", "OTHER_X"])
        row.construction_division = rng.choice(["ROOF_EXTERIOR_WALL", "OPENINGS", "INTERIOR", "STRUCTURE"])

def m_equipment(s, rng, T):
    if not s.equipment: return
    eq = rng.choice(s.equipment)
    k = rng.randrange(10)
    if k == 0: eq.quantity = rng.choice([None, -1.0, 0.0, 3, 1e9])
    elif k == 1: eq.quantity_unit = rng.choice([None, "unit", "kg", "piece"])
    elif k == 2: eq.factor_id = pick_fid(s, rng, "A1-A3")
    elif k == 3: eq.service_life = rng.choice(lives_for(T, rng))
    elif k == 4: eq.repair_rate = rng.choice([None, -1.0, 0.0, 0.02, 3.0])
    elif k == 5: eq.replacement_event_list = rng.choice([None, events_for(T, rng)])
    elif k == 6: eq.end_of_life_mass_kg = rng.choice([None, -1.0, 0.0, 250.0])
    elif k == 7: eq.eol_factor_id = pick_fid(s, rng, "C3")
    elif k == 8: eq.delivery_factor_id = pick_fid(s, rng, "A4")
    elif k == 9: eq.installation_factor_id = pick_fid(s, rng, "A5")

def m_refrigerant(s, rng, T):
    if not s.refrigerants: return
    d = rng.choice(s.refrigerants)
    k = rng.randrange(9)
    if k == 0: d.charge_mass_kg = rng.choice([None, -1.0, 0.0, 12.0])
    elif k == 1: d.gwp = rng.choice([None, -1.0, 0.0, 2000.0])
    elif k == 2: d.annual_leak_rate = rng.choice([None, -0.1, 0.0, 1.0, 1.0000001, 1e-15, 1e-9, 0.5, 0.999999999, 0.02])
    elif k == 3: d.replacement_loss_rate = rng.choice([None, -0.1, 0.0, 1.0, 1.1, 0.1])
    elif k == 4: d.end_of_life_recovery_rate = rng.choice([None, -0.1, 0.0, 1.0, 1.1, 0.7])
    elif k == 5: d.change_years = rng.choice([None, events_for(T, rng)])
    elif k == 6: d.service_life = rng.choice(lives_for(T, rng))
    elif k == 7: d.top_up = rng.choice([True, False])
    elif k == 8: d.change_years, d.service_life = rng.choice([(None, None), (events_for(T, rng), rng.choice(lives_for(T, rng)))])

def m_factor(s, rng, T):
    f = s.factors[rng.choice(list(s.factors))]
    k = rng.randrange(9)
    if k == 0: f.stages = rng.choice([["A1-A3"], ["A4"], ["A5"], ["C3"], ["C4"], ["B6"], ["A1-A3", "A4"], [], ["MEMO"]])
    elif k == 1: f.unit = rng.choice(["kg", "t", "m3", "piece", "tkm", "unit", "kgkm", "L", "MJ"])
    elif k == 2: f.licence_status = rng.choice(["UNKNOWN", "RESTRICTED", "PERMISSION_REQUIRED", "PERMITTED_PUBLIC"])
    elif k == 3: f.source_url = ""
    elif k == 4: f.value = rng.choice([0.0, 1.0, 123.456, 1e-12])
    elif k == 5: f.valid_until = rng.choice([None, "2000-01-01", "2999-12-31"])
    elif k == 6: f.release_year += rng.choice([-1, 1, 10])
    elif k == 7:
        for g in f.gas_amounts: f.gas_amounts[g] *= rng.choice([0.0, 1.0, 2.0])
    elif k == 8: s.factors.pop(f.factor_id if f.factor_id in s.factors else next(iter(s.factors)), None)

def m_profile(p, rng):
    k = rng.randrange(8)
    if k == 0: p.kind = rng.choice(["CONSTANT", "LINEAR_TREND", "TABLE", "WEIRD"])
    elif k == 1: p.base = rng.choice([None, 0.0, 1000.0, -500.0, 1e9])
    elif k == 2: p.slope = rng.choice([None, 0.0, 5.0, -5.0, -20.0, 20.0])
    elif k == 3: p.unit = rng.choice(["kWh/year", "MWh/year", "m3/year", "L/year", "MJ/year", "kg/year", "kWh/month", "m3", "kWh/day", "GJ/year", "t/year", "kL/year"])
    elif k == 4: p.table[rng.randrange(len(p.table))] *= rng.choice([0.0, 2.0, 1 + 1e-12, 1 + 2e-12, 1 + 0.5e-12, -1.0])
    elif k == 5 and p.base is not None and p.slope is not None: p.table = [p.base + p.slope * i for i in range(len(p.table))]
    elif k == 6 and p.base is not None: p.table = [p.base] * len(p.table)
    elif k == 7:
        p.kind = "LINEAR_TREND"; p.base = rng.choice([1000.0, 5e5, 0.0]); p.slope = rng.choice([-p.base / rng.choice([10, 20, 59, 60, 61, 100]), 7.0, -1.0])

def m_operation(s, rng, T):
    op, ww = s.operation, s.water_waste
    k = rng.randrange(12)
    if k <= 3: m_profile(rng.choice([op.electricity, op.onsite_generation, op.onsite_export]), rng)
    elif k <= 5: m_profile(rng.choice([op.gas, op.oil, op.district_heat, ww.water, ww.sewage, ww.municipal_waste]), rng)
    elif k == 6: op.facility_management_ratio = rng.choice([None, 0.0, 1.0, 1.5, -0.1, 0.3])
    elif k == 7: op.electricity_per_m2_per_year = rng.choice([None, -1.0, 0.0, 120.0])
    elif k == 8:
        name = rng.choice(["gas_factor_id", "oil_factor_id", "district_heat_factor_id"]); setattr(op, name, pick_fid(s, rng, "B6"))
    elif k == 9:
        name = rng.choice(["water_factor_id", "sewage_factor_id", "waste_factor_id"]); setattr(ww, name, pick_fid(s, rng, "B7"))
    elif k == 10:
        # generation exceeding consumption at one end
        for p, (b, sl) in zip((op.electricity, op.onsite_generation, op.onsite_export), rng.choice([((1000.0, 0.0), (0.0, 20.0), (0.0, 0.0)), ((1000.0, -10.0), (1500.0, -30.0), (100.0, 0.0)), ((1000.0, 0.0), (1000.0, 0.0), (0.0, 0.0)), ((1000.0, -1000.0 / 59), (0.0, 0.0), (0.0, 0.0)), ((1000.0, 5.0), (400.0, 5.0), (400.0, 0.0))])):
            p.kind, p.base, p.slope = rng.choice(["LINEAR_TREND", "LINEAR_TREND", "CONSTANT"]), b, sl
    elif k == 11: op.grid.licence_status = rng.choice(["UNKNOWN", "PERMITTED_PUBLIC"])

def m_grid(s, rng, T):
    g = s.operation.grid
    k = rng.randrange(9)
    Y = math.ceil(T)
    if k == 0: g.kind = rng.choice(["CONSTANT", "LINEAR_DECLINE_TO_FLOOR", "STEPWISE", "TABLE", "SPLINE"])
    elif k == 1: g.start = rng.choice([None, 0.0, 0.5, -0.5, 1.0])
    elif k == 2: g.floor = rng.choice([None, 0.0, 0.1, 0.5, 0.6, -1.0])
    elif k == 3: g.annual_decline = rng.choice([None, 0.0, -0.01, 0.01, 0.4 / (Y - 1) if Y > 1 else 0.1, 0.4 / Y, 0.02, 1e-9, 10.0])
    elif k == 4:
        n = rng.randrange(0, 5)
        idx = sorted(rng.sample(range(0, Y + 5), min(n, Y + 5)))
        if idx and rng.random() < 0.7: idx[0] = 0
        g.steps = rng.choice([None, [model.GridStep(i, rng.choice([0.5, 0.3, 0.0, 0.7])) for i in idx]])
    elif k == 5: g.unit = rng.choice(["kgCO2e/kWh", "kgCO2e/MWh", "kgCO2e/MJ", "kgCO2e/", "tCO2e/kWh", "kgCO2e", "kgCO2e/barrel"])
    elif k == 6: g.table[rng.randrange(min(len(g.table), Y + 2))] *= rng.choice([0.0, 2.0, 1 + 1e-12, 1 + 2e-12])
    elif k == 7: g.construction_value = rng.choice([0.0, 0.9, -0.1])
    elif k == 8:
        g.kind = "LINEAR_DECLINE_TO_FLOOR"; g.start = 0.5; g.floor = rng.choice([0.1, 0.25, 0.5]); 
        n = rng.choice([1, 2, 10, Y - 1, Y, Y + 1, 20])
        g.annual_decline = (g.start - g.floor) / max(n, 1)

def m_boundary(s, rng, T):
    b = s.boundary
    k = rng.randrange(6)
    if k == 0: b.included_lifecycle_stages = rng.sample(list(model.LIFECYCLE_STAGES), rng.randrange(0, 15)) + rng.choice([[], ["D"], ["B6"]])
    elif k == 1: b.replacement_cycle = rng.choice(lives_for(T, rng))
    elif k == 2: b.reconstruction_scenario = rng.choice(["NONE", "REBUILD_IDENTICAL", "MAJOR_REFURBISHMENT", "???"])
    elif k == 3: b.reconstruction_scope_fraction = rng.choice([None, 0.0, 1.0, 0.3, 1.5, -0.2])
    elif k == 4: b.results_gas_scope = rng.choice(["CO2_ONLY", "CO2E_ALL_GASES"])
    elif k == 5: b.included_lifecycle_stages = [x for x in b.included_lifecycle_stages if x != rng.choice(["B2", "B6", "B1"])]

def m_misc(s, rng, T):
    k = rng.randrange(16)
    pr, sq, site, end = s.project, s.summary_quantities, s.construction, s.end_of_life
    if k == 0: pr.gross_floor_area = rng.choice([None, 0.0, -10.0, 1e-9, 1234.5])
    elif k == 1 and pr.use_area_breakdown:
        u = rng.choice(list(pr.use_area_breakdown)); pr.use_area_breakdown[u] *= rng.choice([1 + 1e-9, 1 + 2e-9, 1 + 1e-6, 1 + 2e-6, 1 - 0.5e-6, 0.0, 1.5])
    elif k == 2:
        name = rng.choice(["reinforcement_kg", "steel_kg", "concrete_m3", "timber_m3", "envelope_m2", "interior_m2", "timber_dry_density_kg_per_m3", "timber_carbon_fraction"])
        setattr(sq, name, rng.choice([0.0, -1.0, 5.0, 1e-9] + ([None] if name.startswith("timber_") and name != "timber_m3" else [])))
    elif k == 3: sq.concrete_uptake_factor_id = pick_fid(s, rng, "MEMO")
    elif k == 4: site.electricity_kwh = rng.choice([None, -1.0, 0.0, 5e4])
    elif k == 5 and site.fuels:
        f = rng.choice(site.fuels); j = rng.randrange(4)
        if j == 0: f.quantity = rng.choice([None, -1.0, 0.0, 100.0])
        elif j == 1: f.unit = rng.choice([None, "L", "kL", "m3", "MJ", "piece"])
        elif j == 2: f.factor_id = pick_fid(s, rng, "A5")
        else: f.conversions = [model.UnitConversion(f.unit, rng.choice(["L", "MJ", "kg", "m3"]), rng.choice([38.0, 0.0, None]), "fuzz")]
    elif k == 6 and site.waste_streams:
        w = rng.choice(site.waste_streams); w.mass_kg = rng.choice([None, -1.0, 0.0, 100.0]); w.factor_id = rng.choice([w.factor_id, pick_fid(s, rng, "A5")])
    elif k == 7 and end.demolition_activities:
        a = rng.choice(end.demolition_activities); j = rng.randrange(3)
        if j == 0: a.quantity = rng.choice([None, -1.0, 0.0, 10.0])
        elif j == 1: a.unit = rng.choice([None, "m2", "kg", "h"])
        else: a.factor_id = pick_fid(s, rng, "C1")
    elif k == 8 and end.waste_hauls:
        h = rng.choice(end.waste_hauls); j = rng.randrange(3)
        if j == 0: h.mass_t = rng.choice([None, -1.0, 0.0, 10.0])
        elif j == 1: h.distance_km = rng.choice([None, -1.0, 0.0, 10.0])
        else: h.factor_id = pick_fid(s, rng, "C2")
    elif k == 9 and s.cost_items:
        it = rng.choice(s.cost_items); j = rng.randrange(5)
        if j == 0: it.amount = rng.choice([None, -1.0, 0.0, 1e6])
        elif j == 1: it.currency = rng.choice([None, "kg", "XCU", it.currency])
        elif j == 2: it.factor_id = pick_fid(s, rng, "A1-A3")
        elif j == 3: it.price_year = rng.choice([it.price_year + 1, 1900, it.factor_base_year])
        else: it.factor_base_year = rng.choice([it.price_year, 1900, it.factor_base_year - 1])
    elif k == 10 and s.price_index:
        y = rng.choice(list(s.price_index)); s.price_index[y] = rng.choice([0.0, -1.0, None, 1e-9, 250.0])
        if rng.random() < 0.3: s.price_index.pop(y)
    elif k == 11 and s.cost_items:
        s.cost_items = rng.choice([[], s.cost_items + [copy.deepcopy(s.cost_items[0])], s.cost_items[::-1]])
    elif k == 12 and s.provenance:
        s.provenance.pop(rng.choice(list(s.provenance)))
    elif k == 13:
        owner = rng.choice(s.materials + s.equipment + s.refrigerants) if (s.materials or s.equipment or s.refrigerants) else None
        if owner is not None:
            owner.states[rng.choice(["quantity", "repair_rate", "gwp", "transport.mass_t", "service_life"])] = rng.choice(["DERIVED", "ESTIMATE", "MISSING", "EXPLICIT_ZERO", "OBSERVED"])
    elif k == 14:
        j = rng.randrange(4)
        if j == 0 and s.unit_conversions: s.unit_conversions.pop(rng.randrange(len(s.unit_conversions)))
        elif j == 1: s.unit_conversions.insert(0, model.UnitConversion(rng.choice(["t", "kg", "piece", "m2", "m3", "unit", "kWh"]), rng.choice(["kg", "t", "tkm", "m3", "MJ", "kWh"]), rng.choice([7.0, 0.0, None, -2.0]), "fuzz"))
        elif j == 2: s.unit_conversions.append(model.UnitConversion("piece", "kg", 12.0, "fuzz"))
        else: s.unit_conversions = list(reversed(s.unit_conversions))
    elif k == 15:
        g = rng.choice(s.gases); s.gwp[g] = rng.choice([0.0, 1.0, 30.0])

MUTATORS = [m_material] * 6 + [m_equipment] * 3 + [m_refrigerant] * 3 + [m_factor] * 3 + [m_operation] * 3 + [m_grid] * 3 + [m_boundary] * 2 + [m_misc] * 4

def build(seed):
    rng = random.Random(seed)
    T = rng.choice(ODD_PERIODS)
    opts = {"profile_kind": rng.choice([None, "CONSTANT", "LINEAR_TREND", "TABLE"]),
            "grid_kind": rng.choice([None, "CONSTANT", "LINEAR_DECLINE_TO_FLOOR", "STEPWISE", "TABLE"]),
            **dict(zip(("composite_share", "epd_share"), rng.choice([(0.0, 0.0), (0.3, 0.3), (1.0, 0.0), (0.0, 1.0), (0.5, 0.5), (0.3, 0.0)]))),
            "explicit_event_share": rng.choice([0.0, 0.5, 1.0]), "change_list_share": rng.choice([0.0, 0.5, 1.0]),
            "n_materials": rng.choice([0, 1, 5, 12]), "n_equipment": rng.choice([0, 1, 6]), "n_refrigerants": rng.choice([0, 1, 4])}
    if rng.random() < 0.5:
        opts["service_life_choices"] = [x for x in rng.sample(lives_for(T, rng), 4) if x is not None and x > 1e-2] or [10.0]
    if rng.random() < 0.3:
        opts["replacement_cycle"] = rng.choice([x for x in lives_for(T, rng) if x is not None and x > 1e-2]); opts["reconstruction_scenario"] = "REBUILD_IDENTICAL"
    structure, use = rng.choice(model.STRUCTURES), rng.choice(model.USES)
    s = synth.make_scenario(rng.randrange(1, 10**6), structure, use, "S", T, dirty=rng.random() < 0.2, scenario_id=f"FZ-{seed}", **opts)
    log = []
    for _ in range(rng.choice([0, 1, 2, 2, 3, 4, 6, 10])):
        m = rng.choice(MUTATORS)
        st = rng.getstate()
        try:
            m(s, rng, T)
            log.append(m.__name__)
        except Exception as e:
            log.append(f"{m.__name__}!{type(e).__name__}")
    return s, T, log
