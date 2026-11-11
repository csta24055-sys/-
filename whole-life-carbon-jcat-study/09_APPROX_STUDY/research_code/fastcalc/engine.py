"""Unified model of the independent conceptual calculation.

Two steps:

``aggregate(scn)``   one pass over the input rows, independent of the study period T.
                     Every emission is written as a line (table, factor key, activity) and
                     the activities are summed per table and factor key. Lines that recur
                     with a period are summed per distinct period.
``finish(agg, T)``   applies the multipliers that depend on T (renewal counts, repair
                     years, charge cycles, weighted year sums) and reads every result
                     from the tables: a value is sum over factor keys of activity * factor.

    E[stage] = sum over lines  activity * factor * multiplier(stage; T, row parameters)

``evaluate(scn)`` = ``finish(aggregate(scn), T)``. Because the first step does not depend
on T, another study period only needs ``finish`` again (``sweep``).

Results have the same shape as the reference calculation so that they can be compared
leaf by leaf. With ``detail=False`` the per-row lists and yearly series are left out and
no factor is multiplied row by row.

Shared structure. A result counts as "unified" only when it is read from one of these
shared tables or produced by one of these shared functions; each of them is an attribute
that can be replaced from outside (``bench/membership_check.py`` breaks them one at a
time and records which results change; ``bench/mechanism_probe.py`` counts what they do):

    tables            ``Aggregate.tables`` / ``route_tables`` (activity per factor key),
                      read by ``tot(table, fval)``
    period groups     ``Aggregate.groups`` (lines summed per renewal period), multiplied by
                      ``cf.renewal_count`` and ``cf.skip_weight_periodic`` / ``_years``
    weighted sums     ``cf.linear_weighted_sum``, ``cf.table_weighted_sum``,
                      ``cf.segment_moments``, ``cf.table_moments``; the yearly series come
                      from ``_values`` (annual quantities) and ``cf.segment_values`` (grid)
    device table      ``Aggregate.charges`` (charge x GWP per refrigerant device),
                      multiplied by the fractions of ``cf.refrigerant_fractions``
    indicators        ``indicator(by_stage, subset, divisor)``
    residual test     ``_within(residual, tol, scale)``
    factor resolution ``Resolver`` (record part per (factor, stage), conversion per unit
                      pair, resolution per (factor, stage, unit)), ``_make_recipe``

Every construction of a list of event years and every loop over the study years sits in
a named function of this module or of ``closed_forms`` so that it can be counted from
outside. The only counters kept in ``_stats`` count memo misses inside ``Resolver`` and
calls of ``_make_recipe``.

Validity rules (restated from the reference calculation, which this module does not
call): a numeric input that is missing, not finite or outside its range is never used in
arithmetic; the row, route, yearly series, class or unit that needs it is left out and
counted, and every stage value it flows into is marked incomplete. Only an invalid study
period raises (``ValueError``). Inputs of a wrong type are outside the scope.

Research tooling only.
"""
from __future__ import annotations

import math

from synth import model, population

from . import closed_forms as cf

ALLOWED = model.ALLOWED_LICENCE_STATES
STAGES = model.LIFECYCLE_STAGES
MEMO = model.STAGE_MEMO


class PseudoKey:
    """Table key of lines that have no factor record (the activity is already an emission).

    Compared by identity only, so no factor id (a string) can be mistaken for it.
    """

    __slots__ = ("name",)

    def __init__(self, name: str):
        self.name = name

    def __repr__(self) -> str:
        return f"<{self.name}>"

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self

    def __reduce__(self):
        return self.name                 # pickled by the name of the module-level object


GRID = PseudoKey("GRID")                 # purchased electricity
REFRIGERANT = PseudoKey("REFRIGERANT")   # refrigerant releases
NOT_FINITE = "NOT_FINITE"                # SYS-01 finding for a NaN or infinite value
INITIAL = ("A1-A3", "A4", "A5", "C1", "C2", "C3", "C4")
UPFRONT = ("A1-A3", "A4", "A5")
EMBODIED = ("A1-A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5", "C1", "C2", "C3", "C4")
SIMPLE_CLASSES = ("REBAR", "STRUCTURAL_STEEL", "CONCRETE", "TIMBER", "ENVELOPE", "INTERIOR")
M_FIELDS = ("quantity", "waste_rate", "reuse_rate", "material_life", "repair_rate", "refresh_cycle")
E_FIELDS = ("quantity", "service_life", "repair_rate", "end_of_life_mass_kg")
R_FIELDS = ("charge_mass_kg", "gwp", "annual_leak_rate", "replacement_loss_rate", "end_of_life_recovery_rate")
# which unit tables make up each stage (B-stage tables are filled in finish)
STAGE_TABLES = {
    "A1-A3": ("A13-01", "A13-03", "A13-04", "X-01"), "A4": ("A4-01", "A4-02"), "A5": ("A5-01", "A5-02", "A5-03"),
    "B1": ("B1",), "B2": ("B2-01",), "B3": ("B3-01",), "B4": ("B4-02",), "B5": ("B5-01",), "B6": ("B6",),
    "B7": ("B7-01", "B7-02", "B7-03"), "C1": ("C1-01",), "C2": ("C2-01",), "C3": ("C3-01", "X-14"), "C4": ("C4-01",),
}
# Completeness: every unit whose result flows into a stage value (the units the stage value is composed
# from and everything they depend on, directly or indirectly). Restated from the data flow of the
# reference calculation; tests/test_engine.py asserts that it equals the closure of the registry.
STAGE_UPSTREAM = {
    "A1-A3": ("A13-01", "A13-02", "A13-03", "A13-04", "A13-05", "X-01", "X-15"),
    "A4": ("A13-05", "A4-01", "A4-02"),
    "A5": ("A5-01", "A5-02", "A5-03", "A5-04"),
    "B1": ("B1-02", "B1-03", "B1-04"),
    "B2": ("B2-01", "B6-01", "B6-04", "X-06"),
    "B3": ("A13-01", "A13-02", "A13-03", "A13-05", "B3-01", "B4-01", "B4-03", "X-01", "X-15"),
    "B4": ("A13-01", "A13-02", "A13-03", "A13-05", "A4-01", "A4-02", "B4-01", "B4-02", "B4-03", "C2-01", "C3-01",
           "C4-01", "X-01", "X-14", "X-15"),
    "B5": ("A13-01", "A13-02", "A13-03", "A13-04", "A13-05", "A4-01", "A4-02", "A5-01", "A5-02", "A5-03", "A5-04",
           "B5-01", "C1-01", "C2-01", "C3-01", "C4-01", "X-01", "X-14", "X-15"),
    "B6": ("B2-01", "B6-01", "B6-02", "B6-03", "B6-04", "X-06"),
    "B7": ("B7-01", "B7-02", "B7-03", "B7-04"),
    "C1": ("C1-01",), "C2": ("C2-01",), "C3": ("C3-01", "X-14"), "C4": ("C4-01",),
}
B6_UPSTREAM_WITHOUT_B2 = ("B6-01", "B6-02", "B6-03", "B6-04", "X-06")   # B2 outside the boundary: B6 = B6-03
# counts in a unit's public result that say "something was left out"
EXCLUSION_COUNTS = ("n_skipped", "n_routes_skipped", "n_partial", "n_invalid", "n_unresolved")

_INF = math.inf
_finite = cf.finite
_nonneg = cf.nonneg
_positive = cf.valid_period            # finite and > 0


def _ratio(x) -> bool:
    return x is not None and 0.0 <= x <= 1.0


def _within(residual, tol, scale) -> bool:
    """The one residual test shared by the area checks, the stage reconciliation and the gas total.

    False when the residual is not a number.
    """
    return abs(residual) <= tol * scale


def _left_out(result) -> bool:
    """True when a unit's public result says that something was left out or not computed."""
    for key in EXCLUSION_COUNTS:
        if result.get(key):
            return True
    return result.get("computed") is False


def _annual_unit(unit):
    head, sep, tail = unit.partition("/")
    return head if sep and tail == "year" else None


def _same(values, table) -> bool:
    """The table has an entry for every value, each a finite number equal to it within a relative 1e-12."""
    if len(table) < len(values):
        return False
    for v, t in zip(values, table):
        if not _finite(v) or not _finite(t):
            return False
        if not (v == t or abs(v - t) <= 1e-12 * max(abs(v), abs(t))):
            return False
    return True


def _record_ok(rec, stage) -> bool:
    """The record part of "may this factor be used": licence, exact stage, value and gas amounts finite >= 0."""
    if rec.licence_status not in ALLOWED or rec.stages != [stage] or not _nonneg(rec.value):
        return False
    for amount in rec.gas_amounts.values():
        if amount is None or not 0.0 <= amount < _INF:           # the test of ``_nonneg``, written out
            return False
    return True


def _epd_applies(epd, rec, assessment) -> bool:
    """The row-specific part of "may the product-specific factor be used": the row's declaration against the record."""
    return (epd.declared_stages == rec.stages and epd.declared_unit == rec.unit and epd.valid_until == rec.valid_until
            and rec.valid_until is not None and not rec.valid_until < assessment)


def tot(table, fval):
    """Value of a table: sum over its factor keys of activity * factor value (one product per key)."""
    total = 0.0
    for key, act in table.items():
        total += act * fval[key]
    return total


def indicator(by_stage, subset, divisor=1.0):
    """(Sum of the stage values of ``subset`` that are inside the boundary) / divisor.

    The one function behind the indicators: divisor 1 gives the upfront, embodied and
    whole-life totals, the floor area the total per m2, area x years the total per m2
    and year, 1000 the total in tonnes, and the whole-life total the share of a stage.
    """
    total = 0.0
    for s in subset:
        if s in by_stage:
            total += by_stage[s]
    return total / divisor


_MISSING = (None, False)        # entry of ``Resolver.records`` for a factor id without a record
_NO_HIT = (None, False)         # resolution: the factor may not be used
_NO_HIT_UNIT = (None, True)     # resolution: the factor may not be used, and the unit is (also) the reason


