"""One line per candidate from an approximation_study.json (schema 3.0). Usage: summ.py FILE"""
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
C = d["candidates"]
pc = lambda x: "%+.2f%%" % (100 * x)
for cid, c in C.items():
    s = c.get("stage_error") or c.get("row_error") or {}
    t = c.get("propagated_total_error") or c.get("local_total_error") or {}
    ws = c.get("worst_stage")
    rng = f"{pc(s['max_under'])}..{pc(s['max_over'])} p95 {100 * s['p95_abs']:.2f}% n={s['n']}" if s.get("n") else "-"
    tot = f"{c.get('total_error_kind')}: p95 {100 * t['p95_abs']:.2f}% max {100 * t['max_abs']:.2f}%" if t.get("n") else "-"
    under = "%.1f%%" % (100 * s["share_under_estimated"]) if s.get("n") else "-"
    wst = f"{ws['stage']}({ws['measured_in']}) {pc(ws['max_under'])}..{pc(ws['max_over'])}" if ws else "-"
    print(f"{cid:7s} {c['step']} scope={c['scope']:8s} units={','.join(c['units']) or '-'} | stage-level={','.join(c['units_stage_level']) or '-'}\n"
          f"        on [{c['stage']}] {rng}; worst stage {wst}; within_stage={c.get('within_stage_target')} | total {tot}; within_total={c.get('within_total_target')} "
          f"| under share {under} under_estimates={c.get('under_estimates')} | params={c.get('parameters_from')} | inputs_measured={c.get('inputs_measured')} load={c['load']['measured']}")
