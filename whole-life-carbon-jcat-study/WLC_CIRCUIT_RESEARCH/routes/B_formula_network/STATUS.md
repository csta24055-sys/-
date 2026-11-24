# Route B STATUS — G2 batch 2 + D pass-2 fix pass (formula kinds → circuit grammar, Ψ reading)

- **Research question:** For each formula kind of the 70-unit model, can a circuit construct built only from 𝒢 = {sources, controlled sources, summing node, 0/1 gate, integrator, clip, comparator, sample-hold/reset, external table}, with the horizon T as the sweep variable, reproduce it exactly? Which kinds are passive, active, switched-hybrid, external digital, or not representable?
- **Git and provenance:**
  - Branch `claude/wlc-equivalent-circuit-20261124`. HEAD at task start was `e182105`. During the runs HEAD read `4f5808b`, and at the finish `e4121d6`, because the coordinator committed concurrently and route B did not touch git. The fix pass started at HEAD `7de1065`; results were regenerated at HEAD `a0bb507`.
  - Frozen trees verified by `tstudy.baseline.assert_frozen()` on every run: refcalc `8976efea…`, synth `55caf5cd…`, common `ad3d0b7e…`.
  - No `__pycache__` was found in 09/10/17/WLC_THEORY_RESEARCH_BASE or in this route after the runs (checked with `find`).
  - No git checkout, commit or push was performed. The files are left untracked for the coordinator.
- **Inputs read:**
  - `coordination/architecture.md` and `07_SHARED_CONTRACT.md`
  - `12_FINAL_OPERATING_PLAN.md` and theory base 03 (§3–§8) and 06 (§1, §4)
  - section headings of 04
  - frozen code: tstudy `baseline/scenarios/unified/msp/knots/interval/rampstep`, `specs/system.py`, and refcalc `base.py` and `units_b.py` (B1/B3/B4/B5/B6/B7 parts)
  - Routes A, C and E were **not** read. The A STATUS header was opened only to copy the file format.
- **Fix-pass inputs:** `routes/D_verification/VERDICTS.md` (pass 2, route B rows), `results/p2_check_b.json` and `results/p2_hb4.json` (read only).
- **Model actually run (self-reported):** `claude-opus-5-5`. The effort level cannot be observed from inside the session; medium was intended.
- **Environment:** Python 3.13.18, x86_64, numpy only. The tests make no network calls.