class Resolver:
    """The factor-resolution table of one scenario.

    Three memos, each entry computed once:

        records  (factor id, stage)        -> (record or None, usable for that stage)
        pairs    (from unit, to unit)      -> multiplier of the scenario's conversion table (None: no usable one)
        triples  (factor id, stage, unit)  -> ((factor id, multiplier) or None, the unit is the reason)

    A row that carries its own conversions cannot use ``triples`` (its multiplier may come from
    the row); it is resolved per row, but its record part still comes from ``records``.
    The findings of the unit and stage check are collected here (``n_uses``, ``unit_viol``,
    ``stage_viol``); the value of every usable factor goes to ``fval``.
    """

    __slots__ = ("factors", "conversions", "fval", "stats", "records", "pairs", "triples", "n_uses", "unit_viol",
                 "stage_viol")

    def __init__(self, scn, fval, stats):
        self.factors = scn.factors
        self.conversions = scn.unit_conversions
        self.fval = fval
        self.stats = stats
        self.records = {}
        self.pairs = {}
        self.triples = {}
        self.n_uses = 0
        self.unit_viol = set()
        self.stage_viol = set()

    def record(self, fid, stage):
        """(record or None, usable for ``stage``): the record part of a resolution, once per (factor id, stage)."""
        key = (fid, stage)
        hit = self.records.get(key)
        if hit is None:
            self.stats["factor_records_resolved"] += 1
            rec = self.factors.get(fid)
            if rec is None:
                hit = _MISSING
            elif _record_ok(rec, stage):
                self.fval[fid] = rec.value
                hit = (rec, True)
            else:
                hit = (rec, False)
            self.records[key] = hit
        return hit

    def convert(self, u, v, extra=()):
        """Multiplier from unit ``u`` to unit ``v``, or None. A row's own conversions (``extra``) are looked at first."""
        if u == v:
            return 1.0
        for c in extra:
            if c.from_unit == u and c.to_unit == v:
                return model.usable_multiplier(c.factor)     # the first entry for the pair decides
        key = (u, v)
        try:
            return self.pairs[key]
        except KeyError:
            self.stats["unit_pairs_resolved"] += 1
            r = self.pairs[key] = model.conversion_factor(self.conversions, u, v)
            return r

    def resolve(self, fid, stage, unit, extra):
        """One resolution: ((factor id, multiplier) or None, the unit is the reason)."""
        rec, ok = self.record(fid, stage)
        if rec is None:
            return _NO_HIT
        c = self.convert(unit, rec.unit, extra)
        if not ok:
            if rec.stages != [stage]:
                self.stage_viol.add(f"factors{{{fid}}}.stages")
            return _NO_HIT_UNIT if c is None else _NO_HIT
        if c is None:
            return _NO_HIT_UNIT
        return ((fid, c), False)

    def use(self, fid, stage, unit, extra, path):
        """(factor id, multiplier) when the factor may be used for an activity in ``unit``, else None."""
        self.n_uses += 1
        if unit is None:
            self.unit_viol.add(path)
            return None
        if fid is None:
            return None
        if extra:
            hit = self.resolve(fid, stage, unit, extra)
        else:
            key = (fid, stage, unit)
            hit = self.triples.get(key)
            if hit is None:
                hit = self.triples[key] = self.resolve(fid, stage, unit, ())
        if hit[1]:
            self.unit_viol.add(path)
        return hit[0]

    def unit_only(self, path, a, b, extra=()):
        """Multiplier between two units where no factor record is involved (None is a unit finding)."""
        self.n_uses += 1
        c = self.convert(a, b, extra) if a is not None and b is not None else None
        if c is None:
            self.unit_viol.add(path)
        return c


class _Group:
    """Rows renewed with the same period: their lines, summed per factor key."""

    __slots__ = ("u", "r", "resource", "waste", "incomplete", "equipment_rows")

    def __init__(self):
        self.u = {}            # one renewal: factor key -> activity
        self.r = {}            # repairs per year: factor key -> activity * repair rate
        self.resource = 0.0    # kg ordered per generation
        self.waste = 0.0       # kg of waste per generation
        self.incomplete = 0    # rows whose renewal lacks a component
        self.equipment_rows = 0


class Aggregate:
    """Everything that does not depend on the study period."""

    def __init__(self, scn, detail):
        self.scn = scn
        self.detail = detail
        self.tables = {}       # table name -> {factor key: activity}
        self.route_tables = {}  # material class -> end-of-life route -> {factor key: activity}
        self.groups = {}       # period -> _Group
        self.explicit = []     # equipment with an explicit event list
        self.charges = []      # device table: charge x GWP of each refrigerant device (None: not usable)
        self.devices = []      # per refrigerant device: what the charge cycle needs (the rows are not read again)
        self.annual = []       # annual quantities with a factor
        self.fval = {GRID: 1.0, REFRIGERANT: 1.0}   # factor key -> value (recipes get a derived value)
        self.recipes = {}      # composition content -> recipe record
        # counted inside the one function that does the work: memo misses of the resolver, calls of _make_recipe
        self.stats = {"factor_records_resolved": 0, "unit_pairs_resolved": 0, "recipes_computed": 0}
        self.resolver = None   # the factor-resolution table (Resolver)
        self.unlicensed = set()   # factor ids the licence gate found without a licence or a source (read by QA-03)
        self.out = {}          # unit id -> results that are already final
        self.rows = {}         # per-row lists (detail only)


def _add(table, key, activity):
    table[key] = table.get(key, 0.0) + activity


