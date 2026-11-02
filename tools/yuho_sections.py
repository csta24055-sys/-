#!/usr/bin/env python3
"""有報テキストから主要節を長めに切り出し data/extracts/<ID>_full.md に保存（.gitignore対象）。
使い方: python3 tools/yuho_sections.py S040 [S041 ...]"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEC = [("沿革", r"【沿革】", 2500), ("事業の内容", r"【事業の内容】", 2500), ("関係会社", r"【関係会社の状況】", 3500),
       ("従業員", r"【従業員の状況】", 3000), ("経営方針・課題", r"【経営方針[，、,]?\s*経営環境及び対処すべき課題等】", 9000),
       ("サステナビリティ・人的資本", r"【サステナビリティに関する考え方及び取組】", 6000), ("事業等のリスク", r"【事業等のリスク】", 5000),
       ("経営成績の分析", r"【経営者による財政状態[、,]?\s*経営成績及びキャッシュ・フローの状況の分析】", 6000),
       ("研究開発", r"【研究開発活動】", 2500), ("設備投資", r"【設備投資等の概要】", 2500), ("主要な設備", r"【主要な設備の状況】", 2500),
       ("新設計画", r"【設備の新設[，、,]?\s*除却等の計画】", 3000)]
for sid in sys.argv[1:]:
    t = open(os.path.join(ROOT, "data", "text", f"{sid}.txt"), encoding="utf-8").read()
    t = re.sub(r"[ \t　]+", " ", t); t = re.sub(r"[+\-=|]{4,}", " ", t); t = re.sub(r"\n\s*\n+", "\n", t)
    out = [f"# {sid}"]
    for lab, pat, n in SEC:
        ms = list(re.finditer(pat, t))
        if not ms: out.append(f"## {lab}\n（見出しなし）"); continue
        m = ms[-1]
        out.append(f"## {lab}\n" + re.sub(r"\s+", " ", t[m.start(): m.start() + n]))
    p = os.path.join(ROOT, "data", "extracts", f"{sid}_full.md"); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write("\n\n".join(out)); print(p, len("\n".join(out)))
