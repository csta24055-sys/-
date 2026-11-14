"""Per book: positions and Excel cached values of the formula cells (for the LibreOffice producers)."""
import sys, os, pickle, collections
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "jcat_tools"))
from store import Store, KEY_SHIFT
import random_cases as R
scan, inst, outdir = sys.argv[1:4]
D = pickle.load(open(inst, "rb"))
for book in ("SIM", "STD", "DET", "SUM"):
    st = Store(scan, books=(book,))
    pos = collections.defaultdict(list)
    for pid, d in D["instances"].items():
        for (bk, sheet), arr in d.items():
            if bk == book:
                pos[sheet].extend(map(tuple, arr.tolist()))
    values = {sh: {(r, c): st.sheet(book, sh).values.get(r * KEY_SHIFT + c) for r, c in ps} for sh, ps in pos.items()}
    sid = {sh: st.sheet(book, sh).sid for sh in pos}
    patch = []
    if book == "STD":
        for (sname, ftxt), newf in R.STD_PATCH.items():
            for pid, d in D["instances"].items():
                if D["patterns"][pid]["text"] == ftxt:
                    for (bk, s2), arr in d.items():
                        if bk == book:
                            patch += [(s2, r, c, newf) for r, c in arr.tolist()]
    pickle.dump(dict(pos=dict(pos), values=values, sid=sid, patch=patch), open(os.path.join(outdir, "cached_%s.pkl" % book), "wb"))
    print(book, sum(len(p) for p in pos.values()), "patch", len(patch))
