"""Stage 4: aggregate the chunk files into results/stage4_summary.json (and print the headline numbers).

Statistical statement (only for the DECLARED sampling distribution of gen4.py): if N independent trials show no
failure, the one-sided 95 % upper confidence bound of the failure probability per trial is p <= 1 - 0.05^(1/N)
(exact binomial / Clopper-Pearson with 0 failures; about 3/N). It says nothing about inputs outside the distribution.
The scenarios are independent draws; the 5 periods of one scenario are NOT independent.  The bound that holds without
any assumption on that dependence is the scenario-level one (a scenario fails if any of its cases fails; the per-case
failure probability is at most the per-scenario one).  The per-case bound over all cases is reported only as the value
an independence assumption would give.  No bound is computed for the inherited sets of chapter 11 (R:), which are not
samples of the declared distribution.
Cases whose T could lie in a band (K, sw(tau)] (chapter 17, D minus D') are counted from T alone: a band lies inside
(K, K(1 + 3e-9)] for an integer K >= 1, so a case with T outside every such interval is in D'.  The D' bounds leave
those cases out (conservative: some of them are not in a band).

Usage (from this folder): python3 -B agg4.py [chunk dir]
"""
import collections
import glob
import json
import math
import os
import statistics
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
NCS = ("NC1", "NC2", "NC3", "NC4", "NC5", "NC6", "NC7", "NC8")


def bound(n, k=0):
    """One-sided 95 % upper bound of a binomial probability with k failures in n (Clopper-Pearson for k = 0)."""
    if n == 0:
        return None
    if k == 0:
        return 1.0 - 0.05 ** (1.0 / n)
    # k > 0: bisection on the binomial tail
    lo, hi = k / n, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        cdf = sum(math.comb(n, j) * mid ** j * (1 - mid) ** (n - j) for j in range(k + 1))
        lo, hi = (mid, hi) if cdf > 0.05 else (lo, mid)
    return hi


def sliver_of(i, T):
    """For a failing pair of the random strata: is T inside a band (K, sw(tau)] after an event tau whose switch point lies
    beyond the end K of its year cell (integer times and times just below an integer; the domain hole of chapter 17,
    D minus D')?  The scenario is regenerated (gen4 is deterministic in i)."""
    for p in (os.path.join(HERE, "..", "..", "17_WHOLE_BUILDING_TIME_THEORY", "code"), HERE):
        if p not in sys.path:
            sys.path.insert(0, p)
    import canon
    import timechar as tc
    import gen4
    from tstudy import baseline
    baseline.load()
    from synth import population
    scn = gen4.make(gen4.plan(i))
    can = canon.build(canon.make_system(scn, population.BASELINES))
    D = 1.0 - canon.EPS
    out = []
    for g in sorted({t.gate for t in can.terms if t.kind in ("atom", "gcell", "wev0", "wev1")}):
        K = math.ceil(g * D)                      # end of the event's year cell
        sw = tc.tswitch(g)
        if K < sw and K < T <= sw:                # switch point beyond the cell end (integer or just below an integer)
            out.append(g)
    return out


def maybe_band(T):
    """Necessary condition for T to lie in a band (K, sw(tau)] after an event whose switch point passes the end K of its
    year cell: K < T <= K (1 + 3e-9) for an integer K >= 1 (sw(tau) <= K / fl(1 - eps)^2 for such events)."""
    K = math.floor(T)
    return K >= 1 and T > K and T <= K * (1.0 + 3e-9)


def q(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, max(0, int(math.ceil(p * len(xs))) - 1))] if xs else None


