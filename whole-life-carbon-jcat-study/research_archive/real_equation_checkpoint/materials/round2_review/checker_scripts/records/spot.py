import copy, random, math
import synth
from synth import population, model
from fastcalc import engine, closed_forms as cf
from refcalc import registry, base
from common.compare import compare
registry.load_all()
# 1. count mismatches of renewal_count only
rnd = random.Random(99); bad = 0; n = 0
for _ in range(300000):
    T = rnd.choice([rnd.uniform(0.05, 130.0), float(rnd.randint(1, 120)), rnd.randint(1, 1200) / 10.0])
    c = rnd.choice([rnd.uniform(0.02, 70.0), rnd.randint(1, 600) / 10.0, T / rnd.randint(1, 12), T / rnd.randint(1, 12) * (1 + rnd.choice([-1, 1]) * 10 ** rnd.uniform(-12, -8)), 1.000000001, None, 0.0, -3.0, float("inf"), float("nan")])
    n += 1
    if cf.renewal_count(T, c) != len(base.periodic_events(T, c)): bad += 1
print("renewal_count vs counting loop:", n, "cases, mismatches", bad)
# 2. own spot check of exactness on fresh seeds (not the study's seeds), both modes, all units
worst = 0.0; fails = []; k = 0
combos = [(s, u) for s in model.STRUCTURES for u in model.USES]
for i in range(60):
    s, u = combos[i % len(combos)]
    scn = synth.make_scenario(90000 + i, s, u, "S", (60.0, 42.5, 100.0, 7.3)[i % 4], dirty=(i % 3 == 0))
    try: ref = registry.run_all(scn)
    except Exception as e: ref = e
    for detail in (True, False):
        try: got = engine.evaluate(scn, detail=detail)
        except Exception as e: got = e
        if isinstance(ref, Exception) or isinstance(got, Exception):
            if type(ref) is not type(got): fails.append((i, detail, repr(ref)[:60], repr(got)[:60]))
            continue
        scale = abs(ref["SUM-03"]["value"]) or 1.0
        for uid in ref:
            c = compare(ref[uid], got.get(uid, {}), floor=1e-9 * scale, ignore_missing=not detail)
            worst = max(worst, c.max_abs_rel_error); k += c.n_numeric + c.n_other
            if not c.within(1e-9) or (detail and c.extra): fails.append((i, detail, uid, c.worst_path, c.max_abs_rel_error, c.mismatches[:1]))
print("spot check: 60 fresh scenarios x 2 modes,", k, "leaves, worst rel diff", worst, "failures", len(fails), fails[:5])
# 3. sweep on fresh scenarios
P = (10.0, 30.0, 42.5, 50.0, 60.0, 75.0, 99.9, 100.0, 120.0); worst = 0.0; nf = 0; k = 0
for i in range(8):
    scn = synth.make_scenario(91000 + i, combos[i][0], combos[i][1], "S", 60.0)
    scn.boundary.baseline_scenario = None
    try: got = engine.sweep(scn, P)
    except Exception as e: print("sweep error", e); continue
    for T in P:
        o = copy.deepcopy(scn); o.boundary.study_period = T
        ref = registry.run_all(o)
        for uid in ref:
            c = compare(ref[uid], got[T].get(uid, {}), floor=1e-9 * abs(ref["SUM-03"]["value"]), ignore_missing=True)
            worst = max(worst, c.max_abs_rel_error); k += c.n_numeric + c.n_other
            if not c.within(1e-9): nf += 1
print("sweep: 8 fresh scenarios x 9 periods, all units (not only the 22 listed):", k, "leaves, worst", worst, "failures", nf)
