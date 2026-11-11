"""Own strict (no floor) rerun over the study's scenario list; own comparison code."""
from vh import *
from common.compare import flatten
from bench import verify_unified as vu
def isnum(x): return isinstance(x, (int, float)) and not isinstance(x, bool)
n = 0; bad = []; mx = 0.0; mxi = None; crash = []; nleaves = 0; extra = 0; inf_leaves = 0; below = 0
for group, scn in vu.scenarios(400, 60):
    n += 1
    r, f, t = three(scn)
    ex = [isinstance(x, Exception) for x in (r, f, t)]
    if any(ex):
        if not (all(ex) and type(r) is type(f) is type(t)): crash.append((group, scn.meta.scenario_id))
        continue
    fl = 1e-9 * (abs(r["SUM-03"]["value"]) or 1.0)
    for u in r:
        fr = flatten(r[u])
        for mode, cand in (("full", f), ("tot", t)):
            fc = flatten(cand.get(u, {}))
            extra += len(set(fc) - set(fr))
            for p, rv in fr.items():
                if p not in fc:
                    if mode == "full": bad.append((group, u, p, "missing"))
                    continue
                cv = fc[p]
                if isnum(rv) and isnum(cv):
                    nleaves += 1
                    if math.isnan(rv) or math.isnan(cv):
                        if not (math.isnan(rv) and math.isnan(cv)): bad.append((group, u, p, rv, cv))
                        continue
                    if rv == cv: continue
                    if math.isinf(rv) or math.isinf(cv): inf_leaves += 1; bad.append((group, u, p, rv, cv)); continue
                    rel = abs(cv - rv) / max(abs(rv), abs(cv))
                    if abs(rv) < fl and mode == "full" and rel > 1e-9: below += 1
                    if rel > 1e-9: bad.append((group, u, p, rv, cv, rel))
                    elif rel > mx: mx = rel; mxi = (group, scn.meta.scenario_id, mode, u, p, rv, cv)
                else:
                    if type(rv) is not type(cv) or rv != cv: bad.append((group, u, p, rv, cv))
print("scenarios", n, "numeric leaf comparisons", nleaves, "crash asymmetries", crash, "extra leaves", extra)
print("strict differences (>1e-9 rel, no floor, type-strict):", len(bad)); [print("   ", b) for b in bad[:15]]
print("largest rel diff <= 1e-9:", mx, mxi)
