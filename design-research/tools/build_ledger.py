#!/usr/bin/env python3
"""Build research-ledger.md (成果物1) from design-research/data/ledger-*.json.

Usage: python3 design-research/tools/build_ledger.py
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "research-ledger.md"

CATS = {
    "A": "A：大学・研究室内部で利用する研究支援アプリ",
    "B": "B：国家規模・公共性の高いプロジェクト向けアプリ",
    "C": "C：収益・利益追求型の商用アプリ",
    "D": "D：大企業品質のアプリ",
}
VERIFY = {
    "fetched_official_page": "公式ページを本セッションで取得",
    "search_results_only": "検索結果のみで確認",
    "prior_knowledge_only": "事前知識のみ（未確認）",
}
FIELDS = [
    ("what", "何をするアプリか"),
    ("users", "主な利用者"),
    ("layout_navigation", "画面構成とナビゲーション"),
    ("visual_traits", "配色・文字・余白・アイコン"),
    ("ux_strengths", "優れている操作体験"),
    ("weaknesses", "使いにくい点・制約"),
    ("adopt", "採用できる要素"),
    ("avoid", "採用すべきでない要素"),
]


def esc(s):
    return str(s).replace("|", "\\|").replace("\n", " ")


def main():
    entries = []
    bad = []
    for f in sorted(DATA.glob("ledger-*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            bad.append(f"{f.name}: {e}")
            continue
        items = d["entries"] if isinstance(d, dict) else d
        for e in items:
            e.setdefault("category", f.stem.split("-")[1])
            entries.append(e)

    by = {k: [e for e in entries if str(e.get("category", "")).upper().startswith(k)] for k in CATS}
    counts = {k: len(v) for k, v in by.items()}
    vcount = {}
    for e in entries:
        vcount[e.get("verification", "?")] = vcount.get(e.get("verification", "?"), 0) + 1

    lines = [
        "# 成果物1：世界の優良UI・UX事例 調査台帳",
        "",
        f"調査件数: **{len(entries)} 件**（" + " / ".join(f"{k}: {counts[k]}件" for k in CATS) + "）",
        "",
        "確認レベル（正直な記録）: " + " / ".join(f"{VERIFY.get(k, k)}: {v}件" for k, v in vcount.items()),
        "",
        "> 各項目の「確認レベル」は、調査エージェントがこのセッション中に実際に公式ページを開いたかどうかを示します。"
        "「検索結果のみ」「事前知識のみ」の項目は、画面の細部について未確認の記述を含む可能性があります。"
        "既存製品の画面は複製せず、設計原則の抽出にのみ利用しています。",
        "",
    ]
    if bad:
        lines += ["**読み込めなかったデータファイル:** " + "; ".join(bad), ""]

    # summary table
    lines += ["## 一覧", "", "| ID | 分類 | 名称 | 公式URL | 確認レベル |", "|---|---|---|---|---|"]
    for k in CATS:
        for e in by[k]:
            lines.append(
                f"| {esc(e.get('id',''))} | {k} | {esc(e.get('name',''))} | {esc(e.get('official_url',''))} | "
                f"{VERIFY.get(e.get('verification'), esc(e.get('verification','')))} |"
            )
    lines.append("")

    for k, title in CATS.items():
        lines += [f"## {title}（{counts[k]}件）", ""]
        for e in by[k]:
            lines += [f"### {esc(e.get('id',''))} {e.get('name','')}", ""]
            lines.append(f"- **公式URL**: {e.get('official_url','')}")
            for key, label in FIELDS:
                lines.append(f"- **{label}**: {e.get(key,'')}")
            refs = e.get("reference_links") or []
            if refs:
                lines.append("- **参考資料**: " + " / ".join(refs))
            lines.append(
                f"- **確認レベル**: {VERIFY.get(e.get('verification'), e.get('verification',''))}"
                f" — {e.get('verification_note','')}"
            )
            lines.append("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT} with {len(entries)} entries; counts={counts}; verification={vcount}; bad={bad}")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
