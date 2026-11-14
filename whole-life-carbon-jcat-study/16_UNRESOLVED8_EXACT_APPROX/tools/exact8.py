"""Research on the 8 unresolved equations: method A (exact) and method B (high-precision approximation),
both written ONLY with the two existing structures (masked sum-product `sp` / `match` of the unchanged
engine tstudy/msp.py, and knot spectra = lattice sums evaluated as sp steps).

Part 1 (this file, first section): exact floating-point building blocks
  * error-free transformations (two-sum, Veltkamp split, two-product): fixed sequences of single IEEE
    operations, each one sp step (the engine evaluates a term product and the term sum left to right);
  * double-double arithmetic built from them;
  * exact decade E(x) = floor(log10 |x|): decimal-lattice knot spectrum whose knots are c_k = the smallest
    double >= 10^k (coefficients), so that [c_k <= |x|] = [10^k <= |x|] exactly for every double;
  * exact 15-significant-digit mantissa M (round-half-even of the exact binary value, as "%.15g"):
    integer-lattice floor + exact residuals.
"""
from __future__ import annotations

import collections
import math
import os
import sys
from fractions import Fraction

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
# the conversion tools of chapter 15 (compile2, excel_ref, store, fx): research layout, or the repository layout
for _p in (os.path.join(os.path.dirname(HERE), "jcat_tools"), os.path.join(os.path.dirname(HERE), "conv"),
           os.path.join(os.path.dirname(os.path.dirname(HERE)), "15_JCAT_CONVERSION", "tools")):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
import compile2 as K  # noqa: E402
from compile2 import C, EQ, LE, PRESENT, isc, V, T0, T1, T2, T3, T4, E_DIV0, E_VALUE, E_NUM, E_REF, ALL  # noqa: E402,F401


def ceil_double(fr: Fraction) -> float:
    """The smallest double >= fr (fr > 0)."""
    f = float(fr)
    if Fraction(f) < fr:
        f = math.nextafter(f, math.inf)
    return f


def dd_const(fr: Fraction):
    hi = float(fr)
    lo = float(fr - Fraction(hi))
    return hi, lo


POW10_KNOT = {k: ceil_double(Fraction(10) ** k) for k in range(-340, 309)}       # [c_k <= x] == [10^k <= x]
POW10_EXACT = {k: float(10 ** k) for k in range(0, 23)}                          # exactly representable


class Exact8(K.Builder):
    """Builder with the research constructs for the 8 equations. ``mode8`` = "A" (exact) or "B" (approximation).
    Only used for the 8 target patterns; the 584 converted rules keep their compiled programs."""

    mode8 = "A"
    flags8 = None

    # ---- single IEEE operations (one sp step each) -----------------------------------------------
    def add(self, a, b, hint="ad"):
        return self.sp([[a], [b]], hint=hint)

    def sub(self, a, b, hint="sb"):
        return self.sp([[a], [C(-1.0), b]], hint=hint)

    def mul(self, a, b, hint="mu"):
        return self.sp([[a, b]], hint=hint)

    def sel(self, key, table, hint="sl", default=None):
        """sum_k [key = k] v_k : a coefficient chosen by an integer-valued column (masked constants)."""
        terms = [[EQ(key, C(float(k))), C(float(v))] for k, v in table.items() if v != 0.0]
        if default is not None:
            terms.append([default])
        return self.sp(terms or [[C(0.0)]], hint=hint)

    def flag(self, f):
        """Outside the certified/compiled domain: the final result becomes missing (see Builder.finish)."""
        self.__dict__.setdefault("fail_flags", []).append(f)

    # ---- error-free transformations ---------------------------------------------------------------
    def two_sum(self, a, b):
        s = self.add(a, b, "ts")
        bb = self.sub(s, a, "tb")
        t1 = self.sub(s, bb, "t1")
        t2 = self.sub(a, t1, "t2")
        t3 = self.sub(b, bb, "t3")
        return s, self.add(t2, t3, "te")

    def fast_two_sum(self, a, b):
        """|a| >= |b| (or a = 0)."""
        s = self.add(a, b, "fs")
        z = self.sub(s, a, "fz")
        return s, self.sub(b, z, "fe")

    def two_prod(self, a, b):
        p = self.mul(a, b, "tp")
        ah, al = self.split(a)
        bh, bl = self.split(b)
        e = self.sp([[ah, bh], [C(-1.0), p], [ah, bl], [al, bh], [al, bl]], hint="tpe")
        return p, e

    # ---- double-double -------------------------------------------------------------------------------
    def dd_add(self, x, y):
        s, e = self.two_sum(x[0], y[0])
        t, f = self.two_sum(x[1], y[1])
        e = self.add(e, t, "da")
        s, e = self.fast_two_sum(s, e)
        e = self.add(e, f, "db")
        return self.fast_two_sum(s, e)

    def dd_mul(self, x, y):
        p, e = self.two_prod(x[0], y[0])
        c = self.sp([[x[0], y[1]], [x[1], y[0]]], hint="dm")
        e = self.add(e, c, "dn")
        return self.fast_two_sum(p, e)

    def dd_mul_d(self, x, b):
        p, e = self.two_prod(x[0], b)
        e = self.sp([[e], [x[1], b]], hint="dk")
        return self.fast_two_sum(p, e)

    def ulp_full(self, q):
        """ulp of a double q over the whole binary range (binary-lattice knot spectrum, subnormals included)."""
        aq = self.absv(q, "uq")
        terms = [[LE(C(2.0 ** k), aq)] + ([LE(C(2.0 ** (k + 1)), aq, True)] if k < 1023 else []) + [C(2.0 ** (k - 52))]
                 for k in range(-1022, 1024)]
        terms.append([LE(C(2.0 ** -1022), aq, True), C(2.0 ** -1074)])
        return self.sp(terms, hint="ulf")

    # ---- comparisons on exact values -----------------------------------------------------------------
    def absv(self, x, hint="av"):
        return self.sp([[LE(C(0.0), x), x], [LE(C(0.0), x, True), C(-1.0), x]], hint=hint)

    # ---- exact decade and 15-digit mantissa ------------------------------------------------------------
    def decade(self, ax):
        """E = floor(log10 ax) for ax > 0 (exact); 0 for ax = 0."""
        terms = [[LE(C(c), ax)] for k, c in POW10_KNOT.items()]
        n_below = len([k for k in POW10_KNOT if k <= 0])        # knots <= 10^0
        e = self.sp(terms + [[C(-float(n_below))]], hint="E")
        self.notes["knot spectrum: exact decimal lattice [c_k <= |x|], c_k = ceil_double(10^k)"] += 1
        return self.sp([[LE(C(0.0), ax, True), C(0.0)], [LE(C(0.0), ax), LE(ax, C(0.0)), C(0.0)], [LE(ax, C(0.0), True), e]], hint="E")

    def floor_exact_div(self, a, k):
        """floor(a / 10^k) for an integer 0 <= a < 2^53 and a constant 0 <= k <= 22: q0 from the product with
        1/10^k, then corrected by one with the exact residual a - q 10^k (all products exact integers)."""
        if k == 0:
            return a
        p = POW10_EXACT[k]
        q0 = self.floor_nonneg(self.sp([[a, C(1.0 / p)]], hint="qd"))
        r = self.sp([[a], [C(-p), q0]], hint="qr")                  # exact (integers < 2^53)
        q = self.sp([[q0], [LE(C(0.0), r, True), C(-1.0)], [LE(C(p), r), C(1.0)]], hint="qq")
        return q

    def mant15(self, x):
        """(sign, M, E, ok) with |x| = M 10^(E-14) after rounding |x| to 15 significant digits, round-half-even
        on the exact binary value (exactly "%.15g"). M in [10^14, 10^15) (0 for x = 0).
        Exact for 1e-8 <= |x| < 1e37 (decimal scaling by an exact power of ten or an exact division);
        for |x| < 1e-8 and |x| >= 1e37 the scaling uses a double-double power of ten and the rounding is
        CERTIFIED (no exact tie can occur there): bad = 1 only within 2^-52 (in units of the 15th digit) of a
        rounding midpoint - never a wrong digit, a missing value instead."""
        ax = self.absv(x)
        neg = self.sp([[LE(C(0.0), x, True)]], hint="ng")
        E = self.decade(ax)
        # --- branch 1: 1e-8 <= ax < 1e15: y = ax 10^(14-E) exactly as a double-double
        p1 = self.sel(E, {k: 10.0 ** (14 - k) for k in range(-8, 15)}, "p1")
        yh, yl = self.two_prod(ax, p1)
        # --- branch 3: ax < 1e-8: double-double power of ten
        # triple-double constants c = c0 + c1 + c2 (error <= 2^-159 |c|) of 10^(14-E) scaled by 2^-600 / 2^600
        def td(fr):
            c0 = float(fr); c1 = float(fr - Fraction(c0)); c2 = float(fr - Fraction(c0) - Fraction(c1))
            return c0, c1, c2
        lo_tab = {k: td(Fraction(10) ** (14 - k) / Fraction(2) ** 600) for k in range(-325, -8)}
        lo_tab.update({k: td(Fraction(10) ** (14 - k) * Fraction(2) ** 600) for k in range(37, 309)})
        c0 = self.sel(E, {k: v[0] for k, v in lo_tab.items()}, "p3a")
        c1 = self.sel(E, {k: v[1] for k, v in lo_tab.items()}, "p3b")
        c2 = self.sel(E, {k: v[2] for k, v in lo_tab.items()}, "p3c")
        tiny = self.sp([[LE(ax, C(0.0), True), LE(E, C(-9.0))]], hint="tn")     # 0 < ax < 10^-8 (exact decade)
        tiny = EQ(tiny, C(1.0))
        huge = LE(C(37.0), E)                                            # ax >= 10^37 (exact decade)
        small = self.sp([[tiny], [huge]], hint="b3")                     # branch 3: tiny or huge
        ax600 = self.sp([[tiny, ax, C(2.0 ** 600)], [huge, ax, C(2.0 ** -600)]], hint="a6")   # exact power-of-two scaling
        # y = ax600 (c0 + c1 + c2): exact partial products, error-free accumulation -> (zh, zl) with
        # zl = fl(y1 + y2) of the renormalised triple (y0, y1, y2); |y - (y0 + y1 + y2)| <= 2^-156 |y|
        p0, e0 = self.two_prod(c0, ax600)
        p1, e1 = self.two_prod(c1, ax600)
        p2 = self.mul(c2, ax600, "p2")
        s1, t1 = self.two_sum(e0, p1)
        s2, t2 = self.two_sum(e1, p2)
        s3, t3 = self.two_sum(t1, s2)
        rest = self.sp([[s3], [t3], [t2]], hint="r3")
        zh, r = self.fast_two_sum(p0, s1)
        y1, y2 = self.fast_two_sum(r, rest)
        zl = self.add(y1, y2, "zl")                                      # sign of y1 + y2 is preserved
        small = EQ(small, C(1.0))
        # choose branch 1 or 3 for (yh, yl)
        yh = self.sp([[small, zh], [EQ(small["a"], C(1.0), True), yh]], hint="yh")
        yl = self.sp([[small, zl], [EQ(small["a"], C(1.0), True), yl]], hint="yl")
        # integer part and exact fraction a + b of y (a = yh - f exact, b = yl)
        f = self.floor_nonneg(yh)
        a = self.sub(yh, f, "fa")
        # a + b < 0  -> f - 1 ;  a + b >= 1 -> f + 1   (exact comparisons of doubles: a + b >= 1 <=> a - 1 >= -b)
        nb = self.sp([[C(-1.0), yl]], hint="nb")
        am1 = self.sub(a, C(1.0), "am")
        down = self.sp([[EQ(a, C(0.0)), LE(C(0.0), yl, True)]], hint="dw")
        upf = self.sp([[LE(nb, am1)]], hint="uf")
        f = self.sp([[f], [EQ(down, C(1.0)), C(-1.0)], [EQ(upf, C(1.0)), C(1.0)]], hint="f2")
        a = self.sp([[a], [EQ(down, C(1.0)), C(1.0)], [EQ(upf, C(1.0)), C(-1.0)]], hint="a2")
        # frac = a + b compared with 1/2: frac > 1/2 <=> a - 1/2 > -b ; tie <=> a - 1/2 == -b
        ah = self.sub(a, C(0.5), "ah")
        gt = self.sp([[LE(ah, nb, True)]], hint="gt")
        tie = self.sp([[EQ(ah, nb)]], hint="ti")
        half = self.floor_nonneg(self.sp([[f, C(0.5)]], hint="hf"))
        odd = self.sp([[f], [C(-2.0), half]], hint="od")
        m1 = self.sp([[f], [EQ(gt, C(1.0)), C(1.0)], [EQ(tie, C(1.0)), EQ(odd, C(1.0)), C(1.0)]], hint="m1")
        # certification of the double-double branch: |frac - 1/2| must exceed the error bound 2^-95 y
        # certification of branch 3. Error of the triple-double y: constant <= 2^-159 |y|, p2 rounding <= 2^-159 |y|,
        # renormalisation exact up to rest = fl(s3 + t3 + t2) (<= 2^-158 |y|): |y_td - y| <= 2^-156 |y| <= 2^-106
        # (y < 10^15 < 2^50). When a != 1/2 the side is decided exactly (|a - 1/2| >= ulp(y0) > |y1 + y2|);
        # at a = 1/2 the sign of zl decides unless |zl| is within the error: certified when gap > 2^-100.
        gap = self.absv(self.add(ah, yl, "gp"))
        amb = self.sp([[small, LE(gap, C(2.0 ** -100))]], hint="amb")
        # --- branch 2: 1e15 <= ax < 1e37: M = round_half_even(ax / 10^(E-14)) by exact division and residual
        big = self.sp([[LE(C(15.0), E), LE(E, C(36.0))]], hint="bg")     # 10^15 <= ax < 10^37 (exact decade)
        big = EQ(big, C(1.0))
        dv = self.sel(E, {k: 10.0 ** (k - 14) for k in range(15, 37)}, "dv")
        dv1 = self.sp([[big, dv], [EQ(big["a"], C(1.0), True), C(1.0)]], hint="dv1")
        q = self.divide(ax, dv1, [big]) if self.improve else self.sp([[big, ax, {"fn": "inv", "a": dv1}]], hint="q")
        fq = self.floor_nonneg(self.sp([[big, q]], hint="fq"))
        # exact residual R = ax - fq dv  (fq dv exact as a double-double; ax - (h + l))
        ph2, pl2 = self.two_prod(fq, dv1)
        s1, e1 = self.two_sum(self.sp([[big, ax]], hint="ab"), self.sp([[C(-1.0), ph2]], hint="mp"))
        s2, e2 = self.two_sum(s1, self.sp([[C(-1.0), pl2]], hint="mq"))
        R = self.sp([[s2], [e1], [e2]], hint="R")                        # |R| < 2 dv, few significant bits
        fq = self.sp([[fq], [LE(C(0.0), R, True), C(-1.0)], [LE(dv1, R), C(1.0)]], hint="fq2")
        R = self.sp([[R], [LE(C(0.0), R, True), dv1], [LE(dv1, R), C(-1.0), dv1]], hint="R2")
        hd = self.sp([[dv1, C(0.5)]], hint="hd")
        gt2 = self.sp([[LE(R, hd, True)]], hint="g2")
        tie2 = self.sp([[EQ(R, hd)]], hint="t2")
        hf2 = self.floor_nonneg(self.sp([[fq, C(0.5)]], hint="h2"))
        odd2 = self.sp([[fq], [C(-2.0), hf2]], hint="o2")
        m2 = self.sp([[fq], [EQ(gt2, C(1.0)), C(1.0)], [EQ(tie2, C(1.0)), EQ(odd2, C(1.0)), C(1.0)]], hint="m2")
        M = self.sp([[EQ(big["a"], C(1.0), True), m1], [big, m2]], hint="M")
        M = self.sp([[LE(C(0.0), ax, True), C(0.0)], [LE(C(0.0), ax), LE(ax, C(0.0)), C(0.0)], [LE(ax, C(0.0), True), M]], hint="M0")
        # renormalise M = 10^15 -> 10^14, E + 1
        ren = self.sp([[EQ(M, C(1e15))]], hint="rn")
        M = self.sp([[EQ(ren, C(1.0), True), M], [EQ(ren, C(1.0)), C(1e14)]], hint="M1")
        E = self.sp([[E], [EQ(ren, C(1.0)), C(1.0)]], hint="E1")
        bad = self.sp([[EQ(amb, C(1.0))]], hint="mbad")          # certified everywhere else (every finite double)
        self.notes["exact 15-digit mantissa (error-free transformations, integer lattice)"] += 1
        return neg, M, E, bad

    # ---- ROUND / ROUNDDOWN / ROUNDUP, method A ----------------------------------------------------------
    def round_exact(self, x, d, mode):
        """Exactly the model  float(Decimal("%.15g" % x).quantize(10^-d, HALF_UP | DOWN | UP))  for d >= 0."""
        neg, M, E, bad = self.mant15(x)
        self.flag(bad)
        # stated domain of method A: |x| < 10^37 (and the powers of ten 10^E, E >= 37, reached by the 15-digit rounding)
        self.flag(self.sp([[LE(C(37.0), E), EQ(M, C(1e14), True)]], hint="rbig"))
        j = self.sp([[C(float(14 - d))], [C(-1.0), E]], hint="j")         # digits of M below 10^-d
        # j <= 0: the 15-digit value has no digit below 10^-d: value = M 10^(E-14), correctly rounded
        pE = self.sel(E, {k: 10.0 ** (k - 14) for k in range(14, 37)}, "pE")
        dE = self.sel(E, {k: 10.0 ** (14 - k) for k in range(-8, 14)}, "dE")
        nolow = LE(j, C(0.0))
        p10 = self.sel(E, {k: float(10 ** k) for k in range(37, 309)}, "p10")      # correctly rounded 10^E
        v_hi = self.sp([[nolow, LE(C(14.0), E), LE(E, C(36.0)), M, pE], [nolow, LE(C(37.0), E), p10]], hint="vh")
        v_lo = self.divide(M, self.sp([[nolow, LE(C(14.0), E, True), dE], [LE(j, C(0.0), True), C(1.0)], [LE(C(14.0), E), C(1.0)]], hint="dd"),
                           [nolow, LE(C(14.0), E, True)])
        # 1 <= j <= 15: q = floor(M / 10^j), rem = M - q 10^j (exact integers)
        pj = self.sel(j, {k: 10.0 ** k for k in range(1, 16)}, "pj", default=None)
        mid = [LE(C(1.0), j), LE(j, C(15.0))]
        pj1 = self.sp([mid + [pj], [LE(C(1.0), j, True), C(1.0)], [LE(j, C(15.0), True), C(1.0)]], hint="pj1")
        q0 = self.floor_nonneg(self.sp([mid + [M, {"fn": "inv", "a": pj1}]], hint="q0"))
        r0 = self.sp([[M], [C(-1.0), q0, pj1]], hint="r0")
        q = self.sp([[q0], [LE(C(0.0), r0, True), C(-1.0)], [LE(pj1, r0), C(1.0)]], hint="q")
        rem = self.sp([[M], [C(-1.0), q, pj1]], hint="rm")
        # j >= 16: q = 0, rem = M
        far = LE(C(16.0), j)
        q = self.sp([mid + [q]], hint="qm")
        rem = self.sp([mid + [rem], [far, M]], hint="rm2")
        halfj = self.sp([mid + [pj1, C(0.5)], [far, C(5e15)]], hint="hj")      # 10^j / 2 (j >= 16: > any M)
        if mode == "round":
            inc = self.sp([[LE(halfj, rem)]], hint="inc")
        elif mode == "down":
            inc = C(0.0)
        else:
            inc = self.sp([[LE(rem, C(0.0), True)]], hint="inc")
        N = self.sp([[q], [inc]], hint="N")
        v_mid = self.divide(N, C(10.0 ** d), [LE(C(1.0), j)]) if d > 0 else self.sp([[LE(C(1.0), j), N]], hint="vm")
        v = self.sp([[nolow, LE(C(14.0), E), v_hi], [nolow, LE(C(14.0), E, True), v_lo], [LE(C(1.0), j), v_mid]], hint="v")
        r = self.sp([[EQ(neg, C(1.0), True), v], [EQ(neg, C(1.0)), C(-1.0), v]], hint="rx")
        self.notes["ROUND method A: exact 15-digit decimal model"] += 1
        return r

    def _round(self, args, mode):
        if self.mode8 != "A":
            return K.Builder._round(self, args, mode)
        d = self._digits(args)
        if d < 0 or d > 22:
            raise K.Unsupported("ROUND method A: digits outside 0..22")
        x, ef, ec = self.to_num(self.val(args[0]))
        r = self.round_exact(self.sp([[EQ(ef, C(1.0), True), x]], hint="xr"), d, mode)
        return self.num_or_err(self.sp([[EQ(ef, C(1.0), True), r]], hint="rr"), ef, ec, d <= 0)


