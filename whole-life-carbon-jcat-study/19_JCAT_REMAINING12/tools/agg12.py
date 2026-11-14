"""Stage 3: write the PUBLIC count files of chapter 19 from the private result files (counts only: no formula text,
no cell address, no value, no name of a downstream equation).

  results/03_無作為ケースの照合件数.json   random building cases recalculated by LibreOffice (per equation and book)
  results/04_依存関係と下流への影響.json   static consumers of each equation (closure size, levels, number of
                                         downstream equations), substitution of method A values, the necessity test
                                         (a different text in every cell of the equation), the closure without the
                                         30-level cap and re-evaluations of it (closure_full.py)

Usage: python3 -B agg12.py <private folder with rc12_*.pkl and down12.pkl> <chapter 19 folder>
"""
import collections
import json
import os
import pickle
import sys

sys.dont_write_bytecode = True
EQS = ("EQ-0090", "EQ-0181", "EQ-0185", "EQ-0317", "EQ-0373", "EQ-0377", "EQ-0417", "EQ-0471", "EQ-0553", "EQ-0587", "EQ-0621", "EQ-0643")
KEYS = ("n", "ok_lo", "ok_ref", "ref_eq_lo", "ok_lo_tol", "ok_ref_tol", "ok_ref_cr", "missing", "wrong", "unsupported")


def main(priv, ch):
    rc = {}
    for book in ("DET", "SIM", "STD", "SUM"):
        p = os.path.join(priv, "rc12_%s.pkl" % book)
        if os.path.exists(p):
            rc[book] = pickle.load(open(p, "rb"))
    out = dict(note="LibreOffice recalculation of random building cases; counts only. 'n' = values of the equation's cells that "
                    "differ from the cached value in the case and were compared; cases_hit = cases in which at least one such value occurred.",
               books={b: rc[b]["cases"] for b in rc}, equations={})
    for eq in EQS:
        e = dict(patterns=0, cases=0, cases_hit=0, A=collections.Counter(), B=collections.Counter())
        for b, d in rc.items():
            for (q, pat), st in d["stats"].items():
                if q != eq:
                    continue
                e["patterns"] += 1
                e["cases"] += st.get("cases", 0)
                e["cases_hit"] += st.get("cases_hit", 0)
                for m in ("A", "B"):
                    for k in KEYS:
                        if st[m].get(k):
                            e[m][k] += st[m][k]
        e["A"], e["B"] = dict(e["A"]), dict(e["B"])
        out["equations"][eq] = e
    json.dump(out, open(os.path.join(ch, "results", "03_無作為ケースの照合件数.json"), "w"), indent=1, ensure_ascii=False)
    dp = os.path.join(priv, "down12.pkl")
    dn = pickle.load(open(dp, "rb")) if os.path.exists(dp) else {}
    o2 = dict(note="Static consumers: every formula cell whose references contain a cell of the equation, transitively, by levels "
                   "(down12.py stops at 30 levels; the closure without that cap is under full_closure). Substitution: the cells take "
                   "method A's values; only cells whose method-A value differs from Excel's cached value are substituted (substituted = 0 "
                   "means nothing to re-evaluate). Necessity test: every cell of the equation takes a different text (the old text with a "
                   "sign before and after it); the closure is re-evaluated by the reference evaluator in level order (2 passes in "
                   "down12.py; to a fixed point in closure_full.py) and compared with Excel's cached values. Changed consumer cells are "
                   "classified: within a proportional 8 ulp, or larger. Identity: the same re-evaluation with no change at all, to see "
                   "which differences the re-evaluation itself makes. Counts only.", equations={})
    cf = os.path.join(priv, "closure_full.pkl")
    full = pickle.load(open(cf, "rb")) if os.path.exists(cf) else {}
    for eq in EQS:
        v = dn.get(eq)
        if not v:
            o2["equations"][eq] = dict(status="not run")
            continue
        rec = v["rec"]
        imp = v.get("impact", {})

        def cls(ch):
            return dict(changed_cells=ch.get("changed", 0) + ch.get("proportional (<= 8 ulp)", 0),
                        within_8_ulp=ch.get("proportional (<= 8 ulp)", 0), larger=ch.get("changed", 0))
        e2 = dict(
            cells_of_equation=len(v.get("tcells", [])), consumer_closure_30_levels=rec["closure"],
            levels_30=[x for x in rec["levels"] if x], level_cap_reached=(len(rec["levels"]) >= 30 and rec["levels"][-1] > 0),
            downstream_equations_30_levels=len(rec["by_eq"]),
            substitution_A=dict(substituted=imp["A"]["substituted"], **cls(imp["A"]["changed"])) if "A" in imp else "not run",
            necessity_test_30_levels=dict(substituted=imp["perturb"]["substituted"], **cls(imp["perturb"]["changed"]))
            if "perturb" in imp else "not run")
        if eq in full:
            f = full[eq]
            e2["full_closure"] = dict(consumer_closure=f["n"], levels=len(f["levels"]), cells_beyond_level_30=f["beyond30"],
                                      downstream_equations=f["downstream_equations"],
                                      cells_per_level_after_30=sorted(collections.Counter(f["levels"][30:]).items()))
        rr = {}
        for mode in ("identity", "perturb"):
            rp = os.path.join(priv, "reeval_%s_%s.pkl" % (eq, mode))
            if os.path.exists(rp):
                rr[mode] = pickle.load(open(rp, "rb"))
        if rr:
            e2["full_closure_reevaluation"] = {
                ("necessity_test" if m == "perturb" else m): dict(substituted=r["substituted"], closure=r["closure"], passes=r["passes"],
                                                                  converged=r["converged"], within_8_ulp=len(r["ulp8"]), larger=len(r["larger"]))
                for m, r in rr.items()}
            if len(rr) == 2:
                a, b = rr["identity"], rr["perturb"]
                e2["full_closure_reevaluation"]["within_8_ulp_sets"] = dict(
                    both=len(a["ulp8"] & b["ulp8"]), identity_only=len(a["ulp8"] - b["ulp8"]), necessity_only=len(b["ulp8"] - a["ulp8"]),
                    larger_in_necessity_not_in_identity=len(b["larger"] - a["larger"]))
        o2["equations"][eq] = e2
    json.dump(o2, open(os.path.join(ch, "results", "04_依存関係と下流への影響.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps({eq: (out["equations"][eq]["cases_hit"], out["equations"][eq]["A"].get("n"), o2["equations"][eq].get("consumer_closure_30_levels")) for eq in EQS}))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
