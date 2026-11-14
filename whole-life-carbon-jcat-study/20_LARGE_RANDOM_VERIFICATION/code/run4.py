"""Stage 4: large random verification of the unified time theory (independent concept model, fictional data).

For every scenario of the declared distribution (gen4.py) and its 5 study periods:
  V1  ideal equation (exact knot form, chapter 17) vs the frozen reference calculation: SUM-03
  V2  the 14 stage values (X-02 by_stage);  V3  the 22 unit values that enter SUM-03
  V4  process recomposition (chapter 18): sum over the 17 process families of (realised part + terminal part)
      equals C(T) EXACTLY (rational arithmetic)
  V5  knot form = sum of the kernel terms EXACTLY (scenarios with < 8000 terms, every period)
  V6  per scenario: Laplace transform closed form vs Gauss-Legendre integration of the pieces (float, recorded)
  V7  per scenario: Fourier coefficients conjugate symmetric (complex -> real) and the partial sum S_64(T) error
      (an APPROXIMATION: recorded, never counted as a pass)
  V8  shared quantities: P07 = rho x electricity (exact)
  negative controls (deliberately wrong equations evaluated on the same pairs; each must be detected):
      NC1 events counted when tau <= T (no strict rule)      NC2 density amplitude a*H used as a rate
      NC3 B6 always minus B2-01 (no stage predicate beta)     NC4 sign of the event-year corrections flipped
      NC5 B1-04 jump form instead of the interval form        NC6 year cells shifted by one year
      NC7 Fourier partial sum S_64 used as the value          NC8 terminal part Z(T) omitted
Comparison: numbers relative 1e-9, a reference of exactly 0 must be 0 (chapter 11). Pairs outside the reference's
validity domain (scenarios.valid_domain) are counted apart; stratum D is compared without that filter (as chapter 11
does for defect sets) and reported apart.

Chunks of CHUNK scenarios are written to results/chunks/c<first>.json; an existing chunk file is skipped (resume).
Usage (from this folder): python3 -B run4.py <first scenario> <last scenario (exclusive)> [chunk size]
"""
from __future__ import annotations

import collections
import json
import math
import os
import sys
import time
import traceback
from fractions import Fraction

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.normpath(os.path.join(HERE, "..", ".."))
for p in (os.path.join(STUDY, "17_WHOLE_BUILDING_TIME_THEORY", "code"), os.path.join(STUDY, "18_DYNAMIC_LCA_EXTENSION", "code")):
    if p not in sys.path:
        sys.path.insert(0, p)
import numpy as np                                     # noqa: E402

import canon                                           # noqa: E402
import timechar as tc                                  # noqa: E402
import processes as pr                                 # noqa: E402
import gen4                                            # noqa: E402
from tstudy import baseline, scenarios                 # noqa: E402

REL = 1e-9
OUT = os.environ.get("RUN4_OUT", os.path.join(HERE, "..", "results", "chunks"))
NCS = ("NC1", "NC2", "NC3", "NC4", "NC5", "NC6", "NC7", "NC8")


def same(a, b):
    if b == 0.0:
        return a == 0.0
    return abs(a - b) <= REL * abs(b)


class FloatTerms:
    """Vectorised float evaluation of the kernel terms (only for the negative controls)."""

    def __init__(self, terms):
        self.amp = np.array([float(t.amp) for t in terms])
        self.s = np.array([t.start for t in terms])
        self.l = np.array([t.length for t in terms])
        self.g = np.array([t.gate for t in terms])
        self.lo = np.array([t.lo for t in terms])
        self.hi = np.array([t.hi for t in terms])
        self.kind = np.array([t.kind for t in terms])
        self.unit = np.array([t.unit for t in terms])
        self.stage = np.array([t.stage for t in terms])

    def k(self, T, strict=True, shift=0.0, mask=None):
        g = self.g < T * (1.0 - canon.EPS) if strict else self.g <= T
        w = (self.lo < T) & (T <= self.hi)
        x = np.clip(T - self.s - shift, 0.0, None)
        ramp = np.where(self.l > 0, np.minimum(x, self.l), 1.0)
        v = np.where(g & w, ramp, 0.0)
        return v if mask is None else v * mask

    def value(self, T, **kw):
        return math.fsum(self.amp * self.k(T, **kw))


def unit_sum(can, u, T):
    return float(sum((t.amp * t.h(T) for t in can.unit_terms.get(u, [])), Fraction(0)))