# ============================================================================================================
# Part 2: x^a (non-integer constant a) and log10 x
#   reduction (exact): x = 2^e f, e from the binary-lattice knot spectrum sum_k [2^k <= x], f = x 2^-e in
#   [0.6875, 1.4375) (one more halving when f >= 1.4375); 48 pieces of width 1/64, t = (f - c_i) 128 in [-1, 1]
#   (exact, Sterbenz). On every piece a polynomial in t of degree DEG interpolates
#       g(f) = f^a                         (power)
#       Q(f) = log10(f) / (f - 1)          (log10, Q(1) = 1/ln 10; keeps the RELATIVE accuracy near x = 1)
#   at Chebyshev-like nodes, coefficients computed once in 60-digit decimal arithmetic (coefficients of the
#   representation, like the constants of the formula) and stored as double-double constants.
#   Method A evaluates the polynomial in double-double (Horner, error-free transformations) and returns the
#   correctly rounded double only when it is CERTIFIED (|lo| + error bound < distance to the rounding
#   boundary); otherwise the result is a flag (missing). Method B evaluates in plain double (Horner).
# ============================================================================================================
import decimal as _dec
from decimal import Decimal as _D

_dec.getcontext().prec = 60
PIECES, P_LO, P_W = 48, 0.6875, 1.0 / 64
DEG_A, DEG_B = 13, 10
ERR_A = 2.0 ** -90            # bound used to certify the rounding (approximation + double-double arithmetic)


def _nodes(n):
    return [math.cos(math.pi * (j + 0.5) / (n + 1)) for j in range(n + 1)]


def _solve(A, b):
    n = len(b)
    M = [row[:] + [bb] for row, bb in zip(A, b)]
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(M[r][i]))
        M[i], M[p] = M[p], M[i]
        for r in range(i + 1, n):
            f = M[r][i] / M[i][i]
            for c in range(i, n + 1):
                M[r][c] -= f * M[i][c]
    x = [_D(0)] * n
    for i in range(n - 1, -1, -1):
        x[i] = (M[i][n] - sum(M[i][c] * x[c] for c in range(i + 1, n))) / M[i][i]
    return x


def fit_piece(fn, i, deg):
    """Monomial coefficients (in t) of the polynomial interpolating fn on piece i at Chebyshev-like nodes."""
    c = _D(P_LO) + (_D(i) + _D("0.5")) * _D(P_W)
    h = _D(P_W) / 2
    ts = [_D(t) for t in _nodes(deg)]
    A = [[t ** k for k in range(deg + 1)] for t in ts]
    b = [fn(c + h * t) for t in ts]
    return _solve(A, b)


def fn_pow(a):
    da = _D(a)
    return lambda f: (da * f.ln()).exp()


def fn_q():
    ln10 = _D(10).ln()
    return lambda f: (1 / ln10) if f == 1 else f.log10() / (f - 1)


_COEF_CACHE = {}


def coefficients(kind, a, deg):
    key = (kind, a, deg)
    if key not in _COEF_CACHE:
        fn = fn_pow(a) if kind == "pow" else fn_q()
        _COEF_CACHE[key] = [fit_piece(fn, i, deg) for i in range(PIECES)]
    return _COEF_CACHE[key]


BIN_ALL = range(-1074, 1024)


