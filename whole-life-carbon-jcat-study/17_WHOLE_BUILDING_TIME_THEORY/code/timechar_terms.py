"""Stage 1, supplement after the independent review: the time theorems checked against the KERNEL SUM itself
(timechar.cx: every term evaluated exactly at the float T), not against the knot form (whose piecewise structure holds
by construction). One analysis per DISTINCT canonical function (duplicates across the sets are skipped by a hash of
the terms). Every count reported is the number of comparisons actually executed.

  S1  TH-1/TH-3 on the kernel sum: on up to 100 random pieces per function, 3 interior floats are collinear and the
      fitted coefficients equal the prefix sums of the knot coefficients                                   (EXACT)
  S2  TH-2 on the kernel sum: on up to 40 random adjacent piece pairs, the jump and the slope change at the common
      breakpoint equal p + q sw and q                                                                       (EXACT)
  S3  the kernel sum equals the knot form AT the breakpoints and at the floats next to them (up to 60 breakpoints:
      integers and switch points)                                                                           (EXACT)
  S4  integer-time events: at a lattice knot K with an event at K, the jump of all terms OTHER than B1-04 is exactly
      0, and the jump of the B1-04 interval form at K equals the jump of the independently built B1-04 jump form at
      sw(K) (two different sets of float coefficients: difference relative to the residual R(K), bound 1e-12)
  S5  per stage and per unit: the knot form of the stage's / unit's terms equals the kernel sum (EXACT, 10 periods)
  S6  TH-4 against the kernel sum: M([0,T)) + Z(T) = kernel sum (EXACT, the S1 sample midpoints)
  S7  C(0+) = knot form just above 0 (not A0); Fourier partial sum (512 terms) at T = 0 vs (C(0+) + C(H))/2 (FLOAT);
      closed-form Fourier coefficients at NEGATIVE n vs Gauss-Legendre integration of the pieces (FLOAT)

Usage (from this folder): python3 -B timechar_terms.py <out.json> [set names...]
"""
from __future__ import annotations

import collections
import hashlib
import json
import math
import random
import sys
import time
from fractions import Fraction

sys.dont_write_bytecode = True
import numpy as np                                     # noqa: E402

import canon                                           # noqa: E402
import timechar as tc                                  # noqa: E402
from checks import sets_unified                        # noqa: E402
from tstudy import baseline                            # noqa: E402


def term_hash(can):
    h = hashlib.sha256()
    for t in can.terms:
        h.update(repr((t.amp.numerator, t.amp.denominator, t.start, t.length, t.gate, t.lo, t.hi, t.stage)).encode())
    return h.hexdigest()


def sub_canon(can, terms):
    c = canon.Canon(H=can.H, terms=list(terms))
    return c


