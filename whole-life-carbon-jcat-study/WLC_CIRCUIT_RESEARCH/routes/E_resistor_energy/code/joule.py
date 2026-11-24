"""Route E analytic oracle (SymPy): resistor Joule energy E_R(t)=int i(s)^2 R ds.

Everything here is a synthetic, declared fixture (coordination/architecture.md §1.2, §2):
  R = 3 ohm, I0 = 2 A, simulated clock 1 s == 1 year, kappa = 1/3 kgCO2e/J
  => P = I0^2 R = 12 W, kappa*P = 4 kgCO2e/"year".
Energies are kept in joules. kgCO2e is obtained ONLY through to_kg(E, kappa).
G0 and replacement events are external scheduled additions in kgCO2e, NOT Joule heat
(09_RESISTOR_ENERGY_ROUTE.md task 3), except in the deliberate H-E2 pulse experiment.

No import of any other route's code. Not a claim that Joule heating is novel.
"""
from sympy import (Rational, Symbol, integrate, sqrt, sin, cos, pi, floor, ceiling,
                   Piecewise, simplify, S, Max, Min)

R = Rational(3)            # ohm
I0 = Rational(2)           # A
KAPPA = Rational(1, 3)     # kgCO2e per J (synthetic scaling, NOT a physical factor)
G0 = Rational(100)         # kgCO2e, initial embodied (external)
EVENTS = ((Rational(10), Rational(20)), (Rational(20), Rational(35)))  # (period yr, kgCO2e)
EPS = Rational(1, 10**9)   # original-research boundary epsilon
CONVENTIONS = ("right", "left", "orig")

s = Symbol("s", real=True)


def to_kg(E_joule, kappa=KAPPA):
    """The ONLY J -> kgCO2e path: multiply by an explicit kappa [kgCO2e/J]."""
    return kappa * E_joule


def kg_to_joule(A_kg, kappa=KAPPA):
    return A_kg / kappa


def energy(i_expr, t, R_=R, t0=0):
    """E_R(t) - E_R(t0) = int_{t0}^{t} i(s)^2 R ds  (joules), symbolic integration."""
    return integrate(i_expr ** 2 * R_, (s, t0, t))


def power(i_expr, R_=R):
    """Instantaneous dissipated power p_R = i^2 R (W). Not cumulative."""
    return i_expr ** 2 * R_


def n_events(t, c, conv):
    """Number of events n*c (n>=1) counted at time t under a boundary convention.
    right: n c <= t (P0);  left: n c < t;  orig: n c < t(1-eps) (original research)."""
    t = Rational(t)
    if conv == "right":
        return floor(t / c)
    if conv == "left":
        return Max(ceiling(t / c) - 1, 0)
    if conv == "orig":
        return Max(ceiling(t * (1 - EPS) / c) - 1, 0)
    raise ValueError(conv)


def event_sum(t, conv, events=EVENTS):
    return sum((A * n_events(t, c, conv) for c, A in events), S(0))


def g_dc(t, conv="right"):
    """E-R1 analytic oracle: G(t) = G0 + kappa * int_0^t I0^2 R ds + external events."""
    t = Rational(t)
    return G0 + to_kg(energy(I0, t)) + event_sum(t, conv)


def p0_fixture(t, conv="right"):
    """Declared P0 closed form 100 + 4t + 20 n10 + 35 n20 (coded here independently)."""
    t = Rational(t)
    return 100 + 4 * t + 20 * n_events(t, 10, conv) + 35 * n_events(t, 20, conv)


def p1(t, policy, conv="right"):
    """P1: renovation at t=20. substitute: -5 ; additional: +50 (both [t>=20] in right conv)."""
    t = Rational(t)
    k = 1 if bool(n_events(t, 20, conv) >= 1) else 0   # renovation counted like the t=20 event
    return p0_fixture(t, conv) + (Rational(-5) if policy == "substitute" else Rational(50)) * k


# ---------------- H-E2: events forced through the SAME resistor as pulses -------------
HORIZON = 60


def pulse_amplitude(A_kg, w, kappa=KAPPA, R_=R):
    """Rectangular pulse of width w carrying energy A/kappa alone: a^2 R w = A/kappa."""
    return sqrt(kg_to_joule(A_kg, kappa) / (R_ * w))


def _windows(w, polarity=(1, 1), horizon=HORIZON):
    """{tau: [amplitudes]} for P0 events (AC every 10, pipe every 20) on [tau, tau+w)."""
    win = {}
    for (c, A), pol in zip(EVENTS, polarity):
        k = 1
        while c * k <= horizon:
            win.setdefault(c * k, []).append(pol * pulse_amplitude(A, w))
            k += 1
    return win


