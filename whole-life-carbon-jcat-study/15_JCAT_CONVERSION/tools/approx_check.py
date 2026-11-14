"""Accuracy of the APPROXIMATION improvement (x^m, log10 x): converted form vs float64 libm on dense grids."""
import sys, os, collections, json
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, compile2 as K
from tstudy import msp
from decimal import Decimal, getcontext
getcontext().prec = 40

def run(xs, kind, m=None):
    B = K.Builder.__new__(K.Builder)
    B.tabs = K.Tables(); B.n = len(xs); B.steps = []; B.k = 0; B.notes = collections.Counter(); B.improve = True; B.memo = {}
    K.index.put_table(B.tabs, "G", {"x": xs})
    if kind == "pow":
        v = B.approx_power("x", K.C(0), K.C(0), m)
        out = v.c["n"]
    else:
        dv, ym = B.mantissa_poly("x", lambda u: np.log10(u))
        out = B.sp([[dv], [ym]], hint="lg")
    eng = msp.Engine(B.tabs); eng.run(msp.Program({"name": "t", "units": [{"id": "P", "steps": B.steps, "outputs": {}}]}))
    return eng.operand("G", out).v, len(B.steps)

def exact(xs, kind, m=None):
    out = []
    for x in xs:
        d = Decimal(float(x))
        out.append(float((d.ln() * Decimal(m)).exp()) if kind == "pow" else float(d.ln() / Decimal(10).ln()))
    return np.array(out)

rng = np.random.default_rng(7)
res = {}
for label, xs in (("wide 1e-6..1e12", 10 ** rng.uniform(-6, 12, 20000)), ("domain 3e4..5e6", rng.uniform(3e4, 5e6, 20000)),
                  ("domain 5e3..3e6", rng.uniform(5e3, 3e6, 20000))):
    for kind, m in (("pow", 0.05416), ("pow", -0.06254), ("log", None)):
        got, nsteps = run(xs, kind, m)
        ref = exact(xs, kind, m)
        rel = np.abs(got - ref) / np.maximum(np.abs(ref), 1e-300)
        key = "%s %s %s" % (label, kind, m)
        res[key] = dict(points=len(xs), max_rel=float(rel.max()), median_rel=float(np.median(rel)), steps=nsteps)
        print(key, res[key], flush=True)
json.dump(res, open(sys.argv[1], "w"), indent=1)
