"""Closed forms that replace loops of the reference calculation.

Each function states the loop it replaces. All of them are exact: they return the same
number as the loop (up to floating-point rounding of a different operation order), and
``tests/test_closed_forms.py`` checks this on random and adversarial inputs.

Time conventions are those of ``refcalc.base`` (T real, Y = ceil(T), year weights
w_y = min(1, T-(y-1)); an event at tau counts when tau < T*(1-1e-9) and belongs to
year max(1, ceil(tau*(1-1e-9)))). The rules are restated here on purpose: this module
does not import the reference calculation.
"""
from __future__ import annotations

import math
from typing import Optional, Sequence

EPS = 1e-9


def n_years(T: float) -> int:
    return math.ceil(T)


def last_weight(T: float) -> float:
    """Weight of the last study year (1 when T is an integer)."""
    return T - (math.ceil(T) - 1)


def inside(tau: float, T: float) -> bool:
    return tau < T * (1.0 - EPS)


def event_year(tau: float) -> int:
    return max(1, math.ceil(tau * (1.0 - EPS)))


def valid_period(period) -> bool:
    return period is not None and period > 0.0 and not math.isinf(period)


def renewal_count(T: float, period: Optional[float]) -> int:
    """#{ n >= 1 : n*period inside the study period }  -- replaces counting up event by event.

    Mathematically ceil(T/period) - 1. The division is only a first guess; the result
    is corrected with the SAME predicate the loop uses, so the count is identical to
    the loop for every input. A missing, non-finite or non-positive period gives 0.
    """
    if not valid_period(period):
        return 0
    n = int(T / period)
    while n > 0 and not inside(n * period, T):
        n -= 1
    while inside((n + 1) * period, T):
        n += 1
    return n


def skip_weight_periodic(T: float, period: Optional[float], n_events: int) -> float:
    """Sum of year weights over the distinct years that contain a periodic event.

    Replaces building the set of event years and summing w_y over it. For period >= 1
    every event has its own year; for period < 1 the events fill every year from 1 to
    the year of the last event. Only the last study year can have a weight below 1.
    """
    if n_events <= 0:
        return 0.0
    last_event_year = event_year(n_events * period)
    distinct = n_events if period >= 1.0 else last_event_year
    if last_event_year == n_years(T):
        return distinct - 1 + last_weight(T)
    return float(distinct)


def skip_weight_events(T: float, events: Sequence[float]) -> float:
    """Same quantity for an explicit event list (one pass over the list)."""
    Y = n_years(T)
    years = {event_year(t) for t in events}
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


# ----------------------------------------------------------------- grid factor: one piecewise-linear form

def grid_segments(grid, Y: int):
    """A well-formed grid descriptor as segments (first index, end index, value at k = alpha + beta*k).

    All three parametric kinds are the same thing: a piecewise-linear function of the
    year index. Returns None when the descriptor is not well formed (the caller then
    uses the year table).
    """
    kind = grid.kind
    if kind == "CONSTANT":
        return [(0, Y, grid.start, 0.0)] if grid.start is not None else None
    if kind == "LINEAR_DECLINE_TO_FLOOR":
        start, floor, d = grid.start, grid.floor, grid.annual_decline
        if None in (start, floor, d) or d < 0.0 or start < floor:
            return None
        if d == 0.0:
            return [(0, Y, start, 0.0)]
        k0 = min(Y, max(0, math.ceil((start - floor) / d)))
        while k0 > 0 and start - d * (k0 - 1) <= floor:
            k0 -= 1
        while k0 < Y and start - d * k0 > floor:
            k0 += 1
        segments = [(0, k0, start, -d)] if k0 > 0 else []
        if k0 < Y:
            segments.append((k0, Y, floor, 0.0))
        return segments
    if kind == "STEPWISE":
        steps = grid.steps or []
        if not steps or steps[0].from_index != 0:
            return None
        for i in range(len(steps) - 1):
            if not steps[i].from_index < steps[i + 1].from_index:
                return None
        segments = []
        for i, step in enumerate(steps):
            hi = min(steps[i + 1].from_index if i + 1 < len(steps) else Y, Y)
            if step.from_index < hi:
                segments.append((step.from_index, hi, step.value, 0.0))
        return segments
    return None


def _power_sum_2(m: int) -> float:
    """0^2 + 1^2 + ... + (m-1)^2."""
    return (m - 1) * m * (2 * m - 1) / 6.0


def segment_moments(segments, T: float):
    """(G, H) with G = sum_k w_{k+1} g_k and H = sum_k w_{k+1} k g_k  -- replaces the year loop.

    With net demand B + S*k and no clamp, purchased-electricity emission is B*G + S*H.
    """
    Y = n_years(T)
    wl = last_weight(T)
    G = H = 0.0
    for a, b, alpha, beta in segments:
        n = b - a
        s1 = (a + b - 1) * n / 2.0
        s2 = _power_sum_2(b) - _power_sum_2(a)
        G += alpha * n + beta * s1
        H += alpha * s1 + beta * s2
        if a <= Y - 1 < b and wl < 1.0:         # the last year counts with weight wl
            last = alpha + beta * (Y - 1)
            G -= (1.0 - wl) * last
            H -= (1.0 - wl) * (Y - 1) * last
    return G, H


def table_moments(table: Sequence[float], T: float):
    """The same (G, H) from a year table (one scan)."""
    Y = n_years(T)
    wl = last_weight(T)
    G = H = 0.0
    for k in range(Y):
        w = wl if k == Y - 1 else 1.0
        G += w * table[k]
        H += w * k * table[k]
    return G, H


# ----------------------------------------------------------------- refrigerant: one charge cycle at a time

def refrigerant_fractions(T: float, rate: float, top_up: bool, event_years: Sequence[int]):
    """Per unit of initial charge: (leaked fraction, [remaining fraction before each event], end fraction).

    Replaces stepping through every study year. Between two charge changes without
    top-up the remaining share after j whole years is (1-rate)**j, so the leak of a
    cycle is 1-(1-rate)**j (plus a prorated step if the cycle ends in the partial last
    year). With top-up the charge is always full and the leak is rate*T. The leak of a
    cycle is computed with expm1/log1p so that very small rates lose no precision.

    ``event_years`` are the years of the charge changes, in order, possibly repeated.
    """
    Y = n_years(T)
    wl = last_weight(T)
    if top_up:
        return rate * T, [1.0] * len(event_years), 1.0
    log_q = math.log1p(-rate) if rate < 1.0 else None
    leaked = 0.0
    before = []
    m = 1.0
    prev = 0
    n = len(event_years)
    i = 0
    while i <= n:
        y = event_years[i] if i < n else Y
        if y > prev:
            partial = y == Y and wl < 1.0
            whole = y - prev - (1 if partial else 0)
            if whole > 0:
                if log_q is None:               # rate = 1: everything leaks in the first year
                    leaked += m
                    m = 0.0
                else:
                    step = -m * math.expm1(whole * log_q)
                    leaked += step
                    m -= step
            if partial:
                step = m * rate * wl
                leaked += step
                m -= step
            prev = y
        if i < n:
            before.append(m)
            m = 1.0
        i += 1
    return leaked, before, m
