"""Quantity tables from CSV or Excel (.xlsx) → candidate quantity rows, each traceable to sheet/row/column.

Recognised columns (Japanese or English header words): 品目/名称/材料 (name), 数量/quantity (quantity),
単位/unit (unit), 区分/工種/部位 (division), 規格/仕様 (specification). A row without a number in the
quantity column is reported, not read as 0. Nothing is calculated here: the rows are candidates that the
user maps to materials and accepts (state 図面から計算 with the trace as source_detail).
"""
from __future__ import annotations

import bisect
import csv
import functools
import heapq
import io
import re
import zipfile
from xml.etree import ElementTree as ET

from ..numbers import number_or_reason

HEADERS = {  # in order of preference: a name / description column is preferred over item codes; "amount" (money) is
    # never a quantity
    "name": ("名称", "品名", "材料", "品目", "material", "description", "name", "項目", "item"),
    "quantity": ("数量", "quantity", "qty", "数"),
    "unit": ("単位", "unit", "uom"),
    "division": ("区分", "工種", "部位", "division", "category", "element"),
    # 摘要 is the specification column of the usual 内訳書 (名称・摘要・数量・単位・単価・金額・備考); 形状・寸法 likewise
    "specification": ("規格", "仕様", "摘要", "寸法", "形状", "spec", "specification", "grade"),
}
MAX_TEXT = 300                                    # characters of a name / unit / spec / division cell that are kept
MONEY_WORDS = ("費", "単価", "金額", "価格", "代価", "円", "cost", "price", "rate", "amount", "value")
MAX_FORMULA_CHARS = 3_000_000                     # distinct formula text scanned over the whole workbook
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
# "Strict Open XML Spreadsheet" (ISO/IEC 29500 strict) uses other namespaces for the same elements
STRICT = {"http://purl.oclc.org/ooxml/spreadsheetml/main": "http://purl.oclc.org/ooxml/officeDocument/relationships"}
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
MAX_COL_ELEMENTS = 16_384                         # <col> elements of one sheet (one per column at most in Excel)
MAX_PART, MAX_TOTAL = 10_000_000, 40_000_000     # bytes after decompression (real quantity tables are far smaller)
MAX_COLS, MAX_CELLS, MAX_SHARED = 16_384, 1_000_000, 300_000   # Excel's column limit (XFD); all sheets together
MAX_CSV_BYTES, MAX_CSV_ROWS = 10_000_000, 100_000
MAX_STRING = 32_767                               # Excel's limit for the text of one cell
MAX_CHARS = 50_000_000                            # characters of cell text over the whole workbook (counted per cell)
MAX_ROWS, MAX_ROW_NUMBER = 1_000_000, 1_048_576   # rows of all sheets together; Excel's last row


class ImportError_(ValueError):
    pass


MAX_SHEET_LABEL = 31                              # Excel's limit for a sheet name: longer ones are cut where shown


def sheet_label(name) -> str:
    """A sheet's name as shown in a trace, a reason or a warning (the full name is kept for following references)."""
    s = str(name)
    return s if len(s) <= MAX_SHEET_LABEL else s[:MAX_SHEET_LABEL] + "…"


_ASCII_WORD = re.compile(r"[a-z]+")


@functools.lru_cache(maxsize=256)
def _word_rx(words: tuple):
    """One pattern for a list of header words: an English word only as a whole word (with a plural s), so that
    "Upper floors", "Superstructure" or "Separate" never read as "per" or "rate"; other words anywhere."""
    alts = []
    for w in words:
        w = w.lower()
        alts.append(r"(?<![a-z])%s(?:e?s)?(?![a-z])" % re.escape(w) if _ASCII_WORD.fullmatch(w) else re.escape(w))
    return re.compile("|".join(alts))


def _has_word(hs: str, words: tuple) -> bool:
    return _word_rx(tuple(words)).search(hs) is not None


_CAMEL = re.compile(r"(?<=[a-z])(?=[A-Z])")


def _head_text(h) -> str:
    """A header cell as matched: cut, stripped, a camelCase run split into words (MaterialCost, UnitPrice, TotalVolume
    are "material cost", "unit price", "total volume": whole-word matching must still see cost, price, volume), lowered."""
    return _CAMEL.sub(" ", str(h or "")[:MAX_TEXT].strip()).lower()


def _num(s):
    """A quantity cell: the same rule as the screen (a comma only as a thousands separator, no inner spaces)."""
    return number_or_reason(s)[0]


def _header_map(row: list) -> dict:
    """The column of each key: the column whose header matches the most preferred word ("Item description" is the name
    before "Item"); an exact match only breaks a tie of the same word; money columns (材料費, Amount …) are never the name
    or the quantity; a column is used for one key only."""
    out, used = {}, set()
    heads = [_head_text(h) for h in row]
    for key, words in HEADERS.items():
        best = None
        for j, hs in enumerate(heads):
            if j in used or not hs:
                continue
            if key in ("name", "quantity") and _has_word(hs, MONEY_WORDS):
                continue                                   # 材料費, 材料単価, Material cost, Amount …
            for rank, w in enumerate(words):
                w = w.lower()
                exact = w == hs
                if exact or (len(w) > 1 and w in hs):
                    score = (rank, 0 if exact else 1, j)
                    if best is None or score < best:
                        best = score
                    break
        if best is not None:
            out[key] = best[2]
            used.add(best[2])
    return out


MAX_FORMULA = 8192                                 # Excel's limit for the text of one formula
# linear: strings ("" escapes a quote), quoted sheet names ('' escapes an apostrophe: 'Owner''s BoQ'!C2), words in any
# script (内訳!B2), single characters
# (an unquoted sheet name may hold a katakana middle dot: LCR･LCW集計!S77 — Excel writes it without quotes)
_FTOK = re.compile(r'"(?:[^"]|"")*"|\'(?:[^\']|\'\')*\'|[\w.$\\\uff65\u30fb]+|.', re.S)
_CELL = re.compile(r"(\$?)([A-Za-z]{1,3})(\$?)(\d+)")
MAX_NAME_FOLLOWS = 20                             # defined names followed per formula (a name may refer to itself)
_COLWORD = re.compile(r"(\$?)([A-Za-z]{1,3})")
_ROWWORD = re.compile(r"\$?\d+")
# error literals are values, not names (#N/A would otherwise read as the names N and A)
_ERRLIT = re.compile(r"#(?:NULL!|DIV/0!|VALUE!|REF!|NAME\?|NUM!|N/A|GETTING_DATA|SPILL!|CALC!|FIELD!|BLOCKED!|UNKNOWN!|"
                     r"CONNECT!|BUSY!|PYTHON!|EXTERNAL!)", re.I)
_EXTBOOK = re.compile(r"\[\d+\]")                 # [1]明細!C2: a link to another workbook, as Excel stores it
_EXTREF = re.compile(r"(?:^|[^\w\]'.\\])\[\d+\]")
DATATABLE = "\x00DATATABLE"                       # the formula of a What-If data table's cells (no formula to follow)
_SR_SPECIAL = ("#all", "#data", "#headers", "#totals", "#this row")


def _split_structured(f: str):
    """(text with each structured (table) reference replaced by __SR<k>__, ((table name or "", inner text) …)), or None
    when the brackets do not balance. [1] before a sheet name is a workbook link and is left in place."""
    if "[" not in f:
        return f, ()
    out, spans, i, n, ident = [], [], 0, len(f), None
    last = 0
    while i < n:
        ch = f[i]
        if ch in "\"'":
            j = i + 1
            while j < n:
                if f[j] == ch:
                    if j + 1 < n and f[j + 1] == ch:
                        j += 2
                        continue
                    break
                j += 1
            i, ident = j + 1, None
            continue
        if ch == "[":
            m = _EXTBOOK.match(f, i)
            if m and ident is None:
                i, ident = m.end(), None
                continue
            depth, j = 0, i
            while j < n:
                c = f[j]
                if c == "'":                       # ' escapes the next character in a column name
                    j += 2
                    continue
                if c == "[":
                    depth += 1
                elif c == "]":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            if j >= n:
                return None
            start = ident if ident is not None else i
            out.append(f[last:start])
            out.append(" __SR%d__ " % len(spans))
            spans.append((f[start:i], f[i + 1:j]))
            last = i = j + 1
            ident = None
            continue
        if ch.isalnum() or ch in "_.\\":
            if ident is None:
                ident = i
        else:
            ident = None
        i += 1
    out.append(f[last:])
    return "".join(out), tuple(spans)


