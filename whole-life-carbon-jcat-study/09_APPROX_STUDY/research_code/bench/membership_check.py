#!/usr/bin/env python3
"""Fault injection: which results of the unified model depend on which shared object.

The study counts an evaluation unit as "unified into a model" only when its value is read
from a shared table or produced by a shared parameterised function. This script does not
take that from the text of a record. It breaks each shared object of ``fastcalc`` on
purpose, one at a time, and records which units' public results change:

  * a shared FUNCTION is replaced from outside (the attribute of the module or class is
    set to a wrapper that falsifies the result) for the duration of one run;
  * a shared TABLE is falsified between the two steps of the unified model: after
    ``engine.aggregate`` has built it and before ``engine.finish`` reads it.

Nothing in ``fastcalc`` knows about this script and no hook exists for it: the objects it
replaces are the ones the calculation itself uses. The run without any fault is compared
with the reference calculation first, so that "the result changes" means the same as
"the comparison with the reference would fail".

How to read the result. A unit that does NOT react to any shared object of a model is
not computed from that model's shared structure, whatever a record says. A unit that
reacts is not thereby proven to be a member: every result downstream of a shared object
reacts as well (the whole-life total reacts to almost everything). Sensitivity is the
necessary condition, the code is the sufficient one.

A second, narrower measurement is added for the shared functions that return numbers:
their return values are marked (a float or int subclass that any arithmetic turns back
into a plain number) and the public results are searched for marked leaves. A unit with
such a leaf returns the function's value as it is ("direct output"). This is a lower
bound: a unit that adds two such values, or a verdict (a bool cannot be marked), is
produced by the function without showing a marked leaf.

All data are synthetic and fictional.

Run:
    cd research_code && python3 -B -m bench.membership_check [--out FILE] [--claims MODELS_JSON]
"""
from __future__ import annotations

import argparse
import contextlib
import json
import sys
from collections import Counter
from pathlib import Path

import synth
from common.compare import compare, flatten
from fastcalc import closed_forms as cf
from fastcalc import engine
from refcalc import registry
from synth import model, population

STUDY = Path(__file__).resolve().parents[2]
OUT = STUDY / "04_VERIFICATION" / "membership_check.json"
TOL = 1e-9
FLOOR = 0.0
MODES = (("full", True), ("totals", False))


# ------------------------------------------------------------------------------------------ the faults

def _scale(table, k=1.5):
    for key in table:
        table[key] *= k


def _tables_scaled(A):
    for table in A.tables.values():
        _scale(table)
    for routes in A.route_tables.values():
        for table in routes.values():
            _scale(table)


def _tables_first_factor_key_removed(A):
    tables = list(A.tables.values()) + [t for routes in A.route_tables.values() for t in routes.values()]
    for table in tables:
        for key in table:
            if not isinstance(key, engine.PseudoKey):
                del table[key]
                break


def _groups_scaled(A):
    for group in A.groups.values():
        _scale(group.u)
        _scale(group.r)
        group.resource *= 1.5
        group.waste *= 1.5


def _charges_scaled(A):
    A.charges[:] = [c * 1.5 if c is not None else None for c in A.charges]


def _recipe_masses_scaled(A):
    for recipe in A.recipes.values():
        recipe["kg"] *= 1.5


def _every_factor_unlicensed(A):
    A.unlicensed.update(A.scn.factors)


def _times(k):
    return lambda original: lambda *a: k * original(*a)


def _pair_times(k):
    return lambda original: lambda *a: tuple(k * x for x in original(*a))


def _list_times(k):
    return lambda original: lambda *a: [k * x for x in original(*a)]


def _negated(original):
    return lambda *a: not original(*a)


def _constant(value):
    return lambda original: lambda *a: value


def _one_event_fewer(original):
    return lambda T, period: max(original(T, period) - 1, 0)


def _one_year_earlier(original):
    return lambda *a: [max(1, y - 1) for y in original(*a)]


def _year_earlier(original):
    return lambda tau: max(1, original(tau) - 1)


def _last_dropped(original):
    return lambda *a: original(*a)[:-1]


def _fractions_times(k):
    def make(original):
        def broken(*a):
            leaked, before, end = original(*a)
            return k * leaked, [k * b for b in before], k * end
        return broken
    return make


def _purchased_times(k):
    def make(original):
        def broken(*a):
            net, elec, weighted = original(*a)
            return [k * v for v in net], [k * v for v in elec], k * weighted
        return broken
    return make


def _first_stage_left_out(original):
    return lambda by_stage, subset, divisor=1.0: original(by_stage, subset[1:], divisor)


def _leak_series_times(k):
    return lambda original: lambda out, charge, *rest: original(out, k * charge, *rest)


def _convert_times(k):
    def make(original):
        def broken(self, u, v, extra=()):
            c = original(self, u, v, extra)
            return c * k if c is not None and u != v else c
        return broken
    return make


def _convert_missing(original):
    def broken(self, u, v, extra=()):
        return original(self, u, v, extra) if u == v else None
    return broken


