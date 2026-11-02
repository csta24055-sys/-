"""実測データ解析関数群（pandas ベース）

フロントエンド（TypeScript）にも同等の実装があり、tests/test_crosscheck.py で
同一入力に対する結果の一致を検証する。
"""
from __future__ import annotations

import io
import math
from typing import Any

import numpy as np
import pandas as pd

TIME_HINTS = ("time", "date", "日時", "時刻", "日付", "timestamp", "datetime")


def read_table(content: bytes, filename: str) -> dict[str, pd.DataFrame]:
    """CSV / Excel を読み込み、シート名→DataFrame を返す"""
    name = filename.lower()
    if name.endswith((".xlsx", ".xlsm", ".xls")):
        sheets = pd.read_excel(io.BytesIO(content), sheet_name=None)
        return {k: _clean(v) for k, v in sheets.items()}
    for enc in ("utf-8-sig", "cp932", "shift_jis", "utf-8"):
        try:
            text = content.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("文字コードを判定できません（UTF-8 / Shift_JIS 以外）")
    sep = "\t" if name.endswith((".tsv", ".txt")) and "\t" in text[:2000] else ","
    return {"data": _clean(pd.read_csv(io.StringIO(text), sep=sep))}


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(how="all").dropna(axis=1, how="all")
    df.columns = [str(c).strip() for c in df.columns]
    return df


def detect_time_column(df: pd.DataFrame) -> str | None:
    for c in df.columns:
        if any(h in c.lower() for h in TIME_HINTS):
            return c
    for c in df.columns[:2]:
        if df[c].dtype == object:
            parsed = pd.to_datetime(df[c], errors="coerce")
            if parsed.notna().mean() > 0.8:
                return c
    return None


def numeric_columns(df: pd.DataFrame, exclude: str | None = None) -> list[str]:
    cols = []
    for c in df.columns:
        if c == exclude:
            continue
        s = pd.to_numeric(df[c], errors="coerce")
        if s.notna().mean() >= 0.5:
            cols.append(c)
    return cols


def quality_report(df: pd.DataFrame, cols: list[str], z: float = 3.5) -> list[dict[str, Any]]:
    """欠損・異常値（Robust Z: |x−median|/(1.4826·MAD) > z）・負値を列ごとに集計"""
    out = []
    for c in cols:
        s = pd.to_numeric(df[c], errors="coerce")
        n = len(s)
        missing = int(s.isna().sum())
        v = s.dropna()
        med = float(v.median()) if len(v) else float("nan")
        mad = float((v - med).abs().median()) if len(v) else float("nan")
        if mad and mad > 0:
            rz = (v - med).abs() / (1.4826 * mad)
            outliers = int((rz > z).sum())
            outlier_idx = [int(i) for i in v.index[rz > z][:50]]
        else:
            outliers, outlier_idx = 0, []
        out.append(
            {
                "column": c,
                "n": n,
                "missing": missing,
                "missing_pct": round(100 * missing / n, 2) if n else 0,
                "negative": int((v < 0).sum()),
                "outliers": outliers,
                "outlier_rows": outlier_idx,
                "mean": _f(v.mean()),
                "median": _f(med),
                "std": _f(v.std()),
                "min": _f(v.min()),
                "max": _f(v.max()),
                "p95": _f(v.quantile(0.95)) if len(v) else None,
            }
        )
    return out


def _f(x: Any) -> float | None:
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) or math.isinf(x) else round(x, 6)


def regression_through_origin(x: np.ndarray, y: np.ndarray) -> dict[str, float]:
    """y = k·x（原点通過）の最小二乗。2025年度梗概 表3 と同じ形式（係数・R²・95%CI）。
    R² は原点通過回帰の非中心化定義 1−SSE/Σy² を用いる（Excel の切片0設定と同じ）。"""
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    n = len(x)
    if n < 3:
        raise ValueError("データ点が不足しています（3点以上必要）")
    sxx = float(np.sum(x * x))
    k = float(np.sum(x * y) / sxx)
    resid = y - k * x
    sse = float(np.sum(resid**2))
    r2 = 1 - sse / float(np.sum(y * y))
    se = math.sqrt(sse / (n - 1) / sxx)
    tcrit = _t975(n - 1)
    return {"k": k, "r2": r2, "se": se, "ci_low": k - tcrit * se, "ci_high": k + tcrit * se, "n": n}


