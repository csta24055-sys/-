import json, collections, re
R = "/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY"
J = lambda p: json.load(open(R+"/"+p, encoding="utf-8"))
T = lambda p: open(R+"/"+p, encoding="utf-8").read()
led = J("05_DECISIONS/progress_ledger.json"); recs = J("03_MODELS/records/units.json")["records"]
units = J("01_LEDGER/units.json"); models = J("03_MODELS/models.json")["models"]; cands = J("03_MODELS/candidates.json")["candidates"]
ex = J("04_VERIFICATION/unified_model_exactness.json"); ld = J("04_VERIFICATION/unified_model_load.json")["sizes"]; ap = J("04_VERIFICATION/approximation_study.json")["candidates"]
pri = J("02_RANKING/research_priority.json"); sf = J("01_LEDGER/sheet_families.json"); cov = J("01_LEDGER/sheet_family_coverage.json"); un = J("01_LEDGER/unlinked_input_disposition.json")
top = T("README.md"); r01 = T("01_LEDGER/README.md"); r02 = T("02_RANKING/README.md"); r03 = T("03_MODELS/README.md"); r04 = T("04_VERIFICATION/README.md"); r05 = T("05_DECISIONS/README.md"); r06 = T("06_OPEN_ISSUES/README.md")
n = 0
def q(label, quoted, computed, text=None):
    global n; n += 1
    okk = (quoted == computed) if not isinstance(computed, float) else abs(float(quoted) - computed) < 0.05 + 1e-9
    present = "" if text is None else (" [in text]" if str(quoted) in text else " [NOT FOUND IN TEXT]")
    print(f"{n:2d} {'OK  ' if okk else 'DIFF'} {label}: quoted {quoted} computed {computed}{present}")