def _recipe_value_times(k):
    def make(original):
        def broken(key, resolver):
            recipe = original(key, resolver)
            if recipe["value"] is not None:
                recipe["value"] = resolver.fval[key] = k * recipe["value"]
            return recipe
        return broken
    return make


# name -> (model, kind, where, what is done to it, fault). A fault is either a function of the Aggregate
# (kind "table": applied between aggregate and finish) or (owner, attribute, wrapper factory) (kind "function").
SHARED_OBJECTS = {
    "K1.tables:scaled": ("K1", "table", "fastcalc.engine.Aggregate.tables, .route_tables",
                         "every activity of every table x 1.5", _tables_scaled),
    "K1.tables:key_removed": ("K1", "table", "fastcalc.engine.Aggregate.tables, .route_tables",
                              "the first factor key of every table removed", _tables_first_factor_key_removed),
    "K1.tot": ("K1", "function", "fastcalc.engine.tot", "result x 1.5", (engine, "tot", _times(1.5))),
    "K2.period_groups:scaled": ("K2", "table", "fastcalc.engine.Aggregate.groups",
                                "lines, repair lines and masses of every period group x 1.5", _groups_scaled),
    "K2.renewal_count": ("K2", "function", "fastcalc.closed_forms.renewal_count", "one event fewer (not below 0)",
                         (cf, "renewal_count", _one_event_fewer)),
    "K2.skip_weight_periodic": ("K2", "function", "fastcalc.closed_forms.skip_weight_periodic", "result x 0.5",
                                (cf, "skip_weight_periodic", _times(0.5))),
    "K2.skip_weight_years": ("K2", "function", "fastcalc.closed_forms.skip_weight_years", "result x 0.5",
                             (cf, "skip_weight_years", _times(0.5))),
    "K2.periodic_years": ("K2", "function", "fastcalc.closed_forms.periodic_years",
                          "every event one year earlier (not before year 1)",
                          (cf, "periodic_years", _one_year_earlier)),
    "K2.explicit_years": ("K2", "function", "fastcalc.closed_forms.explicit_years", "the last used entry dropped",
                          (cf, "explicit_years", _last_dropped)),
    "K2.event_year": ("K2", "function", "fastcalc.closed_forms.event_year", "one year earlier (not before year 1)",
                      (cf, "event_year", _year_earlier)),
    "K3.linear_weighted_sum": ("K3", "function", "fastcalc.closed_forms.linear_weighted_sum", "result x 1.5",
                               (cf, "linear_weighted_sum", _times(1.5))),
    "K3.table_weighted_sum": ("K3", "function", "fastcalc.closed_forms.table_weighted_sum", "result x 1.5",
                              (cf, "table_weighted_sum", _times(1.5))),
    "K3.segment_moments": ("K3", "function", "fastcalc.closed_forms.segment_moments", "both moments x 1.5",
                           (cf, "segment_moments", _pair_times(1.5))),
    "K3.table_moments": ("K3", "function", "fastcalc.closed_forms.table_moments", "both moments x 1.5",
                         (cf, "table_moments", _pair_times(1.5))),
    "K3.grid_segments": ("K3", "function", "fastcalc.closed_forms.grid_segments", "every descriptor reported as not well formed",
                         (cf, "grid_segments", _constant(None))),
    "K3.segment_values": ("K3", "function", "fastcalc.closed_forms.segment_values", "every yearly grid value x 1.5",
                          (cf, "segment_values", _list_times(1.5))),
    "K3._values": ("K3", "function", "fastcalc.engine._values", "every yearly value of an annual quantity x 1.5",
                   (engine, "_values", _list_times(1.5))),
    "K3._purchased_series": ("K3", "function", "fastcalc.engine._purchased_series",
                             "yearly purchase, emission and their sum x 1.5",
                             (engine, "_purchased_series", _purchased_times(1.5))),
    "K4.device_table:scaled": ("K4", "table", "fastcalc.engine.Aggregate.charges", "every charge x GWP entry x 1.5",
                               _charges_scaled),
    "K4.refrigerant_fractions": ("K4", "function", "fastcalc.closed_forms.refrigerant_fractions", "all three fractions x 1.5",
                                 (cf, "refrigerant_fractions", _fractions_times(1.5))),
    "K4._change_years": ("K4", "function", "fastcalc.engine._change_years", "the last charge change dropped",
                         (engine, "_change_years", _last_dropped)),
    "K4._add_leak_series": ("K4", "function", "fastcalc.engine._add_leak_series", "yearly leak x 1.5",
                            (engine, "_add_leak_series", _leak_series_times(1.5))),
    "K5.indicator:scaled": ("K5", "function", "fastcalc.engine.indicator", "result x 1.5 (cancels in a ratio of two indicators)",
                            (engine, "indicator", _times(1.5))),
    "K5.indicator:stage_left_out": ("K5", "function", "fastcalc.engine.indicator", "the first stage of the subset left out",
                                    (engine, "indicator", _first_stage_left_out)),
    "K6._within": ("K6", "function", "fastcalc.engine._within", "verdict negated", (engine, "_within", _negated)),
    "K7._record_ok": ("K7", "function", "fastcalc.engine._record_ok (the record part of Resolver.record)",
                      "every record reported unusable", (engine, "_record_ok", _constant(False))),
    "K7.Resolver.convert:scaled": ("K7", "function", "fastcalc.engine.Resolver.convert",
                                   "every multiplier between different units x 1.5",
                                   (engine.Resolver, "convert", _convert_times(1.5))),
    "K7.Resolver.convert:missing": ("K7", "function", "fastcalc.engine.Resolver.convert",
                                    "every conversion between different units reported missing",
                                    (engine.Resolver, "convert", _convert_missing)),
    "K7._epd_applies": ("K7", "function", "fastcalc.engine._epd_applies", "no product-specific factor applies",
                        (engine, "_epd_applies", _constant(False))),
    "K7._make_recipe": ("K7", "function", "fastcalc.engine._make_recipe", "every composite factor x 1.5",
                        (engine, "_make_recipe", _recipe_value_times(1.5))),
    "K7.recipes:mass_scaled": ("K7", "table", "fastcalc.engine.Aggregate.recipes", "the mass summed per composition x 1.5",
                               _recipe_masses_scaled),
    "K7.licence_findings": ("K7", "table", "fastcalc.engine.Aggregate.unlicensed",
                            "every factor id entered as unlicensed (after the licence gate has reported)",
                            _every_factor_unlicensed),
    "other._left_out": (None, "function", "fastcalc.engine._left_out", "verdict negated", (engine, "_left_out", _negated)),
    "other._same": (None, "function", "fastcalc.engine._same", "verdict negated", (engine, "_same", _negated)),
    "other.last_weight": (None, "function", "fastcalc.closed_forms.last_weight", "weight of the last study year x 0.5",
                          (cf, "last_weight", _times(0.5))),
}
# the functions of closed_forms that stand for a loop of the reference calculation (for "who detects a broken closed form")
CLOSED_FORMS = {"renewal_count": "K2.renewal_count", "skip_weight_periodic": "K2.skip_weight_periodic",
                "skip_weight_years": "K2.skip_weight_years", "linear_weighted_sum": "K3.linear_weighted_sum",
                "segment_moments": "K3.segment_moments", "refrigerant_fractions": "K4.refrigerant_fractions"}
