"""Converted form (masked sum-product + knot spectra, engine msp.py unchanged) vs Excel's cached values,
every formula cell. Usage: run_compile.py <scan> <instances.pkl> <out.pkl> [n_proc] [pattern ids...]"""
import sys, os
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "jcat_tools"))
import collections, multiprocessing as mp, pickle, time, traceback
import numpy as np
import fx
import excel_ref as X
import compile2 as K
from tstudy import msp
from store import Store, Err, KEY_SHIFT
from validate_ref import same

STORE = DATA = SD = CACHE = None
IMPROVE = bool(int(os.environ.get("IMPROVE", "0")))


def all_strings(store, data):
    out = set()
    for sh in store.sheets.values():
        for v in sh.values.values():
            if isinstance(v, str):
                out.add(v)
    for p in data["patterns"].values():
        for t in fx.tokenize(p["text"]):
            if t[0] == "str":
                out.add(t[1][1:-1].replace('""', '"'))
    return out


def col_num(letters):
    c = 0
    for ch in letters:
        c = c * 26 + ord(ch) - 64
    return c


def run_pattern(pid, keep_program=False, values_of=None):
    """Compile and run one pattern on all its instances. ``values_of``: alternative expected values
    (dict (book, sheet) -> {key: value}); default = Excel's cached values."""
    p = DATA["patterns"][pid]
    rec = dict(n=0, ok=0, bad=0, missing=0, max_rel=0.0, examples=[], unsupported=None, kinds=collections.Counter(),
               steps=0, notes=collections.Counter(), usage=collections.Counter(), groups=0)
    cache = CACHE
    programs = []
    try:
        ast = fx.Parser(fx.tokenize(p["text"])).parse()
        col0 = col_num(p["col"])
        for (book, sheet), arr in DATA["instances"][pid].items():
            tree = X.prepare(ast, p["row"], col0, STORE, book, sheet)
            sh = STORE.sheet(book, sheet)
            b = K.Builder(STORE, SD, cache, book, sheet, arr[:, 0], arr[:, 1])
            b.improve = IMPROVE
            v = b.finish(b.ev(tree))
            got, prog, eng = b.run(v)
            rec["groups"] += 1
            rec["steps"] += len(prog.steps)
            rec["notes"].update(b.notes)
            for u in msp.static_usage(prog).values():
                rec["usage"].update(u)
            if keep_program:
                programs.append((book, sheet, prog.spec, v.c))
            for (r, c), g in zip(arr.tolist(), got):
                rec["n"] += 1
                key = r * KEY_SHIFT + c
                want = (values_of[(book, sheet)] if values_of else sh.values).get(key)
                if g == "<missing>":
                    rec["missing"] += 1
                    rec["bad"] += 1
                    rec["kinds"]["missing"] += 1
                    if len(rec["examples"]) < 5:
                        rec["examples"].append((book, sheet, r, c, "<missing>", repr(want)[:80]))
                    continue
                eq, kind, rel = same(g, want)
                if rel is not None and eq and rel > rec["max_rel"]:
                    rec["max_rel"] = rel
                if eq:
                    rec["ok"] += 1
                else:
                    rec["bad"] += 1
                    rec["kinds"][kind] += 1
                    if len(rec["examples"]) < 5:
                        rec["examples"].append((book, sheet, r, c, repr(g)[:80], repr(want)[:80]))
    except K.Unsupported as e:
        rec["unsupported"] = str(e)
    except Exception:
        rec["unsupported"] = "EXC " + traceback.format_exc()[-600:]
    if keep_program:
        rec["programs"] = programs
    return rec


def work(pids):
    out = {}
    for pid in pids:
        out[pid] = run_pattern(pid)
    return out


def setup(scan, inst):
    global STORE, DATA, SD
    STORE = Store(scan)
    DATA = pickle.load(open(inst, "rb"))
    SD = K.StrDict(all_strings(STORE, DATA))
    global CACHE
    CACHE = K.SheetCache(SD)


if __name__ == "__main__":
    t0 = time.time()
    setup(sys.argv[1], sys.argv[2])
    print("loaded", round(time.time() - t0), "s", "strings", len(SD.code), flush=True)
    nproc = int(sys.argv[4]) if len(sys.argv) > 4 else 4
    pids = sys.argv[5:] or sorted(DATA["patterns"], key=lambda p: -DATA["patterns"][p]["n"])
    if len(pids) <= 8:
        res = work(pids)
    else:
        chunks = [pids[i::nproc * 8] for i in range(nproc * 8)]
        res = {}
        with mp.get_context("fork").Pool(nproc) as pool:
            for part in pool.imap_unordered(work, chunks):
                res.update(part)
                print("done", len(res), round(time.time() - t0), "s", flush=True)
    pickle.dump(res, open(sys.argv[3], "wb"))
    tot = collections.Counter()
    for r in res.values():
        tot["n"] += r["n"]; tot["ok"] += r["ok"]; tot["bad"] += r["bad"]; tot["missing"] += r["missing"]
        tot["unsupported_patterns"] += r["unsupported"] is not None
        tot["bad_patterns"] += r["bad"] > 0
    print(dict(tot), "seconds", round(time.time() - t0))
    if len(pids) <= 8:
        for pid, r in res.items():
            print(pid, {k: r[k] for k in ("n", "ok", "bad", "missing", "unsupported", "steps", "max_rel")}, r["examples"][:3])
