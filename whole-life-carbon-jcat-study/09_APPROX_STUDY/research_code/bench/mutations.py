"""Adversarial input mutations for the exactness check.

Each mutation changes a valid fictional scenario into one with a defect or an extreme
value that the eight defect kinds of the generator do not cover. The list follows the
independent numerical review of the study. A mutation returns nothing; it edits the
scenario in place. ``MUTATIONS`` maps a name to (function, generator options).
"""
from __future__ import annotations

import copy

from synth import population

SMALL = {"n_materials": 12, "n_equipment": 6, "n_refrigerants": 4}


def _grid_entry(s):
    s.operation.grid.table[10] *= 2.0


def _profile_entries(s):
    s.water_waste.water.table[5] *= 3.0
    s.operation.electricity.table[5] *= 3.0
    s.operation.gas.table[7] *= 0.25


def _constant_with_slope(s):
    for p in (s.water_waste.water, s.operation.electricity, s.operation.gas):
        if p.kind == "CONSTANT":
            p.slope = 5.0


def _linear_clamped_table(s):
    p = s.operation.electricity
    if p.kind == "LINEAR_TREND":
        p.slope = -abs(p.base) / 20.0
        p.table = [max(0.0, p.base + p.slope * k) for k in range(len(p.table))]


def _linear_negative_demand(s):
    p = s.operation.electricity
    if p.kind == "LINEAR_TREND":
        p.slope = -abs(p.base) / 20.0
        p.table = [p.base + p.slope * k for k in range(len(p.table))]


def _missing_records(s):
    if len(s.equipment) > 1:
        s.equipment[0].factor_id = s.equipment[1].factor_id = "F-NOT-IN-TABLE"
    if s.materials:
        s.materials[0].end_of_life.routes[0].factor_id = None
        s.materials[0].end_of_life.haul_factor_id = None
        s.materials[-1].transport.factor_id = "F-NOT-IN-TABLE"
    s.water_waste.waste_factor_id = None
    s.operation.oil_factor_id = "F-NOT-IN-TABLE"
    s.summary_quantities.concrete_uptake_factor_id = "F-NOT-IN-TABLE"
    for row in s.materials:
        if row.composition:
            row.composition[0].factor_id = None
            break
    if s.cost_items:
        s.cost_items[0].factor_id = None


def _stage_tags(s):
    for fid in ("F-TR-TRUCK_LARGE", "F-TR-TRUCK_SMALL", "F-HAUL-1", "F-SITE-DIESEL", "F-OP-GAS", "F-WATER"):
        if fid in s.factors:
            s.factors[fid].stages = ["A1-A3"]
    for row in s.materials[:3]:
        fid = row.end_of_life.routes[3].factor_id
        if fid in s.factors:
            s.factors[fid].stages = ["C3"]
    for row in s.materials:
        if row.composition:
            s.factors[row.composition[0].factor_id].stages = ["A1-A3", "A4"]
            break


def _factor_units(s):
    for eq in s.equipment[:2]:
        if eq.eol_factor_id in s.factors:
            s.factors[eq.eol_factor_id].unit = "t"            # convertible: the result must scale by 1/1000
    if "F-HAUL-1" in s.factors:
        s.factors["F-HAUL-1"].unit = "kgkm"                    # not convertible
    if "F-TR-RAIL" in s.factors:
        s.factors["F-TR-RAIL"].unit = "t"
    for row in s.materials[:2]:
        fid = row.end_of_life.routes[1].factor_id
        if fid in s.factors:
            s.factors[fid].unit = "t"
    for row in s.materials:
        if row.composition:
            s.factors[row.composition[-1].factor_id].unit = "t"
            break


def _electricity_units(s):
    s.operation.electricity.unit = "MWh/year"
    s.operation.grid.unit = "kgCO2e/MJ"


def _grid_unit_unknown(s):
    s.operation.grid.unit = "kgCO2e/barrel"


def _month_units(s):
    s.operation.gas.unit = "m3/month"
    s.water_waste.sewage.unit = "m3"
    s.operation.onsite_generation.unit = "kWh/day"


def _negative_values(s):
    if len(s.materials) > 4:
        s.materials[1].quantity = -5.0
        s.materials[2].end_of_life.mass_kg = -1.0
        s.materials[3].transport.distance_km = -10.0
        s.materials[4].end_of_life.routes[0].fraction = -0.2
        s.materials[0].repair_rate = -0.01
        s.materials[0].waste_rate = 1.0
        s.materials[1].unquantified_cost_ratio = 1.2
        s.materials[2].unquantified_cost_ratio = -0.2
        s.materials[3].reuse_rate = 1.5
        s.materials[4].transport.load_factor = 0.0
    if s.equipment:
        s.equipment[0].quantity = -1.0
        s.equipment[-1].end_of_life_mass_kg = -3.0
        s.equipment[-1].repair_rate = -0.5
    if s.cost_items:
        s.cost_items[-1].amount = -100.0
    s.construction.electricity_kwh = -1.0
    if s.construction.fuels:
        s.construction.fuels[0].quantity = -2.0


