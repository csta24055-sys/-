"""The 8 unresolved equations on the REAL patterns (private, local only): for methods A and B
  L1   every instance cell: converted value vs Excel's cached value and vs the reference evaluator;
  VB   boundary / edge variants (verify_boundary's generator, 40 variants x up to 8 instances per group):
       the program compiled ONCE, value columns refilled per variant, vs the reference evaluator;
  plus steps, compile / run time and table memory.
Usage: run8.py <out.pkl>"""
import os, sys, time, collections, pickle, traceback, resource
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
S = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(S, "conv")); sys.path.insert(0, os.path.join(S, "jcat_tools"))
import warnings; warnings.simplefilter("ignore")
import numpy as np
import fx, excel_ref as X, compile2 as K, run_compile as RC, verify_boundary as VBM
from overlay import OverlayStore
from store import KEY_SHIFT, Err
from validate_ref import same as same_tol
from synth import same            # exact comparison
import exact8 as E8
import crref

TARGETS = {"EQ-0023": ["Pe2979d3e5788", "Pfc2290929762"], "EQ-0144": ["P892de908464d"], "EQ-0469": ["P298801d08d8c"],
           "EQ-0298": ["P61f78fa1a114"], "EQ-0450": ["P75f658bb292b"], "EQ-0451": ["P1dc5fedc15a9"], "EQ-0452": ["P3565aef94445"],
           "EQ-0229": ["P23b54bccaf8f"]}


def builder(book, sheet, rows, cols, mode):
    b = E8.Exact8Final(RC.STORE, RC.SD, RC.CACHE, book, sheet, rows, cols)
    b.improve = True
    b.mode8 = mode
    return b


def table_bytes(b):
    return int(sum(a.nbytes for d in b.tabs.data.values() for a in d.values()))


def l1(pid, mode):
    p = RC.DATA["patterns"][pid]
    rec = collections.Counter()
    ex, notes = [], collections.Counter()
    ast = fx.Parser(fx.tokenize(p["text"])).parse()
    for (book, sheet), arr in RC.DATA["instances"][pid].items():
        tree = X.prepare(ast, p["row"], RC.col_num(p["col"]), RC.STORE, book, sheet)
        sh = RC.STORE.sheet(book, sheet)
        t0 = time.time()
        b = builder(book, sheet, arr[:, 0], arr[:, 1], mode)
        try:
            v = b.finish(b.ev(tree))
        except K.Unsupported as e:
            rec["unsupported"] += len(arr)
            ex.append(("unsupported", str(e)[:120]))
            continue
        t1 = time.time()
        got, prog, eng = b.run(v)
        t2 = time.time()
        rec["groups"] += 1; rec["steps"] = max(rec["steps"], len(prog.steps)); rec["compile_ms"] += 1000 * (t1 - t0)
        rec["run_ms"] += 1000 * (t2 - t1); rec["table_bytes"] = max(rec["table_bytes"], table_bytes(b))
        eb = int(sum(c.v.nbytes + c.m.nbytes for c in eng.cols.values()))          # engine columns (results of the steps)
        rec["engine_bytes"] = max(rec["engine_bytes"], eb)
        rec["rows_max"] = max(rec["rows_max"], max(b.tabs.rows.values()))
        notes.update(b.notes)
        for (r, c), g in zip(arr.tolist(), got):
            rec["n"] += 1
            want = sh.values.get(r * KEY_SHIFT + c)
            X._INDEX_CACHE.clear(); X._SUMIF_CACHE.clear()
            try:
                ref = X.evaluate(tree, RC.STORE, book, sheet, r, c)
            except Exception as e:
                ref = "EXC:%s" % type(e).__name__
            X._INDEX_CACHE.clear(); X._SUMIF_CACHE.clear()
            with crref.correctly_rounded():
                try:
                    ref_cr = X.evaluate(tree, RC.STORE, book, sheet, r, c)
                except Exception as e:
                    ref_cr = "EXC:%s" % type(e).__name__
            if g == "<missing>":
                rec["missing"] += 1
                if len(ex) < 6:
                    ex.append((book, sheet, r, c, "<missing>", repr(want)[:50]))
                continue
            okc, okr = same(g, want)[0], same(g, ref)[0]
            rec["ok_cached"] += okc; rec["ok_ref"] += okr
            rec["ok_cached_tol"] += same_tol(g, want)[0]; rec["ok_ref_tol"] += same_tol(g, ref)[0]
            rec["ref_eq_cached"] += same(ref, want)[0]
            rec["ok_ref_cr"] += same(g, ref_cr)[0]; rec["refcr_eq_cached"] += same(ref_cr, want)[0]
            if not (okc and okr) and len(ex) < 6:
                ex.append((book, sheet, r, c, repr(g)[:50], repr(want)[:50], repr(ref)[:50]))
    return dict(rec), ex, dict(notes)


