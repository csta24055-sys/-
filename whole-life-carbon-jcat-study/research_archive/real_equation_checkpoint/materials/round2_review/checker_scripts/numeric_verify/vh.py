"""Own harness (independent of the checker's h.py)."""
import sys, math, copy
sys.dont_write_bytecode = True
import synth
from synth import model, population
from refcalc import registry, base
from fastcalc import engine, closed_forms as cf
from common.compare import compare
registry.load_all()
SMALL = dict(n_materials=12, n_equipment=6, n_refrigerants=4)
nan, inf = float("nan"), float("inf")

def mk(seed=1, T=60.0, **o):
    d = dict(SMALL); d.update(o)
    return synth.make_scenario(seed, "RC", "office", "S", T, **d)

def run(fn):
    try:
        return fn()
    except Exception as e:
        return e

def three(s, held=None):
    return (run(lambda: registry.run_all(s)), run(lambda: engine.evaluate(s, detail=True, baseline_totals=held)),
            run(lambda: engine.evaluate(s, detail=False, baseline_totals=held)))

def study_fails(s):
    """The study's own comparison rule (as in bench/verify_unified): floor 1e-9*|SUM-03|, tol 1e-9."""
    r, f, t = three(s)
    if any(isinstance(x, Exception) for x in (r, f, t)):
        return ("EXC", repr(r)[:80] if isinstance(r, Exception) else "ok", repr(f)[:80] if isinstance(f, Exception) else "ok",
                repr(t)[:80] if isinstance(t, Exception) else "ok")
    scale = abs(r["SUM-03"]["value"]) or 1.0
    out = []
    for u in r:
        c = compare(r[u], f.get(u, {}), floor=1e-9 * scale)
        cs = compare(r[u], t.get(u, {}), floor=1e-9 * scale, ignore_missing=True)
        if not (c.within(1e-9) and not c.extra and cs.within(1e-9)):
            out.append((u, c.worst_path, c.max_abs_rel_error, c.mismatches[:2], cs.mismatches[:2]))
    return out

def g(x, u, k="value"):
    return repr(x)[:90] if isinstance(x, Exception) else x[u][k]
