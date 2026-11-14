"""Reference evaluator: Excel semantics, one cell at a time (the "original equation" A).

The formula of a pattern is parsed once at its representative cell; references are kept as
relative/absolute descriptors so that the same tree evaluates every instance of the pattern.
This evaluator is independent of the masked sum-product compiler (different code path).
"""
from __future__ import annotations

import bisect
import decimal
import math
import re

import fx
from store import KEY_SHIFT, Err, err, to_float_text

NA, VALUE, DIV0, REF, NUM, NAME = err("#N/A"), err("#VALUE!"), err("#DIV/0!"), err("#REF!"), err("#NUM!"), err("#NAME?")
MAX_ROWS, MAX_COLS = 1048576, 16384


class Unsupported(Exception):
    pass


# ---------------------------------------------------------------------------------------------
# compile a formula tree into a tree with reference descriptors
# ---------------------------------------------------------------------------------------------
def _corner(ca, c, ra, r, row0, col0):
    """(row_abs, row_or_offset, col_abs, col_or_offset); None parts for whole-row/column."""
    rr = None if r is None else (True, r) if ra else (False, r - row0)
    cc = None if c is None else (True, c) if ca else (False, c - col0)
    return rr, cc


def prepare(node, row0, col0, store, book, sheet):
    k = node[0]
    if k == "ref":
        prefix, body = node[1]
        sh = fx.norm_sheet(prefix) or None
        parts = fx._parts(body)
        corners = [_corner(*p, row0, col0) for p in parts]
        return ("R", sh, corners)
    if k == "range2":
        a, b = prepare(node[1], row0, col0, store, book, sheet), prepare(node[2], row0, col0, store, book, sheet)
        if a[0] == "R" and b[0] == "R" and a[1] == b[1]:
            return ("R", a[1], [a[2][0], b[2][-1]])
        raise Unsupported("range of different sheets")
    if k == "name":
        ref = store.resolve_name(book, sheet, node[1])
        if ref is None:
            if node[1].upper() in ("TRUE", "FALSE"):
                return ("const", node[1].upper() == "TRUE")
            return ("const", NAME)
        if "#REF!" in ref:
            return ("const", REF)
        toks = fx.tokenize(ref)
        ast = fx.Parser(toks).parse()
        return prepare(ast, row0, col0, store, book, sheet) if ast[0] in ("ref", "range2") else ("const", REF)
    if k == "num":
        return ("const", float(node[1]))
    if k == "str":
        return ("const", node[1][1:-1].replace('""', '"'))
    if k == "bool":
        return ("const", node[1] == "TRUE")
    if k == "err":
        return ("const", err(node[1]) if not node[1].endswith("#REF!") or node[1] == "#REF!" else REF)
    if k == "empty":
        return ("empty",)
    if k == "array":
        return ("const_array", [[_lit(x) for x in row] for row in node[1]])
    if k in ("paren", "pos"):
        return prepare(node[1], row0, col0, store, book, sheet)
    if k in ("neg", "pct"):
        return (k, prepare(node[1], row0, col0, store, book, sheet))
    if k == "bin":
        return ("bin", node[1], prepare(node[2], row0, col0, store, book, sheet), prepare(node[3], row0, col0, store, book, sheet))
    if k == "call":
        return ("call", node[1], [prepare(a, row0, col0, store, book, sheet) for a in node[2]])
    raise Unsupported(k)


def _lit(x):
    try:
        return float(x)
    except ValueError:
        return x.strip('"')


