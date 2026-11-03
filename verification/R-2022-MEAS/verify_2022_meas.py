"""2022年度 実験住宅の実測とシミュレーション（MIN〜MAX帯）の照合（04 実測シミュ比較, 4条件）。

入力: private_data/raw/2022_meas/f<BoxID>_*.txt（Box get_file_content のテキスト。Git 管理外）
出力: results.json / results.md（集計値のみ）【計算結果】
- 実測値は 353.357 個/m³（=1個/2.83 L）の整数倍 → 1分値の生カウント。ポアソン誤差は √n 個。
- シミュレーションは各室の MIN・MAX 2系列（10秒刻み）。実測時刻（60秒刻み）で照合。
- 各測点は別々の試行で測定（F-2022-03）。
"""
import json, math
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "private_data" / "raw" / "2022_meas"
OUT = Path(__file__).parent
FILES = {"1 弱・EP OFF": "f1516299373332_1weakOFF.txt", "2 弱・EP ON": "f1516299517875_2weakON.txt",
         "3 強・EP OFF": "f1516299525075_3strongOFF.txt", "4 強・EP ON": "f1516295349094_4strongON.txt"}
UNIT = 1 / 0.00283  # 個/m³ per count
MEAS = ["LDK", "レターン", "空調室", "ダクト", "階間", "洋室中"]
SIMNAME = {"ダクト": "建築ダクト"}
T_GEN = 600


def fnum(x):
    try:
        return float(x)
    except ValueError:
        return None


def parse(path):
    L = path.read_text(encoding="utf-8").split("\n")
    head = L[3].split("\t")
    grp = L[2].split("\t") + [""] * 100
    # 実測列: index 6..11, 時間5 / sim: 時間13, MIN 14.., MAX 28..
    mincol = {head[i].strip(): i for i in range(14, 28)}
    maxcol = {head[i].strip(): i for i in range(28, 42)}
    meas, sim = {}, {}
    for l in L[4:250]:
        c = l.split("\t") + [""] * 60
        t = fnum(c[5])
        if t is not None:
            meas[t] = {n: fnum(c[6 + k]) for k, n in enumerate(MEAS)}
        ts = fnum(c[13])
        if ts is not None:
            sim[ts] = {"min": {n: fnum(c[i]) for n, i in mincol.items()}, "max": {n: fnum(c[i]) for n, i in maxcol.items()}}
    return meas, sim


def analyse(meas, sim):
    res = {}
    for n in MEAS:
        sn = SIMNAME.get(n, n)
        pts = [(t, v[n]) for t, v in sorted(meas.items()) if v[n] is not None and t in sim]
        if not pts:
            continue
        inband = inband_tol = 0
        post = [(t, v) for t, v in pts if t >= T_GEN]
        pre = [v for t, v in pts if t < T_GEN]
        ratios = []
        for t, v in pts:
            lo, hi = sim[t]["min"][sn], sim[t]["max"][sn]
            if lo is None or hi is None:
                continue
            lo, hi = min(lo, hi), max(lo, hi)
            inband += lo <= v <= hi
            tol = UNIT * max(1.0, math.sqrt(v / UNIT))  # ±1σ（最低1カウント）
            inband_tol += (lo - tol) <= v <= (hi + tol)
            if t >= T_GEN and hi > 0:
                ratios.append(v / (0.5 * (lo + hi)))
        tp_m, vp_m = max(post, key=lambda x: x[1])
        sim_post = [(t, sim[t]["max"][sn]) for t in sorted(sim) if t >= T_GEN and sim[t]["max"][sn] is not None]
        tp_s, vp_s = max(sim_post, key=lambda x: x[1])
        counts = [v / UNIT for t, v in post]
        res[n] = {
            "n_points": len(pts), "frac_in_band": round(inband / len(pts), 3), "frac_in_band_poisson": round(inband_tol / len(pts), 3),
            "meas_pre_mean": round(sum(pre) / len(pre), 0) if pre else None,
            "meas_peak": round(vp_m, 0), "meas_peak_t_s": tp_m, "sim_max_peak": round(vp_s, 0), "sim_peak_t_s": tp_s,
            "peak_ratio_meas_over_simmax": round(vp_m / vp_s, 2) if vp_s else None,
            "median_ratio_meas_over_simmid_post": round(sorted(ratios)[len(ratios) // 2], 2) if ratios else None,
            "integer_count_check": all(abs(v / UNIT - round(v / UNIT)) < 1e-6 for t, v in pts),
            "post_mean_count_per_sample": round(sum(counts) / len(counts), 2),
        }
    return res


def main():
    allres = {}
    for cond, fn in FILES.items():
        meas, sim = parse(RAW / fn)
        allres[cond] = {"n_meas_times": len(meas), "n_sim_times": len(sim), "rooms": analyse(meas, sim)}
    (OUT / "results.json").write_text(json.dumps(allres, ensure_ascii=False, indent=1), encoding="utf-8")
    L = ["# 2022年度 実測 vs シミュレーション帯の照合（自動生成: verify_2022_meas.py）", "", "区分: 【計算結果】。帯内率=実測点がシミュレーションの MIN〜MAX に入る割合（括弧内はポアソン±1σを許容）。ピーク比=実測ピーク/シミュMAXピーク。", "",
         "| 条件 | 測点 | 点数 | 帯内率 | 帯内率(±1σ) | 実測ピーク[個/m³] (時刻s) | シミュMAXピーク (時刻s) | ピーク比 | 発生後の実測/帯中央 中央値 | 発生後の平均カウント/2.83L |", "|---|---|---|---|---|---|---|---|---|---|"]
    for cond, r in allres.items():
        for n, x in r["rooms"].items():
            L.append(f"| {cond} | {n} | {x['n_points']} | {x['frac_in_band']} | {x['frac_in_band_poisson']} | {x['meas_peak']:.0f} ({x['meas_peak_t_s']:.0f}) | {x['sim_max_peak']:.0f} ({x['sim_peak_t_s']:.0f}) | {x['peak_ratio_meas_over_simmax']} | {x['median_ratio_meas_over_simmid_post']} | {x['post_mean_count_per_sample']} |")
    ok = all(x["integer_count_check"] for r in allres.values() for x in r["rooms"].values())
    L += ["", f"実測値が 353.357 個/m³ の整数倍（1分値の生カウント×1/2.83 L）: {'全点で成立' if ok else '不成立あり'}"]
    (OUT / "results.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
