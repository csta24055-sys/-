import json, collections
R = "/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY"
d = json.load(open(R+"/03_MODELS/records/units.json", encoding="utf-8"))
recs = d["records"]
print(collections.Counter(r["outcome"] for r in recs))
print(collections.Counter((r["step"], r["outcome"]) for r in recs))
print(collections.Counter(r["verification"] for r in recs))
for r in recs:
    if r["outcome"] == "SUCCESS":
        print(f'## {r["unit_id"]} {r["step"]} [{r["candidate_id"]}] {r["unified_model"]} | {r["title"]}')
        print("   reason:", r["reason"])
        print("   evid:", json.dumps(r["evidence"], ensure_ascii=False)[:400])