class Exact8Pow(Exact8):
    def bin_reduce(self, ax):
        """(e, f) with ax = 2^e f exactly, f in [0.6875, 1.4375); ax > 0 (rows with ax <= 0 give e = f = 0)."""
        e = self.sp([[LE(C(2.0 ** k), ax)] for k in BIN_ALL] + [[C(-1075.0)]], hint="e2")
        terms = []
        for k in BIN_ALL:
            m = [EQ(e, C(float(k)))]
            if k >= -1022:
                terms.append(m + [ax, C(2.0 ** -k)])
            else:
                terms.append(m + [ax, C(2.0 ** 600), C(2.0 ** (-k - 600))])
        f = self.sp(terms, hint="f2")
        hi = LE(C(1.4375), f)
        f = self.sp([[LE(C(1.4375), f, True), f], [hi, f, C(0.5)]], hint="f3")
        e = self.sp([[e], [hi, C(1.0)]], hint="e3")
        self.notes["knot spectrum: binary lattice sum_k [2^k <= x] (exact 2^e f reduction)"] += 1
        return e, f

    def piece(self, f):
        i = self.sp([[LE(C(P_LO + k * P_W), f)] for k in range(1, PIECES)], hint="pc")
        cc = self.sel(i, {k: P_LO + (k + 0.5) * P_W for k in range(PIECES)}, "pcc")
        t = self.sp([[self.sub(f, cc, "fc"), C(128.0)]], hint="t")          # exact
        self.notes["knot spectrum: interval form (48 pieces) of the mantissa"] += 1
        return i, t

    def poly_dd(self, coefs, i, t):
        deg = len(coefs[0]) - 1
        cs = []
        for k in range(deg + 1):
            hl = [dd_const(Fraction(str(coefs[p][k]))) for p in range(PIECES)]
            ch = self.sel(i, {p: hl[p][0] for p in range(PIECES)}, "ch")
            cl = self.sel(i, {p: hl[p][1] for p in range(PIECES)}, "cl")
            cs.append((ch, cl))
        acc = cs[deg]
        for k in range(deg - 1, -1, -1):
            acc = self.dd_add(self.dd_mul_d(acc, t), cs[k])
        return acc

    def poly_d(self, coefs, i, t):
        deg = len(coefs[0]) - 1
        cs = [self.sel(i, {p: float(coefs[p][k]) for p in range(PIECES)}, "cb") for k in range(deg + 1)]
        acc = cs[deg]
        for k in range(deg - 1, -1, -1):
            acc = self.sp([[acc, t], [cs[k]]], hint="hb")
        return acc

    def certify(self, yh, yl):
        """Correct rounding is certain when |yl| + ERR_A |yh| < half the gap to the neighbouring double on the
        side of yl (a quarter ulp below a power of two)."""
        ay = self.absv(yh, "cay")
        u = self.ulp_full(yh)
        p2 = self.sp([[EQ(self.sp([[u, C(2.0 ** 52)]], hint="u52"), ay)]], hint="p2")      # |yh| is a power of two
        toward0 = self.sp([[LE(C(0.0), yh), LE(C(0.0), yl, True)], [LE(C(0.0), yh, True), LE(C(0.0), yl)]], hint="t0")
        lim = self.sp([[EQ(p2, C(1.0)), EQ(toward0, C(1.0)), u, C(0.25)], [EQ(p2, C(1.0)), EQ(toward0, C(1.0), True), u, C(0.5)],
                       [EQ(p2, C(1.0), True), u, C(0.5)], [C(-ERR_A), ay]], hint="lim")
        inr = [LE(C(2.0 ** -1000), ay), LE(ay, C(2.0 ** 1000))]
        ok = self.sp([inr + [LE(lim, self.absv(yl, "al"), True)], [EQ(yh, C(0.0)), EQ(yl, C(0.0))]], hint="ok")   # lim > |yl|, or exactly 0
        bad = self.sp([[EQ(ok, C(1.0), True)]], hint="ncert")
        self.notes["method A: certified correct rounding (double-double, bound 2^-90)"] += 1
        return bad

    def pow_core(self, ax, a):
        e, f = self.bin_reduce(ax)
        i, t = self.piece(f)
        if self.mode8 == "A":
            g = self.poly_dd(coefficients("pow", a, DEG_A), i, t)
            ks = [k for k in range(-1075, 1025) if abs(k * a) <= 1000]           # 2^(k a) stays far inside the range
            self.flag(self.sp([[EQ(self.cert_mask, C(1.0)), EQ(self.sp([[EQ(e, C(float(k)))] for k in ks], hint="ein"), C(1.0), True)]], hint="pr"))
            tab = {k: dd_const(_frac_pow2(k, a)) for k in ks}
            th = self.sel(e, {k: v[0] for k, v in tab.items()}, "th")
            tl = self.sel(e, {k: v[1] for k, v in tab.items()}, "tl")
            yh, yl = self.dd_mul((th, tl), g)
            self.flag(self.sp([[EQ(self.cert_mask, C(1.0)), self.certify(yh, yl)]], hint="pf"))
            return yh
        g = self.poly_d(coefficients("pow", a, DEG_B), i, t)
        ks = [k for k in range(-1075, 1025) if abs(k * a) <= 1000]
        self.flag(self.sp([[EQ(self.cert_mask, C(1.0)), EQ(self.sp([[EQ(e, C(float(k)))] for k in ks], hint="ein"), C(1.0), True)]], hint="pr"))
        tab = {k: float(_frac_pow2(k, a)) for k in ks}
        th = self.sel(e, tab, "th")
        return self.mul(th, g, "pw")

    def log10_core(self, ax):
        e, f = self.bin_reduce(ax)
        i, t = self.piece(f)
        u = self.sub(f, C(1.0), "u")                                        # exact (Sterbenz)
        L2h, L2l = dd_const(Fraction(str(_D(2).log10())))
        if self.mode8 == "A":
            q = self.poly_dd(coefficients("q", None, DEG_A), i, t)
            r = self.dd_mul_d(q, u)
            p, pe = self.two_prod(e, C(L2h))
            pe = self.sp([[pe], [e, C(L2l)]], hint="pe")
            el = self.fast_two_sum(p, pe)
            yh, yl = self.dd_add(el, r)
            self.flag(self.sp([[EQ(self.cert_mask, C(1.0)), self.certify(yh, yl)]], hint="lf"))
            return yh
        q = self.poly_d(coefficients("q", None, DEG_B), i, t)
        return self.sp([[e, C(L2h)], [u, q]], hint="lg")

    # ---- the Excel functions --------------------------------------------------------------------------------
    def arith(self, op, av, bv, node=None):
        if op == "^" and node is not None and not self.has_cell(node[3]) and bv.types == {T1} and isc(bv.op("n")):
            m = bv.op("n")["const"]
            if m != int(m):
                a, ea, ca = self.to_num(av)
                neg = self.sp([[EQ(ea, C(1.0), True), LE(C(0.0), a, True)]], hint="ng")
                zero_neg = self.sp([[EQ(ea, C(1.0), True), EQ(a, C(0.0))]], hint="zr") if m < 0 else C(0)
                ef, ec = self.first_error([(ea, ca), (neg, C(E_NUM)), (zero_neg, C(E_NUM))])
                ax = self.sp([[EQ(ef, C(1.0), True), LE(a, C(0.0), True), a], [LE(a, C(0.0)), C(1.0)], [EQ(ef, C(1.0)), C(1.0)]], hint="pa")
                self.cert_mask = self.sp([[EQ(ef, C(1.0), True), LE(a, C(0.0), True)]], hint="cm")
                y = self.pow_core(ax, m)
                r = self.sp([[EQ(ef, C(1.0), True), LE(a, C(0.0), True), y]], hint="pw")
                self.notes["x^a (a not an integer), method %s" % self.mode8] += 1
                return self.num_or_err(r, ef, ec)
        return K.Builder.arith(self, op, av, bv, node)

    def f_LOG10(self, args):
        x, ef, ec = self.to_num(self.val(args[0]))
        bad = self.sp([[EQ(ef, C(1.0), True), LE(x, C(0.0))]], hint="nb")
        ef2, ec2 = self.first_error([(ef, ec), (bad, C(E_NUM))])
        ax = self.sp([[EQ(ef2, C(1.0), True), x], [EQ(ef2, C(1.0)), C(1.0)]], hint="lx")
        self.cert_mask = self.sp([[EQ(ef2, C(1.0), True)]], hint="cm")
        y = self.log10_core(ax)
        self.notes["log10, method %s" % self.mode8] += 1
        return self.num_or_err(self.sp([[EQ(ef2, C(1.0), True), y]], hint="lg"), ef2, ec2)


def _frac_pow2(k, a):
    """2^(k a) as an exact-enough Fraction (from 60-digit decimal)."""
    v = (_D(k) * _D(a) * _D(2).ln()).exp()
    return Fraction(str(v))


# ============================================================================================================
# Part 3: texts as index sets of characters
#   A text value is a set of rows (instance, position, code point, valid) spread over "segments" (child tables
#   of G): characters of a text cell (data layout: lexical decomposition, like tstudy.index.tokenise), the
#   characters of a number formatted by Excel's general format (24 slots per instance, computed in the engine
#   from the exact 15-digit mantissa), constant texts, TRUE/FALSE. Concatenation shifts positions by the
#   lengths of the preceding operands (grouped sums) - nothing outside sp/match.
#   Character properties (lower case, collation key, digit value, white space, full-width translation) come
#   from a constant table over the Basic Multilingual Plane (Unicode / cp932 standards; data independent).
# ============================================================================================================
import unicodedata as _ud

NF_SLOTS = 24
CH_DOT, CH_MINUS, CH_PLUS, CH_E, CH_ZERO = 46.0, 45.0, 43.0, 69.0, 48.0
_FW = {0xFF10 + d: 0x30 + d for d in range(10)}
_FW.update({0xFF0E: 0x2E, 0xFF0C: 0x2C, 0xFF0D: 0x2D, 0xFF0B: 0x2B, 0xFF05: 0x25})


def _key6(ch):
    """6-byte left-aligned collation key of one character as excel_ref.text_order encodes it (of ch.lower())."""
    b = b""
    for c in ch.lower():
        try:
            b += c.encode("cp932")
        except UnicodeEncodeError:
            b += b"\xff\xff" + c.encode("utf-16-be")
    if len(b) > 6:
        return -1.0
    v = 0
    for i in range(6):
        v = v * 256 + (b[i] if i < len(b) else 0)
    return float(v)


def fallback_key(cp):
    """Key of a character that is not in cp932 and is its own lower case: ff ff + UTF-16BE."""
    if cp < 0x10000:
        return float(0xFFFF * 2 ** 32 + cp * 2 ** 16)
    hi, lo = 0xD800 + ((cp - 0x10000) >> 10), 0xDC00 + ((cp - 0x10000) & 0x3FF)
    return float(0xFFFF * 2 ** 32 + hi * 2 ** 16 + lo)


_CPROP = None
ORDER_BAD = (0x130, 0xF8F3, 0x3A3)      # multi-character lower case / prefix of the fallback / context-dependent lower case


def char_props():
    """Sparse constant table (Unicode / cp932 / Python sre case folding; data independent): one row for every
    code point whose properties differ from the DEFAULTS that the steps compute themselves
    (cased 0, group of the lower case = the code point, fallback collation key, no white space, no digit).
    Columns: cp, cased (sre: lower != c or upper != c), gidl (representative of the sre case-folding group of
    the simple lower case), key (collation key of str.lower()), obad (order comparisons not certified),
    spc (str.isspace), dig (decimal digit value, -1), tr (translation of full-width . , - + %)."""
    global _CPROP
    if _CPROP is None:
        import _sre
        import re._casefix as _cf
        rep = {}
        for a, others in _cf._EXTRA_CASES.items():
            g = (a,) + tuple(others)
            m = min(g)
            for x in g:
                rep[x] = min(rep.get(x, m), m)
        cols = {k: [] for k in ("cp", "cased", "gidl", "key", "obad", "spc", "dig", "tr")}
        for cp in range(0x110000):
            if 0xD800 <= cp < 0xE000:
                continue
            ch = chr(cp)
            low = _sre.unicode_tolower(cp)
            cased = _sre.unicode_iscased(cp)
            try:
                ch.encode("cp932")
                enc = True
            except UnicodeEncodeError:
                enc = False
            d = _ud.decimal(ch, -1)
            sp_ = ch.isspace()
            special = cp in rep or low in rep or cp in _FW or cp in ORDER_BAD
            if not (enc or cased or low != cp or sp_ or d >= 0 or special):
                continue
            cols["cp"].append(cp)
            cols["cased"].append(1.0 if cased else 0.0)
            cols["gidl"].append(float(rep.get(low, low)))
            k = _key6(ch)
            cols["key"].append(k)
            cols["obad"].append(1.0 if (cp in ORDER_BAD or k < 0) else 0.0)
            cols["spc"].append(1.0 if sp_ else 0.0)
            cols["dig"].append(float(d))
            cols["tr"].append(float(_FW.get(cp, cp)))
        _CPROP = {k: np.array(v, dtype=float) for k, v in cols.items()}
    return _CPROP


class TXV(V):
    """A text value as character segments (only produced by '&' in the research builder)."""
    __slots__ = ("tx",)