def aggregate(scn, detail: bool = True) -> Aggregate:
    """One pass over the input rows. Independent of the study period."""
    A = Aggregate(scn, detail)
    factors = scn.factors
    T = {name: {} for name in ("A13-01", "A13-03", "A13-04", "X-01", "A4-01", "A4-02", "X-12", "A5-01", "A5-02", "A5-03",
                               "C1-01", "C2-01", "C3-01", "C4-01", "X-14", "STO-02", "X-16")}
    for k in SIMPLE_CLASSES:
        T["CLASS:" + k] = {}
    A.tables = T
    fval = A.fval

    # ---- factor resolution: the record part once per (factor, stage), a conversion once per unit pair,
    #      a resolution once per (factor, stage, unit); rows with their own conversions are resolved per row ----
    resolver = A.resolver = Resolver(scn, fval, A.stats)
    use, conv, unit_only, record = resolver.use, resolver.convert, resolver.unit_only, resolver.record
    unit_viol = resolver.unit_viol

    # ---- licence gate: count references per factor id ----
    refs = {}
    bad_refs = {}

    def ref(fid, path):
        if fid is None:
            key = f"{path} (no factor)"
            bad_refs[key] = bad_refs.get(key, 0) + 1
        else:
            refs[fid] = refs.get(fid, 0) + 1

    # ---- input states ----
    prov = scn.provenance
    counts = {s: 0 for s in model.VALUE_STATES}
    missing = []
    MISSING, DERIVED, ZERO = model.STATE_MISSING, model.STATE_DERIVED, model.STATE_EXPLICIT_ZERO

    counts[NOT_FINITE] = 0
    not_finite = []

    def see(owner, name, value, path):
        st = owner.states.get(name) if owner.states else None
        if st is None:
            rec = prov.get(owner.provenance_id)
            st = rec.value_state if rec is not None else MISSING
        if value is None:
            st = MISSING
        elif not -_INF < value < _INF:                  # NaN or an infinity
            st = NOT_FINITE
            not_finite.append(path)
        elif st != DERIVED and value == 0:
            st = ZERO
        counts[st] += 1
        if st == MISSING or st == NOT_FINITE:
            missing.append(path)

    see(scn.project, "gross_floor_area", scn.project.gross_floor_area, "project.gross_floor_area")

    skip = dict.fromkeys(("A13-05", "A13-01", "A13-03", "A13-04", "X-01", "A4-01", "A4-02", "X-12", "C2-01", "C3-01",
                          "C4-01", "X-14", "B3", "X-10"), 0)
    routes_skipped = {"C3": 0, "C4": 0}
    n_invalid = n_unresolved = n_declined = 0
    n_bad_cycle = n_bad_life = 0            # cycles / service lives that are given but not finite positive
    x13_skip = 0
    c05_viol, c05_under = [], []
    c05_unchecked = 0
    x09_mass, x09_emis = {}, A.route_tables
    groups = A.groups
    assessment = scn.project.assessment_date
    if detail:
        L = A.rows
        for k in ("q_ord", "q_inst", "net", "disp", "a1302", "kind", "factor", "conv", "a1301", "a1303", "a1304", "a401",
                  "a402", "x12", "c2", "c3", "c4", "mcycle", "mu", "x01", "x14", "eu", "ecycle", "eexp"):
            L[k] = []

    # =============================== materials ===============================
    for i, row in enumerate(scn.materials):
        base = f"materials[{i}]"
        tr, eol = row.transport, row.end_of_life
        qu, rconv = row.quantity_unit, row.conversions
        for name in M_FIELDS:
            see(row, name, getattr(row, name), f"{base}.{name}")
        see(row, "transport.mass_t", tr.mass_t, f"{base}.transport.mass_t")
        see(row, "transport.distance_km", tr.distance_km, f"{base}.transport.distance_km")
        see(row, "end_of_life.mass_kg", eol.mass_kg, f"{base}.end_of_life.mass_kg")

        q, w = row.quantity, row.waste_rate
        if not _nonneg(q) or w is None or not 0.0 <= w < 1.0:
            q_ord = q_inst = None
            skip["A13-05"] += 1
        elif row.quantity_basis == "DESIGN":
            q_inst = q
            q_ord = q / (1.0 - w)
        else:
            q_ord = q
            q_inst = q * (1.0 - w)

        # ---- which factor (EPD, composite, generic) ----
        comp = row.composition
        recipe = None
        hit = None
        c_kg = None
        if comp is not None:
            key = tuple([(c.factor_id, c.mass_fraction) for c in comp])
            recipe = A.recipes.get(key)
            if recipe is None:
                recipe = A.recipes[key] = _make_recipe(key, resolver)
            c_kg = unit_only(f"{base}.quantity_unit", qu, "kg", rconv)
            resolver.n_uses += len(key)
            if recipe["unit_bad"]:
                unit_viol.add(f"{base}.composition")
            recipe["rows"] += 1
            if recipe["none_at"]:
                for j in recipe["none_at"]:
                    ref(None, f"{base}.composition[{j}].factor_id")
            if recipe["value"] is None:
                n_invalid += 1
        else:
            ref(row.factor_id, f"{base}.factor_id")
            hit = use(row.factor_id, "A1-A3", qu, rconv, f"{base}.quantity_unit")
        kind = f = c = fkey = None
        epd = row.epd
        if epd is not None:
            efid = epd.factor_id
            ref(efid, f"{base}.epd.factor_id")
            if efid is not None:
                rec, rec_ok = record(efid, "A1-A3")          # the record part is shared with every other use
                if rec is not None and _epd_applies(epd, rec, assessment) and rec_ok:
                    ce = conv(qu, rec.unit, rconv)
                    if ce is not None:
                        kind, f, c, fkey = "EPD", rec.value, ce, efid
            if kind is None:
                n_declined += 1
        if kind is None:
            if comp is not None:
                if recipe["value"] is not None and c_kg is not None:
                    kind, f, c, fkey = "COMPOSITE", recipe["value"], c_kg, key
            elif hit is not None:
                kind, fkey, c = "GENERIC", hit[0], hit[1]
                f = fval[fkey]
        if kind is None:
            n_unresolved += 1

        incomplete = False
        act_mfg = None
        if kind is None:
            skip["A13-01"] += 1
            incomplete = True
        elif q_ord is None:
            skip["A13-03" if kind == "EPD" else "A13-01"] += 1
            incomplete = True
        else:
            act_mfg = q_ord * c
            _add(T["A13-03" if kind == "EPD" else "A13-01"], fkey, act_mfg)
            if kind == "COMPOSITE":
                recipe["kg"] += act_mfg
                recipe["used"] = True
        r_unq = row.unquantified_cost_ratio
        g = None
        if r_unq is not None and r_unq != 0.0:
            if 0.0 < r_unq < 1.0:
                g = r_unq / (1.0 - r_unq)
                if act_mfg is not None:
                    _add(T["A13-04"], fkey, act_mfg * g)
            else:
                skip["A13-04"] += 1

        # ---- delivery: mass-distance, or per quantity ----
        dline = None
        x12 = None
        dfid = tr.delivery_factor_id
        if dfid is None:
            ref(tr.factor_id, f"{base}.transport.factor_id")
            hit = use(tr.factor_id, "A4", "tkm", (), f"{base}.transport")
            if hit is None or not _nonneg(tr.mass_t) or not _nonneg(tr.distance_km):
                skip["A4-01"] += 1
                skip["X-12"] += 1
                incomplete = True
            else:
                dline = (hit[0], tr.mass_t * tr.distance_km * hit[1])
                _add(T["A4-01"], dline[0], dline[1])
                lf = tr.load_factor
                if _positive(lf):
                    x12 = dline[1] / lf
                    _add(T["X-12"], dline[0], x12)
                else:
                    skip["X-12"] += 1
        else:
            ref(dfid, f"{base}.transport.delivery_factor_id")
            hit = use(dfid, "A4", qu, rconv, f"{base}.quantity_unit")
            if hit is None or q_ord is None:
                skip["A4-02"] += 1
                incomplete = True
            else:
                dline = (hit[0], q_ord * hit[1])
                _add(T["A4-02"], dline[0], dline[1])

        iline = None
        ifid = row.installation_factor_id
        if ifid is not None:
            ref(ifid, f"{base}.installation_factor_id")
            hit = use(ifid, "A5", qu, rconv, f"{base}.quantity_unit")
            if hit is not None and q_ord is not None:
                iline = (hit[0], q_ord * hit[1])
            else:
                incomplete = True

        # ---- end of life ----
        ref(eol.haul_factor_id, f"{base}.end_of_life.haul_factor_id")
        mass = eol.mass_kg
        mass_ok = _nonneg(mass)
        hit = use(eol.haul_factor_id, "C2", "tkm", (), f"{base}.end_of_life")
        hline = None
        if hit is None or not mass_ok or not _nonneg(eol.haul_distance_km):
            skip["C2-01"] += 1
            incomplete = True
        else:
            hline = (hit[0], mass / 1000.0 * eol.haul_distance_km * hit[1])
            _add(T["C2-01"], hline[0], hline[1])
        rlines = []
        fraction_sum = 0.0
        bad_fraction = False
        if not mass_ok:
            skip["C3-01"] += 1
            skip["C4-01"] += 1
            incomplete = True
        else:
            m_row = x09_mass.get(row.material_class)
            if m_row is None:
                m_row = x09_mass[row.material_class] = dict.fromkeys(model.EOL_ROUTES, 0.0)
                x09_emis[row.material_class] = {r: {} for r in model.EOL_ROUTES}
            e_row = x09_emis[row.material_class]
        for j, route in enumerate(eol.routes):
            ref(route.factor_id, f"{base}.end_of_life.routes[{j}].factor_id")
            p = route.fraction
            p_ok = _nonneg(p)
            if p_ok:
                fraction_sum += p
            else:
                bad_fraction = True
            stage = "C4" if route.route == "LANDFILL" else "C3"
            hit = use(route.factor_id, stage, "kg", (), f"{base}.end_of_life")
            if not mass_ok:
                continue
            if p_ok:
                m_row[route.route] += mass * p
            if hit is None or not p_ok:
                routes_skipped[stage] += 1
                incomplete = True
                continue
            act = mass * p * hit[1]
            _add(T["C4-01" if stage == "C4" else "C3-01"], hit[0], act)
            _add(e_row[route.route], hit[0], act)
            rlines.append((stage, hit[0], act))
        if bad_fraction or fraction_sum > 1.0 + 1e-6:
            c05_viol.append(f"{base}.end_of_life.routes")
        elif fraction_sum < 1.0 - 1e-6:
            c05_under.append(f"{base}.end_of_life.routes")
        c_any = conv(qu, "kg", rconv) if comp is None else c_kg
        if c_any is None or q_inst is None or not mass_ok:
            c05_unchecked += 1
        elif mass > q_inst * c_any * (1.0 + 1e-6):
            c05_viol.append(f"{base}.end_of_life.mass_kg")

        # ---- the row's lines go to the group of its renewal period ----
        cycle = row.refresh_cycle
        if not cf.valid_period(cycle):
            if cycle is not None:
                n_bad_cycle += 1
            cycle = None
        grp = groups.get(cycle)
        if grp is None:
            grp = groups[cycle] = _Group()
        gu = grp.u
        if act_mfg is not None:
            gu[fkey] = gu.get(fkey, 0.0) + act_mfg
        if dline is not None:
            gu[dline[0]] = gu.get(dline[0], 0.0) + dline[1]
        if hline is not None:
            gu[hline[0]] = gu.get(hline[0], 0.0) + hline[1]
        for _, rk, act in rlines:
            gu[rk] = gu.get(rk, 0.0) + act
        if iline is not None:
            gu[iline[0]] = gu.get(iline[0], 0.0) + iline[1]
        if incomplete:
            grp.incomplete += 1
        rr = row.repair_rate
        if not _nonneg(rr):
            skip["B3"] += 1
        elif act_mfg is not None and rr != 0.0:
            grp.r[fkey] = grp.r.get(fkey, 0.0) + act_mfg * rr
        if c_any is None or q_ord is None or not mass_ok:
            skip["X-10"] += 1
        else:
            grp.resource += q_ord * c_any
            grp.waste += (q_ord - q_inst) * c_any + mass

        # ---- class table for the simplified estimate ----
        if act_mfg is not None:
            mc = row.material_class
            cls = mc if mc in ("REBAR", "STRUCTURAL_STEEL", "CONCRETE", "TIMBER") else None
            if cls is None and qu == "m2":
                div = row.construction_division
                cls = "ENVELOPE" if div in ("ROOF_EXTERIOR_WALL", "OPENINGS") else "INTERIOR" if div == "INTERIOR" else None
            if cls is not None:
                _add(T["CLASS:" + cls], fkey, act_mfg)

        rho = row.reuse_rate
        x13_bad = q_ord is None or rho is None or not 0.0 <= rho <= 1.0
        if x13_bad:
            x13_skip += 1
        if detail:                                      # per-row outputs: here factors are multiplied row by row
            e_mfg = act_mfg * f if act_mfg is not None else 0.0
            v = lambda line: line[1] * fval[line[0]] if line is not None else 0.0
            e_del, e_c2 = v(dline), v(hline)
            e_c3 = sum(act * fval[rk] for st, rk, act in rlines if st == "C3")
            e_c4 = sum(act * fval[rk] for st, rk, act in rlines if st == "C4")
            L["q_ord"].append(q_ord)
            L["q_inst"].append(q_inst)
            if x13_bad:
                L["net"].append(None)
                L["disp"].append(None)
            else:
                d = (q_ord - q_inst) * (1.0 - rho)
                L["disp"].append(d)
                L["net"].append(q_inst + d)
            L["a1302"].append(recipe["value"] if recipe is not None else None)
            L["kind"].append(kind)
            L["factor"].append(f)
            L["conv"].append(c)
            L["a1301"].append(e_mfg if kind in ("GENERIC", "COMPOSITE") else 0.0)
            L["a1303"].append(e_mfg if kind == "EPD" else 0.0)
            L["a1304"].append(e_mfg * g if g is not None else 0.0)
            L["a401"].append(e_del if dfid is None else 0.0)
            L["a402"].append(e_del if dfid is not None else 0.0)
            L["x12"].append(x12 * fval[dline[0]] if x12 is not None else 0.0)
            L["c2"].append(e_c2)
            L["c3"].append(e_c3)
            L["c4"].append(e_c4)
            L["mcycle"].append(cycle)
            L["mu"].append(e_mfg + e_del + e_c2 + e_c3 + e_c4 + v(iline))

    # =============================== equipment ===============================
    for j, eq in enumerate(scn.equipment):
        base = f"equipment[{j}]"
        for name in E_FIELDS:
            value = getattr(eq, name)
            if name == "service_life" and value is None and eq.replacement_event_list is not None:
                continue
            see(eq, name, value, f"{base}.{name}")
        qty = eq.quantity
        qty_ok = _nonneg(qty)
        ref(eq.factor_id, f"{base}.factor_id")
        hit = use(eq.factor_id, "A1-A3", eq.quantity_unit, (), f"{base}.quantity_unit")
        lines = []
        incomplete = False
        mline = None
        if not qty_ok or hit is None:
            skip["X-01"] += 1
            incomplete = True
        else:
            mline = (hit[0], qty * hit[1])
            _add(T["X-01"], mline[0], mline[1])
            lines.append(mline)
        for fid, stage in ((eq.delivery_factor_id, "A4"), (eq.installation_factor_id, "A5")):
            if fid is None:
                continue
            refs[fid] = refs.get(fid, 0) + 1
            hit = use(fid, stage, eq.quantity_unit, (), f"{base}.quantity_unit")
            if hit is None or not qty_ok:
                incomplete = True
            else:
                lines.append((hit[0], qty * hit[1]))
        efid = eq.eol_factor_id
        eline = None
        hit = None
        ref(efid, f"{base}.eol_factor_id")              # a mandatory slot: without it the row is left out of X-14
        if efid is not None:
            hit = use(efid, "C3", "kg", (), f"{base}.end_of_life")
        emass_ok = _nonneg(eq.end_of_life_mass_kg)
        if hit is None or not emass_ok:
            skip["X-14"] += 1
            incomplete = True
        else:
            eline = (hit[0], eq.end_of_life_mass_kg * hit[1])
            _add(T["X-14"], eline[0], eline[1])
            lines.append(eline)
        rr = eq.repair_rate
        rline = None
        if not _nonneg(rr):
            skip["B3"] += 1
        elif mline is not None and rr != 0.0:
            rline = (mline[0], mline[1] * rr)
        years = eq.replacement_event_list
        if years is not None:
            A.explicit.append((j, years, lines, rline, eq.end_of_life_mass_kg if emass_ok else None, incomplete))
            cycle = None
        else:
            cycle = eq.service_life
            if not cf.valid_period(cycle):
                if cycle is not None:
                    n_bad_life += 1
                cycle = None
            grp = groups.get(cycle)
            if grp is None:
                grp = groups[cycle] = _Group()
            for fk, act in lines:
                grp.u[fk] = grp.u.get(fk, 0.0) + act
            if rline is not None:
                grp.r[rline[0]] = grp.r.get(rline[0], 0.0) + rline[1]
            if incomplete:
                grp.incomplete += 1
            grp.equipment_rows += 1
            if emass_ok:
                grp.waste += eq.end_of_life_mass_kg
        if not emass_ok:
            skip["X-10"] += 1
        if detail:
            L["x01"].append(mline[1] * fval[mline[0]] if mline is not None else 0.0)
            L["x14"].append(eline[1] * fval[eline[0]] if eline is not None else 0.0)
            L["eu"].append(sum(act * fval[fk] for fk, act in lines))
            L["ecycle"].append(cycle)
            L["eexp"].append(years is not None)

    # =============================== refrigerants ===============================
    # One table entry per device: its charge in CO2e (charge x GWP). B1-01 is the sum of the table and
    # B1-02..04 multiply the same entries by the fractions of the charge cycle (in finish). Everything
    # else the charge cycle needs is copied here, so that finish does not read the rows again.
    charges, devices = A.charges, A.devices
    for j, dev in enumerate(scn.refrigerants):
        base = f"refrigerants[{j}]"
        for name in R_FIELDS:
            see(dev, name, getattr(dev, name), f"{base}.{name}")
        life, change_years = dev.service_life, dev.change_years
        if life is None and change_years is None:
            see(dev, "service_life", None, f"{base}.service_life")
        charge_ok = _nonneg(dev.charge_mass_kg) and _nonneg(dev.gwp)
        charges.append(dev.charge_mass_kg * dev.gwp if charge_ok else None)
        life_ok = change_years is not None or life is None or cf.valid_period(life)
        rate = dev.annual_leak_rate
        devices.append((charge_ok and _ratio(rate) and life_ok, rate, dev.top_up, change_years, life,
                        dev.replacement_loss_rate, dev.end_of_life_recovery_rate))

    # =============================== construction site ===============================
    site = scn.construction
    grid = scn.operation.grid
    grid_ok = grid.licence_status in ALLOWED
    head, sep, tail = grid.unit.partition("/")
    grid_u = tail if sep and head == "kgCO2e" and tail else None
    see(site, "electricity_kwh", site.electricity_kwh, "construction.electricity_kwh")
    c_site = unit_only("construction.electricity", "kWh", grid_u)
    a5_01_ok = _nonneg(site.electricity_kwh) and c_site is not None and grid_ok and _nonneg(grid.construction_value)
    if a5_01_ok:
        _add(T["A5-01"], GRID, site.electricity_kwh * c_site * grid.construction_value)
    a5_02_skip = a5_03_skip = 0
    for k, fuel in enumerate(site.fuels):
        see(site, f"fuels[{k}].quantity", fuel.quantity, f"construction.fuels[{k}].quantity")
        ref(fuel.factor_id, f"construction.fuels[{k}].factor_id")
        hit = use(fuel.factor_id, "A5", fuel.unit, fuel.conversions, f"construction.fuels[{k}].unit")
        if not _nonneg(fuel.quantity) or hit is None:
            a5_02_skip += 1
        else:
            _add(T["A5-02"], hit[0], fuel.quantity * hit[1])
    for k, waste in enumerate(site.waste_streams):
        see(site, f"waste_streams[{k}].mass_kg", waste.mass_kg, f"construction.waste_streams[{k}].mass_kg")
        ref(waste.factor_id, f"construction.waste_streams[{k}].factor_id")
        hit = use(waste.factor_id, "A5", "kg", (), f"construction.waste_streams[{k}]")
        if not _nonneg(waste.mass_kg) or hit is None:
            a5_03_skip += 1
        else:
            _add(T["A5-03"], hit[0], waste.mass_kg * hit[1])

    # =============================== operation: units and factors (values wait for T) ===============================
    op, ww = scn.operation, scn.water_waste
    eu = _annual_unit(op.electricity.unit)
    c_elec = unit_only("operation.electricity", eu, grid_u)
    c_gen = unit_only("operation.onsite_generation", _annual_unit(op.onsite_generation.unit), eu)
    c_exp = unit_only("operation.onsite_export", _annual_unit(op.onsite_export.unit), eu)
    for table, profile, fid, path, stage in (
            ("B6-02", op.gas, op.gas_factor_id, "operation.gas", "B6"),
            ("B6-02", op.oil, op.oil_factor_id, "operation.oil", "B6"),
            ("B6-02", op.district_heat, op.district_heat_factor_id, "operation.district_heat", "B6"),
            ("B7-01", ww.water, ww.water_factor_id, "water_waste.water", "B7"),
            ("B7-02", ww.sewage, ww.sewage_factor_id, "water_waste.sewage", "B7"),
            ("B7-03", ww.municipal_waste, ww.waste_factor_id, "water_waste.municipal_waste", "B7")):
        ref(fid, path.replace("municipal_waste", "waste") + "_factor_id")
        A.annual.append((table, profile, use(fid, stage, _annual_unit(profile.unit), (), path)))

    # =============================== building-level end of life, memo items, cost items ===============================
    end = scn.end_of_life
    c1_skip = 0
    for k, act in enumerate(end.demolition_activities):
        see(end, f"demolition_activities[{k}].quantity", act.quantity, f"end_of_life.demolition_activities[{k}].quantity")
        ref(act.factor_id, f"end_of_life.demolition_activities[{k}].factor_id")
        hit = use(act.factor_id, "C1", act.unit, (), f"end_of_life.demolition_activities[{k}].unit")
        if not _nonneg(act.quantity) or hit is None:
            c1_skip += 1
        else:
            _add(T["C1-01"], hit[0], act.quantity * hit[1])
    for k, haul in enumerate(end.waste_hauls):
        see(end, f"waste_hauls[{k}].mass_t", haul.mass_t, f"end_of_life.waste_hauls[{k}].mass_t")
        see(end, f"waste_hauls[{k}].distance_km", haul.distance_km, f"end_of_life.waste_hauls[{k}].distance_km")
        ref(haul.factor_id, f"end_of_life.waste_hauls[{k}].factor_id")
        hit = use(haul.factor_id, "C2", "tkm", (), f"end_of_life.waste_hauls[{k}]")
        if hit is None or not _nonneg(haul.mass_t) or not _nonneg(haul.distance_km):
            skip["C2-01"] += 1
        else:
            _add(T["C2-01"], hit[0], haul.mass_t * haul.distance_km * hit[1])
    sq = scn.summary_quantities
    sto_02_ok = False
    if sq.concrete_uptake_factor_id is not None:
        refs[sq.concrete_uptake_factor_id] = refs.get(sq.concrete_uptake_factor_id, 0) + 1
        hit = use(sq.concrete_uptake_factor_id, MEMO, "m3", (), "summary_quantities.concrete_uptake")
        if hit is not None and _nonneg(sq.concrete_m3):
            _add(T["STO-02"], hit[0], sq.concrete_m3 * hit[1])
            sto_02_ok = True
    x16_skip = 0
    x16_items = []
    deflator = {}
    for k, item in enumerate(scn.cost_items):
        ref(item.factor_id, f"cost_items[{k}].factor_id")
        hit = use(item.factor_id, "A1-A3", item.currency, (), f"cost_items[{k}]")
        dkey = (item.factor_base_year, item.price_year)
        if dkey not in deflator:                         # one ratio per distinct pair of years
            pb, pc = scn.price_index.get(item.factor_base_year), scn.price_index.get(item.price_year)
            deflator[dkey] = pb / pc if _positive(pb) and _positive(pc) else None
        d = deflator[dkey]
        if not _nonneg(item.amount) or hit is None or d is None:
            x16_skip += 1
            x16_items.append(None)
        else:
            act = item.amount * d * hit[1]
            _add(T["X-16"], hit[0], act)
            x16_items.append((hit[0], act))

    # =============================== checks that do not depend on T ===============================
    for key, rec in A.recipes.items():
        for fid, _ in key:
            if fid is not None:
                refs[fid] = refs.get(fid, 0) + rec["rows"]
    n_refs = sum(bad_refs.values())
    unlicensed = A.unlicensed                           # referenced records without a licence or a source
    for fid, count in refs.items():
        n_refs += count
        rec = factors.get(fid)
        if rec is None:
            bad_refs[f"factors{{{fid}}} (no record)"] = count
        elif rec.licence_status not in ALLOWED or not rec.source_url:
            bad_refs[f"factors{{{fid}}}.licence_status"] = count
            unlicensed.add(fid)
    if not grid_ok:
        bad_refs["operation.grid"] = 1
    area = scn.project.gross_floor_area
    area_sum = 0.0
    for use_name in sorted(scn.project.use_area_breakdown):
        use_area = scn.project.use_area_breakdown[use_name]
        if not _nonneg(use_area):
            area_sum = None                              # a use area that cannot be used: no sum
            break
        area_sum += use_area
    area_ok = _positive(area)
    if not area_ok or area_sum is None:
        sys_04 = {"ok": False, "status": "INVALID", "sum": area_sum, "residual": None}
        qa_04 = {"ok": False, "status": "NOT_EVALUATED"}
    else:
        residual = area - area_sum
        sys_04 = {"ok": _within(residual, 1e-9, area), "status": "EVALUATED", "sum": area_sum, "residual": residual}
        qa_04 = {"ok": _within(residual, 1e-6, area), "status": "EVALUATED"}

    A.out = {
        "SYS-01": {"ok": not missing, "counts": counts, "violations": missing, "not_finite": not_finite},
        # the unit and stage check is read from the resolution table
        "SYS-02": {"ok": not unit_viol and not resolver.stage_viol, "n_checked": resolver.n_uses,
                   "violations": sorted(unit_viol), "stage_mismatches": sorted(resolver.stage_viol)},
        "SYS-03": {"ok": not bad_refs, "n_checked": n_refs + 1, "violations": sorted(bad_refs),
                   "n_references_affected": sum(bad_refs.values())},
        "SYS-04": sys_04,
        "QA-04": qa_04,
        "A13-05": {"n_skipped": skip["A13-05"]},
        "A13-02": {"n_invalid": n_invalid},
        "X-15": {"n_unresolved": n_unresolved, "n_epd_declined": n_declined},
        "C-05": {"ok": not c05_viol, "violations": c05_viol, "under_allocated": c05_under, "n_mass_unchecked": c05_unchecked},
    }
    A.misc = {"skip": skip, "routes_skipped": routes_skipped, "a5_01_ok": a5_01_ok, "a5_02_skip": a5_02_skip,
              "a5_03_skip": a5_03_skip, "c1_skip": c1_skip, "x16_skip": x16_skip, "x16_items": x16_items,
              "sto_02_ok": sto_02_ok, "x09_mass": x09_mass, "grid_ok": grid_ok, "c_elec": c_elec, "c_gen": c_gen,
              "c_exp": c_exp, "c_site": c_site, "area_ok": area_ok, "n_bad_cycle": n_bad_cycle, "n_bad_life": n_bad_life,
              "x13_skip": x13_skip}
    return A


