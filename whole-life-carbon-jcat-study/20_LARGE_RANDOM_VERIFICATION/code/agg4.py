"""Stage 4: aggregate the chunk files into results/stage4_summary.json (and print the headline numbers).

Statistical statement (only for the DECLARED sampling distribution of gen4.py): if N independent pairs show no
failure, the one-sided 95 % upper confidence bound of the failure probability per pair is p <= 1 - 0.05^(1/N)
(exact binomial / Clopper-Pearson with 0 failures; about 3/N). It says nothing about inputs outside the distribution.

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
            if p.get("fourier64_rel") is not None:
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
        d["upper95_failure_probability"] = bound(c["checked"], c["fail"])
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
    out["total"]["upper95_failure_probability_in_domain"] = bound(in_dom, fail_in)
    out["total"]["nc"] = {k: dict(applicable=sum(nc_app[s][k] for s in nc_app), detected=sum(nc_det[s][k] for s in nc_det)) for k in NCS}
    out["laplace_max_rel"] = max(lap) if lap else None
    out["fourier_conjugate_max"] = max(conj) if conj else None
    out["fourier64_rel"] = {b: dict(n=len(v), median=statistics.median(v), p95=q(v, 0.95), max=max(v)) for b, v in four.items()}
    json.dump(out, open(os.path.join(HERE, "..", "results", "stage4_summary.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: out["total"][k] for k in ("scenarios", "pairs", "pairs_in", "checked", "fail", "in_domain_pairs", "in_domain_failures",
                                                   "upper95_failure_probability_in_domain") if k in out["total"]}, indent=1))
    return out


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "results", "chunks"))
