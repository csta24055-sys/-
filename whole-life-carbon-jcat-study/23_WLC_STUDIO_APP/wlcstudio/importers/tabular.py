"""Quantity tables from CSV or Excel (.xlsx) → candidate quantity rows, each traceable to sheet/row/column.

Recognised columns (Japanese or English header words): 品目/名称/材料 (name), 数量/quantity (quantity),
単位/unit (unit), 区分/工種/部位 (division), 規格/仕様 (specification). A row without a number in the
quantity column is reported, not read as 0. Nothing is calculated here: the rows are candidates that the
user maps to materials and accepts (state 図面から計算 with the trace as source_detail).
"""
from __future__ import annotations

import csv
import functools
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
_FTOK = re.compile(r'"(?:[^"]|"")*"|\'(?:[^\']|\'\')*\'|[\w.$]+|.', re.S)
_CELL = re.compile(r"(\$?)([A-Za-z]{1,3})(\$?)(\d+)")
MAX_NAME_FOLLOWS = 20                             # defined names followed per formula (a name may refer to itself)
_COLWORD = re.compile(r"(\$?)([A-Za-z]{1,3})")
_ROWWORD = re.compile(r"\$?\d+")


@functools.lru_cache(maxsize=4096)
def _formula_parts(f: str) -> tuple:
    """(function names, references, other names, structured reference?, 3D reference?) of a formula, by one linear scan.
    A reference is (sheet or None, first column absolute?, first column, last column absolute?, last column, first row
    absolute?, first row, last row absolute?, last row): a cell (B5), a range (A2:D2; the sheet of the first end carries
    to the second; ends written in reverse order are put in order), a whole column (C:C, rows None) or whole rows (2:5,
    every column). Text inside double quotes is skipped; a word or quoted name before "!" names the sheet. A reference
    over several sheets (明細:集計!C2, '明細:集計'!C2) is flagged: what it reaches cannot be checked here."""
    toks, sheet, structured, three_d = [], None, False, False
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
        if tok[0].isalnum() or tok[0] in "_.$":
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
            else:
                toks.append(("name", tok.upper(), sheet))
            sheet = None
            continue
        if tok == "[":
            structured = True
        toks.append(("op", tok, None))
    funcs, refs, names = set(), [], []
    k = 0
    while k < len(toks):
        kind, val, sh = toks[k]
        if kind in ("ref", "col", "row", "name") and sh is None and k + 2 < len(toks) and toks[k + 1] == ("op", ":", None) \
                and toks[k + 2][0] in ("ref", "col", "row") and toks[k + 2][2] is not None:
            three_d = True                                  # 明細:集計!C2 — the first sheet is the word before ":"
        if kind in ("ref", "col", "row") and k + 2 < len(toks) and toks[k + 1] == ("op", ":", None) \
                and toks[k + 2][0] in ("ref", "col", "row"):
            kind2, val2, sh2 = toks[k + 2]
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
            k += 3
            continue
        if kind == "ref":
            refs.append((sh, val[0], val[1], val[0], val[1], val[2], val[3], val[2], val[3]))
        elif kind == "col":
            names.append((val[2], sh))                              # a lone 1-3 letter word is a name, not a column
        elif kind == "name":
            names.append((val, sh))
        elif kind == "func":
            funcs.add(val)
        k += 1
    return frozenset(funcs), tuple(refs), tuple(names), structured, three_d


def _formula_tuple(formula):
    if isinstance(formula, str):
        return formula, 0, False, 0
    return (tuple(formula) + (0,))[:4] if len(formula) == 3 else tuple(formula)