class Exact8All(Exact8Pow):

    # ---- data layout: the characters of text cells -------------------------------------------------------
    def fill(self, rec, src):
        if rec[0] == "chars":
            _, table, sheet, rr, cc, bad = rec
            par, pos, code = [], [], []
            keys = (np.asarray(rr, dtype=np.int64) * K.KEY_SHIFT + np.asarray(cc, dtype=np.int64)).tolist()
            for i, k in enumerate(keys):
                if bad[i]:
                    continue
                v = src.raw(sheet, k)
                if isinstance(v, str):
                    for j, ch in enumerate(v):
                        par.append(i); pos.append(j); code.append(ord(ch))
            self.table(table, {"_parent": par, "pos": pos, "code": code, "valid": np.ones(len(par))})
            return
        return K.Builder.fill(self, rec, src)

    def apply_case(self, src):
        undo = K.Builder.apply_case(self, src)
        for rec in self.recipes:
            if rec[0] == "chars" and rec[2].sid in src.ck:
                undo.append(("W", rec[1], dict(self.tabs.data[rec[1]]), self.tabs.rows[rec[1]]))
                self.fill(rec, src)
        return undo

    def floor_t(self, x, table, bits):
        """floor(x) for 0 <= x < 2^(bits-1) in any table (integer-lattice knot spectrum, dyadic bisection)."""
        r = self.sp([[x]], table=table, hint="fr")
        for j in range(bits - 2, -1, -1):
            p = float(2 ** j)
            r = self.sp([[r], [LE(C(p), r), C(-p)]], table=table, hint="fb")
        return self.sp([[x], [C(-1.0), r]], table=table, hint="fl")

    def cprop_table(self):
        if "CP" not in self.tabs.rows:
            self.table("CP", char_props())
        return "CP"

    def props(self, table, code, want=("cased", "gidl", "key", "obad", "spc", "dig", "tr")):
        """Character properties of the rows of `table` (code column): a match into the sparse constant table;
        a code point without a row has the default properties, computed here."""
        cp = self.cprop_table()
        m = self.match([code], cp, ["cp"], table=table, hint="cpm")
        hit, miss = PRESENT(m), PRESENT(m, True)
        out = {}
        for k in want:
            t = [[hit, {"col": k, "via": m}]]
            if k in ("gidl", "tr"):
                t.append([miss, code])
            elif k == "dig":
                t.append([miss, C(-1.0)])
            elif k == "key":
                # fallback key ff ff + UTF-16BE of the code point itself
                bmp = LE(code, C(65535.0))
                hi = self.floor_t(self.sp([[miss, LE(code, C(65535.0), True), code, C(1.0 / 1024)],
                                           [miss, LE(code, C(65535.0), True), C(-65536.0 / 1024)]], table=table, hint="khi"), table, 12)
                t += [[miss, bmp, C(float(0xFFFF * 2 ** 32))], [miss, bmp, code, C(65536.0)],
                      [miss, LE(code, C(65535.0), True), C(float(0xFFFF * 2 ** 32 + 0xD800 * 65536 + 0xDC00 - 65536))],
                      [miss, LE(code, C(65535.0), True), hi, C(65536.0 - 1024.0)], [miss, LE(code, C(65535.0), True), code]]
            out[k] = self.sp(t, table=table, hint="p" + k)
        self.notes["sparse constant character-property table (Unicode / cp932 / sre case folding), match"] += 1
        return out

    # ---- segments ---------------------------------------------------------------------------------------------
    def seg_cell_text(self, node):
        x = self.make_ref(node)
        if not isinstance(x, K.RefS) or not x.single:
            raise K.Unsupported("text operand that is not a single cell")
        name = "G.ch%d" % (self.k + 1)
        self.k += 1
        rec = ("chars", name, x.sheet, np.where(x.bad > 0, 1, x.r1), np.where(x.bad > 0, 1, x.c1), x.bad.copy())
        self.recipes.append(rec)
        self.fill(rec, self.cache)
        return name, x

    def seg_const(self, text, mask=None):
        """Constant characters: n * len(text) rows; `mask` (a G operand) makes them valid only where 1."""
        name = "G.cs%d" % (self.k + 1)
        self.k += 1
        n, L = self.n, len(text)
        self.table(name, {"_parent": np.repeat(np.arange(n), L), "pos": np.tile(np.arange(L), n),
                          "code": np.tile(np.array([ord(c) for c in text], dtype=float), n)})
        valid = self.sp([[{"col": mask, "via": "_parent"}]] if mask is not None and not isc(mask) else [[C(1.0)]], table=name, hint="cv") \
            if mask is None or not isc(mask) else C(float(mask["const"]))
        return name, "pos", "code", valid

    def seg_len(self, seg):
        table, pos, code, valid = seg
        return self.sp([[valid]], table=table, group={"by": "_parent"}, hint="sl")

    def number_text(self, x, mask):
        """The characters of Excel's general format of the number x (as excel_ref.num_text): a slot table with
        NF_SLOTS rows per instance; valid where `mask` = 1 and the slot is inside the text."""
        neg, M, E, bad = self.mant15(x)
        self.flag(self.sp([[EQ(mask, C(1.0)), bad]], hint="nbad"))
        ax = self.absv(x, "nx")
        zero = self.sp([[EQ(ax, C(0.0))]], hint="z0")
        # digits D_1..D_15 of M: q_j = floor(M / 10^j)
        qs = [M] + [self.floor_exact_div(M, j) for j in range(1, 15)] + [C(0.0)]
        dname = "G.dg%d" % (self.k + 1)
        self.k += 1
        self.table(dname, {"_parent": np.repeat(np.arange(self.n), 15), "i": np.tile(np.arange(1, 16), self.n)})
        terms = []
        for i in range(1, 16):
            hi_, lo_ = qs[15 - i], qs[16 - i]
            terms.append([EQ("i", C(float(i))), hi_ if isc(hi_) else {"col": hi_, "via": "_parent"}])
            if not isc(lo_):
                terms.append([EQ("i", C(float(i))), C(-10.0), {"col": lo_, "via": "_parent"}])
        D = self.sp(terms, table=dname, hint="D")
        # trailing zeros of M: tz = #{j = 1..14 : 10^j divides M} = #{j : q_j 10^j = M} (exact integer products)
        zt = [[EQ(self.sp([[qs[j], C(10.0 ** j)]], hint="qp"), M)] for j in range(1, 15)]
        tz = self.sp(zt, hint="tz")
        ksig = self.sp([[C(15.0)], [C(-1.0), tz]], hint="ks")
        # layout quantities
        fixed_pos = self.sp([[LE(C(0.0), E), LE(E, C(14.0))]], hint="fp")
        fixed_neg = self.sp([[LE(C(-4.0), E), LE(E, C(-1.0))]], hint="fn")
        sci = self.sp([[EQ(fixed_pos, C(0.0)), EQ(fixed_neg, C(0.0))]], hint="sci")
        ni = self.sp([[E], [C(1.0)]], hint="ni")
        # fraction digits max(0, k - ni); an integral x < 1e15 has k <= ni (its digits are exact), so the
        # str(int(x)) branch of the general format needs no separate case
        nf = self.sp([[LE(ksig, ni, True), ksig], [LE(ksig, ni, True), C(-1.0), ni]], hint="nf")
        zz = self.sp([[C(-1.0), E], [C(-1.0)]], hint="zz")                     # zeros after "0." (fixed, E < 0)
        aE = self.absv(E, "aE")
        e3 = self.sp([[LE(C(100.0), aE)]], hint="e3")                          # three exponent digits
        ed1 = self.floor_exact_div(aE, 2)
        ed12 = self.floor_exact_div(aE, 1)
        ed2 = self.sp([[ed12], [C(-10.0), ed1]], hint="ed2")
        ed3 = self.sp([[aE], [C(-10.0), ed12]], hint="ed3")
        mant_len = self.sp([[C(1.0)], [LE(C(2.0), ksig), ksig]], hint="ml")    # "D1" or "D1.D2..Dk"
        length = self.sp([[neg],
                          [EQ(zero, C(1.0)), C(1.0)],
                          [EQ(zero, C(0.0)), EQ(fixed_pos, C(1.0)), ni], [EQ(zero, C(0.0)), EQ(fixed_pos, C(1.0)), LE(C(1.0), nf), C(1.0)],
                          [EQ(zero, C(0.0)), EQ(fixed_pos, C(1.0)), nf],
                          [EQ(zero, C(0.0)), EQ(fixed_neg, C(1.0)), C(2.0)], [EQ(zero, C(0.0)), EQ(fixed_neg, C(1.0)), zz],
                          [EQ(zero, C(0.0)), EQ(fixed_neg, C(1.0)), ksig],
                          [EQ(zero, C(0.0)), EQ(sci, C(1.0)), mant_len], [EQ(zero, C(0.0)), EQ(sci, C(1.0)), C(4.0)],
                          [EQ(zero, C(0.0)), EQ(sci, C(1.0)), e3]], hint="len")
        # slot table
        sname = "G.nf%d" % (self.k + 1)
        self.k += 1
        self.table(sname, {"_parent": np.repeat(np.arange(self.n), NF_SLOTS), "s": np.tile(np.arange(NF_SLOTS), self.n)})
        g = lambda col: col if isc(col) else {"col": col, "via": "_parent"}
        q = self.sp([["s"], [C(-1.0), g(neg)]], table=sname, hint="q")
        Z, FP, FN, SC = g(zero), g(fixed_pos), g(fixed_neg), g(sci)
        NI, NF, ZZ, KS, ML = g(ni), g(nf), g(zz), g(ksig), g(mant_len)
        nz = EQ(Z, C(0.0))
        # digit index (1-based) for digit cases
        c_fp_int = [nz, EQ(FP, C(1.0)), LE(C(0.0), q), LE(NI, q, True)]                       # q < ni
        c_fp_dot = [nz, EQ(FP, C(1.0)), EQ(q, NI), LE(C(1.0), NF)]
        c_fp_frac = [nz, EQ(FP, C(1.0)), LE(NI, q, True) if False else LE(q, NI, True), LE(q, self.sp([[NI], [NF]], table=sname, hint="nn"))]
        c_fn_0 = [nz, EQ(FN, C(1.0)), EQ(q, C(0.0))]
        c_fn_dot = [nz, EQ(FN, C(1.0)), EQ(q, C(1.0))]
        zend = self.sp([[C(2.0)], [ZZ]], table=sname, hint="ze")
        c_fn_z = [nz, EQ(FN, C(1.0)), LE(C(2.0), q), LE(zend, q, True)]
        c_fn_d = [nz, EQ(FN, C(1.0)), LE(zend, q), LE(self.sp([[zend], [KS]], table=sname, hint="zk"), q, True)]
        c_sc_d1 = [nz, EQ(SC, C(1.0)), EQ(q, C(0.0))]
        c_sc_dot = [nz, EQ(SC, C(1.0)), EQ(q, C(1.0)), LE(C(2.0), KS)]
        c_sc_dd = [nz, EQ(SC, C(1.0)), LE(C(2.0), q), LE(q, KS), LE(C(2.0), KS)]
        c_sc_E = [nz, EQ(SC, C(1.0)), EQ(q, ML)]
        c_sc_sg = [nz, EQ(SC, C(1.0)), EQ(q, self.sp([[ML], [C(1.0)]], table=sname, hint="m1"))]
        x1 = self.sp([[ML], [C(2.0)]], table=sname, hint="x1")
        G3 = g(e3)
        c_sc_x1 = [nz, EQ(SC, C(1.0)), EQ(q, x1), EQ(G3, C(1.0))]                              # hundreds digit
        c_sc_x2 = [nz, EQ(SC, C(1.0)), EQ(q, self.sp([[x1], [G3]], table=sname, hint="x2"))]
        c_sc_x3 = [nz, EQ(SC, C(1.0)), EQ(q, self.sp([[x1], [G3], [C(1.0)]], table=sname, hint="x3"))]
        idx = self.sp([c_fp_int + [q], c_fp_int + [C(1.0)], c_fp_frac + [q], c_fn_d + [q], c_fn_d + [C(-1.0)], c_fn_d + [C(-1.0), ZZ],
                       c_sc_d1 + [C(1.0)], c_sc_dd + [q]], table=sname, hint="ix")
        dm = self.match(["_parent", idx], dname, ["_parent", "i"], table=sname, hint="dm")
        dval = self.sp([[PRESENT(dm), {"col": D, "via": dm}]], table=sname, hint="dv")
        isdig = c_fp_int, c_fp_frac, c_fn_d, c_sc_d1, c_sc_dd
        code = self.sp([[EQ(q, C(-1.0)), C(CH_MINUS)]] +
                       [t + [C(CH_ZERO)] for t in isdig] + [t + [dval] for t in isdig] +
                       [c_fp_dot + [C(CH_DOT)], c_fn_0 + [C(CH_ZERO)], c_fn_dot + [C(CH_DOT)], c_fn_z + [C(CH_ZERO)],
                        c_sc_dot + [C(CH_DOT)], c_sc_E + [C(CH_E)],
                        c_sc_sg + [LE(C(0.0), g(E)), C(CH_PLUS)], c_sc_sg + [LE(C(0.0), g(E), True), C(CH_MINUS)],
                        c_sc_x1 + [C(CH_ZERO)], c_sc_x1 + [g(ed1)], c_sc_x2 + [C(CH_ZERO)], c_sc_x2 + [g(ed2)],
                        c_sc_x3 + [C(CH_ZERO)], c_sc_x3 + [g(ed3)],
                        [EQ(Z, C(1.0)), EQ("s", C(0.0)), C(CH_ZERO)]], table=sname, hint="cd")
        valid = self.sp([[LE("s", g(length), True) if False else LE(g(length), "s", True), EQ(g(mask), C(1.0)) if not isc(mask) else C(float(mask["const"]))]],
                        table=sname, hint="vd")
        self.notes["number formatting (general format, 15 digits) as a slot index set"] += 1
        return (sname, "s", code, valid)

    def to_text_segs(self, node):
        """Segments of to_text(operand) and the error pair of the operand."""
        k = node[0]
        if k == "const":
            v = node[1]
            if isinstance(v, K.Err):
                return [], (C(1.0), C(float(v.code)))
            if isinstance(v, bool):
                return [self.seg_const("TRUE" if v else "FALSE")], (C(0.0), C(0.0))
            if isinstance(v, float):
                return [self.number_text(C(v), C(1.0))], (C(0.0), C(0.0))
            return ([self.seg_const(v)] if v else []), (C(0.0), C(0.0))
        if k == "R":
            name, ref = self.seg_cell_text(node)
            v = self.scalar(ref)
            tv = v.op("t")
            isnum = self.sp([[EQ(tv, C(T1))]], hint="isn")
            segs = [(name, "pos", "code", "valid"),
                    self.number_text(self.sp([[EQ(tv, C(T1)), v.op("n")]], hint="nv"), isnum),
                    self.seg_const("TRUE", self.sp([[EQ(tv, C(T3)), EQ(v.op("n"), C(1.0))]], hint="bt")),
                    self.seg_const("FALSE", self.sp([[EQ(tv, C(T3)), EQ(v.op("n"), C(1.0), True)]], hint="bf"))]
            return segs, self.err_of(v)
        raise K.Unsupported("text operand that is neither a cell nor a constant")

    def concat_segs(self, parts):
        """parts: list of (segments, error pair). Returns (segments with output positions, length, error pair)."""
        out, offset = [], C(0.0)
        errs = []
        for segs, err in parts:
            errs.append(err)
            lens = []
            for seg in segs:
                table, pos, code, valid = seg
                opos = self.sp([[pos], [offset if isc(offset) else {"col": offset, "via": "_parent"}]], table=table, hint="op")
                out.append((table, opos, code, valid))
                lens.append(self.seg_len(seg))
            offset = self.sp([[offset]] + [[l] for l in lens], hint="of")
        ef, ec = self.first_error(errs)
        return out, offset, (ef, ec)

    def gate_flags(self, n0, ef):
        """Flags raised after position n0 matter only where the error flag ef is not 1 (an error result does not
        depend on the texts of the numbers)."""
        fl = self.__dict__.get("fail_flags", [])
        if isc(ef, 0.0) or len(fl) <= n0:
            return
        for i in range(n0, len(fl)):
            fl[i] = self.sp([[EQ(ef, C(1.0), True), fl[i]]], hint="gf")

    def binary(self, op, a, b):
        if op != "&" or self.mode8 not in ("A", "B"):
            return K.Builder.binary(self, op, a, b)
        raise RuntimeError("binary is not used")

    def ev(self, node):
        if node[0] == "bin" and node[1] == "&" and self.has_cell(node):
            parts = []
            def flat(n):
                if n[0] == "bin" and n[1] == "&":
                    flat(n[2]); flat(n[3])
                else:
                    parts.append(n)
            flat(node)
            nf0 = len(self.__dict__.get("fail_flags", []))
            segs, L, (ef, ec) = self.concat_segs([self.to_text_segs(p) for p in parts])
            self.gate_flags(nf0, ef)
            t = self.sp([[EQ(ef, C(1.0)), C(T4)], [EQ(ef, C(1.0), True), C(T2)]], hint="tt")
            v = TXV({"t": t, "e": self.sp([[EQ(ef, C(1.0)), ec]], hint="te")}, {T2, T4})
            v.tx = dict(segs=segs, L=L, ef=ef)
            self.notes["text concatenation as a union of character index sets"] += 1
            return v
        return K.Builder.ev(self, node)

    def finish(self, v):
        if isinstance(v, TXV):
            flags = self.__dict__.get("fail_flags", [])
            if flags:
                anyf = self.sp([[LE(C(1.0), self.sp([[f_] for f_ in flags], hint="nf"))]], hint="anyf")
                c = dict(v.c)
                c["t"] = self.sp([[EQ(anyf, C(1.0), True), v.op("t")], [EQ(anyf, C(1.0)), "_missing"]], hint="t")
                w = TXV(c, v.types)
                w.tx = v.tx
                return w
            return v
        return K.Builder.finish(self, v)

    def run(self, v, src=None, sd=None):
        if not isinstance(v, TXV):
            return K.Builder.run(self, v, src, sd)
        undo = None
        if src is not None:
            undo = self.apply_case(src) if isinstance(src, K.CaseSource) and src.base is self.cache else self.refresh(src)
        prog = self.program()
        from tstudy import msp
        eng = msp.Engine(self.tabs)
        try:
            eng.run(prog)
            tcol = eng.operand("G", v.c["t"]) if not isc(v.c["t"]) else None
            ecol = eng.operand("G", v.c["e"]) if not isc(v.c["e"]) else None
            chars = [[] for _ in range(self.n)]
            for table, opos, code, valid in v.tx["segs"]:
                par = eng.col(table, "_parent").v.astype(np.int64)
                P = eng.operand(table, opos) if not isc(opos) else None
                Cc = eng.operand(table, code) if not isc(code) else None
                Vv = eng.operand(table, valid) if not isc(valid) else None
                for r in range(len(par)):
                    ok = (Vv.v[r] if Vv is not None else valid["const"]) == 1.0
                    if ok and (Vv is None or Vv.m[r]):
                        chars[par[r]].append((P.v[r], int(Cc.v[r])))
        finally:
            if undo is not None:
                self.undo_case(undo)
        out = []
        for i in range(self.n):
            if tcol is not None and not tcol.m[i]:
                out.append("<missing>")
                continue
            t = tcol.v[i] if tcol is not None else v.c["t"]["const"]
            if t == T4:
                out.append(K.Err(int(ecol.v[i])))
                continue
            cs = sorted(chars[i])
            out.append("".join(chr(c) for _, c in cs))
        return out, prog, eng


