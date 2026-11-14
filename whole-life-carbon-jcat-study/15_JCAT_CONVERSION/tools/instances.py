"""Instances of every normalized pattern (from the private ledgers 01 and 02b) -> instances.pkl"""
import csv, collections, gzip, glob, os, pickle, re, sys

import numpy as np

P = sys.argv[1]           # private_out
out = sys.argv[2]
BOOKCODE = {"1_": "SIM", "2_": "STD", "3_": "CLS", "4_": "SUM", "5_": "DET"}
pats = {}
for r in csv.DictReader(open(os.path.join(P, "02b_正規化パターン全件.csv"), encoding="utf-8-sig")):
    m = re.match(r"^(\w+):(.*)!([A-Z]+)(\d+)$", r["代表（ブック:シート!セル）"])
    pats[r["パターンID"]] = dict(eq=r["独立方程式ID"], mt=r["方法ID"], text=r["A 原版の式（代表）"][1:], r1c1=r["R1C1 相対形"],
                              skel=r["骨格"], book=m.group(1), sheet=m.group(2), col=m.group(3), row=int(m.group(4)),
                              kind=r["種類"], funcs=r["使用関数"].split(), n=int(r["セル数"]))
inst = collections.defaultdict(lambda: collections.defaultdict(list))   # pid -> (book, sheet) -> [(row, col)]
n = 0
for path in sorted(glob.glob(os.path.join(P, "01_原版数式セル完全台帳_*.csv.gz"))):
    with gzip.open(path, "rt", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            book = BOOKCODE[r["元ファイル"][:2]]
            m = re.match(r"^([A-Z]+)(\d+)$", r["セル番地"])
            c = 0
            for ch in m.group(1):
                c = c * 26 + ord(ch) - 64
            inst[r["正規化パターンID"]][(book, r["シート"])].append((int(m.group(2)), c))
            n += 1
print("instances", n, "patterns", len(inst))
data = {"patterns": pats, "instances": {pid: {k: np.array(v, dtype=np.int64) for k, v in d.items()} for pid, d in inst.items()}}
pickle.dump(data, open(out, "wb"))