def negative_controls(can, ft, T, H, fcoef):
    """Values of the 8 deliberately wrong equations at T (floats)."""
    base = ft.value(T)
    out = {}
    out["NC1"] = ft.value(T, strict=False)
    dens = (ft.kind == "density").astype(float)
    out["NC2"] = base + math.fsum(ft.amp * dens * ft.k(T) * (H - 1.0))
    if can.inc.get("B6") and not can.inc.get("B2"):
        out["NC3"] = base - unit_sum(can, "B2-01", T)
    else:
        out["NC3"] = base
    gc = (ft.kind == "gcell").astype(float)
    out["NC4"] = base - 2.0 * math.fsum(ft.amp * gc * ft.k(T))
    if can.inc.get("B1"):
        out["NC5"] = base - unit_sum(can, "B1-04", T) + unit_sum(can, "B1-04J", T)
    else:
        out["NC5"] = base
    cell = (ft.kind == "cell").astype(float)
    out["NC6"] = base - math.fsum(ft.amp * cell * ft.k(T)) + math.fsum(ft.amp * cell * ft.k(T, shift=1.0))
    ns, cs = fcoef
    out["NC7"] = float(np.real(np.sum(cs * np.exp(2j * math.pi * ns * T / H))))
    term = np.isin(ft.unit, list(pr.TERMINAL)).astype(float)
    out["NC8"] = base - math.fsum(ft.amp * term * ft.k(T))
    return out


def scenario_checks(i, from_pop):
    p = gen4.plan(i)
    rec = dict(i=i, stratum=p["stratum"], size=p["size"], pairs=[], scenario_error=None)
    try:
        scn = gen4.make(p)
    except Exception as ex:
        rec["scenario_error"] = "generate: %s %s" % (type(ex).__name__, str(ex)[:160])
        return rec
    return checks_on(rec, scn, from_pop, lambda can, kf: gen4.resolve_periods(p, scn, sorted({g for g in kf.eg})))


def checks_on(rec, scn, from_pop, periods_of):
    try:
        sysm = canon.make_system(scn, from_pop.BASELINES)
        can = canon.build(sysm)
    except Exception as ex:
        rec["scenario_error"] = "prepare: %s %s" % (type(ex).__name__, str(ex)[:160])
        return rec
    H = float(can.H)
    kf = tc.KF(can)
    Ts = periods_of(can, kf)
    rec["n_terms"], rec["n_event_knots"], rec["H"] = len(can.terms), len(kf.eg), can.H
    fam, inst = pr.decompose(can, sysm)
    ft = FloatTerms(can.terms)
    # per scenario: Laplace / Fourier (float, recorded)
    bp = tc.breakpoints(kf, can.H)
    pieces = []
    cumP, cumQ, k, ks = kf.A0, Fraction(0), 0, kf.knots()
    for a, b in zip(bp, bp[1:]):
        while k < len(ks) and ks[k][0] <= a:
            cumP += ks[k][1]; cumQ += ks[k][2]; k += 1
        pieces.append((a, b, cumP, cumQ))
    lap = []
    for s in (0.05, 0.5):
        a_, b_ = tc.laplace_closed(kf, H, s), tc.laplace_pieces(pieces, s)
        lap.append(abs(a_ - b_) / max(abs(a_), 1e-300))
    rec["laplace_max_rel"] = max(lap)
    ns = np.arange(-64, 65)
    cs = tc.laplace_many(kf, H, 2j * math.pi * ns / H) / H
    rec["fourier_conj_max"] = float(max(abs(cs[64 + n] - np.conj(cs[64 - n])) / max(abs(cs[64 + n]), 1e-300) for n in range(1, 65)))
    # shared quantity P07 = rho x electricity (exact)
    rho = canon.b21_share(sysm)
    elk = collections.defaultdict(float)
    for q in sysm.pieces.get("EL", []):
        elk[int(q.start)] += q.amp
    rec["P07_rho_bad"] = sum(1 for a0, b0, r in fam["P07"].densities if elk.get(int(a0)) and r != Fraction(elk[int(a0)]) * Fraction(rho))
    for T in Ts:
        pr_ = dict(T=T)
        cur = scenarios.with_period(scn, T)
        why = scenarios.valid_domain(cur)
        pr_["in_domain"] = not why
        try:
            ref = baseline.run_reference(cur)
        except Exception as ex:
            pr_["ref_error"] = "%s %s" % (type(ex).__name__, str(ex)[:120])
            rec["pairs"].append(pr_)
            continue
        C = kf(T)
        Cf = float(C)
        want = ref["SUM-03"]["value"]
        pr_["v1"] = same(Cf, want)
        pr_["rel"] = 0.0 if Cf == want else abs(Cf - want) / max(abs(Cf), abs(want))
        bad_st, n_st = 0, 0
        for st, w in ref["X-02"]["by_stage"].items():
            n_st += 1
            v = float(sum((t.amp * t.h(T) for t in can.stage_terms(st)), Fraction(0))) if len(can.stage_terms(st)) < 4000 else float(tc.KF(can, st)(T))
            bad_st += not same(v, w)
        pr_["v2_bad"], pr_["v2_n"] = bad_st, n_st
        bad_u, n_u = 0, 0
        for u in can.unit_terms:
            if u == "B1-04J":
                continue
            n_u += 1
            bad_u += not same(unit_sum(can, u, T), ref[u]["value"])
        pr_["v3_bad"], pr_["v3_n"] = bad_u, n_u
        acc = sum((P.accounted(T) for P in fam.values()), Fraction(0))
        pr_["v4"] = (acc == C)
        if len(can.terms) < 8000:
            pr_["v5"] = (tc.cx(can, T) == C)
        S64 = float(np.real(np.sum(cs * np.exp(2j * math.pi * ns * T / H))))
        pr_["fourier64_rel"] = abs(S64 - Cf) / max(abs(Cf), 1e-300)
        nc = negative_controls(can, ft, T, H, (ns, cs))
        pr_["nc_detected"] = {k_: (not same(v, want)) for k_, v in nc.items()}
        pr_["nc_applicable"] = {k_: (abs(v - Cf) > 1e-12 * max(abs(Cf), 1.0)) for k_, v in nc.items()}
        rec["pairs"].append(pr_)
    return rec