# ============================================================================================================
# Part 4: SUMIF / COUNTIF whose criterion is built by concatenation (method A)
#   criterion text = union of its character segments (one index set); operator prefix from positions 0, 1;
#   the rest is matched against the text of every cell of the criteria range by a dynamic programme over
#   (instance x cell, text position j) with ONE transition per pattern position (fixed number of steps L_MAX):
#     literal  new[j] = old[j-1] [char equivalence (Python sre IGNORECASE: case-folding groups)]
#     '?'      new[j] = old[j-1]
#     '*'      new[j] = [j >= jmin], jmin = first j with old = 1 (FIRST MATCH in row order)
#     escape / beyond the end: new = old
#   order operators: first differing position (first match) of the collation keys, then the lengths.
#   The numeric and the empty-criterion branches are excluded STATICALLY when the last operand is a constant
#   text that cannot end a number (checked here; otherwise not compiled).
# ============================================================================================================
L_MAX = 255
K22 = 2.0 ** 22
OPS = {"EQ": 0.0, "NE": 1.0, "LT": 2.0, "GT": 3.0, "LE": 4.0, "GE": 5.0}


def _cannot_end_number(text):
    """True when every string ending with `text` is rejected by store.to_float_text and is not empty."""
    t = text.rstrip()
    if not t or t != text and not t:
        return False
    if len(t) != len(text):            # trailing white space would be stripped: decide on the stripped text
        pass
    c = t[-1]
    c = chr(_FW.get(ord(c), ord(c)))
    return not (c.isspace() or c == "%" or c == "." or _ud.decimal(c, -1) >= 0 or c.isdigit())


