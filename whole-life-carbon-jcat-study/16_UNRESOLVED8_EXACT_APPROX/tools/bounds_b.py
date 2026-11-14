"""Approximation error of the piece polynomials (methods A and B) for x^a and log10 x, sampled densely on every
piece in 60-digit decimal arithmetic, plus the analytic remainder bound of polynomial interpolation for x^a:
|g - p| <= max|g^(n+1)| / (n+1)! * prod|t - t_j| * h^(n+1),  prod over the n+1 nodes, t in [-1, 1].
Usage: bounds_b.py <exponent> [<exponent> ...]  (log10 is always included)"""
import os, sys, json, math
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from decimal import Decimal as D
import decimal
import exact8 as E8

decimal.getcontext().prec = 60
SAMPLES = 96


def node_poly_max(n):
    nodes = [D(t) for t in E8._nodes(n)]
    best = D(0)
    for k in range(4001):
        t = D(-1) + D(2) * D(k) / D(4000)
        v = D(1)
        for tj in nodes:
            v *= abs(t - tj)
        best = max(best, v)
    return best


def run(kind, a):
    fn = E8.fn_pow(a) if kind == "pow" else E8.fn_q()
    out = {}
    for meth, deg in (("A", E8.DEG_A), ("B", E8.DEG_B)):
        co = E8.coefficients(kind, a, deg)
        worst_rel = D(0)
        for i in range(E8.PIECES):
            c = D(E8.P_LO) + (D(i) + D("0.5")) * D(E8.P_W)
            h = D(E8.P_W) / 2
            cs = [D(str(x)) if meth == "A" else D(float(x)) for x in co[i]]
            for k in range(SAMPLES + 1):
                t = D(-1) + D(2) * D(k) / D(SAMPLES)
                p = D(0)
                for cc in reversed(cs):
                    p = p * t + cc
                g = fn(c + h * t)
                if g != 0:
                    worst_rel = max(worst_rel, abs(p - g) / abs(g))
        rec = dict(deg=deg, sampled_max_rel=float(worst_rel), log2=float(math.log2(worst_rel)) if worst_rel > 0 else None)
        if kind == "pow":
            n = deg
            prodmax = node_poly_max(n)
            coef = D(1)
            for j in range(n + 1):
                coef *= abs(D(a) - j)
            fmin = D(E8.P_LO)
            # max |g^(n+1)| / min |g| over the pieces (relative bound), h = 1/128 in f per unit of t
            rel = coef * fmin ** (-(n + 1)) / math.factorial(n + 1) * prodmax * (D(E8.P_W) / 2) ** (n + 1)
            rec["analytic_rel_bound"] = float(rel)
            rec["analytic_log2"] = float(math.log2(rel))
        out[meth] = rec
    return out


if __name__ == "__main__":
    res = {}
    for a in [float(x) for x in sys.argv[1:]]:
        res["pow %r" % a] = run("pow", a)
        print("pow", a, res["pow %r" % a], flush=True)
    res["log10"] = run("log", None)
    print("log10", res["log10"], flush=True)
    json.dump(res, open(os.environ.get("OUT", "/dev/null"), "w"), indent=1) if os.environ.get("OUT") else None