# ---------------------------------------------------------------------------------------------
# references
# ---------------------------------------------------------------------------------------------
class Ref:
    __slots__ = ("sheet", "r1", "c1", "r2", "c2")

    def __init__(self, sheet, r1, c1, r2, c2):
        self.sheet, self.r1, self.c1, self.r2, self.c2 = sheet, r1, c1, r2, c2

    @property
    def single(self):
        return self.r1 == self.r2 and self.c1 == self.c2

    def cells(self):
        """Values in row-major order (blank cells as None)."""
        sh = self.sheet
        if sh is None:
            return []
        r2 = min(self.r2, sh.max_row) if self.r2 >= sh.max_row else self.r2
        c2 = min(self.c2, sh.max_col) if self.c2 >= sh.max_col else self.c2
        out = []
        vals = sh.values
        for r in range(self.r1, r2 + 1):
            base = r * KEY_SHIFT
            for c in range(self.c1, c2 + 1):
                out.append(vals.get(base + c))
        return out

    def get(self, i, j):
        """Cell at 0-based (row i, column j) inside the reference."""
        if self.sheet is None:
            return None
        return self.sheet.values.get((self.r1 + i) * KEY_SHIFT + self.c1 + j)

    @property
    def height(self):
        return self.r2 - self.r1 + 1

    @property
    def width(self):
        return self.c2 - self.c1 + 1


class Ctx:
    def __init__(self, store, book, sheet_name, row, col):
        self.store, self.book, self.sheet_name, self.row, self.col = store, book, sheet_name, row, col


def make_ref(node, ctx):
    _, sh, corners = node
    sheet = ctx.store.sheet(ctx.book, sh) if sh else ctx.store.sheet(ctx.book, ctx.sheet_name)
    if sh and sheet is None:
        return REF
    rs, cs = [], []
    for rr, cc in corners:
        r = None if rr is None else (rr[1] if rr[0] else ctx.row + rr[1])
        c = None if cc is None else (cc[1] if cc[0] else ctx.col + cc[1])
        rs.append(r), cs.append(c)
    if rs[0] is None:                                     # whole columns
        r1, r2 = 1, max(sheet.max_row, 1)
    else:
        r1, r2 = min(rs), max(rs)
    if cs[0] is None:                                     # whole rows
        c1, c2 = 1, max(sheet.max_col, 1)
    else:
        c1, c2 = min(cs), max(cs)
    if r1 < 1 or c1 < 1 or r2 > MAX_ROWS or c2 > MAX_COLS:
        return REF
    return Ref(sheet, r1, c1, r2, c2)


# ---------------------------------------------------------------------------------------------
# coercions
# ---------------------------------------------------------------------------------------------
def to_num(v):
    if v is None:
        return 0.0
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, float):
        return v
    if isinstance(v, Err):
        return v
    if isinstance(v, str):
        x = to_float_text(v)
        return VALUE if x is None else x
    return VALUE


def to_bool(v):
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, float):
        return v != 0.0
    if isinstance(v, Err):
        return v
    if isinstance(v, str):
        u = v.upper()
        if u in ("TRUE", "FALSE"):
            return u == "TRUE"
        return VALUE
    return VALUE


def num_text(x: float) -> str:
    """Excel's text of a number in a concatenation (general format, 15 significant digits)."""
    if x == 0:
        return "0"
    if x == int(x) and abs(x) < 1e15:
        return str(int(x))
    s = "%.15g" % x
    if "e" in s:
        mant, ex = s.split("e")
        mant = mant.rstrip("0").rstrip(".") if "." in mant else mant
        e = int(ex)
        if -5 < e < 15:
            s = ("%.15f" % x).rstrip("0").rstrip(".")
        else:
            return "%sE%s%02d" % (mant, "+" if e >= 0 else "-", abs(e))
    return s


def to_text(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, float):
        return num_text(v)
    return v


def scalar(v, ctx):
    """A value where one value is needed (implicit intersection of a reference)."""
    if isinstance(v, Ref):
        if v.single:
            return v.get(0, 0)
        if v.width == 1 and v.r1 <= ctx.row <= v.r2:
            return v.get(ctx.row - v.r1, 0)
        if v.height == 1 and v.c1 <= ctx.col <= v.c2:
            return v.get(0, ctx.col - v.c1)
        return VALUE
    if isinstance(v, list):                               # array: its first element
        return v[0][0] if v and v[0] else VALUE
    return v


def text_order(s: str) -> bytes:
    """Collation key of a text: case-insensitive, then Shift_JIS (cp932) code order - the order of Excel
    in a Japanese locale as far as these workbooks show it (all 514,007 look-up cells reproduced)."""
    out = []
    for ch in s.lower():
        try:
            out.append(ch.encode("cp932"))
        except UnicodeEncodeError:
            out.append(b"\xff\xff" + ch.encode("utf-16-be"))
    return b"".join(out)