def vb(pid, mode):
    """verify_boundary.run_pattern with the research builder."""
    p = RC.DATA["patterns"][pid]
    rec = dict(n=0, ok=0, bad=0, missing=0, wrong=0, ref_exc=0, by_kind=collections.Counter(), bad_by_kind=collections.Counter(),
               examples=[], unsupported=None, run_ms=0.0, variants=0)
    try:
        ast = fx.Parser(fx.tokenize(p["text"])).parse()
        col0 = RC.col_num(p["col"])
        for (book, sheet), arr in RC.DATA["instances"][pid].items():
            r0 = VBM.rng_for(pid, book, sheet, "sample")
            idx = sorted(r0.sample(range(len(arr)), min(VBM.S_INST, len(arr))))
            sub = arr[idx]
            tree = X.prepare(ast, p["row"], col0, RC.STORE, book, sheet)
            b = builder(book, sheet, sub[:, 0], sub[:, 1], mode)
            v = b.finish(b.ev(tree))
            consts = VBM.constants(tree, [])
            singles, pool = VBM.precedents(b)
            for vi in range(VBM.N_VAR):
                kind = VBM.KINDS[vi]
                r = VBM.rng_for(pid, book, sheet, vi)
                changes = collections.defaultdict(dict)
                new_texts = set()
                for sh_, key in singles:
                    k2 = r.choice(VBM.MIX) if kind == "mixed" else kind
                    val = VBM.gen_value(k2, r, consts, pool)
                    changes[sh_.sid][key] = val
                    if isinstance(val, str):
                        new_texts.add(val)
                sd = K.StrDictExt(RC.SD, new_texts)
                src = K.CaseSource(RC.CACHE, dict(changes), sd)
                t0 = time.time()
                got, prog, eng = b.run(v, src, sd)
                rec["run_ms"] += 1000 * (time.time() - t0)
                ost = OverlayStore(RC.STORE, dict(changes))
                X._INDEX_CACHE.clear(); X._SUMIF_CACHE.clear()
                rec["variants"] += 1
                for (rr, cc), g in zip(sub.tolist(), got):
                    try:
                        want = X.evaluate(tree, ost, book, sheet, rr, cc)
                    except Exception as e:
                        want = "EXC:%s" % type(e).__name__
                    X._INDEX_CACHE.clear(); X._SUMIF_CACHE.clear()
                    with crref.correctly_rounded():
                        try:
                            want_cr = X.evaluate(tree, ost, book, sheet, rr, cc)
                        except Exception as e:
                            want_cr = "EXC:%s" % type(e).__name__
                    if g != "<missing>":
                        rec["ok_cr"] = rec.get("ok_cr", 0) + same(g, want_cr)[0]
                        rec["ref_eq_cr"] = rec.get("ref_eq_cr", 0) + same(want, want_cr)[0]
                    if isinstance(want, str) and want.startswith("EXC:"):
                        rec["ref_exc"] += 1
                        continue
                    rec["n"] += 1
                    rec["by_kind"][kind] += 1
                    if g == "<missing>":
                        rec["missing"] += 1; rec["bad"] += 1; rec["bad_by_kind"][kind] += 1
                        if len(rec["examples"]) < 6:
                            rec["examples"].append((book, sheet, rr, cc, kind, vi, "<missing>", repr(want)[:60]))
                        continue
                    if same(g, want)[0]:
                        rec["ok"] += 1
                    elif same_tol(g, want)[0]:
                        rec["bad"] += 1; rec["wrong"] += 1; rec["within_1e-9"] = rec.get("within_1e-9", 0) + 1; rec["bad_by_kind"][kind] += 1
                        if len(rec["examples"]) < 6:
                            rec["examples"].append((book, sheet, rr, cc, kind, vi, repr(g)[:60], repr(want)[:60]))
                    else:
                        rec["bad"] += 1; rec["wrong"] += 1; rec["bad_by_kind"][kind] += 1
                        if len(rec["examples"]) < 6:
                            rec["examples"].append((book, sheet, rr, cc, kind, vi, repr(g)[:60], repr(want)[:60]))
            X._INDEX_CACHE.clear(); X._SUMIF_CACHE.clear()
    except K.Unsupported as e:
        rec["unsupported"] = str(e)
    except Exception:
        rec["unsupported"] = "EXC " + traceback.format_exc()[-800:]
    return rec


def main(outp):
    t0 = time.time()
    RC.setup(os.path.join(S, "jcat_work", "scan.sqlite3"), os.path.join(S, "conv", "instances.pkl"))
    print("loaded", round(time.time() - t0), "s", flush=True)
    only = sys.argv[2:] or list(TARGETS)
    out = pickle.load(open(outp, "rb")) if (sys.argv[2:] and os.path.exists(outp)) else {}     # partial rerun: merge
    for eq in only:
        for pid in TARGETS[eq]:
            for mode in ("A", "B"):
                ta = time.time()
                a, ex, notes = l1(pid, mode)
                b = vb(pid, mode)
                out[(eq, pid, mode)] = dict(l1=a, l1_examples=ex, notes=notes, vb=b, seconds=time.time() - ta)
                print(eq, pid, mode, "L1", a, ex[:2], flush=True)
                print("    VB", {k: b[k] for k in ("n", "ok", "bad", "missing", "wrong", "ref_exc", "variants", "unsupported")},
                      "run %.0f ms" % b["run_ms"], b["examples"][:3], flush=True)
                pickle.dump(out, open(outp, "wb"))
    print("peak RSS MB", resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, "total s", round(time.time() - t0))


if __name__ == "__main__":
    main(sys.argv[1])
