"""第10部 10-7・10-8：教材の内容を表示形式から分離した学習データ（learning/）を作る。

入力は追跡監査の結果（trace.audit）と学習設計台帳。出力（研究フォルダの learning/ 配下）:
- lessons.csv               教材の節（## 見出しごと）＝ lesson。論文の段落・主張・資料への対応
- questions.csv             問題ごとの正答・解説・原文位置・検算方法・仮定値の有無
- learning_evidence_map.csv 資料 → 主張 → 論文段落 → lesson → 問題 の経路（1行1経路）
- prioritization.csv        学習上の重要度（S/A/B/C）と証拠の強さの二軸
- curriculum.yaml           章・対象読者・到達目標（学習目標）
- README.md                 版・親論文の SHA-256・台帳の版・生成日・QA 状態

同じ入力からは同じ内容を出す（日時は引数で渡す）。
"""
from __future__ import annotations

import re
from pathlib import Path

from research_pipeline import blocks as BL
from research_pipeline import trace as TR
from research_pipeline.common import file_sha256, read_csv, write_csv

LESSON_COLS = ["lesson_id", "paper_id", "paper_version", "section_id", "source_ids", "claim_ids", "model_ids", "level",
               "importance", "evidence_strength", "explanation", "example", "counterexample", "limits",
               "last_verified_at", "review_status", "file", "heading", "material_version"]
QUESTION_COLS = ["question_id", "lesson_id", "type", "prompt", "correct_answers", "rationale", "source_location",
                 "answer_validation", "assumptions", "synthetic_data_flag", "level", "status", "learning_objective",
                 "section_id", "claim_ids", "paper_version"]
MAP_COLS = ["source_id", "claim_id", "paper_unit", "lesson_id", "question_id"]
PRIO_COLS = ["unit_id", "topic", "importance", "importance_reason", "evidence_strength", "evidence_warning",
             "used_in_materials", "quadrant"]
# 教材ファイル名 → 学習レベル（10-8 の beginner/intermediate/advanced と対応）
LEVEL_BY_FILE = {"00": "初級", "01": "初級", "07": "初級", "03": "中級", "05": "中級", "08": "中級", "02": "上級",
                 "06": "上級", "04": "問題"}
EXPLAIN = {"fact", "term", "step", "synthesis", "derivation", "calc", "objective", "proposal"}
EXAMPLE = {"analogy", "tip"}
RANK = {"S": 0, "A": 1, "B": 2, "C": 3}


def _short(text: str, n: int = 400) -> str:
    t = re.sub(r"\s+", " ", text).strip()
    return t if len(t) <= n else t[: n - 1] + "…"


def lessons(a, root: Path, design: dict, verified_at: str, review_status: str) -> tuple[list[dict], dict]:
    claims = a.led.index("claims")
    rows, block_lesson = [], {}
    for doc in a.edus:
        fname = Path(doc.path).name.replace(".src.md", "")
        level = LEVEL_BY_FILE.get(fname[:2], "")
        groups: list[tuple[str, list]] = []
        heading = "（冒頭）"
        for it in doc.items:
            if it[0] == "heading":
                if it[1] <= 2:
                    heading = it[2]
                    groups.append((heading, []))
                continue
            if not groups:
                groups.append((heading, []))
            groups[-1][1].append(it[1])
        for i, (head, blocks) in enumerate(groups, 1):
            blocks = [b for b in blocks if b.kind != "quiz"]
            if not blocks:
                continue
            lid = f"{fname}#L{i:02d}"
            units = list(dict.fromkeys(u for b in blocks for u in b.ids("units")))
            cids = list(dict.fromkeys(c for b in blocks for c in b.ids("claims")))
            for b in blocks:
                block_lesson[(fname, b.id)] = lid
            imps = [design.get(u, {}).get("importance", "") for u in units]
            imps = sorted([x for x in imps if x in RANK], key=RANK.get)
            ev = sorted({design.get(u, {}).get("evidence_strength", "") for u in units} - {""})
            rows.append(dict(
                lesson_id=lid, paper_id="P8-development_engineering", paper_version=doc.meta.get("paper_version", ""),
                section_id=";".join(units), source_ids=";".join(dict.fromkeys(claims[c]["source_id"] for c in cids if c in claims)),
                claim_ids=";".join(cids), model_ids="", level=level, importance=imps[0] if imps else "",
                evidence_strength=" ／ ".join(ev)[:400],
                explanation=_short(" ".join(b.text for b in blocks if b.kind in EXPLAIN), 600),
                example=_short(" ".join(b.text for b in blocks if b.kind in EXAMPLE)),
                counterexample=_short(" ".join(b.text for b in blocks if "反例" in b.text or b.attrs.get("role") == "counterexample")),
                limits=_short(" ".join(b.text for b in blocks if b.kind == "limitation")),
                last_verified_at=verified_at, review_status=review_status, file=f"{fname}.src.md", heading=head,
                material_version=doc.meta.get("version", "")))
    return rows, block_lesson