NOT_BROKEN = {
    "fastcalc.closed_forms.inside": "a falsified verdict puts events outside the study years and the yearly outputs fail with "
                                    "an index error instead of a changed value",
    "fastcalc.engine.Resolver.triples": "a memo that is filled and read inside the aggregation; its content is the result of "
                                        "Resolver.record and Resolver.convert, which are broken instead",
    "fastcalc.engine.STAGE_TABLES, STAGE_UPSTREAM": "constants that say which table belongs to which stage; not a computation",
}


# ------------------------------------------------------------------------------------------ direct outputs

class _MarkedFloat(float):
    """A float that remembers which shared function returned it; any arithmetic gives a plain float."""


class _MarkedInt(int):
    """The same for an int (a count or a year)."""


def _marked(value, origin):
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, float):
        out = _MarkedFloat(value)
    elif isinstance(value, int):
        out = _MarkedInt(value)
    elif isinstance(value, tuple):
        return tuple(_marked(v, origin) for v in value)
    elif isinstance(value, list):
        return [_marked(v, origin) for v in value]
    else:
        return value
    out.origin = origin
    return out


def _marking(origin):
    return lambda original: lambda *a: _marked(original(*a), origin)


def _marking_recipe(origin):
    def make(original):
        def wrapper(key, resolver):
            recipe = original(key, resolver)
            if recipe["value"] is not None:
                recipe["value"] = resolver.fval[key] = _marked(recipe["value"], origin)
            return recipe
        return wrapper
    return make


# the shared functions whose return values can be marked: label -> (owner, attribute, wrapper factory)
MARKED_FUNCTIONS = {
    "K1.tot": (engine, "tot", _marking), "K5.indicator": (engine, "indicator", _marking),
    "K2.renewal_count": (cf, "renewal_count", _marking), "K2.skip_weight_periodic": (cf, "skip_weight_periodic", _marking),
    "K2.skip_weight_years": (cf, "skip_weight_years", _marking), "K2.periodic_years": (cf, "periodic_years", _marking),
    "K2.explicit_years": (cf, "explicit_years", _marking), "K3.linear_weighted_sum": (cf, "linear_weighted_sum", _marking),
    "K3.table_weighted_sum": (cf, "table_weighted_sum", _marking), "K3.segment_moments": (cf, "segment_moments", _marking),
    "K3.table_moments": (cf, "table_moments", _marking), "K3.segment_values": (cf, "segment_values", _marking),
    "K3._values": (engine, "_values", _marking), "K3._purchased_series": (engine, "_purchased_series", _marking),
    "K4.refrigerant_fractions": (cf, "refrigerant_fractions", _marking), "K4._change_years": (engine, "_change_years", _marking),
    "K7.Resolver.convert": (engine.Resolver, "convert", _marking), "K7._make_recipe": (engine, "_make_recipe", _marking_recipe),
}
NOT_MARKED = {
    "K6._within, other._left_out, other._same, K7._record_ok, K7._epd_applies":
        "they return a verdict (bool), which cannot carry a mark",
    "K4._add_leak_series": "it adds to a list and returns nothing",
    "K3.grid_segments, K2.event_year": "their values only enter other shared functions (segment_moments / explicit_years)",
}


