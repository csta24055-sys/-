"""Stage A: read-only structural scan of the workbooks into a private SQLite file (never in Git).

Streams the OOXML parts with the standard library; does not run Excel or macros and does not
modify the originals. Usage: python3 -I scan.py <originals dir> <out.sqlite3>
"""
import hashlib, os, re, sqlite3, sys, time, zipfile
import xml.etree.ElementTree as ET

X = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
P = "{http://schemas.openxmlformats.org/package/2006/relationships}"
X14 = "{http://schemas.microsoft.com/office/spreadsheetml/2009/9/main}"
XM = "{http://schemas.microsoft.com/office/excel/2006/main}"

SCHEMA = """
CREATE TABLE files (id INTEGER PRIMARY KEY, name TEXT, size INTEGER, sha256 TEXT, n_sheets INTEGER, has_vba INTEGER,
                    n_external_links INTEGER, workbook_protected INTEGER, seconds REAL);
CREATE TABLE sheets (id INTEGER PRIMARY KEY, file_id INTEGER, idx INTEGER, name TEXT, state TEXT, path TEXT, dimension TEXT,
                     protected INTEGER, tab_color TEXT, n_cells INTEGER, n_formula INTEGER, n_num INTEGER, n_str INTEGER,
                     n_blank INTEGER, n_blank_skipped INTEGER, n_merge INTEGER, n_cf INTEGER, n_hidden_rows INTEGER, hidden_cols TEXT);
CREATE TABLE styles (file_id INTEGER, xf INTEGER, locked INTEGER, hidden INTEGER, fill TEXT, numfmt TEXT, font_color TEXT,
                     PRIMARY KEY (file_id, xf));
CREATE TABLE cells (sheet_id INTEGER, row INTEGER, col INTEGER, t TEXT, v TEXT, f TEXT, si INTEGER, xf INTEGER);
CREATE TABLE validations (id INTEGER PRIMARY KEY, sheet_id INTEGER, sqref TEXT, type TEXT, operator TEXT, formula1 TEXT,
                          formula2 TEXT, allow_blank INTEGER, prompt_title TEXT, prompt TEXT, error_title TEXT, error TEXT, ext INTEGER);
CREATE TABLE names (file_id INTEGER, name TEXT, local_sheet INTEGER, hidden INTEGER, refers_to TEXT);
CREATE TABLE merges (sheet_id INTEGER, ref TEXT);
CREATE TABLE controls (file_id INTEGER, sheet_path TEXT, part TEXT, object_type TEXT, fmla_link TEXT, fmla_range TEXT, attrs TEXT);
CREATE TABLE comments (sheet_id INTEGER, ref TEXT, text TEXT);
CREATE TABLE parts (file_id INTEGER, name TEXT, size INTEGER);
"""

def col_num(letters):
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n

REF = re.compile(r"^([A-Z]+)(\d+)$")

def text_of(si):
    """Text of a shared-string or inline-string item, without phonetic runs."""
    out = []
    for child in si:
        if child.tag == X + "t":
            out.append(child.text or "")
        elif child.tag == X + "r":
            for t in child.findall(X + "t"):
                out.append(t.text or "")
    return "".join(out)

def color_of(node):
    if node is None:
        return None
    for key in ("rgb", "theme", "indexed"):
        if key in node.attrib:
            tint = node.attrib.get("tint")
            return "%s:%s%s" % (key, node.attrib[key], ("/" + tint[:6]) if tint else "")
    return None