def questions(a, block_lesson: dict) -> list[dict]:
    claims = a.led.index("claims")
    rows = []
    for key, it in a.edu_items.items():
        b = it.block
        if b.kind != "quiz":
            continue
        fname = key.split("#")[0]
        q = TR.parse_quiz(b)
        t = b.attrs.get("type", "")
        ans = b.attrs.get("answer", "")
        if t == "choice":
            correct = f"{ans}) " + next((c[1] for c in q["choices"] if c[0] == ans), "")
            validation = "選択肢の形式と正答キーを自動検査（内容は独立監査で確認）"
        elif t == "tf":
            correct, validation = ans, "正答キー（○/×）を自動検査（内容は独立監査で確認）"
        elif t == "calc":
            correct = b.attrs.get("expect", ans)
            validation = f"分数で厳密に自動検算（expr={b.attrs.get('expr', '')}）"
        else:
            correct, validation = q["model"], "解答例あり（採点は人の判断が必要）"
        data = b.attrs.get("data", "")
        locs = [f"{c}→{claims[c]['source_id']}「{claims[c]['original_position']}」" for c in b.ids("claims") if c in claims]
        units = b.ids("units")
        rows.append(dict(
            question_id=key, lesson_id="", type=t, prompt=_short(q["stem"], 500), correct_answers=_short(correct, 300),
            rationale=_short(q["explain"], 800), source_location=" ／ ".join(locs)[:800], answer_validation=validation,
            assumptions="教材上の仮定値を使用" if data == "教材上の仮定値" else "",
            synthetic_data_flag="true" if data == "教材上の仮定値" else "false", level=b.attrs.get("level", ""),
            status=TR.quiz_status(b), learning_objective=";".join(b.ids("lo")), section_id=";".join(units),
            claim_ids=";".join(b.ids("claims")), paper_version=it.doc.meta.get("paper_version", "")))
    return rows


def link_questions_to_lessons(qrows: list[dict], lrows: list[dict]) -> None:
    """問題 → lesson：同じ論文段落を多く共有する lesson（教材本文側）を対応先にする。"""
    for q in qrows:
        qu = set(q["section_id"].split(";")) - {""}
        best, score = "", 0
        for l in lrows:
            if l["file"].startswith("04"):
                continue
            s = len(qu & (set(l["section_id"].split(";")) - {""}))
            if s > score:
                best, score = l["lesson_id"], s
        q["lesson_id"] = best


def evidence_map(a, lrows: list[dict], qrows: list[dict]) -> list[dict]:
    claims = a.led.index("claims")
    rows = []
    for l in lrows:
        for c in [x for x in l["claim_ids"].split(";") if x]:
            for u in [x for x in l["section_id"].split(";") if x and c in a.units[x].block.ids("claims")] or [""]:
                qs = [q["question_id"] for q in qrows if q["lesson_id"] == l["lesson_id"] and c in q["claim_ids"].split(";")]
                for q in qs or [""]:
                    rows.append(dict(source_id=claims[c]["source_id"] if c in claims else "", claim_id=c, paper_unit=u,
                                     lesson_id=l["lesson_id"], question_id=q))
    return rows


def prioritization(design_rows: list[dict]) -> list[dict]:
    out = []
    for r in design_rows:
        strong = not r.get("evidence_warning") and not r.get("evidence_strength", "").startswith("根拠なし")
        hi = r.get("importance") in ("S", "A")
        quad = ("重要・独立検証あり" if strong else "重要・独立検証なし（経験則として教える）") if hi else \
            ("補足・独立検証あり" if strong else "補足・独立検証なし")
        out.append({**{k: r.get(k, "") for k in PRIO_COLS if k != "quadrant"}, "quadrant": quad})
    return out


