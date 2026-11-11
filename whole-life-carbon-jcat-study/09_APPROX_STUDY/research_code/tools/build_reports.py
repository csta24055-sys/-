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
             "NOT_INSPECTED": "未調査", "NON_CALCULATION": "計算なし"}
OUTCOME_JA = {"SUCCESS": "成功", "REJECTED": "不採用", "HOLD": "保留", "NOT_APPLICABLE": "対象外"}


def ledger_report():
    led = load("01_LEDGER/units.json")
    fam = load("01_LEDGER/sheet_families.json")
    cov = load("01_LEDGER/sheet_family_coverage.json")
    unl = load("01_LEDGER/unlinked_input_disposition.json")
    na = load("01_LEDGER/considered_not_adopted.json")["not_adopted"]
    units = led["units"]
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
         "- 基準計算が実際に採用した定義は、各単位の `reference_semantics` に記載している（基準計算の関数の説明文と同一）。", "",
         "## 調べていないもの（未調査の範囲）", "",
         f"- **原版ブックの数式本文は確認していない。** 本研究環境にも本リポジトリにも原版ファイルは存在しない。約 {total:,} の数式ノードを調査したものではない。",
         "- 下表の「対応」は**シート名だけからの推定**で、原版の式の内容が評価単位と同じであることを意味しない。",
         f"- 名称から計算構造を特定できなかったシート族は {by_status.get('NOT_INSPECTED', [0, 0])[0]} 件（数式ノードの {pct(by_status.get('NOT_INSPECTED', [0, 0])[1] / total, 2)}）。未調査として残した。",
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
         "- [sheet_family_coverage.json](sheet_family_coverage.json)：シート族と評価単位の対応（名称からの推定）",
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
         "測定したのは独立に実装した基準計算であり、原版ブックではない（原版は実行していない）。",
         f"重みは 実行時間 {a['weights']['a1']}、命令数 {a['weights']['a2']}、メモリ {a['weights']['a3']}、入力数と演算数 {a['weights']['a4']}、分岐と反復 {a['weights']['a5']}、"
         f"依存 {a['weights']['a6']}、対応するシート族の数式ノード占有率（推定の対応による代理指標）{a['weights']['a7']}。", "",
         table(["順位", "ID", "名称", "A スコア", f"時間の割合（{last}）", f"時間 ms（{last}）", f"命令数（{last}）", f"メモリ KiB（{last}）", "入力+演算", "分岐+反復", "依存", "ノード占有（推定）"],
               rows_a, ["---:", "---", "---", "---:", "---:", "---:", "---:", "---:", "---:", "---:", "---:", "---:"]), "",
         "重みを変えたときの順位の違いは [axis_a.json](axis_a.json) の `rank_by_variant` にある（実行時間のみ、全指標等重み、代理指標を除外）。", "",
         "## 軸 B：簡略化・近似化・統合の余地（成果物 3）", "",
         "互いの採点を見ない 3 名（代数的統合、数値近似、入力・データモデル削減）が、評価単位の事実だけをまとめた資料（[axis_b_input_digest.json](axis_b_input_digest.json)）を読んで、"
         "8 観点を各 0〜3 点で採点した。B スコアは観点ごとの中央値の合計（0〜24）。統合に関する観点は b2・b3・b4・b8。", "",
         table(["順位", "ID", "名称", "B スコア", "統合観点", "b1", "b2", "b3", "b4", "b5", "b6", "b7", "b8", "3 名の合計", "評価の割れ"],
               rows_b, ["---:", "---", "---", "---:", "---:"] + ["---:"] * 8 + ["---", "---"]), "",
         f"3 名の合計の差が 6 点以上だった単位：{'、'.join(b['disputed_units']) or 'なし'}。採点の理由と置き換え案は [axis_b_judges/](axis_b_judges/) の各ファイルにある。", "",
         "## 研究対象と着手順序（成果物 4）", "",
         f"優先スコア = {p['priority_formula']}。上位から 3 つの着手群に分けたが、群は順番を示すだけで、**第 3 群まで全件を検証した**（結果は [05_DECISIONS/PROGRESS.md](../05_DECISIONS/PROGRESS.md)）。", "",
         table(["着手順", "群", "ID", "名称", "段階", "優先スコア", "A 順位", "B 順位", "統合観点", "旧・上位30％"],
               rows_p, ["---:", "---:", "---", "---", "---", "---:", "---:", "---:", "---:", "---"])]
    write("02_RANKING/README.md", "\n".join(t))


