"""Random realistic building cases: LibreOffice recalculates the whole workbook with randomised inputs;
for every pattern of the workbook, a fixed seeded sample of instances is evaluated with the converted
form (program compiled ONCE; value columns refilled with the case's values) and with the reference
evaluator, on the SAME case values, and compared with LibreOffice's result for the cell.

Sampling of inputs (per case, seed = SHA-256(SEED, book, case)):
  choice cells (input rule list)          : an option of the list (p = 0.85), else the original
  numbers                                 : original x 10^U(-0.6, 0.6) (0.25x .. 4x), integers stay integers
      years (1900..2100, unit or name 年)  : integer U[1995, 2035]
      evaluation period (name 評価期間)     : one of 30 40 50 60 65 70 75 80 90 100
      rates (0 < v <= 1, name 率 or unit %): U(0, 1) rounded to 3 decimals
  Summary Table (SUM) blank input cells   : filled with p = 0.3 by U-log(0.1, 1000), 2 decimals
  blank cells of numeric input columns    : filled with p = 0.15 by a log-uniform value between 1/5 of the
                                            smallest and 5x the largest original number of the column
                                            (U(0.1, 1000) when the column has none), 2 decimals
  texts                                   : unchanged
  SIM and STD (many inputs, slow input writes in LibreOffice): every input cell is varied with p = 0.05
  (the rules above), otherwise it keeps its original value
Instances: S per (pattern, sheet) group, seeded sample (the same in every case).
A pattern is evaluated in a case only when a cell it reads or the cell itself changed (new conditions).

Usage: random_cases.py <scan> <instances.pkl> <input_spec.pkl> <books_dir> <book> <case_from> <case_to> <port> <out.pkl>"""
import sys, os
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "jcat_tools"))
import collections, hashlib, json, math, pickle, random, time, traceback
import numpy as np
import fx
import excel_ref as X
import compile2 as K
import run_compile as RC
import lo_engine
from lo_baseline import FILES
from overlay import OverlayStore
from store import Err, KEY_SHIFT
from validate_ref import same

SEED = 20261114
S_INST = 8
PERIODS = [30, 40, 50, 60, 65, 70, 75, 80, 90, 100]
def _private_patch():
    """LibreOffice cannot evaluate _xlfn.SINGLE (implicit intersection) of a one-cell name; the LibreOffice copy of
    the Standard workbook gets the equivalent formula without SINGLE. The formulas are J-CAT content, so they are
    kept in a PRIVATE configuration file (not in the public repository)."""
    p = os.environ.get("JCAT_PRIVATE_CONFIG", os.path.join(os.path.dirname(os.path.abspath(__file__)), "private_config.json"))
    if not os.path.exists(p):
        return {}
    return {(a, b): c for a, b, c in json.load(open(p, encoding="utf-8"))["STD_PATCH"]}


STD_PATCH = _private_patch()


def rng_for(*parts):
    h = hashlib.sha256(("|".join(map(str, (SEED,) + parts))).encode()).digest()
    return random.Random(int.from_bytes(h[:8], "big"))


def column_stats(items):
    st = collections.defaultdict(list)
    for it in items:
        if isinstance(it["value"], float) and not isinstance(it["value"], bool) and it["value"] > 0:
            st[(it["sid"], it["col"])].append(it["value"])
    return st


SUBSET = {"SIM": 0.05, "STD": 0.05}       # SIM/STD: each input cell is varied with this probability (else original)


def gen_inputs(items, colstats, r, book=None):
    out = []
    for it in items:
        v, name, unit = it["value"], it["item"] or "", it["unit"] or ""
        if book in SUBSET and r.random() >= SUBSET[book]:
            out.append(v)
            continue
        if it["options"]:
            nv = r.choice(it["options"]) if r.random() < 0.85 else v
        elif isinstance(v, float) and not isinstance(v, bool):
            if "評価期間" in name:
                nv = float(r.choice(PERIODS))
            elif 1900 <= v <= 2100 and v == int(v) and ("年" in unit or "年" in name):
                nv = float(r.randint(1995, 2035))
            elif 0 < v <= 1 and ("率" in name or "%" in unit):
                nv = round(r.random(), 3)
            elif v == 0:
                nv = v if r.random() < 0.7 else round(10 ** r.uniform(-1, 3), 2)
            else:
                nv = v * 10 ** r.uniform(-0.6, 0.6)
                nv = float(round(nv)) if v == int(v) and abs(v) >= 1 else float("%.6g" % nv)
        elif v is None:
            cs = colstats.get((it["sid"], it["col"]))
            if cs is not None and r.random() < 0.15:
                lo, hi = max(min(cs) / 5, 1e-3), max(cs) * 5
                nv = round(10 ** r.uniform(math.log10(lo), math.log10(hi)), 2)
            elif cs is None and book == "SUM" and r.random() < 0.3:
                # Summary Table: its input cells are all blank (values to be entered): U-log(0.1, 1000)
                nv = round(10 ** r.uniform(-1, 3), 2)
            else:
                nv = None
        else:
            nv = v
        out.append(nv)
    return out


