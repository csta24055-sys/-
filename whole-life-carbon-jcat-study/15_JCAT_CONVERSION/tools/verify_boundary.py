"""Boundary and edge conditions, every pattern: the converted form (program compiled ONCE, value columns
refilled per variant) vs the reference evaluator (Excel semantics, validated on all 3,818,483 cells), with
the SAME overlaid inputs.

For every pattern and sheet: up to S instances (seeded sample); their precedent cells (the cells the
compiled program reads by position: single cells and the cells of ranges of at most SMALL cells) get
values from a variant generator; 40 variants per pattern (blank, 0, +-1, realistic magnitudes,
integers, thresholds of the formula +- delta, half-way points of rounding, texts, errors, logicals,
values taken from the look-up tables, mixtures). Seeds: SEED, pattern id, variant number.

Usage: verify_boundary.py <scan> <instances.pkl> <out.pkl> <n_proc> [pids...]"""
import sys, os
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "jcat_tools"))
import collections, hashlib, json, math, multiprocessing as mp, pickle, random, time, traceback
import numpy as np
import fx
import excel_ref as X
import compile2 as K
import run_compile as RC
from overlay import OverlayStore
from store import Err, KEY_SHIFT
from validate_ref import same

SEED = 20261114
S_INST = 8
SMALL = 64
N_VAR = 40
IMPROVE = bool(int(os.environ.get("IMPROVE", "0")))
SKIP_SAME = bool(int(os.environ.get("SKIP_SAME", "0")))     # base method: skip groups whose program equals the improved one


def rng_for(*parts):
    h = hashlib.sha256(("|".join(map(str, (SEED,) + parts))).encode()).digest()
    return random.Random(int.from_bytes(h[:8], "big"))


def constants(node, out):
    k = node[0]
    if k == "const":
        out.append(node[1])
    elif k in ("neg", "pct"):
        constants(node[1], out)
    elif k == "bin":
        constants(node[2], out); constants(node[3], out)
    elif k == "call":
        for a in node[2]:
            constants(a, out)
    return out


def precedents(b):
    """Positions the compiled program reads: [(sheet, key)] of single cells, and pools of range values."""
    singles, pool = [], []
    for rec in b.recipes:
        if rec[0] in ("G", "lexG"):
            sheet, rr, cc = rec[2], rec[3], rec[4]
            bad = rec[5] if rec[0] == "G" else np.zeros(len(rr))
            for r, c, bd in zip(rr.tolist(), cc.tolist(), np.asarray(bad).tolist() if rec[0] == "G" else [0] * len(rr)):
                if not bd:
                    singles.append((sheet, r * KEY_SHIFT + c))
        elif rec[0] == "T":
            sheet, rr, cc = rec[3], rec[4], rec[5]
            keys = (np.asarray(rr, dtype=np.int64) * KEY_SHIFT + np.asarray(cc, dtype=np.int64)).tolist()
            vals = [sheet.values.get(k) for k in keys]
            pool.extend(v for v in vals if v is not None)
            if len(keys) <= SMALL:
                singles.extend((sheet, k) for k in keys)
    seen, uniq = set(), []
    for s_, k in singles:
        if (s_.sid, k) not in seen:
            seen.add((s_.sid, k))
            uniq.append((s_, k))
    return uniq, pool


def gen_value(kind, r, consts, pool):
    nums = [c for c in consts if isinstance(c, float) and not isinstance(c, bool)]
    texts = [c for c in consts if isinstance(c, str)]
    if kind == "blank":
        return None
    if kind == "zero":
        return 0.0
    if kind == "one":
        return 1.0
    if kind == "minus":
        return -1.0
    if kind == "real":
        x = 10 ** r.uniform(-3, 6)
        x = round(x, r.choice([0, 1, 2, 3, 4]))
        return -x if r.random() < 0.1 else x
    if kind == "int":
        return float(r.randint(0, 120))
    if kind == "thresh":
        if not nums:
            return float(r.randint(-2, 2))
        c = r.choice(nums)
        d = r.choice([0.0, 1.0, -1.0, 0.5, -0.5, 1e-9 * max(1.0, abs(c)), -1e-9 * max(1.0, abs(c))])
        return c + d
    if kind == "half":
        k = r.randint(0, 1000)
        x = k + 0.5 + r.choice([0.0, 0.0, 1e-13, -1e-13, 1e-10, -1e-10])
        x = x / 10 ** r.choice([0, 1, 2, 3])
        return float(x) if r.random() < 0.5 else float("%.3f" % (r.randint(0, 99999) / 1000.0 + 0.0005 * r.choice([0, 1])))
    if kind == "text":
        return r.choice(["", "abc", "1", "1,000", "TRUE", "  2.5 ", "x-1"] + texts + [v for v in pool[:200] if isinstance(v, str)][:20])
    if kind == "err":
        return Err(r.choice([7, 2, 3]))
    if kind == "bool":
        return r.random() < 0.5
    if kind == "lookup":
        cands = [v for v in pool if not isinstance(v, Err)]
        if cands and r.random() < 0.85:
            return r.choice(cands)
        return gen_value("real", r, consts, pool)
    raise ValueError(kind)


KINDS = (["blank", "zero", "one", "minus"] + ["real"] * 6 + ["int"] * 4 + ["thresh"] * 6 + ["half"] * 3 + ["text"] * 2 +
         ["err", "bool"] + ["lookup"] * 6 + ["mixed"] * 7)
