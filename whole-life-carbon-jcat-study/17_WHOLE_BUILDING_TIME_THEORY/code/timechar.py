"""Stage 1: exact time characteristics of the canonical whole-building function C(T) (independent concept model,
fictional data). Checks marked EXACT are rational identities evaluated on the model's own float inputs; checks
marked FLOAT are measurements in double precision.

  TH-0  (EXACT) the sum of the kernel terms equals the merged knot form at sample periods (up to 60 sample pieces)
  TH-1  (EXACT) C is affine on every piece between consecutive breakpoints
  TH-2  (EXACT) C is continuous at lattice knots; at an event switch point sw (the float where the rule
        g < fl(T(1-eps)) turns on; within 1 ulp of g/(1-eps)) it jumps by J = sum (p + q sw); the value just below sw is
        on the left piece (also checked with the TERMS on both sides of up to 12 sampled events)
  TH-3  (EXACT) slope on a piece = sum of q over active knots; the slope changes at a knot by its q
  TH-4  (EXACT) real-time decomposition C(T) = M([0, T)) + Z(T); dC/dT = rho(T) + Z'(T)
  TH-5  (EXACT) annual increments C(y) - C(y-1) = M((y-1, y]) + Z(y) - Z(y-1)
  TH-6  (EXACT) cumulative integral in closed form
  TH-7  (FLOAT) finite Laplace transform on [0, H] in closed form vs Gauss-Legendre integration of the pieces
  TH-8  (FLOAT) Fourier coefficients in closed form; truncated partial sums: error measured (approximation)
  TH-9  (EXACT order, FLOAT DMD) minimal linear recurrence of the annual increments over Q; DMD with that order
  TH-10 (FLOAT) finite rate of innovation: event times of a jump-only stage recovered from 2K+1 Fourier coefficients

Usage (from this folder): python3 -B timechar.py <out.json> [set names...] [--max-scenarios N]
"""
from __future__ import annotations

import bisect
import cmath
import collections
import json
import math
import random
import sys
import time
from fractions import Fraction

sys.dont_write_bytecode = True
import numpy as np                                     # noqa: E402

import canon                                           # noqa: E402
from checks import sets_unified                        # noqa: E402
from tstudy import baseline                            # noqa: E402

EPS = canon.EPS
D = Fraction(1.0 - EPS)                                # the double (1 - 1e-9) of the gate test
NEG_INF = canon.NEG_INF
INITIAL_UNITS = {"A13-01", "A13-03", "A13-04", "X-01", "A4-01", "A4-02", "A5-04"}
TERMINAL_UNITS = {"C1-01", "C2-01", "C3-01", "X-14", "C4-01", "B1-04"}


def tstar(g: float) -> Fraction:
    """Threshold of the event rule g < T(1 - eps) in exact real arithmetic: the event counts iff T > tstar(g)."""
    return Fraction(g) / D


_SW = {}


def tswitch(g: float) -> float:
    """The float at which the model's event rule g < fl(T * (1 - eps)) switches on: the event counts iff T >= tswitch(g).
    (fl(T * d) is non-decreasing in T, so the set of floats where the rule holds is an up-set.) Within 1 ulp of tstar(g)."""
    if g in _SW:
        return _SW[g]
    x = float(tstar(g))
    while not g < x * (1.0 - EPS):
        x = math.nextafter(x, math.inf)
    while True:
        y = math.nextafter(x, -math.inf)
        if g < y * (1.0 - EPS):
            x = y
        else:
            break
    _SW[g] = x
    return x


# ------------------------------------------------------------------------------------------------------------------
# evaluators
# ------------------------------------------------------------------------------------------------------------------

def cx(can, T: float, stage=None) -> Fraction:
    """EXACT value of the canonical kernel terms at the float T (gate test in float, as the model)."""
    Tg = T * (1.0 - EPS)
    TF = Fraction(T)
    v = Fraction(0)
    for t in can.stage_terms(stage):
        if not t.gate < Tg:
            continue
        if not (t.lo < T and T <= t.hi):
            continue
        if t.length == 0.0:
            v += t.amp
        else:
            x = TF - Fraction(t.start)
            if x > 0:
                v += t.amp * min(x, Fraction(t.length))
    return v


