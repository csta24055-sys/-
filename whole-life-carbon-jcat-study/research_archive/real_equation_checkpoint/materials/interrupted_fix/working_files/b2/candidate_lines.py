"""One report line per candidate from the final JSON and the verdicts in proposals.py."""
import json, sys
sys.path.insert(0, ".")
import proposals
C = json.load(open("approximation_study.json", encoding="utf-8"))["candidates"]
pc = lambda x: "%+.1f%%" % (100 * x)
lines = []
for cid, c in C.items():
    s = c.get("stage_error") or c.get("row_error") or {}
    ws = c.get("worst_stage")
    if ws:
        worst = f"worst stage {ws['stage']} ({ws['measured_in']}) {pc(ws['max_under'])}..{pc(ws['max_over'])}"
    elif s.get("n"):
        worst = f"no real stage value measured; primary [{c['stage']}] {pc(s['max_under'])}..{pc(s['max_over'])}"
    else:
        worst = "no point estimate"
    t = c.get("propagated_total_error") or c.get("local_total_error") or {}
    total = f"total {c['total_error_kind']} p95 {100 * t['p95_abs']:.2f}% max {100 * t['max_abs']:.2f}%" if t.get("n") else "total none"
    under = f"{100 * s['share_under_estimated']:.1f}%" if s.get("n") else "-"
    v = proposals.P.get(cid, {}).get("verdict", "?")
    verdict = {"SUPPORTED": "conclusion supported", "REWORD": "conclusion needs rewording", "NEW": "no conclusion yet (new candidate)"}[v]
    lines.append(f"{cid} | {c['step']} | scope {c['scope']} | units {','.join(c['units']) or '-'} | stage-level {','.join(c['units_stage_level']) or '-'} | {worst} -> "
                 f"within_stage={c.get('within_stage_target')} | {total} -> within_total={c.get('within_total_target')} | under share {under} | {verdict}")
json.dump(lines, open("candidate_lines.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\n".join(lines))
