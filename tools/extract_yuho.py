#!/usr/bin/env python3
"""EDINET DB 有報テキストから比較分析用の要所を抽出する。
使い方: python3 tools/extract_yuho.py S041 [S042 ...]  → data/extracts/<ID>.md（.gitignore対象・再生成可）"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECTIONS = [  # (ラベル, 見出し正規表現, 文字数)
    ("事業の内容", r"【事業の内容】", 1200),
    ("従業員", r"【従業員の状況】", 1400),
    ("経営方針・課題", r"【経営方針[，、,]?\s*経営環境及び対処すべき課題等】", 4500),
    ("経営成績（経常利益）", r"経常(利益|損益)は", 900),
    ("研究開発", r"【研究開発活動】", 700),
    ("設備投資概要", r"【設備投資等の概要】", 1000),
    ("新設計画", r"【設備の新設[，、,]?\s*除却等の計画】", 1300),
    ("大株主", r"【大株主の状況】", 1000),
    ("役員", r"【役員の状況】", 2500),
]
def norm(t): return re.sub(r"[ \t　]+", " ", re.sub(r"\n\s*\n+", "\n", t))
for sid in sys.argv[1:]:
    txt = norm(open(os.path.join(ROOT, "data", "text", f"{sid}.txt"), encoding="utf-8").read())
    out = [f"# {sid}"]
    for label, pat, n in SECTIONS:
        ms = list(re.finditer(pat, txt))
        if not ms:
            out.append(f"## {label}\n（該当見出しなし）"); continue
        m = ms[-1] if label != "経営成績（経常利益）" else ms[0]   # 目次ではなく本文側を取る
        out.append(f"## {label}\n" + txt[m.start(): m.start() + n].replace("\n", " "))
    os.makedirs(os.path.join(ROOT, "data", "extracts"), exist_ok=True)
    p = os.path.join(ROOT, "data", "extracts", f"{sid}.md")
    open(p, "w", encoding="utf-8").write("\n\n".join(out)); print(p, len("\n".join(out)))
