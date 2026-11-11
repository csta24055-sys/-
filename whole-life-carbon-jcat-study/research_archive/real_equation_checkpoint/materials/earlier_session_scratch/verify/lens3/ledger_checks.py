import json, collections, math, re
R = "/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY"
J = lambda p: json.load(open(R+"/"+p, encoding="utf-8"))
led = J("05_DECISIONS/progress_ledger.json")
recs = J("03_MODELS/records/units.json")["records"]
units = J("01_LEDGER/units.json")
models = J("03_MODELS/models.json")["models"]
cands = J("03_MODELS/candidates.json")
ex = J("04_VERIFICATION/unified_model_exactness.json")
ld = J("04_VERIFICATION/unified_model_load.json")
ap = J("04_VERIFICATION/approximation_study.json")
pri = J("02_RANKING/research_priority.json")
A = J("02_RANKING/axis_a.json"); B = J("02_RANKING/axis_b.json")
LU = led["units"]
STATES = set(led["status_labels"])
ok = True
def chk(name, cond, detail=""):
    global ok
    print(("PASS " if cond else "FAIL ") + name + (" :: " + str(detail) if detail else ""))
    ok = ok and cond

# ---------- item 6
ledger_ids = [u["id"] for u in LU]
unit_ids = [u["id"] for u in units["units"]]
chk("70 units in ledger, equal to 01_LEDGER ids", len(LU) == 70 and sorted(ledger_ids) == sorted(unit_ids), (len(LU), len(unit_ids)))
chk("statuses in six states", all(u["status"] in STATES for u in LU), collections.Counter(u["status"] for u in LU))
steps = ["M1","M2","M3","M4","M5","M6"]
bad = [u["id"] for u in LU if u["status"].startswith("DONE") and any(u["steps"][s]["conclusion"] == "NOT_DONE" for s in steps)]
chk("no DONE unit with NOT_DONE step", not bad, bad)
missing_reason = []
for u in LU:
    for s in steps:
        st = u["steps"][s]
        if st["conclusion"] in ("REJECTED","NOT_APPLICABLE","HOLD") and not (st.get("reason") or "").strip():
            missing_reason.append((u["id"], s))
        for c in st.get("candidates", []):
            if c["outcome"] in ("REJECTED","NOT_APPLICABLE","HOLD") and not (c.get("reason") or "").strip():
                missing_reason.append((u["id"], s, c["candidate_id"]))
chk("reasons present for REJECTED/NA/HOLD", not missing_reason, missing_reason[:5])
weak = [(r["unit_id"], r["step"], r["reason"]) for r in recs if r["outcome"] in ("REJECTED","NOT_APPLICABLE","HOLD") and len(r["reason"].strip()) < 8]
print("   records whose reason is a bare back-reference (<8 chars):", weak)
hold_units = [(u["id"], u["unit_hold_reason"]) for u in LU if u["status"] == "HOLD_DATA_OR_RIGHTS"]
print("   unit-level HOLD:", hold_units)
print("   X-16 step conclusions:", {s: LU[ledger_ids.index("X-16")]["steps"][s]["conclusion"] for s in steps}, "records for X-16:", sum(1 for r in recs if r["unit_id"] == "X-16"))
# re-derive status by P10
def derive(u):
    con = [u["steps"][s]["conclusion"] for s in steps]
    if u.get("unit_hold"): return "HOLD_DATA_OR_RIGHTS"
    if all(c == "NOT_DONE" for c in con): return "NOT_VERIFIED"
    if any(c == "NOT_DONE" for c in con): return "IN_PROGRESS"
    if u["steps"]["M2"]["conclusion"] == "SUCCESS" or u["steps"]["M4"]["conclusion"] == "SUCCESS": return "DONE_UNIFIED"
    if any(u["steps"][s]["conclusion"] == "SUCCESS" for s in ("M1","M3","M5","M6")): return "DONE_SIMPLIFIED"
    if any(c == "HOLD" for c in con): return "HOLD_DATA_OR_RIGHTS"
    return "DONE_APPROX_REJECTED"
