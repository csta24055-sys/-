"""2024年度 住宅A〜H の1分値原データ（Box『全測定』フォルダ, ファイル名に居住者姓を含むため Box ID で管理）を解析する。

入力: private_data/raw/2024_all/f<BoxID>.txt（get_file_content のテキスト, 非コミット）
出力: knowledge/verification_2024.json（住宅記号ごとの集計値のみ）
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "private_data" / "raw" / "2024_all"
# Box ID → 住宅記号（2024年度発表スライドの測定点・測定期間と照合して決定）
HOUSES = {"A": "1777498129877", "B": "1777500039706", "C": "1777515152950", "D": "1777507478134",
          "E": "1777498590422", "F": "1777500947702", "G": "1777501395735", "H": "1777498540083"}
OUT_LABELS = ("外気",)
DT = re.compile(r"^\d{1,4}/\d{1,2}/\d{1,4} \d{1,2}:\d{2}$")
# 2024年度 I/O 算出シート（S-2024-12）の値: 外気, 室内, I/O
REPORTED = {"B": (9.42, 7.76, 0.82), "A": (5.11, 3.69, 0.72), "D": (16.00, 6.87, 0.43), "C": (8.14, 2.82, 0.35),
            "F": (6.29, 2.70, 0.43), "E": (17.86, 2.03, 0.11), "G": (11.40, 1.31, 0.11), "H": (10.83, 0.60, 0.06)}
SLIDE_GT5 = {"A": 23.9, "B": 56.6, "C": 24.2, "D": 77.2, "E": 10.1, "F": 8.5, "G": 11.0, "H": 10.1}  # S-2024-04


def to_ts(s):
    t = pd.to_datetime(s, errors="coerce", format="mixed")
    return None if pd.isna(t) else t.floor("min")


def parse_sections(path: Path):
    sections, cur = [], None
    for line in path.read_text(encoding="utf-8").split("\n"):
        if line and not line.startswith("\t"):
            cur = {"name": line.strip(), "lines": []}
            sections.append(cur)
        elif cur is not None:
            cur["lines"].append(line.split("\t"))
    return sections


def section_series(sec) -> dict[str, dict]:
    header, series = None, {}
    for f in sec["lines"]:
        dcols = [j for j, c in enumerate(f) if DT.match(c.strip())]
        if not dcols:
            labels = [c.strip() for c in f]
            if sum(1 for c in labels if c and not re.match(r"^[-\d.]+$", c)) >= 2:
                header = labels
            continue
        if header is None:
            continue
        if len(dcols) == 1:  # 横持ち: 日時1列＋各室
            ts = to_ts(f[dcols[0]].strip())
            for j in range(dcols[0] + 1, len(f)):
                lab = header[j] if j < len(header) else ""
                if lab and f[j].strip():
                    try:
                        series.setdefault(lab, {})[ts] = float(f[j])
                    except ValueError:
                        pass
        else:  # 測点ごとの（日時, 値）ペア
            for j in dcols:
                lab = (header[j] if j < len(header) and header[j] else (header[j + 1] if j + 1 < len(header) else ""))
                if lab and j + 1 < len(f) and f[j + 1].strip():
                    try:
                        series.setdefault(lab, {})[to_ts(f[j].strip())] = float(f[j + 1])
                    except ValueError:
                        pass
    return series


UNION = {"D"}  # 測点がシート内の複数ブロックに分かれている住宅は全セクションを統合


def load_house(box_id: str, union: bool = False) -> pd.DataFrame:
    best = None
    if union:
        allser: dict = {}
        for sec in parse_sections(RAW / f"f{box_id}.txt"):
            for k, v in section_series(sec).items():
                allser.setdefault(k, {}).update(v)
        best = (0, allser)
    for sec in ([] if union else parse_sections(RAW / f"f{box_id}.txt")):
        s = section_series(sec)
        if "外気" not in s:
            continue
        n = len(s["外気"])
        if best is None or n > best[0]:
            best = (n, s)
    df = pd.DataFrame({k: pd.Series(v) for k, v in best[1].items()})
    df = df[~df.index.isna()].sort_index()
    return df[~df.index.duplicated()]


def main():
    out = {"note": "2024年度住宅A〜Hの1分値（0.3–1.0 μm, センサー表示 μg/m³）から本プロジェクトが算出【計算結果】。室内は全測点の単純平均（気積加重ではない）。", "houses": {}}
    for h, bid in HOUSES.items():
        df = load_house(bid, union=h in UNION)
        oc = "外気"
        rooms = [c for c in df.columns if c != oc]
        both = df.dropna(subset=[oc])
        indoor = both[rooms].mean(axis=1)
        allrooms = df[rooms]
        r = {"start": str(df.index.min()), "end": str(df.index.max()), "n_min_outdoor": int(df[oc].notna().sum()), "rooms": len(rooms),
             "outdoor_mean": float(both[oc].mean()), "indoor_mean_simple": float(indoor.mean()),
             "io_simple": float(indoor.mean() / both[oc].mean()),
             "room_io": {"min": float((both[rooms].mean() / both[oc].mean()).min()), "max": float((both[rooms].mean() / both[oc].mean()).max())},
             "gt5_pct_house_mean": float(100 * (allrooms.mean(axis=1) > 5).mean()),
             "gt5_pct_room_range": [float(100 * (allrooms[c].dropna() > 5).mean()) for c in rooms],
             "gt15_pct_house_mean": float(100 * (allrooms.mean(axis=1) > 15).mean()),
             "reported_io_sheet": REPORTED[h], "slide_gt5_pct": SLIDE_GT5[h]}
        r["gt5_pct_room_range"] = [min(r["gt5_pct_room_range"]), max(r["gt5_pct_room_range"])]
        out["houses"][h] = r
        print(h, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items() if k not in ("room_io",)}, {k: round(v, 2) for k, v in r["room_io"].items()})
    (ROOT / "knowledge" / "verification_2024.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
