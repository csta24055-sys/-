"""Small dense linear algebra over a field (fractions.Fraction exact, or float).

Generic numerics only: no circuit or domain vocabulary.
"""
from __future__ import annotations

import math
from fractions import Fraction

FLOAT_TOL = 1e-11


def is_exact(x) -> bool:
    return isinstance(x, (Fraction, int)) and not isinstance(x, bool)


def zero_like(exact: bool):
    return Fraction(0) if exact else 0.0


def one_like(exact: bool):
    return Fraction(1) if exact else 1.0


def is_zero(x, exact: bool, scale: float = 1.0) -> bool:
    if exact:
        return x == 0
    return abs(x) <= FLOAT_TOL * max(1.0, scale)


def zeros(r, c, exact):
    z = zero_like(exact)
    return [[z] * c for _ in range(r)]


def eye(n, exact):
    m = zeros(n, n, exact)
    for i in range(n):
        m[i][i] = one_like(exact)
    return m


def matmul(A, B, exact):
    if not A:
        return []
    n, k, m = len(A), len(B), (len(B[0]) if B else 0)
    z = zero_like(exact)
    out = [[z] * m for _ in range(n)]
    for i in range(n):
        Ai = A[i]
        oi = out[i]
        for p in range(k):
            a = Ai[p]
            if a == 0:
                continue
            Bp = B[p]
            for j in range(m):
                b = Bp[j]
                if b != 0:
                    oi[j] = oi[j] + a * b
    return out


def matvec(A, x, exact):
    z = zero_like(exact)
    out = []
    for row in A:
        s = z
        for a, b in zip(row, x):
            if a != 0 and b != 0:
                s = s + a * b
        out.append(s)
    return out


def dot(a, b, exact):
    s = zero_like(exact)
    for x, y in zip(a, b):
        if x != 0 and y != 0:
            s = s + x * y
    return s


class GeneralSolver:
    """Row-reduction of a (possibly rectangular / singular) matrix M.

    Provides: rank, a particular solution of M z = y for consistent y (free variables 0),
    a basis of the left null space (rows l with l M = 0) and of the right null space.
    """

    def __init__(self, M, ncols, exact):
        self.exact = exact
        self.nrows = len(M)
        self.ncols = ncols
        R = [list(r) for r in M]
        E = eye(self.nrows, exact)
        scale = 1.0
        if not exact:
            for r in R:
                for v in r:
                    scale = max(scale, abs(v))
        self.scale = scale
        pivots = []
        row = 0
        for col in range(ncols):
            if row >= self.nrows:
                break
            # pivot choice
            best, bestval = None, None
            for i in range(row, self.nrows):
                v = R[i][col]
                if exact:
                    if v != 0:
                        best = i
                        break
                else:
                    if abs(v) > FLOAT_TOL * scale and (bestval is None or abs(v) > bestval):
                        best, bestval = i, abs(v)
            if best is None:
                continue
            R[row], R[best] = R[best], R[row]
            E[row], E[best] = E[best], E[row]
            pv = R[row][col]
            inv = (Fraction(1) / pv) if exact else 1.0 / pv
            R[row] = [v * inv for v in R[row]]
            E[row] = [v * inv for v in E[row]]
            for i in range(self.nrows):
                if i != row:
                    f = R[i][col]
                    if f != 0 and (exact or abs(f) > 0.0):
                        Rr, Er = R[row], E[row]
                        R[i] = [a - f * b for a, b in zip(R[i], Rr)]
                        E[i] = [a - f * b for a, b in zip(E[i], Er)]
                        if not exact:
                            R[i][col] = 0.0
            pivots.append(col)
            row += 1
        self.rank = row
        self.pivots = pivots
        self.R = R
        self.E = E
        # clean float rows
        self.left_null = [E[i] for i in range(self.rank, self.nrows)]
        piv_set = set(pivots)
        self.free = [c for c in range(ncols) if c not in piv_set]
        self.right_null = []
        for f in self.free:
            v = [zero_like(exact)] * ncols
            v[f] = one_like(exact)
            for i, pc in enumerate(pivots):
                v[pc] = -R[i][f]
            self.right_null.append(v)

    def particular(self, y):
        """Particular solution of M z = y (assumes consistency), free variables = 0."""
        ey = matvec(self.E, y, self.exact)
        z = [zero_like(self.exact)] * self.ncols
        for i, pc in enumerate(self.pivots):
            z[pc] = ey[i]
        return z

    def particular_matrix(self):
        """Matrix S with z = S y (generalized inverse consistent with `particular`)."""
        S = zeros(self.ncols, self.nrows, self.exact)
        for i, pc in enumerate(self.pivots):
            S[pc] = list(self.E[i])
        return S


# ----------------------------------------------------------------- matrix exponential

