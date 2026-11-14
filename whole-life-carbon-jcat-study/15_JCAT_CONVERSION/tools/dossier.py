"""Per independent equation (skeleton): what it computes, where, what it returns (private dossier)."""
import sys, os, csv, json, pickle, collections, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "jcat_tools"))
import fx
from store import Store, Err, KEY_SHIFT

scan, inst, p02b, out = sys.argv[1:5]
st = Store(scan)
D = pickle.load(open(inst, "rb"))
rows = list(csv.DictReader(open(p02b, encoding="utf-8-sig")))
by_eq = collections.defaultdict(list)
for r in rows:
    by_eq[r["独立方程式ID"]].append(r)


def text_at(sh, r, c):
    v = sh.values.get(r * KEY_SHIFT + c)
    return v if isinstance(v, str) and v.strip() and not sh.formula.get(r * KEY_SHIFT + c) else None


def headers(sh, r, c):
    col_h = []
    for rr in range(r - 1, max(0, r - 15), -1):
        t = text_at(sh, rr, c)
        if t:
            col_h.append(t.strip()[:40])
            if len(col_h) >= 2:
                break
    row_h = []
    for cc in range(1, min(c, 12)):
        t = text_at(sh, r, cc)
        if t:
            row_h.append(t.strip()[:40])
    # also the top rows of the column (table headers) when nothing near
    top = [text_at(sh, rr, c) for rr in range(1, 8)]
    return col_h, row_h[:3], [t.strip()[:40] for t in top if t][:2]


out_d = {}
for eq, pats in sorted(by_eq.items()):
    pats.sort(key=lambda r: -int(r["セル数"]))
    types = collections.Counter()
    nums, strs, errs = [], collections.Counter(), collections.Counter()
    for r in pats:
        pid = r["パターンID"]
        for (book, sheet), arr in D["instances"][pid].items():
            sh = st.sheet(book, sheet)
            for rr, cc in arr[:2000].tolist():
                v = sh.values.get(rr * KEY_SHIFT + cc)
                if isinstance(v, Err):
                    types["error"] += 1; errs[repr(v)] += 1
                elif isinstance(v, str):
                    types["text"] += 1; strs[v[:30]] += 1
                elif isinstance(v, bool):
                    types["bool"] += 1
                elif v is None:
                    types["blank"] += 1
                else:
                    types["number"] += 1; nums.append(v)
    rep = pats[0]
    m = re.match(r"^(\w+):(.*)!([A-Z]+)(\d+)$", rep["代表（ブック:シート!セル）"])
    book, sheet, col, row = m.group(1), m.group(2), m.group(3), int(m.group(4))
    c0 = 0
    for ch in col:
        c0 = c0 * 26 + ord(ch) - 64
    sh = st.sheet(book, sheet)
    ch_, rh_, top = headers(sh, row, c0)
    # headers of the main referenced cells (first 3 references)
    ref_heads = []
    for tok in fx.tokenize(rep["A 原版の式（代表）"][1:]):
        if tok[0] == "ref" and len(ref_heads) < 4:
            pre, body = tok[2]
            tsh = st.sheet(book, fx.norm_sheet(pre)) if pre else sh
            if tsh is None:
                continue
            parts = fx._parts(body)
            ca, cc, ra, rr = parts[0]
            if cc is None or rr is None:
                continue
            a, b, t = headers(tsh, rr, cc)
            ref_heads.append({"ref": tok[1], "sheet": tsh.name, "col_header": a[:1], "row_header": b[:2], "top": t[:1]})
    out_d[eq] = {
        "eq": eq, "cells": sum(int(r["セル数"]) for r in pats), "patterns": len(pats), "kind": rep["種類"],
        "functions": rep["使用関数"], "features": rep["特徴"], "skeleton": rep["骨格"], "sheets": rep["現れるシート"][:300],
        "process": rep["工程・分類"][:200], "representative": rep["代表（ブック:シート!セル）"],
        "formula": rep["A 原版の式（代表）"][:600], "variants": [r["A 原版の式（代表）"][:300] for r in pats[1:4]],
        "result_types": dict(types), "number_range": [min(nums), max(nums)] if nums else None,
        "number_examples": sorted(set(round(x, 6) for x in nums))[:6], "text_examples": [s for s, _ in strs.most_common(6)],
        "errors": dict(errs), "col_header": ch_, "row_header": rh_, "top_header": top, "ref_headers": ref_heads,
    }
json.dump(out_d, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(out_d))
