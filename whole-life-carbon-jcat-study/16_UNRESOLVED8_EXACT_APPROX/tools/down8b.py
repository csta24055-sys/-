"""Downstream impact with NON-TRIVIAL inputs (the baseline template has mostly empty quantities, so the
results of the numeric rules are 0 there). For every numeric equation: V variants of the precedent cells
(verify_boundary's generator, numeric kinds), the equation's cells get (i) the reference values, (ii) method A,
(iii) method B, (iv) reference +- 1 ulp; the consumer closure (down8) is re-evaluated by the reference
evaluator for each; consumer cells that differ from scenario (i) are counted (exactly; and whether the change
is proportional, <= 8 ulp, or discontinuous).
Usage: down8b.py <down8.pkl> <out.pkl> [n_variants]"""
import os, sys, time, collections, pickle, math
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import warnings; warnings.simplefilter("ignore")
import numpy as np
import down8 as DN
import fx, excel_ref as X, compile2 as K, run_compile as RC, verify_boundary as VBM
from overlay import OverlayStore
from store import KEY_SHIFT, Err
from synth import same
from run8 import TARGETS, builder

NUMERIC = ["EQ-0469", "EQ-0298", "EQ-0450", "EQ-0451", "EQ-0452", "EQ-0229"]
KINDS = ["real", "real", "int", "thresh", "half", "real", "lookup", "int"]


def main(dp, outp, nv):
    t0 = time.time()
    RC.setup(os.path.join(DN.S, "jcat_work", "scan.sqlite3"), os.path.join(DN.S, "conv", "instances.pkl"))
    idx = DN.build_index()
    trees = {(pid, sheet): tree for b, lst in idx.items() for pid, sheet, arr, tree, rl in lst}
    D = pickle.load(open(dp, "rb"))
    out = {}
    for eq in NUMERIC:
        closure = sorted(D[eq]["closure"].items(), key=lambda kv: kv[1])
        units = []
        for pid in TARGETS[eq]:
            p = RC.DATA["patterns"][pid]
            ast = fx.Parser(fx.tokenize(p["text"])).parse()
            for (book, sheet), arr in RC.DATA["instances"][pid].items():
                tree = X.prepare(ast, p["row"], RC.col_num(p["col"]), RC.STORE, book, sheet)
                bs = {}
                for mode in ("A", "B"):
                    b = builder(book, sheet, arr[:, 0], arr[:, 1], mode)
                    v = b.finish(b.ev(tree))
                    b.program()
                    bs[mode] = (b, v)
                singles, pool = VBM.precedents(bs["A"][0])
                units.append(dict(pid=pid, book=book, sheet=sheet, arr=arr, tree=tree, bs=bs, singles=singles, pool=pool,
                                  consts=VBM.constants(tree, [])))
        cnt = {s: collections.Counter() for s in ("A", "B", "ulp+", "ulp-")}
        ex = collections.defaultdict(list)
        for vi in range(nv):
            changes = collections.defaultdict(dict)
            kind = KINDS[vi % len(KINDS)]
            for u in units:
                r = VBM.rng_for(u["pid"], u["book"], u["sheet"], "down", vi)
                for sh_, key in u["singles"]:
                    changes[sh_.sid][key] = VBM.gen_value(kind, r, u["consts"], u["pool"])
            new_texts = {v for d in changes.values() for v in d.values() if isinstance(v, str)}
            sd = K.StrDictExt(RC.SD, new_texts)
            src = K.CaseSource(RC.CACHE, dict(changes), sd)
            ost0 = OverlayStore(RC.STORE, dict(changes))
            target_vals = {"ref": {}, "A": {}, "B": {}}
            for u in units:
                sh = RC.STORE.sheet(u["book"], u["sheet"])
                for mode in ("A", "B"):
                    b, v = u["bs"][mode]
                    got, _, _ = b.run(v, src, sd)
                    for (rr, cc), g in zip(u["arr"].tolist(), got):
                        target_vals[mode][(sh.sid, rr * KEY_SHIFT + cc)] = None if g == "<missing>" else g
                for rr, cc in u["arr"].tolist():
                    X._INDEX_CACHE.clear(); X._SUMIF_CACHE.clear()
                    try:
                        w = X.evaluate(u["tree"], ost0, u["book"], u["sheet"], rr, cc)
                    except Exception:
                        w = Err(15)
                    target_vals["ref"][(sh.sid, rr * KEY_SHIFT + cc)] = w
            scen = {"ref": target_vals["ref"], "A": target_vals["A"], "B": target_vals["B"]}
            for sgn in ("ulp+", "ulp-"):
                scen[sgn] = {k: (math.nextafter(w, math.inf if sgn == "ulp+" else -math.inf)
                                 if isinstance(w, float) and not isinstance(w, bool) and math.isfinite(w) and w != 0.0 else w)
                             for k, w in target_vals["ref"].items()}
            results = {}
            for sname, tv in scen.items():
                ch = collections.defaultdict(dict)
                for sid, kv in changes.items():
                    ch[sid].update(kv)
                for (sid, key), w in tv.items():
                    ch[sid][key] = w
                ost = OverlayStore(RC.STORE, dict(ch))
                vals = {}
                for _pass in range(2):
                    for (book, pid, sheet, r_, c_), lev in closure:
                        X._INDEX_CACHE.clear(); X._SUMIF_CACHE.clear()
                        try:
                            val = X.evaluate(trees[(pid, sheet)], ost, book, sheet, r_, c_)
                        except Exception:
                            val = Err(15)
                        sid = RC.STORE.sheet(book, sheet).sid
                        ost.changes.setdefault(sid, {})[r_ * KEY_SHIFT + c_] = val
                        vals[(book, pid, sheet, r_, c_)] = val
                results[sname] = vals
            base = results["ref"]
            for sname in ("A", "B", "ulp+", "ulp-"):
                c = cnt[sname]
                tdiff = sum(1 for k in scen[sname] if not same(scen[sname][k], scen["ref"][k])[0])
                c["targets_differing"] += tdiff
                for k, w0 in base.items():
                    w1 = results[sname][k]
                    c["consumer_evals"] += 1
                    if same(w0, w1)[0]:
                        continue
                    if isinstance(w0, float) and isinstance(w1, float) and math.isfinite(w0) and w0 != 0.0 and abs(w1 - w0) <= 8 * math.ulp(w0):
                        c["proportional"] += 1
                    else:
                        c["discontinuous"] += 1
                        c[RC.DATA["patterns"][k[1]]["eq"]] += 1
                        if len(ex[sname]) < 6:
                            ex[sname].append((vi, kind) + k[:1] + k[2:] + (RC.DATA["patterns"][k[1]]["eq"], repr(w0)[:40], repr(w1)[:40]))
        out[eq] = dict(variants=nv, closure=len(closure), counts={k: dict(v) for k, v in cnt.items()}, examples=dict(ex))
        print(eq, "closure", len(closure), {k: dict(v) for k, v in cnt.items()}, round(time.time() - t0), "s", flush=True)
        pickle.dump(out, open(outp, "wb"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 40)