def main(cdir):
    recs = []
    for f in sorted(glob.glob(os.path.join(cdir, "c*.json"))) + sorted(glob.glob(os.path.join(cdir, "set_*.json"))):
        recs += json.load(open(f))
    by = collections.defaultdict(lambda: collections.Counter())
    rels = collections.defaultdict(list)
    four = collections.defaultdict(list)
    lap, conj = [], []
    nc_app = collections.defaultdict(collections.Counter)
    nc_det = collections.defaultdict(collections.Counter)
    errors = collections.Counter()
    examples = []
    for r in recs:
        st = r.get("stratum", "?")
        c = by[st]
        c["scenarios"] += 1
        if r.get("scenario_error"):
            c["scenario_errors"] += 1
            errors[r["scenario_error"].split(":")[0] + ": " + r["scenario_error"].split(":")[1].strip().split(" ")[0]] += 1
            continue
        c["terms"] += r.get("n_terms", 0)
        c["P07_rho_bad"] += r.get("P07_rho_bad", 0)
        if r.get("laplace_max_rel") is not None:
            lap.append(r["laplace_max_rel"])
        if r.get("fourier_conj_max") is not None:
            conj.append(r["fourier_conj_max"])
        for p in r["pairs"]:
            c["pairs"] += 1
            if "ref_error" in p:
                c["ref_errors"] += 1
                continue
            outside_set = (st == "D") or st.endswith(":outside")        # compared without the domain filter, reported apart
            dom = p["in_domain"] or outside_set
            key = "in" if p["in_domain"] else ("outside_compared" if outside_set else "excluded")
            c["pairs_" + key] += 1
            if not dom:
                continue
            fail = (not p["v1"]) or p["v2_bad"] or p["v3_bad"] or (not p["v4"]) or (p.get("v5") is False)
            c["checked"] += 1
            c["fail"] += bool(fail)
            c["v1_fail"] += (not p["v1"]); c["v2_fail"] += bool(p["v2_bad"]); c["v3_fail"] += bool(p["v3_bad"])
            c["v4_fail"] += (not p["v4"]); c["v5_fail"] += (p.get("v5") is False); c["v5_checked"] += ("v5" in p)
            c["stage_values"] += p["v2_n"]; c["unit_values"] += p["v3_n"]
            if fail and len(examples) < 30:
                examples.append(dict(i=r["i"], stratum=st, T=p["T"], v1=p["v1"], rel=p["rel"], v2=p["v2_bad"], v3=p["v3_bad"], v4=p["v4"], v5=p.get("v5")))
            rels[st].append(p["rel"])
            if st.startswith("R:") or st == "D":
                pass                                   # Fourier statistics: declared random strata in the domain only
            elif p.get("fourier64_rel") is not None and p["fourier64_rel"] > 1e100:
                c["fourier_C_zero"] += 1               # C(T) = 0: the relative error is undefined (run4 divides by 1e-300)
            elif p.get("fourier64_rel") is not None:
                band = "T<1" if p["T"] < 1 else "1<=T<10" if p["T"] < 10 else "T>=10"
                four[band].append(p["fourier64_rel"])
            for k in NCS:
                if p["nc_applicable"].get(k):
                    nc_app[st][k] += 1
                    nc_det[st][k] += bool(p["nc_detected"].get(k))
    out = dict(n_scenarios=len(recs), strata={}, errors=dict(errors), examples=examples)
    tot = collections.Counter()
    for st, c in sorted(by.items()):
        d = dict(c)
        rs = rels[st]
        d["rel_median"], d["rel_p99"], d["rel_max"] = statistics.median(rs) if rs else None, q(rs, 0.99), max(rs) if rs else None
        d["upper95_failure_probability"] = None if (st.startswith("R:") or st == "D") else bound(c["checked"], c["fail"])   # cases as if independent
        if not (st.startswith("R:") or st == "D"):     # per stratum, scenario level (holds without independence of the periods)
            scn = [r for r in recs if r.get("stratum") == st and not r.get("scenario_error")
                   and any(p.get("in_domain") and "ref_error" not in p for p in r.get("pairs", []))]
            nf = sum(1 for r in scn if any(p.get("in_domain") and "ref_error" not in p and
                                           ((not p["v1"]) or p["v2_bad"] or p["v3_bad"] or (not p["v4"]) or (p.get("v5") is False))
                                           for p in r["pairs"]))
            d["scenarios_in_domain"], d["scenarios_failing"] = len(scn), nf
            d["upper95_failure_probability_per_scenario"] = bound(len(scn), nf)
        d["nc"] = {k: dict(applicable=nc_app[st][k], detected=nc_det[st][k]) for k in NCS}
        out["strata"][st] = d
        tot.update(c)
    allrel = [x for v in rels.values() for x in v]
    out["total"] = dict(tot)
    out["total"]["rel_max"] = max(allrel) if allrel else None
    out["total"]["rel_p99"] = q(allrel, 0.99)
    rand = [s for s in by if not s.startswith("R:")]
    in_dom = sum(by[s]["pairs_in"] for s in rand)
    fail_in = sum(1 for r in recs if not str(r.get("stratum", "")).startswith("R:") for p in r.get("pairs", [])
                  if p.get("in_domain") and "ref_error" not in p and
                  ((not p["v1"]) or p["v2_bad"] or p["v3_bad"] or (not p["v4"]) or (p.get("v5") is False)))
    out["total"]["random_strata"] = rand
    out["total"]["in_domain_pairs"] = in_dom
    out["total"]["in_domain_failures"] = fail_in
    out["total"]["upper95_failure_probability_in_domain"] = bound(in_dom, fail_in)        # only if cases were independent
    # D': cases whose T cannot lie in a band (necessary condition from T alone)
    isfail = lambda p: (not p["v1"]) or p["v2_bad"] or p["v3_bad"] or (not p["v4"]) or (p.get("v5") is False)
    mb = [(r, p) for r in recs if not str(r.get("stratum", "")).startswith("R:") for p in r.get("pairs", [])
          if p.get("in_domain") and "ref_error" not in p and maybe_band(p["T"])]
    out["total"]["in_domain_pairs_maybe_in_band"] = len(mb)
    out["total"]["in_domain_failures_maybe_in_band"] = sum(1 for r, p in mb if isfail(p))
    out["total"]["maybe_in_band_by_stratum"] = dict(collections.Counter(r.get("stratum") for r, p in mb))
    dp_n = in_dom - len(mb)
    dp_f = fail_in - out["total"]["in_domain_failures_maybe_in_band"]
    out["total"]["D_prime_pairs"] = dp_n
    out["total"]["D_prime_failures"] = dp_f
    out["total"]["upper95_failure_probability_D_prime_if_independent"] = bound(dp_n, dp_f)
    sn = sf = 0
    for r in recs:
        if str(r.get("stratum", "")).startswith("R:") or r.get("scenario_error") or r.get("stratum") == "D":
            continue
        ps = [p for p in r.get("pairs", []) if p.get("in_domain") and "ref_error" not in p and not maybe_band(p["T"])]
        if ps:
            sn += 1
            sf += any(isfail(p) for p in ps)
    out["total"]["D_prime_scenarios"] = sn
    out["total"]["D_prime_scenarios_failing"] = sf
    out["total"]["upper95_failure_probability_D_prime_per_scenario"] = bound(sn, sf)
    # scenario level (the 5 periods of one scenario are not independent): a scenario fails if any in-domain pair fails
    scn_n = scn_f = 0
    for r in recs:
        if str(r.get("stratum", "")).startswith("R:") or r.get("scenario_error") or r.get("stratum") == "D":
            continue
        ps = [p for p in r.get("pairs", []) if p.get("in_domain") and "ref_error" not in p]
        if not ps:
            continue
        scn_n += 1
        scn_f += any((not p["v1"]) or p["v2_bad"] or p["v3_bad"] or (not p["v4"]) or (p.get("v5") is False) for p in ps)
    out["total"]["scenarios_with_in_domain_pairs"] = scn_n
    out["total"]["scenarios_failing"] = scn_f
    out["total"]["upper95_failure_probability_per_scenario"] = bound(scn_n, scn_f)
    # failures inside a band (K, sw(tau)] (D minus D', chapter 17) are reported apart (exact test, scenario regenerated)
    sl = []
    for r in recs:
        if str(r.get("stratum", "")).startswith("R:"):
            continue
        for p in r.get("pairs", []):
            if p.get("in_domain") and "ref_error" not in p and ((not p["v1"]) or p["v2_bad"] or p["v3_bad"] or (not p["v4"]) or (p.get("v5") is False)):
                sl.append(dict(i=r["i"], stratum=r.get("stratum"), T=p["T"], integer_events_with_T_in_band=sliver_of(r["i"], p["T"])))
    n_band = sum(1 for x in sl if x["integer_events_with_T_in_band"])
    out["total"]["in_domain_failures_in_band"] = n_band
    out["total"]["in_domain_failures_outside_band"] = len(sl) - n_band
    out["total"]["failures_band_detail"] = sl[:50]
    out["total"]["fourier_C_zero_random"] = sum(by[s]["fourier_C_zero"] for s in rand)
    out["total"]["nc"] = {k: dict(applicable=sum(nc_app[s][k] for s in nc_app), detected=sum(nc_det[s][k] for s in nc_det)) for k in NCS}
    rin = [s for s in rand if s != "D"]
    out["total"]["nc_random_in_domain"] = {k: dict(applicable=sum(nc_app[s][k] for s in rin), detected=sum(nc_det[s][k] for s in rin)) for k in NCS}
    out["laplace_max_rel"] = max(lap) if lap else None
    out["fourier_conjugate_max"] = max(conj) if conj else None
    out["fourier64_rel"] = {b: dict(n=len(v), median=statistics.median(v), p95=q(v, 0.95), max=max(v)) for b, v in four.items()}
    json.dump(out, open(os.path.join(HERE, "..", "results", "stage4_summary.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: out["total"][k] for k in ("scenarios", "pairs", "pairs_in", "checked", "fail", "in_domain_pairs", "in_domain_failures",
                                                   "upper95_failure_probability_in_domain") if k in out["total"]}, indent=1))
    return out


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "results", "chunks"))
