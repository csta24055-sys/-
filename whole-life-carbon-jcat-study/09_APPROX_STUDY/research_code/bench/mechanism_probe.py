#!/usr/bin/env python3
"""Measured operation counts of the unified model (``fastcalc.engine``).

Nothing here is a tally kept by the engine. The operations are observed from outside:

  * every factor-record value, gas amount, device GWP and the construction grid value is
    replaced by a float subclass that reports each multiplication it takes part in,
    together with the function that executes it and the kind of input row that is being
    read at that moment;
  * the row lists (materials, equipment, refrigerants) are replaced by lists that report
    every iteration, indexed read and row attribute read;
  * the factor table is a dict that reports every look-up; the year tables are lists that
    report every element read;
  * the functions that resolve factors, convert units, build event-year lists, evaluate
    closed forms or loop over the study years are wrapped and their calls are counted.

The counted run returns the same results as an uninstrumented run (checked, tolerance 0).

From the counts the statements P1..P7 are evaluated as booleans. A statement that the
numbers do not support is reported as false.

All data are synthetic and fictional. The counts describe what this code does on these
inputs; they are not a statement about any other tool or about real buildings.

Run:
    cd research_code && python3 -B -m bench.mechanism_probe [--out FILE] [--sizes SML]
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import json
import math
import sys
from collections import Counter
from pathlib import Path

import synth
from common.compare import compare
from fastcalc import closed_forms as cf
from fastcalc import engine
from synth import model, population

STUDY = Path(__file__).resolve().parents[2]
OUT = STUDY / "04_VERIFICATION" / "mechanism_probe.json"

MECHANISM_CASES = {
    "mechanism_parametric": {"profile_kind": "LINEAR_TREND", "grid_kind": "LINEAR_DECLINE_TO_FLOOR"},
    "mechanism_year_tables": {"profile_kind": "TABLE", "grid_kind": "TABLE"},
}
MECHANISM_ROWS = {"n_materials": 400, "n_equipment": 120, "n_refrigerants": 10}
SECOND_PERIOD = 30.0                    # the "second study period" of P6

# Functions that loop over the study years, and how many yearly values one call handles (nominal
# loop length: a check that fails early stops sooner). tests/test_mechanism_probe.py asserts that
# no other function of fastcalc contains a loop over range(...), so nothing is left uncounted.
YEAR_LOOPS = {
    # name: (module, class of the loop, nominal length of one call)
    "table_weighted_sum": (cf, "value_loop", lambda a, r: cf.n_years(a[1])),
    "table_moments": (cf, "value_loop", lambda a, r: cf.n_years(a[1])),
    "_purchased_series": (engine, "value_loop", lambda a, r: len(r[0]) - 1),
    "segment_values": (cf, "series_generation", lambda a, r: len(r)),
    "_values": (engine, "series_generation", lambda a, r: len(r)),
    "_same": (engine, "copy_check", lambda a, r: len(a[0])),
    "table_usable": (cf, "validity_scan", lambda a, r: a[1]),
    "_add_leak_series": (engine, "yearly_output", lambda a, r: a[5]),
    "_add_repair_series": (engine, "yearly_output", lambda a, r: a[4]),
    "_annual_series": (engine, "yearly_output", lambda a, r: a[2] * len(a[0])),
    "_whole_life_series": (engine, "yearly_output", lambda a, r: len(r["by_year"]) - 1),
}
# functions with a loop over range(...) that is not a loop over the study years
OTHER_RANGE_LOOPS = {"periodic_years": "one value per event (an event-year list, counted as such)",
                     "grid_segments": "one step of a STEPWISE descriptor at a time"}
# who may build a list of event years, and what kind of list it is
EVENT_LIST_KINDS = {
    ("periodic_years", "_renewal_years"): "periodic_material_equipment",
    ("periodic_years", "_rebuild_years"): "rebuild",
    ("periodic_years", "_change_years"): "refrigerant_periodic",
    ("explicit_years", "_explicit_event_years"): "explicit_equipment",
    ("explicit_years", "_change_years"): "refrigerant_explicit",
}
CLOSED_FORMS = ("renewal_count", "skip_weight_periodic", "skip_weight_years", "linear_weighted_sum", "segment_moments",
                "refrigerant_fractions")
_SKIP_NAMES = ("<locals>", "<genexpr>", "<lambda>", "<listcomp>", "<dictcomp>", "<setcomp>")


# ------------------------------------------------------------------------------------------ the observer

class _State:
    def __init__(self):
        self.reset()

    def reset(self):
        self.phase = "idle"
        self.row = None                 # kind of the input row that is being read right now
        self.products = Counter()       # (phase, tag, function, row kind) -> multiplications
        self.other_arithmetic = Counter()   # (phase, tag, function) -> additions, subtractions, divisions
        self.rows = Counter()           # (phase, row kind, what) -> count
        self.lookups = Counter()        # (phase, function) -> look-ups in the factor table
        self.calls = Counter()          # (phase, name[, detail]) -> calls
        self.sets = {}                  # (phase, name) -> set of distinct keys
        self.years = Counter()          # (phase, helper, class) -> nominal yearly values
        self.table_reads = Counter()    # (phase, function) -> year-table elements read

    def distinct(self, name, key):
        self.sets.setdefault((self.phase, name), set()).add(key)


_S = _State()
_where_cache: dict = {}


def _where(code) -> str:
    """Name of the function a code object belongs to, without the markers of nested scopes."""
    name = _where_cache.get(code)
    if name is None:
        name = _where_cache[code] = ".".join(p for p in code.co_qualname.split(".") if p not in _SKIP_NAMES)
    return name


class _Counted(float):
    """A float that reports every multiplication it takes part in; the product itself is the plain one.

    Additions, subtractions and divisions are reported too (separately), so that "no multiplication"
    cannot hide a use of the value in another operation.
    """

    __slots__ = ()
    tag = ""

    def __mul__(self, other):
        _S.products[(_S.phase, self.tag, _where(sys._getframe(1).f_code), _S.row)] += 1
        return float.__mul__(self, other)

    def __rmul__(self, other):
        _S.products[(_S.phase, self.tag, _where(sys._getframe(1).f_code), _S.row)] += 1
        return float.__rmul__(self, other)

    def _other(name):                                   # noqa: N805 - a small factory for the operators below
        base = getattr(float, name)

        def method(self, other):
            _S.other_arithmetic[(_S.phase, self.tag, _where(sys._getframe(1).f_code))] += 1
            return base(self, other)
        return method

    __add__, __radd__, __sub__, __rsub__ = _other("__add__"), _other("__radd__"), _other("__sub__"), _other("__rsub__")
    __truediv__, __rtruediv__ = _other("__truediv__"), _other("__rtruediv__")
    del _other


class FactorValue(_Counted):
    __slots__ = ()
    tag = "factor_value"


class GasAmount(_Counted):
    __slots__ = ()
    tag = "gas_amount"


class DeviceGwp(_Counted):
    __slots__ = ()
    tag = "device_gwp"


class GridConstructionValue(_Counted):
    __slots__ = ()
    tag = "grid_construction_value"


class _Row:
    """Stands in for one input row and reports every attribute read."""

    __slots__ = ("_o", "_k")

    def __init__(self, obj, kind):
        object.__setattr__(self, "_o", obj)
        object.__setattr__(self, "_k", kind)

    def __getattr__(self, name):
        _S.rows[(_S.phase, self._k, "attribute_reads")] += 1
        _S.sets.setdefault((_S.phase, "rows_read:" + self._k), set()).add(id(self))
        return getattr(self._o, name)


class _Rows(list):
    """A row list that reports iterations, rows handed out, indexed reads and length reads."""

    kind = ""

    def __iter__(self):
        _S.rows[(_S.phase, self.kind, "iterations")] += 1
        try:
            for row in list.__iter__(self):
                _S.rows[(_S.phase, self.kind, "rows_handed_out")] += 1
                _S.row = self.kind
                yield row
        finally:
            _S.row = None

    def __getitem__(self, index):
        _S.rows[(_S.phase, self.kind, "indexed_reads")] += 1
        return list.__getitem__(self, index)

    def __len__(self):
        _S.rows[(_S.phase, self.kind, "length_reads")] += 1
        return list.__len__(self)


class _Factors(dict):
    """The factor table: every look-up is reported with the function that makes it."""

    def get(self, key, default=None):
        _S.lookups[(_S.phase, _where(sys._getframe(1).f_code))] += 1
        return dict.get(self, key, default)

    def __getitem__(self, key):
        _S.lookups[(_S.phase, _where(sys._getframe(1).f_code))] += 1
        return dict.__getitem__(self, key)


class _YearTable(list):
    """A year table: every element read is reported with the function that reads it."""

    def __getitem__(self, index):
        out = list.__getitem__(self, index)
        _S.table_reads[(_S.phase, _where(sys._getframe(1).f_code))] += len(out) if isinstance(index, slice) else 1
        return out

    def __iter__(self):
        for value in list.__iter__(self):
            _S.table_reads[(_S.phase, _where(sys._getframe(1).f_code))] += 1
            yield value


def _rows(kind, items):
    out = _Rows(_Row(item, kind) for item in items)
    out.kind = kind
    return out


def instrument(scn):
    """Replace the observable inputs of ``scn`` (in place) by their reporting stand-ins."""
    for rec in scn.factors.values():
        if rec.value is not None:
            rec.value = FactorValue(rec.value)
        rec.gas_amounts = {g: (GasAmount(a) if a is not None else None) for g, a in rec.gas_amounts.items()}
    scn.factors = _Factors(scn.factors)
    for dev in scn.refrigerants:
        if dev.gwp is not None:
            dev.gwp = DeviceGwp(dev.gwp)
    grid = scn.operation.grid
    if grid.construction_value is not None:
        grid.construction_value = GridConstructionValue(grid.construction_value)
    scn.materials = _rows("materials", scn.materials)
    scn.equipment = _rows("equipment", scn.equipment)
    scn.refrigerants = _rows("refrigerants", scn.refrigerants)
    for profile in _profiles(scn):
        profile.table = _YearTable(profile.table)
    grid.table = _YearTable(grid.table)
    return scn


def _profiles(scn):
    op, ww = scn.operation, scn.water_waste
    return (op.electricity, op.onsite_generation, op.onsite_export, op.gas, op.oil, op.district_heat, ww.water, ww.sewage,
            ww.municipal_waste)


@contextlib.contextmanager
def observed():
    """Wrap the functions whose calls are counted; everything is restored on exit."""
    saved = []

    def patch(owner, name, make):
        original = owner.__dict__[name] if isinstance(owner, type) else getattr(owner, name)
        saved.append((owner, name, original))
        setattr(owner, name, make(original))

    def counted(name):
        def make(original):
            def wrapper(*args, **kwargs):
                _S.calls[(_S.phase, name)] += 1
                return original(*args, **kwargs)
            return wrapper
        return make

    def year_loop(name, kind, length):
        def make(original):
            def wrapper(*args):
                result = original(*args)
                _S.years[(_S.phase, name, kind, _where(sys._getframe(1).f_code))] += length(args, result)
                _S.calls[(_S.phase, "year_loop:" + name)] += 1
                return result
            return wrapper
        return make

    def event_list(name):
        def make(original):
            def wrapper(*args):
                result = original(*args)
                kind = EVENT_LIST_KINDS.get((name, _where(sys._getframe(1).f_code)),
                                            "other:" + _where(sys._getframe(1).f_code))
                _S.calls[(_S.phase, "event_list:" + kind)] += 1
                _S.calls[(_S.phase, "event_years_listed")] += len(result)
                return result
            return wrapper
        return make

    def record_ok(original):
        def wrapper(rec, stage):
            _S.calls[(_S.phase, "record_check")] += 1
            key = (id(rec), stage)                  # the record object, whatever id it is filed under
            _S.calls[(_S.phase, "record_check_of", key)] += 1
            _S.distinct("record_check", key)
            return original(rec, stage)
        return wrapper

    def make_recipe(original):
        def wrapper(key, resolver):
            _S.calls[(_S.phase, "recipe")] += 1
            rec = original(key, resolver)
            if rec["value"] is not None:            # so that products with a composite factor are counted too
                rec["value"] = resolver.fval[key] = FactorValue(rec["value"])
            return rec
        return wrapper

    def conversion_factor(original):
        def wrapper(table, from_unit, to_unit, extra=()):
            if from_unit == to_unit:
                _S.calls[(_S.phase, "table_conversion_identity")] += 1
            else:
                _S.calls[(_S.phase, "table_conversion")] += 1
                _S.distinct("table_conversion", (from_unit, to_unit))
            return original(table, from_unit, to_unit, extra)
        return wrapper

    def usable_multiplier(original):
        def wrapper(value):
            _S.calls[(_S.phase, "usable_multiplier", _where(sys._getframe(1).f_code))] += 1
            return original(value)
        return wrapper

    def use(original):
        def wrapper(self, fid, stage, unit, extra, path):
            _S.calls[(_S.phase, "use")] += 1
            return original(self, fid, stage, unit, extra, path)
        return wrapper

    def resolve(original):
        def wrapper(self, fid, stage, unit, extra):
            name = "resolve_with_row_conversions" if extra else "resolve_triple"
            _S.calls[(_S.phase, name)] += 1
            _S.distinct(name, (fid, stage, unit))
            return original(self, fid, stage, unit, extra)
        return wrapper

    def convert(original):
        def wrapper(self, u, v, extra=()):
            _S.calls[(_S.phase, "convert_identity" if u == v else "convert_row_list" if extra else "convert_pair")] += 1
            return original(self, u, v, extra)
        return wrapper

    def record(original):
        def wrapper(self, fid, stage):
            _S.calls[(_S.phase, "record_read")] += 1
            _S.distinct("record_read", (fid, stage))
            return original(self, fid, stage)
        return wrapper

    def tot(original):
        def wrapper(table, fval):
            _S.calls[(_S.phase, "tot")] += 1
            _S.calls[(_S.phase, "tot_entries")] += len(table)
            return original(table, fval)
        return wrapper

    try:
        patch(engine, "_record_ok", record_ok)
        patch(engine, "_epd_applies", counted("epd_applicability"))
        patch(engine, "_make_recipe", make_recipe)
        patch(engine, "tot", tot)
        patch(engine, "indicator", counted("indicator"))
        patch(engine, "_within", counted("residual_test"))
        patch(engine.Resolver, "use", use)
        patch(engine.Resolver, "resolve", resolve)
        patch(engine.Resolver, "convert", convert)
        patch(engine.Resolver, "record", record)
        patch(model, "conversion_factor", conversion_factor)
        patch(model, "usable_multiplier", usable_multiplier)
        patch(cf, "periodic_years", event_list("periodic_years"))
        patch(cf, "explicit_years", event_list("explicit_years"))
        patch(cf, "event_year", counted("event_year"))
        for name in CLOSED_FORMS:
            patch(cf, name, counted("closed_form:" + name))
        for name, (owner, kind, length) in YEAR_LOOPS.items():
            patch(owner, name, year_loop(name, kind, length))
        yield
    finally:
        for owner, name, original in reversed(saved):
            setattr(owner, name, original)


# ------------------------------------------------------------------------------------------ one scenario

def _phase_counts(phase: str) -> dict:
    """Everything observed in one phase, as plain JSON data."""
    S = _S
    prod = {}
    for (ph, tag, where, row), n in sorted(S.products.items(), key=str):
        if ph != phase:
            continue
        t = prod.setdefault(tag, {"total": 0, "while_reading_a_material_or_equipment_row": 0,
                                  "while_reading_a_refrigerant_row": 0, "in_recipe_builder": 0, "in_table_read_out": 0,
                                  "by_function": {}})
        t["total"] += n
        t["by_function"][where] = t["by_function"].get(where, 0) + n
        if where == "_make_recipe":
            t["in_recipe_builder"] += n                 # once per distinct composition, whichever row triggers it
        elif row in ("materials", "equipment"):
            t["while_reading_a_material_or_equipment_row"] += n
        elif row == "refrigerants":
            t["while_reading_a_refrigerant_row"] += n
        if where == "tot":
            t["in_table_read_out"] += n
    rows = {}
    for kind in ("materials", "equipment", "refrigerants"):
        rows[kind] = {what: S.rows.get((phase, kind, what), 0)
                      for what in ("iterations", "rows_handed_out", "indexed_reads", "length_reads", "attribute_reads")}
        rows[kind]["distinct_rows_read"] = len(S.sets.get((phase, "rows_read:" + kind), ()))
    calls = lambda name: S.calls.get((phase, name), 0)
    n_set = lambda name: len(S.sets.get((phase, name), ()))
    per_pair = [n for (ph, name, *rest), n in S.calls.items() if ph == phase and name == "record_check_of"]
    lookups = {where: n for (ph, where), n in sorted(S.lookups.items()) if ph == phase}
    multipliers = {k[2]: n for k, n in sorted(S.calls.items(), key=str) if k[0] == phase and k[1] == "usable_multiplier"}
    lists = {k[1].split(":", 1)[1]: n for k, n in sorted(S.calls.items(), key=str)
             if k[0] == phase and len(k) == 2 and k[1].startswith("event_list:")}
    loops, by_class = {}, {}
    for (ph, name, kind, caller), n in sorted(S.years.items()):
        if ph != phase:
            continue
        entry = loops.setdefault(name, {"class": kind, "calls": S.calls.get((phase, "year_loop:" + name), 0),
                                        "yearly_values": 0, "by_caller": {}})
        entry["yearly_values"] += n
        entry["by_caller"][caller] = entry["by_caller"].get(caller, 0) + n
        by_class[kind] = by_class.get(kind, 0) + n
    other = {}
    for (ph, tag, where), n in sorted(S.other_arithmetic.items()):
        if ph == phase:
            other.setdefault(tag, {})[where] = n
    return {
        "multiplications": prod,
        "other_arithmetic_with_these_values": other,
        "row_lists": rows,
        "factor_table_lookups": {"total": sum(lookups.values()), "by_function": lookups},
        "record_checks": {"calls": calls("record_check"), "distinct_factor_stage_pairs": n_set("record_check"),
                          "most_checks_of_one_pair": max(per_pair, default=0)},
        "record_reads_from_the_resolution_table": {"calls": calls("record_read"),
                                                   "distinct_factor_stage_pairs": n_set("record_read")},
        "resolutions": {"use_calls": calls("use"),
                        "per_triple": {"calls": calls("resolve_triple"), "distinct_triples": n_set("resolve_triple")},
                        "per_row_with_row_conversions": {"calls": calls("resolve_with_row_conversions"),
                                                         "distinct_triples": n_set("resolve_with_row_conversions")}},
        "unit_conversions": {"conversion_table_lookups": calls("table_conversion"),
                             "distinct_unit_pairs": n_set("table_conversion"),
                             "conversion_table_identity_calls": calls("table_conversion_identity"),
                             "convert_calls": {"identity": calls("convert_identity"), "from_pair_memo": calls("convert_pair"),
                                               "row_list_searched_first": calls("convert_row_list")},
                             "multiplier_checks_by_function": multipliers},
        "epd_applicability_checks": calls("epd_applicability"),
        "recipes_computed": calls("recipe"),
        "event_year_lists": {"lists_by_kind": lists, "years_listed": calls("event_years_listed"),
                             "exact_year_function_calls": calls("event_year")},
        "closed_form_calls": {name: calls("closed_form:" + name) for name in CLOSED_FORMS},
        "year_loops": {"yearly_values_by_class": by_class, "by_function": loops},
        "year_table_values_read": {where: n for (ph, where), n in sorted(S.table_reads.items()) if ph == phase},
        "table_read_out": {"calls": calls("tot"), "entries": calls("tot_entries")},
        "indicator_calls": calls("indicator"), "residual_test_calls": calls("residual_test"),
    }


def _describe(scn) -> dict:
    """Row counts and distinct things of the INPUT (computed without the unified model)."""
    T = scn.boundary.study_period
    Y = cf.n_years(T)
    compositions = {tuple((c.factor_id, c.mass_fraction) for c in row.composition) for row in scn.materials if row.composition}
    periods = {row.refresh_cycle for row in scn.materials if cf.valid_period(row.refresh_cycle)}
    periods |= {eq.service_life for eq in scn.equipment
                if eq.replacement_event_list is None and cf.valid_period(eq.service_life)}
    profiles = _profiles(scn)
    descriptors = [engine._profile(p, Y) for p in profiles]
    net = descriptors[:3]
    return {
        "rows": {"materials": list.__len__(scn.materials), "equipment": list.__len__(scn.equipment),
                 "refrigerants": list.__len__(scn.refrigerants), "cost_items": len(scn.cost_items)},
        "study_period": T,
        "distinct": {"factor_records": len(scn.factors), "compositions": len(compositions),
                     "renewal_periods": len(periods)},
        "rows_with": {"own_conversions": sum(1 for r in scn.materials if r.conversions),
                      "product_specific_factor": sum(1 for r in scn.materials if r.epd is not None),
                      "composition": sum(1 for r in scn.materials if r.composition),
                      "explicit_event_list": sum(1 for e in scn.equipment if e.replacement_event_list is not None),
                      "refrigerant_change_list": sum(1 for d in scn.refrigerants if d.change_years is not None)},
        "annual_profiles_given_by_descriptor": sum(d is not None for d in descriptors),
        "annual_profiles": len(profiles),
        "grid_given_by_descriptor": cf.grid_segments(scn.operation.grid, Y) is not None,
        "all_yearly_inputs_parametric": all(d is not None for d in descriptors)
                                        and cf.grid_segments(scn.operation.grid, Y) is not None,
        "net_electricity_descriptors": all(d is not None for d in net),
    }


def _identical(a: dict, b: dict) -> bool:
    """Every public leaf equal (relative difference exactly 0, no leaf on one side only)."""
    if {k for k in a if not k.startswith("_")} != {k for k in b if not k.startswith("_")}:
        return False
    for uid, value in a.items():
        if uid.startswith("_"):
            continue
        c = compare(value, b[uid], floor=0.0)
        if c.mismatches or c.missing or c.extra or c.max_abs_rel_error != 0.0:
            return False
    return True


def measure(scn) -> dict:
    """Counts for one scenario: totals-only and full outputs, aggregate and finish apart, and a second period.

    A comparison baseline is detached first: its rows would be aggregated inside ``finish`` and counted there.
    """
    if scn.boundary.baseline_scenario is not None:
        scn = copy.copy(scn)
        scn.boundary = copy.copy(scn.boundary)
        scn.boundary.baseline_scenario = None
    plain = {False: engine.evaluate(scn, detail=False), True: engine.evaluate(scn, detail=True)}
    seen = instrument(copy.deepcopy(scn))
    T = scn.boundary.study_period
    out = {"input": _describe(scn)}
    identical = True
    with observed():
        for detail, label in ((False, "totals_only"), (True, "full_outputs")):
            _S.reset()
            _S.phase = "aggregate"
            A = engine.aggregate(seen, detail)
            _S.phase = "finish"
            result = engine.finish(A, T, detail, None)
            if not detail:
                _S.phase = "second_period"
                engine.finish(A, SECOND_PERIOD if T != SECOND_PERIOD else 2.0 * SECOND_PERIOD, False, None, _compare=False)
            _S.phase = "idle"
            identical = identical and _identical(plain[detail], result)
            entry = {"aggregate": _phase_counts("aggregate"), "finish": _phase_counts("finish")}
            if not detail:
                entry["second_period_finish"] = _phase_counts("second_period")
            entry["engine_counters"] = result["_stats"]
            entry["table_entries"] = sum(len(t) for t in result["_tables"].values())
            entry["period_groups"] = len(A.groups)
            out[label] = entry
    _S.reset()
    out["results_identical_to_an_uninstrumented_run"] = identical
    return out


# ------------------------------------------------------------------------------------------ the statements

def _products(phase_counts, tag="factor_value", field="while_reading_a_material_or_equipment_row"):
    return phase_counts["multiplications"].get(tag, {}).get(field, 0)


def statements(scenarios: dict) -> dict:
    """P1..P7 as booleans computed from the counts of every probed scenario."""
    P = {}
    names = list(scenarios)

    def each(fn):
        return {name: fn(scenarios[name]) for name in names}

    # P1
    ev = each(lambda s: {
        "factor_value_products_per_row": _products(s["totals_only"]["aggregate"]) + _products(s["totals_only"]["finish"]),
        "gas_amount_products_per_row": _products(s["totals_only"]["aggregate"], "gas_amount")
                                       + _products(s["totals_only"]["finish"], "gas_amount"),
        "factor_value_products_in_aggregation": _products(s["totals_only"]["aggregate"], field="total"),
        "gas_amount_products_in_aggregation": _products(s["totals_only"]["aggregate"], "gas_amount", "total"),
        "factor_value_products_in_recipe_builder": _products(s["totals_only"]["aggregate"], field="in_recipe_builder"),
        "other_arithmetic_with_factor_values_or_gas_amounts": sum(
            n for mode in ("totals_only", "full_outputs") for phase in ("aggregate", "finish")
            for tag in ("factor_value", "gas_amount")
            for n in s[mode][phase]["other_arithmetic_with_these_values"].get(tag, {}).values()),
        "factor_value_products_in_table_read_out": _products(s["totals_only"]["finish"], field="in_table_read_out"),
        "table_entries_read": s["totals_only"]["finish"]["table_read_out"]["entries"],
        "factor_value_products_elsewhere_in_finish": _products(s["totals_only"]["finish"], field="total")
                                                     - _products(s["totals_only"]["finish"], field="in_table_read_out"),
        "full_outputs_factor_value_products_per_row": _products(s["full_outputs"]["aggregate"]),
        "rows": s["input"]["rows"]["materials"] + s["input"]["rows"]["equipment"]})
    P["P1"] = {"statement": "totals-only mode: no multiplication by a factor-record value (or gas amount) is executed while a "
                            "material or equipment row is being read. The only such products of the whole aggregation are "
                            "those of the builder of composite factors (once per distinct composition, see P5); in finish "
                            "they are those of the table read-out (one per table entry) and of the expansion of the composite "
                            "factors (at most one per component of a composition). No other arithmetic uses these values",
               "holds": all(e["factor_value_products_per_row"] == 0 and e["gas_amount_products_per_row"] == 0
                            and e["factor_value_products_in_aggregation"] == e["factor_value_products_in_recipe_builder"]
                            and e["gas_amount_products_in_aggregation"] == 0
                            and e["factor_value_products_in_table_read_out"] <= e["table_entries_read"]
                            and e["factor_value_products_elsewhere_in_finish"] <= e["factor_value_products_in_recipe_builder"]
                            and e["other_arithmetic_with_factor_values_or_gas_amounts"] == 0 for e in ev.values()),
               "evidence": ev}

    # P2
    def p2(s):
        a, f = s["totals_only"]["aggregate"]["row_lists"], s["totals_only"]["finish"]["row_lists"]
        return {kind: {"rows": s["input"]["rows"][kind], "aggregate": a[kind], "finish": f[kind]}
                for kind in ("materials", "equipment")}
    ev = each(p2)
    P["P2"] = {"statement": "totals-only mode: the material list and the equipment list are each iterated exactly once, every "
                            "row is handed out once, nothing is read by index, and finish reads no row and no row list",
               "holds": all(e[k]["aggregate"]["iterations"] == 1 and e[k]["aggregate"]["rows_handed_out"] == e[k]["rows"]
                            and e[k]["aggregate"]["indexed_reads"] == 0 and not any(e[k]["finish"].values())
                            for e in ev.values() for k in e),
               "evidence": ev}

    # P3
    def p3(s):
        lists = Counter()
        for phase in ("aggregate", "finish"):
            lists.update(s["totals_only"][phase]["event_year_lists"]["lists_by_kind"])
        return {"lists_by_kind": dict(lists),
                "years_listed": sum(s["totals_only"][ph]["event_year_lists"]["years_listed"] for ph in ("aggregate", "finish")),
                "exact_year_function_calls": sum(s["totals_only"][ph]["event_year_lists"]["exact_year_function_calls"]
                                                 for ph in ("aggregate", "finish")),
                "full_outputs_lists_by_kind": dict(Counter(s["full_outputs"]["aggregate"]["event_year_lists"]["lists_by_kind"])
                                                   + Counter(s["full_outputs"]["finish"]["event_year_lists"]["lists_by_kind"]))}
    ev = each(p3)
    allowed = {"explicit_equipment", "refrigerant_explicit", "refrigerant_periodic"}
    P["P3"] = {"statement": "totals-only mode: no list of the years of periodic material or equipment renewals (and none for the "
                            "rebuild) is built; the lists that are built are those of explicit event lists and of refrigerant "
                            "charge changes, whose counts are given",
               "holds": all(set(e["lists_by_kind"]) <= allowed for e in ev.values()),
               "evidence": ev}

    # P4
    def p4(s):
        f = s["totals_only"]["finish"]
        return {"all_yearly_inputs_parametric": s["input"]["all_yearly_inputs_parametric"],
                "yearly_values_by_class": f["year_loops"]["yearly_values_by_class"],
                "year_table_values_read": f["year_table_values_read"],
                "year_loops_in_aggregate": s["totals_only"]["aggregate"]["year_loops"]["yearly_values_by_class"]}
    ev = each(p4)
    parametric = [e for e in ev.values() if e["all_yearly_inputs_parametric"]]
    P["P4"] = {"statement": "parametric yearly inputs, totals-only mode: no loop that computes a value per year "
                            "(class value_loop) runs; what remains is the consistency scan (descriptor values generated "
                            "and compared with the table copy), whose size is given",
               "holds": bool(parametric) and all(e["yearly_values_by_class"].get("value_loop", 0) == 0
                                                 and not e["year_loops_in_aggregate"] for e in parametric),
               "scenarios_it_was_evaluated_on": [n for n, e in ev.items() if e["all_yearly_inputs_parametric"]],
               "evidence": ev}

    # P5
    ev = each(lambda s: {"distinct_compositions": s["input"]["distinct"]["compositions"],
                         "rows_with_a_composition": s["input"]["rows_with"]["composition"],
                         "recipes_computed_totals_only": s["totals_only"]["aggregate"]["recipes_computed"],
                         "recipes_computed_full_outputs": s["full_outputs"]["aggregate"]["recipes_computed"],
                         "recipes_computed_in_finish": s["totals_only"]["finish"]["recipes_computed"]
                                                       + s["full_outputs"]["finish"]["recipes_computed"]})
    P["P5"] = {"statement": "composite factors: one computation per distinct composition, in both output modes",
               "holds": all(e["recipes_computed_totals_only"] == e["distinct_compositions"] == e["recipes_computed_full_outputs"]
                            and e["recipes_computed_in_finish"] == 0 for e in ev.values()),
               "evidence": ev}

    # P6
    ev = each(lambda s: s["totals_only"]["second_period_finish"]["row_lists"])
    P["P6"] = {"statement": "a second study period from the same aggregation reads no material row and no equipment row "
                            "(the counts for the refrigerant rows are given as well)",
               "holds": all(not any(e[k].values()) for e in ev.values() for k in ("materials", "equipment")),
               "refrigerant_rows_read_again": any(any(e["refrigerants"].values()) for e in ev.values()),
               "evidence": ev}

    # P7
    def p7(s):
        a = s["totals_only"]["aggregate"]
        return {"record_checks": a["record_checks"], "resolutions": a["resolutions"],
                "unit_conversions": a["unit_conversions"], "epd_applicability_checks": a["epd_applicability_checks"],
                "factor_table_lookups": a["factor_table_lookups"],
                "record_reads_from_the_resolution_table": a["record_reads_from_the_resolution_table"],
                "rows_with_own_conversions": s["input"]["rows_with"]["own_conversions"],
                "rows_with_product_specific_factor": s["input"]["rows_with"]["product_specific_factor"],
                "rows": s["input"]["rows"]["materials"] + s["input"]["rows"]["equipment"]}
    ev = each(p7)
    P["P7"] = {"statement": "the record part of a factor (exists, licence, stage, value and gas amounts valid) is checked once "
                            "per (factor, stage); the scenario's conversion table is consulted once per unit pair; a resolution "
                            "without row-specific conversions happens once per (factor, stage, unit). Work that is repeated per "
                            "row is limited to the resolutions of rows that carry their own conversions and to the "
                            "applicability check of a product-specific factor (both counted in the evidence), plus reads of "
                            "the memos",
               "holds": all(e["record_checks"]["calls"] == e["record_checks"]["distinct_factor_stage_pairs"]
                            and e["record_checks"]["most_checks_of_one_pair"] <= 1
                            and e["unit_conversions"]["conversion_table_lookups"] == e["unit_conversions"]["distinct_unit_pairs"]
                            and e["unit_conversions"]["conversion_table_identity_calls"] == 0
                            and e["resolutions"]["per_triple"]["calls"] == e["resolutions"]["per_triple"]["distinct_triples"]
                            for e in ev.values()),
               "evidence": ev}
    return P


def engine_counters_agree(scenarios: dict) -> dict:
    """The three counters the engine still keeps, against what was observed from outside."""
    out = {}
    for name, s in scenarios.items():
        for mode in ("totals_only", "full_outputs"):
            a, st = s[mode]["aggregate"], s[mode]["engine_counters"]
            observed_values = {"factor_records_resolved": a["factor_table_lookups"]["by_function"].get("Resolver.record", 0),
                               "unit_pairs_resolved": a["unit_conversions"]["conversion_table_lookups"],
                               "recipes_computed": a["recipes_computed"]}
            out[f"{name}/{mode}"] = {"engine": st, "observed": observed_values, "agree": st == observed_values}
    return {"all_agree": all(v["agree"] for v in out.values()), "by_scenario": out}


# ------------------------------------------------------------------------------------------ the scenarios

def mechanism_scenario(case: str):
    """The mechanism scenario of the study: seed 5, 400 material rows, 120 equipment rows, 10 refrigerant devices."""
    return synth.make_scenario(5, "RC", "office", "S", 60.0, **MECHANISM_ROWS, **MECHANISM_CASES[case])


def run(sizes: str = "SML") -> dict:
    scenarios = {case: measure(mechanism_scenario(case)) for case in MECHANISM_CASES}
    for scn in population.standard_benchmark():
        size = scn.meta.size_class
        if size in sizes:
            scn.boundary.baseline_scenario = None       # the same building without a baseline to compare with
            scenarios["benchmark_" + size] = measure(scn)
    return {
        "schema_version": "1.0",
        "what": "Operation counts of the unified model (fastcalc.engine), observed from outside with reporting stand-ins for "
                "the inputs and wrappers around the shared functions. No count is a tally kept by the engine.",
        "data_statement": "SYNTHETIC_FICTIONAL data only. Counts of this code on these inputs; not evidence about real "
                          "buildings or about any other tool.",
        "how_to_read": {
            "phases": "aggregate = the pass over the input rows; finish = everything that depends on the study period; "
                      "second_period_finish = finish again for another period from the same aggregation (totals-only mode)",
            "multiplications": "products in which the named kind of value is an operand. "
                               "while_reading_a_material_or_equipment_row excludes the builder of composite factors, which "
                               "is reported as in_recipe_builder (it runs once per distinct composition). Any addition, "
                               "subtraction or division with such a value would appear under "
                               "other_arithmetic_with_these_values",
            "year_loops": "nominal number of yearly values handled by the functions that loop over the study years, by class: "
                          "value_loop (a total is accumulated year by year), series_generation (yearly values are generated "
                          "from a descriptor), copy_check (descriptor values compared with the table copy), validity_scan "
                          "(a year table that is the input is checked), yearly_output (series of the full outputs)",
            "second_period": f"{SECOND_PERIOD:g} years (twice that when the scenario's own period is {SECOND_PERIOD:g})",
        },
        "year_loop_functions": {name: kind for name, (_, kind, _) in YEAR_LOOPS.items()},
        "scenarios": scenarios,
        "statements": statements(scenarios),
        "engine_counters": engine_counters_agree(scenarios),
        "results_identical_to_uninstrumented_runs": all(s["results_identical_to_an_uninstrumented_run"]
                                                        for s in scenarios.values()),
        "notes": [
            "The counters that remain in the engine's _stats (factor_records_resolved, unit_pairs_resolved, recipes_computed) "
            "are compared with the observed counts under engine_counters.",
            "Pseudo-key lines: the charge x GWP of a refrigerant device (tag device_gwp) and the construction electricity x "
            "grid value (tag grid_construction_value) are multiplied once per device / once per scenario in the aggregation; "
            "they are reported under multiplications and are not factor-record values.",
            "Row attribute reads are counted on the row object itself; reads of objects a row refers to (its transport or "
            "end-of-life record, its lists) are not counted separately.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--sizes", default="SML",
                    help="benchmark sizes to probe besides the mechanism scenario (e.g. S, SM, SML, '')")
    args = ap.parse_args()
    result = run(args.sizes)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    for key, st in result["statements"].items():
        print(f"{key}: {st['holds']}  {st['statement'][:110]}")
    print("engine counters agree:", result["engine_counters"]["all_agree"],
          "| results identical under instrumentation:", result["results_identical_to_uninstrumented_runs"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
