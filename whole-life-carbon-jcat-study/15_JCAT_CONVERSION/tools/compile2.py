"""Compiler: an Excel formula pattern -> a program of the EXISTING masked sum-product engine
(10_TRANSFORM_STUDY/research_code/tstudy/msp.py, used unchanged) + knot spectra, and its execution
on every instance of the pattern.

Generic research code: it contains no J-CAT formula, value or coefficient. The formulas and the cell
values are read at run time from the private scan.

VALUE ENCODING (the same for every cell; "lexical companions" of a text are computed when a table is
built, like tstudy.index.tokenise):
  t  type: 0 blank, 1 number, 2 text, 3 logical, 4 error
  n  number (t=1), 1/0 (t=3)
  s  identity code of the text (exact string)
  k  collation rank of the text (case-insensitive; Shift_JIS order); equal ranks = equal texts for "="
  e  error code (t=4)
  p  the number a text reads as (Excel's text-to-number coercion), q 1 when it reads as a number
  w  1 when the text contains a wildcard character (* ? ~)
  o  1 when the text starts with a comparison operator (< > =)
Everything else is a step of the engine: ``sp`` (masked sum-product) or ``match`` (first keyed match).

KNOT SPECTRA used (all jump forms of the ramp-step kernel with l = 0, i.e. sums of unit jumps):
  integer lattice   F(x) = sum_{m>=1} [m <= x]           floor of x >= 0 (ROUND*, INT, MOD, positions)
                    evaluated exactly by dyadic bisection r <- r - 2^j [2^j <= r] (Sterbenz: exact)
  decimal lattice   E(y) = sum_k [10^k <= y]               decade of y (Excel's 15-significant-digit rounding)
  position lattice  O(p) = sum_{q<=p} [nonblank(q)]        running count along a look-up vector
Nothing is evaluated outside the engine except
  * the placement of cells that a formula addresses by POSITION (static references: formula geometry),
  * sub-expressions without any cell (coefficients), evaluated once with the reference evaluator.
"""
from __future__ import annotations

import bisect
import collections
import math
import os
import re
import sys

import numpy as np

STUDY = os.environ.get("STUDY", "/home/user/-/whole-life-carbon-jcat-study")
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(STUDY, "10_TRANSFORM_STUDY", "research_code"))
from tstudy import msp, index  # noqa: E402
from tstudy.tables import Tables  # noqa: E402

import excel_ref as X  # noqa: E402   (front end: the prepared tree; constant folding)
from store import KEY_SHIFT, Err, to_float_text  # noqa: E402

COMPS = ("t", "n", "s", "k", "e", "p", "q", "w", "o")
T0, T1, T2, T3, T4 = 0, 1, 2, 3, 4            # blank, number, text, logical, error
ALL = frozenset(range(5))
E_DIV0, E_VALUE, E_REF, E_NAME, E_NUM, E_NA = 2, 3, 4, 5, 6, 7
MAX_ROWS, MAX_COLS = 1048576, 16384
FLOOR_BITS = 53
DEC_K = range(-40, 41)


class Unsupported(Exception):
    """Outside the vocabulary of the two structures (or of this compiler): recorded as a failure."""


# =============================================================================================
# text dictionary
# =============================================================================================
class StrDict:
    def __init__(self, strings):
        uniq = sorted(set(strings) | {"", "TRUE", "FALSE"})
        self.code = {s: i + 1 for i, s in enumerate(uniq)}
        self.text = {i + 1: s for i, s in enumerate(uniq)}
        self.keys = sorted({X.text_order(s) for s in uniq})
        self.rank_of_key = {k: float(i + 1) for i, k in enumerate(self.keys)}

    def scode(self, s):
        c = self.code.get(s)
        if c is None:
            c = self.code[s] = len(self.code) + 1
            self.text[c] = s
        return c

    def rank(self, s):
        key = X.text_order(s)
        r = self.rank_of_key.get(key)
        if r is None:                        # a text that is not in the dictionary: between its neighbours
            r = bisect.bisect_left(self.keys, key) + 0.5
        return r

    def enc(self, v):
        if v is None:
            return (0, 0.0, 0, 0.0, 0, 0.0, 0, 0, 0)
        if isinstance(v, bool):
            return (3, 1.0 if v else 0.0, 0, 0.0, 0, 0.0, 0, 0, 0)
        if isinstance(v, float):
            return (1, v, 0, 0.0, 0, 0.0, 0, 0, 0)
        if isinstance(v, Err):
            return (4, 0.0, 0, 0.0, v.code, 0.0, 0, 0, 0)
        x = to_float_text(v)
        return (2, 0.0, self.scode(v), self.rank(v), 0, 0.0 if x is None else x, 0 if x is None else 1,
                1 if any(ch in v for ch in "*?~") else 0, 1 if v[:1] in ("<", ">", "=") else 0)

    def dec(self, t, n, s, e):
        t = int(round(t))
        if t == 0:
            return 0.0
        if t == 1:
            return float(n)
        if t == 2:
            return self.text.get(int(round(s)), "<?>")
        if t == 3:
            return bool(round(n))
        return Err(int(round(e)))