def cls_key(v):
    """(class, key) for comparisons: numbers < text < logicals; text compared case-insensitively."""
    if isinstance(v, bool):
        return (3, 1.0 if v else 0.0)
    if isinstance(v, float):
        return (1, v)
    if isinstance(v, str):
        return (2, text_order(v))
    return (0, 0.0)


def compare(op, a, b):
    if isinstance(a, Err):
        return a
    if isinstance(b, Err):
        return b
    if a is None and b is None:
        ka = kb = (1, 0.0)
    elif a is None:
        kb = cls_key(b)
        ka = (kb[0], {1: 0.0, 2: b"", 3: 0.0}[kb[0]])
    elif b is None:
        ka = cls_key(a)
        kb = (ka[0], {1: 0.0, 2: b"", 3: 0.0}[ka[0]])
    else:
        ka, kb = cls_key(a), cls_key(b)
    if op == "=":
        return ka == kb
    if op == "<>":
        return ka != kb
    if op == "<":
        return ka < kb
    if op == ">":
        return ka > kb
    if op == "<=":
        return ka <= kb
    return ka >= kb


def arith(op, a, b):
    a, b = to_num(a), to_num(b)
    if isinstance(a, Err):
        return a
    if isinstance(b, Err):
        return b
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == "/":
        return DIV0 if b == 0.0 else a / b
    if op == "^":
        try:
            r = a ** b
        except (OverflowError, ZeroDivisionError):
            return NUM
        if isinstance(r, complex) or (isinstance(r, float) and not math.isfinite(r)):
            return NUM
        return float(r)
    raise Unsupported(op)


# ---------------------------------------------------------------------------------------------
# rounding (decimal, 15 significant digits as Excel)
# ---------------------------------------------------------------------------------------------
def _dec(x):
    return decimal.Decimal("%.15g" % x)


def xround(x, d, mode):
    if not math.isfinite(x):
        return NUM
    d = int(d) if d >= 0 else -int(-d)
    q = decimal.Decimal(1).scaleb(-d)
    rounding = {"round": decimal.ROUND_HALF_UP, "down": decimal.ROUND_DOWN, "up": decimal.ROUND_UP}[mode]
    with decimal.localcontext() as c:
        c.prec = 60
        return float(_dec(x).quantize(q, rounding=rounding)) if d >= 0 else float((_dec(x) / q).quantize(decimal.Decimal(1), rounding=rounding) * q)


def xfloor_int(x):
    return float(math.floor(float(_dec(x))))


def xmod(a, b):
    if b == 0.0:
        return DIV0
    r = a - b * math.floor(a / b)
    if r != 0.0 and abs(r - b) < abs(b) * 1e-15:
        r = 0.0
    return r


# ---------------------------------------------------------------------------------------------
# criteria (SUMIF / COUNTIF) and look-ups
# ---------------------------------------------------------------------------------------------
def _wild(pattern: str):
    out, i = [], 0
    while i < len(pattern):
        ch = pattern[i]
        if ch == "~" and i + 1 < len(pattern) and pattern[i + 1] in "*?~":
            out.append(re.escape(pattern[i + 1])); i += 2; continue
        out.append(".*" if ch == "*" else "." if ch == "?" else re.escape(ch))
        i += 1
    return re.compile("^" + "".join(out) + "$", re.S | re.I)


