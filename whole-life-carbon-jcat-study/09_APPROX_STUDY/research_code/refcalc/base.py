"""Conventions and small helpers shared by all reference units.

CONVENTIONS OF THIS STUDY (design choices of the independent model, not statements
about any other tool). Version 3: exact time rules and validity rules after the second
independent re-check.

General principle
  A numeric input that is missing (``None``), not finite (NaN, +-inf) or outside its range
  is never used in arithmetic. The smallest thing that needs it (a row, a route, a yearly
  series, a class, a unit) is left out and counted in the public result of the unit that
  needs it, and every total that depends on it is marked incomplete. The only input that
  makes the calculation refuse to run is an invalid study period.
  Inputs of a wrong TYPE (text where a number is expected, decimal or array scalar types,
  nested containers) are outside the scope of these rules; numbers are Python ``int`` or
  ``float``.

Time
  * tau = 0 is completion (start of the study period); T = boundary.study_period must be
    a finite positive number of years (otherwise ``ValueError``; nothing else raises).
  * Study years are y = 1..Y with Y = ceil(T). Year y covers (y-1, y]; its year-table
    index is k = y-1. Year weight w_y = min(1, T-(y-1)), so a non-integer T prorates the
    last year and sum_y w_y = T.
  * All time tests are evaluated in exact rational arithmetic on the given binary
    floating-point values, so that no result depends on rounding or on the order of
    operations. c is the double nearest to 1 - 1e-9, taken as an exact ratio.
      - "inside": tau lies inside the study period when tau < T*c (exactly). An event at
        T, or within a relative 1e-9 below T, is NOT counted (3 * 33.3 is treated as
        equal to 99.9).
      - year(tau) = max(1, ceil(tau*c)) (exactly): an event within a relative 1e-9 above
        a whole year still belongs to that year.
      - the n-th periodic event of a period L is at tau = n*L exactly (the product of
        the integer n and the binary value of L, not its rounded product).
  * Periodic events are counted up one by one: n = 1, 2, ... while n*L is inside.
  * Explicit event lists hold offsets t. An entry is used when it is a finite number,
    t > 0 and inside the period. Entries that are missing or not finite are ignored by
    the calculation and reported by QA-02 like entries outside the period. Entries that
    are listed twice are each counted.
  * A cycle or service life that is ``None`` means "not renewed": no events, nothing is
    counted (SYS-01 lists the missing value). A cycle or service life that is present
    but not a finite positive number gives no events AND is counted by the unit that
    needs it (``n_invalid``; a refrigerant device is skipped), so the stages that depend
    on it are incomplete. A rebuild scenario other than NONE needs a finite positive
    cycle, otherwise B5-01 is not computed.
  * ``by_year`` results have Y+1 entries: index 0 is tau = 0, index y is study year y.
    Event lists handed between units hold the YEARS of the events (ints).

Annual series (which input counts)
  * Annual profile: CONSTANT with a base -> base; LINEAR_TREND with a base and a slope ->
    base + slope*k; otherwise (kind TABLE, or the descriptor is not given) the year
    table. The Y yearly values that count must all be finite and >= 0, and a table that
    counts needs at least Y entries; otherwise the series is unusable: the unit that
    needs it skips it and counts it. For the two parametric kinds the table is a
    redundant copy; a copy that is shorter than Y entries or differs (relative 1e-12)
    is reported (``descriptors_match_tables``), the descriptor is used.
  * Grid factor: the descriptor of a well-formed scenario: CONSTANT with a finite
    start >= 0; LINEAR_DECLINE_TO_FLOOR with finite start, floor and decline,
    decline >= 0 and start >= floor >= 0; STEPWISE with at least one step, step indices
    of type int strictly increasing from 0 and finite step values >= 0. Otherwise the
    year table, which then needs at least Y entries, all finite and >= 0. When neither
    is usable the grid factor is unusable: X-06 reports it and the units that need the
    series are not computed. The same copy check applies (``matches_table``).
  * An annual quantity has the unit "<unit>/year"; any other time base is not converted.

Using a factor
  A factor is used for an activity only if ALL of these hold; otherwise the row (or
  the route) is skipped and counted, never computed with a wrong factor:
  * the record exists and its licence status is PERMITTED_PUBLIC;
  * its covered stages are exactly the stage it is used for;
  * its value and every one of its gas amounts are finite numbers >= 0;
  * the activity unit equals the factor unit or a direct conversion is registered
    (row-specific conversions first; no chaining). A conversion whose multiplier is not
    a finite number > 0 counts as "no conversion".

Missing and invalid data
  * ``None`` means MISSING and is never treated as zero. Quantities, masses, distances
    and rates must be finite and >= 0; ratios must lie in [0, 1]; areas, load factors
    and price indices must be finite and > 0. A row with a missing or out-of-range
    input is skipped and counted in ``n_skipped`` (routes in ``n_routes_skipped``).
    ``by_item`` holds the amount that was added, so it is 0.0 for a skipped row; the
    count tells skipped rows from computed zeros.
  * A stage value is incomplete when ANY unit whose results flow into it left something
    out (one of its counts ``n_skipped``, ``n_routes_skipped``, ``n_partial``,
    ``n_invalid``, ``n_unresolved`` is above zero, or ``computed`` is false), whether or
    not that unit's own stage is in the boundary. "Flow into" is the data flow of the
    registry: the units X-02 composes the stage value from and everything they depend
    on, directly or indirectly (with B2 outside the boundary, B6 is composed from B6-03
    alone). The rule is deliberately conservative: a unit upstream of a stage marks it
    even when the rows it left out happen not to be used by that stage. X-02 lists those
    units in ``incomplete_units`` and the totals carry ``complete``. The comparison with
    a baseline (SUM-08) is made only when both totals are complete.
  * Counts that do NOT mark a total incomplete, because they report a defined fallback or
    a check rather than something left out of a stage value: ``n_epd_declined`` (X-15:
    the generic factor is used instead), ``n_mass_unchecked`` (C-05), ``n_excluded``
    (X-10), ``n_classes_skipped`` (X-17), ``n_gases_skipped`` (X-04; when that gas has
    a non-zero amount the gas total fails its check against the stage total, which
    QA-01 reports).

Results
  * Keys starting with "_" carry working data for downstream units and are ignored by
    result comparison.
  * ``_lines`` is a flat list of (factor_id, activity) with emission = activity * factor
    value; ``_row_lines`` is the same per input row. Purchased electricity and
    refrigerant releases have no factor record: their lines carry the markers ``GRID``
    and ``REFRIGERANT`` (objects that cannot be equal to any factor id) and the
    activity is already an emission.
"""
from __future__ import annotations

