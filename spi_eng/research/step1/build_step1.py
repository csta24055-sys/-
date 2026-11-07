#!/usr/bin/env python3
"""STEP1 のレコードを、手作業の判定記録(manual_review_*.csv)から組み立てる。架空の行は作らない。"""
import csv, os
H = os.path.dirname(os.path.abspath(__file__))
COLS = ["report_id","url","medium","post_date","exam_period","eng_evidence","n_passages","q_per_passage","seiro","order","feel",
        "score_statement","selection_result","verification_method","original_verified","duplicate_group","notes"]
out = []
for f in ["manual_review_pages.csv", "manual_review_cb.csv"]:
    for r in csv.DictReader(open(os.path.join(H, f), encoding="utf-8")):
        if r["adopt"] == "yes":
            out.append({c: r.get(c, "") for c in COLS})
# 原文を取得できなかった(サイトが403)が、検索要約で存在を確認した報告
for r in csv.DictReader(open(os.path.join(H, "snippet_only_records.csv"), encoding="utf-8")):
    out.append({c: r.get(c, "") for c in COLS})
with open(os.path.join(H, "eng_records.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=COLS); w.writeheader(); w.writerows(out)
print("records", len(out), "original_verified", sum(r["original_verified"] == "yes" for r in out))
