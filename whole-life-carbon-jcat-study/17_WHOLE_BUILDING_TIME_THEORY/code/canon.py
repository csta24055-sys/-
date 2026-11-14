"""The canonical whole-building equation of the 70-unit model (independent concept model, fictional data).

Starting point (chapter 11 / 14, unchanged code imported read-only): every T-dependent unit is a superposition
of gated clipped ramps h(T; s, l, g) = [g < T(1-eps)] clip((T - s)/l, 0, 1) with T-independent amplitudes, the
end residual B1-04 is the same function in interval form, B2-01 = [ok] rho EL(T), and the stage values are
bs_s(T) = [inc_s] sum_c sigma_c beta_c v_u(c)(T).

This module assembles, for one scenario, the WHOLE-BUILDING function and every stage function as ONE list of
kernel terms and as the minimal truncated-power ("knot") form

    C(T) = A0 + sum_k B_k w_k(T) + sum_j G_j theta(T - tau_j) + sum_m D_m theta(T - tau_m) w_{k_m}(T)
         = A0 + sum_{knots kappa, rule(kappa) < T} (p_kappa + q_kappa T)

with w_k(T) = clip(T - k, 0, 1) and theta(T - tau) = [tau < T(1 - eps)].
Evaluation is exact (fractions.Fraction on the float amplitudes; the gate rule in float exactly as the model).
Nothing here reads the reference calculation; the unified system is only asked for its amplitude columns."""
from __future__ import annotations

import bisect
import collections
import math
import os
import sys
from dataclasses import dataclass, field
from fractions import Fraction

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.normpath(os.path.join(HERE, "..", ".."))
RC = os.path.join(STUDY, "10_TRANSFORM_STUDY", "research_code")
if RC not in sys.path:
    sys.path.insert(0, RC)

from tstudy import rampstep as rs, unified          # noqa: E402  (read-only use)
from specs import system as S_                      # noqa: E402

EPS = rs.EPS
NEG_INF = rs.NEG_INF
STAGES = S_.STAGES
COMP_ROWS = S_.COMP_ROWS
CONST_UNITS = tuple(S_.CONST_VALUE)
SPECTRUM_UNITS = ("B1-02", "B1-03", "B3-01", "B4-02", "B5-01", "B6-03", "B7-04")
OP = "operation"


@dataclass(frozen=True)
class Term:
    """One kernel term of the canonical equation.

    value = amp * k(T),  k(T) = [lo < T <= hi] [gate < T(1-eps)] clip(T - start, 0, length)   (length > 0: a ramp, amp is a rate)
                         k(T) = [lo < T <= hi] [gate < T(1-eps)]                            (length = 0: a step, amp is an amount)
    lo = -inf, hi = +inf for the five kernel shapes of chapter 11; a finite window only for the interval form of B1-04.
    amp is an exact Fraction (the float produced by the masked sum-product, times the exact stage sign and share)."""
    amp: Fraction
    start: float
    length: float
    gate: float
    unit: str
    stage: str
    kind: str          # const | cell | atom | gcell | density | win0 | win1 | wev0 | wev1  (win*: interval form of B1-04)
    lo: float = NEG_INF        # window [lo < T <= hi] (lattice rule); only the interval form of B1-04 uses it
    hi: float = math.inf

    def h(self, T: float) -> Fraction:
        if not (self.lo < T and T <= self.hi):
            return Fraction(0)
        if not self.gate < T * (1.0 - EPS):
            return Fraction(0)
        if self.length == 0.0:
            return Fraction(1)
        x = Fraction(T) - Fraction(self.start)
        return Fraction(0) if x <= 0 else min(x, Fraction(self.length))


def kind_of(p) -> str:
    if p.length == 0.0:
        return "const" if p.gate == NEG_INF else "atom"
    if p.length == 1.0:
        return "cell" if p.gate == NEG_INF else "gcell"
    return "density"