def _make_recipe(key, resolver):
    """Composite factor of one distinct composition: value per kg, computed once.

    The record part and the conversion of every component come from the resolution table.
    """
    resolver.stats["recipes_computed"] += 1
    total_fraction = value = 0.0
    ok = True
    unit_bad = False
    none_at = []
    parts = []
    for j, (fid, fraction) in enumerate(key):
        if fid is None:
            none_at.append(j)
            rec, rec_ok = _MISSING
        else:
            rec, rec_ok = resolver.record(fid, "A1-A3")
        c = resolver.convert("kg", rec.unit) if rec is not None else None
        if rec is not None and c is None:
            unit_bad = True
        if rec is not None and rec.stages != ["A1-A3"]:
            resolver.stage_viol.add(f"factors{{{fid}}}.stages")
        if rec is None or c is None or not rec_ok or not _nonneg(fraction):
            ok = False
            continue
        total_fraction += fraction
        value += fraction * c * rec.value
        parts.append((fid, fraction, c))
    valid = ok and abs(total_fraction - 1.0) <= 1e-6
    if valid:
        resolver.fval[key] = value
    return {"value": value if valid else None, "parts": parts if valid else None, "unit_bad": unit_bad,
            "none_at": none_at, "rows": 0, "kg": 0.0, "used": False}