@contextlib.contextmanager
def marking():
    """Every function of MARKED_FUNCTIONS returns marked values for the duration of the block."""
    saved = []
    try:
        for origin, (owner, attribute, factory) in MARKED_FUNCTIONS.items():
            original = owner.__dict__[attribute] if isinstance(owner, type) else getattr(owner, attribute)
            saved.append((owner, attribute, original))
            setattr(owner, attribute, factory(origin)(original))
        yield
    finally:
        for owner, attribute, original in reversed(saved):
            setattr(owner, attribute, original)


def marked_leaves(result: dict) -> dict:
    """unit id -> {origin: one example leaf path} for the public leaves that are a marked return value."""
    out = {}
    for uid, value in result.items():
        if uid.startswith("_"):
            continue
        for path, leaf in flatten(value).items():
            if isinstance(leaf, (_MarkedFloat, _MarkedInt)):
                out.setdefault(uid, {}).setdefault(leaf.origin, path)
    return out


# ------------------------------------------------------------------------------------------ the scenarios

def scenarios() -> dict:
    """Five small fictional scenarios that together exercise every branch (see ``coverage`` in the output)."""
    rows = {"n_materials": 60, "n_equipment": 24, "n_refrigerants": 8, "composite_share": 0.3, "epd_share": 0.3,
            "explicit_event_share": 0.3, "change_list_share": 0.4}
    out = {
        "parametric_rebuild": synth.make_scenario(
            5, "RC", "office", "S", 60.0, profile_kind="LINEAR_TREND", grid_kind="LINEAR_DECLINE_TO_FLOOR", replacement_cycle=25.0,
            reconstruction_scenario="REBUILD_IDENTICAL", scenario_id="MEMBERSHIP-parametric-rebuild", **rows),
        "year_tables_partial_year": synth.make_scenario(
            6, "S", "retail", "S", 42.5, profile_kind="TABLE", grid_kind="TABLE", replacement_cycle=20.0,
            reconstruction_scenario="MAJOR_REFURBISHMENT", scenario_id="MEMBERSHIP-year-tables", **rows),
        "constant_stepwise_short_lives": synth.make_scenario(
            7, "W", "school", "S", 60.0, profile_kind="CONSTANT", grid_kind="STEPWISE", service_life_choices=[0.75, 7.0, 12.5, 15.0],
            reconstruction_scenario="NONE", scenario_id="MEMBERSHIP-constant-stepwise", **rows),
        "descriptor_profiles_grid_table": synth.make_scenario(
            9, "RC", "residential", "S", 30.0, profile_kind="LINEAR_TREND", grid_kind="TABLE",
            scenario_id="MEMBERSHIP-descriptor-profiles-grid-table", **rows),
    }
    # parametric inputs whose on-site generation outgrows the demand during the study period: the clamp
    # max(0, .) acts in the later years, so the purchased electricity is evaluated year by year also in
    # totals-only mode (generation: half the demand in the first year, one and a half times in the last)
    clamp = synth.make_scenario(8, "SRC", "hospital", "S", 60.0, profile_kind="LINEAR_TREND", grid_kind="CONSTANT",
                                scenario_id="MEMBERSHIP-clamp", **rows)
    op = clamp.operation
    demand, generation, export = op.electricity, op.onsite_generation, op.onsite_export
    to_demand_unit = model.conversion_factor(clamp.unit_conversions, generation.unit.partition("/")[0],
                                             demand.unit.partition("/")[0])
    last = cf.n_years(clamp.boundary.study_period) - 1
    generation.base = 0.5 * demand.base / to_demand_unit
    generation.slope = (1.5 * (demand.base + demand.slope * last) / to_demand_unit - generation.base) / last
    generation.table = [generation.base + generation.slope * k for k in range(len(generation.table))]
    export.base = export.slope = 0.0
    export.table = [0.0] * len(export.table)
    out["parametric_clamp_acts"] = clamp
    for scn in out.values():
        population.attach_baseline(scn)
    return out


def run_engine(scn, detail, fault=None):
    """engine.evaluate, with the two steps apart so that a table can be falsified in between."""
    T = engine.check_period(scn)
    A = engine.aggregate(scn, detail)
    if fault is not None:
        fault(A)
    return engine.finish(A, T, detail, None)