def read_styles(book):
    root = ET.fromstring(book.read("xl/styles.xml"))
    numfmts = {n.attrib["numFmtId"]: n.attrib.get("formatCode", "") for n in root.iter(X + "numFmt")}
    fills = []
    for fill in root.find(X + "fills") or []:
        pattern = fill.find(X + "patternFill")
        if pattern is None or pattern.attrib.get("patternType") in (None, "none"):
            fills.append(None)
        else:
            fills.append(color_of(pattern.find(X + "fgColor")) or ("pattern:" + pattern.attrib.get("patternType", "")))
    fonts = [color_of(font.find(X + "color")) for font in (root.find(X + "fonts") or [])]
    out = []
    for i, xf in enumerate(root.find(X + "cellXfs") or []):
        prot = xf.find(X + "protection")
        locked = 0 if (prot is not None and prot.attrib.get("locked") in ("0", "false")) else 1
        hidden = 1 if (prot is not None and prot.attrib.get("hidden") in ("1", "true")) else 0
        fill_id, font_id, fmt = int(xf.attrib.get("fillId", 0)), int(xf.attrib.get("fontId", 0)), xf.attrib.get("numFmtId", "0")
        out.append((i, locked, hidden, fills[fill_id] if fill_id < len(fills) else None, numfmts.get(fmt, fmt),
                    fonts[font_id] if font_id < len(fonts) else None))
    return out

def read_shared_strings(book):
    if "xl/sharedStrings.xml" not in book.namelist():
        return []
    out = []
    with book.open("xl/sharedStrings.xml") as fh:
        for event, node in ET.iterparse(fh, events=("end",)):
            if node.tag == X + "si":
                out.append(text_of(node))
                node.clear()
    return out

