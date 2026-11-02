"""多室モデルの実測検証（2020年度 実験住宅・線香2本・LDK発生）

入力: private_data/raw/S-2020-06_urawa_dust.txt（Box 1516270811625『20201210浦和実測 粉塵計.xlsx』のテキスト抽出, 非コミット）
      シート『梗概作成用』: 各室の粉塵計1分値（ファン弱3回・強3回とその平均, t=-600〜2940 s）
モデル: backend/aqros/models.py の multizone_simulate と SHASE2021（その40）の回路網
出力: knowledge/validation_multizone.json（評価指標のみ。実測時系列は含まない）

使い方:  .venv/bin/python scripts/validate_multizone.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from aqros import models as M  # noqa: E402

RAW = ROOT / "private_data" / "raw" / "S-2020-06_urawa_dust.txt"
ROOM_MAP = {"玄関": "1階廊下・玄関", "洗面所": "洗面所", "レターン": "2階廊下・レターン", "洋室中": "洋室(中)", "洋室大": "洋室(大)"}


def load_measured():
    L = RAW.read_text(encoding="utf-8").split("\n")
    i0 = next(i for i, l in enumerate(L) if l.startswith("梗概作成用"))
    names = L[i0 + 1].split("\t")
    room_cols = [(j, n) for j, n in enumerate(names) if n.strip()]
    data = {}
    for j, n in room_cols:
        t, weak, strong = [], [], []
        for l in L[i0 + 3:]:
            f = l.split("\t")
            if len(f) <= j + 9 or not f[j].strip().lstrip("-").isdigit():
                if t:
                    break
                continue
            try:
                tw, ww, ts, ss = float(f[j]), float(f[j + 4]), float(f[j + 5]), float(f[j + 9])
            except ValueError:
                continue
            t.append(tw); weak.append(ww); strong.append(ss)
        data[n.strip()] = {"t": np.array(t), "弱": np.array(weak), "強": np.array(strong)}
    return data


def simulate(setting, d_rate, k_mg_s=0.0144, burn_s=1020.0):
    v, f = M.shase2021_network(setting)
    r = M.multizone_simulate(v, f, hours=3000 / 3600, c_out=0.0, c0=0.0, sources={"LDK": k_mg_s * 3600},
                             source_hours=(0, burn_s / 3600), beta=M.decay_rate_to_beta(d_rate), record_every_s=60)
    return np.array(r["t_h"]) * 3600, r["series"]


def metrics(meas_t, meas_rise, sim_t, sim):
    m = (meas_t >= 0) & (meas_t <= 2940)
    tt = meas_t[m]
    mv = meas_rise[m]
    sv = np.interp(tt, sim_t, sim)
    rmse = float(np.sqrt(np.mean((sv - mv) ** 2)))
    nrmse = rmse / float(np.max(mv)) if np.max(mv) > 0 else float("nan")
    return {
        "peak_meas": float(np.max(mv)), "peak_sim": float(np.max(sv)),
        "peak_ratio_sim_over_meas": float(np.max(sv) / np.max(mv)) if np.max(mv) > 0 else None,
        "t_peak_meas": float(tt[np.argmax(mv)]), "t_peak_sim": float(tt[np.argmax(sv)]),
        "end_meas": float(mv[-1]), "end_sim": float(sv[-1]),
        "rmse": rmse, "nrmse": nrmse,
    }


def main():
    meas = load_measured()
    out = {"note": "多室モデル（SHASE2021回路網）と2020年度実測（粉塵計, 線香2本LDK発生）の比較【計算結果】。実測の上昇分=各時刻値−発生前10分平均。",
           "source_data": "Box 1516270811625（梗概作成用シート）", "cases": []}
    for setting in ("弱", "強"):
        for d in (0.0, 0.00015, 0.0003):
            sim_t, ser = simulate(setting, d)
            rows = {}
            for jp, zone in ROOM_MAP.items():
                if jp not in meas:
                    continue
                t = meas[jp]["t"]
                y = meas[jp][setting]
                base = float(np.mean(y[t < 0]))
                rows[jp] = {"baseline": base, **metrics(t, y - base, sim_t, np.array(ser[zone]))}
            nr = [r["nrmse"] for r in rows.values()]
            pr = [r["peak_ratio_sim_over_meas"] for r in rows.values() if r["peak_ratio_sim_over_meas"]]
            out["cases"].append({"fan": setting, "D_per_s": d, "beta_per_h": M.decay_rate_to_beta(d),
                                 "mean_nrmse": float(np.mean(nr)), "mean_peak_ratio": float(np.mean(pr)), "rooms": rows})
    best = {}
    for setting in ("弱", "強"):
        c = min((c for c in out["cases"] if c["fan"] == setting), key=lambda c: c["mean_nrmse"])
        best[setting] = {"D_per_s": c["D_per_s"], "mean_nrmse": c["mean_nrmse"], "mean_peak_ratio": c["mean_peak_ratio"]}
    # 連続的なDの最適値（グリッド探索）
    grid = {}
    for setting in ("弱", "強"):
        res = []
        for d in np.linspace(0, 0.0008, 33):
            sim_t, ser = simulate(setting, d)
            nr = []
            for jp, zone in ROOM_MAP.items():
                t = meas[jp]["t"]; y = meas[jp][setting]; base = float(np.mean(y[t < 0]))
                nr.append(metrics(t, y - base, sim_t, np.array(ser[zone]))["nrmse"])
            res.append((float(d), float(np.mean(nr))))
        grid[setting] = {"best_D": min(res, key=lambda x: x[1])[0], "best_nrmse": min(res, key=lambda x: x[1])[1]}
    out["best_of_3"] = best
    out["grid_best"] = grid
    dst = ROOT / "knowledge" / "validation_multizone.json"
    dst.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for c in out["cases"]:
        print(c["fan"], c["D_per_s"], "meanNRMSE=%.2f peakRatio=%.2f" % (c["mean_nrmse"], c["mean_peak_ratio"]),
              {k: (round(v["peak_meas"], 4), round(v["peak_sim"], 4), int(v["t_peak_meas"]), int(v["t_peak_sim"])) for k, v in c["rooms"].items()})
    print("grid", grid)


if __name__ == "__main__":
    main()
