"""G4 integration -- Phi side (physical time t): ONE hybrid event-driven model for the fictional pilots
P0 / P1 (both policies, also a non-coincident renovation P1') / P2 / Px, with two interchangeable
realizations of the SAME operating term:

  realization "charge" (route A's accepted construct, A-1/A-12/A-14):
      accumulator capacitor Q, operating current I_Q = r(t)/gamma, initial charge G0/gamma,
      each event a charge impulse dQ = A/gamma;  readout G = gamma*Q  (V = Q/C_cap is NOT carbon).
  realization "joule" (route E's accepted construct E-1/E-1p, H-E1):
      resistor R driven so that kappa*I^2*R = r(t) (the source sets I^2 exactly; I itself may be irrational),
      an energy meter E_m = integral of I^2 R dt (the resistor stores nothing), G0 and events as EXTERNAL
      additions S_ext (NOT Joule pulses: one-resistor pulses are non-additive, H-E2 / D-12);
      readout G = kappa*E_m + S_ext.

Shared structure (identical for both realizations):
  * one reset clock per item (AC period 10, pipe period 20), state x in [0,1], rate nu = 1/c;
    a comparator at x = 1 fires the item's event and resets x to 0;
  * external scheduled events (renovation, early replacement) with a declared restart set;
  * SET RULE for simultaneous events: all events due at one instant are collected first; superseded
    clock events are removed as a set; then amounts are added and restarts applied (order-free);
  * P2: a 0/1 latch switches the operating rate 4 -> 3 at the first AC firing;
  * explicit convention parameter:
      right : event at tau counted for t >= tau (right-continuous)
      left  : counted for t >  tau
      orig  : counted for T*(1-eps) > tau (the original horizon rule, eps = 1e-9); realised by clock rate
              (1-eps)/c, external events moved to tau/(1-eps) and left semantics. The operating ramp is NOT
              slowed, so under 'orig' this is a horizon READOUT device, not a physical-time model (A, STATUS).
              orig is declared only for P0 and P1; P2/Px under orig raise ValueError (undefined, as in A/D).

This module is a thin INDEPENDENT re-implementation written for G4: it imports no route code. Exact
rational arithmetic (fractions.Fraction) throughout. All data are FICTIONAL (07, architecture S1.2).
Units: kgCO2e, t in years; J only inside the joule realization, converted by the explicit synthetic kappa.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction as F

EPS = F(1, 10**9)
CONVENTIONS = ("right", "left", "orig")
REALIZATIONS = ("charge", "joule")


@dataclass
class ExtEvent:
    time: F
    name: str
    amount: F
    restarts: frozenset = frozenset()      # clocks set to 0 when this event fires
    supersedes: frozenset = frozenset()    # clock events at the SAME instant removed (set rule)


@dataclass
class Spec:
    case: str
    G0: F
    rate0: F
    clocks: dict                            # name -> (period, amount)
    ext: list = field(default_factory=list)
    rate_switch: tuple | None = None        # (item name, new rate): latched at the item's first firing
    orig_allowed: bool = True


def pilot(case: str, policy: str | None = None, tau_R=F(20), A_R=F(50), t_early=F(7)) -> Spec:
    """Fictional pilots of 07 / architecture S1.2 (values declared there; not re-derived here)."""
    clocks = {"AC": (F(10), F(20)), "PIPE": (F(20), F(35))}
    if case == "P0":
        return Spec("P0", F(100), F(4), clocks)
    if case == "P1":
        if policy not in ("substitute", "additional"):
            raise ValueError("P1 needs policy 'substitute' or 'additional'")
        sup = frozenset(clocks) if policy == "substitute" else frozenset()
        ren = ExtEvent(F(tau_R), "RENOV", F(A_R), restarts=frozenset(clocks), supersedes=sup)
        return Spec(f"P1-{policy}", F(100), F(4), clocks, [ren])
    if case == "P2":
        return Spec("P2", F(100), F(4), clocks, rate_switch=("AC", F(3)), orig_allowed=False)
    if case == "Px":
        early = ExtEvent(F(t_early), "AC-early", F(20), restarts=frozenset({"AC"}))
        return Spec("Px", F(100), F(4), clocks, [early], orig_allowed=False)
    raise ValueError(case)


class Hybrid:
    """Event-driven hybrid automaton. `run(ts)` sweeps once from t=0 over the sorted query times."""

    def __init__(self, spec: Spec, conv: str = "right", realization: str = "charge",
                 gamma=F(1), C_cap=F(1), R=F(3), kappa=F(1, 3)):
        if conv not in CONVENTIONS:
            raise ValueError(f"unknown convention {conv!r}")
        if realization not in REALIZATIONS:
            raise ValueError(f"unknown realization {realization!r}")
        if conv == "orig" and not spec.orig_allowed:
            raise ValueError(f"orig convention not declared for {spec.case} (NOT_RUN / undefined)")
        self.spec, self.conv, self.real = spec, conv, realization
        self.gamma, self.C_cap, self.R, self.kappa = F(gamma), F(C_cap), F(R), F(kappa)
        if self.gamma <= 0 or self.C_cap <= 0 or self.R <= 0 or self.kappa <= 0:
            raise ValueError("gamma, C_cap, R, kappa must be > 0")
        slow = (1 - EPS) if conv == "orig" else F(1)
        self.nu = {k: slow / c for k, (c, _) in spec.clocks.items()}
        self.amount = {k: a for k, (_, a) in spec.clocks.items()}
        # external events on the clock time base (orig: tau/(1-eps))
        self.ext = sorted(((e.time / slow, e) for e in spec.ext), key=lambda p: p[0])
        self.ops = {"segments": 0, "events": 0, "fired_items": 0}

    # ---------------------------------------------------------------- state
    def reset(self):
        self.t = F(0)
        self.x = {k: F(0) for k in self.nu}
        self.latch = False
        self.next_ext = 0
        if self.real == "charge":
            self.Q = self.spec.G0 / self.gamma
        else:
            self.Em = F(0)
            self.S_ext = self.spec.G0
        self.ledger = []                    # (effective time, item, amount) actually added
        self.ops = {"segments": 0, "events": 0, "fired_items": 0}   # counters of the last sweep only

    def rate(self) -> F:
        if self.spec.rate_switch and self.latch:
            return self.spec.rate_switch[1]
        return self.spec.rate0

    def I2(self) -> F:
        """joule realization: the source sets I^2 so that kappa*I^2*R = r."""
        return self.rate() / (self.kappa * self.R)

    def _advance(self, t_new: F):
        dt = t_new - self.t
        if dt < 0:
            raise RuntimeError("time went backwards")
        if dt == 0:
            return
        for k in self.x:
            self.x[k] += self.nu[k] * dt
        if self.real == "charge":
            self.Q += (self.rate() / self.gamma) * dt          # I_Q = r/gamma
        else:
            self.Em += self.I2() * self.R * dt                  # p = I^2 R (J per simulated year)
        self.t = t_new
        self.ops["segments"] += 1

    def _next_event(self):
        cands = [self.t + (1 - x) / self.nu[k] for k, x in self.x.items()]
        if self.next_ext < len(self.ext):
            cands.append(self.ext[self.next_ext][0])
        return min(cands)

    def _add(self, amount: F, item: str):
        if self.real == "charge":
            self.Q += amount / self.gamma                      # charge impulse
        else:
            self.S_ext += amount                               # external addition (not Joule)
        self.ledger.append((self.t, item, amount))

    def _fire(self):
        """All events due at self.t, applied as a SET (order-free)."""
        due_clocks = {k for k, x in self.x.items() if x >= 1}
        due_ext = []
        while self.next_ext < len(self.ext) and self.ext[self.next_ext][0] == self.t:
            due_ext.append(self.ext[self.next_ext][1])
            self.next_ext += 1
        superseded = frozenset().union(*(e.supersedes for e in due_ext)) if due_ext else frozenset()
        for k in sorted(due_clocks):          # sorted only for a deterministic ledger listing
            if k not in superseded:
                self._add(self.amount[k], k)
                self.ops["fired_items"] += 1
                if self.spec.rate_switch and k == self.spec.rate_switch[0]:
                    self.latch = True
            self.x[k] = F(0)                  # comparator resets its clock in every case
        for e in due_ext:
            self._add(e.amount, e.name)
            for k in e.restarts:
                self.x[k] = F(0)
        self.ops["events"] += 1

    def readout(self) -> F:
        if self.real == "charge":
            return self.gamma * self.Q
        return self.kappa * self.Em + self.S_ext

    def run(self, ts) -> dict:
        """G at each query time (Fraction). One sorted sweep from t=0."""
        self.reset()
        out = {}
        strict = self.conv != "right"
        for t in sorted({F(t) for t in ts}):
            if t < 0:
                raise ValueError("t < 0")
            while True:
                te = self._next_event()
                if te > t or (strict and te == t):
                    break
                self._advance(te)
                self._fire()
            self._advance(t)
            out[t] = self.readout()
        return out

    def G(self, t) -> F:
        return self.run([t])[F(t)]

    # ---------------------------------------------------------------- bookkeeping
    def capacitor_view(self):
        """charge realization only: (V, E_cap) -- electrical quantities, NOT carbon."""
        if self.real != "charge":
            raise ValueError("capacitor view exists only for the charge realization")
        return self.Q / self.C_cap, self.Q * self.Q / (2 * self.C_cap)

    def state_tuple(self) -> tuple:
        """(continuous states, discrete states, comparator thresholds, external table entries) of THIS
        realization (readout class: integrators + comparators + linear summing readout, no floor readout)."""
        n_clk = len(self.nu)
        cont = n_clk + (1 if self.real == "charge" else 2)     # Q  |  meter E_m + register S_ext
        disc = 1 if self.spec.rate_switch else 0
        comps = n_clk + len(self.ext)
        return (cont, disc, comps, len(self.ext))


def G(case, t, conv="right", policy=None, realization="charge", **kw) -> F:
    return Hybrid(pilot(case, policy, **kw), conv, realization).G(t)
