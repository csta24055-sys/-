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
    letters = re.match(r"[A-Z]+", ref).group(0)
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def xlsx_sheets(data: bytes) -> list[tuple[str, list[list]]]:
    """All sheets of an .xlsx as (name, rows); cell values are the stored text/cached values (no formula is evaluated)."""
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ImportError_("Excel（.xlsx）として開けない") from None
    names = z.namelist()
    if any(n.lower().endswith("vbaproject.bin") for n in names):
        raise ImportError_("マクロを含むファイルは読まない（マクロを実行・解析しない方針）")
    shared = []
    if "xl/sharedStrings.xml" in names:
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.findall("m:si", NS):
            shared.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    rel_target = {r.get("Id"): r.get("Target") for r in rels}
    out = []
    for sh in wb.find("m:sheets", NS):
        rid = sh.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        target = rel_target.get(rid, "")
        path = "xl/" + target.lstrip("/").replace("xl/", "") if not target.startswith("/xl/") else target.lstrip("/")
        if path not in names:
            continue
        root = ET.fromstring(z.read(path))
        rows = []
        for row in root.iter("{%s}row" % NS["m"]):
            vals = {}
            for c in row.findall("m:c", NS):
                ref, t = c.get("r"), c.get("t")
                v = c.find("m:v", NS)
                if t == "s" and v is not None:
                    val = shared[int(v.text)]
                elif t == "inlineStr":
                    val = "".join(x.text or "" for x in c.iter("{%s}t" % NS["m"]))
                else:
                    val = v.text if v is not None else None   # formulas: the cached value only, never evaluated
                vals[_col_index(ref)] = val
            rows.append([vals.get(j) for j in range(max(vals) + 1)] if vals else [])
        out.append((sh.get("name"), rows))
    return out


def read_xlsx(data: bytes, doc_id: str) -> dict:
    return {"format": "xlsx", "sheets": [_rows_to_candidates(rows, name, doc_id) for name, rows in xlsx_sheets(data)]}
