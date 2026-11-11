"""Conventions and small helpers shared by all reference units.

CONVENTIONS OF THIS STUDY (design choices of the independent model, not statements
about any other tool). Version 2: hardened after the independent review.

Time
  * tau = 0 is completion (start of the study period); T = boundary.study_period must be
    a finite positive number of years (otherwise the calculation refuses to run).
  * Study years are y = 1..Y with Y = ceil(T). Year y covers (y-1, y]; its year-table
    index is k = y-1. Year weight w_y = min(1, T-(y-1)), so a non-integer T prorates the
    last year and sum_y w_y = T.
  * A periodic event with period L happens at tau = n*L for n = 1, 2, ... while tau lies
    inside the period. "Inside" means tau < T*(1 - 1e-9): an event at T, or within a
    relative 1e-9 of T, is NOT counted. The tolerance makes the rule independent of
    binary rounding (3 * 33.3 is treated as equal to 99.9).
  * An event at tau belongs to year ceil(tau*(1 - 1e-9)) (at least 1): an event within a
    relative 1e-9 above a whole year belongs to that year.
  * Explicit event lists hold offsets t; only 0 < t that lie inside the period are used.
  * A period, cycle or service life that is missing, not finite or not positive gives
    no events.
  * ``by_year`` results have Y+1 entries: index 0 is tau = 0, index y is study year y.

Annual series (which input counts)
  * Annual profile: CONSTANT -> base; LINEAR_TREND -> base + slope*k; TABLE -> the table.
    For the two parametric kinds the table is a redundant copy; a disagreement is
    reported (``descriptors_match_tables``), the descriptor is used.
  * Grid factor: the descriptor of a well-formed CONSTANT, LINEAR_DECLINE_TO_FLOOR
    (decline >= 0, start >= floor) or STEPWISE (steps strictly increasing from index 0)
    scenario; otherwise the table. The same disagreement check applies.
  * An annual quantity has the unit "<unit>/year"; any other time base is not converted.

Using a factor
  A factor is used for an activity only if ALL of these hold; otherwise the row (or
  the route) is skipped and counted, never computed with a wrong factor:
  * the record exists and its licence status is PERMITTED_PUBLIC;
  * its covered stages are exactly the stage it is used for;
  * the activity unit equals the factor unit or a direct conversion is registered
    (row-specific conversions first; no chaining).

Missing and invalid data
  * ``None`` means MISSING and is never treated as zero. Quantities, masses, distances
    and rates must be finite and >= 0; ratios must lie in [0, 1]. A row with a missing
    or out-of-range input is skipped and counted in ``n_skipped`` (routes in
    ``n_routes_skipped``). ``by_item`` holds the amount that was added, so it is 0.0 for
    a skipped row; the count tells skipped rows from computed zeros.
  * A result that could not be computed completely is flagged: X-02 lists the units
    with skipped rows in ``incomplete_units`` and the totals carry ``complete``.

Results
  * Keys starting with "_" carry working data for downstream units and are ignored by
    result comparison.
  * ``_lines`` is a flat list of (factor_id, activity) with emission = activity * factor
    value; ``_row_lines`` is the same per input row.
"""
from __future__ import annotations

import math
from typing import Any, Optional, Sequence

from synth import model

ALLOWED = model.ALLOWED_LICENCE_STATES
STAGES = model.LIFECYCLE_STAGES
GRID = "GRID"                # pseudo factor id of purchased electricity (no gas breakdown)
REFRIGERANT = "REFRIGERANT"  # pseudo factor id of refrigerant releases
EPS = 1e-9                   # relative tolerance of the time boundary rules


def check_period(scn) -> float:
    """The study period, or ValueError when it is not a finite positive number."""
    T = scn.boundary.study_period
    if T is None or isinstance(T, bool) or not (T > 0.0) or math.isinf(T):
        raise ValueError("study_period must be a finite positive number of years")
    if len(scn.operation.grid.table) < math.ceil(T):
        raise ValueError("year tables are shorter than the study period")
    return T


