"""Stage B: group the scanned cells into regions (private working data, never in Git).

Roles  I  editable value or blank (cell protection off)      C  locked numeric / boolean constant
       TD column of text data (codes, item names, units)     L  scattered text (labels, notes) - one aggregate per sheet
       F  formulas - aggregated per block of adjacent columns
Usage: python3 -I regions.py <scan.sqlite3>
"""
import collections, hashlib, json, re, sqlite3, sys, time

def L(c):
    s = ""
    while c:
        c, r = divmod(c - 1, 26)
        s = chr(65 + r) + s
    return s

REF = re.compile(r"\$?([A-Z]+)\$?(\d+)")

def col_num(letters):
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n

def parse_range(ref):
    parts = ref.replace("$", "").split(":")
    a = REF.match(parts[0]); b = REF.match(parts[-1])
    if not a or not b:
        return None
    return int(a.group(2)), col_num(a.group(1)), int(b.group(2)), col_num(b.group(1))

def runs_of(rows):
    """Consecutive runs in a sorted list of row numbers."""
    out, start, prev = [], None, None
    for r in rows:
        if start is None:
            start = prev = r
        elif r == prev + 1:
            prev = r
        else:
            out.append((start, prev)); start = prev = r
    if start is not None:
        out.append((start, prev))
    return out

def ranges_text(col, runs):
    return " ".join("%s%d" % (L(col), a) if a == b else "%s%d:%s%d" % (L(col), a, L(col), b) for a, b in runs)

# Fill colours that the legends of the input sheets give for required / optional input cells.
INPUT_FILLS = {1: ({"rgb:FFF8D1D5"}, set()), 2: ({"rgb:FFD2E3F2"}, set()),
               5: ({"rgb:FFC9F1E3", "theme:5/0.7999"}, {"theme:8/0.7999"})}
LEGEND = ("必須入力項目", "任意入力項目")