@functools.lru_cache(maxsize=4096)
def _formula_parts(f: str) -> tuple:
    """(function names, references, other names, structured references, 3D reference?, computed range?, name ranges)
    of a formula, by one linear scan. A reference is (sheet or None, first column absolute?, first column, last column
    absolute?, last column, first row absolute?, first row, last row absolute?, last row): a cell (B5), a range (A2:D2;
    the sheet of the first end carries to the second; ends written in reverse order are put in order), a whole column
    (C:C, rows None) or whole rows (2:5, every column). Text inside double quotes is skipped; a word or quoted name
    before "!" names the sheet. A reference over several sheets (明細:集計!C2) is flagged, so is a range whose end is
    computed (A2:INDEX(…)); a range between two defined names (開始:終了) is kept as a name range. Structured references
    are None when their brackets do not balance."""
    f = _ERRLIT.sub('""', f)
    sp = _split_structured(f)
    if sp is None:
        return frozenset(), (), (), None, False, False, (), frozenset()
    f, structured = sp
    toks, sheet, three_d, computed = [], None, False, False
    for m in _FTOK.finditer(f):
        tok = m.group(0)
        nxt = f[m.end():m.end() + 1]
        if tok.isspace() or tok == "!":
            continue
        if tok[0] == "'" and len(tok) > 1:
            if nxt == "!":
                sheet = tok[1:-1].replace("''", "'")
                if ":" in sheet:
                    three_d = True
            continue
        if tok[0] == '"':
            toks.append(("str", None, None))
            sheet = None
            continue
        if tok[0].isalnum() or tok[0] in "_.$\\\uff65\u30fb":
            if nxt == "!":
                sheet = tok
                continue
            if nxt == "(":
                toks.append(("func", re.sub(r"^(?:_XL(?:FN|WS)\.)+", "", tok.upper()), None))
            elif _CELL.fullmatch(tok):
                c = _CELL.fullmatch(tok)
                toks.append(("ref", (c.group(1) == "$", _col_index(c.group(2).upper()), c.group(3) == "$", int(c.group(4))), sheet))
            elif _COLWORD.fullmatch(tok):
                c = _COLWORD.fullmatch(tok)
                toks.append(("col", (c.group(1) == "$", _col_index(c.group(2).upper()), tok.upper()), sheet))
            elif _ROWWORD.fullmatch(tok):
                toks.append(("row", (tok.startswith("$"), int(tok.lstrip("$"))), sheet))
            elif tok[0].isdigit() or tok[0] == ".":
                toks.append(("num", None, None))           # 2.4, 1E (of 1E-3): a number, not a name
            else:
                toks.append(("name", tok.upper(), sheet))
            sheet = None
            continue
        toks.append(("op", tok, None))
    funcs, refs, names, nranges, seq = set(), [], [], [], []
    k = 0
    colon = ("op", ":", None)
    while k < len(toks):
        kind, val, sh = toks[k]
        if kind in ("ref", "col", "row", "name") and sh is None and k + 2 < len(toks) and toks[k + 1] == colon \
                and toks[k + 2][0] in ("ref", "col", "row") and toks[k + 2][2] is not None:
            three_d = True                                  # 明細:集計!C2 — the first sheet is the word before ":"
        if toks[k] == colon and ((k > 0 and (toks[k - 1][0] == "func" or toks[k - 1] == ("op", ")", None)))
                                 or (k + 1 < len(toks) and toks[k + 1][0] == "func")):
            computed = True                                 # A2:INDEX(C:C,9), INDEX(…):C9 — the end is computed
        if kind in ("ref", "col", "row", "name") and k + 2 < len(toks) and toks[k + 1] == colon \
                and toks[k + 2][0] in ("ref", "col", "row", "name"):
            kind2, val2, sh2 = toks[k + 2]
            if "name" in (kind, kind2) or {kind, kind2} == {"ref", "col"}:
                # 開始:終了 (two defined names), 開始:C9, A2:QTY: the block between what the two ends are
                nranges.append((toks[k], toks[k + 2]))
                seq.append(("nr", len(nranges) - 1))
                k += 3
                continue
            if kind == "row" or kind2 == "row":                         # whole rows: every column
                rr = [x[-1] if isinstance(x, tuple) else None for x in (val, val2)]
                ra = [x[-2] if isinstance(x, tuple) else True for x in (val, val2)]
                ends = [(ra[0], rr[0]), (ra[1], rr[1])]
                if None not in rr and rr[0] > rr[1]:
                    ends.reverse()
                refs.append((sh, True, 0, True, MAX_COLS - 1, ends[0][0], ends[0][1], ends[1][0], ends[1][1]))
            else:
                (a1, c1), (a2, c2) = val[:2], val2[:2]
                r1 = (val[2], val[3]) if kind == "ref" else (True, None)     # a whole column: every row
                r2 = (val2[2], val2[3]) if kind2 == "ref" else (True, None)
                if c1 > c2:
                    (a1, c1), (a2, c2) = (a2, c2), (a1, c1)
                if r1[1] is not None and r2[1] is not None and r1[1] > r2[1]:
                    r1, r2 = r2, r1
                refs.append((sh, a1, c1, a2, c2, r1[0], r1[1], r2[0], r2[1]))
            seq.append(("ref", len(refs) - 1))
            k += 3
            continue
        if kind == "ref":
            refs.append((sh, val[0], val[1], val[0], val[1], val[2], val[3], val[2], val[3]))
            seq.append(("ref", len(refs) - 1))
        elif kind == "col":
            names.append((val[2], sh))                              # a lone 1-3 letter word is a name, not a column
            seq.append(("nm", len(names) - 1))
        elif kind == "name" and val.startswith("__SR") and val.endswith("__") and val[4:-2].isdigit():
            seq.append(("sr", int(val[4:-2])))                     # a structured (table) reference
        elif kind == "name":
            names.append((val, sh))
            seq.append(("nm", len(names) - 1))
        elif kind == "func":
            funcs.add(val)
            seq.append(("func", val))
        elif kind == "op":
            seq.append(("op", val))
        else:
            seq.append(("val", None))                               # a number, a string, a lone row number
        k += 1
    return frozenset(funcs), tuple(refs), tuple(names), structured, three_d, computed, tuple(nranges), \
        _additive(seq, tuple(nm for nm, _ in names))


# How a formula's value is made of its references (see _additive). Functions whose value is (one of) their arguments
# added up, rounded, picked or reshaped: a reference in such a place is part of the value. SUMPRODUCT adds its one
# argument that is not a 0/1 condition (SUMPRODUCT(R), SUMPRODUCT((名称=x)*R), SUMPRODUCT(--(名称=x), R)); the summed
# range of SUMIF / SUMIFS is added, its criteria are not; a lookup adds what it returns (INDEX, VLOOKUP, XLOOKUP …).
_REFKINDS = ("ref", "nm", "sr", "nr")
_ADD_ALL = frozenset(("SUM", "MAX", "MIN", "SUBTOTAL", "AGGREGATE", "AVERAGE", "AVERAGEA", "MEDIAN", "MAXA", "MINA", "MODE",
                      "MODE.SNGL", "HSTACK", "VSTACK"))
_ADD_FIRST = frozenset(("ROUND", "ROUNDUP", "ROUNDDOWN", "TRUNC", "INT", "ABS", "N", "VALUE", "CEILING", "FLOOR", "MROUND",
                        "CEILING.MATH", "FLOOR.MATH", "ODD", "EVEN", "LARGE", "SMALL", "INDEX", "SUMIFS", "AVERAGEIFS",
                        "MAXIFS", "MINIFS", "DSUM", "DMAX", "DMIN", "DAVERAGE", "DGET", "FILTER", "SORT", "SORTBY", "UNIQUE",
                        "TAKE", "DROP", "CHOOSECOLS", "CHOOSEROWS", "TOCOL", "TOROW", "TRANSPOSE", "WRAPROWS", "WRAPCOLS",
                        "EXPAND", "ANCHORARRAY", "SINGLE"))
_ADD_AT = {"VLOOKUP": (1,), "HLOOKUP": (1,), "XLOOKUP": (2, 3), "GROUPBY": (1,), "PIVOTBY": (2,)}
_ADD_BRANCH = {"IF": (1, 2), "IFERROR": (0, 1), "IFNA": (0, 1)}       # CHOOSE, IFS, SWITCH: see _picked
# functions whose value depends on their references only through a condition, a count or a position (a 0/1 mask
# in SUMPRODUCT((名称=x)*R), ISNUMBER(SEARCH(…)), COUNTIF …): never a quantity factor
_MASK = frozenset(("ISNUMBER", "ISTEXT", "ISNONTEXT", "ISBLANK", "ISERROR", "ISERR", "ISNA", "ISLOGICAL", "ISEVEN", "ISODD",
                   "ISFORMULA", "ISREF", "NOT", "AND", "OR", "XOR", "EXACT", "COUNT", "COUNTA", "COUNTBLANK", "COUNTIF",
                   "COUNTIFS", "ROW", "ROWS", "COLUMN", "COLUMNS", "LEN", "SEARCH", "FIND", "SEARCHB", "FINDB", "MATCH",
                   "XMATCH"))
