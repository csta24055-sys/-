"""E-R1: event-driven hybrid realisation (exact Fraction arithmetic, stdlib only).

Blocks:
  resistor R (stateless: converts i to p = i^2 R, holds no cumulative value)
  energy meter E [J]         continuous state 1   dE/dt = p
  event ledger S [kgCO2e]    continuous state 2   receives external scheduled additions
  clocks x_A, x_P [yr]       continuous states 3,4  dx/dt = rate, reset at threshold
  comparators x_A>=10, x_P>=20  (2 thresholds)
Readout: G = G0 + kappa*E + S   (kappa explicit, kgCO2e/J)
If the ledger S is merged into one readout register Y = kappa*E + S, the tuple is (3,0,2,0).

Optional P2/H-E4 variant: a gain switch on the integrator (1 discrete flag) makes the
register integrate kappa(t)*p, i.e. it stores carbon, not joules.
"""
from fractions import Fraction as Fr

R = Fr(3); I0 = Fr(2); KAPPA = Fr(1, 3); G0 = Fr(100)
EPS = Fr(1, 10**9)
CLOCKS = (("A", Fr(10), Fr(20)), ("P", Fr(20), Fr(35)))   # name, threshold, kgCO2e


class ER1:
    STATES_SEPARATE = (4, 0, 2, 0)
    STATES_MERGED = (3, 0, 2, 0)
    STATES_EF_SWITCH = (4, 1, 2, 0)

    def __init__(self, conv="right", ef_step=False):
        self.conv = conv
        self.ef_step = ef_step
        self.rate = (1 - EPS) if conv == "orig" else Fr(1)   # slowed clock => orig convention
        self.now = Fr(0)
        self.E = Fr(0)          # joules (meter)
        self.Ycarb = Fr(0)      # carbon integrator, used only if ef_step
        self.S = Fr(0)          # kgCO2e ledger of external additions
        self.x = {n: Fr(0) for n, _, _ in CLOCKS}
        self.flag = 0           # P2: first AC replacement done
        self.ops = 0

    def p(self):
        return I0 * I0 * R      # constant DC operating current through the resistor

    def kappa(self):
        return Fr(1, 4) if (self.ef_step and self.flag) else KAPPA

    def _advance(self, dt):
        self.E += self.p() * dt
        self.Ycarb += self.kappa() * self.p() * dt
        for n in self.x:
            self.x[n] += self.rate * dt
        self.now += dt
        self.ops += 1

    def _fire(self, name):
        thr, A = {n: (c, a) for n, c, a in CLOCKS}[name]
        self.x[name] = Fr(0)
        self.S += A
        if name == "A":
            self.flag = 1
        self.ops += 1

    def run_to(self, t):
        t = Fr(t)
        assert t >= self.now
        while True:
            dts = {n: (c - self.x[n]) / self.rate for n, c, _ in CLOCKS}
            nxt = min(dts.values())
            if self.now + nxt < t or (self.now + nxt == t and self.conv == "right"):
                self._advance(nxt)
                for n, c, _ in CLOCKS:
                    if self.x[n] == c:
                        self._fire(n)
            else:
                self._advance(t - self.now)
                return self.readout()

    def readout(self):
        op = self.Ycarb if self.ef_step else KAPPA * self.E
        return G0 + op + self.S


def g_er1(t, conv="right", ef_step=False):
    return ER1(conv, ef_step).run_to(Fr(t))


def resistor_only_observable(t):
    """E-R0: the resistor alone exposes only p(t) (and, if leaky-thermal, a bounded
    temperature). p is the same for every t, so G(t) is not recoverable from it."""
    return I0 * I0 * R
