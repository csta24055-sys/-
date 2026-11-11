"""Strict (no floor) comparison on the study's own scenario list (imported generator function only; nothing is written)."""
from h import *
from bench import verify_unified as vu
import collections
n = 0; worst = collections.Counter(); bad = []; maxrel = 0.0; maxitem = None
for group, scn in vu.scenarios(400, 60):
    n += 1
    ref, full, tot = run3(scn)
    exc = [isinstance(x, Exception) for x in (ref, full, tot)]
    if any(exc):
        if not (all(exc) and type(ref) is type(full) is type(tot)): bad.append((group, scn.meta.scenario_id, "CRASH"))
        continue
    for uid in ref:
        for mode, cand, im in (("full", full, False), ("tot", tot, True)):
            for d in diffs(ref[uid], cand.get(uid, {}), 0.0, 0.0, ignore_missing=im):
                rel = d[3]
                if rel is None or rel != rel or rel > 1e-9:
                    bad.append((group, scn.meta.scenario_id, mode, uid) + d)
                elif rel > maxrel:
                    maxrel = rel; maxitem = (group, scn.meta.scenario_id, mode, uid) + d
print("scenarios:", n, "| leaves differing by more than 1e-9 relative WITHOUT any floor:", len(bad))
by = collections.Counter((b[0].split(":")[0], b[3] if len(b) > 3 else "", ) for b in bad)
print(by.most_common(20))
for b in bad[:12]: print("   ", b)
print("largest relative difference below 1e-9:", maxrel, maxitem)