# lookups that return one cell of a table (a unit mass, a density): such a cell multiplying another reference is a factor
_LOOKUP_ONE = frozenset(("VLOOKUP", "HLOOKUP", "XLOOKUP", "LOOKUP", "INDEX", "LARGE", "SMALL", "DGET"))
MAX_NEST = 64                                     # Excel's limit for nested functions in one formula
UNPARSED = ("unparsed",)                          # in _additive's answer: the formula's shape was not understood


class _Unparsed(Exception):
    pass


def _picked(f: str, n: int):
    """The argument places whose value a choosing function returns (None: not a choosing function)."""
    if f in _ADD_BRANCH:
        return [i for i in _ADD_BRANCH[f] if i < n]
    if f == "CHOOSE":
        return list(range(1, n))
    if f == "IFS":
        return list(range(1, n, 2))
    if f == "SWITCH":                             # SWITCH(expr, v1, r1, v2, r2, …, default)
        return list(range(2, n, 2)) + ([n - 1] if n > 1 and (n - 1) % 2 == 1 else [])
    if f in ("SUMIF", "AVERAGEIF"):
        return [2] if n == 3 else [0]
    if f == "LOOKUP":
        return [2] if n == 3 else [1]
    if f in _ADD_AT:
        return [i for i in _ADD_AT[f] if i < n]
    return None


def _additive(seq, names=()) -> frozenset:
    """The references (their tokens) of a formula that are ADDED into its value: alone or in a sum, rounded, chosen by
    IF / IFS / SWITCH / CHOOSE, returned by a lookup, scaled by a number (C2*1.05), by a 0/1 condition ((名称=x)*C2,
    --(名称=x)) or by another reference (SUM(明細!C2:E2)*(1+$E$1), 長さ×$G$2: each factor that is not a divisor may carry
    the quantity, as C2*1.05 does — a factor in a money / factor column is no part of a row's quantity, see documents),
    passed to a function this parser does not know (MMULT, PRODUCT, REDUCE, MAP, CONVERT …: its arguments may make its
    value); not those that sit inside a condition, a count or a lookup's key, that divide, or are raised to a power, and
    not a value looked up (VLOOKUP, INDEX …: one cell of a table, a unit mass) that multiplies another reference. A LET
    name is what its value is; a LAMBDA parameter is nothing of its own. One linear pass (recursive descent, at most
    MAX_NEST levels); a shape it does not understand gives UNPARSED (the formula is then not checked), never a guess
    (13 回目: an unknown function and a product of references counted as adding nothing, the one unsafe default)."""
    n = len(seq)
    if not n:
        return frozenset()                        # an empty formula adds nothing
    depth = mx = 0
    for t in seq:
        if t == ("op", "("):
            depth += 1
            mx = max(mx, depth)
        elif t == ("op", ")"):
            depth -= 1
    if mx > MAX_NEST:
        return frozenset((UNPARSED,))
    pos = [0]
    env = []                                      # LET scopes: [{name: (all refs, added, mask)}]
    picks = set()                                 # added tokens that are one looked-up cell (not summed since)
    E = (frozenset(), frozenset(), False)

    def peek(k=0):
        return seq[pos[0] + k] if pos[0] + k < n else ("end", None)

    def take():
        t = peek()
        pos[0] += 1
        return t

    def expect(op):
        if take() != ("op", op):
            raise _Unparsed()

    def arg():                                    # an argument; an empty one (IF(A1,,B1)) is nothing
        if peek() in (("op", ","), ("op", ")")):
            return E
        return cmp_()

    def arglist():
        out = [arg()]
        while peek() == ("op", ","):
            take()
            out.append(arg())
        expect(")")
        return out

    def let_():                                   # LET(name1, value1, …, calculation)
        scope = {}
        env.append(scope)
        try:
            alls = set()
            while peek()[0] == "nm" and peek(1) == ("op", ","):
                nm = names[peek()[1]] if peek()[1] < len(names) else None
                take()
                take()
                v = arg()
                alls |= v[0]
                scope[nm] = v
                if take() != ("op", ","):
                    raise _Unparsed()
            r = arg()
            expect(")")
            return frozenset(alls | r[0]), r[1], r[2]
        finally:
            env.pop()

    def lambda_():                                # LAMBDA(param, …, body): the parameters are bound by the caller
        scope = {}
        env.append(scope)
        try:
            while peek()[0] == "nm" and peek(1) == ("op", ","):
                nm = names[peek()[1]] if peek()[1] < len(names) else None
                take()
                take()
                scope[nm] = E
            r = arg()
            expect(")")
            return r[0], r[1], False
        finally:
            env.pop()

    def call(f):
        if f == "LET":
            return let_()
        if f == "LAMBDA":
            return lambda_()
        res = arglist()
        alls = frozenset().union(*(r[0] for r in res))
        if f in _ADD_ALL:
            got = frozenset().union(*(r[1] for r in res))
            picks.difference_update(got)          # summed: no longer one looked-up cell
            return alls, got, False
        if f in _ADD_FIRST:
            if f in _LOOKUP_ONE:
                picks.update(res[0][1])
            return alls, res[0][1], res[0][2] if f in ("N", "VALUE", "INT", "ABS", "ROUND") else False
        if f == "SUMPRODUCT":                     # every array that is not a 0/1 condition is a factor of the sum
            live = [r for r in res if r[0] and not r[2]]
            got = frozenset().union(*(r[1] for r in live))
            picks.difference_update(got)
            return alls, got, False
        if f in _MASK:
            return alls, frozenset(), True
        pick = _picked(f, len(res))
        if pick is not None:
            got = [res[i] for i in pick]
            mask = bool(alls) and all(r[2] or not r[0] for r in got) and f not in _ADD_AT and f not in ("SUMIF", "AVERAGEIF", "LOOKUP")
            added = frozenset().union(*(r[1] for r in got))
            if f in _LOOKUP_ONE:
                picks.update(added)
            return alls, added, mask
        got = frozenset().union(*(r[1] for r in res))   # a function not known here: its arguments may make its value
        picks.difference_update(got)
        return alls, got, False

    def primary():
        t = take()
        if t[0] == "nm":
            nm = names[t[1]] if t[1] < len(names) else None
            for scope in reversed(env):
                if nm in scope:
                    return scope[nm]
            return frozenset((t,)), frozenset((t,)), False
        if t[0] in _REFKINDS:
            return frozenset((t,)), frozenset((t,)), False
        if t[0] == "val":
            return E
        if t[0] == "func":
            expect("(")
            return call(t[1])
        if t == ("op", "("):
            r = [cmp_()]
            while peek() == ("op", ","):          # (A1:B2,D1:D9): a union of references
                take()
                r.append(cmp_())
            expect(")")
            if len(r) == 1:
                return r[0]
            return frozenset().union(*(x[0] for x in r)), frozenset().union(*(x[1] for x in r)), False
        if t == ("op", "{"):                     # an array constant {1,2;3,4}: numbers only
            while peek() != ("op", "}"):
                if take()[0] == "end":
                    raise _Unparsed()
            take()
            return E
        raise _Unparsed()

    def postfix():
        r = primary()
        while peek() in (("op", "%"), ("op", "#")):          # 5%, A1# (a spilled range)
            take()
        return r

    def unary():
        while peek() in (("op", "-"), ("op", "+"), ("op", "@")):
            take()
        return postfix()

    def factor():
        a = unary()
        while peek() == ("op", "^"):
            take()
            b = unary()
            a = (a[0] | b[0], frozenset(), False)
        return a

    def term():
        fs = [(None, factor())]
        while peek() in (("op", "*"), ("op", "/")):
            op = take()[1]
            fs.append((op, factor()))
        if len(fs) == 1:
            return fs[0][1]
        alls = frozenset().union(*(f[1][0] for f in fs))
        withrefs = [f for f in fs if f[1][0]]
        if withrefs and all(f[1][2] for f in withrefs):
            return alls, frozenset(), True                    # a product of conditions is a condition
        live = [f for f in withrefs if not f[1][2]]
        if len(live) == 1 and live[0][0] != "/":
            return alls, live[0][1][1], False                 # one reference scaled by numbers or by conditions
        # several references multiplied: each that does not divide may carry the quantity (C2*1.05 and C2*(1+$E$1)
        # alike), except a looked-up cell (長さ×VLOOKUP(径, 単位質量表, 2): a unit mass)
        return alls, frozenset().union(*(f[1][1] - picks for f in live if f[0] != "/")), False

    def sum_():
        rs = [term()]
        while peek() in (("op", "+"), ("op", "-")):
            take()
            rs.append(term())
        if len(rs) == 1:
            return rs[0]
        withrefs = [r for r in rs if r[0]]
        mask = bool(withrefs) and all(r[2] for r in withrefs)
        return frozenset().union(*(r[0] for r in rs)), frozenset().union(*(r[1] for r in rs)), mask

    def cat():
        a = sum_()
        while peek() == ("op", "&"):
            take()
            b = sum_()
            a = (a[0] | b[0], frozenset(), False)
        return a

    def cmp_():
        a = cat()
        while peek()[0] == "op" and peek()[1] in ("=", "<", ">"):
            op = take()[1]
            if op in ("<", ">") and peek() in (("op", "="), ("op", ">")):
                take()
            b = cat()
            a = (a[0] | b[0], frozenset(), True)
        return a

    try:
        r = cmp_()
        while peek() == ("op", ","):                         # a name defined as a union: 明細!$C$2,明細!$C$5
            take()
            b = cmp_()
            r = (r[0] | b[0], r[1] | b[1], False)
    except (_Unparsed, IndexError):
        return frozenset((UNPARSED,))
    if pos[0] < n:
        return frozenset((UNPARSED,))
    return frozenset(r[1])