def _ratios_out_of_range(s):
    for i, dev in enumerate(s.refrigerants):
        if i % 4 == 0:
            dev.annual_leak_rate = 1.3
        elif i % 4 == 1:
            dev.end_of_life_recovery_rate = 1.3
        elif i % 4 == 2:
            dev.replacement_loss_rate = -0.1
        else:
            dev.gwp = -5.0
    s.operation.facility_management_ratio = 1.5
    s.boundary.reconstruction_scope_fraction = 1.7
    s.boundary.reconstruction_scenario = "REBUILD_IDENTICAL"
    s.boundary.replacement_cycle = 25.0


def _nan_inf(s):
    nan, inf = float("nan"), float("inf")
    if len(s.materials) > 3:
        s.materials[0].refresh_cycle = nan
        s.materials[1].refresh_cycle = inf
        s.materials[2].quantity = nan
        s.materials[3].refresh_cycle = 0.0
    if len(s.equipment) > 1:
        s.equipment[0].service_life = nan
        s.equipment[1].service_life = -4.0
    if s.refrigerants:
        s.refrigerants[0].annual_leak_rate = nan
        s.refrigerants[-1].service_life, s.refrigerants[-1].change_years = inf, None


def _event_lists(s):
    T = s.boundary.study_period
    for i, eq in enumerate(s.equipment):
        eq.replacement_event_list = [[0, 10, 10, 30], [T, 5], [25, 3, 3.5, 12.25], [-2, 7], [], [T - 1e-12, 1]][i % 6]
    for i, dev in enumerate(s.refrigerants):
        dev.change_years, dev.service_life = [[0], [T], [7, 7, 7], [9, 2, 2.5]][i % 4], None


def _tiny_leaks(s):
    for i, dev in enumerate(s.refrigerants):
        dev.annual_leak_rate = (1e-9, 1e-7, 1e-12, 0.0)[i % 4]
        dev.top_up = False


def _steps_unsorted(s):
    g = s.operation.grid
    if g.steps:
        g.steps = list(reversed(g.steps))


def _steps_late_start(s):
    g = s.operation.grid
    if g.steps:
        g.steps[0].from_index = 2


def _steps_empty(s):
    g = s.operation.grid
    if g.kind == "STEPWISE":
        g.steps = []


def _linear_rising(s):
    g = s.operation.grid
    if g.kind == "LINEAR_DECLINE_TO_FLOOR":
        g.annual_decline = -abs(g.annual_decline)


def _start_below_floor(s):
    g = s.operation.grid
    if g.kind == "LINEAR_DECLINE_TO_FLOOR":
        g.floor = g.start * 2.0


def _unknown_grid_kind(s):
    s.operation.grid.kind = "SPLINE"


def _self_baseline(s):
    population.BASELINES[s.meta.scenario_id] = s
    s.boundary.baseline_scenario = s.meta.scenario_id


def _mutual_baseline(s):
    other = copy.deepcopy(s)
    other.meta.scenario_id = s.meta.scenario_id + "-TWIN"
    for row in other.materials[::3]:
        if row.quantity is not None:
            row.quantity *= 1.1
    other.boundary.baseline_scenario = s.meta.scenario_id
    s.boundary.baseline_scenario = other.meta.scenario_id
    population.BASELINES[s.meta.scenario_id] = s
    population.BASELINES[other.meta.scenario_id] = other


def _baseline_other_area(s):
    base = population.attach_baseline(s)
    base.project.gross_floor_area = (base.project.gross_floor_area or 1.0) * 1.5
    base.boundary.included_lifecycle_stages = base.boundary.included_lifecycle_stages[:-1]


def _edited_baseline(s):
    base = population.attach_baseline(s)
    for row in base.materials:
        if row.quantity is not None:
            row.quantity *= 2.0


def _same_label_other_content(s):
    rows = [r for r in s.materials if r.composition]
    if len(rows) >= 2:
        rows[1].specification = rows[0].specification
        rows[1].composition = copy.deepcopy(rows[0].composition)
        rows[1].composition[0].mass_fraction, rows[1].composition[-1].mass_fraction = (
            rows[1].composition[-1].mass_fraction, rows[1].composition[0].mass_fraction)


def _negative_fraction_recipe(s):
    for row in s.materials:
        if row.composition and len(row.composition) >= 2:
            a, b = row.composition[0], row.composition[1]
            a.mass_fraction, b.mass_fraction = a.mass_fraction + b.mass_fraction + 0.25, -0.25
            break


def _epd_declaration_differs(s):
    n = 0
    for row in s.materials:
        if row.epd is not None:
            if n % 3 == 0:
                row.epd.valid_until = "2000-01-01"
            elif n % 3 == 1:
                row.epd.declared_stages = ["A1-A3", "A4"]
            else:
                row.epd.declared_unit = "piece"
            n += 1


