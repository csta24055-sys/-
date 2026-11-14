"""Stage 1: aggregate the time-characteristics runs (tc_*.json) and the canonical-equation verification
(verify_canon_all.json) into results/stage1_summary.json.

Usage (from this folder): python3 -B aggregate1.py
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
RES = os.path.join(HERE, "..", "results")


def q(xs, p):
    xs = sorted(xs)
    if not xs:
        return None
    return xs[min(len(xs) - 1, int(math.ceil(p * len(xs))) - 1)]


def main():
    runs = []
    for f in sorted(glob.glob(os.path.join(RES, "tc_*.json"))):
        runs += [r for r in json.load(open(f))]
    ok = [r for r in runs if "th0123" in r]
    out = dict(n_scenarios=len(runs), n_analysed=len(ok), prepare_errors=[r for r in runs if "th0123" not in r])
    # exact identities
    exact = collections.Counter()
    exact_n = collections.Counter()
    for r in ok:
        for part in ("th0123", "th45", "th6"):
            for k, v in r[part].items():
                if k.endswith("_bad") or k == "lattice_jumps_above_1em12":
                    exact[k] += v
                    exact_n[k] += 1
    out["exact_failures"] = dict(exact)
    out["exact_checked_scenarios"] = dict(exact_n)
    th = lambda part, key: [r[part][key] for r in ok if key in r[part]]
    out["counts"] = dict(
        pieces=sum(th("th0123", "n_pieces")), event_knots=sum(th("th0123", "n_event_knots")),
        lattice_knots=sum(th("th0123", "n_lattice_knots")), jumps=sum(th("th0123", "n_jumps")),
        th0_points=sum(th("th0123", "th0_points")), th2_events_with_terms=sum(th("th0123", "th2_terms_events")),
        lattice_rounding_jumps=sum(th("th0123", "n_lattice_rounding_jumps")),
        integer_event_reset_jumps=sum(th("th0123", "n_integer_event_reset_jumps")),
        th6_points=sum(th("th6", "th6_points")))
    nt = [r["n_terms"] for r in ok]
    nk = [r["th0123"]["n_event_knots"] + r["th0123"]["n_lattice_knots"] for r in ok]
    out["size"] = dict(terms_median=statistics.median(nt) if nt else None, terms_max=max(nt, default=None),
                       knots_median=statistics.median(nk) if nk else None, knots_max=max(nk, default=None),
                       ratio_terms_per_knot_median=statistics.median([a / b for a, b in zip(nt, nk) if b]) if any(nk) else None, n_without_knots=sum(1 for b in nk if not b),
                       H_values=sorted({r["H"] for r in ok}))
    out["max_rel_lattice_rounding_jump"] = max(th("th0123", "max_rel_lattice_rounding_jump"), default=0.0)
    out["switch_offset_ulp_max"] = max((r["switch_points"]["max_switch_offset_ulp"] for r in ok), default=0.0)
    # real-time decomposition
    zs = [r["th45"]["pieces_with_terminal_slope"] / max(1, r["th0123"]["n_pieces"]) for r in ok]
    out["terminal_slope"] = dict(
        scenarios_with_any=sum(1 for r in ok if r["th45"]["pieces_with_terminal_slope"] > 0),
        median_fraction_of_pieces=statistics.median(zs) if zs else None,
        max_rel_to_total_slope=max(th("th45", "max_rel_terminal_slope"), default=0.0),
        p95_rel_to_total_slope=q(th("th45", "max_rel_terminal_slope"), 0.95))
    neg = collections.defaultdict(collections.Counter)
    for r in ok:
        for key in ("neg_mass_units", "neg_density_units", "neg_stage_density_intervals", "neg_stage_masses"):
            for u, n in r["th45"][key].items():
                neg[key][u] += n
                neg[key + "__scenarios"][u] += 1
    out["negative_parts"] = {k: dict(v) for k, v in neg.items()}
    # Laplace / Fourier
    out["laplace_max_rel"] = max((x["rel"] for r in ok for x in r["th78"]["laplace"]), default=None)
    out["fourier_closed_vs_pieces_max_rel"] = max((r["th78"]["fourier_closed_vs_pieces_max_rel"] for r in ok), default=None)
    out["fourier_conjugate_symmetry_max"] = max((r["th78"]["fourier_conjugate_symmetry_max"] for r in ok), default=None)
    four = {}
    for M in ("8", "32", "128", "512"):
        far = [r["th78"]["fourier"][M]["max_rel_far"] for r in ok if r["th78"]["fourier"][M]["max_rel_far"] is not None]
        allv = [r["th78"]["fourier"][M]["max_rel_all"] for r in ok]
        med = [r["th78"]["fourier"][M]["median_rel"] for r in ok]
        four[M] = dict(max_rel_far_median=statistics.median(far) if far else None, max_rel_far_max=max(far, default=None),
                       max_rel_all_median=statistics.median(allv) if allv else None, max_rel_all_max=max(allv, default=None),
                       median_rel_median=statistics.median(med) if med else None)
    out["fourier_partial_sums"] = four
    sl = [r["th78"]["fourier_decay_loglog_slope"] for r in ok]
    out["fourier_decay_slope"] = dict(median=statistics.median(sl) if sl else None, min=min(sl, default=None), max=max(sl, default=None))
    bm = [r["th78"]["boundary_midpoint"]["rel_to_midpoint"] for r in ok]
    out["fourier_boundary_midpoint_rel_max"] = max(bm, default=None)
    # recurrences
    rec = collections.Counter()
    for r in ok:
        n = r["th9"].get("n")
        L = r["th9"].get("order")
        rec["full (L = ceil(n/2))" if L is not None and n is not None and L >= (n + 1) // 2 else "low order L=%s" % L] += 1
    out["recurrence_total"] = dict(rec)
    role_rec = collections.defaultdict(collections.Counter)
    low_examples = collections.defaultdict(list)
    for r in ok:
        for role, d in r["role_recurrence"].items():
            L = d.get("order")
            role_rec[role][str(L) if L is not None and L <= 24 else ">24"] += 1
            if L and L <= 24 and d.get("certified_unique") and len(low_examples[role]) < 6:
                low_examples[role].append(dict(label=r["label"][:60], order=L, eigenvalues=d.get("eigenvalues")))
    out["recurrence_by_role"] = {k: dict(v) for k, v in role_rec.items()}
    out["recurrence_low_order_examples"] = dict(low_examples)
    dmd = [r["th9"].get("recurrence_float_max_rel") for r in ok if r["th9"].get("recurrence_float_max_rel") is not None]
    out["recurrence_float_replay_max_rel"] = max(dmd, default=None)
    # FRI
    fri = []
    for r in ok:
        for st, d in r["th10"].items():
            if d and d.get("pure_jump") and "max_abs_time_error" in d:
                fri.append(dict(stage=st, K=d["K"], err=d["max_abs_time_error"], cond=d["cond"], sep=d["min_separation"]))
    out["fri"] = dict(n=len(fri), by_K=sorted(fri, key=lambda x: x["K"])[:200])
    # roles
    shares = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in ok:
        for T, d in r["roles"].items():
            tot = sum(d["value"].values())
            if tot:
                for role, v in d["value"].items():
                    shares[T][role].append(v / tot)
    out["role_share_median"] = {T: {role: statistics.median(v) for role, v in d.items()} for T, d in shares.items()}
    # canonical verification
    vf = os.path.join(RES, "verify_canon_all.json")
    if os.path.exists(vf):
        v = json.load(open(vf))
        keys = ("n_pairs", "n_excluded", "n_failed", "total_vs_ref_bad", "total_vs_sys_bad", "knot_vs_terms_bad", "n_stage",
                "stage_vs_ref_bad", "n_unit", "unit_vs_ref_bad", "n_jumpform", "jumpform_vs_ref_bad")
        out["canonical_verification"] = {k: sum(s.get(k, 0) for s in v.values()) for k in keys}
        out["canonical_verification"]["max_rel_total_vs_ref"] = max(s["max_rel_ref"] for s in v.values())
        out["canonical_verification"]["max_rel_stage_vs_ref"] = max(s["max_rel_stage"] for s in v.values())
        out["canonical_verification"]["max_rel_unit_vs_ref"] = max(s["max_rel_unit"] for s in v.values())
        out["canonical_verification"]["by_set"] = {k: {kk: s.get(kk) for kk in keys} for k, s in v.items()}
    json.dump(out, open(os.path.join(RES, "stage1_summary.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: out[k] for k in ("n_scenarios", "n_analysed", "exact_failures", "counts")}, indent=1))


if __name__ == "__main__":
    main()