def _formula_tuple(formula):
    if isinstance(formula, str):
        return formula, 0, False, 0
    return (tuple(formula) + (0,))[:4] if len(formula) == 3 else tuple(formula)


def name_target(defined: dict, nm: str, sheet_cf: str):
    """The definition of a defined name as Excel resolves it on a sheet: the sheet's own (local) name first, then the
    workbook's. `defined` maps NAME -> text (workbook names) or NAME -> {sheet casefolded or None: text}."""
    t = defined.get(nm)
    if isinstance(t, dict):
        return t[sheet_cf] if sheet_cf in t else t.get(None)
    return t


def _sr_items(inner: str):
    """The parts of a structured reference's brackets: [("item", text) | ("sep", ":" or ",")], or None."""
    s = inner.strip()
    if "[" not in s:
        if s.startswith("@"):
            return [("item", "#this row")] + ([("sep", ","), ("item", s[1:].strip())] if s[1:].strip() else [])
        return [("item", s)] if s else []
    out, i, n = [], 0, len(s)
    while i < n:
        ch = s[i]
        if ch.isspace():
            i += 1
        elif ch == "@":
            out += [("item", "#this row"), ("sep", ",")]
            i += 1
        elif ch in ",:":
            out.append(("sep", ch))
            i += 1
        elif ch == "[":
            j, buf = i + 1, []
            while j < n and s[j] != "]":
                if s[j] == "'" and j + 1 < n:
                    buf.append(s[j + 1])
                    j += 2
                    continue
                buf.append(s[j])
                j += 1
            if j >= n:
                return None
            out.append(("item", "".join(buf)))
            i = j + 1
        else:
            return None
    return out


def _structured_block(table: str, inner: str, ctx: dict):
    """(why, block) of one structured reference: the rows (data rows unless #All / #Headers / #Totals / #This Row or @)
    and the columns (named, a range of named columns, or all) of the table."""
    tables = ctx.get("tables") or {}
    this = (ctx.get("sheet") or "").casefold()
    if table:
        T = tables.get(table.upper())
        if T is None:
            return "表の参照（%s）の範囲が分からない。必要なら手で入れる" % table[:40], None
    else:
        row, col = ctx.get("row"), ctx.get("col")
        T = next((t for t in tables.values() if t["sheet"] == this and row is not None and col is not None
                  and t["r1"] <= row <= t["r2"] and t["c1"] <= col <= t["c2"]), None)
        if T is None:
            return "表の中でない場所の表の参照（[@…]）は確かめられない。必要なら手で入れる", None
    items = _sr_items(inner)
    if items is None:
        return "表の参照の書き方を読めない。必要なら手で入れる", None
    d1, d2 = T["r1"] + T["hdr"], T["r2"] - T["tot"]
    rows, cols, pend = [], [], None
    for kind, x in items:
        if kind == "sep":
            pend = x if x == ":" else None
            continue
        low = x.strip().casefold()
        if low in _SR_SPECIAL:
            if low == "#this row":
                r = ctx.get("row")
                if r is None or not d1 <= r <= d2:
                    return "表の同じ行の参照（@）を確かめられない。必要なら手で入れる", None
                rows.append((r, r))
            elif low == "#all":
                rows.append((T["r1"], T["r2"]))
            elif low == "#data":
                rows.append((d1, d2))
            elif low == "#headers":
                rows.append((T["r1"], T["r1"] + T["hdr"] - 1))
            else:
                rows.append((T["r2"] - T["tot"] + 1, T["r2"]))
            continue
        if low not in T["cols"]:
            return "表 %s に列「%s」が無い。必要なら手で入れる" % (T["name"][:40], x[:40]), None
        c = T["c1"] + T["cols"].index(low)
        if pend == ":" and cols:
            a, _b = cols.pop()
            cols.append((min(a, c), max(a, c)))
        else:
            cols.append((c, c))
        pend = None
    rlo = min((a for a, _ in rows), default=d1)
    rhi = max((b for _, b in rows), default=d2)
    clo = min((a for a, _ in cols), default=T["c1"])
    chi = max((b for _, b in cols), default=T["c2"])
    if rlo > rhi:
        return None, None                                  # an empty part of the table (no totals row …)
    return None, (None if T["sheet"] == this else T["sheet"], clo, chi, rlo, rhi)


class FollowBudget(Exception):
    """Raised by ctx["spend"] when the walk of one document's formulas goes over its budget."""


MAX_NAME_DEPTH = 20                               # defined names inside names (a chain deeper than this is not checked)


def _name_shift(ctx: dict) -> tuple:
    """(column shift, row shift) of a defined name's relative references. Excel stores them relative to A1 and resolves
    them from the cell that uses the name: 明細!$C1 used in row 5 is 明細!$C5, 明細!B1 used in C2 is 明細!D2."""
    col, row = ctx.get("col"), ctx.get("row")
    return (col or 0), ((row or 1) - 1)


def _relative(text: str) -> bool:
    """Whether what a name's definition refers to depends on the cell that uses it: a relative reference, a table
    reference or another name in it (then the name is followed again for each cell that uses it)."""
    funcs, refs, names, structured, _t, _c, nranges, _a = _formula_parts(text)
    if structured is None or names or structured or nranges:
        return True
    return any(not (a1 and a2 and ar1 and ar2) for _s, a1, _c1, a2, _c2, ar1, _r1, ar2, _r2 in refs)


def _expand_name(nm: str, scope: str, target: str, ctx: dict, path: frozenset) -> tuple:
    """(why, blocks) of one defined name used in a formula: its definition followed from the using cell (relative
    references move with it). A name that reaches itself (directly or through other names) is a circular reference
    (#REF! in Excel) and cannot be checked. What a name reaches is kept per document (and per using cell only when it
    depends on it); every block it gives is charged to the document's budget each time it is used."""
    key = (scope, nm)
    if key in path:
        return "名前 %s が自分自身を参照している（循環する参照）ので確かめられない。必要なら手で入れる" % nm[:40], []
    if len(path) >= MAX_NAME_DEPTH:
        return "名前の中の名前が深すぎて確かめられない（%d 段まで）。必要なら手で入れる" % MAX_NAME_DEPTH, []
    text = target.lstrip("=")
    shift = _name_shift(ctx) if _relative(text) else (0, 0)
    memo = ctx.get("name_memo")
    mkey = (scope, nm, (ctx.get("sheet") or "").casefold(), shift)
    got = memo.get(mkey) if memo is not None else None
    if got is None:
        got = formula_walk((text, shift[0], False, shift[1]), ctx, path | {key})
        if memo is not None and (not path or got[0] is None):
            memo[mkey] = got                               # (a cycle / depth answer is kept only from the top)
    spend = ctx.get("spend")
    if spend is not None:
        spend(len(got[1]) + 1)
    return got


def _lone_block(tok, ctx, path):
    """(why, sheet or None, c1, c2, r1, r2) of one end of a name range (a defined name that is one block, or a cell)."""
    kind, val, sh = tok
    if kind == "ref":
        return None, (None if sh is None else sh.casefold(), val[1], val[1], val[3], val[3])
    nm = val if kind == "name" else val[2]
    this = (ctx.get("sheet") or "").casefold()
    scope = sh.casefold() if sh else this
    target = name_target(ctx.get("names") or {}, nm, scope)
    if not target:
        return "名前 %s の参照先が分からない。必要なら手で入れる" % nm[:40], None
    why, blocks = _expand_name(nm, scope, target, ctx, path)
    if why or len(blocks) != 1:
        return why or "名前の範囲（%s）の端を確かめられない。必要なら手で入れる" % nm[:40], None
    return None, blocks[0][:5]