@dataclass
class Canon:
    """Terms of every stage of one scenario; the total is the sum over included stages (already masked)."""
    H: int
    terms: list = field(default_factory=list)
    inc: dict = field(default_factory=dict)
    b2_included: bool = False
    unit_terms: dict = field(default_factory=dict)      # unit -> unsigned terms (all units of COMP_ROWS, every stage)
    _by_stage: dict = field(default_factory=dict, repr=False)

    def stage_terms(self, stage):
        if stage is None:
            return self.terms
        if not self._by_stage:
            for t in self.terms:
                self._by_stage.setdefault(t.stage, []).append(t)
        return self._by_stage.get(stage, [])

    def unit_value(self, T: float, unit: str) -> float:
        return float(sum((t.amp * t.h(T) for t in self.unit_terms.get(unit, [])), Fraction(0)))

    # ---- evaluation -----------------------------------------------------------------------------
    def value(self, T: float, stage: str | None = None, exact: bool = True):
        ts = self.stage_terms(stage)
        if exact:
            return float(sum((t.amp * t.h(T) for t in ts), Fraction(0)))
        return math.fsum(float(t.amp) * float(t.h(T)) for t in ts)

    def stage_values(self, T: float) -> dict:
        return {s: self.value(T, s) for s in STAGES}

    # ---- the minimal truncated-power form ---------------------------------------------------------
    def knot_form(self, stage: str | None = None):
        """(A0, event knots {tau: [p, q]}, lattice knots {t: [p, q]}) with C(T) = A0 + sum_ev[tau < T(1-eps)](p + qT)
        + sum_la[t < T](p + qT); coefficients as exact Fractions, merged per knot."""
        A0 = Fraction(0)
        ev, la = collections.defaultdict(lambda: [Fraction(0), Fraction(0)]), collections.defaultdict(lambda: [Fraction(0), Fraction(0)])
        for t in self.terms:
            if stage is not None and t.stage != stage:
                continue
            a, s, l, g = t.amp, Fraction(t.start), Fraction(t.length), t.gate
            if a == 0:
                continue
            if t.hi != math.inf:                              # window: base * [lo < T] - (base value after hi) * [hi < T]
                if not t.gate < t.hi * (1.0 - EPS):
                    continue                                   # an event that is never counted inside its cell: identically 0
                assert t.lo != NEG_INF and (t.length == 0.0 or (t.start >= t.lo and t.start + t.length <= t.hi)), t
                assert t.gate == NEG_INF or t.lo <= t.gate, t
                v_hi = Fraction(1) if t.length == 0.0 else l            # saturated base for T > hi
                la[t.hi][0] += -a * v_hi
                if t.length == 0.0 and g == NEG_INF:
                    la[t.lo][0] += a                                     # [lo < T]
                    continue
            if t.length == 0.0:
                if g == NEG_INF:
                    A0 += a
                else:
                    ev[g][0] += a
                continue
            end = s + l
            if g == NEG_INF:
                la[t.start][0] += -a * s; la[t.start][1] += a
                la[float(end)][0] += a * end; la[float(end)][1] += -a
            elif g >= float(end) * (1.0 - EPS):
                ev[g][0] += a * l
            else:
                assert g > t.start, ("gate before the start of a ramp", t)
                ev[g][0] += -a * s; ev[g][1] += a
                la[float(end)][0] += a * end; la[float(end)][1] += -a
        drop = lambda d: {k: v for k, v in sorted(d.items()) if v[0] != 0 or v[1] != 0}
        return A0, drop(ev), drop(la)

    def knot_value(self, T: float, stage: str | None = None) -> float:
        A0, ev, la = self.knot_form(stage)
        v = A0
        for tau, (p, q) in ev.items():
            if tau < T * (1.0 - EPS):
                v += p + q * Fraction(T)
        for t, (p, q) in la.items():
            if t < T:
                v += p + q * Fraction(T)
        return float(v)


def b21_share(sysm) -> float:
    return sysm.s("b21.share", OP)


def rate_pieces(sysm) -> dict:
    """Spectrum -> list of (rate or amount, start, length, gate, kind) built from the emission table EMIT exactly as
    unified.System._emit does, except that a density keeps its rate a (per year) instead of the product a*H."""
    import numpy as np
    P = collections.defaultdict(list)
    eng, H = sysm.eng, sysm.H
    for e in S_.EMIT:
        t = e["table"]
        if not eng.nrows(t):
            continue
        a = sysm.v(t, e["amp"])
        idx = np.nonzero(a)[0]
        if not len(idx):
            continue
        out, shape = P[e["spectrum"]], e["shape"]
        k = eng.col(t, e["k"]).v if "k" in e else None
        tau = eng.col(t, e["tau"]).v if "tau" in e else None
        for i in idx:
            amp = float(a[i])
            if shape == "const":
                out.append((amp, 0.0, 0.0, NEG_INF, "const"))
            elif shape == "density":
                out.append((amp, 0.0, float(H), NEG_INF, "density"))
            elif shape == "cell":
                out.append((amp, float(int(k[i])), 1.0, NEG_INF, "cell"))
            elif shape == "atom":
                out.append((amp, float(tau[i]), 0.0, float(tau[i]), "atom"))
            elif shape == "gcell":
                out.append((amp, float(int(k[i])), 1.0, float(tau[i]), "gcell"))
            else:
                raise ValueError(shape)
    return P


