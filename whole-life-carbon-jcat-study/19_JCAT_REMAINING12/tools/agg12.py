"""Stage 3: write the PUBLIC count files of chapter 19 from the private result files (counts only: no formula text,
no cell address, no value, no name of a downstream equation).

  results/03_無作為ケースの照合件数.json   random building cases recalculated by LibreOffice (per equation and book)
  results/04_依存関係と下流への影響.json   static consumers of each equation (closure size, levels, number of
                                         downstream equations), substitution of method A values, +-1 ulp perturbation

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
    o2 = dict(note="Static consumers: every formula cell whose references contain a cell of the equation, transitively, by levels. "
                   "Substitution: the cells take method A's values and the closure is re-evaluated by the reference evaluator, compared "
                   "with Excel's cached values (number of consumer cells that changed). Perturbation: every numeric cell of the equation "
                   "moved by +-1 ulp; consumer cells that change are classified (proportional <= 8 ulp, or larger: a rounding, threshold "
                   "or look-up that flips). Counts only.", equations={})
    for eq in EQS:
        v = dn.get(eq)
        if not v:
            o2["equations"][eq] = dict(status="not run")
            continue
        rec = v["rec"]
        imp = v.get("impact", {})
        o2["equations"][eq] = dict(
            cells_of_equation=len(v.get("tcells", [])), consumer_closure=rec["closure"], levels=[x for x in rec["levels"] if x],
            downstream_equations=len(rec["by_eq"]),
            substitution_A=dict(changed_cells=sum(imp["A"]["changed"].values()), by_class=imp["A"]["changed"]) if "A" in imp else "not run",
            perturbation=dict(perturbed_cells=imp["perturb"]["substituted"], changed_cells=sum(imp["perturb"]["changed"].values()),
                              by_class=imp["perturb"]["changed"]) if "perturb" in imp else "not run")
    json.dump(o2, open(os.path.join(ch, "results", "04_依存関係と下流への影響.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps({eq: (out["equations"][eq]["cases_hit"], out["equations"][eq]["A"].get("n"), o2["equations"][eq].get("consumer_closure")) for eq in EQS}))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
