# Integration STATUS: G4 (fictional data only)

## Run record
- **Branch, model and scope.**
  - Branch `claude/wlc-equivalent-circuit-20261124` @ `2ae99ce54cf13dc66d0eb16835beaf2cc20855a0`, verified before work. All routes had finished this cycle.
  - Model actually run, self-reported: **`claude-opus-5-5`** (Opus 5.5). High effort was requested; the effort level **cannot be observed** from inside the session.
  - Files were written **only** under `WLC_CIRCUIT_RESEARCH/integration/`. There were no git operations (no checkout, commit or push), and no route, study, app or frozen file was edited.
  - `tstudy.baseline.assert_frozen()` passed in every script (refcalc `8976efea…`, synth `55caf5cd…`, common `ad3d0b7e…`). No `__pycache__` was found anywhere in the checkout after any run (checked in code and with `find`).
- **Inputs read:**
  - `12_FINAL_OPERATING_PLAN.md` and `07_SHARED_CONTRACT.md`;
  - `coordination/architecture.md`, `ARCHITECTURE_ERRATA.md` and `RUN_MANIFEST.json`;
  - D's `VERDICTS.md` (passes 1–3), `STATUS.md` and `claims.md`;
  - the STATUS and claims files of A, E, B and C;
  - the code of `D/oracle_d.py`, `D/p2_gates.py`, `D/p2_common.py`, `B/grammar.py`, `B/oracle_io.py`, `B/route_b_experiments.py` and `C/common.py` (only the parts needed).
  - Input sha256 values are in `results/*.json` → `meta.inputs_sha256`.
- **Review status of the inputs.**
  - At the time of the G4 run, the B and C fix passes (`013b1e5`, `a0bb507`) had not been re-reviewed. **D pass 4 (HEAD `6585f4a`) has since confirmed both:** B is ACCEPT, with H-B1 overall still PARTIAL; C is ACCEPT, with the MAPPING constructs still [H].
  - B's `grammar.py`, which the composed model uses, is byte-identical to the version D reviewed (`git diff 06e0943 HEAD` is empty for this file).
  - C's code changed only in `build_mapping.py` (the truncation fix).