def criterion(crit):
    """A test function for SUMIF/COUNTIF criteria."""
    if isinstance(crit, Err):
        return lambda v: False
    if crit is None:
        crit = 0.0
    if isinstance(crit, bool) or isinstance(crit, float):
        return lambda v, c=crit: (not isinstance(v, bool)) and isinstance(v, float) and v == c if not isinstance(c, bool) else v is c
    m = re.match(r"^(<=|>=|<>|=|<|>)?(.*)$", crit, re.S)
    op, rest = m.group(1) or "=", m.group(2)
    x = to_float_text(rest)
    if x is not None:
        def num_test(v, op=op, x=x):
            if isinstance(v, str):
                y = to_float_text(v)
                if y is None or op != "=":
                    return op == "<>"
                v = y
            if not isinstance(v, float) or isinstance(v, bool):
                return op == "<>"
            return {"=": v == x, "<>": v != x, "<": v < x, ">": v > x, "<=": v <= x, ">=": v >= x}[op]
        return num_test
    if rest == "" and op in ("=", "<>"):
        return (lambda v: v is None or v == "") if op == "=" else (lambda v: not (v is None or v == ""))
    if op in ("=", "<>"):
        rx = _wild(rest)
        if op == "=":
            return lambda v, rx=rx: isinstance(v, str) and bool(rx.match(v))
        return lambda v, rx=rx: not (isinstance(v, str) and bool(rx.match(v)))
    low = text_order(rest)
    return lambda v, op=op, low=low: isinstance(v, str) and {"<": text_order(v) < low, ">": text_order(v) > low,
                                                             "<=": text_order(v) <= low, ">=": text_order(v) >= low}[op]


_INDEX_CACHE = {}


def _norm(v):
    if isinstance(v, bool):
        return ("b", v)
    if isinstance(v, float):
        return ("n", v)
    if isinstance(v, str):
        return ("t", v.lower())
    return None


def first_exact(key, seq, cache_key):
    """Position of the first exact match (memoised per range; wildcard keys are scanned)."""
    if isinstance(key, str) and any(ch in key for ch in "*?~"):
        return next((i for i, v in enumerate(seq) if exact_eq(key, v)), -1)
    idx = _INDEX_CACHE.get(cache_key)
    if idx is None:
        idx = {}
        for i, v in enumerate(seq):
            k = _norm(v)
            if k is not None and k not in idx:
                idx[k] = i
        _INDEX_CACHE[cache_key] = idx
    k = _norm(key)
    return idx.get(k, -1) if k is not None else -1


def exact_eq(key, v):
    """Exact-match equality of VLOOKUP/MATCH (type-strict; text case-insensitive; wildcards in text keys)."""
    if isinstance(key, str):
        if not isinstance(v, str):
            return False
        if any(ch in key for ch in "*?~"):
            return bool(_wild(key).match(v))
        return v.lower() == key.lower()
    if isinstance(key, bool):
        return isinstance(v, bool) and v == key
    return isinstance(v, float) and not isinstance(v, bool) and v == key


def approx_pos(key, seq):
    """Largest position whose value is <= key among values of the key's type (binary search as Excel)."""
    kc = cls_key(key)
    lo, hi, best = 0, len(seq) - 1, -1
    while lo <= hi:
        mid = (lo + hi) // 2
        v = seq[mid]
        if v is None or isinstance(v, Err):
            # skip blanks/errors: search the nearest non-blank on the left
            j = mid
            while j >= lo and (seq[j] is None or isinstance(seq[j], Err)):
                j -= 1
            if j < lo:
                lo = mid + 1
                continue
            v, mid2 = seq[j], j
        else:
            mid2 = mid
        vc = cls_key(v)
        if vc[0] != kc[0]:
            if vc[0] < kc[0]:
                lo = mid + 1
            else:
                hi = mid2 - 1
            continue
        if vc[1] == kc[1]:
            return mid2                                    # Excel stops at an equal value
        if vc[1] <= kc[1]:
            best = mid2
            lo = mid + 1
        else:
            hi = mid2 - 1
    return best


# ---------------------------------------------------------------------------------------------
# evaluation
# ---------------------------------------------------------------------------------------------
def ev(node, ctx):
    k = node[0]
    if k == "const":
        return node[1]
    if k == "R":
        return make_ref(node, ctx)
    if k == "empty":
        return None
    if k == "const_array":
        return node[1]
    if k == "neg":
        v = to_num(scalar(ev(node[1], ctx), ctx))
        return v if isinstance(v, Err) else -v
    if k == "pct":
        v = to_num(scalar(ev(node[1], ctx), ctx))
        return v if isinstance(v, Err) else v / 100.0
    if k == "bin":
        op = node[1]
        a, b = scalar(ev(node[2], ctx), ctx), scalar(ev(node[3], ctx), ctx)
        if op in ("=", "<>", "<", ">", "<=", ">="):
            return compare(op, a, b)
        if op == "&":
            if isinstance(a, Err):
                return a
            if isinstance(b, Err):
                return b
            return to_text(a) + to_text(b)
        return arith(op, a, b)
    if k == "call":
        f = FUNCS.get(node[1])
        if f is None:
            raise Unsupported("function " + node[1])
        return f(node[2], ctx)
    raise Unsupported(k)


