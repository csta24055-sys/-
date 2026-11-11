import json
R = "/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY"
ap = json.load(open(R+"/04_VERIFICATION/approximation_study.json", encoding="utf-8"))["candidates"]
f = lambda s: {k: (round(v*100, 2) if isinstance(v, float) else v) for k, v in s.items()}
for cid in ("AP-09a", "AP-09b"):
    for k, v in ap[cid]["by_grid_kind"].items(): print(cid, k, f(v))
for k, v in ap["AP-08"]["by_profile_kind"].items(): print("AP-08", k, f(v))
print("AP-14 note:", ap["AP-14"].get("note"))
print("AP-12 dd:", ap["AP-12"].get("data_dependence"))
print("AP-16 nparam:", ap["AP-16"].get("n_parameters"))
for k, v in ap["AP-05"]["by_rate_times_cycle_years_no_top_up_devices"].items(): print("AP-05", k, f(v))