import math
from typing import Any, Optional, Sequence

from synth import model

ALLOWED = model.ALLOWED_LICENCE_STATES
STAGES = model.LIFECYCLE_STAGES
EPS = 1e-9                                       # relative tolerance of the time boundary rules
C_NUM, C_DEN = (1.0 - EPS).as_integer_ratio()    # c = the double nearest to 1 - 1e-9, as an exact ratio
# counts in a unit's public result that say "something was left out"
EXCLUSION_COUNTS = ("n_skipped", "n_routes_skipped", "n_partial", "n_invalid", "n_unresolved")


class PseudoLine:
    """Marker of emission lines that have no factor record (the activity is already an emission).

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
        return self.name                         # pickled by the name of the module-level object


GRID = PseudoLine("GRID")                        # purchased electricity (no gas breakdown)
REFRIGERANT = PseudoLine("REFRIGERANT")          # refrigerant releases


def check_period(scn) -> float:
    """The study period, or ValueError when it is not a finite positive number."""
    T = scn.boundary.study_period
    if T is None or isinstance(T, bool) or not (T > 0.0) or math.isinf(T):
        raise ValueError("study_period must be a finite positive number of years")
    return T


def n_years(T: float) -> int:
    return math.ceil(T)


def year_weights(T: float) -> list[float]:
    """w[0] = 0 (tau = 0), w[y] = min(1, T-(y-1)) for y = 1..ceil(T)."""
    out = [0.0]
    for y in range(1, n_years(T) + 1):
        out.append(min(1.0, T - (y - 1)))
    return out


def finite(x) -> bool:
    """A finite number (False for None, NaN and the infinities)."""
    return x is not None and -math.inf < x < math.inf


def positive(x) -> bool:
    """Finite and > 0."""
    return x is not None and 0.0 < x < math.inf


def nonneg(x) -> bool:
    """Finite and >= 0 (False for None, NaN, infinities and negatives)."""
    return x is not None and 0.0 <= x < math.inf


def ratio(x) -> bool:
    return x is not None and 0.0 <= x <= 1.0


def invalid_period(x) -> bool:
    """A cycle or service life that is given but is not a finite positive number."""
    return x is not None and not positive(x)


def inside(tau, T) -> bool:
    """True when an event at tau lies before the end of the study period: tau < T*c, exactly.

    Both arguments must be finite numbers; the test uses their exact binary values.
    """
    a, b = tau.as_integer_ratio()
    p, q = T.as_integer_ratio()
    return a * q * C_DEN < p * C_NUM * b


def event_year(tau) -> int:
    """The study year an event at tau belongs to: max(1, ceil(tau*c)), exactly."""
    a, b = tau.as_integer_ratio()
    return max(1, -((-a * C_NUM) // (b * C_DEN)))


def periodic_events(T, period) -> list[int]:
    """Years of the events n*period (n = 1, 2, ...) inside the study period, by counting up.

    The n-th event is at n*period exactly. The integers of the exact test are prepared
    once: n*period is inside  <=>  n*step < limit, and its year is ceil(n*num/den).
    A period that is missing or not a finite positive number gives no events.
    """
    years: list[int] = []
    if not positive(period):
        return years
    a, b = period.as_integer_ratio()
    p, q = T.as_integer_ratio()
    step, limit = a * q * C_DEN, p * C_NUM * b
    num, den = a * C_NUM, b * C_DEN
    n = 1
    while n * step < limit:
        years.append(max(1, -((-n * num) // den)))
        n += 1
    return years


def explicit_events(T, entries: Sequence[Any]) -> list[int]:
    """Years of the listed offsets that are used (finite, t > 0, inside the period), in list order."""
    return [event_year(t) for t in entries if finite(t) and t > 0 and inside(t, T)]


def convert(scn, from_unit: str, to_unit: str, extra: Sequence[Any] = ()) -> Optional[float]:
    return model.conversion_factor(scn.unit_conversions, from_unit, to_unit, extra)


def factor_values_ok(rec) -> bool:
    """The record's value and every one of its gas amounts are finite numbers >= 0."""
    if not nonneg(rec.value):
        return False
    for amount in rec.gas_amounts.values():
        if amount is None or not 0.0 <= amount < math.inf:      # the test of ``nonneg``, written out
            return False
    return True


