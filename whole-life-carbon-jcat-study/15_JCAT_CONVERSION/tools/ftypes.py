"""Result type (t attribute) of every formula cell, read again from the workbook XML (read-only)."""
import os, re, sqlite3, sys, zipfile
import xml.etree.ElementTree as ET
X = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REF = re.compile(r"^([A-Z]+)(\d+)$")
def coln(s):
    n = 0
    for ch in s: n = n * 26 + ord(ch) - 64
    return n
db = sqlite3.connect(sys.argv[1])
db.execute("DROP TABLE IF EXISTS ftype")
db.execute("CREATE TABLE ftype (sheet_id INTEGER, row INTEGER, col INTEGER, t TEXT, has_v INTEGER)")
for fid, fname in db.execute("SELECT id, name FROM files").fetchall():
    if not fname.endswith((".xlsx", ".xlsm")): continue
    z = zipfile.ZipFile(os.path.join(sys.argv[2], fname))
    for sid, path in db.execute("SELECT id, path FROM sheets WHERE file_id=? AND path LIKE 'xl/worksheets/%'", (fid,)).fetchall():
        batch = []
        with z.open(path) as fh:
            for ev, node in ET.iterparse(fh, events=("end",)):
                if node.tag == X + "c":
                    if node.find(X + "f") is not None:
                        m = REF.match(node.attrib.get("r", ""))
                        v = node.find(X + "v")
                        batch.append((sid, int(m.group(2)), coln(m.group(1)), node.attrib.get("t", "n"), int(v is not None)))
                    node.clear()
                elif node.tag == X + "row":
                    node.clear()
        db.executemany("INSERT INTO ftype VALUES (?,?,?,?,?)", batch)
    db.commit()
db.execute("CREATE INDEX ftype_pos ON ftype(sheet_id, row, col)")
db.commit()
print(db.execute("SELECT t, has_v, COUNT(*) FROM ftype GROUP BY 1,2").fetchall())
