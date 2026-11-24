"""Route A circuit realizations (physical-time reading Phi). Exact Fraction arithmetic.

Independent of p0_oracle.py: nothing here calls floor/ceil on t/c; event times come
only from integrating clock states to their comparator thresholds.

Units (simulation mapping, declared): 1 simulated time unit == 1 year.
  gamma  [kgCO2e/C]  defined simulation scaling (NOT a physical conversion)
  Q      [C]         charge on the total accumulator capacitor, G = gamma*Q
  I      [C/yr]      current into the accumulator between events (impulses at events)
  C_cap  [F]         accumulator capacitance, V = Q/C_cap [V]
  P_in   [W-equiv]   instantaneous electrical power into the capacitor, V*I
  E_cap  [J-equiv]   stored electrical energy Q^2/(2 C_cap)  -- NOT carbon
Clock integrators x_k are dimensionless (x = charge / threshold charge of a clock cap).

State 4-tuple (architecture S2): (continuous states, discrete states/counters,
comparator thresholds, external table entries). The independent variable t of the
simulator is not counted; a ramp integrator that reproduces t IS counted.

Realizations
  R1  event-driven: accumulator Q + one clock integrator per equipment type
      (threshold 1, reset) + charge impulses A/gamma; optional external schedule
      (renovation, early reset) and an operating-mode latch (P2).
  R2  impulse-free: ramp y(t) with slope r + sum A_k nu_k, minus sum A_k x_k
      (stairs = ramp - sawtooth residual), no impulses.
  R3  single superperiod clock (period 20) for P0, readout or impulse variant;
      R3i generic: one clock with several (threshold, charge) comparators.
  AC  rectified / zero-mean AC clocks (float; transcendental).
"""
from fractions import Fraction as F
import math

EPS = F(1, 10**9)
RIGHT, LEFT, ORIG = "right", "left", "orig"


class Clock:
    def __init__(self, name, period, charge, conv=RIGHT, eps=EPS, x0=F(0)):
        self.name, self.period, self.charge = name, F(period), F(charge)
        # ORIG convention == LEFT-continuous clock slowed by (1-eps)
        self.nu = (1 - eps) / self.period if conv == ORIG else 1 / self.period
        self.x0 = F(x0)


class ExtEvent:
    """External scheduled event (an external table entry + a comparator on t).
    kind 'renovation': inject A, reset `resets`; with policy 'substitute' it
    suppresses the impulses of clocks in `replaces` that fire at the same instant."""
    def __init__(self, time, charge, resets=(), replaces=(), kind="event"):
        self.time, self.charge = F(time), F(charge)
        self.resets, self.replaces, self.kind = tuple(resets), tuple(replaces), kind


