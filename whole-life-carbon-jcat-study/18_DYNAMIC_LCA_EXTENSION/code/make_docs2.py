"""Stage 2: aggregate results/dyn_*.json into results/stage2_summary.json and write 07_検証の結果.md
(numbers are never typed by hand).

Usage (from this folder): python3 -B make_docs2.py
"""
import collections
import glob
import json
import os
import statistics
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
CH = os.path.normpath(os.path.join(HERE, ".."))
RES = os.path.join(CH, "results")
FAM = ["P%02d" % i for i in range(1, 18)]


def q(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, max(0, int(p * len(xs) + 0.999999) - 1))] if xs else None


def main():
    recs = []
    for f in sorted(glob.glob(os.path.join(RES, "dyn_*.json"))):
        recs += json.load(open(f))
    ok = [r for r in recs if "error" not in r]
    s = dict(n_scenarios=len(recs), n_ok=len(ok), errors=[(r["set"], r["label"], r["error"]) for r in recs if "error" in r])
    s["R1_partition_bad"] = sum(r["R1_partition_bad"] for r in ok)
    s["R2_recomposition_bad"] = sum(r["R2_recomposition_bad"] for r in ok)
    s["R1_instances_bad"] = sum(r["R1_instances_vs_family_bad"] for r in ok)
    s["R3_annual_bad"] = sum(r["R3_annual_bad"] for r in ok)
    s["periods_checked"] = sum(r["n_periods"] for r in ok)
    s["instances_total"] = sum(r["n_instances"] for r in ok)
    s["terminal_share_max"] = max((r["terminal_share_max"] for r in ok), default=None)
    s["P07_bad"] = sum(r["relations"]["P07_equals_rho_times_electricity_bad"] for r in ok)
    cov = collections.Counter()
    for r in ok:
        for pid, n in r.get("families_without_full_instance_coverage", {}).items():
            cov[pid] += 1
    s["families_without_instances_in_scenarios"] = dict(cov)
    # families: signs and kinds
    fam = {}
    for pid in FAM:
        rows = [r["families"][pid] for r in ok if pid in r["families"]]
        fam[pid] = dict(name=rows[0]["name"] if rows else "", kind=rows[0]["kind"] if rows else "",
                        scenarios_active=sum(1 for x in rows if x["n_terms"]),
                        negative_masses=sum(x["negative_masses"] for x in rows), negative_densities=sum(x["negative_densities"] for x in rows),
                        negative_net_rate_intervals=sum(x["negative_net_rate_intervals"] for x in rows),
                        negative_net_masses=sum(x["negative_net_masses"] for x in rows),
                        share_at_H_median=statistics.median([x["accounted_at_H"] / tot for x, tot in
                                                             ((x, sum(r2["families"][p]["accounted_at_H"] for p in FAM)) for x, r2 in
                                                              ((r["families"][pid], r) for r in ok)) if tot]) if rows else None)
    s["families"] = fam
    # relations
    co = collections.Counter(); con = collections.Counter()
    for r in ok:
        for k, v in r["relations"]["coincident_event_times"].items():
            co[k] += v
        for k, v in r["relations"]["event_times_per_family"].items():
            con[k] += v
    s["coincident_event_times"] = dict(co)
    s["event_times_per_family"] = dict(con)
    p10 = [x for r in ok for x in r["relations"].get("P10_amount_over_initial_plus_eol", []) if x is not None]
    s["P10_ratio"] = dict(n=len(p10), min=min(p10) if p10 else None, max=max(p10) if p10 else None)
    lti = collections.defaultdict(list)
    for r in ok:
        for k, v in r["relations"]["lti_deconvolution"].items():
            lti[k].append(v["rel_residual"])
    s["lti_residual"] = {k: dict(n=len(v), median=statistics.median(v), min=min(v), max=max(v)) for k, v in lti.items()}
    corr = collections.defaultdict(list)
    for r in ok:
        for k, v in r["relations"]["annual_correlation"].items():
            corr[k].append(v)
    s["annual_correlation_median"] = {k: statistics.median(v) for k, v in corr.items() if len(v) >= 5}
    # extensions
    ext = collections.defaultdict(lambda: collections.defaultdict(list))
    tot_ok = collections.Counter()
    for r in ok:
        for T, d in r["extensions"]["periods"].items():
            for var, x in d["variants"].items():
                tot_ok[var] += bool(x["total_equals_C70"])
                tot_ok[var + "_n"] += 1
                for te, rel in x["weighted_rel_to_M0"].items():
                    if rel is not None:
                        key = "t_end=T" if float(te) == float(T) else ("t_end=100" if float(te) == 100.0 else "t_end=T+100")
                        ext[var][key].append(rel)
    s["variants_total_equal"] = dict(tot_ok)
    s["variants_weighted_rel"] = {v: {k: dict(n=len(x), median=statistics.median(x), min=min(x), max=max(x)) for k, x in d.items()} for v, d in ext.items()}
    term = [d["terminal_at_T"] / d["C70"] for r in ok for T, d in r["extensions"]["periods"].items() if d["C70"]]
    s["terminal_share_at_T"] = dict(median=statistics.median(term) if term else None, max=max(term) if term else None)
    json.dump(s, open(os.path.join(RES, "stage2_summary.json"), "w"), indent=1, ensure_ascii=False)
    write07(s)
    print(json.dumps({k: s[k] for k in ("n_scenarios", "n_ok", "R1_partition_bad", "R2_recomposition_bad", "R1_instances_bad", "R3_annual_bad",
                                        "periods_checked", "P07_bad")}, indent=1))