class Exact8Text(Exact8All):
    NL_DOLLAR = True          # reproduce the reference's regular-expression '$' (see _sumif)

    def fill(self, rec, src):
        kind = rec[0]
        if kind == "charsT":                       # characters of the cells of a range table (data layout)
            _, table, sheet, rr, cc = rec
            par, pos, code = [], [], []
            keys = (np.asarray(rr, dtype=np.int64) * K.KEY_SHIFT + np.asarray(cc, dtype=np.int64)).tolist()
            for i, k in enumerate(keys):
                v = src.raw(sheet, k)
                if isinstance(v, str):
                    for j, ch in enumerate(v):
                        par.append(i); pos.append(j); code.append(ord(ch))
            self.table(table, {"_parent": par, "pos": pos, "code": code})
            return
        if kind == "union":                        # one index set over the rows of several segment tables
            _, table, segs = rec
            par, cols = [], {"r%d" % s: [] for s in range(len(segs))}
            for s, name in enumerate(segs):
                p = self.tabs.data[name]["_parent"]
                par.extend(p.tolist())
                for s2 in range(len(segs)):
                    cols["r%d" % s2].extend(np.arange(len(p)).tolist() if s2 == s else [math.nan] * len(p))
            cols["_parent"] = par
            self.table(table, cols)
            return
        if kind == "dp":                           # (instance x cell, j = 0..len(text of the cell))
            _, table, ptab, chtab = rec
            pinst = self.tabs.data[ptab]["_parent"].astype(np.int64)
            py = self.tabs.data[ptab]["y"].astype(np.int64)
            chpar = self.tabs.data[chtab]["_parent"].astype(np.int64)
            first = {}
            for r_, p_ in enumerate(chpar.tolist()):
                first.setdefault(p_, r_)
            ln = np.bincount(chpar, minlength=int(py.max()) + 1 if len(py) else 0) if len(chpar) else np.zeros(int(py.max()) + 1 if len(py) else 0)
            par, jj, gg, cr = [], [], [], []
            for p_, (g_, y_) in enumerate(zip(pinst.tolist(), py.tolist())):
                L = int(ln[y_]) if y_ < len(ln) else 0
                for j in range(L + 1):
                    par.append(p_); jj.append(j); gg.append(g_)
                    cr.append(first[y_] + j - 1 if j >= 1 else math.nan)
            self.table(table, {"_parent": par, "j": jj, "g": gg, "cr": cr})
            return
        return Exact8All.fill(self, rec, src)

    def apply_case(self, src):
        undo = K.Builder.apply_case(self, src)
        touched = False
        for rec in self.recipes:
            if rec[0] in ("chars", "charsT") and rec[2].sid in src.ck:
                touched = True
            if rec[0] in ("chars", "charsT", "union", "dp") and touched:
                undo.append(("W", rec[1], dict(self.tabs.data[rec[1]]), self.tabs.rows[rec[1]]))
                self.fill(rec, src)
        return undo

    # ---- union of the criterion segments -------------------------------------------------------------
    def union(self, segs):
        name = "G.u%d" % (self.k + 1)
        self.k += 1
        rec = ("union", name, [s[0] for s in segs])
        self.recipes.append(rec)
        self.fill(rec, self.cache)
        cols = {"code": [], "pos": [], "valid": []}
        for s, (table, opos, code, valid) in enumerate(segs):
            m = self.match(["r%d" % s], table, ["_row"], table=name, hint="um")
            for key, o in (("code", code), ("pos", opos), ("valid", valid)):
                cols[key].append([PRESENT(m), o if isc(o) else {"col": o, "via": m}])
        out = {k: self.sp(v, table=name, hint="u" + k) for k, v in cols.items()}
        self.notes["union of character segments (one index set, match per segment)"] += 1
        return name, out

    def char_at(self, U, uc, pos_col, valid_col, i, hint="ca"):
        """(present, code, U-ref) of the character at position i (operand) of every instance."""
        m = self.match(["_row", i, C(1.0)], U, ["_parent", pos_col, valid_col], hint=hint)
        return m

    # ---- SUMIF with a text criterion -------------------------------------------------------------------
    def _sumif(self, args, count):
        a1 = args[1]
        if not (self.mode8 == "A" and a1[0] == "bin" and a1[1] == "&" and self.has_cell(a1)):
            return K.Builder._sumif(self, args, count)
        # static exclusion of the numeric / empty criterion branches
        last = a1
        while last[0] == "bin" and last[1] == "&":
            last = last[3]
        if not (last[0] == "const" and isinstance(last[1], str) and _cannot_end_number(last[1])):
            raise K.Unsupported("criterion by concatenation whose last operand is not a constant non-numeric text")
        x = self.ev(args[0])
        s = self.ev(args[2]) if not count and len(args) > 2 else x
        if not isinstance(x, K.RefS) or not isinstance(s, K.RefS):
            return self.errv(E_VALUE)
        extra = [("s.", s)] if not count else []
        R, Rc, gref, bad = self.range_tables(x, extra=extra, truncate=True, key=("sumif", count))
        if not count:
            bad = np.where(bad > 0, bad, s.bad)
        st, sn, se = ("s.t", "s.n", "s.e") if not count else ("t", "n", "e")
        bf, bc = self.static_bad(bad)
        cv = self.ev(a1)                                      # TXV: segments of the criterion text
        segs, Lc, cef = cv.tx["segs"], cv.tx["L"], cv.tx["ef"]
        U, uc = self.union(segs)
        upr = self.props(U, uc["code"], want=("cased", "gidl", "key", "obad"))
        # operator prefix
        c0m = self.char_at(U, uc, uc["pos"], uc["valid"], C(0.0), "c0")
        c1m = self.char_at(U, uc, uc["pos"], uc["valid"], C(1.0), "c1")
        c0 = self.sp([[PRESENT(c0m), {"col": uc["code"], "via": c0m}], [PRESENT(c0m, True), C(-1.0)]], hint="c0")
        c1 = self.sp([[PRESENT(c1m), {"col": uc["code"], "via": c1m}], [PRESENT(c1m, True), C(-1.0)]], hint="c1")
        lt, gt_, eq_ = 60.0, 62.0, 61.0
        op_terms = {  # (op code, oplen)
            "LE": [EQ(c0, C(lt)), EQ(c1, C(eq_))], "GE": [EQ(c0, C(gt_)), EQ(c1, C(eq_))], "NE": [EQ(c0, C(lt)), EQ(c1, C(gt_))],
            "LT": [EQ(c0, C(lt)), EQ(c1, C(eq_), True), EQ(c1, C(gt_), True)], "GT": [EQ(c0, C(gt_)), EQ(c1, C(eq_), True)],
            "EQ1": [EQ(c0, C(eq_))]}
        op = self.sp([t + [C(OPS[k if k != "EQ1" else "EQ"])] for k, t in op_terms.items() if OPS[k if k != "EQ1" else "EQ"] != 0.0], hint="op")
        oplen = self.sp([op_terms[k] + [C(2.0 if k in ("LE", "GE", "NE") else 1.0)] for k in op_terms], hint="ol")
        Lr = self.sp([[Lc], [C(-1.0), oplen]], hint="Lr")
        self.flag(self.sp([[EQ(cef, C(1.0), True), LE(C(float(L_MAX)), Lr), LE(Lr, C(float(L_MAX)), True)]], hint="lmx"))
        # rest positions
        rpos = self.sp([[uc["pos"]], [C(-1.0), {"col": oplen, "via": "_parent"}]], table=U, hint="rp")
        rval = self.sp([[EQ(uc["valid"], C(1.0)), LE(C(0.0), rpos)]], table=U, hint="rv")
        # pairs (instance x cell of the criteria range), as in the base compilation
        P = self.nm("G.x")
        par = self.tabs.data[Rc]["_parent"].astype(np.int64)
        ridv = self.memo[("rid", R)]
        byr = collections.defaultdict(list)
        for idx, g in enumerate(par):
            byr[g].append(idx)
        inst, cell = [], []
        for i in range(self.n):
            g = int(ridv[i]) if ridv[i] >= 0 else -1
            cs = byr.get(g, [])
            inst.append(np.full(len(cs), i)); cell.append(np.array(cs, dtype=np.int64))
        inst = np.concatenate(inst) if inst else np.zeros(0)
        cell = np.concatenate(cell) if cell else np.zeros(0)
        self.table(P, {"_parent": inst, "y": cell})
        ry = self.match(["y"], Rc, ["_row"], table=P, hint="ry")
        # characters of the criteria cells and the DP index set
        rec0 = [r for r in self.recipes if r[0] == "T" and r[1] == Rc and r[2] == ""][0]
        CH = Rc + ".ch"
        rec = ("charsT", CH, rec0[3], rec0[4], rec0[5])
        self.recipes.append(rec)
        self.fill(rec, self.cache)
        D = P + ".d"
        rec = ("dp", D, P, CH)
        self.recipes.append(rec)
        self.fill(rec, self.cache)
        cpr = self.props(CH, "code", want=("gidl", "key", "obad"))
        mcr = self.match(["cr"], CH, ["_row"], table=D, hint="mcr")
        tg = self.sp([[PRESENT(mcr), C(K22)], [PRESENT(mcr), {"col": cpr["gidl"], "via": mcr}]], table=D, hint="tg")
        te = self.sp([[PRESENT(mcr), C(2 * K22)], [PRESENT(mcr), {"col": "code", "via": mcr}]], table=D, hint="te")
        prev = self.match(["_parent", self.sp([["j"], [C(-1.0)]], table=D, hint="jm")], D, ["_parent", "j"], table=D, hint="pv")
        ylen = self.sp([[C(1.0)]], table=CH, group={"by": "_parent"}, hint="yl")          # length of every cell text
        plen = self.sp([[PRESENT(ry), {"col": ylen, "via": ry}]], table=P, hint="pl")
        # ---- the dynamic programme: one transition per pattern position
        old = self.sp([[EQ("j", C(0.0))]], table=D, hint="d0")
        esc = C(0.0)
        m_next = self.char_at(U, uc, rpos, rval, C(0.0), "rc")
        for i in range(L_MAX):
            m_i = m_next
            m_next = self.char_at(U, uc, rpos, rval, C(float(i + 1)), "rc")
            ci = self.sp([[PRESENT(m_i), {"col": uc["code"], "via": m_i}], [PRESENT(m_i, True), C(-1.0)]], hint="ci")
            cn = self.sp([[PRESENT(m_next), {"col": uc["code"], "via": m_next}], [PRESENT(m_next, True), C(-1.0)]], hint="cn")
            nesc = self.sp([[EQ(cn, C(42.0))], [EQ(cn, C(63.0))], [EQ(cn, C(126.0))]], hint="ne")
            e0 = EQ(esc, C(0.0)) if not isc(esc) else None
            base = [PRESENT(m_i)] + ([e0] if e0 else [])
            start = base + [EQ(ci, C(126.0)), EQ(nesc, C(1.0))]                 # '~' that escapes the next char
            star = base + [EQ(ci, C(42.0))]
            any1 = base + [EQ(ci, C(63.0))]
            lit_plain = base + [EQ(ci, C(42.0), True), EQ(ci, C(63.0), True), EQ(self.sp([start + [C(1.0)]], hint="st"), C(1.0), True)]
            lits = [lit_plain] + ([[PRESENT(m_i), EQ(esc, C(1.0))]] if not isc(esc) else [])
            cased = {"col": upr["cased"], "via": m_i}
            gidl = {"col": upr["gidl"], "via": m_i}
            pk = self.sp([t + [EQ(cased, C(1.0)), C(K22)] for t in lits] + [t + [EQ(cased, C(1.0)), gidl] for t in lits] +
                         [t + [EQ(cased, C(1.0), True), C(2 * K22)] for t in lits] + [t + [EQ(cased, C(1.0), True), ci] for t in lits] +
                         [any1 + [C(3 * K22)], star + [C(4 * K22)]], hint="pk")
            esc = self.sp([start + [C(1.0)]], hint="es")
            pkp = self.sp([[{"col": pk, "via": "_parent"}]], table=P, hint="pkp")
            fm = self.match(["_row", C(1.0)], D, ["_parent", old], table=P, hint="fm")
            jmin = self.sp([[PRESENT(fm), {"col": "j", "via": fm}], [PRESENT(fm, True), C(1e9)]], table=P, hint="jn")   # none: beyond any j
            pkd = {"col": pkp, "via": "_parent"}
            op_ = {"col": old, "via": prev}
            old = self.sp([[EQ(pkd, C(0.0)), old],
                           [PRESENT(prev), EQ(pkd, tg), op_], [PRESENT(prev), EQ(pkd, te), op_],
                           [PRESENT(prev), EQ(pkd, C(3 * K22)), op_],
                           [EQ(pkd, C(4 * K22)), LE({"col": jmin, "via": "_parent"}, "j")]],
                          table=D, hint="dp")
        fin = self.match(["_row", plen], D, ["_parent", "j"], table=P, hint="fin")
        wild = self.sp([[PRESENT(fin), {"col": old, "via": fin}]], table=P, hint="wm")
        if self.NL_DOLLAR:
            # the reference matches with Python's re: '$' also matches just before ONE final newline, so a cell
            # text t + "\n" matches when t does (reproduced here; a spreadsheet would most likely not do this)
            pl1 = self.sp([[plen], [C(-1.0)]], table=P, hint="pl1")
            fin1 = self.match(["_row", pl1], D, ["_parent", "j"], table=P, hint="fin1")
            lastc = self.match(["y", pl1], CH, ["_parent", "pos"], table=P, hint="lc")
            nl = self.sp([[PRESENT(lastc), EQ({"col": "code", "via": lastc}, C(10.0))]], table=P, hint="nl")
            wild = self.sp([[wild], [EQ(wild, C(1.0), True), EQ(nl, C(1.0)), PRESENT(fin1), EQ({"col": old, "via": fin1}, C(1.0))]],
                           table=P, hint="wm2")
        # ---- order comparison: first differing collation key, then the lengths
        mk = self.match(["g", self.sp([["j"], [C(-1.0)]], table=D, hint="jk"), C(1.0)], U, ["_parent", rpos, rval], table=D, hint="mk")
        kc = {"col": cpr["key"], "via": mcr}
        kp = {"col": upr["key"], "via": mk}
        cmp_ = self.sp([[PRESENT(mcr), PRESENT(mk), LE(kp, kc, True), C(-1.0)], [PRESENT(mcr), PRESENT(mk), LE(kc, kp, True), C(1.0)],
                        [PRESENT(mcr), PRESENT(mk, True), C(1.0)]], table=D, hint="cmp")
        nz = self.sp([[EQ(cmp_, C(0.0), True)]], table=D, hint="nz")
        fd = self.match(["_row", C(1.0)], D, ["_parent", nz], table=P, hint="fd")
        Lrp = {"col": Lr, "via": "_parent"}
        res = self.sp([[PRESENT(fd), {"col": cmp_, "via": fd}], [PRESENT(fd, True), LE(Lrp, plen, True), C(-1.0)],
                       [PRESENT(fd, True), LE(plen, Lrp, True), C(1.0)]], table=P, hint="res")
        # ---- hit of every pair
        opp = {"col": op, "via": "_parent"}
        ty = {"col": "t", "via": ry}
        txt = EQ(ty, C(T2))
        okc = EQ({"col": cef, "via": "_parent"}, C(1.0), True)
        hit = self.sp([[okc, EQ(opp, C(0.0)), txt, EQ(wild, C(1.0))],
                       [okc, EQ(opp, C(1.0))], [okc, EQ(opp, C(1.0)), txt, EQ(wild, C(1.0)), C(-1.0)],
                       [okc, EQ(opp, C(2.0)), txt, EQ(res, C(-1.0))], [okc, EQ(opp, C(3.0)), txt, EQ(res, C(1.0))],
                       [okc, EQ(opp, C(4.0)), txt, LE(res, C(0.0))], [okc, EQ(opp, C(5.0)), txt, LE(C(0.0), res)]], table=P, hint="hit")
        # flag: order operator, text cell, and a character of ORDER_BAD at or before the deciding position
        # (first differing position, or the end of the cell text when one text is a prefix of the other)
        jcut = self.sp([[PRESENT(fd), {"col": "j", "via": fd}], [PRESENT(fd, True), plen]], table=P, hint="jc")
        badr = self.sp([[PRESENT(mcr), EQ({"col": cpr["obad"], "via": mcr}, C(1.0))],
                        [PRESENT(mk), EQ({"col": upr["obad"], "via": mk}, C(1.0))]], table=D, hint="bdr")
        cntb = self.sp([[LE("j", {"col": jcut, "via": "_parent"}), badr]], table=D, group={"by": "_parent"}, hint="cb")
        fpair = self.sp([[okc, LE(C(2.0), opp), txt, LE(C(1.0), cntb)]], table=P, hint="fp")
        self.flag(self.sp([[LE(C(1.0), fpair)]], table=P, group={"by": "_parent"}, hint="fpg"))
        # ---- sums and errors (first matched error in cell order)
        sv = {"t": {"col": st, "via": ry}, "n": {"col": sn, "via": ry}, "e": {"col": se, "via": ry}}
        if count:
            tot = self.sp([[EQ(hit, C(1.0))]], table=P, group={"by": "_parent"}, hint="cnt")
            ef1, ec1 = C(0), C(0)
        else:
            tot = self.sp([[EQ(hit, C(1.0)), EQ(sv["t"], C(T1)), sv["n"]]], table=P, group={"by": "_parent"}, hint="sif")
            nerr = self.sp([[EQ(hit, C(1.0)), EQ(sv["t"], C(T4))]], table=P, group={"by": "_parent"}, hint="sne")
            isr = self.sp([[EQ(hit, C(1.0)), EQ(sv["t"], C(T4))]], table=P, hint="ise")
            fe = self.match(["_row", C(1.0)], P, ["_parent", isr], hint="sfe")
            fy = self.sp([[PRESENT(fe), {"col": "y", "via": fe}]], hint="fy")
            fr = self.match([fy], Rc, ["_row"], hint="fr")
            ec1 = self.sp([[PRESENT(fr), {"col": se, "via": fr}]], hint="ec")
            ef1 = self.sp([[LE(C(1.0), nerr)]], hint="ef")
        ef, ec = self.first_error([(bf, bc), (ef1, ec1)])
        r = self.sp([[EQ(ef, C(1.0), True), tot]], hint="sif")
        self.notes["SUMIF with a concatenated criterion: union, DP over pattern positions (first match), collation keys"] += 1
        return self.num_or_err(r, ef, ec, count)


# ============================================================================================================
# Part 5: VALUE(LEFT(x, n)) (method A)
#   text of x = character segments (cell text, general-format number, TRUE/FALSE); LEFT keeps positions < n;
#   VALUE = store.to_float_text as a deterministic finite automaton over the n positions (one masked
#   sum-product per position: sum over (state, class) of [state = s][class = c] T(s, c)), with the
#   accumulation of the mantissa digits N, the fraction digits f and the exponent; the value
#   N 10^(e - f) is formed with ONE correctly rounded IEEE operation (product or correctly rounded
#   division by an exact power of ten) when |e - f| <= 22, and with a certified double-double product
#   otherwise (k = 23 is exact); '%' is a correctly rounded division by 100.
# ============================================================================================================
VL_MAX = 15
# automaton states
(S_PRE, S_SIGN, S_I1, S_I2, S_I3, S_I4, S_C0, S_C1, S_C2, S_C3, S_F, S_D0, S_D1, S_X0, S_X1, S_X2, S_SP, S_PCT, S_DEAD) = range(19)
NUM_ACC = (S_I1, S_I2, S_I3, S_I4, S_C3, S_F, S_D1, S_X2)
# character classes
(K_SPC, K_DIG, K_PLUS, K_MINUS, K_DOT, K_COMMA, K_E, K_PCT, K_OTHER) = range(9)


def _trans(s, k):
    if s == S_DEAD:
        return S_DEAD
    if s == S_PRE:
        return {K_SPC: S_PRE, K_DIG: S_I1, K_PLUS: S_SIGN, K_MINUS: S_SIGN, K_DOT: S_D0}.get(k, S_DEAD)
    if s == S_SIGN:
        return {K_DIG: S_I1, K_DOT: S_D0}.get(k, S_DEAD)
    if s in (S_I1, S_I2, S_I3, S_I4):
        if k == K_DIG:
            return {S_I1: S_I2, S_I2: S_I3, S_I3: S_I4, S_I4: S_I4}[s]
        if k == K_COMMA:
            return S_C0 if s != S_I4 else S_DEAD
    if s in (S_C0, S_C1, S_C2):
        return {S_C0: S_C1, S_C1: S_C2, S_C2: S_C3}[s] if k == K_DIG else S_DEAD
    if s == S_C3:
        if k == K_COMMA:
            return S_C0
        if k == K_DIG:
            return S_DEAD
    if s in (S_I1, S_I2, S_I3, S_I4, S_C3) and k == K_DOT:
        return S_F
    if s == S_F and k == K_DIG:
        return S_F
    if s == S_D0:
        return S_D1 if k == K_DIG else S_DEAD
    if s == S_D1 and k == K_DIG:
        return S_D1
    if s in (S_I1, S_I2, S_I3, S_I4, S_C3, S_F, S_D1) and k == K_E:
        return S_X0
    if s == S_X0:
        return {K_PLUS: S_X1, K_MINUS: S_X1, K_DIG: S_X2}.get(k, S_DEAD)
    if s == S_X1:
        return S_X2 if k == K_DIG else S_DEAD
    if s == S_X2 and k == K_DIG:
        return S_X2
    if s in NUM_ACC or s == S_SP:
        if k == K_SPC:
            return S_SP
        if k == K_PCT:
            return S_PCT
        return S_DEAD
    if s == S_PCT:
        return S_PCT if k == K_SPC else S_DEAD
    return S_DEAD


ACCEPT = NUM_ACC + (S_SP, S_PCT)