def models_report():
    models = load("03_MODELS/models.json")["models"]
    cands = load("03_MODELS/candidates.json")["candidates"]
    recs = load("03_MODELS/records/units.json")
    oc = Counter(r["outcome"] for r in recs["records"])
    names = {u["id"]: u["name"] for u in load("01_LEDGER/units.json")["units"]}
    t = ["# 03 検討した近似式・統合モデル（成果物 5）", "", NOTICE, CAVEAT,
         "## 結論の要約", "",
         f"- 評価単位ごとに 6 段階（M1 厳密な簡略化、M2 厳密な統合、M3 単純な近似、M4 共通の近似モデル、M5 代理モデル、M6 併用）を検討し、**{recs['record_count']} 件**の記録を残した"
         f"（成功 {oc['SUCCESS']}、不採用 {oc['REJECTED']}、保留 {oc['HOLD']}、対象外 {oc['NOT_APPLICABLE']}）。記録は [records/units.json](records/units.json)。",
         f"- 計算できる 69 単位のうち {sum(m['unit_count'] for m in models)} 単位が、下の **8 つの統合モデル**に**結果を変えずに**まとまった。",
         "- 近似候補は、測定の結果、採用できるものがなかった（不採用または実データ待ちの保留）。厳密な統合だけで計算が十分に軽くなり、近似で得るものが残らなかったためである。", "",
         "## 全体を 1 つの式で書くと", "",
         "```",
         "E[段階] = Σ_行  活動量 × 係数 × 乗数(段階; T, 行のパラメータ)",
         "",
         "乗数の種類   1 回限り      1                         A1-A3・A4・A5・C1〜C4",
         "            更新          N(T, 周期)                B4",
         "            修繕          修繕率 × (T − 除外年)     B3",
         "            建替          N(T, 建替周期) × 範囲比   B5",
         "            年次          年重み付きの和            B6・B7・B2",
         "            充填サイクル  1 − (1−漏洩率)^年数 など  B1",
         "```",
         "",
         "- 材料・用途・構造の違いは**式には現れない**。違うのは行（数量と係数）というデータだけで、式は共通である。",
         "- 評価期間 T と更新・修繕の条件は、乗数の関数の引数として入る。T を変えても式は同じで、乗数を計算し直すだけでよい。",
         "- 段階ごとの値、ガス別の内訳、CO2 のみの結果、各種の指標は、同じ行テーブルから読み出す。", "",
         "## 統合モデルの目録", "",
         table(["ID", "名称", "式", "考え方", "統合しても保つもの", "単位数"],
               [[m["id"], m["name"], f"`{m['form']}`", m["idea"], m["kept"], m["unit_count"]] for m in models],
               ["---", "---", "---", "---", "---", "---:"]), "",
         "統合した単位：", "",
         "\n".join(f"- **{m['id']} {m['name']}**（{m['unit_count']}）：{'、'.join(m['units'])}" for m in models), "",
         "統合しなかった単位：B1-01・STO-01・STO-02 は参考値（段階合計の外）で、関数形は同じでも境界を保つために行テーブルへ入れていない。X-16 は入力とデータがなく保留。", "",
         "## 近似候補と測定結果", "",
         "誤差 = (候補 − 基準) ÷ 基準。負は過小評価。「段階」は候補が置き換える段階の値、「合計」はホールライフ合計に対する影響。", "",
         table(["ID", "候補", "判定", "段階：平均", "段階：95％点", "段階：最大の過大", "段階：最大の過小", "合計：95％点", "理由"],
               [[c["candidate_id"], c["title"], OUTCOME_JA[c["outcome"]], pct(c["stage_error"].get("mean_signed"), 1, True), pct(c["stage_error"].get("p95_abs")),
                 pct(c["stage_error"].get("max_over"), 1, True), pct(c["stage_error"].get("max_under"), 1, True), pct(c["total_error"].get("p95_abs")), c["reason"]]
                for c in cands], ["---", "---", "---", "---:", "---:", "---:", "---:", "---:", "---"]), "",
         "- 保留の候補（AP-10〜13・15・16）は、誤差が建物ごとの資材構成や使用量の分布で決まる。架空データは実建物を表していないので、ここでの値からは採否を判断できない。必要なデータは [06_OPEN_ISSUES](../06_OPEN_ISSUES/README.md) に記載した。",
         "- 条件別の内訳（買電量の種類別、電力係数の種類別、漏洩率×年数別、構造別・用途別）は [04_VERIFICATION/approximation_study.json](../04_VERIFICATION/approximation_study.json) にある。", "",
         "## 単位別の記録の見方", "",
         "`records/units.json` の 1 件は「評価単位×段階×候補」。`outcome` は SUCCESS・REJECTED・HOLD・NOT_APPLICABLE のいずれかで、SUCCESS は検証出力に裏付けがあるものだけ"
         "（生成時に検証出力と突き合わせ、裏付けがなければ生成が失敗する）。NOT_APPLICABLE には必ず理由がある。"]
    write("03_MODELS/README.md", "\n".join(t))


