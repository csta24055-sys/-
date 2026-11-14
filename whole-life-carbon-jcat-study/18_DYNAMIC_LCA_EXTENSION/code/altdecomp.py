"""Stage 2: non-uniqueness of the real-time decomposition (exact).

The end-of-life refrigerant residual R(T) (unit B1-04) is placed at t = T by the meaning of the unit. Its JUMP form
(chapter 11 D-09) is a sum of kernel terms (constant, year cells, atoms, gated year cells), so it can ALSO be read as a
T-independent real-time measure M_R (initial charge at t = 0, negative leak flows, positive resets at the changes)
with  R_jump(T) = M_R([0, T))  for every T. Both readings give the same C(T) for every T (up to the difference
between the jump and the interval form of B1-04, which is zero for exact inputs and rounding-level for float ones).
So C(T) alone does not determine where in real time the emissions lie.

Usage (from this folder): python3 -B altdecomp.py <out.json> [set names...] [--max-scenarios N]
"""
import json
import random
import sys
import time
from fractions import Fraction

sys.dont_write_bytecode = True
import processes as pr                        # noqa: E402  (puts chapter 17 on the path)
import canon                                  # noqa: E402
import timechar as tc                         # noqa: E402
from checks import sets_unified               # noqa: E402
from tstudy import baseline                   # noqa: E402


def main(outp, names, mx):
    baseline.assert_frozen()
    baseline.load()
    from synth import population
    out = []
    t0 = time.time()
    for name, label, scn in tc.scenario_entries(names, mx):
        can = canon.build(canon.make_system(scn, population.BASELINES))
        jt = [canon.Term(t.amp, t.start, t.length, t.gate, "B1-04J*", "B1", t.kind, t.lo, t.hi, t.src) for t in can.unit_terms.get("B1-04J", [])]
        if not jt or not can.inc.get("B1"):
            continue
        masses, dens, Z = tc.realtime(canon.Canon(H=can.H, terms=jt))      # unit B1-04J* is not terminal: read as a flow
        rt = tc.RT(masses, dens)
        it = [t for t in can.terms if t.unit == "B1-04"]
        rng = random.Random(sum(map(ord, label)))
        n_bad, n, worst = 0, 0, 0.0
        neg_flow = sum(1 for a0, b0, r, u, s in dens if r < 0)
        pos_mass = sum(1 for tm, thr, a, u, s in masses if a > 0)
        for _ in range(40):
            T = rng.uniform(0.01, float(can.H))
            n += 1
            Rj = sum((t.amp * t.h(T) for t in jt), Fraction(0))
            n_bad += (rt.M(Fraction(T)) != Rj)                                 # exact identity of the two readings
            Ri = sum((t.amp * t.h(T) for t in it), Fraction(0))
            C = tc.KF(can)(T)
            C_alt = C - Ri + rt.M(Fraction(T))
            if C:
                worst = max(worst, abs(float((C_alt - C) / C)))
        out.append(dict(set=name, label=label, n=n, measure_vs_jump_form_bad=n_bad, max_rel_C_alt_minus_C=worst,
                        negative_flow_segments=neg_flow, positive_masses=pos_mass))
        print("[%s] %-40s n %d bad %d max rel %.1e | neg flows %d pos masses %d | %.0f s" % (name, label[:40], n, n_bad, worst, neg_flow, pos_mass,
                                                                                         time.time() - t0), flush=True)
        json.dump(out, open(outp, "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    a = sys.argv[1:]
    mx = 10 ** 9
    if "--max-scenarios" in a:
        i = a.index("--max-scenarios")
        mx = int(a[i + 1])
        del a[i:i + 2]
    main(a[0], a[1:] or ["dev_edge"], mx)