class Exact8Value(Exact8Text):

    def dd_round(self, Nb, ph, pl):
        """fl(N (ph + pl)) for an integer N and a double-double constant, with the certificate
        ulp/2 - |error part| > 2^-100 |value| (the error of the double-double product is below 2^-102 |value|)."""
        hh, ll = self.two_prod(Nb, ph)
        ll = self.sp([[ll], [Nb, pl]], hint="ll")
        sb, eb = self.fast_two_sum(hh, ll)
        ub = self.ulp_full(sb)
        gap = self.sp([[ub, C(0.5)], [LE(C(0.0), eb), C(-1.0), eb], [LE(C(0.0), eb, True), eb]], hint="gap")
        bound = self.sp([[sb, C(2.0 ** -100)]], hint="bd")
        return sb, self.sp([[LE(gap, bound, True)]], hint="ct")

    def div100(self, v, mask):
        """Correctly rounded v / 100 for every double v: the inherited correctly rounded division is valid for
        |v| in [2^-290, 2^290]; outside, v is scaled by an exact power of two (2^-600 or 2^600), divided and
        scaled back (exact while the quotient is a normal number). A subnormal quotient is flagged."""
        av = self.absv(v, "dv")
        mid = [mask, LE(C(2.0 ** -290), av), LE(av, C(2.0 ** 290))]
        big = [mask, LE(av, C(2.0 ** 290), True)]
        tin = [mask, LE(C(2.0 ** -290), av, True), LE(C(100.0 * 2.0 ** -1022), av)]
        q1 = self.divide(v, C(100.0), mid)
        q2 = self.divide(self.sp([big + [v, C(2.0 ** -600)]], hint="vb"), C(100.0), big)
        q3 = self.divide(self.sp([tin + [v, C(2.0 ** 600)]], hint="vt"), C(100.0), tin)
        q = self.sp([mid + [q1], big + [q2, C(2.0 ** 300), C(2.0 ** 300)], tin + [q3, C(2.0 ** -300), C(2.0 ** -300)]], hint="q100")
        subn = self.sp([[mask, LE(C(100.0 * 2.0 ** -1022), av, True), LE(av, C(0.0), True)]], hint="sbn")
        return q, subn

    def dec_to_double(self, N, kk):
        """The double nearest to N 10^k (ties to even), N an integer 0 <= N < 2^53, k an integer column.
        Returns (value, uncertified flag). Exact single IEEE operations for |k| <= 22; certified double-double
        otherwise (k = 23 is exact: 10^23 = ph + pl and every product is exact); subnormal results by
        rounding N 10^k 2^1074 to an integer; 0 for k < -340; inf (flagged) for k > 308 and N > 0."""
        rng = lambda a, b_: [LE(C(float(a)), kk), LE(kk, C(float(b_)))]
        p10 = self.sel(kk, {k: 10.0 ** k for k in range(0, 23)}, "p10")
        q10 = self.sel(kk, {k: 10.0 ** (-k) for k in range(-22, 0)}, "q10")
        v1 = self.sp([rng(0, 22) + [N, p10]], hint="v1")
        v2 = self.divide(N, self.sp([rng(-22, -1) + [q10], [LE(C(-22.0), kk, True), C(1.0)], [LE(C(0.0), kk), C(1.0)]], hint="qd"), rng(-22, -1))
        # 23 <= k <= 308: constants scaled by 2^-600 (no overflow in the splitting), result scaled back exactly
        ph = self.sel(kk, {k: dd_const(Fraction(10) ** k / Fraction(2) ** 600)[0] for k in range(23, 309)}, "bh")
        pl = self.sel(kk, {k: dd_const(Fraction(10) ** k / Fraction(2) ** 600)[1] for k in range(23, 309)}, "bl")
        s3, c3 = self.dd_round(self.sp([rng(23, 308) + [N]], hint="N3"), ph, pl)
        v3 = self.sp([rng(23, 308) + [s3, C(2.0 ** 300), C(2.0 ** 300)]], hint="v3")
        # -290 <= k <= -23: unscaled double-double (every partial product stays normal)
        ph = self.sel(kk, {k: dd_const(Fraction(10) ** k)[0] for k in range(-290, -22)}, "ch")
        pl = self.sel(kk, {k: dd_const(Fraction(10) ** k)[1] for k in range(-290, -22)}, "cl")
        s4, c4 = self.dd_round(self.sp([rng(-290, -23) + [N]], hint="N4"), ph, pl)
        # -340 <= k <= -291: y = N 10^k 2^1074; y >= 2^52: normal result fl(y) 2^-1074; else round(y) 2^-1074
        ph = self.sel(kk, {k: dd_const(Fraction(10) ** k * Fraction(2) ** 1074)[0] for k in range(-340, -290)}, "eh")
        pl = self.sel(kk, {k: dd_const(Fraction(10) ** k * Fraction(2) ** 1074)[1] for k in range(-340, -290)}, "el")
        N5 = self.sp([rng(-340, -291) + [N]], hint="N5")
        yh, yl = self.two_prod(N5, ph)
        yl = self.sp([[yl], [N5, pl]], hint="yl5")
        yh, yl = self.fast_two_sum(yh, yl)
        s5n, c5n = self.dd_round(N5, ph, pl)
        # subnormal result: round y = yh + yl to an integer, ties impossible (5^291 does not divide N 2^...)
        f5 = self.floor_nonneg(self.sp([[LE(C(2.0 ** 52), yh, True), yh]], hint="y5"))
        a5 = self.sp([[yh], [C(-1.0), f5]], hint="a5")                     # exact, in [0, 1)
        nb5 = self.sp([[C(-1.0), yl]], hint="nb5")
        dn5 = self.sp([[EQ(a5, C(0.0)), LE(C(0.0), yl, True)]], hint="dn5")   # a + b < 0
        up5 = self.sp([[LE(nb5, self.sp([[a5], [C(-1.0)]], hint="am5"))]], hint="up5")   # a + b >= 1
        f5 = self.sp([[f5], [EQ(dn5, C(1.0)), C(-1.0)], [EQ(up5, C(1.0)), C(1.0)]], hint="f5b")
        a5 = self.sp([[a5], [EQ(dn5, C(1.0)), C(1.0)], [EQ(up5, C(1.0)), C(-1.0)]], hint="a5b")
        ah5 = self.sp([[a5], [C(-0.5)]], hint="ah5")                        # exact
        gt5 = self.sp([[LE(ah5, nb5, True)]], hint="gt5")                   # frac > 1/2
        sub = self.sp([[f5], [EQ(gt5, C(1.0)), C(1.0)]], hint="sub")
        c5s = self.sp([[LE(self.absv(self.sp([[ah5], [yl]], hint="d5"), "a5d"), C(2.0 ** -40))]], hint="c5s")
        normal5 = LE(C(2.0 ** 52), yh)
        v5 = self.sp([rng(-340, -291) + [normal5, s5n, C(2.0 ** -537), C(2.0 ** -537)],
                      rng(-340, -291) + [LE(C(2.0 ** 52), yh, True), sub, C(2.0 ** -537), C(2.0 ** -537)]], hint="v5")
        val = self.sp([rng(0, 22) + [v1], rng(-22, -1) + [v2], rng(23, 308) + [v3], rng(-290, -23) + [s4], rng(-340, -291) + [v5]], hint="val")
        nz = EQ(N, C(0.0), True)                                            # N = 0: the value 0 is exact
        unc = self.sp([rng(23, 308) + [nz, EQ(c3, C(1.0), True), EQ(kk, C(23.0), True)], rng(-290, -23) + [nz, EQ(c4, C(1.0), True)],
                       rng(-340, -291) + [nz, normal5, EQ(c5n, C(1.0), True)], rng(-340, -291) + [nz, LE(C(2.0 ** 52), yh, True), EQ(c5s, C(1.0))],
                       [LE(kk, C(308.0), True), LE(N, C(0.0), True)]], hint="unc")
        self.notes["decimal to double: exact single operations for |k| <= 22, certified double-double beyond"] += 1
        return val, unc

    def f_VALUE(self, args):
        a0 = args[0]
        if self.mode8 == "A" and a0[0] == "call" and a0[1] == "LEFT":
            return self.value_left_exact(a0[2])
        return Exact8Text.f_VALUE(self, args)

    def value_left_exact(self, largs):
        if len(largs) < 2 or self.has_cell(largs[1]):
            raise K.Unsupported("LEFT with a computed length")
        n = int(K.X.to_num(K.X.ev(largs[1], K.X.Ctx(self.store, self.book, self.sheet_name, 1, 1))))
        if n < 0 or n > VL_MAX:
            raise K.Unsupported("LEFT length outside 0..%d (method A)" % VL_MAX)
        segs, (ef, ec) = self.to_text_segs(largs[0])
        segs = [s_ for s_ in segs]
        if not segs:
            raise K.Unsupported("VALUE(LEFT) of a constant")
        # the argument of VALUE is a text: LEFT(x, n) = the characters at positions < n
        U, uc = self.union([(t, p, c, v) for (t, p, c, v) in segs])
        pr = self.props(U, uc["code"], want=("spc", "dig", "tr"))
        state = C(float(S_PRE))
        N, fd, ev_, msg, esg = C(0.0), C(0.0), C(0.0), C(0.0), C(0.0)
        for p in range(n):
            m = self.match(["_row", C(float(p)), C(1.0)], U, ["_parent", uc["pos"], uc["valid"]], hint="vm")
            pres = PRESENT(m)
            tr = {"col": pr["tr"], "via": m}
            dig = {"col": pr["dig"], "via": m}
            spc = {"col": pr["spc"], "via": m}
            cls = self.sp([[pres, EQ(spc, C(1.0)), C(float(K_SPC))],
                           [pres, EQ(spc, C(1.0), True), LE(C(0.0), dig), C(float(K_DIG))],
                           [pres, EQ(spc, C(1.0), True), LE(C(0.0), dig, True), EQ(tr, C(43.0)), C(float(K_PLUS))],
                           [pres, EQ(spc, C(1.0), True), LE(C(0.0), dig, True), EQ(tr, C(45.0)), C(float(K_MINUS))],
                           [pres, EQ(spc, C(1.0), True), LE(C(0.0), dig, True), EQ(tr, C(46.0)), C(float(K_DOT))],
                           [pres, EQ(spc, C(1.0), True), LE(C(0.0), dig, True), EQ(tr, C(44.0)), C(float(K_COMMA))],
                           [pres, EQ(spc, C(1.0), True), LE(C(0.0), dig, True), EQ(tr, C(101.0)), C(float(K_E))],
                           [pres, EQ(spc, C(1.0), True), LE(C(0.0), dig, True), EQ(tr, C(69.0)), C(float(K_E))],
                           [pres, EQ(spc, C(1.0), True), LE(C(0.0), dig, True), EQ(tr, C(37.0)), C(float(K_PCT))],
                           [pres, EQ(spc, C(1.0), True), LE(C(0.0), dig, True), EQ(tr, C(43.0), True), EQ(tr, C(45.0), True),
                            EQ(tr, C(46.0), True), EQ(tr, C(44.0), True), EQ(tr, C(101.0), True), EQ(tr, C(69.0), True),
                            EQ(tr, C(37.0), True), C(float(K_OTHER))]], hint="cls")
            d = self.sp([[pres, LE(C(0.0), dig), dig]], hint="dv")
            ts, mant, frac, expd, msign, esign = [], [], [], [], [], []
            for s0 in range(19):
                for k in range(9):
                    s1 = _trans(s0, k)
                    cond = [EQ(state, C(float(s0))), EQ(cls, C(float(k))), pres]
                    if s1 != 0:
                        ts.append(cond + [C(float(s1))])
                    if k == K_DIG and s1 in (S_I1, S_I2, S_I3, S_I4, S_C1, S_C2, S_C3, S_F, S_D1):
                        mant.append(cond)
                        if s1 in (S_F, S_D1):
                            frac.append(cond)
                    if k == K_DIG and s1 == S_X2:
                        expd.append(cond)
                    if k == K_MINUS and s1 == S_SIGN:
                        msign.append(cond)
                    if k == K_MINUS and s1 == S_X1:
                        esign.append(cond)
            ts.append([PRESENT(m, True), state])                       # beyond the text: state unchanged
            ism = self.sp([t + [C(1.0)] for t in mant], hint="im")
            N = self.sp([[EQ(ism, C(1.0), True), N], [EQ(ism, C(1.0)), N, C(10.0)], [EQ(ism, C(1.0)), d]], hint="N")
            fd = self.sp([[fd]] + [t + [C(1.0)] for t in frac], hint="fd")
            ise = self.sp([t + [C(1.0)] for t in expd], hint="ie")
            ev_ = self.sp([[EQ(ise, C(1.0), True), ev_], [EQ(ise, C(1.0)), ev_, C(10.0)], [EQ(ise, C(1.0)), d]], hint="ev")
            msg = self.sp([[msg]] + [t + [C(1.0)] for t in msign], hint="ms")
            esg = self.sp([[esg]] + [t + [C(1.0)] for t in esign], hint="es")
            state = self.sp(ts, hint="st")
        ok = self.sp([[EQ(state, C(float(s)))] for s in ACCEPT], hint="acc")
        pct = self.sp([[EQ(state, C(float(S_PCT)))]], hint="pct")
        # exponent k = +-e - f  and the correctly rounded value of N 10^k
        kk = self.sp([[EQ(esg, C(1.0), True), ev_], [EQ(esg, C(1.0)), C(-1.0), ev_], [C(-1.0), fd]], hint="k")
        val, unc = self.dec_to_double(N, kk)
        val = self.sp([[EQ(msg, C(1.0), True), val], [EQ(msg, C(1.0)), C(-1.0), val]], hint="sv")
        valp, subn = self.div100(val, EQ(pct, C(1.0)))
        val = self.sp([[EQ(pct, C(1.0), True), val], [EQ(pct, C(1.0)), valp]], hint="vf")
        unc = self.sp([[unc], [EQ(pct, C(1.0)), subn]], hint="unc2")
        # outside the certified domain: a rounding that the double-double bound cannot certify, or float()
        # overflowing to inf (k > 308 with N > 0: the reference returns inf, not an Excel value)
        okc = EQ(ef, C(1.0), True) if not isc(ef) else C(1.0)
        self.flag(self.sp([[okc, EQ(ok, C(1.0)), EQ(unc, C(1.0))]], hint="vflag"))
        ef2, ec2 = self.first_error([(ef, ec), (self.sp([[EQ(ok, C(1.0), True)]], hint="nv"), C(E_VALUE))])
        self.notes["VALUE(LEFT) method A: character positions, automaton of to_float_text, exact value"] += 1
        return self.num_or_err(self.sp([[EQ(ef2, C(1.0), True), val]], hint="vv"), ef2, ec2)


