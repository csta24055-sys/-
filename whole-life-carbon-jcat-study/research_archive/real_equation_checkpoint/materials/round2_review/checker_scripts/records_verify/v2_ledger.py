import json, copy, collections
from tools import progress_ledger as pl   # import only; roll_up() works on a dict in memory
S = "/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/"
led = json.load(open(S + "05_DECISIONS/progress_ledger.json"))
units = {u["id"]: u for u in led["units"]}
print("stored:", collections.Counter(u["status"] for u in led["units"]))
for uid, drop in (("A13-05", "EX-A13-05-M2"), ("X-13", "EX-X-13-M2"), ("B1-01", "EX-B1-01-M2"), ("SYS-03", "EX-SYS-03-M2"), ("QA-03", "EX-QA-03-M2"), ("B6-04", "EX-B6-04-M2"), ("X-07", "EX-X-07-M2"), ("A5-01", "EX-A5-01-M2")):
    u = copy.deepcopy(units[uid]); before = u["status"]
    for m in pl.STEPS:
        u["steps"][m]["candidates"] = [c for c in u["steps"][m]["candidates"] if c["candidate_id"] != drop]
        if not u["steps"][m]["candidates"]:
            u["steps"][m]["candidates"] = [{"candidate_id": "NA-x", "outcome": "NOT_APPLICABLE", "verification": "NOT_VERIFIED"}]
        u["steps"][m]["conclusion"] = pl.step_conclusion(u["steps"][m]["candidates"])
    pl.roll_up(u)
    print(uid, before, "-> without", drop, ":", u["status"], {m: u["steps"][m]["conclusion"] for m in pl.STEPS})