def _delivered(tau, w, t=None, after=None):
    """Length of window [tau,tau+w) inside [0,t]. Either numeric t, or t = after + w."""
    if after is not None:
        return w if tau <= after else S(0)
    t = Rational(t)
    w = Rational(w)
    return Min(Max(t - tau, 0), w)


def g_pulse_single(t, w, polarity=(1, 1), after=None):
    """One resistor carries I0 + sum of event pulses. E = int (I0 + sum a_k)^2 R.
    Exact SymPy integration of the piecewise-constant current; t = after + w if given."""
    tt = (after + w) if after is not None else Rational(t)
    E = integrate(I0 ** 2 * R, (s, 0, tt))
    for tau, amps in _windows(w, polarity).items():
        L = _delivered(tau, w, t, after)
        E += integrate(((I0 + sum(amps)) ** 2 - I0 ** 2) * R, (s, 0, L))
    return G0 + to_kg(E)


def g_pulse_separate(t, w, after=None):
    """Fix: one resistor per source, powers summed (or one meter per resistor) before
    integrating: E = int [I0^2 R + sum_k a_k^2 R 1_k] ds -- exactly additive."""
    tt = (after + w) if after is not None else Rational(t)
    E = integrate(I0 ** 2 * R, (s, 0, tt))
    for tau, amps in _windows(w).items():
        L = _delivered(tau, w, t, after)
        E += sum((integrate(a ** 2 * R, (s, 0, L)) for a in amps), S(0))
    return G0 + to_kg(E)


def cross_terms_kg(w):
    """Closed forms (kg) of the non-additive parts at a single event time."""
    a10, a20 = pulse_amplitude(20, w), pulse_amplitude(35, w)
    return dict(dc_ac_pulse=simplify(to_kg(2 * I0 * a10 * R * w)),
                dc_pipe_pulse=simplify(to_kg(2 * I0 * a20 * R * w)),
                simultaneous_ac_pipe=simplify(to_kg(2 * a10 * a20 * R * w)))


def ac_operating_cross_kg(w, tau=10, omega=2 * pi, phi=0):
    """Cross term of an AC operating current sqrt2*2 sin(omega s+phi) with the 20 kg pulse
    at tau: 2 a R int_tau^{tau+w} i_op ds, converted with kappa."""
    a = pulse_amplitude(20, w)
    return to_kg(2 * a * R * integrate(sqrt(2) * I0 * sin(omega * s + phi), (s, tau, tau + w)))


# ---------------- H-E3: AC ---------------------------------------------------------------
def e_ac(t, Irms=I0, omega=2 * pi, phi=0, R_=R):
    """Energy for i = sqrt2 Irms sin(omega s + phi), E(0)=0 (symbolic)."""
    return energy(sqrt(2) * Irms * sin(omega * s + phi), t, R_)


def e_ac_closed(t, Irms=I0, omega=2 * pi, phi=0, R_=R):
    return Irms ** 2 * R_ * (t - (sin(2 * omega * t + 2 * phi) - sin(2 * phi)) / (2 * omega))


def ac_ripple_bound_kg(omega, phi, r=4):
    """sup_t |kappa E_ac - r t| = r(1+|sin 2phi|)/(2 omega) <= r/omega."""
    return r * (1 + abs(sin(2 * phi))) / (2 * omega)


# ---------------- H-E4: time-varying EF -------------------------------------------------
def kappa_step(x):
    """P2 as an EF step: 1/3 kg/J on [0,10), 1/4 kg/J on [10,inf) (right-continuous)."""
    return Piecewise((Rational(1, 3), x < 10), (Rational(1, 4), True))


def op_convert_then_integrate(t):
    t = Rational(t)
    return integrate(kappa_step(s) * I0 ** 2 * R, (s, 0, t))


def op_meter_then_convert(t, which="current"):
    """Wrong: read a joule meter, then multiply by one EF (current or initial)."""
    t = Rational(t)
    E = energy(I0, t)
    k = kappa_step(t) if which == "current" else Rational(1, 3)
    return k * E


def p2_fixture(t, conv="right"):
    t = Rational(t)
    op = 4 * Min(t, 10) + 3 * Max(t - 10, 0)
    return 100 + op + 20 * n_events(t, 10, conv) + 35 * n_events(t, 20, conv)


# ---------------- thermal counterexample: temperature is not the energy integral --------
def thermal_rise(t, P=12, R_th=1, C_th=2):
    """C_th dtheta/dt = P - theta/R_th, theta(0)=0 -> bounded, not linear."""
    from sympy import exp
    return P * R_th * (1 - exp(-Rational(t) / (R_th * C_th)))
