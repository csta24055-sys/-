"""Adversarial input mutations for the exactness check.

Each mutation changes a valid fictional scenario into one with a defect or an extreme
value that the eight defect kinds of the generator do not cover. The list follows the
two independent numerical reviews of the study. A mutation returns nothing; it edits the
scenario in place. ``MUTATIONS`` maps a name to (function, generator options).

The second part of the list is generated: every numeric input that the first review
round left without a range check (annual profiles, grid factor, factor values, gas
amounts, conversion multipliers and others) is set to NaN, +inf, -inf, a negative number
and ``None``, one mutation per input and value.
"""
from __future__ import annotations

import copy
import math

from synth import population
from synth.model import GridStep

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



# ----------------------------------------------------------------- second review round

def _short_annual_tables(s):
    s.operation.gas.table = s.operation.gas.table[:10]
    s.water_waste.water.table = s.water_waste.water.table[:math.ceil(s.boundary.study_period) - 1]
    s.operation.electricity.table = s.operation.electricity.table[:10]


def _short_table_no_factor(s):
    s.water_waste.water.table = s.water_waste.water.table[:math.ceil(s.boundary.study_period) - 1]
    s.water_waste.water_factor_id = None
    s.operation.oil.table = s.operation.oil.table[:5]
    s.operation.oil_factor_id = "F-NOT-IN-TABLE"


def _short_table_bad_unit(s):
    s.operation.electricity.table = s.operation.electricity.table[:10]
    s.operation.onsite_generation.unit = "kWh/day"
    s.operation.gas.table = s.operation.gas.table[:10]
    s.operation.gas.unit = "m3/month"


def _short_grid_table(s):
    s.operation.grid.table = s.operation.grid.table[:10]


def _empty_tables(s):
    s.operation.grid.table = []
    s.operation.district_heat.table = []
    s.water_waste.sewage.table = []


def _factor_zero_with_gases(s):
    """A factor whose value is 0 while its gas amounts are not: the repair lines keep the gas amounts."""
    if s.equipment:
        s.equipment[0].repair_rate = 0.02
        s.factors[s.equipment[0].factor_id].value = 0.0
    for row in s.materials:
        if row.factor_id in s.factors:
            row.repair_rate = 0.01
            s.factors[row.factor_id].value = 0.0
            break


def _gases_contradict_value(s):
    """Gas amounts that do not add up to the factor value: X-04 and QA-01 must say so."""
    for row in s.materials:
        if row.factor_id in s.factors:
            s.factors[row.factor_id].gas_amounts["CO2"] *= 3.0
            break


def _zero_gwp_gas(s):
    s.gwp["NF3"] = 0.0
    if s.equipment:
        rec = s.factors[s.equipment[0].factor_id]
        rec.gas_amounts = {g: (7.0 if g == "NF3" else 0.0) for g in rec.gas_amounts}
        rec.value = 0.0
        s.equipment[0].repair_rate = 0.02


def _float_step_index(s):
    g = s.operation.grid
    g.kind, g.steps = "STEPWISE", [GridStep(0, 0.5), GridStep(3.0, 0.3)]


def _fractional_step_index(s):
    g = s.operation.grid
    g.kind, g.steps = "STEPWISE", [GridStep(0, 0.5), GridStep(2.5, 0.3)]


def _bool_step_index(s):
    g = s.operation.grid
    g.kind, g.steps = "STEPWISE", [GridStep(False, 0.5), GridStep(4, 0.3)]


def _factor_id_like_pseudo(name):
    def mutate(s):
        for row in s.materials:
            if row.factor_id in s.factors:
                rec = copy.deepcopy(s.factors[row.factor_id])
                rec.factor_id = name
                s.factors[name] = rec
                row.factor_id = name
                break
        if s.equipment:
            s.equipment[0].eol_factor_id = name       # wrong stage for this use: must be skipped, not confused
    return mutate


def _gas_list_duplicate(s):
    s.gases = list(s.gases) + ["CO2", "CH4"]


def _gas_list_without_co2(s):
    s.gases = [g for g in s.gases if g != "CO2"]


def _gas_list_empty(s):
    s.gases = []


def _gas_list_unknown(s):
    s.gases = list(s.gases) + ["XYZ"]                # no GWP and no amount for it


