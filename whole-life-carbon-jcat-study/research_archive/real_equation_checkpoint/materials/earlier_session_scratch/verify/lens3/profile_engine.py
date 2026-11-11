import cProfile, pstats, io, time, gc
from fastcalc import engine
from refcalc import registry
from synth import population
registry.load_all()
scn = population.standard_benchmark()[1]
engine.evaluate(scn, detail=False)
pr = cProfile.Profile(); pr.enable()
for _ in range(5): engine.evaluate(scn, detail=False)
pr.disable()
s = io.StringIO(); pstats.Stats(pr, stream=s).sort_stats("tottime").print_stats(9); print(s.getvalue()[:2200])
# how much of the totals-only run is the SYS-01 state pass?  Time evaluate with see() replaced by a no-op via a patched copy of the source
import inspect, types
src = inspect.getsource(engine)
patched = src.replace("    def see(owner, name, value, path):\n", "    def see(owner, name, value, path):\n        return\n", 1)
assert patched != src
mod = types.ModuleType("engine_nosee"); mod.__dict__["__package__"] = "fastcalc"; mod.__dict__["__name__"] = "fastcalc.engine_nosee"
exec(compile(patched, "engine_nosee", "exec"), mod.__dict__)
def med(fn, n=9):
    ts = []
    for _ in range(n):
        gc.collect(); t = time.perf_counter(); fn(); ts.append(time.perf_counter() - t)
    return sorted(ts)[n // 2] * 1000
a = med(lambda: engine.evaluate(scn, detail=False)); b = med(lambda: mod.evaluate(scn, detail=False))
print("totals-only M: %.1f ms ; with the SYS-01 per-field state pass removed: %.1f ms ; share of SYS-01 pass: %.0f%%" % (a, b, 100 * (a - b) / a))
