"""Figures of stage 1 (static SVG + the plotted numbers as CSV next to each figure).

  F1-1  C(T), the realised part M([0, T]) and the end terms Z(T) of one scenario (TH-4), T in (0, H]
  F1-2  Fourier partial sums: maximum error relative to max|C| versus the number of terms (median and maximum over
        the scenarios, results/stage1_summary.json), log-log
Usage (from this folder): python3 -B figures1.py
"""
import csv
import json
import os
import sys
from fractions import Fraction

sys.dont_write_bytecode = True
import canon                                   # noqa: E402
import timechar as tc                          # noqa: E402
import svgplot as sp                           # noqa: E402
from checks import sets_unified                # noqa: E402
from tstudy import baseline                    # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "..", "figures")


def f1():
    from synth import population
    label, scn, periods = sets_unified.build(["dev_design"])["dev_design"][0]
    can = canon.build(canon.make_system(scn, population.BASELINES))
    kf = tc.KF(can)
    masses, dens, Zt = tc.realtime(can)
    rt = tc.RT(masses, dens)
    Zkf = tc.KF(canon.Canon(H=can.H, terms=Zt))
    Ts = [k / 20 for k in range(1, 20 * 40 + 1)]               # T in (0, 40]: the jumps at the events are visible
    C = [float(kf(T)) / 1e6 for T in Ts]
    Mv = [float(rt.M(Fraction(T))) / 1e6 for T in Ts]
    Zv = [float(Zkf(T)) / 1e6 for T in Ts]
    ch = sp.Chart(title="C(T) と実時間の分解 C(T) = M([0,T]) + Z(T)、T ≤ 40（dev_design の 1 件目）", xlabel="評価期間 T（年）", ylabel="t-CO2e（千トン）")
    ch.line(Ts, C, "C(T)")
    ch.line(Ts, Mv, "M([0,T]) 実現した排出")
    ch.line(Ts, Zv, "Z(T) 終わりの項")
    ch.render(os.path.join(FIG, "F1-1_C_and_realtime_decomposition.svg"),
              note="独立概念モデル・架空データ。0.05 年刻みで正準形を厳密に評価（1e6 kgCO2e 単位）。跳びは更新・交換の時刻。数値は同名の CSV。")
    with open(os.path.join(FIG, "F1-1_C_and_realtime_decomposition.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(("T", "C_kgCO2e", "M_0_T_kgCO2e", "Z_T_kgCO2e"))
        for T, a, b, c in zip(Ts, C, Mv, Zv):
            w.writerow((T, a * 1e6, b * 1e6, c * 1e6))
    return label


def f2():
    s = json.load(open(os.path.join(HERE, "..", "results", "stage1_summary.json")))
    fo = s["fourier_partial_sums"]
    Ns = sorted(int(k) for k in fo)
    med = [fo[str(n)]["max_rel_all_median"] for n in Ns]
    mx = [fo[str(n)]["max_rel_all_max"] for n in Ns]
    ch = sp.Chart(w=640, h=380, title="フーリエ級数の部分和の最大誤差（max|C| に対する相対）", xlabel="項の数 N", ylabel="相対誤差", logx=True, logy=True)
    ch.line(Ns, med, "中央値")
    ch.line(Ns, mx, "最大")
    ch.render(os.path.join(FIG, "F1-2_fourier_partial_sum_error.svg"), note="全シナリオの最大誤差（T∈[0.37, H−0.37] の 997 点）。数値は同名の CSV。")
    with open(os.path.join(FIG, "F1-2_fourier_partial_sum_error.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(("N", "median_max_rel_error", "max_max_rel_error"))
        for n, a, b in zip(Ns, med, mx):
            w.writerow((n, a, b))


if __name__ == "__main__":
    baseline.assert_frozen()
    baseline.load()
    os.makedirs(FIG, exist_ok=True)
    print(f1())
    f2()
