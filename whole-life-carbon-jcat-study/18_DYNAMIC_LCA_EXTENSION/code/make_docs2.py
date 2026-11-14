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


def fmt_slope(v, zero):
    if v is None:
        return "係数が 0（%d 件）" % zero if zero else "—"
    return "%.2f" % v + ("（係数が 0：%d 件）" % zero if zero else "")


def write08():
    """08: the stage-1 time analysis applied to each process function (results/proc_time.json from proc_time.py)."""
    pt_path = os.path.join(RES, "proc_time.json")
    if not os.path.exists(pt_path):
        return
    d = json.load(open(pt_path))
    L = ["# 08 工程ごとの時間特性（第 1 段階の解析を各工程関数に適用）", "",
         "指示書の第 2 段階 9 項（各 $e_i(t)$ の厳密な関数形・節点・周期・不連続性・微分と積分・フーリエ・ラプラス・複素指数・モード）への対応。"
         "`code/proc_time.py` の結果（`results/proc_time.json`）を `code/make_docs2.py` が書き出した。標本：%d シナリオ（dev_design, dev_edge, rep_evaluation, rep_boundary, rep_constructed の各集合の先頭 10 件まで）。独立概念モデル・架空データ。" % d["n_scenarios"], "",
         "## 1. 厳密な関数形（すべての工程に共通）", "",
         "各工程の実時間関数は符号付きの測度で、",
         "",
         "$$ e_i(t) = \\sum_j m_{ij}\\,\\delta(t - t_{ij}) + \\rho_i(t),\\qquad E_i(t) = e_i([0,t]) = \\sum_{t_{ij}\\le t} m_{ij} + \\int_0^t \\rho_i, $$",
         "",
         "原子の位置 $t_{ij}$ は $t=0$（A 段階）と事象の切り替え点 $\\mathrm{sw}(\\tau)$、$\\rho_i$ は年の境と切り替え点で区切られた区分的に一定の率（02 の 3 節）。終わりの項（P13〜P17 と P17 の冷媒の期末残存量）は $t=T$ に置かれ、実時間の関数には入らない。したがって：",
         "",
         "- **節点と不連続**：累積 $E_i$ は原子の位置で跳び（跳びの大きさ $m_{ij}$）、率の区切りで傾きが変わる（折れ点）。$e_i$ 自身は超関数（$\\delta$ を含む）。",
         "- **微分・積分**：$E_i' = e_i$（超関数の意味）、$\\int_0^t E_i = \\sum_{t_{ij}\\le t} m_{ij}(t - t_{ij}) + \\iint\\rho_i$（区分的に二次）。",
         "- **ラプラス変換・複素指数**：$\\mathcal{L}[e_i](s) = \\sum_j m_{ij}e^{-st_{ij}} + \\sum_b d_b\\,(e^{-sb} - e^{-sH})/s$（$d_b$ は区切り $b$ での率の変化）。指数多項式で、節点＝指数（第 17 章 TH-7 と同じ）。",
         "- **フーリエ係数**（$[0,H]$）：原子は $|c_n|$ が減衰しない（測度の係数）。率の跳びは $O(1/n)$。累積 $E_i$ は跳びがあれば $O(1/n)$、連続なら $O(1/n^2)$。したがって $e_i$ のフーリエ級数は点ごとに収束せず、表現には使えない（第 17 章 TH-8 の結論は累積 $E_i$ について成り立つ）。",
         "", "## 2. 工程ごとの測定", "",
         "| 族 | 名前 | 現れたシナリオ | 原子の数（中央値・最大） | 負の原子（合計） | 率の区切り（中央値） | $e_i$ の係数の減衰の指数（中央値） | 累積 $E_i$ の減衰の指数（中央値） | ラプラス：閉じた形と数値積分の最大相対差 | 年ごとの量の最小の線形漸化式の次数（中央値。列の長さ 130 の半分 65 を超える次数は一意でない） |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for p, v in d["families"].items():
        if not v["present"]:
            L.append("| %s | %s | 0（実現分なし。終わりの項だけ） | — | — | — | — | — | — | — |" % (p, v["name"]))
            continue
        L.append("| %s | %s | %d | %s・%s | %d | %s | %s | %s | %s | %s |" % (p, v["name"], v["present"], v["atoms_median"], v["atoms_max"], v["negative_atoms_total"], v["rate_breaks_median"],
                 fmt_slope(v["decay_e_median"], v["decay_e_zero"]), fmt_slope(v["decay_E_median"], v["decay_E_zero"]), e(v["laplace_rel_max"]), v["recurrence_order_median"]))
    L += ["", "- 減衰の指数：$n$ = 1〜512 の係数を 2 進の区間ごとの最大で包み、$\\log|c_n|$ を $\\log n$ に当てはめた傾き（$n\\ge4$）。予言は、原子あり → 0（減衰しない）、率の跳び → −1、累積で跳びあり → −1。正の値は、減衰しない係数の包絡が区間を広げると少し増えることによる。「係数が 0」は、その関数が $[0,H]$ で定数（周期の延長で連続）なので $n\\ne0$ の係数が丸めの大きさしかない場合。",
          "- ラプラスの照合は、閉じた形のコードと数値積分の整合の確認（同じ測度の別の計算）で、独立の証明ではない。", "",
          "## 3. 周期（事象の族の実体ごと）", "",
          "| 族 | 実体：等差（$\\tau_n = \\mathrm{fl}(n\\tau_1)$）／等差でない（明示の一覧）／事象が 1 つ以下 | 相異なる周期の数 | 多い周期（年：実体の数） |", "|---|---|---|---|"]
    for p in ("P06", "P08", "P09", "P10"):
        v = d["families"][p]
        ins = v["instances"]
        L.append("| %s %s | %d／%d／%d | %d | %s |" % (p, v["name"], ins.get("lattice", 0), ins.get("not_lattice", 0), ins.get("single_or_none", 0), v["n_distinct_periods"],
                 "、".join("%s：%d" % (k, n) for k, n in list(v["periods_top"].items())[:6]) or "—"))
    L += ["", "P10（大型改修）は建物全体で 1 つの実体（改修周期 $C_{\\mathrm{ren}}$ の格子 $nC_{\\mathrm{ren}}$）。P08 の負の原子は、更新の時刻に置かれる「その年の修繕の取り消し」で、P09 の更新と同じ時刻にある（07 の 3 節：事象の時刻の一致）。", "",
          "## 4. モード的な共通成分", "",
          "年ごとの量の最小の線形漸化式（有理数で厳密、バーレカンプ・マッシー法）の次数の分布（上位）：", ""]
    for p, v in d["families"].items():
        if v["present"]:
            L.append("- %s %s：%s" % (p, v["name"], "、".join("次数 %s が %d 件" % (k, n) for k, n in v["recurrence_order_dist"].items())))
    L += ["", "次数 1 は定数の列（A 段階の 1 年目だけの原子、一定の率）。次数が小さい（10、16、17 など）のは周期的な交換・更新で、特性根は 1 の冪根（第 17 章 TH-9）。最大の 65 は低い次数のモードに載らない列（年次表が表で与えられる流れ、多数の周期の重ね合わせ）。工程の間で共通のモード（同じ特性根）は、同じ周期の事象を持つ P06・P08・P09 の間に現れる（07 の 3 節の時刻の一致と同じ理由）。", "",
          "## 5. 工程ごとの最良の表現", "",
          "| 族 | 表現 | 理由 |", "|---|---|---|",
          "| P01〜P04 | $t=0$ の原子 1 つ（モデルの配置）。拡張では施工期間の分布（05 の変種） | 70 単位は施工の時期を定義しない |",
          "| P05、P07、P11、P12 | 区分的に一定の率（年セル） | 年重み $w_k$ が一次。P05 は二時刻の核（03 の 4 節）、P07 は買電への比例（03 の 2 節） |",
          "| P06、P08、P09、P10 | 原子の列（周期の格子または明示の一覧）＋事象の年の率の補正 | 周期の格子は（周期・振幅・個数）の周期ブロックでも書ける（第 17 章 05 の 3 節） |",
          "| P13〜P17 | $t=T$ の終わりの項（実時間の関数の外） | 70 単位は解体・処理の時期を定義しない。拡張は 05 の変種 X3 |",
          "", "どの工程でも、ラプラス変換（指数多項式）が厳密で、畳み込み（気候影響の応答関数との合成、06）を積に変える。フーリエ級数は表現には使わない。"]
    open(os.path.join(CH, "08_工程ごとの時間特性.md"), "w").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
    write08()