def main_sets():
    """The 1,293 pairs of the 10 named sets of chapter 11 (inherited), with the stage-4 checks."""
    from checks import sets_unified
    baseline.assert_frozen()
    baseline.load()
    from synth import population
    os.makedirs(OUT, exist_ok=True)
    sets = sets_unified.build(sets_unified.ALL_SETS)
    t0 = time.time()
    for name, cases in sets.items():
        path = os.path.join(OUT, "set_%s.json" % name)
        if os.path.exists(path):
            continue
        recs = []
        for n, (label, scn, periods) in enumerate(cases):
            rec = dict(i=n, stratum="R:" + name + (":outside" if name in sets_unified.OUTSIDE_DOMAIN else ""), size=None, label=label,
                       pairs=[], scenario_error=None)
            try:
                recs.append(checks_on(rec, scn, population, lambda can, kf, periods=periods: [float(T) for T in periods]))
            except Exception:
                rec["scenario_error"] = "checks: " + traceback.format_exc()[-400:]
                recs.append(rec)
        json.dump(recs, open(path, "w"))
        print("set %s: scenarios %d pairs %d | %.0f s" % (name, len(recs), sum(len(r.get("pairs", [])) for r in recs), time.time() - t0), flush=True)


def main(first, last, chunk=100):
    baseline.assert_frozen()
    baseline.load()
    from synth import population
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    for c0 in range(first, last, chunk):
        path = os.path.join(OUT, "c%06d.json" % c0)
        if os.path.exists(path):
            continue
        recs = []
        for i in range(c0, min(last, c0 + chunk)):
            try:
                recs.append(scenario_checks(i, population))
            except Exception:
                recs.append(dict(i=i, scenario_error="checks: " + traceback.format_exc()[-400:]))
        tmp = path + ".tmp"
        json.dump(recs, open(tmp, "w"))
        os.replace(tmp, path)
        n_pairs = sum(len(r.get("pairs", [])) for r in recs)
        bad = sum(1 for r in recs for q in r.get("pairs", []) if q.get("in_domain") and (not q.get("v1", True) or q.get("v2_bad") or q.get("v3_bad") or q.get("v4") is False or q.get("v5") is False))
        errs = sum(1 for r in recs if r.get("scenario_error"))
        print("chunk %d: scenarios %d pairs %d bad(in domain) %d scenario errors %d | %.0f s" % (c0, len(recs), n_pairs, bad, errs, time.time() - t0), flush=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "--sets":
        main_sets()
    else:
        main(int(a[0]), int(a[1]), int(a[2]) if len(a) > 2 else 100)
