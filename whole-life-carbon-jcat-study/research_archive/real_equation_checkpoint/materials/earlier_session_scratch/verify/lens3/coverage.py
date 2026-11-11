import json, collections
R = "/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY"
J = lambda p: json.load(open(R+"/"+p, encoding="utf-8"))
cov = J("01_LEDGER/sheet_family_coverage.json"); units = J("01_LEDGER/units.json")["units"]; models = J("03_MODELS/models.json")["models"]
print(list(cov["families"][0].keys()))
ni = [f for f in cov["families"] if f["status"] == "NOT_INSPECTED"]
for f in ni:
    print({k: f[k] for k in f if k not in ("sheets",)})
# which units link to NOT_INSPECTED families
ni_ids = {f.get("family_id") or f.get("id") for f in ni}
print(ni_ids)
by_unit = {u["id"]: u.get("sheet_family_links") for u in units}
linked = {uid: [x for x in (l or []) if (x if isinstance(x, str) else x.get("family_id")) in ni_ids] for uid, l in by_unit.items()}
print("units linked to NOT_INSPECTED families:", {k: v for k, v in linked.items() if v})
mm = {x: m["id"] for m in models for x in m["units"]}
agg = collections.defaultdict(set)
for uid, v in linked.items():
    for x in v:
        agg[mm.get(uid, "-")].add(x if isinstance(x, str) else x.get("family_id"))
print("models whose units link to NOT_INSPECTED families:", dict(agg))
print("example sheet_family_links:", by_unit["SYS-01"], by_unit["SUM-07"], by_unit["X-15"], by_unit["X-03"])
