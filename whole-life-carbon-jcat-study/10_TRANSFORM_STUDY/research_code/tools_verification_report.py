"""Writes ``11_UNIFIED_SYSTEM/VERIFICATION.md`` from the JSON results of the checks and experiments.

Run from ``research_code`` after the checks:  PYTHONDONTWRITEBYTECODE=1 python3 -B tools_verification_report.py
Nothing is computed here except sums, maxima and percentiles of the recorded numbers.
"""
import collections
import json
import os
import sys

sys.dont_write_bytecode = True

from checks import sets_unified

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.normpath(os.path.join(HERE, "..", "11_UNIFIED_SYSTEM", "results"))
OUT = os.path.normpath(os.path.join(HERE, "..", "11_UNIFIED_SYSTEM", "VERIFICATION.md"))
PURPOSE = {
    "dev_design": "調整用：設計用集合 40 件 × 4 期間", "dev_edge": "調整用：名前付き境界条件 32 件 × 2 期間",
    "rep_evaluation": "再現：評価用集合 60 件 × 5 期間", "rep_boundary": "再現：境界の評価期間（S・評価用 3 件・M）",
    "rep_constructed": "再現：特殊条件 115 件 × 3 期間", "rep_scale_L": "再現：最大規模 L × 2 期間",
    "rep_defects": "再現：欠陥入り 12 件 × 2 期間（有効範囲外）", "new_population": "新規：別シードの母集団 40 件 × 6 期間",
    "new_defects": "新規：欠陥入り 12 件 × 2 期間（有効範囲外）", "new_special": "新規：追加単位向けの特殊条件 × 3 期間（有効範囲外を含む）",
}


def load(name):
    path = os.path.join(RES, name)
    return json.load(open(path)) if os.path.exists(path) else None


def e(x):
    return "-" if x is None else "%.1e" % x


