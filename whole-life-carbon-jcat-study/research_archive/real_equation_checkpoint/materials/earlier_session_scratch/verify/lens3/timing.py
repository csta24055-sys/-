import gc, statistics, time, sys
from fastcalc import engine
from refcalc import registry
from synth import population
registry.load_all()
t0 = time.perf_counter()
bench = population.standard_benchmark()
print("benchmark build s", round(time.perf_counter()-t0, 1), flush=True)
def med(fn, reps, gc_on=True):
    fn()
    ts = []
    for _ in range(reps):
        gc.collect()
        if not gc_on:
            gc.disable()
        t = time.perf_counter_ns()
        fn()
        ts.append((time.perf_counter_ns() - t) / 1e6)
        gc.enable()
    return statistics.median(ts), min(ts), max(ts)
for scn in bench:
    size = scn.meta.size_class
    no_base = registry.order([u for u in registry.UNITS if u != "SUM-08"])
    def ref_all(): registry.run_all(scn)
    def ref_nb(): registry.run_all(scn, ids=no_base)
    def cold():
        engine.clear_baseline_cache(); engine.evaluate(scn, detail=True)
    def warm(): engine.evaluate(scn, detail=True)
    def summ(): engine.evaluate(scn, detail=False)
    reps = 5 if size != "L" else 3
    for gc_on in (True, False):
        r = {}
        for name, fn in (("ref_all", ref_all), ("ref_noSUM08", ref_nb), ("fast_cold", cold), ("fast_warm", warm), ("fast_summary", summ)):
            r[name] = med(fn, reps, gc_on)
        ra = r["ref_all"][0]
        print(size, "gc_on" if gc_on else "gc_off", {k: tuple(round(x, 1) for x in v) for k, v in r.items()})
        print("   reductions vs ref_all: cold %.1f%% warm %.1f%% summary %.1f%% | warm vs ref_noSUM08 %.1f%% | ref_all/ref_noSUM08 = %.2f" % (
            100*(1-r["fast_cold"][0]/ra), 100*(1-r["fast_warm"][0]/ra), 100*(1-r["fast_summary"][0]/ra),
            100*(1-r["fast_warm"][0]/r["ref_noSUM08"][0]), ra/r["ref_noSUM08"][0]), flush=True)
