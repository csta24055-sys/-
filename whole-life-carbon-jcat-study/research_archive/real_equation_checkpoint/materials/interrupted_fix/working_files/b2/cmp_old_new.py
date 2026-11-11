"""Check that every statistic of the OLD approximation_study.json is still present, bit for bit, in the NEW one.

Usage: cmp_old_new.py OLD.json NEW.json
Mapping of renamed places: AP-05 -> AP-05b; total_error -> local_total_error; for the electricity candidates the old
stage_error (measured on B6-03) -> other_targets['B6-03（= B6＋B2 ...）'], old by_profile_kind / by_grid_kind -> *_B6_03.
Leaves that differ are listed with old and new value.
"""
import json, sys
old = json.load(open(sys.argv[1], encoding="utf-8")); new = json.load(open(sys.argv[2], encoding="utf-8"))
OC, NC = old["candidates"], new["candidates"]
B603 = "B6-03（= B6＋B2。従来「B6 段階」として公表していた量）"
ELEC = ("AP-08", "AP-09a", "AP-09b", "AP-09c", "AP-13")
n = {"same": 0, "diff": 0, "missing": 0}
diffs = []
def walk(o, v, path):
    if isinstance(o, dict):
        if not isinstance(v, dict):
            n["missing"] += 1; diffs.append(("MISSING/TYPE", path, type(v).__name__)); return
        for k, x in o.items():
            k2 = "local_total_error" if k == "total_error" else k
            if k2 not in v:
                n["missing"] += 1; diffs.append(("MISSING", path + "/" + k, None)); continue
            walk(x, v[k2], path + "/" + k)
    elif isinstance(o, list):
        if o != v: n["diff"] += 1; diffs.append(("DIFF", path, (o, v)))
        else: n["same"] += 1
    else:
        if o == v or (o != o and v != v): n["same"] += 1
        else: n["diff"] += 1; diffs.append(("DIFF", path, (o, v)))
for cid, oc in OC.items():
    ncid = "AP-05b" if cid == "AP-05" else cid
    if ncid not in NC:
        n["missing"] += 1; diffs.append(("MISSING CANDIDATE", cid, None)); continue
    nc = NC[ncid]
    for k, x in oc.items():
        path = cid + "/" + k
        if k in ("candidate_id",) and cid == "AP-05": continue
        if cid in ELEC and k == "stage_error":
            walk(x, nc["other_targets"][B603], path + "->other_targets[B6-03]"); continue
        if cid in ELEC and k == "by_group":
            # the breakdown by structure/use now follows the primary quantity (stage B6): not comparable
            continue
        if cid == "AP-08" and k == "by_profile_kind":
            walk(x, nc["by_profile_kind_B6_03"], path + "->_B6_03"); continue
        if cid in ("AP-09a", "AP-09b") and k == "by_grid_kind":
            walk(x, nc["by_grid_kind_B6_03"], path + "->_B6_03"); continue
        k2 = "local_total_error" if k == "total_error" else k
        if k2 not in nc:
            n["missing"] += 1; diffs.append(("MISSING", path, None)); continue
        walk(x, nc[k2], path)
for k, x in old.items():
    if k == "candidates": continue
    if k not in new: n["missing"] += 1; diffs.append(("MISSING", "/" + k, None)); continue
    walk(x, new[k], "/" + k)
print(n)
import collections
kinds = collections.Counter()
for kind, path, val in diffs:
    cid = path.split("/")[0]; key = path.split("/")[1] if "/" in path else ""
    kinds[(kind, cid, key.split("->")[0])] += 1
for (kind, cid, key), c in sorted(kinds.items()):
    print(f"{kind:8s} {cid:8s} {key:40s} x{c}")
if "-v" in sys.argv:
    for kind, path, val in diffs: print(kind, path, val)
