"""Independent recomputation of unit statuses from 03_MODELS/records/units.json by the rules of P8/P10 (own code)."""
import json, collections
S = "/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/"
recs = json.load(open(S + "03_MODELS/records/units.json"))["records"]
led = json.load(open(S + "05_DECISIONS/progress_ledger.json"))
units = [u["id"] for u in json.load(open(S + "01_LEDGER/units.json"))["units"]]
steps = ("M1", "M2", "M3", "M4", "M5", "M6")
by = collections.defaultdict(lambda: collections.defaultdict(list))
for r in recs: by[r["unit_id"]][r["step"]].append(r)
order = ("SUCCESS", "HOLD", "REJECTED", "NOT_APPLICABLE")
def status(uid, drop=()):
    concl = {}
    for m in steps:
        outs = {r["outcome"] for r in by[uid][m] if r["candidate_id"] not in drop}
        concl[m] = next((o for o in order if o in outs), "NOT_DONE")
    measured = any(r["verification"] != "NOT_VERIFIED" for m in steps for r in by[uid][m] if r["candidate_id"] not in drop)
    vals = set(concl.values())
    if vals == {"NOT_DONE"} or not measured: return "NOT_VERIFIED", concl
    if "NOT_DONE" in vals: return "IN_PROGRESS", concl
    if concl["M2"] == "SUCCESS" or concl["M4"] == "SUCCESS": return "DONE_UNIFIED", concl
    if any(concl[m] == "SUCCESS" for m in ("M1", "M3", "M5", "M6")): return "DONE_SIMPLIFIED", concl
    if "HOLD" in vals: return "HOLD_DATA_OR_RIGHTS", concl
    return "DONE_APPROX_REJECTED", concl
diff = []
cnt = collections.Counter()
for u in led["units"]:
    st, concl = status(u["id"])
    cnt[u["status"]] += 1
    if st != u["status"] or any(u["steps"][m]["conclusion"] != concl[m] for m in steps): diff.append((u["id"], u["status"], st))
    if u.get("unit_hold"): print("unit_hold:", u["id"])
print("ledger units", len(led["units"]), "ledger ids == unit ids:", sorted(x["id"] for x in led["units"]) == sorted(units))
print("stored status counts:", dict(cnt))
print("differences between stored and recomputed:", diff)
n_rec = sum(len(u["steps"][m]["candidates"]) for u in led["units"] for m in steps)
print("candidate records in ledger:", n_rec, "records file:", len(recs))
# SUCCESS records and what backs them
succ = [r for r in recs if r["outcome"] == "SUCCESS"]
print("SUCCESS:", len(succ), "| mechanism None:", sum(1 for r in succ if not r["mechanism"]), "| derivation None:", sum(1 for r in succ if not r["derivation"]),
      "| both None:", [r["candidate_id"] for r in succ if not r["mechanism"] and not r["derivation"]])
print("SUCCESS without mechanism:", [r["candidate_id"] for r in succ if not r["mechanism"]])
# units whose DONE_UNIFIED rests only on an M2 record that I judge not to meet the membership rule
for uid, drop in (("A13-05", {"EX-A13-05-M2"}), ("X-13", {"EX-X-13-M2"}), ("B1-01", {"EX-B1-01-M2"}), ("SYS-03", {"EX-SYS-03-M2"}), ("QA-03", {"EX-QA-03-M2"}),
                  ("A5-01", {"EX-A5-01-M2", "EX-A5-01-M1"}), ("B6-04", {"EX-B6-04-M2"}), ("X-07", {"EX-X-07-M2"})):
    print(f"  {uid}: stored {status(uid)[0]} -> without {sorted(drop)}: {status(uid, drop)[0]}  {status(uid, drop)[1]}")
