import synth
from fastcalc import engine
from refcalc import registry
from common.compare import compare
registry.load_all()
for seed, st, use, T in ((3, "S", "office", 60.0), (7, "RC", "office", 35.5)):
    scn = synth.make_scenario(seed, st, use, "S", T)
    i = next(i for i, r in enumerate(scn.materials) if r.repair_rate and r.repair_rate > 0)
    scn.materials[i].refresh_cycle = 1.000000001
    ref = registry.run_all(scn)
    for detail in (False, True):
        got = engine.evaluate(scn, detail=detail)
        floor = 1e-9 * abs(ref["SUM-03"]["value"])
        bad = {}
        for uid in ref:
            c = compare(ref[uid], got[uid], floor=floor, ignore_missing=not detail)
            if not c.within(1e-9): bad[uid] = (c.max_abs_rel_error, c.worst_path)
        print(seed, T, "detail", detail, "failing units:", bad)