diff = [(u["id"], u["status"], derive(u)) for u in LU if u["status"] != derive(u)]
chk("status equals P10 rule", not diff, diff)
# units DONE with zero verified record
ver_by_unit = collections.defaultdict(set); out_by_unit = collections.defaultdict(list)
for r in recs:
    ver_by_unit[r["unit_id"]].add(r["verification"]); out_by_unit[r["unit_id"]].append(r["outcome"])
nov = [u["id"] for u in LU if u["status"].startswith("DONE") and ver_by_unit[u["id"]] <= {"NOT_VERIFIED"}]
print("   DONE units whose every record has verification NOT_VERIFIED:", nov, {i: collections.Counter(out_by_unit[i]) for i in nov})
print("   records per unit distribution:", collections.Counter(len(v) for v in out_by_unit.values()), "units with records:", len(out_by_unit))
m4 = collections.Counter(r["outcome"] for r in recs if r["step"] == "M4"); m5 = collections.Counter(r["outcome"] for r in recs if r["step"] == "M5"); m6 = collections.Counter(r["outcome"] for r in recs if r["step"] == "M6"); m3 = collections.Counter(r["outcome"] for r in recs if r["step"] == "M3")
print("   M3:", dict(m3), "M4:", dict(m4), "M5:", dict(m5), "M6:", dict(m6))
print("   M6 SUCCESS titles all exact?:", collections.Counter("どちらも厳密" in r["title"] or "厳密" in r["title"] for r in recs if r["step"] == "M6" and r["outcome"] == "SUCCESS"))
print("   SUCCESS by verification:", collections.Counter((r["step"], r["verification"]) for r in recs if r["outcome"] == "SUCCESS"))
print("   distinct SUCCESS reason templates:", len({re.sub(r"[0-9.e+\-]+", "#", r["reason"]) for r in recs if r["outcome"] == "SUCCESS"}))
print("   distinct NA reasons:", len({r["reason"] for r in recs if r["outcome"] == "NOT_APPLICABLE"}), "of", sum(1 for r in recs if r["outcome"] == "NOT_APPLICABLE"))
# order of work
orders = sorted(u["order"] for u in LU); chk("order 1..70", orders == list(range(1, 71)))
print("   waves:", collections.Counter(u["wave"] for u in LU))
po = {r["id"]: r for r in pri["units"]}
print("   priority unit keys:", list(pri["units"][0].keys()))
chk("ledger order == priority order", all(po[u["id"]].get("order", po[u["id"]].get("rank")) == u["order"] for u in LU))
print("   reference_top30_counts:", pri["reference_top30_counts"], "research_target_count:", pri["research_target_count"])
# models
mu = collections.Counter()
for m in models:
    chk(f"model {m['id']} unit_count", m["unit_count"] == len(m["units"]), (m["unit_count"], len(m["units"])))
    for x in m["units"]: mu[x] += 1
chk("66 units in models, each once", len(mu) == 66 and set(mu.values()) == {1}, len(mu))
lm = {u["id"]: u["unified_models"] for u in LU}
mm = {x: m["id"] for m in models for x in m["units"]}
chk("ledger unified_models == models.json", all((lm[i] == [mm[i]]) if i in mm else (lm[i] == []) for i in lm), [(i, lm[i], mm.get(i)) for i in lm if ((lm[i] != [mm[i]]) if i in mm else (lm[i] != []))][:5])
# exactness coverage
exu = ex["units"]
print("   exactness units:", len(exu), "missing from exactness:", sorted(set(unit_ids) - set(exu)))
print("   leaves total:", sum(v["leaves_compared"] for v in exu.values()), "non numeric:", sum(v["non_numeric_compared"] for v in exu.values()), "max err:", max((v["max_abs_rel_error"], k) for k, v in exu.items()))
print("   by_group:", ex["by_group"])
zero_leaves = [k for k, v in exu.items() if v["leaves_compared"] == 0]
print("   units with zero numeric leaves compared:", zero_leaves)
sz = [(k, v["summary_leaves_compared"]) for k, v in exu.items() if v["summary_leaves_compared"] == 0]
print("   units with zero leaves compared in totals-only mode:", sz)
few = sorted((v["leaves_compared"], k) for k, v in exu.items())[:12]
print("   fewest numeric leaves:", few)