@contextlib.contextmanager
def broken(name):
    """The shared object ``name`` falsified for the duration of the block; yields the table fault (or None)."""
    fault = SHARED_OBJECTS[name][4]
    if callable(fault):
        yield fault
        return
    owner, attribute, make = fault
    original = owner.__dict__[attribute] if isinstance(owner, type) else getattr(owner, attribute)
    setattr(owner, attribute, make(original))
    try:
        yield None
    finally:
        setattr(owner, attribute, original)


def _is_float(x) -> bool:
    return isinstance(x, float)


def changed_units(base: dict, got: dict):
    """(units whose public result differs, units in which a float leaf differs) - relative 1e-9, no floor."""
    changed, value_changed = [], []
    for uid in sorted(set(base) | set(got)):
        if uid.startswith("_"):
            continue
        c = compare(base.get(uid, {}), got.get(uid, {}), floor=FLOOR)
        if c.within(TOL) and not c.extra:
            continue
        changed.append(uid)
        a, b = flatten(base.get(uid, {})), flatten(got.get(uid, {}))
        for path, x in a.items():
            y = b.get(path)
            if (_is_float(x) or _is_float(y)) and not compare({"v": x}, {"v": y}, floor=FLOOR).within(TOL):
                value_changed.append(uid)
                break
    return changed, value_changed


def failing_units(ref: dict, got: dict, detail: bool) -> list:
    """Units that fail the comparison with the reference, by the rule of the exactness check."""
    out = []
    for uid, ref_value in ref.items():
        c = compare(ref_value, got.get(uid, {}), floor=FLOOR, ignore_missing=not detail)
        if not (c.within(TOL) and not c.extra):
            out.append(uid)
    return sorted(out)


def _coverage(scn, full: dict, totals: dict) -> dict:
    """Which branches of the unified model the scenario exercises (from its inputs and its unbroken results)."""
    T = scn.boundary.study_period
    calls = Counter()

    def counting(original):
        def wrapper(*a):
            calls["n"] += 1
            return original(*a)
        return wrapper

    original = engine._purchased_series
    engine._purchased_series = counting(original)
    try:
        engine.evaluate(scn, detail=False)
    finally:
        engine._purchased_series = original
    devices = scn.refrigerants
    kinds = Counter(full["X-15"]["kind"])
    profiles = (scn.operation.electricity, scn.operation.onsite_generation, scn.operation.onsite_export, scn.operation.gas,
                scn.operation.oil, scn.operation.district_heat, scn.water_waste.water, scn.water_waste.sewage,
                scn.water_waste.municipal_waste)
    return {
        "study_period": T, "last_year_is_partial": cf.last_weight(T) < 1.0,
        "rows": {"materials": len(scn.materials), "equipment": len(scn.equipment), "refrigerants": len(devices)},
        "material_rows_by_factor_kind": {str(k): v for k, v in sorted(kinds.items(), key=str)},
        "rows_with_own_conversions": sum(1 for r in scn.materials if r.conversions),
        "equipment_with_explicit_event_list": sum(1 for e in scn.equipment if e.replacement_event_list is not None),
        "renewal_events_of_equipment": full["B4-01"]["n_events"],
        "material_rows_with_a_renewal": sum(1 for n in full["B4-03"]["by_item"] if n),
        "renewal_periods_below_one_year": sum(1 for r in scn.materials if r.refresh_cycle is not None and r.refresh_cycle < 1.0),
        "rebuild_events": full["B5-01"]["n_events"], "reconstruction_scenario": scn.boundary.reconstruction_scenario,
        "refrigerant_devices": {"with_change_list": sum(1 for d in devices if d.change_years is not None),
                                "periodic": sum(1 for d in devices if d.change_years is None and d.service_life is not None),
                                "topped_up": sum(1 for d in devices if d.top_up),
                                "not_topped_up": sum(1 for d in devices if not d.top_up)},
        "annual_profiles_by_kind": dict(sorted(Counter(p.kind for p in profiles).items())),
        "grid_kind": scn.operation.grid.kind, "grid_source": full["X-06"]["source"],
        "purchased_electricity_year_by_year_in_totals_mode": calls["n"] > 0,
        "baseline_comparison": totals["SUM-08"]["status"],
        "whole_life_total": totals["SUM-03"]["value"], "total_complete": totals["SUM-03"]["complete"],
    }