def precedent_keys(b):
    """{sheet sid: sorted array of keys} the program reads; sheets read as a whole (dynamic positions): 'ALL'."""
    d = collections.defaultdict(list)
    whole = set()
    for rec in b.recipes:
        if rec[0] in ("G", "lexG"):
            sh, rr, cc = rec[2], rec[3], rec[4]
            d[sh.sid].append(np.asarray(rr, dtype=np.int64) * KEY_SHIFT + np.asarray(cc, dtype=np.int64))
        elif rec[0] in ("T", "lex"):
            sh, rr, cc = (rec[3], rec[4], rec[5]) if rec[0] == "T" else (rec[2], rec[3], rec[4])
            d[sh.sid].append(np.asarray(rr, dtype=np.int64) * KEY_SHIFT + np.asarray(cc, dtype=np.int64))
        elif rec[0] == "W":
            whole.add(rec[2].sid)
    return {sid: np.unique(np.concatenate(v)) for sid, v in d.items()}, whole


class Unit:
    def __init__(self, pid, book, sheet, sub, tree, b_base, v_base, b_imp, v_imp):
        self.pid, self.book, self.sheet, self.sub, self.tree = pid, book, sheet, sub, tree
        self.bb, self.vb, self.bi, self.vi = b_base, v_base, b_imp, v_imp
        pk1, w1 = precedent_keys(b_imp) if b_imp else ({}, set())
        pk2, w2 = precedent_keys(b_base) if b_base else ({}, set())
        keys = collections.defaultdict(list)
        for pk in (pk1, pk2):
            for sid, a in pk.items():
                keys[sid].append(a)
        self.prec = {sid: np.unique(np.concatenate(a)) for sid, a in keys.items()}
        self.whole = w1 | w2
        sh = RC.STORE.sheet(book, sheet)
        self.own_sid = sh.sid
        self.own = np.asarray(sub[:, 0], dtype=np.int64) * KEY_SHIFT + np.asarray(sub[:, 1], dtype=np.int64)


def build_units(book):
    units, fails = [], {}
    for pid, inst in RC.DATA["instances"].items():
        p = RC.DATA["patterns"][pid]
        ast = None
        for (bk, sheet), arr in inst.items():
            if bk != book:
                continue
            try:
                if ast is None:
                    ast = fx.Parser(fx.tokenize(p["text"])).parse()
                r0 = rng_for(pid, bk, sheet, "sample")
                idx = sorted(r0.sample(range(len(arr)), min(S_INST, len(arr))))
                sub = arr[idx]
                tree = X.prepare(ast, p["row"], RC.col_num(p["col"]), RC.STORE, bk, sheet)
                cache = RC.CACHE
                out = []
                for improve in (False, True):
                    try:
                        b = K.Builder(RC.STORE, RC.SD, cache, bk, sheet, sub[:, 0], sub[:, 1])
                        b.improve = improve
                        v = b.finish(b.ev(tree))
                        b.program()
                        out += [b, v]
                    except K.Unsupported as e:
                        out += [None, str(e)]
                units.append(Unit(pid, bk, sheet, sub, tree, out[0], out[1], out[2], out[3]))
            except Exception:
                fails[(pid, sheet)] = traceback.format_exc()[-400:]
    return units, fails