def lookup(scn, factor_id: Optional[str], stage: str, activity_unit: Optional[str], extra: Sequence[Any] = ()):
    """(factor record, conversion multiplier) when the factor may be used, else None.

    This is the one place where the reference calculation decides whether a factor record
    may be used (see "Using a factor" in the module docstring).
    """
    if factor_id is None or activity_unit is None:
        return None
    rec = scn.factors.get(factor_id)
    if rec is None or rec.licence_status not in ALLOWED or rec.stages != [stage] or not factor_values_ok(rec):
        return None
    conv = convert(scn, activity_unit, rec.unit, extra)
    if conv is None:
        return None
    return rec, conv


def annual_unit(unit: str) -> Optional[str]:
    """The unit of an annual quantity "<unit>/year"; None for any other time base."""
    head, sep, tail = unit.partition("/")
    return head if sep and tail == "year" else None


def profile_uses_descriptor(profile) -> bool:
    """True when the descriptor of a parametric profile is given (then the year table is only a copy)."""
    if profile.kind == "CONSTANT":
        return profile.base is not None
    if profile.kind == "LINEAR_TREND":
        return profile.base is not None and profile.slope is not None
    return False


def descriptor_values(profile, Y: int) -> Optional[list[float]]:
    """Yearly values of a given descriptor; None when base (or slope) is not a finite number."""
    out = []
    if profile.kind == "CONSTANT":
        if not finite(profile.base):
            return None
        for _ in range(Y):
            out.append(profile.base)
    else:
        if not finite(profile.base) or not finite(profile.slope):
            return None
        for k in range(Y):
            out.append(profile.base + profile.slope * k)
    return out