BRANCHES = {
    "annual quantities by descriptor (trend)": lambda c: c["annual_profiles_by_kind"].get("LINEAR_TREND", 0) > 0,
    "annual quantities by descriptor (constant)": lambda c: c["annual_profiles_by_kind"].get("CONSTANT", 0) > 0,
    "annual quantities by year table": lambda c: c["annual_profiles_by_kind"].get("TABLE", 0) > 0,
    "grid factor by descriptor": lambda c: c["grid_source"] == "DESCRIPTOR",
    "grid factor by year table": lambda c: c["grid_source"] == "TABLE",
    "purchased electricity by closed form, grid by descriptor":
        lambda c: not c["purchased_electricity_year_by_year_in_totals_mode"] and c["grid_source"] == "DESCRIPTOR",
    "purchased electricity by closed form, grid by year table":
        lambda c: not c["purchased_electricity_year_by_year_in_totals_mode"] and c["grid_source"] == "TABLE",
    "purchased electricity year by year in totals mode, grid by descriptor":
        lambda c: c["purchased_electricity_year_by_year_in_totals_mode"] and c["grid_source"] == "DESCRIPTOR",
    "purchased electricity year by year in totals mode, grid by year table":
        lambda c: c["purchased_electricity_year_by_year_in_totals_mode"] and c["grid_source"] == "TABLE",
    "partial last year": lambda c: c["last_year_is_partial"],
    "rebuild or major refurbishment event": lambda c: c["rebuild_events"] > 0,
    "equipment with explicit event lists": lambda c: c["equipment_with_explicit_event_list"] > 0,
    "periodic renewals of equipment": lambda c: c["renewal_events_of_equipment"] > 0,
    "periodic renewals of materials": lambda c: c["material_rows_with_a_renewal"] > 0,
    "renewal period below one year": lambda c: c["renewal_periods_below_one_year"] > 0,
    "composite rows": lambda c: c["material_rows_by_factor_kind"].get("COMPOSITE", 0) > 0,
    "rows with a product-specific factor": lambda c: c["material_rows_by_factor_kind"].get("EPD", 0) > 0,
    "rows with their own unit conversions": lambda c: c["rows_with_own_conversions"] > 0,
    "refrigerant devices with a change list": lambda c: c["refrigerant_devices"]["with_change_list"] > 0,
    "refrigerant devices changed periodically": lambda c: c["refrigerant_devices"]["periodic"] > 0,
    "refrigerant devices topped up and not topped up": lambda c: c["refrigerant_devices"]["topped_up"] > 0
                                                                 and c["refrigerant_devices"]["not_topped_up"] > 0,
    "baseline compared": lambda c: c["baseline_comparison"] == "COMPARED",
}


# ------------------------------------------------------------------------------------------ the check

