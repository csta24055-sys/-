"""2024年度 1分値から室内の濃度上昇イベント（生活行動による発生を想定）を検出し、減衰率を推定する（T-05 の基礎）。

方法: 各室の1分値を5分移動平均 → 基線=過去120分の20パーセンタイル → 上昇量 ΔC = C − 基線。
ΔC が 3 μg/m³ 以上でピークをとる区間をイベントとし、ピーク後に ΔC が 1/e になるまでの時間 τ（分）と
ピーク後 ΔC が ピーク×0.2 に下がるまでの時間（『浮遊時間』に相当）を求める。λ = 60/τ [1/h]。
出力: knowledge/events_2024.json（住宅記号ごとの集計のみ）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import raw_2024 as R  # noqa: E402

TYPE = {"A": "個別", "B": "個別", "C": "個別", "D": "個別", "E": "全館", "F": "全館", "G": "全館+EP", "H": "全館+EP"}
THR = 3.0


def events_in(series: pd.Series):
    s = series.asfreq("1min").interpolate(limit=5).rolling(5, center=True, min_periods=3).mean()
    base = s.rolling(120, min_periods=30).quantile(0.2).shift(1)
    d = (s - base).to_numpy()
    out, i, n = [], 0, len(d)
    while i < n:
        if np.isfinite(d[i]) and d[i] >= THR:
            j = i
            while j < n and np.isfinite(d[j]) and d[j] >= THR * 0.5:
                j += 1
            seg = d[i:j]
            k = i + int(np.nanargmax(seg))
            peak = d[k]
            e1 = next((m for m in range(k, min(n, k + 360)) if np.isfinite(d[m]) and d[m] <= peak / np.e), None)
            e2 = next((m for m in range(k, min(n, k + 360)) if np.isfinite(d[m]) and d[m] <= peak * 0.2), None)
            if e1 is not None and e1 > k:
                out.append({"peak": float(peak), "tau_min": float(e1 - k), "t20_min": float(e2 - k) if e2 else None,
                            "hour": int(s.index[k].hour)})
            i = max(j, (e2 or j)) + 1
        else:
            i += 1
    return out


VOL = json.loads((ROOT / "private_data" / "raw" / "2024_volumes.json").read_text(encoding="utf-8")) if (ROOT / "private_data" / "raw" / "2024_volumes.json").exists() else {}


def room_volume(h, room):
    v = VOL.get(h, {})
    if room in v:
        return v[room]
    rooms = [k for k in v if not k.startswith("_")]
    return float(np.mean([v[k] for k in rooms])) if rooms else float("nan")


def main():
    res = {"note": "2024年度1分値の室内上昇イベント（ΔC≥3 μg/m³）の減衰。τ: 1/eまでの時間、t20: 20%までの時間【計算結果】。外気変動による上昇も含み得る。", "houses": {}}
    for h, bid in R.HOUSES.items():
        df = R.load_house(bid, union=h in R.UNION)
        ev = []
        for c in df.columns:
            if c == "外気":
                continue
            for e in events_in(df[c].dropna()):
                e["room_m_ug"] = e["peak"] * room_volume(h, c)  # 瞬時放出・室内完全混合の下限推定 [μg]
                e["house_m_ug"] = e["peak"] * VOL.get(h, {}).get("_total", float("nan"))  # 全館に均一化した場合
                ev.append(e)
        days = (df.index.max() - df.index.min()).total_seconds() / 86400
        rooms = len(df.columns) - 1
        tau = np.array([e["tau_min"] for e in ev]); t20 = np.array([e["t20_min"] for e in ev if e["t20_min"]])
        res["houses"][h] = {"type": TYPE[h], "n_events": len(ev), "events_per_room_day": len(ev) / max(days * rooms, 1e-9),
                            "tau_median_min": float(np.median(tau)) if len(tau) else None,
                            "lambda_median_per_h": float(60 / np.median(tau)) if len(tau) else None,
                            "t20_median_min": float(np.median(t20)) if len(t20) else None,
                            "t20_p10_p90": [float(np.percentile(t20, 10)), float(np.percentile(t20, 90))] if len(t20) > 4 else None,
                            "peak_median": float(np.median([e["peak"] for e in ev])) if ev else None,
                            "room_mass_median_mg": float(np.median([e["room_m_ug"] for e in ev]) / 1000) if ev else None,
                            "room_mass_p90_mg": float(np.percentile([e["room_m_ug"] for e in ev], 90) / 1000) if ev else None,
                            "house_mass_median_mg": float(np.median([e["house_m_ug"] for e in ev]) / 1000) if ev else None,
                            "hours_top": pd.Series([e["hour"] for e in ev]).value_counts().head(3).to_dict() if ev else {}}
        r = res["houses"][h]
        print(h, TYPE[h], {k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()})
    (ROOT / "knowledge" / "events_2024.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=int), encoding="utf-8")


if __name__ == "__main__":
    main()