def curriculum_yaml(a, chapter_plan: list[tuple[str, str, str]]) -> str:
    los = []
    for key, it in sorted(a.edu_items.items()):
        if it.block.kind == "objective":
            los.append((it.block.id, re.sub(r"\s+", " ", it.block.text).strip(), ";".join(it.block.ids("units"))))
    lines = ["# 第10部 10-8：章・対象読者・到達目標（自動生成。手で編集しない）", "chapters:"]
    for ch, title, status in chapter_plan:
        lines += [f"  - id: {ch}", f"    title: \"{title}\"", f"    status: \"{status}\""]
    lines += ["audiences:", "  - {id: beginner, files: [00, 01, 07], note: \"前提知識なし\"}",
              "  - {id: intermediate, files: [03, 05, 08], note: \"開発・研究の実務者\"}",
              "  - {id: advanced, files: [02, 06], note: \"原典と論文を読み比べる人\"}", "objectives:"]
    for lo, text, units in sorted(set(los)):
        lines.append(f"  - {{id: {lo}, units: \"{units}\", text: \"{text.replace(chr(34), '')}\"}}")
    return "\n".join(lines) + "\n"


def write_all(root: Path, a, verified_at: str, review_status: str, chapter_plan: list[tuple[str, str, str]],
              qa_state: str) -> dict:
    out = root / "learning"
    for sub in ["drafts", "beginner", "intermediate", "advanced", "practical_manuals", "comparison_tables", "glossary",
                "exercises", "flashcards", "figures", "exports", "audit", "revisions"]:
        (out / sub).mkdir(parents=True, exist_ok=True)
    design_rows = read_csv(root / "education" / "learning_design.csv")
    design = {r["unit_id"]: r for r in design_rows}
    lrows, block_lesson = lessons(a, root, design, verified_at, review_status)
    qrows = questions(a, block_lesson)
    link_questions_to_lessons(qrows, lrows)
    mrows = evidence_map(a, lrows, qrows)
    write_csv(out / "lessons.csv", LESSON_COLS, lrows)
    write_csv(out / "questions.csv", QUESTION_COLS, qrows)
    write_csv(out / "learning_evidence_map.csv", MAP_COLS, mrows)
    write_csv(out / "prioritization.csv", PRIO_COLS, prioritization(design_rows))
    (out / "curriculum.yaml").write_text(curriculum_yaml(a, chapter_plan), encoding="utf-8")
    papers = sorted((root / "papers").rglob("*.src.md"))
    led_files = ["sources/sources.csv", "claims/claims.csv", "people/people.csv", "people/role_evidence.csv"]
    readme = ["# learning/（第10部 10-8）", "",
              "教材の内容（`education/` の正本）を表示形式から分けた学習データ。自動生成なので手で編集しない。", "",
              f"- 生成日: {verified_at}", f"- QA 状態: {qa_state}", "", "## 親論文", "", "| ファイル | 版 | SHA-256 |",
              "|---|---|---|"]
    for p in papers:
        d = BL.parse(p)
        readme.append(f"| {p.relative_to(root)} | {d.meta.get('version', '')} | {file_sha256(p)} |")
    readme += ["", "## 対応するデータ台帳", "", "| ファイル | SHA-256 |", "|---|---|"]
    for f in led_files:
        if (root / f).exists():
            readme.append(f"| {f} | {file_sha256(root / f)} |")
    readme += ["", "## 教材", "", "| ファイル | 教材の版 | 準拠する論文の版 | 状態 |", "|---|---|---|---|"]
    for d in a.edus:
        name = Path(d.path).name
        readme.append(f"| {name} | {d.meta.get('version', '')} | {d.meta.get('paper_version', '')} | {d.meta.get('status', '')} |")
    readme += ["", "## 生成物の件数", "", f"- lessons: {len(lrows)}", f"- questions: {len(qrows)}",
               f"- evidence map rows: {len(mrows)}"]
    (out / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")
    return {"lessons": len(lrows), "questions": len(qrows), "map": len(mrows)}