def run(scenario_set: dict | None = None, claims: dict | None = None) -> dict:
    registry.load_all()
    scns = scenarios() if scenario_set is None else scenario_set
    base, ref, coverage = {}, {}, {}
    agrees = True
    leaves = {}
    table_keys = {}
    for sname, scn in scns.items():
        ref[sname] = registry.run_all(scn)
        for mode, detail in MODES:
            res = base[(sname, mode)] = run_engine(scn, detail)
            agrees = agrees and not failing_units(ref[sname], res, detail)
            for uid, value in res.items():
                if uid.startswith("_"):
                    continue
                flat = flatten(value)
                rec = leaves.setdefault(uid, {"numeric_full": 0, "numeric_totals": 0, "float_full": 0, "float_totals": 0,
                                              "keys_totals": set()})
                rec["numeric_" + mode] += sum(1 for v in flat.values() if isinstance(v, (int, float)) and not isinstance(v, bool))
                rec["float_" + mode] += sum(1 for v in flat.values() if _is_float(v))
                if mode == "totals":
                    rec["keys_totals"].update(value)
            for tname, table in res["_tables"].items():
                rec = table_keys.setdefault(tname, {"entries": 0, "pseudo_key_entries": 0})
                rec["entries"] += len(table)
                rec["pseudo_key_entries"] += sum(1 for k in table if isinstance(k, engine.PseudoKey))
        coverage[sname] = _coverage(scn, base[(sname, "full")], base[(sname, "totals")])

    objects = {}
    for name, (model_id, kind, where, what, _) in SHARED_OBJECTS.items():
        entry = {"model": model_id, "kind": kind, "where": where, "perturbation": what,
                 "units_changed_full": set(), "units_changed_totals": set(),
                 "units_with_a_changed_value_full": set(), "units_with_a_changed_value_totals": set(),
                 "units_failing_against_reference_full": set(), "units_failing_against_reference_totals": set(),
                 "changed_in_scenarios": [], "raised": []}
        for sname, scn in scns.items():
            hit = False
            for mode, detail in MODES:
                try:
                    with broken(name) as fault:
                        got = run_engine(scn, detail, fault)
                except Exception as exc:                # noqa: BLE001 - a fault that stops the calculation is reported
                    entry["raised"].append({"scenario": sname, "mode": mode, "error": f"{type(exc).__name__}: {exc}"[:160]})
                    continue
                changed, value_changed = changed_units(base[(sname, mode)], got)
                entry["units_changed_" + mode].update(changed)
                entry["units_with_a_changed_value_" + mode].update(value_changed)
                entry["units_failing_against_reference_" + mode].update(failing_units(ref[sname], got, detail))
                hit = hit or bool(changed)
            if hit:
                entry["changed_in_scenarios"].append(sname)
        for key, value in entry.items():
            if isinstance(value, set):
                entry[key] = sorted(value)
        entry["detection_equals_change"] = (entry["units_changed_full"] == entry["units_failing_against_reference_full"]
                                            and entry["units_changed_totals"] == entry["units_failing_against_reference_totals"])
        objects[name] = entry

    direct = {origin: {"units_full": set(), "units_totals": set(), "example_leaves": {}} for origin in MARKED_FUNCTIONS}
    unchanged_by_marking = True
    for sname, scn in scns.items():
        for mode, detail in MODES:
            with marking():
                got = run_engine(scn, detail)
            unchanged_by_marking = unchanged_by_marking and not changed_units(base[(sname, mode)], got)[0]
            for uid, origins in marked_leaves(got).items():
                for origin, path in origins.items():
                    direct[origin]["units_" + mode].add(uid)
                    direct[origin]["example_leaves"].setdefault(uid, f"{path} ({mode})")
    for entry in direct.values():
        entry["units_full"], entry["units_totals"] = sorted(entry["units_full"]), sorted(entry["units_totals"])
        entry["example_leaves"] = dict(sorted(entry["example_leaves"].items()))

    units = {}
    for uid in sorted(leaves):
        rec = leaves[uid]
        in_full = sorted(n for n, e in objects.items() if uid in e["units_changed_full"])
        in_totals = sorted(n for n, e in objects.items() if uid in e["units_changed_totals"])
        units[uid] = {
            "sensitive_to": sorted(set(in_full) | set(in_totals)),
            "sensitive_to_full": in_full, "sensitive_to_totals": in_totals,
            "value_sensitive_to_totals": sorted(n for n, e in objects.items() if uid in e["units_with_a_changed_value_totals"]),
            "models_sensitive_to": sorted({objects[n]["model"] for n in set(in_full) | set(in_totals) if objects[n]["model"]}),
            "direct_output_of_full": sorted(o for o, e in direct.items() if uid in e["units_full"]),
            "direct_output_of_totals": sorted(o for o, e in direct.items() if uid in e["units_totals"]),
            "numeric_leaves_full": rec["numeric_full"], "numeric_leaves_totals": rec["numeric_totals"],
            "float_leaves_full": rec["float_full"], "float_leaves_totals": rec["float_totals"],
            "keys_in_totals": sorted(rec["keys_totals"]),
            "flag_only_in_totals": rec["float_totals"] == 0,
        }

    by_model = {}
    for name, entry in objects.items():
        m = by_model.setdefault(entry["model"] or "other", {"shared_objects": [], "units_sensitive_full": set(),
                                                             "units_sensitive_totals": set(),
                                                             "units_with_a_changed_value_totals": set()})
        m["shared_objects"].append(name)
        m["units_sensitive_full"].update(entry["units_changed_full"])
        m["units_sensitive_totals"].update(entry["units_changed_totals"])
        m["units_with_a_changed_value_totals"].update(entry["units_with_a_changed_value_totals"])
    for m in by_model.values():
        for key, value in m.items():
            if isinstance(value, set):
                m[key] = sorted(value)

    closed_forms = {}
    for fn, name in CLOSED_FORMS.items():
        e = objects[name]
        closed_forms[fn] = {"shared_object": name, "perturbation": e["perturbation"],
                            "detected_by_full": e["units_failing_against_reference_full"],
                            "detected_by_totals": e["units_failing_against_reference_totals"]}

    exercised = {branch: [s for s, c in coverage.items() if test(c)] for branch, test in BRANCHES.items()}
    out = {
        "schema_version": "1.0",
        "what": "Fault injection into the shared tables and functions of the unified model (fastcalc). For each fault: the "
                "units whose public results change against the run without the fault.",
        "data_statement": "SYNTHETIC_FICTIONAL data only. Not evidence about real buildings or about any other tool.",
        "comparison": {"function": "common.compare.compare", "relative_tolerance": TOL, "absolute_floor": FLOOR,
                       "changed": "a leaf differs by more than the tolerance, is missing, or is new",
                       "a_changed_value": "a leaf of type float differs (counts, flags and texts do not count here)",
                       "failing_against_reference": "the rule of the exactness check (leaves the totals-only mode leaves out "
                                                    "are ignored in that mode)"},
        "unbroken_run_agrees_with_reference": agrees,
        "shared_objects": objects,
        "units": units,
        "by_model": dict(sorted(by_model.items())),
        "direct_outputs": {
            "definition": "a public leaf of the unit IS the value a shared function returned (marked float or int, unchanged by "
                          "any arithmetic). A lower bound of 'produced by the shared function': sums of such values and "
                          "verdicts do not show up here.",
            "results_unchanged_by_marking": unchanged_by_marking,
            "by_function": direct, "not_marked": NOT_MARKED},
        "closed_forms": closed_forms,
        "tables": {"note": "entries of the tables the unified model returns (summed over the scenarios and both modes); a "
                           "pseudo key marks a line whose activity is already an emission (factor 1)",
                   "by_table": dict(sorted(table_keys.items())),
                   "tables_with_only_pseudo_keys": sorted(t for t, r in table_keys.items()
                                                          if r["entries"] and r["entries"] == r["pseudo_key_entries"])},
        "scenarios": [{"name": s, "scenario_id": scn.meta.scenario_id, "coverage": coverage[s]} for s, scn in scns.items()],
        "branches_exercised": exercised,
        "every_branch_exercised": all(exercised.values()),
        "shared_objects_without_effect": sorted(n for n, e in objects.items() if not e["units_changed_full"]
                                                and not e["units_changed_totals"] and not e["raised"]),
        "faults_that_raised": sorted(n for n, e in objects.items() if e["raised"]),
        "not_broken": NOT_BROKEN,
        "notes": [
            "Sensitivity is necessary for membership, not sufficient: a unit downstream of a shared object reacts too.",
            "A table fault is applied to the proposal between aggregate and finish. The baseline of the comparison (SUM-08) is "
            "aggregated inside finish and is not touched by it; a function fault acts on the baseline as well.",
            "In full-output mode the per-row lists were multiplied row by row during the aggregation, so a table fault changes "
            "a unit's value and leaves its per-row list as it was.",
            "units[...].flag_only_in_totals: the unit returns no float in totals-only mode on any scenario of the set "
            "(only counts, flags or texts). The leaf counts of a unit are summed over the scenarios of the set.",
            "A fault that only rescales (x 1.5) cancels in a ratio of two values of the same function; the indicator is "
            "therefore also broken structurally (a stage left out).",
            "K7.licence_findings is not the resolution table: it is the per-factor finding of the licence gate, which the "
            "check of the used factors reads again.",
        ],
    }
    if claims is not None:
        out["claims"] = against_claims(out, claims)
    return out


