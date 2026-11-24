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
