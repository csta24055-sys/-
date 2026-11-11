import json, collections
R = "/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY"
d = json.load(open(R+"/03_MODELS/records/units.json", encoding="utf-8"))
recs = d["records"]
for oc in ("NOT_APPLICABLE","REJECTED","HOLD"):
    c = collections.defaultdict(list)
    for r in recs:
        if r["outcome"] == oc:
            c[(r["step"], r["title"], r["reason"], r["verification"], r.get("candidate_id") if oc!="NOT_APPLICABLE" else None, r.get("data_needed"))].append(r["unit_id"])
    print("=========", oc, "distinct:", len(c))
    for k, v in sorted(c.items(), key=lambda kv: (kv[0][0], -len(kv[1]))):
        print(f'[{k[0]}] n={len(v)} cand={k[4]} verif={k[3]}\n   title: {k[1]}\n   reason: {k[2]}\n   data: {k[5]}\n   units: {", ".join(v)}')
