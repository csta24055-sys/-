from h import *
from common.compare import compare, flatten
import collections, re
for scn in population.standard_benchmark()[:2]:
    ref = registry.run_all(scn)
    scale = abs(ref["SUM-03"]["value"]); floor = 1e-9 * scale
    n = below = 0; pats = collections.Counter()
    for uid, r in ref.items():
        for p, v in flatten(r).items():
            if isnum(v) and v != 0:
                n += 1
                if abs(v) < floor:
                    below += 1; pats[uid + ":" + re.sub(r"\[\d+\]", "[]", p)] += 1
    print(f"size {scn.meta.size_class}: SUM-03 {scale:.4g}, floor {floor:.3g}; non-zero numeric leaves {n}, of which below the floor {below} ({100*below/n:.1f}%)")
    print("    most frequent patterns below the floor:", pats.most_common(12))
    # effect: a dimensionless leaf changed by a relative 1e-7 still passes
    full = engine.evaluate(scn, detail=True)
    for uid, key in (("SUM-07", "by_stage"),):
        small = min((s for s in ref[uid][key] if ref[uid][key][s] > 0), key=lambda s: ref[uid][key][s])
        v = ref[uid][key][small]
        for rel in (1e-8, 1e-7, 1e-6, 1e-5):
            cand = copy.deepcopy(full[uid]); cand[key][small] = v * (1 + rel)
            c = compare(ref[uid], cand, floor=floor)
            print(f"    SUM-07.by_stage.{small} = {v:.3e} changed by relative {rel:g}: study comparison within(1e-9) = {c.within(1e-9)} (reported error {c.max_abs_rel_error:.2e})")