def e(x, f="%.2e"):
    return "—" if x is None else f % x


def write07(s):
    L = ["# 07 検証の結果（第 2 段階）\n",
         "`code/dynlca.py` の結果（`results/dyn_*.json`）を `code/make_docs2.py` が集計した（`results/stage2_summary.json`）。数値は手で書いていない。独立概念モデル・架空データ。\n",
         "## 1. 工程関数の再構成と整合（厳密：有理数）\n",
         "シナリオ %d 件（失敗 %d 件）、評価期間の標本 %d 点（各シナリオで区切り区間の中点 40 点と年の境）、工程の実体 %d 個。\n"
         % (s["n_ok"], len(s["errors"]), s["periods_checked"], s["instances_total"]),
         "| 照合 | 不一致 |", "|---|---|",
         "| R-1 割り当て：17 族の（実現分＋終わりの項）の和 ＝ 第 17 章の $C(T)$ | %d |" % s["R1_partition_bad"],
         "| R-2 再構成：$\\int_{[0,T]} e_{\\mathrm{total}} + Z(T) = C_{70}(T)$ | %d |" % s["R2_recomposition_bad"],
         "| R-1 実体の和 ＝ 族（実体で全項を覆う族だけ） | %d |" % s["R1_instances_bad"],
         "| R-3 年ごと：族の年の実現量＋終わりの項の変化 ＝ $C(y)-C(y-1)$ | %d |" % s["R3_annual_bad"],
         "| 共有量：P07 の率 ＝ $\\rho_{\\mathrm{B2}}\\times$ 買電排出（年セルごと） | %d |" % s["P07_bad"],
         "",
         "- 実体に分けられない項を持つ族（シナリオ数）：%s。P01〜P04、P07、P11〜P16 は建物全体の集計値、P17 の区間形の年セルの係数は機器の和。" % s["families_without_instances_in_scenarios"],
         "- 終わりの項 $Z(T)$ の $C(T)$ に対する割合：中央値 %s、最大 %s（実現した排出だけでは $C_{70}$ に一致しない分）。" % (e(s["terminal_share_at_T"]["median"]), e(s["terminal_share_at_T"]["max"])),
         "",
         "## 2. 工程ごとの性質\n",
         "| 族 | 名前 | 形 | 現れたシナリオ | 負の原子 | 負の率 | 族でまとめた負の率の区間 | 族でまとめた負の原子 | $C(H)$ に占める割合（中央値） |",
         "|---|---|---|---|---|---|---|---|---|"]
    for pid, d in s["families"].items():
        L.append("| %s | %s | %s | %d | %d | %d | %d | %d | %s |" % (pid, d["name"], d["kind"], d["scenarios_active"], d["negative_masses"], d["negative_densities"],
                                                              d["negative_net_rate_intervals"], d["negative_net_masses"], e(d["share_at_H_median"], "%.3f")))
    L += ["", "## 3. 工程間の関係\n",
          "- 事象の時刻の一致（全シナリオの合計。同じ浮動小数の切り替え点を持つ事象の数）：%s。各族の事象の時刻の数：%s。" % (s["coincident_event_times"], s["event_times_per_family"]),
          "- P10（改修）の量 ÷（A 段階＋C 段階の合計）：%d 件、範囲 %s〜%s（$\\varphi$ に等しい比例関係）。" % (s["P10_ratio"]["n"], e(s["P10_ratio"]["min"], "%.4f"), e(s["P10_ratio"]["max"], "%.4f")),
          "- 年の系列での線形時不変の畳み込み $e_j = h * e_i$（因果的な長さ 12 年の核を最小二乗で当てはめた相対残差。0 なら厳密に成り立つ）：", ""]
    L.append("| 関係 | 件数 | 残差 中央値 | 最小 | 最大 |")
    L.append("|---|---|---|---|---|")
    for k, d in sorted(s["lti_residual"].items()):
        L.append("| %s | %d | %s | %s | %s |" % (k, d["n"], e(d["median"]), e(d["min"]), e(d["max"])))
    use = ("P05", "P06", "P07", "P08", "P09", "P10", "P11", "P12")
    cm = {k: round(v, 3) for k, v in sorted(s["annual_correlation_median"].items()) if k[:3] in use and k[4:] in use}
    L += ["", "- 年の系列の相関（中央値、5 シナリオ以上で定義されるもの。供用中の族 P05〜P12 の間だけ。P01〜P04 は $t=0$ の原子なので 1 年目にしか値がない）：%s" % cm, ""]
    L += ["## 4. 時間配分の仮定（拡張）と非一意性\n",
          "合計の一致（各変種で $\\sum$ 排出 $= C_{70}(T)$、厳密）：%s。\n" % s["variants_total_equal"],
          "時間で重みをつけた気候影響の指標（06）の、モデルの配置 M0 に対する相対差：\n",
          "| 変種 | 終点 | 件数 | 中央値 | 最小 | 最大 |", "|---|---|---|---|---|---|"]
    for v, d in sorted(s["variants_weighted_rel"].items()):
        for k, x in sorted(d.items()):
            L.append("| %s | %s | %d | %s | %s | %s |" % (v, k, x["n"], e(x["median"]), e(x["min"]), e(x["max"])))
    L.append("")
    open(os.path.join(CH, "07_検証の結果.md"), "w").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
