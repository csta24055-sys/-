"""knowledge/literature.json と docs/文献レビュー.md を生成する。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from literature_notes import NOTES  # noqa: E402

raw = json.loads((ROOT / "knowledge" / "literature_raw.json").read_text(encoding="utf-8"))
items = []
for k, n in NOTES.items():
    r = raw[k]
    level = "要旨確認" if r.get("abstract") and n["key"] else "書誌のみ"
    items.append({"doi": r["doi"], "title": r["title"], "authors": r["authors"], "year": r["year"], "venue": r["venue"],
                  "level": level, "topic": n["topic"], "stance": n["stance"], "related": n["lab"], "key": n["key"], "comparison": n["comp"],
                  "url": f"https://doi.org/{r['doi']}"})
items.sort(key=lambda x: (x["topic"], -(x["year"] or 0)))
(ROOT / "knowledge" / "literature.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
L = ["# 国内外文献レビュー（研究室の結論との比較）", "", "> `scripts/literature_notes.py` と `knowledge/literature_raw.json`（Crossref・OpenAlex から取得）から自動生成。",
     "> 確認水準: **要旨確認**＝要旨を取得して読んだ文献、**書誌のみ**＝DOI・題名・誌名だけを確認した文献（内容の数値は主張しない）。全文を精読した文献はまだない。", "",
     f"収録 {len(items)} 件（要旨確認 {sum(i['level']=='要旨確認' for i in items)} 件・書誌のみ {sum(i['level']=='書誌のみ' for i in items)} 件）。立場: 支持／反証・制約／方法／文脈。", "",
     "## 検索方法", "", "- Crossref の書誌検索（英語・日本語のキーワード）と DOI 照会、OpenAlex の要旨（2026-11-03 実施）。J-STAGE・CiNii の全文検索は未実施で、日本語文献の網羅性は低い。",
     "- 日本語の検索（『全館空調 住宅 粉塵 濃度』『住宅 PM2.5 室内外濃度比 実測』等）では該当する学術論文が Crossref 上でほとんど見つからなかった。これは『国内で研究されていない』ことの証拠にはならない（検索範囲の制約）。", "",
     "## 主要な比較（研究室の結論への影響）", ""]
for i in items:
    if i["level"] == "要旨確認":
        L += [f"### {i['title']}（{i['year']}）", f"- {', '.join(i['authors'][:3])}{' ほか' if len(i['authors'])>3 else ''}. *{i['venue']}*. DOI: [{i['doi']}]({i['url']})（{i['level']}, {i['topic']}, {i['stance']}）",
              f"- 要旨の要点【確認事実】: {i['key']}", f"- 研究室との比較【分析】: {i['comparison']}（関連: {', '.join(i['related'])}）", ""]
L += ["## 書誌のみ確認した文献", "", "| 年 | 題名 | 誌名 | DOI | 関連 |", "|---|---|---|---|---|"]
for i in items:
    if i["level"] == "書誌のみ":
        L.append(f"| {i['year']} | {i['title']} | {i['venue']} | [{i['doi']}]({i['url']}) | {i['comparison']} |")
L += ["", "## 研究室の研究の位置づけ【分析】", "",
      "1. **既知のこと**: 住宅の室内粒子は外気侵入・室内発生・ろ過・沈着・換気の収支で決まり（Nazaroff 2004）、侵入係数は住宅の気密性と強く関係する（Stephens & Siegel 2012）。in-duct の電気式エアクリーナは試験住宅で高い除去率を示す（MacIntosh et al. 2008）。高効率フィルタは圧力損失で CADR を下げ得る（2020, Indoor Air）。",
      "2. **研究室の独自性の候補**: 床吹出型全館空調（空調室に EP を置く循環型）を、実験住宅・実住宅・西日本の複数地域で継続測定し、EP 稼働・停止の比較と年間予測まで行った点。ただし文献検索が限定的なため『新規』とは断定しない。",
      "3. **反証・制約となる知見**: (a) 研究室の EP の実効除去率は文献の in-duct EAC より1桁小さい → 循環風量・気積を揃えた比較が必要。(b) 『C値とI/O無相関』は狭い範囲・少数住宅による可能性。(c) 外気の粒径分布で k は変わる（年間予測の前提）。(d) EP のオゾン等の副生成物を研究室は測っていない。(e) 低価格センサーは高湿度で過大表示し得る。",
      "4. **次年度への示唆**: T-02（湿度を含むセンサー校正）、T-03（季節別 k）、T-01/T-04（EP の CADR と電力・副生成物）を優先する根拠になる。"]
(ROOT / "docs" / "文献レビュー.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print(len(items), "items")