def scan_sheet(book, path, sheet_id, strings, keep_blank, db):
    stats = dict(n_cells=0, n_formula=0, n_num=0, n_str=0, n_blank=0, n_blank_skipped=0, n_merge=0, n_cf=0, n_hidden_rows=0)
    info = dict(dimension=None, protected=0, tab_color=None, hidden_cols=[])
    batch = []
    with book.open(path) as fh:
        for event, node in ET.iterparse(fh, events=("start", "end")):
            tag = node.tag
            if event == "start":
                if tag == X + "row" and node.attrib.get("hidden") in ("1", "true"):
                    stats["n_hidden_rows"] += 1
                continue
            if tag == X + "c":
                m = REF.match(node.attrib.get("r", ""))
                if not m:
                    node.clear(); continue
                row, col = int(m.group(2)), col_num(m.group(1))
                xf = int(node.attrib.get("s", 0))
                t = node.attrib.get("t", "n")
                fnode, vnode = node.find(X + "f"), node.find(X + "v")
                v = vnode.text if vnode is not None else None
                f = si = None
                if fnode is not None:
                    stats["n_formula"] += 1
                    f = (fnode.text or "")[:4000]
                    if fnode.attrib.get("t") == "shared":
                        si = int(fnode.attrib.get("si", -1))
                        if not f:
                            f = None
                    elif fnode.attrib.get("t") == "array":
                        f = "{ARRAY %s}%s" % (fnode.attrib.get("ref", ""), f)
                    kind = "f"
                    if t == "s" and v is not None:
                        v = strings[int(v)]
                elif t == "s":
                    v = strings[int(v)] if v is not None else ""
                    kind = "s"; stats["n_str"] += 1
                elif t == "inlineStr":
                    isn = node.find(X + "is")
                    v = text_of(isn) if isn is not None else ""
                    kind = "s"; stats["n_str"] += 1
                elif t == "str":
                    kind = "s"; stats["n_str"] += 1
                elif v is None or v == "":
                    kind = "z"
                elif t == "b":
                    kind = "b"
                elif t == "e":
                    kind = "e"
                else:
                    kind = "n"; stats["n_num"] += 1
                if kind == "z":
                    if xf in keep_blank:
                        stats["n_blank"] += 1
                        batch.append((sheet_id, row, col, "z", None, None, None, xf))
                    else:
                        stats["n_blank_skipped"] += 1
                else:
                    stats["n_cells"] += 1
                    if v is not None and len(v) > 2000:
                        v = v[:2000]
                    batch.append((sheet_id, row, col, kind, v, f, si, xf))
                if len(batch) >= 50000:
                    db.executemany("INSERT INTO cells VALUES (?,?,?,?,?,?,?,?)", batch); batch.clear()
                node.clear()
            elif tag == X + "row":
                node.clear()
            elif tag == X + "dimension":
                info["dimension"] = node.attrib.get("ref")
            elif tag == X + "sheetProtection":
                info["protected"] = 1 if node.attrib.get("sheet") in ("1", "true") else 0
            elif tag == X + "tabColor":
                info["tab_color"] = color_of(node)
            elif tag == X + "col":
                if node.attrib.get("hidden") in ("1", "true"):
                    info["hidden_cols"].append("%s-%s" % (node.attrib.get("min"), node.attrib.get("max")))
            elif tag == X + "mergeCell":
                stats["n_merge"] += 1
                db.execute("INSERT INTO merges VALUES (?,?)", (sheet_id, node.attrib.get("ref")))
            elif tag == X + "conditionalFormatting":
                stats["n_cf"] += 1
                node.clear()
            elif tag == X + "dataValidation":
                a = node.attrib
                f1, f2 = node.find(X + "formula1"), node.find(X + "formula2")
                db.execute("INSERT INTO validations (sheet_id, sqref, type, operator, formula1, formula2, allow_blank, prompt_title, "
                           "prompt, error_title, error, ext) VALUES (?,?,?,?,?,?,?,?,?,?,?,0)",
                           (sheet_id, a.get("sqref"), a.get("type"), a.get("operator"), f1.text if f1 is not None else None,
                            f2.text if f2 is not None else None, 1 if a.get("allowBlank") in ("1", "true") else 0,
                            a.get("promptTitle"), a.get("prompt"), a.get("errorTitle"), a.get("error")))
            elif tag == X14 + "dataValidation":
                a = node.attrib
                f1, f2, sq = node.find(X14 + "formula1"), node.find(X14 + "formula2"), node.find(XM + "sqref")
                g = lambda n: (n.find(XM + "f").text if n is not None and n.find(XM + "f") is not None else None)
                db.execute("INSERT INTO validations (sheet_id, sqref, type, operator, formula1, formula2, allow_blank, prompt_title, "
                           "prompt, error_title, error, ext) VALUES (?,?,?,?,?,?,?,?,?,?,?,1)",
                           (sheet_id, sq.text if sq is not None else None, a.get("type"), a.get("operator"), g(f1), g(f2),
                            1 if a.get("allowBlank") in ("1", "true") else 0, a.get("promptTitle"), a.get("prompt"),
                            a.get("errorTitle"), a.get("error")))
    if batch:
        db.executemany("INSERT INTO cells VALUES (?,?,?,?,?,?,?,?)", batch)
    return stats, info