def main():
    sets = collections.OrderedDict((n, load("verification_%s.json" % n)) for n in sets_unified.ALL_SETS)
    sets = collections.OrderedDict((n, r) for n, r in sets.items() if r)
    L = ["# 検証結果（全70評価単位、基準計算との総当たり比較）", "",
         "`research_code/tools_verification_report.py` が `results/*.json` から生成した。数値はすべて架空データ・独立概念モデルでのもので、",
         "確認者は実装者のみ（証拠水準 N：数値の一致）。証明ではなく、他のツールとの整合を示すものでもない。", "",
         "比較の規則（`checks/check_msp_pre_a.py` の `compare`。緩めていない）：数値は相対差 1e-9 以内、基準計算が厳密に 0 の値は厳密に 0、",
         "真偽値・整数・文字列・一覧・辞書のキーは型を含めて完全一致。70 単位の公開出力キーをすべて、要素ごとに比べる。", "",
         "## 1. 集合ごとの結果", "",
         "| 集合 | 内容 | 組 | 除外 | 失敗 | 単位 | キー | 比較した値 | 不一致 | 最大相対差（単位） | SUM-03 p95 / 最大 | 段階 p95 の最大 / 段階の最大 |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    tot = collections.Counter()
    for n, r in sets.items():
        p3 = r["precision"].get("SUM-03", {})
        stage = [v for k, v in r["precision"].items() if k != "SUM-03" and v["n"]]
        L.append("| `%s` | %s | %d | %d | %d | %d | %d | %s | %d | %s（%s） | %s / %s | %s / %s |" % (
            n, PURPOSE.get(n, ""), r["n_pairs"], r["n_excluded"], r["n_failed"], r["n_units"], r["n_keys"], format(r["n_values"], ","),
            r["n_mismatch"], e(r["max_rel"]), r["max_rel_unit"], e(p3.get("p95")), e(p3.get("max")),
            e(max((v["p95"] for v in stage), default=None)), e(max((v["max"] for v in stage), default=None))))
        grp = n.split("_")[0]
        for k in ("n_pairs", "n_excluded", "n_failed", "n_values", "n_mismatch"):
            tot[(grp, k)] += r[k]; tot[("all", k)] += r[k]
    L += ["", "合計：%s 組、比較した値 %s 個、不一致 %d、失敗 %d、除外 %d。" % (
        format(tot[("all", "n_pairs")], ","), format(tot[("all", "n_values")], ","), tot[("all", "n_mismatch")], tot[("all", "n_failed")], tot[("all", "n_excluded")]),
          "内訳：調整用 %d 組、再現 %d 組（うち欠陥入り 24 組を除く %d 組が 2026-11-12 の「調整に使っていない 693 組」と同じ条件）、新規 %d 組。" % (
              tot[("dev", "n_pairs")], tot[("rep", "n_pairs")], tot[("rep", "n_pairs")] - (sets.get("rep_defects") or {}).get("n_pairs", 0), tot[("new", "n_pairs")]), ""]
    notes = [(n, x) for n, r in sets.items() for x in r["notes"]]
    if notes:
        L += ["除外・注記："] + ["- `%s`：%s" % nx for nx in notes[:20]] + [""]
    # ---- per unit
    units = collections.OrderedDict()
    for n, r in sets.items():
        for uid, u in r["units"].items():
            a = units.setdefault(uid, {"keys": set(), "n": 0, "bad": 0, "max": 0.0, "nf": 0, "nb": 0})
            a["keys"].update(u["keys"]); a["n"] += u["n_compared"]; a["bad"] += u["n_mismatch"]; a["max"] = max(a["max"], u["max_rel"])
            for k in u["keys"].values():
                a["nf"] += k["n_float"]; a["nb"] += k["n_bit_identical"]
    L += ["## 2. 単位ごとの結果（全集合の合計）", "",
          "「ビット一致」は、0 でない数値のうち基準計算と倍精度で完全に同じ値だった割合。", "",
          "| 単位 | 出力キー | 比較した値 | 不一致 | 最大相対差 | ビット一致 |", "|---|---|---|---|---|---|"]
    for uid, a in units.items():
        L.append("| %s | %s | %s | %d | %s | %s |" % (uid, ", ".join(sorted(a["keys"])), format(a["n"], ","), a["bad"], e(a["max"]) if a["nf"] else "-",
                                                    ("%.1f%%" % (100.0 * a["nb"] / a["nf"])) if a["nf"] else "-"))
    worst = sorted(((a["max"], uid) for uid, a in units.items()), reverse=True)[:6]
    L += ["", "単位 %d、出力キー %d。最大相対差の大きい順：%s。" % (len(units), sum(len(a["keys"]) for a in units.values()),
                                                  "、".join("%s %s" % (u, e(m)) for m, u in worst)), ""]
    # ---- precision criteria
    L += ["## 3. 精度の基準との対比", "",
          "暫定基準：ホールライフ合計（SUM-03）の相対誤差の 95 パーセンタイルが 1％以内、段階別が 2％以内。比較基準：2026-11-12 の最大相対差 5.7e-13。", "",
          "| 集合 | SUM-03 の組数 | SUM-03 p95 | SUM-03 最大 | 段階 p95 の最大 | 段階の最大 |", "|---|---|---|---|---|---|"]
    for n, r in sets.items():
        p3 = r["precision"].get("SUM-03", {})
        stage = [v for k, v in r["precision"].items() if k != "SUM-03" and v["n"]]
        L.append("| `%s` | %d | %s | %s | %s | %s |" % (n, p3.get("n", 0), e(p3.get("p95")), e(p3.get("max")),
                                                      e(max((v["p95"] for v in stage), default=None)), e(max((v["max"] for v in stage), default=None))))
    L += [""]
    # ---- variety
    var = collections.Counter()
    for r in sets.values():
        var.update(r["variety"])
    flags = collections.OrderedDict()
    for k, v in sorted(var.items()):
        for suffix in (" = True", " = False", " non-empty", " empty", " is None", " > 0", " = 0"):
            if k.endswith(suffix):
                flags.setdefault(k[:-len(suffix)], {})[suffix.strip()] = v
    L += ["## 4. 検査が実際に働いた回数（基準計算側の値の内訳）", "",
          "真偽値が常に真、一覧が常に空のままでは一致に意味がないので、基準計算の値の内訳を数えた。", "",
          "| 出力 | 内訳 |", "|---|---|"]
    for k, d in flags.items():
        if any(x in d for x in ("= True", "= False", "non-empty", "is None")) or k.split("/")[1] in ("n_partial", "n_used"):
            L.append("| %s | %s |" % (k, "、".join("%s %d" % kv for kv in d.items())))
    status = {k: v for k, v in var.items() if k.startswith(("SUM-08/status", "SYS-04/status", "QA-04/status", "X-06/source"))}
    L += ["", "状態の内訳：" + "、".join("%s %d" % kv for kv in sorted(status.items())), ""]
    # ---- controls
    c = load("controls.json")
    if c:
        L += ["## 5. 誤り検出の確認", "",
              "仕様を 1 か所ずつわざと壊し、比較がその単位の不一致を報告するかを確かめた（%d 件中 %d 件で検出）。" % (
                  c["summary"]["controls"], c["summary"]["controls_detected"]), "",
              "| 壊した内容 | 検出を期待した単位 | 結果 | 不一致が出た単位 |", "|---|---|---|---|"]
        for x in c["negative_controls"]:
            L.append("| %s | %s | %s | %s |" % (x["control"], ", ".join(x["expected_units"]), "検出" if x["detected"] else "**見逃し**",
                                               ", ".join(x["units_with_mismatch"][:8]) + (" …" if len(x["units_with_mismatch"]) > 8 else "")))
        L += ["", "QA-01 は入力では違反を起こせない（導出文書 D-12）。上流の結果を両側で同じように偽って、基準計算の関数と同じ違反一覧になるかを確かめた"
              "（%d 件中 %d 件で一致し、どれも不合格）。" % (c["summary"]["qa01_cases"], c["summary"]["qa01_agree_and_fail"]), "",
              "| 偽った内容 | 一致 | 基準計算の違反一覧 |", "|---|---|---|"]
        for x in c["qa01_fault_injection"]:
            L.append("| %s | %s | %s |" % (x["case"], "一致" if x["agree_and_fail"] else "**不一致**", "; ".join(x["reference"]["violations"][:5])))
        st = c["structure"]
        L += ["", "構造の確認：仕様 3 本はデータのみ（JSON にできる）＝%s、エンジン・平坦化・節点スペクトル・核・18 単位の仕様はコミット済みのまま＝%s、"
              "統合モジュールは基準計算を読まない＝%s。" % (st["SPEC1 is JSON-serialisable (data only)"],
                                           st["engine, flattening, knot spectrum, kernel and the 18-unit specification are the committed files"],
                                           st["tstudy/unified.py does not mention the reference calculation in code"]),
              "ステップ数：" + "、".join("%s %s" % (k, v) for k, v in st["steps"].items()) + "。使っている関数：" + ", ".join(st["functions_in_use"]) +
              "。エンジンの語彙の外の要素：%s。" % (st["vocabulary_outside_the_engine"] or "なし"), ""]
    # ---- experiments
    u1, u2, ext = load("expU1_b14_forms.json"), load("expU2_cross_engines.json"), load("external_engines.json")
    L += ["## 6. 別エンジンによる照合", ""]
    if u1:
        L += ["EXP-U1（mpmath 60 桁を真値とする B1-04 の 3 表現、%d 条件）：最大相対誤差は 基準計算 %s、跳び形 %s、区間形 %s、局所形（積和）%s。" % (
            len(u1["rows"]), e(u1["max"]["rel_err_reference"]), e(u1["max"]["rel_err_jump"]), e(u1["max"]["rel_err_interval"]), e(u1["max"]["rel_err_local"])), ""]
    if u2:
        L += ["EXP-U2：", "- SymPy（厳密）：" + "；".join("%s → %s" % kv for kv in u2["1_sympy"].items()),
              "- SciPy（疎な三角解、ベンチマーク M、未知数 %d）：積和 8 段との最大相対差 %s" % (u2["2_scipy_benchmark_M"]["n_unknowns"], e(u2["2_scipy_benchmark_M"]["max_rel_difference"])),
              "- DuckDB（SQL での再集計、ベンチマーク M）：" + "；".join("%s → %s" % (k, json.dumps(v, ensure_ascii=False)) for k, v in u2["3_duckdb_benchmark_M"].items())]
        if "4_lca_ops" in u2:
            L.append("- main の `math_tools_v2/lca_ops.py`（厳密な有理数）：" + "；".join("T=%s 厳密値 %s、相対差 %s" % (x["T"], x["lca_ops_exact"], e(x["rel_difference"])) for x in u2["4_lca_ops"]))
        L.append("- 版：" + json.dumps(u2["versions"]))
        L.append("")
    if ext:
        for k in ("sagemath", "matlab"):
            L.append("- %s（GitHub Actions、実行 ID %s、%s）：%s" % (k, ext[k]["run_id"], ext[k]["conclusion"], json.dumps(ext[k]["output"])))
        L.append("")
    with open(OUT, "w") as f:
        f.write("\n".join(L) + "\n")
    print("written", OUT, "sets", list(sets), "units", len(units))


if __name__ == "__main__":
    main()
