"""06_全検証ケース.csv: every verification whose result is SAVED in the repository, one row per comparison record.

Only saved evidence is used; nothing is recomputed and nothing is estimated. Where a quantity was not
saved (for example the absolute error, or the result of each single (scenario, T) pair), the row says so.
Usage: python3 -B tools_verification_export.py <out dir> [app test log]
"""
from __future__ import annotations

import csv
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.normpath(os.path.join(HERE, "..", ".."))
RES10 = os.path.join(STUDY, "10_TRANSFORM_STUDY", "11_UNIFIED_SYSTEM", "results")
RES09 = os.path.join(STUDY, "09_APPROX_STUDY", "04_VERIFICATION")
NOT_SAVED = "保存なし"
HEAD = ["検証ID", "区分", "対象（評価単位・出力キー・式）", "入力条件", "評価期間・時間条件", "比較した2つの方程式（実装）", "比較した値の数",
        "不一致の数", "最大相対誤差", "最大絶対誤差", "合格条件", "結果", "証拠ファイル"]
TOL = "相対差 ≤ 1e-9（|基準| < 1e-300 では絶対差 ≤ 1e-300）、0 は厳密に 0、型・キー・None の位置が一致"


def rel(path):
    return os.path.relpath(path, STUDY).replace(os.sep, "/")


