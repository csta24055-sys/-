"""学習設計台帳（第10部 10-4）・論文と教材の差分表（10-3(10)）・問題台帳（10-5）。

重要度（学習上）と証拠の強さを別の列に持つ。旧 structlab-exam の scoring.py の点数・閾値は使わない。
  S 核心・前提: 欠くと各章の結論を誤解する論点
  A 実務・応用上の重要論点
  B 補足・専門的発展（前提と適用範囲が限られる）
  C 未確認・旧仕様・否定された仮説・対象外（消去せず、理由と差異を残す）
重要度を変えたときは learning_design_log.csv に旧値・新値・理由・確認者を追記する。
"""
from __future__ import annotations

import re
from pathlib import Path

from research_pipeline.common import read_csv, write_csv

COLS = ["unit_id", "chapter", "topic", "importance", "importance_reason", "evidence_strength",
        "evidence_warning", "used_in_materials", "reviewer", "reviewed_at"]
LOG_COLS = ["at", "unit_id", "old", "new", "reason", "reviewer"]
QCOLS = ["question_id", "file", "paper_version", "section_id", "claim_ids", "difficulty", "type",
         "answer_status", "data_kind", "learning_objective"]
LEVELS = {"S", "A", "B", "C"}
E_RX = re.compile(r"^(E\d)")


def evidence_strength(a, unit_id: str) -> tuple[str, str]:
    """段落が引く主張の証拠水準（E1/E2/E3）をまとめる。E1 だけなら独立検証なし。"""
    claims = a.led.index("claims")
    blk = a.units[unit_id].block
    levels = sorted({m.group(1) for c in blk.ids("claims") if c in claims
                     for m in [E_RX.match(claims[c]["evidence_level"])] if m})
    kinds = {"E1": "開発者の公式資料（独立検証なし）", "E2": "無作為化試験の中間報告", "E3": "無作為化比較試験"}
    if not levels:
        return "根拠なし（本研究の方法・提案・限界）", ""
    return "＋".join(f"{lv} {kinds.get(lv, '')}" for lv in levels), ("独立検証なし" if levels == ["E1"] else "")


def validate(rows: list[dict], a) -> list[str]:
    errs = []
    seen = set()
    for r in rows:
        u = r["unit_id"]
        if u not in a.units:
            errs.append(f"学習設計台帳: 存在しない段落 {u}")
        if u in seen:
            errs.append(f"学習設計台帳: 段落の重複 {u}")
        seen.add(u)
        if r["importance"] not in LEVELS:
            errs.append(f"学習設計台帳 {u}: 重要度は S/A/B/C")
        if not r["importance_reason"]:
            errs.append(f"学習設計台帳 {u}: 重要度の理由が無い")
    missing = [u for u in a.units if u not in seen]
    if missing:
        errs.append(f"学習設計台帳: 未登録の論文段落 {missing}")
    return errs


def refresh(root: Path, a) -> list[dict]:
    """計算で決まる列（証拠の強さ・警告・使用教材）を更新する。人が決める列（重要度・理由）は変えない。"""
    path = root / "education" / "learning_design.csv"
    rows = read_csv(path)
    used: dict[str, list[str]] = {}
    for key, it in a.edu_items.items():
        for u in it.block.ids("units"):
            used.setdefault(u, []).append(key)
    for r in rows:
        if r["unit_id"] not in a.units:
            continue
        es, warn = evidence_strength(a, r["unit_id"])
        if r["importance"] == "S" and warn:
            warn = "S相当の重要性・独立検証なし（開発者の経験則として教える）"
        r["evidence_strength"], r["evidence_warning"] = es, warn
        r["used_in_materials"] = ";".join(sorted({k.split("#")[0] for k in used.get(r["unit_id"], [])}))
    write_csv(path, COLS, rows)
    return rows


def question_rows(a) -> list[dict]:
    from research_pipeline import trace as TR
    out = []
    for key, it in sorted(a.edu_items.items()):
        b = it.block
        if b.kind != "quiz":
            continue
        out.append({"question_id": key, "file": str(it.doc.path.relative_to(a.root)),
                    "paper_version": it.doc.meta.get("paper_version", ""), "section_id": ";".join(b.ids("units")),
                    "claim_ids": ";".join(b.ids("claims")), "difficulty": b.attrs.get("level", ""),
                    "type": b.attrs.get("type", ""), "answer_status": TR.quiz_status(b),
                    "data_kind": b.attrs.get("data", "未設定"), "learning_objective": ";".join(b.ids("lo"))})
    return out


def diff_blocks(a, rows: list[dict]) -> list[dict]:
    """論文と教材の差分表: 段落ごとに、教材での扱い・教材で使わなかった主張・省略による誤解の恐れ。"""
    claims = a.led.index("claims")
    used_claims: dict[str, set] = {}
    used_docs: dict[str, set] = {}
    for key, it in a.edu_items.items():
        for u in it.block.ids("units"):
            used_claims.setdefault(u, set()).update(it.block.ids("claims"))
            used_docs.setdefault(u, set()).add(key.split("#")[0])
    imp = {r["unit_id"]: r for r in rows}
    table = [["論文段落", "種類", "重要度", "教材での扱い", "教材で使っていない主張", "省略による誤解の恐れ"]]
    for uid, it in a.units.items():
        cl = it.block.ids("claims")
        omitted = [c for c in cl if c not in used_claims.get(uid, set())]
        r = imp.get(uid, {})
        caveat = [c for c in omitted if claims.get(c, {}).get("statement_summary", "") and
                  re.search(r"限界|鮮度|代表性|信頼|不適切|選択|注記", claims[c]["statement_summary"])]
        if not used_docs.get(uid):
            risk = "教材で未使用" + ("（S: 要対応）" if r.get("importance") == "S" else "")
        elif caveat:
            risk = "注意書き・限界の主張が教材に無い: " + ", ".join(caveat)
        elif omitted:
            risk = "低（補足的な主張の省略）"
        else:
            risk = "なし（全主張を使用）"
        table.append([uid, it.block.kind, r.get("importance", "未登録"),
                      "・".join(sorted(used_docs.get(uid, []))) or "未使用",
                      ", ".join(omitted) or "なし", risk])
    return [{"t": "title", "text": "論文と教材の差分表（自動生成）"},
            {"t": "small", "text": "第10部 10-3(10)。各論文段落が、どの教材でどう使われ、どの主張を教材で使っていないかを示す。"
                                   "「注意書き・限界の主張が教材に無い」は、省略で誤解が起きうる箇所として確認が必要。"},
            {"t": "table", "rows": table, "widths_mm": [18, 18, 12, 50, 36, 40]}]
