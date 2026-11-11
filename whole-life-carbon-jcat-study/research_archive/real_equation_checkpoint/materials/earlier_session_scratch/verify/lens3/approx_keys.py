import json
R = "/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY"
ap = json.load(open(R+"/04_VERIFICATION/approximation_study.json", encoding="utf-8"))["candidates"]
for cid, c in ap.items():
    extra = [k for k in c if k not in ("candidate_id","title","replaces","stage","units","stage_error","total_error","within_stage_target","within_total_target","under_estimates")]
    bg = c.get("by_group", {})
    kinds = sorted({k.split("=")[0] for k in bg})
    print(cid, "| stage:", c["stage"], "| units:", c["units"], "| n:", c["stage_error"]["n"], "| by_group dims:", kinds, "| extra keys:", extra, "| under:", c["under_estimates"], "| within stage/total:", c["within_stage_target"], c["within_total_target"])
print(json.dumps(ap["AP-06"]["stage_error"]), json.dumps(ap["AP-06"]["total_error"]))
print("AP-06 replaces:", ap["AP-06"]["replaces"])
print("AP-09a:", json.dumps(ap["AP-09a"]["stage_error"]), json.dumps(ap["AP-09a"]["total_error"]))
print("AP-04:", json.dumps(ap["AP-04"]["total_error"]))