def analyse(can, rng):
    H = can.H
    kf = tc.KF(can)
    bp = tc.breakpoints(kf, H)
    ks = kf.knots()
    pos_p, pos_q = collections.defaultdict(Fraction), collections.defaultdict(Fraction)
    for pos, p, q, kd, _ in ks:
        pos_p[pos] += p; pos_q[pos] += q
    # theory coefficients of every breakpoint interval
    pieces = []
    cumP, cumQ, k = kf.A0, Fraction(0), 0
    for a, b in zip(bp, bp[1:]):
        while k < len(ks) and ks[k][0] <= a:
            cumP += ks[k][1]; cumQ += ks[k][2]; k += 1
        pieces.append((a, b, cumP, cumQ))
    r = collections.Counter()
    f = lambda x: tc.cx(can, x)
    # S1 + S6
    masses, dens, Zt = tc.realtime(can)
    rt = tc.RT(masses, dens)
    zkf = tc.KF(canon.Canon(H=can.H, terms=Zt))
    idx = list(range(len(pieces)))
    rng.shuffle(idx)
    for i in idx[:100]:
        a, b, P, Q = pieces[i]
        fit = tc.affine_on(f, a, b)
        if fit is None:
            r["s1_skipped_no_interior_floats"] += 1
            continue
        al, be, ok = fit
        r["s1_checked"] += 1
        r["s1_bad"] += (not ok) or al != P or be != Q
        x = tc.fl_inside(a, b, Fraction(1, 2))
        r["s6_checked"] += 1
        r["s6_bad"] += (rt.M(Fraction(x)) + zkf(x) != f(x))
    # S2
    adj = [i for i in range(len(pieces) - 1)]
    rng.shuffle(adj)
    for i in adj[:40]:
        a0, b0, P0, Q0 = pieces[i]
        a1, b1, P1, Q1 = pieces[i + 1]
        L = tc.affine_on(f, a0, b0)
        R = tc.affine_on(f, a1, b1)
        if L is None or R is None:
            r["s2_skipped_no_interior_floats"] += 1
            continue
        r["s2_checked"] += 1
        J = (R[0] - L[0]) + (R[1] - L[1]) * b0
        r["s2_bad"] += (J != pos_p[b0] + pos_q[b0] * b0) or (R[1] - L[1] != pos_q[b0]) or not (L[2] and R[2])
    # S3 at the breakpoints and next to them
    bps = [x for x in bp if 0 < x <= H]
    rng.shuffle(bps)
    for x in bps[:60]:
        T = float(x)
        for y in (T, math.nextafter(T, -math.inf), math.nextafter(T, math.inf)):
            if 0 < y <= H:
                r["s3_checked"] += 1
                r["s3_bad"] += (f(y) != kf(y))
    # S4 integer-time events
    b14 = [t for t in can.terms if t.unit == "B1-04"]
    rest = [t for t in can.terms if t.unit != "B1-04"]
    cr, cb = sub_canon(can, rest), sub_canon(can, b14)
    jt = [canon.Term(t.amp, t.start, t.length, t.gate, "B1-04J", "B1", t.kind, t.lo, t.hi, t.src) for t in can.unit_terms.get("B1-04J", [])] \
        if can.inc.get("B1") else []
    cj = sub_canon(can, jt)
    ints = sorted({int(round(g)) for g in kf.eg if abs(g - round(g)) <= 1e-9 * max(1.0, abs(g)) and 1 <= round(g) < H})
    rng.shuffle(ints)
    rel_s4 = []
    for K in ints[:20]:
        Kf = Fraction(K)
        sw = Fraction(tc.tswitch(float(K)))                        # the event at K switches just after K
        left = (Kf - Fraction(1, 1000), Kf)
        mid = (Kf, sw)                                            # the sliver between the lattice knot and the switch
        right = (sw, sw + Fraction(1, 1000))
        def jump(cn, a_, b_, c_, at):
            L_ = tc.affine_on(lambda x: tc.cx(cn, x), *a_)
            R_ = tc.affine_on(lambda x: tc.cx(cn, x), b_, c_)
            if L_ is None or R_ is None:
                return None
            return (R_[0] - L_[0]) + (R_[1] - L_[1]) * at
        jr = jump(cr, left, mid[0], mid[1], Kf)
        if jr is None:
            r["s4_skipped"] += 1
            continue
        r["s4_checked"] += 1
        r["s4_other_jump_bad"] += (jr != 0)                       # every other unit is continuous at the lattice knot
        if b14 and jt:
            jb = jump(cb, left, mid[0], mid[1], Kf)                 # interval form: resets at K
            jj = jump(cj, mid, right[0], right[1], sw)              # jump form: resets at sw(K)
            if jb is not None and jj is not None:
                scale = max(abs(float(tc.cx(cb, float(K)))), 1e-300)      # size of the residual itself
                rel = abs(float(jb - jj)) / scale                        # interval-form rounding jumps are ~1e-16 of it
                rel_s4.append(rel)
                r["s4_b14_compared"] += 1
                r["s4_b14_resets"] += (abs(float(jj)) > 1e-9 * scale)
                r["s4_b14_bad"] += (rel > 1e-12)
    # S5 per stage and per unit
    Ts = [rng.uniform(0.01, float(H)) for _ in range(10)]
    for st in canon.STAGES:
        ts = can.stage_terms(st)
        if not ts:
            continue
        kfs = tc.KF(can, st)
        for T in Ts:
            r["s5_stage_checked"] += 1
            r["s5_stage_bad"] += (kfs(T) != tc.cx(can, T, st))
    for u, ts in can.unit_terms.items():
        if not ts:
            continue
        cu = sub_canon(can, ts)
        kfu = tc.KF(cu)
        for T in Ts:
            r["s5_unit_checked"] += 1
            r["s5_unit_bad"] += (kfu(T) != tc.cx(cu, T))
    # S7
    Hf = float(H)
    c0p = float(kf(math.ulp(0.0)))
    cH = float(kf(Hf))
    N = 512
    nall = np.arange(-N, N + 1)
    cs = tc.laplace_many(kf, Hf, 2j * math.pi * nall / Hf) / Hf
    S0 = float(np.real(np.sum(cs)))
    mid = (c0p + cH) / 2
    out = dict(counts=dict(r), s4_max_rel=max(rel_s4, default=0.0), C0plus=c0p, A0=float(kf.A0),
               boundary_rel_to_midpoint=abs(S0 - mid) / max(abs(cH), 1e-300))
    lp = [(a, b, P, Q) for a, b, P, Q in pieces]
    neg = []
    for n in (-1, -5, -37):
        s = 2j * math.pi * n / Hf
        a_ = tc.laplace_closed(kf, Hf, s)
        b_ = tc.laplace_pieces(lp, s, 16)
        neg.append(abs(a_ - b_) / max(abs(a_), 1e-300))
    out["fourier_negative_n_max_rel"] = max(neg)
    return out


def main(outp, names):
    baseline.assert_frozen()
    baseline.load()
    from synth import population
    seen = {}
    res = []
    t0 = time.time()
    for name, label, scn in tc.scenario_entries(names or sets_unified.ALL_SETS, 10 ** 9):
        can = canon.build(canon.make_system(scn, population.BASELINES))
        h = term_hash(can)
        if h in seen:
            res.append(dict(set=name, label=label, duplicate_of=seen[h]))
            continue
        seen[h] = label
        rng = random.Random(int(h[:12], 16))
        r = analyse(can, rng)
        r.update(set=name, label=label, n_terms=len(can.terms))
        res.append(r)
        c = collections.Counter(r["counts"])
        bad = sum(v for k, v in c.items() if k.endswith("_bad"))
        print("[%s] %-38s s1 %d s2 %d s3 %d s4 %d/%d s5 %d+%d s6 %d | bad %d | C0+ %.6g (A0 %.6g) mid %.1e | %.0f s"
              % (name, label[:38], c["s1_checked"], c["s2_checked"], c["s3_checked"], c["s4_checked"], c["s4_b14_compared"],
                 c["s5_stage_checked"], c["s5_unit_checked"], c["s6_checked"], bad, r["C0plus"], r["A0"], r["boundary_rel_to_midpoint"],
                 time.time() - t0), flush=True)
        json.dump(res, open(outp, "w"), indent=1, ensure_ascii=False)
    json.dump(res, open(outp, "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
