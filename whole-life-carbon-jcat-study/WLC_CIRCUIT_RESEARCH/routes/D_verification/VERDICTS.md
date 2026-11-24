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

---

# Pass 2: routes B and C, gates X2 (B side), X3, X4, X5
Inputs: HEAD `06e0943`, with the route B/C files as committed there. The frozen trees were verified by `assert_frozen()` before every pass-2 script: refcalc `8976efea…`, synth `55caf5cd…`, common `ad3d0b7e…`. Routes A and E were not assessed in this pass.
D ran on scenarios that neither route used: `evaluation_set` items 6 and 10 (seed 720002; EV6 is `SYN-RC-office-M-T50-seed389633541` and EV10 is `SYN-RC-retail-S-T100-seed169387912`).
- Random T used seed 2026.
- Boundary and band points were placed around integer refrigerant event times, including T = sw(τ) itself and ±1 ulp.
- Benchmark S/M and the edge scenario `rebuild_within_period` were used only where a route's own number had to be re-measured.

All agreements in this pass are float agreements (relative), except where a result is marked exact.

## Route B (`routes/B_formula_network/claims.md`, `MAPPING.csv`)
| claim | verdict | D evidence | required fix |
|---|---|---|---|
| H-B1: the six C(T) kernel kinds are generated by 𝒢 netlists | CONFIRMED for the six kinds. PARTIAL overall, as B itself states: K26, K28, K30 and K32 are NOT_RUN. | `results/p2_check_b.json`. On EV6 and EV10 (90 T, 64 of them in 𝒟′), D's own kernel evaluator (03 §5.1 written out independently) differs from refcalc by at most 4.8e-13 (B3-01) and by ≤1.7e-15 for every other unit. B's clip and integrator netlists differ from D's values by ≤8.2e-16 for B4-02, B5-01, B6-03, B7-04, B3-01, B1-03, B1-02 and B2-01, both in and out of 𝒟′. | — |
| H-B3 (S/H part): the automaton reproduces B1-02/03/04 from raw inputs | CONFIRMED | B's automaton differs from D's exact recurrence (03 §5.5 plus refcalc docstrings, from raw inputs) by ≤8.2e-16 everywhere, inside the band included. D's recurrence differs from refcalc by ≤1.1e-15. | — |
| H-B3 (RC-a/RC-b numbers 2.88e-3 etc.) | NOT_RUN by D | — | — |
| Late-reset counterexample ("without it up to 3.15e-2 / 3.27e-2") | CONFIRMED, and the effect is much larger | With `late_reset=False` the error inside 𝒟′ reaches 0.97 (B1-04), 1.0 (B1-03) and 0.87 (B1-02) relative on EV6/EV10. The missing reset corrupts every later T, not only the band. B's 3.15e-2 is specific to its scenario. | report the magnitude as scenario-dependent |
| Automaton matches refcalc in the band (K, sw(τ)] where msp deviates (3.12e-2) | CONFIRMED; the deviation is larger here | In the band the automaton differs from refcalc by ≤5.1e-16, while msp's interval form B1-04 differs by up to **1.24** (EV10, at sw−1 ulp) and SUM-03(msp) by 1.1e-4. **At T = sw(τ) itself msp agrees** (0 to 2.5e-16), so the observed deviating set is the open band (K, sw(τ)), as 03 §5.4 writes; 03 §3.4's closed (K, sw(τ)] is a conservative exclusion. | none for B. Wording for the record: per 03 §3.2/§3.4 refcalc (基準計算) defines the model; 𝒟′ excludes the band and the source itself documents the interval-form deviation as an unresolved boundary (§3.4, §5.4 / TH-2-3). This is **not** an original-theory defect. |
| H-B2: passive LTI RC cannot equal a kinked or jumping kernel | CONFIRMED-as-textbook, with GAPS | Review below | scope the claim to **LTI** with sources analytic on (0,∞). Fix `hb2_passive.py:8-9` ("every passive RC response is in it" is false: a DC current source into a capacitor gives c·T, i.e. s=0 double root, which the basis {1, e^{−λT}} lacks). Reclassify `MAPPING.csv` K10 ("clip is a saturating (active) element") and K37 as relative to the grammar 𝒢, not physical. |
| H-B4, memoryless families: no circuit-specific compression | CONFIRMED (B's own analysis; D did not re-count) | — | — |
| H-B4, refrigerant: "refutes H-B4 in the stored-state metric" (`claims.md:64`) | REFUTED as a representation claim: it is a **metric artefact** | `results/p2_hb4.json`. On BM-M (B's own scenario) the **merged** knot forms of B1-02/03/04 (canon.py) need 263 + 417 + 345 = **1,025** coefficients, against **1,072** numbers in the automaton tuple (160, 81, 360, 471). The 5,200-row table and 10,400 knots B compared against are msp's *unmerged* per-device pieces. EV6 gives 625 vs 1,246. Random access: automaton replay 0.43–0.54 ms/T, merged exact-Fraction form ≈5.5 µs per unit per T, msp float form ≈0.24 µs. tracemalloc: automaton 74–78 KB, merged Fraction KF 0.19–0.31 MB. This is the same order of stored numbers, a constant-factor memory difference and a 100× slower random access. | restate as a time–memory trade-off against the merged form; no asymptotic state saving |
| `MAPPING.csv` K16/K17/K19 "per device" tuples | minor inconsistency | K19 lists (4,2,H−1+#events,#events+6) *per device*, but the H−1 cell thresholds are shared. `grammar.py:454` returns totals (4nd, 1+2nd, (H−1)+n_ev, n_ev+6nd). | state shared vs per-device counts |
| Test audit | no tautology found; weak points noted | `test_oracle.py` compares against refcalc, an independent oracle, but only on benchmark S/M, the same scenarios as the experiments (no out-of-sample run). The ablation/band tests are one-sided inequality observations (`test_oracle.py:57,61`). `test_grammar.py:83-107` `hand_refrigerant` is an independent restatement and is fine. B1-02 [P1 cells] in the band is 8.9e-10 from refcalc on EV6, within B's 1e-9 tolerance by only about 10 %. B excludes band-sensitive kernels only at `band_in` (`route_b_experiments.py:213`). | add an out-of-sample scenario to the tests |
| Boundary points outside 𝒟′ | B's handling CONFIRMED | 10.000000005, 10.00000002 and every band point τ(1+δ) with 1e-10<δ<1e-8 lie in `valid_domain`'s knife window, so they are outside 𝒟. B labels and asserts them deterministically and does not assert the knife point. Minor: the band comment at `route_b_experiments.py:31` and `test_grammar.py:24` writes the half-open "[τ, τ/(1−ε))" (see pass-1 A-3). | — |

### H-B2 review (proof sketch, `claims.md:18-31`)
**What is sound.** For a lumped LTI RC network whose sources are analytic on (0,∞), including DC switched on at 0 and sinusoids, every response is real-analytic on (0,∞). An analytic function that is affine on one side of a knot is affine everywhere (identity theorem). So no kink or jump can be reproduced exactly on any interval containing a knot. This is textbook material [L] and a corollary of TH-1/TH-7. No novelty.

**Gaps.**
1. Step 2's exponential-polynomial form needs exponential-polynomial sources. Analyticity of the sources is enough for the argument, and it must hold on a neighbourhood of (0,∞).
2. The statement must say LTI, not just passive. The following passive networks reproduce the kernels exactly:
   - A **time-varying passive** network: a switch, closed only on (k,k+1], connecting a DC current source to a capacitor gives w_k exactly.
   - A **nonlinear passive** network: an ideal-diode clipper gives clip(·,0,1) exactly.
   - An ideal switch with a charged capacitor gives jumps.

   B's "class e / active" labels are therefore relative to 𝒢.
3. The illustration's basis omits the T term (see `hb2_passive.py:8-9` above).
4. The kink sup error goes to 0 as the order grows (Müntz-type density); "never 0" holds only at finite order, which B states correctly.

Verdict: **CONFIRMED-as-textbook for LTI; GAP in scope wording.**

## Route C (`routes/C_70_units/claims.md`, `MAPPING.csv`)
| claim | verdict | D evidence | required fix |
|---|---|---|---|
| C-0 inventory, roles, COMP | CONFIRMED | `results/p2_check_c.json`: 70 rows. Role counts in MAPPING equal units70.json (DIRECT 21, AUX 15, DEC 9, REF 10, AGG 9, BRK 6). The 22 COMP rows in units70.json equal `specs/system.py` COMP_ROWS (stage, unit, sign). The only non-trivial β is (B6, B2-01, −1, ι_B2). | — |
| C-1 / H-C1 composition = one summing node (C's own caveat: refcalc X-02 implements the same rule) | CONFIRMED, now **independently** = gate X4 PASS | D composed in exact Fraction arithmetic from units70.json COMP rows. Per-unit values: D's raw refrigerant recurrence for B1-02/03/04, D's kernel evaluator (03 §5.1 rate form) on the msp/canon amplitude columns for the other T-dependent units, and the msp constants. Five cases (EV6, EV10, BM-S, EV6 without B2 to exercise β=ι_B2, EV10 restricted to {B1, B4, B6, C3}) × 9 T, all in domain. vs refcalc SUM-03: ≤**3.3e-14**. vs X-02 by_stage: ≤2.2e-13, with equal stage key sets. vs canon's own total: equal in float. refcalc's own unit floats summed exactly vs SUM-03: 3.6e-16. | Caveat: the non-refrigerant amplitudes still come from msp P1. That is a different implementation from refcalc but the same project, so the independence is at implementation level, not at data level. |
| C-1n naive Σ of 21 DIRECT errs by B2-01/C | NOT_RUN by D | — | — |
| C-2 block-type consistency (signature detector) | NOT_RUN by D (detector not re-implemented); X3 set comparison below | — | — |
| C-2r year-table replay counterexample (B1-03, B3-01 0.18–0.6 %) | CONFIRMED | D's own exact replay (by_year at T=60 replayed with w_y(T), 240 cell-interior points per scenario). B1-02 exact (≤6.5e-16). B3-01 **0.15–0.56 %** (BM-S 0.56, BM-M 0.26, edge 0.15; C measured 0.18–0.6 % on an 8-point grid). B1-03, B4-02 and edge B5-01 are grossly wrong (up to 0.31 / 0.15 / 0.44 of their own scale). The replay is not the declared structure, so the failure shows that annual tables lose intra-year event timing, as C says. | — |
| C-3 ranks: total 1; stage 6/6/7; DIRECT 7/8/9 | CONFIRMED **exactly** (rational Gaussian elimination, rank modulo constants, 240 T) | S 1/6/7, M 1/6/8, edge 1/7/9; extra EV6 1/7/9. Each rank equals the number of T-varying stages or units, so no varying column is linearly dependent. A float SVD with route C's scaling agrees. | — |
| C-3 interpretation | CONFIRMED with emphasis | The rank bounds the number of independent outputs a fixed linear read-out needs. It does **not** bound the state of a realization: every piecewise-linear waveform still needs its knot schedule (thousands of comparator thresholds or table entries for B3-01/B4-02). Rank 1 for the total does not mean one capacitor suffices. C says the same in its STATUS limits. | — |
| C-3x "7" is scenario-dependent | CONFIRMED | S and M give 6 | — |
| C-4 non-DIRECT roles are not sources | NOT_RUN by D | — | — |
| C-5 constructs, classes and tuples are [H] design rules | CONFIRMED as correctly labelled | No row has status exact or verified; every evidence string carries [H]; all 21 DIRECT rows are marked circuit_simulation NOT_RUN. 10-row sample (seed 20261124: B4-01, SYS-01, A13-02, B1-03, X-07, X-10, B3-01, SUM-08, B6-03, B6-02): role, stage, time_dependent, comp_rows, id and name match units70.json and the ledger text. | `time_form_text` is **truncated to 160 characters** (`build_mapping.py:148`). For B1-03 and B3-01 the jump/slope details are cut, so the column is not the full ledger form; say so in the header or drop the truncation. |
| C-6 t=0 vs t=T placement not observable from V(T) | NOT_RUN by D (consistent with TH-4(c); see X5) | — | — |

## Gates
| gate | verdict | evidence |
|---|---|---|
| X2 B side: P0 in the original convention, B's θ_ε kernel vs D's rational ledger and A's published orig points | PASS | `results/p2_gates.json`. B's netlist on the P0 pieces equals D's rational orig evaluation at the same float T at all 15 points (difference 0), including fl(10/(1−ε)) and sw(10)−1 ulp. It equals A's published orig values at the decimal t, except at 10.000000005 (2.8e-14 float rounding) and at the float knife edge 10.00000001: there the decimal value is below 10/(1−ε) and excluded, while its float lies 0.46 ulp above it and is counted (20 kg). **Closed band endpoint:** 10/(1−ε) is not a float. fl(10/(1−ε)) = sw(10) = 10.00000001 is the first float that counts, so the closed real endpoint has no float representative. |
| X3: B formula kinds vs C DIRECT block types, both directions | PASS (set level) with one-sided items listed | Both sides give the same 7 types {const_t0, const_tT, year_cell, density, atom, gated_year_cell, interval}; nothing is C-only or B-only. Per unit, the only mismatch is B2-01: C has year_cell, while B lists it under K21 (gain × year cells), a labelling artefact. 27 B kinds have no C block type (P1/AGG/digital kinds, K15 counts, K16 refrigerant state recurrence, K20 RC alternative, K21 gain). This is expected, because C's time_form describes V_u(T) shapes only. Mapping used: `p2_check_c.json` `X3.kind_to_block_map_used`. |
| X4: independent composition | PASS | C-1 row above |
| X5 on EV6 (B1 included): canon.py + timechar.py, conventions read from source | PASS | At 5 T: C − M([0,T]) = Z(T) **exactly** (Fraction), with Z ≈ 1.51–1.54e6 ≠ 0. dC/dT = ρ + Z′ exactly and dC/dT ≠ ρ, with **Z′ ∈ [−3,440, −680] < 0**. C(0+) = 32,166,137.6 ≠ A^init = 30,627,387.7; the difference is A^term 1,461,403.9 + R(0+) 77,346.0, exactly. D's independent Z (msp constants + raw B1-04 recurrence) equals canon's Z (relative difference 0.0). refcalc − Z_D = M_canon within 1.5e-14. Note: `timechar.RT.M` counts atoms with sw(τ) ≤ T (closed [0,T], as in 03 §7), whereas the timechar docstring (line 11) writes M([0,T)). This is a documentation inconsistency in frozen code; it was not edited and is not a defect claim. |

## G4 integration recommendations (limited to what D verified)
- **Route B: ACCEPT-WITH-CONDITIONS.**
  - Accept: the six C(T) kernel netlists (constant, atom, year cell clip/integrator, gated cell, density, B2-01 gain) and the late-reset S/H refrigerant automaton, as float-exact reproductions of refcalc on 𝒟′. The automaton is also exact in the excluded band.
  - Conditions:
    1. Restate H-B4 for the refrigerant as a time–memory trade-off against the merged knot form (no state saving).
    2. Scope H-B2 to LTI with analytic sources; fix the `hb2_passive.py` superset statement; mark the class-e/active labels as relative to 𝒢.
    3. Quote the band as (K, sw(τ)), as in §5.4, and keep §3.4 as the conservative exclusion.
    4. K26/K28/K30/K32 and the RC-a/RC-b numbers remain NOT_RUN.
    5. Do not rely on B1-02 [P1 cells] inside the band (8.9e-10, near the tolerance).
- **Route C: ACCEPT-WITH-CONDITIONS.**
  - Accept: inventory, composition (independently verified), exact ranks and the replay counterexample.
  - Conditions:
    1. MAPPING constructs, classes and tuples stay [H] design rules.
    2. Mark `time_form_text` as truncated.
    3. C-2's signature detector and C-4 are not independently re-checked by D.
    4. Rank statements must keep the "rank ≠ state" caveat.
