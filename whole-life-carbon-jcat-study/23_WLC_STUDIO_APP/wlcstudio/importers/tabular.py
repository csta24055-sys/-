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
    "unit": ("単位", "unit", "uom", "units", "u/m", "u.o.m"),
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


# a camelCase boundary: a lower-case letter, then an upper-case letter that starts a word (MaterialCost, TotalVolume);
# UoM, NetQTY, U/M are not split by it (14 回目: round 13 split every lower→upper change and made UoM "uo m")
_CAMEL = re.compile(r"(?<=[a-z])(?=[A-Z][a-z])")
_CAMEL_ANY = re.compile(r"(?<=[a-z])(?=[A-Z])")    # round 13's split (NetQTY → net qty): also tried, never alone
# spaces between two kanji / kana (名　称, 数 量, 単　位: the usual 内訳書 spaces its two-letter headers out)
_CJK = "\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"
_CJK_SPACE = re.compile("(?<=[%s])[ \u3000]+(?=[%s])" % (_CJK, _CJK))


MAX_HEADER_CELLS = 1_024                          # non-empty cells of a row looked at for the header (15 回目)
MAX_HEADER_WORK = 100_000                         # header cells looked at per document, all sheets (15 回目の攻撃)


class HeaderWork:
    """The header search of one document: what is known of each distinct header text, worked out once per document
    (its forms in `heads`; how well it names each key in `scores`, worked out only for the cells the header map looks
    at, `scored` times), how many cells were looked at and how many searches were made. 15 回目: the forms were kept in a
    global cache of 4,096 texts, which a wide sheet of distinct texts thrashed, and every sheet's header was searched
    twice over all its 16,384 columns (a 2–4 MB upload held the worker 30–45 s). 15 回目の攻撃: the columns of the
    quantity / size / factor headers still looked at the whole header row and worked out the scores they do not use, and
    nothing bounded the cells of all sheets together (see MAX_HEADER_WORK)."""
    __slots__ = ("heads", "scores", "cells", "searches", "scored")

    def __init__(self):
        self.heads, self.scores, self.cells, self.searches, self.scored = {}, {}, 0, 0, 0


def _forms(s: str) -> tuple:
    """The lowered forms of one header text that are matched: split before an upper-case letter that starts a word,
    unsplit, and split at every lower→upper change; and, when spaces stand between kanji or kana, the text without
    those spaces (名　称 is 名称, 14 回目の攻撃). A word is found when it is found in any form. The split and joined
    forms are worked out only when the text has a lower→upper change or spaces between kanji (otherwise every form is
    the plain one; 15 回目)."""
    camel = _CAMEL_ANY.search(s) is not None          # (every _CAMEL boundary is a _CAMEL_ANY boundary)
    if not camel and _CJK_SPACE.search(s) is None:
        return (s.lower(),)
    out = []
    for v in ((_CAMEL.sub(" ", s), s, _CAMEL_ANY.sub(" ", s)) if camel else (s,)) + (_CJK_SPACE.sub("", s),):
        v = v.lower()
        if v not in out:
            out.append(v)
    return tuple(out)


def _text_forms(s: str, work: HeaderWork | None) -> tuple:
    """The forms of a stripped, non-empty header text, worked out once per document (see _forms)."""
    got = work.heads.get(s) if work is not None else None
    if got is None:
        got = _forms(s)
        if work is not None:
            work.heads[s] = got
    return got


def _text_scores(s: str, work: HeaderWork | None):
    """How well a stripped, non-empty header text names each key (see _key_scores), worked out once per document and
    only when asked (the header map; 15 回目の攻撃: the quantity / size / factor columns, which need the forms only,
    worked them out for every cell of a 16,384-column header row)."""
    if work is None:
        return _key_scores(_forms(s))
    if s in work.scores:
        return work.scores[s]
    work.scored += 1
    got = work.scores[s] = _key_scores(_text_forms(s, work))
    return got


def _head_forms(h, work: HeaderWork | None = None) -> tuple:
    """A header cell as matched: cut, stripped, in each of its forms (see _forms); () for an empty cell."""
    s = str(h if h is not None else "")[:MAX_TEXT].strip()
    return _text_forms(s, work) if s else ()


def _head_cells(row: list, work: HeaderWork | None = None) -> list:
    """(column, stripped text) of the first MAX_HEADER_CELLS non-empty cells of a row: the only cells of a row that are
    read as a header (15 回目; 15 回目の攻撃: also for the quantity / size / factor columns). Counted in work.cells."""
    out = []
    for j, h in enumerate(row):
        if h is None:
            continue
        t = str(h)[:MAX_TEXT].strip()
        if not t:
            continue
        out.append((j, t))
        if len(out) >= MAX_HEADER_CELLS:
            break
    if work is not None:
        work.cells += len(out)
    return out


def _head_text(h) -> str:
    """A header cell as shown in a match: cut, stripped, split before an upper-case letter that starts a word
    (MaterialCost, UnitPrice, TotalVolume are "material cost", "unit price", "total volume"), lowered."""
    f = _head_forms(h)
    return f[0] if f else ""


def _forms_have(forms: tuple, words: tuple) -> bool:
    return any(_has_word(v, words) for v in forms)


# a money word that ends one ASCII run of a header whose start is a cost word (MATERIALRATE, Materialcost, LABOURCOST,
# UNITPRICE, TOTALAMOUNT, ALLINRATE): money for the name, quantity and unit keys. Only listed starts are read, so that
# real words that end in the same letters (Substrate, Separate, Corporate, Accurate, Paramount, Devalue) are not
# money (14 回目)
_MONEY_EN = ("cost", "price", "rate", "amount", "value")
_MONEY_STARTS = frozenset((
    "material", "materials", "matl", "mat", "labour", "labor", "lab", "plant", "equipment", "equip", "unit", "total",
    "net", "nett", "gross", "sub", "subcon", "subcontract", "item", "line", "base", "supply", "fix", "fixing", "install",
    "installation", "extended", "ext", "all", "in", "composite", "contract", "tender", "budget", "est", "estimated",
    "actual", "final", "bill", "boq", "day", "daily", "hour", "hourly"))
_ASCII_RUN = re.compile(r"[a-z]+")


@functools.lru_cache(maxsize=4096)
def _cost_start(p: str) -> bool:
    """Is p one or more of the listed cost-word starts written together (material, totalmaterial, allin …)?"""
    if not p or len(p) > 40:
        return False
    ok = [True] + [False] * len(p)
    for i in range(1, len(p) + 1):
        ok[i] = any(ok[i - len(w)] and p[i - len(w):i] == w for w in _MONEY_STARTS if len(w) <= i)
    return ok[len(p)]


def _joined_money(forms: tuple) -> bool:
    for v in forms:
        for m in _ASCII_RUN.finditer(v):
            run = m.group(0)
            for w in _MONEY_EN:
                for end in (w, w + "s"):
                    if len(run) > len(end) and run.endswith(end) and _cost_start(run[:-len(end)]):
                        return True
    return False


def _money_head(forms: tuple) -> bool:
    """A money column (材料費, 材料単価, Material cost, MaterialCost, MATERIALRATE, Amount …): never the name, the quantity
    or the unit."""
    return _forms_have(forms, MONEY_WORDS) or _joined_money(forms)


# the unit key: an exact unit word wins over a header that only contains one; a header that only contains one is not
# the unit when it names a factor or a mass per unit (Unit Weight, 単位質量, 単位重量: 14 回目)
UNIT_EXACT = frozenset(("単位", "unit", "units", "uom", "u/m", "u.o.m.", "u.o.m"))
UNIT_NOT = ("per", "比重", "密度", "density", "率", "rate", "係数", "factor", "質量", "重量", "weight", "mass", "単重")


def _num(s):
    """A quantity cell: the same rule as the screen (a comma only as a thousands separator, no inner spaces)."""
    return number_or_reason(s)[0]


