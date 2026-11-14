"""Stage 1: expansion of the canonical whole-building equation back to the 70-unit model (independent concept
model, fictional data).

For one scenario: every knot of the merged knot form (L5) with its contributions grouped by (unit, stage, kernel
shape), the provenance rows of the masked sum-product (P1), and an exact check that the contributions add up to the
merged coefficients; and C(T) at chosen periods split by stage, unit and role (exact).

Usage (from this folder): python3 -B expand.py <out.json> <set name> <scenario index> [T ...]
"""
import collections
import json
import math
import sys
from fractions import Fraction

sys.dont_write_bytecode = True
import canon                                            # noqa: E402
import timechar as tc                                   # noqa: E402
from checks import sets_unified                         # noqa: E402
from tstudy import baseline                             # noqa: E402

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
            if len(g[3]) < 3:
                g[3].append(t.src)
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


def main(outp, set_name, index, Ts):
    baseline.assert_frozen()
    baseline.load()
    from synth import population
    label, scn, periods = sets_unified.build([set_name])[set_name][index]
    sysm = canon.make_system(scn, population.BASELINES)
    can = canon.build(sysm)
    rows, n_bad = expansion(can)
    Ts = Ts or [float(p) for p in periods]
    res = dict(label=label, H=can.H, n_terms=len(can.terms), n_knots=len(rows), contributions_vs_merged_bad=n_bad,
               values=[split(can, T) for T in Ts], reference={str(T): sysm.at(T)["SUM-03"]["value"] for T in Ts}, knots=rows)
    json.dump(res, open(outp, "w"), indent=1, ensure_ascii=False)
    print(label, "terms", len(can.terms), "knots", len(rows), "contributions vs merged bad", n_bad,
          [(v["T"], v["C"], res["reference"][str(v["T"])]) for v in res["values"]])


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], int(a[2]), [float(x) for x in a[3:]])