def scan_book(path, file_id, db):
    t0 = time.time()
    with open(path, "rb") as fh:
        sha = hashlib.sha256(fh.read()).hexdigest()
    book = zipfile.ZipFile(path)
    names = book.namelist()
    for info in book.infolist():
        db.execute("INSERT INTO parts VALUES (?,?,?)", (file_id, info.filename, info.file_size))
    styles = read_styles(book)
    db.executemany("INSERT INTO styles VALUES (?,?,?,?,?,?,?)", [(file_id,) + s for s in styles])
    keep_blank = {s[0] for s in styles if s[1] == 0 or s[3] is not None}      # unlocked or filled
    strings = read_shared_strings(book)
    wb = ET.fromstring(book.read("xl/workbook.xml"))
    rels = {r.attrib["Id"]: r.attrib["Target"] for r in ET.fromstring(book.read("xl/_rels/workbook.xml.rels")).findall(P + "Relationship")}
    sheets = []
    for i, s in enumerate(wb.find(X + "sheets")):
        target = rels[s.attrib[R + "id"]].lstrip("/")
        if not target.startswith("xl/"):
            target = "xl/" + target
        sheets.append((i + 1, s.attrib.get("name"), s.attrib.get("state", "visible"), target))
    dn = wb.find(X + "definedNames")
    for n in (dn if dn is not None else []):
        db.execute("INSERT INTO names VALUES (?,?,?,?,?)", (file_id, n.attrib.get("name"), n.attrib.get("localSheetId"),
                                                           1 if n.attrib.get("hidden") in ("1", "true") else 0, n.text))
    wp = wb.find(X + "workbookProtection")
    for idx, name, state, target in sheets:
        if not target.startswith("xl/worksheets/"):
            db.execute("INSERT INTO sheets (file_id, idx, name, state, path) VALUES (?,?,?,?,?)", (file_id, idx, name, state, target))
            continue
        cur = db.execute("INSERT INTO sheets (file_id, idx, name, state, path) VALUES (?,?,?,?,?)", (file_id, idx, name, state, target))
        sid = cur.lastrowid
        stats, info = scan_sheet(book, target, sid, strings, keep_blank, db)
        db.execute("UPDATE sheets SET dimension=?, protected=?, tab_color=?, n_cells=?, n_formula=?, n_num=?, n_str=?, n_blank=?, "
                   "n_blank_skipped=?, n_merge=?, n_cf=?, n_hidden_rows=?, hidden_cols=? WHERE id=?",
                   (info["dimension"], info["protected"], info["tab_color"], stats["n_cells"], stats["n_formula"], stats["n_num"],
                    stats["n_str"], stats["n_blank"], stats["n_blank_skipped"], stats["n_merge"], stats["n_cf"],
                    stats["n_hidden_rows"], ",".join(info["hidden_cols"]), sid))
        # comments and form controls attached to the sheet
        rel_path = target.replace("worksheets/", "worksheets/_rels/") + ".rels"
        if rel_path in names:
            for r in ET.fromstring(book.read(rel_path)).findall(P + "Relationship"):
                tgt = os.path.normpath(os.path.join("xl/worksheets", r.attrib["Target"])).replace(os.sep, "/")
                if "comments" in tgt and tgt in names:
                    for c in ET.fromstring(book.read(tgt)).iter(X + "comment"):
                        t = c.find(X + "text")
                        db.execute("INSERT INTO comments VALUES (?,?,?)", (sid, c.attrib.get("ref"), text_of(t)[:1000] if t is not None else ""))
                elif "ctrlProp" in tgt and tgt in names:
                    a = ET.fromstring(book.read(tgt)).attrib
                    db.execute("INSERT INTO controls VALUES (?,?,?,?,?,?,?)", (file_id, target, tgt, a.get("objectType"), a.get("fmlaLink"),
                                                                               a.get("fmlaRange"), repr(sorted(a.items()))[:500]))
        db.commit()
    db.execute("INSERT INTO files VALUES (?,?,?,?,?,?,?,?,?)",
               (file_id, os.path.basename(path), os.path.getsize(path), sha, len(sheets), int("xl/vbaProject.bin" in names),
                sum(1 for n in names if n.startswith("xl/externalLinks/externalLink")), int(wp is not None), time.time() - t0))
    db.commit()
    print("%-60s sheets %3d  %.0f s" % (os.path.basename(path), len(sheets), time.time() - t0), flush=True)

def main(src, out):
    if os.path.exists(out):
        os.remove(out)
    db = sqlite3.connect(out)
    db.executescript(SCHEMA)
    db.execute("PRAGMA synchronous = OFF"); db.execute("PRAGMA journal_mode = MEMORY")
    books = sorted(n for n in os.listdir(src) if n.lower().endswith((".xlsx", ".xlsm")))
    for i, name in enumerate(books, 1):
        scan_book(os.path.join(src, name), i, db)
    db.execute("CREATE INDEX cells_pos ON cells(sheet_id, row, col)")
    db.execute("CREATE INDEX cells_kind ON cells(sheet_id, t)")
    db.commit(); db.close()

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