_KEY_WORDS = re.compile("|".join(re.escape(w.lower()) for ws in HEADERS.values() for w in ws if len(w) > 1))
_KEY_CHARS = frozenset(w.lower() for ws in HEADERS.values() for w in ws if len(w) == 1)


def _key_scores(fs: tuple):
    """For each key of HEADERS, how well one header text names it — (unit: exact unit word first,) rank of the first of
    the key's words that it holds, 0 for an exact match — or None; None for all when it names no key. Money columns
    (材料費, Amount, MATERIALRATE …) are never the name, the quantity or the unit; a text that only contains a unit word
    is not the unit when it names a factor or a mass per unit (Unit Weight, 単位質量). It depends on the text only, so it
    is worked out once per distinct text (15 回目). A text that holds none of the keys' words is answered by one
    search (15 回目の攻撃: most cells of a wide sheet name no key)."""
    if not any(v in _KEY_CHARS or _KEY_WORDS.search(v) for v in fs):
        return None
    money = _money_head(fs)
    out = []
    for key, words in HEADERS.items():
        sc = None
        if not (key in ("name", "quantity", "unit") and money):     # 材料費, 材料単価, Material cost, Amount, Unit Rate …
            first = ()
            if key == "unit":
                exact_unit = any(v in UNIT_EXACT for v in fs)
                first = None if not exact_unit and _forms_have(fs, UNIT_NOT) else (0 if exact_unit else 1,)
            if first is not None:                                  # (Unit Weight, 単位質量: a factor, not the unit)
                for rank, w in enumerate(words):
                    w = w.lower()
                    exact = w in fs
                    if exact or (len(w) > 1 and any(w in v for v in fs)):
                        sc = first + (rank, 0 if exact else 1)
                        break
        out.append(sc)
    return tuple(out) if any(x is not None for x in out) else None


def _header_cells(row: list, work: HeaderWork | None) -> list:
    """(column, scores) of the cells of a row that name a key, among its first MAX_HEADER_CELLS non-empty cells (15 回目:
    a header is far narrower; a wide row of distinct texts was matched cell by cell, key by key and word by word over all
    16,384 columns, twice per sheet)."""
    out = []
    for j, t in _head_cells(row, work):
        sc = _text_scores(t, work)
        if sc is not None:
            out.append((j, sc))
    return out


def _header_map(row: list, not_name: frozenset = frozenset(), work: HeaderWork | None = None) -> dict:
    """The column of each key: the column whose header matches the most preferred word ("Item description" is the name
    before "Item"); an exact match only breaks a tie of the same word; money columns (材料費, Amount, MATERIALRATE …) are
    never the name, the quantity or the unit; for the unit, an exact unit word (単位, Unit, UoM, U/M) wins over a header
    that only contains one (Unit Rate, Unit Weight, 単位質量); a column is used for one key only (see _key_scores).
    `not_name`: columns not to take as the name (their cells are numbers, see _find_header). Only the first
    MAX_HEADER_CELLS non-empty cells of the row are looked at (15 回目)."""
    out, used = {}, set()
    heads = _header_cells(row, work)
    for ki, key in enumerate(HEADERS):
        best = None
        for j, sc in heads:
            if sc[ki] is None or j in used or (key == "name" and j in not_name):
                continue
            score = sc[ki] + (j,)
            if best is None or score < best:
                best = score
        if best is not None:
            out[key] = best[-1]
            used.add(best[-1])
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
    """(function names, references, other names, structured references, 3D reference?, computed range?, name ranges,
    added tokens, summed tokens, looked-up tokens with their keys: see _additive) of a formula, by one linear scan.
    A reference is (sheet or None, first column absolute?, first column, last column
    absolute?, last column, first row absolute?, first row, last row absolute?, last row): a cell (B5), a range (A2:D2;
    the sheet of the first end carries to the second; ends written in reverse order are put in order), a whole column
    (C:C, rows None) or whole rows (2:5, every column). Text inside double quotes is skipped; a word or quoted name
    before "!" names the sheet. A reference over several sheets (明細:集計!C2) is flagged, so is a range whose end is
    computed (A2:INDEX(…)); a range between two defined names (開始:終了) is kept as a name range. Structured references
    are None when their brackets do not balance."""
    f = _ERRLIT.sub('""', f)
    sp = _split_structured(f)
    if sp is None:
        return frozenset(), (), (), None, False, False, (), frozenset(), frozenset(), (), ()
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
        elif kind == "row" and not val[0] and sh is None and val[1] < 100_000:
            seq.append(("val", val[1]))                             # a whole number (a lookup's column index)
        else:
            seq.append(("val", None))                               # a number, a string, a lone row number
        k += 1
    return (frozenset(funcs), tuple(refs), tuple(names), structured, three_d, computed, tuple(nranges)) \
        + _additive(seq, tuple(nm for nm, _ in names))


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
# lookups whose returned column (row) is given by a number: (table argument, index argument, which way)
_NARROW = {"VLOOKUP": (1, 2, "col"), "HLOOKUP": (1, 2, "row"), "INDEX": (0, 2, "col")}
MAX_NEST = 64                                     # Excel's limit for nested functions in one formula
UNPARSED = ("unparsed",)                          # in _additive's answer: the formula's shape was not understood
# how an added reference makes the value, besides its level (see _additive's MARKS; documents._Helpers reads them):
PICKED = 1                                        # one cell looked up (VLOOKUP, INDEX …) or cells chosen by a criterion
SCALED = 2                                        # multiplied or divided (by a number, or by another reference)
ALONE = 4                                         # a lone reference multiplied or divided by numbers only (面積*0.6)
# functions whose first argument is the range they choose cells of by a criterion (SUMIFS(合計範囲, 条件範囲, 条件) …)
_CHOSEN_FIRST = frozenset(("SUMIFS", "AVERAGEIFS", "MAXIFS", "MINIFS", "DSUM", "DMAX", "DMIN", "DAVERAGE", "FILTER"))


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


def _lookup_keys(f: str, res: list) -> frozenset:
    """The key array of a lookup (what it searches for its value), as (token, how): VLOOKUP's table searched in its
    first column ("col"), HLOOKUP's in its first row ("row"), XLOOKUP's / LOOKUP's lookup array and INDEX's MATCH /
    XMATCH arrays ("all")."""
    n = len(res)
    if f in ("VLOOKUP", "HLOOKUP") and n > 1:
        return frozenset((t, "col" if f == "VLOOKUP" else "row") for t in res[1][0])
    if f == "XLOOKUP" and n > 1:
        return frozenset((t, "all") for t in res[1][0])
    if f == "LOOKUP" and n > 1:
        return frozenset((t, "all" if n == 3 else "col") for t in res[1][0])
    if f == "INDEX":
        return frozenset((t, "all") for r in res[1:] for t in r[5])
    return frozenset()


