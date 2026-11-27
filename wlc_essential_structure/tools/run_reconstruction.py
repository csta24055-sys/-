"""(e)(g) Whole-building reconstruction with the five families, against the FROZEN reference calculation.

What is independent here: the F3 kernel evaluator, the F5 composition table (re-coded from the published stage
table, 14/07 section 3), the five-destination aggregation, the time-shape classification and all comparisons.
What is reused read-only: the earlier unified system builds the kernel amplitudes (F1/F2/F4 outputs) through
17_WHOLE_BUILDING_TIME_THEORY/code/canon.py; the reference values come from the frozen baseline (09 refcalc).
Nothing in the earlier checkout is modified (python -B, no bytecode).

Usage: python3 -B tools/run_reconstruction.py <foundation_checkout> <out_dir> [set names...]
"""
import collections
import json
import math
import os
import sys
import time
from fractions import Fraction

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import five_families as ff  # noqa: E402

REL = 1e-9
DIRECT = ["A13-01", "A13-03", "A13-04", "X-01", "A4-01", "A4-02", "A5-04", "B1-02", "B1-03", "B1-04", "B2-01",
          "B3-01", "B4-02", "B5-01", "B6-03", "B7-04", "C1-01", "C2-01", "C3-01", "X-14", "C4-01"]
# F5: (stage, unit, sign, beta) -- beta "B2" means [stage B2 is included]
COMP = [("A1-A3", "A13-01", 1, 1), ("A1-A3", "A13-03", 1, 1), ("A1-A3", "A13-04", 1, 1), ("A1-A3", "X-01", 1, 1),
        ("A4", "A4-01", 1, 1), ("A4", "A4-02", 1, 1), ("A5", "A5-04", 1, 1),
        ("B1", "B1-02", 1, 1), ("B1", "B1-03", 1, 1), ("B1", "B1-04", 1, 1), ("B2", "B2-01", 1, 1),
        ("B3", "B3-01", 1, 1), ("B4", "B4-02", 1, 1), ("B5", "B5-01", 1, 1),
        ("B6", "B6-03", 1, 1), ("B6", "B2-01", -1, "B2"), ("B7", "B7-04", 1, 1),
        ("C1", "C1-01", 1, 1), ("C2", "C2-01", 1, 1), ("C3", "C3-01", 1, 1), ("C3", "X-14", 1, 1), ("C4", "C4-01", 1, 1)]
DEST = {"D1 製造・施工(A1-A5)": ("A1-A3", "A4", "A5"), "D2 使用時の物質・機器(B1-B5)": ("B1", "B2", "B3", "B4", "B5"),
        "D3 運用エネルギー(B6)": ("B6",), "D4 運用水・廃棄物(B7)": ("B7",), "D5 解体・廃棄(C1-C4)": ("C1", "C2", "C3", "C4")}
STATE_UNITS = {"B1-02", "B1-03", "B1-04"}


def same(a, b, rel=REL):
    if b is None or a is None:
        return a is None and b is None
    if b == 0.0:
        return abs(a) <= 1e-300
    return abs(a - b) <= rel * abs(b)


def shape_of(unit, kind):
    """time shape of one kernel term (kernel axis) and its amplitude source (state or static)."""
    if kind.startswith(("win", "wev")):
        sh = "TERMINAL(期末の状態)"
    elif kind == "const":
        sh = {"A": "INITIAL(t=0)", "C": "TERMINAL(t=T)"}.get(unit[0], "CONST(other)")
        if unit == "X-14":
            sh = "TERMINAL(t=T)"
        if unit == "X-01":
            sh = "INITIAL(t=0)"
    elif kind in ("cell", "density"):
        sh = "CONTINUOUS(率)"
    elif kind == "atom":
        sh = "EVENT(時点)"
    elif kind == "gcell":
        sh = "GATED(事象で切替わる率)"
    else:
        sh = "?" + kind
    return sh, ("STATE" if unit in STATE_UNITS else "STATIC")


def to_kernel(t):
    return ff.Kernel(t.amp, s=t.start, l=t.length, g=t.gate, lo=t.lo, hi=t.hi)