assert len(KINDS) == N_VAR
MIX = ["blank", "zero", "one", "real", "real", "int", "thresh", "half", "text", "err", "bool", "lookup", "lookup"]


def run_pattern(pid):
    p = RC.DATA["patterns"][pid]
    rec = dict(n=0, ok=0, bad=0, missing=0, kinds=collections.Counter(), examples=[], unsupported=None,
               variants=0, by_kind=collections.Counter(), bad_by_kind=collections.Counter(), changed=0)
    try:
        ast = fx.Parser(fx.tokenize(p["text"])).parse()
        col0 = RC.col_num(p["col"])
        for (book, sheet), arr in RC.DATA["instances"][pid].items():
            r0 = rng_for(pid, book, sheet, "sample")
            idx = sorted(r0.sample(range(len(arr)), min(S_INST, len(arr))))
            sub = arr[idx]
            tree = X.prepare(ast, p["row"], col0, RC.STORE, book, sheet)
            cache = RC.CACHE
            b = K.Builder(RC.STORE, RC.SD, cache, book, sheet, sub[:, 0], sub[:, 1])
            b.improve = IMPROVE
            v = b.finish(b.ev(tree))
            if SKIP_SAME and not IMPROVE:
                b2 = K.Builder(RC.STORE, RC.SD, cache, book, sheet, sub[:, 0], sub[:, 1])
                b2.improve = True
                try:
                    v2 = b2.finish(b2.ev(tree))
                    same_prog = json.dumps(b.steps, sort_keys=True) == json.dumps(b2.steps, sort_keys=True) and v.c == v2.c
                except K.Unsupported:
                    same_prog = False
                if same_prog:
                    rec["same_as_improved_groups"] = rec.get("same_as_improved_groups", 0) + 1
                    continue
            consts = constants(tree, [])
            singles, pool = precedents(b)
            for vi in range(N_VAR):
                kind = KINDS[vi]
                r = rng_for(pid, book, sheet, vi)
                changes = collections.defaultdict(dict)
                new_texts = set()
                for sh_, key in singles:
                    if sh_.formula.get(key) is not None and False:
                        continue
                    k2 = r.choice(MIX) if kind == "mixed" else kind
                    val = gen_value(k2, r, consts, pool)
                    changes[sh_.sid][key] = val
                    if isinstance(val, str):
                        new_texts.add(val)
                sd = K.StrDictExt(RC.SD, new_texts)
                src = K.CaseSource(cache, dict(changes), sd)
                got, prog, eng = b.run(v, src, sd)
                ost = OverlayStore(RC.STORE, dict(changes))
                X._INDEX_CACHE.clear(); X._SUMIF_CACHE.clear()
                rec["variants"] += 1
                for (rr, cc), g in zip(sub.tolist(), got):
                    try:
                        want = X.evaluate(tree, ost, book, sheet, rr, cc)
                    except X.Unsupported:
                        raise
                    except Exception as e:
                        want = "EXC:%s" % type(e).__name__
                    rec["n"] += 1
                    rec["by_kind"][kind] += 1
                    if g == "<missing>":
                        rec["missing"] += 1; rec["bad"] += 1; rec["kinds"]["missing"] += 1; rec["bad_by_kind"][kind] += 1
                        if len(rec["examples"]) < 6:
                            rec["examples"].append((book, sheet, rr, cc, kind, vi, "<missing>", repr(want)[:60]))
                        continue
                    eq, k_, rel = same(g, want)
                    if eq:
                        rec["ok"] += 1
                    else:
                        rec["bad"] += 1; rec["kinds"][k_] += 1; rec["bad_by_kind"][kind] += 1
                        if len(rec["examples"]) < 6:
                            rec["examples"].append((book, sheet, rr, cc, kind, vi, repr(g)[:60], repr(want)[:60]))
            X._INDEX_CACHE.clear(); X._SUMIF_CACHE.clear()
    except K.Unsupported as e:
        rec["unsupported"] = str(e)
    except Exception:
        rec["unsupported"] = "EXC " + traceback.format_exc()[-800:]
    return rec


def work(pids):
    return {pid: run_pattern(pid) for pid in pids}


if __name__ == "__main__":
    t0 = time.time()
    RC.setup(sys.argv[1], sys.argv[2])
    nproc = int(sys.argv[4])
    pids = sys.argv[5:] or sorted(RC.DATA["patterns"], key=lambda q: -RC.DATA["patterns"][q]["n"])
    res = {}
    if len(pids) <= 8:
        res = work(pids)
    else:
        chunks = [pids[i::nproc * 8] for i in range(nproc * 8)]
        with mp.get_context("fork").Pool(nproc) as pool:
            for part in pool.imap_unordered(work, chunks):
                res.update(part)
                print("done", len(res), round(time.time() - t0), "s", flush=True)
    pickle.dump({"seed": SEED, "S": S_INST, "SMALL": SMALL, "kinds": KINDS, "mix": MIX, "improve": IMPROVE, "results": res},
                open(sys.argv[3], "wb"))
    tot = collections.Counter()
    for r in res.values():
        for k in ("n", "ok", "bad", "missing", "variants"):
            tot[k] += r[k]
        tot["unsupported"] += r["unsupported"] is not None
        tot["bad_patterns"] += r["bad"] > 0
    print(dict(tot), "seconds", round(time.time() - t0))
    if len(pids) <= 8:
        for pid, r in res.items():
            print(pid, {k: r[k] for k in ("n", "ok", "bad", "missing", "unsupported")}, dict(r["bad_by_kind"]), r["examples"][:4])
