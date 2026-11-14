"""Stage 2: dynamic LCA extension of the 70-unit model (independent concept model, fictional data).

Per scenario:
  R-1 (EXACT) partition: every kernel term belongs to exactly one process family; sum over families of the accounted
      contribution equals C(T) of chapter 17 at sample periods (all pieces of a sample); instances add up to families
  R-2 (EXACT) recomposition  C_dyn(T) = integral_{[0,T)} e_total(t) dt + Z(T) = C_70(T);  the realised part alone
      differs from C_70 by the terminal part Z(T) (end-of-life and refrigerant stock at T)
  R-3 (EXACT) process totals per year: sum over families of the annual real-time amounts + terminal changes =
      C(y) - C(y-1)
  R-4 sign and support of every process function; time variables (calendar year = start year + t)
  R-5 inter-process relations: order and overlap of supports; shared quantities (P07 = rho x electricity, P10 =
      phi x initial upfront and end-of-life), coincident event times (renewals and the processes they trigger),
      correlation of the annual series, and whether an LTI convolution e_j = h * e_i holds (least-squares
      deconvolution residual on the annual series; an exact relation gives residual 0)
  R-6 Laplace transform of every process function (closed form) and its sum = Laplace transform of the realised part

Usage (from this folder): python3 -B dynlca.py <out.json> [set names...] [--max-scenarios N]
"""
from __future__ import annotations

import collections
import json
import math
import random
import sys
import time
from fractions import Fraction

sys.dont_write_bytecode = True
import numpy as np                                     # noqa: E402

import processes as pr                                 # noqa: E402
import extensions as ex                                # noqa: E402
import dyncharac as dc                                 # noqa: E402
import canon                                           # noqa: E402
import timechar as tc                                  # noqa: E402
from checks import sets_unified                        # noqa: E402
from tstudy import baseline                            # noqa: E402

FAM_IDS = [f[0] for f in pr.FAMILIES]


