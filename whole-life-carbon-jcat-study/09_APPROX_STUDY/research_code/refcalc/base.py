"""Conventions and small helpers shared by all reference units.

CONVENTIONS OF THIS STUDY (design choices of the independent model, not statements
about any other tool)

Time
  * tau = 0 is completion (start of the study period); T = boundary.study_period > 0
    is a real number of years.
  * Study years are y = 1..Y with Y = ceil(T). Year y covers (y-1, y]; its year-table
    index is k = y-1. Year weight w_y = min(1, T-(y-1)), so a non-integer T prorates the
    last year and sum_y w_y = T.
  * A periodic event with period L happens at tau = n*L for n = 1, 2, ... while n*L < T
    (an event exactly at T is NOT counted). An event at tau belongs to year ceil(tau).
  * Explicit event lists hold offsets t; only 0 < t < T is used.
  * ``by_year`` results have Y+1 entries: index 0 is tau = 0, index y is study year y.

Missing data and gates
  * ``None`` means MISSING and is never treated as zero. A row whose required input is
    missing, whose factor may not be used (licence) or whose unit cannot be converted
    is skipped and counted in ``n_skipped``.
  * A factor may be used only when its licence status is PERMITTED_PUBLIC.
  * Unit conversion is a direct lookup (row-specific conversions first); no chaining.

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
GRID = "GRID"            # pseudo factor id of purchased electricity (no gas breakdown)
REFRIGERANT = "REFRIGERANT"  # pseudo factor id of refrigerant releases


def n_years(T: float) -> int:
    return math.ceil(T)


def year_weights(T: float) -> list[float]:
    """w[0] = 0 (tau = 0), w[y] = min(1, T-(y-1)) for y = 1..ceil(T)."""
    out = [0.0]
    for y in range(1, n_years(T) + 1):
        out.append(min(1.0, T - (y - 1)))
    return out


def periodic_events(T: float, period: Optional[float]) -> list[float]:
    """Times n*period (n >= 1) strictly inside (0, T), by counting up."""
    events: list[float] = []
    if period is None or period <= 0.0:
        return events
    n = 1
    while n * period < T:
        events.append(n * period)
        n += 1
    return events


def explicit_events(T: float, years: Sequence[float]) -> list[float]:
    return [float(t) for t in years if 0 < t < T]


def event_year(tau: float) -> int:
    return math.ceil(tau)


def usable_factor(scn, factor_id: Optional[str]):
    """The factor record, or None when absent or not licensed for use."""
    if factor_id is None:
        return None
    rec = scn.factors.get(factor_id)
    if rec is None or rec.licence_status not in ALLOWED:
        return None
    return rec


def convert(scn, from_unit: str, to_unit: str, extra: Sequence[Any] = ()) -> Optional[float]:
    return model.conversion_factor(scn.unit_conversions, from_unit, to_unit, extra)


def included(scn) -> set[str]:
    return set(scn.boundary.included_lifecycle_stages)


def zeros(n: int) -> list[float]:
    return [0.0] * n