@functools.lru_cache(maxsize=4096)
def _let_params(text: str) -> frozenset:
    """The parameter names of LET(name1, value1, …, calculation) and LAMBDA(param, …, body): the names at those
    places only (a workbook name used as a LET value, LET(q, 明細数量, SUM(q)), is followed). Excel writes them as
    _xlpm.x; other writers may not."""
    toks = [m.group(0) for m in _FTOK.finditer(text) if not m.group(0).isspace()]
    out = set()
    for i, tok in enumerate(toks):
        fn = re.sub(r"^(?:_XL(?:FN|WS)\.)+", "", tok.upper())
        if fn not in ("LET", "LAMBDA") or i + 1 >= len(toks) or toks[i + 1] != "(":
            continue
        args, cur, depth = [], [], 0
        for t in toks[i + 2:]:
            if t == "(":
                depth += 1
            elif t == ")":
                if depth == 0:
                    break
                depth -= 1
            if t == "," and depth == 0:
                args.append(cur)
                cur = []
                continue
            cur.append(t)
        args.append(cur)
        slots = range(0, len(args) - 1, 2) if fn == "LET" else range(len(args) - 1)
        for k in slots:
            if len(args[k]) == 1 and (args[k][0][0].isalpha() or args[k][0][0] == "_"):
                out.add(args[k][0].upper())
    return frozenset(out)


def formula_walk(formula, ctx: dict | None = None, _path: frozenset = frozenset()) -> tuple:
    """(why what the formula reaches cannot be checked, or None; the blocks it reaches) for one cell's formula.
    Each block is (sheet casefolded, or None for this sheet; first column; last column; first row; last row; added?),
    None rows meaning every row, and "added" telling whether the block is ADDED into the formula's value (alone, in a
    sum, rounded, chosen, scaled by a number: see _additive) rather than multiplied by another reference, looked up or
    tested. Shared-formula copies are moved by their column / row shift; a defined name is followed to what it refers
    to (the sheet's own name first, then the workbook's; relative references in it from the using cell); a table
    reference becomes the table's rows and columns; a range between two names is the block between their ends.
    Cannot be checked (the quantity is then not added): a shared-formula copy without its master, a formula longer than
    Excel allows, INDIRECT / OFFSET (the reference is computed), a range whose end is computed, a reference moved past
    the sheet's edge, a name or a table that the workbook does not define, a name that reaches itself, a data table,
    references over several sheets, other workbooks.
    `formula` is (text, column shift, master missing?, row shift) or plain text; `ctx` has "sheet" (this sheet's name),
    "names" (defined names), "tables", "row" / "col" of the cell (for [@列] and relative names), and optionally
    "spend" (charged for what names give; raises FollowBudget) and "name_memo" (a dict kept per document)."""
    if not formula:
        return None, []
    text, dcol, no_master, drow = _formula_tuple(formula)
    ctx = ctx or {}
    if no_master:
        return "数式の中身が分からない（共有の数式の元が無い）。必要なら手で入れる", []
    if text == DATATABLE:
        return "データテーブル（What-If 分析）の値は確かめられない。必要なら手で入れる", []
    if len(text) > MAX_FORMULA:
        return "数式が長すぎて確かめられない（%d 文字まで）" % MAX_FORMULA, []
    funcs, refs, names, structured, three_d, computed, nranges, add = _formula_parts(text)
    if structured is None:
        return "数式の括弧を読めない。必要なら手で入れる", []
    if "[" in text and _EXTREF.search(re.sub(r'"(?:[^"]|"")*"', '""', text)):
        return "別のブックを参照した数量は確かめられない。必要なら手で入れる", []
    if funcs & {"INDIRECT", "OFFSET"}:
        return "参照先が数式の中で決まる（INDIRECT・OFFSET）ので確かめられない。必要なら手で入れる", []
    if computed:
        return "範囲の端が数式で決まる（A2:INDEX(…) など）ので確かめられない。必要なら手で入れる", []
    if three_d:
        return "複数のシートにまたがる参照（3D 参照）は確かめられない。必要なら手で入れる", []
    if UNPARSED in add:
        return "数式の形を読めない（入れ子が %d 段より深い、または読めない書き方）ので確かめられない。必要なら手で入れる" % MAX_NEST, []
    this = (ctx.get("sheet") or "").casefold()
    out = []
    for i, (sh, a1, c1, a2, c2, ar1, r1, ar2, r2) in enumerate(refs):
        if sh is not None and sh.startswith("["):
            return "別のブックを参照した数量は確かめられない。必要なら手で入れる", []
        lo, hi = (c1 if a1 else c1 + dcol), (c2 if a2 else c2 + dcol)
        rlo = None if r1 is None else (r1 if ar1 else r1 + drow)
        rhi = None if r2 is None else (r2 if ar2 else r2 + drow)
        if lo > hi:
            lo, hi = hi, lo
        if rlo is not None and rhi is not None and rlo > rhi:
            rlo, rhi = rhi, rlo
        if lo < 0 or hi >= MAX_COLS or (rlo is not None and rlo < 1) or (rhi is not None and rhi > MAX_ROW_NUMBER):
            return "参照がシートの端を越える（#REF! になる）ので確かめられない。必要なら手で入れる", []
        shf = None if sh is None or sh.casefold() == this else sh.casefold()
        out.append((shf, lo, hi, rlo, rhi, ("ref", i) in add))
    for k, (table, inner) in enumerate(structured):
        why, blk = _structured_block(table, inner, ctx)
        if why:
            return why, []
        if blk:
            out.append(tuple(blk) + (("sr", k) in add,))
    for j, (left, right) in enumerate(nranges):
        w1, b1 = _lone_block(left, ctx, _path)
        w2, b2 = _lone_block(right, ctx, _path) if not w1 else (None, None)
        if w1 or w2:
            return w1 or w2, []
        s1 = b1[0] or this
        s2 = b2[0] or this
        if s1 != s2 or None in (b1[3], b1[4], b2[3], b2[4]):
            return "名前の範囲（%s）の端を確かめられない。必要なら手で入れる" % "：".join(str(x[1])[:20] for x in (left, right)), []
        out.append((None if s1 == this else s1, min(b1[1], b2[1]), max(b1[2], b2[2]), min(b1[3], b2[3]), max(b1[4], b2[4]),
                    ("nr", j) in add))
    defined = ctx.get("names") or {}
    params = _let_params(text) if funcs & {"LET", "LAMBDA"} else set()
    used = {}                                              # each name once per formula: added anywhere?
    for j, (nm, sh) in enumerate(names):
        if nm.startswith(("_XLPM.", "__SR")) or nm in params or nm in ("TRUE", "FALSE"):
            continue
        k = (sh.casefold() if sh else this, nm, sh)
        used[k] = used.get(k, False) or ("nm", j) in add
    if len(used) > MAX_NAME_FOLLOWS:
        return "名前の参照が多すぎて確かめられない（%d 個まで）。必要なら手で入れる" % MAX_NAME_FOLLOWS, []
    for (scope, nm, sh), a in used.items():
        target = name_target(defined, nm, scope)
        if not target:
            T = (ctx.get("tables") or {}).get(nm)
            if T is not None:                              # a table's name alone: its data rows
                why, blk = _structured_block(nm, "", ctx)
                if why:
                    return why, []
                if blk:
                    out.append(tuple(blk) + (a,))
                continue
            return "名前 %s の参照先が分からない（ブックに定義が無い）。必要なら手で入れる" % nm[:40], []
        why, more = _expand_name(nm, scope, target, dict(ctx, sheet=sh or ctx.get("sheet")), _path)
        if why:
            return (why if "（名前 " in why else why + "（名前 %s の参照先）" % nm[:40]), []
        if sh and sh.casefold() != this:                   # blocks of a name used as 集計!QTY: on that name's sheet
            more = [(b[0] if b[0] is not None else sh.casefold(),) + tuple(b[1:]) for b in more]
        out += [tuple(b[:5]) + (a and b[5],) for b in more]
    return None, out


def formula_refs(formula, ctx: dict | None = None, _seen=None) -> tuple:
    """(why, blocks (sheet, c1, c2, r1, r2)) of formula_walk, without the "added" flags (`_seen` is kept for older
    callers and not used)."""
    why, blocks = formula_walk(formula, ctx)
    return why, [b[:5] for b in blocks]


def added_blocks(formula, ctx: dict | None = None) -> list:
    """The blocks (sheet casefolded or None, c1, c2, r1, r2) that a formula ADDS into its value (see _additive), moved
    by a shared formula's shift. With `ctx` the names and table references ([@1F], 明細表[@[1F]:[3F]]) are followed too;
    [] when the formula cannot be read or checked."""
    if not formula:
        return []
    text, dcol, no_master, drow = _formula_tuple(formula)
    if no_master or text == DATATABLE or len(text) > MAX_FORMULA:
        return []
    if ctx is not None:
        why, blocks = formula_walk(formula, ctx)
        if why is None:
            return [b[:5] for b in blocks if b[5]]
    parts = _formula_parts(text)
    out = []
    for key in sorted(k for k in parts[7] if k[0] == "ref"):
        sh, a1, c1, a2, c2, ar1, r1, ar2, r2 = parts[1][key[1]]
        lo, hi = (c1 if a1 else c1 + dcol), (c2 if a2 else c2 + dcol)
        rlo = None if r1 is None else (r1 if ar1 else r1 + drow)
        rhi = None if r2 is None else (r2 if ar2 else r2 + drow)
        out.append((None if sh is None else sh.casefold(), min(lo, hi), max(lo, hi), rlo, rhi))
    return out