def _invalid_cycles(s):
    s.boundary.replacement_cycle = -25.0
    s.boundary.reconstruction_scenario = "REBUILD_IDENTICAL"
    s.boundary.reconstruction_scope_fraction = 1.0
    for row in s.materials:
        if row.refresh_cycle is not None:
            row.refresh_cycle = -row.refresh_cycle
    for eq in s.equipment:
        eq.service_life = float("nan")
    for dev in s.refrigerants:
        dev.service_life = -3.0


def _rebuild_cycle(value):
    def mutate(s):
        s.boundary.reconstruction_scenario = "REBUILD_IDENTICAL"
        s.boundary.reconstruction_scope_fraction = 1.0
        s.boundary.replacement_cycle = value
    return mutate


def _none_in_event_lists(s):
    nan = float("nan")
    for i, eq in enumerate(s.equipment):
        eq.replacement_event_list = [[None, 10, 20], [nan, 5], [float("inf"), 7, 7], [None], [12, None, 12.0]][i % 5]
    for i, dev in enumerate(s.refrigerants):
        dev.change_years, dev.service_life = [[None, 7], [nan], [float("-inf"), 9, 2]][i % 3], None


def _units_named_none(s):
    """Units literally called "None": a valid (if odd) unit name, not a missing unit."""
    s.operation.electricity.unit = s.operation.onsite_generation.unit = s.operation.onsite_export.unit = "None/year"
    s.operation.grid.unit = "kgCO2e/None"


def _baseline_not_registered(s):
    s.boundary.baseline_scenario = "NO-SUCH-SCENARIO"


def _baseline_incomplete(s):
    base = population.attach_baseline(s)
    for row in base.materials[:4]:
        row.quantity = None


def _proposal_incomplete(s):
    population.attach_baseline(s)
    for row in s.materials[:2]:
        row.quantity = None


def _baseline_bad_grid(s):
    base = population.attach_baseline(s)
    base.operation.grid.annual_decline = float("nan")
    base.operation.grid.start = float("inf")


def _period_beyond_tables(s):
    """A study period longer than every year table: series that need the table are unusable, nothing raises."""
    s.boundary.study_period = 500.0


def _repeated_event_years(s):
    for eq in s.equipment:
        eq.replacement_event_list = [15, 15, 15]
    for dev in s.refrigerants:
        dev.change_years, dev.service_life = [9, 9.0], None


MUTATIONS.update({
    "short_annual_tables": (_short_annual_tables, {"profile_kind": "TABLE"}),
    "short_annual_table_copies": (_short_annual_tables, {"profile_kind": "LINEAR_TREND"}),
    "short_annual_table_and_no_factor": (_short_table_no_factor, {"profile_kind": "TABLE"}),
    "short_annual_table_and_bad_unit": (_short_table_bad_unit, {"profile_kind": "TABLE"}),
    "short_grid_table": (_short_grid_table, {"grid_kind": "TABLE"}),
    "short_grid_table_copy": (_short_grid_table, {"grid_kind": "STEPWISE", "profile_kind": "CONSTANT"}),
    "empty_year_tables": (_empty_tables, {"grid_kind": "TABLE", "profile_kind": "TABLE"}),
    "factor_value_zero_with_gas_amounts": (_factor_zero_with_gases, {"composite_share": 0.0, "epd_share": 0.0}),
    "gas_amounts_contradict_value": (_gases_contradict_value, {"composite_share": 0.0, "epd_share": 0.0}),
    "gas_with_zero_gwp": (_zero_gwp_gas, {"composite_share": 0.0, "epd_share": 0.0}),
    "step_index_float": (_float_step_index, {"profile_kind": "CONSTANT"}),
    "step_index_fractional": (_fractional_step_index, {"profile_kind": "LINEAR_TREND"}),
    "step_index_bool": (_bool_step_index, {"profile_kind": "TABLE"}),
    "factor_id_named_GRID": (_factor_id_like_pseudo("GRID"), {"composite_share": 0.0, "epd_share": 0.0}),
    "factor_id_named_REFRIGERANT": (_factor_id_like_pseudo("REFRIGERANT"), {"composite_share": 0.0, "epd_share": 0.0}),
    "gas_list_with_duplicates": (_gas_list_duplicate, {"composite_share": 0.5, "epd_share": 0.2}),
    "gas_list_without_co2": (_gas_list_without_co2, {"composite_share": 0.5, "epd_share": 0.2}),
    "gas_list_empty": (_gas_list_empty, {"composite_share": 0.5, "epd_share": 0.2}),
    "gas_list_with_unknown_gas": (_gas_list_unknown, {"composite_share": 0.5, "epd_share": 0.2}),
    "invalid_cycles": (_invalid_cycles, {"explicit_event_share": 0.0, "change_list_share": 0.0}),
    "rebuild_cycle_missing": (_rebuild_cycle(None), {}),
    "rebuild_cycle_zero": (_rebuild_cycle(0.0), {}),
    "rebuild_cycle_infinite": (_rebuild_cycle(float("inf")), {}),
    "rebuild_cycle_nan": (_rebuild_cycle(float("nan")), {}),
    "none_in_event_lists": (_none_in_event_lists, {"n_refrigerants": 6}),
    "repeated_event_years": (_repeated_event_years, {}),
    "units_named_None": (_units_named_none, {}),
    "baseline_not_registered": (_baseline_not_registered, {}),
    "baseline_incomplete": (_baseline_incomplete, {}),
    "proposal_incomplete": (_proposal_incomplete, {}),
    "baseline_with_unusable_grid": (_baseline_bad_grid, {"grid_kind": "LINEAR_DECLINE_TO_FLOOR"}),
    "period_beyond_year_tables": (_period_beyond_tables, {"profile_kind": "TABLE", "grid_kind": "TABLE"}),
    "period_beyond_year_table_copies": (_period_beyond_tables, {"profile_kind": "LINEAR_TREND", "grid_kind": "STEPWISE"}),
})

