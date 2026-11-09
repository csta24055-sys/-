#!/usr/bin/env python3
"""Build the static research app's data files (STEP 9).

Each company gets its own JSON file, and the app loads exactly one company file per company page,
so data from one company can never leak into another's page. Cross-company and world layers are
separate files.

    python3 research/tools/build_app.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import AS_OF, axes, companies, company_dir, read_json, read_jsonl, research_root, write_json  # noqa: E402
from research_gates import load_company  # noqa: E402


def company_payload(c: dict) -> dict:
    d = load_company(c)
    cdir = company_dir(c)
    status = read_json(cdir / "COMPANY_RESEARCH_STATUS.json", {})
    topic_state = {t["topic_id"]: t for t in status.get("topics", [])} if status.get("topics") else {}
    axis_list = []
    by_axis = {}
    for a in axes():
        by_axis.setdefault(a["axis_id"], {"axis_id": a["axis_id"], "axis_name": a["axis_name"], "topics": []})
        by_axis[a["axis_id"]]["topics"].append(a)
    full_status = read_json(cdir / "COMPANY_RESEARCH_STATUS.json", {})
    axes_state = full_status.get("axes", {})
    tstatus = {t["topic_id"]: t for t in d["topics"]}
    for axis_id, a in by_axis.items():
        axis_list.append({
            "axis_id": axis_id, "axis_name": a["axis_name"],
            "state": axes_state.get(axis_id, {}).get("state", "NOT_STARTED"),
            "synthesis_md": d["synthesis"].get(axis_id) or "",
            "topics": [{"topic_id": t["topic_id"], "name": t["subtopic"], "priority": t["priority"],
                        "declared": tstatus.get(t["topic_id"], {}).get("declared_state"),
                        "applicability": tstatus.get(t["topic_id"], {}).get("applicability")} for t in a["topics"]],
        })
    models = []
    for m in d["models"]:
        out = cdir / "datasets" / m["outputs"]
        models.append({**m, "outputs_data": json.loads(out.read_text(encoding="utf-8")) if out.exists() else None})
    snaps = sorted(p.name for p in (cdir / "snapshots").iterdir() if p.is_dir()) if (cdir / "snapshots").exists() else []
    events = d["status_events"]
    return {
        "company": c, "as_of": AS_OF, "status": {k: v for k, v in status.items() if k != "topics"},
        "topic_gates": status.get("topics", []),
        "report_md": d["report"], "axes": axis_list,
        "sources": d["sources"], "passages": d["passages"], "observations": d["observations"],
        "claims": [{k: v for k, v in x.items() if k != "_file"} for x in d["claims"]],
        "hypotheses": d["hypotheses"],
        "questions": [q for q in d["questions"] if q.get("kind") != "ROOT_RESEARCH_CARD" or q.get("status") != "NOT_STARTED"],
        "root_questions_not_started": sum(1 for q in d["questions"] if q.get("kind") == "ROOT_RESEARCH_CARD" and q.get("status") == "NOT_STARTED"),
        "relations": d["relations"], "search_log": d["search_log"], "models": models,
        "snapshots": snaps, "claim_status_events": events,
        "update_history_md": (cdir / "UPDATE_HISTORY.md").read_text(encoding="utf-8") if (cdir / "UPDATE_HISTORY.md").exists() else "",
        "next_steps_md": (cdir / "NEXT_STEPS.md").read_text(encoding="utf-8") if (cdir / "NEXT_STEPS.md").exists() else "",
    }


def main() -> int:
    root = research_root()
    out = root / "app" / "data"
    rs = read_json(root / "research_status.json", {})
    summary = []
    for c in companies():
        p = company_payload(c)
        write_json(out / "company" / f"{c['short_code']}.json", p)
        s = p["status"]
        summary.append({"company_id": c["company_id"], "short_code": c["short_code"], "name_ja": c["name_ja"], "name_en": c["name_en"],
                        "status": s.get("company_research_status", "NOT_STARTED"), "report_status": s.get("report_status"),
                        "axes_pass": s.get("axes_pass", 0), "axes_in_progress": s.get("axes_in_progress", 0),
                        "topics_by_state": s.get("topics_by_state", {}), "claims": sum((s.get("claims_by_type") or {}).values()),
                        "sources": s.get("sources_direct", 0), "errors": s.get("errors", 0)})
    write_json(out / "companies.json", {"as_of": AS_OF, "RESEARCH_STATUS": rs.get("RESEARCH_STATUS"), "companies": summary})
    write_json(out / "cross_company.json", {
        "relations": read_jsonl(root / "cross_company" / "relations.jsonl"),
        "entities": read_jsonl(root / "registry" / "entities.jsonl"),
        "layers": rs.get("layers", {}),
        "note": "会社間エッジは双方の会社台帳の原文IDが揃ったものだけを VERIFIED_BOTH_SIDES とし、片側のみは ONE_SIDED と表示する。",
        "report_md": (root / "cross_company" / "COMPARATIVE_REPORT.md").read_text(encoding="utf-8") if (root / "cross_company" / "COMPARATIVE_REPORT.md").exists() else "",
    })
    world = root / "world_context" / "WORLD_INTEGRATED_REPORT.md"
    write_json(out / "world.json", {"report_md": world.read_text(encoding="utf-8") if world.exists() else "", "layers": rs.get("layers", {})})
    write_json(out / "gates.json", rs)
    print(f"app data written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