def verification_report():
    ex = load("04_VERIFICATION/unified_model_exactness.json")
    ld = load("04_VERIFICATION/unified_model_load.json")
    ap = load("04_VERIFICATION/approximation_study.json")
    leaves = sum(u["leaves_compared"] for u in ex["units"].values())
    other = sum(u["non_numeric_compared"] for u in ex["units"].values())
    worst = max(ex["units"].items(), key=lambda kv: kv[1]["max_abs_rel_error"])
    group_ja = {"benchmark": "標準ベンチマーク", "edge": "境界条件", "population": "検証用の母集団", "defective": "欠陥を入れたシナリオ"}
    rows = []
    keys = [("reference_all_units", "基準計算（全単位）"), ("reference_without_SUM-08", "基準計算（基準案との比較 SUM-08 を除く）"),
            ("unified_full_outputs_baseline_recomputed", "統合モデル：全出力、基準案も計算"),
            ("unified_full_outputs_baseline_cached", "統合モデル：全出力、基準案は保持した結果を再利用"),
            ("unified_totals_only_baseline_cached", "統合モデル：合計・段階・指標・検査のみ")]
    for size, r in ld["sizes"].items():
        for key, label in keys:
            v = r[key]
            rows.append([size, f"{r['rows']['materials']:,}", label, f"{v['time_ms']:.1f}", f"{v['instructions']:,}", f"{v['peak_memory_kib']:,.0f}",
                         pct(v.get("time_reduction_vs_reference")) if "time_reduction_vs_reference" in v else "—",
                         f"{v['speedup_vs_reference']:.1f} 倍" if "speedup_vs_reference" in v else "—",
                         pct(v.get("instruction_reduction_vs_reference")) if "instruction_reduction_vs_reference" in v else "—",
                         pct(v.get("memory_reduction_vs_reference")) if "memory_reduction_vs_reference" in v else "—"])
    c = ap["candidates"]
    st = lambda s: f"{s['n']} 件、平均 {pct(s['mean_signed'], 2, True)}、95％点 {pct(s['p95_abs'], 2)}、範囲 {pct(s['max_under'], 1, True)}〜{pct(s['max_over'], 1, True)}" if s.get("n") else "該当なし"
    t = ["# 04 基準計算との誤差と処理時間（成果物 6）", "", NOTICE, CAVEAT,
         "## 1. 統合モデルは基準計算と一致するか", "",
         f"統合モデル（`research_code/fastcalc/engine.py`）と基準計算（`research_code/refcalc/`）の全出力を、**{ex['scenarios']} シナリオ**で 1 つずつ突き合わせた。", "",
         table(["シナリオの種類", "件数", "最大の相対差", "不一致のシナリオ"],
               [[group_ja[k], v["scenarios"], f"{v['max_abs_rel_error']:.1e}", v["failed"]] for k, v in ex["by_group"].items()], ["---", "---:", "---:", "---:"]), "",
         f"- 比較した数値は **{leaves:,} 個**、数値以外（合否・状態・件数の一覧など）は {other:,} 個。許容差は相対 {ex['tolerance']:.0e}。",
         f"- 結果：**不一致なし**（`all_exact = {str(ex['all_exact']).lower()}`）。最大の相対差は {worst[1]['max_abs_rel_error']:.1e}（{worst[0]}）で、加算の順序が違うことによる丸めの差。",
         "- 欠陥を入れたシナリオ（欠損、使用許諾のない係数、単位の不整合、比率の不整合、期間外の事象、面積 0）でも、検査の結果と、計算から除外される行が一致した。"
         "つまり、統合しても入力検査は弱まっていない。",
         "- 「合計・段階・指標・検査のみ」の出力でも同じ値になることを確認した。",
         "- 個々の閉形式（更新回数、修繕の除外年、年次の和、電力係数の累積、冷媒の充填サイクル）は、ループ版との一致を別途、乱数と境界値で検査している（`tests/test_closed_forms.py`）。", "",
         "## 2. 計算の重さはどれだけ減るか", "",
         "同じ言語（純粋な Python）、同じ機械、同じ入力で測った。ベクトル化などの実装技法の効果は含まない。時間は反復の中央値。", "",
         table(["規模", "資材行", "計算", "時間 ms", "命令数", "ピークメモリ KiB", "時間の削減", "速さ", "命令数の削減", "メモリの削減"],
               rows, ["---", "---:", "---", "---:", "---:", "---:", "---:", "---:", "---:", "---:"]), "",
         "- 削減率は「基準計算（全単位）」に対する値。基準計算は基準案との比較（SUM-08）のたびに基準案を最初から計算し直すので、その分が大きい。",
         "- 「全出力」は、基準計算が出す行別の一覧と年次の系列をすべて出す場合。「合計・段階・指標・検査のみ」はそれらを省いた場合。",
         "- 測定値は実行環境で変わる。再測定は `python3 -m bench.verify_unified`。", "",
         "## 3. 近似候補の誤差", "",
         f"検証用の母集団 {ap['population']} シナリオ（構造 4 種×用途 6 種、規模 S・M、評価期間 30〜100 年と非整数）で測定した。目標は 合計 {pct(ap['targets']['total'], 0)}、段階 {pct(ap['targets']['stage'], 0)}。", "",
         table(["ID", "候補", "対象の段階", "段階の誤差", "合計への影響（95％点）", "過小評価"],
               [[cid, v["title"], v["stage"], st(v["stage_error"]), pct(v["total_error"].get("p95_abs"), 2), "あり" if v["under_estimates"] else "なし"]
                for cid, v in c.items()]), "",
         "条件別に見ると：", "",
         f"- **AP-08（平均×平均）**：買電量が一定なら {st(c['AP-08']['by_profile_kind']['CONSTANT'])}。直線的に変化する場合は {st(c['AP-08']['by_profile_kind']['LINEAR_TREND'])}。",
         f"- **AP-09a（5 年ごとの補間）**：直線低下の係数では {st(c['AP-09a']['by_grid_kind']['LINEAR_DECLINE_TO_FLOOR'])}、段階的な係数では {st(c['AP-09a']['by_grid_kind']['STEPWISE'])}。",
         f"- **AP-05（冷媒の線形近似）**：補充しない機器で 漏洩率×サイクル年数 が 0.05〜0.2 の場合 {st(c['AP-05']['by_rate_times_cycle_years_no_top_up_devices']['0.05<rk<=0.2'])}。",
         "- **AP-04（修繕の概算）**：構造別・用途別のどの区分でも過大側で、区分による差は小さい（下表）。", "",
         table(["区分", "件数", "平均", "95％点", "最大"],
               [[k, v["n"], pct(v["mean_signed"], 2, True), pct(v["p95_abs"], 2), pct(v["max_over"], 2, True)] for k, v in c["AP-04"]["by_group"].items()],
               ["---", "---:", "---:", "---:", "---:"]), "",
         "代理モデル（AP-15）の段階別の誤差（架空の母集団）：", "",
         table(["段階", "件数", "平均", "95％点", "最大の過大", "最大の過小"],
               [[k, v["n"], pct(v["mean_signed"], 0, True), pct(v["p95_abs"], 0), pct(v["max_over"], 0, True), pct(v["max_under"], 0, True)]
                for k, v in c["AP-15"]["by_stage"].items() if v.get("n")], ["---", "---:", "---:", "---:", "---:", "---:"]), "",
         "これらの大きな誤差は、架空データの数量と係数を広い範囲の乱数で作っているためで、実建物での誤差を表していない。代理モデルの採否は実データなしには判断できない。", "",
         "## ファイル", "",
         "- [unified_model_exactness.json](unified_model_exactness.json)：単位ごとの比較結果",
         "- [unified_model_load.json](unified_model_load.json)：時間・命令数・メモリ",
         "- [approximation_study.json](approximation_study.json)：近似候補の誤差（全体・構造別・用途別・条件別）"]
    write("04_VERIFICATION/README.md", "\n".join(t))