BAD_VALUES = {"nan": float("nan"), "inf": float("inf"), "minus_inf": float("-inf"), "negative": -1.0, "none": None}


def _first_factor(s, stage):
    return next((f for f in s.factors.values() if f.stages == [stage]), None)


def _set_factor_values(s, v):
    for row in s.materials:
        if row.factor_id in s.factors:
            s.factors[row.factor_id].value = v
            break
    if s.equipment and s.equipment[0].factor_id in s.factors:
        s.factors[s.equipment[0].factor_id].value = v
    if s.operation.gas_factor_id in s.factors:
        s.factors[s.operation.gas_factor_id].value = v
    for row in s.materials:
        if row.composition and row.composition[0].factor_id in s.factors:
            s.factors[row.composition[0].factor_id].value = v
            break
    for row in s.materials:
        if row.epd is not None and row.epd.factor_id in s.factors:
            s.factors[row.epd.factor_id].value = v
            break


def _set_gas_amounts(s, v):
    for row in s.materials:
        if row.factor_id in s.factors:
            s.factors[row.factor_id].gas_amounts["CH4"] = v
            break
    if s.water_waste.water_factor_id in s.factors:
        s.factors[s.water_waste.water_factor_id].gas_amounts["CO2"] = v
    for row in s.materials:
        if row.end_of_life.routes and row.end_of_life.routes[0].factor_id in s.factors:
            s.factors[row.end_of_life.routes[0].factor_id].gas_amounts["N2O"] = v
            break


def _set_conversions(s, v):
    n = 0
    for row in s.materials:
        if row.conversions and n < 2:
            row.conversions[0].factor = v
            n += 1
    for conv in s.unit_conversions:
        if (conv.from_unit, conv.to_unit) in (("kg", "t"), ("kWh", "MJ"), ("L", "m3")):
            conv.factor = v


def _conversions_and_units(s, v):
    """Conversions that are actually needed: electricity in MWh against a grid factor per MJ."""
    s.operation.electricity.unit = "MWh/year"
    s.operation.grid.unit = "kgCO2e/MJ"
    for conv in s.unit_conversions:
        if (conv.from_unit, conv.to_unit) in (("MWh", "MJ"), ("kWh", "MJ"), ("kWh", "MWh")):
            conv.factor = v
    for eq in s.equipment[:2]:
        if eq.eol_factor_id in s.factors:
            s.factors[eq.eol_factor_id].unit = "t"
    for conv in s.unit_conversions:
        if (conv.from_unit, conv.to_unit) == ("kg", "t"):
            conv.factor = v


def _set_step_value(s, v):
    g = s.operation.grid
    if g.steps:
        g.steps[min(1, len(g.steps) - 1)].value = v


def _set_table_entries(s, v):
    s.operation.gas.table[3] = v
    s.water_waste.municipal_waste.table[0] = v
    s.operation.onsite_export.table[math.ceil(s.boundary.study_period) - 1] = v


