#!/usr/bin/env python3
"""有報テキスト（EDINET DB）から比較用の基本数値を抽出し data/company_facts.csv に保存する。
使い方: python3 tools/company_facts.py S040:関西電力 S041:中部電力 ..."""
import csv, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def flat(t): return re.sub(r"\s+", "", t)
rows = []
for arg in sys.argv[1:]:
    sid, name = arg.split(":", 1)
    raw = open(os.path.join(ROOT, "data", "text", f"{sid}.txt"), encoding="utf-8").read()
    t = flat(raw)
    def find(pats, n=1):
        for p in pats:
            m = re.search(p, t)
            if m: return m.group(n)
        return ""
    # 提出会社の従業員表：従業員数|平均年齢|平均勤続|平均年間給与
    emp = re.search(r"提出会社の状況.{0,400}?\|([\d,]+)(?:\[[\d,]+\])?\|([\d.]+)\|([\d.]+)\|([\d,]+)\|", t)
    cons = find([r"連結会社の状況.{0,600}?合計\|?([\d,]+)", r"連結会社の状況.{0,300}?従業員数\(人\)\|?([\d,]+)"])
    rows.append(dict(
        id=sid, company=name,
        consolidated_employees=cons,
        parent_employees=emp.group(1) if emp else "", parent_avg_age=emp.group(2) if emp else "",
        parent_avg_tenure=emp.group(3) if emp else "", parent_avg_salary_yen=emp.group(4) if emp else "",
        ordinary_profit=find([r"経常利益は[、,]?([^。]{0,40}?(?:億円|百万円))", r"経常利益([\d,]+百万円)"]),
        net_income=find([r"親会社株主に帰属する当期純利益は[、,]?([^。]{0,50}?(?:億円|百万円))", r"親会社の所有者に帰属する当期利益は[、,]?([^。]{0,50}?(?:億円|百万円))"]),
        equity_ratio=find([r"自己資本比率は[、,]?[^。]{0,30}?([\d.]+[％%])", r"親会社所有者帰属持分比率は[、,]?([\d.]+[％%])"]),
        capex=find([r"設備投資(?:額|の総額|総額)?は[、,]?[^。]{0,30}?([\d,]+(?:百万円|億円))", r"総額([\d,]+(?:百万円|億円))の設備投資", r"設備投資額は[^。]{0,40}?([\d,]+(?:百万円|億円))"]),
        rnd=find([r"研究開発費(?:の総額|の金額)?は[、,]?[^。]{0,20}?([\d,]+(?:百万円|億円))"]),
    ))
out = os.path.join(ROOT, "data", "company_facts.csv")
with open(out, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
for r in rows: print(r)