def formula_refs(formula, ctx: dict | None = None, _seen: set | None = None) -> tuple:
    """(why what the formula reaches cannot be checked, or None; the cells it reaches) for one cell's formula.
    Each reached block is (sheet casefolded, or None for this sheet; first column; last column; first row; last row),
    None rows meaning every row; shared-formula copies are moved by their column / row shift; a defined name is followed
    to what it refers to (each name once, at most MAX_NAME_FOLLOWS names).
    Cannot be checked: a shared-formula copy without its master, a formula longer than Excel allows, INDIRECT / OFFSET
    (the reference is computed), structured (table) references, references over several sheets, other workbooks.
    Whether a reached cell is another material row (a copy, a total, an allowance) is judged by the importer, which
    knows the rows of every sheet. `formula` is (text, column shift, master missing?, row shift) or plain text; `ctx` has
    "sheet" (this sheet's name) and "names" (defined names)."""
    if not formula:
        return None, []
    text, dcol, no_master, drow = _formula_tuple(formula)
    ctx = ctx or {}
    seen = set() if _seen is None else _seen
    if no_master:
        return "数式の中身が分からない（共有の数式の元が無い）。必要なら手で入れる", []
    if len(text) > MAX_FORMULA:
        return "数式が長すぎて確かめられない（%d 文字まで）" % MAX_FORMULA, []
    funcs, refs, names, structured, three_d = _formula_parts(text)
    if funcs & {"INDIRECT", "OFFSET"}:
        return "参照先が数式の中で決まる（INDIRECT・OFFSET）ので確かめられない。必要なら手で入れる", []
    if structured:
        return "表の参照（構造化参照）は確かめられない。必要なら手で入れる", []
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
    defined = ctx.get("names") or {}
    for nm, _sh in names:
        target = defined.get(nm)
        if not target or nm in seen:
            continue
        if len(seen) >= MAX_NAME_FOLLOWS:
            return "名前の参照が多すぎて確かめられない（%d 個まで）。必要なら手で入れる" % MAX_NAME_FOLLOWS, []
        seen.add(nm)
        why, more = formula_refs((target.lstrip("="), 0, False, 0), ctx, seen)
        if why:
            return why + "（名前 %s の参照先）" % nm, []
        out += more
    return None, out


