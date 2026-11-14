"""Input cells of every workbook (from the input inventory of chapter 13) with their kind, unit, original
value and the options of their input rule. Private output (cell addresses and original values)."""
import sys, os, csv, re, pickle, sqlite3, collections
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "jcat_tools"))
import fx
from store import Store, KEY_SHIFT, Err

scan, inv, out = sys.argv[1:4]
st = Store(scan)
db = sqlite3.connect(scan)
FILE2BOOK = {"1_": "SIM", "2_": "STD", "3_": "CLS", "4_": "SUM", "5_": "DET"}
sid2 = {sh.sid: sh for sh in st.sheets.values()}


def cells_of(rng):
    out = []
    for part in rng.replace(",", " ").split():
        try:
            ps = fx._parts(part.replace("$", ""))
        except Exception:
            continue
        if any(p[1] is None or p[3] is None for p in ps):
            continue
        if len(ps) == 1:
            ca, c, ra, r = ps[0]
            out.append((r, c))
        else:
            (ca, c1, ra, r1), (cb, c2, rb, r2) = ps[0], ps[-1]
            for r in range(min(r1, r2), max(r1, r2) + 1):
                for c in range(min(c1, c2), max(c1, c2) + 1):
                    out.append((r, c))
    return out


# merged areas: only the top-left cell holds a value
merged_hidden = collections.defaultdict(set)
for sid, ref in db.execute("SELECT sheet_id, ref FROM merges"):
    cs = cells_of(ref)
    for (r, c) in cs[1:]:
        merged_hidden[sid].add((r, c))
# validation lists
valid = collections.defaultdict(dict)
for sid, sqref, typ, f1 in db.execute("SELECT sheet_id, sqref, type, formula1 FROM validations"):
    if typ != "list" or f1 is None:
        continue
    sh = sid2.get(sid)
    if sh is None:
        continue
    opts = None
    if f1.startswith('"'):
        opts = [x.strip() for x in f1.strip('"').split(",")]
    else:
        ref = f1.lstrip("=")
        if not re.search(r"[!:$A-Z]", ref) or re.fullmatch(r"[A-Za-z_][\w.]*", ref):
            r2 = st.resolve_name(sh.book, sh.name, ref)
            if r2 is None:
                continue
            ref = r2
        if "!" in ref:
            sname, body = ref.rsplit("!", 1)
            tsh = st.sheet(sh.book, fx.norm_sheet(sname))
        else:
            tsh, body = sh, ref
        if tsh is None or "#REF" in body:
            continue
        vals = []
        for (r, c) in cells_of(body):
            v = tsh.values.get(r * KEY_SHIFT + c)
            if v is not None and not isinstance(v, Err) and v != "":
                vals.append(v)
        opts = vals
    if not opts:
        continue
    for (r, c) in cells_of(sqref):
        valid[sid][(r, c)] = opts

spec = collections.defaultdict(list)
seen = set()
for row in csv.DictReader(open(inv, encoding="utf-8-sig")):
    if row["入力データの種類"] not in ("利用者が直接入力する値", "選択式の入力項目", "入力可能な空欄"):
        continue
    book = FILE2BOOK[row["元ファイル"][:2]]
    sh = st.sheet(book, row["シート"])
    if sh is None or not row["セル位置"]:
        continue
    for (r, c) in cells_of(row["セル位置"]):
        key = r * KEY_SHIFT + c
        if (sh.sid, key) in seen or (r, c) in merged_hidden[sh.sid] or sh.formula.get(key) is not None or key in sh.formula:
            continue
        seen.add((sh.sid, key))
        v = sh.values.get(key)
        spec[book].append(dict(sheet=sh.name, sid=sh.sid, row=r, col=c, item=row["項目名"], detail=row["詳細分類"], unit=row["単位"],
                               dtype=row["データ型"], kind=row["入力データの種類"], value=v, options=valid[sh.sid].get((r, c))))
pickle.dump(dict(spec), open(out, "wb"))
for b, items in spec.items():
    c = collections.Counter(("choice" if it["options"] else ("num" if isinstance(it["value"], float) else ("blank" if it["value"] is None else "text"))) for it in items)
    print(b, len(items), dict(c))
