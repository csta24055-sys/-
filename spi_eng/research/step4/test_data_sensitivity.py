#!/usr/bin/env python3
"""実データが計算に反映されていることの確認：報告の長文題数を書き換えると、仮説の確率と推定順位が変わること。"""
import csv, os, sys, tempfile
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H)
import model
base = model.run()["grid"]["s=2|slope=1.0|rho=0.3"]
rows = list(csv.DictReader(open(os.path.join(H, "../step2/verified_records.csv"), encoding="utf-8")))
for r in rows:
    if r["passages"] == "3": r["passages"] = "1"      # 3題の報告を1題に書き換える
fd, p = tempfile.mkstemp(suffix=".csv"); os.close(fd)
with open(p, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
alt = model.run(counts_path=p)["grid"]["s=2|slope=1.0|rho=0.3"]
os.remove(p)
dh = abs(alt["hyp"]["H_high"] - base["hyp"]["H_high"]) + abs(alt["hyp"]["H_none"] - base["hyp"]["H_none"])
dm = abs(alt["rank"]["中央値(上位%)"] - base["rank"]["中央値(上位%)"])
assert dh > 0.05 and dm > 1.0, (dh, dm)
print("DATA SENSITIVITY OK", round(dh, 3), round(dm, 2))