U = units["units"]
q("unit count", 70, len(U)); q("existing 53", 53, sum(1 for u in U if u["origin"] == "EXISTING_53")); q("additional 17", 17, sum(1 for u in U if u["origin"] == "ADDITIONAL"))
q("units unified", 66, sum(m["unit_count"] for m in models)); q("models", 8, len(models))
q("scenarios", 494, ex["scenarios"]); q("numeric leaves", 6761414, sum(v["leaves_compared"] for v in ex["units"].values()), None)
q("non numeric", 535373, sum(v["non_numeric_compared"] for v in ex["units"].values()))
L = ld["L"]; ra = L["reference_all_units"]; rn = L["reference_without_SUM-08"]; fw = L["unified_full_outputs_baseline_cached"]; fc = L["unified_full_outputs_baseline_recomputed"]; fs = L["unified_totals_only_baseline_cached"]
q("L ref ms", 3103, round(ra["time_ms"])); q("L warm ms", 472, round(fw["time_ms"])); q("L time reduction %", 84.8, round(100*(1-fw["time_ms"]/ra["time_ms"]), 1))
q("L ref w/o SUM-08 ms", 1459, round(rn["time_ms"])); q("reduction vs no-SUM-08 %", 67.6, round(100*(1-fw["time_ms"]/rn["time_ms"]), 1))
q("L mem reduction %", 88.8, round(100*(1-fw["peak_memory_kib"]/ra["peak_memory_kib"]), 1)); q("L cold ms", 926, round(fc["time_ms"])); q("cold reduction", 70.2, round(100*(1-fc["time_ms"]/ra["time_ms"]), 1))
q("summary ms", 416, round(fs["time_ms"])); q("summary reduction", 86.6, round(100*(1-fs["time_ms"]/ra["time_ms"]), 1))
q("instr reduction", 80.1, round(100*(1-fw["instructions"]/ra["instructions"]), 1)); q("peak MiB ref", 111, round(ra["peak_memory_kib"]/1024)); q("peak MiB fast", 12, round(fw["peak_memory_kib"]/1024))
q("instr ref", 278096808, ra["instructions"]); q("instr fast", 55403311, fw["instructions"])
q("approx candidates", 16, len(cands)); q("rejected", 10, sum(1 for c in cands if c["outcome"] == "REJECTED")); q("hold", 6, sum(1 for c in cands if c["outcome"] == "HOLD"))
q("records", 432, len(recs)); oc = collections.Counter(r["outcome"] for r in recs)
q("SUCCESS", 132, oc["SUCCESS"]); q("REJECTED", 31, oc["REJECTED"]); q("HOLD", 52, oc["HOLD"]); q("NA", 217, oc["NOT_APPLICABLE"])
q("units with steps on hold among DONE", 39, sum(1 for u in led["units"] if u["status"].startswith("DONE") and u["steps_on_hold"]))
q("formula kinds reduction %", 84.1, round(100*(69-11)/69, 1)); q("unit->model reduction %", 87.9, round(100*(66-8)/66, 1))
# sheet families
q("families", 59, cov["family_count"]); q("families with formulas", 41, sf["families_with_formulas"]); q("total nodes", 3818483, sf["total_formula_nodes"])
q("not inspected families", 9, cov["families_by_status"]["NOT_INSPECTED"]); q("share additional %", 97.11, round(100*cov["node_share_by_status"]["COVERED_BY_ADDITIONAL"], 2)); q("share not inspected %", 2.08, round(100*cov["node_share_by_status"]["NOT_INSPECTED"], 2))
print("   nodes_by_scope_suffix:", sf["nodes_by_scope_suffix"])
q("unlinked inputs", 53, un["input_count"]); q("metadata only", 30, un["counts"]["METADATA_ONLY"])
sc = collections.Counter(u["structure_class"] for u in U); print("   structure classes:", dict(sc), "| ledger header:", units["structure_class_counts"])
q("LINEAR_SUM_PRODUCT 29", 29, sc["LINEAR_SUM_PRODUCT"]); q("RATIO 11", 11, sc["RATIO"]); q("PREDICATE_GATE 8", 8, sc["PREDICATE_GATE"])
q("top30 A", 21, pri["reference_top30_counts"]["A"]); q("top30 B", 30, pri["reference_top30_counts"]["B"]); q("top30 union", 41, pri["reference_top30_counts"]["union"])
# approx table
for cid, quoted in (("AP-01", (-18.7, 41.7, 0.0, -58.5, 8.1)), ("AP-04", (2.1, 4.0, 5.4, 0.1, 0.6)), ("AP-05", (28.0, 109.8, 180.7, -0.0, 2.3)), ("AP-12", (-9.5, 26.0, 8.1, -40.3, 4.4)), ("AP-16", (3.7, 74.8, 193.1, -74.7, 74.8)), ("AP-14", (2.3, 11.8, 22.8, -11.9, 11.8))):
    s = ap[cid]["stage_error"]; t = ap[cid]["total_error"]
    comp = (round(100*s["mean_signed"], 1), round(100*s["p95_abs"], 1), round(100*s["max_over"], 1), round(100*s["max_under"], 1), round(100*t["p95_abs"], 1))
    q(f"{cid} (mean,p95,max over,max under,total p95)", quoted, comp)
print("   AP-04 stage_error keys:", list(ap["AP-04"]["stage_error"].keys()), ap["AP-04"]["stage_error"])
print("   AP-01 n:", ap["AP-01"]["stage_error"]["n"], "AP-10 n:", ap["AP-10"]["stage_error"]["n"], "AP-14 n:", ap["AP-14"]["stage_error"]["n"])
# inputs 88
used = set()
for u in U:
    for i in u["inputs"]:
        used.add(i)
new = {i for i in used if str(i).startswith("NEW:")}
print("   distinct inputs referenced by units:", len(used), "of which NEW:", len(new), "existing:", len(used - new))
import os
inp = json.load(open(R + "/../03_INPUTS/inputs.json", encoding="utf-8"))
ids = [x["id"] for x in (inp["inputs"] if isinstance(inp, dict) else inp)] if not isinstance(inp, dict) or "inputs" in inp else None
print("   inputs.json:", type(inp).__name__, (list(inp.keys())[:8] if isinstance(inp, dict) else len(inp)))
print("total quoted numbers checked:", n)
