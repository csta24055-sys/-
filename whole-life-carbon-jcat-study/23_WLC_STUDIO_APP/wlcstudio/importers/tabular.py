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

HEADERS = {
    "name": ("品目", "名称", "材料", "品名", "項目", "item", "material", "name", "description"),
    "quantity": ("数量", "数", "quantity", "qty", "amount"),
    "unit": ("単位", "unit", "uom"),
    "division": ("区分", "工種", "部位", "division", "category", "element"),
    "specification": ("規格", "仕様", "spec", "specification", "grade"),
}
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
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
    out = {}
    for j, h in enumerate(row):
        hs = str(h or "").strip().lower()
        for key, words in HEADERS.items():
            if key not in out and any(w.lower() == hs or w.lower() in hs for w in words if len(w) > 1 or w == hs):
                out[key] = j
                break
    return out


MAX_FORMULA = 8192                                 # Excel's limit for the text of one formula
_FTOK = re.compile(r'"[^"]*"|\'[^\']*\'|[A-Za-z0-9_.$]+|.', re.S)   # linear: strings, words, single characters
_CELL = re.compile(r"(\$?)([A-Za-z]{1,3})(\$?)(\d+)")
_TOTAL_FUNCS = {"SUM", "SUMIF", "SUMIFS", "SUMPRODUCT", "SUBTOTAL", "AGGREGATE"}


@functools.lru_cache(maxsize=4096)
def _formula_parts(f: str) -> tuple[frozenset, tuple]:
    """(function names, cell references) of a formula, by one linear scan. A reference is (column absolute?, column
    index, qualified by a sheet name?). Text inside quotes is skipped."""
    funcs, refs = set(), []
    last = ""
    for m in _FTOK.finditer(f):
        tok = m.group(0)
        nxt = f[m.end():m.end() + 1]
        if tok[0] in "\"'":
            last = tok
            continue
        if tok[0].isalnum() or tok[0] in "_.$":
            if nxt == "(":
                funcs.add(re.sub(r"^_XL(FN|WS)\.", "", tok.upper()))
            elif nxt != "!":
                c = _CELL.fullmatch(tok)
                if c:
                    refs.append((c.group(1) == "$", _col_index(c.group(2).upper()), last == "!"))
        last = tok
    return frozenset(funcs), tuple(refs)


def formula_reason(formula, col: int) -> str | None:
    """Why a quantity cell computed by a formula must not be added: a SUM-like function, or a reference to another row of
    the same column of this sheet (a total, a 再掲 repeat or an allowance on another row). None for e.g. volume ×
    density. `formula` is (text, column shift of a shared-formula copy, master missing?) or plain text."""
    if not formula:
        return None
    if isinstance(formula, str):
        formula = (formula, 0, False)
    text, dcol, no_master = formula
    if no_master:
        return "数式の中身が分からない（共有の数式の元が無い）。必要なら手で入れる"
    if len(text) > MAX_FORMULA:
        return "数式が長すぎて確かめられない（%d 文字まで）" % MAX_FORMULA
    funcs, refs = _formula_parts(text)
    tot = sorted(funcs & _TOTAL_FUNCS)
    if tot:
        return "数式の合計（%s）の行は足さない（二重計上を防ぐ）" % tot[0]
    # a shared-formula copy: relative columns move with the cell (absolute $ columns stay)
    if any(not sheet and (c if absolute else c + dcol) == col for absolute, c, sheet in refs):
        return "同じ列の別の行から計算した数量（合計・再掲・割増のおそれ）は足さない。必要なら手で入れる"
    return None