def _valid_period(T) -> bool:
    return not (T is None or isinstance(T, bool) or not (T > 0.0) or math.isinf(T))


def check_period(scn) -> float:
    """The study period, or ValueError when it is not a finite positive number (the only refusal)."""
    T = scn.boundary.study_period
    if not _valid_period(T):
        raise ValueError("study_period must be a finite positive number of years")
    return T


def _profile(profile, Y):
    """(base, slope) of a parametric profile whose descriptor is given, or None when the year table is the input."""
    if profile.kind == "CONSTANT" and profile.base is not None:
        return profile.base, 0.0
    if profile.kind == "LINEAR_TREND" and profile.base is not None and profile.slope is not None:
        return profile.base, profile.slope
    return None


def _profile_state(profile, Y):
    """(descriptor or None, usable, copy matches) of an annual quantity for Y study years.

    Usable: every one of the Y yearly values that count is finite and >= 0. For a descriptor
    base and slope must be finite, and because base + slope*k is monotone in k (also in
    floating point) the two end values bound every year. For a year table the first Y
    entries are scanned and there must be Y of them. The copy check compares the
    descriptor values with the table copy; it is true when the table itself is the input.
    """
    d = _profile(profile, Y)
    if d is None:
        return None, cf.table_usable(profile.table, Y), True
    base, slope = d
    if not _finite(base) or not _finite(slope):
        return d, False, False
    usable = _nonneg(base + slope * 0) and _nonneg(base + slope * (Y - 1)) if slope else _nonneg(base)
    return d, usable, _same(_values(profile, Y), profile.table)


def _values(profile, Y):
    d = _profile(profile, Y)
    if d is None:
        return profile.table[:Y]
    return [d[0] + d[1] * k for k in range(Y)] if d[1] else [d[0]] * Y


# ---- every list of event years is built by one of these four functions ----

def _explicit_event_years(T, entries):
    """Years of the entries of an equipment row's explicit event list that are used (list order)."""
    return cf.explicit_years(T, entries)


def _change_years(T, change_years, service_life):
    """Years of the charge changes of one refrigerant device, in non-decreasing order."""
    if change_years is not None:
        return sorted(cf.explicit_years(T, change_years))
    if service_life is None:
        return []                                       # no list and no service life: the charge is never changed
    return cf.periodic_years(service_life, cf.renewal_count(T, service_life))


def _renewal_years(period, n_events):
    """Years of the periodic renewals of the rows that share a period (only the yearly outputs need them)."""
    return cf.periodic_years(period, n_events)


def _rebuild_years(period, n_events):
    """Years of the rebuild or major-refurbishment events (only the yearly output needs them)."""
    return cf.periodic_years(period, n_events)


# ---- every loop over the study years is in a named function: the five below, ``_values`` and ``_same``
#      above, and the year scans of closed_forms ----

def _purchased_series(consumption, generation, export, c_gen, c_exp, c_elec, g_values, elec_ok, Y, wl):
    """Year by year: purchased electricity max(0, .), its emission, and the weighted sum of the emission."""
    net_series = [0.0]
    elec_series = [0.0]
    elec_w = 0.0
    for k in range(Y):
        nk = max(0.0, consumption[k] - (generation[k] * c_gen - export[k] * c_exp))
        ek = nk * c_elec * g_values[k] if elec_ok else 0.0
        net_series.append(nk)
        elec_series.append(ek)
        elec_w += (wl if k == Y - 1 else 1.0) * ek
    return net_series, elec_series, elec_w


def _add_leak_series(out, charge, rate, top_up, ev_years, Y, wl):
    """Add the yearly leak of one refrigerant device to ``out`` (the series needs one value per year)."""
    m = 1.0
    k = 0
    for y in range(1, Y + 1):
        leak = m * rate * (wl if y == Y else 1.0)
        out[y] += charge * leak
        if not top_up:
            m -= leak
        while k < len(ev_years) and ev_years[k] == y:
            m = 1.0
            k += 1


def _add_repair_series(out, rate, w, skip_years, Y):
    """Add the yearly repair emission ``rate`` to ``out`` for every year without a renewal."""
    for y in range(1, Y + 1):                           # added year by year, never by subtraction
        if y not in skip_years:
            out[y] += rate * w[y]


def _annual_series(parts, fval, Y):
    """Yearly emission (unweighted) of the annual quantities of one unit."""
    out = [0.0] * (Y + 1)
    for profile, hit in parts:
        values = _values(profile, Y)
        value = fval[hit[0]]
        for k in range(Y):
            out[k + 1] += values[k] * hit[1] * value
    return out


def _whole_life_series(inc, stage_all, share, w, elec_series, series, b1_year, b1_event_year, b3_year, b4_year, b5_year,
                       b1_04, Y):
    """The whole-life series: initial stages in year 0, the yearly series, the end-of-life stages in the last year."""
    out = [0.0] * (Y + 1)
    for s in ("A1-A3", "A4", "A5"):
        if s in inc:
            out[0] += stage_all[s]
    for y in range(1, Y + 1):
        e = 0.0
        ew = w[y] * elec_series[y]
        if "B6" in inc:
            e += (ew * (1.0 - share) if "B2" in inc else ew) + w[y] * series["B6-02"][y]
        if "B2" in inc:
            e += ew * share
        if "B7" in inc:
            e += w[y] * (series["B7-01"][y] + series["B7-02"][y] + series["B7-03"][y])
        if "B1" in inc:
            e += b1_year[y] + b1_event_year[y]
        if "B3" in inc:
            e += b3_year[y]
        if "B4" in inc:
            e += b4_year[y]
        if "B5" in inc:
            e += b5_year[y]
        out[y] += e
    last = Y if Y >= 1 else 0
    for s in ("C1", "C2", "C3", "C4"):
        if s in inc:
            out[last] += stage_all[s]
    if "B1" in inc:
        out[last] += b1_04
    cumulative, running = [], 0.0
    for v in out:
        running += v
        cumulative.append(running)
    return {"by_year": out, "cumulative": cumulative, "value": running}