def formula_reason(formula, col: int = 0, ctx: dict | None = None) -> str | None:
    """Why a formula's references cannot be checked (None when they can; `col` is kept for older callers)."""
    return formula_refs(formula, ctx)[0]


QTY_LIKE = ("数量", "quantity", "qty", "体積", "容積", "重量", "質量", "面積", "volume", "weight", "mass", "area")
NOT_QTY = ("単位", "unit", "per", "/", "比重", "密度", "density", "率", "rate", "係数", "factor")   # 単位質量 kg/m is a factor


def _qty_cols(header: list) -> list:
    """The columns whose header names a quantity (設計数量, 所要数量, 体積, 重量, Qty …; not money): a formula elsewhere that
    reaches one of them on another material row copies that row's quantity."""
    out = []
    for j, h in enumerate(header):
        hs = _head_text(h)
        if hs and _has_word(hs, QTY_LIKE) and not _has_word(hs, MONEY_WORDS + NOT_QTY):
            out.append(j)
    return out


def _factor_cols(header: list) -> list:
    """The columns whose header names money or a factor (単価, 金額, 単位質量, 比重, 密度, 係数, 率, kg/m …): a number there
    is never part of a material row's quantity."""
    return [j for j, h in enumerate(header) if _has_word(_head_text(h), MONEY_WORDS + NOT_QTY)]


HEADING = "見出しの行（数量も単位も無い）は材料の行ではない"


def _find_header(rows: list[list]):
    for i, r in enumerate(rows[:30]):            # the header is one of the first rows
        m = _header_map(r)
        if "name" in m and "quantity" in m:
            return i, m
    return None, {}


def _rows_to_candidates(rows: list[list], sheet: str, doc_id: str, row_numbers: list[int] | None = None,
                        formulas: list[dict] | None = None, fctx: dict | None = None) -> dict:
    hdr_i, hmap = _find_header(rows)
    if hdr_i is None:
        return {"sheet": sheet, "rows": [], "skipped": [], "error": "見出し行（名称・数量）が見つからない"}
    cands, skipped = [], []
    for i in range(hdr_i + 1, len(rows)):
        r = rows[i]
        def col(k):
            j = hmap.get(k)
            return r[j] if j is not None and j < len(r) else None
        def text(k):                             # a long cell is cut before anything copies it
            x = col(k)
            return "" if x is None else str(x)[:MAX_TEXT].strip()
        name = text("name")
        q = _num(col("quantity"))
        if not name and q is None:
            continue
        rn = row_numbers[i] if row_numbers else i + 1          # the sheet's own row number (gaps kept)
        trace = "%s:%s!R%dC%d" % (doc_id, sheet_label(sheet), rn, (hmap["quantity"] or 0) + 1)
        texts = {"name": name, "unit": text("unit"), "division": text("division"), "specification": text("specification")}
        # the columns of the row that hold numbers (a formula elsewhere that adds one of them up copies part of it)
        ncols = tuple(j for j, x in enumerate(r[:MAX_COLS]) if x is not None and x != "" and _num(x) is not None)
        if q is None:
            raw = col("quantity")
            if (raw is None or str(raw).strip() == "") and not texts["unit"]:
                skipped.append(dict(texts, row=rn, trace=trace, reason=HEADING, heading=True, ncols=ncols))
                continue                         # コンクリート工事, 鉄筋工事 …: a heading, not a row left out
            why = number_or_reason(raw)[1]
            skipped.append(dict(texts, row=rn, trace=trace, qtext="" if raw is None else str(raw)[:40], ncols=ncols,
                                reason="数量が数値でない（0 として読まない）" + ("：" + why if why else "")))
            continue
        # a formula's references are checked by the importer, which follows them through the whole workbook (one walk
        # per document, within its budget)
        fobj = (formulas[i] if formulas else {}).get(hmap["quantity"])
        cands.append(dict(texts, quantity=q, trace=trace, row=rn, qf=fobj, ncols=ncols))
    return {"sheet": sheet, "rows": cands, "skipped": skipped, "qcol": hmap["quantity"],
            "qcols": sorted(set(_qty_cols(rows[hdr_i])) | {hmap["quantity"]}),
            "xcols": _factor_cols(rows[hdr_i]),
            "header_row": row_numbers[hdr_i] if row_numbers else hdr_i + 1}