def expm_float(A):
    """exp(A) for a small float matrix: scaling and squaring with a Taylor series."""
    n = len(A)
    if n == 0:
        return []
    A = [[float(v) for v in r] for r in A]
    norm = max(sum(abs(v) for v in r) for r in A)
    s = 0
    if norm > 0.5:
        s = int(math.ceil(math.log2(norm / 0.5)))
    scale = 2.0 ** (-s)
    As = [[v * scale for v in r] for r in A]
    result = eye(n, False)
    term = eye(n, False)
    for k in range(1, 30):
        term = matmul(term, As, False)
        term = [[v / k for v in r] for r in term]
        result = [[a + b for a, b in zip(r1, r2)] for r1, r2 in zip(result, term)]
        if max(abs(v) for r in term for v in r) < 1e-18:
            break
    for _ in range(s):
        result = matmul(result, result, False)
    return result


def nilpotent_powers(A, exact, maxdeg=None):
    """Return [I, A, A^2, ...] up to the last nonzero power if A is nilpotent, else None."""
    n = len(A)
    if maxdeg is None:
        maxdeg = n + 1
    powers = [eye(n, exact)]
    P = A
    for _ in range(maxdeg):
        if all(v == 0 for r in P for v in r):
            return powers
        powers.append(P)
        P = matmul(P, A, exact)
    return None


# ----------------------------------------------------------------- polynomials (coefficient lists, low order first)

def poly_trim(p):
    p = list(p)
    while len(p) > 1 and p[-1] == 0:
        p.pop()
    return p


def poly_add(a, b):
    n = max(len(a), len(b))
    out = []
    for i in range(n):
        x = a[i] if i < len(a) else 0
        y = b[i] if i < len(b) else 0
        out.append(x + y)
    return out


def poly_scale(a, c):
    return [c * x for x in a]


def poly_mul(a, b):
    if not a or not b:
        return [0]
    out = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        if x == 0:
            continue
        for j, y in enumerate(b):
            if y != 0:
                out[i + j] = out[i + j] + x * y
    return out


def poly_eval(p, t):
    s = 0
    for c in reversed(p):
        s = s * t + c
    return s


def poly_integral(p, h):
    """Definite integral of p over [0, h]."""
    s = 0
    hp = h
    for k, c in enumerate(p):
        if c != 0:
            s = s + c * hp / (k + 1)
        hp = hp * h
    return s


def poly_deriv(p):
    return [c * k for k, c in enumerate(p)][1:] or [0]


def sign_after(p, t, exact):
    """Sign of the polynomial immediately to the right of t (+1, -1 or 0 if identically 0)."""
    q = list(p)
    while True:
        v = poly_eval(q, t)
        if exact:
            if v != 0:
                return 1 if v > 0 else -1
        else:
            if abs(v) > 1e-14:
                return 1 if v > 0 else -1
        if len(q) <= 1:
            return 0
        q = poly_deriv(q)


def _isqrt_fraction(x: Fraction):
    if x < 0:
        return None
    n, d = x.numerator, x.denominator
    rn, rd = math.isqrt(n), math.isqrt(d)
    if rn * rn == n and rd * rd == d:
        return Fraction(rn, rd)
    return None


def poly_roots_in(p, lo, hi, exact):
    """Sorted real roots of p in (lo, hi]. Returns (roots, all_exact)."""
    p = poly_trim(p)
    deg = len(p) - 1
    if deg <= 0:
        return [], True
    if deg == 1:
        r = -p[0] / p[1]
        return ([r] if lo < r <= hi else []), True
    if deg == 2 and exact:
        a, b, c = p[2], p[1], p[0]
        disc = b * b - 4 * a * c
        if disc < 0:
            return [], True
        sq = _isqrt_fraction(Fraction(disc))
        if sq is not None:
            rs = sorted({(-b - sq) / (2 * a), (-b + sq) / (2 * a)})
            return [r for r in rs if lo < r <= hi], True
    # general: monotone pieces between critical points, bisection
    crit, _ = poly_roots_in(poly_deriv(p), lo, hi, exact)
    pts = [lo] + [c for c in crit if lo < c < hi] + [hi]
    roots = []
    for a, b in zip(pts[:-1], pts[1:]):
        fa, fb = poly_eval(p, a), poly_eval(p, b)
        if fb == 0:
            roots.append(b)
            continue
        if fa == 0 or (fa > 0) == (fb > 0):
            continue
        x0, x1 = (float(a), float(b)) if not exact else (a, b)
        f0 = fa
        for _ in range(200 if exact else 120):
            m = (x0 + x1) / 2
            fm = poly_eval(p, m)
            if fm == 0:
                x0 = x1 = m
                break
            if (fm > 0) == (f0 > 0):
                x0, f0 = m, fm
            else:
                x1 = m
            if exact and (x1 - x0) < Fraction(1, 10 ** 40):
                break
        roots.append(x1)
    return sorted(set(roots)), False