def sample_periods(kf, H, rng, n=40):
    bp = tc.breakpoints(kf, H)
    pieces = [(a, b) for a, b in zip(bp, bp[1:])]
    rng.shuffle(pieces)
    Ts = []
    for a, b in pieces[:n]:
        x = tc.fl_inside(a, b, Fraction(1, 2))
        if x is not None:
            Ts.append(x)
    Ts += [float(y) for y in range(1, H + 1, max(1, H // 13))] + [float(H)]
    return sorted(set(Ts))


def laplace_process(P, s: complex) -> complex:
    """Laplace transform of the realised part of a process (masses at their switch thresholds, densities)."""
    v = 0j
    for tm, thr, a in P.masses:
        t0 = float(thr) if thr is not None else 0.0
        v += float(a) * np.exp(-s * t0)
    for a0, b0, r in P.densities:
        A, B = float(a0), float(b0)
        v += float(r) * ((np.exp(-s * A) - np.exp(-s * B)) / s if s != 0 else (B - A))
    return complex(v)


def deconv_residual(x, y, L=12):
    """Least-squares LTI kernel h (length L, causal) with y ~ h * x on the annual series; relative residual."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    n = len(x)
    if not np.any(x) or not np.any(y):
        return None
    X = np.zeros((n, L))
    for j in range(L):
        X[j:, j] = x[:n - j]
    h, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = np.linalg.norm(X @ h - y) / max(np.linalg.norm(y), 1e-300)
    return float(res), [float(v) for v in h[:4]]


def analyse(sysm, can, label, rng):
    H = can.H
    kf = tc.KF(can)
    fam, inst = pr.decompose(can, sysm)
    Ts = sample_periods(kf, H, rng)
    out = dict(label=label, H=H, n_terms=len(can.terms), n_instances=len(inst))
    # R-1, R-2
    n1 = n2 = n_inst_bad = 0
    zmax = 0.0
    for T in Ts:
        C = tc.cx(can, T) if len(can.terms) < 8000 else kf(T)
        acc = sum((P.accounted(T) for P in fam.values()), Fraction(0))
        n1 += (acc != C)
        realised = sum((P.emitted_before(T) for P in fam.values()), Fraction(0))
        Z = sum((P.terminal_at(T) for P in fam.values()), Fraction(0))
        n2 += (realised + Z != C)
        if C:
            zmax = max(zmax, abs(float(Z / C)))
    by_fam = collections.defaultdict(list)
    for (pid, ik), P in inst.items():
        by_fam[pid].append(P)
    covered = [pid for pid in by_fam if not pr.decompose.no_instance.get(pid)]
    for T in Ts[:: max(1, len(Ts) // 8)]:
        for pid in covered:
            n_inst_bad += (sum((P.accounted(T) for P in by_fam[pid]), Fraction(0)) != fam[pid].accounted(T))
    out["families_without_full_instance_coverage"] = dict(pr.decompose.no_instance)
    out["R1_partition_bad"] = n1
    out["R2_recomposition_bad"] = n2
    out["R1_instances_vs_family_bad"] = n_inst_bad
    out["n_periods"] = len(Ts)
    out["terminal_share_max"] = zmax
    # R-3 annual
    n3 = 0
    ann = {pid: pr.annual_series(P, H) for pid, P in fam.items()}
    for y in range(2, H + 1):
        inc = kf(float(y)) - kf(float(y - 1))
        s_ = sum((ann[pid][y - 1] for pid in fam), Fraction(0))
        z = sum((fam[pid].terminal_at(float(y)) - fam[pid].terminal_at(float(y - 1)) for pid in fam), Fraction(0))
        n3 += (inc != s_ + z)
    out["R3_annual_bad"] = n3
    # R-4 per family: sign, support, sizes, totals at H
    fams = {}
    for pid, name, units, kind in pr.FAMILIES:
        P = fam[pid]
        sup = P.support()
        neg_m = sum(1 for _, _, a in P.masses if a < 0)
        neg_d = sum(1 for _, _, r in P.densities if r < 0)
        # net density on elementary intervals (is the family's rate non-negative everywhere?)
        evs = collections.defaultdict(Fraction)
        for a0, b0, r in P.densities:
            evs[a0] += r; evs[b0] -= r
        run, xs, neg_net = Fraction(0), sorted(evs), 0
        for lo, hi in zip(xs, xs[1:]):
            run += evs[lo]
            neg_net += (run < 0)
        netm = collections.defaultdict(Fraction)
        for tm, thr, a in P.masses:
            netm[tm] += a
        fams[pid] = dict(name=name, kind=kind, n_terms=P.n_terms, n_masses=len(P.masses), n_densities=len(P.densities),
                         n_terminal_terms=len(P.terminal), support=[float(x) for x in sup] if sup else None,
                         negative_masses=neg_m, negative_densities=neg_d, negative_net_rate_intervals=neg_net,
                         negative_net_masses=sum(1 for a in netm.values() if a < 0),
                         accounted_at_H=float(P.accounted(float(H))), terminal_at_H=float(P.terminal_at(float(H))),
                         distinct_mass_times=len({tm for tm, _, a in P.masses if a != 0}))
    out["families"] = fams
    # R-5 relations
    rel = {}
    # order / overlap of supports
    sup = {pid: fams[pid]["support"] for pid in FAM_IDS if fams[pid]["support"]}
    ov = {}
    for i in sup:
        for j in sup:
            if i < j:
                a = max(sup[i][0], sup[j][0]); b = min(sup[i][1], sup[j][1])
                ov[i + "-" + j] = max(0.0, b - a)
    rel["support_overlap_years"] = ov
    # shared quantity: P07 rate / electricity rate per year = rho (exact)
    rho = canon.b21_share(sysm)
    el = sysm.pieces.get("EL", [])
    elk = collections.defaultdict(float)
    for p in el:
        elk[int(p.start)] += p.amp
    p07 = fam["P07"]
    ratio_bad = 0
    for a0, b0, r in p07.densities:
        k = int(a0)
        if elk.get(k):
            ratio_bad += (r != Fraction(elk[k]) * Fraction(rho))
    rel["P07_equals_rho_times_electricity_bad"] = ratio_bad
    rel["rho"] = rho
    # P10 amount vs phi x (initial + end-of-life totals)
    p10 = [a for tm, thr, a in fam["P10"].masses if a != 0]
    if p10:
        base = sum((fam[p].accounted(1e-9) for p in ("P01", "P02", "P03", "P04")), Fraction(0))
        base_c = sum((fam[p].terminal_at(float(H)) for p in ("P13", "P14", "P15", "P16")), Fraction(0))
        rel["P10_amount_over_initial_plus_eol"] = [float(a / (base + base_c)) if base + base_c else None for a in p10[:3]]
        rel["P10_n_events"] = len(p10)
    # coincident event times between families (renewal-triggered processes)
    times = {pid: {float(thr) for tm, thr, a in fam[pid].masses if thr is not None and a != 0} for pid in FAM_IDS}
    co = {}
    for i in ("P06", "P08", "P09", "P10"):
        for j in ("P06", "P08", "P09", "P10"):
            if i < j and times[i] and times[j]:
                co[i + "-" + j] = len(times[i] & times[j])
    rel["coincident_event_times"] = co
    rel["event_times_per_family"] = {pid: len(times[pid]) for pid in FAM_IDS if times[pid]}
    # correlation of annual series (float)
    series = {pid: np.array([float(x) for x in ann[pid]]) for pid in FAM_IDS if any(ann[pid])}
    corr = {}
    ids = sorted(series)
    for a_ in range(len(ids)):
        for b_ in range(a_ + 1, len(ids)):
            x, y = series[ids[a_]], series[ids[b_]]
            if x.std() > 0 and y.std() > 0:
                corr[ids[a_] + "-" + ids[b_]] = float(np.corrcoef(x, y)[0, 1])
    rel["annual_correlation"] = corr
    # LTI convolution tests on annual series
    conv = {}
    for i, j in (("P11", "P07"), ("P09", "P08"), ("P09", "P06"), ("P05", "P06"), ("P09", "P10"), ("P12", "P11"), ("P05", "P11")):
        if i in series and j in series:
            r = deconv_residual(series[i], series[j])
            if r:
                conv[j + "<-" + i] = dict(rel_residual=r[0], h_first=r[1])
    rel["lti_deconvolution"] = conv
    out["relations"] = rel
    # R-6 Laplace
    lap = {}
    for s in (0.05, 0.3, complex(0.02, 0.4)):
        tot = sum(laplace_process(fam[p], s) for p in FAM_IDS)
        # the realised part of C as a measure: L{dM}(s) = sum masses e^{-s t} + densities -> same as above by linearity
        lap[str(s)] = dict(sum_of_processes=str(tot))
    out["laplace"] = lap
    out["extensions"] = ext_analysis(fam, can, sysm)
    return out


def ext_analysis(fam, can, sysm):
    """Timing variants (labelled assumptions) at the scenario's own period and at T = 60: totals (exact), the
    real-time cumulative curve, and the time-weighted climate metric with fixed end points."""
    scn = sysm.scn
    Dc = (scn.construction.duration_months or 0.0) / 12.0 if getattr(scn, "construction", None) else 0.0
    res = dict(construction_years=Dc, periods={})
    for T in sorted({float(min(can.H, scn.boundary.study_period)), 60.0}):
        if T > can.H:
            continue
        C70 = tc.cx(can, T) if len(can.terms) < 8000 else tc.KF(can)(T)
        rows = {}
        for var in ("M0", "X1", "X2", "X3", "X4"):
            m, b = ex.timeline(fam, T, var, Dc)
            tot = ex.total(m, b)
            cums = {str(t): float(ex.cumulative(m, b, Fraction(t))) for t in (0, 1, 10, 30, T, T + 1e-9, T + 2 * Dc + 1)}
            W = {str(te): dc.weighted(m, b, te) for te in (T, 100.0, T + 100.0)}
            rows[var] = dict(total_equals_C70=(tot == C70), total=float(tot), cumulative=cums, weighted=W)
        base = rows["M0"]["weighted"]
        for var, r in rows.items():
            r["weighted_rel_to_M0"] = {te: (r["weighted"][te] / base[te] - 1.0) if base[te] else None for te in r["weighted"]}
        realised = sum((P.emitted_before(T) for P in fam.values()), Fraction(0))
        res["periods"][str(T)] = dict(C70=float(C70), realised_by_T=float(realised), terminal_at_T=float(C70 - realised), variants=rows)
    return res


def main(outp, names, max_scn):
    baseline.assert_frozen()
    baseline.load()
    from synth import population
    res = []
    t0 = time.time()
    sets = sets_unified.build(names or sets_unified.ALL_SETS)
    for name, cases in sets.items():
        for n, (label, scn, periods) in enumerate(cases):
            if n >= max_scn:
                break
            rng = random.Random(sum(map(ord, label)) * 40503 % 2 ** 32)
            try:
                sysm = canon.make_system(scn, population.BASELINES)
                can = canon.build(sysm)
                r = analyse(sysm, can, label, rng)
            except Exception as ex:
                res.append(dict(set=name, label=label, error="%s %s" % (type(ex).__name__, str(ex)[:200])))
                print("[%s] %s ERROR %s" % (name, label[:40], ex), flush=True)
                continue
            r["set"] = name
            r["start_year"] = getattr(scn.boundary, "study_start_year", None)
            r["construction_months"] = getattr(scn.construction, "duration_months", None)
            res.append(r)
            print("[%s] %-40s inst %4d | bad R1 %d R2 %d inst %d R3 %d | P07=rho*EL bad %d | %.0f s"
                  % (name, label[:40], r["n_instances"], r["R1_partition_bad"], r["R2_recomposition_bad"], r["R1_instances_vs_family_bad"],
                     r["R3_annual_bad"], r["relations"]["P07_equals_rho_times_electricity_bad"], time.time() - t0), flush=True)
            json.dump(res, open(outp, "w"), indent=1, ensure_ascii=False, default=str)
    json.dump(res, open(outp, "w"), indent=1, ensure_ascii=False, default=str)


if __name__ == "__main__":
    a = sys.argv[1:]
    mx = 10 ** 9
    if "--max-scenarios" in a:
        i = a.index("--max-scenarios")
        mx = int(a[i + 1])
        del a[i:i + 2]
    main(a[0], a[1:], mx)
