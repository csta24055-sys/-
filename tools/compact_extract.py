#!/usr/bin/env python3
"""data/extracts/<ID>.md を、数値を含む文中心に圧縮して表示する（比較分析の下読み用）。"""
import re, sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIM = {"事業の内容": 350, "従業員": 450, "経営方針・課題": 1600, "経営成績（経常利益）": 260, "研究開発": 250, "設備投資概要": 650, "新設計画": 900, "大株主": 0, "役員": 0}
for sid in sys.argv[1:]:
    t = open(os.path.join(ROOT, "data", "extracts", f"{sid}.md"), encoding="utf-8").read()
    print(f"===== {sid}")
    for sec in re.split(r"\n## ", t)[1:]:
        name, body = sec.split("\n", 1)
        lim = LIM.get(name, 300)
        if not lim: continue
        body = re.sub(r"[+\-|=]{3,}", " ", body); body = re.sub(r"\s+", " ", body)
        if name == "経営方針・課題":
            sents = re.split(r"(?<=[。])", body)
            body = "".join(s for s in sents if re.search(r"(億円|兆円|％|%|GW|万kW|千kW|万ｔ|万トン|20[3-5]0|ROE|ROIC|配当)", s))
        print(f"[{name}] {body[:lim]}")
