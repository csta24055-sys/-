"""Where does LibreOffice differ from Excel at the ROOT? For every cell where LO != Excel cached value:
evaluate the formula with the reference evaluator on LO's own values of all cells; if that reproduces
LO's value, the difference came from upstream; otherwise LO itself computes the rule differently."""
import sys, os, pickle, collections
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "jcat_tools"))
import fx, excel_ref as X
from store import Store, KEY_SHIFT
from overlay import OverlayStore
from validate_ref import same
st = Store(sys.argv[1]); D = pickle.load(open(sys.argv[2], "rb")); B = pickle.load(open(sys.argv[3], "rb"))
changes = collections.defaultdict(dict)
for (book, sheet), vals in B["values"].items():
    sh = st.sheet(book, sheet)
    for (r, c), v in vals.items():
        changes[sh.sid][r * KEY_SHIFT + c] = v
ost = OverlayStore(st, dict(changes))
pos2pid = {}
for pid, d in D["instances"].items():
    for (book, sheet), arr in d.items():
        for r, c in arr.tolist():
            pos2pid[(book, sheet, r, c)] = pid
roots = collections.Counter(); root_ex = collections.defaultdict(list); n_bad = collections.Counter()
for (book, sheet), vals in B["values"].items():
    sh = st.sheet(book, sheet)
    for (r, c), v in vals.items():
        want = sh.values.get(r * KEY_SHIFT + c)
        if same(v, want)[0]:
            continue
        n_bad[book] += 1
        pid = pos2pid[(book, sheet, r, c)]
        p = D["patterns"][pid]
        col0 = 0
        for ch in p["col"]:
            col0 = col0 * 26 + ord(ch) - 64
        tree = X.prepare(fx.Parser(fx.tokenize(p["text"])).parse(), p["row"], col0, st, book, sheet)
        X._INDEX_CACHE.clear(); X._SUMIF_CACHE.clear()
        try:
            ref = X.evaluate(tree, ost, book, sheet, r, c)
        except Exception as e:
            ref = "EXC"
        if not same(ref, v)[0]:
            roots[(book, p["eq"], pid)] += 1
            if len(root_ex[(book, p["eq"], pid)]) < 2:
                root_ex[(book, p["eq"], pid)].append((sheet, r, c, repr(v)[:40], repr(ref)[:40], repr(want)[:40]))
print("mismatching cells", dict(n_bad))
print("root cells (LO differs from the rule applied to LO's own inputs):", sum(roots.values()), "patterns", len(roots))
for k, n in roots.most_common(40):
    print(n, k, D["patterns"][k[2]]["text"][:110], root_ex[k][:1])
pickle.dump({"roots": roots, "examples": dict(root_ex), "n_bad": n_bad}, open(sys.argv[4], "wb"))