class KF:
    """The merged knot form with prefix sums: C(T) = A0 + sum_{lattice t < T}(p + qT) + sum_{event g < T(1-eps)}(p + qT)."""

    def __init__(self, can, stage=None):
        A0, ev, la = can.knot_form(stage)
        self.A0 = A0
        self.lt = sorted(la)
        self.eg = sorted(ev)
        self.la, self.ev = la, ev
        self.LP, self.LQ, self.EP, self.EQ = [Fraction(0)], [Fraction(0)], [Fraction(0)], [Fraction(0)]
        for t in self.lt:
            self.LP.append(self.LP[-1] + la[t][0]); self.LQ.append(self.LQ[-1] + la[t][1])
        for g in self.eg:
            self.EP.append(self.EP[-1] + ev[g][0]); self.EQ.append(self.EQ[-1] + ev[g][1])

    def __call__(self, T: float) -> Fraction:
        i = bisect.bisect_left(self.lt, T)                     # number of lattice knots t < T
        j = bisect.bisect_left(self.eg, T * (1.0 - EPS))       # number of event knots g < T(1 - eps)
        TF = Fraction(T)
        return self.A0 + self.LP[i] + TF * self.LQ[i] + self.EP[j] + TF * self.EQ[j]

    def knots(self):
        """[(position (exact), p, q, kind, raw)] sorted by position."""
        ks = [(Fraction(t), self.la[t][0], self.la[t][1], "lattice", t) for t in self.lt]
        ks += [(Fraction(tswitch(g)), self.ev[g][0], self.ev[g][1], "event", g) for g in self.eg]
        ks.sort(key=lambda x: x[0])
        return ks


def breakpoints(kf: KF, H: int) -> list:
    pts = {Fraction(k) for k in range(0, H + 1)} | {Fraction(tswitch(g)) for g in kf.eg}
    return sorted(p for p in pts if 0 <= p <= H)


def fl_inside(a: Fraction, b: Fraction, r: Fraction):
    x = float(a + (b - a) * r)
    while Fraction(x) <= a:
        x = math.nextafter(x, math.inf)
    while Fraction(x) >= b:
        x = math.nextafter(x, -math.inf)
    return x if a < Fraction(x) < b else None


def affine_on(f, a, b):
    """(alpha, beta, ok) of f on (a, b) from 3 interior floats (exact)."""
    xs = sorted({x for x in (fl_inside(a, b, Fraction(1, 4)), fl_inside(a, b, Fraction(1, 2)), fl_inside(a, b, Fraction(3, 4)))
                 if x is not None})
    if len(xs) < 2:
        return None
    v = [f(x) for x in xs]
    X = [Fraction(x) for x in xs]
    beta = (v[1] - v[0]) / (X[1] - X[0])
    alpha = v[0] - beta * X[0]
    return alpha, beta, all(alpha + beta * X[i] == v[i] for i in range(len(xs)))


# ------------------------------------------------------------------------------------------------------------------
# TH-0 .. TH-3
# ------------------------------------------------------------------------------------------------------------------

