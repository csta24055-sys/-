"""The five basic equation families of building whole-life carbon (independent implementation, general mathematics only).

No coefficient, formula text or value of any third-party tool is used. All numbers in tests are fictional.

Notation: [P] is the Iverson bracket (1 if P else 0). Exact arithmetic uses fractions.Fraction.

F1  rational map with exclusive masks (preparation / post-processing, elementwise, T-independent)
        y = sum_k [c_k(x)] * prod_i x_i^(e_ik),   e_ik in Z,  the c_k mutually exclusive
    covers unit conversion, gross-up 1/(1-w), shares, priority selection, look-up, min/max/clip, ratios, indicators.
F2  masked sum-product (the bilinear core of an inventory)
        E = sum_{i in I} m_i(x) * q_i * f_i            (m_i in {0,1}; q activity, f factor; may carry more factors)
F3  time-measure integral over the study period T (continuous operation AND discrete events in one form)
        V(T) = sum_j a_j * kappa_j(T),  kappa(T; s,l,g,lo,hi) = [lo < T <= hi] [g < T(1-eps)] r_l(T - s)
        r_0 = 1, r_l(x) = clip(x, 0, l):  const (initial/terminal), year cell w_k, density, atom (event), gated cell
        with the event generator tau_n = n c (n >= 1, n c < H(1-eps)) and counts N(T) = sum_n [tau_n < T(1-eps)].
F4  state recurrence (amplitudes that depend on history)
        u_{k+1} = A_k u_k + b_k  (affine, switched by events);  emission = linear functional of u
F5  signed linear aggregation (composition of stages / totals)
        S_s = iota_s * sum_u sigma_{s,u} beta_{s,u} V_u,   C = sum_s S_s,   sigma in {-1,0,+1}
G   domain guards (common internal mechanism, not a value family): finite, T > 0, cycle > 0, 0 <= rate <= 1 ...
    A failed guard yields MISSING (None), never 0.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction

EPS = 1e-9
NEG_INF = float("-inf")
MISSING = None


# ------------------------------------------------------------------------------------------------ G: guards
class Guard:
    """Common guard layer. Each check returns True/False and records the reason; values are never replaced by 0."""

    def __init__(self):
        self.violations = []

    def check(self, ok, what):
        if not ok:
            self.violations.append(what)
        return ok

    def finite(self, x, what):
        return self.check(x is not None and isinstance(x, (int, float, Fraction)) and math.isfinite(float(x)), what + ": finite")

    def positive(self, x, what):
        return self.finite(x, what) and self.check(x > 0, what + ": > 0")

    def nonneg(self, x, what):
        return self.finite(x, what) and self.check(x >= 0, what + ": >= 0")

    def rate(self, x, what, lo_open=False, hi_open=False):
        if not self.finite(x, what):
            return False
        lo_ok = x > 0 if lo_open else x >= 0
        hi_ok = x < 1 if hi_open else x <= 1
        return self.check(lo_ok and hi_ok, what + ": rate in %s0,1%s" % ("(" if lo_open else "[", ")" if hi_open else "]"))


def guarded(fn):
    """Wrap a family evaluation: if any guard fails inside, the result is MISSING (not 0)."""
    def run(*a, guard=None, **k):
        g = guard if guard is not None else Guard()
        n0 = len(g.violations)
        v = fn(*a, guard=g, **k)
        return MISSING if len(g.violations) > n0 else v
    return run


# ------------------------------------------------------------------------------------------------ F1
def f1_monomial(xs, exps):
    """prod x_i^e_i, e_i in Z (exact)."""
    out = Fraction(1)
    for x, e in zip(xs, exps):
        assert isinstance(e, int)
        out *= Fraction(x) ** e
    return out


def f1_select(cases, default=MISSING):
    """sum_k [c_k] y_k with exclusive c_k; first-match semantics made exclusive by prefix products
    [c_1], [not c_1][c_2], ... (rule R-SEL)."""
    for c, y in cases:
        if c:
            return y
    return default


# ------------------------------------------------------------------------------------------------ F2
def f2_sum_product(rows):
    """rows: iterable of (mask, factor_1, factor_2, ...). Returns sum mask * prod factors (exact)."""
    tot = Fraction(0)
    for r in rows:
        m, fs = r[0], r[1:]
        if m:
            p = Fraction(1)
            for f in fs:
                p *= Fraction(f)
            tot += p
    return tot


# ------------------------------------------------------------------------------------------------ F3
@dataclass(frozen=True)
class Kernel:
    """a * [lo < T <= hi] [g < T(1-eps)] r_l(T - s)."""
    a: Fraction
    s: float = 0.0
    l: float = 0.0
    g: float = NEG_INF
    lo: float = NEG_INF
    hi: float = math.inf

    def __call__(self, T):
        if not (self.lo < T <= self.hi):
            return Fraction(0)
        if not (self.g < T * (1.0 - EPS)):          # the event rule, evaluated in float exactly like the model
            return Fraction(0)
        if self.l == 0.0:
            return Fraction(self.a)
        x = Fraction(T) - Fraction(self.s)
        if x <= 0:
            return Fraction(0)
        return Fraction(self.a) * min(x, Fraction(self.l))


def f3_value(kernels, T):
    return sum((k(T) for k in kernels), Fraction(0))


def f3_events(cycle, H):
    """Event generator tau_n = n c for n >= 1 while n c < H(1-eps); empty if the cycle is missing/non-positive/inf."""
    if cycle is None or not math.isfinite(cycle) or cycle <= 0:
        return []
    out, n = [], 1
    while n * cycle < H * (1.0 - EPS):
        out.append(n * cycle)
        n += 1
    return out


def f3_count(taus, T):
    return sum(1 for t in taus if t < T * (1.0 - EPS))


def year_weight(k, T):
    """w_k(T) = clip(T - k, 0, 1): share of year cell k inside (0, T]."""
    return Kernel(Fraction(1), s=float(k), l=1.0)(T)


# ------------------------------------------------------------------------------------------------ F4
def f4_affine(A, b, u0, n):
    """u_{k+1} = A u_k + b (scalar), returns [u_0..u_n] exactly."""
    u = [Fraction(u0)]
    for _ in range(n):
        u.append(Fraction(A) * u[-1] + Fraction(b))
    return u


def f4_closed(A, b, u0, k):
    """Closed form of the scalar affine recurrence (A != 1): u_k = A^k u0 + b (1 - A^k)/(1 - A)."""
    A, b, u0 = Fraction(A), Fraction(b), Fraction(u0)
    if A == 1:
        return u0 + k * b
    return A ** k * u0 + b * (1 - A ** k) / (1 - A)


# ------------------------------------------------------------------------------------------------ F5
def f5_aggregate(values, comp, inc):
    """values: {unit: V_u}; comp: [(stage, unit, sign, beta)]; inc: {stage: 0/1}. Returns ({stage: S_s}, C)."""
    S = {}
    for st, u, sg, beta in comp:
        S[st] = S.get(st, Fraction(0)) + inc.get(st, 0) * sg * beta * Fraction(values[u])
    return S, sum(S.values(), Fraction(0))


# ------------------------------------------------------------------------------------------------ reduction rules
# Each rule rewrites a spreadsheet-style operation into the families above; verify_families.py checks them exactly.
def r_if(c, a, b):                 # IF(c, a, b) = [c] a + [not c] b
    return int(bool(c)) * a + int(not c) * b


def r_min(a, b):                   # min(a, b) = a + [b < a](b - a)
    return a + int(b < a) * (b - a)


def r_max(a, b):                   # max(a, b) = a + [b > a](b - a)
    return a + int(b > a) * (b - a)


def r_clip(x, lo, hi):             # clip = max(lo, min(x, hi))
    return r_max(lo, r_min(x, hi))


def r_abs(x):
    return r_if(x >= 0, x, -x)


def r_lookup(key, table):          # exact-match look-up = sum_k [key = k] v_k (missing key -> MISSING, not 0)
    hits = [v for k, v in table if k == key]
    return hits[0] if hits else MISSING


def r_floor_count(y, N):           # floor(y) for 0 <= y < N+1 as a lattice count sum_{n=1..N} [n <= y]
    return sum(1 for n in range(1, N + 1) if n <= y)


def r_round(y, digits, N):         # ROUND half away from zero for y >= 0: floor(y 10^d + 1/2) / 10^d (lattice count)
    s = Fraction(10) ** digits
    return Fraction(r_floor_count(Fraction(y) * s + Fraction(1, 2), N)) / s


def r_mod_flag(year, cycle, H):    # [year is an event year] = sum_n [n c = year], n c <= H (integer cycle)
    return int(any(n * cycle == year for n in range(1, H // cycle + 1)))


def r_replacements(T, c):          # number of replacements strictly inside (0, T): sum_n [n c < T]
    n, out = 1, 0
    while n * c < T:
        out += 1
        n += 1
    return out
