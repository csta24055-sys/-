"""Stage 4: write 02_結果.md, the README headline and the figure from results/stage4_summary.json (no hand-typed numbers).
Usage (from this folder): python3 -B make_docs4.py"""
import csv
import json
import math
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "17_WHOLE_BUILDING_TIME_THEORY", "code"))
import svgplot as sp                                   # noqa: E402

ROOT = os.path.join(HERE, "..")
NAMES = {"N": "通常", "B": "境界重視", "G": "桁（10^±6 倍）", "E": "同時事象", "S": "特別な設定", "D": "欠損・異常（定義域の外）"}
NC_TXT = {"NC1": "事象を τ ≤ T で数える", "NC2": "密度の振幅 aH を率として使う", "NC3": "B6 から常に B2-01 を引く", "NC4": "事象の年の補正の符号を逆",
          "NC5": "B1-04 を跳び形で計算", "NC6": "年セルを 1 年ずらす", "NC7": "64 項のフーリエ部分和を値に使う", "NC8": "終わりの項 Z(T) を落とす"}


def e(x):
    return "—" if x is None else ("%.1e" % x if (x != 0 and (abs(x) < 1e-3 or abs(x) >= 1e4)) else "%.4g" % x)


def main():
    s = json.load(open(os.path.join(ROOT, "results", "stage4_summary.json")))
    t = s["total"]
    L = ["# 02 大規模ランダム検証の結果（第 4 段階）", "",
         "`code/run4.py` の結果（`results/chunks/`）を `code/agg4.py` が集計し（`results/stage4_summary.json`）、`code/make_docs4.py` が書き出した。数値は手で書いていない。独立概念モデル・架空データ。", ""]
    rand = [k for k in s["strata"] if not k.startswith("R:")]
    nscn = sum(s["strata"][k]["scenarios"] for k in rand)
    npairs = sum(s["strata"][k].get("pairs", 0) for k in rand)
    L.append("## 1. 全体\n")
    L.append("| 項目 | 値 |")
    L.append("|---|---|")
    L.append("| 無作為のシナリオ（宣言した分布、層 N・B・G・E・S・D） | %d |" % nscn)
    L.append("| ケース（シナリオ × 評価期間） | %d |" % npairs)
    L.append("| 定義域の内側のケース（D 層を除く） | %d |" % t["in_domain_pairs"])
    L.append("| うち失敗（V1〜V5 のどれかが不一致） | **%d** |" % t["in_domain_failures"])
    L.append("| 失敗のうち、切り替え点が年セルの終わりを越える事象の直後の帯 $(K,\\mathrm{sw}(\\tau)]$ にあるもの／ないもの | %d／%d |" % (t.get("in_domain_failures_in_band", 0), t.get("in_domain_failures_outside_band", 0)))
    L.append("| 95％ 片側上限（ケースあたりの失敗の確率、宣言した分布） | %s |" % e(t["upper95_failure_probability_in_domain"]))
    L.append("| シナリオ単位：定義域の内側のケースを持つシナリオ／失敗したシナリオ／95％ 上限 | %d／%d／%s |" % (t["scenarios_with_in_domain_pairs"], t["scenarios_failing"], e(t["upper95_failure_probability_per_scenario"])))
    L.append("| 照合した段階の値・単位の値 | %d・%d |" % (t.get("stage_values", 0), t.get("unit_values", 0)))
    L.append("| SUM-03 の基準計算との相対差：99％点・最大（D 層を含む比べた全ケース） | %s・%s |" % (e(t.get("rel_p99")), e(t.get("rel_max"))))
    L.append("| 共有量 P07 ＝ $\\rho_{\\mathrm{B2}}\\times$ 買電 の不一致（年セル） | %d |" % t.get("P07_rho_bad", 0))
    L.append("| シナリオの準備・評価の失敗（例外） | %d |" % t.get("scenario_errors", 0))
    L.append("")
    L.append("## 2. 層ごと\n")
    L.append("| 層 | シナリオ | ケース | 比べたケース | 失敗 | V1 | V2 | V3 | V4 | V5（照合したケース） | 相対差 中央値 | 99％点 | 最大 | 95％ 上限 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for k in ["N", "B", "G", "E", "S", "D"] + sorted(x for x in s["strata"] if x.startswith("R:")):
        if k not in s["strata"]:
            continue
        v = s["strata"][k]
        L.append("| %s | %d | %d | %d | %d | %d | %d | %d | %d | %d（%d） | %s | %s | %s | %s |" % (
            (k + " " + NAMES.get(k, "")) if k in NAMES else k, v["scenarios"], v.get("pairs", 0), v.get("checked", 0), v.get("fail", 0), v.get("v1_fail", 0), v.get("v2_fail", 0),
            v.get("v3_fail", 0), v.get("v4_fail", 0), v.get("v5_fail", 0), v.get("v5_checked", 0), e(v.get("rel_median")), e(v.get("rel_p99")), e(v.get("rel_max")),
            e(v.get("upper95_failure_probability"))))
    L.append("")
    L.append("- D 層は基準計算の定義域の外（欠損・異常値）で、定義域の絞り込みなしで比べた（第 11 章の欠陥集合と同じ扱い）。上限の計算からは除いた。")
    L.append("- `R:` の行は継承した第 11 章の 10 集合（1,293 組）を同じ照合で再実行したもの。`:outside` は定義域の外の集合。")
    L.append("")
    L.append("## 3. 負の対照（意図的に誤った式）\n")
    L.append("| 記号 | 誤り | 適用できるケース | 検出 | 検出率 |")
    L.append("|---|---|---|---|---|")
    for k, v in t["nc"].items():
        L.append("| %s | %s | %d | %d | %s |" % (k, NC_TXT[k], v["applicable"], v["detected"], ("%.4f" % (v["detected"] / v["applicable"])) if v["applicable"] else "—"))
    L.append("")
    L.append("- 「適用できる」＝誤った式の値が正しい値と相対 1e-12 を超えて異なるケース。検出 ＝ その値が基準計算と相対 1e-9 で一致しない。")
    L.append("- 適用できるのに検出されないケースは、誤りの影響が 1e-9 より小さいケース（比較の許容差の中に隠れる）。NC5 は、跳び形と区間形がほとんどのケースで 1e-12 以内で一致するため、適用できるケースがほとんどない（第 11 章 D-09 の桁落ちは強く減衰する冷媒の特別な場合にだけ起きる）。")
    L.append("")
    L.append("## 4. 近似と変換（記録。合格には数えない）\n")
    L.append("| 項目 | 値 |")
    L.append("|---|---|")
    L.append("| ラプラス変換：閉じた形と区分ごとのガウス積分の最大相対差（$s$ = 0.05、0.5） | %s |" % e(s.get("laplace_max_rel")))
    L.append("| フーリエ係数の共役対称（浮動小数で自動的に成り立つので証拠にしない） | %s |" % e(s.get("fourier_conjugate_max")))
    for b in ("T<1", "1<=T<10", "T>=10"):
        v = s.get("fourier64_rel", {}).get(b)
        if v:
            L.append("| 64 項のフーリエ部分和の相対誤差（%s）：件数・中央値・95％点・最大 | %d・%s・%s・%s |" % (b, v["n"], e(v["median"]), e(v["p95"]), e(v["max"])))
    L.append("")
    L.append("フーリエ部分和は近似であり、$T$ が小さいほど（周期の延長での $C(0^+)$ と $C(H)$ の食い違い、ギブス）誤差が大きい。第 17 章 TH-8 の結論（表現には使わない）を大量のケースで確かめた。")
    L.append("")
    L.append("## 5. 読み方（主張の範囲）\n")
    L.append("- 失敗 0 件は、**宣言した抽出分布で**ケースあたりの失敗の確率が上の上限以下であることを、95％ の信頼で言う。全入力についての数学的な一致の主張ではない。")
    L.append("- 同じシナリオの 5 つのケースは独立でないので、シナリオ単位の上限（1 節）がより保守的な読み方になる。")
    L.append("- 抽出分布は、切り替え点が年セルの終わりを越える事象の直後の帯 $(K,\\mathrm{sw}(\\tau)]$ に確率を置かない（01 の 1 節）。第 17 章の帯の中の不一致は、この検証の対象外で、別の検査（第 17 章 07 の 6 節）で記録した。")
    open(os.path.join(ROOT, "02_結果.md"), "w").write("\n".join(L) + "\n")
    # figure: relative difference distribution is not stored per pair in the summary; plot the per-stratum quantiles
    ks = [k for k in ["N", "B", "G", "E", "S", "D"] if k in s["strata"] and s["strata"][k].get("rel_max")]
    os.makedirs(os.path.join(ROOT, "figures"), exist_ok=True)
    rows = []
    ch = sp.Chart(w=720, h=380, title="SUM-03 の基準計算との相対差（層ごとの中央値・99％点・最大）", xlabel="層（1 N 通常, 2 B 境界, 3 G 桁, 4 E 同時事象, 5 S 特別, 6 D 欠損）", ylabel="相対差", logy=True)
    xs = list(range(1, len(ks) + 1))
    for q, lab in (("rel_median", "中央値"), ("rel_p99", "99％点"), ("rel_max", "最大")):
        ys = [max(s["strata"][k][q] or 1e-17, 1e-17) for k in ks]
        ch.line(xs, ys, lab)
        rows.append([lab] + ys)
    ch.render(os.path.join(ROOT, "figures", "F4-1_relative_difference_by_stratum.svg"), note="相対差 0 は 1e-17 として描いた。比較の許容差は 1e-9。数値は同名の CSV。")
    with open(os.path.join(ROOT, "figures", "F4-1_relative_difference_by_stratum.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["quantile"] + ks); w.writerows(rows)
    print("written")


if __name__ == "__main__":
    main()
