"""The recorded exactness run uses standard_benchmark()[:2] (S, M). Check size L, which all headline load figures use."""
import inspect
from bench import verify_unified
from common.compare import compare
from fastcalc import engine
from refcalc import registry
from synth import population
registry.load_all()
print([l.strip() for l in inspect.getsource(verify_unified.scenarios).splitlines() if "standard_benchmark" in l])
scn = population.standard_benchmark()[2]
print("size", scn.meta.size_class, len(scn.materials), len(scn.equipment), len(scn.refrigerants))
ref = registry.run_all(scn)
engine.clear_baseline_cache()
full = engine.evaluate(scn, detail=True)
warm = engine.evaluate(scn, detail=True)       # warm baseline cache: the configuration behind the 472 ms figure
summ = engine.evaluate(scn, detail=False)
scale = abs(ref["SUM-03"]["value"]) or 1.0
worst = 0.0; n = 0; bad = []
for uid, rv in ref.items():
    for tag, res, kw in (("full", full, {}), ("warm", warm, {}), ("summary", summ, {"ignore_missing": True})):
        c = compare(rv, res.get(uid, {}), floor=1e-9 * scale, **kw)
        n += c.n_numeric
        worst = max(worst, c.max_abs_rel_error)
        if not c.within(1e-9) or (tag != "summary" and c.extra):
            bad.append((uid, tag, c.max_abs_rel_error, c.worst_path))
print("numeric leaves compared:", n, "worst relative difference:", worst, "failures:", bad)
print("SUM-03 ref", ref["SUM-03"]["value"], "fast", full["SUM-03"]["value"])
