"""Quantity tables from CSV or Excel (.xlsx) → candidate quantity rows, each traceable to sheet/row/column.

Recognised columns (Japanese or English header words): 品目/名称/材料 (name), 数量/quantity (quantity),
単位/unit (unit), 区分/工種/部位 (division), 規格/仕様 (specification). A row without a number in the
quantity column is reported, not read as 0. Nothing is calculated here: the rows are candidates that the
user maps to materials and accepts (state 図面から計算 with the trace as source_detail).
"""
from __future__ import annotations

import csv
import io
import re
import zipfile
from xml.etree import ElementTree as ET

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


class ImportError_(ValueError):
    pass


def _num(s):
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    t = str(s).strip().replace(",", "").replace("，", "")
    t = t.translate(str.maketrans("０１２３４５６７８９．－", "0123456789.-"))
    if not re.fullmatch(r"-?\d+(\.\d+)?([eE]-?\d+)?", t):
        return None
    return float(t)


def _header_map(row: list) -> dict:
    out = {}
    for j, h in enumerate(row):
        hs = str(h or "").strip().lower()
        for key, words in HEADERS.items():
            if key not in out and any(w.lower() == hs or w.lower() in hs for w in words if len(w) > 1 or w == hs):
                out[key] = j
                break
    return out


def _rows_to_candidates(rows: list[list], sheet: str, doc_id: str) -> dict:
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
        trace = "%s:%s!R%dC%d" % (doc_id, sheet, i + 1, (hmap["quantity"] or 0) + 1)
        if q is None:
            skipped.append({"row": i + 1, "name": name, "reason": "数量が数値でない（0 として読まない）", "trace": trace})
            continue
        cands.append({"name": name, "quantity": q, "unit": str(col("unit") or "").strip(),
                      "division": str(col("division") or "").strip(), "specification": str(col("specification") or "").strip(),
                      "trace": trace, "row": i + 1})
    return {"sheet": sheet, "rows": cands, "skipped": skipped, "header_row": hdr_i + 1}


def read_csv(data: bytes, doc_id: str) -> dict:
    for enc in ("utf-8-sig", "cp932", "utf-8"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ImportError_("CSV の文字コードを読めない（UTF-8 か Shift_JIS にする）")
    rows = list(csv.reader(io.StringIO(text)))
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
    """All sheets of an .xlsx as (name, rows); cell values are the stored text/cached values (no formula is evaluated).

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
                shared.append("".join(t.text or "" for t in el.iter(M + "t")))
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
    cells = {"n": 0}
    sheets_el = wb.find("m:sheets", NS)
    for sh in (sheets_el if sheets_el is not None else []):
        rid = sh.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        target = rel_target.get(rid, "") or ""
        path = "xl/" + target.lstrip("/").replace("xl/", "") if not target.startswith("/xl/") else target.lstrip("/")
        if path not in names:
            continue
        rows = []
        root = None
        for ev, el in events(path):
            if root is None:
                root = el
            if ev != "end" or el.tag != M + "row":
                continue
            vals = {}
            last = -1
            for c in el.findall("m:c", NS):
                ref, t = c.get("r"), c.get("t")
                v = c.find("m:v", NS)
                if t == "s" and v is not None:
                    try:
                        val = shared[int(v.text)]
                    except (ValueError, TypeError, IndexError):
                        raise ImportError_("共有の文字列の番号 %r が正しくない" % (v.text,)) from None
                elif t == "inlineStr":
                    val = "".join(x.text or "" for x in c.iter(M + "t"))
                else:
                    val = v.text if v is not None else None   # formulas: the cached value only, never evaluated
                ci = _col_index(ref) if ref else last + 1     # a cell without a reference follows the previous one
                last = ci
                if ci >= MAX_COLS:
                    raise ImportError_("列の位置 %s が Excel の上限を超えている" % ref)
                vals[ci] = val
            cells["n"] += max(vals) + 1 if vals else 0
            if cells["n"] > MAX_CELLS:
                raise ImportError_("セルが多すぎる（%d まで）" % MAX_CELLS)
            rows.append([vals.get(j) for j in range(max(vals) + 1)] if vals else [])
            el.clear()
            root.clear()
        out.append((sh.get("name"), rows))
    return out


def read_xlsx(data: bytes, doc_id: str) -> dict:
    return {"format": "xlsx", "sheets": [_rows_to_candidates(rows, name, doc_id) for name, rows in xlsx_sheets(data)]}