def _rows_to_candidates(rows: list[list], sheet: str, doc_id: str, row_numbers: list[int] | None = None,
                        formulas: list[dict] | None = None) -> dict:
    hdr_i, hmap = None, {}
    for i, r in enumerate(rows[:30]):            # the header is one of the first rows
        m = _header_map(r)
        if "name" in m and "quantity" in m:
            hdr_i, hmap = i, m
            break
    if hdr_i is None:
        return {"sheet": sheet, "rows": [], "skipped": [], "error": "見出し行（名称・数量）が見つからない"}
    cands, skipped = [], []
    for i in range(hdr_i + 1, len(rows)):
        r = rows[i]
        def col(k):
            j = hmap.get(k)
            return r[j] if j is not None and j < len(r) else None
        name = str(col("name") or "").strip()
        q = _num(col("quantity"))
        if not name and q is None:
            continue
        rn = row_numbers[i] if row_numbers else i + 1          # the sheet's own row number (gaps kept)
        trace = "%s:%s!R%dC%d" % (doc_id, sheet, rn, (hmap["quantity"] or 0) + 1)
        if q is None:
            why = number_or_reason(col("quantity"))[1]
            skipped.append({"row": rn, "name": name, "reason": "数量が数値でない（0 として読まない）" + ("：" + why if why else ""),
                            "trace": trace})
            continue
        why = formula_reason((formulas[i] if formulas else {}).get(hmap["quantity"]), hmap["quantity"])
        if why:
            skipped.append({"row": rn, "name": name, "reason": why, "trace": trace})
            continue
        cands.append({"name": name, "quantity": q, "unit": str(col("unit") or "").strip(),
                      "division": str(col("division") or "").strip(), "specification": str(col("specification") or "").strip(),
                      "trace": trace, "row": rn})
    return {"sheet": sheet, "rows": cands, "skipped": skipped,
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
    """All sheets of an .xlsx as (name, rows), the rows packed in order (the statistics loaders search by content)."""
    return [(name, rows) for name, rows, _, _ in xlsx_workbook(data)]


def xlsx_workbook(data: bytes) -> list[tuple[str, list[list], list[int], list[dict]]]:
    """All sheets of an .xlsx as (name, rows, row numbers, formulas); cell values are the stored text/cached values
    (no formula is evaluated; the formula text is kept per cell so that totals can be recognised).

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

    M = "{%s}" % NS["m"]
    shared = []
    if "xl/sharedStrings.xml" in names:
        root = None
        for ev, el in events("xl/sharedStrings.xml"):
            if root is None:
                root = el
            if ev == "end" and el.tag == M + "si":
                text = "".join(t.text or "" for t in el.iter(M + "t"))
                if len(text) > MAX_STRING:
                    raise ImportError_("共有の文字列が長すぎる（1 つ %d 文字まで：Excel の上限）" % MAX_STRING)
                shared.append(text)
                if len(shared) > MAX_SHARED:
                    raise ImportError_("共有の文字列が多すぎる（%d まで）" % MAX_SHARED)
                el.clear()
                root.clear()
    wb_raw = read("xl/workbook.xml")
    rels_raw = read("xl/_rels/workbook.xml.rels")
    if len(wb_raw) > 2_000_000 or len(rels_raw) > 2_000_000:
        raise ImportError_("Excel のブックの部品が大きすぎる")
    try:
        wb = ET.fromstring(wb_raw)
        rels = ET.fromstring(rels_raw)
    except ET.ParseError as e:
        raise ImportError_("Excel のブックの部品を読めない（%s）" % e) from None
    rel_target = {r.get("Id"): r.get("Target") for r in rels}
    out = []
    cells = {"n": 0, "chars": 0, "rows": 0}
    sheets_el = wb.find("m:sheets", NS)
    for sh in (sheets_el if sheets_el is not None else []):
        rid = sh.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        target = rel_target.get(rid, "") or ""
        path = "xl/" + target.lstrip("/").replace("xl/", "") if not target.startswith("/xl/") else target.lstrip("/")
        if path not in names:
            continue
        rows, numbers, forms = [], [], []
        shared_f = {}                                   # si -> formula text of a shared formula's master cell
        root = None
        last_row = 0
        for ev, el in events(path):
            if root is None:
                root = el
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
            vals, fs = {}, {}
            last = -1
            for c in el.findall("m:c", NS):
                ref, t = c.get("r"), c.get("t")
                v = c.find("m:v", NS)
                f = c.find("m:f", NS)
                if t == "s" and v is not None:
                    try:
                        val = shared[int(v.text)]
                    except (ValueError, TypeError, IndexError):
                        raise ImportError_("共有の文字列の番号 %r が正しくない" % (v.text,)) from None
                elif t == "inlineStr":
                    val = "".join(x.text or "" for x in c.iter(M + "t"))
                    if len(val) > MAX_STRING:
                        raise ImportError_("セルの文字列が長すぎる（%d 文字まで）" % MAX_STRING)
                else:
                    val = v.text if v is not None else None   # formulas: the cached value only, never evaluated
                ci = _col_index(ref) if ref else last + 1     # a cell without a reference follows the previous one
                last = ci
                if ci >= MAX_COLS:
                    raise ImportError_("列の位置 %s が Excel の上限を超えている" % ref)
                vals[ci] = val
                cells["chars"] += len(val) if isinstance(val, str) else 0
                if f is not None:
                    text = f.text or ""
                    if len(text) > MAX_FORMULA:
                        text = text[:MAX_FORMULA + 1]        # kept only to say "too long" (formula_reason)
                    dcol, no_master = 0, False
                    si = f.get("si")
                    if f.get("t") == "shared" and si is not None:
                        if text:
                            shared_f[si] = (text, ci)         # the master cell: its text and column
                        elif si in shared_f:
                            text, mcol = shared_f[si]
                            dcol = ci - mcol                  # relative columns of the copy move by this much
                        else:
                            no_master = True
                    fs[ci] = (text, dcol, no_master)
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
        out.append((sh.get("name"), rows, numbers, forms))
    return out


def read_xlsx(data: bytes, doc_id: str) -> dict:
    return {"format": "xlsx", "sheets": [_rows_to_candidates(rows, name, doc_id, numbers, forms)
                                         for name, rows, numbers, forms in xlsx_workbook(data)]}
