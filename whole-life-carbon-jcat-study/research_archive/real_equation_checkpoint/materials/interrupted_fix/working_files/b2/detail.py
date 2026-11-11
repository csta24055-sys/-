"""Compact dump of the new parts of a study JSON. Usage: detail.py FILE [cid ...]"""
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
C = d["candidates"]
only = sys.argv[2:]
pc = lambda x: "%+.3f%%" % (100 * x)
def st(v):
    if not isinstance(v, dict): return str(v)
    if not v.get("n"): return "n=0 zero=%s/%s" % (v.get("n_reference_zero"), v.get("n_reference_zero_candidate_nonzero"))
    z = "" if "n_reference_zero" not in v else " zero=%d/%d" % (v["n_reference_zero"], v["n_reference_zero_candidate_nonzero"])
    return "n=%d mean %s p95 %.3f%% [%s..%s] under %.1f%%%s" % (v["n"], pc(v["mean_signed"]), 100 * v["p95_abs"], pc(v["max_under"]), pc(v["max_over"]), 100 * v["share_under_estimated"], z)
for cid, c in C.items():
    if only and cid not in only: continue
    print("=====", cid, "|", c["stage"], "| step", c["step"], "| scope", c["scope"])
    for k in ("stage_error", "row_error", "local_total_error", "propagated_total_error"):
        if c.get(k): print("  %-24s %s" % (k, st(c[k])))
    for k, v in (c.get("by_stage") or {}).items(): print("  by_stage %-15s %s" % (k, st(v)))
    p = c.get("propagation") or {}
    if p.get("measured"):
        print("  propagation check %.2e n=%d" % (p["rewrite_reproduces_local_candidate_max_rel_diff"], p["n"]))
        for k, v in p["stage_error"].items(): print("  propagated %-13s %s" % (k, st(v)))
    for u, qs in (c.get("by_unit") or {}).items():
        for q, e in qs.items(): print("  by_unit %-6s %-34s %s %s %s" % (u, q[:34], e["level"], "" if e["role"] == "REPLACED" else e["role"], st(e["error"])))
    for k, v in (c.get("other_targets") or {}).items():
        if isinstance(v, dict) and "stage_error" in v: print("  other %-30s %s | total %s" % (k[:30], st(v["stage_error"]), st(v.get("local_total_error"))))
        else: print("  other %-30s %s" % (k[:30], st(v)))
    z = c.get("by_material_class_zero_reference")
    if z: print("  classes:", len(c["by_material_class"]), "zero-reference pairs", z)
    elif "by_material_class_reason" in c: print("  no classes:", c["by_material_class_reason"])
    print("  flags: within_stage", c.get("within_stage_target"), "within_total", c.get("within_total_target"), "under", c.get("under_estimates"), "| worst", c.get("worst_stage") and (c["worst_stage"]["stage"], c["worst_stage"]["measured_in"], round(c["worst_stage"]["max_abs"], 5)))
    i = c["inputs"]
    print("  inputs:", ("exact %.1f -> candidate %.1f (%s)" % (i["exact"], i["candidate"], i["unit"][:60])) if c["inputs_measured"] else i["text"][:80])
    l = c["load"]
    if l["measured"]:
        for name, x in (l.get("cases") or {"": l}).items():
            print("  load %s: candidate %d / exact %d = %.3f over %d rows, %d kernel runs; exact kernel vs reference %s %s" % (
                name[:28], x["candidate_instructions"], x["exact_closed_form_instructions"], x["ratio_candidate_to_exact"], x["n_rows"], x["n_kernel_runs"],
                x["exact_kernel_max_rel_diff_to_reference"], {k: v for k, v in x.items() if k.startswith("n_distinct") or k == "n_classes"}))
    else: print("  load: not measured -", l["reason"][:70])
    for k in c:
        if k in ("by_rate_times_cycle_years_no_top_up_devices", "by_profile_kind", "by_profile_kind_stage_B2", "by_grid_kind", "by_grid_kind_stage_B2", "by_summary_class", "by_own_study_period"):
            for kk, v in c[k].items(): print("  %s %-24s %s" % (k[:28], kk, st(v)))