def formula_reason(formula, col: int = 0, ctx: dict | None = None) -> str | None:
    """Why a formula's references cannot be checked (None when they can; `col` is kept for older callers)."""
    return formula_refs(formula, ctx)[0]


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
        why = formula_reason(fobj, hmap["quantity"], dict(fctx or {}, sheet=sheet))
        if why:
            skipped.append(dict(texts, row=rn, trace=trace, reason=why))
            continue
        cands.append(dict(texts, quantity=q, trace=trace, row=rn, qf=fobj))
    return {"sheet": sheet, "rows": cands, "skipped": skipped, "qcol": hmap["quantity"],
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


def xlsx_workbook(data: bytes, skip_hidden: bool = True, formula_budget: int | None = MAX_FORMULA_CHARS) -> dict:
    """{"sheets": [{name, rows, numbers, formulas, hidden_rows}], "hidden_sheets": [...], "names": {defined names}}.
    Cell values are the stored text/cached values (no formula is evaluated; the formula text is kept per cell so that
    totals can be recognised). With skip_hidden, hidden / veryHidden sheets and hidden rows are not read (an old
    revision kept hidden would be added on top of the visible one) and are named in the result.

    Guards (a quantity table is small): every part is read through a bounded stream counting the bytes actually
    decompressed; the XML is parsed incrementally (iterparse, elements cleared as they are consumed), with limits on
    shared strings, cells and columns enforced while parsing, never after a full tree is built."""
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

    wb_raw = read("xl/workbook.xml")
    rels_raw = read("xl/_rels/workbook.xml.rels")
    if len(wb_raw) > 2_000_000 or len(rels_raw) > 2_000_000:
        raise ImportError_("Excel のブックの部品が大きすぎる")
    try:
        wb = ET.fromstring(wb_raw)
        rels = ET.fromstring(rels_raw)
    except ET.ParseError as e:
        raise ImportError_("Excel のブックの部品を読めない（%s）" % e) from None
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
    out, hidden_sheets = [], []
    cells = {"n": 0, "chars": 0, "rows": 0, "fchars": 0}
    defined = {}
    dn = wb.find("m:definedNames", ns)
    for d in (dn if dn is not None else []):
        if d.get("name") and d.text and len(defined) < 2000:
            defined[d.get("name").upper()] = d.text[:MAX_FORMULA]
    sheets_el = wb.find("m:sheets", ns)
    for sh in (sheets_el if sheets_el is not None else []):
        rid = sh.get("{%s}id" % rel_ns)
        target = rel_target.get(rid, "") or ""
        path = "xl/" + target.lstrip("/").replace("xl/", "") if not target.startswith("/xl/") else target.lstrip("/")
        if path not in names:
            continue
        if skip_hidden and sh.get("state") in ("hidden", "veryHidden"):
            hidden_sheets.append(sh.get("name"))
            continue
        rows, numbers, forms = [], [], []
        hidden_rows = 0
        hidden_cols = bytearray(MAX_COLS)               # 1 = hidden; set by slices (no per-column loop in Python)
        shared_f = {}                                   # si -> formula text of a shared formula's master cell
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
            # every row costs at least one cell, so that a sheet of empty <row/> elements cannot run unbounded
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
            if skip_hidden and el.get("hidden") in ("1", "true"):
                hidden_rows += 1
                cells["n"] += 1
                el.clear()
                root.clear()
                continue
            vals, fs = {}, {}
            last = -1
            for c in el.findall("m:c", ns):
                ref, t = c.get("r"), c.get("t")
                v = c.find("m:v", ns)
                f = c.find("m:f", ns)
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
                ci = _col_index(ref) if ref else last + 1     # a cell without a reference follows the previous one
                last = ci
                if ci >= MAX_COLS:
                    raise ImportError_("列の位置 %s が Excel の上限を超えている" % ref)
                if hidden_cols[ci]:
                    continue                          # a hidden column (often an old revision) is not read
                vals[ci] = val
                cells["chars"] += len(val) if isinstance(val, str) else 0
                if f is not None:
                    text = f.text or ""
                    if len(text) > MAX_FORMULA:
                        text = text[:MAX_FORMULA + 1]        # kept only to say "too long" (formula_reason)
                    dcol, no_master, drow = 0, False, 0
                    si = f.get("si")
                    if text:
                        cells["fchars"] += len(text)          # each distinct formula text is scanned once
                        if formula_budget is not None and cells["fchars"] > formula_budget:
                            raise ImportError_("数式の文字が多すぎる（合計 %d 文字まで）" % formula_budget)
                    if f.get("t") == "shared" and si is not None:
                        if text:
                            shared_f[si] = (text, ci, rn)     # the master cell: its text, column and row
                        elif si in shared_f:
                            text, mcol, mrow = shared_f[si]
                            dcol = ci - mcol                  # relative columns / rows of the copy move by this much
                            drow = rn - mrow
                        else:
                            no_master = True
                    fs[ci] = (text, dcol, no_master, drow)
                    cells["chars"] += len(text)
            if cells["chars"] > MAX_CHARS:
                raise ImportError_("セルの文字が多すぎる（合計 %d 文字まで）" % MAX_CHARS)
            cells["n"] += max(max(vals) + 1 if vals else 0, 1)
            if cells["n"] > MAX_CELLS:
                raise ImportError_("セルが多すぎる（%d まで）" % MAX_CELLS)
            if vals:
                rows.append([vals.get(j) for j in range(max(vals) + 1)])
                numbers.append(rn)
                forms.append(fs)
            el.clear()
            root.clear()
        out.append({"name": sh.get("name"), "rows": rows, "numbers": numbers, "formulas": forms, "hidden_rows": hidden_rows,
                    "hidden_cols": hidden_cols.count(1)})
    return {"sheets": out, "hidden_sheets": hidden_sheets, "names": defined}


def read_xlsx(data: bytes, doc_id: str) -> dict:
    wbk = xlsx_workbook(data)
    # the sheets read as quantity tables: a formula that references one of them from another is a copy (a 再掲)
    qsheets = [sh["name"] for sh in wbk["sheets"] if _find_header(sh["rows"])[0] is not None]
    fctx = {"qsheets": qsheets, "names": wbk["names"]}
    warnings = []
    if not wbk["sheets"] and not wbk["hidden_sheets"]:
        warnings.append("シートを読めなかった（シートが無いか、形式が違う）")
    if wbk["hidden_sheets"]:
        warnings.append("非表示のシート（%s）は読んでいない（古い版を隠して残していることがある。必要なら表示してから読み込む）"
                        % "、".join(str(x) for x in wbk["hidden_sheets"][:10]))
    for sh in wbk["sheets"]:
        if sh["hidden_rows"]:
            warnings.append("%s：非表示の行 %d 行は読んでいない" % (sh["name"], sh["hidden_rows"]))
        if sh.get("hidden_cols"):
            warnings.append("%s：非表示の列 %d 列は読んでいない（古い数量の列のことがある）" % (sh["name"], sh["hidden_cols"]))
    if len(qsheets) > 1:
        warnings.append("数量の表が %d シートある（%s）：同じ材料が別のシートにも載っていないか確かめる"
                        % (len(qsheets), "、".join(qsheets[:6])))
    # the formula of every cell of every read sheet (the importer follows what a quantity formula reaches)
    cells = {str(sh["name"]).casefold(): {rn: fs for rn, fs in zip(sh["numbers"], sh["formulas"]) if fs}
             for sh in wbk["sheets"]}
    return {"format": "xlsx", "warnings": warnings, "names": wbk["names"], "cells": cells,
            "sheet_names": {str(sh["name"]).casefold(): str(sh["name"]) for sh in wbk["sheets"]},
            "sheets": [_rows_to_candidates(sh["rows"], sh["name"], doc_id, sh["numbers"], sh["formulas"], fctx)
                       for sh in wbk["sheets"]]}