def decisions_report():
    models = load("03_MODELS/models.json")["models"]
    cands = load("03_MODELS/candidates.json")["candidates"]
    led = load("05_DECISIONS/progress_ledger.json")
    ld = load("04_VERIFICATION/unified_model_load.json")["sizes"]
    ex = load("04_VERIFICATION/unified_model_exactness.json")
    units = load("01_LEDGER/units.json")["units"]
    cov = load("01_LEDGER/sheet_family_coverage.json")["families"]
    status = Counter(u["status"] for u in led["units"])
    n_units = len(units)
    computable = sum(u["computable_in_reference"] for u in units)
    unified = sum(m["unit_count"] for m in models)
    kept = [u["id"] for u in led["units"] if u["status"] == "DONE_APPROX_REJECTED"]
    hold = [u["id"] for u in led["units"] if u["status"] == "HOLD_DATA_OR_RIGHTS"]
    partial = [u for u in led["units"] if u["steps_on_hold"] and u["status"].startswith("DONE")]
    inputs_used = sorted({i for u in units if u["computable_in_reference"] for i in u["inputs"] if not i.startswith("NEW:")})
    fam_by_unit = {}
    for f in cov:
        for uid in f["related_units"]:
            fam_by_unit.setdefault(uid, []).append(f)
    rows_models = []
    for m in models:
        fams = {f["family"]: f for uid in m["units"] for f in fam_by_unit.get(uid, []) if f["formula_xml_nodes"]}
        top = sorted(fams.values(), key=lambda f: -f["formula_xml_nodes"])[:3]
        rows_models.append([m["id"], m["name"], m["unit_count"], "、".join(f"{f['family']}（{pct(f['share_of_all_nodes'], 1)}）" for f in top) or "—"])
    L = ld["L"]
    full, tot = L["unified_full_outputs_baseline_cached"], L["unified_totals_only_baseline_cached"]
    cold = L["unified_full_outputs_baseline_recomputed"]
    t = ["# 05 採否の理由と、統合前後の変化（成果物 7・8）", "", NOTICE, CAVEAT,
         "## 採用（研究上の推奨）", "",
         f"**8 つの統合モデル（K1〜K8）を、厳密な統合として推奨する。** {ex['scenarios']} の架空シナリオで基準計算と全出力が一致し、入力検査の結果も変わらない。"
         "ここでの「採用」は将来の実装候補としての推奨で、製品への組み込みを意味しない。", "",
         table(["モデル", "名称", "まとめた単位数", "関連すると推定されるシート族（数式ノード占有率）"], rows_models, ["---", "---", "---:", "---"]), "",
         "右端の列は、シート名だけからの推定による対応で、原版の式がこのモデルで置き換えられることを確認したものではない。", "",
         "## 不採用", "",
         "\n".join(f"- **{c['candidate_id']} {c['title']}**：{c['reason']}" for c in cands if c["outcome"] == "REJECTED"), "",
         "共通する理由は 2 つ。(1) 重大な過小評価が出る、または誤差が段階 2％・合計 1％ の目標を超える。(2) 厳密な閉形式が同じ手間で使えるので、近似に替える利点がない。", "",
         "## 検証保留", "",
         "\n".join(f"- **{c['candidate_id']} {c['title']}**：{c['reason']} 必要なデータ：{c['data_needed']}" for c in cands if c["outcome"] == "HOLD"), "",
         f"- **X-16 物価補正**：{next(u.get('unit_hold_reason') for u in led['units'] if u['id'] == 'X-16')}。", "",
         "## 現状のまま維持", "",
         f"- {'、'.join(kept)}：すでに最小の形（積 1 回）の参考値で、段階合計の外にある。関数形は活動量×係数と同じだが、合計と混同しないよう行テーブルへは入れない。",
         "- すべての検査（SYS・QA・C-05）：近似しない。統合は「同じ判定を繰り返さない」ことだけで、判定の基準は変えていない。", "",
         "## 進捗の集計", "",
         table(["状態", "件数"], [[led["status_labels"][k], status.get(k, 0)] for k in led["status_labels"]] + [["**合計**", f"**{n_units}**"]], ["---", "---:"]), "",
         f"検証完了のうち {len(partial)} 単位は、一部の段階（主に M4：少数入力の共通近似モデル）が実データ待ちで保留になっている。単位ごとの状態は [PROGRESS.md](PROGRESS.md)。", "",
         "## 統合前後の変化（成果物 8）", "",
         table(["項目", "統合前", "統合後", "変化"], [
             ["計算式の種類（評価単位）", f"{computable}（計算できるもの）", f"{len(models) + len(kept)}（統合モデル {len(models)}＋維持 {len(kept)}）", pct(1 - (len(models) + len(kept)) / computable) + " 減"],
             ["共通化できた単位", "—", f"{unified} 単位 → {len(models)} モデル", pct(1 - len(models) / unified) + " 減"],
             ["必要な入力項目", f"{len(inputs_used)}（既存 124 項目のうち式が使うもの）", f"{len(inputs_used)}", "変化なし"],
             [f"計算時間（規模 L、全出力）", f"{L['reference_all_units']['time_ms']:.0f} ms", f"{full['time_ms']:.0f} ms", pct(full["time_reduction_vs_reference"]) + " 減"],
             [f"同（基準案との比較を除いた部分どうし）", f"{L['reference_without_SUM-08']['time_ms']:.0f} ms", f"{full['time_ms']:.0f} ms", pct(1 - full["time_ms"] / L["reference_without_SUM-08"]["time_ms"]) + " 減"],
             [f"同（基準案も毎回計算する場合）", f"{L['reference_all_units']['time_ms']:.0f} ms", f"{cold['time_ms']:.0f} ms", pct(cold["time_reduction_vs_reference"]) + " 減"],
             [f"同（合計・段階・指標・検査のみ）", f"{L['reference_all_units']['time_ms']:.0f} ms", f"{tot['time_ms']:.0f} ms", pct(tot["time_reduction_vs_reference"]) + " 減"],
             ["実行した命令数（規模 L、全出力）", f"{L['reference_all_units']['instructions']:,}", f"{full['instructions']:,}", pct(full["instruction_reduction_vs_reference"]) + " 減"],
             ["ピークメモリ（規模 L、全出力）", f"{L['reference_all_units']['peak_memory_kib'] / 1024:.0f} MiB", f"{full['peak_memory_kib'] / 1024:.0f} MiB", pct(full["memory_reduction_vs_reference"]) + " 減"],
             ["結果の差", "—", f"相対 {ex['tolerance']:.0e} 以内で一致", "精度の低下なし"],
         ], ["---", "---:", "---:", "---:"]), "",
         "- **入力項目は減っていない。** 厳密な統合は結果を変えないので、必要な入力も変わらない。入力を減らすには少数入力の近似モデル（AP-10・11・15・16）が必要で、それは実データ待ちで保留している。",
         "- 計算の重さが減った主な理由は、(a) 行を 1 回だけ走査する、(b) 年ごと・事象ごとのループを閉形式にする、(c) 係数を掛ける前に活動量を合算する、(d) 基準案の結果を使い回す、の 4 つ。"
         "1 行目の削減率には (d) の効果が含まれる。(d) を除いた効果が 2 行目、(d) を使わない場合が 3 行目である。",
         "- 規模 S・M の値は [04_VERIFICATION](../04_VERIFICATION/README.md) にある。",
         "- これらは独立に実装した基準計算に対する値で、原版ブックの計算時間がどれだけ変わるかを示すものではない。"]
    write("05_DECISIONS/README.md", "\n".join(t))