def _set_copy_entries(s, v):
    """An entry of a redundant table copy: the descriptor is used, the copy check must report it."""
    s.operation.gas.table[2] = v
    s.operation.electricity.table[0] = v
    s.operation.grid.table[1] = v


def _set_other_inputs(which):
    def mutate(s, v):
        if which == "route_fraction" and s.materials:
            s.materials[0].end_of_life.routes[1].fraction = v
            s.materials[-1].end_of_life.routes[3].fraction = v
        elif which == "summary_quantity":
            s.summary_quantities.concrete_m3 = s.summary_quantities.reinforcement_kg = v
            s.summary_quantities.timber_m3 = v
        elif which == "use_area":
            key = sorted(s.project.use_area_breakdown)[0]
            s.project.use_area_breakdown[key] = v
        elif which == "gross_floor_area":
            s.project.gross_floor_area = v
        elif which == "price_index" and s.cost_items:
            s.price_index[s.cost_items[0].price_year] = v
            s.price_index[s.cost_items[-1].factor_base_year] = v
        elif which == "load_factor_and_haul" and s.materials:
            s.materials[0].transport.load_factor = v
            s.materials[1 % len(s.materials)].end_of_life.haul_distance_km = v
        elif which == "gwp":
            s.gwp["CH4"] = v
        elif which == "shares":
            s.operation.facility_management_ratio = v
            s.boundary.reconstruction_scope_fraction = v
            s.boundary.reconstruction_scenario = "REBUILD_IDENTICAL"
            s.boundary.replacement_cycle = 25.0
        elif which == "memo_inputs":
            s.summary_quantities.timber_dry_density_kg_per_m3 = v
            s.operation.electricity_per_m2_per_year = v
        elif which == "costs_and_site" and s.cost_items:
            s.cost_items[0].amount = v
            s.construction.electricity_kwh = v
            if s.construction.waste_streams:
                s.construction.waste_streams[0].mass_kg = v
    return mutate


def _attr(path):
    """Setter of one dotted attribute path below the scenario."""
    names = path.split(".")

    def mutate(s, v):
        obj = s
        for name in names[:-1]:
            obj = getattr(obj, name)
        setattr(obj, names[-1], v)
    return mutate


def _several(*setters):
    def mutate(s, v):
        for setter in setters:
            setter(s, v)
    return mutate


LINEAR = {"profile_kind": "LINEAR_TREND"}
BAD_VALUE_TARGETS = {
    "annual_base": (_several(_attr("operation.gas.base"), _attr("water_waste.water.base")), LINEAR),
    "annual_base_constant": (_several(_attr("operation.oil.base"), _attr("water_waste.sewage.base")), {"profile_kind": "CONSTANT"}),
    "electricity_base": (_attr("operation.electricity.base"), LINEAR),
    "generation_base": (_attr("operation.onsite_generation.base"), {"profile_kind": "CONSTANT"}),
    "annual_slope": (_several(_attr("operation.oil.slope"), _attr("water_waste.sewage.slope"),
                              _attr("operation.onsite_export.slope")), LINEAR),
    "electricity_slope": (_attr("operation.electricity.slope"), LINEAR),
    "annual_table_entry": (_set_table_entries, {"profile_kind": "TABLE"}),
    "table_copy_entry": (_set_copy_entries, {"profile_kind": "LINEAR_TREND", "grid_kind": "LINEAR_DECLINE_TO_FLOOR"}),
    "grid_start": (_attr("operation.grid.start"), {"grid_kind": "LINEAR_DECLINE_TO_FLOOR"}),
    "grid_start_constant": (_attr("operation.grid.start"), {"grid_kind": "CONSTANT", "profile_kind": "CONSTANT"}),
    "grid_floor": (_attr("operation.grid.floor"), {"grid_kind": "LINEAR_DECLINE_TO_FLOOR", "profile_kind": "LINEAR_TREND"}),
    "grid_decline": (_attr("operation.grid.annual_decline"), {"grid_kind": "LINEAR_DECLINE_TO_FLOOR", "profile_kind": "CONSTANT"}),
    "grid_step_value": (_set_step_value, {"grid_kind": "STEPWISE", "profile_kind": "LINEAR_TREND"}),
    "grid_table_entry": (lambda s, v: s.operation.grid.table.__setitem__(4, v), {"grid_kind": "TABLE", "profile_kind": "CONSTANT"}),
    "grid_construction_value": (_attr("operation.grid.construction_value"), {}),
    "factor_value": (_set_factor_values, {"composite_share": 0.3, "epd_share": 0.3, "epd_inapplicable_share": 0.0}),
    "gas_amount": (_set_gas_amounts, {"composite_share": 0.0, "epd_share": 0.0}),
    "conversion_multiplier": (_set_conversions, {"composite_share": 0.5}),
    "conversion_multiplier_needed": (_conversions_and_units, {}),
    "route_fraction": (_set_other_inputs("route_fraction"), {}),
    "summary_quantity": (_set_other_inputs("summary_quantity"), {}),
    "use_area": (_set_other_inputs("use_area"), {"multi_use": True}),
    "gross_floor_area": (_set_other_inputs("gross_floor_area"), {}),
    "price_index": (_set_other_inputs("price_index"), {}),
    "load_factor_and_haul_distance": (_set_other_inputs("load_factor_and_haul"), {}),
    "gwp_of_a_gas": (_set_other_inputs("gwp"), {}),
    "shares": (_set_other_inputs("shares"), {}),
    "memo_inputs": (_set_other_inputs("memo_inputs"), {}),
    "costs_and_site": (_set_other_inputs("costs_and_site"), {}),
}