def _additive(seq, names=()) -> tuple:
    """(added, summed, looked-up, narrowed) tokens of a formula.
    ADDED: the references that may carry the quantity into the formula's value: alone or in a sum, rounded, chosen by
    IF / IFS / SWITCH / CHOOSE, returned by a lookup, scaled by a number (C2*1.05), by a 0/1 condition ((名称=x)*C2,
    --(名称=x)) or by another reference (SUM(明細!C2:E2)*(1+$E$1), 長さ×$G$2: each factor that is not a divisor may carry
    the quantity, as C2*1.05 does), passed to a function this parser does not know (MMULT, PRODUCT, REDUCE, MAP,
    CONVERT …: its arguments may make its value); not those that sit inside a condition, a count or a lookup's key, that
    divide, or are raised to a power, and not a value looked up (VLOOKUP, INDEX …: one cell of a table, a unit mass)
    that multiplies another reference (13 回目: an unknown function and a product of references counted as adding
    nothing, the one unsafe default).
    SUMMED (a part of ADDED): the references the value adds up: alone, in a sum or a difference, rounded, chosen, looked
    up, scaled by numbers or conditions, in a function this parser does not know, and inside a factor of a product that
    itself adds up references ((C2+D2)*E2, SUM(C2:E2)*$H$1: C2, D2 and C2:E2). A reference that is one factor of a
    product of references (面積×厚さ, 長さ×本数×単重, C2*$H$1) is a dimension or a factor of the value, not a part of it
    (14 回目: a row's own parts are what its quantity sums, see documents._Cells.own_parts).
    LOOKED UP: ((token, ((key token, how) …)) …) for each value looked up that a product left out of ADDED, with the key
    array the lookup searched (see _lookup_keys): a lookup keyed on a bill's name column returns a row's own number,
    which documents then treats as added (14 回目).
    NARROWED: ((token, "col" / "row", offset) …) for each table of a VLOOKUP / HLOOKUP / INDEX whose column (row) index
    is a whole number: the lookup returns that column (row) of the table only (14 回目の攻撃).
    A LET name is what its value is; a LAMBDA parameter is nothing of its own. One linear pass (recursive descent, at
    most MAX_NEST levels); a shape it does not understand gives UNPARSED in ADDED (the formula is then not checked),
    never a guess."""
    n = len(seq)
    if not n:
        return frozenset(), frozenset(), (), (), {}   # an empty formula adds nothing
    depth = mx = 0
    for t in seq:
        if t == ("op", "("):
            depth += 1
            mx = max(mx, depth)
        elif t == ("op", ")"):
            depth -= 1
    if mx > MAX_NEST:
        return frozenset((UNPARSED,)), frozenset(), (), (), {}
    pos = [0]
    env = []                                      # LET scopes: [{name: value}]
    picks = {}                                    # added token that is one looked-up cell (not summed since) -> keys
    chosen, scaled, alone = set(), set(), set()   # see MARKS below
    narrow = {}                                   # a lookup's table token -> ("col" / "row", offset) it returns (see call)
    dropped = set()                               # looked-up tokens a product left out of ADDED
    # a value: (all refs, added, a condition?, summed, adds references up?, MATCH / XMATCH key arrays)
    E = (frozenset(), frozenset(), False, frozenset(), False, frozenset())

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

    def arglist(consts=None):                     # consts: the whole number each argument is, or None
        start = pos[0]
        out = [arg()]
        while True:
            if consts is not None:
                one = seq[start] if pos[0] - start == 1 else None
                consts.append(one[1] if one and one[0] == "val" and isinstance(one[1], int) else None)
            if peek() != ("op", ","):
                break
            take()
            start = pos[0]
            out.append(arg())
        expect(")")
        return out

    def unpick(got):                              # summed: no longer one looked-up cell
        for t in got:
            picks.pop(t, None)

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
            return (frozenset(alls | r[0]),) + r[1:]
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
            return r[0], r[1], False, r[3], r[4], r[5]
        finally:
            env.pop()

    def call(f):
        if f == "LET":
            return let_()
        if f == "LAMBDA":
            return lambda_()
        consts = []
        res = arglist(consts)
        alls = frozenset().union(*(r[0] for r in res))
        # VLOOKUP(key, 明細!B:E, 4, 0), HLOOKUP(key, …, 2, 0) and INDEX(明細!B:E, MATCH(…), 4) with the column (row)
        # index written as a number return a cell of that column (row) only (14 回目の攻撃: the whole table reached
        # the other numbers of every row of the bill)
        at = _NARROW.get(f)
        if at and len(res) > at[1] and consts[at[1]] and len(res[at[0]][0]) == 1:
            (tk,) = res[at[0]][0]
            if tk[0] in ("ref", "sr", "nr") and tk in res[at[0]][1]:
                narrow[tk] = (at[2], consts[at[1]] - 1)
        mk = frozenset().union(*(r[5] for r in res))
        if f in _ADD_ALL:
            got = frozenset().union(*(r[1] for r in res))
            unpick(got)
            return alls, got, False, frozenset().union(*(r[3] for r in res)), bool(alls), mk
        if f in _ADD_FIRST:
            if f in _CHOSEN_FIRST:                # SUMIFS(R, …), FILTER(R, 条件), DSUM(表, …): cells chosen by criteria
                chosen.update(res[0][1])
            if f in _LOOKUP_ONE:
                keys = _lookup_keys(f, res)
                for t in res[0][1]:
                    picks[t] = picks.get(t, frozenset()) | keys
                if f == "INDEX":
                    mk = res[0][5]                # INDEX(…, MATCH(…)) uses its MATCH's key array
            return alls, res[0][1], res[0][2] if f in ("N", "VALUE", "INT", "ABS", "ROUND") else False, res[0][3], \
                res[0][4], mk
        if f == "SUMPRODUCT":                     # every array that is not a 0/1 condition is a factor of the sum
            live = [r for r in res if r[0] and not r[2]]
            got = frozenset().union(*(r[1] for r in live))
            unpick(got)
            if any(r[0] and r[2] for r in res):   # SUMPRODUCT(--(名称=x), R): R's cells chosen by the condition
                chosen.update(got)
            summed = live[0][3] if len(live) == 1 else frozenset().union(*(r[3] for r in live if r[4]))
            return alls, got, False, summed, bool(live), mk
        if f in _MASK:
            if f in ("MATCH", "XMATCH") and len(res) > 1:
                mk = mk | res[1][0]               # the array MATCH searches: INDEX's key
            return alls, frozenset(), True, frozenset(), False, mk
        pick = _picked(f, len(res))
        if pick is not None:
            got = [res[i] for i in pick]
            mask = bool(alls) and all(r[2] or not r[0] for r in got) and f not in _ADD_AT and f not in ("SUMIF", "AVERAGEIF", "LOOKUP")
            added = frozenset().union(*(r[1] for r in got))
            summed = frozenset().union(*(r[3] for r in got))
            if f in _LOOKUP_ONE:
                keys = _lookup_keys(f, res)
                for t in added:
                    picks[t] = picks.get(t, frozenset()) | keys
            if f in ("SUMIF", "AVERAGEIF"):       # the sum range's cells are chosen by the criterion
                chosen.update(added)
            return alls, added, mask, summed, any(r[4] for r in got) or f in ("SUMIF", "AVERAGEIF"), mk
        got = frozenset().union(*(r[1] for r in res))   # a function not known here: its arguments may make its value
        unpick(got)
        return alls, got, False, frozenset().union(*(r[3] for r in res)), bool(alls), mk

    def primary():
        t = take()
        if t[0] == "nm":
            nm = names[t[1]] if t[1] < len(names) else None
            for scope in reversed(env):
                if nm in scope:
                    return scope[nm]
            one = frozenset((t,))
            return one, one, False, one, False, frozenset()
        if t[0] in _REFKINDS:
            one = frozenset((t,))
            return one, one, False, one, False, frozenset()
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
            return frozenset().union(*(x[0] for x in r)), frozenset().union(*(x[1] for x in r)), False, \
                frozenset().union(*(x[3] for x in r)), True, frozenset().union(*(x[5] for x in r))
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
            a = (a[0] | b[0], frozenset(), False, frozenset(), False, a[5] | b[5])
        return a

    def term():
        fs = [(None, factor())]
        while peek() in (("op", "*"), ("op", "/")):
            op = take()[1]
            fs.append((op, factor()))
        if len(fs) == 1:
            return fs[0][1]
        alls = frozenset().union(*(f[1][0] for f in fs))
        mk = frozenset().union(*(f[1][5] for f in fs))
        withrefs = [f for f in fs if f[1][0]]
        if withrefs and all(f[1][2] for f in withrefs):
            return alls, frozenset(), True, frozenset(), False, mk   # a product of conditions is a condition
        live = [f for f in withrefs if not f[1][2]]
        if len(live) == 1 and live[0][0] != "/":
            v = live[0][1]
            if len(withrefs) > 1:                 # (名称=x)*C2: its cells chosen by the condition
                chosen.update(v[1])
            else:                                 # C2*1.05, 12.5*C2, 1200*C2/1000: scaled by numbers
                scaled.update(v[1])
                if not v[4]:
                    alone.update(v[1])            # (a lone reference, not a sum)
            return alls, v[1], False, v[3], v[4], mk                 # one reference scaled by numbers or by conditions
        # several references multiplied: each that does not divide may carry the quantity (C2*1.05 and C2*(1+$E$1)
        # alike), except a looked-up cell (長さ×VLOOKUP(径, 単位質量表, 2): a unit mass). Of a factor that adds
        # references up ((C2+D2)*E2) those stay summed; a factor that is one reference is a dimension
        mul = [f[1] for f in live if f[0] != "/"]
        for v in mul:
            dropped.update(t for t in v[1] if t in picks)
        added = frozenset().union(*(v[1] - frozenset(picks) for v in mul))
        summed = frozenset().union(*(v[3] - frozenset(picks) for v in mul if v[4]))
        scaled.update(summed)                     # (C2+D2)*E2, SUM(C2:E2)*$H$1: a sum multiplied by another reference
        return alls, added, False, summed, False, mk

    def sum_():
        rs = [term()]
        while peek() in (("op", "+"), ("op", "-")):
            take()
            rs.append(term())
        if len(rs) == 1:
            return rs[0]
        withrefs = [r for r in rs if r[0]]
        mask = bool(withrefs) and all(r[2] for r in withrefs)
        agg = len([r for r in withrefs if not r[2]]) >= 2 or any(r[4] for r in withrefs)
        return frozenset().union(*(r[0] for r in rs)), frozenset().union(*(r[1] for r in rs)), mask, \
            frozenset().union(*(r[3] for r in rs)), agg, frozenset().union(*(r[5] for r in rs))

    def cat():
        a = sum_()
        while peek() == ("op", "&"):
            take()
            b = sum_()
            a = (a[0] | b[0], frozenset(), False, frozenset(), False, a[5] | b[5])
        return a

    def cmp_():
        a = cat()
        while peek()[0] == "op" and peek()[1] in ("=", "<", ">"):
            op = take()[1]
            if op in ("<", ">") and peek() in (("op", "="), ("op", ">")):
                take()
            b = cat()
            a = (a[0] | b[0], frozenset(), True, frozenset(), False, a[5] | b[5])
        return a

    try:
        r = cmp_()
        while peek() == ("op", ","):                         # a name defined as a union: 明細!$C$2,明細!$C$5
            take()
            b = cmp_()
            r = (r[0] | b[0], r[1] | b[1], False, r[3] | b[3], True, r[5] | b[5])
    except (_Unparsed, IndexError):
        return frozenset((UNPARSED,)), frozenset(), (), (), {}
    if pos[0] < n:
        return frozenset((UNPARSED,)), frozenset(), (), (), {}
    added = frozenset(r[1])
    looked = tuple(sorted((t, tuple(sorted(picks.get(t, ())))) for t in dropped if t not in added and picks.get(t)))
    # MARKS: {added token: PICKED | SCALED | ALONE} for the added tokens that are not plainly summed. PICKED: a value
    # looked up (VLOOKUP, INDEX, XLOOKUP …: one cell of what they name, not summed since) or cells chosen by a criterion
    # (the sum range of SUMIF / SUMIFS / AVERAGEIF(S) / MAXIFS / MINIFS / DSUM, FILTER's array, an array of SUMPRODUCT
    # with a 0/1 condition, (名称=x)*R); SCALED: multiplied or divided; ALONE: a lone reference scaled by numbers only
    # (面積*0.6, 12.5*戸数, 1200*早見!B3/1000). 15 回目の攻撃: documents._Helpers took conditional sums and a shared area or
    # factor cell scaled by a number for cells a counted row sums, and dropped real rows.
    marks = {}
    for t in added:
        m = (PICKED if t in picks or t in chosen else 0) | (SCALED if t in scaled else 0) | (ALONE if t in alone else 0)
        if m:
            marks[t] = m
    return added, frozenset(r[3]) & added, looked, tuple(sorted((t, h, k) for t, (h, k) in narrow.items())), marks


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
    funcs, refs, names, structured, _t, _c, nranges = _formula_parts(text)[:7]
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


