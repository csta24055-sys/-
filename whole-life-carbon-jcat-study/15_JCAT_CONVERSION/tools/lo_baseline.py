"""LibreOffice recalculation at the original inputs vs Excel's cached values, every formula cell."""
import sys, os, pickle, time, collections
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "jcat_tools"))
from store import Store, KEY_SHIFT
from validate_ref import same
import lo_engine

FILES = {"SIM": "1_J-CAT_Software_Simplified Calculation_v2.3.xlsx", "STD": "2_J-CAT_Software_Standard Calculation_v2.3.2.xlsx",
         "SUM": "4_J-CAT_Summary Table_v2.0.xlsx", "DET": "5_J-CAT_Software_Detailed Calculation_v2.3.xlsm"}
if __name__ == "__main__":
    scan, inst, books_dir, out, port = sys.argv[1:6]
    store = Store(scan)
    data = pickle.load(open(inst, "rb"))
    pos = collections.defaultdict(list)
    for pid, d in data["instances"].items():
        for (book, sheet), arr in d.items():
            pos[(book, sheet)].extend(map(tuple, arr.tolist()))
    res = {"values": {}, "cmp": {}}
    for book in sys.argv[6:] or ["SIM", "STD", "SUM", "DET"]:
        t = time.time()
        lo = lo_engine.LO(int(port), os.path.join(os.path.dirname(out), "lo_profile_%s" % port))
        lo.load(os.path.join(books_dir, FILES[book]))
        tl = time.time() - t
        lo.recalc()
        tc = time.time() - t - tl
        cnt = collections.Counter()
        ex = []
        for (b, sheet), ps in pos.items():
            if b != book:
                continue
            vals = lo.read_sheet(sheet, ps)
            res["values"][(b, sheet)] = vals
            sh = store.sheet(b, sheet)
            for (r, c), v in vals.items():
                want = sh.values.get(r * KEY_SHIFT + c)
                eq, kind, rel = same(v, want)
                cnt["n"] += 1
                cnt["ok" if eq else "bad"] += 1
                if not eq:
                    cnt["bad:" + kind] += 1
                    if len(ex) < 30:
                        ex.append((b, sheet, r, c, repr(v)[:60], repr(want)[:60]))
        lo.close()
        res["cmp"][book] = (dict(cnt), ex, tl, tc)
        print(book, dict(cnt), "load %.0f s calc %.0f s" % (tl, tc), flush=True)
        for e in ex[:12]:
            print("   ", e, flush=True)
    pickle.dump(res, open(out, "wb"))
