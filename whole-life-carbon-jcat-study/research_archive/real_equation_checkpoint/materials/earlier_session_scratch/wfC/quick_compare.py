import sys, time, collections
import synth
from synth import population
from refcalc import registry
from fastcalc import engine
from common.compare import compare
registry.load_all()

def check(name, scn, verbose=True):
    ref = registry.run_all(scn)
    fast = engine.evaluate(scn)
    scale = abs(ref['SUM-03']['value']) or 1.0
    worst = []
    for uid in ref:
        c = compare(ref[uid], fast.get(uid, {}), floor=1e-9*scale)
        if c.mismatches or c.missing or c.extra or c.max_abs_rel_error > 1e-9:
            worst.append((uid, c.max_abs_rel_error, c.worst_path, c.mismatches[:2], c.missing[:2], c.extra[:2]))
    if worst and verbose:
        print('==', name)
        for w in worst[:12]: print('   ', w)
    return worst

bad = 0
for scn in population.standard_benchmark()[:2]:
    bad += bool(check('bench '+scn.meta.size_class, scn))
for name, scn in population.edge_cases():
    bad += bool(check('edge '+name, scn))
for seed in (3, 4, 5):
    bad += bool(check(f'dirty {seed}', synth.make_scenario(seed, "RC", "office", "S", dirty=True)))
print('scenarios with differences:', bad)
