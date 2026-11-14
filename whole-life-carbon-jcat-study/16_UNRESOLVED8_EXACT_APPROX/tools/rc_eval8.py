"""Random building cases (LibreOffice recalculation, regenerated with the seeds of the conversion study) for
the 8 equations, methods A and B: converted value vs LibreOffice's value and vs the reference evaluator on
the same case values. Units: every (pattern, sheet) group of the book, up to MAX_INST seeded instances.
Usage: rc_eval8.py <book> <n_cases> <cases_dir> <out.pkl>"""
import os, sys, time, collections, pickle, traceback, random, hashlib
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
S = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(S, "conv")); sys.path.insert(0, os.path.join(S, "jcat_tools"))
import warnings; warnings.simplefilter("ignore")
import numpy as np
import fx, excel_ref as X, compile2 as K, run_compile as RC, rc_eval as RE, verify_boundary as VBM
from overlay import OverlayStore
from store import KEY_SHIFT
from validate_ref import same as same_tol
from synth import same            # exact comparison
import exact8 as E8
import crref
from run8 import TARGETS

MAX_INST = 200


def main():
    book, n_cases, cdir, outp = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
    t0 = time.time()
    RE.setup_book(os.path.join(S, "jcat_work", "scan.sqlite3"), os.path.join(S, "conv", "instances.pkl"), book)
    units = []
    for eq, pids in TARGETS.items():
        for pid in pids:
            p = RC.DATA["patterns"][pid]
            for (bk, sheet), arr in RC.DATA["instances"][pid].items():
                if bk != book:
                    continue
                r0 = VBM.rng_for(pid, bk, sheet, "rc8")
                idx = sorted(r0.sample(range(len(arr)), min(MAX_INST, len(arr))))
                sub = arr[idx]
                tree = X.prepare(fx.Parser(fx.tokenize(p["text"])).parse(), p["row"], RC.col_num(p["col"]), RC.STORE, bk, sheet)
                built = {}
                for mode in ("A", "B"):
                    b = E8.Exact8Final(RC.STORE, RC.SD, RC.CACHE, bk, sheet, sub[:, 0], sub[:, 1])
                    b.improve = True
                    b.mode8 = mode
                    v = b.finish(b.ev(tree))
                    b.program()
                    built[mode] = (b, v)
                sh = RC.STORE.sheet(bk, sheet)
                prec = collections.defaultdict(set)
                whole = set()
                for rec in built["A"][0].recipes:
                    if rec[0] in ("G", "chars"):
                        for r_, c_ in zip(np.asarray(rec[3]).tolist(), np.asarray(rec[4]).tolist()):
                            prec[rec[2].sid].add(int(r_) * KEY_SHIFT + int(c_))
                    elif rec[0] == "T":
                        for r_, c_ in zip(np.asarray(rec[4]).tolist(), np.asarray(rec[5]).tolist()):
                            prec[rec[3].sid].add(int(r_) * KEY_SHIFT + int(c_))
                    elif rec[0] == "W":
                        whole.add(rec[2].sid)
                units.append(dict(eq=eq, pid=pid, sheet=sheet, sid=sh.sid, sub=sub, tree=tree, built=built,
                                  prec={k: np.array(sorted(v), dtype=np.int64) for k, v in prec.items()}, whole=whole,
                                  own=np.array([int(a) * KEY_SHIFT + int(b_) for a, b_ in sub.tolist()], dtype=np.int64)))
    print(book, "units", len(units), round(time.time() - t0), "s", flush=True)
    stats = {}
    examples = collections.defaultdict(list)
    done = 0
    while done < n_cases:
        path = os.path.join(cdir, "%s_%05d.pkl" % (book, done))
        if not os.path.exists(path):
            time.sleep(2.0)
            continue
        c = pickle.load(open(path, "rb"))
        changes = collections.defaultdict(dict)
        for d in (c["inputs"], c["formula_changes"]):
            for sid, kv in d.items():
                changes[sid].update(kv)
        changes = dict(changes)
        ck = {sid: np.array(sorted(v), dtype=np.int64) for sid, v in changes.items()}
        sd = K.StrDictExt(RC.SD, {v for d in changes.values() for v in d.values() if isinstance(v, str)})
        src = K.CaseSource(RC.CACHE, changes, sd)
        ost = OverlayStore(RC.STORE, changes)
        for u in units:
            hit = np.isin(u["own"], ck.get(u["sid"], np.zeros(0, dtype=np.int64))).any() or any(sid in ck for sid in u["whole"])
            if not hit:
                for sid, a in u["prec"].items():
                    c_ = ck.get(sid)
                    if c_ is not None and np.isin(a, c_).any():
                        hit = True
                        break
            rec = stats.setdefault((u["eq"], u["pid"]), {"A": collections.Counter(), "B": collections.Counter(), "cases_hit": 0, "cases": 0})
            rec["cases"] += 1
            if not hit:
                continue
            rec["cases_hit"] += 1
            sh = RC.STORE.sheet(book, u["sheet"])
            ch_own = changes.get(sh.sid, {})
            want_lo = []
            for a, b_ in u["sub"].tolist():
                key = int(a) * KEY_SHIFT + int(b_)
                want_lo.append(ch_own[key] if key in ch_own else sh.values.get(key))
            refs, refs_cr = [], []
            for a, b_ in u["sub"].tolist():
                X._INDEX_CACHE.clear(); X._SUMIF_CACHE.clear()
                try:
                    refs.append(X.evaluate(u["tree"], ost, book, u["sheet"], int(a), int(b_)))
                except Exception as e:
                    refs.append("EXC:%s" % type(e).__name__)
                X._INDEX_CACHE.clear(); X._SUMIF_CACHE.clear()
                with crref.correctly_rounded():
                    try:
                        refs_cr.append(X.evaluate(u["tree"], ost, book, u["sheet"], int(a), int(b_)))
                    except Exception as e:
                        refs_cr.append("EXC:%s" % type(e).__name__)
            for mode in ("A", "B"):
                b, v = u["built"][mode]
                cnt = rec[mode]
                t1 = time.time()
                got, _, _ = b.run(v, src, sd)
                cnt["run_ms"] += 1000 * (time.time() - t1)
                for (a, b_), g, wl, wr, wc in zip(u["sub"].tolist(), got, want_lo, refs, refs_cr):
                    if g != "<missing>":
                        cnt["ok_ref_cr"] += same(g, wc)[0]
                    cnt["n"] += 1
                    wl = 0.0 if wl is None else wl
                    if g == "<missing>":
                        cnt["missing"] += 1
                        ok_lo = ok_ref = False
                    else:
                        ok_lo, ok_ref = same(g, wl)[0], same(g, wr)[0]
                    cnt["ok_lo"] += ok_lo; cnt["ok_ref"] += ok_ref; cnt["ref_eq_lo"] += same(wr, wl)[0]
                    if g != "<missing>":
                        cnt["ok_lo_tol"] += same_tol(g, wl)[0]; cnt["ok_ref_tol"] += same_tol(g, wr)[0]
                    cnt["ref_eq_lo_tol"] += same_tol(wr, wl)[0]
                    if not (ok_lo and ok_ref):
                        kind = ("conv=ref, LO differs" if ok_ref else "conv=LO, ref differs" if ok_lo else
                                "missing" if g == "<missing>" else "conv differs from both")
                        cnt[kind] += 1
                        if len(examples[(u["eq"], mode)]) < 8:
                            examples[(u["eq"], mode)].append((done, kind, u["sheet"], a, b_, repr(g)[:50], repr(wl)[:50], repr(wr)[:50]))
        X._INDEX_CACHE.clear(); X._SUMIF_CACHE.clear()
        done += 1
        if done % 10 == 0 or done == n_cases:
            print(book, "cases", done, {k: (dict(v["A"]), v["cases_hit"]) for k, v in stats.items()}, round(time.time() - t0), "s", flush=True)
            pickle.dump(dict(book=book, cases=done, stats=stats, examples=dict(examples), max_inst=MAX_INST), open(outp, "wb"))
    pickle.dump(dict(book=book, cases=done, stats=stats, examples=dict(examples), max_inst=MAX_INST), open(outp, "wb"))


if __name__ == "__main__":
    main()
