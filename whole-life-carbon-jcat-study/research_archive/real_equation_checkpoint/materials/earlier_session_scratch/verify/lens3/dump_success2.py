import json, collections
R = "/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY"
d = json.load(open(R+"/03_MODELS/records/units.json", encoding="utf-8"))
recs = d["records"]
for r in recs:
    if r["outcome"] == "SUCCESS" and r["step"] in ("M1","M6"):
        print(f'{r["unit_id"]} {r["step"]} | {r["title"]}')
print("---- M2 titles distinct")
c = collections.Counter(r["title"] for r in recs if r["outcome"]=="SUCCESS" and r["step"]=="M2")
for k,v in c.items(): print(v, k)
