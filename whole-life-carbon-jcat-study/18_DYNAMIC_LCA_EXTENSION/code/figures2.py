"""Figure of stage 2: the real-time annual amounts of the process functions of one scenario, grouped (static SVG + CSV).
Usage (from this folder): python3 -B figures2.py"""
import csv
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "17_WHOLE_BUILDING_TIME_THEORY", "code"))
import processes as pr                                 # noqa: E402
import canon                                           # noqa: E402
import svgplot as sp                                   # noqa: E402
from checks import sets_unified                        # noqa: E402
from tstudy import baseline                            # noqa: E402

GROUPS = [("運用（P05・P07・P11・P12）", ("P05", "P07", "P11", "P12")), ("修繕（P08）", ("P08",)), ("更新・交換・改修（P06・P09・P10）", ("P06", "P09", "P10"))]


def main():
    baseline.assert_frozen()
    baseline.load()
    from synth import population
    label, scn, periods = sets_unified.build(["dev_design"])["dev_design"][0]
    sysm = canon.make_system(scn, population.BASELINES)
    can = canon.build(sysm)
    fam, _ = pr.decompose(can, sysm)
    Y = 60
    series = []
    for name, ps in GROUPS:
        tot = [0.0] * Y
        for p in ps:
            for i, v in enumerate(pr.annual_series(fam[p], Y)):
                tot[i] += float(v) / 1e3
        series.append(tot)
    init = sum(float(fam[p].emitted_before(0.5)) for p in ("P01", "P02", "P03", "P04")) / 1e3
    term = sum(float(fam[p].terminal_at(60.0)) for p in ("P13", "P14", "P15", "P16", "P17")) / 1e3
    years = list(range(1, Y + 1))
    ch = sp.Chart(w=820, h=420, title="工程関数の年ごとの実現量（dev_design の 1 件目、年 1〜60）", xlabel="年 y（実時間の区間 (y−1, y]）", ylabel="t-CO2e／年")
    ch.mr = 40
    ch.bars(years, series, [g[0] for g in GROUPS], width=0.8)
    ch.render(os.path.join(HERE, "..", "figures", "F2-1_process_annual_amounts.svg"),
              note="t=0 の A 段階 %.0f t と、T=60 の終わりの項 %.0f t は省いた（目盛りを保つため）。修繕（P08）は更新の年の取り消し（負の原子）を含み、その年の修繕が少なく見える。数値は同名の CSV。" % (init, term))
    with open(os.path.join(HERE, "..", "figures", "F2-1_process_annual_amounts.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["year"] + [g[0] for g in GROUPS])
        for i, y in enumerate(years):
            w.writerow([y] + [s[i] * 1e3 for s in series])
        w.writerow(["t=0 (A stages, kgCO2e)", init * 1e3])
        w.writerow(["t=T=60 end terms (kgCO2e)", term * 1e3])
    print(label, init, term)


if __name__ == "__main__":
    main()