def n_years(T: float) -> int:
    return math.ceil(T)


def year_weights(T: float) -> list[float]:
    """w[0] = 0 (tau = 0), w[y] = min(1, T-(y-1)) for y = 1..ceil(T)."""
    out = [0.0]
    for y in range(1, n_years(T) + 1):
        out.append(min(1.0, T - (y - 1)))
    return out


def inside(tau: float, T: float) -> bool:
    """True when an event at tau counts as lying before the end of the study period."""
    return tau < T * (1.0 - EPS)


def positive(x) -> bool:
    return x is not None and x > 0.0 and not math.isinf(x)


def nonneg(x) -> bool:
    """Finite and >= 0 (False for None, NaN, infinities and negatives)."""
    return x is not None and x >= 0.0 and not math.isinf(x)


def ratio(x) -> bool:
    return x is not None and 0.0 <= x <= 1.0


def periodic_events(T: float, period: Optional[float]) -> list[float]:
    """Times n*period (n >= 1) inside the study period, by counting up."""
    events: list[float] = []
    if not positive(period):
        return events
    n = 1
    while inside(n * period, T):
        events.append(n * period)
        n += 1
    return events


def explicit_events(T: float, years: Sequence[float]) -> list[float]:
    return [float(t) for t in years if t > 0 and inside(t, T)]


def event_year(tau: float) -> int:
    return max(1, math.ceil(tau * (1.0 - EPS)))


def convert(scn, from_unit: str, to_unit: str, extra: Sequence[Any] = ()) -> Optional[float]:
    return model.conversion_factor(scn.unit_conversions, from_unit, to_unit, extra)


def lookup(scn, factor_id: Optional[str], stage: str, activity_unit: Optional[str], extra: Sequence[Any] = ()):
    """(factor record, conversion multiplier) when the factor may be used, else None."""
    if factor_id is None or activity_unit is None:
        return None
    rec = scn.factors.get(factor_id)
    if rec is None or rec.licence_status not in ALLOWED or rec.stages != [stage]:
        return None
    conv = convert(scn, activity_unit, rec.unit, extra)
    if conv is None:
        return None
    return rec, conv


def annual_unit(unit: str) -> Optional[str]:
    """The unit of an annual quantity "<unit>/year"; None for any other time base."""
    head, sep, tail = unit.partition("/")
    return head if sep and tail == "year" else None


def profile_values(profile, Y: int) -> list[float]:
    """The yearly values that count for an annual profile (see module docstring)."""
    out = []
    if profile.kind == "CONSTANT" and profile.base is not None:
        for _ in range(Y):
            out.append(profile.base)
    elif profile.kind == "LINEAR_TREND" and profile.base is not None and profile.slope is not None:
        for k in range(Y):
            out.append(profile.base + profile.slope * k)
    else:
        for k in range(Y):
            out.append(profile.table[k])
    return out


def same_series(values: Sequence[float], table: Sequence[float]) -> bool:
    return all(v == t or abs(v - t) <= 1e-12 * max(abs(v), abs(t)) for v, t in zip(values, table))


def grid_well_formed(grid) -> bool:
    if grid.kind == "CONSTANT":
        return grid.start is not None
    if grid.kind == "LINEAR_DECLINE_TO_FLOOR":
        return (None not in (grid.start, grid.floor, grid.annual_decline) and grid.annual_decline >= 0.0
                and grid.start >= grid.floor)
    if grid.kind == "STEPWISE":
        steps = grid.steps or []
        return bool(steps) and steps[0].from_index == 0 and all(
            steps[i].from_index < steps[i + 1].from_index for i in range(len(steps) - 1))
    return False


def grid_values(grid, Y: int) -> list[float]:
    """The yearly grid factors that count (descriptor when well formed, else the table)."""
    out = []
    if not grid_well_formed(grid):
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