def interval_pieces(sysm) -> list:
    """B1-04 in interval form (D-09): for K < T <= K+1,  A_K + B_K (T - K) + sum_{events j of cell K, tau_j < T(1-eps)} (a_j + g_j (T - K)).
    The same columns as unified.System._interval; each coefficient becomes a windowed kernel term."""
    import numpy as np
    from specs.lib import CAL
    from specs.physical import DY
    eng = sysm.eng
    A, B = sysm.v(CAL, "b1.iA"), sysm.v(CAL, "b1.iB")
    out = []
    for K in range(len(A)):
        if A[K] != 0.0:
            out.append((Fraction(float(A[K])), 0.0, 0.0, NEG_INF, "win0", float(K), float(K + 1)))
        if B[K] != 0.0:
            out.append((Fraction(float(B[K])), float(K), 1.0, NEG_INF, "win1", float(K), float(K + 1)))
    if eng.nrows(DY):
        k, p = sysm.v(DY, "k"), sysm.v(DY, "b1.p")
        ea, eg = sysm.v(DY, "b1.e4a"), sysm.v(DY, "b1.e4g")
        tau = eng.col(DY, "b1.tau1").v
        for i in np.nonzero(p)[0]:
            K, t = int(k[i]), float(tau[i])
            if ea[i] != 0.0:
                out.append((Fraction(float(ea[i])), 0.0, 0.0, t, "wev0", float(K), float(K + 1)))
            if eg[i] != 0.0:
                out.append((Fraction(float(eg[i])), float(K), 1.0, t, "wev1", float(K), float(K + 1)))
    return out


def unit_pieces(sysm) -> dict:
    """Unit -> list of (amount or rate as exact Fraction, start, length, gate, kind[, lo, hi])."""
    P = rate_pieces(sysm)
    out = {}
    for u in CONST_UNITS:
        out[u] = [(Fraction(sysm.s(S_.CONST_VALUE[u])), 0.0, 0.0, NEG_INF, "const")]
    for u in SPECTRUM_UNITS:
        out[u] = [(Fraction(a), s, l, g, kd) for a, s, l, g, kd in P.get(u, [])]
    out["B1-04"] = interval_pieces(sysm)                          # the interval form, as the unified system uses
    out["B1-04J"] = [(Fraction(a), s, l, g, kd) for a, s, l, g, kd in P.get("B1-04", [])]   # jump form (comparison only)
    q = Fraction(b21_share(sysm))
    out["B2-01"] = [(Fraction(a) * q, s, l, g, kd) for a, s, l, g, kd in P.get("EL", [])] if q else []
    return out


def stage_inclusion(sysm) -> tuple[dict, bool]:
    scn = sysm.scn
    inc_list = set(scn.boundary.included_lifecycle_stages or [])
    inc = {s: (s in inc_list) for s in STAGES}
    return inc, inc["B2"]


def build(sysm, T_probe: float | None = None) -> Canon:
    """The canonical terms of every stage. ``T_probe`` (optional): a period at which the stage inclusion read by
    the AGG program is cross-checked against the scenario's declared stage list."""
    pieces = unit_pieces(sysm)
    inc, b2 = stage_inclusion(sysm)
    if T_probe is not None:
        sysm.at(T_probe)
        col = sysm.eng.col("STG", "x02.inc").v
        names = list(sysm.tabs.data["STG"]["name"])
        got = {n: bool(c) for n, c in zip(names, col)}
        assert got == inc, ("stage inclusion differs", got, inc)
    can = Canon(H=int(sysm.H), inc=inc, b2_included=b2)
    for u in sorted({r[1] for r in COMP_ROWS}) + ["B1-04J"]:
        can.unit_terms[u] = [Term(pc[0], pc[1], pc[2], pc[3], u, "", pc[4], *(pc[5:7] if len(pc) > 5 else (NEG_INF, math.inf)))
                             for pc in pieces.get(u, []) if pc[0] != 0]
    for stage, unit, sign in COMP_ROWS:
        if not inc[stage]:
            continue
        beta = 1.0
        if (stage, unit) == ("B6", "B2-01"):
            beta = 1.0 if b2 else 0.0
        if beta == 0.0:
            continue
        for pc in pieces.get(unit, []):
            if pc[0] == 0:
                continue
            a, s, l, g, kd = pc[:5]
            lo, hi = (pc[5], pc[6]) if len(pc) > 5 else (NEG_INF, math.inf)
            can.terms.append(Term(a * sign, s, l, g, unit, stage, kd, lo, hi))
    return can


def make_system(scn, baselines=None):
    return unified.System(scn, baselines=baselines, b14="interval")