def read_csv(data: bytes, doc_id: str) -> dict:
    for enc in ("utf-8-sig", "cp932", "utf-8"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ImportError_("CSV の文字コードを読めない（UTF-8 か Shift_JIS にする）")
    if len(data) > MAX_CSV_BYTES:
        raise ImportError_("CSV が大きすぎる（%d MB まで）" % (MAX_CSV_BYTES // 1_000_000))
    rows, cells = [], 0
    try:
        for r in csv.reader(io.StringIO(text)):        # streamed with a cell budget, never materialised blindly
            cells += len(r)
            if len(rows) >= MAX_CSV_ROWS or cells > MAX_CELLS:
                raise ImportError_("CSV の行・セルが多すぎる（%d 行・%d セルまで）" % (MAX_CSV_ROWS, MAX_CELLS))
            rows.append(r)
    except csv.Error as e:
        raise ImportError_("CSV として読めない（%s）" % e) from None
    return {"format": "csv", "sheets": [_rows_to_candidates(rows, "csv", doc_id)]}


def _col_index(ref: str) -> int:
    m = re.match(r"[A-Z]+", ref or "")
    if not m or len(m.group(0)) > 3:
        raise ImportError_("セルの位置 %r を読めない（Excel の列の上限を超えている）" % ref)
    letters = m.group(0)
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def xlsx_sheets(data: bytes) -> list[tuple[str, list[list]]]:
    """All sheets of an .xlsx as (name, rows), the rows packed in order (the statistics loaders search by content;
    hidden sheets and rows are read too)."""
    return [(sh["name"], sh["rows"]) for sh in xlsx_workbook(data, skip_hidden=False, formula_budget=None)["sheets"]]


def _plain_text(el, M) -> str:
    """The text of a shared string / inline string: <t> and the <t> of rich-text runs <r>; the phonetic runs <rPh>
    (furigana that Japanese Excel stores with IME input) are not part of the text."""
    parts = []
    for ch in el:
        if ch.tag == M + "t":
            parts.append(ch.text or "")
        elif ch.tag == M + "r":
            t = ch.find(M + "t")
            parts.append((t.text or "") if t is not None else "")
    return "".join(parts)


MAX_NAME_CHARS = 2_000_000                        # characters of defined names (all kept within this; a cut is said)
MAX_TABLES, MAX_ARRAYS = 1_000, 10_000            # Excel tables / array formulas of a workbook
# hidden sheets (helpers, masters, old revisions): their values are not read, their formulas are kept to see copies
# through them. They have their own budget: when it runs out the rest of the sheet is not read, and a quantity that
# reaches that sheet cannot be checked (it is not added); the workbook is still read
MAX_HIDDEN_CELLS, MAX_HIDDEN_FORMULA_CHARS = 2_000_000, 3_000_000
_HAS_FORMULA = re.compile(rb"<(?:[A-Za-z_][\w.-]*:)?f[\s>/]")


def _ref_block(ref: str):
    """(c1, c2, r1, r2) of "A2:D4" or "B5" (0-based columns), or None."""
    parts = (ref or "").replace("$", "").split(":")
    if not 1 <= len(parts) <= 2:
        return None
    ends = []
    for p in parts:
        m = _CELL.fullmatch(p.strip())
        if not m:
            return None
        ends.append((_col_index(m.group(2).upper()), int(m.group(4))))
    (c1, r1), (c2, r2) = ends[0], ends[-1]
    return min(c1, c2), max(c1, c2), min(r1, r2), max(r1, r2)


def xlsx_workbook(data: bytes, skip_hidden: bool = True, formula_budget: int | None = MAX_FORMULA_CHARS) -> dict:
    """{"sheets": [{name, rows, numbers, formulas, hidden_rows, hidden_cols}], "hidden_sheets": [...], "names": {...},
    "tables": {...}, "fcells": {sheet casefolded: {row: {column: formula}}}}.
    Cell values are the stored text/cached values (no formula is evaluated). With skip_hidden, the VALUES of hidden /
    veryHidden sheets, hidden rows and hidden columns are not read (an old revision kept hidden would be added on top of
    the visible one) and are named in the result; their FORMULAS are kept in fcells (with every other cell's), so that a
    visible quantity that copies a detail row through a hidden helper is still seen as a copy. A cell inside an array
    formula's range (a spill, a {…} array) carries the array's formula; a data table's cells carry DATATABLE.
    Defined names keep their scope (a sheet's own name and the workbook's are different names); tables are read from
    each sheet's table parts.

    Guards (a quantity table is small): every part is read through a bounded stream counting the bytes actually
    decompressed; the XML is parsed incrementally (iterparse, elements cleared as they are consumed), with limits on
    shared strings, cells (every <c> element, hidden or not) and columns enforced while parsing."""
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except (zipfile.BadZipFile, ValueError):
        raise ImportError_("Excel（.xlsx）として開けない") from None
    names = z.namelist()
    if any(n.lower().endswith("vbaproject.bin") for n in names):
        raise ImportError_("マクロを含むファイルは読まない（マクロを実行・解析しない方針）")
    budget = {"left": MAX_TOTAL}
    if sum(i.file_size for i in z.infolist()) > MAX_TOTAL or any(i.file_size > MAX_PART for i in z.infolist()):
        raise ImportError_("展開すると大きすぎる Excel ファイルは読まない（1 部品 %d MB・合計 %d MB まで）"
                           % (MAX_PART // 1_000_000, MAX_TOTAL // 1_000_000))      # declared sizes: refuse early

    def read(name):
        try:
            with z.open(name) as fh:
                data = fh.read(MAX_PART + 1)
        except KeyError:
            raise ImportError_("Excel（.xlsx）の部品 %s が無い" % name) from None
        except (zipfile.BadZipFile, OSError, EOFError) as e:
            raise ImportError_("Excel ファイルが壊れている（%s）" % e) from None
        if len(data) > MAX_PART or len(data) > budget["left"]:
            raise ImportError_("展開すると大きすぎる Excel ファイルは読まない（1 部品 %d MB・合計 %d MB まで）"
                               % (MAX_PART // 1_000_000, MAX_TOTAL // 1_000_000))
        budget["left"] -= len(data)
        return data

    def events(name, small=False, raw=None):
        raw = read(name) if raw is None else raw
        if small and len(raw) > 2_000_000:
            raise ImportError_("Excel の部品 %s が大きすぎる" % name)
        try:
            yield from ET.iterparse(io.BytesIO(raw), events=("start", "end"))
        except ET.ParseError as e:
            raise ImportError_("Excel の部品 %s を読めない（%s）" % (name, e)) from None

    def small_xml(name):
        raw = read(name)
        if len(raw) > 2_000_000:
            raise ImportError_("Excel の部品 %s が大きすぎる" % name)
        try:
            return ET.fromstring(raw)
        except ET.ParseError as e:
            raise ImportError_("Excel の部品 %s を読めない（%s）" % (name, e)) from None

    wb = small_xml("xl/workbook.xml")
    rels = small_xml("xl/_rels/workbook.xml.rels")
    main = wb.tag[1:].split("}")[0] if wb.tag.startswith("{") else NS["m"]
    if main != NS["m"] and main not in STRICT:
        raise ImportError_("Excel のブックの形式（名前空間 %s）を読めない" % main[:80])
    ns = {"m": main}
    rel_ns = STRICT.get(main, REL_NS)
    M = "{%s}" % main
    shared = []
    if "xl/sharedStrings.xml" in names:
        root = None
        for ev, el in events("xl/sharedStrings.xml"):
            if root is None:
                root = el
            if ev == "end" and el.tag == M + "si":
                text = _plain_text(el, M)
                if len(text) > MAX_STRING:
                    raise ImportError_("共有の文字列が長すぎる（1 つ %d 文字まで：Excel の上限）" % MAX_STRING)
                shared.append(text)
                if len(shared) > MAX_SHARED:
                    raise ImportError_("共有の文字列が多すぎる（%d まで）" % MAX_SHARED)
                el.clear()
                root.clear()
    rel_target = {r.get("Id"): r.get("Target") for r in rels}
    out, hidden_sheets, fcells, sheet_names, cut_sheets = [], [], {}, {}, []
    cells = {"n": 0, "chars": 0, "rows": 0, "fchars": 0, "arrays": 0, "hn": 0, "hfchars": 0}
    sheets_el = wb.find("m:sheets", ns)
    order = [str(sh.get("name")) for sh in (sheets_el if sheets_el is not None else [])]
    # defined names with their scope: NAME -> {sheet casefolded (a sheet's own name) or None (the workbook's): text}
    defined, nchars, names_cut = {}, 0, False
    dn = wb.find("m:definedNames", ns)
    for d in (dn if dn is not None else []):
        nm, txt = d.get("name"), d.text
        if not nm or not txt:
            continue
        nchars += len(nm) + len(txt)
        if nchars > MAX_NAME_CHARS:
            names_cut = True
            break
        scope = None
        if d.get("localSheetId") is not None:
            try:
                scope = order[int(d.get("localSheetId"))].casefold()
            except (ValueError, IndexError):
                continue                                   # a name of no sheet: left undefined (refused when used)
        defined.setdefault(nm.upper(), {})[scope] = txt[:MAX_FORMULA + 1]
    tables = {}

    def read_tables(path, shf):
        rp = path.rsplit("/", 1)
        rels_path = "%s/_rels/%s.rels" % (rp[0], rp[1]) if len(rp) == 2 else ""
        if rels_path not in names:
            return
        for r in small_xml(rels_path):
            if not str(r.get("Type") or "").endswith("/table"):
                continue
            tgt = str(r.get("Target") or "")
            parts = (rp[0] + "/" + tgt).split("/") if not tgt.startswith("/") else tgt.lstrip("/").split("/")
            norm = []
            for p in parts:
                if p == "..":
                    if norm:
                        norm.pop()
                elif p and p != ".":
                    norm.append(p)
            tpath = "/".join(norm)
            if tpath not in names:
                continue
            if len(tables) >= MAX_TABLES:
                raise ImportError_("表（テーブル）が多すぎる（%d まで）" % MAX_TABLES)
            t = small_xml(tpath)
            blk = _ref_block(t.get("ref"))
            if blk is None:
                continue
            try:
                hdr = int(t.get("headerRowCount", "1"))
                tot = int(t.get("totalsRowCount", "0"))
            except ValueError:
                continue
            cols = [str(c.get("name") or "").strip().casefold() for c in t.iter() if c.tag.endswith("}tableColumn")]
            info = {"name": str(t.get("displayName") or t.get("name") or ""), "sheet": shf, "c1": blk[0], "c2": blk[1],
                    "r1": blk[2], "r2": blk[3], "hdr": hdr, "tot": tot, "cols": cols[:blk[1] - blk[0] + 1]}
            for key in {str(t.get("displayName") or ""), str(t.get("name") or "")}:
                if key:
                    tables[key.upper()] = info

    for sh in (sheets_el if sheets_el is not None else []):
        rid = sh.get("{%s}id" % rel_ns)
        target = rel_target.get(rid, "") or ""
        path = "xl/" + target.lstrip("/").replace("xl/", "") if not target.startswith("/xl/") else target.lstrip("/")
        if path not in names:
            continue
        shname = str(sh.get("name"))
        shf = shname.casefold()
        sheet_names[shf] = shname
        sheet_hidden = skip_hidden and sh.get("state") in ("hidden", "veryHidden")
        if sheet_hidden:
            hidden_sheets.append(sh.get("name"))
        if skip_hidden:
            read_tables(path, shf)
        rows, numbers, forms = [], [], []
        allf = fcells.setdefault(shf, {})
        hidden_rows = 0
        hidden_cols = bytearray(MAX_COLS)               # 1 = hidden; set by slices (no per-column loop in Python)
        shared_f = {}                                   # si -> formula text of a shared formula's master cell
        arrays, starts, expiry = [], [], []             # array formulas whose range still lies ahead (sorted by column; a heap of last rows)
        root = None
        last_row = 0
        cut = False
        raw = read(path)
        if sheet_hidden and not _HAS_FORMULA.search(raw):
            continue                                    # a hidden sheet of values only (a master): nothing to follow
        for ev, el in events(path, raw=raw):
            if root is None:
                root = el
            if ev == "end" and el.tag == M + "cols":
                col_els = el.findall("m:col", ns)
                if len(col_els) > MAX_COL_ELEMENTS:
                    raise ImportError_("列の設定が多すぎる（1 シート %d 個まで）" % MAX_COL_ELEMENTS)
                for c_ in (col_els if skip_hidden else []):
                    if c_.get("hidden") in ("1", "true"):
                        try:
                            lo_, hi_ = max(int(c_.get("min")), 1) - 1, min(int(c_.get("max")), MAX_COLS)
                        except (TypeError, ValueError):
                            continue
                        if lo_ < hi_:
                            hidden_cols[lo_:hi_] = b"\x01" * (hi_ - lo_)
                el.clear()
                continue
            if ev != "end" or el.tag != M + "row":
                continue
            if not sheet_hidden:
                cells["rows"] += 1
                if cells["rows"] > MAX_ROWS:
                    raise ImportError_("行が多すぎる（%d 行まで）" % MAX_ROWS)
            rattr = el.get("r")
            try:
                rn = int(rattr) if rattr is not None else last_row + 1
            except ValueError:
                raise ImportError_("行の番号 %r を読めない" % rattr) from None
            if not (last_row < rn <= MAX_ROW_NUMBER):
                raise ImportError_("行の番号 %r が正しくない（増える順で Excel の上限 %d まで）" % (rattr, MAX_ROW_NUMBER))
            last_row = rn
            while expiry and expiry[0][0] < rn:          # array formulas whose range ended above this row
                _r2, c1_, uid = heapq.heappop(expiry)
                k = bisect.bisect_left(starts, c1_)
                while k < len(arrays) and starts[k] == c1_ and arrays[k][4] != uid:
                    k += 1
                if k < len(arrays) and arrays[k][4] == uid:
                    del arrays[k], starts[k]
            row_hidden = sheet_hidden or (skip_hidden and el.get("hidden") in ("1", "true"))
            if row_hidden and not sheet_hidden:
                hidden_rows += 1
            vals, fs = {}, {}
            last = -1
            n_el = 0
            for c in el.findall("m:c", ns):
                n_el += 1
                ref, t = c.get("r"), c.get("t")
                ci = _col_index(ref) if ref else last + 1     # a cell without a reference follows the previous one
                last = ci                                     # (every element is counted, repeated or not)
                if ci >= MAX_COLS:
                    raise ImportError_("列の位置 %s が Excel の上限を超えている" % ref)
                v = c.find("m:v", ns)
                f = c.find("m:f", ns)
                fobj = None
                if f is not None:
                    text = f.text or ""
                    if len(text) > MAX_FORMULA:
                        text = text[:MAX_FORMULA + 1]        # kept only to say "too long" (formula_reason)
                    dcol, no_master, drow = 0, False, 0
                    si = f.get("si")
                    ft = f.get("t")
                    if text and sheet_hidden:
                        cells["hfchars"] += len(text)         # a hidden sheet's formulas: its own budget
                        if cells["hfchars"] > MAX_HIDDEN_FORMULA_CHARS:
                            cut = True
                            break
                    elif text:
                        cells["fchars"] += len(text)          # each distinct formula text is scanned once
                        if formula_budget is not None and cells["fchars"] > formula_budget:
                            raise ImportError_("数式の文字が多すぎる（合計 %d 文字まで）" % formula_budget)
                    if ft == "shared" and si is not None:
                        if text:
                            shared_f[si] = (text, ci, rn)     # the master cell: its text, column and row
                        elif si in shared_f:
                            text, mcol, mrow = shared_f[si]
                            dcol = ci - mcol                  # relative columns / rows of the copy move by this much
                            drow = rn - mrow
                        else:
                            no_master = True
                    elif ft in ("array", "dataTable"):
                        if ft == "dataTable":
                            text = DATATABLE
                        blk = _ref_block(f.get("ref") or ref or "")
                        if blk and (blk[1] > blk[0] or blk[3] > blk[2]):
                            cells["arrays"] += 1
                            if cells["arrays"] > MAX_ARRAYS:
                                raise ImportError_("配列数式が多すぎる（%d まで）" % MAX_ARRAYS)
                            k = bisect.bisect_left(starts, blk[0])
                            arrays.insert(k, (blk[0], blk[1], blk[3], text, cells["arrays"]))
                            starts.insert(k, blk[0])
                            heapq.heappush(expiry, (blk[3], blk[0], cells["arrays"]))
                    fobj = (text, dcol, no_master, drow)
                elif arrays:
                    k = bisect.bisect_right(starts, ci) - 1   # a cell of an array's range: the array's formula
                    if k >= 0 and arrays[k][1] >= ci and arrays[k][2] >= rn:
                        fobj = (arrays[k][3], 0, False, 0)
                if fobj is not None:
                    fs[ci] = fobj
                    cells["chars"] += len(fobj[0])
                if row_hidden or hidden_cols[ci]:
                    continue                          # a hidden row / column (often an old revision): value not read
                if t == "s" and v is not None:
                    try:
                        val = shared[int(v.text)]
                    except (ValueError, TypeError, IndexError):
                        raise ImportError_("共有の文字列の番号 %r が正しくない" % (v.text,)) from None
                elif t == "inlineStr":
                    is_ = c.find(M + "is")
                    val = _plain_text(is_, M) if is_ is not None else ""
                    if len(val) > MAX_STRING:
                        raise ImportError_("セルの文字列が長すぎる（%d 文字まで）" % MAX_STRING)
                elif t == "b":
                    val = "TRUE" if (v is not None and v.text == "1") else "FALSE"   # a boolean is not a quantity
                elif t == "e":
                    val = "#ERROR " + ((v.text or "") if v is not None else "")    # an error value is not a quantity
                else:
                    val = v.text if v is not None else None   # formulas: the cached value only, never evaluated
                vals[ci] = val
                cells["chars"] += len(val) if isinstance(val, str) else 0
            if cut:
                el.clear()
                root.clear()
                break
            if cells["chars"] > MAX_CHARS:
                raise ImportError_("セルの文字が多すぎる（合計 %d 文字まで）" % MAX_CHARS)
            # every <c> element counts (hidden rows and columns too), and a row costs at least its width: a sheet of
            # empty or repeated cells cannot run unbounded. A hidden sheet counts against its own budget
            if sheet_hidden:
                cells["hn"] += max(n_el, 1)
                if cells["hn"] > MAX_HIDDEN_CELLS:
                    cut = True
                    el.clear()
                    root.clear()
                    break
            else:
                cells["n"] += max(n_el, max(vals) + 1 if vals else 0, 1)
                if cells["n"] > MAX_CELLS:
                    raise ImportError_("セルが多すぎる（%d まで）" % MAX_CELLS)
            if fs:
                allf[rn] = fs
            if vals:
                rows.append([vals.get(j) for j in range(max(vals) + 1)])
                numbers.append(rn)
                forms.append({j: x for j, x in fs.items() if j in vals})
            el.clear()
            root.clear()
        if cut:
            cut_sheets.append(shf)
        if not sheet_hidden:
            out.append({"name": sh.get("name"), "rows": rows, "numbers": numbers, "formulas": forms,
                        "hidden_rows": hidden_rows, "hidden_cols": hidden_cols.count(1)})
    return {"sheets": out, "hidden_sheets": hidden_sheets, "names": defined, "names_cut": names_cut, "tables": tables,
            "fcells": fcells, "sheet_names": sheet_names, "cut_sheets": cut_sheets}


def read_xlsx(data: bytes, doc_id: str) -> dict:
    wbk = xlsx_workbook(data)
    qsheets = [sh["name"] for sh in wbk["sheets"] if _find_header(sh["rows"])[0] is not None]
    fctx = {"qsheets": qsheets, "names": wbk["names"], "tables": wbk["tables"]}
    warnings = []
    if not wbk["sheets"] and not wbk["hidden_sheets"]:
        warnings.append("シートを読めなかった（シートが無いか、形式が違う）")
    if wbk["hidden_sheets"]:
        warnings.append("非表示のシート（%s）の値は読んでいない（古い版を隠して残していることがある。必要なら表示してから読み込む）。"
                        "その数式はたどって、写しを見分けるのに使う" % "、".join(sheet_label(x) for x in wbk["hidden_sheets"][:10]))
    if wbk.get("cut_sheets"):
        warnings.append("非表示のシート（%s）が大きすぎるので、途中から読んでいない（セル %d 個・数式 %d 文字まで）。"
                        "そのシートを参照する数量は確かめられないので足さない"
                        % ("、".join(sheet_label(wbk["sheet_names"].get(x, x)) for x in wbk["cut_sheets"][:10]), MAX_HIDDEN_CELLS,
                           MAX_HIDDEN_FORMULA_CHARS))
    if wbk.get("names_cut"):
        warnings.append("名前の定義が多すぎるので、途中から読んでいない（%d 文字まで）。読んでいない名前を使う数量は足さない"
                        % MAX_NAME_CHARS)
    for sh in wbk["sheets"]:
        if sh["hidden_rows"]:
            warnings.append("%s：非表示の行 %d 行は読んでいない" % (sheet_label(sh["name"]), sh["hidden_rows"]))
        if sh.get("hidden_cols"):
            warnings.append("%s：非表示の列 %d 列は読んでいない（古い数量の列のことがある）" % (sheet_label(sh["name"]), sh["hidden_cols"]))
    if len(qsheets) > 1:
        warnings.append("数量の表が %d シートある（%s）：同じ材料が別のシートにも載っていないか確かめる"
                        % (len(qsheets), "、".join(sheet_label(x) for x in qsheets[:6])))
    return {"format": "xlsx", "warnings": warnings, "names": wbk["names"], "tables": wbk["tables"], "cells": wbk["fcells"],
            "sheet_names": wbk["sheet_names"], "cut_sheets": wbk.get("cut_sheets", []),
            "sheets": [_rows_to_candidates(sh["rows"], sh["name"], doc_id, sh["numbers"], sh["formulas"], fctx)
                       for sh in wbk["sheets"]]}