class R1:
    """Event-driven hybrid circuit. `conv` in {right,left,orig}:
    right : at threshold the clock resets to 0 AT tau and the impulse is in Q(tau)
    left  : at tau the clock is held at x=1 and Q excludes the impulse; reset at tau+
    orig  : left semantics with clock rate (1-eps)/c (horizon convention, P0 only)."""

    def __init__(self, clocks, G0=F(100), rates=(F(4),), mode_latch_clock=None,
                 ext=(), conv=RIGHT, policy="substitute", gamma=F(1), C_cap=F(1),
                 sequential_order=None):
        self.clocks, self.G0, self.rates = list(clocks), F(G0), [F(r) for r in rates]
        self.mode_latch_clock = mode_latch_clock
        if conv not in (RIGHT, LEFT, ORIG):
            raise ValueError(f"unsupported convention {conv!r}")
        if mode_latch_clock and conv == ORIG:
            raise ValueError("mode latch (P2) under 'orig' is not defined (no oracle)")
        # ORIG counts an event at tau iff tau < T(1-eps)  <=>  tau/(1-eps) < T.
        # Clocks are slowed by (1-eps); external events must be mapped the same way,
        # otherwise a renovation fires at physical 20 while the clocks fire at
        # 20/(1-eps) (D pass 1 defect: P1-additional@30 gave 290, oracle 345).
        if conv == ORIG:
            ext = [ExtEvent(e.time / (1 - EPS), e.charge, e.resets, e.replaces, e.kind) for e in ext]
        self.ext = sorted(ext, key=lambda e: e.time)
        self.conv, self.policy = conv, policy
        self.gamma, self.C_cap = F(gamma), F(C_cap)
        self.sequential_order = sequential_order  # None => order-free set semantics

    def states(self):
        cont = 1 + len(self.clocks)
        disc = 1 if self.mode_latch_clock else 0
        comps = len(self.clocks) + len(self.ext)
        return (cont, disc, comps, len(self.ext))

    def _apply_set(self, tau, x, fired, ext_now):
        """Order-free simultaneous application at instant tau. Returns charge [kgCO2e]."""
        suppressed = set()
        if self.policy == "substitute":
            for e in ext_now:
                suppressed.update(e.replaces)
        A = F(0)
        for k in fired:
            x[k.name] = F(0)
            if k.name not in suppressed:
                A += k.charge
        for e in ext_now:
            A += e.charge
            for name in e.resets:
                x[name] = F(0)
        return A

    def _apply_sequential(self, tau, x, ext_now):
        """NAIVE sequential application in a fixed item order (counterexample tool):
        each item acts on the state left by the previous one."""
        A = F(0)
        byname = {k.name: k for k in self.clocks}
        for item in self.sequential_order:
            if item in byname:
                k = byname[item]
                if x[k.name] >= 1:
                    x[k.name] = F(0)
                    A += k.charge
            else:
                for e in ext_now:
                    if e.kind == item:
                        A += e.charge
                        for name in e.resets:
                            x[name] = F(0)
        return A

    def run(self, t_end):
        t_end = F(t_end)
        now = F(0)
        Q = self.G0 / self.gamma
        x = {k.name: k.x0 for k in self.clocks}
        mode = 0
        ei = 0
        ops = {"segments": 0, "event_instants": 0}
        while True:
            I = self.rates[mode] / self.gamma
            cand = [now + (1 - x[k.name]) / k.nu for k in self.clocks]
            if ei < len(self.ext):
                cand.append(self.ext[ei].time)
            tau = min(cand) if cand else None
            strict = self.conv in (LEFT, ORIG)
            fire = tau is not None and (tau < t_end or (not strict and tau == t_end))
            stop = t_end if not fire else tau
            dt = stop - now
            Q += I * dt
            for k in self.clocks:
                x[k.name] += k.nu * dt
            now = stop
            ops["segments"] += 1
            if not fire:
                break
            ops["event_instants"] += 1
            fired = [k for k in self.clocks if x[k.name] >= 1]
            assert all(x[k.name] == 1 for k in fired), "exact threshold crossing expected"
            ext_now = []
            while ei < len(self.ext) and self.ext[ei].time == tau:
                ext_now.append(self.ext[ei]); ei += 1
            if self.sequential_order is None:
                A = self._apply_set(tau, x, fired, ext_now)
            else:
                A = self._apply_sequential(tau, x, ext_now)
            Q += A / self.gamma
            if self.mode_latch_clock and any(k.name == self.mode_latch_clock for k in fired) and len(self.rates) > 1:
                mode = 1
        return self._readout(Q, x, I, ops)

    def _readout(self, Q, x, I, ops):
        V = Q / self.C_cap
        return {"G": self.gamma * Q, "Q": Q, "V": V, "I": I, "P_in": V * I,
                "E_cap": Q * Q / (2 * self.C_cap), "x": dict(x), "ops": ops}

    def G(self, t):
        return self.run(t)["G"]


def p0_r1(conv=RIGHT, gamma=1, C_cap=1):
    return R1([Clock("A", 10, 20, conv), Clock("P", 20, 35, conv)], conv=conv,
              gamma=F(gamma), C_cap=F(C_cap))


