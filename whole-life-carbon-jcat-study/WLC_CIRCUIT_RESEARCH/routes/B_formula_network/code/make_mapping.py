"""Write MAPPING.csv: one row per formula KIND enumerated by route B from the theory base (not from route C).
Numbers in `validation` are read from results/kernel_comparison.json, hb3_refrigerant.json, hb2_illustration.json
when present (otherwise NOT_RUN)."""
from __future__ import annotations

import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROUTE = os.path.dirname(HERE)
B = "whole-life-carbon-jcat-study/WLC_THEORY_RESEARCH_BASE/"
S03, S04, S06 = B + "03_数式と記号の完全仕様.md", B + "04_マスク積和の理論.md", B + "06_建物全体の統一方程式.md"


def load(name):
    p = os.path.join(ROUTE, "results", name)
    return json.load(open(p)) if os.path.exists(p) else None


K = load("kernel_comparison.json")
H3 = load("hb3_refrigerant.json")
H2 = load("hb2_illustration.json")


def v(*kernels):
    if K is None:
        return "NOT_RUN"
    parts = []
    for k in kernels:
        d = K["summary"].get(k)
        if d is None:
            parts.append(f"{k}: NOT_RUN")
        else:
            parts.append(f"{k}: n={d['n']} fail={d['n_fail']} max_rel_vs_refcalc={d['max_rel_ref_asserted']:.1e} "
                         f"max_rel_vs_msp={d['max_rel_msp_asserted']:.1e}")
    return "; ".join(parts) + " (S,M benchmark scenarios; tests/test_oracle.py)"


def h3():
    if H3 is None:
        return "NOT_RUN"
    s = H3["single_device"]["B1-04"]
    return (f"single no-top-up device, {H3['single_device']['n_T']} T: RC-b max rel {s['RC-b (RC in cell, S/H resets)']['max_rel_fractional_T']:.2e} "
            f"inside cells / {s['RC-b (RC in cell, S/H resets)']['max_rel_integer_T']:.1e} at whole years; RC-a {s['RC-a (physical RC, reset at event)']['max_rel_fractional_T']:.2e}; "
            f"S/H {s['SH']['max_rel_fractional_T']:.1e} (results/hb3_refrigerant.json)")


def h2():
    if H2 is None:
        return "NOT_RUN"
    j = min(r["sup_error"] for r in H2["jump_atom"])
    k = min(r["sup_error"] for r in H2["kink_w0"])
    return f"illustration only: best exp-sum (<=24 terms) sup error jump {j:.3f} (>=0.5 bound), kink {k:.3f} (results/hb2_illustration.json)"


COLS = ["kind_id", "kind_name", "source_path", "source_section", "formula", "example_units", "target_circuit_construct",
        "class", "justification", "status", "validation", "evidence", "state_tuple_per_instance"]

