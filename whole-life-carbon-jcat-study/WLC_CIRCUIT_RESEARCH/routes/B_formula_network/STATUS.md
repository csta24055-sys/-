# Route B STATUS — G2 batch 2 (formula kinds → circuit grammar, Ψ reading)

- **Research question:** For each formula kind of the 70-unit model, can a circuit construct built only from 𝒢 = {sources, controlled sources, summing node, 0/1 gate, integrator, clip, comparator, sample-hold/reset, external table}, with the horizon T as the sweep variable, reproduce it exactly? Which kinds are passive, active, switched-hybrid, external digital, or not representable?
- **Git and provenance:**
  - Branch `claude/wlc-equivalent-circuit-20261124`. HEAD at task start was `e182105`. During the runs HEAD read `4f5808b`, and at the finish `e4121d6`, because the coordinator committed concurrently and route B did not touch git.
  - Frozen trees verified by `tstudy.baseline.assert_frozen()` on every run: refcalc `8976efea…`, synth `55caf5cd…`, common `ad3d0b7e…`.
  - No `__pycache__` was found in 09/10/17/WLC_THEORY_RESEARCH_BASE or in this route after the runs (checked with `find`).
  - No git checkout, commit or push was performed. The files are left untracked for the coordinator.
- **Inputs read:**
  - `coordination/architecture.md` and `07_SHARED_CONTRACT.md`
  - `12_FINAL_OPERATING_PLAN.md` and theory base 03 (§3–§8) and 06 (§1, §4)
  - section headings of 04
  - frozen code: tstudy `baseline/scenarios/unified/msp/knots/interval/rampstep`, `specs/system.py`, and refcalc `base.py` and `units_b.py` (B1/B3/B4/B5/B6/B7 parts)
  - Routes A, C and E were **not** read. The A STATUS header was opened only to copy the file format.
- **Model actually run (self-reported):** `claude-opus-5-5`. The effort level cannot be observed from inside the session; medium was intended.
- **Environment:** Python 3.13.18, x86_64, numpy only. The tests make no network calls.

## Verdicts
| hypothesis | verdict | decisive numbers |
|---|---|---|
| H-B1 kernel completeness | **PARTIAL** (PASS for the 6 C(T) kinds of 06 §4.2; 4 classified b/c kinds NOT_RUN) | 1,523 asserted comparisons, 0 failures (rel ≤ 1e-9). Max relative error vs refcalc: B3-01 1.15e-13; B4-02 2.0e-15; B6-03 5.6e-16 (clip) / 5.3e-16 (integrator); B7-04 6.1e-16; B5-01 1.4e-16; B1-03 6.7e-16 (P1) / 6.5e-16 (raw S/H); B1-02 6.0e-16 (P1) / 0.0 (raw S/H); B1-04 5.7e-16 (jump pieces) / 0.0 (raw S/H); B2-01 4.6e-16; B4-01 count 0.0; constants 0–2e-16; SUM-03 2.3e-14 |
| H-B2 passive LTI RC impossible | **[H] proof sketch, pending D**; illustration executed | best exponential sum (≤24 terms) sup error: jump ≥ 0.501 at every order (bound 0.5); kink 0.242 → 0.019, never 0 |
| H-B3 refrigerant RC vs S/H | **Confirmed [F]** (+ refinement) | single no-top-up device, 242 T: RC-b 2.88e-3 inside cells, 1.1e-15 at whole years; RC-a 2.88e-3; S/H 0.0. Whole M: RC-b B1-04 1.36e-4, B1-02 4.9e-3. Late reset is required: without it up to 3.15e-2 (B1-04) / 3.27e-2 (B1-02) on M |
| H-B4 isomorphic rewriting | **PARTIAL** (refuted for the refrigerant family in stored state) | automaton on M stores (160, 81, 360, 471) against msp's 5,200-row device×year table and 10,400 knots, but evaluates sequentially (1.0 ms vs 38 µs for 10 T after the 0.35 s P1 build). Memoryless families: apparent parameter savings (e.g. B4-02 M 5,182 vs 5,394) are all explained by source fan-out, shared w_k and the implicit origin, which the Σ form also uses. No speed advantage |

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
  - K37 passive RC realisation of kinked or jumping kernels

## Counterexamples and findings
1. **S/H without late reset fails.** For integer τ the comparator fires after the cell has closed, so an S/H that samples only at cell ends misses the replacement. Measured error: up to 3.15e-2 (B1-04) and 3.27e-2 (B1-02) on M.
2. **The automaton matches in the excluded band where the interval form does not.** With the late reset, the automaton matches refcalc inside (K, sw(τ)], where msp's interval form deviates by up to 3.12e-2 (B1-04, M, T = 15.0000000075). This makes SUM-03(msp) 2.5e-5 off there. Seen on 2 scenarios only; this is outside 𝒟′ and is not generalised.
3. **The continuous RC decay agrees only at whole years** (H-B3 numbers above).
4. **A naive "irreducible parameter" metric would wrongly suggest circuit compression** in every memoryless family. See H-B4.

## Mismatches vs architecture [H] statements
- The step counts 1,528 / 95 / 166 are **confirmed**: 1,358 sp + 170 match; 95 sp; 156 sp + 10 match.
- The representative units B4-02 (atom), B6-03 (cell), B3-01 (density + gated cell), B1-03 (atom + gated cell) and B1-04 (interval) are **confirmed** as their kinds. Two qualifications:
  - B1-04 also carries a jump-form EMIT ("kept for comparison only"); the unit value at T uses the interval form.
  - Scenario S has B5-01 = 0 (no pieces), so atoms in S are tested through B4-02 only.
- **"6 kernel kinds" is complete for C(T) only.** Other T-dependent outputs need further kinds: counts (K15), division by T (K24), shares (K25) and T-dependent predicates (K26).
- **Boundary points.** 10.000000005 and 10.00000002 lie in `scenarios.valid_domain`'s relative knife window (1e-10 < d < 1e-8) whenever an event at 10 exists. 10.000000005 is also inside the band excluded from 𝒟′. They are therefore **not inside 𝒟′**, contrary to the wording of the G2 instruction. They were still asserted, labelled `band_in`/`band_out`, because the comparisons there are deterministic (not within ulps). Only T = τ(1+1e-9), labelled `knife`, is treated as undefined and recorded without assertion.
- **03 §3.4's reported band deviation** (B1-04 5.5e-3) is exceeded at our points (3.12e-2). This is not a contradiction: it was measured at different points and scenarios.

## Completed tests
`python3 -B -m unittest discover -s <route>/tests -v` → **16 tests, 16 OK, 0 failures** (log: `results/log_tests.txt`; ~32 s). `test_oracle.test_each_kernel_within_tolerance` contains 22 subtests.

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
- H-B2 independent review (D)
- SageMath/MATLAB (not needed)
- integration with A/C/E (coordinator)

## Next actions
1. D reviews the H-B2 sketch and re-checks the late-reset finding with an independent rational implementation.
2. Run K26/K30 netlists, and X-11/SUM-04/B4-03.
3. Run the band test on more scenarios, e.g. `scenarios.design_set`, to see whether the agreement of the automaton in the band holds generally.
4. The coordinator compares the K-list with route C's DIRECT time_form list (X3).
