"""Closed forms that replace loops of the reference calculation.

Each function states the loop it replaces.

The time rules are evaluated in exact rational arithmetic on the given binary
floating-point values (``as_integer_ratio`` and integers only), exactly as the reference
calculation defines them, so the event counts, event years and skip weights below are
provably the same numbers as the loops they replace, for every finite input:

    c            = the double nearest to 1 - 1e-9, as an exact ratio C_NUM / C_DEN
    inside       : an event at tau counts when tau < T*c
    year(tau)    = max(1, ceil(tau*c))
    n-th event   : of a period L is at tau = n*L exactly (not the rounded product)

The weighted year sums (annual profiles, grid factor moments, refrigerant fractions) are
floating-point sums in a different order than the year loops: they agree with the loops
up to rounding, not bit for bit. ``tests/test_closed_forms.py`` checks all of this
against literal loops written with ``fractions.Fraction``.

Other conventions (T real, Y = ceil(T), year weights w_y = min(1, T-(y-1))) are those of
the reference calculation. The rules are restated here on purpose: this module does not
import the reference calculation.
"""
from __future__ import annotations

import math
from typing import Optional, Sequence

EPS = 1e-9
C_NUM, C_DEN = (1.0 - EPS).as_integer_ratio()    # c as an exact ratio


def finite(x) -> bool:
    """A finite number (False for None, NaN and the infinities)."""
    return x is not None and -math.inf < x < math.inf


def nonneg(x) -> bool:
    """Finite and >= 0."""
    return x is not None and 0.0 <= x < math.inf


def n_years(T: float) -> int:
    return math.ceil(T)


def last_weight(T: float) -> float:
    """Weight of the last study year (1 when T is an integer)."""
    return T - (math.ceil(T) - 1)


def inside(tau, T) -> bool:
    """tau < T*c, exactly (both arguments finite numbers)."""
    a, b = tau.as_integer_ratio()
    p, q = T.as_integer_ratio()
    return a * q * C_DEN < p * C_NUM * b


