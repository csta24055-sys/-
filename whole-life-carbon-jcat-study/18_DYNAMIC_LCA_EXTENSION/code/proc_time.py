"""Stage 2, item 9 of the directive: the time analysis of stage 1 applied to EACH process function e_i(t)
(independent concept model, fictional data).  For every family P01..P17 (and the instances of the event families):

  form      e_i = sum_j m_j delta(t - t_j) + rho_i(t)  (atoms at the switch points, rho piecewise constant): counts
  knots     jumps of the cumulative E_i(t) = M_i([0, t]) (atom times) and kinks (breakpoints of rho)
  periods   event families: per instance, are the event times tau_n = fl(n tau_1) (a renewal lattice)? which periods?
  Laplace   closed form sum m e^{-s t} + sum r (e^{-s a} - e^{-s b}) / s versus Gauss-Legendre on the pieces (float)
  Fourier   coefficients c_n = L_H[e_i](2 pi i n / H) / H of the MEASURE e_i and of the cumulative E_i on [0, H]:
            decay exponent of the dyadic-block envelope max_{2^j <= n < 2^{j+1}} |c_n| (n = 1..512)
            prediction: atoms -> 0 (no decay, a measure), rho with jumps -> -1; cumulative: -1 with atoms, -2 without
  modes     order of the minimal linear recurrence of the annual series (exact, Berlekamp-Massey over Q; max = H/2)

Usage (from this folder): python3 -B proc_time.py <out.json> [set ...] [--max-scenarios N]
"""
import collections
import json
import math
import statistics
import sys
import time
from fractions import Fraction

sys.dont_write_bytecode = True
import numpy as np                                     # noqa: E402

import processes as pr                                 # noqa: E402
import canon                                           # noqa: E402
import timechar as tc                                  # noqa: E402
from checks import sets_unified                        # noqa: E402
from tstudy import baseline                            # noqa: E402

FAM = [f[0] for f in pr.FAMILIES]
NMAX = 512
GL_X, GL_W = np.polynomial.legendre.leggauss(8)


def measure(P, H):
    """Merged atoms {time: amount} (time = switch threshold, 0 for constants) and density breakpoints {t: delta rate}."""
    at = collections.defaultdict(Fraction)
    for tm, thr, a in P.masses:
        at[thr if thr is not None else Fraction(0)] += a
    at = {t: a for t, a in at.items() if a != 0 and t <= H}
    dr = collections.defaultdict(Fraction)
    for a0, b0, r in P.densities:
        dr[a0] += r; dr[b0] -= r
    dr = {t: d for t, d in dr.items() if d != 0}
    return at, dr


def coeffs(at, dr, H, ns):
    """Fourier coefficients on [0, H] of the measure e (atoms + density) and of the cumulative E(t) = e([0, t])."""
    w = 2 * np.pi * ns / H
    ce = np.zeros(len(ns), complex)
    for t, a in at.items():
        ce += float(a) * np.exp(-1j * w * float(t))
    # density: rho(t) = sum_{b <= t} d_b ; integral of rho e^{-iwt} over [0, H] = sum_b d_b (e^{-iwb} - e^{-iwH}) / (iw)
    for b, d in dr.items():
        ce += float(d) * (np.exp(-1j * w * float(b)) - np.exp(-1j * w * H)) / (1j * w)
    ce /= H
    # cumulative: E' = e on (0, H); c_n(E) = (E(H^-) - E(0^+) e^{0}) / (2 pi i n) ... use integration by parts:
    # int_0^H E(t) e^{-iwt} dt = [E(t) e^{-iwt}/(-iw)]_0^H + (1/(iw)) int e(t) e^{-iwt} dt
    E_H = float(sum(at.values(), Fraction(0)) + sum((d * (Fraction(H) - b) for b, d in dr.items()), Fraction(0)))
    E_0 = float(at.get(Fraction(0), Fraction(0)))
    cE = ((E_H * np.exp(-1j * w * H) - E_0) / (-1j * w) + (ce * H - E_0) / (1j * w)) / H     # the atom at 0 is in E(0+)
    return ce, cE


def decay(c, ns, scale):
    """Exponent of the envelope; None if every coefficient is zero to rounding (|c_n| <= 1e-12 scale)."""
    if float(np.max(np.abs(c))) <= 1e-12 * max(scale, 1e-300):
        return "zero"
    js, env = [], []
    j = 0
    while 2 ** (j + 1) <= ns[-1] + 1:
        sel = (ns >= 2 ** j) & (ns < 2 ** (j + 1))
        m = float(np.max(np.abs(c[sel])))
        if m > 0:
            js.append(math.log(2 ** j)); env.append(math.log(m))
        j += 1
    if len(js) < 4:
        return None
    return float(np.polyfit(js[2:], env[2:], 1)[0])      # blocks n >= 4


def laplace_check(at, dr, H, s):
    """Closed form versus Gauss-Legendre (8 points) on every piece cut into sub-intervals of at most 1 year."""
    closed = sum(float(a) * math.exp(-s * float(t)) for t, a in at.items())
    num = closed
    pts = sorted(set([0.0, float(H)] + [float(b) for b in dr if 0 < b < H] + [float(k) for k in range(1, int(H))]))
    rate = 0.0
    bs = sorted(dr)
    k = 0
    for a, b in zip(pts, pts[1:]):
        while k < len(bs) and float(bs[k]) <= a:
            rate += float(dr[bs[k]]); k += 1
        if rate:
            x = (b - a) / 2 * GL_X + (a + b) / 2
            num += rate * float(np.sum(GL_W * np.exp(-s * x)) * (b - a) / 2)
    for b, d in dr.items():
        bb = min(float(b), float(H))
        closed += float(d) * (math.exp(-s * bb) - math.exp(-s * H)) / s
    return abs(closed - num) / max(abs(closed), 1e-300)


