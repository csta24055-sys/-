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
    "specification": ("規格", "仕様", "spec", "specification", "grade"),
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


def _num(s):
    """A quantity cell: the same rule as the screen (a comma only as a thousands separator, no inner spaces)."""
    return number_or_reason(s)[0]


def _header_map(row: list) -> dict:
    """The column of each key: the column whose header matches the most preferred word ("Item description" is the name
    before "Item"); an exact match only breaks a tie of the same word; money columns (材料費, Amount …) are never the name
    or the quantity; a column is used for one key only."""
    out, used = {}, set()
    heads = [str(h or "")[:MAX_TEXT].strip().lower() for h in row]
    for key, words in HEADERS.items():
        best = None
        for j, hs in enumerate(heads):
            if j in used or not hs:
                continue
            if key in ("name", "quantity") and any(m in hs for m in MONEY_WORDS):
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
_FTOK = re.compile(r'"(?:[^"]|"")*"|\'(?:[^\']|\'\')*\'|[\w.$\\]+|.', re.S)
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
        if tok[0].isalnum() or tok[0] in "_.$\\":
            if nxt == "!":
                sheet = tok
                continue
            if nxt == "(":
                toks.append(("func", re.sub(r"^_XL(FN|WS)\.", "", tok.upper()), None))
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
                seq.append(("name", None))
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
            seq.append(("name", None))
        elif kind == "name":
            names.append((val, sh))
            seq.append(("name", None))
        elif kind == "func":
            funcs.add(val)
            seq.append(("func", val))
        elif kind == "op":
            seq.append(("op", val))
        else:
            seq.append(("val", None))                               # a number, a string, a lone row number
        k += 1
    return frozenset(funcs), tuple(refs), tuple(names), structured, three_d, computed, tuple(nranges), _additive(seq)


# functions whose value is (one of) their arguments added up or rounded: a cell in such a place is part of the value
_ADD_ALL = frozenset(("SUM", "MAX", "MIN", "SUBTOTAL", "AGGREGATE"))
_ADD_FIRST = frozenset(("ROUND", "ROUNDUP", "ROUNDDOWN", "TRUNC", "INT", "ABS", "N", "VALUE", "CEILING", "FLOOR", "MROUND",
                        "CEILING.MATH", "FLOOR.MATH", "ODD", "EVEN"))
_ADD_BRANCH = {"IF": (1, 2), "IFERROR": (0, 1), "IFNA": (0, 1), "CHOOSE": None}


def _additive(seq: list) -> frozenset:
    """The references (indices) of a formula that are ADDED into its value: alone or in a sum, rounded, chosen by IF,
    scaled by a number (C2*1.05); not those that only multiply another reference (長さ×$G$2: G2 is a factor), that sit
    inside a lookup or a condition (VLOOKUP, SUMIF, the test of IF), or are raised to a power. A recursive descent over
    the token sequence; anything it does not understand adds nothing (the reference is then simply not "added")."""
    pos = [0]
    n = len(seq)

    def peek():
        return seq[pos[0]] if pos[0] < n else ("end", None)

    def take():
        t = peek()
        pos[0] += 1
        return t

    def args():
        out, cur = [], []
        depth = 0
        while pos[0] < n:
            t = peek()
            if t == ("op", "("):
                depth += 1
            elif t == ("op", ")"):
                if depth == 0:
                    take()
                    break
                depth -= 1
            if t == ("op", ",") and depth == 0:
                take()
                out.append(cur)
                cur = []
                continue
            cur.append(take())
        out.append(cur)
        return out

    def primary():
        t = take()
        if t[0] == "ref":
            return {t[1]}, {t[1]}
        if t[0] == "func":
            if peek() == ("op", "("):
                take()
            parts = args()
            res = [_additive_seq(a) for a in parts]
            alls = set().union(*(r[0] for r in res)) if res else set()
            f = t[1]
            if f in _ADD_ALL:
                return alls, set().union(*(r[1] for r in res)) if res else set()
            if f in _ADD_FIRST:
                return alls, (res[0][1] if res else set())
            if f in _ADD_BRANCH:
                idx = _ADD_BRANCH[f]
                pick = range(1, len(res)) if idx is None else [i for i in idx if i < len(res)]
                return alls, set().union(*(res[i][1] for i in pick)) if pick else set()
            return alls, set()
        if t == ("op", "("):
            parts = args()
            res = [_additive_seq(a) for a in parts]
            if len(res) == 1:
                return res[0]
            return set().union(*(r[0] for r in res)), set()
        return set(), set()

    def factor():
        while peek() in (("op", "-"), ("op", "+")):
            take()
        a, d = primary()
        while peek() in (("op", "^"),):
            take()
            b, _ = primary()
            a, d = a | b, set()
        while peek() == ("op", "%"):
            take()
        return a, d

    def term():
        fs = [(None, factor())]
        while peek() in (("op", "*"), ("op", "/")):
            op = take()[1]
            fs.append((op, factor()))
        if len(fs) == 1:
            return fs[0][1]
        alls = set().union(*(f[1][0] for f in fs))
        with_refs = [i for i, f in enumerate(fs) if f[1][0]]
        if len(with_refs) == 1 and fs[with_refs[0]][0] != "/":
            return alls, fs[with_refs[0]][1][1]                  # one reference scaled by numbers
        return alls, set()

    def expr():
        a, d = term()
        while True:
            t = peek()
            if t in (("op", "+"), ("op", "-")):
                take()
                b, e = term()
                a, d = a | b, d | e
            elif t[0] == "op" and t[1] in ("=", "<", ">", "&"):
                take()
                b, _ = term()
                a, d = a | b, set()
            else:
                return a, d

    a, d = expr()
    return frozenset(d) if pos[0] >= n else frozenset()