ROWS = [
    ("K01", "masked sum-product sp (row products of data columns, T-independent, P1)", S03, "§4.2; 04 §2.2-2.3",
     "out[g]=sum_x sum_t prod_k phi_tk(x)", "all P1 amplitudes (1,528 steps)",
     "external digital table feeding source amplitudes; a column x constant is a gain", "d",
     "product of two data columns needs a multiplier, which is not in G; amplitudes are T-independent so they are configuration data",
     "unsupported", "not reproduced in G; used as external table (P1 pieces) by every kernel test", "[F] indirect", "(0,0,0,N amplitudes)"),
    ("K02", "grouping total / by (scatter-add)", S03, "§4.2 grouping", "out[y]=sum_{x:r[x]=y} ...", "SUM-03, stage vector",
     "summing node (KCL of source currents)", "a", "KCL adds currents exactly with ideal sources; no active part needed",
     "exact", v("SUM-03 [gain + summing node]"), "[F]", "(0,0,0,0)"),
    ("K03", "static predicates/masks on data (present, range, eq, le, not)", S03, "§4.4; 04 §3", "[c!=bot], [l<=c<=u], [a=b], [a<=b]",
     "device_ok, ratio(share), ratio(eta)", "switch position fixed at build time by external logic", "d",
     "T-independent; a comparator could evaluate numeric ones but key equality on codes and missing-value logic is digital",
     "exact", "used in B1-0x automaton and B2-01 gain (static predicate)", "[F] indirect", "(0,0,0,0)"),
    ("K04", "one-column functions inv, one_minus, inv_one_minus, ratio_one_minus", S03, "§4.2 (3); §8", "1/a, 1-a, 1/(1-a), a/(1-a)",
     "SUM-04 1/A, rates", "one_minus = src + gain(-1) + summing node (b); inv family = divider", "d",
     "no divider in G; one_minus alone is expressible (b)", "unsupported", "NOT_RUN (no T dependence; P1 only)", "[H]", "-"),
    ("K05", "match (first keyed look-up, min over row positions)", S03, "§4.3", "ref[x]=min{y: on(y)=keys(x)}",
     "factor look-ups (170 P1 steps)", "external table / digital search", "d", "order-dependent search over keys: digital, not an analog quantity",
     "unsupported", "NOT_RUN", "[H]", "-"),
    ("K06", "template expansion use", S03, "§4.6", "textual substitution", "STAGE, DOUBLE, ...", "none (not a computation)", "n/a",
     "no arithmetic", "exact", "not applicable", "-", "-"),
    ("K07", "common index I (flatten, tokenise, product, distinct, sorted, event lattice n*c<H(1-eps))", S03, "§5.2; 06 §1", "event times tau_n = fl(n c)",
     "event tables of B4/B3/B1", "external digital event table; each entry becomes one comparator threshold", "d",
     "enumeration and sorting are digital; the circuit only consumes the threshold list",
     "exact", v("B4-01 n_events [raw comparator bank]", "B1-04 [raw S/H automaton]") + " (route B builds its own tables from raw inputs)", "[F]", "(0,0,0,#events)"),
    ("K08", "constant A^init (T-independent unit values, t=0)", S06, "§4.2; 03 §5.1 const", "a", "A13-01,A13-03,A13-04,X-01,A4-01,A4-02,A5-04",
     "independent DC source", "a", "constant in T", "exact", v("A13-01 [DC source]", "A4-01 [DC source]", "A5-04 [DC source]"), "[F]", "(0,0,0,1)"),
    ("K09", "terminal constant A^term (horizon-only, placed at t=T)", S06, "§4.2-4.3; 03 §7", "Z(T) const part", "C1-01,C2-01,C3-01,C4-01,X-14",
     "Psi: DC source added at the read-out node; Phi: must NOT be integrated (read-out adder only)", "a",
     "in the T sweep it is a constant; in real time it moves with the horizon (TH-4), so it is not a capacitor charge",
     "conditional", v("C1-01 [DC source]", "C4-01 [DC source]", "X-14 [DC source]") + "; Phi/X5 NOT_RUN (route D)", "[F]", "(0,0,0,1)"),
    ("K10", "year cell w_k(T)=clip(T-k,0,1) (single)", S03, "§3.2; §5.1", "a*clip(T-k,0,1)", "B6-03, B7-04, B1-02, EL, G",
     "summing node T + src(-k) -> clip -> gain a", "b", "clip is a saturating (active) element; kink at k and k+1 (H-B2 excludes passive LTI RC)",
     "exact", v("B6-03 [P1 pieces]", "B7-04 [P1 pieces]", "B1-02 [P1 cells]"), "[F]", "(0,0,0,2)"),
    ("K11", "year-cell superposition sum_k B_k w_k(T)", S06, "§4.2 U_B", "sum_k B_k w_k(T)", "B6-03, B7-04",
     "external table of per-cell currents indexed by a comparator-bank counter k(T) -> ONE integrator (switched current source)", "c",
     "integrator of a piecewise-constant current = sum of year weights", "exact",
     v("B6-03 [P1 pieces, integrator]", "B7-04 [P1 pieces, integrator]"), "[F]", "(1,1,H-1,H)"),
    ("K12", "density B* min(T,H)", S06, "§4.2; 03 §5.1 density", "a*min(T,H)", "B3-01 (uniform repair rate)",
     "DC current source charging one capacitor (KCL sum of all density currents)", "a",
     "for 0<T<=H the clamp at H is inactive; outside the domain a clamp (b) would be needed and is NOT built", "conditional",
     v("B3-01 [P1 pieces]") + " (density+gated-cell sum)", "[F]", "(1,0,0,1)"),
    ("K13", "atom theta_eps(T;tau)=[tau<T(1-eps)]", S03, "§3.2; §5.1 atom", "a*[tau<T(1-eps)]", "B4-02, B5-01, B1-03",
     "gain (1-eps) on T (passive divider) -> comparator vs src(tau) -> switch on src(a)", "b",
     "jump at sw(tau): comparator needed; event at T excluded; the float knife edge T~tau/(1-eps) is undefined (recorded, not asserted)",
     "exact", v("B4-02 [P1 pieces]", "B5-01 [P1 pieces]"), "[F]", "(0,0,1,2)"),
    ("K14", "gated year cell theta_eps(T;tau) w_k(T)", S06, "§4.2 U_Delta; 03 §5.7", "D*[tau<T'] clip(T-k,0,1)", "B3-01 (skip repair in event year), B1-03",
     "comparator-driven switch on a clip block", "b", "AND of a comparator and a saturation", "exact",
     v("B3-01 [P1 pieces]", "B1-03 [P1 pieces]"), "[F]", "(0,0,1,3)"),
    ("K15", "count N(T)=sum theta_eps (event counters, mis.* counts, N.b42)", S03, "§5.5 counts; TH-14", "sum_tau [tau<T(1-eps)]",
     "B4-01 n_events, B4-03, X-08 counts", "comparator bank -> summing node (counter)", "b", "integer staircase", "exact",
     v("B4-01 n_events [raw comparator bank]") + "; B4-03/X-08/mis.* NOT_RUN", "[F]", "(0,1,#events,#events)"),
    ("K16", "refrigerant state recurrence u_dk = chi m0 + (1-chi) q u_d,k-1 (switched affine, D-08)", S03, "§5.5", "u_{d,k}",
     "B1-02/03/04 state", "sample-hold per device (gain q at each cell boundary, reset switch to m0 on a counted event)", "c",
     "not time-invariant linear (TH-9); needs reset; continuous RC cannot reset", "exact",
     v("B1-02 [raw S/H automaton]", "B1-04 [raw S/H automaton]"), "[F]", "(1,1,0,0) per device"),
    ("K17", "refrigerant leak B1-02 = sum u_dk r GWP w_k", S03, "§5.5", "sum_{d,k} u r GWP w_k(T)", "B1-02",
     "VCCS (gain r) on the held state into an integrator reset each cell; S/H accumulator of closed cells", "c", "state-dependent current", "exact",
     v("B1-02 [raw S/H automaton]", "B1-02 [P1 cells]"), "[F]", "(2,0,0,0) per device"),
    ("K18", "replacement loss B1-03 (atom + gated cell with state amplitude)", S03, "§5.5 (D-08 f)", "lambda GWP u_before", "B1-03",
     "comparator-gated sample of the held state minus the in-cell integrator; S/H accumulator", "c", "amplitude depends on T until the cell closes",
     "exact", v("B1-03 [raw S/H automaton]", "B1-03 [P1 pieces]"), "[F]", "(1,1,#events,0) per device"),
    ("K19", "refrigerant terminal residual R(T) interval form (Z part, iota_B1 R)", S03, "§5.4", "A_K + B_K (T-K) + sum theta (alpha + gamma (T-K))", "B1-04",
     "S/H + reset + switched integrator with LATE reset when a comparator fires after its cell closed (integer tau)", "c",
     "reproduces the model's recomputation of history at each T; the msp interval form deviates in the band (K, sw(tau)]",
     "exact", v("B1-04 [raw S/H automaton]") + "; inside band (K,sw] also matched (outside D'); ablation without late reset: "
     + (f"max rel {max(u['rel_ref'] for u in K['summary']['B1-04 [raw S/H, no late reset]']['unasserted']):.2e}" if K else "NOT_RUN"), "[F]", "(4,2,H-1+#events,#events+6) per device"),
    ("K20", "continuous RC discharge as a realisation of R(T) (alternative to K19)", S03, "§5.4-5.5 (H-B3)", "m0 q^(T-t_reset), exp(-1/RC)=q",
     "B1-04, B1-02", "passive RC (+ reset switch)", "a", "matches at whole years only; the model is linear inside a cell",
     "approximate", h3(), "[F]", "(1,0,0,0) per device"),
    ("K21", "T-independent scalar times T-dependent kernel (B2-01 = share EL(T); X-11 = c G(T))", S06, "§6.4 (03 §6.4)", "share * sum e_k w_k",
     "B2-01, X-11", "gain block; share in [0,1] = resistive divider (a); c>1 needs an amplifier (b)", "b",
     "linear in the signal with a constant coefficient", "exact", v("B2-01 [gain x year cells]") + "; X-11 NOT_RUN", "[F]", "(0,0,0,1)"),
    ("K22", "outer composition stage x unit 0/+-1 matrix with beta, iota (S_s, SUM-01/02/03)", S06, "§3.1-3.2; 03 §6.2", "S3=sum_s iota_s sum_c sigma beta V_u",
     "SUM-03 (22 COMP rows)", "gains +-1/beta and one summing node", "a", "current-mode KCL; sign by source orientation", "exact",
     v("SUM-03 [gain + summing node]") + "; SUM-01/02 not asserted separately", "[F]", "(0,0,0,22)"),
    ("K23", "division by a constant (SUM-04 = S3/A, SUM-06 = S3/1000)", S03, "§6.4", "S3 * (1/A)", "SUM-04, SUM-06", "gain block", "a",
     "constant coefficient <1", "exact", v("SUM-06 [gain 0.001]") + "; SUM-04 NOT_RUN", "[F]", "(0,0,0,1)"),
    ("K24", "division by the sweep variable (SUM-05 = S3/(A T))", S03, "§6.4; TH-14 hyperbola per interval", "S3/(A T)", "SUM-05",
     "external digital read-out (divider not in G)", "d", "y=x/T is a product of two signals; not in G; not silently approximated",
     "unsupported", v("SUM-05 [external digital division]") + " (as digital read-out, not as circuit)", "[F]", "-"),
    ("K25", "ratio of two T-dependent signals (share_s = bs_s/S3) and SUM-08 rho", S03, "§6.4", "bs_s/S3; (base-S3)/base", "SUM-07, SUM-08",
     "share: external digital; rho: gain (base is constant) with static predicate", "d", "divider of two signals not in G", "unsupported",
     "NOT_RUN", "[H]", "-"),
    ("K26", "T-dependent predicates in AGG ([S3>0], #{bs<0}=0, complete(T))", S03, "§6.4-6.5", "[sum [bad>=1]=0]", "X-02 complete, SUM-07 defined",
     "comparators + logic gates", "b", "0/1 outputs of comparisons of T-dependent signals", "unverified", "NOT_RUN", "[H]", "(0,0,#preds,0)"),
    ("K27", "conditional branches if/elif/else as exclusive masks", S04, "§3 (03 §4.7)", "[A]a + not[A][B]b + not[A]not[B]c", "all units",
     "T-independent: fixed switches (d config); T-dependent ([tau<T']): comparator-switch (b)", "b",
     "mutually exclusive switch network", "exact", "covered through K13/K14 tests", "[F] indirect", "-"),
    ("K28", "max/min/abs via masks", S04, "§3 (03 §4.7)", "[d>=0]d, [p<=q]q+not[p<=q]p", "P1 only",
     "comparator + switch (b)", "b", "no T dependence in the 70-unit model", "unverified", "NOT_RUN", "[H]", "-"),
    ("K29", "nilpotent-shift resolvent by doubling prod(I+N^{2^i}), H<256", S03, "§5.5", "u <- u + c^(s) u[k-s]", "B1-02 state (msp)",
     "replaced by the sequential S/H recurrence (K16); no doubling needed", "c", "different algorithm for the same recurrence",
     "exact", v("B1-02 [raw S/H automaton]"), "[F]", "-"),
    ("K30", "knot form L5 (truncated powers [t<T](P+QT), theta(p+qT))", S03, "§5.6", "A0+sum[t<T](P+QT)+sum theta(p+qT)", "C(T)",
     "comparator + switch on (P + gain Q on T)", "b", "equivalent to K10-K14 (lemma L-1)", "unverified",
     "NOT_RUN as separate netlist (rational form is route D's)", "[H]", "(0,0,#knots,2#knots)"),
    ("K31", "jump form KnotSpectrum (prefix sums + binary search)", S03, "§5.3", "b+P0[k]+T P1[k]", "all T-units (msp)",
     "digital search (d); its circuit counterpart is K13/K14", "d", "binary search is digital", "exact",
     v("B1-04 [P1 jump pieces]") + " (jump-form pieces through G)", "[F]", "-"),
    ("K32", "real-time decomposition C=M([0,T])+Z(T), dC/dT=rho+Z'", S03, "§7 (TH-4)", "C(T)-M([0,T])=Z(T)", "whole building",
     "Psi: read-out adder of Z; Phi: integrator holds M only", "c", "Z is horizon-only; not an emission rate", "unverified",
     "NOT_RUN (gate X5, route D)", "[P] in source; [H] for the circuit", "-"),
    ("K33", "per-year series and cumulative lists (by_year, X-07)", S06, "§6.5", "vector indexed by year", "X-07, by_year outputs",
     "S/H bank or external memory", "d", "vector outputs, not one node value", "unverified", "NOT_RUN", "[H]", "(0,0,0,H)"),
    ("K34", "missing values bot propagation, strings, enums, violation lists", S03, "§4.4-4.5; §6.5", "bot rules", "DECISION/QA units",
     "validity flags (digital)", "e", "strings and missing-ness are not physical circuit quantities", "unsupported", "NOT_RUN", "[H]", "-"),
    ("K35", "float knife edge of theta_eps (relative 1e-10..1e-8 window; T=tau(1+1e-9))", S03, "§3.3-3.4", "fl(T d) vs tau",
     "all events", "none: rounding artefact, undefined", "e", "decided by binary rounding, not by the formula; recorded only", "unsupported",
     (f"recorded at {sum(1 for d in K['summary'].values() for u in d['unasserted'] if u['label']=='knife')} (kernel,T) knife points, not asserted" if K else "NOT_RUN"),
     "[F] recorded", "-"),
    ("K36", "non-integer powers / log10 (J-CAT conversion experiment only)", S04, "§6.1", "x^p, log10 x", "none in 70-unit model",
     "not in G", "e", "outside the 70-unit model; masked sum-product cannot represent them as reals ([P] in source)", "unsupported",
     "out of scope, NOT_RUN", "[P] source / [H] here", "-"),
    ("K37", "passive LTI RC realisation of any kinked/jumping kernel (H-B2)", S03, "§5.1; TH-1, TH-7", "exp-polynomial = kernel on interval with knot?",
     "K10, K13, K14", "passive RC with analytic sources", "e", "real-analytic response vs piecewise-linear kernel with knot (identity theorem)",
     "unsupported", h2(), "[H] proof sketch pending D", "-"),
]


def main():
    path = os.path.join(ROUTE, "MAPPING.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLS)
        for r in ROWS:
            assert len(r) == len(COLS), r[0]
            w.writerow(r)
    print(f"wrote {path}: {len(ROWS)} kinds")


if __name__ == "__main__":
    main()
