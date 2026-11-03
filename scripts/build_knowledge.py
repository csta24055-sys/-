"""knowledge_data.py から アプリ用 JSON と Markdown 文書を生成する。

使い方:  python scripts/build_knowledge.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "backend"))

import knowledge_data as K  # noqa: E402
from aqros.models import MODEL_REGISTRY  # noqa: E402

OUT = ROOT / "knowledge"
DOCS = ROOT / "docs"


def build_graph() -> dict:
    nodes, edges = [], []

    def node(id, type, label, detail="", sources=()):
        nodes.append({"id": id, "type": type, "label": label, "detail": detail, "sources": list(sources)})

    for st in K.STUDIES:
        node(st["id"], "研究", st["label"], st["outcome"], st["sources"])
    for a, b in zip(K.STUDIES, K.STUDIES[1:]):
        edges.append({"from": a["id"], "to": b["id"], "rel": "継承"})
    for f in K.FINDINGS:
        node(f["id"], "成果", f["id"] + " " + f["text"][:24] + "…", f"【{f['class']}】{f['text']}", f["sources"])
        if f["study"]:
            edges.append({"from": f["study"], "to": f["id"], "rel": "成果"})
    devices = {
        "D-EP": ("電気集塵機（セントラル型）", ["Y2018", "Y2021", "Y2022", "Y2024", "Y2025", "Y2026"]),
        "D-PC": ("パーティクルカウンター KC-52", ["Y2018", "Y2021", "Y2022", "Y2023", "Y2026"]),
        "D-DM": ("粉塵計 KANOMAX 3442", ["Y2018", "Y2020", "Y2021"]),
        "D-WS": ("ワイヤレスPMセンサー（Watty）", ["Y2024", "Y2025"]),
        "D-BOX": ("実験BOX（1〜8 m³）", ["Y2018", "Y2020", "Y2021", "Y2022"]),
        "D-HOUSE": ("実験住宅（床吹出型全館空調）", ["Y2018", "Y2020", "Y2021", "Y2022"]),
        "D-FAN": ("風量一定制御送風機", ["Y2026"]),
        "D-AIRTIGHT": ("住宅用気密測定器・微差圧計", ["Y2026"]),
    }
    for did, (label, studies) in devices.items():
        node(did, "装置", label)
        for s in studies:
            edges.append({"from": s, "to": did, "rel": "使用"})
    meas = {
        "M-COUNT": ("粒径別個数濃度 [個/m³]", ["D-PC"]),
        "M-MASS": ("質量濃度 [μg/m³]", ["D-WS", "D-DM"]),
        "M-IO": ("I/O比", ["Y2024", "Y2025"]),
        "M-BETA": ("沈着係数 β [1/s]", ["Y2021", "Y2022"]),
        "M-DP": ("差圧 ΔP [Pa]・風量 Q [m³/h]", ["D-AIRTIGHT"]),
        "M-W": ("消費電力 [W]", ["D-FAN"]),
        "M-CADR": ("CADR [m³/h]", ["Y2026"]),
    }
    for mid, (label, links) in meas.items():
        node(mid, "測定項目", label)
        for l in links:
            edges.append({"from": l, "to": mid, "rel": "測定"})
    for h in K.HYPOTHESES:
        node(h["id"], "仮説", h["title"], h["expected"])
        for f in h["related_findings"]:
            edges.append({"from": f, "to": h["id"], "rel": "根拠"})
    for q in K.OPEN_QUESTIONS:
        node(q["id"], "未解決問題", q["text"][:28], q["text"])
        for r in q["related"]:
            if r.startswith(("H-", "F-")):
                edges.append({"from": r, "to": q["id"], "rel": "未解決"})
    for t in K.THEMES:
        node(t["id"], "研究テーマ", t["name"], t["why_now"])
        for h in t["hypotheses"]:
            edges.append({"from": h, "to": t["id"], "rel": "検証"})
        for ref in sorted(set(re.findall(r"F-[A-Z0-9]+-\d+", t.get("evaluation", {}).get("evidence", "")))):
            edges.append({"from": ref, "to": t["id"], "rel": "評価根拠"})
    ids = {n["id"] for n in nodes}
    edges = [e for e in edges if e["from"] in ids and e["to"] in ids]
    return {"nodes": nodes, "edges": edges}


def write_json():
    OUT.mkdir(exist_ok=True)
    data = {
        "studies": K.STUDIES,
        "sources": K.SOURCES,
        "external": K.EXTERNAL,
        "findings": K.FINDINGS,
        "hypotheses": K.HYPOTHESES,
        "questions": K.OPEN_QUESTIONS,
        "themes": K.THEMES,
        "roadmap": K.ROADMAP,
        "models": MODEL_REGISTRY,
        "graph": build_graph(),
        "validation": {
            "multizone": json.loads((OUT / "validation_multizone.json").read_text(encoding="utf-8")) if (OUT / "validation_multizone.json").exists() else None,
            "fate2022": json.loads((OUT / "validation_fate_2022.json").read_text(encoding="utf-8")) if (OUT / "validation_fate_2022.json").exists() else None,
            "raw2024": json.loads((OUT / "verification_2024.json").read_text(encoding="utf-8")) if (OUT / "verification_2024.json").exists() else None,
            "annual2025": json.loads((OUT / "verification_annual_2025.json").read_text(encoding="utf-8")) if (OUT / "verification_annual_2025.json").exists() else None,
            "raw2025": json.loads((OUT / "verification_2025.json").read_text(encoding="utf-8")) if (OUT / "verification_2025.json").exists() else None,
        },
        "meta": {"accessed": K.ACCESSED, "generator": "scripts/build_knowledge.py"},
    }
    (OUT / "knowledge.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return data


def md_table(rows, headers):
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for r in rows:
        out.append("| " + " | ".join(str(x).replace("|", "／").replace("\n", " ") for x in r) + " |")
    return "\n".join(out)


def write_docs(d):
    src = {s["id"]: s for s in d["sources"]}
    c = Counter(s["status"] for s in d["sources"])
    hdr = "> このファイルは `scripts/build_knowledge.py` により `scripts/knowledge_data.py` から自動生成。直接編集しない。\n\n"

    # SOURCES.md
    lines = ["# SOURCES — 資料台帳", "", hdr,
             f"取得日: {K.ACCESSED}（Box MCP 経由, 読み取り専用）。調査状態: " + "、".join(f"{k} {v}件" for k, v in c.items()), "",
             "調査状態の定義: **未確認**=存在のみ/読めず、**目録確認**=ファイル名・場所・サイズのみ、**読了**=本文を通読、**数値検証済み**=本文の数値を本アプリで再計算して照合。", "",
             "原文は転載していない。要旨は本プロジェクトによる言い換え。個人名は記載しない。", ""]
    for fy in sorted({s["fiscal_year"] or 0 for s in d["sources"]}, reverse=True):
        rows = [s for s in d["sources"] if (s["fiscal_year"] or 0) == fy]
        lines.append(f"## {fy if fy else '年度不明・参考文献'}年度" if fy else "## 年度不明・参考文献")
        lines.append(md_table([[s["id"], s["status"], f"[{s['title']}]({s['link']})", s["box_id"], s["folder"], s["topic"], s["pages"] or "-"] for s in rows],
                              ["ID", "状態", "資料名", "Box ID", "フォルダ", "主題", "参照ページ"]))
        lines.append("")
        for s in rows:
            if s["status"] in ("読了", "数値検証済み"):
                lines += [f"### {s['id']} {s['title']}", ""]
                for k, lab in [("purpose", "目的"), ("conditions", "実験条件"), ("instruments", "測定器"), ("measurements", "測定項目・単位"),
                               ("raw_data", "原データ"), ("methods", "手法"), ("results", "結果"), ("conclusions", "結論【当事者の主張】"),
                               ("limitations", "限界・未解決【分析】"), ("related", "関連"), ("version", "版")]:
                    if s.get(k):
                        lines.append(f"- **{lab}**: {s[k]}")
                lines.append("")
    lines += ["## Box外の公開情報", "", md_table([[e["id"], f"[{e['title']}]({e['url']})", e["note"]] for e in d["external"]], ["ID", "資料", "要点"])]
    (ROOT / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # FINDINGS.md
    lines = ["# FINDINGS — 研究上の知見", "", hdr,
             "区分: 【確認事実】資料に数値・観測として記載 / 【当事者の主張】資料著者の解釈 / 【分析】本プロジェクトの分析 / 【仮説】/【予測】/【計算結果】本アプリのプログラムによる再計算 / 【不明】", ""]
    for f in d["findings"]:
        refs = ", ".join(f"[{s}]({src[s]['link']})" if s in src else s for s in f["sources"])
        lines.append(f"- **{f['id']}** 【{f['class']}】{f['text']}  — 出典: {refs}")
    (ROOT / "FINDINGS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # HYPOTHESES.md
    lines = ["# HYPOTHESES — 仮説と競合仮説", "", hdr]
    for h in d["hypotheses"]:
        lines += [f"## {h['id']} {h['title']}（{h['status']}）", "", f"関連知見: {', '.join(h['related_findings'])}", ""]
        lines.append(md_table([[c_["label"], c_["text"], c_["test"]] for c_ in h["competing"]], ["競合仮説", "内容", "判別方法"]))
        lines += ["", f"予想される分岐: {h['expected']}", ""]
    (ROOT / "HYPOTHESES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # OPEN_QUESTIONS.md
    lines = ["# OPEN_QUESTIONS — 未解決問題", "", hdr,
             md_table([[q["id"], q["priority"], q["text"], ", ".join(q["related"]), q["status"]] for q in d["questions"]], ["ID", "優先度", "問題", "関連", "状態"])]
    (ROOT / "OPEN_QUESTIONS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # 年度別研究分析
    DOCS.mkdir(exist_ok=True)
    lines = ["# 年度別研究分析（2018〜2026年度）", "", hdr]
    for st in d["studies"]:
        fs = [f for f in d["findings"] if f["study"] == st["id"]]
        lines += [f"## {st['label']}", "", f"**題目**: {st['title']}", "", f"- 研究課題: {st['question']}", f"- 方法: {st['method']}",
                  f"- 結果【当事者の主張】: {st['outcome']}", f"- 次年度への引継ぎ: {st['handover']}",
                  f"- 資料: {', '.join(st['sources'])}", ""]
        if fs:
            lines.append("知見:")
            lines += [f"- {f['id']} 【{f['class']}】{f['text']}" for f in fs]
            lines.append("")
    (DOCS / "年度別研究分析.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # 研究テーマ候補一覧
    lines = ["# 研究テーマ候補一覧", "", hdr, "評価は 1〜5（5が高い）。総合 = 重要度×0.35 + 新規性×0.2 + 実行可能性×0.25 + 既存設備適合×0.2 【分析】", ""]
    def total(t):
        s = t["scores"]
        return round(s["importance"] * .35 + s["novelty"] * .2 + s["feasibility"] * .25 + s["fit"] * .2, 2)
    lines.append(md_table([[t["id"], t["name"], t["horizon"], t["scores"]["importance"], t["scores"]["novelty"], t["scores"]["feasibility"], t["scores"]["fit"], total(t)]
                           for t in sorted(d["themes"], key=total, reverse=True)],
                          ["ID", "テーマ", "期間", "重要度", "新規性", "実行可能性", "設備適合", "総合"]))
    lines.append("")
    lines += ["## 実現可能性・新規性・必要設備・実験期間・失敗リスクの比較（2026-11-02 更新）【分析】", ""]
    ev = [t for t in sorted(d["themes"], key=total, reverse=True) if t.get("evaluation")]
    lines.append(md_table([[t["id"], t["evaluation"]["feasibility"], t["evaluation"]["novelty"], t["evaluation"]["equipment"],
                            "〜".join(str(m) for m in sorted(set(t["evaluation"]["months"]))), t["evaluation"]["failure_risk"], t["evaluation"]["failure_mode"]] for t in ev],
                          ["ID", "実現可能性", "新規性", "必要設備", "期間[月]", "失敗リスク", "失敗時の代替"]))
    lines += ["", "スコア変更: " + ("／".join(f"{t['id']} {t['evaluation']['score_change']}" for t in ev if t["evaluation"]["score_change"]) or "なし"), ""]
    labels = [("why_now", "なぜ今研究するべきか"), ("known", "既往研究から判明していること"), ("unsolved", "未解決の科学的問題"),
              ("equipment", "必要な実験装置"), ("measurements", "測定項目と実験条件"), ("procedure", "実験手順"), ("analysis", "解析方法"),
              ("data_needed", "必要なデータ"), ("branches", "予想される結果の分岐"), ("difficulty", "実施難易度"),
              ("duration_cost", "期間・費用の概算"), ("significance", "学術的・実用的意義"), ("risks", "失敗する可能性と代替手段")]
    for t in d["themes"]:
        lines += [f"## {t['id']} {t['name']}（{t['horizon']}）", "", f"- **検証すべき仮説**: {', '.join(t['hypotheses']) or '-'}"]
        lines += [f"- **{lab}**: {t[k]}" for k, lab in labels]
        if t.get("evaluation"):
            lines.append(f"- **評価の根拠（2026-11 資料読解・検証）**: {t['evaluation']['evidence']}")
        lines.append("")
    lines += ["## ロードマップ", ""] + [f"- **{r['phase']}**: " + " / ".join(r["items"]) for r in d["roadmap"]]
    (DOCS / "研究テーマ候補一覧.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    d = write_json()
    write_docs(d)
    print(f"sources={len(d['sources'])} findings={len(d['findings'])} hypotheses={len(d['hypotheses'])} "
          f"themes={len(d['themes'])} nodes={len(d['graph']['nodes'])} edges={len(d['graph']['edges'])}")