def th0123(can, kf, H, rng):
    bp = breakpoints(kf, H)
    ks = kf.knots()
    pos_p = collections.defaultdict(Fraction); pos_q = collections.defaultdict(Fraction); pos_kind = collections.defaultdict(set)
    for pos, p, q, kd, _ in ks:
        pos_p[pos] += p; pos_q[pos] += q; pos_kind[pos].add(kd)
    pieces, n_aff_bad, n_coef_bad = [], 0, 0
    cumP, cumQ, k = kf.A0, Fraction(0), 0
    for a, b in zip(bp, bp[1:]):
        while k < len(ks) and ks[k][0] <= a:
            cumP += ks[k][1]; cumQ += ks[k][2]; k += 1
        r = affine_on(kf, a, b)
        if r is None:
            continue
        al, be, ok = r
        n_aff_bad += (not ok)
        n_coef_bad += not (al == cumP and be == cumQ)
        pieces.append((a, b, al, be))
    n_jump_bad = n_dq_bad = n_jumps = 0
    jumps, lat_jumps, int_event_jumps = [], [], []
    # scale of the interval-form (window) coefficients: their lattice jumps are rounding-level (exact continuity of the
    # refrigerant stock holds for exact inputs; the float coefficients A_K, B_K, a_j, g_j are rounded separately)
    wscale = max((abs(float(t.amp)) * (t.length or 1.0) for t in can.terms if t.hi != math.inf), default=0.0)
    for (a0, b0, al0, be0), (a1, b1, al1, be1) in zip(pieces, pieces[1:]):
        if b0 != a1:
            continue
        J = (al1 - al0) + (be1 - be0) * b0
        Jth = pos_p[b0] + pos_q[b0] * b0
        n_jump_bad += (J != Jth)
        n_dq_bad += (be1 - be0 != pos_q[b0])
        if J != 0:
            n_jumps += 1
            if "event" in pos_kind[b0]:
                jumps.append(abs(float(J)))
            elif any(abs(g - float(b0)) <= 1e-9 * float(b0) for g in kf.eg[max(0, bisect.bisect_left(kf.eg, float(b0) * (1 - 2e-9))):
                                                                          bisect.bisect_right(kf.eg, float(b0) * (1 + 2e-9))]):
                int_event_jumps.append(abs(float(J)))            # reset of the interval form at an event at integer time
            else:
                lat_jumps.append(abs(float(J)) / max(wscale, 1e-300))
    n_lat_bad = sum(1 for x in lat_jumps if x > 1e-12)            # a lattice jump larger than rounding would contradict TH-2
    n_jump_bad += n_lat_bad
    sample = list(range(len(pieces)))
    rng.shuffle(sample)
    n0, n0_bad = 0, 0
    for i in sorted(sample[:60]):
        a, b, al, be = pieces[i]
        x = fl_inside(a, b, Fraction(1, 2))
        n0 += 1
        n0_bad += (cx(can, x) != kf(x))
    ev_pos = [i for i in range(len(pieces) - 1) if pieces[i][1] == pieces[i + 1][0] and "event" in pos_kind[pieces[i][1]]]
    rng.shuffle(ev_pos)
    n2_terms = n2_terms_bad = n_left_bad = 0
    for i in ev_pos[:12]:
        (a0, b0, al0, be0), (a1, b1, al1, be1) = pieces[i], pieces[i + 1]
        L = affine_on(lambda x: cx(can, x), a0, b0)
        R = affine_on(lambda x: cx(can, x), a1, b1)
        if L is None or R is None:
            continue
        n2_terms += 1
        J = (R[0] - L[0]) + (R[1] - L[1]) * b0
        n2_terms_bad += (J != pos_p[b0] + pos_q[b0] * b0) or not (L[2] and R[2])
        x = math.nextafter(float(b0), -math.inf)               # b0 is a float switch point
        if Fraction(x) > a0:
            n_left_bad += (cx(can, x) != L[0] + L[1] * Fraction(x))
    return dict(n_pieces=len(pieces), n_event_knots=len(kf.eg), n_lattice_knots=len(kf.lt), n_jumps=n_jumps,
                max_abs_jump=max(jumps, default=0.0), n_lattice_rounding_jumps=len(lat_jumps),
                max_rel_lattice_rounding_jump=max(lat_jumps, default=0.0), lattice_jumps_above_1em12=n_lat_bad,
                n_integer_event_reset_jumps=len(int_event_jumps),
                th0_points=n0, th0_bad=n0_bad, th1_affine_bad=n_aff_bad, th3_coef_bad=n_coef_bad,
                th2_jump_bad=n_jump_bad, th3_slope_change_bad=n_dq_bad,
                th2_terms_events=n2_terms, th2_terms_bad=n2_terms_bad, th2_left_continuity_bad=n_left_bad), pieces


# ------------------------------------------------------------------------------------------------------------------
# TH-4, TH-5 real-time decomposition
# ------------------------------------------------------------------------------------------------------------------

def realtime(can):
    """Signed measure M: masses (time, threshold or None, amount, unit, stage) and densities (start, end, rate, unit, stage);
    terminal terms Z (emitted at the end of the study period)."""
    masses, dens, Z = [], [], []
    for t in can.terms:
        if t.unit in TERMINAL_UNITS:
            Z.append(t)
        elif t.kind == "const":
            masses.append((Fraction(0), None, t.amp, t.unit, t.stage))
        elif t.kind == "atom":
            masses.append((Fraction(t.start), Fraction(tswitch(t.gate)), t.amp, t.unit, t.stage))
        elif t.kind in ("cell", "density"):
            s = Fraction(t.start)
            dens.append((s, s + Fraction(t.length), t.amp, t.unit, t.stage))
        elif t.kind == "gcell":
            s, e, ts = Fraction(t.start), Fraction(t.start) + Fraction(t.length), Fraction(tswitch(t.gate))
            if ts >= e:
                masses.append((Fraction(t.gate), ts, t.amp * (e - s), t.unit, t.stage))
            else:
                masses.append((Fraction(t.gate), ts, t.amp * (ts - s), t.unit, t.stage))
                dens.append((ts, e, t.amp, t.unit, t.stage))
        else:
            raise ValueError(t.kind)
    return masses, dens, Z


