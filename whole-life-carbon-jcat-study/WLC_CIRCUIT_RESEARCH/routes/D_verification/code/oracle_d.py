"""Route D independent oracle: exact rational EVENT-LEDGER SWEEP (stdlib only).

Written without reading or importing route A/E code paths into this module.
Algorithm (deliberately different from closed-form floor/ceil expressions and from
clock-integrator circuits):
  1. build an explicit event ledger by integer stepping  tau = r + k*c  (k = 1, 2, ...)
     from each reset time r of each item (no floor/ceil anywhere);
  2. apply ledger policies (supersession for P1 'substitute') as a SET operation;
  3. evaluate G(t) = G0 + integral_0^t rate(s) ds + sum{amount : event included at t}
     with the inclusion predicate of the declared convention;
  4. the operating integral is a sweep over piecewise-constant rate segments.

All data are FICTIONAL (07_SHARED_CONTRACT P0/P1/P2/Px, architecture S1.2).
Units: kgCO2e, t in years (physical time t for right/left; horizon T for 'orig').

Conventions for an event at tau evaluated at t:
  right : tau <= t            left : tau < t           orig : tau < t*(1-eps), eps=1e-9
G0 is an initial condition present at t=0 under all conventions.
"""
from fractions import Fraction as F

EPS = F(1, 10**9)
RIGHT, LEFT, ORIG = "right", "left", "orig"
CONVENTIONS = (RIGHT, LEFT, ORIG)
HORIZON = F(200)            # ledger horizon (larger than every query used)

CONTRACT_POINTS = ["0", "1", "9.999999", "10", "10.000001", "19.999999", "20",
                   "20.000001", "30", "40", "60"]
KNIFE_POINTS = ["10.000000005", "10.00000002"]
EVENT_TIMES = [10, 20, 30, 40, 60]


class Event:
    __slots__ = ("time", "item", "amount", "ledger", "supersedes")

    def __init__(self, time, item, amount, ledger="base", supersedes=()):
        self.time, self.item, self.amount = F(time), item, F(amount)
        self.ledger, self.supersedes = ledger, frozenset(supersedes)

    def key(self):
        return (self.item, self.time)

    def __repr__(self):
        return f"Event({self.time},{self.item},{self.amount},{self.ledger})"


def item_events(item, period, amount, resets, horizon=HORIZON, reset_is_event=()):
    """Events of one item. `resets` = sorted reset times (0 first). Between reset r and
    the next reset r', events at r+k*period for r+k*period <= r' (an event that lands
    exactly on the next reset is kept; coincidence is resolved by ledger policy).
    Resets listed in `reset_is_event` are themselves replacement events of this item."""
    period = F(period)
    out = []
    rs = [F(r) for r in resets] + [F(horizon)]
    for i in range(len(rs) - 1):
        r, nxt = rs[i], rs[i + 1]
        if r in [F(x) for x in reset_is_event]:
            out.append(Event(r, item, amount))
        tau = r + period                       # integer stepping, no floor
        while tau <= nxt and tau <= horizon:
            if not (tau == nxt and nxt in [F(x) for x in reset_is_event]):
                out.append(Event(tau, item, amount))
            tau += period
    # de-duplicate (item,time) pairs that could arise when tau == next reset
    seen, uniq = set(), []
    for e in out:
        if e.key() not in seen:
            seen.add(e.key()); uniq.append(e)
    return uniq


def ledger(case, policy="substitute", tau_R=F(20), A_R=F(50), t_early=F(7)):
    """Return (events, rate_segments). rate_segments: list of (start, rate)."""
    if case == "P0":
        ev = item_events("AC", 10, 20, [0]) + item_events("PIPE", 20, 35, [0])
        return ev, [(F(0), F(4))]
    if case == "P1":
        tau_R = F(tau_R)
        ev = item_events("AC", 10, 20, [0, tau_R]) + item_events("PIPE", 20, 35, [0, tau_R])
        sup = [e.key() for e in ev if e.time == tau_R] if policy == "substitute" else []
        if policy not in ("substitute", "additional"):
            raise ValueError(policy)
        ev.append(Event(tau_R, "RENOV", A_R, ledger="renovation", supersedes=sup))
        return apply_supersession(ev), [(F(0), F(4))]
    if case == "P2":
        ev = item_events("AC", 10, 20, [0]) + item_events("PIPE", 20, 35, [0])
        first_ac = min(e.time for e in ev if e.item == "AC")
        return ev, [(F(0), F(4)), (first_ac, F(3))]
    if case == "Px":
        ev = item_events("AC", 10, 20, [0, t_early], reset_is_event=[t_early]) \
            + item_events("PIPE", 20, 35, [0])
        return ev, [(F(0), F(4))]
    raise ValueError(case)


def apply_supersession(events):
    """Set semantics: remove every event whose (item,time) is superseded by any event.
    Independent of the order of `events` (it is a set difference)."""
    sup = set()
    for e in events:
        sup |= e.supersedes
    return [e for e in events if e.key() not in sup]


def included(tau, t, conv, eps=EPS):
    if conv == RIGHT:
        return tau <= t
    if conv == LEFT:
        return tau < t
    if conv == ORIG:
        return tau < t * (1 - eps)
    raise ValueError(conv)


def op_integral(t, segs):
    """Exact integral of a piecewise-constant rate from 0 to t (sweep)."""
    total = F(0)
    for i, (s0, r) in enumerate(segs):
        s1 = segs[i + 1][0] if i + 1 < len(segs) else None
        hi = t if s1 is None else min(t, s1)
        if hi > s0:
            total += r * (hi - s0)
    return total


def G(case, t, conv=RIGHT, policy="substitute", G0=F(100), **kw):
    if conv == ORIG and case in ("P2", "Px"):
        raise ValueError("orig convention not declared for P2/Px (NOT_RUN)")
    t = F(t)
    ev, segs = ledger(case, policy, **kw)
    return G0 + op_integral(t, segs) + sum((e.amount for e in ev if included(e.time, t, conv)), F(0))


def limits(case, a, conv=RIGHT, policy="substitute"):
    """Exact one-sided limits of G at a (not delta samples).
    left limit : events with effective time < a;  right limit : effective time <= a,
    where the effective jump time is tau (right/left) or tau/(1-eps) (orig)."""
    a = F(a)
    ev, segs = ledger(case, policy)
    eff = (lambda tau: tau / (1 - EPS)) if conv == ORIG else (lambda tau: tau)
    base = F(100) + op_integral(a, segs)
    lo = base + sum((e.amount for e in ev if eff(e.time) < a), F(0))
    hi = base + sum((e.amount for e in ev if eff(e.time) <= a), F(0))
    return lo, hi


def naive_sequential_G20(order):
    """Counterexample model of a NAIVE sequential processor at t=20 (P1, additional ledger
    but with renovation resetting clocks first-come): items AC, PIPE are 'due' at 20; an item
    fires only if still due; the renovation adds 50 and clears both due flags."""
    g = F(100) + 4 * 20 + 20      # G0 + op + AC@10
    due = {"AC": True, "PIPE": True}
    amt = {"AC": F(20), "PIPE": F(35)}
    for it in order:
        if it == "RENOV":
            g += 50; due = {k: False for k in due}
        elif due[it]:
            g += amt[it]; due[it] = False
    return g


def dec(x):
    """Canonical exact string 'num/den'."""
    x = F(x)
    return f"{x.numerator}/{x.denominator}"