def val(node, ctx):
    return scalar(ev(node, ctx), ctx)


def _numbers_of(args, ctx, count_direct_text=True):
    """Numbers of SUM-like arguments: references contribute numbers only; direct values are coerced."""
    for a in args:
        v = ev(a, ctx)
        if isinstance(v, Ref):
            for x in v.cells():
                if isinstance(x, Err):
                    yield x
                elif isinstance(x, float) and not isinstance(x, bool):
                    yield x
        elif isinstance(v, list):
            for row in v:
                for x in row:
                    if isinstance(x, Err):
                        yield x
                    elif isinstance(x, float) and not isinstance(x, bool):
                        yield x
        elif isinstance(v, Err):
            yield v
        elif v is None:
            continue
        else:
            yield to_num(v)


def f_sum(args, ctx):
    s = 0.0
    for x in _numbers_of(args, ctx):
        if isinstance(x, Err):
            return x
        s += x
    return s


def f_average(args, ctx):
    xs = []
    for x in _numbers_of(args, ctx):
        if isinstance(x, Err):
            return x
        xs.append(x)
    return DIV0 if not xs else math.fsum(xs) / len(xs) if False else sum(xs) / len(xs)


def f_max(args, ctx):
    xs = []
    for x in _numbers_of(args, ctx):
        if isinstance(x, Err):
            return x
        xs.append(x)
    return max(xs) if xs else 0.0


def f_if(args, ctx):
    c = to_bool(val(args[0], ctx))
    if isinstance(c, Err):
        return c
    if c:
        return val(args[1], ctx) if len(args) > 1 and args[1][0] != "empty" else (0.0 if len(args) > 1 else True)
    if len(args) < 3:
        return False
    return 0.0 if args[2][0] == "empty" else val(args[2], ctx)


def f_iferror(args, ctx):
    v = val(args[0], ctx)
    if isinstance(v, Err):
        return 0.0 if args[1][0] == "empty" else val(args[1], ctx)
    return 0.0 if v is None else v


def f_isnumber(args, ctx):
    v = val(args[0], ctx)
    return isinstance(v, float) and not isinstance(v, bool)


def f_istext(args, ctx):
    return isinstance(val(args[0], ctx), str)


def f_iserror(args, ctx):
    return isinstance(val(args[0], ctx), Err)


def _logic(args, ctx, mode):
    seen, acc = False, (mode == "and")
    for a in args:
        v = ev(a, ctx)
        items = v.cells() if isinstance(v, Ref) and not v.single else [scalar(v, ctx)]
        for x in items:
            if isinstance(x, Err):
                return x
            if x is None or (isinstance(x, str) and isinstance(v, Ref)):
                continue
            b = to_bool(x)
            if isinstance(b, Err):
                return b
            seen = True
            acc = (acc and b) if mode == "and" else (acc or b)
    return acc if seen else VALUE


def f_mod(args, ctx):
    a, b = to_num(val(args[0], ctx)), to_num(val(args[1], ctx))
    if isinstance(a, Err):
        return a
    if isinstance(b, Err):
        return b
    return xmod(a, b)


def _round(args, ctx, mode):
    x = to_num(val(args[0], ctx))
    d = to_num(val(args[1], ctx)) if len(args) > 1 else 0.0
    if isinstance(x, Err):
        return x
    if isinstance(d, Err):
        return d
    return xround(x, math.trunc(d), mode)


def f_int(args, ctx):
    x = to_num(val(args[0], ctx))
    return x if isinstance(x, Err) else float(math.floor(x))


def f_abs(args, ctx):
    x = to_num(val(args[0], ctx))
    return x if isinstance(x, Err) else abs(x)


