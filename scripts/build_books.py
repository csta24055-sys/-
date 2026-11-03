"""2027年度向け2冊（Markdown）を knowledge.json・RESEARCH_COMPLETENESS.json・report/09・books_text.py から生成し、
pandoc で .docx、pandoc→HTML→Chromium で .pdf を作る。出力: deliverables/

使い方: .venv/bin/python scripts/build_books.py [--no-convert]
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import books_text as T  # noqa: E402

K = json.loads((ROOT / "knowledge" / "knowledge.json").read_text(encoding="utf-8"))
C = json.loads((ROOT / "RESEARCH_COMPLETENESS.json").read_text(encoding="utf-8"))
OUT = ROOT / "deliverables"
OUT.mkdir(exist_ok=True)
F = {f["id"]: f for f in K["findings"]}
S = {s["id"]: s for s in K["sources"]}
TODAY = date.today().isoformat()
W = {"importance": 0.35, "novelty": 0.2, "feasibility": 0.25, "fit": 0.2}


def total(t):
    return round(sum(t["scores"][k] * w for k, w in W.items()), 2)


def frontmatter(title, subtitle):
    return f"""---
title: "{title}"
subtitle: "{subtitle}"
date: "{TODAY}"
lang: ja
---
"""


def fcite(fid):
    f = F.get(fid)
    return f"**{fid}**【{f['class']}】{f['text']}" if f else fid


def dossier_by_year():
    """report/09 の年度別整理を年度見出しで分割"""
    txt = (ROOT / "report" / "09_年度別研究の整理.md").read_text(encoding="utf-8")
    parts = re.split(r"\n## ", txt)
    out = {}
    for p in parts[1:]:
        m = re.match(r"(\d{4})年度", p)
        if m:
            out.setdefault(int(m.group(1)), []).append("### " + p.strip())
    return out


def book1():
    L = [frontmatter("2027年度 井口研究室 空気環境・電気集塵研究 総合研究継承資料", "過去研究（2013〜2026年度）の再検証と研究の始め方"), T.BOOK1_INTRO]
    # 第1章 研究史
    hist = (ROOT / "report" / "01_研究史.md").read_text(encoding="utf-8")
    hist = re.sub(r"^# .*\n", "", hist).replace("\n## ", "\n### ")
    L += ["# 第1章 研究室の研究史と研究テーマの変遷", "", hist, ""]
    syn = (ROOT / "report" / "12_統合分析.md").read_text(encoding="utf-8")
    syn = re.sub(r"^# .*\n", "", syn).replace("\n## ", "\n#### 問")
    L += ["### 1.6 研究全体の統合分析（系統図と12の問い）", "", syn, ""]
    # 第2章 理論
    L += ["# 第2章 空気環境・粒子・電気集塵の基礎理論", T.THEORY, ""]
    # モデル一覧
    L += ["## 2.7 本アプリに実装したモデルと適用範囲", "", "| モデル | 式 | 根拠 | 適用範囲 |", "|---|---|---|---|"]
    for m in K["models"]:
        L.append(f"| {m['name']} | {m['equation']} | {m['basis']} | {m['validity']} |")
    # 第3章 測定
    L += ["", "# 第3章 測定機器と測定方法", T.MEASURE, ""]
    # 第4章 研究単位ごと
    dos = dossier_by_year()
    L += ["# 第4章 過去の各研究の詳細と再検証", "", "各研究について、年度別の整理（目的・条件・測定・式・結果・結論・限界）と、本プロジェクトの検証状況（13項目）を示す。検証状況の『済』は証拠のある実施、『一部』は一部のみ、『不能』は資料が取得できず実施できないことを表す。", ""]
    for u in C["units"]:
        L += [f"## 4.{C['units'].index(u)+1} {u['year']}年度 {u['title']}（{u['id']}）", ""]
        if u["year"] in dos and not u["id"].startswith(("R-2013", "R-2015", "R-JOINT")):
            for blk in dos.pop(u["year"]):
                L += [blk.replace("### ", "#### ", 1), ""]
        L += [f"**検証の分類**: {u['cls']}（完成度 {u['score']}）", "", "| " + " | ".join(C["items"]) + " |", "|" + "---|" * len(C["items"]),
              "| " + " | ".join(u["items"][k] for k in C["items"]) + " |", "", "**主な検証結果**", ""]
        L += [f"- {fcite(fid)}" for fid in u["evidence"]] + ["", f"**未確認事項・制約**: {u['notes']}", ""]
    # 第5章 誤り
    L += ["# 第5章 過去研究の再検証で分かった注意点（よくある誤り）", T.MISTAKES, ""]
    # 第6章 文献
    lit = (ROOT / "docs" / "文献レビュー.md").read_text(encoding="utf-8")
    lit = re.sub(r"^# .*\n", "", lit).replace("\n## ", "\n## 6. ").replace("\n### ", "\n#### ")
    L += ["# 第6章 国内外の先行研究との比較", lit, ""]
    # 第7章 未解決問題
    L += ["# 第7章 研究室の未解決問題", "", "| ID | 優先 | 問題 | 状態 |", "|---|---|---|---|"]
    L += [f"| {q['id']} | {q['priority']} | {q['text']} | {q['status']} |" for q in K["questions"]]
    L += ["", "## 7.1 競合仮説", ""]
    for h in K["hypotheses"]:
        L += [f"### {h['id']} {h['title']}（{h['status']}）", "", "| 競合仮説 | 内容 | 判別方法 |", "|---|---|---|"]
        L += [f"| {c['label']} | {c['text']} | {c['test']} |" for c in h["competing"]] + [""]
    # 第8章 データの所在
    L += ["# 第8章 研究データの所在とアクセス手順", "",
          "- 研究室資料は Box（読み取りで利用）。資料IDと Box のファイルID・フォルダは付録Bと SOURCES.md に記載し、アプリ『資料ライブラリ』から Box のリンクを開ける。",
          "- 原データ（Excel/CSV）と個人情報を含む資料は公開リポジトリに置かない。解析時は `private_data/`（Git 管理外）に置き、再計算スクリプトは集計値だけを `knowledge/*.json` に出力する。",
          "- 大容量ファイル（10 MB 超）や画像PDFの取得方法と失敗例は `docs/資料取得の技術的検討.md`。今後の測定データは月ごとの CSV（UTF-8）で保存すること。",
          "- 再計算スクリプト: `scripts/raw_2024.py`（2024年度8住宅）、`scripts/events_2024.py`（上昇イベント）、`scripts/raw_2025.py`（2025年度）、`scripts/annual_2024.py`（年間予測）、`scripts/validate_multizone.py`（2020年度）、`verification/Y2022_simulation/verify_2022_sim.py`（2022年度）。",
          "", "## 8.1 資料の調査状態（集計）", ""]
    from collections import Counter
    cnt = Counter(s["status"] for s in K["sources"])
    L += ["| 状態 | 件数 |", "|---|---|"] + [f"| {k} | {v} |" for k, v in cnt.most_common()] + [""]
    # 第9章 学習順序
    L += ["# 第9章 初学者のための学習順序", "", T.LEARNING, ""]
    # 付録
    L += ["# 付録A 用語集", "", "| 用語 | 説明 |", "|---|---|"] + [f"| {a} | {b} |" for a, b in T.GLOSSARY] + [""]
    L += ["# 付録B 資料一覧（研究室資料）", "", "| ID | 年度 | 資料 | 状態 |", "|---|---|---|---|"]
    L += [f"| {s['id']} | {s.get('fiscal_year') or '—'} | {s['title']} | {s['status']} |" for s in K["sources"]] + [""]
    L += ["# 付録C 参考文献（国内外）", ""]
    for i, l in enumerate(sorted(K["literature"], key=lambda x: (x["authors"][0] if x["authors"] else "", x["year"] or 0)), 1):
        au = ", ".join(l["authors"][:3]) + (" et al." if len(l["authors"]) > 3 else "")
        L.append(f"{i}. {au} ({l['year']}). {l['title']}. *{l['venue']}*. https://doi.org/{l['doi']}（{l['level']}）")
    L += ["", "# 付録D 索引（主要語と章）", "", "| 語 | 主な章 |", "|---|---|",
          "| I/O比 | 2.1, 3.3, 4（2024・2025）, 5 |", "| CADR | 2.1, 2.4, 6 |", "| 沈着係数β | 2.2, 4（2021・2023）, 5 |", "| 電気集塵機 | 2.3, 4（2018・2026）, 6 |",
          "| バイパス開口率 | 2.4, 4（2026） |", "| 多室モデル | 2.5, 4（2020・2022） |", "| センサー校正 | 3.2, 5 |", "| 時間刻み | 4（2022）, 5 |", "| 年間予測 | 4（2025）, 6 |"]
    return "\n".join(L) + "\n"


def book2():
    themes = sorted(K["themes"], key=total, reverse=True)
    L = [frontmatter("2027年度 井口研究室 研究方針・研究テーマ戦略提案書", "証拠に基づく研究テーマの比較と2027年4月〜2028年3月のロードマップ")]
    L += ["# 第1章 本提案書の位置づけ", "",
          "本提案書は、過去研究の再検証（第1冊）と国内外の文献比較から、2027年度の研究テーマを選ぶための判断材料をまとめたものである。テーマの評価は重要度・新規性・実行可能性・既存設備適合の4観点（1〜5点, 重み0.35・0.20・0.25・0.20）による【分析】で、重みはアプリ『研究計画』で変更して感度を確かめられる。**未確認の設備・予算・協力住宅を利用できるとは仮定していない**。前提が成り立たない場合の代替案を各テーマに示す。", ""]
    # 第2章 総合評価
    L += ["# 第2章 過去研究の総合評価", "", "| ID | 年度 | 研究 | 分類 | 完成度 |", "|---|---|---|---|---|"]
    L += [f"| {u['id']} | {u['year']} | {u['title']} | {u['cls']} | {u['score']} |" for u in C["units"]]
    L += ["", "## 2.1 十分な証拠で支持される結論", "",
          "- 空調室（循環経路）の EP を稼働させると住宅全体の濃度が下がる: 2024年度住宅GのEP停止で約10倍（F-V-10）、2025年度住宅AのEP稼働でI/O 0.27（F-V-01）。",
          "- 粗大粒子（30–45 μm）は発生室でほぼ沈着し、5–10 μm は EP で3〜5割捕集される（2022年度, 全20シートで検証, F-SIM-13）。",
          "- 全館空調・EP付き住宅では室内の上昇イベントが少ない（F-V-17）。",
          "- センサーとKC-52の換算の傾きは2年で一致（F-V-07/09）。",
          "", "## 2.2 再検証が必要な結論", "",
          "- 2025年度の条件①回帰係数0.14（住宅Dのデータ未検証, F-V-06, Q-12）と、住宅間で約2倍異なる k の代表性（F-V-05, F-V-11）。",
          "- 2026年度の最適バイパス開口率（750 m³/h 超の外挿に依存, F-2026-03）。",
          "- 『全館空調は浮遊時間が短い』（イベント全体の統計では支持が弱い, F-V-18）。",
          "- 『C値とI/O比に相関なし』（3住宅・狭い範囲, F-LIT-02）。",
          "- 年間予測（k一定・室内発生なし, F-2025-21, F-LIT 文献 Riley et al. 2002）。", ""]
    # 第3章 文献動向
    L += ["# 第3章 国内外の研究動向", ""]
    lit = (ROOT / "docs" / "文献レビュー.md").read_text(encoding="utf-8")
    m = re.search(r"## 研究室の研究の位置づけ【分析】\n\n(.*)", lit, re.S)
    L += [m.group(1) if m else "", "", "詳細は第1冊 第6章と docs/文献レビュー.md を参照。", ""]
    # 第4章 未解決問題
    L += ["# 第4章 未解決問題", "", "| ID | 優先 | 問題 | 状態 |", "|---|---|---|---|"]
    L += [f"| {q['id']} | {q['priority']} | {q['text']} | {q['status']} |" for q in K["questions"] if q["status"] not in ("解決",)] + [""]
    # 第5章 強み制約
    L += ["# 第5章 研究室の強みと制約", T.BOOK2_STRENGTHS, ""]
    # 第6章 テーマ比較
    L += ["# 第6章 研究テーマ候補の比較", "", "| 順位 | ID | テーマ | 重要 | 新規 | 実行 | 適合 | 総合 | 期間[月] | 失敗リスク |", "|---|---|---|---|---|---|---|---|---|---|"]
    for i, t in enumerate(themes, 1):
        e = t.get("evaluation", {})
        mo = "〜".join(str(x) for x in sorted(set(e.get("months", []))))
        L.append(f"| {i} | {t['id']} | {t['name']} | {t['scores']['importance']} | {t['scores']['novelty']} | {t['scores']['feasibility']} | {t['scores']['fit']} | {total(t)} | {mo} | {e.get('failure_risk','')} |")
    L += ["", "## 6.1 各テーマの評価の詳細", ""]
    for t in themes:
        e = t.get("evaluation", {})
        L += [f"### {t['id']} {t['name']}", "", f"- **なぜ今か**: {t['why_now']}", f"- **既知**: {t['known']}", f"- **未解決**: {t['unsolved']}",
              f"- **実現可能性**: {e.get('feasibility','')}", f"- **新規性**: {e.get('novelty','')}", f"- **必要設備**: {e.get('equipment','')}（詳細: {t['equipment']}）",
              f"- **失敗時の代替**: {e.get('failure_mode','')}", f"- **根拠**: {e.get('evidence','')}", ""]
    # 第7章 上位3テーマ
    L += ["# 第7章 最有力テーマ・次点テーマと上位3テーマの実験計画", "",
          f"総合点の上位は {themes[0]['id']}（{total(themes[0])}）、{themes[1]['id']}（{total(themes[1])}）、{themes[2]['id']}（{total(themes[2])}）である。差は小さく、重みを変えると順位が入れ替わり得る（アプリで確認できる）。**最有力**は {themes[0]['id']}、**次点**は {themes[1]['id']} とする。{themes[2]['id']} は他の2テーマの品質基盤であり、並行して最初の1か月で行うことを推奨する【分析】。", ""]
    for t in themes[:3]:
        L += [f"## {t['id']} {t['name']}", "", f"**研究背景**: {t['why_now']}", "", f"**研究目的**: {t['unsolved']}を明らかにする。", "",
              f"**検証する仮説**: {', '.join(t['hypotheses']) or '—'}（第1冊 7.1 の競合仮説を参照）", "",
              f"**必要設備**: {t['equipment']}", "", f"**測定項目・条件**: {t['measurements']}", "", f"**手順**: {t['procedure']}", "",
              f"**解析方法**: {t['analysis']}", "", f"**必要なデータ**: {t['data_needed']}", "", f"**想定される結果の分岐**: {t['branches']}", "",
              f"**難易度・期間・費用**: {t['difficulty']}／{t['duration_cost']}", "", f"**意義**: {t['significance']}", "", f"**リスクと代替**: {t['risks']}", "",
              f"**研究が成立する条件**: 必要設備が確認できること（第10章）。{t.get('evaluation',{}).get('failure_mode','')}", ""]
    # 第8章 ロードマップ
    t1, t2, t3 = themes[0]["id"], themes[1]["id"], themes[2]["id"]
    L += ["# 第8章 2027年4月〜2028年3月の研究ロードマップ", "",
          "| 月 | 全員 | " + f"{t1} | {t2} | {t3} |", "|---|---|---|---|---|",
          f"| 4月 | 第1冊 第1〜3章、アプリ学習モード 1〜6 | 文献・装置の確認 | 文献・測定住宅の確認 | センサー全台の並置（24 h）・湿度計の準備 |",
          f"| 5月 | 過去データの再現演習（2024・2025年度） | 予備試験（EP OFF の健全性確認） | 春季の測定（3〜5月の後半） | 湿度ステップ・発生源別試験 |",
          f"| 6月 | テーマ確定・計画書（アプリで作成） | 本試験 100〜750 m³/h | 同上・解析 | 補正式の作成 |",
          f"| 7〜8月 | 中間発表準備 | 750 m³/h 超の試験（装置が可能な場合） | 夏季の測定 | 現地測定前後の再並置 |",
          f"| 9月 | 中間発表 | 抵抗則の判定・バイパスモデル再計算 | 夏季の解析 | 補正前後の I/O・k 再計算 |",
          f"| 10〜11月 | 追加測定 | 電極洗浄前後の比較 | 秋季の測定（2025年度と比較） | — |",
          f"| 12〜1月 | 解析・執筆 | 統合（T-04 への接続） | 季節別 k と年間予測の更新 | — |",
          f"| 2〜3月 | 卒論提出・発表・データ引継ぎ（CSV と再計算スクリプトを Box へ） | | | |", ""]
    # 第9章 成立可能性
    L += ["# 第9章 卒業研究としての成立可能性", "",
          f"- {t1}: 既存装置で実施でき、結果がどちらに出ても（二乗則か累乗則か）2026年度の結論の検証として成立する。750 m³/h 超が出せない場合も、風速相似の試験に切り替えれば成立する。",
          f"- {t2}: 測定期間が季節に依存するため、春の測定を逃すと1年で完結しない。モデルハウスが使えない場合は既存の2024・2025年度データの季節差解析に縮小する。",
          f"- {t3}: 既存機器で1か月で完了し、単独では卒論として小さいため、{t1} または {t2} と組み合わせる。", ""]
    # 第10章 変更条件・教員確認
    L += ["# 第10章 研究テーマを変更すべき条件", "",
          "- 実験住宅・モデルハウスが4月中に確保できない → T-03 を既存データ解析へ縮小し、T-01・T-02 を主とする。",
          "- 単体試験装置が使えない → T-01 を中止し、T-06（多室モデル、既存データで実施可）へ変更する。",
          "- オゾン計が使える → EP の副生成物（F-LIT-04）を T-01 に追加する価値が高い。",
          "- 2025年度住宅Dの CSV が得られた → 条件①の再計算（Q-12）を最初の課題に加える。", "",
          "# 第11章 教員への確認事項", "", "| ID | 確認事項 |", "|---|---|"] + [f"| {a} | {b} |" for a, b in T.TEACHER_QUESTIONS] + [""]
    L += ["# 付録 評価方法", "", "総合点 = 重要度×0.35 ＋ 新規性×0.20 ＋ 実行可能性×0.25 ＋ 既存設備適合×0.20（各1〜5点）。点数は本プロジェクトの判断【分析】であり、2026-11-03 時点の資料と検証結果に基づく。スコアの変更履歴は docs/研究テーマ候補一覧.md にある。"]
    return "\n".join(L) + "\n"


CSS = """
body{font-family:'WenQuanYi Zen Hei','Noto Sans CJK JP',sans-serif;font-size:10.5pt;line-height:1.65;color:#111;max-width:none;margin:0}
h1{font-size:17pt;border-bottom:2px solid #0f5b5c;padding-bottom:4px;margin-top:28px;page-break-before:always}
h1.title{page-break-before:avoid;border:none;font-size:22pt;margin-top:120px}
h2{font-size:13.5pt;color:#0f5b5c;margin-top:20px}h3{font-size:11.5pt}h4{font-size:10.5pt}
table{border-collapse:collapse;width:100%;font-size:8.6pt;margin:8px 0;page-break-inside:auto}
th,td{border:1px solid #999;padding:3px 5px;vertical-align:top}th{background:#e8f0f0}
code{font-size:9pt}nav#TOC{page-break-after:always}nav#TOC ul{list-style:none;padding-left:14px}
p.subtitle{font-size:13pt;color:#333}p.date{color:#555}
img{max-width:100%;height:auto}figure{margin:8px 0}figcaption{font-size:9pt;color:#444;text-align:center}
"""


def convert(md_path: Path):
    stem = md_path.with_suffix("")
    subprocess.run(["pandoc", str(md_path), "-o", str(stem) + ".docx", "--resource-path", str(md_path.parent), "--toc", "--toc-depth=2"], check=True)
    css = OUT / "book.css"
    css.write_text(CSS, encoding="utf-8")
    html = str(stem) + ".html"
    subprocess.run(["pandoc", str(md_path), "-s", "-o", html, "--toc", "--toc-depth=2", "--mathml", "-c", "book.css", "--metadata", "title-prefix="], check=True)
    js = f"""
const {{ chromium }} = require('playwright');
(async () => {{
  const b = await chromium.launch(); const p = await b.newPage();
  await p.goto('file://{html}'); await p.waitForTimeout(500);
  await p.pdf({{ path: '{stem}.pdf', format: 'A4', margin: {{top:'18mm',bottom:'18mm',left:'16mm',right:'16mm'}}, displayHeaderFooter: true,
    headerTemplate: '<div></div>', footerTemplate: '<div style="font-size:8px;width:100%;text-align:center;color:#666"><span class=pageNumber></span> / <span class=totalPages></span></div>' }});
  await b.close();
}})();"""
    jsf = OUT / "_pdf.cjs"
    jsf.write_text(js, encoding="utf-8")
    npm_root = subprocess.check_output(["npm", "root", "-g"], text=True).strip()
    import os
    subprocess.run(["node", str(jsf)], check=True, env={**os.environ, "NODE_PATH": npm_root})
    jsf.unlink()
    Path(html).unlink()


def main():
    b1 = OUT / "2027_研究継承総合資料.md"
    b2 = OUT / "2027_研究方針・研究テーマ戦略提案書.md"
    b1.write_text(book1(), encoding="utf-8")
    b2.write_text(book2(), encoding="utf-8")
    print(b1, len(b1.read_text()), b2, len(b2.read_text()))
    if "--no-convert" not in sys.argv:
        for b in (b1, b2):
            convert(b)


if __name__ == "__main__":
    main()
