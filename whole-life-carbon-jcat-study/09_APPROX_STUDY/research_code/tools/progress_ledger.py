#!/usr/bin/env python3
"""Progress ledger for the approximation / unification study (protocol P8, P10).

Every evaluation unit is a research target. For each unit the six method steps
M1..M6 get a recorded conclusion, and the unit status is rolled up from them.
Nothing is counted as verified unless a record says so.

Commands
  init     create or extend 05_DECISIONS/progress_ledger.json from the unit ledger
  merge    fold candidate records (03_MODELS/records/*.json) into the ledger
  rollup   recompute unit statuses from step conclusions
  check    validate invariants (exit code 1 on violation)
  report   write 05_DECISIONS/PROGRESS.md

Research tooling only. Standard library only.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

STUDY = Path(__file__).resolve().parents[2]
UNITS = STUDY / "01_LEDGER" / "units.json"
PRIORITY = STUDY / "02_RANKING" / "research_priority.json"
RECORDS = STUDY / "03_MODELS" / "records"
LEDGER = STUDY / "05_DECISIONS" / "progress_ledger.json"
REPORT = STUDY / "05_DECISIONS" / "PROGRESS.md"

STEPS = {
    "M1": "数学的に完全に同じ結果になる簡略化",
    "M2": "異なる式の共通化・統合（厳密）",
    "M3": "単純な近似式への置き換え",
    "M4": "複数の異なる式を共通の近似モデルへ統合",
    "M5": "高度な代理モデルによる近似",
    "M6": "厳密計算と近似計算の併用",
}
OUTCOMES = ("SUCCESS", "REJECTED", "NOT_APPLICABLE", "HOLD")
CONCLUSIONS = OUTCOMES + ("NOT_DONE",)
VERIFICATION = ("VERIFIED_ANALYTIC_AND_SYNTHETIC", "VERIFIED_SYNTHETIC_ONLY", "NOT_VERIFIED")
STATUS_LABELS = {
    "DONE_SIMPLIFIED": "検証完了・簡略化成功",
    "DONE_UNIFIED": "検証完了・統合成功",
    "DONE_APPROX_REJECTED": "検証完了・近似不採用",
    "IN_PROGRESS": "検証中",
    "NOT_VERIFIED": "未検証",
    "HOLD_DATA_OR_RIGHTS": "データ・権利上の制約により保留",
}
UNIFY_STEPS = ("M2", "M4")
SIMPLIFY_STEPS = ("M1", "M3", "M5", "M6")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(obj) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def empty_step() -> dict:
    return {"conclusion": "NOT_DONE", "candidates": [], "reason": ""}


def step_conclusion(candidates: list) -> str:
    """One conclusion per step from its candidate records.

    A candidate on hold keeps the step open: a step is not closed as rejected while
    another of its candidates still waits for data.
    """
    outcomes = {c["outcome"] for c in candidates}
    for value in ("SUCCESS", "HOLD", "REJECTED", "NOT_APPLICABLE"):
        if value in outcomes:
            return value
    return "NOT_DONE"


def roll_up(unit: dict) -> None:
    concl = {m: unit["steps"][m]["conclusion"] for m in STEPS}
    values = set(concl.values())
    unit["steps_on_hold"] = [m for m in STEPS if concl[m] == "HOLD"]
    has_success = "SUCCESS" in values
    # a unit is verified only when at least one of its records rests on a measurement or a checked derivation
    measured = any(c.get("verification") != "NOT_VERIFIED" for m in STEPS for c in unit["steps"][m]["candidates"])
    unit["has_verified_record"] = measured
    if unit.get("unit_hold"):
        status = "HOLD_DATA_OR_RIGHTS"
    elif values == {"NOT_DONE"} or not measured:
        status = "NOT_VERIFIED"
    elif "NOT_DONE" in values:
        status = "IN_PROGRESS"
    elif any(concl[m] == "SUCCESS" for m in UNIFY_STEPS):
        status = "DONE_UNIFIED"
    elif any(concl[m] == "SUCCESS" for m in SIMPLIFY_STEPS):
        status = "DONE_SIMPLIFIED"
    elif not has_success and "HOLD" in values:
        # nothing adopted and at least one step cannot be judged without data or rights
        status = "HOLD_DATA_OR_RIGHTS"
    else:
        status = "DONE_APPROX_REJECTED"
    unit["status"] = status
    unit["status_label"] = STATUS_LABELS[status]
    # the six states say nothing about the approximate steps of a unit whose exact part succeeded: say it beside the state
    if status.startswith("DONE") and unit["steps_on_hold"]:
        unit["status_note"] = "厳密な部分は完了。近似の段階（" + "・".join(unit["steps_on_hold"]) + "）は実データ待ちで保留"
    elif status in ("DONE_SIMPLIFIED", "DONE_UNIFIED"):
        unit["status_note"] = "厳密な部分は完了。近似は不採用または候補なし"
    else:
        unit["status_note"] = ""


def cmd_init() -> int:
    units = load(UNITS)["units"]
    prio = {r["id"]: r for r in load(PRIORITY)["units"]} if PRIORITY.exists() else {}
    old = {u["id"]: u for u in load(LEDGER)["units"]} if LEDGER.exists() else {}
    rows = []
    for u in units:
        row = old.get(u["id"]) or {
            "id": u["id"],
            "steps": {m: empty_step() for m in STEPS},
            "unit_hold": False,
            "unit_hold_reason": "",
            "unified_models": [],
        }
        # recomputed on every init: a unit that has since got a reference calculation is no longer on hold
        row["unit_hold"] = not u.get("computable_in_reference", True)
        row["unit_hold_reason"] = (u.get("not_computable_reason") or "") if row["unit_hold"] else ""
        row.update({
            "name": u["name"],
            "stage": u["stage"],
            "origin": u.get("origin"),
            "structure_class": u.get("structure_class"),
            "order": (prio.get(u["id"]) or {}).get("order"),
            "wave": (prio.get(u["id"]) or {}).get("wave"),
        })
        roll_up(row)
        rows.append(row)
    rows.sort(key=lambda r: (r["order"] is None, r["order"] or 0, r["id"]))
    save({
        "schema_version": "1.0",
        "protocol": "00_POLICY/EVALUATION_PROTOCOL.md (P8 steps, P10 statuses)",
        "scope_statement": "All evaluation units of the independent conceptual model are research targets. 'Verified' means analytic derivation and synthetic-data checks; it is not a guarantee of practical accuracy on real buildings.",
        "steps": STEPS,
        "status_labels": STATUS_LABELS,
        "unit_count": len(rows),
        "units": rows,
    })
    print(f"initialised {len(rows)} units ({len(old)} kept)")
    return 0


def cmd_merge() -> int:
    ledger = load(LEDGER)
    by_id = {u["id"]: u for u in ledger["units"]}
    for u in ledger["units"]:
        for m in STEPS:
            u["steps"][m]["candidates"] = []
        u["unified_models"] = []
    n = 0
    problems = []
    for path in sorted(RECORDS.glob("*.json")):
        data = load(path)
        for rec in data["records"] if isinstance(data, dict) else data:
            uid, step = rec.get("unit_id"), rec.get("step")
            if uid not in by_id or step not in STEPS or rec.get("outcome") not in OUTCOMES:
                problems.append(f"{path.name}: bad record {rec.get('candidate_id')} ({uid}, {step}, {rec.get('outcome')})")
                continue
            if rec.get("verification") not in VERIFICATION:
                problems.append(f"{path.name}: {rec.get('candidate_id')} has no valid verification state")
                continue
            if rec["outcome"] == "SUCCESS" and rec["verification"] == "NOT_VERIFIED":
                problems.append(f"{path.name}: {rec.get('candidate_id')} claims SUCCESS without verification")
                continue
            unit = by_id[uid]
            unit["steps"][step]["candidates"].append({
                "candidate_id": rec.get("candidate_id"),
                "title": rec.get("title"),
                "outcome": rec["outcome"],
                "verification": rec["verification"],
                "unified_model": rec.get("unified_model"),
                "reason": rec.get("reason"),
                "data_needed": rec.get("data_needed"),
                "evidence": rec.get("evidence") or [],
                "source_record": f"03_MODELS/records/{path.name}",
            })
            if rec["outcome"] == "SUCCESS" and rec.get("unified_model") and rec["unified_model"] not in unit["unified_models"]:
                unit["unified_models"].append(rec["unified_model"])
            n += 1
    for u in ledger["units"]:
        for m in STEPS:
            cands = u["steps"][m]["candidates"]
            u["steps"][m]["conclusion"] = step_conclusion(cands)
            u["steps"][m]["reason"] = "; ".join(c["reason"] for c in cands if c.get("reason") and c["outcome"] == u["steps"][m]["conclusion"])[:600]
        roll_up(u)
    save(ledger)
    print(f"merged {n} candidate records")
    for line in problems:
        print("PROBLEM:", line, file=sys.stderr)
    return 1 if problems else 0


def cmd_rollup() -> int:
    ledger = load(LEDGER)
    for u in ledger["units"]:
        roll_up(u)
    save(ledger)
    print(Counter(u["status"] for u in ledger["units"]))
    return 0


def cmd_check() -> int:
    ledger = load(LEDGER)
    unit_ids = [u["id"] for u in load(UNITS)["units"]]
    rows = {u["id"]: u for u in ledger["units"]}
    errors = []
    if sorted(rows) != sorted(unit_ids):
        errors.append("ledger units differ from 01_LEDGER/units.json")
    for uid, u in rows.items():
        concl = [u["steps"][m]["conclusion"] for m in STEPS]
        if any(c not in CONCLUSIONS for c in concl):
            errors.append(f"{uid}: unknown conclusion")
        if u["status"].startswith("DONE") and "NOT_DONE" in concl:
            errors.append(f"{uid}: marked done while a step is NOT_DONE")
        if u["status"].startswith("DONE") and not any(c["verification"] != "NOT_VERIFIED" for m in STEPS for c in u["steps"][m]["candidates"]):
            errors.append(f"{uid}: marked done without any measured or derived record")
        for m in STEPS:
            step = u["steps"][m]
            if step["conclusion"] != "NOT_DONE" and not step["candidates"]:
                errors.append(f"{uid} {m}: conclusion without a candidate record")
            for c in step["candidates"]:
                if c["outcome"] == "SUCCESS" and c["verification"] == "NOT_VERIFIED":
                    errors.append(f"{uid} {m}: success without verification")
                if c["outcome"] in ("REJECTED", "NOT_APPLICABLE", "HOLD") and not c.get("reason"):
                    errors.append(f"{uid} {m}: {c['outcome']} without a reason")
                if c["outcome"] == "HOLD" and not c.get("data_needed"):
                    errors.append(f"{uid} {m}: hold without the data or permission needed")
        before = u["status"]
        roll_up(u)
        if u["status"] != before:
            errors.append(f"{uid}: stored status {before} differs from roll-up {u['status']}")
    for e in errors:
        print("FAIL:", e, file=sys.stderr)
    print(f"checked {len(rows)} units: {'OK' if not errors else str(len(errors)) + ' problems'}")
    return 1 if errors else 0


def cmd_report() -> int:
    ledger = load(LEDGER)
    rows = ledger["units"]
    counts = Counter(u["status"] for u in rows)
    mark = {"SUCCESS": "成功", "REJECTED": "不採用", "NOT_APPLICABLE": "候補なし", "HOLD": "保留", "NOT_DONE": "未実施"}
    out = ["# 進捗台帳（全評価単位）", "",
           "`progress_ledger.json` から自動生成。手で編集しない。状態の定義は [研究プロトコル P10](../00_POLICY/EVALUATION_PROTOCOL.md) を参照。", "",
           "「検証完了」は、数学的導出と架空データによる確認が終わったことを指す。実建物データでの実用精度を保証するものではない。", "",
           "## 状態別の件数", "", "| 状態 | 件数 |", "|---|---:|"]
    for key, label in STATUS_LABELS.items():
        out.append(f"| {label} | {counts.get(key, 0)} |")
    out.append(f"| **合計** | **{len(rows)}** |")
    held = [u for u in rows if u["steps_on_hold"] and u["status"].startswith("DONE")]
    unit_holds = [u for u in rows if u.get("unit_hold")]
    out += ["", f"検証完了のうち、近似の段階が保留中の単位：{len(held)} 件（下表の「保留中の段階」列）。"
            "「検証完了・統合成功」「検証完了・簡略化成功」は厳密な部分（M1・M2）についての状態で、近似の段階（M3〜M6）の結論は段階ごとの列を見ること。", "",
            "## 段階別の結論の件数（単位の数）", "",
            "| 段階 | 成功 | 不採用 | 保留 | 候補なし | 未実施 |", "|---|---:|---:|---:|---:|---:|"]
    for m, label in STEPS.items():
        c = Counter(u["steps"][m]["conclusion"] for u in rows)
        out.append(f"| {m} {label} | {c.get('SUCCESS', 0)} | {c.get('REJECTED', 0)} | {c.get('HOLD', 0)} | {c.get('NOT_APPLICABLE', 0)} | {c.get('NOT_DONE', 0)} |")
    out += ["", "「成功」は基準計算と同じ結果になることを確かめたもの（M1・M2 だけにある）。近似の段階（M3〜M6）で採用した候補はない。"
            "「不採用」は測定のうえで採らなかったもの、「保留」は架空データでは判断できず実データが要るもの、"
            "「候補なし」は測定をせずに理由だけで見送ったもの（理由は `progress_ledger.json` と `03_MODELS/records/units.json`）。", "",
            "## 単位別の状態", "",
            "| 着手順 | 群 | ID | 名称 | 状態 | M1 | M2 | M3 | M4 | M5 | M6 | 統合先モデル | 保留中の段階 |",
            "|---:|---:|---|---|---|---|---|---|---|---|---|---|---|"]
    for u in rows:
        steps = " | ".join(mark[u["steps"][m]["conclusion"]] for m in STEPS)
        out.append(f"| {u.get('order') or ''} | {u.get('wave') or ''} | {u['id']} | {u['name']} | {u['status_label']} | {steps} | "
                   f"{', '.join(u.get('unified_models') or []) or '—'} | {', '.join(u['steps_on_hold']) or '—'} |")
    if unit_holds:
        out += ["", "## 単位そのものが保留のもの", ""]
        out += [f"- **{u['id']} {u['name']}**：{u.get('unit_hold_reason') or '理由未記入'}" for u in unit_holds]
    out += ["", "## 段階の意味", ""]
    out += [f"- **{m}**：{label}" for m, label in STEPS.items()]
    REPORT.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote {REPORT.name}: {dict(counts)}")
    return 0


COMMANDS = {"init": cmd_init, "merge": cmd_merge, "rollup": cmd_rollup, "check": cmd_check, "report": cmd_report}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(2)
    sys.exit(COMMANDS[sys.argv[1]]())