def f_power(args, ctx):
    return arith("^", val(args[0], ctx), val(args[1], ctx))


def f_log10(args, ctx):
    x = to_num(val(args[0], ctx))
    if isinstance(x, Err):
        return x
    return NUM if x <= 0 else math.log10(x)


def f_vlookup(args, ctx, horizontal=False):
    key = val(args[0], ctx)
    rng = ev(args[1], ctx)
    if isinstance(key, Err):
        return key
    if isinstance(rng, Err):
        return rng
    if not isinstance(rng, Ref):
        return VALUE
    idx = to_num(val(args[2], ctx))
    if isinstance(idx, Err):
        return idx
    idx = int(math.trunc(idx))
    approx = True
    if len(args) > 3:
        a = args[3]
        approx = False if a[0] == "empty" else to_bool(val(a, ctx))
        if isinstance(approx, Err):
            return approx
    if idx < 1:
        return VALUE
    if idx > (rng.height if horizontal else rng.width):
        return REF
    if key is None:
        key = 0.0
    n = rng.width if horizontal else rng.height
    seq = [rng.get(0, j) for j in range(n)] if horizontal else [rng.get(i, 0) for i in range(n)]
    if approx:
        pos = approx_pos(key, seq)
    else:
        pos = first_exact(key, seq, (id(rng.sheet), rng.r1, rng.c1, rng.r2, rng.c2, horizontal))
    if pos < 0:
        return NA
    v = rng.get(idx - 1, pos) if horizontal else rng.get(pos, idx - 1)
    return 0.0 if v is None else v


def f_lookup(args, ctx):
    key = val(args[0], ctx)
    if isinstance(key, Err):
        return key
    vec, res = ev(args[1], ctx), ev(args[2], ctx) if len(args) > 2 else None
    if not isinstance(vec, Ref):
        return VALUE
    seq = vec.cells()
    pos = approx_pos(key, seq)
    if pos < 0:
        return NA
    if res is None:
        v = seq[pos]
    else:
        cells = res.cells()
        if pos >= len(cells):
            return NA
        v = cells[pos]
    return 0.0 if v is None else v


def f_index(args, ctx):
    rng = ev(args[0], ctx)
    if not isinstance(rng, Ref):
        return VALUE
    r = to_num(val(args[1], ctx)) if len(args) > 1 and args[1][0] != "empty" else 0.0
    c = to_num(val(args[2], ctx)) if len(args) > 2 and args[2][0] != "empty" else 0.0
    if isinstance(r, Err):
        return r
    if isinstance(c, Err):
        return c
    r, c = int(r), int(c)
    if rng.height == 1 and len(args) == 2:
        r, c = 1, r
    if r < 0 or c < 0 or r > rng.height or c > rng.width:
        return REF
    if r == 0 or c == 0:
        if r == 0 and rng.height == 1:
            r = 1
        elif c == 0 and rng.width == 1:
            c = 1
        else:
            return Ref(rng.sheet, rng.r1 + (r - 1 if r else 0), rng.c1 + (c - 1 if c else 0),
                       rng.r1 + (r - 1 if r else rng.height - 1), rng.c1 + (c - 1 if c else rng.width - 1))
    return Ref(rng.sheet, rng.r1 + r - 1, rng.c1 + c - 1, rng.r1 + r - 1, rng.c1 + c - 1)


def f_match(args, ctx):
    key = val(args[0], ctx)
    if isinstance(key, Err):
        return key
    rng = ev(args[1], ctx)
    if not isinstance(rng, Ref):
        return NA
    mt = 1.0
    if len(args) > 2:
        mt = 0.0 if args[2][0] == "empty" else to_num(val(args[2], ctx))
        if isinstance(mt, Err):
            return mt
    seq = rng.cells()
    if key is None:
        return NA
    if mt == 0:
        pos = first_exact(key, seq, (id(rng.sheet), rng.r1, rng.c1, rng.r2, rng.c2, "match"))
    elif mt > 0:
        pos = approx_pos(key, seq)
    else:
        raise Unsupported("MATCH -1")
    return NA if pos < 0 else float(pos + 1)