def finish(A: Aggregate, T: float | None = None, detail: bool | None = None, baseline_totals: dict | None = None,
           _compare: bool = True) -> dict:
    """Apply the multipliers that depend on the study period and read the results from the tables.

    ``baseline_totals`` is an optional dict the caller keeps in order to reuse the whole-life total of a
    baseline: ``{baseline id: {"value": total, "complete": bool}}``. The key is the proposal's input
    ``boundary.baseline_scenario``; it identifies the baseline BY NAME ONLY. A held entry is used as it
    is, so any change of the baseline scenario, of the study period or of the boundary (stages) makes
    it invalid: the caller must then drop it.
    """
    scn = A.scn
    if T is None:
        T = check_period(scn)
    elif not _valid_period(T):
        raise ValueError("study_period must be a finite positive number of years")
    detail = A.detail if detail is None else detail
    if detail and not A.detail:
        raise ValueError("the aggregate was built without per-row lists")
    Y = cf.n_years(T)
    wl = cf.last_weight(T)
    factors = scn.factors
    fval = A.fval
    tables = dict(A.tables)
    M = A.misc
    inc = set(scn.boundary.included_lifecycle_stages)
    bnd = scn.boundary
    op, ww = scn.operation, scn.water_waste
    grid = op.grid

    # ---- renewals, repairs, masses: one multiplier per distinct period ----
    b4, b3, b3_alt = {}, {}, {}
    n_partial = 0
    resource = waste = 0.0
    counts = {}
    for cycle, grp in A.groups.items():
        n = cf.renewal_count(T, cycle)
        counts[cycle] = n
        resource += grp.resource * (1 + n)
        waste += grp.waste * (1 + n)
        if n:
            n_partial += grp.incomplete
            for key, act in grp.u.items():
                b4[key] = b4.get(key, 0.0) + act * n
        if grp.r:
            years = T - cf.skip_weight_periodic(T, cycle, n) if n else T
            for key, act in grp.r.items():
                b3[key] = b3.get(key, 0.0) + act * years
                b3_alt[key] = b3_alt.get(key, 0.0) + act * T
    explicit_b4 = {}
    explicit_events = {}
    n_events = sum(counts[c] * g.equipment_rows for c, g in A.groups.items())
    qa02, qa02_warn = [], []

    def check_list(entries, path):
        """QA-02 for one explicit list: every entry a finite number, 0 <= t, inside; t = 0 and repeats are warnings."""
        numbers = [t for t in entries if _finite(t)]
        if len(numbers) < len(entries) or any(not (t >= 0 and cf.inside(t, T)) for t in numbers):
            qa02.append(path)
        if any(t == 0 for t in numbers) or len(set(numbers)) < len(numbers):
            qa02_warn.append(path)

    for j, years, lines, rline, emass, incomplete in A.explicit:
        check_list(years, f"equipment[{j}].replacement_event_list")
        events = _explicit_event_years(T, years)        # the years of the entries that are used
        explicit_events[j] = events
        n = len(events)
        n_events += n
        if n:
            for key, act in lines:
                explicit_b4[key] = explicit_b4.get(key, 0.0) + act * n
            if incomplete:
                n_partial += 1
        if rline is not None:
            b3[rline[0]] = b3.get(rline[0], 0.0) + rline[1] * (T - cf.skip_weight_years(T, events))
            b3_alt[rline[0]] = b3_alt.get(rline[0], 0.0) + rline[1] * T
        if emass is not None:
            waste += emass * (1 + n)
    for key, act in explicit_b4.items():
        b4[key] = b4.get(key, 0.0) + act
    tables["B4-02"], tables["B3-01"], tables["B3-02"] = b4, b3, b3_alt

    # ---- refrigerants: the device table (charge x GWP) times the fractions of the charge cycle ----
    b1_01 = b1_02 = b1_03 = b1_04 = 0.0
    b1_01_skip = 0
    b1_skip = [0, 0, 0]
    b1_items = []
    b1_year = [0.0] * (Y + 1)
    b1_event_year = [0.0] * (Y + 1)
    charges = A.charges
    for j, (ok, rate, top_up, years_raw, life, loss_rate, recovery_rate) in enumerate(A.devices):
        charge = charges[j]                             # the device's charge in CO2e: the activity of all four terms
        if charge is None:
            b1_01_skip += 1
        else:
            b1_01 += charge                             # B1-01: the sum of the device table
        if years_raw is not None:
            check_list(years_raw, f"refrigerants[{j}].change_years")
        loss_ok, rec_ok = _ratio(loss_rate), _ratio(recovery_rate)
        if not ok:
            b1_skip[0] += 1
            b1_skip[1] += 1
            b1_skip[2] += 1
            b1_items.append(0.0)
            continue
        ev_years = _change_years(T, years_raw, life)
        leaked, before, end = cf.refrigerant_fractions(T, rate, top_up, ev_years)
        b1_02 += charge * leaked
        b1_items.append(charge * leaked)
        if loss_ok:
            for y, share in zip(ev_years, before):
                loss = charge * share * loss_rate
                b1_03 += loss
                b1_event_year[y] += loss
        else:
            b1_skip[1] += 1
        if rec_ok:
            b1_04 += charge * end * (1.0 - recovery_rate)
        else:
            b1_skip[2] += 1
        if detail:                                      # the yearly series needs one value per year
            _add_leak_series(b1_year, charge, rate, top_up, ev_years, Y, wl)
    tables["B1"] = {REFRIGERANT: b1_02 + b1_03 + b1_04}

    # ---- grid factor: moments of a piecewise-linear series, or of the table ----
    segments = cf.grid_segments(grid, Y)
    if segments is not None:
        grid_source = "DESCRIPTOR"
        G, H = cf.segment_moments(segments, T)
        g_values = cf.segment_values(segments)          # one value per year: for the copy check and the yearly outputs
        grid_matches = _same(g_values, grid.table)
    elif cf.table_usable(grid.table, Y):
        grid_source = "TABLE"
        G, H = cf.table_moments(grid.table, T)
        g_values = grid.table[:Y]
        grid_matches = True                             # the table itself is the input
    else:                                               # neither a well-formed descriptor nor a usable table
        grid_source = "NONE"
        G = H = 0.0
        g_values = [0.0] * Y
        grid_matches = False
    grid_usable = grid_source != "NONE"

    # ---- purchased electricity ----
    c_elec, c_gen, c_exp = M["c_elec"], M["c_gen"], M["c_exp"]
    eu = _annual_unit(op.electricity.unit)
    profiles = (op.electricity, op.onsite_generation, op.onsite_export)
    states = [_profile_state(p, Y) for p in profiles]
    net_match = all(st[2] for st in states)
    net_ok = eu is not None and c_gen is not None and c_exp is not None and all(st[1] for st in states)
    elec_ok = M["grid_ok"] and grid_usable and net_ok and c_elec is not None
    net_series = elec_series = None
    elec_w = 0.0
    params = [st[0] for st in states]
    linear = None
    if net_ok and all(p is not None for p in params):
        B = params[0][0] - (params[1][0] * c_gen - params[2][0] * c_exp)
        S = params[0][1] - (params[1][1] * c_gen - params[2][1] * c_exp)
        if B >= 0.0 and B + S * (Y - 1) >= 0.0:        # the clamp max(0, .) never acts
            linear = (B, S)
    if linear is not None and not detail:
        if elec_ok:
            elec_w = (linear[0] * G + linear[1] * H) * c_elec
    elif net_ok:
        c_v, g_v, x_v = (_values(p, Y) for p in profiles)
        net_series, elec_series, elec_w = _purchased_series(c_v, g_v, x_v, c_gen, c_exp, c_elec, g_values, elec_ok, Y, wl)
        if linear is not None and elec_ok:
            elec_w = (linear[0] * G + linear[1] * H) * c_elec
    else:
        net_series = [0.0] * (Y + 1)
        elec_series = [0.0] * (Y + 1)
    share = op.facility_management_ratio
    b2_ok = _ratio(share) and elec_ok
    b2 = elec_w * share if b2_ok else 0.0
    tables["B2-01"] = {GRID: b2}
    tables["B6-01"] = {GRID: elec_w}

    # ---- annual quantities with a factor: weighted year sums ----
    for name in ("B6-02", "B7-01", "B7-02", "B7-03"):
        tables[name] = {}
    annual_skip = dict.fromkeys(("B6-02", "B7-01", "B7-02", "B7-03"), 0)
    annual_match = dict.fromkeys(("B6-02", "B7-01", "B7-02", "B7-03"), True)
    annual_parts = {name: [] for name in annual_skip}
    for name, profile, hit in A.annual:
        d, usable, matches = _profile_state(profile, Y)
        annual_match[name] = annual_match[name] and matches
        if hit is None or not usable:
            annual_skip[name] += 1
            continue
        if d is not None:
            total = cf.linear_weighted_sum(T, d[0], d[1])
        else:
            total = cf.table_weighted_sum(profile.table, T)
        _add(tables[name], hit[0], total * hit[1])
        annual_parts[name].append((profile, hit))
    b6_table = dict(tables["B6-02"])
    _add(b6_table, GRID, elec_w - b2)
    tables["B6"] = b6_table

    # ---- unit values, read from the tables ----
    val = {name: tot(tables[name], fval) for name in (
        "A13-01", "A13-03", "A13-04", "X-01", "A4-01", "A4-02", "X-12", "A5-01", "A5-02", "A5-03", "C1-01", "C2-01",
        "C3-01", "C4-01", "X-14", "B4-02", "B3-01", "B3-02", "B6-02", "B7-01", "B7-02", "B7-03", "X-16")}
    a5_04 = val["A5-01"] + val["A5-02"] + val["A5-03"]
    b6_03 = elec_w + val["B6-02"]
    b7_04 = val["B7-01"] + val["B7-02"] + val["B7-03"]

    # ---- rebuild: one multiplier on the initial stages ----
    b5_computed = True
    b5_n = 0
    k5 = 0.0
    if bnd.reconstruction_scenario != "NONE":
        if _ratio(bnd.reconstruction_scope_fraction) and cf.valid_period(bnd.replacement_cycle):
            b5_n = cf.renewal_count(T, bnd.replacement_cycle)
            k5 = b5_n * bnd.reconstruction_scope_fraction
        else:
            b5_computed = False
    b5_table = {}
    if k5:
        for s in INITIAL:
            for name in STAGE_TABLES[s]:
                for key, act in tables[name].items():
                    b5_table[key] = b5_table.get(key, 0.0) + act * k5
    tables["B5-01"] = b5_table
    b5_base = (val["A13-01"] + val["A13-03"] + val["A13-04"] + val["X-01"] + val["A4-01"] + val["A4-02"] + a5_04
               + val["C1-01"] + val["C2-01"] + val["C3-01"] + val["C4-01"] + val["X-14"])
    b5 = k5 * b5_base if k5 else 0.0

    # ---- stage vector, gas breakdown, CO2-only: the same tables with other factor columns ----
    gases = list(dict.fromkeys(scn.gases))              # the gas list without repetitions, order kept
    columns = gases if "CO2" in gases else gases + ["CO2"]   # the CO2-only result does not need CO2 to be listed
    gas_cache = {}

    def gas_of(key):
        g = gas_cache.get(key)
        if g is None:
            if type(key) is tuple:                      # recipe: weighted gas amounts of its components
                g = dict.fromkeys(columns, 0.0)
                for fid, fraction, c in A.recipes[key]["parts"]:
                    amounts = factors[fid].gas_amounts
                    for name in columns:
                        g[name] += fraction * c * amounts.get(name, 0.0)
            else:
                g = factors[key].gas_amounts            # a gas the record does not list counts 0
            gas_cache[key] = g
        return g

    by_gas = dict.fromkeys(gases, 0.0)
    grid_total = refrigerant_total = 0.0
    stage_all, stage_co2 = {}, {}
    used = set()
    for s in STAGES:
        merged = {}
        for name in STAGE_TABLES[s]:
            for key, act in tables[name].items():
                merged[key] = merged.get(key, 0.0) + act
        stage_all[s] = tot(merged, fval)                # the value column (the two pseudo keys have the value 1)
        co2 = 0.0
        for key, act in merged.items():                 # the same entries with the gas columns
            if key is GRID:
                grid_total += act
                co2 += act
            elif key is REFRIGERANT:
                refrigerant_total += act
            else:
                amounts = gas_of(key)
                co2 += act * amounts.get("CO2", 0.0)
                for name in gases:
                    by_gas[name] += act * amounts.get(name, 0.0)
                if type(key) is tuple:
                    used.update(fid for fid, _, _ in A.recipes[key]["parts"])
                else:
                    used.add(key)
        stage_co2[s] = co2
    from_gases = 0.0
    gases_skipped = 0
    for name in gases:
        gwp = scn.gwp.get(name)
        if not _nonneg(gwp):                            # a gas without a usable GWP is left out and counted
            gases_skipped += 1
            continue
        from_gases += gwp * by_gas[name]
    gas_value = from_gases + grid_total + refrigerant_total
    stage_sum = 0.0
    for s in STAGES:
        stage_sum += stage_all[s]
    gas_matches = _within(gas_value - stage_sum, 1e-9, max(abs(stage_sum), 1.0))
    by_stage = {s: stage_all[s] for s in STAGES if s in inc}
    co2_total = sum(stage_co2[s] for s in STAGES if s in inc)
    if "B6" in inc and "B2" not in inc:                 # nothing may fall between B2 and B6
        by_stage["B6"] = b6_03
        co2_total += stage_co2["B2"]

    # stage values from the unit values: a second accumulation, compared with the first (QA-01)
    unit_stage = {
        "A1-A3": val["A13-01"] + val["A13-03"] + val["A13-04"] + val["X-01"], "A4": val["A4-01"] + val["A4-02"],
        "A5": a5_04, "B1": b1_02 + b1_03 + b1_04, "B2": b2, "B3": val["B3-01"], "B4": val["B4-02"], "B5": b5,
        "B6": b6_03 - b2, "B7": b7_04, "C1": val["C1-01"], "C2": val["C2-01"], "C3": val["C3-01"] + val["X-14"],
        "C4": val["C4-01"],
    }
    qa01 = [f"stage {s}" for s in STAGES if not _within(unit_stage[s] - stage_all[s], 1e-9, max(abs(unit_stage[s]), 1.0))]
    if not gas_matches:
        qa01.append("gas breakdown total")

    # ---- indicators: one function of the stage vector (a subset sum divided by a scale) ----
    upfront = indicator(by_stage, UPFRONT)
    embodied = indicator(by_stage, EMBODIED)
    wlc = indicator(by_stage, STAGES)                   # the whole-life total; the comparison below builds on it
    area = scn.project.gross_floor_area
    area_ok = M["area_ok"]
    if wlc > 0.0 and all(v >= 0.0 for v in by_stage.values()):
        sum_07 = {"defined": True, "by_stage": {s: indicator(by_stage, (s,), wlc) for s in by_stage}}
    else:
        sum_07 = {"defined": False, "by_stage": {}}

    sum_08 = None
    held = None                                         # the baseline's total and completeness, when comparable
    if _compare:
        base_id = bnd.baseline_scenario
        base_scn = population.BASELINES.get(base_id) if base_id is not None else None
        if base_id is None:
            sum_08 = {"status": "NO_BASELINE", "delta": None, "saving": None}
        elif base_scn is None:
            sum_08 = {"status": "BASELINE_NOT_FOUND", "delta": None, "saving": None}
        else:
            reasons = []
            if base_scn.project.gross_floor_area != area:
                reasons.append("AREA")
            if base_scn.boundary.study_period != T:
                reasons.append("PERIOD")
            if set(base_scn.boundary.included_lifecycle_stages) != inc:
                reasons.append("STAGES")
            if base_scn.boundary.results_gas_scope != bnd.results_gas_scope:
                reasons.append("GAS_SCOPE")
            if {f.release_year for f in base_scn.factors.values()} != {f.release_year for f in factors.values()}:
                reasons.append("FACTOR_VERSION")
            if reasons:
                sum_08 = {"status": "NOT_COMPARABLE", "reasons": reasons, "delta": None, "saving": None}
            else:
                held = baseline_totals.get(base_id) if baseline_totals is not None else None
                if held is None:                        # the caller may keep and reuse it; nothing is kept here
                    b_res = finish(aggregate(base_scn, False), None, False, None, _compare=False)["SUM-03"]
                    held = {"value": b_res["value"], "complete": b_res["complete"]}
                    if baseline_totals is not None:
                        baseline_totals[base_id] = held  # keyed by the input id, with the baseline's completeness

    # ---- remaining checks ----
    # used factors = the factor keys of the stage tables; their licence finding was made once per referenced id
    qa03 = [fid for fid in sorted(used) if fid in A.unlicensed]
    sq = scn.summary_quantities
    if _nonneg(sq.timber_m3) and _nonneg(sq.timber_dry_density_kg_per_m3) and _nonneg(sq.timber_carbon_fraction):
        sto_01 = sq.timber_m3 * sq.timber_dry_density_kg_per_m3 * sq.timber_carbon_fraction * (44.0 / 12.0)
    else:
        sto_01 = None
    x11 = None
    if (area_ok and _nonneg(op.electricity_per_m2_per_year) and M["c_site"] is not None and M["grid_ok"]
            and grid_usable):
        x11 = area * op.electricity_per_m2_per_year * M["c_site"] * G
    x17, x17_total = {}, 0.0
    x17_skipped = 0
    summary_q = {"REBAR": sq.reinforcement_kg, "STRUCTURAL_STEEL": sq.steel_kg, "CONCRETE": sq.concrete_m3,
                 "TIMBER": sq.timber_m3, "ENVELOPE": sq.envelope_m2, "INTERIOR": sq.interior_m2}
    for k in SIMPLE_CLASSES:
        qk = summary_q[k]
        if not _positive(qk):                           # no representative factor without a positive quantity
            x17_skipped += 1
            x17[k] = {"quantity": qk, "fbar": None, "emission": 0.0}
            continue
        fbar = tot(tables["CLASS:" + k], fval) / qk
        x17[k] = {"quantity": qk, "fbar": fbar, "emission": qk * fbar}
        x17_total += qk * fbar
    x09_emis, x09_total = {}, 0.0
    for cls, routes in A.route_tables.items():
        x09_emis[cls] = {r: tot(t, fval) for r, t in routes.items()}
        x09_total += sum(x09_emis[cls].values())
    x03_mass, x03_emis, x03_total = {}, {}, 0.0
    for key, rec in A.recipes.items():
        if not rec["used"]:
            continue
        kg = rec["kg"]                                  # the rows of one composition are expanded once
        for fid, fraction, c in rec["parts"]:
            m = kg * fraction
            e = m * c * factors[fid].value
            x03_mass[fid] = x03_mass.get(fid, 0.0) + m
            x03_emis[fid] = x03_emis.get(fid, 0.0) + e
            x03_total += e
    by_cycle = {}
    x08_total = tot(explicit_b4, fval)
    explicit_total = x08_total
    group_u = {}
    for cycle in sorted((c for c in A.groups if c is not None and counts[c]), key=float):
        u = group_u[cycle] = tot(A.groups[cycle].u, fval)
        e = counts[cycle] * u
        by_cycle[repr(float(cycle))] = {"count": counts[cycle], "unit_emission": u, "emission": e}
        x08_total += e
    skip = M["skip"]

    R = dict(A.out)
    R.update({
        "X-13": {"n_skipped": M["x13_skip"]},
        "A13-01": {"value": val["A13-01"], "n_skipped": skip["A13-01"]},
        "A13-03": {"value": val["A13-03"], "n_skipped": skip["A13-03"]},
        "A13-04": {"value": val["A13-04"], "n_skipped": skip["A13-04"]},
        "X-01": {"value": val["X-01"], "n_skipped": skip["X-01"]},
        "X-03": {"value": x03_total, "mass_by_component": x03_mass, "emission_by_component": x03_emis},
        "A4-01": {"value": val["A4-01"], "n_skipped": skip["A4-01"]},
        "X-12": {"value": val["X-12"], "n_skipped": skip["X-12"]},
        "A4-02": {"value": val["A4-02"], "n_skipped": skip["A4-02"]},
        "A5-01": {"value": val["A5-01"], "computed": M["a5_01_ok"]},
        "A5-02": {"value": val["A5-02"], "n_skipped": M["a5_02_skip"]},
        "A5-03": {"value": val["A5-03"], "n_skipped": M["a5_03_skip"]},
        "A5-04": {"value": a5_04, "parts": {"power": val["A5-01"], "fuels": val["A5-02"], "waste": val["A5-03"]},
                  "other_assessed": False},
        "X-17": {"value": x17_total, "by_class": x17, "n_classes_skipped": x17_skipped},
        "X-16": {"value": val["X-16"], "n_skipped": M["x16_skip"]},
        "B4-01": {"n_events": n_events, "n_invalid": M["n_bad_life"]},
        "B4-03": {"n_invalid": M["n_bad_cycle"]},
        "B4-02": {"value": val["B4-02"], "n_partial": n_partial},
        "X-08": {"value": x08_total, "by_cycle": by_cycle, "explicit": explicit_total},
        "B3-01": {"value": val["B3-01"], "n_skipped": skip["B3"]},
        "B3-02": {"value": val["B3-02"], "n_skipped": skip["B3"]},
        "B1-01": {"value": b1_01, "n_skipped": b1_01_skip},
        "B1-02": {"value": b1_02, "n_skipped": b1_skip[0]},
        "B1-03": {"value": b1_03, "n_skipped": b1_skip[1]},
        "B1-04": {"value": b1_04, "n_skipped": b1_skip[2]},
        "B5-01": {"value": b5, "n_events": b5_n, "computed": b5_computed},
        "X-06": {"matches_table": grid_matches, "source": grid_source, "computed": grid_usable},
        "B6-04": {"computed": net_ok, "descriptors_match_tables": net_match},
        "B6-01": {"computed": elec_ok},
        "B6-02": {"n_skipped": annual_skip["B6-02"], "descriptors_match_tables": annual_match["B6-02"]},
        "B6-03": {"value": b6_03},
        "B2-01": {"value": b2, "computed": b2_ok},
        "X-11": {"value": x11},
        "B7-01": {"n_skipped": annual_skip["B7-01"], "descriptors_match_tables": annual_match["B7-01"]},
        "B7-02": {"n_skipped": annual_skip["B7-02"], "descriptors_match_tables": annual_match["B7-02"]},
        "B7-03": {"n_skipped": annual_skip["B7-03"], "descriptors_match_tables": annual_match["B7-03"]},
        "B7-04": {"value": b7_04},
        "C1-01": {"value": val["C1-01"], "n_skipped": M["c1_skip"]},
        "C2-01": {"value": val["C2-01"], "n_skipped": skip["C2-01"]},
        "C3-01": {"value": val["C3-01"], "n_skipped": skip["C3-01"], "n_routes_skipped": M["routes_skipped"]["C3"]},
        "C4-01": {"value": val["C4-01"], "n_skipped": skip["C4-01"], "n_routes_skipped": M["routes_skipped"]["C4"]},
        "X-14": {"value": val["X-14"], "n_skipped": skip["X-14"]},
        "X-09": {"value": x09_total, "mass": M["x09_mass"], "emission": x09_emis},
        "X-10": {"resource_kg": resource, "waste_kg": waste, "n_excluded": skip["X-10"]},
        "STO-01": {"value": sto_01},
        "STO-02": {"value": tot(tables["STO-02"], fval) if M["sto_02_ok"] else None},
        "X-04": {"value": gas_value, "by_gas": by_gas, "co2e_from_gases": from_gases,
                 "grid_co2e": grid_total, "refrigerant_co2e": refrigerant_total, "by_stage_recomputed": unit_stage,
                 "n_gases_skipped": gases_skipped, "matches_stage_total": gas_matches},
        "X-05": {"value": co2_total, "by_stage_co2": stage_co2},
        "X-07": {"value": wlc},
        "SUM-04": {"value": indicator(by_stage, STAGES, area) if area_ok else None},
        "SUM-05": {"value": indicator(by_stage, STAGES, area * T) if area_ok else None},
        "SUM-06": {"value": indicator(by_stage, STAGES, 1000.0)},
        "SUM-07": sum_07,
        "QA-01": {"ok": not qa01, "violations": qa01},
        "QA-02": {"ok": not qa02, "violations": qa02, "warnings": qa02_warn},
        "QA-03": {"ok": not qa03, "violations": qa03, "n_used": len(used)},
    })
    # completeness: a stage value is incomplete when any unit whose result flows into it left something out
    incomplete = set()
    for s in STAGES:
        if s in inc:
            for uid in (B6_UPSTREAM_WITHOUT_B2 if s == "B6" and "B2" not in inc else STAGE_UPSTREAM[s]):
                if _left_out(R[uid]):
                    incomplete.add(uid)
    complete = not incomplete
    R["X-02"] = {"by_stage": by_stage, "by_stage_all": stage_all, "complete": complete, "incomplete_units": sorted(incomplete)}
    if held is not None:                                # comparable: both totals must be complete to be compared
        b_total, b_complete = held["value"], held["complete"]
        flags = {"proposal_complete": complete, "baseline_complete": b_complete}
        if not (complete and b_complete):
            sum_08 = {"status": "INCOMPLETE", "delta": None, "saving": None, **flags}
        else:
            sum_08 = {"status": "COMPARED", "baseline": b_total, "delta": wlc - b_total,
                      "saving": (b_total - wlc) / b_total if b_total > 0.0 else None, **flags}
    if sum_08 is not None:
        R["SUM-08"] = sum_08
    R["SUM-01"] = {"value": upfront, "complete": complete}
    R["SUM-02"] = {"value": embodied, "complete": complete}
    R["SUM-03"] = {"value": wlc, "complete": complete}
    R["_stats"] = dict(A.stats)
    R["_tables"] = tables
    R["_n_events_check"] = n_events
    if not detail:
        del R["_n_events_check"]
    if detail:
        _detail(A, R, T, Y, wl, counts, group_u, explicit_events, b1_items, b1_year, b1_event_year, g_values,
                net_series, elec_series, annual_parts, b5_n, b5_base, b2_ok, stage_all, b1_04)
    return R


