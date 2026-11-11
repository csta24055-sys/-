from fuzzlib import *
import random
for seed in (17207, 6494, 12208):
    # rebuild step by step to find the mutation that introduces the difference
    rng = random.Random(seed)
    s, T, log = build(seed)
    ref, full, tot = run3(s)
    d = [x for uid in ref for x in [(uid,) + y for y in diffs(ref[uid], full.get(uid, {}), 1e-9, 0.0)] if not x[0].startswith("B1")]
    print(seed, T, log, len(d))
    for x in d[:14]: print("    ", x)
    print("   gases", s.gases, "gwp", s.gwp)
    comp = [(i, r.quantity_unit, [(c.factor_id, c.mass_fraction) for c in r.composition], r.epd is not None) for i, r in enumerate(s.materials) if r.composition is not None]
    print("   composite rows:", comp[:6])
    print("   X-15 kinds:", ref["X-15"]["kind"])
    print("   X-04 ref by_stage_recomputed vs X-02 by_stage_all:", {k: (ref["X-04"]["by_stage_recomputed"][k], ref["X-02"]["by_stage_all"][k]) for k in ("A1-A3", "B3", "B4")})
    print("   QA-01 ref", ref["QA-01"], "unified", full["QA-01"])