def p1_r1(policy, conv=RIGHT, sequential_order=None):
    ren = ExtEvent(20, 50, resets=("A", "P"), replaces=("A", "P"), kind="renovation")
    pol = policy if policy in ("substitute", "additional") else "additional"
    return R1([Clock("A", 10, 20, conv), Clock("P", 20, 35, conv)], ext=[ren], conv=conv,
              policy=pol, sequential_order=sequential_order)


def p2_r1(conv=RIGHT):
    if conv == ORIG:
        raise ValueError("P2 under 'orig' is not defined (oracle g_p2 is right/left only)")
    return R1([Clock("A", 10, 20, conv), Clock("P", 20, 35, conv)], rates=(F(4), F(3)),
              mode_latch_clock="A", conv=conv)


def px_r1(conv=RIGHT, t_early=7):
    if conv == ORIG:
        raise ValueError("Px under 'orig' is not defined (oracle g_px is right/left only)")
    early = ExtEvent(t_early, 20, resets=("A",), kind="early_ac")
    return R1([Clock("A", 10, 20, conv), Clock("P", 20, 35, conv)], ext=[early], conv=conv)


class R2:
    """Impulse-free: y' = r + sum A_k nu_k (ramp integrator), clocks x_k (no charge),
    G = G0 + y - sum A_k x_k. Clock reset semantics as in R1."""

    def __init__(self, clocks, G0=F(100), r=F(4), conv=RIGHT):
        self.clocks, self.G0, self.r, self.conv = list(clocks), F(G0), F(r), conv
        self.slope = self.r + sum(k.charge * k.nu for k in self.clocks)

    def states(self):
        return (1 + len(self.clocks), 0, len(self.clocks), 0)

    def G(self, t):
        t = F(t)
        now, y = F(0), F(0)
        x = {k.name: k.x0 for k in self.clocks}
        strict = self.conv in (LEFT, ORIG)
        while True:
            tau = min(now + (1 - x[k.name]) / k.nu for k in self.clocks)
            fire = tau < t or (not strict and tau == t)
            stop = tau if fire else t
            y += self.slope * (stop - now)
            for k in self.clocks:
                x[k.name] += k.nu * (stop - now)
            now = stop
            if not fire:
                break
            for k in self.clocks:
                if x[k.name] == 1:
                    x[k.name] = F(0)
        return self.G0 + y - sum(k.charge * x[k.name] for k in self.clocks)


def p0_r2(conv=RIGHT):
    return R2([Clock("A", 10, 20, conv), Clock("P", 20, 35, conv)], conv=conv)


class R3:
    """Single superperiod clock (period L=20) for P0. Readout (impulse-free):
    G = G0 + slope*t - (A_P + 2 A_A) x + A_A * b,  b = [x >= 1/2] (right) or [x > 1/2]
    (left/orig). Derivation: frac(2s) = 2 frac(s) - b. States (y, x)."""

    def __init__(self, conv=RIGHT, G0=F(100), r=F(4), A_A=F(20), A_P=F(35), L=F(20), eps=EPS):
        self.conv = conv
        self.clk = Clock("S", L, 0, conv, eps)
        self.G0, self.A_A, self.A_P = F(G0), F(A_A), F(A_P)
        # A_A fires twice per superperiod, A_P once
        self.slope = F(r) + (2 * self.A_A + self.A_P) * self.clk.nu

    def states(self):
        return (2, 0, 2, 0)   # ramp y, clock x; comparators x=1 (reset) and x vs 1/2

    def G(self, t):
        t = F(t)
        strict = self.conv in (LEFT, ORIG)
        now, x, y = F(0), F(0), F(0)
        while True:
            tau = now + (1 - x) / self.clk.nu
            fire = tau < t or (not strict and tau == t)
            stop = tau if fire else t
            y += self.slope * (stop - now); x += self.clk.nu * (stop - now); now = stop
            if not fire:
                break
            x = F(0)
        half = F(1, 2)
        b = 1 if ((x >= half) if not strict else (x > half)) else 0
        return self.G0 + y - (self.A_P + 2 * self.A_A) * x + self.A_A * b


