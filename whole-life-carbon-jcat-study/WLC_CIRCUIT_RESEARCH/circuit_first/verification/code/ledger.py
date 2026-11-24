"""Verifier's exact rational event ledger for stage-A scenarios (independent oracle).

Written from the MEANING of the inputs (adapter.md section 1, 07 contract pilots,
architecture section 5.4 conventions, refcalc base.py time rules), not from the builder's
tests or circuit. Nominal event times tau; a convention decides inclusion:
    right:    tau <= T            (epsilon = 0)
    left:     tau <  T            (epsilon = 0)
    original: tau <  T (1 - eps)  (eps = 1e-9, refcalc base.inside)
Year of an event: max(1, ceil(tau (1 - eps))) (refcalc base.event_year); eps = 0 for right/left.
Year weights w_y = min(1, T - (y - 1)), y = 1..ceil(T) (refcalc base.year_weights).

Item semantics (stage-A synthetic schema):
  * own events: clock fires at base + n c (base restarts at the clock's own fire, at an
    explicit event if explicit_policy == 'restart', and at a SUBSTITUTING renovation of the
    item); explicit years are own events under both policies;
  * a packet (amount) is taken at an own event unless a substituting renovation of the item
    happens at the same instant; several sources at one instant give ONE event (set rule);
  * renewals = own events + substituting renovations (used by repair exclusion, efficiency
    switch, degradation age reset);
  * renovation: amount at every listed year (both policies); 'additional' does not touch items.
Continuous quantities (rates, degradation) live in REAL time t. In the circuit the event
schedule of the original convention is dilated: an event of nominal time tau happens at
real time tau/(1-eps). `dilate=True` reproduces that convention; `dilate=False` is the
undilated semantics (renewal at real time tau). The two differ only for time-dependent
quantities (degradation, efficiency switch) and only in the original convention.
"""
from __future__ import annotations

import math
from fractions import Fraction as F

EPS = F(1, 10 ** 9)


def eps_of(conv):
    return EPS if conv == "original" else F(0)


def inside(tau, T, conv):
    tau, T = F(tau), F(T)
    if conv == "right":
        return tau <= T
    if conv == "left":
        return tau < T
    if conv == "original":
        return tau < T * (1 - EPS)
    raise ValueError(conv)


def year_of(tau, conv):
    x = F(tau) * (1 - eps_of(conv))
    return max(1, -((-x.numerator) // x.denominator))   # ceil


def ceil(x):
    x = F(x)
    return -((-x.numerator) // x.denominator)


def item_events(item, renovations, horizon):
    """Nominal (packet_times, renewal_times) of one item up to `horizon`."""
    c = F(item["period"]) if item.get("period") not in (None, 0) and F(item["period"]) > 0 else None
    explicit = sorted({F(x) for x in item.get("explicit", []) if F(x) > 0})
    policy = item.get("explicit_policy", "restart")
    subs = sorted({F(y) for rv in renovations if rv.get("policy") == "substituted"
                   and item["id"] in rv.get("replaces", []) for y in rv.get("years", []) if F(y) > 0})
    restarts = set(subs) | (set(explicit) if policy == "restart" else set())
    packets, renewals = [], []
    base = F(0)
    t = F(0)
    while True:
        cand = []
        if c is not None:
            cand.append(base + c)
        cand += [x for x in explicit if x > t]
        cand += [x for x in subs if x > t]
        if not cand:
            break
        now = min(cand)
        if now > horizon:
            break
        clock = c is not None and now == base + c
        own = clock or now in explicit
        sub = now in subs
        if own and not sub:
            packets.append(now)
        if own or sub:
            renewals.append(now)
        if clock or now in restarts:
            base = now
        t = now
    return packets, renewals


def total(scn, T, conv, dilate=True):
    """Exact stage values and total C(T) for a stage-A scenario."""
    T = F(T)
    e = eps_of(conv)
    real = (lambda tau: tau / (1 - e)) if dilate else (lambda tau: tau)
    st = {}

    def add(s, v):
        st[s] = st.get(s, F(0)) + v
    for row in scn.get("initial", []):
        A = F(row["amount"])
        if A != 0 and inside(0, T, conv):      # signed: a negative atom is kept
            add(row["stage"], A)
    rens = scn.get("renovations", [])
    for rv in rens:
        A = F(rv.get("amount") or 0)
        for y in rv.get("years", []):
            if F(y) > 0 and A != 0 and inside(F(y), T, conv):
                add(rv["stage"], A)
    horizon = T + 1
    ev = {}
    for it in scn.get("items", []):
        pk, rn = item_events(it, rens, horizon)
        ev[it["id"]] = (pk, rn)
        A = F(it.get("amount") or 0)
        if A != 0:
            add(it["stage"], A * sum(1 for p in pk if inside(p, T, conv)))
        if it.get("repair"):
            e0, r = F(it["repair"]["base"]), F(it["repair"]["rate"])
            skip = {year_of(p, conv) for p in rn if inside(p, T, conv)}
            v = F(0)
            for y in range(1, ceil(T) + 1):
                if y not in skip:
                    v += e0 * r * min(F(1), T - (y - 1))
            add(it["repair"]["stage"], v)
    for fl in scn.get("flows", []):
        r = F(fl.get("rate") or 0)
        if fl.get("switch_on"):
            rn = ev[fl["switch_on"]][1]
            ts = real(rn[0]) if rn else None
            ra = F(fl.get("rate_after") or 0)
            if ts is None or ts >= T:
                add(fl["stage"], r * T)
            else:
                add(fl["stage"], r * ts + ra * (T - ts))
        else:
            add(fl["stage"], r * T)              # signed: a negative rate is kept
        if fl.get("degradation"):
            d = fl["degradation"]
            delta = F(d["slope"])
            pts = [F(0)] + [real(x) for x in ev[d["item"]][1] if real(x) < T] + [T]
            add(fl["stage"], sum((delta * (b - a) ** 2 / 2 for a, b in zip(pts[:-1], pts[1:])), F(0)))
    return sum(st.values(), F(0)), st


def event_years(scn, item_id, T, conv):
    """(nominal tau, year) of every renewal of an item inside T."""
    pk, rn = item_events(next(i for i in scn["items"] if i["id"] == item_id), scn.get("renovations", []), F(T) + 1)
    return [(t, year_of(t, conv)) for t in rn if inside(t, T, conv)]