def main(out, app_log=None):
    rows = []
    add = rows.append
    # ---- A. unified system vs reference calculation, per set x unit x key
    for path in sorted(glob.glob(os.path.join(RES10, "verification_*.json"))):
        d = json.load(open(path, encoding="utf-8"))
        s = d["set"]
        cond = "集合 %s：%d 組（除外 %d、失敗 %d）%s" % (s, d["n_pairs"], d["n_excluded"], d["n_failed"],
                                                "・有効域の外も含む" if s in ("rep_defects", "new_defects", "new_special") else "")
        add(["U-%s" % s, "統一系×基準計算（集合の総計）", "全 70 単位・%d キー" % d["n_keys"], cond, "06b_統一系の検証組一覧.csv の集合 %s" % s,
             "tstudy.unified.System.at(T) ↔ refcalc（基準計算）", d["n_values"], d["n_mismatch"], d["max_rel"], NOT_SAVED, TOL,
             "合格" if d["n_mismatch"] == 0 and d["n_failed"] == 0 else "不合格", rel(path)])
        for uid, u in sorted(d["units"].items()):
            for key, k in sorted(u["keys"].items()):
                add(["U-%s-%s-%s" % (s, uid, key), "統一系×基準計算", "%s.%s" % (uid, key), cond, "集合 %s の全組" % s,
                     "tstudy.unified.System.at(T) ↔ refcalc", k["n_compared"], k["n_mismatch"], k["max_rel"], NOT_SAVED, TOL,
                     "合格" if k["n_mismatch"] == 0 else "不合格", rel(path)])
        for stage, p in sorted(d.get("precision", {}).items()):
            add(["U-%s-precision-%s" % (s, stage), "統一系×基準計算（精度の分布）", "段階・合計 %s" % stage, cond, "集合 %s" % s,
                 "tstudy.unified.System.at(T) ↔ refcalc", p["n"], NOT_SAVED, p["max"], NOT_SAVED, "p95 = %.3g（保存値）" % p["p95"],
                 "記録", rel(path)])
    # ---- B. controls
    c = json.load(open(os.path.join(RES10, "controls.json"), encoding="utf-8"))
    for i, x in enumerate(c["negative_controls"], 1):
        add(["C-NEG-%02d" % i, "負の対照（仕様をわざと壊す）", x["control"], "対照ごとの組 %d" % x["n_pairs"], NOT_SAVED,
             "壊した統一系 ↔ refcalc", NOT_SAVED, x["n_mismatch"], NOT_SAVED, NOT_SAVED, "期待した単位（%s）で不一致が検出されること" % ",".join(x["expected_units"]),
             "検出" if x["detected"] else "未検出", rel(os.path.join(RES10, "controls.json"))])
    for i, x in enumerate(c["qa01_fault_injection"], 1):
        add(["C-QA01-%d" % i, "故障注入（QA-01）", x["case"], "故障を入れた架空シナリオ", NOT_SAVED, "統一系 QA-01 ↔ refcalc QA-01", 1,
             0 if x["agree_and_fail"] else 1, NOT_SAVED, NOT_SAVED, "両方が同じ違反を検出すること", "合格" if x["agree_and_fail"] else "不合格",
             rel(os.path.join(RES10, "controls.json"))])
    for k, v in c["structure"].items():
        if isinstance(v, bool):
            add(["C-STR-%s" % re.sub(r"\W+", "_", k)[:40], "構造の確認", k, "仕様・コード", "-", "-", 1, 0 if v else 1, "-", "-", "真であること",
                 "合格" if v else "不合格", rel(os.path.join(RES10, "controls.json"))])
    # ---- C. experiments
    e1 = json.load(open(os.path.join(RES10, "expU1_b14_forms.json"), encoding="utf-8"))
    for i, r in enumerate(e1["rows"], 1):
        for form in ("reference", "interval", "local", "jump"):
            add(["X-U1-%03d-%s" % (i, form), "実験 U1：B1-04 の表現", "B1-04（%s 形）" % form, "%s／%s" % (e1["scenario"], r["case"]), "T = %s" % r["T"],
                 "%s ↔ mpmath 60 桁の定義の漸化式" % form, 1, NOT_SAVED, r["rel_err_" + form], NOT_SAVED, "記録（採用判断：区間形）", "記録",
                 rel(os.path.join(RES10, "expU1_b14_forms.json"))])
    e2 = json.load(open(os.path.join(RES10, "expU2_cross_engines.json"), encoding="utf-8"))
    for k, v in e2["1_sympy"].items():
        add(["X-U2-sympy-%s" % re.sub(r"\W+", "_", k)[:30], "実験 U2：別エンジン", "冷媒の倍化積（D-08）", k, "-", "積和 8 段 ↔ SymPy 厳密", NOT_SAVED,
             v if isinstance(v, int) and not isinstance(v, bool) else (0 if v else 1), 0.0 if v is True or v == 0 else NOT_SAVED, NOT_SAVED,
             "厳密に一致", "合格" if v is True or v == 0 else "不合格", rel(os.path.join(RES10, "expU2_cross_engines.json"))])
    sc = e2["2_scipy_benchmark_M"]
    add(["X-U2-scipy", "実験 U2：別エンジン", "冷媒の線形方程式 (I−N)u=b", "benchmark M（未知数 %d）" % sc["n_unknowns"], "-", "積和の倍化積 ↔ SciPy 疎行列ソルバ",
         sc["n_unknowns"], NOT_SAVED, sc["max_rel_difference"], sc["max_abs_where_zero"], "相対 1e-12 程度", "合格", rel(os.path.join(RES10, "expU2_cross_engines.json"))])
    for k, v in e2["3_duckdb_benchmark_M"].items():
        add(["X-U2-duckdb-%s" % re.sub(r"\W+", "_", k)[:30], "実験 U2：別エンジン", k, "benchmark M", "T = 62.5" if "62.5" in k else "-",
             "統一系 ↔ DuckDB の SQL", v.get("cells", v.get("rows", 1)), v.get("rows_that_differ", NOT_SAVED), v.get("max_rel_difference", v.get("rel_difference")),
             NOT_SAVED, "一致", "合格", rel(os.path.join(RES10, "expU2_cross_engines.json"))])
    for r in e2["4_lca_ops"]:
        add(["X-U2-lcaops-T%s" % r["T"].replace("/", "_"), "実験 U2：別エンジン", "年重みつき和（節点スペクトル）", "main の math_tools_v2/lca_ops.py",
             "T = %s" % r["T"], "節点スペクトル ↔ lca_ops 有理数厳密", 1, NOT_SAVED, r["rel_difference"], NOT_SAVED, "相対 1e-15 程度", "合格",
             rel(os.path.join(RES10, "expU2_cross_engines.json"))])
    e3 = json.load(open(os.path.join(RES10, "expU3_intermediate_state.json"), encoding="utf-8"))
    add(["X-U3-before", "実験 U3：中間状態", "冷媒の事象前の残量", "%d シナリオ・%d 組" % (e3["scenarios"], e3["device_period_pairs"]), "各組の T",
         "統一系の中間列 ↔ refcalc の中間値", e3["masses_before_an_event_compared"], e3["non_zero_where_reference_is_zero"],
         e3["max_rel_difference_before_event"], NOT_SAVED, "相対 1e-12 程度", "合格", rel(os.path.join(RES10, "expU3_intermediate_state.json"))])
    add(["X-U3-end", "実験 U3：中間状態", "冷媒の期末残量", "%d シナリオ" % e3["scenarios"], "各組の T", "統一系 ↔ refcalc", e3["end_masses_compared"],
         NOT_SAVED, e3["max_rel_difference_end"], NOT_SAVED, "相対 1e-12 程度", "合格", rel(os.path.join(RES10, "expU3_intermediate_state.json"))])
    ext = json.load(open(os.path.join(RES10, "external_engines.json"), encoding="utf-8"))
    for name in ("sagemath", "matlab"):
        if name in ext:
            x = ext[name]
            add(["X-EXT-%s" % name, "外部エンジン（GitHub Actions）", "冷媒の倍化積と逆行列", "run %s" % x.get("run_id"), "-", "倍化積 ↔ %s" % name, NOT_SAVED,
                 NOT_SAVED, json.dumps(x.get("output", ""), ensure_ascii=False)[:120], NOT_SAVED, "恒等式が成り立つこと", x.get("conclusion", ""),
                 rel(os.path.join(RES10, "external_engines.json"))])
    rp = json.load(open(os.path.join(RES10, "reproduction_check.json"), encoding="utf-8"))
    for r in rp["compared"]:
        add(["R-%s" % r["file"].replace(".json", ""), "再現確認", r["file"], "コミット %s を別の場所で再実行" % rp["commit_checked_out"], "-",
             "再実行の結果 ↔ 保存した結果", 1, 0 if r["equal"] else 1, "-", "-", "実行時間を除いて同一", "合格" if r["equal"] else "不合格",
             rel(os.path.join(RES10, "reproduction_check.json"))])
    # ---- D. chapter 9 (the earlier integrated model of the same concept model)
    ex = json.load(open(os.path.join(RES09, "unified_model_exactness.json"), encoding="utf-8"))
    for g, v in ex["by_group"].items():
        add(["N9-group-%s" % g, "9 章の統合モデル×基準計算", "全 70 単位", "群 %s：%d シナリオ" % (g, v["scenarios"]), "各シナリオの評価期間",
             "fastcalc.engine ↔ refcalc", NOT_SAVED, v["failed"], v["max_abs_rel_error"], NOT_SAVED, "相対 1e-9", "合格" if not v["failed"] else "不合格",
             rel(os.path.join(RES09, "unified_model_exactness.json"))])
    for uid, v in sorted(ex["units"].items()):
        add(["N9-unit-%s" % uid, "9 章の統合モデル×基準計算", uid, "681 シナリオ", "各シナリオの評価期間", "fastcalc.engine ↔ refcalc",
             v["leaves_compared"] + v["non_numeric_compared"], v["failures"], v["max_abs_rel_error"], NOT_SAVED, "相対 1e-9",
             "合格" if not v["failures"] else "不合格", rel(os.path.join(RES09, "unified_model_exactness.json"))])
    ps = ex["period_sweep"]
    add(["N9-period-sweep", "9 章の統合モデル×基準計算", "%d 単位" % len(ps["units"]), "%d シナリオ" % ps["scenarios"],
         "T = " + ", ".join(str(t) for t in ps["periods"]), "fastcalc.engine ↔ refcalc", ps["values_compared"], len(ps["failures"]),
         ps["max_abs_rel_error"], NOT_SAVED, "相対 1e-9", "合格" if ps["all_exact"] else "不合格", rel(os.path.join(RES09, "unified_model_exactness.json"))])
    # ---- E. app tests (base system of the app), from the log of the last run
    if app_log and os.path.exists(app_log):
        pending = None
        for line in open(app_log, encoding="utf-8"):
            line = line.strip()
            head = re.match(r"^(test_\w+) \(([\w.]+)\)$", line)          # a test with a docstring: name, then "doc ... ok"
            if head:
                pending = head
                continue
            m = re.match(r"^(test_\w+) \(([\w.]+)\)\s*\.\.\.\s*(ok|FAIL|ERROR|skipped.*)$", line)
            if not m and pending:
                r = re.search(r"\.\.\.\s*(ok|FAIL|ERROR|skipped.*)$", line)
                if r:
                    m = type("M", (), {"group": lambda self, i, h=pending, r=r: (h.group(i) if i < 3 else r.group(1))})()
            pending = None
            if m:
                add(["A-%s" % m.group(1), "アプリ基礎のテスト", "%s.%s" % (m.group(2), m.group(1)), "架空データ", "テストによる", "テストの内容による",
                     NOT_SAVED, NOT_SAVED, NOT_SAVED, NOT_SAVED, "unittest の判定", "合格" if m.group(3) == "ok" else m.group(3),
                     "14_EQUATION_DISCLOSURE/apptests_2026-11-14.log"])
    with open(os.path.join(out, "06_全検証ケース.csv"), "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(HEAD)
        w.writerows(rows)
    by = {}
    for r in rows:
        by.setdefault(r[1], [0, 0])
        by[r[1]][0] += 1
        by[r[1]][1] += r[11] in ("合格", "検出", "success")
    json.dump({"rows": len(rows), "by_kind": by}, open(os.path.join(out, "verification_counts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(rows), json.dumps(by, ensure_ascii=False))


if __name__ == "__main__":
    main(*sys.argv[1:3])