class R3i:
    """Generic single clock (period L) with comparator list [(theta, charge)], theta in (0,1],
    theta=1 is the reset threshold; impulses into accumulator Q. States (Q, x).
    Used for P0 ([(1/2,20),(1,55)]) and the FIXED Px schedule ([(7/20,20),(17/20,20),(1,35)])."""

    def __init__(self, thresholds, L=F(20), G0=F(100), r=F(4), conv=RIGHT, eps=EPS):
        if conv not in (RIGHT, LEFT, ORIG):
            raise ValueError(f"unsupported convention {conv!r}")
        self.th = sorted((F(a), F(b)) for a, b in thresholds)
        if self.th[-1][0] != 1:
            raise ValueError("last comparator must be the reset threshold 1")
        self.L, self.G0, self.r, self.conv = F(L), F(G0), F(r), conv
        # ORIG: left semantics + clock slowed by (1-eps) (the ramp is NOT slowed)
        self.nu = (1 - F(eps)) / self.L if conv == ORIG else 1 / self.L

    def states(self):
        return (2, 0, len(self.th), 0)

    def G(self, t):
        t = F(t)
        strict = self.conv in (LEFT, ORIG)
        nu = self.nu
        now, x, Q = F(0), F(0), self.G0
        while True:
            nxt = [(th, A) for th, A in self.th if th > x]
            th, A = nxt[0]
            tau = now + (th - x) / nu
            fire = tau < t or (not strict and tau == t)
            stop = tau if fire else t
            Q += self.r * (stop - now); x += nu * (stop - now); now = stop
            if not fire:
                break
            Q += A
            if th == 1:
                x = F(0)
        return Q


def single_clock_fit(period, t_points=(10, 20), G_targets=(160, 140 + 40 + 75)):
    """Counterexample helper: one merged clock of `period` with ONE charge amount A.
    Returns the set of A (Fraction) consistent with G(10)=160 and G(20)=255 (right conv),
    i.e. A*n(t) = G(t) - 100 - 4t for each t, n from an R1 clock run (no floor)."""
    sols = None
    for t, g in zip(t_points, G_targets):
        n = R1([Clock("M", period, 1)], G0=F(0), rates=(F(0),)).run(t)["G"]  # counts with unit charge
        need = F(g) - 100 - 4 * F(t)
        if n == 0:
            s = None if need == 0 else set()   # None == any A
        else:
            s = {need / n}
        if s is None:
            continue
        sols = s if sols is None else (sols & s)
    return sols


# ---------------- AC clocks (float; transcendental) ----------------
def q_fullwave(t, I0, w):  # phase 0 (kept for the ripple test)
    """Charge from |I0 sin(w t)| into an ideal capacitor, Q(0)=0."""
    k = math.floor(w * t / math.pi)
    return (I0 / w) * (2 * k + 1 - math.cos(w * t - k * math.pi))


def _P_fullwave(v, I0, w):
    """Antiderivative of I0|sin v| in the phase variable v (divided by w): monotone."""
    k = math.floor(v / math.pi)
    return (I0 / w) * (2 * k + 1 - math.cos(v - k * math.pi))


def q_fullwave_phase(t, I0, w, phi=0.0):
    """Charge from |I0 sin(w t + phi)|, Q(0)=0."""
    return _P_fullwave(w * t + phi, I0, w) - _P_fullwave(phi, I0, w)


def _inv_P_fullwave(p, I0, w):
    per_half = 2 * I0 / w
    k = math.floor(p / per_half)
    rem = p - k * per_half
    u = math.acos(max(-1.0, min(1.0, 1 - rem * w / I0)))
    return k * math.pi + u


