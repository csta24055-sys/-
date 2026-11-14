"""Synthetic harness: a one-sheet workbook whose rows hold generated inputs; a formula (relative references)
is compiled once with a given builder class and mode, run, and compared with the reference evaluator."""
import os, sys, time, collections, resource
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
for _p in (os.path.join(os.path.dirname(HERE), "jcat_tools"), os.path.join(os.path.dirname(HERE), "conv"),
           os.path.join(os.path.dirname(os.path.dirname(HERE)), "15_JCAT_CONVERSION", "tools")):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
import numpy as np
import fx, excel_ref as X, compile2 as K
from store import Sheet, KEY_SHIFT, Err
from validate_ref import same as same_tol      # tolerant comparison (relative 1e-9), used for cached values


def same(a, b):
    """EXACT comparison: numbers must be the same double (+0 and -0 are equal); texts, logicals, errors exact.
    Returns (equal, kind, relative difference) like validate_ref.same."""
    if isinstance(a, float) and isinstance(b, float) and not isinstance(a, bool) and not isinstance(b, bool):
        if a == b or (a != a and b != b):
            return True, "num", 0.0
        d = abs(a - b)
        return False, "num", d / max(abs(a), abs(b)) if max(abs(a), abs(b)) > 0 else d
    return same_tol(a, b)


class FakeStore:
    def __init__(self, sheets):
        self.sheets = sheets
        self.names, self.local_names = {}, {}

    def sheet(self, book, name):
        return self.sheets.get((book, name))

    def resolve_name(self, book, sheet, name):
        return None


def make(columns, nrows, extra=None):
    """columns: {col_index: list of values (row 1..nrows)}; extra: {(r, c): value}."""
    sh = Sheet("T", "S", 1)
    for c, vals in columns.items():
        for i, v in enumerate(vals):
            if v is not None:
                sh.values[(i + 1) * KEY_SHIFT + c] = v
    for (r, c), v in (extra or {}).items():
        if v is not None:
            sh.values[r * KEY_SHIFT + c] = v
    keys = list(sh.values)
    sh.max_row = max(k // KEY_SHIFT for k in keys) if keys else 1
    sh.max_col = max(k % KEY_SHIFT for k in keys) if keys else 1
    return FakeStore({("T", "S"): sh}), sh


def strings_of(sh, formula):
    out = {v for v in sh.values.values() if isinstance(v, str)}
    for t in fx.tokenize(formula):
        if t[0] == "str":
            out.add(t[1][1:-1].replace('""', '"'))
    return out


def run(formula, columns, nrows, out_col, builder_cls, mode8="A", improve=True, extra=None, reference=True):
    """Compile `formula` (written for row 1, column out_col) at rows 1..nrows; returns dict of results."""
    store, sh = make(columns, nrows, extra)
    sd = K.StrDict(strings_of(sh, formula))
    cache = K.SheetCache(sd)
    rows = np.arange(1, nrows + 1)
    cols = np.full(nrows, out_col)
    t0 = time.time()
    b = builder_cls(store, sd, cache, "T", "S", rows, cols)
    b.improve = improve
    b.mode8 = mode8
    tree = X.prepare(fx.Parser(fx.tokenize(formula)).parse(), 1, out_col, store, "T", "S")
    v = b.finish(b.ev(tree))
    t1 = time.time()
    got, prog, eng = b.run(v)
    t2 = time.time()
    refs = []
    if reference:
        for r in rows.tolist():
            X._INDEX_CACHE.clear(); X._SUMIF_CACHE.clear()
            try:
                refs.append(X.evaluate(tree, store, "T", "S", r, out_col))
            except Exception as e:
                refs.append("EXC:%s" % type(e).__name__)
    t3 = time.time()
    bad, missing = [], 0
    for i, (g, w) in enumerate(zip(got, refs)):
        if g == "<missing>":
            missing += 1
            bad.append((i + 1, g, w))
        elif not same(g, w)[0]:
            bad.append((i + 1, g, w))
    cells = sum(len(d) for d in b.tabs.data.values())
    mem = sum(a.nbytes for d in b.tabs.data.values() for a in d.values())
    return dict(n=nrows, bad=bad, missing=missing, steps=len(b.steps), compile_s=t1 - t0, run_s=t2 - t1, ref_s=t3 - t2,
                table_bytes=mem, got=got, ref=refs, builder=b, value=v)