class RT:
    """Fast exact evaluation of M([0, T)) and rho(T) by prefix sums (masses with exact thresholds; densities as ramps)."""

    def __init__(self, masses, dens):
        self.m0 = sum((a for tm, thr, a, u, s in masses if thr is None), Fraction(0))
        mm = collections.defaultdict(Fraction)
        for tm, thr, a, u, s in masses:
            if thr is not None:
                mm[thr] += a
        self.mt = sorted(mm)
        self.MP = [Fraction(0)]
        for x in self.mt:
            self.MP.append(self.MP[-1] + mm[x])
        dd = collections.defaultdict(lambda: [Fraction(0), Fraction(0)])
        for a0, b0, r, u, s in dens:
            dd[a0][0] -= r * a0; dd[a0][1] += r
            dd[b0][0] += r * b0; dd[b0][1] -= r
        self.dt = sorted(dd)
        self.DP, self.DQ = [Fraction(0)], [Fraction(0)]
        for x in self.dt:
            self.DP.append(self.DP[-1] + dd[x][0]); self.DQ.append(self.DQ[-1] + dd[x][1])

    def M(self, T: Fraction) -> Fraction:
        i = bisect.bisect_right(self.mt, T)                    # masses with threshold <= T
        j = bisect.bisect_left(self.dt, T)
        return self.m0 + self.MP[i] + self.DP[j] + T * self.DQ[j]

    def rho(self, T: Fraction) -> Fraction:
        return self.DQ[bisect.bisect_left(self.dt, T)]


class _ZF:
    """Terminal part: evaluated by its knot form; every 50th call is also summed term by term (exact check)."""

    def __init__(self, zkf, terms, rng):
        self.zkf, self.terms, self.n, self.bad = zkf, terms, 0, 0

    def __call__(self, T: float) -> Fraction:
        v = self.zkf(T)
        self.n += 1
        if self.n % 50 == 1:
            self.bad += (v != sum((t.amp * t.h(T) for t in self.terms), Fraction(0)))
        return v


def zx(Z, T: float) -> Fraction:
    return Z(T)


def th45(can, kf, H, pieces, rng):
    masses, dens, Zt = realtime(can)
    rt = RT(masses, dens)
    zkf = KF(canon.Canon(H=can.H, terms=Zt))                   # the terminal part in knot form (fast, exact)
    Z = _ZF(zkf, Zt, rng)
    n_bad = n_rate_bad = n_zs = n_direct_bad = 0
    zs_rel = []
    sample = set(rng.sample(range(len(pieces)), min(40, len(pieces))))
    for i, (a, b, al, be) in enumerate(pieces):
        x, x2 = fl_inside(a, b, Fraction(1, 3)), fl_inside(a, b, Fraction(2, 3))
        if x is None or x2 is None or x == x2:
            continue
        X, X2 = Fraction(x), Fraction(x2)
        z, z2 = zx(Z, x), zx(Z, x2)
        n_bad += (rt.M(X) + z != al + be * X)
        zs = (z2 - z) / (X2 - X)
        n_rate_bad += (be - rt.rho(X) != zs)
        if zs != 0:
            n_zs += 1
            if be != 0:
                zs_rel.append(abs(float(zs / be)))
        if i in sample:
            direct = sum((am for tm, thr, am, u, s in masses if thr is None or thr <= X), Fraction(0))
            direct += sum((r * (min(X, b0) - a0) for a0, b0, r, u, s in dens if X > a0), Fraction(0))
            n_direct_bad += (direct != rt.M(X))
    n_inc_bad = 0
    for y in range(2, H + 1):
        inc = kf(float(y)) - kf(float(y - 1))
        inc_rt = rt.M(Fraction(y)) - rt.M(Fraction(y - 1)) + zx(Z, float(y)) - zx(Z, float(y - 1))
        n_inc_bad += (inc != inc_rt)
    neg_mass_units = collections.Counter(u for tm, thr, a, u, s in masses if a < 0)
    neg_dens_units = collections.Counter(u for a0, b0, r, u, s in dens if r < 0)
    neg_stage_dens = collections.Counter()
    for st in set(x[4] for x in dens):
        evs = collections.defaultdict(Fraction)
        for a0, b0, r, u, s_ in dens:
            if s_ == st:
                evs[a0] += r; evs[b0] -= r
        run, xs = Fraction(0), sorted(evs)
        for lo, hi in zip(xs, xs[1:]):
            run += evs[lo]
            if run < 0:
                neg_stage_dens[st] += 1
    net_mass = collections.defaultdict(Fraction)
    for tm, thr, a, u, s in masses:
        net_mass[(s, tm)] += a
    neg_stage_mass = collections.Counter(s for (s, tm), a in net_mass.items() if a < 0)
    return dict(th4_decomp_bad=n_bad, th4_rate_bad=n_rate_bad, th4_direct_sum_bad=n_direct_bad, th4_terminal_form_bad=Z.bad,
                pieces_with_terminal_slope=n_zs, max_rel_terminal_slope=max(zs_rel, default=0.0),
                th5_increment_bad=n_inc_bad, n_masses=len(masses), n_densities=len(dens), n_terminal_terms=len(Zt),
                neg_mass_units=dict(neg_mass_units), neg_density_units=dict(neg_dens_units),
                neg_stage_density_intervals=dict(neg_stage_dens), neg_stage_masses=dict(neg_stage_mass)), rt, Z