class SheetCache:
    """A value source: encoded cells of every sheet (data layout only), sorted cell keys and components.
    The baseline source reads the cached values of the workbook; ``CaseSource`` overlays changed cells."""

    def __init__(self, sd):
        self.sd = sd
        self.memo = {}

    def sheet_arrays(self, sheet):
        a = self.memo.get(sheet.sid)
        if a is None:
            ks = np.array(sorted(sheet.values), dtype=np.int64)
            enc = self.sd.enc
            vals = sheet.values
            m = np.array([enc(vals[int(k)]) for k in ks], dtype=float).reshape(len(ks), len(COMPS))
            a = self.memo[sheet.sid] = (ks, m)
        return a

    def encode(self, sheet, rows, cols):
        ks, m = self.sheet_arrays(sheet)
        keys = np.asarray(rows, dtype=np.int64) * KEY_SHIFT + np.asarray(cols, dtype=np.int64)
        out = np.zeros((len(keys), len(COMPS)))
        if len(ks) and len(keys):
            idx = np.searchsorted(ks, keys)
            idx = np.minimum(idx, len(ks) - 1)
            found = ks[idx] == keys
            out[found] = m[idx[found]]
        return {c: out[:, i].copy() for i, c in enumerate(COMPS)}

    def all_cells(self, sheet):
        ks, m = self.sheet_arrays(sheet)
        cols = {c: m[:, i].copy() for i, c in enumerate(COMPS)}
        cols["r"] = (ks // KEY_SHIFT).astype(float)
        cols["c"] = (ks % KEY_SHIFT).astype(float)
        return cols

    def raw(self, sheet, key):
        return sheet.values.get(key)

    def lexical(self, sheet, rows, cols, J):
        """IMPROVEMENT (lexical companions of a text, like tstudy.index.tokenise): the length of the
        lower-cased text and the code points of its first J characters (0 beyond the end)."""
        keys = (np.asarray(rows, dtype=np.int64) * KEY_SHIFT + np.asarray(cols, dtype=np.int64)).tolist()
        L = np.zeros(len(keys))
        ch = np.zeros((len(keys), J))
        for i, k in enumerate(keys):
            v = self.raw(sheet, k)
            if isinstance(v, str):
                t = v.lower()
                L[i] = len(t)
                for j, c in enumerate(t[:J]):
                    ch[i, j] = ord(c)
        out = {"lex.L": L}
        for j in range(J):
            out["lex.c%d" % j] = ch[:, j].copy()
        return out


class StrDictExt:
    """The base dictionary plus the texts of one case: new texts get new identity codes and ranks strictly
    between the ranks of their neighbours (base ranks unchanged, so the compiled constants stay valid)."""

    def __init__(self, base, new_texts):
        self.base = base
        self.code = dict(base.code)
        self.text = dict(base.text)
        self.extra_rank = {}
        gaps = collections.defaultdict(set)
        for t in new_texts:
            if t not in self.code:
                c = len(self.code) + 1
                self.code[t] = c
                self.text[c] = t
            key = X.text_order(t)
            if key not in base.rank_of_key:
                gaps[bisect.bisect_left(base.keys, key)].add(key)
        for p, keys in gaps.items():
            ks = sorted(keys)
            for j, key in enumerate(ks):
                self.extra_rank[key] = p + (j + 1) / (len(ks) + 1)

    def scode(self, s):
        c = self.code.get(s)
        if c is None:
            c = self.code[s] = len(self.code) + 1
            self.text[c] = s
        return c

    def rank(self, s):
        key = X.text_order(s)
        r = self.base.rank_of_key.get(key)
        if r is None:
            r = self.extra_rank.get(key)
        if r is None:
            r = bisect.bisect_left(self.base.keys, key) + 0.5
        return r

    enc = StrDict.enc
    dec = StrDict.dec


class CaseSource(SheetCache):
    """Value source of one case: the baseline cells overlaid by ``changes`` {sheet sid: {key: value}}."""

    def __init__(self, base, changes, sd):
        self.base, self.changes, self.sd = base, changes, sd
        self.memo = {}
        self.ck = {}
        for sid, ch in changes.items():
            ks = np.array(sorted(ch), dtype=np.int64)
            m = np.array([sd.enc(ch[int(k)]) for k in ks], dtype=float).reshape(len(ks), len(COMPS))
            self.ck[sid] = (ks, m)

    def encode(self, sheet, rows, cols):
        out = self.base.encode(sheet, rows, cols)
        ch = self.ck.get(sheet.sid)
        if ch is None or not len(ch[0]):
            return out
        ks, m = ch
        keys = np.asarray(rows, dtype=np.int64) * KEY_SHIFT + np.asarray(cols, dtype=np.int64)
        idx = np.minimum(np.searchsorted(ks, keys), len(ks) - 1)
        hit = ks[idx] == keys
        if np.any(hit):
            for i, c in enumerate(COMPS):
                out[c][hit] = m[idx[hit], i]
        return out

    def sheet_arrays(self, sheet):
        a = self.memo.get(sheet.sid)
        if a is not None:
            return a
        ks, m = self.base.sheet_arrays(sheet)
        ch = self.ck.get(sheet.sid)
        if ch is None or not len(ch[0]):
            self.memo[sheet.sid] = (ks, m)
            return ks, m
        ck, cm = ch
        keep = ~np.isin(ks, ck)
        nonblank = cm[:, 0] != T0
        ks2 = np.concatenate([ks[keep], ck[nonblank]])
        m2 = np.concatenate([m[keep], cm[nonblank]])
        order = np.argsort(ks2, kind="stable")
        a = self.memo[sheet.sid] = (ks2[order], m2[order])
        return a

    def raw(self, sheet, key):
        ch = self.changes.get(sheet.sid)
        if ch is not None and key in ch:
            return ch[key]
        return sheet.values.get(key)


# =============================================================================================
# compile-time values
# =============================================================================================
def C(x):
    return {"const": float(x)}


def isc(o, v=None):
    return isinstance(o, dict) and "const" in o and (v is None or o["const"] == v)


def EQ(a, b, neg=False):
    f = {"pred": "eq", "a": a, "b": b}
    if neg:
        f["not"] = True
    return f


def LE(a, b, neg=False):
    f = {"pred": "le", "a": a, "b": b}
    if neg:
        f["not"] = True
    return f


def PRESENT(a, neg=False):
    f = {"pred": "present", "a": a}
    if neg:
        f["not"] = True
    return f


class V:
    """A scalar value per instance: operands of the components (None = 0) and the possible types."""
    __slots__ = ("c", "types", "integral")

    def __init__(self, c, types, integral=False):
        self.c = dict(c)
        self.types = frozenset(types)
        self.integral = integral

    def op(self, k):
        o = self.c.get(k)
        return C(0) if o is None else o


class RefS:
    """A static reference (determined by the formula geometry): one sheet, corner arrays per instance,
    ``bad`` = per-instance error code of the reference itself (0 = valid)."""

    def __init__(self, sheet, r1, c1, r2, c2, bad):
        self.sheet, self.r1, self.c1, self.r2, self.c2, self.bad = sheet, r1, c1, r2, c2, bad

    @property
    def single(self):
        return bool(np.all(self.r1 == self.r2) and np.all(self.c1 == self.c2))


class RefD:
    """A single cell whose position is computed from data: row/column operands and an error pair."""

    def __init__(self, sheet, row, col, ef, ec, fail=None):
        self.sheet, self.row, self.col, self.ef, self.ec, self.fail = sheet, row, col, ef, ec, fail


# =============================================================================================
# the builder
# =============================================================================================
class Builder:
    def __init__(self, store, sd, cache, book, sheet_name, rows, cols):
        self.store, self.sd, self.cache, self.book, self.sheet_name = store, sd, cache, book, sheet_name
        self.recipes = []           # how every value column of every table is filled from a value source
        self.improve = False        # True: allow the IMPROVEMENTS (recorded separately from the base method)
        self.rows = np.asarray(rows, dtype=np.int64)
        self.cols = np.asarray(cols, dtype=np.int64)
        self.n = len(self.rows)
        self.tabs = Tables()
        index.put_table(self.tabs, "G", {"_r": self.rows.astype(float), "_c": self.cols.astype(float)})
        self.steps = []
        self.k = 0
        self.notes = collections.Counter()
        self.memo = {}

    # ---- emission ---------------------------------------------------------------------------
    def nm(self, hint):
        self.k += 1
        return "%s%d" % (hint, self.k)

    def sp(self, terms, table="G", group="none", hint="v"):
        terms = [t for t in terms if t is not None]
        if not terms:
            return C(0)
        if group == "none" and len(terms) == 1 and len(terms[0]) == 1 and isc(terms[0][0]):
            return terms[0][0]
        out = self.nm(hint)
        self.steps.append({"op": "sp", "table": table, "out": out, "group": group, "terms": terms})
        return out

    def match(self, keys, into, on, table="G", hint="m"):
        out = self.nm(hint)
        self.steps.append({"op": "match", "table": table, "out": out, "keys": keys, "into": into, "on": on})
        return out

    def gcol(self, hint, arr):
        name = self.nm(hint)
        self.tabs.data["G"][name] = np.asarray(arr, dtype=float)
        self.tabs.data["G"][name + "?"] = np.ones(self.n, dtype=bool)
        return name

    def table(self, name, cols):
        index.put_table(self.tabs, name, {k: np.asarray(v, dtype=float) for k, v in cols.items()})

    # ---- error pairs ---------------------------------------------------------------------------
    def first_error(self, pairs):
        pairs = [(f, c) for f, c in pairs if not isc(f, 0.0)]
        if not pairs:
            return C(0), C(0)
        if len(pairs) == 1:
            return pairs[0]
        fl, co, prefix = [], [], []
        for f, c in pairs:
            fl.append(prefix + [EQ(f, C(1))])
            co.append(prefix + [EQ(f, C(1)), c])
            prefix = prefix + [EQ(f, C(1), True)]
        return self.sp(fl, hint="ef"), self.sp(co, hint="ec")

    def err_of(self, v):
        if T4 not in v.types:
            return C(0), C(0)
        if v.types == {T4}:
            return C(1), v.op("e")
        return self.sp([[EQ(v.op("t"), C(T4))]], hint="ef"), self.sp([[EQ(v.op("t"), C(T4)), v.op("e")]], hint="ec")

    def errv(self, code):
        return V({"t": C(T4), "e": C(code)}, {T4})

    def num_or_err(self, value, ef, ec, integral=False):
        if isc(ef, 0.0):
            return V({"t": C(T1), "n": value}, {T1}, integral)
        t = self.sp([[EQ(ef, C(1)), C(T4)], [EQ(ef, C(1), True), C(T1)]], hint="t")
        return V({"t": t, "n": self.sp([[EQ(ef, C(1), True), value]], hint="n"), "e": self.sp([[EQ(ef, C(1)), ec]], hint="e")},
                 {T1, T4}, integral)

    def bool_or_err(self, value, ef, ec):
        if isc(ef, 0.0):
            return V({"t": C(T3), "n": value}, {T3})
        t = self.sp([[EQ(ef, C(1)), C(T4)], [EQ(ef, C(1), True), C(T3)]], hint="t")
        return V({"t": t, "n": self.sp([[EQ(ef, C(1), True), value]], hint="n"), "e": self.sp([[EQ(ef, C(1)), ec]], hint="e")},
                 {T3, T4})

    def choose(self, cases):
        """cases: list of (mask factors, V); the masks are exclusive and cover every instance."""
        comps = {}
        for comp in COMPS:
            terms = []
            for mask, v in cases:
                o = v.c.get(comp)
                if o is None or isc(o, 0.0):
                    continue
                terms.append(list(mask) + [o])
            comps[comp] = self.sp(terms, hint=comp) if terms else None
        types = set()
        for _, v in cases:
            types |= v.types
        return V(comps, types, all(v.integral for _, v in cases))

    # ---- coercions -------------------------------------------------------------------------------
    def to_num(self, v):
        """Excel's to_num: blank 0, logical 1/0, text read as a number or #VALUE!, error itself."""
        T = v.types
        if T <= {T1}:
            return v.op("n"), C(0), C(0)
        tv = v.op("t")
        vt, et, ct = [], [], []
        if T1 in T:
            vt.append([EQ(tv, C(T1)), v.op("n")])
        if T3 in T:
            vt.append([EQ(tv, C(T3)), v.op("n")])
        if T2 in T:
            vt.append([EQ(tv, C(T2)), EQ(v.op("q"), C(1)), v.op("p")])
            et.append([EQ(tv, C(T2)), EQ(v.op("q"), C(1), True)])
            ct.append([EQ(tv, C(T2)), EQ(v.op("q"), C(1), True), C(E_VALUE)])
        if T4 in T:
            et.append([EQ(tv, C(T4))])
            ct.append([EQ(tv, C(T4)), v.op("e")])
        return (self.sp(vt, hint="x") if vt else C(0)), (self.sp(et, hint="ef") if et else C(0)), (self.sp(ct, hint="ec") if ct else C(0))

    def to_bool(self, v):
        T = v.types
        tv = v.op("t")
        vt, et, ct = [], [], []
        if T1 in T:
            vt.append([EQ(tv, C(T1)), EQ(v.op("n"), C(0.0), True)])
        if T3 in T:
            vt.append([EQ(tv, C(T3)), v.op("n")])
        if T2 in T:
            rt, rf = self.sd.rank("TRUE"), self.sd.rank("FALSE")
            vt.append([EQ(tv, C(T2)), EQ(v.op("k"), C(rt))])
            bad = [EQ(tv, C(T2)), EQ(v.op("k"), C(rt), True), EQ(v.op("k"), C(rf), True)]
            et.append(bad)
            ct.append(bad + [C(E_VALUE)])
        if T4 in T:
            et.append([EQ(tv, C(T4))])
            ct.append([EQ(tv, C(T4)), v.op("e")])
        return (self.sp(vt, hint="b") if vt else C(0)), (self.sp(et, hint="ef") if et else C(0)), (self.sp(ct, hint="ec") if ct else C(0))

    # ---- static cells ---------------------------------------------------------------------------
    def sheet_obj(self, name):
        if name:
            return self.store.sheet(self.book, name)
        return self.store.sheet(self.book, self.sheet_name)

    def make_ref(self, node):
        _, sh, corners = node
        sheet = self.sheet_obj(sh)
        n = self.n
        if sh and sheet is None:
            return self.errv(E_REF)
        rs, cs = [], []
        for rr, cc in corners:
            rs.append(None if rr is None else (np.full(n, rr[1]) if rr[0] else self.rows + rr[1]))
            cs.append(None if cc is None else (np.full(n, cc[1]) if cc[0] else self.cols + cc[1]))
        if rs[0] is None:
            r1, r2 = np.full(n, 1), np.full(n, max(sheet.max_row, 1))
        else:
            r1, r2 = np.minimum.reduce(rs), np.maximum.reduce(rs)
        if cs[0] is None:
            c1, c2 = np.full(n, 1), np.full(n, max(sheet.max_col, 1))
        else:
            c1, c2 = np.minimum.reduce(cs), np.maximum.reduce(cs)
        bad = np.where((r1 < 1) | (c1 < 1) | (r2 > MAX_ROWS) | (c2 > MAX_COLS), E_REF, 0)
        return RefS(sheet, r1, c1, r2, c2, bad)

    def cells_v(self, sheet, rr, cc, bad):
        """The values of static single cells (per instance) as a V; ``bad`` = error code per instance."""
        rr = np.where(bad > 0, 1, rr)
        cc = np.where(bad > 0, 1, cc)
        base = self.nm("c")
        rec = ("G", base + ".", sheet, rr, cc, bad.copy())
        self.recipes.append(rec)
        self.fill(rec, self.cache)
        comps = {c: base + "." + c for c in COMPS}
        self.notes["placement of a cell (static reference)"] += 1
        return V(comps, ALL)

    def dyn_cell(self, ref):
        """A cell whose position is data: keyed match into the cells of the sheet."""
        key = ("cells", ref.sheet.sid)
        tab = self.memo.get(key)
        if tab is None:
            tab = "W%d" % ref.sheet.sid
            rec = ("W", tab, ref.sheet)
            self.recipes.append(rec)
            self.fill(rec, self.cache)
            self.memo[key] = tab
        m = self.match([ref.row, ref.col], tab, ["r", "c"], hint="cell")
        ok = EQ(ref.ef, C(1), True)
        comps = {}
        for c in COMPS:
            o = {"col": c, "via": m}
            terms = [[ok, PRESENT(m), o]]
            if c == "t":
                terms.append([EQ(ref.ef, C(1)), C(T4)])
            if c == "e":
                terms.append([EQ(ref.ef, C(1)), ref.ec])
            comps[c] = self.sp(terms, hint="d" + c)
        if ref.fail is not None and not isc(ref.fail, 0.0):
            comps["t"] = self.mark_missing(comps["t"], ref.fail)
        self.notes["keyed match of a computed position (match)"] += 1
        return V(comps, ALL)

    def mark_missing(self, t, flag):
        """Outside the compiled domain where ``flag`` is 1: the result is MISSING (never silently a value).
        A missing value would be read as 'not equal' by the predicates of later steps, so every flag is also
        collected and the FINAL result of the formula is made missing wherever any flag is 1 (conservative:
        also when the flagged value is in a branch that is not taken)."""
        self.notes["outside the compiled domain -> missing (flag)"] += 1
        self.__dict__.setdefault("fail_flags", []).append(flag)
        return self.sp([[EQ(flag, C(1.0), True), t], [EQ(flag, C(1.0)), "_missing"]], hint="t")

    def scalar(self, x):
        if isinstance(x, V):
            return x
        if isinstance(x, RefD):
            return self.dyn_cell(x)
        n = self.n
        r = np.where(x.r1 == x.r2, x.r1, 0)
        c = np.where(x.c1 == x.c2, x.c1, 0)
        bad = x.bad.copy()
        single = (x.r1 == x.r2) & (x.c1 == x.c2)
        col_isect = ~single & (x.c1 == x.c2) & (x.r1 <= self.rows) & (self.rows <= x.r2)
        row_isect = ~single & ~col_isect & (x.r1 == x.r2) & (x.c1 <= self.cols) & (self.cols <= x.c2)
        r = np.where(col_isect, self.rows, np.where(row_isect, x.r1, r))
        c = np.where(col_isect, x.c1, np.where(row_isect, self.cols, c))
        bad = np.where((bad == 0) & ~single & ~col_isect & ~row_isect, E_VALUE, bad)
        if np.any(col_isect | row_isect):
            self.notes["implicit intersection (static)"] += 1
        return self.cells_v(x.sheet, r, c, bad)

    # ---- ranges as tables -------------------------------------------------------------------------
    def range_tables(self, ref, extra=None, truncate=True, key=None):
        """Distinct ranges of a static reference -> table R (one row per distinct range, column len_i, len_j)
        and its child R.c (one row per cell, row-major): _parent, i, j, the components.
        ``extra``: list of (prefix, RefS) aligned ranges whose cells are stored in the same rows.
        Returns (R, Rc, gref, bad) with gref a reference column of G into R."""
        def geo_key(r):
            return (r.sheet.sid, r.r1.tobytes(), r.c1.tobytes(), r.r2.tobytes(), r.c2.tobytes(), r.bad.tobytes())
        mk = ("rt", geo_key(ref), tuple((e[0], geo_key(e[1])) for e in (extra or [])), truncate, key)
        if mk in self.memo:
            return self.memo[mk]
        sheet = ref.sheet
        mr = max([sheet.max_row, 1] + [e.sheet.max_row for _, e in (extra or [])])
        geo = []
        for i in range(self.n):
            r1, c1, r2, c2 = int(ref.r1[i]), int(ref.c1[i]), int(ref.r2[i]), int(ref.c2[i])
            if ref.bad[i]:
                geo.append(None)
                continue
            r2t = min(r2, mr) if (truncate and r2 >= mr) else r2
            g = (r1, c1, r2t, c2, r2 - r1 + 1, c2 - c1 + 1)
            if extra:
                g = g + tuple((int(e.r1[i]), int(e.c1[i])) for _, e in extra)
            geo.append(g)
        uniq = sorted({g for g in geo if g is not None})
        pos = {g: j for j, g in enumerate(uniq)}
        total = sum(max(0, g[2] - g[0] + 1) * (g[3] - g[1] + 1) for g in uniq)
        if total > 6_000_000:
            raise Unsupported("range tables too large (%d cells)" % total)
        R = self.nm("R")
        Rc = R + ".c"
        self.table(R, {"h": [g[4] for g in uniq], "wd": [g[5] for g in uniq],
                       "ht": [max(0, g[2] - g[0] + 1) for g in uniq]})
        par, ii, jj, rr, cc = [], [], [], [], []
        for j, g in enumerate(uniq):
            h, w = max(0, g[2] - g[0] + 1), g[3] - g[1] + 1
            a, b = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
            par.append(np.full(h * w, j)); ii.append(a.ravel()); jj.append(b.ravel())
            rr.append(g[0] + a.ravel()); cc.append(g[1] + b.ravel())
        cat = (lambda L: np.concatenate(L) if L else np.zeros(0))
        par, ii, jj, rr, cc = cat(par), cat(ii), cat(jj), cat(rr), cat(cc)
        cols = {"_parent": par, "i": ii, "j": jj}
        self.table(Rc, cols)
        rec = ("T", Rc, "", sheet, rr, cc)
        self.recipes.append(rec)
        self.fill(rec, self.cache)
        for k_, (prefix, e) in enumerate(extra or []):
            er, ec_ = [], []
            for j, g in enumerate(uniq):
                h, w = max(0, g[2] - g[0] + 1), g[3] - g[1] + 1
                a, b = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
                er.append(g[6 + k_][0] + a.ravel()); ec_.append(g[6 + k_][1] + b.ravel())
            rec = ("T", Rc, prefix, e.sheet, cat(er), cat(ec_))
            self.recipes.append(rec)
            self.fill(rec, self.cache)
        rid = np.array([pos[g] if g is not None else -1 for g in geo], dtype=float)
        ridc = self.nm("rid")
        self.tabs.data["G"][ridc] = rid
        self.tabs.data["G"][ridc + "?"] = rid >= 0
        gref = self.match([ridc], R, ["_row"], hint="gr")
        self.notes["range as an index set (table of its cells)"] += 1
        out = (R, Rc, gref, ref.bad)
        self.memo[mk] = out
        self.memo[("rid", R)] = rid
        return out

    def static_bad(self, bad):
        """(flag, code) operands of a per-instance static error code."""
        if not np.any(bad > 0):
            return C(0), C(0)
        return self.gcol("rbf", (bad > 0).astype(float)), self.gcol("rbc", bad.astype(float))

    # ---- value columns from a value source (data layout; the steps never change) ------------------
    def fill(self, rec, src):
        kind = rec[0]
        if kind == "G":
            _, prefix, sheet, rr, cc, bad = rec
            enc = src.encode(sheet, rr, cc)
            if np.any(bad > 0):
                enc["t"] = np.where(bad > 0, T4, enc["t"])
                enc["e"] = np.where(bad > 0, bad, enc["e"])
                for c in ("n", "s", "k", "p", "q", "w", "o"):
                    enc[c] = np.where(bad > 0, 0.0, enc[c])
            for c in COMPS:
                self.tabs.data["G"][prefix + c] = enc[c]
                self.tabs.data["G"][prefix + c + "?"] = np.ones(len(enc[c]), dtype=bool)
        elif kind == "T":
            _, table, prefix, sheet, rr, cc = rec
            enc = src.encode(sheet, rr, cc) if len(rr) else {c: np.zeros(0) for c in COMPS}
            for c in COMPS:
                self.tabs.data[table][prefix + c] = enc[c]
                self.tabs.data[table][prefix + c + "?"] = np.ones(len(enc[c]), dtype=bool)
        elif kind == "W":
            _, table, sheet = rec
            self.table(table, src.all_cells(sheet))
        elif kind == "lex":
            _, table, sheet, rr, cc, J = rec
            for name, arr in src.lexical(sheet, rr, cc, J).items():
                self.tabs.data[table][name] = arr
                self.tabs.data[table][name + "?"] = np.ones(len(arr), dtype=bool)
        elif kind == "lexG":
            _, prefix, sheet, rr, cc, J = rec
            for name, arr in src.lexical(sheet, rr, cc, J).items():
                self.tabs.data["G"][prefix + name] = arr
                self.tabs.data["G"][prefix + name + "?"] = np.ones(len(arr), dtype=bool)
        elif kind == "copy":
            _, a, b, sel, comps = rec
            for c in comps:
                self.tabs.data[b][c] = self.tabs.data[a][c][sel]
                self.tabs.data[b][c + "?"] = np.ones(len(sel), dtype=bool)

    def refresh(self, src):
        for rec in self.recipes:
            self.fill(rec, src)

    def _rec_keys(self, i, rec):
        kc = self.__dict__.setdefault("_keys", {})
        if i not in kc:
            if rec[0] == "G":
                rr, cc, bad = rec[3], rec[4], rec[5]
                k = np.asarray(rr, dtype=np.int64) * KEY_SHIFT + np.asarray(cc, dtype=np.int64)
                kc[i] = np.where(np.asarray(bad) > 0, -1, k)
            elif rec[0] == "T":
                kc[i] = np.asarray(rec[4], dtype=np.int64) * KEY_SHIFT + np.asarray(rec[5], dtype=np.int64)
            elif rec[0] in ("lex", "lexG"):
                rr, cc = (rec[3], rec[4])
                kc[i] = np.asarray(rr, dtype=np.int64) * KEY_SHIFT + np.asarray(cc, dtype=np.int64)
        return kc[i]

    def apply_case(self, src):
        """Overlay the changed cells of ``src`` (a CaseSource over this builder's baseline) on the value
        columns; returns the undo list (the baseline is restored by ``undo_case``)."""
        undo = []
        for i, rec in enumerate(self.recipes):
            kind = rec[0]
            if kind in ("G", "T"):
                sheet = rec[2] if kind == "G" else rec[3]
                ch = src.ck.get(sheet.sid)
                if ch is None or not len(ch[0]):
                    continue
                keys = self._rec_keys(i, rec)
                idx = np.nonzero(np.isin(keys, ch[0]))[0]
                if not len(idx):
                    continue
                j = np.searchsorted(ch[0], keys[idx])
                table, prefix = ("G", rec[1]) if kind == "G" else (rec[1], rec[2])
                for ci, c in enumerate(COMPS):
                    col = self.tabs.data[table][prefix + c]
                    undo.append((table, prefix + c, idx, col[idx].copy()))
                    col[idx] = ch[1][j, ci]
            elif kind == "W":
                if rec[2].sid in src.ck:
                    undo.append(("W", rec[1], dict(self.tabs.data[rec[1]]), self.tabs.rows[rec[1]]))
                    self.fill(rec, src)
            elif kind in ("lex", "lexG"):
                sheet = rec[2]
                ch = src.ck.get(sheet.sid)
                if ch is None or not np.isin(self._rec_keys(i, rec), ch[0]).any():
                    continue
                table = rec[1] if kind == "lex" else "G"
                prefix = "" if kind == "lex" else rec[1]
                for name in ["lex.L"] + ["lex.c%d" % j for j in range(rec[5])]:
                    undo.append((table, prefix + name, slice(None), self.tabs.data[table][prefix + name].copy()))
                self.fill(rec, src)
            elif kind == "copy":
                _, a, b, sel, comps = rec
                for c in comps:
                    undo.append((b, c, slice(None), self.tabs.data[b][c].copy()))
                self.fill(rec, src)
        return undo

    def undo_case(self, undo):
        for u in reversed(undo):
            if u[0] == "W":
                self.tabs.data[u[1]] = u[2]
                self.tabs.rows[u[1]] = u[3]
            else:
                table, name, idx, old = u
                self.tabs.data[table][name][idx] = old

    # ---- the tree ---------------------------------------------------------------------------------
    def has_cell(self, node):
        k = node[0]
        if k == "R":
            return True
        if k == "call":
            if node[1] in ("ROW",) and not node[2]:
                return True
            return any(self.has_cell(a) for a in node[2])
        if k in ("neg", "pct"):
            return self.has_cell(node[1])
        if k == "bin":
            return self.has_cell(node[2]) or self.has_cell(node[3])
        return False

    def const_v(self, v):
        t, n, s, k, e, p, q, w, o = self.sd.enc(v)
        integral = isinstance(v, float) and not isinstance(v, bool) and math.isfinite(v) and v == int(v)
        return V({"t": C(t), "n": C(n), "s": C(s), "k": C(k), "e": C(e), "p": C(p), "q": C(q), "w": C(w), "o": C(o)},
                 {t}, integral)

    def fold(self, node):
        """A sub-expression without any cell: a coefficient (evaluated once by the reference evaluator)."""
        ctx = X.Ctx(self.store, self.book, self.sheet_name, int(self.rows[0]), int(self.cols[0]))
        v = X.ev(node, ctx)
        if isinstance(v, list):
            raise Unsupported("constant array")
        if isinstance(v, X.Ref):
            raise Unsupported("constant reference")
        self.notes["coefficient (sub-expression without a cell)"] += 1
        return self.const_v(v)

    def ev(self, node):
        k = node[0]
        if k not in ("R", "const", "empty") and not self.has_cell(node):
            return self.fold(node)
        if k == "const":
            return self.const_v(node[1])
        if k == "R":
            return self.make_ref(node)
        if k == "empty":
            return V({"t": C(T0)}, {T0})
        if k == "neg":
            a, ef, ec = self.to_num(self.val(node[1]))
            return self.num_or_err(self.sp([[EQ(ef, C(1), True), C(-1.0), a]], hint="neg"), ef, ec)
        if k == "pct":
            a, ef, ec = self.to_num(self.val(node[1]))
            return self.num_or_err(self.divide(a, C(100.0), [EQ(ef, C(1), True)]), ef, ec)
        if k == "bin":
            op = node[1]
            a, b = self.val(node[2]), self.val(node[3])
            if op in ("=", "<>", "<", ">", "<=", ">="):
                return self.compare(op, a, b)
            if op == "&":
                raise Unsupported("text concatenation (the two structures have no operation that builds a text)")
            return self.arith(op, a, b, node)
        if k == "call":
            f = getattr(self, "f_" + node[1], None)
            if f is None:
                raise Unsupported("function " + node[1])
            return f(node[2])
        if k == "const_array":
            raise Unsupported("array constant")
        raise Unsupported(k)

    def val(self, node):
        return self.scalar(self.ev(node))

    # ---- operators ---------------------------------------------------------------------------------
    def class_key(self, v, other):
        """(class, key) of a compared value; a blank takes the class of the other side (0 or "")."""
        tv, to = v.op("t"), other.op("t")
        cl = [[EQ(tv, C(T1)), C(1)], [EQ(tv, C(T2)), C(2)], [EQ(tv, C(T3)), C(3)]]
        ky = [[EQ(tv, C(T1)), v.op("n")], [EQ(tv, C(T2)), v.op("k")], [EQ(tv, C(T3)), v.op("n")]]
        cl = [t for t, tt in zip(cl, (T1, T2, T3)) if tt in v.types]
        ky = [t for t, tt in zip(ky, (T1, T2, T3)) if tt in v.types]
        if T0 in v.types:
            b0 = EQ(tv, C(T0))
            for tt, cv in ((T1, 1), (T2, 2), (T3, 3), (T0, 1)):
                if tt in other.types:
                    cl.append([b0, EQ(to, C(tt)), C(cv)])
            if T2 in other.types:
                ky.append([b0, EQ(to, C(T2)), C(self.sd.rank(""))])
        return self.sp(cl, hint="cl"), self.sp(ky, hint="ky")

    def compare(self, op, a, b):
        ef, ec = self.first_error([self.err_of(a), self.err_of(b)])
        ca, ka = self.class_key(a, b)
        cb, kb = self.class_key(b, a)
        ok = EQ(ef, C(1), True)
        same = EQ(ca, cb)
        if op == "=":
            terms = [[ok, same, EQ(ka, kb)]]
        elif op == "<>":
            terms = [[ok, same, EQ(ka, kb, True)], [ok, EQ(ca, cb, True)]]
        elif op == "<":
            terms = [[ok, LE(cb, ca, True)], [ok, same, LE(kb, ka, True)]]
        elif op == ">":
            terms = [[ok, LE(ca, cb, True)], [ok, same, LE(ka, kb, True)]]
        elif op == "<=":
            terms = [[ok, LE(cb, ca, True)], [ok, same, LE(ka, kb)]]
        else:
            terms = [[ok, LE(ca, cb, True)], [ok, same, LE(kb, ka)]]
        return self.bool_or_err(self.sp(terms, hint="cmp"), ef, ec)

    def arith(self, op, av, bv, node=None):
        a, ea, ca = self.to_num(av)
        if op == "^":
            if node is None or self.has_cell(node[3]) or not (bv.types == {T1} and isc(bv.op("n"))):
                raise Unsupported("power with a variable exponent (not a rational function)")
            m = bv.op("n")["const"]
            if (m != int(m) or abs(m) > 64) and self.improve:
                return self.approx_power(a, ea, ca, m)
            if m != int(m) or abs(m) > 64:
                raise Unsupported("power with a non-integer exponent of a variable base (not a rational function)")
            m = int(m)
            if m == 0:
                return self.num_or_err(C(1.0), ea, ca)
            r = self.sp([[EQ(ea, C(1), True)] + [a] * abs(m)], hint="pow")
            if m < 0:
                z = self.sp([[EQ(ea, C(1), True), EQ(r, C(0.0))]], hint="z")
                ef, ec = self.first_error([(ea, ca), (z, C(E_NUM))])
                return self.num_or_err(self.sp([[EQ(ef, C(1), True), {"fn": "inv", "a": r}]], hint="pow"), ef, ec)
            return self.num_or_err(r, ea, ca)
        b, eb, cb = self.to_num(bv)
        if op == "/":
            z = self.sp([[EQ(b, C(0.0))]], hint="z")
            ef, ec = self.first_error([(ea, ca), (eb, cb), (z, C(E_DIV0))])
            return self.num_or_err(self.divide(a, b, [EQ(ef, C(1), True)]), ef, ec)
        ef, ec = self.first_error([(ea, ca), (eb, cb)])
        ok = EQ(ef, C(1), True)
        integral = av.integral and bv.integral
        if op == "+":
            return self.num_or_err(self.sp([[ok, a], [ok, b]], hint="add"), ef, ec, integral)
        if op == "-":
            return self.num_or_err(self.sp([[ok, a], [ok, C(-1.0), b]], hint="sub"), ef, ec, integral)
        if op == "*":
            return self.num_or_err(self.sp([[ok, a, b]], hint="mul"), ef, ec, integral)
        raise Unsupported("operator " + op)

    # ---- division ---------------------------------------------------------------------------------------
    BIN_K = range(-300, 301)

    def ulp(self, q):
        """ulp(q) = 2^(floor(log2|q|) - 52): binary-lattice knot spectrum sum_k [2^k <= |q| < 2^(k+1)] 2^(k-52)."""
        aq = self.sp([[LE(C(0.0), q), q], [LE(C(0.0), q, True), C(-1.0), q]], hint="aq")
        terms = [[LE(C(2.0 ** k), aq), LE(C(2.0 ** (k + 1)), aq, True), C(2.0 ** (k - 52))] for k in self.BIN_K]
        self.notes["knot spectrum: binary lattice sum_k [2^k <= |q|] (ulp of a quotient)"] += 1
        return self.sp(terms, hint="ulp"), aq

    def split(self, x):
        """Veltkamp splitting x = hi + lo (exact), each line one floating-point operation."""
        c = self.sp([[C(134217729.0), x]], hint="vc")
        d = self.sp([[c], [C(-1.0), x]], hint="vd")
        hi = self.sp([[c], [C(-1.0), d]], hint="vh")
        lo = self.sp([[x], [C(-1.0), hi]], hint="vl")
        return hi, lo

    def residual(self, a, b, q):
        """a - b q exactly (Dekker's two-product; exact for a faithful quotient q)."""
        p_ = self.sp([[b, q]], hint="bp")
        bh, bl = self.split(b)
        qh, ql = self.split(q)
        e = self.sp([[bh, qh], [C(-1.0), p_], [bh, ql], [bl, qh], [bl, ql]], hint="be")
        d = self.sp([[a], [C(-1.0), p_]], hint="ap")
        return self.sp([[d], [C(-1.0), e]], hint="rs")

    def divide(self, a, b, ok):
        """a / b under the mask ``ok`` (b != 0). Base method: a * (1/b) (may differ from IEEE a/b by one ulp).
        IMPROVEMENT: the correctly rounded quotient: q0 = a (1/b), then two corrections by one ulp toward
        a/b, decided by the sign and size of the exact residual a - b q (all steps are masked sum-products)."""
        q = self.sp([ok + [a, {"fn": "inv", "a": b}]], hint="div")
        if not self.improve:
            return q
        ab = self.sp([[LE(C(0.0), b), b], [LE(C(0.0), b, True), C(-1.0), b]], hint="ab")
        for _ in range(2):
            u, aq = self.ulp(q)
            r = self.residual(a, b, q)
            half = self.sp([[ab, u, C(0.5)]], hint="hf")
            ar = self.sp([[LE(C(0.0), r), r], [LE(C(0.0), r, True), C(-1.0), r]], hint="ar")
            move = LE(ar, half, True)                                   # |r| > |b| u / 2
            up = self.sp([[LE(C(0.0), r), LE(C(0.0), b)], [LE(C(0.0), r, True), LE(C(0.0), b, True)]], hint="up")  # sign(r b) >= 0
            q = self.sp([[q], [move, EQ(up, C(1.0)), u], [move, EQ(up, C(1.0), True), C(-1.0), u]], hint="dq")
        self.notes["IMPROVEMENT: correctly rounded division (Dekker residual + binary-lattice ulp)"] += 1
        return self.sp([ok + [q]], hint="div")

    # ---- knot spectra -----------------------------------------------------------------------------
    def floor_nonneg(self, x, bits=FLOOR_BITS):
        """floor(x) for x >= 0 by the integer-lattice knot spectrum F(x) = sum_{m>=1}[m <= x],
        evaluated by dyadic bisection (exact). x >= 2^52 is already an integer."""
        big = float(2 ** 52)
        r = self.sp([[LE(C(big), x, True), x]], hint="fr")           # x < 2^52 (else handled below)
        for j in range(bits - 2, -1, -1):
            p = float(2 ** j)
            r = self.sp([[r], [LE(C(p), r), C(-p)]], hint="fb")
        self.notes["knot spectrum: integer lattice sum_m [m <= x] (dyadic, %d steps)" % (bits - 1)] += 1
        return self.sp([[LE(C(big), x, True), x], [LE(C(big), x, True), C(-1.0), r], [LE(C(big), x), x]], hint="fl")

    def floor_any(self, x):
        pos = LE(C(0.0), x)
        neg = LE(C(0.0), x, True)
        ax = self.sp([[pos, x], [neg, C(-1.0), x]], hint="ax")
        f = self.floor_nonneg(ax)
        frac = self.sp([[EQ(f, ax, True)]], hint="fr")
        return self.sp([[pos, f], [neg, C(-1.0), f], [neg, C(-1.0), frac]], hint="flr")

    def trunc(self, v):
        """Truncation toward zero (Excel int() of an index); integral values pass unchanged."""
        if v.integral:
            return v.op("n")
        x = v.op("n")
        if isc(x):
            return C(math.trunc(x["const"]))
        pos = LE(C(0.0), x)
        neg = LE(C(0.0), x, True)
        ax = self.sp([[pos, x], [neg, C(-1.0), x]], hint="ax")
        f = self.floor_nonneg(ax)
        return self.sp([[pos, f], [neg, C(-1.0), f]], hint="tr")

    def decade_half_unit(self, y):
        """0.5 * 10^(E(y) - 14) with E(y) = floor(log10 y) from the decimal-lattice knot spectrum
        E(y) = sum_k [10^k <= y] - const: the half unit of Excel's 15th significant digit."""
        terms = []
        for kk in DEC_K:
            terms.append([LE(C(10.0 ** kk), y), LE(C(10.0 ** (kk + 1)), y, True), C(0.5 * 10.0 ** (kk - 14))])
        self.notes["knot spectrum: decimal lattice sum_k [10^k <= y] (15-digit rounding)"] += 1
        return self.sp(terms, hint="hu")

    # ---- functions: logic -----------------------------------------------------------------------------
    def f_IF(self, args):
        cb, ef, ec = self.to_bool(self.val(args[0]))
        if len(args) > 1:
            yes = self.val(args[1]) if args[1][0] != "empty" else self.const_v(0.0)
        else:
            yes = self.const_v(True)
        if len(args) < 3:
            no = self.const_v(False)
        else:
            no = self.const_v(0.0) if args[2][0] == "empty" else self.val(args[2])
        ok = EQ(ef, C(1), True)
        cases = [([ok, EQ(cb, C(1))], yes), ([ok, EQ(cb, C(1), True)], no)]
        if not isc(ef, 0.0):
            cases.append(([EQ(ef, C(1))], V({"t": C(T4), "e": ec}, {T4})))
        self.notes["condition as exclusive masks (IF)"] += 1
        return self.choose(cases)

    def f_IFERROR(self, args):
        x = self.val(args[0])
        y = self.const_v(0.0) if args[1][0] == "empty" else self.val(args[1])
        tx = x.op("t")
        cases = []
        if T0 in x.types:
            cases.append(([EQ(tx, C(T0))], self.const_v(0.0)))
            okm = [EQ(tx, C(T0), True), EQ(tx, C(T4), True)]
        else:
            okm = [EQ(tx, C(T4), True)]
        cases.append((okm, x))
        if T4 in x.types:
            cases.append(([EQ(tx, C(T4))], y))
        r = self.choose(cases)
        if T4 not in y.types:
            r.types = r.types - {T4}
        if T0 not in y.types:
            r.types = r.types - {T0}
        return r

    def f_ISNUMBER(self, args):
        x = self.val(args[0])
        return V({"t": C(T3), "n": self.sp([[EQ(x.op("t"), C(T1))]], hint="isn")}, {T3})

    def f_ISTEXT(self, args):
        x = self.val(args[0])
        return V({"t": C(T3), "n": self.sp([[EQ(x.op("t"), C(T2))]], hint="ist")}, {T3})

    def f_ISERROR(self, args):
        x = self.val(args[0])
        return V({"t": C(T3), "n": self.sp([[EQ(x.op("t"), C(T4))]], hint="ise")}, {T3})

    def _logic(self, args, mode):
        parts = []
        for a in args:
            x = self.ev(a)
            if isinstance(x, RefS) and not x.single:
                raise Unsupported("AND/OR over a range")
            is_ref = isinstance(x, (RefS, RefD))
            v = self.scalar(x)
            tv = v.op("t")
            ef, ec = self.err_of(v)
            if is_ref:
                seen = self.sp([[EQ(tv, C(T1))], [EQ(tv, C(T3))]], hint="sn")
                b = self.sp([[EQ(tv, C(T1)), EQ(v.op("n"), C(0.0), True)], [EQ(tv, C(T3)), v.op("n")]], hint="b")
            else:
                b, ef, ec = self.to_bool(v)
                seen = self.sp([[EQ(tv, C(T0), True), EQ(ef, C(1), True)]], hint="sn")
            parts.append((b, seen, ef, ec))
        ef, ec = self.first_error([(p[2], p[3]) for p in parts])
        anyseen = self.sp([[p[1]] for p in parts], hint="as")
        if mode == "and":
            cnt = self.sp([[EQ(p[1], C(1)), EQ(p[0], C(1), True)] for p in parts], hint="cf")
            res = self.sp([[EQ(cnt, C(0.0))]], hint="and")
        else:
            cnt = self.sp([[EQ(p[1], C(1)), EQ(p[0], C(1))] for p in parts], hint="ct")
            res = self.sp([[LE(C(1.0), cnt)]], hint="or")
        none = self.sp([[EQ(anyseen, C(0.0))]], hint="nv")
        ef2, ec2 = self.first_error([(ef, ec), (none, C(E_VALUE))])
        return self.bool_or_err(res, ef2, ec2)

    def f_AND(self, args):
        return self._logic(args, "and")

    def f_OR(self, args):
        return self._logic(args, "or")

    # ---- functions: sums ------------------------------------------------------------------------------
    def range_numbers(self, ref, want=("sum",)):
        """Per instance: sum of the numbers in the range, count of numbers, (error flag, first error code)."""
        R, Rc, gref, bad = self.range_tables(ref)
        out = {}
        if "sum" in want:
            s = self.sp([[EQ("t", C(T1)), "n"]], table=Rc, group={"by": "_parent"}, hint="rs")
            out["sum"] = self.sp([[PRESENT(gref), {"col": s, "via": gref}]], hint="rsv")
        if "count" in want:
            c = self.sp([[EQ("t", C(T1))]], table=Rc, group={"by": "_parent"}, hint="rc")
            out["count"] = self.sp([[PRESENT(gref), {"col": c, "via": gref}]], hint="rcv")
        ne = self.sp([[EQ("t", C(T4))]], table=Rc, group={"by": "_parent"}, hint="rne")
        fe = self.match(["_row", C(T4)], Rc, ["_parent", "t"], table=R, hint="rfe")
        fec = self.sp([[PRESENT(fe), {"col": "e", "via": fe}]], table=R, hint="rfc")
        ef = self.sp([[PRESENT(gref), LE(C(1.0), {"col": ne, "via": gref})]], hint="ref")
        ec = self.sp([[PRESENT(gref), {"col": fec, "via": gref}]], hint="rec")
        bf, bc = self.static_bad(bad)
        out["err"] = self.first_error([(bf, bc), (ef, ec)])
        self.notes["grouped sum over a range (sp group by)"] += 1
        return out

    def sum_items(self, args, want=("sum",)):
        items = []
        for a in args:
            if a[0] == "empty":
                continue
            x = self.ev(a)
            if isinstance(x, RefS) and not x.single:
                items.append(self.range_numbers(x, want))
                continue
            if isinstance(x, (RefS, RefD)):
                v = self.scalar(x)
                tv = v.op("t")
                d = {"sum": self.sp([[EQ(tv, C(T1)), v.op("n")]], hint="sn"),
                     "count": self.sp([[EQ(tv, C(T1))]], hint="cn"), "err": self.err_of(v)}
                items.append(d)
                continue
            v = x
            a_, ef, ec = self.to_num(v)
            cnt = self.sp([[EQ(v.op("t"), C(T0), True)]], hint="cn") if T0 in v.types else C(1.0)
            items.append({"sum": a_, "count": cnt, "err": (ef, ec)})
        return items

    def f_SUM(self, args):
        items = self.sum_items(args)
        ef, ec = self.first_error([it["err"] for it in items])
        r = self.sp([[EQ(ef, C(1), True), it["sum"]] for it in items], hint="sum")
        return self.num_or_err(r, ef, ec)

    def f_AVERAGE(self, args):
        items = self.sum_items(args, ("sum", "count"))
        ef, ec = self.first_error([it["err"] for it in items])
        s = self.sp([[it["sum"]] for it in items], hint="sum")
        n = self.sp([[it["count"]] for it in items], hint="cnt")
        z = self.sp([[EQ(n, C(0.0))]], hint="z")
        ef2, ec2 = self.first_error([(ef, ec), (z, C(E_DIV0))])
        return self.num_or_err(self.divide(s, n, [EQ(ef2, C(1), True)]), ef2, ec2)

    def pairs_table(self, Rc):
        """All ordered pairs (a, b) of cells of the same range (a product index set), child of Rc."""
        key = ("pairs", Rc)
        if key in self.memo:
            return self.memo[key]
        par = self.tabs.data[Rc]["_parent"].astype(np.int64)
        aa, bb = [], []
        for g in np.unique(par):
            idx = np.nonzero(par == g)[0]
            a, b = np.meshgrid(idx, idx, indexing="ij")
            aa.append(a.ravel()); bb.append(b.ravel())
        aa = np.concatenate(aa) if aa else np.zeros(0)
        bb = np.concatenate(bb) if bb else np.zeros(0)
        if len(aa) > 5_000_000:
            raise Unsupported("pair table too large")
        P = Rc + ".pp"
        self.table(P, {"_parent": aa, "b": bb})
        rb = self.match(["b"], Rc, ["_row"], table=P, hint="rb")
        self.memo[key] = (P, rb)
        return P, rb

    def f_MAX(self, args):
        if len(args) != 1:
            raise Unsupported("MAX of several arguments")
        x = self.ev(args[0])
        if not isinstance(x, RefS) or x.single:
            raise Unsupported("MAX form")
        R, Rc, gref, bad = self.range_tables(x)
        P, rb = self.pairs_table(Rc)
        gt = self.sp([[EQ({"col": "t", "via": "_parent"}, C(T1)), EQ({"col": "t", "via": rb}, C(T1)),
                       LE({"col": "n", "via": rb}, {"col": "n", "via": "_parent"}, True)]], table=P, group={"by": "_parent"}, hint="gt")
        top = self.sp([[EQ("t", C(T1)), EQ(gt, C(0.0))]], table=Rc, hint="top")
        first = self.match(["_row", C(1.0)], Rc, ["_parent", top], table=R, hint="mx")
        mv = self.sp([[PRESENT(first), {"col": "n", "via": first}]], table=R, hint="mv")
        nums = self.range_numbers(x, ())
        ef, ec = nums["err"]
        r = self.sp([[EQ(ef, C(1), True), PRESENT(gref), {"col": mv, "via": gref}]], hint="max")
        self.notes["maximum as the element with no larger element (pair table, match)"] += 1
        return self.num_or_err(r, ef, ec)

    # ---- functions: rounding (knot spectra) -------------------------------------------------------------
    def _digits(self, args):
        if len(args) < 2:
            return 0
        d = self.val(args[1]) if self.has_cell(args[1]) else None
        if d is not None:
            raise Unsupported("rounding digits given by a cell")
        dv = X.to_num(X.ev(args[1], X.Ctx(self.store, self.book, self.sheet_name, 1, 1)))
        if isinstance(dv, Err):
            raise Unsupported("rounding digits are an error")
        return int(math.trunc(dv))

    def _round(self, args, mode):
        d = self._digits(args)
        x, ef, ec = self.to_num(self.val(args[0]))
        pos, neg = LE(C(0.0), x), LE(C(0.0), x, True)
        if d >= 0:
            scale = C(10.0 ** d)
            y = self.sp([[pos, x, scale], [neg, C(-1.0), x, scale]], hint="ay")
        else:
            y = self.sp([[pos, x, {"fn": "inv", "a": C(10.0 ** (-d))}], [neg, C(-1.0), x, {"fn": "inv", "a": C(10.0 ** (-d))}]], hint="ay")
        hu = self.decade_half_unit(y)
        # |x| 10^d >= 10^14: the 15-digit grid is not finer than the integers; the value is the nearest
        # multiple of u = 10^(E(y)-14) (exact halves rounded up), then nothing is left to round
        bigk = range(14, 308)
        u = self.sp([[LE(C(10.0 ** k), y), LE(C(10.0 ** (k + 1)), y, True), C(10.0 ** (k - 14))] for k in bigk], hint="u")
        isbig = LE(C(1e14), y)
        qb = self.divide(y, self.sp([[isbig, u], [LE(C(1e14), y, True), C(1.0)]], hint="uu"), [isbig])
        mb = self.sp([[isbig, self.floor_nonneg(self.sp([[isbig, qb], [isbig, C(0.5)]], hint="qh")), u]], hint="mb")
        self.notes["15-digit rounding of magnitudes >= 1e14 (nearest multiple of 10^(E-14))"] += 1
        if mode == "round":
            m = self.floor_nonneg(self.sp([[y], [C(0.5)], [hu]], hint="z"))
        elif mode == "down":
            m = self.floor_nonneg(self.sp([[y], [hu]], hint="z"))
        else:
            z = self.sp([[y], [C(-1.0), hu]], hint="z")
            zp = self.sp([[LE(C(0.0), z), z]], hint="zp")
            f = self.floor_nonneg(zp)
            m = self.sp([[f], [EQ(f, zp, True), C(1.0)]], hint="ce")
        m = self.sp([[LE(C(1e14), y, True), m], [LE(C(1e14), y), mb]], hint="mm")
        okm = [EQ(ef, C(1), True)]
        if d >= 0:
            mq = self.divide(m, C(10.0 ** d), okm)
        else:
            mq = self.sp([okm + [m, C(10.0 ** (-d))]], hint="mq")
        r = self.sp([okm + [pos, mq], okm + [neg, C(-1.0), mq]], hint="rnd")
        return self.num_or_err(r, ef, ec, d <= 0)

    def f_ROUND(self, args):
        return self._round(args, "round")

    def f_ROUNDDOWN(self, args):
        return self._round(args, "down")

    def f_ROUNDUP(self, args):
        return self._round(args, "up")

    def f_INT(self, args):
        x, ef, ec = self.to_num(self.val(args[0]))
        return self.num_or_err(self.sp([[EQ(ef, C(1), True), self.floor_any(x)]], hint="int"), ef, ec, True)

    def f_MOD(self, args):
        a, ea, ca = self.to_num(self.val(args[0]))
        b, eb, cb = self.to_num(self.val(args[1]))
        z = self.sp([[EQ(b, C(0.0))]], hint="z")
        ef, ec = self.first_error([(ea, ca), (eb, cb), (z, C(E_DIV0))])
        ok = EQ(ef, C(1), True)
        q = self.divide(a, b, [ok])
        f = self.floor_any(q)
        r = self.sp([[ok, a], [ok, C(-1.0), b, f]], hint="r")
        d = self.sp([[r], [C(-1.0), b]], hint="d")
        ad = self.sp([[LE(C(0.0), d), d], [LE(C(0.0), d, True), C(-1.0), d]], hint="ad")
        ab = self.sp([[LE(C(0.0), b), b], [LE(C(0.0), b, True), C(-1.0), b]], hint="ab")
        tol = self.sp([[ab, C(1e-15)]], hint="tl")
        snap = self.sp([[EQ(r, C(0.0), True), LE(tol, ad, True)]], hint="sn")
        res = self.sp([[EQ(snap, C(1), True), r]], hint="mod")
        return self.num_or_err(res, ef, ec)

    def f_ABS(self, args):
        x, ef, ec = self.to_num(self.val(args[0]))
        r = self.sp([[EQ(ef, C(1), True), LE(C(0.0), x), x], [EQ(ef, C(1), True), LE(C(0.0), x, True), C(-1.0), x]], hint="abs")
        return self.num_or_err(r, ef, ec)

    def f_POWER(self, args):
        return self.arith("^", self.val(args[0]), self.val(args[1]), ("bin", "^", args[0], args[1]))

    def f_LOG10(self, args):
        if not self.improve:
            raise Unsupported("logarithm of a variable (transcendental; not a rational function)")
        x, ef, ec = self.to_num(self.val(args[0]))
        bad = self.sp([[EQ(ef, C(1.0), True), LE(x, C(0.0))]], hint="nb")
        ef2, ec2 = self.first_error([(ef, ec), (bad, C(E_NUM))])
        dec, ym = self.mantissa_poly(x, lambda u: np.log10(u))
        r = self.sp([[EQ(ef2, C(1.0), True), dec], [EQ(ef2, C(1.0), True), ym]], hint="lg")
        self.notes["APPROXIMATION: log10 = decade (decimal-lattice knot spectrum) + piecewise polynomial of the mantissa"] += 1
        return self.num_or_err(r, ef2, ec2)

    APPROX_PIECES, APPROX_DEG = 24, 12

    def mantissa_poly(self, x, fn, decade_value=None):
        """For x > 0: the decade E(x) = sum_k [10^k <= x] - 41 (knot spectrum on the decimal lattice) and a
        piecewise polynomial of fn on the mantissa m = x 10^-E in [1, 10) (interval form of a knot spectrum,
        Chebyshev interpolation on every piece). Returns (decade or decade_value(E) operand, fn(m) operand)."""
        Ks = list(range(-40, 41))
        e = self.sp([[LE(C(10.0 ** k), x)] for k in Ks] + [[C(-41.0)]], hint="dec")
        if decade_value is None:
            dv = e
        else:
            dv = self.sp([[LE(C(10.0 ** k), x), LE(C(10.0 ** (k + 1)), x, True), C(decade_value(k))] for k in Ks], hint="dv")
        mm = self.sp([[LE(C(10.0 ** k), x), LE(C(10.0 ** (k + 1)), x, True), x, C(10.0 ** (-k))] for k in Ks], hint="mt")
        P, D = self.APPROX_PIECES, self.APPROX_DEG
        edges = np.geomspace(1.0, 10.0, P + 1)
        tt, terms = [], []
        for k in range(P):
            lo_, hi_ = edges[k], edges[k + 1]
            c_, h_ = (lo_ + hi_) / 2, (hi_ - lo_) / 2
            mask = ([LE(C(lo_), mm)] if k > 0 else []) + ([LE(C(hi_), mm, True)] if k < P - 1 else [])
            tt.append(mask + [mm, C(1.0 / h_)])
            tt.append(mask + [C(-c_ / h_)])
            nodes = np.cos(np.pi * (np.arange(D + 1) + 0.5) / (D + 1))
            coef = np.polynomial.chebyshev.chebfit(nodes, fn(c_ + h_ * nodes), D)
            poly = np.polynomial.chebyshev.cheb2poly(coef)
            for j, a_ in enumerate(poly):
                terms.append(mask + [C(float(a_))] + ["@t"] * j)
        t = self.sp(tt, hint="tt")
        terms = [[t if f == "@t" else f for f in term] for term in terms]
        ym = self.sp(terms, hint="pm")
        return dv, ym

    def approx_power(self, a, ea, ca, m):
        """IMPROVEMENT (approximation, not exact): x^m for a non-integer constant m:
        x > 0: 10^(E m) * poly(mantissa); x = 0: 0 (m > 0) or #DIV/0! (m < 0); x < 0: #NUM!."""
        neg = self.sp([[EQ(ea, C(1.0), True), LE(C(0.0), a, True)]], hint="ng")
        zero_neg = self.sp([[EQ(ea, C(1.0), True), EQ(a, C(0.0))]], hint="zr") if m < 0 else C(0)
        ef, ec = self.first_error([(ea, ca), (neg, C(E_NUM)), (zero_neg, C(E_DIV0))])
        dv, ym = self.mantissa_poly(a, lambda u: u ** m, decade_value=lambda k: 10.0 ** (k * m))
        pos = LE(C(0.0), a, True) if False else LE(a, C(0.0), True)
        r = self.sp([[EQ(ef, C(1.0), True), pos, dv, ym]], hint="pw")
        self.notes["APPROXIMATION: x^m = 10^(E m) (decimal-lattice knot spectrum) x piecewise polynomial of the mantissa"] += 1
        return self.num_or_err(r, ef, ec)

    def f_SUBSTITUTE(self, args):
        raise Unsupported("text substitution (the two structures have no operation that builds a text)")

    def f_LEFT(self, args):
        raise Unsupported("part of a text (the two structures have no operation that builds a text)")

    def f_VALUE(self, args):
        a0 = args[0]
        if a0[0] == "call" and a0[1] == "LEFT" and self.improve:
            return self.value_left(a0[2])
        v = self.val(args[0])
        tv = v.op("t")
        vt, et, ct = [], [], []
        if T1 in v.types:
            vt.append([EQ(tv, C(T1)), v.op("n")])
        if T2 in v.types:
            vt.append([EQ(tv, C(T2)), EQ(v.op("q"), C(1)), v.op("p")])
            et.append([EQ(tv, C(T2)), EQ(v.op("q"), C(1), True)])
            ct.append([EQ(tv, C(T2)), EQ(v.op("q"), C(1), True), C(E_VALUE)])
        for tt in (T0, T3):
            if tt in v.types:
                et.append([EQ(tv, C(tt))])
                ct.append([EQ(tv, C(tt)), C(E_VALUE)])
        if T4 in v.types:
            et.append([EQ(tv, C(T4))])
            ct.append([EQ(tv, C(T4)), v.op("e")])
        return self.num_or_err(self.sp(vt, hint="val") if vt else C(0), self.sp(et, hint="ef") if et else C(0),
                               self.sp(ct, hint="ec") if ct else C(0))

    def value_left(self, largs):
        """IMPROVEMENT (domain: integers |x| < 10^15): VALUE(LEFT(x, n)) for a number x and a constant n:
        the number read from the first n characters of the text of x. With d = number of digits of |x|
        (decimal-lattice knot spectrum): |x| itself when d <= n' (n' = n, or n - 1 for the minus sign),
        else floor(|x| / 10^(d - n')) (integer-lattice knot spectrum, exact by a correction step).
        A logical gives #VALUE!; a non-integer number or a text is outside the domain -> missing."""
        if len(largs) < 2 or self.has_cell(largs[1]):
            raise Unsupported("LEFT with a computed length")
        n = int(X.to_num(X.ev(largs[1], X.Ctx(self.store, self.book, self.sheet_name, 1, 1))))
        x0 = self.ev(largs[0])
        v = self.scalar(x0)
        tv = v.op("t")
        text_val = None
        if isinstance(x0, RefS) and x0.single and n >= 1:
            # text branch: the first n characters must all be digits (ASCII or full-width)
            pre = self.nm("lx") + "."
            rec = ("lexG", pre, x0.sheet, np.where(x0.bad > 0, 1, x0.r1), np.where(x0.bad > 0, 1, x0.c1), n)
            self.recipes.append(rec)
            self.fill(rec, self.cache)
            Lc = pre + "lex.L"
            dig, isd = [], []
            for j in range(n):
                cj = pre + "lex.c%d" % j
                dig.append(self.sp([[LE(C(48.0), cj), LE(cj, C(57.0)), cj], [LE(C(48.0), cj), LE(cj, C(57.0)), C(-48.0)],
                                    [LE(C(65296.0), cj), LE(cj, C(65305.0)), cj], [LE(C(65296.0), cj), LE(cj, C(65305.0)), C(-65296.0)]], hint="dg"))
                isd.append(self.sp([[LE(C(48.0), cj), LE(cj, C(57.0))], [LE(C(65296.0), cj), LE(cj, C(65305.0))]], hint="isd"))
            terms, okt = [], []
            for ln in range(1, n + 1):
                cond = [LE(C(float(ln)), Lc), LE(Lc, C(float(ln)))] if ln < n else [LE(C(float(n)), Lc)]
                okt.append(cond + [EQ(self.sp([[EQ(isd[j], C(1.0), True)] for j in range(ln)], hint="nd"), C(0.0))])
                for j in range(ln):
                    terms.append(cond + [dig[j], C(10.0 ** (ln - 1 - j))])
            text_val = self.sp(terms, hint="tv")
            text_ok = self.sp(okt, hint="tok")
            self.notes["IMPROVEMENT: digits of a text from its lexical companions"] += 1
        x = self.sp([[EQ(tv, C(T1)), v.op("n")]], hint="x")
        f = self.floor_any(x)
        integral = self.sp([[EQ(f, x)]], hint="ig")
        neg = LE(C(0.0), x, True)
        ax = self.sp([[LE(C(0.0), x), x], [neg, C(-1.0), x]], hint="ax")
        digits = self.sp([[LE(C(10.0 ** k), ax)] for k in range(0, 15)], hint="nd")      # 0 for x = 0 ("0" has 1 char)
        def lead(nn):
            """first nn digits of the integer ax (nn >= 1)."""
            terms = [[LE(digits, C(float(nn))), ax]]
            for d in range(nn + 1, 16):
                k = d - nn
                q0 = self.floor_nonneg(self.sp([[ax, {"fn": "inv", "a": C(10.0 ** k)}]], hint="qd"))
                # exact floor division: correct by one when q0 * 10^k > ax or (q0 + 1) * 10^k <= ax
                q = self.sp([[q0], [LE(self.sp([[q0, C(10.0 ** k)]], hint="qa"), ax, True), C(-1.0)],
                             [LE(self.sp([[q0, C(10.0 ** k)], [C(10.0 ** k)]], hint="qb"), ax), C(1.0)]], hint="q")
                terms.append([EQ(digits, C(float(d))), q])
            return self.sp(terms, hint="ld")
        pos_val = lead(n) if n >= 1 else C(0.0)
        neg_val = lead(n - 1) if n >= 2 else C(0.0)
        r = self.sp([[EQ(tv, C(T1)), LE(C(0.0), x), pos_val], [EQ(tv, C(T1)), neg, C(-1.0), neg_val]] +
                    ([[EQ(tv, C(T2)), EQ(text_ok, C(1.0)), text_val]] if text_val is not None else []), hint="vl")
        bad_t = [[EQ(tv, C(T3))], [EQ(tv, C(T0))]] + ([[EQ(tv, C(T1)), neg]] if n < 2 else []) + ([[EQ(tv, C(T1))]] if n < 1 else [])
        ef0 = self.sp(bad_t, hint="ef")
        ef, ec = self.first_error([self.err_of(v), (ef0, C(E_VALUE))])
        out = self.num_or_err(self.sp([[EQ(ef, C(1.0), True), r]], hint="vv"), ef, ec)
        outside = self.sp([[EQ(tv, C(T2))] + ([EQ(text_ok, C(1.0), True)] if text_val is not None else []),
                           [EQ(tv, C(T1)), EQ(integral, C(1.0), True)], [EQ(tv, C(T1)), LE(C(1e15), ax)]], hint="od")
        out.c["t"] = self.mark_missing(out.op("t"), outside)
        self.notes["IMPROVEMENT: VALUE(LEFT(x, n)) of an integer by decimal/integer-lattice knot spectra"] += 1
        return out

    def f_SINGLE(self, args):
        return self.val(args[0])

    def f_ROW(self, args):
        if not args:
            return V({"t": C(T1), "n": "_r"}, {T1}, True)
        x = self.ev(args[0])
        if not isinstance(x, RefS):
            return self.errv(E_VALUE)
        return V({"t": C(T1), "n": self.gcol("row", x.r1)}, {T1}, True)

    # ---- functions: look-ups -------------------------------------------------------------------------------
    def key_line(self, ref, horizontal, kind):
        """Key line of a range (first column, first row, or all cells in order) as a child table of R:
        _parent (range), pos, cls (1 number, 2 text, 3 logical, 0 blank/error), key, nb (cls >= 1), w."""
        R, Rc, gref, bad = self.range_tables(ref, truncate=(kind != "approx"))
        mk = ("kl", R, horizontal, kind)
        if mk in self.memo:
            return self.memo[mk]
        d = self.tabs.data[Rc]
        if kind == "all":
            sel = np.ones(len(d["i"]), dtype=bool)
            posv = np.zeros(len(d["i"]))
            # row-major position within its range
            par = d["_parent"].astype(np.int64)
            first = {}
            for idx in range(len(par)):
                posv[idx] = idx - first.setdefault(par[idx], idx)
        else:
            sel = (d["i"] == 0) if horizontal else (d["j"] == 0)
            posv = d["j"] if horizontal else d["i"]
        KL = R + ".k" + ("h" if horizontal else "v") + kind[0]
        cols = {"_parent": d["_parent"][sel], "pos": posv[sel]}
        self.table(KL, cols)
        rec = ("copy", Rc, KL, np.nonzero(sel)[0], ("t", "n", "k", "w"))
        self.recipes.append(rec)
        self.fill(rec, self.cache)
        tt = "t"
        cls = self.sp([[EQ(tt, C(T1)), C(1)], [EQ(tt, C(T2)), C(2)], [EQ(tt, C(T3)), C(3)]], table=KL, hint="kc")
        key = self.sp([[EQ(tt, C(T1)), "n"], [EQ(tt, C(T2)), "k"], [EQ(tt, C(T3)), "n"]], table=KL, hint="kk")
        # rows with no key (blank, error) must never match: their class 0 is not a key class
        out = (R, Rc, gref, bad, KL, cls, key)
        self.memo[mk] = out
        return out

    def key_of(self, v, blank):
        """(class, key, wildcard flag) of a look-up value. ``blank``: class for a blank value (None = no match)."""
        tv = v.op("t")
        cl = [[EQ(tv, C(T1)), C(1)], [EQ(tv, C(T2)), C(2)], [EQ(tv, C(T3)), C(3)]]
        if blank is not None:
            cl.append([EQ(tv, C(T0)), C(blank)])
        cls = self.sp(cl, hint="lc")
        key = self.sp([[EQ(tv, C(T1)), v.op("n")], [EQ(tv, C(T2)), v.op("k")], [EQ(tv, C(T3)), v.op("n")]], hint="lk")
        wild = self.sp([[EQ(tv, C(T2)), EQ(v.op("w"), C(1))]], hint="wd") if T2 in v.types else C(0)
        return cls, key, wild

    def exact_pos(self, KL, cls, key, gref, rid_col, kcls, kkey):
        m = self.match([rid_col, kcls, kkey], KL, ["_parent", cls, key], hint="ex")
        pos = self.sp([[PRESENT(m), {"col": "pos", "via": m}], [PRESENT(m, True), C(-1.0)]], hint="pos")
        self.notes["exact look-up (match: first row with equal keys)"] += 1
        return pos

    def approx_pos(self, KL, cls, key, R, gref, kcls, kkey):
        """Excel's approximate look-up: its binary search, step by step (each step: masks, a floor of the
        mid point by the integer-lattice knot spectrum, and keyed matches). Stops at an equal value;
        a blank/error at the mid point is replaced by the nearest non-blank to its left within [lo, mid]."""
        kld = self.tabs.data[KL]
        P = KL + ".pp"
        par = kld["_parent"].astype(np.int64)
        aa, bb = [], []
        for g in np.unique(par):
            idx = np.nonzero(par == g)[0]
            a, b = np.meshgrid(idx, idx, indexing="ij")
            keep = b <= a
            aa.append(a[keep]); bb.append(b[keep])
        self.table(P, {"_parent": np.concatenate(aa) if aa else np.zeros(0), "b": np.concatenate(bb) if bb else np.zeros(0)})
        rb = self.match(["b"], KL, ["_row"], table=P, hint="rb")
        nb = self.sp([[LE(C(1.0), cls)]], table=KL, hint="nb")
        ordc = self.sp([[EQ({"col": nb, "via": rb}, C(1.0))]], table=P, group={"by": "_parent"}, hint="ord")
        pm = self.match(["_parent", ordc, C(1.0)], KL, ["_parent", ordc, nb], table=KL, hint="pnb")
        pnb = self.sp([[PRESENT(pm), {"col": "pos", "via": pm}], [PRESENT(pm, True), C(-1.0)]], table=KL, hint="pnbp")
        self.notes["knot spectrum: running count along the vector sum_{q<=p}[nonblank(q)]"] += 1
        maxlen = int(np.max(np.bincount(par))) if len(par) else 1
        L = max(1, int(math.floor(math.log2(maxlen))) + 2)
        bits = max(2, int(math.ceil(math.log2(2 * maxlen + 2))) + 1)
        rid = self.sp([[PRESENT(gref), gref]], hint="rid")
        cnt = self.sp([[C(1.0)]], table=KL, group={"by": "_parent"}, hint="cnt")
        lo, hi = C(0.0), self.sp([[PRESENT(gref), {"col": cnt, "via": gref}], [C(-1.0)]], hint="hi")
        best, done, res = C(-1.0), C(0.0), C(-1.0)
        for it in range(L):
            act = [EQ(done, C(1.0), True), LE(lo, hi)]
            s = self.sp([act + [lo, C(0.5)], act + [hi, C(0.5)]], hint="hs")
            mid = self.floor_nonneg(s, bits)
            mref = self.match([rid, mid], KL, ["_parent", "pos"], hint="mid")
            pmv = self.sp([[PRESENT(mref), {"col": pnb, "via": mref}], [PRESENT(mref, True), C(-1.0)]], hint="pm")
            vref = self.match([rid, pmv], KL, ["_parent", "pos"], hint="vr")
            vc = self.sp([[PRESENT(vref), {"col": cls, "via": vref}]], hint="vc")
            vk = self.sp([[PRESENT(vref), {"col": key, "via": vref}]], hint="vk")
            empty = LE(lo, pmv, True)                       # pm < lo
            ne = LE(lo, pmv)
            dlt = [ne, EQ(vc, kcls, True), LE(kcls, vc, True)]        # vc < kc
            dgt = [ne, EQ(vc, kcls, True), LE(vc, kcls, True)]        # vc > kc
            eq_ = [ne, EQ(vc, kcls), EQ(vk, kkey)]
            lt = [ne, EQ(vc, kcls), LE(kkey, vk, True)]               # vk < key
            gt = [ne, EQ(vc, kcls), LE(vk, kkey, True)]               # vk > key
            inact = [[EQ(done, C(1.0))], [EQ(done, C(1.0), True), LE(lo, hi, True)]]
            up = lambda cond, val: act + cond + [val]
            nlo = self.sp([t + [lo] for t in inact] + [up([empty], mid), up([empty], C(1.0)), up(dlt, mid), up(dlt, C(1.0)),
                                                        up(lt, mid), up(lt, C(1.0)), up(dgt, lo), up(eq_, lo), up(gt, lo)], hint="lo")
            nhi = self.sp([t + [hi] for t in inact] + [up([empty], hi), up(dlt, hi), up(lt, hi), up(dgt, pmv), up(dgt, C(-1.0)),
                                                        up(eq_, hi), up(gt, pmv), up(gt, C(-1.0))], hint="hi")
            nbest = self.sp([t + [best] for t in inact] + [up([empty], best), up(dlt, best), up(dgt, best), up(eq_, best),
                                                            up(gt, best), up(lt, pmv)], hint="be")
            ndone = self.sp([t + [done] for t in inact] + [up(eq_, C(1.0))], hint="dn")
            nres = self.sp([t + [res] for t in inact] + [up(eq_, pmv)], hint="rs")
            lo, hi, best, done, res = nlo, nhi, nbest, ndone, nres
        unfinished = self.sp([[EQ(done, C(1.0), True), LE(lo, hi)]], hint="uf")
        pos = self.sp([[EQ(done, C(1.0)), res], [EQ(done, C(1.0), True), best]], hint="ap")
        self.notes["binary search of the approximate look-up (%d fixed steps)" % L] += 1
        return pos, unfinished

    def lookup_value(self, Rc, rid, i, j):
        cell = self.match([rid, i, j], Rc, ["_parent", "i", "j"], hint="cell")
        return cell

    def result_of(self, cell, ef, ec, blank_to_zero=True, extra_fail=None):
        ok = EQ(ef, C(1), True)
        comps = {}
        for c in COMPS:
            o = {"col": c, "via": cell}
            if c == "t":
                terms = [[ok, PRESENT(cell), EQ(o, C(T0), True), o], [EQ(ef, C(1)), C(T4)]]
                if blank_to_zero:
                    terms.append([ok, PRESENT(cell), EQ(o, C(T0)), C(T1)])
            elif c == "e":
                terms = [[ok, PRESENT(cell), o], [EQ(ef, C(1)), ec]]
            else:
                terms = [[ok, PRESENT(cell), o]]
            comps[c] = self.sp(terms, hint="r" + c)
        if extra_fail is not None:
            comps["t"] = self.mark_missing(comps["t"], extra_fail)
        return V(comps, ALL)

    def f_VLOOKUP(self, args, horizontal=False):
        key = self.val(args[0])
        x = self.ev(args[1])
        if isinstance(x, V):
            raise Unsupported("look-up table is not a reference")
        if isinstance(x, RefD):
            raise Unsupported("look-up table at a computed position")
        approx = True
        if len(args) > 3:
            a3 = args[3]
            if a3[0] == "empty":
                approx = False
            elif not self.has_cell(a3):
                av = X.to_bool(X.ev(a3, X.Ctx(self.store, self.book, self.sheet_name, 1, 1)))
                if isinstance(av, Err):
                    raise Unsupported("look-up mode is an error")
                approx = bool(av)
            else:
                raise Unsupported("look-up mode given by a cell")
        idx = self.val(args[2])
        iv, ief, iec = self.to_num(idx)
        it = self.trunc(V({"n": iv}, {T1}, idx.integral)) if not isc(iv) else C(math.trunc(iv["const"]))
        R, Rc, gref, bad, KL, cls, kk = self.key_line(x, horizontal, "approx" if approx else "exact")
        width = self.sp([[PRESENT(gref), {"col": ("h" if horizontal else "wd"), "via": gref}]], hint="wd")
        kef, kec = self.err_of(key)
        bf, bc = self.static_bad(bad)
        kcls, kkey, wild = self.key_of(key, 1)           # blank key -> 0 (number)
        rid = self.sp([[PRESENT(gref), gref]], hint="rid")
        if approx:
            pos, unfinished = self.approx_pos(KL, cls, kk, R, gref, kcls, kkey)
        else:
            pos = self.exact_pos(KL, cls, kk, gref, rid, kcls, kkey)
            unfinished = wild
        small = self.sp([[LE(C(1.0), it, True)]], hint="i1")
        big = self.sp([[LE(it, width, True)]], hint="iw")
        na = self.sp([[LE(C(0.0), pos, True)]], hint="na")
        ef, ec = self.first_error([(kef, kec), (bf, bc), (ief, iec), (small, C(E_VALUE)), (big, C(E_REF)), (na, C(E_NA))])
        im1 = self.sp([[it], [C(-1.0)]], hint="im")
        cell = self.lookup_value(Rc, rid, im1, pos) if horizontal else self.lookup_value(Rc, rid, pos, im1)
        self.notes["look-up result cell (match on position)"] += 1
        return self.result_of(cell, ef, ec, True, None if isc(unfinished, 0.0) else unfinished)

    def f_HLOOKUP(self, args):
        return self.f_VLOOKUP(args, True)

    def f_LOOKUP(self, args):
        key = self.val(args[0])
        vec = self.ev(args[1])
        if len(args) < 3:
            raise Unsupported("LOOKUP with two arguments")
        res = self.ev(args[2])
        if not isinstance(vec, RefS) or not isinstance(res, RefS):
            raise Unsupported("LOOKUP form")
        R, Rc, gref, bad, KL, cls, kk = self.key_line(vec, False, "all")
        kef, kec = self.err_of(key)
        kcls, kkey, wild = self.key_of(key, 0)            # blank key: class 0 (below every key class)
        pos, unfinished = self.approx_pos(KL, cls, kk, R, gref, kcls, kkey)
        bf, bc = self.static_bad(bad)
        R2, Rc2, gref2, bad2 = self.range_tables(res, truncate=True)
        self.row_major(Rc2)
        rid2 = self.sp([[PRESENT(gref2), gref2]], hint="rid")
        cell = self.match([rid2, pos], Rc2, ["_parent", "rm"], hint="cell")
        b2f, b2c = self.static_bad(bad2)
        na = self.sp([[LE(C(0.0), pos, True)]], hint="na")
        beyond = self.sp([[LE(C(0.0), pos), PRESENT(cell, True)]], hint="by")
        ef, ec = self.first_error([(kef, kec), (bf, bc), (b2f, b2c), (na, C(E_NA)), (beyond, C(E_NA))])
        return self.result_of(cell, ef, ec, True, None if isc(unfinished, 0.0) else unfinished)

    def row_major(self, Rc):
        """Position of every cell in row-major order within its range (formula geometry)."""
        mk = ("rowmajor", Rc)
        if mk not in self.memo:
            d = self.tabs.data[Rc]
            par = d["_parent"].astype(np.int64)
            posv = np.zeros(len(par))
            first = {}
            for idx in range(len(par)):
                posv[idx] = idx - first.setdefault(par[idx], idx)
            d["rm"] = posv
            d["rm?"] = np.ones(len(par), dtype=bool)
            self.memo[mk] = True

    def f_MATCH(self, args):
        key = self.val(args[0])
        x = self.ev(args[1])
        if not isinstance(x, RefS):
            return self.errv(E_NA)
        mt = 1.0
        if len(args) > 2:
            if args[2][0] == "empty":
                mt = 0.0
            elif self.has_cell(args[2]):
                raise Unsupported("MATCH type given by a cell")
            else:
                mt = X.to_num(X.ev(args[2], X.Ctx(self.store, self.book, self.sheet_name, 1, 1)))
        if mt != 0:
            raise Unsupported("MATCH approximate")
        R, Rc, gref, bad, KL, cls, kk = self.key_line(x, False, "all")
        kef, kec = self.err_of(key)
        kcls, kkey, wild = self.key_of(key, None)
        rid = self.sp([[PRESENT(gref), gref]], hint="rid")
        pos = self.exact_pos(KL, cls, kk, gref, rid, kcls, kkey)
        bf, bc = self.static_bad(bad)
        blank = self.sp([[EQ(key.op("t"), C(T0))]], hint="kb") if T0 in key.types else C(0)
        na = self.sp([[LE(C(0.0), pos, True)]], hint="na")
        ef, ec = self.first_error([(kef, kec), (bf, bc), (blank, C(E_NA)), (na, C(E_NA))])
        r = self.sp([[EQ(ef, C(1), True), pos], [EQ(ef, C(1), True), C(1.0)]], hint="mt")
        out = self.num_or_err(r, ef, ec, True)
        if not isc(wild, 0.0):
            out.c["t"] = self.mark_missing(out.op("t"), wild)
        return out

    def f_INDEX(self, args):
        x = self.ev(args[0])
        if not isinstance(x, RefS):
            return self.errv(E_VALUE)
        n = self.n
        h = (x.r2 - x.r1 + 1)
        w = (x.c2 - x.c1 + 1)
        if not (np.all(h == h[0]) and np.all(w == w[0])):
            raise Unsupported("INDEX of ranges of different shapes")
        h, w = int(h[0]), int(w[0])
        rv = self.val(args[1]) if len(args) > 1 and args[1][0] != "empty" else self.const_v(0.0)
        cv = self.val(args[2]) if len(args) > 2 and args[2][0] != "empty" else self.const_v(0.0)
        r, rf, rc = self.to_num(rv)
        c, cf, cc = self.to_num(cv)
        rt = self.trunc(V({"n": r}, {T1}, rv.integral)) if not isc(r) else C(int(r["const"]))
        ct = self.trunc(V({"n": c}, {T1}, cv.integral)) if not isc(c) else C(int(c["const"]))
        if h == 1 and len(args) == 2:
            rt, ct = C(1.0), rt
        if isc(rt) and isc(ct):
            ri, ci = int(rt["const"]), int(ct["const"])
            if ri < 0 or ci < 0 or ri > h or ci > w:
                return self.errv(E_REF)
            if ri == 0 or ci == 0:
                if ri == 0 and h == 1:
                    ri = 1
                elif ci == 0 and w == 1:
                    ci = 1
                else:
                    return RefS(x.sheet, x.r1 + (ri - 1 if ri else 0), x.c1 + (ci - 1 if ci else 0),
                                x.r1 + (ri - 1 if ri else h - 1), x.c1 + (ci - 1 if ci else w - 1), x.bad)
            return RefS(x.sheet, x.r1 + ri - 1, x.c1 + ci - 1, x.r1 + ri - 1, x.c1 + ci - 1, x.bad)
        bf, bc = self.static_bad(x.bad)
        oob = self.sp([[LE(C(0.0), rt, True)], [LE(C(0.0), rt), LE(rt, C(float(h)), True)],
                       [LE(C(0.0), rt), LE(rt, C(float(h))), LE(C(0.0), ct, True)],
                       [LE(C(0.0), rt), LE(rt, C(float(h))), LE(C(0.0), ct), LE(ct, C(float(w)), True)]], hint="oob")
        # a zero index of a one-row (one-column) range selects its only row (column); any other zero index
        # gives a whole row/column (a range), which is outside this compilation -> missing
        if h == 1:
            rt = self.sp([[EQ(rt, C(0.0)), C(1.0)], [EQ(rt, C(0.0), True), rt]], hint="r1")
        elif w == 1:
            ct = self.sp([[EQ(ct, C(0.0)), C(1.0)], [EQ(ct, C(0.0), True), ct]], hint="c1")
        ef0, ec0 = self.first_error([(rf, rc), (cf, cc), (bf, bc), (oob, C(E_REF))])
        ok0 = EQ(ef0, C(1.0), True)
        zr = self.sp([[ok0, EQ(rt, C(0.0))]], hint="zr")          # whole column of the range
        zc = self.sp([[ok0, EQ(rt, C(0.0), True), EQ(ct, C(0.0))]], hint="zc")   # whole row of the range
        # a zero index gives a whole row (column) of the range; in a value context Excel intersects it with the
        # row (column) of the formula cell (formula geometry), else #VALUE!; both zero is outside this compilation
        both = self.sp([[ok0, EQ(rt, C(0.0)), EQ(ct, C(0.0))]], hint="z2")
        r1 = self.gcol("ir", x.r1.astype(float))
        c1 = self.gcol("ic", x.c1.astype(float))
        r2 = self.gcol("ir2", x.r2.astype(float))
        c2 = self.gcol("ic2", x.c2.astype(float))
        in_r = self.sp([[LE(r1, "_r"), LE("_r", r2)]], hint="inr")
        in_c = self.sp([[LE(c1, "_c"), LE("_c", c2)]], hint="inc")
        vrow = self.sp([[EQ(zr, C(1.0)), EQ(in_r, C(1.0), True)], [EQ(zc, C(1.0)), EQ(in_c, C(1.0), True)]], hint="vx")
        ef, ec = self.first_error([(ef0, ec0), (vrow, C(E_VALUE))])
        row = self.sp([[EQ(zr, C(1.0)), "_r"], [EQ(zr, C(1.0), True), r1], [EQ(zr, C(1.0), True), rt], [EQ(zr, C(1.0), True), C(-1.0)]], hint="row")
        col = self.sp([[EQ(zc, C(1.0)), "_c"], [EQ(zc, C(1.0), True), c1], [EQ(zc, C(1.0), True), ct], [EQ(zc, C(1.0), True), C(-1.0)]], hint="col")
        self.notes["INDEX with a computed position (keyed match)"] += 1
        self.notes["INDEX zero index: implicit intersection with the formula cell (formula geometry)"] += 1
        return RefD(x.sheet, row, col, ef, ec, None if isc(both, 0.0) else both)

    def f_OFFSET(self, args):
        base = self.ev(args[0])
        if not isinstance(base, RefS):
            return self.errv(E_VALUE)
        if len(args) > 3 and any(a[0] != "empty" for a in args[3:]):
            raise Unsupported("OFFSET with height/width")
        dr_v, dc_v = self.val(args[1]), self.val(args[2])
        dr, rf, rc = self.to_num(dr_v)
        dc, cf, cc = self.to_num(dc_v)
        if isc(dr) and isc(dc) and isc(rf, 0.0) and isc(cf, 0.0):
            r1 = base.r1 + int(math.trunc(dr["const"]))
            c1 = base.c1 + int(math.trunc(dc["const"]))
            bad = np.where((base.bad == 0) & ((r1 < 1) | (c1 < 1)), E_REF, base.bad)
            self.notes["OFFSET with constant offsets (static reference)"] += 1
            return RefS(base.sheet, r1, c1, r1 + (base.r2 - base.r1), c1 + (base.c2 - base.c1), bad)
        if not base.single:
            raise Unsupported("OFFSET of a range by a computed offset")
        drt = self.trunc(V({"n": dr}, {T1}, dr_v.integral)) if not isc(dr) else C(math.trunc(dr["const"]))
        dct = self.trunc(V({"n": dc}, {T1}, dc_v.integral)) if not isc(dc) else C(math.trunc(dc["const"]))
        r0 = self.gcol("or", base.r1.astype(float))
        c0 = self.gcol("oc", base.c1.astype(float))
        row = self.sp([[r0], [drt]], hint="row")
        col = self.sp([[c0], [dct]], hint="col")
        bf, bc = self.static_bad(base.bad)
        oob = self.sp([[LE(C(1.0), row, True)], [LE(C(1.0), row), LE(C(1.0), col, True)],
                       [LE(C(1.0), row), LE(C(1.0), col), LE(row, C(float(MAX_ROWS)), True)],
                       [LE(C(1.0), row), LE(C(1.0), col), LE(row, C(float(MAX_ROWS))), LE(col, C(float(MAX_COLS)), True)]], hint="oob")
        ef, ec = self.first_error([(bf, bc), (rf, rc), (cf, cc), (oob, C(E_REF))])
        self.notes["OFFSET with a computed offset (keyed match of the position)"] += 1
        return RefD(base.sheet, row, col, ef, ec)

    # ---- functions: criteria -----------------------------------------------------------------------------
    def crit_masks(self, cv, cells):
        """Masks (list of factor lists, exclusive) that a cell of a criteria range matches a criterion value
        given by DATA (no operator prefix, no wildcard; otherwise the result is made missing).
        ``cells``: operand dict of the cell components (in the table of the cells)."""
        t, n, k, p, q = cells["t"], cells["n"], cells["k"], cells["p"], cells["q"]
        ct = cv["t"]
        empty = C(self.sd.rank(""))
        m = []
        m.append([EQ(ct, C(T1)), EQ(t, C(T1)), EQ(n, cv["n"])])
        m.append([EQ(ct, C(T0)), EQ(t, C(T1)), EQ(n, C(0.0))])
        m.append([EQ(ct, C(T3)), EQ(t, C(T3)), EQ(n, cv["n"])])
        m.append([EQ(ct, C(T2)), EQ(cv["q"], C(1.0)), EQ(t, C(T1)), EQ(n, cv["p"])])
        m.append([EQ(ct, C(T2)), EQ(cv["q"], C(1.0)), EQ(t, C(T2)), EQ(q, C(1.0)), EQ(p, cv["p"])])
        m.append([EQ(ct, C(T2)), EQ(cv["q"], C(1.0), True), EQ(cv["k"], empty), EQ(t, C(T0))])
        m.append([EQ(ct, C(T2)), EQ(cv["q"], C(1.0), True), EQ(cv["k"], empty), EQ(t, C(T2)), EQ(k, empty)])
        m.append([EQ(ct, C(T2)), EQ(cv["q"], C(1.0), True), EQ(cv["k"], empty, True), EQ(t, C(T2)), EQ(k, cv["k"])])
        return m

    def const_crit_masks(self, crit, cells):
        """Masks for a criterion that is a coefficient (operators and wildcards parsed once)."""
        t, n, k, p, q = cells["t"], cells["n"], cells["k"], cells["p"], cells["q"]
        if isinstance(crit, Err):
            return []
        if crit is None:
            crit = 0.0
        if isinstance(crit, bool):
            return [[EQ(t, C(T3)), EQ(n, C(1.0 if crit else 0.0))]]
        if isinstance(crit, float):
            return [[EQ(t, C(T1)), EQ(n, C(crit))]]
        mm = re.match(r"^(<=|>=|<>|=|<|>)?(.*)$", crit, re.S)
        op, rest = mm.group(1) or "=", mm.group(2)
        x = to_float_text(rest)
        if x is not None:
            numtest = {"=": [EQ(n, C(x))], "<>": [EQ(n, C(x), True)], "<": [LE(C(x), n, True)], ">": [LE(n, C(x), True)],
                       "<=": [LE(n, C(x))], ">=": [LE(C(x), n)]}[op]
            out = [[EQ(t, C(T1))] + numtest]
            if op == "=":
                out.append([EQ(t, C(T2)), EQ(q, C(1.0)), EQ(p, C(x))])
            elif op == "<>":
                out.append([EQ(t, C(T2))])
                out.append([EQ(t, C(T0))])
                out.append([EQ(t, C(T3))])
                out.append([EQ(t, C(T4))])
            return out
        empty = C(self.sd.rank(""))
        if rest == "" and op in ("=", "<>"):
            if op == "=":
                return [[EQ(t, C(T0))], [EQ(t, C(T2)), EQ(k, empty)]]
            return [[EQ(t, C(T1))], [EQ(t, C(T3))], [EQ(t, C(T4))], [EQ(t, C(T2)), EQ(k, empty, True)]]
        if op in ("=", "<>"):
            if any(ch in rest for ch in "*~") or (("?" in rest) and not self.improve):
                raise Unsupported("criterion with a wildcard (text pattern matching)")
            if "?" in rest:
                # IMPROVEMENT: '?' patterns as a product of predicates on the lexical companions
                low = rest.lower()
                self.need_lex = max(getattr(self, "need_lex", 0), len(low))
                m = [EQ(t, C(T2)), EQ("lex.L", C(float(len(low))))]
                m += [EQ("lex.c%d" % j, C(float(ord(ch)))) for j, ch in enumerate(low) if ch != "?"]
                self.notes["IMPROVEMENT: wildcard '?' criterion as a product of character predicates"] += 1
                if op == "=":
                    return [m]
                raise Unsupported("negated wildcard criterion")
            r = C(self.sd.rank(rest))
            if op == "=":
                return [[EQ(t, C(T2)), EQ(k, r)]]
            return [[EQ(t, C(T2), True)], [EQ(t, C(T2)), EQ(k, r, True)]]
        r = C(self.sd.rank(rest))
        cmpm = {"<": [LE(r, k, True)], ">": [LE(k, r, True)], "<=": [LE(k, r)], ">=": [LE(r, k)]}[op]
        return [[EQ(t, C(T2))] + cmpm]

    def _sumif(self, args, count):
        x = self.ev(args[0])
        if not isinstance(x, RefS):
            return self.errv(E_VALUE)
        if not count and len(args) > 2:
            s = self.ev(args[2])
            if not isinstance(s, RefS):
                return self.errv(E_VALUE)
        else:
            s = x
        extra = [("s.", s)] if not count else []
        R, Rc, gref, bad = self.range_tables(x, extra=extra, truncate=True, key=("sumif", count))
        if not count:
            sb = s.bad
            bad = np.where(bad > 0, bad, sb)
        cells = {c: c for c in COMPS}
        st, sn, se = ("s.t", "s.n", "s.e") if not count else ("t", "n", "e")
        rid = self.sp([[PRESENT(gref), gref]], hint="rid")
        bf, bc = self.static_bad(bad)
        self.notes["criterion as masks; grouped sum (SUMIF/COUNTIF)"] += 1
        if not self.has_cell(args[1]):
            crit = X.val(args[1], X.Ctx(self.store, self.book, self.sheet_name, int(self.rows[0]), int(self.cols[0])))
            self.need_lex = 0
            masks = self.const_crit_masks(crit, cells)
            if self.need_lex:
                rec0 = [r for r in self.recipes if r[0] == "T" and r[1] == Rc and r[2] == ""][0]
                rec = ("lex", Rc, rec0[3], rec0[4], rec0[5], self.need_lex)
                self.recipes.append(rec)
                self.fill(rec, self.cache)
            if count:
                tot = self.sp([m for m in masks] or [[C(0.0)]], table=Rc, group={"by": "_parent"}, hint="cnt")
                r = self.sp([[PRESENT(gref), {"col": tot, "via": gref}]], hint="cif")
                ef, ec = self.first_error([(bf, bc)])
                return self.num_or_err(self.sp([[EQ(ef, C(1.0), True), r]], hint="cif"), ef, ec, True)
            hit = self.sp(masks or [[C(0.0)]], table=Rc, hint="hit")
            tot = self.sp([[EQ(hit, C(1.0)), EQ(st, C(T1)), sn]], table=Rc, group={"by": "_parent"}, hint="sif")
            nerr = self.sp([[EQ(hit, C(1.0)), EQ(st, C(T4))]], table=Rc, group={"by": "_parent"}, hint="sne")
            fe = self.match(["_row", C(1.0), C(T4)], Rc, ["_parent", hit, st], table=R, hint="sfe")
            fec = self.sp([[PRESENT(fe), {"col": se, "via": fe}]], table=R, hint="sfc")
            ef1 = self.sp([[PRESENT(gref), LE(C(1.0), {"col": nerr, "via": gref})]], hint="ef")
            ec1 = self.sp([[PRESENT(gref), {"col": fec, "via": gref}]], hint="ec")
            ef, ec = self.first_error([(bf, bc), (ef1, ec1)])
            r = self.sp([[EQ(ef, C(1.0), True), PRESENT(gref), {"col": tot, "via": gref}]], hint="sif")
            return self.num_or_err(r, ef, ec)
        cv = self.val(args[1])
        # criterion from data: compare every (instance, cell) pair -> product index set of instances x cells
        P = self.nm("G.x")
        par = self.tabs.data[Rc]["_parent"].astype(np.int64)
        ridv = self.memo[("rid", R)]
        inst, cell = [], []
        byr = collections.defaultdict(list)
        for idx, g in enumerate(par):
            byr[g].append(idx)
        for i in range(self.n):
            g = int(ridv[i]) if ridv[i] >= 0 else -1
            cs = byr.get(g, [])
            inst.append(np.full(len(cs), i)); cell.append(np.array(cs, dtype=np.int64))
        inst = np.concatenate(inst) if inst else np.zeros(0)
        cell = np.concatenate(cell) if cell else np.zeros(0)
        if len(inst) > 20_000_000:
            raise Unsupported("criterion product too large")
        self.table(P, {"_parent": inst, "y": cell})
        ry = self.match(["y"], Rc, ["_row"], table=P, hint="ry")
        cop = {c: (cv.op(c) if isc(cv.op(c)) else {"col": cv.op(c), "via": "_parent"}) for c in COMPS}
        cel = {c: {"col": c, "via": ry} for c in COMPS}
        masks = self.crit_masks(cop, cel)
        sv = {"t": {"col": st, "via": ry}, "n": {"col": sn, "via": ry}, "e": {"col": se, "via": ry}}
        if count:
            tot = self.sp(masks, table=P, group={"by": "_parent"}, hint="cnt")
        else:
            tot = self.sp([m + [EQ(sv["t"], C(T1)), sv["n"]] for m in masks], table=P, group={"by": "_parent"}, hint="sif")
        hit = self.sp(masks, table=P, hint="hit")
        if not count:
            nerr = self.sp([[EQ(hit, C(1.0)), EQ(sv["t"], C(T4))]], table=P, group={"by": "_parent"}, hint="sne")
            isr = self.sp([[EQ(hit, C(1.0)), EQ(sv["t"], C(T4))]], table=P, hint="ise")
            fe = self.match(["_row", C(1.0)], P, ["_parent", isr], hint="sfe")
            fy = self.sp([[PRESENT(fe), {"col": "y", "via": fe}]], hint="fy")
            fr = self.match([fy], Rc, ["_row"], hint="fr")
            ec1 = self.sp([[PRESENT(fr), {"col": se, "via": fr}]], hint="ec")
            ef1 = self.sp([[LE(C(1.0), nerr)]], hint="ef")
        else:
            ef1, ec1 = C(0), C(0)
        cef, cec = self.err_of(cv)
        # an error criterion matches nothing (sum 0); an operator prefix or a wildcard in a data criterion
        # is outside this compilation -> missing
        flag = self.sp([[EQ(cv.op("t"), C(T2)), EQ(cv.op("o"), C(1.0))], [EQ(cv.op("t"), C(T2)), EQ(cv.op("o"), C(1.0), True), EQ(cv.op("w"), C(1.0))]],
                       hint="cf") if T2 in cv.types else C(0)
        ef, ec = self.first_error([(bf, bc), (ef1, ec1)])
        r = self.sp([[EQ(ef, C(1.0), True), tot]], hint="sif")
        out = self.num_or_err(r, ef, ec, count)
        if not isc(flag, 0.0):
            out.c["t"] = self.mark_missing(out.op("t"), flag)
        self.notes["criterion from data: product index set (instances x cells)"] += 1
        return out

    def f_SUMIF(self, args):
        return self._sumif(args, False)

    def f_COUNTIF(self, args):
        return self._sumif(args, True)

    # ---- functions: arrays -----------------------------------------------------------------------------
    def f_SUMPRODUCT(self, args):
        refs = [self.ev(a) for a in args]
        if not all(isinstance(r, RefS) for r in refs):
            raise Unsupported("SUMPRODUCT of something that is not a range")
        h = [(r.r2 - r.r1 + 1) for r in refs]
        w = [(r.c2 - r.c1 + 1) for r in refs]
        if not all(np.all(a == h[0]) for a in h) or not all(np.all(b == w[0]) for b in w):
            return self.errv(E_VALUE)
        R, Rc, gref, bad = self.range_tables(refs[0], extra=[("a%d." % i, r) for i, r in enumerate(refs[1:], 1)], truncate=False)
        names = [""] + ["a%d." % i for i in range(1, len(refs))]
        factors = []
        for pf in names:
            factors += [EQ(pf + "t", C(T1)), pf + "n"]
        s = self.sp([factors], table=Rc, group={"by": "_parent"}, hint="spr")
        anyerr = self.sp([[EQ(names[0] + "t", C(T4))]] + [[EQ(pf + "t", C(T4))] + [EQ(q + "t", C(T4), True) for q in names[:i]]
                                                           for i, pf in enumerate(names) if i > 0], table=Rc, hint="ae")
        code = self.sp([[EQ(pf + "t", C(T4))] + [EQ(q + "t", C(T4), True) for q in names[:i]] + [pf + "e"] for i, pf in enumerate(names)],
                       table=Rc, hint="ac")
        fe = self.match(["_row", C(1.0)], Rc, ["_parent", anyerr], table=R, hint="fe")
        fec = self.sp([[PRESENT(fe), {"col": code, "via": fe}]], table=R, hint="fc")
        ef = self.sp([[PRESENT({"col": fe, "via": gref})]], hint="ef")
        ec = self.sp([[PRESENT(gref), {"col": fec, "via": gref}]], hint="ec")
        bads = [r.bad for r in refs]
        bb = bads[0]
        for b_ in bads[1:]:
            bb = np.where(bb > 0, bb, b_)
        bf, bc = self.static_bad(bb)
        ef2, ec2 = self.first_error([(bf, bc), (ef, ec)])
        r = self.sp([[EQ(ef2, C(1.0), True), PRESENT(gref), {"col": s, "via": gref}]], hint="spv")
        self.notes["sum of products over a range (sp group by)"] += 1
        return self.num_or_err(r, ef2, ec2)

    def f_RANK(self, args):
        x, ef, ec = self.to_num(self.val(args[0]))
        ref = self.ev(args[1])
        if len(args) > 2:
            raise Unsupported("RANK with order")
        if not isinstance(ref, RefS):
            raise Unsupported("RANK form")
        R, Rc, gref, bad = self.range_tables(ref)
        P = self.nm("G.x")
        par = self.tabs.data[Rc]["_parent"].astype(np.int64)
        ridv = self.memo[("rid", R)]
        inst, cell = [], []
        for i in range(self.n):
            cs = np.nonzero(par == ridv[i])[0]
            inst.append(np.full(len(cs), i)); cell.append(cs)
        self.table(P, {"_parent": np.concatenate(inst), "y": np.concatenate(cell)})
        ry = self.match(["y"], Rc, ["_row"], table=P, hint="ry")
        xv = {"col": x, "via": "_parent"} if not isc(x) else x
        gt = self.sp([[EQ({"col": "t", "via": ry}, C(T1)), LE({"col": "n", "via": ry}, xv, True)]], table=P, group={"by": "_parent"}, hint="gt")
        eqc = self.sp([[EQ({"col": "t", "via": ry}, C(T1)), EQ({"col": "n", "via": ry}, xv)]], table=P, group={"by": "_parent"}, hint="eq")
        na = self.sp([[EQ(eqc, C(0.0))]], hint="na")
        ef2, ec2 = self.first_error([(ef, ec), (na, C(E_NA))])
        self.notes["rank as a gated count (product index set)"] += 1
        return self.num_or_err(self.sp([[EQ(ef2, C(1.0), True), gt], [EQ(ef2, C(1.0), True), C(1.0)]], hint="rank"), ef2, ec2, True)

    def f_AGGREGATE(self, args):
        """AGGREGATE(15, 2|6, 1/(range <op> c) * ROW(range2), k): the k-th smallest number of the array;
        the array is increasing along the range (ROW), so it is the ROW of the k-th cell whose condition holds."""
        if self.has_cell(args[0]) or self.has_cell(args[1]):
            raise Unsupported("AGGREGATE with a computed function number")
        ctx = X.Ctx(self.store, self.book, self.sheet_name, 1, 1)
        fn, opt = X.to_num(X.ev(args[0], ctx)), X.to_num(X.ev(args[1], ctx))
        if fn != 15 or opt not in (2.0, 6.0):
            raise Unsupported("AGGREGATE %s,%s" % (fn, opt))
        arr = args[2]
        ok = (arr[0] == "bin" and arr[1] == "*" and arr[2][0] == "bin" and arr[2][1] == "/" and arr[2][2] == ("const", 1.0)
              and arr[3][0] == "call" and arr[3][1] == "ROW" and len(arr[3][2]) == 1)
        if not ok:
            raise Unsupported("AGGREGATE array form")
        cond = arr[2][3]
        if not (cond[0] == "bin" and cond[1] in ("=", "<>", "<", ">", "<=", ">=") and cond[2][0] == "R" and not self.has_cell(cond[3])):
            raise Unsupported("AGGREGATE condition form")
        cref = self.make_ref(cond[2])
        rref = self.make_ref(arr[3][2][0])
        if not isinstance(cref, RefS) or not isinstance(rref, RefS) or not (np.all(cref.c1 == cref.c2) and np.all(rref.c1 == rref.c2)):
            raise Unsupported("AGGREGATE ranges")
        R, Rc, gref, bad = self.range_tables(cref, truncate=False)
        c0 = self.fold(cond[3])
        # the condition of every cell (in the table of the cells): compare, then 1/(condition) * ROW
        cl = [[EQ("t", C(T1)), C(1)], [EQ("t", C(T2)), C(2)], [EQ("t", C(T3)), C(3)]]
        if c0.types == {T1}:
            cls_c, key_c = C(1), c0.op("n")
            cl.append([EQ("t", C(T0)), C(1)])
        elif c0.types == {T2}:
            cls_c, key_c = C(2), c0.op("k")
            cl.append([EQ("t", C(T0)), C(2)])
        else:
            raise Unsupported("AGGREGATE condition constant type")
        ccl = self.sp(cl, table=Rc, hint="acl")
        cky = self.sp([[EQ("t", C(T1)), "n"], [EQ("t", C(T2)), "k"], [EQ("t", C(T3)), "n"]] +
                      ([[EQ("t", C(T0)), C(self.sd.rank(""))]] if c0.types == {T2} else []), table=Rc, hint="aky")
        op = cond[1]
        same = EQ(ccl, cls_c)
        terms = {"=": [[same, EQ(cky, key_c)]], "<>": [[same, EQ(cky, key_c, True)], [EQ(ccl, cls_c, True)]],
                 "<": [[LE(cls_c, ccl, True)], [same, LE(key_c, cky, True)]], ">": [[LE(ccl, cls_c, True)], [same, LE(cky, key_c, True)]],
                 "<=": [[LE(cls_c, ccl, True)], [same, LE(cky, key_c)]], ">=": [[LE(ccl, cls_c, True)], [same, LE(key_c, cky)]]}[op]
        holds = self.sp([[EQ("t", C(T4), True)] + t for t in terms], table=Rc, hint="hold")
        # element i exists only where ROW(range2) has a row i (broadcast of arrays of different sizes -> #N/A)
        nrow = int(rref.r2[0] - rref.r1[0] + 1)
        valid = self.sp([[EQ(holds, C(1.0)), LE("i", C(float(nrow - 1)))]], table=Rc, hint="vl")
        P, rb = self.pairs_table(Rc)
        ordc = self.sp([[EQ({"col": valid, "via": rb}, C(1.0)), LE({"col": "i", "via": rb}, {"col": "i", "via": "_parent"})]],
                       table=P, group={"by": "_parent"}, hint="ord")
        kv, kf, kc = self.to_num(self.val(args[3]))
        kt = self.trunc(V({"n": kv}, {T1}, True))
        rid = self.sp([[PRESENT(gref), gref]], hint="rid")
        m = self.match([rid, kt, C(1.0)], Rc, ["_parent", ordc, valid], hint="ag")
        r1 = self.gcol("ar", rref.r1.astype(float))
        rowv = self.sp([[PRESENT(m), r1], [PRESENT(m), {"col": "i", "via": m}]], hint="agr")
        miss = self.sp([[PRESENT(m, True)]], hint="nm")
        bf, bc = self.static_bad(bad)
        ef, ec = self.first_error([(bf, bc), (kf, kc), (miss, C(E_NUM))])
        self.notes["k-th selected row: running count (pair table) and match"] += 1
        return self.num_or_err(self.sp([[EQ(ef, C(1.0), True), rowv]], hint="agv"), ef, ec, True)

    # ---- running ---------------------------------------------------------------------------------
    def finish(self, v):
        """Result components of the top-level value (implicit intersection, blank shows 0); missing wherever
        a flag of the compiled domain is 1 anywhere in the formula."""
        v = self.scalar(v) if not isinstance(v, V) else v
        flags = self.__dict__.get("fail_flags", [])
        if flags:
            anyf = self.sp([[LE(C(1.0), self.sp([[f_] for f_ in flags], hint="nf"))]], hint="anyf")
            c = dict(v.c)
            c["t"] = self.sp([[EQ(anyf, C(1.0), True), v.op("t")], [EQ(anyf, C(1.0)), "_missing"]], hint="t")
            v = V(c, v.types, v.integral)
        return v

    def program(self):
        if getattr(self, "_prog", None) is None:
            self._prog = msp.Program({"name": "pattern", "templates": {}, "shared": [],
                                      "units": [{"id": "P", "steps": self.steps, "outputs": {}}]})
        return self._prog

    def run(self, v, src=None, sd=None):
        """Run the (fixed) program; with ``src`` the value columns are first refilled from that source."""
        undo = None
        if src is not None:
            if isinstance(src, CaseSource) and src.base is self.cache:
                undo = self.apply_case(src)
            else:
                self.refresh(src)
        sd = sd or self.sd
        prog = self.program()
        eng = msp.Engine(self.tabs)
        try:
            eng.run(prog)
            cols = {}
            for c in ("t", "n", "s", "e"):
                o = v.c.get(c)
                if o is None:
                    cols[c] = (np.zeros(self.n), np.ones(self.n, dtype=bool))
                elif isc(o):
                    cols[c] = (np.full(self.n, float(o["const"])), np.ones(self.n, dtype=bool))
                else:
                    col = eng.operand("G", o)
                    cols[c] = (col.v.copy(), col.m.copy())
        finally:
            if undo is not None:
                self.undo_case(undo)
        out = []
        for i in range(self.n):
            if not all(cols[c][1][i] for c in cols):
                out.append("<missing>")
                continue
            out.append(sd.dec(cols["t"][0][i], cols["n"][0][i], cols["s"][0][i], cols["e"][0][i]))
        return out, prog, eng
