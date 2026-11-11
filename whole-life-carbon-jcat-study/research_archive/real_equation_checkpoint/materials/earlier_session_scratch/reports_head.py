#!/usr/bin/env python3
"""Generate the Markdown reports of chapter 09 from the JSON results.

Every number in the generated files is read from a JSON output of the study, so the
reports cannot drift from the data. Generated files carry a notice at the top.

Run:  cd research_code && python3 -m tools.build_reports
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

S = Path(__file__).resolve().parents[2]
NOTICE = "> このファイルは `research_code/tools/build_reports.py` が JSON の結果から自動生成したもの。数値を手で書き換えない。\n"
CAVEAT = ("> **読み方の注意**：検証はすべて乱数で作った架空データ上で行った。ここでの一致・誤差・速度は、独立に設計した基準計算に対するものであり、"
          "実建物での精度や、他のツールとの一致を示すものではない。\n")


def load(rel):
    return json.loads((S / rel).read_text(encoding="utf-8"))


def table(header, rows, align=None):
    align = align or ["---"] * len(header)
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(align) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def pct(x, digits=1, sign=False):
    if x is None:
        return "—"
    return f"{x * 100:+.{digits}f}％" if sign else f"{x * 100:.{digits}f}％"


def write(rel, text):
    (S / rel).write_text(text.rstrip() + "\n", encoding="utf-8")
    print("wrote", rel)


CLASS_JA = {
    "LINEAR_SUM_PRODUCT": "活動量×係数の総和", "WEIGHTED_AVERAGE": "加重和", "MATRIX_EXPANSION": "構成行列の展開",
    "TIME_SERIES_SUM": "年次の積算", "RECURRENCE": "年ごとの状態更新", "EVENT_SCHEDULE": "周期イベント",
    "COUNT_FLOOR": "回数の計数", "SUM_OF_STAGES": "段階の合計", "RATIO": "比・換算", "MAX_CLAMP": "打ち切り",
    "PREDICATE_GATE": "判定・検証", "MASS_BALANCE_CONSTRAINT": "収支の制約", "LOOKUP_JOIN": "検索結合",
    "UNDEFINED_MODEL": "モデル未定義",
}
STATUS_JA = {"COVERED_BY_EXISTING": "既存 53 式が対応（推定）", "COVERED_BY_ADDITIONAL": "追加単位が対応（推定）",
             "NOT_INSPECTED": "名称から対応を推定できない", "NON_CALCULATION": "計算なし（数式 0 件）"}
OUTCOME_JA = {"SUCCESS": "成功", "REJECTED": "不採用", "HOLD": "保留", "NOT_APPLICABLE": "候補なし"}
AGENTS = ("分類台帳の分析担当、評価軸 B の評価者、検査担当は、いずれも互いの出力を見ないように分けて動かした自動の AI エージェントであり、人ではない。"
          "「独立」は、相手の結論を見ずに作業したという意味である。")


def ledger_report():
    led = load("01_LEDGER/units.json")
    fam = load("01_LEDGER/sheet_families.json")
    cov = load("01_LEDGER/sheet_family_coverage.json")
    unl = load("01_LEDGER/unlinked_input_disposition.json")
    na = load("01_LEDGER/considered_not_adopted.json")["not_adopted"]
    units = led["units"]
    inputs_all = {i for u in units for i in u["inputs"]}
    inputs_new = {i for i in inputs_all if i.startswith("NEW:")}
    zero_covered = sum(1 for f in cov["families"] if f["status"].startswith("COVERED") and not f["formula_xml_nodes"])
    by_status = {}
    for f in cov["families"]:
        e = by_status.setdefault(f["status"], [0, 0])
        e[0] += 1
        e[1] += f["formula_xml_nodes"]
    total = fam["total_formula_nodes"]
    scope = fam["nodes_by_scope_suffix"]
    t = ["# 01 全計算式・式群の分類台帳（成果物 1）", "", NOTICE,
         "## 何を調べたか", "",
         f"- 評価単位は **{led['unit_count']} 件**：既存の概念式 {led['existing_unit_count']} 件と、追加で特定した計算構造 {led['additional_unit_count']} 件（`X-01`〜`X-17`）。",
         "- 追加単位は、シート名・数式ノード数、式に未接続の入力項目、既存資料の記述から読み取った**独立設計の案**で、原版の式の再現ではない。",
         "- 1 件ごとに、目的、入力、出力、数学的な構造、反復と分岐、計算量、依存関係、類似の単位、統合と近似の見込み、同一視してはならない境界・単位を記録した（[units.json](units.json)）。",
         "- 基準計算が実際に採用した定義は、各単位の `reference_semantics` に記載している（基準計算の関数の説明文と同一）。",
         f"- 単位が参照する入力項目は {len(inputs_all)} 種類：既存の入力仕様（124 項目）のうち {len(inputs_all) - len(inputs_new)}、本研究で仮に置いたもの（`NEW:`）{len(inputs_new)}。",
         f"- {AGENTS}", "",
         "## 調べていないもの（未調査の範囲）", "",
         f"- **原版ブックの数式本文は、全シート族について確認していない（数式ノードの 100％ が未調査）。** 本研究環境にも本リポジトリにも原版ファイルは存在しない。約 {total:,} の数式ノードを調査したものではない。",
         "- 下表の「対応」は**シート名だけからの推定**で、原版の式の内容が評価単位と同じであることを意味しない。「対応あり」の割合は、調査済みの割合ではない。",
         f"- 名称からは対応する計算構造を推定できなかったシート族が {by_status.get('NOT_INSPECTED', [0, 0])[0]} 件ある（数式ノードの {pct(by_status.get('NOT_INSPECTED', [0, 0])[1] / total, 2)}）。これらはどの評価単位にも対応させていない。",
         f"- 「対応（推定）」とした族のうち {zero_covered} 件は数式が 0 件で、表や一覧と推定されるものである。",
         "- 詳細算定ブックは外部の計算ツールとの連携が前提で、その内部は確認できない。", "",
         "## 198 シートの整理（メタデータのみ）", "",
         f"198 シートを、シート名の末尾（`_GHG`・`_CO2`）などを除いて **{fam['family_count']} のシート族**に整理した（うち数式を持つもの {fam['families_with_formulas']}）。", "",
         table(["シート名からの対応状況", "シート族", "数式ノード", "占有率"],
               [[STATUS_JA[k], v[0], f"{v[1]:,}", pct(v[1] / total, 2)] for k, v in sorted(by_status.items(), key=lambda kv: -kv[1][1])],
               ["---", "---:", "---:", "---:"]), "",
         "数式ノードの多いシート族（上位 12）：", "",
         table(["シート族", "数式ノード", "占有率", "関連すると推定した単位", "対応状況"],
               [[f["family"], f"{f['formula_xml_nodes']:,}", pct(f["share_of_all_nodes"], 2), "、".join(f["related_units"]) or "—", STATUS_JA[f["status"]]]
                for f in cov["families"][:12]], ["---", "---:", "---:", "---", "---"]), "",
         f"- 「資材構成」だけで全数式ノードの {pct(cov['families'][0]['share_of_all_nodes'])} を占める。名称からは複合品を構成資材へ展開する表と推定されるが、内容は未確認。",
         f"- 末尾が `_GHG` のシートの数式ノードは {scope['GHG']:,}、`_CO2` は {scope['CO2']:,} でほぼ同数。同じ構成の計算が 2 系統あることを示唆するが、式が同一かどうかは未確認（評価単位 X-05 として扱った）。",
         "- 数式ノード数は「同じ式が何回繰り返されているか」の代理指標で、実行時間でも式の種類数でもない。", "",
         "## 数学的な構造別の件数", "",
         table(["構造", "件数"], [[CLASS_JA[k], v] for k, v in led["structure_class_counts"].items()], ["---", "---:"]), "",
         "## 評価単位の一覧", "",
         table(["ID", "名称", "段階", "構造", "区分", "基準計算"],
               [[u["id"], u["name"], u["stage"], CLASS_JA[u["structure_class"]], "既存" if u["origin"] == "EXISTING_53" else "追加",
                 "あり" if u["computable_in_reference"] else "なし"] for u in units]), "",
         "## 式に未接続だった入力 53 項目の扱い", "",
         table(["扱い", "件数"], [[{"METADATA_ONLY": "記録用（計算に使わない）", "NEEDS_NEW_UNIT": "追加単位で接続", "IMPLICIT_IN_EXISTING": "既存式が暗黙に使用"}[k], v]
                              for k, v in unl["counts"].items()], ["---", "---:"]), "",
         "詳細は [unlinked_input_disposition.json](unlinked_input_disposition.json)。", "",
         "## 検討したが評価単位にしなかったもの", "",
         "\n".join(f"- **{x['name']}**：{x['reason']}" for x in na), "",
         "## ファイル", "",
         "- [units.json](units.json)：分類台帳本体",
         "- [sheet_families.json](sheet_families.json)：198 シート → 59 シート族（名称と数式ノード数のみ）",
         "- [sheet_family_coverage.json](sheet_family_coverage.json)：シート族と評価単位の対応（名称からの推定）。対応の唯一の出所で、`units.json` の `sheet_family_links` はここから機械的に作る",
         "- [unlinked_input_disposition.json](unlinked_input_disposition.json)、[considered_not_adopted.json](considered_not_adopted.json)"]
    write("01_LEDGER/README.md", "\n".join(t))


def ranking_report():
    a, b, p = load("02_RANKING/axis_a.json"), load("02_RANKING/axis_b.json"), load("02_RANKING/research_priority.json")
    m = load("02_RANKING/axis_a_measurements.json")
    names = {r["id"]: r["name"] for r in p["units"]}
    sizes = m["size_classes"]
    last = sizes[-1]
    ms = lambda v: "—" if v is None else f"{v / 1e6:.2f}"
    rows_a = []
    for r in a["ranking"]:
        ts = r["time_share"] or {}
        rows_a.append([r["rank"], r["id"], names[r["id"]], f"{r['a_score']:.3f}" if r["a_score"] is not None else "—",
                       pct(ts.get(last), 2) if r["measured"] else "測定不能", ms((r["time_ns"] or {}).get(last)) if r["measured"] else "—",
                       f"{(r['operations'] or {}).get(last, 0):,}" if r["measured"] else "—",
                       f"{(r['peak_memory_bytes'] or {}).get(last, 0) / 1024:,.0f}" if r["measured"] else "—",
                       r["static"]["a4"], r["static"]["a5"], r["static"]["a6"], pct(r["static"]["a7"], 2)])
    rows_b = []
    for r in b["ranking"]:
        med = r["median_by_criterion"]
        rows_b.append([r["rank"], r["id"], names[r["id"]], f"{r['b_score']:g}", f"{r['unification_subscore']:g}"]
                      + [f"{med[c]:g}" for c in ("b1", "b2", "b3", "b4", "b5", "b6", "b7", "b8")]
                      + ["/".join(str(v) for v in r["judge_totals"].values()), "あり" if r["disputed"] else ""])
    rows_p = [[r["order"], r["wave"], r["id"], r["name"], r["stage"], f"{r['priority_score']:.3f}", r["a_rank"], r["b_rank"],
               f"{r['b_unification_subscore']:g}", "・".join(r["reference_top30"]) or "—"] for r in p["units"]]
    ref = p["reference_top30_counts"]
    t = ["# 02 2 軸の評価と着手順序（成果物 2・3・4）", "", NOTICE, CAVEAT,
         "## 位置づけ", "",
         f"- 研究対象は、確定できた評価単位 **{p['unit_count']} 件のすべて**。2 軸の評価は**着手順序を決めるためだけ**に使い、対象の絞り込みには使っていない（追加・変更指示 第1号）。",
         "- 順位は独立概念モデルの評価単位についてのもので、原資料全体の順位ではない。",
         f"- 旧方針の上位 30％（各軸 {ref['k_per_axis']} 件）は参考として表に印を残した：軸 A {ref['A']} 件（重みを変えた場合だけ入るもの {ref['A_sensitivity_only']} 件）、軸 B {ref['B']} 件（境界の同点を含む）、和集合 {ref['union']} 件。", "",
         "## 軸 A：計算負荷・複雑性（成果物 2）", "",
         f"基準計算を標準ベンチマーク（規模 {'・'.join(sizes)}）で実行し、単位ごとの実行時間・実行したバイトコード命令数・ピークメモリを**実測**した。"
         "測定したのは独立に実装した基準計算であり、原版ブックではない（原版は実行していない）。時間は、ごみ集め（GC）を止めて測った反復の中央値。",
         f"重みは 実行時間 {a['weights']['a1']}、命令数 {a['weights']['a2']}、メモリ {a['weights']['a3']}、入力数と演算数 {a['weights']['a4']}、分岐と反復 {a['weights']['a5']}、"
         f"依存 {a['weights']['a6']}、対応するシート族の数式ノード占有率（推定の対応による代理指標）{a['weights']['a7']}。", "",
         table(["順位", "ID", "名称", "A スコア", f"時間の割合（{last}）", f"時間 ms（{last}）", f"命令数（{last}）", f"メモリ KiB（{last}）", "入力+演算", "分岐+反復", "依存", "ノード占有（推定）"],
               rows_a, ["---:", "---", "---", "---:", "---:", "---:", "---:", "---:", "---:", "---:", "---:", "---:"]), "",
         "重みを変えたときの順位の違いは [axis_a.json](axis_a.json) の `rank_by_variant` にある（実行時間のみ、全指標等重み、代理指標を除外）。", "",
         "## 軸 B：簡略化・近似化・統合の余地（成果物 3）", "",
         "互いの採点を見ない 3 つの自動評価（AI エージェント。観点は代数的統合、数値近似、入力・データモデル削減。人による評価ではない）が、評価単位の事実だけをまとめた資料（[axis_b_input_digest.json](axis_b_input_digest.json)）を読んで、"
         "8 観点を各 0〜3 点で採点した。B スコアは観点ごとの中央値の合計（0〜24）。統合に関する観点は b2・b3・b4・b8。", "",
         table(["順位", "ID", "名称", "B スコア", "統合観点", "b1", "b2", "b3", "b4", "b5", "b6", "b7", "b8", "3 者の合計", "評価の割れ"],
               rows_b, ["---:", "---", "---", "---:", "---:"] + ["---:"] * 8 + ["---", "---"]), "",
         f"3 者の合計の差が 6 点以上だった単位：{'、'.join(b['disputed_units']) or 'なし'}。採点の理由と置き換え案は [axis_b_judges/](axis_b_judges/) の各ファイルにある。"
         "採点は初版の台帳に対して行ったもので、その後に基準計算へ加えた X-16 の定義変更などは反映していない。"
         "評価者が挙げた置き換え案のうち 2 点以上のものが、その後どう記録されたかは [03_MODELS/judge_proposal_trace.json](../03_MODELS/judge_proposal_trace.json) にまとめた。", "",
         "## 研究対象と着手順序（成果物 4）", "",
         f"優先スコア = {p['priority_formula']}。上位から 3 つの着手群に分けたが、群は順番を示すだけで、第 3 群まで**独立概念モデルの全評価単位**に段階ごとの結論を記録した。"
         "ただし近似の段階（M3〜M6）には、実データ待ちの保留と、測定をせずに理由だけで見送ったものがある（[05_DECISIONS/PROGRESS.md](../05_DECISIONS/PROGRESS.md)）。", "",
         table(["着手順", "群", "ID", "名称", "段階", "優先スコア", "A 順位", "B 順位", "統合観点", "旧・上位30％"],
               rows_p, ["---:", "---:", "---", "---", "---", "---:", "---:", "---:", "---:", "---"])]
    write("02_RANKING/README.md", "\n".join(t))


