"""2025年度の年間予測（室内 = k × 外気PM2.5, 2024年度そらまめくん1時間値）を原データから再計算する。

入力: private_data/raw/S-2025-17_soramame2024.txt（Box『2024そらまめくん.xlsx』のテキスト抽出, 非コミット）
      private_data/raw/S-2025-16_cumfreq.txt（Box『累積度数曲線 都道府県別.xlsx』）
出力: knowledge/verification_annual_2025.json（集計値のみ）
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "private_data" / "raw"
K = {"条件①": 0.14, "条件②": 0.55, "条件③": 1.00}  # 2025年度最終梗概 表3


def load_sites():
    L = (RAW / "S-2025-17_soramame2024.txt").read_text(encoding="utf-8").split("\n")
    sites, cur = {}, None
    for l in L:
        f = l.split("\t")
        if len(f) == 1 and f[0].strip() and not f[0].startswith("image") and not any(ch in f[0] for ch in "%0123456789"):
            cur = f[0].strip(); sites[cur] = {"pm": [], "sheet_k": []}
            continue
        if cur and len(f) > 5 and f[1][:1].isdigit():
            try:
                pm = float(f[2])
            except ValueError:
                sites[cur]["pm"].append(np.nan); continue
            sites[cur]["pm"].append(pm)
            try:
                sites[cur]["sheet_k"].append([float(f[3]) / pm if pm else np.nan, float(f[4]) / pm if pm else np.nan, float(f[5]) / pm if pm else np.nan])
            except ValueError:
                pass
    return {k: v for k, v in sites.items() if len(v["pm"]) > 1000}


def main():
    out = {"note": "2024年度そらまめくん1時間値に回帰係数kを乗じた年間予測を再計算【計算結果】。室内発生は含まない（F-2024-09）。", "sites": {}}
    for name, d in load_sites().items():
        pm = np.array(d["pm"], float)
        n_artifact = int(np.sum(pm > 1000))  # 列ずれでExcel日付シリアル値（45292.08等）がPM列に入った行
        pm[pm > 1000] = np.nan
        ok = pm[~np.isnan(pm)]
        sk = np.nanmedian(np.array(d["sheet_k"]), axis=0) if d["sheet_k"] else [None] * 3
        r = {"n_hours": int(len(pm)), "n_valid": int(len(ok)), "n_date_serial_artifact": n_artifact, "outdoor_median": float(np.median(ok)), "outdoor_mean": float(ok.mean()),
             "outdoor_gt5_pct": float(100 * np.mean(ok > 5)), "sheet_k_used": [float(x) for x in sk]}
        for c, k in K.items():
            r[f"{c}_gt5_pct"] = float(100 * np.mean(k * ok > 5))
            r[f"{c}_gt15_pct"] = float(100 * np.mean(k * ok > 15))
            r[f"{c}_annual_mean"] = float(k * ok.mean())
        out["sites"][name] = r
        print(name, {k: round(v, 2) if isinstance(v, float) else v for k, v in r.items()})
    (ROOT / "knowledge" / "verification_annual_2025.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