MAX_KEYS = 8                                      # key blocks kept per looked-up block


def formula_walk(formula, ctx: dict | None = None, _path: frozenset = frozenset()) -> tuple:
    """(why what the formula reaches cannot be checked, or None; the blocks it reaches) for one cell's formula.
    Each block is (sheet casefolded, or None for this sheet; first column; last column; first row; last row; level;
    keys), None rows meaning every row. The level tells how the block makes the formula's value (see _additive):
    2 = summed into it (alone, in a sum, rounded, chosen, looked up, scaled by a number), 1 = added only as a factor of
    a product of references (面積×厚さ, SUM(…)*(1+$E$1)), 0 = not added (looked up and multiplied, tested, counted,
    a divisor); the level is true when the block is ADDED. `keys` are, for a block looked up and multiplied (level 0),
    the blocks the lookup searched with how ("col": a VLOOKUP table's first column, "row": an HLOOKUP table's first row,
    "all": an XLOOKUP / LOOKUP array or INDEX's MATCH array), else (). With ctx["ones"], an eighth item says how the
    block makes the value besides its level: PICKED | SCALED | ALONE, 0 when plainly summed (see _additive, 15 回目).
    A VLOOKUP / HLOOKUP / INDEX whose column (row) index is written as a whole number gives two blocks: its whole table
    at level 0 (reached: a quantity cell in it is still a copy) and the returned column (row) at the lookup's level
    (14 回目の攻撃: the whole table reached the other numbers of every row of a bill).
    Shared-formula copies are moved by their column / row shift; a defined name is followed to what it refers
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
    funcs, refs, names, structured, three_d, computed, nranges, add, summed, looked, narrow, ones = _formula_parts(text)
    # (ones: the MARKS of _additive)
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
    tokb, order = {}, []                                   # token -> its blocks (sheet, c1, c2, r1, r2), in order
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
        tokb[("ref", i)] = [(shf, lo, hi, rlo, rhi)]
        order.append(("ref", i))
    for k, (table, inner) in enumerate(structured):
        why, blk = _structured_block(table, inner, ctx)
        if why:
            return why, []
        tokb[("sr", k)] = [tuple(blk)] if blk else []
        order.append(("sr", k))
    for j, (left, right) in enumerate(nranges):
        w1, b1 = _lone_block(left, ctx, _path)
        w2, b2 = _lone_block(right, ctx, _path) if not w1 else (None, None)
        if w1 or w2:
            return w1 or w2, []
        s1 = b1[0] or this
        s2 = b2[0] or this
        if s1 != s2 or None in (b1[3], b1[4], b2[3], b2[4]):
            return "名前の範囲（%s）の端を確かめられない。必要なら手で入れる" % "：".join(str(x[1])[:20] for x in (left, right)), []
        tokb[("nr", j)] = [(None if s1 == this else s1, min(b1[1], b2[1]), max(b1[2], b2[2]), min(b1[3], b2[3]),
                            max(b1[4], b2[4]))]
        order.append(("nr", j))
    defined = ctx.get("names") or {}
    params = _let_params(text) if funcs & {"LET", "LAMBDA"} else set()
    used = {}                                              # each name once per formula: its uses
    for j, (nm, sh) in enumerate(names):
        if nm.startswith(("_XLPM.", "__SR")) or nm in params or nm in ("TRUE", "FALSE"):
            continue
        used.setdefault((sh.casefold() if sh else this, nm, sh), []).append(("nm", j))
    if len(used) > MAX_NAME_FOLLOWS:
        return "名前の参照が多すぎて確かめられない（%d 個まで）。必要なら手で入れる" % MAX_NAME_FOLLOWS, []
    named = []
    for (scope, nm, sh), toks in used.items():
        target = name_target(defined, nm, scope)
        if not target:
            T = (ctx.get("tables") or {}).get(nm)
            if T is not None:                              # a table's name alone: its data rows
                why, blk = _structured_block(nm, "", ctx)
                if why:
                    return why, []
                more = [tuple(blk) + (2, ())] if blk else []
            else:
                return "名前 %s の参照先が分からない（ブックに定義が無い）。必要なら手で入れる" % nm[:40], []
        else:
            why, more = _expand_name(nm, scope, target, dict(ctx, sheet=sh or ctx.get("sheet")), _path)
            if why:
                return (why if "（名前 " in why else why + "（名前 %s の参照先）" % nm[:40]), []
            if sh and sh.casefold() != this:               # blocks of a name used as 集計!QTY: on that name's sheet
                on = sh.casefold()
                more = [(b[0] if b[0] is not None else on,) + tuple(b[1:6])
                        + (tuple(((kb[0] if kb[0] is not None else on,) + tuple(kb[1:]), how) for kb, how in b[6]),)
                        for b in more]
        named.append((toks, more))
        for t in toks:
            tokb[t] = more                                 # (blocks with their levels: a key reads their first five)
    looked = dict(looked)

    def level(tok):
        return 2 if tok in summed else (1 if tok in add else 0)

    def keys(tok):
        out_ = []
        for kt, how in looked.get(tok, ()):
            for kb in tokb.get(kt, ())[:MAX_KEYS]:
                out_.append((tuple(kb[:5]), how))
        return tuple(out_[:MAX_KEYS])

    narrow = {t: (h, k) for t, h, k in narrow}
    marks = bool(ctx.get("ones"))                       # the eighth item, when the caller asks for it

    def mark(m):
        return (m,) if marks else ()
    out = []
    for tok in order:
        lv = level(tok)
        kz = keys(tok) if lv == 0 else ()
        blks = tokb[tok]
        nb = narrow.get(tok) if len(blks) == 1 else None
        if nb:
            b = blks[0]
            how, k = nb
            if how == "col" and b[1] + k <= b[2]:
                one = (b[0], b[1] + k, b[1] + k, b[3], b[4])
            elif how == "row" and b[3] is not None and b[4] is not None and b[3] + k <= b[4]:
                one = (b[0], b[1], b[2], b[3] + k, b[3] + k)
            else:
                one = None                                 # past the table's edge (#REF!): the whole table, as before
            if one is not None:
                # the table is still reached (a quantity cell in it is a copy, as before); only the returned column
                # (row) makes the value
                out += [b + (0, ()) + mark(PICKED), one + (lv, kz) + mark(ones.get(tok, 0) | PICKED)]
                continue
        out += [b + (lv, kz) + mark(ones.get(tok, 0)) for b in blks]
    for toks, more in named:
        lv = max(level(t) for t in toks)
        use = PICKED | SCALED | ALONE                      # how the name is used: the least marked of its uses
        for t in toks:
            use &= ones.get(t, 0)
        if len(more) > 1:
            use &= ~ALONE                                  # (a name of several blocks is a sum: scaled, not alone)

        def inner(b, use=use):
            return use | (b[7] if len(b) > 7 else 0)
        if lv == 2:                                        # used as it is: its blocks keep their own levels
            out += [tuple(b[:7]) + mark(inner(b)) for b in more] if marks else more
            continue
        kz = tuple(x for t in toks if level(t) == 0 for x in keys(t))[:MAX_KEYS] if lv == 0 else ()
        for b in more:
            lv2 = min(lv, b[5])
            out.append(tuple(b[:5]) + (lv2, ((kz + tuple(b[6]))[:MAX_KEYS] if lv2 == 0 else ())) + mark(inner(b)))
    return None, out


def formula_refs(formula, ctx: dict | None = None, _seen=None) -> tuple:
    """(why, blocks (sheet, c1, c2, r1, r2)) of formula_walk, without the "added" flags (`_seen` is kept for older
    callers and not used)."""
    why, blocks = formula_walk(formula, ctx)
    return why, [b[:5] for b in blocks]


def added_blocks(formula, ctx: dict | None = None, levels: bool = False) -> list:
    """The blocks (sheet casefolded or None, c1, c2, r1, r2) that a formula ADDS into its value (see _additive), moved
    by a shared formula's shift; with `levels`, each with its level (2 summed, 1 a factor of a product of references),
    and also the blocks it looks a value up from to multiply (level 0).
    With `ctx` the names and table references ([@1F], 明細表[@[1F]:[3F]]) are followed too; when the formula cannot be
    checked, only its own references are read; [] when it cannot be read."""
    if not formula:
        return []
    text, dcol, no_master, drow = _formula_tuple(formula)
    if no_master or text == DATATABLE or len(text) > MAX_FORMULA:
        return []
    if ctx is not None:
        why, blocks = formula_walk(formula, ctx)
        if why is None:
            return [b[:5] + ((b[5],) if levels else ()) for b in blocks if b[5] or (levels and b[6])]
    parts = _formula_parts(text)
    out = []
    for key in sorted(k for k in parts[7] if k[0] == "ref"):
        sh, a1, c1, a2, c2, ar1, r1, ar2, r2 = parts[1][key[1]]
        lo, hi = (c1 if a1 else c1 + dcol), (c2 if a2 else c2 + dcol)
        rlo = None if r1 is None else (r1 if ar1 else r1 + drow)
        rhi = None if r2 is None else (r2 if ar2 else r2 + drow)
        out.append((None if sh is None else sh.casefold(), min(lo, hi), max(lo, hi), rlo, rhi)
                   + (((2 if key in parts[8] else 1),) if levels else ()))
    return out


def formula_reason(formula, col: int = 0, ctx: dict | None = None) -> str | None:
    """Why a formula's references cannot be checked (None when they can; `col` is kept for older callers)."""
    return formula_refs(formula, ctx)[0]