def _additive_seq(tokens: list) -> tuple:
    """(every reference, the added references) of a part of a formula (an argument)."""
    alls = {t[1] for t in tokens if t[0] == "ref"}
    return alls, set(_additive(tokens))


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


def _lone_block(tok, ctx, seen):
    """(why, sheet or None, c1, c2, r1, r2) of one end of a name range (a defined name that is one block, or a cell)."""
    kind, val, sh = tok
    if kind == "ref":
        return None, (None if sh is None else sh.casefold()), val[1], val[1], val[3], val[3]
    nm = val if kind == "name" else val[2]
    this = (ctx.get("sheet") or "").casefold()
    target = name_target(ctx.get("names") or {}, nm, sh.casefold() if sh else this)
    if not target:
        return "名前 %s の参照先が分からない。必要なら手で入れる" % nm[:40], None
    why, blocks = formula_refs((target.lstrip("="), 0, False, 0), ctx, seen)
    if why or len(blocks) != 1:
        return why or "名前の範囲（%s）の端を確かめられない。必要なら手で入れる" % nm[:40], None
    return None, blocks[0]


def formula_refs(formula, ctx: dict | None = None, _seen: set | None = None) -> tuple:
    """(why what the formula reaches cannot be checked, or None; the cells it reaches) for one cell's formula.
    Each reached block is (sheet casefolded, or None for this sheet; first column; last column; first row; last row),
    None rows meaning every row; shared-formula copies are moved by their column / row shift; a defined name is followed
    to what it refers to (the sheet's own name first, then the workbook's; each name once, at most MAX_NAME_FOLLOWS);
    a table reference becomes the table's rows and columns; a range between two names is the block between their ends.
    Cannot be checked (the quantity is then not added): a shared-formula copy without its master, a formula longer than
    Excel allows, INDIRECT / OFFSET (the reference is computed), a range whose end is computed, a name or a table that
    the workbook does not define, a data table, references over several sheets, other workbooks.
    Whether a reached cell is another material row is judged by the importer. `formula` is (text, column shift, master
    missing?, row shift) or plain text; `ctx` has "sheet" (this sheet's name), "names" (defined names), "tables",
    and "row" / "col" of the cell (for [@列])."""
    if not formula:
        return None, []
    text, dcol, no_master, drow = _formula_tuple(formula)
    ctx = ctx or {}
    seen = set() if _seen is None else _seen
    if no_master:
        return "数式の中身が分からない（共有の数式の元が無い）。必要なら手で入れる", []
    if text == DATATABLE:
        return "データテーブル（What-If 分析）の値は確かめられない。必要なら手で入れる", []
    if len(text) > MAX_FORMULA:
        return "数式が長すぎて確かめられない（%d 文字まで）" % MAX_FORMULA, []
    funcs, refs, names, structured, three_d, computed, nranges, _add = _formula_parts(text)
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
    this = (ctx.get("sheet") or "").casefold()
    out = []
    for sh, a1, c1, a2, c2, ar1, r1, ar2, r2 in refs:
        if sh is not None and sh.startswith("["):
            return "別のブックを参照した数量は確かめられない。必要なら手で入れる", []
        lo, hi = (c1 if a1 else c1 + dcol), (c2 if a2 else c2 + dcol)
        rlo = None if r1 is None else (r1 if ar1 else r1 + drow)
        rhi = None if r2 is None else (r2 if ar2 else r2 + drow)
        if lo > hi:
            lo, hi = hi, lo
        if rlo is not None and rhi is not None and rlo > rhi:
            rlo, rhi = rhi, rlo
        shf = None if sh is None or sh.casefold() == this else sh.casefold()
        out.append((shf, lo, hi, rlo, rhi))
    for table, inner in structured:
        why, blk = _structured_block(table, inner, ctx)
        if why:
            return why, []
        if blk:
            out.append(blk)
    for left, right in nranges:
        w1, b1 = _lone_block(left, ctx, seen)
        w2, b2 = _lone_block(right, ctx, seen) if not w1 else (None, None)
        if w1 or w2:
            return w1 or w2, []
        s1 = b1[0] or this
        s2 = b2[0] or this
        if s1 != s2 or None in (b1[3], b1[4], b2[3], b2[4]):
            return "名前の範囲（%s）の端を確かめられない。必要なら手で入れる" % "：".join(str(x[1])[:20] for x in (left, right)), []
        out.append((None if s1 == this else s1, min(b1[1], b2[1]), max(b1[2], b2[2]), min(b1[3], b2[3]), max(b1[4], b2[4])))
    defined = ctx.get("names") or {}
    params = set()
    if funcs & {"LET", "LAMBDA"}:
        # LET(x, …, expr) / LAMBDA(x, …, body): the parameters are not workbook names (Excel stores them as _xlpm.x)
        params = {m.group(1).upper() for m in re.finditer(r"(?:\(|,)\s*([^\W\d][\w.]*)\s*(?=,)", text)}
    for nm, sh in names:
        if nm.startswith(("_XLPM.", "__SR")) or nm in params or nm in ("TRUE", "FALSE"):
            continue
        scope = sh.casefold() if sh else this
        key = (scope, nm)
        target = name_target(defined, nm, scope)
        if not target:
            T = (ctx.get("tables") or {}).get(nm)
            if T is not None:                              # a table's name alone: its data rows
                why, blk = _structured_block(nm, "", ctx)
                if why:
                    return why, []
                if blk:
                    out.append(blk)
                continue
            return "名前 %s の参照先が分からない（ブックに定義が無い）。必要なら手で入れる" % nm[:40], []
        if key in seen:
            continue
        if len(seen) >= MAX_NAME_FOLLOWS:
            return "名前の参照が多すぎて確かめられない（%d 個まで）。必要なら手で入れる" % MAX_NAME_FOLLOWS, []
        seen.add(key)
        why, more = formula_refs((target.lstrip("="), 0, False, 0), dict(ctx, sheet=sh or ctx.get("sheet")), seen)
        if why:
            return why + "（名前 %s の参照先）" % nm, []
        if sh and sh.casefold() != this:                   # blocks of a name used as 集計!QTY: on that name's sheet
            more = [(b[0] if b[0] is not None else sh.casefold(),) + tuple(b[1:]) for b in more]
        out += more
    return None, out