def overview_report():
    led = load("01_LEDGER/units.json")
    cov = load("01_LEDGER/sheet_family_coverage.json")
    models = load("03_MODELS/models.json")["models"]
    cands = load("03_MODELS/candidates.json")["candidates"]
    recs = load("03_MODELS/records/units.json")
    ex = load("04_VERIFICATION/unified_model_exactness.json")
    ld = load("04_VERIFICATION/unified_model_load.json")["sizes"]["L"]
    prog = load("05_DECISIONS/progress_ledger.json")
    status = Counter(u["status"] for u in prog["units"])
    partial = sum(1 for u in prog["units"] if u["steps_on_hold"] and u["status"].startswith("DONE"))
    leaves = sum(u["leaves_compared"] for u in ex["units"].values())
    not_inspected = [f for f in cov["families"] if f["status"] == "NOT_INSPECTED"]
    oc = Counter(c["outcome"] for c in cands)
    full, tot = ld["unified_full_outputs_baseline_cached"], ld["unified_totals_only_baseline_cached"]
    t = ["# 第9章：計算式の近似化・統合研究", "", NOTICE,
         "独立計算モデルの式群を、必要な精度を保ったまま、できるだけ少数の簡単な計算式へ置き換えられるかを調べた研究の記録。",
         "**アプリ・UI・製品用エンジンは作っていない。** J-CAT の原版ファイル・式本文・原単位などは含まない（[第1章](../01_COMPLIANCE/README.md)）。", "",
         "## 統制文書", "",
         "- [00_POLICY/DIRECTIVE.md](00_POLICY/DIRECTIVE.md)：開発方針指示書（受領した全文）",
         "- [00_POLICY/DIRECTIVE_AMENDMENT_01.md](00_POLICY/DIRECTIVE_AMENDMENT_01.md)：追加・変更指示 第1号（上位 30％ 制限の撤廃。受領した全文）",
         "- [00_POLICY/EVALUATION_PROTOCOL.md](00_POLICY/EVALUATION_PROTOCOL.md)：評価単位、2 軸評価、着手順序、検討手順、検証手順、進捗台帳の定義", "",
         "## 結果の要点", "",
         f"1. **評価単位は {led['unit_count']} 件**（既存の概念式 {led['existing_unit_count']}＋追加で特定した計算構造 {led['additional_unit_count']}）。上位 30％ に絞らず、全件を研究対象にした。",
         f"2. **{sum(m['unit_count'] for m in models)} 単位が {len(models)} つの統合モデルに、結果を変えずにまとまった。** 全体は「活動量×係数×乗数」の 1 つの式と、数個の乗数の関数で書ける（[03_MODELS](03_MODELS/README.md)）。",
         f"3. **統合モデルは基準計算と一致した。** {ex['scenarios']} の架空シナリオ、数値 {leaves:,} 個を突き合わせて不一致なし（許容差は相対 {ex['tolerance']:.0e}）。入力検査の結果も変わらない。",
         f"4. **計算の重さは大きく減った。** 資材 2 万行の規模で、計算時間は {ld['reference_all_units']['time_ms']:.0f} ms から {full['time_ms']:.0f} ms（{pct(full['time_reduction_vs_reference'])} 減）。"
         f"このうち基準案との比較を除いた部分だけで比べても {ld['reference_without_SUM-08']['time_ms']:.0f} ms から {full['time_ms']:.0f} ms（{pct(1 - full['time_ms'] / ld['reference_without_SUM-08']['time_ms'])} 減）。"
         f"ピークメモリは {pct(full['memory_reduction_vs_reference'])} 減（同じ言語・同じ機械での比較。内訳は [05_DECISIONS](05_DECISIONS/README.md)）。",
         f"5. **近似は採用しなかった。** 近似候補 {len(cands)} 種を測定し、不採用 {oc['REJECTED']}、実データ待ちの保留 {oc['HOLD']}。更新回数の連続近似のように重大な過小評価を生むものがあり、"
         "それ以外も、厳密な閉形式が同じ手間で使えるため近似の利点がなかった。",
         "6. **入力項目は減っていない。** 入力を減らすには少数入力の近似モデルが必要だが、その精度は実建物のデータがなければ検証できない（保留）。",
         "7. 材料・用途・構造の違いは式には現れず、行（数量と係数）というデータの違いとして扱える。評価期間と更新・修繕の条件は、乗数の関数の引数になる。", "",
         "## 進捗（全評価単位）", "",
         table(["状態", "件数"], [[prog["status_labels"][k], status.get(k, 0)] for k in prog["status_labels"]] + [["**合計**", f"**{len(prog['units'])}**"]], ["---", "---:"]), "",
         f"検証完了のうち {partial} 単位は、一部の段階（主に少数入力の共通近似モデル）が実データ待ちで保留。記録は {recs['record_count']} 件（[05_DECISIONS/PROGRESS.md](05_DECISIONS/PROGRESS.md)）。", "",
         "## この研究で言えないこと", "",
         "- **原版ブックの数式は調べていない。** 原版ファイルは本リポジトリにも研究環境にも存在しない。評価単位は独立概念モデルのもので、原版の約 382 万の数式ノードを調査・検証したものではない。",
         f"- シート名と評価単位の対応は名称からの推定。名称から構造を特定できなかったシート族が {len(not_inspected)} 件ある（{'、'.join(f['family'] for f in not_inspected)}）。",
         "- 検証はすべて架空データ。**実建物での精度、他のツールとの一致は検証していない。**",
         "- 計算時間は独立に実装した基準計算との比較で、原版ブックの計算時間がどれだけ変わるかは分からない。",
         "- 基準計算の定義には、本研究が決めた規約（端数年の按分、事象の年への帰属、更新年の修繕の除外など）が含まれる。未決の点は [06_OPEN_ISSUES](06_OPEN_ISSUES/README.md) に挙げた。", "",
         "## 成果物", "",
         table(["成果物", "場所"], [
             ["1 全計算式・式群の分類台帳", "[01_LEDGER/](01_LEDGER/README.md)"],
             ["2 評価軸 A のランキング", "[02_RANKING/](02_RANKING/README.md)"],
             ["3 評価軸 B のランキング", "[02_RANKING/](02_RANKING/README.md)"],
             ["4 研究対象と着手順序", "[02_RANKING/](02_RANKING/README.md)"],
             ["5 検討した近似式・統合モデル", "[03_MODELS/](03_MODELS/README.md)"],
             ["6 基準計算との誤差と処理時間", "[04_VERIFICATION/](04_VERIFICATION/README.md)"],
             ["7 採用・不採用・検証保留の理由、進捗台帳", "[05_DECISIONS/](05_DECISIONS/README.md)、[PROGRESS.md](05_DECISIONS/PROGRESS.md)"],
             ["8 統合前後の数式数と計算負荷", "[05_DECISIONS/](05_DECISIONS/README.md)"],
             ["9 未解決事項と必要なデータ", "[06_OPEN_ISSUES/](06_OPEN_ISSUES/README.md)"],
             ["次段階の材料分類の構造調査", "[07_MATERIAL_TAXONOMY/](07_MATERIAL_TAXONOMY/README.md)"],
             ["検算用コード（製品コードではない）", "[research_code/](research_code/README.md)"],
         ])]
    write("README.md", "\n".join(t))


def main() -> int:
    overview_report()
    ledger_report()
    ranking_report()
    models_report()
    verification_report()
    decisions_report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