def _detail(A, R, T, Y, wl, counts, group_u, explicit_events, b1_items, b1_year, b1_event_year, g_values,
            net_series, elec_series, annual_parts, b5_n, b5_base, b2_ok, stage_all, b1_04):
    """Per-row lists and yearly series (the same outputs as the reference; not needed for the totals)."""
    scn = A.scn
    L = A.rows
    fval = A.fval
    inc = set(scn.boundary.included_lifecycle_stages)
    bnd = scn.boundary
    R["A13-05"] = dict(R["A13-05"], q_ord=L["q_ord"], q_inst=L["q_inst"])
    R["X-13"] = {"by_item": L["net"], "waste_by_item": L["disp"], "n_skipped": R["X-13"]["n_skipped"]}
    R["A13-02"] = dict(R["A13-02"], by_item=L["a1302"])
    R["X-15"] = dict(R["X-15"], kind=L["kind"], factor=L["factor"], conv=L["conv"])
    for uid, key in (("A13-01", "a1301"), ("A13-03", "a1303"), ("A13-04", "a1304"), ("X-01", "x01"), ("A4-01", "a401"),
                     ("A4-02", "a402"), ("X-12", "x12"), ("C2-01", "c2"), ("C3-01", "c3"), ("C4-01", "c4"), ("X-14", "x14")):
        R[uid]["by_item"] = L[key]
    R["X-16"]["by_item"] = [it[1] * fval[it[0]] if it is not None else 0.0 for it in A.misc["x16_items"]]
    n_mat = [counts[c] for c in L["mcycle"]]
    R["B4-03"] = {"by_item": n_mat, "n_invalid": R["B4-03"]["n_invalid"]}
    events_all = []
    n_events = 0
    period_years = {}                                   # event years of one period, built once per distinct period

    def years_of(cycle):
        ev = period_years.get(cycle)
        if ev is None:
            ev = period_years[cycle] = _renewal_years(cycle, counts[cycle]) if counts[cycle] else []
        return ev

    for j, explicit in enumerate(L["eexp"]):            # the per-row lists of the aggregation; the rows are not read again
        ev = explicit_events[j] if explicit else list(years_of(L["ecycle"][j]))    # a copy per row for the output
        events_all.append(ev)
        n_events += len(ev)
    R["B4-01"] = {"events": events_all, "n_events": n_events, "n_invalid": R["B4-01"]["n_invalid"]}
    assert n_events == R["_n_events_check"]
    del R["_n_events_check"]
    R["B1-02"]["by_item"] = b1_items

    w = [0.0] + [1.0] * (Y - 1) + ([wl] if Y else [])
    b4_year = [0.0] * (Y + 1)
    b3_year = [0.0] * (Y + 1)
    for cycle, grp in A.groups.items():
        n = counts[cycle]
        skip_years = set()
        if n:
            u = group_u[cycle] if cycle in group_u else sum(act * fval[key] for key, act in grp.u.items())
            for y in years_of(cycle):
                b4_year[y] += u
                skip_years.add(y)
        if grp.r:
            rate = sum(act * fval[key] for key, act in grp.r.items())      # the builtin sum (compensated), as before
            _add_repair_series(b3_year, rate, w, skip_years, Y)
    for j, years, lines, rline, emass, incomplete in A.explicit:
        events = explicit_events[j]
        u = sum(act * fval[key] for key, act in lines)
        skip_years = set()
        for y in events:
            b4_year[y] += u
            skip_years.add(y)
        if rline is not None:
            _add_repair_series(b3_year, rline[1] * fval[rline[0]], w, skip_years, Y)
    b5_year = [0.0] * (Y + 1)
    if b5_n:
        for y in _rebuild_years(bnd.replacement_cycle, b5_n):
            b5_year[y] += bnd.reconstruction_scope_fraction * b5_base
    R["X-06"]["by_year"] = [0.0] + list(g_values)
    R["B6-04"]["by_year"] = net_series
    R["B6-01"]["by_year"] = elec_series
    series = {}
    for name, parts in annual_parts.items():
        series[name] = R[name]["by_year"] = _annual_series(parts, fval, Y)
    R["B4-02"].update(by_item_material=[n * u if n else 0.0 for n, u in zip(n_mat, L["mu"])],     # no renewal: exactly 0
                      by_item_equipment=[len(ev) * u if ev else 0.0 for ev, u in zip(events_all, L["eu"])], by_year=b4_year)
    R["B3-01"]["by_year"] = b3_year
    R["B1-02"]["by_year"] = b1_year
    R["B1-03"]["by_year"] = b1_event_year
    R["B5-01"]["by_year"] = b5_year

    share = scn.operation.facility_management_ratio if b2_ok else 0.0
    R["X-07"] = _whole_life_series(inc, stage_all, share, w, elec_series, series, b1_year, b1_event_year, b3_year, b4_year,
                                   b5_year, b1_04, Y)


def evaluate(scn, detail: bool = True, baseline_totals: dict | None = None) -> dict:
    """All results of one scenario.

    ``baseline_totals`` is an optional dict the caller keeps to reuse the whole-life total of the
    baseline (see ``finish``): entries are keyed by ``boundary.baseline_scenario``, which identifies
    the baseline by name only, and carry the baseline's completeness. Any change of the baseline, of
    the study period or of the boundary invalidates an entry; the caller must drop it then.
    """
    T = check_period(scn)
    return finish(aggregate(scn, detail), T, detail, baseline_totals)


def sweep(scn, periods, compare: bool = False) -> dict:
    """Totals for several study periods from ONE pass over the rows.

    With ``compare`` the comparison with the baseline (SUM-08) is evaluated for every period; the
    baseline is computed afresh each time (a total held for one period is not valid for another).
    """
    check_period(scn)
    A = aggregate(scn, False)
    out = {}
    for T in periods:
        if not _valid_period(T):
            raise ValueError("invalid study period")
        out[T] = finish(A, T, False, None, _compare=compare)
    return out