# ------------------------------------------------------------------------------------------------------------------
# TH-6 .. TH-8
# ------------------------------------------------------------------------------------------------------------------

def integral_closed(kf, T: Fraction) -> Fraction:
    v = kf.A0 * T
    for c, p, q, kd, _ in kf.knots():
        if c < T:
            v += p * (T - c) + q * (T * T - c * c) / 2
    return v


def th6(kf, pieces, H):
    """Integral of the knot form: piece by piece (coefficients of EVERY breakpoint interval from the prefix sums of the
    knots, including intervals too short to hold a float) against the closed form; also at interior points."""
    bp = breakpoints(kf, H)
    ks = kf.knots()
    cumP, cumQ, k = kf.A0, Fraction(0), 0
    acc, n_bad, checked = Fraction(0), 0, 0
    step = max(1, len(bp) // 12)
    for i, (a, b) in enumerate(zip(bp, bp[1:])):
        while k < len(ks) and ks[k][0] <= a:
            cumP += ks[k][1]; cumQ += ks[k][2]; k += 1
        if i % step == 0:
            m = (a + b) / 2
            n_bad += (integral_closed(kf, m) != acc + cumP * (m - a) + cumQ * (m * m - a * a) / 2)
            checked += 1
        acc += cumP * (b - a) + cumQ * (b * b - a * a) / 2
    n_bad += (integral_closed(kf, bp[-1]) != acc)
    return dict(th6_integral_bad=n_bad, th6_points=checked + 1, integral_0_H=float(acc))


def prim(p: float, q: float, c: float, H: float, s: complex) -> complex:
    """int_c^H (p + q T) e^{-sT} dT."""
    if s == 0:
        return p * (H - c) + q * (H * H - c * c) / 2
    F = lambda T: -cmath.exp(-s * T) * ((p + q * T) / s + q / (s * s))
    return F(H) - F(c)


def _knot_arrays(kf, H):
    if getattr(kf, "_arr", None) is None:
        ks = [(float(c), float(p), float(q)) for c, p, q, kd, _ in kf.knots() if c < H]
        kf._arr = (np.array([k[0] for k in ks]), np.array([k[1] for k in ks]), np.array([k[2] for k in ks]))
    return kf._arr


def laplace_closed(kf, H: float, s: complex) -> complex:
    """int_0^H C(T) e^{-sT} dT = A0 (1 - e^{-sH})/s + sum_knots [F(H) - F(c)],  F(T) = -e^{-sT}((p + qT)/s + q/s^2)."""
    return complex(laplace_many(kf, H, np.array([s], dtype=complex))[0])


def laplace_many(kf, H: float, ss) -> np.ndarray:
    c, p, q = _knot_arrays(kf, H)
    A0 = float(kf.A0)
    out = np.empty(len(ss), dtype=complex)
    for i0 in range(0, len(ss), 64):
        s = ss[i0:i0 + 64][:, None]
        zero = (s == 0)
        sz = np.where(zero, 1.0, s)
        F = lambda T: -np.exp(-sz * T) * ((p + q * T) / sz + q / (sz * sz))
        val = np.sum(F(H) - F(c), axis=1) + A0 * (1 - np.exp(-sz[:, 0] * H)) / sz[:, 0]
        val0 = np.sum(p * (H - c) + q * (H * H - c * c) / 2) + A0 * H
        out[i0:i0 + 64] = np.where(zero[:, 0], val0, val)
    return out


def laplace_pieces(pieces, s: complex, n=8) -> complex:
    xg, wg = np.polynomial.legendre.leggauss(n)
    v = 0j
    for a, b, al, be in pieces:
        A, B = float(a), float(b)
        if B <= A:
            continue
        m, r = (A + B) / 2, (B - A) / 2
        T = m + r * xg
        v += np.sum(wg * r * (float(al) + float(be) * T) * np.exp(-s * T))
    return complex(v)


def th78(kf, H, pieces, n_max=(8, 32, 128, 512)):
    Hf = float(H)
    out = {"laplace": [], "fourier": {}}
    for s in (0.01, 0.1, 1.0, complex(0.05, 0.3)):
        a, b = laplace_closed(kf, Hf, s), laplace_pieces(pieces, s)
        out["laplace"].append(dict(s=str(s), rel=abs(a - b) / max(abs(a), 1e-300)))
    N = max(n_max)
    nall = np.arange(-N, N + 1)
    cs = dict(zip(nall.tolist(), (laplace_many(kf, Hf, 2j * math.pi * nall / Hf) / Hf).tolist()))
    out["fourier_closed_vs_pieces_max_rel"] = max(
        abs(cs[n] - laplace_pieces(pieces, 2j * math.pi * n / Hf, 16) / Hf) / max(abs(cs[n]), 1e-300) for n in (0, 1, 5, 37))
    out["fourier_conjugate_symmetry_max"] = max(abs(cs[n] - cs[-n].conjugate()) / max(abs(cs[n]), 1e-300) for n in range(1, N + 1))
    bp = np.array([float(x) for x in breakpoints(kf, H)])
    grid = np.linspace(0.37, Hf - 0.37, 997)
    exact = np.array([float(kf(float(T))) for T in grid])
    scale = max(np.abs(exact).max(), 1e-300)
    dist = np.min(np.abs(grid[:, None] - bp[None, :]), axis=1)
    for M in n_max:
        ns = np.arange(-M, M + 1)
        cvec = np.array([cs[n] for n in ns])
        S = np.real(np.exp(2j * math.pi * np.outer(grid, ns) / Hf) @ cvec)
        err = np.abs(S - exact) / scale
        far = dist > 0.05
        out["fourier"][str(M)] = dict(max_rel_all=float(err.max()), max_rel_far=float(err[far].max()) if far.any() else None,
                                      median_rel=float(np.median(err)))
    nn = np.arange(16, N + 1)
    mag = np.array([abs(cs[n]) for n in nn])
    out["fourier_decay_loglog_slope"] = float(np.polyfit(np.log(nn), np.log(np.maximum(mag, 1e-300)), 1)[0])
    c0, cH = float(kf(math.ulp(0.0))), float(kf(Hf))          # C(0+): the knot form just above 0 (not A0)
    S0 = float(np.real(sum(cs[n] for n in range(-N, N + 1))))
    out["boundary_midpoint"] = dict(C0plus=c0, CH=cH, partial_sum_at_0=S0, midpoint=(c0 + cH) / 2,
                                    rel_to_midpoint=abs(S0 - (c0 + cH) / 2) / max(abs(cH), 1e-300))
    return out


# ------------------------------------------------------------------------------------------------------------------
# TH-9 minimal linear recurrence (exact) and DMD (float)
# ------------------------------------------------------------------------------------------------------------------

def berlekamp_massey(seq):
    """Minimal L and connection polynomial C (C[0] = 1) over Q: sum_{i=0}^{L} C[i] s[n-i] = 0 for n >= L."""
    Cp, Bp = [Fraction(1)], [Fraction(1)]
    L, m, b = 0, 1, Fraction(1)
    for n in range(len(seq)):
        d = seq[n]
        for i in range(1, L + 1):
            if i < len(Cp):
                d += Cp[i] * seq[n - i]
        if d == 0:
            m += 1
            continue
        coef = d / b
        Tp = Cp[:]
        need = len(Bp) + m
        if len(Cp) < need:
            Cp = Cp + [Fraction(0)] * (need - len(Cp))
        for i, x in enumerate(Bp):
            Cp[i + m] -= coef * x
        if 2 * L <= n:
            L, Bp, b, m = n + 1 - L, Tp, d, 1
        else:
            m += 1
    Cp = (Cp + [Fraction(0)] * (L + 1))[:L + 1]
    return L, Cp


def th9(kf, H):
    inc = [kf(float(y)) - kf(float(y - 1)) for y in range(2, H + 1)]
    res = dict(n=len(inc))
    if len(inc) > 260:
        res["skipped"] = "sequence longer than 260"
        return res
    L, Cp = berlekamp_massey(inc)
    ok = all(sum((Cp[i] * inc[n - i] for i in range(L + 1)), Fraction(0)) == 0 for n in range(L, len(inc)))
    res.update(order=L, recurrence_holds=ok, certified_unique=2 * L <= len(inc))
    if 0 < L <= 40 and 2 * L <= len(inc):
        roots = np.roots([float(c) for c in Cp])
        res["eigenvalues"] = sorted([[round(r.real, 10), round(r.imag, 10)] for r in roots])
        x = np.array([float(v) for v in inc])
        Hk = np.array([x[i:i + L] for i in range(len(x) - L + 1)])
        X0, X1 = Hk[:-1].T, Hk[1:].T
        try:
            U, S, Vt = np.linalg.svd(X0, full_matrices=False)
            r = int((S > S[0] * 1e-12).sum())
            At = U[:, :r].T @ X1 @ Vt[:r].T @ np.diag(1 / S[:r])
            ev = np.linalg.eigvals(At)
            res["dmd_rank"] = r
            res["dmd_eigenvalues"] = sorted([[round(e.real, 8), round(e.imag, 8)] for e in ev])
            sc = max(np.abs(x).max(), 1e-300)
            y = list(x[:L])
            for n in range(L, len(x)):
                y.append(-sum(float(Cp[i]) * y[n - i] for i in range(1, L + 1)))
            res["recurrence_float_max_rel"] = float(np.max(np.abs(np.array(y) - x)) / sc)
        except np.linalg.LinAlgError as ex:
            res["dmd_error"] = str(ex)
    return res


# ------------------------------------------------------------------------------------------------------------------
# TH-10 finite rate of innovation
# ------------------------------------------------------------------------------------------------------------------

def th10(can, H, stage):
    kf = KF(can, stage)
    if kf.lt or any(q != 0 for p, q in kf.ev.values()):
        return dict(pure_jump=False)
    ev = sorted((tswitch(g), float(p)) for g, (p, q) in kf.ev.items() if p != 0)
    K = len(ev)
    if K == 0 or K > 30:
        return dict(pure_jump=True, K=K, skipped=True)
    Hf = float(H)
    CH, C0 = float(kf(Hf)), float(kf.A0)
    # X_n = int_0^H C'(T) e^{-i w_n T} dT = sum_j J_j e^{-i w_n tau_j}; by parts: X_n = C(H) e^{-i w_n H} - C(0) + i w_n L(i w_n)
    X = []
    for n in range(0, 2 * K + 1):
        w = 2 * math.pi * n / Hf
        X.append(CH * cmath.exp(-1j * w * Hf) - C0 + 1j * w * laplace_closed(kf, Hf, 1j * w))
    X = np.array(X)
    A = np.array([[X[K + i - j] for j in range(1, K + 1)] for i in range(K)])
    bvec = -np.array([X[K + i] for i in range(K)])
    try:
        h = np.linalg.solve(A, bvec)
    except np.linalg.LinAlgError:
        return dict(pure_jump=True, K=K, singular=True)
    roots = np.roots(np.concatenate([[1.0], h]))
    taus = sorted((-np.angle(r) * Hf / (2 * math.pi)) % Hf for r in roots)
    true = [t for t, _ in ev]
    return dict(pure_jump=True, K=K, max_abs_time_error=float(max(abs(a - b) for a, b in zip(taus, true))),
                cond=float(np.linalg.cond(A)), min_separation=float(min((b - a for a, b in zip(true, true[1:])), default=Hf)))


# ------------------------------------------------------------------------------------------------------------------

def role_of(t) -> str:
    """Role of a kernel term in the ideal equation (roles are never merged)."""
    if t.unit == "B1-04":
        return "R"                                   # end-of-life refrigerant residual (state at T, emitted at T)
    if t.kind == "const":
        return "A_init" if t.unit in INITIAL_UNITS else "A_term"
    return {"cell": "B", "density": "B", "atom": "Gamma", "gcell": "Delta"}[t.kind]


def role_recurrences(can, H):
    """Minimal recurrence order (exact) of the annual increments of each role separately, and of the float switch
    offsets sw(g) - g/(1-eps) in ulps (lemma L-2)."""
    by = collections.defaultdict(list)
    for t in can.terms:
        by[role_of(t)].append(t)
    out = {}
    for r, ts in sorted(by.items()):
        kf = KF(canon.Canon(H=can.H, terms=ts))
        inc = [kf(float(y)) - kf(float(y - 1)) for y in range(2, H + 1)]
        if all(x == 0 for x in inc):
            out[r] = dict(order=0)
            continue
        L, Cp = berlekamp_massey(inc)
        d = dict(order=L, certified_unique=2 * L <= len(inc))
        if 0 < L <= 24 and 2 * L <= len(inc):
            roots = np.roots([float(c) for c in Cp])
            d["eigenvalues"] = sorted([[round(z.real, 8), round(z.imag, 8)] for z in roots])
        out[r] = d
    gs = sorted({t.gate for t in can.terms if t.gate != NEG_INF})
    offs = [abs(Fraction(tswitch(g)) - tstar(g)) / Fraction(math.ulp(float(tstar(g)))) for g in gs]
    return out, dict(n_event_times=len(gs), max_switch_offset_ulp=float(max(offs, default=0)))


def roles(can, H):
    """Value and slope of every role at T = 1, 10, 30, 60, H (where <= H): exact, from per-role knot forms."""
    by = collections.defaultdict(list)
    for t in can.terms:
        by[role_of(t)].append(t)
    kfs = {r: KF(canon.Canon(H=can.H, terms=ts)) for r, ts in by.items()}
    out = {}
    for T in sorted({1.0, 10.0, 30.0, 60.0, float(H)}):
        if T > H:
            continue
        x = math.nextafter(T, -math.inf)
        vals = {r: kf(T) for r, kf in kfs.items()}
        slopes = {}
        for r, kf in kfs.items():
            y = math.nextafter(x, -math.inf) - 1e-6 * T
            slopes[r] = (kf(x) - kf(y)) / (Fraction(x) - Fraction(y))
        out[str(T)] = dict(value={r: float(v) for r, v in vals.items()}, slope_left={r: float(v) for r, v in slopes.items()},
                           n_terms={r: len(ts) for r, ts in by.items()})
    return out


def scenario_entries(names, max_scn):
    sets = sets_unified.build(names)
    for name, cases in sets.items():
        for n, (label, scn, periods) in enumerate(cases):
            if n >= max_scn:
                break
            yield name, label, scn


def analyse(can, label, rng):
    H = can.H
    kf = KF(can)
    r = dict(label=label, H=H, n_terms=len(can.terms))
    r["th0123"], pieces = th0123(can, kf, H, rng)
    r["th45"], rt, Z = th45(can, kf, H, pieces, rng)
    r["th6"] = th6(kf, pieces, H)
    r["th78"] = th78(kf, H, pieces)
    r["th9"] = th9(kf, H)
    r["th10"] = {st: th10(can, H, st) for st in ("B4", "B5")}
    r["roles"] = roles(can, H)
    r["role_recurrence"], r["switch_points"] = role_recurrences(can, H)
    return r


def main(outp, names, max_scn):
    baseline.assert_frozen()
    baseline.load()
    from synth import population
    out = []
    t0 = time.time()
    for name, label, scn in scenario_entries(names or sets_unified.ALL_SETS, max_scn):
        rng = random.Random(sum(map(ord, label)) * 2654435761 % 2 ** 32)
        try:
            can = canon.build(canon.make_system(scn, population.BASELINES))
        except Exception as ex:
            out.append(dict(set=name, label=label, prepare_error="%s %s" % (type(ex).__name__, str(ex)[:120])))
            continue
        r = analyse(can, label, rng)
        r.update(set=name, grid=getattr(scn.operation.grid, "kind", None), gas=getattr(scn.operation.gas, "kind", None))
        out.append(r)
        a, b = r["th0123"], r["th45"]
        bad = sum(a[k] for k in a if k.endswith("_bad")) + sum(b[k] for k in b if k.endswith("_bad")) + r["th6"]["th6_integral_bad"]
        print("[%s] %-38s H %3d terms %5d pieces %4d ev %3d jumps %3d | exact-bad %d | Zslope %4d | rec %s | F512far %.1e | %.0f s"
              % (name, label[:38], r["H"], r["n_terms"], a["n_pieces"], a["n_event_knots"], a["n_jumps"], bad, b["pieces_with_terminal_slope"],
                 r["th9"].get("order"), r["th78"]["fourier"]["512"]["max_rel_far"] or -1, time.time() - t0), flush=True)
        json.dump(out, open(outp, "w"), indent=1, default=str)
    json.dump(out, open(outp, "w"), indent=1, default=str)


if __name__ == "__main__":
    args = sys.argv[1:]
    mx = 10 ** 9
    if "--max-scenarios" in args:
        i = args.index("--max-scenarios")
        mx = int(args[i + 1])
        del args[i:i + 2]
    main(args[0], args[1:], mx)
