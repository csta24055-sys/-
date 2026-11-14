"""Reference evaluator vs Excel's cached values, every formula cell. Usage: validate_ref.py <scan> <instances.pkl> <out.pkl> [n_proc]"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "jcat_tools"))
import collections, math, multiprocessing as mp, os, pickle, sys, time, traceback
import fx
import excel_ref as X
from store import Store, Err, KEY_SHIFT

STORE = DATA = None


def same(a, b):
    """(equal, kind of difference, relative difference)."""
    if isinstance(b, Err) or isinstance(a, Err):
        return (isinstance(a, Err) and isinstance(b, Err) and a.code == b.code), "error", None
    if isinstance(b, str) or isinstance(a, str):
        return (a == b), "text", None
    if isinstance(a, bool) or isinstance(b, bool):
        return (a == b), "bool", None
    if a is None or b is None:
        return (a == b), "blank", None
    if a == b:
        return True, "num", 0.0
    d = abs(a - b)
    rel = d / max(abs(a), abs(b))
    return (rel <= 1e-9 or d <= 1e-12), "num", rel


def work(pids):
    out = {}
    for pid in pids:
        p = DATA["patterns"][pid]
        rec = dict(n=0, ok=0, bad=0, max_rel=0.0, examples=[], unsupported=None, kinds=collections.Counter())
        try:
            toks = fx.tokenize(p["text"])
            col0 = 0
            for ch in p["col"]:
                col0 = col0 * 26 + ord(ch) - 64
            for (book, sheet), arr in DATA["instances"][pid].items():
                tree = X.prepare(fx.Parser(toks).parse(), p["row"], col0, STORE, book, sheet)
                sh = STORE.sheet(book, sheet)
                for r, c in arr:
                    rec["n"] += 1
                    want = sh.values.get(int(r) * KEY_SHIFT + int(c))
                    try:
                        got = X.evaluate(tree, STORE, book, sheet, int(r), int(c))
                    except X.Unsupported as e:
                        raise
                    except Exception as e:
                        got = "EXC:%s:%s" % (type(e).__name__, e)
                    eq, kind, rel = same(got, want)
                    if rel is not None and rel > rec["max_rel"] and eq:
                        rec["max_rel"] = rel
                    if eq:
                        rec["ok"] += 1
                    else:
                        rec["bad"] += 1
                        rec["kinds"][kind] += 1
                        if len(rec["examples"]) < 5:
                            rec["examples"].append((book, sheet, int(r), int(c), repr(got)[:80], repr(want)[:80]))
        except X.Unsupported as e:
            rec["unsupported"] = str(e)
        except Exception as e:
            rec["unsupported"] = "EXC " + traceback.format_exc()[-300:]
        out[pid] = rec
    return out


if __name__ == "__main__":
    t0 = time.time()
    STORE = Store(sys.argv[1])
    DATA = pickle.load(open(sys.argv[2], "rb"))
    print("loaded", round(time.time() - t0), "s", flush=True)
    pids = sorted(DATA["patterns"], key=lambda p: -DATA["patterns"][p]["n"])
    nproc = int(sys.argv[4]) if len(sys.argv) > 4 else 4
    chunks = [pids[i::nproc * 8] for i in range(nproc * 8)]
    res = {}
    with mp.get_context("fork").Pool(nproc) as pool:
        for part in pool.imap_unordered(work, chunks):
            res.update(part)
            print("done", len(res), round(time.time() - t0), "s", flush=True)
    pickle.dump(res, open(sys.argv[3], "wb"))
    tot = collections.Counter()
    for r in res.values():
        tot["n"] += r["n"]; tot["ok"] += r["ok"]; tot["bad"] += r["bad"]; tot["unsupported"] += r["unsupported"] is not None
        tot["bad_patterns"] += r["bad"] > 0
    print(dict(tot), "seconds", round(time.time() - t0))