def linear_regression(x: np.ndarray, y: np.ndarray) -> dict[str, float]:
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    a, b = np.polyfit(x, y, 1)
    yhat = a * x + b
    r2 = 1 - np.sum((y - yhat) ** 2) / np.sum((y - y.mean()) ** 2)
    return {"slope": float(a), "intercept": float(b), "r2": float(r2), "n": int(len(x))}


def power_law_fit(x: np.ndarray, y: np.ndarray) -> dict[str, float]:
    """y = a·x^b を対数線形回帰で推定（2026年度 式(2) Q=78.611ΔP^0.828 と同じ手法 = Excel 累乗近似）"""
    m = (x > 0) & (y > 0) & np.isfinite(x) & np.isfinite(y)
    lx, ly = np.log(x[m]), np.log(y[m])
    b, ln_a = np.polyfit(lx, ly, 1)
    yhat = ln_a + b * lx
    r2 = 1 - np.sum((ly - yhat) ** 2) / np.sum((ly - ly.mean()) ** 2)
    return {"a": float(math.exp(ln_a)), "b": float(b), "r2": float(r2), "n": int(m.sum())}


def removal_efficiency(upstream: np.ndarray, downstream: np.ndarray) -> dict[str, float]:
    """η = (1 − 下流/上流)×100（2026年度 式(1)）。時刻ごとの η と、平均濃度比による η の両方を返す。"""
    m = np.isfinite(upstream) & np.isfinite(downstream) & (upstream > 0)
    up, dn = upstream[m], downstream[m]
    per = 1 - dn / up
    return {
        "eta_mean_of_ratios": float(np.mean(per) * 100),
        "eta_ratio_of_means": float((1 - dn.mean() / up.mean()) * 100),
        "eta_std": float(np.std(per, ddof=1) * 100) if len(per) > 1 else 0.0,
        "n": int(m.sum()),
    }


def io_ratio(indoor: np.ndarray, outdoor: np.ndarray) -> dict[str, float]:
    m = np.isfinite(indoor) & np.isfinite(outdoor) & (outdoor > 0)
    i, o = indoor[m], outdoor[m]
    return {
        "io_ratio_of_means": float(i.mean() / o.mean()),
        "io_median_of_ratios": float(np.median(i / o)),
        "indoor_mean": float(i.mean()),
        "outdoor_mean": float(o.mean()),
        "n": int(m.sum()),
    }


def exceedance(values: np.ndarray, threshold: float) -> float:
    v = values[np.isfinite(values)]
    return float((v > threshold).mean()) if len(v) else float("nan")


def fit_decay(t_s: np.ndarray, c: np.ndarray, c_bg: float = 0.0) -> dict[str, float]:
    """発塵終了後の減衰区間から β を推定（ln(C−Cbg) の線形回帰）"""
    m = np.isfinite(c) & (c - c_bg > 0)
    t, y = t_s[m], np.log(c[m] - c_bg)
    slope, intercept = np.polyfit(t, y, 1)
    yhat = slope * t + intercept
    r2 = 1 - np.sum((y - yhat) ** 2) / np.sum((y - y.mean()) ** 2)
    return {"beta_per_s": float(-slope), "c0": float(math.exp(intercept)), "r2": float(r2), "n": int(m.sum())}


def resample_mean(df: pd.DataFrame, time_col: str, cols: list[str], rule: str = "1h") -> pd.DataFrame:
    d = df.copy()
    d[time_col] = pd.to_datetime(d[time_col], errors="coerce")
    d = d.dropna(subset=[time_col]).set_index(time_col)
    for c in cols:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    return d[cols].resample(rule).mean().reset_index()


def _t975(df: int) -> float:
    """t 分布 97.5% 点（scipy 非依存の近似; df≥1）"""
    table = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262,
             10: 2.228, 15: 2.131, 20: 2.086, 30: 2.042, 60: 2.000, 120: 1.980}
    if df in table:
        return table[df]
    keys = sorted(table)
    for a, b in zip(keys, keys[1:]):
        if a < df < b:
            return table[a] + (table[b] - table[a]) * (df - a) / (b - a)
    return 1.96