def hit_fullwave(level, I0, w, phi=0.0):
    """First time q_fullwave_phase reaches `level` (closed form; Q strictly increasing)."""
    v = _inv_P_fullwave(level + _P_fullwave(phi, I0, w), I0, w)
    return (v - phi) / w


def q_zero_mean(t, I0, w, phi=0.0):
    """Unrectified I0 sin(w t + phi) into ideal capacitor: Q=(I0/w)(cos phi - cos(w t+phi))."""
    return (I0 / w) * (math.cos(phi) - math.cos(w * t + phi))


def simulate_clock(t_end, charge_fn, theta=1.0, reset="subtract", clamp=False, dt=1e-3):
    """Actually integrate a clock capacitor fed by a current whose antiderivative is
    `charge_fn(t)` (exact increments per step), comparator at `theta`.
    reset='subtract': q <- q - theta at the hit;  reset='zero': q <- 0 at the hit
    (identical when the hit is located exactly). clamp=True: an ideal diode keeps q>=0
    (applied per step: approximate at the dt scale). Crossing times by bisection.
    Returns the list of hit times."""
    hits, t, q = [], 0.0, 0.0
    while t < t_end:
        t2 = min(t + dt, t_end)
        dq = charge_fn(t2) - charge_fn(t)
        if q + dq >= theta:
            lo, hi = t, t2
            for _ in range(60):
                mid = 0.5 * (lo + hi)
                if q + charge_fn(mid) - charge_fn(t) >= theta:
                    hi = mid
                else:
                    lo = mid
            hits.append(hi)
            q = (q + charge_fn(hi) - charge_fn(t)) - theta if reset == "subtract" else 0.0
            t = hi
            continue
        q += dq
        if clamp and q < 0:
            q = 0.0
        t = t2
    return hits


def ac_clock_count(t, c, w, rect="full", phi=0.0):
    """Clock with threshold 1, AC amplitude chosen so that the RECTIFIED mean current is 1/c.
    full : closed-form hits (reset at exact hit == subtract threshold, no drift)
    zero : unrectified current actually integrated by simulate_clock (no hard-coded 0)."""
    I0 = math.pi / (2 * c)       # mean of |I0 sin| is 2 I0/pi = 1/c
    if rect == "full":
        n = 0
        while hit_fullwave(n + 1, I0, w, phi) <= t:
            n += 1
        return n
    if rect == "zero":
        return len(simulate_clock(t, lambda s: q_zero_mean(s, I0, w, phi), 1.0))
    raise ValueError(rect)


def fullwave_ripple_bound(I0, w):
    """max_t |Q_fw(t) - (2 I0/pi) t| = (I0/w)(sqrt(1-4/pi^2) + 2 asin(2/pi)/pi - 1)."""
    return (I0 / w) * (math.sqrt(1 - 4 / math.pi**2) + 2 * math.asin(2 / math.pi) / math.pi - 1)


class R3k:
    """Alternative 4-tuple trade-off: one clock x (period 20) + one integer counter k of
    completed superperiods; NO ramp integrator. G = G0 + 4*20(k+x) + A_A(2k+b) + A_P k.
    States (1,1,2,0): continuous state traded for an unbounded discrete counter."""

    def __init__(self, conv=RIGHT):
        if conv not in (RIGHT, LEFT):
            raise ValueError("R3k implemented for right/left only")
        self.conv = conv

    def states(self):
        return (1, 1, 2, 0)

    def G(self, t):
        t = F(t)
        strict = self.conv == LEFT
        nu = F(1, 20)
        now, x, k = F(0), F(0), 0
        while True:
            tau = now + (1 - x) / nu
            fire = tau < t or (not strict and tau == t)
            stop = tau if fire else t
            x += nu * (stop - now); now = stop
            if not fire:
                break
            x, k = F(0), k + 1
        half = F(1, 2)
        b = 1 if ((x >= half) if not strict else (x > half)) else 0
        return 100 + 80 * (k + x) + 20 * (2 * k + b) + 35 * k