def f_offset(args, ctx):
    base = ev(args[0], ctx)
    if not isinstance(base, Ref):
        return VALUE
    dr = to_num(val(args[1], ctx))
    dc = to_num(val(args[2], ctx))
    if isinstance(dr, Err):
        return dr
    if isinstance(dc, Err):
        return dc
    h = to_num(val(args[3], ctx)) if len(args) > 3 and args[3][0] != "empty" else float(base.height)
    w = to_num(val(args[4], ctx)) if len(args) > 4 and args[4][0] != "empty" else float(base.width)
    if isinstance(h, Err) or isinstance(w, Err):
        return VALUE
    r1, c1 = base.r1 + int(math.trunc(dr)), base.c1 + int(math.trunc(dc))
    if r1 < 1 or c1 < 1 or h < 1 or w < 1 or r1 + int(h) - 1 > MAX_ROWS or c1 + int(w) - 1 > MAX_COLS:
        return REF
    return Ref(base.sheet, r1, c1, r1 + int(h) - 1, c1 + int(w) - 1)


_SUMIF_CACHE = {}


def f_sumif(args, ctx):
    rng = ev(args[0], ctx)
    if not isinstance(rng, Ref):
        return VALUE
    crit = val(args[1], ctx)
    srng = ev(args[2], ctx) if len(args) > 2 else rng
    if not isinstance(srng, Ref):
        return VALUE
    ck = (id(rng.sheet), rng.r1, rng.c1, rng.r2, rng.c2, id(srng.sheet), srng.r1, srng.c1, type(crit).__name__, repr(crit))
    if ck in _SUMIF_CACHE:
        return _SUMIF_CACHE[ck]
    _SUMIF_CACHE[ck] = r = _sumif(rng, crit, srng)
    return r


def _sumif(rng, crit, srng):
    test = criterion(crit)
    s = 0.0
    for i in range(rng.height):
        for j in range(rng.width):
            if test(rng.get(i, j)):
                v = srng.get(i, j) if srng.sheet is not None else None
                if isinstance(v, Err):
                    return v
                if isinstance(v, float) and not isinstance(v, bool):
                    s += v
    return s


def f_countif(args, ctx):
    rng = ev(args[0], ctx)
    if not isinstance(rng, Ref):
        return VALUE
    test = criterion(val(args[1], ctx))
    return float(sum(1 for v in rng.cells() if test(v)))


def _array(node, ctx):
    """Array value of an argument evaluated element-wise (SUMPRODUCT, AGGREGATE)."""
    v = ev_array(node, ctx)
    return v


def ev_array(node, ctx):
    """Element-wise evaluation: references become lists, operators broadcast."""
    k = node[0]
    if k == "R":
        r = make_ref(node, ctx)
        if isinstance(r, Err):
            return r
        return [[r.get(i, j) for j in range(r.width)] for i in range(r.height)]
    if k == "const":
        return node[1]
    if k == "bin":
        a, b = ev_array(node[2], ctx), ev_array(node[3], ctx)
        return _broadcast(node[1], a, b)
    if k == "call" and node[1] == "ROW":
        r = make_ref(node[2][0], ctx) if node[2] else None
        if r is None:
            return float(ctx.row)
        return [[float(r.r1 + i)] for i in range(r.height)]
    if k == "pct":
        a = ev_array(node[1], ctx)
        return _broadcast("/", a, 100.0)
    return val(node, ctx)


def _broadcast(op, a, b):
    def one(x, y):
        if op in ("=", "<>", "<", ">", "<=", ">="):
            return compare(op, x, y)
        return arith(op, x, y)
    if isinstance(a, list) and isinstance(b, list):
        return [[one(a[i][j], b[i][j]) if i < len(b) and j < len(b[i]) else NA for j in range(len(a[i]))] for i in range(len(a))]
    if isinstance(a, list):
        return [[one(x, b) for x in row] for row in a]
    if isinstance(b, list):
        return [[one(a, y) for y in row] for row in b]
    return one(a, b)