def _bound(setter, value):
    return lambda s: setter(s, value)


for _target, (_setter, _options) in BAD_VALUE_TARGETS.items():
    for _label, _value in BAD_VALUES.items():
        MUTATIONS[f"{_target}_{_label}"] = (_bound(_setter, _value), _options)

# study periods and renewal periods whose product meets the end of the period in decimal but not in binary;
# 1.000000001 is the double for which period*(1 - 1e-9) rounds to exactly 1.0 (second review, NUM-1)
DECIMAL_BOUNDARIES = ((99.9, [33.3, 11.1, 16.65, 0.3]), (55.5, [2.2, 18.5, 11.1]), (60.0, [0.1, 0.3, 1.2, 7.5]),
                      (0.3, [0.1]), (12.3, [4.1, 1.23]), (60.0, [1.000000001]), (30.0, [1.000000001, 2.000000002, 0.999999999]),
                      (7.0, [1.000000001, 1.0000000010000003, 1.0000000009999998]))
STAGE_SUBSETS = (["B3"], ["B6"], ["B2"], ["B6", "B2"], ["A1-A3", "C3"], ["B4", "B3", "B1"], ["B5"], [])
# stage subsets whose upstream rows carry a defect: the total must be marked incomplete although the
# stage of the defective unit is outside the boundary (second review, RED-1)
UPSTREAM_DEFECT_SUBSETS = (["B3"], ["B5"], ["B3", "B5"], ["B4"], ["B6"], ["B2"], ["B2", "B6"], ["A4"], ["C3", "C4"])


def _defect_missing_quantity(s):
    for row in sorted(s.materials, key=lambda r: -(r.quantity or 0.0))[:3]:
        row.quantity = None
    if s.equipment:
        s.equipment[0].factor_id = "F-NOT-IN-TABLE"


def _defect_unlicensed_factor(s):
    for row in s.materials:
        if row.factor_id in s.factors:
            s.factors[row.factor_id].licence_status = "RESTRICTED"
            break
    for row in s.materials:
        if row.end_of_life.haul_factor_id in s.factors:
            s.factors[row.end_of_life.haul_factor_id].licence_status = "UNKNOWN"
            break


def _defect_invalid_cycle(s):
    for row in s.materials[:2]:
        row.refresh_cycle = -5.0
    if s.equipment:
        s.equipment[-1].service_life = float("inf")
    s.boundary.replacement_cycle = float("nan")


def _defect_operation(s):
    s.operation.facility_management_ratio = None
    s.operation.gas.base = -1.0
    s.operation.gas.table = [-1.0] * len(s.operation.gas.table)
    s.operation.grid.construction_value = float("nan")


def _defect_grid(s):
    g = s.operation.grid
    g.kind, g.start, g.steps = "TABLE", None, None
    g.table = g.table[:3]


UPSTREAM_DEFECTS = {"missing_quantity_and_unknown_factor": _defect_missing_quantity,
                    "unlicensed_factor": _defect_unlicensed_factor, "invalid_cycle": _defect_invalid_cycle,
                    "operation_inputs": _defect_operation, "grid_unusable": _defect_grid}
# the only inputs that make the calculation refuse to run
INVALID_PERIODS = (0.0, -5.0, float("nan"), float("inf"), float("-inf"), None)
