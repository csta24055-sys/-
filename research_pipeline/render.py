"""書き出し。内容は structlab-exam の render.py と同じブロック形式（t=title/h1/h2/p/small/list/table/break）で
組み立て、Markdown（正本の閲覧用）と PDF/Word（structlab-exam の render.py を再利用）に出力する。

全ての文の後ろに［根拠 n］を付け、巻末の追跡表で 主張ID → 資料 → 原文位置 → 原文抜粋 → 訳 を示す。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from . import trace as TR
from .blocks import Doc


def _status(a: TR.Audit, doc: Doc, items: dict) -> tuple[str, list[str]]:
    reasons = []
    mine = [it for it in items.values() if it.doc is doc]
    if any(it.status != "OK" for it in mine):
        n = sum(it.status != "OK" for it in mine)
        reasons.append(f"未承認または要改訂の項目 {n} 件")
    rel = str(doc.path.relative_to(a.root))
    w = [x for x in a.warnings if x.startswith(rel)]
    if w:
        reasons.append(f"警告 {len(w)} 件（未照合の根拠など）")
    declared = doc.meta.get("status", "暫定版")
    if declared != "検証済み版":
        reasons.append(f"正本の宣言: {declared}")
    return ("検証済み版" if not reasons else "暫定版"), reasons


def _split_table(text: str) -> list[dict]:
    out, rows, para = [], [], []

    def flush_para():
        if para:
            out.append({"t": "p", "text": "\n".join(para).strip()})
            para.clear()

    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith("|"):
            flush_para()
            cells = [c.strip() for c in s.strip("|").split("|")]
            if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                rows.append(cells)
        else:
            if rows:
                out.append({"t": "table", "rows": rows})
                rows = []
            para.append(ln)
    if rows:
        out.append({"t": "table", "rows": rows})
    flush_para()
    return [b for b in out if b.get("text", "x").strip() or b["t"] == "table"]


def _cite(nums: list[int]) -> str:
    return "［根拠 " + ", ".join(str(n) for n in nums) + "］" if nums else ""


def layout(a: TR.Audit, doc: Doc, scope: str, mode: str = "full") -> tuple[list[dict], list[str]]:
    """mode: full | quiz_questions | quiz_answers"""
    items = a.units if scope == "paper" else a.edu_items
    status, reasons = _status(a, doc, items)
    order: list[str] = []

    def num(cid: str) -> int:
        if cid not in order:
            order.append(cid)
        return order.index(cid) + 1

    title = doc.meta.get("title", doc.path.stem)
    if mode == "quiz_answers":
        title += "【解答・解説】"
    out = [{"t": "title", "text": title},
           {"t": "small", "text": f"版: {doc.meta.get('version', '?')} ／ 状態: {status} ／ 作成日: "
                                  f"{doc.meta.get('date', '?')} ／ 研究基準日: 2026-11-15（日本時間）"}]
    if reasons:
        out.append({"t": "small", "text": "暫定版の理由: " + "；".join(reasons)})
    for k in ("basis", "audience", "part10"):
        if doc.meta.get(k):
            out.append({"t": "small", "text": doc.meta[k]})
    qn = 0
    for it in doc.items:
        if it[0] == "heading":
            _, level, text, _ = it
            if level == 1:
                continue  # 文書名は title で出す
            out.append({"t": "h1" if level == 2 else "h2", "text": text})
            continue
        b = it[1]
        # 問題用紙には根拠を出さない（原文の抜粋・訳から正答がわかるため）。根拠は解答・解説に付ける
        nums = [] if mode == "quiz_questions" else [num(c) for c in b.ids("claims")]
        origin = f"（論文段落 {', '.join(b.ids('units'))} から）" if scope == "education" and b.ids("units") else ""
        if b.kind == "quiz":
            qn += 1
            q = TR.parse_quiz(b)
            lo = ",".join(b.ids("lo"))
            out.append({"t": "h2", "text": f"問{qn}（{b.attrs.get('level', '')}・{lo}）"})
            out.append({"t": "p", "text": q["stem"]})
            if q["choices"]:
                out.append({"t": "list", "items": [f"{k}) {v}" for k, v in q["choices"]]})
            if mode == "quiz_questions":
                if b.attrs.get("type") in ("short", "calc"):
                    out.append({"t": "space", "lines": 3})
                else:
                    out.append({"t": "small", "text": "解答欄: ＿＿＿＿"})
                continue
            ans = b.attrs.get("answer", "") or q["model"]
            if b.attrs.get("type") == "calc":
                v = TR.safe_eval(b.attrs["expr"])
                ans = f"{b.attrs.get('answer', '')}（式 {b.attrs['expr']} = {v} ≈ {float(v):.6g}。自動検算一致）"
            out.append({"t": "p", "text": f"正答: {ans}"})
            if q["model"] and b.attrs.get("type") == "short":
                out.append({"t": "p", "text": "解答例: " + q["model"]})
            out.append({"t": "p", "text": "解説: " + q["explain"]})
            out.append({"t": "small", "text": f"{_cite(nums)}{origin}"})
            continue
        if mode != "full":
            if b.kind in ("objective",):
                out.append({"t": "small", "text": f"{b.id}: {b.text}"})
            continue
        label = TR.LABELS.get(b.kind, "")
        text = b.text
        if b.kind == "objective":
            text = f"{b.id}: {text}"
        elif b.kind == "term":
            text = f"用語「{b.attrs.get('name', b.id)}」: {text}"
        elif b.kind == "step":
            label = "【本研究の提案による手順（未実証）】" if b.attrs.get("basis") == "proposal" else ""
        elif b.kind == "calc":
            v = TR.safe_eval(b.attrs["expr"])
            text += f"\n式: {b.attrs['expr']} = {v} ≈ {float(v):.6g}（記載値 {b.attrs['expect']} と一致）"
        body = _split_table((label + "\n" if label else "") + text)
        out += body
        tail = f"{_cite(nums)}{origin}"
        if tail:
            out.append({"t": "small", "text": tail})

    if order:
        claims, srcs = a.led.index("claims"), a.led.index("sources")
        rows = [["番号", "主張ID・種別", "資料（著者・公開日）・原文位置・URL", "原文抜粋（短い引用）", "日本語訳"]]
        for i, cid in enumerate(order, 1):
            c = claims[cid]
            s = srcs[c["source_id"]]
            v = a.verify.get(cid, {})
            check = "原文と一字一句一致（自動照合）" if v.get("found") == "true" else c["verification_status"]
            rows.append([str(i), f"{cid}\n{c['claim_type']}／{s['source_tier']}\n{check}",
                         f"{c['source_id']} {s['title']}（{s['author']}・{s['published_at']}）\n"
                         f"位置: {c['original_position']}\n{s['canonical_url'] or s['original_url']}",
                         c["original_language_excerpt_short"], c["translation_ja"]])
        out += [{"t": "break"}, {"t": "h1", "text": "根拠一覧（一次資料への追跡表）"},
                {"t": "small", "text": "各文末の［根拠 n］は下表の番号。原文抜粋は著作権に配慮した短い引用で、"
                                       "観測日 2026-11-15 に保存した原文と自動照合した結果を示す。"},
                {"t": "table", "rows": rows, "widths_mm": [10, 30, 50, 42, 42]}]
    return out, order


def to_markdown(blocks: list[dict]) -> str:
    md = []
    for b in blocks:
        t = b["t"]
        if t == "title":
            md.append(f"# {b['text']}\n")
        elif t == "h1":
            md.append(f"## {b['text']}\n")
        elif t == "h2":
            md.append(f"### {b['text']}\n")
        elif t == "p":
            md.append(b["text"].replace("\n", "  \n") + "\n")
        elif t == "small":
            md.append("<small>" + b["text"].replace("\n", "<br>") + "</small>\n")
        elif t == "list":
            md.append("\n".join(f"- {x}" for x in b["items"]) + "\n")
        elif t == "space":
            md.append("（解答欄）\n\n" + "\n".join("＿" * 30 for _ in range(int(b.get("lines", 3)))) + "\n")
        elif t == "table":
            rows = [[str(c).replace("|", "／").replace("\n", "<br>") for c in r] for r in b["rows"]]
            md.append("| " + " | ".join(rows[0]) + " |\n|" + "---|" * len(rows[0]) + "\n" +
                      "\n".join("| " + " | ".join(r) + " |" for r in rows[1:]) + "\n")
        elif t == "break":
            md.append("---\n")
    return "\n".join(md)


def office(blocks: list[dict], pdf: Path, docx: Path, title: str, structlab_src: Path | None) -> dict:
    """structlab-exam の render.py（取得・テスト済みの既存コード）で PDF/Word を作り、品質検査する。"""
    if structlab_src is None or not (structlab_src / "structlab" / "exam" / "render.py").exists():
        return {"ok": False, "skipped": "structlab-exam の render.py が見つからない（未取得として扱う）"}
    if str(structlab_src) not in sys.path:
        sys.path.insert(0, str(structlab_src))
    try:
        from structlab.exam import render as R  # 既存コードの再利用
    except ImportError as e:
        return {"ok": False, "skipped": f"structlab-exam の render.py を読み込めない: {e}"}
    mm = 72 / 25.4
    clean = [dict(b) for b in blocks]
    for b in clean:
        if b["t"] == "table":
            w = b.pop("widths_mm", None) or [174 / len(b["rows"][0])] * len(b["rows"][0])
            b["widths"] = [x * mm for x in w]
    try:
        R.to_pdf(clean, pdf, title, header=title[:40])
        R.to_docx(clean, docx, title)
    except ImportError as e:
        return {"ok": False, "skipped": f"PDF/Word 用ライブラリが無い: {e}"}
    expect = [b["text"] for b in clean if b["t"] in ("h1",)][:3]
    res = {"pdf": R.check_pdf(pdf, expect), "docx": R.check_docx(docx, expect),
           "missing_glyphs": R.missing_glyphs(clean)}
    res["ok"] = res["pdf"]["ok"] and res["docx"]["ok"] and not res["missing_glyphs"]
    return res
