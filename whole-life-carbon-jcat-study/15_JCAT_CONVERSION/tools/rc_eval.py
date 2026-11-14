"""Evaluator of the random cases written by rc_producer.py (one process per book).

Every (pattern, sheet) unit of the book is compiled ONCE on a seeded sample of S instances (improved
method; the base method is compiled too when its program differs). For a case, a unit is evaluated when
it is in the case's seeded unit subset (fraction F) and a cell it reads (or the cell itself) changed.
Expected values: LibreOffice's value of the cell in that case; the reference evaluator is run on the
same case values as a second opinion (three-way comparison).

Usage: rc_eval.py <scan> <instances.pkl> <book> <n_cases> <cases_dir> <fraction> <out.pkl>"""
import sys, os
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "jcat_tools"))
import collections, json, pickle, time, traceback
import numpy as np
import fx
import excel_ref as X
import compile2 as K
import run_compile as RC
import random_cases as R
from overlay import OverlayStore
from store import Store, KEY_SHIFT, Err
from validate_ref import same


def setup_book(scan, inst, book):
    RC.STORE = Store(scan, books=(book,))
    RC.DATA = pickle.load(open(inst, "rb"))
    RC.SD = K.StrDict(RC.all_strings(RC.STORE, RC.DATA))
    RC.CACHE = K.SheetCache(RC.SD)


def build(book):
    units = []
    for pid, inst in RC.DATA["instances"].items():
        p = RC.DATA["patterns"][pid]
        for (bk, sheet), arr in inst.items():
            if bk != book:
                continue
            ast = fx.Parser(fx.tokenize(p["text"])).parse()
            r0 = R.rng_for(pid, bk, sheet, "sample")
            idx = sorted(r0.sample(range(len(arr)), min(R.S_INST, len(arr))))
            sub = arr[idx]
            tree = X.prepare(ast, p["row"], RC.col_num(p["col"]), RC.STORE, bk, sheet)
            res = {}
            for improve in (True, False):
                try:
                    b = K.Builder(RC.STORE, RC.SD, RC.CACHE, bk, sheet, sub[:, 0], sub[:, 1])
                    b.improve = improve
                    v = b.finish(b.ev(tree))
                    b.program()
                    res[improve] = (b, v)
                except K.Unsupported as e:
                    res[improve] = (None, str(e))
            bi, vi = res[True]
            bb, vb = res[False]
            if bb is not None and bi is not None and json.dumps(bb.steps, sort_keys=True) == json.dumps(bi.steps, sort_keys=True):
                bb, vb = None, "same program as the improved method"
            units.append(R.Unit(pid, bk, sheet, sub, tree, bb, vb, bi, vi))
    return units


def main():
    scan, inst, book, n_cases, cdir, frac, outp = sys.argv[1:8]
    n_cases, frac = int(n_cases), float(frac)
    start = int(sys.argv[8]) if len(sys.argv) > 8 else 0
    t0 = time.time()
    setup_book(scan, inst, book)
    units = build(book)
    print("units", len(units), "with a distinct base program", sum(u.bb is not None for u in units), round(time.time() - t0), "s", flush=True)
    stats, examples, case_log = {}, collections.defaultdict(list), []
    done = start
    while done < n_cases:
        path = os.path.join(cdir, "%s_%05d.pkl" % (book, done))
        if not os.path.exists(path):
            time.sleep(1.0)
            continue
        tc = time.time()
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
        X._INDEX_CACHE.clear(); X._SUMIF_CACHE.clear()
        rsel = R.rng_for(book, done, "units")
        n_eval = collections.Counter()
        for u in units:
            pick = rsel.random()
            if pick >= frac:
                continue
            hit = np.isin(u.own, ck.get(u.own_sid, np.zeros(0, dtype=np.int64))).any() or any(sid in ck for sid in u.whole)
            if not hit:
                for sid, a in u.prec.items():
                    c_ = ck.get(sid)
                    if c_ is not None and np.isin(a, c_, assume_unique=True).any():
                        hit = True
                        break
            if not hit:
                continue
            sh = RC.STORE.sheet(book, u.sheet)
            ch_own = changes.get(sh.sid, {})
            want_lo = []
            for a, b_ in u.sub.tolist():
                key = int(a) * KEY_SHIFT + int(b_)
                want_lo.append(ch_own[key] if key in ch_own else sh.values.get(key))
            refs = []
            for a, b_ in u.sub.tolist():
                try:
                    refs.append(X.evaluate(u.tree, ost, book, u.sheet, int(a), int(b_)))
                except Exception as e:
                    refs.append("EXC:%s" % type(e).__name__)
            rec = stats.setdefault(u.pid, {"improved": collections.Counter(), "base": collections.Counter()})
            for method, b, v in (("improved", u.bi, u.vi), ("base", u.bb, u.vb)):
                if method == "base" and (b is None or pick >= frac / 2):
                    continue
                cnt = rec[method]
                if b is None:
                    cnt["unsupported"] += len(want_lo)
                    continue
                n_eval[method] += 1
                try:
                    got, _, _ = b.run(v, src, sd)
                except Exception:
                    cnt["run_error"] += len(want_lo)
                    if len(examples[u.pid]) < 6:
                        examples[u.pid].append((done, method, "run_error", traceback.format_exc()[-300:]))
                    continue
                for (a, b_), g, wl, wr in zip(u.sub.tolist(), got, want_lo, refs):
                    cnt["n"] += 1
                    wl = 0.0 if wl is None else wl
                    if g == "<missing>":
                        cnt["missing"] += 1
                        ok_lo = ok_ref = False
                    else:
                        ok_lo, ok_ref = same(g, wl)[0], same(g, wr)[0]
                    ref_lo = same(wr, wl)[0]
                    cnt["ok_lo"] += ok_lo
                    cnt["ok_ref"] += ok_ref
                    cnt["ref_eq_lo"] += ref_lo
                    if not (ok_lo and ok_ref):
                        kind = ("conv=ref, LO differs" if ok_ref else "conv=LO, ref differs" if ok_lo else
                                "missing" if g == "<missing>" else "conv differs from both")
                        cnt[kind] += 1
                        if len(examples[u.pid]) < 8:
                            examples[u.pid].append((done, method, kind, u.sheet, a, b_, repr(g)[:50], repr(wl)[:50], repr(wr)[:50]))
        X._INDEX_CACHE.clear(); X._SUMIF_CACHE.clear()
        case_log.append(dict(case=done, seed_parts=c["seed_parts"], inputs_changed=sum(len(v) for v in c["inputs"].values()),
                             cells_changed=sum(len(v) for v in c["formula_changes"].values()), units_improved=n_eval["improved"],
                             units_base=n_eval["base"], lo_seconds=c["t_total"], eval_seconds=round(time.time() - tc, 2),
                             inputs=c["inputs"]))
        os.remove(path)
        done += 1
        if done % 10 == 0 or done == n_cases:
            tot = collections.Counter()
            for r_ in stats.values():
                for k, v in r_["improved"].items():
                    tot[k] += v
            print("cases", done, dict(tot), "eval s", case_log[-1]["eval_seconds"], round(time.time() - t0), "s", flush=True)
            pickle.dump(dict(book=book, seed=R.SEED, S=R.S_INST, fraction=frac, cases=case_log, stats=stats, examples=dict(examples)),
                        open(outp, "wb"))


if __name__ == "__main__":
    main()
