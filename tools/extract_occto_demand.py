#!/usr/bin/env python3
"""OCCTO需要想定（S012）のテキストから、全国と東京エリアの年度別数値を抽出してCSV化する。
出力: data/occto_demand_2026.csv  （表の出現順：最大需要電力[千kW]、需要電力量、家庭用その他、業務用、産業用その他[百万kWh]）"""
import csv, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = os.path.join(ROOT, "data", "text", "S012.txt")
labels = ["最大需要電力_千kW", "需要電力量_百万kWh", "家庭用その他_百万kWh", "業務用_百万kWh", "産業用その他_百万kWh"]
years = list(range(2026, 2036))
rows, seen = [], {"東京": 0, "全国": 0}
for line in open(src, encoding="utf-8"):
    s = re.sub(r"\s+", " ", line).strip()
    s = re.sub(r"^要 ", "", s)
    m = re.match(r"^(東京|全国) ((?:[\d,]+ ){9}[\d,]+)", s)
    if not m:
        continue
    area = m.group(1); idx = seen[area]
    if idx >= len(labels):
        continue
    vals = [int(v.replace(",", "")) for v in m.group(2).split()]
    for y, v in zip(years, vals):
        rows.append({"area": area, "item": labels[idx], "fiscal_year": y, "value": v})
    seen[area] += 1
out = os.path.join(ROOT, "data", "occto_demand_2026.csv")
with open(out, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["area", "item", "fiscal_year", "value"]); w.writeheader(); w.writerows(rows)
print(out, len(rows), seen)