def f_sumproduct(args, ctx):
    arrs = [ev_array(a, ctx) for a in args]
    if any(not isinstance(a, list) for a in arrs):
        return VALUE
    h, w = len(arrs[0]), len(arrs[0][0])
    if any(len(a) != h or len(a[0]) != w for a in arrs):
        return VALUE
    s = 0.0
    for i in range(h):
        for j in range(w):
            p = 1.0
            for a in arrs:
                x = a[i][j]
                if isinstance(x, Err):
                    return x
                p *= x if (isinstance(x, float) and not isinstance(x, bool)) else 0.0
            s += p
    return s


def f_aggregate(args, ctx):
    fn = to_num(val(args[0], ctx))
    opt = to_num(val(args[1], ctx))
    if fn != 15 or opt not in (2.0, 6.0):
        raise Unsupported("AGGREGATE %s,%s" % (fn, opt))
    arr = ev_array(args[2], ctx)
    k = to_num(val(args[3], ctx))
    xs = sorted(x for row in (arr if isinstance(arr, list) else [[arr]]) for x in row if isinstance(x, float) and not isinstance(x, bool))
    k = int(k)
    return NUM if k < 1 or k > len(xs) else xs[k - 1]


def f_row(args, ctx):
    if not args:
        return float(ctx.row)
    r = ev(args[0], ctx)
    return float(r.r1) if isinstance(r, Ref) else VALUE


def f_rank(args, ctx):
    x = to_num(val(args[0], ctx))
    if isinstance(x, Err):
        return x
    r = ev(args[1], ctx)
    order = to_num(val(args[2], ctx)) if len(args) > 2 else 0.0
    nums = [v for v in r.cells() if isinstance(v, float) and not isinstance(v, bool)]
    if x not in nums:
        return NA
    return float(1 + sum(1 for v in nums if (v > x if not order else v < x)))


def f_substitute(args, ctx):
    t, old, new = (val(a, ctx) for a in args[:3])
    for v in (t, old, new):
        if isinstance(v, Err):
            return v
    return to_text(t).replace(to_text(old), to_text(new)) if to_text(old) else to_text(t)


def f_left(args, ctx):
    t = val(args[0], ctx)
    n = to_num(val(args[1], ctx)) if len(args) > 1 else 1.0
    if isinstance(t, Err):
        return t
    if isinstance(n, Err):
        return n
    return to_text(t)[:int(n)]


def f_value(args, ctx):
    t = val(args[0], ctx)
    if isinstance(t, Err):
        return t
    if isinstance(t, float):
        return t
    x = to_float_text(to_text(t))
    return VALUE if x is None else x


def f_single(args, ctx):
    return scalar(ev(args[0], ctx), ctx)


FUNCS = {
    "SUM": f_sum, "AVERAGE": f_average, "MAX": f_max, "IF": f_if, "IFERROR": f_iferror, "ISNUMBER": f_isnumber,
    "ISTEXT": f_istext, "ISERROR": f_iserror, "AND": lambda a, c: _logic(a, c, "and"), "OR": lambda a, c: _logic(a, c, "or"),
    "MOD": f_mod, "ROUND": lambda a, c: _round(a, c, "round"), "ROUNDDOWN": lambda a, c: _round(a, c, "down"),
    "ROUNDUP": lambda a, c: _round(a, c, "up"), "INT": f_int, "ABS": f_abs, "POWER": f_power, "LOG10": f_log10,
    "VLOOKUP": f_vlookup, "HLOOKUP": lambda a, c: f_vlookup(a, c, True), "LOOKUP": f_lookup, "INDEX": f_index,
    "MATCH": f_match, "OFFSET": f_offset, "SUMIF": f_sumif, "COUNTIF": f_countif, "SUMPRODUCT": f_sumproduct,
    "AGGREGATE": f_aggregate, "ROW": f_row, "RANK": f_rank, "SUBSTITUTE": f_substitute, "LEFT": f_left,
    "VALUE": f_value, "SINGLE": f_single,
}


def evaluate(tree, store, book, sheet_name, row, col):
    ctx = Ctx(store, book, sheet_name, row, col)
    v = ev(tree, ctx)
    v = scalar(v, ctx)
    if v is None:
        return 0.0            # a formula that refers to an empty cell shows 0
    if isinstance(v, list):
        v = v[0][0]
    return v
