# Route D verdicts — G3 pass 1 (routes A and E only)

Inputs: branch `claude/wlc-equivalent-circuit-20261124` @ `e182105` (route files as committed there; A/E report source `5a2f898`).
Verdicts: CONFIRMED / REFUTED / PARTIAL / NOT_RUN. "Confirmed" means D's own independent computation agrees on the stated domain; it is not a proof, a real-building validation or a novelty finding.
Evidence paths are relative to `routes/D_verification/`. Line numbers refer to the files at `e182105`.

## Route A (`routes/A_waveform/claims.md`)
| claim | verdict | D evidence | required fix |
|---|---|---|---|
| A-1 R1 = oracle at 11 points, 3 conventions | CONFIRMED | `results/boundary_comparison.json` (490/490 A rows match D's ledger oracle); `results/probe_routes.json` (R1 on 100 044 right + 20 044 left + 20 044 orig points, 0 mismatches) | — |
| A-2 limits and jumps at event times | CONFIRMED | `boundary_comparison.json` `exact_limits_P0` (exact one-sided limits, not δ samples) | — |
| A-3 convention ⇔ reset semantics; "orig band [nc, nc/(1−ε))" | PARTIAL | semantics confirmed (R1-orig = D orig on 20 044 points + knife + band end). The band is **closed**: at T=10/(1−ε) right gives 159.99…, orig 139.99… (`boundary_comparison.json` `orig_band`); A's own test asserts this (`tests/test_a.py:85`) | write `[nc, nc/(1−ε)]` in A-3 and in architecture §1.2 |
| A-4 knife points 10.000000005 / 10.00000002 | CONFIRMED | `boundary_comparison.json` | — |
| A-5 float knife edge 10.00000001 | CONFIRMED | float `t(1−ε)` = 10.000000000000002 > 10 → counts; exact excludes (`float_slip_through`) | — |
| A-6 R2 ramp − sawtooth = R1 | CONFIRMED | `probe_routes.json` R2, 0 mismatches on 140 132 points | — |
| A-7 readout invariant in (γ, C_cap), E_cap ≠ carbon | CONFIRMED (algebraic only; D did not re-execute) | G=γQ, Q=G/γ, E_cap=Q²/2C_cap | — |
| A-8 R3/R3i/R3k reproduce P0 | CONFIRMED | `probe_routes.json` (R3 all 3 conv; R3i, R3k right/left) | — |
| A-9 counterexample: fixed Px with one period-20 clock, comparators {7/20,17/20,1} | CONFIRMED | `results/states_check.json` `px_fixed_schedule` (Px phases mod 20 = {0,7,17}; periodic rebuild = Px jumps to t=200); `probe_routes.json` R3i_Px 0 mismatches. Extension: any early reset s∈(0,10) gives 3 comparators; s∈(10,20) leaves a transient at t=10 → 4 | — |
| A-10 online reset: futures 107 vs 127, 64 vs 99; "two phases necessary" [H] | PARTIAL | numbers confirmed (`states_check.json` `online_reset`). D adds a lower-bound proof draft (claims D-9, still [H]) and a realization with **2** continuous states + 2 counters (`online_two_continuous_states`, exact for 6 reset times) → A's (3,0,3,1) is not minimal in continuous dimension | state the tuple trade-off; do not report (3,…) as required |
| A-11 merged clocks 30 / 15 / 20⁄3 fail | CONFIRMED (strengthened) | `states_check.json` `merged_clocks`: a single-charge clock has equal jumps, P0 has jumps 20 and 55 → fails for **every** period | — |
| A-12 P1 250/405, 305/460, left 200 | CONFIRMED | `results/events_check.json`; probe P1 0 mismatches | — |
| A-13 naive sequential gives {250,270,285,305} | CONFIRMED | D's own naive processor (`oracle_d.naive_sequential_G20`) and A's R1: same 6-order table | add a permutation test of the **set** rule (`test_a.py:234-236` says it is trivial and does not test it; D checked a reversed clock list + 200 shuffled ledgers) |
| A-14 P2 160/245/295/380/515 | CONFIRMED | `events_check.json` P2; year-cell rounding would give 159/244/294/379/514 → not used | — |
| A-15 zero-mean AC bounded, cannot drive clock | CONFIRMED (bound) | `joule_ac_check.json` `zero_mean_ac` (4 phases; range width 2I0/ω). With a threshold below the swing a subtract-reset clock fires by frequency (3 counts in 10 y at θ=0.1, ω=2π) | the "never fires" assertion is hard-coded: `circuit_a.py:333-335` returns 0 without integrating, so `test_a.py:272,276` are tautological; simulate the clock instead |
| A-16 rectified clock exact iff c/h∈½ℤ | PARTIAL | true at phase 0 (c/h=k/4: exact iff k even). **Phase-dependent**: at φ=π/4, 0.3, 1.0 half-integer multiples are off by 0.04–0.08 yr; exact half-integer phases are only φ∈{0, π/2} mod π (`joule_ac_check.json` `rectified_clock`). The "else error < h" bound holds but is ~9.5× loose: sharp bound m·h/2 = 0.10526 h (sampled max 0.105257 h) | qualify A-16 with φ∈{0,π/2}; general φ: iff c/h∈ℤ; quote 0.1053 h |
| A-17 full-wave ripple ≤ 0.2105 I0/ω | CONFIRMED | analytic max of 1−cos u−2u/π at u=asin(2/π); consistent with D's sharp hit bound | — |
| A-18 no speed benefit | CONFIRMED | `results/benchmark.json` (D's own implementations, 100 011 points) | — |
| A-19 (1,0,∞,0) remark | NOT_RUN | unimplemented remark. Note: with a floor-type static readout, one ramp gives (1,0,0,0) (that *is* the closed form), so tuples are only comparable for a fixed readout class | state the readout class used for counting |
| latent: `R3i(conv='orig')` | defect (outside A's claimed domain) | `circuit_a.py:250-280` (conv param line 255) accepts `orig` but uses ν=1/L (no ε): G(10.000000005)=160.00000002 instead of 140.00000002 (`probe_routes.json`); untested (`test_a.py:158`) | reject `orig` in R3i or slow the clock |
| latent: P1 under `orig` | defect (outside claimed domain) | `circuit_a.py:40` slows only clocks; `:123` uses the ExtEvent time unslowed (`:44-50`, `p1_r1` `:165-169`): ExtEvent time not mapped to τ/(1−ε) while clocks are slowed. A.R1 additional@30 = 290 vs A's own `g_p1(orig)` = E = D = 345; @20.00000001: 250.0000004 vs 200.0000004 | raise for orig P1, or slow external events too |

## Route E (`routes/E_resistor_energy/claims.md`)
| claim | verdict | D evidence | required fix |
|---|---|---|---|
| E-L0 Joule heating textbook | CONFIRMED [L] (not a D result) | — | — |
| E-1 E-R1 = P0, 11+2 points × 3 conventions | CONFIRMED | `boundary_comparison.json` (39 P0 rows); `probe_routes.json` ER1 100 044 + 2×20 044 points, 0 mismatches | — |
| E-1s resistor stateless; tuples | CONFIRMED | merged register (3,0,2,0) = A's R1 rule; table-driven (1,1,1,6) = D's single accumulator (`states_check.json`) | P1 tuple `[4,0,3,0]` (`make_results.py:39`) omits the renovation table entry that A counts (3,0,3,1) |
| E-1t temperature ≠ cumulative energy | CONFIRMED (analytic only) | θ=PR_th(1−e^{−t/R_thC_th}) ≤ 12 K | — |
| E-2a DC×pulse cross 4√(20w), 4√(35w) | CONFIRMED | `joule_ac_check.json` HE2 (exact coefficient bookkeeping) | — |
| E-2b simultaneous cross 20√7, width-independent, 60√7 by t=60 | PARTIAL | equal, aligned windows: 52.91502622129181181 for w=1e-6, 1e-2, 1 (D). The "general 2√(AiAj) form" is **false** for unequal/misaligned shapes: widths w and 4w → √700 = 26.4575; half overlap → 26.4575. General: 2√(AiAj)·ρ, ρ = L² cosine of the two pulse shapes (claims D-12) | restate with ρ; 20√7 is the Cauchy–Schwarz maximum |
| E-2c polarity counterexample 202.097 vs 307.974 | CONFIRMED | D: 202.097090547215786, 307.974471628064207 | — |
| E-2d separate resistors / summed powers restore additivity | CONFIRMED, conclusion REFUTED | the fixes work, but they are not the only ones: on **one shared resistor**, time-interleaved pulses remove the event×event term and Walsh-orthogonal zero-mean pulses remove every cross term exactly (window energy = 4w+55 exactly) (`joule_ac_check.json` `walsh_orthogonal_single_resistor`). E STATUS "single-resistor integration of events is dropped" (architecture early stop (2)) is too strong | keep single-resistor designs with L²-orthogonal excitations as a valid option; note that the trick is not available to a charge accumulator (zero-mean pulses carry no charge) |
| E-2e finite pulse yields left value at τ | CONFIRMED | `joule_ac_check.json` X1 (separate pulses = left value at 10,20,30,40,60) | — |
| E-3a lattice exactness | CONFIRMED | quadrature: 0 at t=1/4, 1/2 and on the second family t=(π−4φ)/(2ω) | — |
| E-3b 9.999999 → +3.99999999989e-6 kg | CONFIRMED | quadrature 3.99999999989e-6 | — |
| E-3c sup = r(1+|sin2φ|)/(2ω) | CONFIRMED | 12 random (φ,ω), quadrature on 60-point grids: 0 violations, max grid/bound 0.99999; attained at predicted t* to 1e-15 | could become [P] after review (one-line: |sin x − sin 2φ| ≤ 1+|sin 2φ|, attained) |
| E-4 convert-then-integrate | CONFIRMED | `joule_ac_check.json` HE4: 40/70/130/190; 30/60/120/180; 40/80/160/240; full G 150/235/505 | — |
| E-5 no speed advantage | CONFIRMED | `benchmark.json` | — |
| E-N κ explicit (1.2e6 kg/kWh) | CONFIRMED | (1/3)·3.6e6 = 1.2e6 | — |
| STATUS "H-E1 … P1 250/405, 305/460 reproduced" | REFUTED as a realization claim (values correct) | `make_results.py:35-39` writes `value=J.p1(...)` (closed form, `joule.py:74-78`) under the label "E-R1 + one-shot external addition"; `circuit_e.py` has no renovation | implement P1 in E-R1 or relabel the rows as closed form |
| benchmark "fixed-step dt=1e-3 max err 3.1e-10" | PARTIAL (misleading) | `make_results.py:113-118` computes events by closed-form floor on the step grid with a `+1e-12` fudge; only the ramp is stepped. D's true fixed-step integration (clocks stepped too) is off by a full charge at event instants: G(10)=140 at dt=1e-2,1e-3,1e-4; 75 / 9 / 7 of 100 011 points off by >1 kg (each a full 20 or 55 kg charge) (`benchmark.json` `fixed_step_errors`) | label as "ramp-only stepping"; report event-detection error |

## Architecture hypotheses and gates (A/E side only)
| item | verdict | evidence |
|---|---|---|
| §1.2 table (3 conventions, 14 points) | CONFIRMED values; band wording REFUTED (closed, see A-3) | `boundary_comparison.json` |
| §1.2 P1 / P2 / Px values | CONFIRMED | `events_check.json` |
| H-A1, H-A2 | CONFIRMED | above |
| H-A3 | REFUTED as stated (fixed Px needs one clock); online part PARTIAL (≥2 continuous [H], 2 achievable with counters) | `states_check.json` |
| AC negative test | CONFIRMED (zero mean bounded); "rectified exact only for integer multiples" is true for generic phase, false at φ∈{0,π/2} mod π | `joule_ac_check.json` |
| H-E1, H-E3, H-E4 | CONFIRMED | above |
| H-E2 | CONFIRMED (equal aligned widths); generalization needs ρ | above |
| X1 (A vs E, same P0) | PASS | A points = E points = D at all common rows; outside windows identical; inside windows E-separate = left value; one-resistor difference = DC cross + 2√(AiAj)ρ, A's charge additive | 
| X2 A-side | PASS (A-side only) | A orig realizations = D orig oracle on 20 044 points + knife + band end. B-side NOT_RUN |
| X2 B-side, X3, X4, X5, Z(T), refrigerant, routes B/C | NOT_RUN | out of scope of this pass |