def event_year(tau) -> int:
    """max(1, ceil(tau*c)), exactly."""
    a, b = tau.as_integer_ratio()
    return max(1, -((-a * C_NUM) // (b * C_DEN)))


def valid_period(period) -> bool:
    """A finite positive number (a period, cycle or service life that produces events)."""
    return period is not None and 0.0 < period < math.inf


def renewal_count(T: float, period: Optional[float]) -> int:
    """#{ n >= 1 : n*period inside the study period }  -- replaces counting up event by event.

    n*period < T*c  <=>  n < T*c/period, so the count is ceil(T*c/period) - 1, evaluated
    with integers. A missing, non-finite or non-positive period gives 0.

    Bounds that follow: T*c/period - 1 <= count < T*c/period (so count < T/period).
    The bound T/period - 1 <= count does NOT hold in general: it fails when T/period lies
    within a relative 1e-9 above a whole number, because an event that close to the end
    of the period is not counted.
    """
    if not valid_period(period):
        return 0
    a, b = period.as_integer_ratio()
    p, q = T.as_integer_ratio()
    return -((-p * C_NUM * b) // (q * C_DEN * a)) - 1


def periodic_year(n: int, period: float) -> int:
    """Year of the n-th periodic event: max(1, ceil(n*period*c)), evaluated with integers."""
    a, b = period.as_integer_ratio()
    return max(1, -((-n * a * C_NUM) // (b * C_DEN)))


def periodic_years(period: float, n_events: int) -> list[int]:
    """Years of the events 1..n_events of a period (the integers of the test are prepared once)."""
    a, b = period.as_integer_ratio()
    num, den = a * C_NUM, b * C_DEN
    return [max(1, -((-n * num) // den)) for n in range(1, n_events + 1)]


def explicit_years(T: float, entries: Sequence) -> list[int]:
    """Years of the entries of an explicit event list that are used: finite, > 0 and inside (list order)."""
    return [event_year(t) for t in entries if finite(t) and t > 0 and inside(t, T)]


def skip_weight_periodic(T: float, period: Optional[float], n_events: int) -> float:
    """Sum of year weights over the distinct years that contain a periodic event.

    Replaces building the set of event years and summing w_y over it. With q = period*c
    (exact): the year of event n is ceil(n*q). If q >= 1 consecutive events are at least
    one year apart in that scale, so the n_events years are distinct. If q < 1 the
    ceiling grows by at most one per event and starts at 1, so the years are exactly
    1..year(last event). Only the last study year can have a weight below 1.
    """
    if n_events <= 0:
        return 0.0
    a, b = period.as_integer_ratio()
    num, den = a * C_NUM, b * C_DEN
    last_event_year = max(1, -((-n_events * num) // den))
    distinct = n_events if num >= den else last_event_year
    if last_event_year == n_years(T):
        return distinct - 1 + last_weight(T)
    return float(distinct)


def skip_weight_years(T: float, years: Sequence[int]) -> float:
    """Sum of year weights over the distinct years of a list of event years (one pass)."""
    distinct = set(years)
    return len(distinct) - (1.0 - last_weight(T) if n_years(T) in distinct else 0.0)


def skip_weight_events(T: float, events: Sequence[float]) -> float:
    """Same quantity for a list of event times (each time is placed in its exact year)."""
    return skip_weight_years(T, [event_year(t) for t in events])


def linear_weighted_sum(T: float, base: float, slope: float) -> float:
    """sum_{k=0..Y-1} w_{k+1} * (base + slope*k)  -- replaces the year loop of a
    CONSTANT (slope = 0) or LINEAR_TREND annual profile.

    The Y-1 full years are summed in closed form and the weighted last year is ADDED
    (nothing is subtracted from a sum over Y full years).
    """
    Y = n_years(T)
    if Y <= 0:
        return 0.0
    full = Y - 1                       # years with weight 1 are k = 0..Y-2
    k_sum = full * (full - 1) / 2.0    # 0 + 1 + ... + (Y-2)
    return base * full + slope * k_sum + last_weight(T) * (base + slope * (Y - 1))


def table_weighted_sum(table: Sequence[float], T: float) -> float:
    """sum_{k=0..Y-1} w_{k+1} * table[k]  -- the year scan of an annual quantity that is given as a year table."""
    Y = n_years(T)
    wl = last_weight(T)
    total = 0.0
    for k in range(Y):
        total += (wl if k == Y - 1 else 1.0) * table[k]
    return total


# ----------------------------------------------------------------- grid factor: one piecewise-linear form

def grid_segments(grid, Y: int):
    """A well-formed grid descriptor as segments (first index, end index, value at k = alpha + beta*k).

    All three parametric kinds are the same thing: a piecewise-linear function of the
    year index. Returns None when the descriptor is not well formed (the caller then
    uses the year table). Well formed: CONSTANT with a finite start >= 0;
    LINEAR_DECLINE_TO_FLOOR with finite start, floor and decline, decline >= 0 and
    start >= floor >= 0; STEPWISE with at least one step, step indices of type int
    strictly increasing from 0 and finite step values >= 0.
    """
    kind = grid.kind
    if kind == "CONSTANT":
        return [(0, Y, grid.start, 0.0)] if nonneg(grid.start) else None
    if kind == "LINEAR_DECLINE_TO_FLOOR":
        start, floor, d = grid.start, grid.floor, grid.annual_decline
        if not (nonneg(start) and nonneg(floor) and nonneg(d) and start >= floor):
            return None
        if d == 0.0:
            return [(0, Y, start, 0.0)]
        # k0 = first index whose value is the floor; the division is only a first guess,
        # corrected with the predicate of the year loop (start - d*k > floor)
        guess = (start - floor) / d
        k0 = Y if guess >= Y else max(0, math.ceil(guess))
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
        if not steps:
            return None
        for step in steps:
            if type(step.from_index) is not int or not nonneg(step.value):
                return None
        if steps[0].from_index != 0:
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


def segment_values(segments) -> list:
    """The yearly values g_0 .. g_{Y-1} of a piecewise-linear series given as segments (one value per year)."""
    values = []
    for a, b, alpha, beta in segments:
        values.extend([alpha + beta * k for k in range(a, b)] if beta else [alpha] * (b - a))
    return values


def table_usable(table: Sequence, Y: int) -> bool:
    """A year table can be used: at least Y entries and the first Y are finite numbers >= 0."""
    if len(table) < Y:
        return False
    for k in range(Y):
        if not nonneg(table[k]):
            return False
    return True


def _power_sum_2(m: int) -> float:
    """0^2 + 1^2 + ... + (m-1)^2."""
    return (m - 1) * m * (2 * m - 1) / 6.0


def segment_moments(segments, T: float):
    """(G, H) with G = sum_k w_{k+1} g_k and H = sum_k w_{k+1} k g_k  -- replaces the year loop.

    With net demand B + S*k and no clamp, purchased-electricity emission is B*G + S*H.
    The full years of each segment are summed in closed form; the last study year
    (k = Y-1) is ADDED with its weight (nothing is subtracted from a full sum).
    The segments must cover the indices 0..Y-1 and end at Y.
    """
    Y = n_years(T)
    wl = last_weight(T)
    G = H = 0.0
    for a, b, alpha, beta in segments:
        holds_last = a <= Y - 1 < b
        hi = b - 1 if holds_last else b         # full years of the segment: k = a .. hi-1
        n = hi - a
        if n > 0:
            s1 = (a + hi - 1) * n / 2.0
            s2 = _power_sum_2(hi) - _power_sum_2(a)
            G += alpha * n + beta * s1
            H += alpha * s1 + beta * s2
        if holds_last:
            last = alpha + beta * (Y - 1)
            G += wl * last
            H += wl * (Y - 1) * last
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
    cycle is computed with expm1/log1p so that very small rates lose no precision, and
    the remaining share with exp, so that a share close to zero loses none either.

    ``event_years`` are the years of the charge changes, in non-decreasing order,
    possibly repeated.
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
                else:                           # leak 1-(1-rate)**whole and remainder (1-rate)**whole, each computed
                    x = whole * log_q           # directly: the small remainder of a long cycle is not obtained
                    leaked += -m * math.expm1(x)    # by subtracting the leak from the charge
                    m *= math.exp(x)
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