def annual_fast(at, dr, H):
    """Exact amount of the realised part in each year [y-1, y) (y = 1..H): atoms by the year of their threshold
    (an atom at t = 0 in year 1), the piecewise-constant density integrated per year (same as processes.annual_series)."""
    out = [Fraction(0)] * H
    for t, a in at.items():
        y = max(1, math.ceil(t))                    # counted in year y when y - 1 < threshold <= y (as annual_series)
        out[min(H, y) - 1] += a
    bs = sorted(dr)
    rate, k = Fraction(0), 0
    pts = sorted(set([Fraction(0), Fraction(H)] + [b for b in bs if 0 < b < H] + [Fraction(j) for j in range(1, H)]))
    for a, b in zip(pts, pts[1:]):
        while k < len(bs) and bs[k] <= a:
            rate += dr[bs[k]]; k += 1
        if rate:
            out[int(math.floor(a))] += rate * (b - a)
    return out


def lattice(P):
    taus = sorted({tm for tm, thr, a in P.masses if thr is not None and a != 0})
    if len(taus) < 2:
        return None
    t1 = float(taus[0])
    return float(taus[0]) if all(float(taus[n]) == (n + 1) * t1 for n in range(len(taus))) else False


def main(outp, names, max_scn):
    baseline.assert_frozen()
    baseline.load()
    from synth import population
    sets = sets_unified.build(names or ["dev_design", "dev_edge", "rep_evaluation", "rep_boundary", "rep_constructed"])
    agg = {p: collections.defaultdict(list) for p in FAM}
    inst = {p: collections.Counter() for p in FAM}
    periods = {p: collections.Counter() for p in FAM}
    ns = np.arange(1, NMAX + 1)
    t0 = time.time()
    n_scn = 0
    for name, cases in sets.items():
        if name in sets_unified.OUTSIDE_DOMAIN:
            continue
        for label, scn, per in cases[:max_scn]:
            sysm = canon.make_system(scn, population.BASELINES)
            can = canon.build(sysm)
            fam, imap = pr.decompose(can, sysm)
            H = can.H
            n_scn += 1
            for p in FAM:
                P = fam[p]
                at, dr = measure(P, H)
                A = agg[p]
                A["terminal_terms"].append(len(P.terminal))
                if not at and not dr:
                    A["empty"].append(1)
                    continue
                A["present"].append(1)
                A["atoms"].append(len(at)); A["negative_atoms"].append(sum(1 for a in at.values() if a < 0))
                A["rate_breaks"].append(len(dr))
                A["atoms_at_0_only"].append(set(at) <= {Fraction(0)})
                ce, cE = coeffs(at, dr, H, ns)
                scale = float(sum(abs(a) for a in at.values()) + sum(abs(d) for d in dr.values()) * H)
                d1, d2 = decay(ce, ns, scale / H), decay(cE, ns, scale)
                for key, d in (("decay_e", d1), ("decay_E", d2)):
                    if d == "zero":
                        A[key + "_zero"].append(1)
                    elif d is not None:
                        A[key].append(d)
                A["laplace_rel"].append(max(laplace_check(at, dr, H, s) for s in (0.05, 0.5)))
                ser = annual_fast(at, dr, H)
                if any(ser):
                    L, _ = tc.berlekamp_massey(ser)
                    A["recurrence_order"].append(L)
            for (p, ik), P in imap.items():
                lat = lattice(P)
                if lat is None:
                    inst[p]["single_or_none"] += 1
                elif lat is False:
                    inst[p]["not_lattice"] += 1
                else:
                    inst[p]["lattice"] += 1
                    periods[p][round(lat, 6)] += 1
            print("[%-14s] %-44s %.0f s" % (name, label[:44], time.time() - t0), flush=True)
    out = dict(n_scenarios=n_scn, families={})
    for p in FAM:
        A = agg[p]
        def med(k):
            return statistics.median(A[k]) if A[k] else None
        out["families"][p] = dict(
            name=dict((f[0], f[1]) for f in pr.FAMILIES)[p], present=len(A["present"]), empty=len(A["empty"]),
            terminal_terms_median=med("terminal_terms"), atoms_median=med("atoms"), atoms_max=max(A["atoms"]) if A["atoms"] else None,
            negative_atoms_total=sum(A["negative_atoms"]), rate_breaks_median=med("rate_breaks"),
            only_atom_at_t0=sum(1 for x in A["atoms_at_0_only"] if x),
            decay_e_median=med("decay_e"), decay_e_range=[min(A["decay_e"]), max(A["decay_e"])] if A["decay_e"] else None,
            decay_e_zero=len(A["decay_e_zero"]),
            decay_E_median=med("decay_E"), decay_E_range=[min(A["decay_E"]), max(A["decay_E"])] if A["decay_E"] else None,
            decay_E_zero=len(A["decay_E_zero"]),
            laplace_rel_max=max(A["laplace_rel"]) if A["laplace_rel"] else None,
            recurrence_order_median=med("recurrence_order"),
            recurrence_order_dist=dict(collections.Counter(A["recurrence_order"]).most_common(8)),
            instances=dict(inst[p]), periods_top=dict(periods[p].most_common(10)), n_distinct_periods=len(periods[p]))
    json.dump(out, open(outp, "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    a = sys.argv[1:]
    mx = 10 ** 9
    if "--max-scenarios" in a:
        i = a.index("--max-scenarios"); mx = int(a[i + 1]); del a[i:i + 2]
    main(a[0], a[1:], mx)
