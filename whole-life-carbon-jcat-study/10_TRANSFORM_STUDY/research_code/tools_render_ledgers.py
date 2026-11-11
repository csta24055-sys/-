"""Render the survey ledger (01_PRIOR_RESEARCH) and the unit records (02_EQUATION_GROUPS) from JSON.

Reads only the JSON written by the survey / classification agents; computes nothing.
Run from research_code:  python3 -B tools_render_ledgers.py
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
NEW = os.path.normpath(os.path.join(HERE, ".."))
SCRATCH = re.compile(r"/tmp/claude-0/[^\s\"'）)]*")
QS = [("q1_meaning", "1 何を意味する理論・方程式か"), ("q2_why_developed", "2 なぜ開発され、何を解決するか"),
      ("q3_where_used", "3 どの分野でどう使われているか"), ("q4_equations_conditions", "4 主要方程式・数学的原理・成立条件"),
      ("q5_cost_reduction_and_error", "5 計算削減の仕組みと誤差の原因"), ("q6_application_to_building_lca", "6 建築 LCA のどの計算にどう適用できるか"),
      ("q7_unification_by_reformulation", "7 方程式の再構成で共通変換へ統合できるか"), ("q8_further_reduction", "8 成立条件や変換の工夫でさらに種類数を減らせるか")]


def clean(s):
    return SCRATCH.sub("（調査担当の作業用フォルダ。保存していない）", str(s)) if s is not None else ""


def cell(s):
    return clean(s).replace("|", "\\|").replace("\n", "<br>")


def kind_counts(e):
    c = {"文献で実証済み": 0, "文献の記載（未読・要旨のみ）": 0, "独自仮説": 0}
    for cl in e.get("claims", []):
        for k in c:
            if cl.get("kind", "").startswith(k[:5]):
                c[k] += 1
    return c


def render_survey(name, fname, title):
    j = json.load(open(os.path.join(NEW, "01_PRIOR_RESEARCH", "ledger", name + ".json"), encoding="utf-8"))
    o = ["# 調査台帳 %s：%s" % (name, title), "",
         "先行研究・数学的変換の調査台帳の一部。調査担当（実行担当とは別の AI 作業担当）が Web の検索と文献の閲覧で作った JSON（`ledger/%s.json`）を、欄ごとにそのまま載せる。" % name,
         "",
         "- **建築 LCA への適用についての記述は、文献がそのとおりのことをしている場合を除き、調査担当の独自仮説である。** 各項目の「主張の区別」で、文献で実証済み／文献の記載（未読・要旨のみ）／独自仮説 を分けている。",
         "- 出典は、調査担当がこの調査の中で見つけたものだけを載せている。どこまで読んだか（本文／要旨のみ／検索結果の記載のみ）を出典ごとに記した。実行担当は出典を読み直していない。",
         "- 対象の計算は独立概念モデル（架空データ）である。型の記号 F01〜F11 は [../00_POLICY/EQUATION_BRIEF.md](../00_POLICY/EQUATION_BRIEF.md) による。",
         ""]
    if j.get("notation"):
        o += ["## 記号", "", clean(j["notation"]) if isinstance(j["notation"], str) else "\n".join("- %s：%s" % (k, clean(v)) for k, v in j["notation"].items()), ""]
    if j.get("evidence_note"):
        o += ["## 根拠についての注記（調査担当）", "", clean(j["evidence_note"]), ""]
    o += ["## 項目の一覧", "", "| 項目 | 理論・変換 | 関連度 | 扱う型 | 出典の数 |", "|---|---|---|---|---|"]
    for e in j["entries"]:
        o.append("| [%s](#%s) | %s | %s | %s | %d |" % (e["id"], e["id"].lower(), cell(e["name_ja"]), cell(e.get("relevance", "")),
                                                     "、".join(e.get("forms_addressed", [])), len(e.get("sources", []))))
    o.append("")
    for e in j["entries"]:
        o += ['<a id="%s"></a>' % e["id"].lower(), "", "## %s　%s" % (e["id"], e["name_ja"]), "",
              "- 英語名：%s　／　族：%s" % (clean(e.get("name_en", "")), clean(e.get("family", ""))),
              "- 関連度：%s（%s）" % (clean(e.get("relevance", "")), clean(e.get("relevance_reason", ""))),
              "- 扱う型：%s　／　厳密か近似か：%s" % ("、".join(e.get("forms_addressed", [])), clean(e.get("exact_or_approximate", ""))), ""]
        for key, label in QS:
            o += ["### %s" % label, "", clean(e.get(key, "（記載なし）")), ""]
        o += ["### 限界", "", clean(e.get("limits", "（記載なし）")), "", "### 主張の区別", ""]
        for cl in e.get("claims", []):
            o.append("- 【%s】%s（出典：%s）" % (clean(cl.get("kind", "")), clean(cl.get("claim", "")), "、".join(cl.get("source_ids", [])) or "なし"))
        o += ["", "### 実験の案", ""]
        for x in e.get("proposed_experiments", []):
            o.append("- %s" % clean(x))
        o += ["", "### 出典", "", "| 記号 | 出典 | 種類 | どこまで読んだか | 所在 |", "|---|---|---|---|---|"]
        for s in e.get("sources", []):
            loc = s.get("url") or s.get("doi") or ""
            o.append("| %s | %s | %s | %s | %s |" % (cell(s.get("id", "")), cell(s.get("citation", "")), cell(s.get("type", "")),
                                                    cell(s.get("read_depth", "")) + ("　" + cell(s["read_note"]) if s.get("read_note") else ""), cell(loc)))
        o.append("")
    o += ["## 統合の仮説（調査担当の提案。すべて独自仮説）", ""]
    for h in j.get("unification_hypotheses", []):
        o += ["### %s" % h["id"], "", "- 主張：%s" % clean(h.get("statement", "")), "- 構成：%s" % clean(h.get("construction", "")),
              "- 条件：%s" % clean(h.get("conditions", "")), "- 反証になるもの：%s" % clean(h.get("what_would_falsify", "")),
              "- 見込まれる誤差の原因：%s" % clean(h.get("expected_error_sources", "")), ""]
    o += ["## LCA・建築 LCA での先行例（調査担当が見つけたもの）", ""]
    for x in j.get("prior_art_in_lca", []):
        o.append("- %s（出典：%s）" % (clean(x.get("what", "")), "、".join(x.get("source_ids", [])) or "なし"))
    o += ["", "## 調べられなかったこと", ""]
    for x in j.get("not_covered", []):
        o.append("- %s" % clean(x))
    if j.get("scratch_checks"):
        o += ["", "## 調査担当による走り書きの数値確認", "",
              "調査担当が自分で書いた小さな計算で確かめた結果である。基準計算とは照合していない（水準は仮説のまま）。スクリプトは保存していない。", "",
              "```json", clean(json.dumps(j["scratch_checks"].get("results", j["scratch_checks"]), ensure_ascii=False, indent=1))[:6000], "```"]
    open(os.path.join(NEW, "01_PRIOR_RESEARCH", fname), "w", encoding="utf-8").write("\n".join(o) + "\n")
    return j


def render_units(name, fname, title):
    j = json.load(open(os.path.join(NEW, "02_EQUATION_GROUPS", "ledger", name + ".json"), encoding="utf-8"))
    o = ["# 評価単位の構造の記録 %s：%s" % (name, title), "",
         "分類担当（実行担当とは別の AI 作業担当）が、基準計算のコードと台帳の定義文を読んで作った記録（`ledger/%s.json`）を、欄ごとにそのまま載せる。" % name,
         "旧研究の統合モデルと旧研究の族の分類は読ませていない（ルート B の、既存成果に拘束されない分類）。",
         "式と閉じた形は分類担当の読み取りと手計算によるもので、数値では確かめていない（水準は仮説）。対象は独立概念モデル（架空データ）である。", "",
         "## 単位の一覧", "", "| 単位 | 名称 | 段階 | 時間の構造 | T への依存 |", "|---|---|---|---|---|"]
    for u in j["units"]:
        o.append("| [%s](#%s) | %s | %s | %s | %s |" % (u["id"], u["id"].lower(), cell(u.get("name", "")), cell(u.get("stage", "")),
                                                     cell(u.get("time_structure", ""))[:120], cell(u.get("T_dependence", ""))[:120]))
    o += ["", "## 数学的な構造による群（分類担当の提案）", ""]
    for g in j["groups"]:
        o += ["### %s" % g["group"], "", "- 定義：%s" % clean(g.get("definition", "")), "- 属する単位：%s" % "、".join(g.get("members", [])),
              "- 理由：%s" % clean(g.get("why", "")), "- 境界にある単位：%s" % ("；".join(clean(x) for x in g.get("borderline", [])) or "なし"),
              "- 候補になる変換："]
        o += ["  - %s" % clean(x) for x in g.get("candidate_transformations", [])]
        o.append("")
    o += ["## 統合にかかわる横断の観察", ""] + ["- %s" % clean(x) for x in j.get("cross_cutting", [])]
    o += ["", "## 定義文とコードの違い", ""] + ["- %s" % clean(x) for x in j.get("text_vs_code", [])]
    o += ["", "## 単位ごとの記録", ""]
    for u in j["units"]:
        o += ['<a id="%s"></a>' % u["id"].lower(), "", "### %s　%s（%s）" % (u["id"], clean(u.get("name", "")), clean(u.get("stage", ""))), "",
              "- 式：%s" % clean(u.get("formula", "")),
              "- 宣言された依存：%s　／　実際に読む結果：%s" % ("、".join(u.get("depends_on", [])) or "なし", "、".join(u.get("reads_results_of", [])) or "なし"),
              "- 宣言に無い読み取り：%s　／　宣言したが読まない：%s" % ("、".join(u.get("undeclared_reads", [])) or "なし", "、".join(u.get("declared_not_read", [])) or "なし"),
              "- 入力：%s" % "、".join(u.get("inputs", [])), "- 添字の集合：%s" % "、".join(u.get("index_sets", [])),
              "- 出力：%s" % "、".join("%s（%s）" % (x.get("key"), x.get("kind")) for x in u.get("outputs", [])),
              "- 演算：%s" % "、".join(u.get("operations", [])),
              "- 線形性：線形＝%s　／　非線形＝%s" % ("、".join(u.get("linearity", {}).get("linear_in", [])) or "なし", "、".join(u.get("linearity", {}).get("nonlinear_in", [])) or "なし"),
              "- 時間の構造：%s" % clean(u.get("time_structure", "")), "- T への依存：%s" % clean(u.get("T_dependence", "")),
              "- 周期性：%s" % clean(u.get("periodicity", "")), "- 条件分岐：%s" % ("；".join(clean(x) for x in u.get("conditionals", [])) or "なし"),
              "- 除外と件数：%s" % clean(u.get("validity_and_counts", "")), "- 仕事の増え方：%s" % clean(u.get("size_scaling", "")),
              "- 注記：%s" % clean(u.get("notes", "")), ""]
    o += ["## 扱えなかったこと", ""] + ["- %s" % clean(x) for x in j.get("not_covered", [])]
    open(os.path.join(NEW, "02_EQUATION_GROUPS", fname), "w", encoding="utf-8").write("\n".join(o) + "\n")
    return j


if __name__ == "__main__":
    s1 = render_survey("S1", "S1_time_axis_transforms.md", "時間軸の積分変換と離散変換")
    s3 = render_survey("S3", "S3_linear_systems_reduction.md", "線形系・モデル縮約・行列関数")
    e = render_units("E1b", "E1b_use_stage_units.md", "使用段階（B1〜B7）の 22 単位")
    rows = []
    for name, j in (("S1", s1), ("S3", s3)):
        for x in j["entries"]:
            c = kind_counts(x)
            rows.append("| %s | %s | %s | %s | %d | %d／%d／%d |" % (x["id"], cell(x["name_ja"]), cell(x.get("relevance", "")),
                        "、".join(x.get("forms_addressed", [])), len(x.get("sources", [])), c["文献で実証済み"], c["文献の記載（未読・要旨のみ）"], c["独自仮説"]))
    open(os.path.join(HERE, "_entries_table.tmp"), "w", encoding="utf-8").write("\n".join(rows) + "\n")
    hy = []
    for name, j in (("S1", s1), ("S3", s3)):
        for h in j.get("unification_hypotheses", []):
            hy.append("| %s | %s |" % (h["id"], cell(h.get("statement", ""))))
    open(os.path.join(HERE, "_hypotheses_table.tmp"), "w", encoding="utf-8").write("\n".join(hy) + "\n")
    print(len(s1["entries"]), len(s3["entries"]), len(e["units"]), len(rows), len(hy))