def added_blocks(formula) -> list:
    """The blocks (sheet casefolded or None, c1, c2, r1, r2) that a formula ADDS into its value (see _additive), moved
    by a shared formula's shift; [] when it cannot be read."""
    if not formula:
        return []
    text, dcol, no_master, drow = _formula_tuple(formula)
    if no_master or text == DATATABLE or len(text) > MAX_FORMULA:
        return []
    parts = _formula_parts(text)
    out = []
    for i in sorted(parts[7]):
        sh, a1, c1, a2, c2, ar1, r1, ar2, r2 = parts[1][i]
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
        hs = str(h or "")[:MAX_TEXT].strip().lower()
        if hs and any(w in hs for w in QTY_LIKE) and not any(m in hs for m in MONEY_WORDS + NOT_QTY):
            out.append(j)
    return out


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
        trace = "%s:%s!R%dC%d" % (doc_id, sheet, rn, (hmap["quantity"] or 0) + 1)
        texts = {"name": name, "unit": text("unit"), "division": text("division"), "specification": text("specification")}
        if q is None:
            why = number_or_reason(col("quantity"))[1]
            skipped.append(dict(texts, row=rn, trace=trace,
                                reason="数量が数値でない（0 として読まない）" + ("：" + why if why else "")))
            continue
        fobj = (formulas[i] if formulas else {}).get(hmap["quantity"])
        why = formula_reason(fobj, hmap["quantity"], dict(fctx or {}, sheet=sheet, row=rn, col=hmap["quantity"]))
        if why:
            skipped.append(dict(texts, row=rn, trace=trace, reason=why))
            continue
        cands.append(dict(texts, quantity=q, trace=trace, row=rn, qf=fobj))
    return {"sheet": sheet, "rows": cands, "skipped": skipped, "qcol": hmap["quantity"],
            "qcols": sorted(set(_qty_cols(rows[hdr_i])) | {hmap["quantity"]}),
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

    def events(name, small=False):
        raw = read(name)
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
    out, hidden_sheets, fcells, sheet_names = [], [], {}, {}
    cells = {"n": 0, "chars": 0, "rows": 0, "fchars": 0, "arrays": 0}
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
        for ev, el in events(path):
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
                    if text:
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
            if cells["chars"] > MAX_CHARS:
                raise ImportError_("セルの文字が多すぎる（合計 %d 文字まで）" % MAX_CHARS)
            # every <c> element counts (hidden ones too), and a row costs at least its width: a sheet of empty or
            # repeated cells cannot run unbounded
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
        if not sheet_hidden:
            out.append({"name": sh.get("name"), "rows": rows, "numbers": numbers, "formulas": forms,
                        "hidden_rows": hidden_rows, "hidden_cols": hidden_cols.count(1)})
    return {"sheets": out, "hidden_sheets": hidden_sheets, "names": defined, "names_cut": names_cut, "tables": tables,
            "fcells": fcells, "sheet_names": sheet_names}


def read_xlsx(data: bytes, doc_id: str) -> dict:
    wbk = xlsx_workbook(data)
    qsheets = [sh["name"] for sh in wbk["sheets"] if _find_header(sh["rows"])[0] is not None]
    fctx = {"qsheets": qsheets, "names": wbk["names"], "tables": wbk["tables"]}
    warnings = []
    if not wbk["sheets"] and not wbk["hidden_sheets"]:
        warnings.append("シートを読めなかった（シートが無いか、形式が違う）")
    if wbk["hidden_sheets"]:
        warnings.append("非表示のシート（%s）の値は読んでいない（古い版を隠して残していることがある。必要なら表示してから読み込む）。"
                        "その数式はたどって、写しを見分けるのに使う" % "、".join(str(x) for x in wbk["hidden_sheets"][:10]))
    if wbk.get("names_cut"):
        warnings.append("名前の定義が多すぎるので、途中から読んでいない（%d 文字まで）。読んでいない名前を使う数量は足さない"
                        % MAX_NAME_CHARS)
    for sh in wbk["sheets"]:
        if sh["hidden_rows"]:
            warnings.append("%s：非表示の行 %d 行は読んでいない" % (sh["name"], sh["hidden_rows"]))
        if sh.get("hidden_cols"):
            warnings.append("%s：非表示の列 %d 列は読んでいない（古い数量の列のことがある）" % (sh["name"], sh["hidden_cols"]))
    if len(qsheets) > 1:
        warnings.append("数量の表が %d シートある（%s）：同じ材料が別のシートにも載っていないか確かめる"
                        % (len(qsheets), "、".join(qsheets[:6])))
    return {"format": "xlsx", "warnings": warnings, "names": wbk["names"], "tables": wbk["tables"], "cells": wbk["fcells"],
            "sheet_names": wbk["sheet_names"],
            "sheets": [_rows_to_candidates(sh["rows"], sh["name"], doc_id, sh["numbers"], sh["formulas"], fctx)
                       for sh in wbk["sheets"]]}