def _price_index_gaps(s):
    if s.cost_items:
        s.price_index.pop(s.cost_items[0].price_year, None)
        s.price_index[s.cost_items[-1].factor_base_year] = 0.0


def _unlicensed_grid(s):
    s.operation.grid.licence_status = "UNKNOWN"


def _missing_area(s):
    s.project.gross_floor_area = None


def _zero_intensity_inputs(s):
    s.summary_quantities.timber_m3 = -1.0
    s.operation.electricity_per_m2_per_year = -3.0


MUTATIONS = {
    "grid_table_entry_differs": (_grid_entry, {}),
    "grid_table_entry_differs_linear": (_grid_entry, {"grid_kind": "LINEAR_DECLINE_TO_FLOOR", "profile_kind": "LINEAR_TREND"}),
    "grid_table_entry_differs_constant": (_grid_entry, {"grid_kind": "CONSTANT", "profile_kind": "CONSTANT"}),
    "profile_table_entries_differ": (_profile_entries, {"profile_kind": "CONSTANT", "grid_kind": "CONSTANT"}),
    "profile_table_entries_differ_linear": (_profile_entries, {"profile_kind": "LINEAR_TREND"}),
    "constant_profile_with_slope": (_constant_with_slope, {"profile_kind": "CONSTANT"}),
    "linear_profile_clamped_table": (_linear_clamped_table, {"profile_kind": "LINEAR_TREND"}),
    "linear_profile_negative_demand": (_linear_negative_demand, {"profile_kind": "LINEAR_TREND"}),
    "missing_factor_records": (_missing_records, {"composite_share": 0.5, "epd_share": 0.2}),
    "stage_tags_wrong": (_stage_tags, {"composite_share": 0.5, "epd_share": 0.2}),
    "factor_units_changed": (_factor_units, {"composite_share": 0.5, "epd_share": 0.2}),
    "electricity_in_other_units": (_electricity_units, {}),
    "grid_unit_unknown": (_grid_unit_unknown, {}),
    "time_base_not_year": (_month_units, {}),
    "negative_values": (_negative_values, {}),
    "ratios_out_of_range": (_ratios_out_of_range, {"n_refrigerants": 8}),
    "nan_and_infinite_values": (_nan_inf, {}),
    "odd_event_lists": (_event_lists, {"n_refrigerants": 8}),
    "tiny_leak_rates": (_tiny_leaks, {"n_refrigerants": 8}),
    "steps_unsorted": (_steps_unsorted, {"grid_kind": "STEPWISE", "profile_kind": "CONSTANT"}),
    "steps_start_late": (_steps_late_start, {"grid_kind": "STEPWISE", "profile_kind": "CONSTANT"}),
    "steps_empty": (_steps_empty, {"grid_kind": "STEPWISE"}),
    "linear_grid_rising": (_linear_rising, {"grid_kind": "LINEAR_DECLINE_TO_FLOOR", "profile_kind": "CONSTANT"}),
    "linear_grid_start_below_floor": (_start_below_floor, {"grid_kind": "LINEAR_DECLINE_TO_FLOOR"}),
    "unknown_grid_kind": (_unknown_grid_kind, {}),
    "baseline_is_itself": (_self_baseline, {}),
    "baselines_name_each_other": (_mutual_baseline, {}),
    "baseline_not_comparable": (_baseline_other_area, {}),
    "baseline_edited": (_edited_baseline, {}),
    "same_label_other_composition": (_same_label_other_content, {"composite_share": 1.0, "epd_share": 0.0}),
    "negative_fraction_in_recipe": (_negative_fraction_recipe, {"composite_share": 1.0, "epd_share": 0.0}),
    "epd_declaration_differs": (_epd_declaration_differs, {"composite_share": 0.0, "epd_share": 1.0, "epd_inapplicable_share": 0.0}),
    "price_index_gaps": (_price_index_gaps, {}),
    "unlicensed_grid": (_unlicensed_grid, {}),
    "missing_area": (_missing_area, {}),
    "invalid_memo_inputs": (_zero_intensity_inputs, {}),
}

# study periods and renewal periods whose product meets the end of the period in decimal but not in binary
DECIMAL_BOUNDARIES = ((99.9, [33.3, 11.1, 16.65, 0.3]), (55.5, [2.2, 18.5, 11.1]), (60.0, [0.1, 0.3, 1.2, 7.5]),
                      (0.3, [0.1]), (12.3, [4.1, 1.23]))
STAGE_SUBSETS = (["B3"], ["B6"], ["B2"], ["B6", "B2"], ["A1-A3", "C3"], ["B4", "B3", "B1"], ["B5"], [])
INVALID_PERIODS = (0.0, -5.0, float("nan"), float("inf"), 500.0)