QTY_LIKE = ("数量", "quantity", "qty", "体積", "容積", "重量", "質量", "面積", "volume", "weight", "mass", "area")
# 単位質量 kg/m is a factor; 単重 is the usual short form of 単位重量 in rebar lists (14 回目)
NOT_QTY = ("単位", "unit", "per", "/", "比重", "密度", "density", "率", "rate", "係数", "factor", "単重")


def _qty_cols(header: list, work: HeaderWork | None = None) -> list:
    """The columns whose header names a quantity (設計数量, 所要数量, 体積, 重量, Qty …; not money): a formula elsewhere that
    reaches one of them on another material row copies that row's quantity. The first MAX_HEADER_CELLS non-empty cells of
    the header row are looked at, as for the header itself (15 回目の攻撃)."""
    out = []
    for j, t in _head_cells(header, work):
        fs = _text_forms(t, work)
        if _forms_have(fs, QTY_LIKE) and not _forms_have(fs, MONEY_WORDS + NOT_QTY):
            out.append(j)
    return out


# the row's own size (面積, 長さ, 本数, 設計数量 …): another row's dimension multiplied by such a number of the row (土間 =
# 面積 × 明細の厚さ) is that dimension reused, not a copy. A number of the row under any other header (割増, 戸数, an
# unlabeled 1.05) times another row's 設計 or per-type share recomputes that row (14 回目の攻撃)
SIZE_WORDS = QTY_LIKE + ("長さ", "延長", "本数", "箇所", "か所", "ヶ所", "個数", "枚数", "幅", "高さ", "設計", "正味", "length",
                         "width", "height", "count", "net", "nett")


