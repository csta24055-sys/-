"""Count what the unified engine really does per row (M benchmark, totals-only and full mode)."""
import sys, collections, copy
from fastcalc import engine
from refcalc import registry
from synth import population
registry.load_all()
bench = population.standard_benchmark()
scn = bench[1]   # M: 2000 materials, 600 equipment, 40 refrigerants
print("rows", len(scn.materials), len(scn.equipment), len(scn.refrigerants), "factors", len(scn.factors),
      "provenance records", len(scn.provenance), "unit conversions", len(scn.unit_conversions))

class Proxy:
    __slots__ = ("_r",)
    n_value = 0
    def __init__(self, r): object.__setattr__(self, "_r", r)
    def __getattr__(self, name):
        if name == "value":
            Proxy.n_value += 1
        return getattr(object.__getattribute__(self, "_r"), name)

class CountDict(dict):
    n_get = 0
    def get(self, k, d=None):
        CountDict.n_get += 1
        return dict.get(self, k, d)

def run(detail):
    s = copy.copy(scn)
    s.factors = {k: Proxy(v) for k, v in scn.factors.items()}
    s.provenance = CountDict(scn.provenance)
    Proxy.n_value = 0; CountDict.n_get = 0
    calls = collections.Counter()
    def prof(frame, event, arg):
        if event == "call":
            calls[frame.f_code.co_name] += 1
    engine.clear_baseline_cache()
    # warm the baseline cache without instrumentation so that only this scenario is counted
    engine.evaluate(scn, detail=False)
    sys.setprofile(prof)
    try:
        R = engine.evaluate(s, detail=detail)
    finally:
        sys.setprofile(None)
    print(f"--- detail={detail}")
    print("   factor .value reads:", Proxy.n_value, "| distinct factor ids used (QA-03 n_used):", R["QA-03"]["n_used"])
    print("   provenance.get calls:", CountDict.n_get, "| distinct provenance ids:", len(scn.provenance), "| SYS-01 counts:", sum(R["SYS-01"]["counts"].values()))
    print("   closure calls:", {k: calls[k] for k in ("see", "fac", "conv", "add", "conversion_factor", "renewal_count", "skip_weight_periodic", "refrigerant_device", "linear_weighted_sum", "grid_cumulative", "annual", "series_of")})
    print("   SYS-02 n_checked:", R["SYS-02"]["n_checked"])
    return R
r0 = run(False)
r1 = run(True)
# distinct keys
recipes = {tuple((c.factor_id, c.mass_fraction) for c in row.composition) for row in scn.materials if row.composition is not None}
ncomp = sum(1 for row in scn.materials if row.composition is not None)
print("composite rows", ncomp, "distinct recipes", len(recipes), "components visited per row to build key:", sum(len(row.composition) for row in scn.materials if row.composition is not None))
print("distinct refresh cycles (materials):", len({row.refresh_cycle for row in scn.materials}), "distinct service lives (equipment):", len({e.service_life for e in scn.equipment}))
print("rows with row-level conversions:", sum(1 for row in scn.materials if row.conversions), "of", len(scn.materials))
op = scn.operation
print("profile kinds:", op.electricity.kind, op.onsite_generation.kind, op.onsite_export.kind, "grid", op.grid.kind, "gas", op.gas.kind)
print("refrigerant distinct (rate, top_up, life):", len({(d.annual_leak_rate, d.top_up, d.service_life) for d in scn.refrigerants}), "of", len(scn.refrigerants))
