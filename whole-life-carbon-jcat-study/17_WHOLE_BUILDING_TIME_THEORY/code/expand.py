"""Stage 1: expansion of the canonical whole-building equation back to the 70-unit model (independent concept
model, fictional data).

For one scenario: every knot of the merged knot form (L5) with its contributions grouped by (unit, stage, kernel
shape) and the provenance rows of the masked sum-product (P1) (the per-term contributions are accumulated by the same
rules as Canon.knot_form, so their sum equals the merged coefficient by construction: a bookkeeping check, not an
independent verification); and C(T) at chosen periods split by stage, unit and role (exact), next to the value of the
unified system (chapter 11) and of the frozen reference calculation.

Usage (from this folder): python3 -B expand.py <out.json> <set name> <scenario index> [T ...]
                          python3 -B expand.py --all-sets <out folder>     (scenario 0 of every set, gzip JSON per set)
Every contributing term is listed with its provenance row and its own (p, q) (earlier versions kept 3 per group).
"""
import gzip
import os
import collections
import json
import math
import sys
from fractions import Fraction

sys.dont_write_bytecode = True
import canon                                            # noqa: E402
import timechar as tc                                   # noqa: E402
from checks import sets_unified                         # noqa: E402
from tstudy import baseline, scenarios                  # noqa: E402

EPS, NEG_INF = canon.EPS, canon.NEG_INF


def term_knots(t):
    """Knot contributions of ONE term (the same rules as Canon.knot_form): [('A0'|'lattice'|'event', pos, p, q)]."""
    one = canon.Canon(H=0, terms=[t])
    A0, ev, la = one.knot_form()
    out = []
    if A0:
        out.append(("A0", None, A0, Fraction(0)))
    out += [("lattice", x, p, q) for x, (p, q) in la.items()]
    out += [("event", g, p, q) for g, (p, q) in ev.items()]
    return out


def expansion(can):
    groups = collections.defaultdict(lambda: collections.defaultdict(lambda: [Fraction(0), Fraction(0), 0, []]))
    for t in can.terms:
        for kind, pos, p, q in term_knots(t):
            g = groups[(kind, pos)][(t.unit, t.stage, t.kind)]
            g[0] += p; g[1] += q; g[2] += 1
            g[3].append((t.src, float(p), float(q)))         # every contributing term (no truncation)
    A0, ev, la = can.knot_form()
    merged = {("A0", None): (A0, Fraction(0))}
    merged.update({("lattice", x): tuple(v) for x, v in la.items()})
    merged.update({("event", g): tuple(v) for g, v in ev.items()})
    n_bad = 0
    rows = []
    for key in sorted(groups, key=lambda k: (k[0] != "A0", k[1] if k[1] is not None else -1, k[0])):
        contrib = groups[key]
        P = sum((c[0] for c in contrib.values()), Fraction(0))
        Q = sum((c[1] for c in contrib.values()), Fraction(0))
        m = merged.get(key, (Fraction(0), Fraction(0)))
        n_bad += (P, Q) != tuple(m)
        if P == 0 and Q == 0:
            continue
        rows.append(dict(kind=key[0], position=key[1], switch=(tc.tswitch(key[1]) if key[0] == "event" else None),
                         p=float(P), q=float(Q),
                         contributions=[dict(unit=u, stage=s, shape=k, p=float(c[0]), q=float(c[1]), n_terms=c[2], provenance=c[3])
                                        for (u, s, k), c in sorted(contrib.items()) if c[0] or c[1]]))
    return rows, n_bad


def split(can, T):
    by_stage = collections.defaultdict(Fraction)
    by_unit = collections.defaultdict(Fraction)
    by_role = collections.defaultdict(Fraction)
    for t in can.terms:
        v = t.amp * t.h(T)
        by_stage[t.stage] += v
        by_unit[t.unit] += v
        by_role[tc.role_of(t)] += v
    tot = sum(by_stage.values(), Fraction(0))
    assert tot == sum(by_unit.values(), Fraction(0)) == sum(by_role.values(), Fraction(0))
    return dict(T=T, C=float(tot), knot_form=float(tc.KF(can)(T)), by_stage={k: float(v) for k, v in sorted(by_stage.items())},
                by_unit={k: float(v) for k, v in sorted(by_unit.items())}, by_role={k: float(v) for k, v in sorted(by_role.items())})


def one(set_name, index, Ts, sets=None):
    from synth import population
    sets = sets or sets_unified.build([set_name])
    label, scn, periods = sets[set_name][index]
    sysm = canon.make_system(scn, population.BASELINES)
    can = canon.build(sysm)
    rows, n_bad = expansion(can)
    Ts = Ts or [float(p) for p in periods]
    res = dict(label=label, H=can.H, n_terms=len(can.terms), n_knots=len(rows), contributions_vs_merged_bad=n_bad,
               values=[split(can, T) for T in Ts], unified_system={str(T): sysm.at(T)["SUM-03"]["value"] for T in Ts},
               reference={str(T): baseline.run_reference(scenarios.with_period(scn, T))["SUM-03"]["value"] for T in Ts}, knots=rows)
    res["values_vs_reference_max_rel"] = max(abs(v["C"] - res["reference"][str(v["T"])]) / max(abs(res["reference"][str(v["T"])]), 1.0)
                                             for v in res["values"])
    res["n_provenance_entries"] = sum(len(c["provenance"]) for r in rows for c in r["contributions"])
    print(set_name, label, "terms", len(can.terms), "knots", len(rows), "provenance entries", res["n_provenance_entries"],
          "contributions vs merged bad", n_bad, "C vs reference max rel %.1e" % res["values_vs_reference_max_rel"], flush=True)
    return res


def main(outp, set_name, index, Ts):
    baseline.assert_frozen()
    baseline.load()
    res = one(set_name, index, Ts)
    json.dump(res, open(outp, "w"), indent=1, ensure_ascii=False)


def main_all(folder):
    baseline.assert_frozen()
    baseline.load()
    os.makedirs(folder, exist_ok=True)
    sets = sets_unified.build(sets_unified.ALL_SETS)
    summary = {}
    for name in sets:
        if not sets[name]:
            continue
        res = one(name, 0, [], sets)
        with gzip.open(os.path.join(folder, name + ".json.gz"), "wt", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False)
        summary[name] = {k: res[k] for k in ("label", "H", "n_terms", "n_knots", "n_provenance_entries", "contributions_vs_merged_bad",
                                             "values_vs_reference_max_rel")}
        summary[name]["periods"] = [v["T"] for v in res["values"]]
    json.dump(summary, open(os.path.join(folder, "summary.json"), "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "--all-sets":
        main_all(a[1])
    else:
        main(a[0], a[1], int(a[2]), [float(x) for x in a[3:]])