def main():
    scan, inst, spec_p, books_dir, book, c0, c1, port, outp = sys.argv[1:10]
    c0, c1 = int(c0), int(c1)
    t0 = time.time()
    RC.setup(scan, inst)
    spec = pickle.load(open(spec_p, "rb"))[book]
    colstats = column_stats(spec)
    units, fails = build_units(book)
    print("units", len(units), "build fails", len(fails), round(time.time() - t0), "s", flush=True)
    # formula cell positions of this book, per sheet
    pos = collections.defaultdict(list)
    for pid, d in RC.DATA["instances"].items():
        for (bk, sheet), arr in d.items():
            if bk == book:
                pos[sheet].extend(map(tuple, arr.tolist()))
    lo = lo_engine.LO(int(port), os.path.join(os.path.dirname(os.path.abspath(outp)), "lo_profile_%s" % port))
    lo.load(os.path.join(books_dir, FILES[book]))
    if book == "STD":
        patched = 0
        for (sname, ftxt), newf in STD_PATCH.items():
            for pid, d in RC.DATA["instances"].items():
                if RC.DATA["patterns"][pid]["text"] != ftxt:
                    continue
                for (bk, sname2), arr in d.items():
                    if bk == book and sname2 == sname:
                        for rr, cc in arr.tolist():
                            lo.sheets[sname].getCellByPosition(cc - 1, rr - 1).setFormula(newf)
                            patched += 1
        print("STD: LibreOffice copy patched (SINGLE of a one-cell name), cells:", patched, flush=True)
    lo.doc.enableAutomaticCalculation(False)
    lo.recalc()
    base_items = spec
    stats = {}
    case_log = []
    for case in range(c0, c1):
        tc = time.time()
        r = rng_for(book, case)
        vals = gen_inputs(spec, colstats, r)
        changes = collections.defaultdict(dict)
        for it, nv in zip(spec, vals):
            lo.set_value(it["sheet"], it["row"], it["col"], nv)
            if nv != it["value"] or type(nv) is not type(it["value"]):
                changes[it["sid"]][it["row"] * KEY_SHIFT + it["col"]] = nv
        n_inputs_changed = sum(len(v) for v in changes.values())
        lo.recalc()
        t_calc = time.time() - tc
        lo_vals = {}
        for sheet, ps in pos.items():
            lo_vals[sheet] = lo.read_sheet(sheet, ps)
        t_read = time.time() - tc - t_calc
        for sheet, vals_ in lo_vals.items():
            sh = RC.STORE.sheet(book, sheet)
            ch = changes[sh.sid]
            for (rr, cc), v in vals_.items():
                key = rr * KEY_SHIFT + cc
                old = sh.values.get(key)
                if not (type(v) is type(old) and (v == old if not isinstance(v, float) else (v == old or (v != v and old != old)))):
                    ch[key] = v
        changes = {k: v for k, v in changes.items() if v}
        ck = {sid: np.array(sorted(v), dtype=np.int64) for sid, v in changes.items()}
        new_texts = {v for d in changes.values() for v in d.values() if isinstance(v, str)}
        sd = K.StrDictExt(RC.SD, new_texts)
        base_cache = {}
        ost = OverlayStore(RC.STORE, changes)
        X._INDEX_CACHE.clear(); X._SUMIF_CACHE.clear()
        n_eval = 0
        for u in units:
            hit = np.isin(u.own, ck.get(u.own_sid, np.zeros(0, dtype=np.int64))).any()
            if not hit:
                for sid in u.whole:
                    if sid in ck:
                        hit = True
                        break
            if not hit:
                for sid, a in u.prec.items():
                    c_ = ck.get(sid)
                    if c_ is not None and np.isin(a, c_, assume_unique=True).any():
                        hit = True
                        break
            if not hit:
                continue
            n_eval += 1
            sheet_vals = lo_vals[u.sheet]
            want_lo = [sheet_vals[(int(a), int(b_))] for a, b_ in u.sub.tolist()]
            refs = []
            for a, b_ in u.sub.tolist():
                try:
                    refs.append(X.evaluate(u.tree, ost, u.book, u.sheet, int(a), int(b_)))
                except Exception as e:
                    refs.append("EXC:%s" % type(e).__name__)
            rec = stats.setdefault(u.pid, {m: collections.Counter() for m in ("base", "improved")})
            ex = stats.setdefault(("ex", u.pid), [])
            for method, b, v in (("base", u.bb, u.vb), ("improved", u.bi, u.vi)):
                cnt = rec[method]
                if b is None:
                    cnt["unsupported"] += len(want_lo)
                    continue
                cache = base_cache.setdefault(id(b.cache), b.cache)
                src = K.CaseSource(b.cache, changes, sd)
                try:
                    got, _, _ = b.run(v, src, sd)
                except Exception as e:
                    cnt["run_error"] += len(want_lo)
                    if len(ex) < 6:
                        ex.append((case, method, "run_error", traceback.format_exc()[-300:]))
                    continue
                for (a, b_), g, wl, wr in zip(u.sub.tolist(), got, want_lo, refs):
                    cnt["n"] += 1
                    if g == "<missing>":
                        cnt["missing"] += 1
                        ok_lo = ok_ref = False
                    else:
                        ok_lo = same(g, wl)[0]
                        ok_ref = same(g, wr)[0]
                    ref_lo = same(wr, wl)[0]
                    if ok_lo:
                        cnt["ok_lo"] += 1
                    if ok_ref:
                        cnt["ok_ref"] += 1
                    if ref_lo:
                        cnt["ref_eq_lo"] += 1
                    if not ok_lo or not ok_ref:
                        kind = ("conv=ref!=LO" if ok_ref and not ok_lo else "conv=LO!=ref" if ok_lo and not ok_ref else "conv differs from both")
                        cnt[kind] += 1
                        if len(ex) < 12:
                            ex.append((case, method, kind, u.sheet, a, b_, repr(g)[:50], repr(wl)[:50], repr(wr)[:50]))
        X._INDEX_CACHE.clear(); X._SUMIF_CACHE.clear()
        case_log.append(dict(case=case, seed_parts=(SEED, book, case), inputs_changed=n_inputs_changed,
                             cells_changed=sum(len(v) for v in changes.values()), units_evaluated=n_eval,
                             t_calc=round(t_calc, 2), t_read=round(t_read, 2), t_total=round(time.time() - tc, 2)))
        print("case", case, case_log[-1], flush=True)
        if (case - c0) % 10 == 9 or case == c1 - 1:
            pickle.dump(dict(book=book, seed=SEED, S=S_INST, cases=case_log, stats=stats, fails=fails), open(outp, "wb"))
    lo.close()


if __name__ == "__main__":
    main()