# ============================================================================================================
# Part 6: method B for the text rules (probabilistic identity by fingerprints)
#   F(t) = (sum_i code_i w1[i], sum_i code_i w2[i]) with fixed pseudo-random integer weights w < 2^20
#   (exact integer sums below 2^53 for texts of up to 2,048 characters). Two different texts have the same
#   fingerprint with probability <= 2^-40 per pair for weights drawn independently of the texts.
#   * concatenation: the fingerprint of the result is matched into the fingerprints of the text dictionary
#     (the texts of the workbook); a result that is not in the dictionary is MISSING (no new text can be
#     named) - the limitation that method A removes;
#   * SUMIF criterion: equality of the case-folded fingerprints (group representative of the lower case);
#     wildcards and order operators are not covered (flag).
# ============================================================================================================
import random as _random

FP_N = 2048
_rw = _random.Random(20261118)
FP_W1 = np.array([float(_rw.randrange(1, 2 ** 20)) for _ in range(FP_N)])
FP_W2 = np.array([float(_rw.randrange(1, 2 ** 20)) for _ in range(FP_N)])


def fp_py(s, codes=None):
    cs = codes if codes is not None else [ord(c) for c in s]
    if len(cs) > FP_N:
        return (math.nan, math.nan)
    return (float(sum(c * FP_W1[i] for i, c in enumerate(cs))), float(sum(c * FP_W2[i] for i, c in enumerate(cs))))


class Exact8Final(Exact8Value):

    def fp_table(self):
        if "FW" not in self.tabs.rows:
            self.table("FW", {"pos": np.arange(FP_N, dtype=float), "w1": FP_W1, "w2": FP_W2})
        return "FW"

    def fingerprint(self, segs, code_of=None):
        """(F1, F2) per instance from character segments (code_of: per-segment code operand override)."""
        fw = self.fp_table()
        f1, f2 = [], []
        for si, (table, opos, code, valid) in enumerate(segs):
            cd = code if code_of is None else code_of[si]
            m = self.match([opos], fw, ["pos"], table=table, hint="fwm")
            vv = [EQ(valid, C(1.0))] if not isc(valid) else ([] if valid["const"] == 1.0 else [EQ(C(0.0), C(1.0))])
            g1 = self.sp([vv + [PRESENT(m), cd, {"col": "w1", "via": m}]], table=table, group={"by": "_parent"}, hint="g1")
            g2 = self.sp([vv + [PRESENT(m), cd, {"col": "w2", "via": m}]], table=table, group={"by": "_parent"}, hint="g2")
            f1.append([g1]); f2.append([g2])
        self.notes["method B: fingerprint (two exact integer weighted sums)"] += 1
        return self.sp(f1, hint="F1"), self.sp(f2, hint="F2")

    def dict_table(self):
        if "DICT" not in self.tabs.rows:
            texts = sorted(self.sd.code, key=self.sd.code.get)
            cols = {k: [] for k in ("F1", "F2", "s", "k", "p", "q", "w", "o")}
            for t in texts:
                a, b = fp_py(t)
                enc = self.sd.enc(t)
                for k, v in zip(("F1", "F2", "s", "k", "p", "q", "w", "o"), (a, b, enc[2], enc[3], enc[5], enc[6], enc[7], enc[8])):
                    cols[k].append(v)
            self.table("DICT", cols)
        return "DICT"

    def ev(self, node):
        if self.mode8 == "B" and node[0] == "bin" and node[1] == "&" and self.has_cell(node):
            parts = []
            def flat(n):
                if n[0] == "bin" and n[1] == "&":
                    flat(n[2]); flat(n[3])
                else:
                    parts.append(n)
            flat(node)
            segs, L, (ef, ec) = self.concat_segs([self.to_text_segs(p) for p in parts])
            F1, F2 = self.fingerprint(segs)
            d = self.dict_table()
            m = self.match([F1, F2], d, ["F1", "F2"], hint="dm")
            okc = EQ(ef, C(1.0), True) if not isc(ef) else C(1.0)
            comps = {"t": self.sp([[EQ(ef, C(1.0)), C(T4)], [EQ(ef, C(1.0), True), C(T2)]], hint="tt"),
                     "e": self.sp([[EQ(ef, C(1.0)), ec]], hint="te")}
            for k in ("s", "k", "p", "q", "w", "o"):
                comps[k] = self.sp([[okc, PRESENT(m), {"col": k, "via": m}]], hint="d" + k)
            v = V(comps, {T2, T4})
            v.c["t"] = self.mark_missing(v.c["t"], self.sp([[okc, PRESENT(m, True)]], hint="nd"))   # not in the dictionary
            self.notes["method B: concatenation named through the text dictionary (fingerprint match)"] += 1
            return v
        return Exact8Value.ev(self, node)

    def _sumif(self, args, count):
        a1 = args[1]
        if not (self.mode8 == "B" and a1[0] == "bin" and a1[1] == "&" and self.has_cell(a1)):
            return Exact8Value._sumif(self, args, count)
        x = self.ev(args[0])
        s = self.ev(args[2]) if not count and len(args) > 2 else x
        if not isinstance(x, K.RefS) or not isinstance(s, K.RefS):
            return self.errv(E_VALUE)
        extra = [("s.", s)] if not count else []
        R, Rc, gref, bad = self.range_tables(x, extra=extra, truncate=True, key=("sumif", count))
        if not count:
            bad = np.where(bad > 0, bad, s.bad)
        st, sn, se = ("s.t", "s.n", "s.e") if not count else ("t", "n", "e")
        bf, bc = self.static_bad(bad)
        parts = []
        def flat(n):
            if n[0] == "bin" and n[1] == "&":
                flat(n[2]); flat(n[3])
            else:
                parts.append(n)
        flat(a1)
        segs, Lc, (cef, cec) = self.concat_segs([self.to_text_segs(p) for p in parts])
        U, uc = self.union(segs)
        upr = self.props(U, uc["code"], want=("gidl",))
        c0m = self.char_at(U, uc, uc["pos"], uc["valid"], C(0.0), "c0")
        c1m = self.char_at(U, uc, uc["pos"], uc["valid"], C(1.0), "c1")
        c0 = self.sp([[PRESENT(c0m), {"col": uc["code"], "via": c0m}], [PRESENT(c0m, True), C(-1.0)]], hint="c0")
        c1 = self.sp([[PRESENT(c1m), {"col": uc["code"], "via": c1m}], [PRESENT(c1m, True), C(-1.0)]], hint="c1")
        ne = self.sp([[EQ(c0, C(60.0)), EQ(c1, C(62.0))]], hint="ne")
        two = self.sp([[EQ(c0, C(60.0)), EQ(c1, C(61.0))], [EQ(c0, C(62.0)), EQ(c1, C(61.0))], [EQ(ne, C(1.0))]], hint="two")
        order = self.sp([[EQ(c0, C(60.0)), EQ(ne, C(1.0), True)], [EQ(c0, C(62.0))]], hint="ord")
        oplen = self.sp([[EQ(two, C(1.0)), C(2.0)], [EQ(two, C(1.0), True), EQ(c0, C(61.0)), C(1.0)],
                         [EQ(two, C(1.0), True), EQ(order, C(1.0)), C(1.0)]], hint="ol")
        rpos = self.sp([[uc["pos"]], [C(-1.0), {"col": oplen, "via": "_parent"}]], table=U, hint="rp")
        rval = self.sp([[EQ(uc["valid"], C(1.0)), LE(C(0.0), rpos)]], table=U, hint="rv")
        wild = self.sp([[EQ(rval, C(1.0)), EQ(uc["code"], C(42.0))], [EQ(rval, C(1.0)), EQ(uc["code"], C(63.0))],
                        [EQ(rval, C(1.0)), EQ(uc["code"], C(126.0))]], table=U, group={"by": "_parent"}, hint="wl")
        okc = EQ(cef, C(1.0), True) if not isc(cef) else C(1.0)
        self.flag(self.sp([[okc, LE(C(1.0), wild)], [okc, EQ(order, C(1.0))]], hint="bfl"))
        # fingerprint of the rest (case-folded codes) and of every criteria-cell text
        fw = self.fp_table()
        m = self.match([rpos], fw, ["pos"], table=U, hint="fwm")
        R1 = self.sp([[EQ(rval, C(1.0)), PRESENT(m), upr["gidl"], {"col": "w1", "via": m}]], table=U, group={"by": "_parent"}, hint="R1")
        R2 = self.sp([[EQ(rval, C(1.0)), PRESENT(m), upr["gidl"], {"col": "w2", "via": m}]], table=U, group={"by": "_parent"}, hint="R2")
        rec0 = [r for r in self.recipes if r[0] == "T" and r[1] == Rc and r[2] == ""][0]
        CH = Rc + ".ch"
        rec = ("charsT", CH, rec0[3], rec0[4], rec0[5])
        self.recipes.append(rec)
        self.fill(rec, self.cache)
        cpr = self.props(CH, "code", want=("gidl",))
        mc = self.match(["pos"], fw, ["pos"], table=CH, hint="fwc")
        H1 = self.sp([[PRESENT(mc), cpr["gidl"], {"col": "w1", "via": mc}]], table=CH, group={"by": "_parent"}, hint="H1")
        H2 = self.sp([[PRESENT(mc), cpr["gidl"], {"col": "w2", "via": mc}]], table=CH, group={"by": "_parent"}, hint="H2")
        # pairs instance x cell
        P = self.nm("G.x")
        par = self.tabs.data[Rc]["_parent"].astype(np.int64)
        ridv = self.memo[("rid", R)]
        byr = collections.defaultdict(list)
        for idx, g in enumerate(par):
            byr[g].append(idx)
        inst, cell = [], []
        for i in range(self.n):
            g = int(ridv[i]) if ridv[i] >= 0 else -1
            cs = byr.get(g, [])
            inst.append(np.full(len(cs), i)); cell.append(np.array(cs, dtype=np.int64))
        inst = np.concatenate(inst) if inst else np.zeros(0)
        cell = np.concatenate(cell) if cell else np.zeros(0)
        self.table(P, {"_parent": inst, "y": cell})
        ry = self.match(["y"], Rc, ["_row"], table=P, hint="ry")
        same_ = self.sp([[EQ({"col": H1, "via": ry}, {"col": R1, "via": "_parent"}), EQ({"col": H2, "via": ry}, {"col": R2, "via": "_parent"})]],
                        table=P, hint="sm")
        ty = {"col": "t", "via": ry}
        nep = {"col": ne, "via": "_parent"}
        okp = EQ({"col": cef, "via": "_parent"}, C(1.0), True)
        hit = self.sp([[okp, EQ(nep, C(1.0), True), EQ(ty, C(T2)), EQ(same_, C(1.0))],
                       [okp, EQ(nep, C(1.0))], [okp, EQ(nep, C(1.0)), EQ(ty, C(T2)), EQ(same_, C(1.0)), C(-1.0)]], table=P, hint="hit")
        sv = {"t": {"col": st, "via": ry}, "n": {"col": sn, "via": ry}, "e": {"col": se, "via": ry}}
        if count:
            tot = self.sp([[EQ(hit, C(1.0))]], table=P, group={"by": "_parent"}, hint="cnt")
            ef1, ec1 = C(0), C(0)
        else:
            tot = self.sp([[EQ(hit, C(1.0)), EQ(sv["t"], C(T1)), sv["n"]]], table=P, group={"by": "_parent"}, hint="sif")
            nerr = self.sp([[EQ(hit, C(1.0)), EQ(sv["t"], C(T4))]], table=P, group={"by": "_parent"}, hint="sne")
            isr = self.sp([[EQ(hit, C(1.0)), EQ(sv["t"], C(T4))]], table=P, hint="ise")
            fe = self.match(["_row", C(1.0)], P, ["_parent", isr], hint="sfe")
            fy = self.sp([[PRESENT(fe), {"col": "y", "via": fe}]], hint="fy")
            fr = self.match([fy], Rc, ["_row"], hint="fr")
            ec1 = self.sp([[PRESENT(fr), {"col": se, "via": fr}]], hint="ec")
            ef1 = self.sp([[LE(C(1.0), nerr)]], hint="ef")
        ef, ec = self.first_error([(bf, bc), (ef1, ec1)])
        r = self.sp([[EQ(ef, C(1.0), True), tot]], hint="sif")
        self.notes["method B: SUMIF criterion equality by case-folded fingerprints"] += 1
        return self.num_or_err(r, ef, ec, count)
