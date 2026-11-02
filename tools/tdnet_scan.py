#!/usr/bin/env python3
"""TDnet（直近約1か月分の公開一覧）から、指定した証券コードの決算関連開示を収集する。
使い方: python3 tools/tdnet_scan.py 20261001 20261102 9503 9502 ...  → data/tdnet_hits.csv
"""
import csv, datetime, os, re, sys, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0"}
d0, d1 = [datetime.datetime.strptime(x, "%Y%m%d").date() for x in sys.argv[1:3]]
codes = set(c if len(c) == 5 else c + "0" for c in sys.argv[3:])
rows = []
d = d0
while d <= d1:
    for p in range(1, 30):
        u = f"https://www.release.tdnet.info/inbs/I_list_{p:03d}_{d:%Y%m%d}.html"
        try:
            h = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read().decode("utf-8", "ignore")
        except Exception:
            break
        for tr in re.findall(r"<tr>(.*?)</tr>", h, re.S):
            cells = [re.sub(r"<[^>]+>", "", c).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
            code = next((c for c in cells if re.fullmatch(r"\d{4}[0-9A-Z]", c)), None)
            if code in codes:
                pdf = re.search(r'href="([^"]+\.pdf)"', tr)
                title = max(cells, key=len)
                rows.append(dict(date=d.isoformat(), code=code, title=title, pdf=("https://www.release.tdnet.info/inbs/" + pdf.group(1)) if pdf else ""))
    d += datetime.timedelta(days=1)
out = os.path.join(ROOT, "data", "tdnet_hits.csv")
with open(out, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["date", "code", "title", "pdf"]); w.writeheader(); w.writerows(rows)
for r in rows: print(r["date"], r["code"], r["title"][:70])
