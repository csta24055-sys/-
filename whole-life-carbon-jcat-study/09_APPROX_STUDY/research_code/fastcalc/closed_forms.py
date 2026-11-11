"""Closed forms that replace loops of the reference calculation.

Each function states the loop it replaces. All of them are exact: they return the same
number as the loop (up to floating-point rounding of a different operation order), and
``tests/test_closed_forms.py`` checks this on random and adversarial inputs.

Time conventions are those of ``refcalc.base`` (T real, Y = ceil(T), year weights
w_y = min(1, T-(y-1)), periodic events at n*L < T, event year = ceil(tau)).
"""
from __future__ import annotations

import math
from typing import Optional, Sequence


def n_years(T: float) -> int:
    return math.ceil(T)


def last_weight(T: float) -> float:
    """Weight of the last study year (1 when T is an integer)."""
    return T - (math.ceil(T) - 1)


def renewal_count(T: float, period: Optional[float]) -> int:
    """#{ n >= 1 : n*period < T }  -- replaces counting up event by event.

    Mathematically ceil(T/period) - 1. The division is only used as a first guess; the
    result is then corrected with the SAME predicate the loop uses (n*period < T), so the
    count is identical to the loop even when T/period is an integer that floating point
    represents slightly off.
    """
    if period is None or period <= 0.0:
        return 0
    n = int(T / period)
    while n > 0 and not n * period < T:
        n -= 1
    while (n + 1) * period < T:
        n += 1
    return n


def skip_weight_periodic(T: float, period: Optional[float], n_events: int) -> float:
    """Sum of year weights over the distinct years that contain a periodic event.

    Replaces building the set {ceil(n*period)} and summing w_y over it. For period >= 1
    every event has its own year; for period < 1 the events fill every year from 1 to
    ceil(n_events*period). Only the last study year can have a weight below 1.
    """
    if n_events <= 0:
        return 0.0
    last_event_year = math.ceil(n_events * period)
    distinct = n_events if period >= 1.0 else last_event_year
    if last_event_year == n_years(T):
        return distinct - 1 + last_weight(T)
    return float(distinct)


def skip_weight_events(T: float, events: Sequence[float]) -> float:
    """Same quantity for an explicit event list (one pass over the list)."""
    Y = n_years(T)
    years = {math.ceil(t) for t in events}
    return len(years) - (1.0 - last_weight(T) if Y in years else 0.0)


def linear_weighted_sum(T: float, base: float, slope: float) -> float:
    """sum_{k=0..Y-1} w_{k+1} * (base + slope*k)  -- replaces the year loop of a
    CONSTANT (slope = 0) or LINEAR_TREND annual profile."""
    Y = n_years(T)
    if Y <= 0:
        return 0.0
    full = Y - 1                       # years with weight 1 are k = 0..Y-2
    k_sum = full * (full - 1) / 2.0    # 0 + 1 + ... + (Y-2)
    return base * T + slope * (k_sum + last_weight(T) * (Y - 1))


def _arith(first: float, step: float, n: int) -> float:
    """first + (first+step) + ... (n terms)."""
    return n * first + step * n * (n - 1) / 2.0


def grid_cumulative(T: float, grid) -> Optional[float]:
    """sum_{k=0..Y-1} w_{k+1} * g_k for a parametric grid scenario (None for TABLE).

    CONSTANT: start*T. LINEAR_DECLINE_TO_FLOOR: an arithmetic series until the floor is
    reached, then floor times the remaining weight. STEPWISE: step value times the
    weight of the years it covers.
    """
    Y = n_years(T)
    wl = last_weight(T)
    if grid.kind == "CONSTANT":
        return grid.start * T
    if grid.kind == "LINEAR_DECLINE_TO_FLOOR":
        d = grid.annual_decline
        if d <= 0.0:
            k0 = Y
        else:
            k0 = min(Y, max(0, math.ceil((grid.start - grid.floor) / d)))
            while k0 > 0 and grid.start - d * (k0 - 1) <= grid.floor:
                k0 -= 1
            while k0 < Y and grid.start - d * k0 > grid.floor:
                k0 += 1
        # years k < k0 are on the line, years k >= k0 are on the floor; the last year has weight wl
        if k0 >= Y:
            return _arith(grid.start, -d, Y - 1) + wl * (grid.start - d * (Y - 1))
        return _arith(grid.start, -d, k0) + grid.floor * ((Y - 1 - k0) + wl)
    if grid.kind == "STEPWISE":
        steps = sorted(grid.steps, key=lambda s: s.from_index)
        total = 0.0
        for i, step in enumerate(steps):
            lo = max(0, step.from_index)
            hi = steps[i + 1].from_index if i + 1 < len(steps) else Y
            hi = min(hi, Y)
            if hi <= lo:
                continue
            n = hi - lo
            weight = n - 1 + wl if hi == Y else n
            total += step.value * weight
        return total
    return None


def refrigerant_device(T: float, m0: float, rate: float, top_up: bool, event_years: Sequence[int]):
    """Leak, pre-event remaining masses and end mass of one device, cycle by cycle.

    Replaces stepping through every study year. Between two charge changes without
    top-up the remaining mass after j whole years is m0*(1-rate)**j, so the leak of a
    cycle is m0*(1-(1-rate)**j) (plus a prorated step if the cycle ends in the partial
    last year). With top-up the mass is always m0 and the leak is m0*rate*T.

    ``event_years`` are the years (ceil of the event time) of the charge changes, in
    order, possibly repeated. Returns (leaked mass, [mass before each event], end mass).
    """
    Y = n_years(T)
    wl = last_weight(T)
    if top_up:
        return m0 * rate * T, [m0] * len(event_years), m0
    q = 1.0 - rate
    leaked = 0.0
    before = []
    m = m0
    prev = 0
    i = 0
    n = len(event_years)
    while i <= n:
        y = event_years[i] if i < n else Y
        if y > prev:
            partial = y == Y and wl < 1.0
            whole = y - prev - (1 if partial else 0)
            after = m * q ** whole
            leaked += m - after
            m = after
            if partial:
                step = m * rate * wl
                leaked += step
                m -= step
            prev = y
        if i < n:
            before.append(m)
            m = m0
        i += 1
    return leaked, before, m
