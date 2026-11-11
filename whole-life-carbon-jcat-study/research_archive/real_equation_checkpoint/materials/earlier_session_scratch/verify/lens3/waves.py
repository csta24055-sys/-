import json, collections
R = "/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY"
J = lambda p: json.load(open(R+"/"+p, encoding="utf-8"))
led = J("05_DECISIONS/progress_ledger.json")["units"]; pri = {r["id"]: r for r in J("02_RANKING/research_priority.json")["units"]}
recs = J("03_MODELS/records/units.json")["records"]
steps = ["M1","M2","M3","M4","M5","M6"]
for grp_name, key in (("wave", lambda u: u["wave"]), ("in old top30 union", lambda u: bool(pri[u["id"]]["reference_top30"]))):
    agg = collections.defaultdict(collections.Counter)
    for u in led:
        for s in steps:
            agg[key(u)][u["steps"][s]["conclusion"]] += 1
        agg[key(u)]["units"] += 1
    for k in sorted(agg, key=str):
        c = agg[k]; n = c["units"]*6
        print(grp_name, k, "units", c["units"], {x: c[x] for x in ("SUCCESS","REJECTED","HOLD","NOT_APPLICABLE","NOT_DONE")}, "share with a measured candidate (REJECTED/HOLD in M3-M6): %.0f%%" % (100*(c["REJECTED"]+c["HOLD"])/ (c["units"]*4)))
# per unit: units with no measured approximation candidate at all in M3..M6
none = [u["id"] for u in led if all(u["steps"][s]["conclusion"] in ("NOT_APPLICABLE","NOT_DONE") for s in ("M3","M4","M5","M6")) and not any(u["steps"][s]["conclusion"]=="SUCCESS" and False for s in steps)]
none2 = [u["id"] for u in led if all(u["steps"][s]["conclusion"] in ("NOT_APPLICABLE","NOT_DONE") or (s=="M6" and u["steps"][s]["conclusion"]=="SUCCESS") for s in ("M3","M4","M5","M6"))]
print("units with no approximation candidate measured in M3-M6 (all N/A; exact M6 'SUCCESS' not counted):", len(none2), none2)
m5 = [u["id"] for u in led if u["steps"]["M5"]["conclusion"] != "NOT_APPLICABLE"]
print("units whose M5 is not N/A:", m5)
print("distinct approx candidates per step:", {s: sorted({r["candidate_id"] for r in recs if r["step"] == s and r["candidate_id"].startswith("AP")}) for s in steps})
