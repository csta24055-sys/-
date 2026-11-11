"""'Change T: only the multipliers need recomputing' (03_MODELS/README). Is that what the engine does? Prototype for stage B4."""
import copy, time, gc, inspect
from fastcalc import engine, closed_forms as cf
from refcalc import registry
from synth import population
from bench.approx_study import per_renewal_emissions
registry.load_all()
print("entry points of fastcalc.engine:", [n for n, f in inspect.getmembers(engine, inspect.isfunction) if f.__module__ == engine.__name__])
scn = population.standard_benchmark()[1]
scn.boundary.baseline_scenario = None
res = registry.run_all(scn)
rows = per_renewal_emissions(scn, res)          # (cycle, u, explicit) per row; u does not depend on T
U = {}; explicit = []
for (cycle, u, ex), src in zip(rows, list(scn.materials) + list(scn.equipment)):
    if ex is not None:
        explicit.append((u, [t for t in src.replacement_event_list]))
    elif cycle:
        U[cycle] = U.get(cycle, 0.0) + u
print("rows:", len(rows), "distinct cycles:", len(U), "rows with explicit lists:", len(explicit), "table length:", len(scn.operation.electricity.table))
def b4_sweep(T):
    e = 0.0
    for c, u in U.items():
        e += cf.renewal_count(T, c) * u
    for u, ev in explicit:
        e += sum(1 for t in ev if 0 < t < T) * u
    return e
for T in (30.0, 42.5, 50.0, 60.0):
    s2 = copy.deepcopy(scn); s2.boundary.study_period = T
    gc.collect(); t0 = time.perf_counter(); full = engine.evaluate(s2, detail=False); t_full = time.perf_counter() - t0
    t0 = time.perf_counter(); fast = b4_sweep(T); t_sw = time.perf_counter() - t0
    ref_b4 = full["B4-02"]["value"]
    print(f"T={T:5.1f}  B4 engine {ref_b4:.6f}  sweep {fast:.6f}  rel diff {(fast-ref_b4)/ref_b4:+.2e}  | engine re-evaluation {t_full*1000:.1f} ms (all rows rescanned) vs multiplier-only B4 {t_sw*1000:.2f} ms")