def against_claims(result: dict, models: dict) -> dict:
    """Compare claimed memberships ({"models": [{"id", "units"}]}, the layout of 03_MODELS/models.json) with the measurement."""
    objects, per_model = result["shared_objects"], {}
    none, n_members = [], 0
    for m in models["models"]:
        mine = [e for e in objects.values() if e["model"] == m["id"]]
        full = set().union(*(e["units_changed_full"] for e in mine)) if mine else set()
        totals = set().union(*(e["units_changed_totals"] for e in mine)) if mine else set()
        value_totals = set().union(*(e["units_with_a_changed_value_totals"] for e in mine)) if mine else set()
        marked = [e for origin, e in result["direct_outputs"]["by_function"].items() if origin.split(".")[0] == m["id"]]
        direct_full = set().union(*(e["units_full"] for e in marked)) if marked else set()
        direct_totals = set().union(*(e["units_totals"] for e in marked)) if marked else set()
        members = list(m["units"])
        n_members += len(members)
        per_model[m["id"]] = {
            "claimed_members": members,
            "not_sensitive_to_any_shared_object_of_the_model": sorted(u for u in members if u not in full and u not in totals),
            "sensitive_only_in_full_output_mode": sorted(u for u in members if u in full and u not in totals),
            "sensitive_in_totals_mode_only_through_counts_or_flags": sorted(u for u in members
                                                                            if u in totals and u not in value_totals),
            "with_a_direct_output_of_a_function_of_the_model_in_totals_mode": sorted(u for u in members if u in direct_totals),
            "with_a_direct_output_only_in_full_output_mode": sorted(u for u in members
                                                                    if u in direct_full and u not in direct_totals),
            "without_a_direct_output_of_a_function_of_the_model": sorted(u for u in members
                                                                         if u not in direct_full and u not in direct_totals),
        }
        none += [f"{u} ({m['id']})" for u in per_model[m["id"]]["not_sensitive_to_any_shared_object_of_the_model"]]
    return {"claimed_members": n_members, "not_sensitive_to_any_shared_object_of_their_model": sorted(none),
            "per_model": per_model}


def _json_default(value):
    if isinstance(value, set):
        return sorted(value)
    return repr(value)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--claims", type=Path, default=None,
                    help="a models.json whose memberships are compared with the measurement (not read by default)")
    args = ap.parse_args()
    claims = json.loads(args.claims.read_text(encoding="utf-8")) if args.claims else None
    result = run(claims=claims)
    if claims is not None:
        result["claims"]["source"] = str(args.claims)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1, default=_json_default), encoding="utf-8")
    print(f"shared objects broken: {len(result['shared_objects'])}; unbroken run agrees with the reference: "
          f"{result['unbroken_run_agrees_with_reference']}; every branch exercised: {result['every_branch_exercised']}")
    print("without effect:", result["shared_objects_without_effect"], "| raised:", result["faults_that_raised"])
    for model_id, m in result["by_model"].items():
        print(f"  {model_id}: {len(m['units_sensitive_full'])} units react in full mode, "
              f"{len(m['units_sensitive_totals'])} in totals mode")
    if claims is not None:
        print("claimed members not sensitive to any shared object of their model:",
              result["claims"]["not_sensitive_to_any_shared_object_of_their_model"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