## Verdicts
| hypothesis | verdict | decisive numbers |
|---|---|---|
| H-B1 kernel completeness | **PARTIAL** (PASS for the 6 C(T) kinds of 06 §4.2, confirmed by D out-of-sample; 4 classified b/c kinds NOT_RUN) | Scenarios S, M + out-of-sample EV3, EV11. 2,928 asserted comparisons, 0 failures (rel ≤ 1e-9). Max relative error vs refcalc: B3-01 1.87e-13; B6-03 3.6e-15 (clip) / 5.7e-16 (integrator); B4-02 2.0e-15; B1-03 1.9e-15 (P1) / 1.7e-15 (raw S/H); B1-04 1.4e-15 (jump pieces) / 0.0 (raw S/H); B7-04 1.2e-15 / 6.1e-16; B1-02 7.6e-16 (P1) / 0.0 (raw S/H); B2-01 6.0e-16; B5-01 1.4e-16; B4-01 count 0.0; constants ≤ 2e-16; SUM-03 2.8e-14. B1-02 [P1 cells] in the band is not relied upon (D: 8.9e-10 on EV6) |
| H-B2 lumped LTI RC with analytic sources cannot equal a kinked/jumping kernel | **Confirmed-as-textbook by D for LTI** [L]; scope corrected (switched and ideal-diode passive networks can reproduce kinks/jumps, so the labels are relative to 𝒢) | Fit basis 1, T, e^{−λT} (ramp added): jump sup error ≥ 0.5004 at every order (bound 0.5); kink 0.094 → 0.019, > 0 at finite order (→0 asymptotically) |
| H-B3 refrigerant RC vs S/H | **Confirmed [F]** (+ refinement) | single no-top-up device, 242 T: RC-b 2.88e-3 inside cells, 1.1e-15 at whole years; RC-a 2.88e-3; S/H 0.0. Whole M: RC-b B1-04 1.36e-4, B1-02 4.9e-3. Late reset is required: without it the error is scenario-dependent — up to 3.15e-2 / 3.27e-2 on M, 4.63e-2 / 7.28e-3 on EV3 (B1-04 / B1-02); D saw up to 0.97 |
| H-B4 isomorphic rewriting | **Not refuted** (corrected after D pass 2; the earlier "refuted in stored state" is withdrawn as a metric artefact) | Refrigerant on BM-M: merged knot form 1,063 coefficients (my count; D's canon 1,025) vs automaton 1,072 tuple numbers (712 distinct). Same order: a time–memory trade-off only; random access 343× slower (57.6 ms vs 0.17 ms for 200 random T). Memoryless families: apparent savings are explained by fan-out, shared w_k and the implicit origin. No speed advantage |

## D pass-2 fixes
| # | D point | outcome | evidence |
|---|---|---|---|
| 1 | H-B4 refrigerant "stores less state" is a metric artefact | **FIXED** (D confirmed by my own re-count) | `hb4_counts.py` merged knot form on BM-M: 263 + 417 + 383 = 1,063 coefficients (D's canon: 1,025; B1-04 jump form 60 vs 41 event knots) vs automaton 1,072 (712 distinct). Random access 343× slower on M, 56× on S. Restated as a time–memory trade-off in claims.md; the earlier claim is withdrawn |
| 2 | H-B2 scope to LTI with analytic sources; `hb2_passive.py` superset statement false; K10/K37 labels relative to 𝒢 | **FIXED** (D confirmed: the basis lacked c·T) | Ramp column added to the fit; docstring and claims.md rescoped; MAPPING K10/K37 justifications say "relative to 𝒢 / LTI", with the switched and ideal-diode passive counterexamples. Regenerated: jump ≥ 0.5004, kink 0.094 → 0.019 |
| 3 | Band wording | **FIXED** (D confirmed independently) | The atom no-count band is the closed real band [τ, τ/(1−ε)] (float: [τ, sw(τ))) in `route_b_experiments.py` and `test_grammar.py`. The refrigerant deviating set is the open (K, sw(τ)): my knife point τ(1+1e-9) = sw(τ) shows the interval form agrees there (≤ 5.6e-16, 4 scenarios); 03 §3.4's closed (K, sw] is the conservative exclusion |
| 4 | MAPPING K19 "per device" vs shared thresholds | **FIXED** | K19 now gives totals (4nd, 1+2nd, (H−1)+n_ev, n_ev+6nd) = `state_tuple()`, with the shared counter and thresholds noted; K16–K18 are labelled per device excluding shared parts |
| 5 | Tests one-sided; no out-of-sample; B1-02 [P1 cells] band near tolerance | **FIXED** | Measured-magnitude assertions (relative 1e-6) for band and ablation on 4 scenarios. Out-of-sample EV3 (hospital-M) and EV11 (warehouse-S), disjoint from D's EV6/EV10, all kernels pass (max 1.87e-13). B1-02 [P1 cells] in the band is flagged as not relied upon (we see ≤ 1.9e-11; D 8.9e-10) |
| 6 | K26/K28/K30/K32/K33 | **NOT_RUN** (unchanged; no new families started) | — |

I have no disagreement with D. Every point was reproduced before it was changed.

## Formula kinds enumerated (37; `MAPPING.csv`)
- **Grammar coverage:** a = 7, b = 9, c = 7, d = 9, e = 4, n/a = 1. K21 is counted as b because a share > 1 needs an amplifier.
- **Status:** exact 20, conditional 2, approximate 1, unsupported 9, unverified 5.
- **Unsupported in 𝒢 (class d/e, not approximated):**
  - K01 P1 masked products of data columns
  - K04 inv-family functions
  - K05 `match`
  - K24 SUM-05 division by T
  - K25 share ratios
  - K34 strings and missing-value propagation
  - K35 float knife edge
  - K36 non-integer powers and logarithms (J-CAT experiment only, out of scope)
  - K37 LTI RC (analytic sources) realisation of kinked or jumping kernels (class e relative to that restriction and to 𝒢, not physical)

## Counterexamples and findings
1. **S/H without late reset fails.** For integer τ the comparator fires after the cell has closed, so an S/H that samples only at cell ends misses the replacement. Measured error: up to 3.15e-2 (B1-04) and 3.27e-2 (B1-02) on M.
2. **The automaton matches in the excluded band where the interval form does not.** With the late reset, the automaton matches refcalc inside the **open** band (K, sw(τ)). There msp's interval form deviates by up to 3.12e-2 (B1-04, M, T = 15.0000000075) and 2.67e-3 (EV3), which makes SUM-03(msp) 2.5e-5 off. At T = sw(τ) the interval form agrees again (≤ 5.6e-16). 03 §3.4's closed (K, sw] is the conservative 𝒟′ exclusion. Seen on 4 scenarios (+2 by D); outside 𝒟′ and not generalised.
3. **The continuous RC decay agrees only at whole years** (H-B3 numbers above).
4. **Naive counting metrics mislead in both directions:** the "irreducible parameter" metric wrongly suggests compression in the memoryless families, and the unmerged-table comparison wrongly suggested a refrigerant state saving (caught by D). See H-B4.

## Mismatches vs architecture [H] statements
- The step counts 1,528 / 95 / 166 are **confirmed**: 1,358 sp + 170 match; 95 sp; 156 sp + 10 match.
- The representative units B4-02 (atom), B6-03 (cell), B3-01 (density + gated cell), B1-03 (atom + gated cell) and B1-04 (interval) are **confirmed** as their kinds. Two qualifications:
  - B1-04 also carries a jump-form EMIT ("kept for comparison only"); the unit value at T uses the interval form.
  - Scenario S has B5-01 = 0 (no pieces), so atoms in S are tested through B4-02 only.
- **"6 kernel kinds" is complete for C(T) only.** Other T-dependent outputs need further kinds: counts (K15), division by T (K24), shares (K25) and T-dependent predicates (K26).
- **Boundary points.** 10.000000005 and 10.00000002 lie in `scenarios.valid_domain`'s relative knife window (1e-10 < d < 1e-8) whenever an event at 10 exists. 10.000000005 is also inside the band excluded from 𝒟′. They are therefore **not inside 𝒟′**, contrary to the wording of the G2 instruction. They were still asserted, labelled `band_in`/`band_out`, because the comparisons there are deterministic (not within ulps). Only T = τ(1+1e-9), labelled `knife`, is treated as undefined and recorded without assertion.
- **03 §3.4's reported band deviation** (B1-04 5.5e-3) is exceeded at our points (3.12e-2). This is not a contradiction: it was measured at different points and scenarios.

## Completed tests
`python3 -B -m unittest discover -s <route>/tests -v` → **17 tests, 17 OK, 0 failures** (log: `results/log_tests.txt`; ~51 s). `test_each_kernel_within_tolerance` contains 22 subtests. The band and ablation tests now assert the measured magnitudes per scenario (relative 1e-6), not one-sided inequalities. Out-of-sample scenarios EV3 and EV11 are included.

## NOT_RUN / unverified
- K26 T-dependent AGG predicates
- K28 max/min/abs
- K30 knot form L5 as a separate netlist
- K32 Φ/Ψ decomposition (X5, route D)
- K33 vector outputs
- X-11, SUM-01/02 and SUM-04 asserted separately
- B4-03 and X-08 counts
- `match`
- scenario L of the benchmark (too slow per T; not run)
- RC-a/RC-b numbers: not re-run by D
- SageMath/MATLAB (not needed)
- integration with A/C/E (coordinator)

## Next actions
1. (done by D: H-B2 confirmed-as-textbook for LTI; the late-reset automaton was confirmed.)
2. Run K26/K30 netlists, and X-11/SUM-04/B4-03.
3. Run the band test on more scenarios, e.g. `scenarios.design_set`, to see whether the agreement of the automaton in the band holds generally.
4. The coordinator compares the K-list with route C's DIRECT time_form list (X3).