def _size_cols(header: list, work: HeaderWork | None = None) -> list:
    """The columns whose header names the row's own size (see SIZE_WORDS), not money or a factor (the first
    MAX_HEADER_CELLS non-empty cells of the header row)."""
    out = []
    for j, t in _head_cells(header, work):
        fs = _text_forms(t, work)
        if _forms_have(fs, SIZE_WORDS) and not _forms_have(fs, MONEY_WORDS + NOT_QTY):
            out.append(j)
    return out


def _factor_cols(header: list, work: HeaderWork | None = None) -> list:
    """The columns whose header names money or a factor (単価, 金額, 単位質量, 比重, 密度, 係数, 率, kg/m …): a number there
    is never part of a material row's quantity unless the row's quantity adds it up (the first MAX_HEADER_CELLS non-empty
    cells of the header row)."""
    return [j for j, t in _head_cells(header, work) if _forms_have(_text_forms(t, work), MONEY_WORDS + NOT_QTY)]


HEADING = "見出しの行（数量も単位も無い）は材料の行ではない"
NAME_PROBE_ROWS = 200                             # data rows looked at to see whether a name column holds numbers


def _numbers_mostly(rows: list, i: int, j: int) -> bool:
    """Are most non-empty cells of column j below row i numbers (the name column is then a rate or a code column)?"""
    n = k = 0
    for r in rows[i + 1:i + 1 + NAME_PROBE_ROWS]:
        x = r[j] if j < len(r) else None
        if x is None or str(x).strip() == "":
            continue
        n += 1
        k += _num(x) is not None
    return n > 0 and 2 * k > n


def _find_header(rows: list[list], work: HeaderWork | None = None):
    """(index of the header row, column of each key). When the name column's cells are mostly numbers (a rate column
    whose header the money words miss), the next name column is taken (14 回目); if every name column holds numbers,
    the first one is kept. Each row is looked at in its first MAX_HEADER_CELLS non-empty cells only, and a sheet's
    header is searched once (15 回目: read_xlsx passes it on)."""
    work = work if work is not None else HeaderWork()
    work.searches += 1
    for i, r in enumerate(rows[:30]):            # the header is one of the first rows
        m = first = _header_map(r, work=work)
        if "name" in m and "quantity" in m:
            skip = set()
            while "name" in m and _numbers_mostly(rows, i, m["name"]) and len(skip) < 8:
                skip.add(m["name"])
                m2 = _header_map(r, frozenset(skip), work)
                if "name" not in m2 or "quantity" not in m2:
                    break
                m = m2
            if skip and ("name" not in m or m["name"] in skip or _numbers_mostly(rows, i, m["name"])):
                m = first                          # every name column holds numbers: as before
            return i, m
    return None, {}


def _pivot_rows(pvs, qc: int) -> tuple:
    """([first row of each stretch of rows], [the reason of the first pivot table that holds the quantity cell of those
    rows, or None]) for one sheet: the pivot tables whose columns hold the quantity column, built once per sheet (a
    sweep over their rows), so that each row is found by bisection. Before, every row tested every pivot table
    (14 回目の攻撃: 1,000 pivot tables × 190,000 rows held the worker three times as long). The first pivot table in
    the workbook's order wins, as before."""
    ivs = sorted((pv["r1"], pv["r2"], i, pv["reason"]) for i, pv in enumerate(pvs) if pv["c1"] <= qc <= pv["c2"])
    if not ivs:
        return (), ()
    starts, reasons, heap, j = [], [], [], 0
    for b in sorted({iv[0] for iv in ivs} | {iv[1] + 1 for iv in ivs}):
        while j < len(ivs) and ivs[j][0] <= b:
            heapq.heappush(heap, (ivs[j][2], ivs[j][1], ivs[j][3]))
            j += 1
        while heap and heap[0][1] < b:                 # pivot tables that end above this row
            heapq.heappop(heap)
        starts.append(b)
        reasons.append(heap[0][2] if heap else None)
    return starts, reasons


