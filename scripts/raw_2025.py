"""2025年度 実測原データ（Box からテキスト抽出したもの）を解析し、梗概・本論の記載値と照合する。

入力: private_data/raw/S-2025-*.txt（Git 管理外。Box get_file_content の出力を保存したもの）
出力: knowledge/verification_2025.json（集計値のみ。原データは含まない）

使い方:  .venv/bin/python scripts/raw_2025.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "private_data" / "raw"
sys.path.insert(0, str(ROOT / "backend"))
from aqros import analysis as A  # noqa: E402


def parse_minute_block(path: Path) -> pd.DataFrame:
    """先頭の1分値ブロック（datetime + 各センサー列）を DataFrame に。列名は2行目の室名。"""
    lines = path.read_text(encoding="utf-8").split("\n")
    rooms_row = lines[2].split("\t")
    # 1行目の datetime 列位置
    hdr = lines[1].split("\t")
    c0 = hdr.index("datetime")
    names = []
    for j in range(c0 + 1, len(rooms_row)):
        r = rooms_row[j].strip()
        if not r:
            break
        names.append(r)
    rows = []
    for ln in lines[3:]:
        if not ln.startswith("\t"):
            break
        f = ln.split("\t")
        ts = f[c0] if len(f) > c0 else ""
        if not ts or not ts[:4].isdigit():
            continue
        vals = []
        for j in range(len(names)):
            k = c0 + 1 + j
            try:
                vals.append(float(f[k]) if k < len(f) and f[k] != "" else math.nan)
            except ValueError:
                vals.append(math.nan)
        rows.append([ts] + vals)
    df = pd.DataFrame(rows, columns=["t"] + names)
    df["t"] = pd.to_datetime(df["t"], errors="coerce")
    return df.dropna(subset=["t"]).set_index("t").sort_index()


def outdoor_col(df):
    for c in df.columns:
        if c in ("外", "外気"):
            return c
    raise KeyError("外気列なし")


def summarize(df: pd.DataFrame, start=None, end=None, indoor=("リビング",)) -> dict:
    d = df.loc[start:end] if (start or end) else df
    oc = outdoor_col(d)
    h = d.resample("1h").mean()
    res = {"start": str(d.index.min()), "end": str(d.index.max()), "n_min": int(len(d)), "outdoor_mean": float(d[oc].mean())}
    for c in d.columns:
        if c == oc:
            continue
        res[f"mean_{c}"] = float(d[c].mean())
        res[f"io_{c}"] = float(d[c].mean() / d[oc].mean())
    ins = [c for c in indoor if c in d.columns]
    if ins:
        ind = h[ins].mean(axis=1)
        m = ind.notna() & h[oc].notna()
        if m.sum() >= 3:
            r = A.regression_through_origin(h[oc][m].to_numpy(), ind[m].to_numpy())
            res["k_hourly_origin"] = r["k"]
            res["k_r2"] = r["r2"]
            res["k_ci"] = [r["ci_low"], r["ci_high"]]
            res["n_hours"] = r["n"]
            res["indoor_cols"] = ins
    return res


def main():
    out: dict = {"note": "原データ（Box, 2025年度）から本プロジェクトが算出した集計値【計算結果】。原データは private_data に保存しコミットしない。"}
    # --- 住宅A 岩国: 条件① 〜9/20 17:00, 条件② 9/20 17:00〜（表5）
    a = parse_minute_block(RAW / "S-2025-19_iwakuni.txt")
    sw = pd.Timestamp("2025-09-20 17:00")
    out["A_iwakuni"] = {
        "columns": list(a.columns),
        "all": summarize(a),
        "cond1": summarize(a, None, sw - pd.Timedelta(minutes=1)),
        "cond2": summarize(a, sw, None),
        "reported": {"outdoor_mean": 3.7, "io_cond1": 0.28, "io_cond2": 1.10},
    }
    # --- 住宅B 下関: 全期間 条件②
    b = parse_minute_block(RAW / "S-2025-20_shimonoseki.txt")
    out["B_shimonoseki"] = {"columns": list(b.columns), "all": summarize(b, indoor=("トイレ", "浴室", "空調室")),
                            "reported": {"outdoor_mean": 5.0, "io_cond2": 0.90}}
    # --- 住宅C 直方: 表5の区分（最終版）と 表6 運転記録による再区分
    c = parse_minute_block(RAW / "S-2025-21_nogata.txt")
    T = pd.Timestamp
    final = {
        "cond2_final_table5": summarize(c, T("2025-09-25"), T("2025-10-12 09:59")),
        "cond3_final_table5": summarize(c, T("2025-10-12 10:00"), None),
    }
    log = {
        "ep_on_1 (9/25〜9/29 18時)": summarize(c, T("2025-09-25"), T("2025-09-29 17:59")),
        "ep_off (9/29 18時〜10/6 6:30) = 真の条件②": summarize(c, T("2025-09-29 18:00"), T("2025-10-06 06:29")),
        "ep_on_2 (10/6 6:30〜10/12 10時)": summarize(c, T("2025-10-06 06:30"), T("2025-10-12 09:59")),
        "cond3_ac_off (10/12 10時〜10/20 9時)": summarize(c, T("2025-10-12 10:00"), T("2025-10-20 08:59")),
        "cond3_ac_on (10/20 9時〜)": summarize(c, T("2025-10-20 09:00"), None),
    }
    out["C_nogata"] = {"columns": list(c.columns), "all": summarize(c), **final, "by_operation_log": log,
                       "reported": {"outdoor_mean": 7.9, "io_cond2_final": 0.68, "io_cond3_final": 1.22,
                                    "interim": {"io_cond1": 0.64, "io_cond2": 0.71, "io_cond3": 1.49}}}
    dst = ROOT / "knowledge" / "verification_2025.json"
    dst.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1, default=float)[:6000])


if __name__ == "__main__":
    main()
