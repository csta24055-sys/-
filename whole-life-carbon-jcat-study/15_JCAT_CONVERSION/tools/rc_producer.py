"""LibreOffice case producer: for cases c0..c1 of a book, set the sampled inputs (only cells whose value
changes), recalculate everything, read every formula cell, and write the cells whose value differs from
Excel's cached value (plus the changed inputs) to <dir>/<book>_<case>.pkl. Inputs: random_cases.gen_inputs."""
import sys, os
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "jcat_tools"))
import collections, pickle, time
import lo_engine
from lo_baseline import FILES
import random_cases as R
from store import KEY_SHIFT


def same_value(v, old):
    return type(v) is type(old) and (v == old or (isinstance(v, float) and v != v and old != old))


def main():
    cached_p, spec_p, books_dir, book, c0, c1, port, outdir = sys.argv[1:9]
    c0, c1 = int(c0), int(c1)
    cached = pickle.load(open(cached_p, "rb"))           # {"pos": {sheet: [(r,c)]}, "values": {sheet: {(r,c): v}}, "sid": {sheet: sid}, "patch": [...]}
    spec = pickle.load(open(spec_p, "rb"))[book]
    colstats = R.column_stats(spec)
    lo = lo_engine.LO(int(port), os.path.join(outdir, "..", "lo_profile_%s" % port))
    lo.load(os.path.join(books_dir, FILES[book]))
    for sheet, r, c, f in cached.get("patch", []):
        lo.sheets[sheet].getCellByPosition(c - 1, r - 1).setFormula(f)
    lo.doc.enableAutomaticCalculation(False)
    for sh in lo.sheets.values():
        if sh.isProtected():
            try:
                sh.unprotect("")
            except Exception:
                pass
    current = {(it["sheet"], it["row"], it["col"]): it["value"] for it in spec}
    for case in range(c0, c1):
        t = time.time()
        r = R.rng_for(book, case)
        vals = R.gen_inputs(spec, colstats, r, book)
        inputs = collections.defaultdict(dict)
        n_set = 0
        for it, nv in zip(spec, vals):
            k = (it["sheet"], it["row"], it["col"])
            if not same_value(nv, current[k]) and not (nv is None and current[k] is None):
                lo.set_value(it["sheet"], it["row"], it["col"], nv)
                current[k] = nv
                n_set += 1
            if not (same_value(nv, it["value"]) or (nv is None and it["value"] is None)):
                inputs[it["sid"]][it["row"] * KEY_SHIFT + it["col"]] = nv
        t_set = time.time() - t
        lo.recalc()
        t_calc = time.time() - t - t_set
        changes = collections.defaultdict(dict)
        for sheet, ps in cached["pos"].items():
            vals_ = lo.read_sheet(sheet, ps)
            base = cached["values"][sheet]
            sid = cached["sid"][sheet]
            for (rr, cc), v in vals_.items():
                if not same_value(v, base[(rr, cc)]):
                    changes[sid][rr * KEY_SHIFT + cc] = v
        lo_values = {sheet: None for sheet in cached["pos"]}
        out = dict(book=book, case=case, seed_parts=(R.SEED, book, case), inputs=dict(inputs), formula_changes=dict(changes),
                   n_set=n_set, t_set=round(t_set, 2), t_calc=round(t_calc, 2), t_total=round(time.time() - t, 2))
        tmp = os.path.join(outdir, "%s_%05d.tmp" % (book, case))
        pickle.dump(out, open(tmp, "wb"))
        os.replace(tmp, os.path.join(outdir, "%s_%05d.pkl" % (book, case)))
        print("case", case, "set", n_set, "inputs", sum(len(v) for v in inputs.values()), "changed", sum(len(v) for v in changes.values()),
              "t", out["t_set"], out["t_calc"], out["t_total"], flush=True)
    lo.close()


if __name__ == "__main__":
    main()