def main(path):
    db = sqlite3.connect(path)
    db.executescript("""
    DROP TABLE IF EXISTS regions;
    DROP TABLE IF EXISTS dv_outside;
    CREATE TABLE dv_outside (sheet_id INTEGER, dv_id INTEGER, n INTEGER);
    CREATE TABLE regions (id INTEGER PRIMARY KEY, sheet_id INTEGER, role TEXT, col1 INTEGER, col2 INTEGER, row_min INTEGER,
        row_max INTEGER, ranges TEXT, n INTEGER, n_blank INTEGER, n_num INTEGER, n_str INTEGER, n_bool INTEGER, n_distinct INTEGER,
        vmin REAL, vmax REAL, uniform INTEGER, seq INTEGER, n_int INTEGER, fills TEXT, numfmt TEXT, header TEXT, left_label TEXT,
        unit TEXT, dv_id INTEGER, n_patterns INTEGER, sample TEXT, n_req INTEGER, vhash TEXT);
    """)
    t0 = time.time()
    for sid, fid, name in db.execute("SELECT id, file_id, name FROM sheets ORDER BY id").fetchall():
        styles = {xf: (locked, fill, numfmt) for xf, locked, fill, numfmt in
                  db.execute("SELECT xf, locked, fill, numfmt FROM styles WHERE file_id=?", (fid,))}
        anchor = {}
        for (ref,) in db.execute("SELECT ref FROM merges WHERE sheet_id=?", (sid,)):
            rng = parse_range(ref)
            if rng and (rng[2] - rng[0] + 1) * (rng[3] - rng[1] + 1) <= 4000:
                for r in range(rng[0], rng[2] + 1):
                    for c in range(rng[1], rng[3] + 1):
                        anchor[(r, c)] = (rng[0], rng[1])
        dv_cells = {}
        for dv_id, sqref in db.execute("SELECT id, sqref FROM validations WHERE sheet_id=?", (sid,)):
            for part in (sqref or "").split():
                rng = parse_range(part)
                if rng and (rng[2] - rng[0] + 1) * (rng[3] - rng[1] + 1) <= 20000:
                    for r in range(rng[0], rng[2] + 1):
                        for c in range(rng[1], rng[3] + 1):
                            dv_cells[(r, c)] = dv_id
        req_fills, opt_fills = INPUT_FILLS.get(fid, (set(), set()))
        input_sheet = name.startswith("入力シート")
        by_col = collections.defaultdict(dict)       # col -> row -> (role, t, v, fill, numfmt)
        text = {}                                     # (row, col) -> label text (locked strings)
        fcols = collections.defaultdict(lambda: [0, set(), 0, 10**9, 0])
        present = set()
        for row, col, t, v, f, si, xf in db.execute("SELECT row, col, t, v, f, si, xf FROM cells WHERE sheet_id=?", (sid,)):
            locked, fill, numfmt = styles.get(xf, (1, None, None))
            if t != "z":
                present.add((row, col))
            if t == "f":
                rec = fcols[col]
                rec[0] += 1
                if si is not None:
                    rec[1].add(si)
                else:
                    rec[2] += 1
                rec[3] = min(rec[3], row); rec[4] = max(rec[4], row)
                continue
            blank = t == "z" or (t == "s" and not (v or "").strip())
            marked = (input_sheet and row >= 3 and (fill in req_fills or fill in opt_fills)
                      and not (t == "s" and (v or "").strip() in LEGEND))
            if blank:
                if locked and (row, col) not in dv_cells and not marked:
                    continue
                role = "I"
                t = "z"
            elif not locked or marked:
                role = "I"
            elif t == "s":
                role = "T"
                text[(row, col)] = v.strip()
            else:
                role = "C"
            by_col[col][row] = (role, t, v, fill, numfmt)
        # validated cells that have no cell element: editable blanks when they lie inside the used area of the
        # sheet; validation ranges far outside it (wrap-around remnants of an older file format) are only counted
        used = [k for k in present]
        if used:
            ur1, ur2 = min(r for r, _ in used), max(r for r, _ in used)
            uc1, uc2 = min(c for _, c in used), max(c for _, c in used)
        outside = collections.Counter()
        for (row, col), dv_id in dv_cells.items():
            if (row, col) in present:
                continue
            if used and ur1 <= row <= ur2 and uc1 <= col <= uc2:
                if row not in by_col[col]:
                    by_col[col][row] = ("I", "z", None, None, None)
            else:
                outside[dv_id] += 1
        for dv_id, n_out in outside.items():
            db.execute("INSERT INTO dv_outside VALUES (?,?,?)", (sid, dv_id, n_out))
        out = []
        label_count = 0
        td_cells = set()
        # text columns: runs of >= 6 strings with one fill
        for col, rows in by_col.items():
            trows = sorted(r for r, x in rows.items() if x[0] == "T")
            for a, b in runs_of(trows):
                seg_start = a
                for r in range(a, b + 2):
                    if r > b or rows[r][3] != rows[seg_start][3]:
                        if r - seg_start >= 6:
                            vals = [rows[k][2] for k in range(seg_start, r)]
                            for k in range(seg_start, r):
                                td_cells.add((k, col))
                            out.append(dict(role="TD", col=col, runs=[(seg_start, r - 1)], cells=[rows[k] for k in range(seg_start, r)], vals=vals))
                        seg_start = r
        def label_at(r, c):
            if (r, c) in td_cells:
                return None
            if (r, c) in text:
                return text[(r, c)]
            a = anchor.get((r, c))
            if a and a != (r, c) and a in text and a not in td_cells:
                return text[a]
            return None
        def header_for(col, row):
            found = []
            for r in range(row - 1, max(0, row - 16), -1):
                s = label_at(r, col)
                if s and (not found or s != found[-1]):
                    found.append(s)
                    if len(found) == 3:
                        break
            return " / ".join(x[:40] for x in reversed(found))
        def left_for(col, row):
            for c in range(col - 1, max(0, col - 14), -1):
                s = label_at(row, c)
                if s:
                    return s[:60]
            return ""
        def unit_for(col, row):
            for c in (col + 1, col + 2):
                s = label_at(row, c)
                if s and len(s) <= 14:
                    return s
            return ""
        # editable cells and constants: 4-connected blocks; a tall narrow block is a set of table columns,
        # anything else (single cell, row of cells, wide matrix) is one region
        for role in ("I", "C"):
            todo = {(r, c) for c, rows in by_col.items() for r, x in rows.items() if x[0] == role}
            table_cols = collections.defaultdict(list)        # col -> rows that belong to table columns
            while todo:
                start = todo.pop()
                comp, stack = [start], [start]
                while stack:
                    r, c = stack.pop()
                    for nb in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                        if nb in todo:
                            todo.discard(nb); comp.append(nb); stack.append(nb)
                r1, r2 = min(r for r, _ in comp), max(r for r, _ in comp)
                c1, c2 = min(c for _, c in comp), max(c for _, c in comp)
                if r2 - r1 + 1 >= 3 and c2 - c1 + 1 <= 40:
                    for r, c in comp:
                        table_cols[c].append(r)
                else:
                    comp.sort()
                    out.append(dict(role=role, col=c1, col2=c2, runs=[(r1, r2)], header=header_for(c1, r1), left=left_for(c1, r1),
                                    unit=unit_for(c2, r1), cells=[by_col[c][r] for r, c in comp], box=True))
            for col, rr in table_cols.items():
                groups = collections.OrderedDict()
                for run in runs_of(sorted(rr)):
                    groups.setdefault(header_for(col, run[0]), []).append(run)
                for head, rs in groups.items():
                    out.append(dict(role=role, col=col, col2=col, runs=rs, header=head, left=left_for(col, rs[0][0]) if sum(b - a + 1 for a, b in rs) < 3 else "",
                                    unit=unit_for(col, rs[0][0]), cells=[by_col[col][k] for a, b in rs for k in range(a, b + 1)]))
        for item in out:
            cells = item["cells"]
            nums = []
            for x in cells:
                if x[1] == "n":
                    try:
                        nums.append(float(x[2]))
                    except (TypeError, ValueError):
                        pass
            vals = [x[2] for x in cells if x[1] != "z"]
            fills = collections.Counter(str(x[3]) for x in cells)
            fmts = collections.Counter(str(x[4]) for x in cells)
            seq = int(len(nums) >= 3 and len(nums) == len(cells) and all(abs((nums[i + 1] - nums[i]) - 1) < 1e-9 for i in range(len(nums) - 1)))
            runs = item["runs"]
            dv = None
            if item["role"] == "I":
                ids = collections.Counter(dv_cells.get((r, c)) for a, b in runs for r in range(a, b + 1)
                                          for c in range(item["col"], item.get("col2", item["col"]) + 1))
                ids.pop(None, None)
                dv = ids.most_common(1)[0][0] if ids and ids.most_common(1)[0][1] * 2 >= len(cells) else None   # the list must cover the region
            if item["role"] == "TD":
                item["header"], item["left"], item["unit"] = header_for(item["col"], runs[0][0]), "", ""
            db.execute("INSERT INTO regions (sheet_id, role, col1, col2, row_min, row_max, ranges, n, n_blank, n_num, n_str, n_bool, "
                       "n_distinct, vmin, vmax, uniform, seq, n_int, fills, numfmt, header, left_label, unit, dv_id, sample, n_req, vhash) "
                       "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (sid, item["role"], item["col"], item.get("col2", item["col"]), runs[0][0], runs[-1][1],
                        ("%s%d:%s%d" % (L(item["col"]), runs[0][0], L(item["col2"]), runs[0][1]) if item.get("box") and len(cells) > 1
                         else ranges_text(item["col"], runs))[:4000],
                        len(cells), sum(1 for x in cells if x[1] == "z"), sum(1 for x in cells if x[1] == "n"),
                        sum(1 for x in cells if x[1] == "s"), sum(1 for x in cells if x[1] == "b"), len(set(vals)),
                        min(nums) if nums else None, max(nums) if nums else None, int(len(set(vals)) == 1 and len(vals) > 1), seq,
                        sum(1 for v in nums if v == int(v)), json.dumps(dict(fills.most_common(4))), fmts.most_common(1)[0][0],
                        item.get("header", ""), item.get("left", ""), item.get("unit", ""), dv,
                        json.dumps([str(v)[:30] for v in vals[:3]], ensure_ascii=False),
                        sum(1 for x in cells if x[3] in req_fills) if input_sheet else 0,
                        hashlib.sha1(repr([(x[1], x[2]) for x in cells]).encode("utf-8")).hexdigest()[:16]))
        # scattered labels: one aggregate record
        n_labels = sum(1 for k in text if k not in td_cells)
        if n_labels:
            db.execute("INSERT INTO regions (sheet_id, role, n, n_str) VALUES (?,?,?,?)", (sid, "L", n_labels, n_labels))
        # formulas: merge adjacent columns with the same extent
        block = None
        for col in sorted(fcols):
            n, sis, single, rmin, rmax = fcols[col]
            key = (n, rmin, rmax)
            if block and block["key"] == key and block["col2"] == col - 1:
                block["col2"] = col; block["n"] += n; block["pat"] += len(sis) + single
            else:
                if block:
                    db.execute("INSERT INTO regions (sheet_id, role, col1, col2, row_min, row_max, n, n_patterns) VALUES (?,?,?,?,?,?,?,?)",
                               (sid, "F", block["col1"], block["col2"], block["key"][1], block["key"][2], block["n"], block["pat"]))
                block = dict(key=key, col1=col, col2=col, n=n, pat=len(sis) + single)
        if block:
            db.execute("INSERT INTO regions (sheet_id, role, col1, col2, row_min, row_max, n, n_patterns) VALUES (?,?,?,?,?,?,?,?)",
                       (sid, "F", block["col1"], block["col2"], block["key"][1], block["key"][2], block["n"], block["pat"]))
        db.commit()
    db.execute("CREATE INDEX IF NOT EXISTS regions_sheet ON regions(sheet_id, role)")
    db.commit()
    print("regions", db.execute("SELECT role, COUNT(*), SUM(n) FROM regions GROUP BY role").fetchall(), "seconds", round(time.time() - t0))
    # coverage: every scanned non-blank cell and every editable blank belongs to exactly one region
    scanned = db.execute("SELECT SUM(t='f'), SUM(t IN ('n','b','e')), SUM(t='s' AND TRIM(v)<>''), COUNT(*) FROM cells").fetchone()
    print("scanned formulas / numbers+bool / non-empty strings / all rows:", scanned)

if __name__ == "__main__":
    main(sys.argv[1])
