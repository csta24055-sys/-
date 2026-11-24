"""Independent numerical oracle: mpmath.quad (dps=40) and scipy.integrate.quad (float64).

The current waveforms are re-coded here numerically (no SymPy expressions reused from
joule.py), and event additions are counted by an explicit loop, not by floor().
"""
import mpmath as mp
from scipy.integrate import quad as squad
import math

mp.mp.dps = 40
R, I0, KAPPA, G0 = 3, 2, mp.mpf(1) / 3, 100
EVENTS = ((10, 20), (20, 35))
EPS = mp.mpf(10) ** -9


def count(t, c, conv):
    n, k = 0, 1
    while True:
        tau = c * k
        ok = {"right": tau <= t, "left": tau < t, "orig": tau < t * (1 - EPS)}[conv]
        if not ok:
            return n
        n += 1; k += 1


def _mpquad(f, a, b, breaks=()):
    pts = [a] + sorted(x for x in breaks if a < x < b) + [b]
    if b <= a:
        return mp.mpf(0)
    return mp.quad(f, pts)


def g_dc_mp(t, conv="right"):
    t = mp.mpf(t)
    E = _mpquad(lambda x: R * I0 ** 2, mp.mpf(0), t, breaks=(10, 20, 30, 40, 50, 60))
    return G0 + KAPPA * E + sum(A * count(t, c, conv) for c, A in EVENTS)


def g_dc_scipy(t, conv="right"):
    tf = float(t)
    E, _ = squad(lambda x: R * I0 ** 2, 0.0, tf, epsabs=1e-13, epsrel=1e-13) if tf > 0 else (0.0, 0)
    ev = sum(A * count(mp.mpf(t), c, conv) for c, A in EVENTS)
    return G0 + E / 3.0 + float(ev)


def _ev_times(c):
    return [c * k for k in range(1, 60 // c + 1)]


def _amps(w):
    return (mp.sqrt(mp.mpf(20) / KAPPA / (R * w)), mp.sqrt(mp.mpf(35) / KAPPA / (R * w)))


def _breaks(w):
    return sorted({x for c, _ in EVENTS for tau in _ev_times(c) for x in (tau, tau + w)})


def i_pulse(x, w, polarity=(1, 1)):
    """Numeric current of the single-resistor pulse model (windows [tau, tau+w))."""
    aA, aP = _amps(w)
    i = mp.mpf(I0)
    if any(tau <= x < tau + w for tau in _ev_times(10)):
        i += polarity[0] * aA
    if any(tau <= x < tau + w for tau in _ev_times(20)):
        i += polarity[1] * aP
    return i


def g_pulse_single_mp(t, w, polarity=(1, 1)):
    w = mp.mpf(w); t = mp.mpf(t)
    f = lambda x: R * i_pulse(x, w, polarity) ** 2
    return G0 + KAPPA * _mpquad(f, mp.mpf(0), t, breaks=_breaks(w))


def g_pulse_separate_mp(t, w):
    """Three resistors: operating DC, AC pulses, pipe pulses; powers summed, one meter."""
    w = mp.mpf(w); t = mp.mpf(t)
    aA, aP = _amps(w)
    def p(x):
        pa = aA ** 2 * R if any(tau <= x < tau + w for tau in _ev_times(10)) else 0
        pp = aP ** 2 * R if any(tau <= x < tau + w for tau in _ev_times(20)) else 0
        return R * I0 ** 2 + pa + pp
    return G0 + KAPPA * _mpquad(p, mp.mpf(0), t, breaks=_breaks(w))


def e_ac_mp(t, Irms=2, omega=2 * mp.pi, phi=0):
    t = mp.mpf(t)
    f = lambda x: R * (mp.sqrt(2) * Irms * mp.sin(omega * x + phi)) ** 2
    per = 2 * mp.pi / omega
    k = int(mp.floor(t / per))
    breaks = [per * j for j in range(1, k + 1)]
    return _mpquad(f, mp.mpf(0), t, breaks=breaks)


def e_ac_scipy(t, Irms=2.0, omega=2 * math.pi, phi=0.0):
    f = lambda x: R * (math.sqrt(2) * Irms * math.sin(omega * x + phi)) ** 2
    return squad(f, 0.0, float(t), limit=2000, epsabs=1e-12, epsrel=1e-12)[0]


def op_convert_then_integrate_mp(t):
    t = mp.mpf(t)
    kap = lambda x: mp.mpf(1) / 3 if x < 10 else mp.mpf(1) / 4
    return _mpquad(lambda x: kap(x) * R * I0 ** 2, mp.mpf(0), t, breaks=(10,))


def op_meter_then_convert_mp(t):
    t = mp.mpf(t)
    E = _mpquad(lambda x: R * I0 ** 2, mp.mpf(0), t)
    return (mp.mpf(1) / 3 if t < 10 else mp.mpf(1) / 4) * E


# ---------------- D pass 1: numeric shapes on one resistor (independent re-coding) -------
def shape_fn(pieces):
    """pieces: list of (a, b, value); current = sum of values whose [a,b) contains x."""
    return lambda x: sum((v for a, b, v in pieces if a <= x < b), mp.mpf(0))


def norm_pieces(pieces, A_kg):
    e = sum((mp.mpf(v) ** 2 * (mp.mpf(b) - mp.mpf(a)) for a, b, v in pieces), mp.mpf(0)) * R
    amp = mp.sqrt(mp.mpf(A_kg) / KAPPA / e)
    return [(mp.mpf(a), mp.mpf(b), amp * v) for a, b, v in pieces]


def walsh_pieces(a, w, signs):
    a = mp.mpf(a); w = mp.mpf(w); n = len(signs)
    return [(a + w * k / n, a + w * (k + 1) / n, sg) for k, sg in enumerate(signs)]


def shared_kg_mp(piece_lists, lo, hi):
    fs = [shape_fn(p) for p in piece_lists]
    br = sorted({x for p in piece_lists for a, b, _ in p for x in (a, b)})
    return KAPPA * _mpquad(lambda x: R * sum(f(x) for f in fs) ** 2, mp.mpf(lo), mp.mpf(hi), breaks=br)


def separate_kg_mp(piece_lists, lo, hi):
    return sum(shared_kg_mp([p], lo, hi) for p in piece_lists)


def charge_mp(pieces, lo, hi):
    f = shape_fn(pieces)
    br = sorted({x for a, b, _ in pieces for x in (a, b)})
    return _mpquad(f, mp.mpf(lo), mp.mpf(hi), breaks=br)


def fixed_step_true(dt, queries, horizon=60.0):
    """TRUE fixed-step integration in float: every step advances E (+p dt) and both clocks
    (+dt); an event fires at the first step end where the clock >= its period (then reset).
    The value at query t is the state after k = round(t/dt) steps. No closed-form floor."""
    qs = sorted((float(t), t) for t in queries)
    out = {}; E = 0.0; S_ = 0.0; xA = 0.0; xP = 0.0; k = 0; j = 0
    nmax = int(round(horizon / dt))
    while j < len(qs) and int(round(qs[j][0] / dt)) == 0:
        out[qs[j][1]] = 100.0; j += 1
    while k < nmax and j < len(qs):
        E += 12.0 * dt; xA += dt; xP += dt; k += 1
        if xA >= 10.0:
            xA = 0.0; S_ += 20.0
        if xP >= 20.0:
            xP = 0.0; S_ += 35.0
        while j < len(qs) and int(round(qs[j][0] / dt)) == k:
            out[qs[j][1]] = 100.0 + E / 3.0 + S_; j += 1
    return out