## What was integrated
- **Composed model:** see `composed_model.md`, with the code in `code/` and the tests in `tests/`.
- **Φ side** (`code/phi_hybrid.py`) is a **thin independent re-implementation**. It contains one physical-time hybrid automaton for P0/P1/P1′/P2/Px with two realizations of the same operating term:
  - a charge accumulator (A's construct);
  - a resistor + energy meter with κ, where events are external additions (E's construct).
  - Common to both: set-rule simultaneous events and an explicit convention parameter (right/left/orig).
- **Ψ side** (`code/psi_compose.py`) is a **documented composition**:
  - the per-unit signals come from B's D-verified 𝒢 netlists and the late-reset refrigerant automaton;
  - C's single-summing-node rule is applied over the 22 COMP rows of units70.json.
- **Bridge.** X5 (C − M = Z) is executed on EV9. The Φ pilot and the Ψ model are different models. They are joined only by this identity, and their only shared-data link is X2 (P0 in the orig convention vs B's θ_ε netlist).

## Commands run
```
cd /home/user/-/whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/integration
export PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0
python3 -B code/run_integration.py     # rc 0, ~55 s -> results/phi.json x2_link.json psi.json psi_integrator_cells_EV9.json x5.json, run_integration_log.txt
python3 -B code/mutation_check.py      # rc 0 -> results/mutation_check.json (4/4 mutants detected)
python3 -B code/bench_int.py           # rc 0, ~95 s -> results/benchmark.json, bench_log.txt
python3 -B -m unittest discover -s tests -v   # 17 tests, 17 OK, 0 fail, 16 s -> results/test_log.txt
find /home/user/- -name __pycache__ -not -path '*/.git/*'   # empty
```
The route suites were **not** re-run by the integration. The coordinator's re-runs are recorded in RUN_MANIFEST: A 27/27, E 24/24, B 17/17, C 16/16, D 25/25.

## Results (headline)
| check | result |
|---|---|
| Φ vs D's rational ledger: 19 case × convention combinations × 2,118 points × 2 realizations | 0 mismatches (exact) |
| Φ vs A's published rows | 595/595 equal |
| X2 link: Φ (orig) vs B's θ_ε netlist | max rel 0.0 at 17 T |
| Ψ vs refcalc on EV2, EV9, EV9-noB2 (1,926 comparisons: total, stages, 21 DIRECT units) | max rel 2.6e-13 |
| C-1n control | executed: the naive 21-source sum is off by 0.056–1.6 %, and the error equals B2-01. D pass 4 confirmed it on EV0/EV7 (0.073–3.07 % / 0.071–1.64 %; = B2-01 to ≤3.2e-13) |
| X5 on EV9, 5 T | exact; Z′ < 0; dC/dT ≠ ρ |
| Mutations (no supersession, orig without moving external events, β ignored, no late reset) | all 4 detected |
| Benchmark | no speed gain against the best direct baseline: Φ 6.1× slower than knots; Ψ about 730× slower per query than the canon knot form |

## Rejected, left out or not composed (why)
- **[H] items are not promoted:** D-9, D-10, D-16, D-24, D-12, the general statements of A-3/A-6/A-10/A-16, E-3c and E's Walsh cost. None has had an independent review.
- **Joule pulses for events** (one resistor) are not composed. They are non-additive (cross term 2√(AiAj)·ρ). The Walsh design is not implemented, so events stay external additions.
- **AC currents, rectified clocks and EF switching** are accepted route findings but lie outside the composed domain, which covers piecewise-constant rates only and exact arithmetic.
- **P2/Px under orig** are undefined and rejected with a ValueError.
- **E's "substitute" as a net −5 entry** has the value accepted, but the encoding was not adopted, because it cannot express P1′ or per-ledger readouts. The integration uses A/D supersession.
- **C's MAPPING constructs, classes and 4-tuples** remain [H]. The integration simulated **B's** constructs for all 21 DIRECT units, not C's declared rows.
- **H-B1 kinds K26/K28/K30/K32/K33** are NOT_RUN. They are not needed for C(T)=SUM-03, so H-B1 stays PARTIAL.
- **The refrigerant band and the float knife edge** are documented boundaries and are not asserted.
- **SUM-05** (division by T), shares and `match` are class d and outside the domain.
- **SageMath/MATLAB, the Math7 seven-engine workflow and SPICE** are NOT_RUN. No workflow was dispatched.

## Plan gates (12 §5)
| gate | verdict | basis |
|---|---|---|
| 1. Original formula, units and time boundaries agree | **PASS** (declared domains only) | Φ exact under 3 explicit conventions, with the closed band; Ψ float ≤2.6e-13 against refcalc on 2 unused scenarios inside valid_domain; units in kgCO2e, with J only through the explicit κ. The float knife edge is recorded as undefined, not asserted |
| 2. Different periods, simultaneous replacement or renovation without double counting, post-replacement state change | **PASS** (fictional pilots and synth scenarios) | P1 under both policies with the set rule (order-free; mutation M1 is detected); P1′ restart; P2 rate latch; Ψ late-reset refrigerant state (mutation M4 is detected) |
| 3. Fewer internal states while keeping future events and output | **PARTIAL** | Exact reductions exist only for known schedules (single clock, A-8/A-9). Every tested merge loses events (A-11, D-11, replay C-2r). The online-reset lower bound is [H] and unreviewed. No Ψ state reduction was found (D-23; rank ≠ state) |
| 4. Operations, time, memory and state against Σ/knots on the same point sets | **PASS** (measured); result negative | `benchmark.md`: no speed gain, so the value is **representational only** |
| 5. No conflation with the J-CAT 667-formula experiment; fiction is not real-building validation | **PASS** | Only the fictional pilots and the 70-unit synth model were used; no real-building, novelty or energy-saving claim is made |

## Overall verdict
- **G4 integration: PASS on the declared common domains.** D's pass-4 recommendation is **ACCEPT-WITH-CONDITIONS**. Its conditions 1 and 2 are closed by the documentation pass; condition 3 (status stays PARTIAL) is kept.
  - A composed Φ hybrid (two realizations) and a composed Ψ summing node over verified kernels are tested against non-composed oracles.
  - They are joined only through X5, which is exact on EV9.
- **Research status overall: PARTIAL.**
  - H-B1 is PARTIAL (4 kinds NOT_RUN).
  - Gate 3 is PARTIAL.
  - The [H] items are unreviewed.
  - C's per-unit MAPPING constructs are unsimulated.
  - The seven-engine check is NOT_RUN.
- **No "optimized equivalent circuit" is claimed.** The circuit forms reproduce the same values with no smaller information-preserving state and no speed gain.

## D pass 4 re-verification (documentation update, HEAD `6585f4a`)
Source: `routes/D_verification/VERDICTS.md` pass 4 and `routes/D_verification/results/p4_integration.json`. No new experiment was run in this update.
- **D's recommendation for G4: ACCEPT-WITH-CONDITIONS.**
  - Φ: 353,940 fresh points (116 case × convention × realization combinations, seed 5151; also τ_R ∈ {13, 27} and Px t_early ∈ {3, 13, 23.5}), 0 mismatches against D's ledger.
  - Ψ: EV0 and EV7 (plus EV7 without B2 and an EV0 stage subset), ≤3.2e-14 against refcalc.
  - X5 is exact on EV7 at 6 T, and the X2 link gives 0.0.
  - The benchmark was reproduced at 5.6× (Φ) and ~850× (Ψ); the integration's own figures were 6.1× and ~730×.
- **Conditions from D, and their status after this pass:**
  1. Update I-18, the "not re-verified" line in STATUS, C-1n in coverage and N1 in next_experiments: **closed** by this pass.
  2. Keep the share source noted as untested for invalid shares: **closed (recorded)**, see the untested edge below and `disagreements.md` §4.
  3. Research status stays PARTIAL: **kept**.
- **Untested edge.** `code/psi_compose.py:53-55` takes the B2-01 share from `scn.operation.facility_management_ratio`, with its own [0,1] check, instead of msp's `b21.share`. It matches refcalc on every scenario tested (EV2, EV9, EV0, EV7), but no invalid-share scenario has been tried.
- **Open items.** D's consolidated open-items table for the whole study is in `routes/D_verification/VERDICTS.md` pass 4 ("Consolidated open items"). It is referenced here, not copied.
- **Gate verdicts are unchanged.** D's pass-4 evidence adds scenarios and points but does not change any gate. Gate 3 stays PARTIAL, and the overall research status stays PARTIAL.
- **Test re-run after the documentation edits:** see `results/test_log.txt`.

## Files
`composed_model.md`, `evidence_index.md`, `coverage.md`, `disagreements.md`, `benchmark.md`, `next_experiments.md`; `code/{int_common,phi_hybrid,psi_compose,run_integration,mutation_check,bench_int}.py`; `tests/test_integration.py`; `results/*.json`, `*_log.txt`.