def main(fnd, out, names):
    code = os.path.join(fnd, "whole-life-carbon-jcat-study", "17_WHOLE_BUILDING_TIME_THEORY", "code")
    sys.path.insert(0, code)
    import canon                                   # noqa: E402  (read-only; sets the research_code path)
    from checks import sets_unified               # noqa: E402
    from tstudy import baseline, scenarios         # noqa: E402
    baseline.assert_frozen()
    baseline.load()
    from synth import population                   # noqa: E402
    sets = sets_unified.build(names or sets_unified.ALL_SETS)
    os.makedirs(out, exist_ok=True)
    R = {}
    unit_shapes = collections.defaultdict(collections.Counter)
    shape_rows = []                                 # per pair: shape totals + SUM-01/02/03 for the rank test
    t0 = time.time()
    for name, cases in sets.items():
        r = collections.Counter()
        ex = []
        check_domain = name not in sets_unified.OUTSIDE_DOMAIN
        for label, scn, periods in cases:
            try:
                sysm = canon.make_system(scn, population.BASELINES)
                can = canon.build(sysm, T_probe=float(periods[0]) if periods else None)
            except Exception as e:  # noqa: BLE001
                r["prepare_failed"] += len(periods)
                ex.append(("PREPARE", label, type(e).__name__, str(e)[:120]))
                continue
            kern = {u: [to_kernel(t) for t in can.unit_terms.get(u, [])] for u in DIRECT}
            for u in DIRECT:
                for t in can.unit_terms.get(u, []):
                    unit_shapes[u][shape_of(u, t.kind)] += 1
            inc = {s: int(bool(v)) for s, v in can.inc.items()}
            for T in periods:
                cur = scenarios.with_period(scn, T)
                if check_domain and scenarios.valid_domain(cur):
                    r["excluded_domain"] += 1
                    continue
                try:
                    ref = baseline.run_reference(cur)
                except Exception:  # noqa: BLE001
                    r["ref_raised"] += 1
                    continue
                r["pairs"] += 1
                V = {u: ff.f3_value(kern[u], T) for u in DIRECT}
                comp = [(s, u, sg, (inc.get("B2", 0) if b == "B2" else b)) for s, u, sg, b in COMP]
                S, C = ff.f5_aggregate(V, comp, inc)
                # (1) unit values of the 21 direct units
                for u in DIRECT:
                    r["unit_checked"] += 1
                    if not same(float(V[u]), ref[u]["value"]):
                        r["unit_bad"] += 1
                        if len(ex) < 30:
                            ex.append(("unit", label, T, u, float(V[u]), ref[u]["value"]))
                # (2) 14 stage values
                for st, w in ref["X-02"]["by_stage"].items():
                    r["stage_checked"] += 1
                    if not same(float(S.get(st, Fraction(0))), w):
                        r["stage_bad"] += 1
                        if len(ex) < 30:
                            ex.append(("stage", label, T, st, float(S.get(st, 0)), w))
                # (3) totals through the five destinations
                D = {d: sum((S.get(s, Fraction(0)) for s in ss), Fraction(0)) for d, ss in DEST.items()}
                dv = list(D.values())
                got = {"SUM-01": dv[0], "SUM-02": dv[0] + dv[1] + dv[4], "SUM-03": sum(dv, Fraction(0))}
                for k, v in got.items():
                    w = ref[k]["value"]
                    r[k + "_checked"] += 1
                    if not same(float(v), w):
                        r[k + "_bad"] += 1
                        if len(ex) < 30:
                            ex.append((k, label, T, float(v), w))
                # (4) time-shape totals (signed, included) for the rank test
                shp = collections.Counter()
                for st, u, sg, b in comp:
                    if not inc.get(st, 0) or not b:
                        continue
                    for t, k in zip(can.unit_terms.get(u, []), kern[u]):
                        shp[shape_of(u, t.kind)[0]] += float(sg * b * k(T))
                shape_rows.append(dict(set=name, label=label, T=T, shapes=dict(shp),
                                       dest={k: float(v) for k, v in D.items()},
                                       SUM01=ref["SUM-01"]["value"], SUM02=ref["SUM-02"]["value"], SUM03=ref["SUM-03"]["value"]))
        R[name] = dict(r, examples=ex)
        print("[%-16s] %s | %.0f s" % (name, dict(r), time.time() - t0), flush=True)
        json.dump(R, open(os.path.join(out, "reconstruction.json"), "w"), indent=1, default=str)
    tot = collections.Counter()
    for v in R.values():
        for k, x in v.items():
            if k != "examples":
                tot[k] += x
    R["TOTAL"] = dict(tot)
    json.dump(R, open(os.path.join(out, "reconstruction.json"), "w"), indent=1, default=str)
    json.dump({u: {"%s|%s" % k: n for k, n in c.items()} for u, c in unit_shapes.items()},
              open(os.path.join(out, "direct_unit_time_shapes.json"), "w"), ensure_ascii=False, indent=1)
    json.dump(shape_rows, open(os.path.join(out, "shape_rows.json"), "w"), ensure_ascii=False)
    print("TOTAL", dict(tot))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