def _rows_to_candidates(rows: list[list], sheet: str, doc_id: str, row_numbers: list[int] | None = None,
                        formulas: list[dict] | None = None, fctx: dict | None = None, found: tuple | None = None,
                        hidden: list | None = None, work: HeaderWork | None = None,
                        hidden_heads: list | None = None) -> dict:
    """The candidate rows of one sheet. `found`: its header as _find_header gave it (read_xlsx searches once per sheet,
    15 回目); `hidden`: for each row, the hidden columns that hold a number (their values are not read, but a formula
    elsewhere that adds one up copies part of that row, 15 回目), except the columns whose hidden header text
    (`hidden_heads`: the hidden columns' texts of the first 30 rows) names money or a factor, as for visible columns
    (割増率, 単価, 単位質量: 15 回目の攻撃)."""
    work = work if work is not None else HeaderWork()
    if found is False:                           # not searched: the document's header budget was spent (read_xlsx)
        return {"sheet": sheet, "rows": [], "skipped": [], "unsearched": True}
    hdr_i, hmap = found if found is not None else _find_header(rows, work)
    if hdr_i is None:
        return {"sheet": sheet, "rows": [], "skipped": [], "error": "見出し行（名称・数量）が見つからない"}
    hx = set()
    if hidden and hidden_heads and hdr_i < len(hidden_heads):
        hx = {j for j, h in hidden_heads[hdr_i].items() if _forms_have(_head_forms(h, work), MONEY_WORDS + NOT_QTY)}
    pivots = _pivot_rows((fctx or {}).get("pivots", {}).get(str(sheet).casefold(), ()), hmap["quantity"])

    def pivot_of(rn):                            # a pivot table's cell: why it is not added (see read_xlsx)
        if pivots[0]:
            k = bisect.bisect_right(pivots[0], rn) - 1
            if k >= 0:
                return pivots[1][k]
        return None
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
        # the columns of the row that hold numbers (a formula elsewhere that adds one of them up copies part of it),
        # with its hidden columns that hold one (15 回目: a summary of a hidden 設計数量 was added on top of the row)
        ncols = tuple(j for j, x in enumerate(r[:MAX_COLS]) if x is not None and x != "" and _num(x) is not None)
        if hidden and hidden[i]:
            ncols = tuple(sorted(set(ncols) | (set(hidden[i]) - hx)))
        pv = pivot_of(rn)
        if q is None:
            raw = col("quantity")
            if (raw is None or str(raw).strip() == "") and not texts["unit"]:
                skipped.append(dict(texts, row=rn, trace=trace, reason=HEADING, heading=True, ncols=ncols))
                continue                         # コンクリート工事, 鉄筋工事 …: a heading, not a row left out
            why = number_or_reason(raw)[1]
            skipped.append(dict(texts, row=rn, trace=trace, qtext="" if raw is None else str(raw)[:40], ncols=ncols,
                                reason="数量が数値でない（0 として読まない）" + ("：" + why if why else ""),
                                **({"pivot": pv} if pv is not None else {})))
            continue
        # a formula's references are checked by the importer, which follows them through the whole workbook (one walk
        # per document, within its budget)
        fobj = (formulas[i] if formulas else {}).get(hmap["quantity"])
        cand = dict(texts, quantity=q, trace=trace, row=rn, qf=fobj, ncols=ncols)
        if pv is not None:
            cand["pivot"] = pv
        cands.append(cand)
    return {"sheet": sheet, "rows": cands, "skipped": skipped, "qcol": hmap["quantity"],
            # the columns that tell the rows apart (a lookup keyed on one of them returns a row's own number)
            "keycols": sorted(hmap[k] for k in ("name", "specification", "division") if k in hmap),
            "qcols": sorted(set(_qty_cols(rows[hdr_i], work)) | {hmap["quantity"]}),
            "xcols": _factor_cols(rows[hdr_i], work),
            "sizecols": _size_cols(rows[hdr_i], work),
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


_COL_LETTERS = re.compile(r"[A-Z]+")
_COL_SEEN = {}                                    # column letters -> index (at most 18,278: AAA..ZZZ and shorter)


def _col_index(ref: str) -> int:
    m = _COL_LETTERS.match(ref or "")
    if not m or len(m.group(0)) > 3:
        raise ImportError_("セルの位置 %r を読めない（Excel の列の上限を超えている）" % ref)
    letters = m.group(0)
    n = _COL_SEEN.get(letters)
    if n is None:
        n = 0
        for ch in letters:
            n = n * 26 + (ord(ch) - 64)
        n = _COL_SEEN[letters] = n - 1
    return n


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
MAX_PIVOTS = 1_000                                # pivot tables of a workbook
PIVOT_HEAD = 65_536                               # bytes read of a pivot part (its location / source come first)
# a pivot table's cells summarise another table: never added (14 回目)
R_PIVOT = "ピボットテーブル（%s）の値は足さない（元の表 %s の集計。そのシートも読んでいるので二重計上になる）"
R_PIVOT_UNREAD = "ピボットテーブル（%s）の値は足さない（元の表 %s の集計。そのシートの数量は読んでいないので、足すべき行なら" \
                 "元の表を確かめて手で入れる）"
R_PIVOT_UNKNOWN = "ピボットテーブル（%s）の元の表が分からないので確かめられない（足さない）。必要なら手で入れる"
R_PIVOT_PLACE = "ピボットテーブル（%s）の場所が分からないので、このシートの値は確かめられない（足さない）。必要なら手で入れる"
# what the warning says of each kind of pivot table: only a source that is read here is counted (15 回目)
PIVOT_SAID = {"read": "元の表の集計。元の表の行を数える",
              "unread": "元の表 %s の集計。%s の数量は読んでいないので、この値はどこにも数えていない。足すべき値なら元の表を確かめて手で入れる",
              "unknown": "元の表が分からないので、元の表の行を数えているかは確かめられない。必要なら手で入れる",
              "place": "ピボットテーブルの場所が分からないので、このシートの値は確かめられない。必要なら手で入れる"}
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

    def head_xml(name, want):
        """{tag: attributes} of the first element of each wanted tag, reading at most PIVOT_HEAD bytes of the part (in
        small pieces, counted against the budget); {} when the part is missing."""
        found, got = {}, 0
        try:
            fh = z.open(name)
        except KeyError:
            return found
        except (zipfile.BadZipFile, OSError, EOFError) as e:
            raise ImportError_("Excel ファイルが壊れている（%s）" % e) from None
        parser = ET.XMLPullParser(events=("start",))
        try:
            with fh:
                while got < PIVOT_HEAD and len(found) < len(want):
                    chunk = fh.read(min(4096, PIVOT_HEAD - got))
                    if not chunk:
                        break
                    got += len(chunk)
                    if got > budget["left"]:
                        raise ImportError_("展開すると大きすぎる Excel ファイルは読まない（1 部品 %d MB・合計 %d MB まで）"
                                           % (MAX_PART // 1_000_000, MAX_TOTAL // 1_000_000))
                    parser.feed(chunk)
                    for _ev, el in parser.read_events():
                        tag = el.tag.rsplit("}", 1)[-1]
                        if tag in want and tag not in found:
                            found[tag] = dict(el.attrib)
        except ET.ParseError as e:
            raise ImportError_("Excel の部品 %s を読めない（%s）" % (name, e)) from None
        except (zipfile.BadZipFile, OSError, EOFError) as e:
            raise ImportError_("Excel ファイルが壊れている（%s）" % e) from None
        budget["left"] -= got
        return found

    def rel_path(base, tgt):
        """A relationship's target as a part name (relative to the folder of the part that refers to it)."""
        parts = (base + "/" + tgt).split("/") if not tgt.startswith("/") else tgt.lstrip("/").split("/")
        norm = []
        for p_ in parts:
            if p_ == "..":
                if norm:
                    norm.pop()
            elif p_ and p_ != ".":
                norm.append(p_)
        return "/".join(norm)

    def part_rels(path):
        """[(type, target part)] of a part's relationships."""
        rp = path.rsplit("/", 1)
        rels_path = "%s/_rels/%s.rels" % (rp[0], rp[1]) if len(rp) == 2 else ""
        if rels_path not in names:
            return []
        return [(str(r.get("Type") or ""), rel_path(rp[0], str(r.get("Target") or ""))) for r in small_xml(rels_path)]

    wb = small_xml("xl/workbook.xml")
    rels = small_xml("xl/_rels/workbook.xml.rels")
    main = wb.tag[1:].split("}")[0] if wb.tag.startswith("{") else NS["m"]
    if main != NS["m"] and main not in STRICT:
        raise ImportError_("Excel のブックの形式（名前空間 %s）を読めない" % main[:80])
    ns = {"m": main}
    rel_ns = STRICT.get(main, REL_NS)
    M = "{%s}" % main
    tag_c, tag_v, tag_f = M + "c", M + "v", M + "f"           # (direct children: faster than find with a path)
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
    tables, pivots, caches = {}, [], {}
    # pivot caches named by the workbook (cacheId -> part), for a pivot table whose own relationship is missing
    cache_ids = {}
    pc = wb.find("m:pivotCaches", ns)
    for c_ in (pc if pc is not None else []):
        tgt = rel_target.get(c_.get("{%s}id" % rel_ns))
        if tgt:
            cache_ids[str(c_.get("cacheId"))] = rel_path("xl", tgt)

    def read_pivot(ppath, shf):
        """A pivot table of a sheet: its cells (with the page fields above them) and the table it summarises."""
        if len(pivots) >= MAX_PIVOTS:
            raise ImportError_("ピボットテーブルが多すぎる（%d まで）" % MAX_PIVOTS)
        h = head_xml(ppath, ("pivotTableDefinition", "location"))
        loc = h.get("location") or {}
        blk = _ref_block(loc.get("ref"))
        placed = blk is not None                  # a pivot whose place is not told: the whole sheet is unsure
        c1, c2, r1, r2 = blk if placed else (0, MAX_COLS - 1, 1, MAX_ROW_NUMBER)
        try:
            pages = max(0, int(loc.get("rowPageCount") or 0))
        except ValueError:
            pages = 0
        if pages:
            r1, c2 = max(1, r1 - pages - 1), max(c2, c1 + 1)       # the page fields sit above the table
        name = str((h.get("pivotTableDefinition") or {}).get("name") or "")[:40]
        cpath = next((t for typ, t in part_rels(ppath) if typ.endswith("/pivotCacheDefinition")), None)
        if cpath is None:
            cpath = cache_ids.get(str((h.get("pivotTableDefinition") or {}).get("cacheId")))
        src, sref = None, None
        if cpath and cpath in names:
            if cpath not in caches:
                caches[cpath] = head_xml(cpath, ("cacheSource", "worksheetSource"))
            c = caches[cpath]
            ws = c.get("worksheetSource")
            if (c.get("cacheSource") or {}).get("type", "worksheet") == "worksheet" and ws \
                    and not any(k.endswith("}id") for k in ws):
                src = ("sheet", ws["sheet"]) if ws.get("sheet") else (("name", ws["name"]) if ws.get("name") else None)
                if ws.get("sheet"):
                    sref = _ref_block(ws.get("ref"))   # (the range it summarises, when told)
        pivots.append({"name": name, "sheet": shf, "c1": c1, "c2": c2, "r1": r1, "r2": r2, "source": src,
                       "placed": placed, "sref": sref})

    def read_tables(path, shf):
        for typ, tpath in part_rels(path):
            if typ.endswith("/pivotTable"):
                if tpath in names:
                    read_pivot(tpath, shf)
                continue
            if not typ.endswith("/table"):
                continue
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
        rows, numbers, forms, hidden_nums, hidden_heads = [], [], [], [], []
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
            vals, fs, hnum, htext = {}, {}, [], {}
            last = -1
            n_el = 0
            for c in el:
                if c.tag != tag_c:
                    continue
                n_el += 1
                ref, t = c.get("r"), c.get("t")
                ci = _col_index(ref) if ref else last + 1     # a cell without a reference follows the previous one
                last = ci                                     # (every element is counted, repeated or not)
                if ci >= MAX_COLS:
                    raise ImportError_("列の位置 %s が Excel の上限を超えている" % ref)
                v = f = None                                  # its first <v> and <f> (as find would give them)
                for ch in c:
                    if ch.tag == tag_v:
                        if v is None:
                            v = ch
                    elif ch.tag == tag_f and f is None:
                        f = ch
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
                    # a hidden row / column (often an old revision): value not read. A number in a hidden column of a
                    # visible row is still one of that row's numbers (its column is kept, not its value: a formula
                    # elsewhere that adds it up copies part of the row, 15 回目)
                    if not row_hidden and t in (None, "n") and (v is not None or f is not None):
                        hnum.append(ci)
                    elif not row_hidden and len(rows) < 30 and len(htext) < MAX_HEADER_CELLS and t in ("s", "inlineStr", "str"):
                        # the text of a hidden column in a row that may be the header (one of the first 30): only to
                        # tell a factor or money column (割増率, 単価, 単位質量), whose numbers are no part of a row (15
                        # 回目の攻撃). It is not read as a value
                        try:
                            if t == "s":
                                ht = shared[int(v.text)] if v is not None else ""
                            elif t == "inlineStr":
                                is_ = c.find(M + "is")
                                ht = _plain_text(is_, M) if is_ is not None else ""
                            else:
                                ht = v.text if v is not None else ""
                        except (ValueError, TypeError, IndexError):
                            ht = ""
                        if ht:
                            htext[ci] = str(ht)[:MAX_TEXT]
                    continue
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
                hidden_nums.append(tuple(hnum))
                if len(rows) <= 30:
                    hidden_heads.append(htext)
            el.clear()
            root.clear()
        if cut:
            cut_sheets.append(shf)
        if not sheet_hidden:
            out.append({"name": sh.get("name"), "rows": rows, "numbers": numbers, "formulas": forms,
                        "hidden_rows": hidden_rows, "hidden_cols": hidden_cols.count(1), "hidden_nums": hidden_nums,
                        "hidden_heads": hidden_heads})
    return {"sheets": out, "hidden_sheets": hidden_sheets, "names": defined, "names_cut": names_cut, "tables": tables,
            "fcells": fcells, "sheet_names": sheet_names, "cut_sheets": cut_sheets, "pivots": pivots}


def _pivot_source(wbk: dict, src) -> str | None:
    """The sheet (casefolded) of the table a pivot table summarises: its cache's worksheetSource sheet, or the sheet of
    the table / defined name it names; None when it cannot be told (another workbook, a consolidation, no sheet)."""
    if not src:
        return None
    kind, val = src
    if kind == "sheet":
        shf = str(val).casefold()
        return shf if shf in wbk["sheet_names"] else None
    T = wbk["tables"].get(str(val).upper())
    if T is not None:
        return T["sheet"]
    text = name_target(wbk["names"], str(val).upper(), None)
    if not text:
        return None
    refs = _formula_parts(text.lstrip("="))[1]
    sheets = {(r[0] or "").casefold() for r in refs}
    if len(sheets) != 1 or "" in sheets:
        return None
    shf = sheets.pop()
    return shf if shf in wbk["sheet_names"] else None


def _pivot_reasons(wbk: dict, qsheets: list, warnings: list) -> dict:
    """{sheet casefolded: [pivot table area with the reason its cells are not added]} (14 回目: a pivot table was read
    as a second bill and every material was doubled). The cells are a summary of their source: surely not added when
    the source sheet is read here, "may belong" when it is not (hidden, or no quantity header), unchecked when the
    source cannot be told."""
    read_here = {str(x).casefold() for x in qsheets}
    seen = {str(sh["name"]).casefold() for sh in wbk.get("sheets") or ()}     # visible sheets: their values are read
    out, said = {}, {}
    for pv in wbk.get("pivots") or ():
        src = _pivot_source(wbk, pv["source"])
        name = pv["name"] or "名前なし"
        label = None
        if not pv.get("placed", True):
            reason, kind = R_PIVOT_PLACE % name, "place"
        elif src is None:
            reason, kind = R_PIVOT_UNKNOWN % name, "unknown"
        else:
            label = sheet_label(wbk["sheet_names"].get(src, src))
            reason, kind = (R_PIVOT % (name, label), "read") if src in read_here else (R_PIVOT_UNREAD % (name, label),
                                                                                       "unread")
        # (src / src_seen: the source sheet, and whether it is a visible sheet whose values are read, quantity table or
        # not: see documents.read, 15 回目の攻撃)
        out.setdefault(pv["sheet"], []).append(dict(pv, reason=reason, label=label, kind=kind, src=src, src_seen=src in seen))
        said.setdefault((pv["sheet"], kind, label), []).append(name)
    # the warning follows each pivot table's reason (15 回目: it said "the source rows are counted" also when the source
    # sheet was hidden or could not be told)
    for (shf, kind, label), nms in said.items():
        warnings.append("%s：ピボットテーブル（%s）の値は足していない（%s）"
                        % (sheet_label(wbk["sheet_names"].get(shf, shf)), "、".join(n[:20] for n in nms[:5]),
                           PIVOT_SAID[kind] % ((label,) * PIVOT_SAID[kind].count("%s"))))
    return out


def read_xlsx(data: bytes, doc_id: str, work: HeaderWork | None = None) -> dict:
    wbk = xlsx_workbook(data)
    # each sheet's header is searched once, and passed on (15 回目: it was searched twice per sheet). Once
    # MAX_HEADER_WORK cells are looked at, the remaining sheets are not searched (False: their rows are not read) and
    # this is said (15 回目の攻撃: 30 sheets with a 16,384-column header row, or 32 sheets of 30 rows × 1,024 texts, held
    # the worker 13–22 s)
    work = work if work is not None else HeaderWork()
    found, unsearched = [], []
    for sh in wbk["sheets"]:
        if work.cells >= MAX_HEADER_WORK:
            found.append(False)
            unsearched.append(sh["name"])
        else:
            found.append(_find_header(sh["rows"], work))
    qsheets = [sh["name"] for sh, fh in zip(wbk["sheets"], found) if fh and fh[0] is not None]
    fctx = {"qsheets": qsheets, "names": wbk["names"], "tables": wbk["tables"]}
    warnings = []
    if unsearched:
        warnings.append("見出しを探すセルが多すぎるので、残りの %d シート（%s%s）は読んでいない（1 つの資料で %d セルまで）。"
                        "必要なら、そのシートだけの資料にして読み込む"
                        % (len(unsearched), "、".join(sheet_label(x) for x in unsearched[:5]), "…" if len(unsearched) > 5 else "",
                           MAX_HEADER_WORK))
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
    fctx["pivots"] = _pivot_reasons(wbk, qsheets, warnings)
    return {"format": "xlsx", "warnings": warnings, "names": wbk["names"], "tables": wbk["tables"], "cells": wbk["fcells"],
            "sheet_names": wbk["sheet_names"], "cut_sheets": wbk.get("cut_sheets", []), "pivots": fctx["pivots"],
            "sheets": [_rows_to_candidates(sh["rows"], sh["name"], doc_id, sh["numbers"], sh["formulas"], fctx, found=fh,
                                           hidden=sh.get("hidden_nums"), work=work, hidden_heads=sh.get("hidden_heads"))
                       for sh, fh in zip(wbk["sheets"], found)]}
