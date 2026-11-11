"""Evaluate the declared conclusions of tools/build_records.conclusions against a NEW approximation_study.json.

The new schema is presented to the unchanged function through an adapter (total_error <- local_total_error,
AP-05 <- AP-05b); nothing is written. Prints for every existing candidate whether its declared condition still
holds and the text the function would produce from the new numbers. Usage: concl_check.py NEW.json
"""
import inspect, json, sys
sys.path.insert(0, "/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/research_code")
import tools.build_records as br
new = json.load(open(sys.argv[1], encoding="utf-8"))["candidates"]
ap = {}
for cid, c in new.items():
    c = dict(c)
    c["total_error"] = c.get("local_total_error")
    ap[cid] = c
ap["AP-05"] = ap["AP-05b"]
src = inspect.getsource(br.conclusions)
src = src.replace('raise SystemExit(f"declared conclusion of {cid} contradicts the measured statistics")', 'FAILED.append(cid)')
src = src.replace('raise SystemExit(f"measured candidates without a conclusion: {sorted(missing)}")', 'MISSING.extend(sorted(missing))')
ns = dict(vars(br)); ns["FAILED"] = []; ns["MISSING"] = []
exec(src, ns)
out = ns["conclusions"](ap)
print("conditions that no longer hold:", ns["FAILED"])
print("candidates without a conclusion:", ns["MISSING"])
for cid, (outcome, ver, ok, text, data) in out.items():
    print(f"--- {cid} {outcome} {ver} ok={ok}\n    {text}")