def profile_values(profile, Y: int) -> Optional[list[float]]:
    """The Y yearly values that count for an annual profile, or None when the series is unusable.

    Unusable: a value that counts is missing, not finite or negative, or the year table
    counts and has fewer than Y entries (see module docstring).
    """
    if profile_uses_descriptor(profile):
        out = descriptor_values(profile, Y)
        if out is None:
            return None
    else:
        if len(profile.table) < Y:
            return None
        out = []
        for k in range(Y):
            out.append(profile.table[k])
    for value in out:
        if not nonneg(value):
            return None
    return out


def same_series(values: Sequence[float], table: Sequence[Any]) -> bool:
    """The table has an entry for every value, each a finite number equal to it within a relative 1e-12."""
    if len(table) < len(values):
        return False
    for v, t in zip(values, table):
        if not finite(v) or not finite(t):
            return False
        if not (v == t or abs(v - t) <= 1e-12 * max(abs(v), abs(t))):
            return False
    return True


def profile_matches_table(profile, Y: int) -> bool:
    """For a given descriptor: its Y values equal the table copy. True when the table itself is the input."""
    if not profile_uses_descriptor(profile):
        return True
    values = descriptor_values(profile, Y)
    return values is not None and same_series(values, profile.table)


def grid_well_formed(grid) -> bool:
    if grid.kind == "CONSTANT":
        return nonneg(grid.start)
    if grid.kind == "LINEAR_DECLINE_TO_FLOOR":
        return (nonneg(grid.start) and nonneg(grid.floor) and nonneg(grid.annual_decline)
                and grid.start >= grid.floor)
    if grid.kind == "STEPWISE":
        steps = grid.steps or []
        if not steps:
            return False
        for step in steps:
            if type(step.from_index) is not int or not nonneg(step.value):
                return False
        if steps[0].from_index != 0:
            return False
        for i in range(len(steps) - 1):
            if not steps[i].from_index < steps[i + 1].from_index:
                return False
        return True
    return False


def grid_table_usable(grid, Y: int) -> bool:
    """The year table can stand in for the descriptor: at least Y entries, the first Y finite and >= 0."""
    if len(grid.table) < Y:
        return False
    for k in range(Y):
        if not nonneg(grid.table[k]):
            return False
    return True


def grid_source(grid, Y: int) -> str:
    """Which input counts for the grid factor: "DESCRIPTOR", "TABLE", or "NONE" when neither is usable."""
    if grid_well_formed(grid):
        return "DESCRIPTOR"
    return "TABLE" if grid_table_usable(grid, Y) else "NONE"


def grid_values(grid, Y: int) -> Optional[list[float]]:
    """The yearly grid factors that count (descriptor when well formed, else the table); None when unusable."""
    source = grid_source(grid, Y)
    if source == "NONE":
        return None
    out = []
    if source == "TABLE":
        for k in range(Y):
            out.append(grid.table[k])
    elif grid.kind == "CONSTANT":
        for _ in range(Y):
            out.append(grid.start)
    elif grid.kind == "LINEAR_DECLINE_TO_FLOOR":
        for k in range(Y):
            out.append(max(grid.floor, grid.start - grid.annual_decline * k))
    else:
        for k in range(Y):
            value = None
            for step in grid.steps:
                if step.from_index <= k:
                    value = step.value
            out.append(value)
    return out


def grid_unit(grid) -> Optional[str]:
    """The electricity unit of the grid factor "kgCO2e/<unit>"."""
    head, sep, tail = grid.unit.partition("/")
    return tail if sep and head == "kgCO2e" and tail else None


def included(scn) -> set[str]:
    return set(scn.boundary.included_lifecycle_stages)


def zeros(n: int) -> list[float]:
    return [0.0] * n


def left_out(result: dict) -> bool:
    """True when a unit's public result says that something was left out or not computed."""
    for key in EXCLUSION_COUNTS:
        if result.get(key):
            return True
    return result.get("computed") is False
