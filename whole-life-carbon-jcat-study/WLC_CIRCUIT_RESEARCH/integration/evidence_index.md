# Evidence index (G4) — integrated statements → route claim → D verdict → files

Paths are relative to `WLC_CIRCUIT_RESEARCH/`. Class follows 07 ([P] [E] [F] [S] [L] [H]); **nothing is [P]**. No [H] item was promoted.
Domain codes:
- **Φ** = fictional P0/P1/P2/Px, t ∈ [0,60]
- **Ψ** = fictional synth 70-unit scenarios inside `valid_domain`/𝒟′
- **Φ↔Ψ** = the X2/X5 joins

"Integration re-check" means a new execution in `integration/` against an oracle other than the composed code.
Review status of the inputs:
- D reviewed A and E in passes 1 and 3, and B and C in pass 2.
- The **B and C fix passes after D pass 2 were not re-reviewed by D.** Their restated wording is route-self-reported and marked **(self-reported)**.
- B's `grammar.py` is byte-identical to the version D reviewed (`git diff 06e0943 HEAD` is empty).

## Integrated (accepted and verified)
| # | integrated statement | route claim | D verdict | route / D files | class | domain | integration re-check |
|---|---|---|---|---|---|---|---|
| I-1 | The charge-accumulator hybrid (Q, 2 reset clocks, charge impulses) reproduces P0 exactly at the 11 contract points, the knife points and the exact one-sided limits, under right/left/orig | A-1, A-2, A-4 | VERDICTS p1 A-1/A-2/A-4 CONFIRMED; D-1..D-3, D-31 | `routes/A_waveform/tests/test_a.py`, `results/points.json`; `routes/D_verification/results/boundary_comparison.json`, `probe_routes.json`, `p3_recheck.json` | [E] | Φ | `integration/results/phi.json`: 0 mismatches vs `oracle_d.G` on 2,118 points |
| I-2 | Convention ⇔ reset semantics: right resets at τ, left holds at τ, orig is left with clock rate (1−ε)/c and external events at τ/(1−ε). The right/orig disagreement band is the **closed** [nc, nc/(1−ε)] | A-3 (corrected) | p1 A-3 PARTIAL → fixed, p3 CONFIRMED; D-4 | A `claims.md`; D `boundary_comparison.json` `orig_band`; `coordination/ARCHITECTURE_ERRATA.md` #1 | [E] on P0; general statement [H] | Φ | `test_three_conventions_at_10_and_knife` (closed band endpoint) |
| I-3 | P1 values: substitute 250/405, additional 305/460, left 200 at 20. The set rule is order-free; naive sequential processing gives {250,270,285,305} | A-12, A-13, E-1p | p1 A-12/A-13 CONFIRMED; D-6; p3 (7) E P1 CONFIRMED (with the net −5 caveat) | D `events_check.json`; A `test_p1_*`; E `test_p1_event_driven_circuit` | [E] | Φ | `phi.json` (P1 × 3 conv × 2 realizations); `test_set_rule_order_free`; mutation M1 |
| I-4 | Non-coincident renovation (τ_R=15) restarts AC (25, 35, …) and pipe (35, 55); substitute = additional | (D-declared P1′) | D-7 [E] | D `events_check.json` | [E] | Φ | `phi.json` P1′ rows; `test_noncoincident_renovation_restarts_clocks` |
| I-5 | P2 (rate 4→3 latched by the first AC firing): 160/245/295/380/515; not year-cell rounded | A-14 | p1 A-14 CONFIRMED; D-8 | D `events_check.json` | [E] | Φ | `phi.json`; `test_p1_p2_values` |
| I-6 | The readout G is invariant in (γ, C_cap); E_cap = Q²/2C_cap is not carbon | A-7 | p1 A-7 CONFIRMED (algebraic) | A `test_scale_invariance_and_separation` | [E] | Φ | `phi.json` gamma_Ccap_invariance (3 pairs, executed) |
| I-7 | Resistor + energy meter with explicit κ (events as external additions) reproduces P0/P1/P2. The resistor stores nothing; the integrator is the state | E-1, E-1s, E-1p, E-N | p1 E-1/E-1s CONFIRMED; p3 (7)/(9) CONFIRMED; D-3, D-31 | E `code/circuit_e.py`, `results/points.json`; D `probe_routes.json`, `p3_recheck.json` | [E] | Φ | `phi.json` joule realization: 0 mismatches; `test_joule_realization_units_and_kappa` (R, κ changed: G unchanged) |
| I-8 | On one shared resistor, event pulses are not additive: the cross term is 2√(AiAj)·ρ (20√7 = 52.915 kg only for equal aligned windows). Separate resistors or summed powers restore additivity. L²-orthogonal pulses are additive only at readouts outside the windows | E-2a..E-2e (revised) | p1 E-2b PARTIAL → p3 (5)(6) CONFIRMED; D-12 formula [H], D-13 [E] | E `test_event_cross_term_is_2sqrtAA_rho`; D `joule_ac_check.json` | [E][F]; ρ formula [H] | Φ | Not re-executed; this is the reason events stay external in the joule realization |
| I-9 | X1: A and E agree at every common point. Inside a finite pulse window E gives the left value at τ | E-2e | X1 PASS (p1); D-14 | D `joule_ac_check.json` X1 | [E] | Φ | Not re-executed |
| I-10 | Merged clock capacitors (any period) cannot reproduce P0. A known-schedule Px needs one period-20 clock with 3 comparators | A-9, A-11 | p1 A-9, A-11 CONFIRMED; D-11 | D `states_check.json` | [E] | Φ | Not re-executed |
| I-11 | A single accumulator suffices iff the schedule is external; the table grows with the horizon | (D) | D-19 [E] | D `states_check.json` | [E] | Φ | Not re-executed |
| I-12 | True fixed-step integration misses event instants by a full 20/55 kg charge | E-5f | p3 (8) CONFIRMED; D-18 | E `benchmark.json`; D `benchmark.json` | [F] | Φ | Not re-executed |
| I-13 | Zero-mean AC charge is bounded and cannot count. A clock with its threshold below the swing gives 3 / 3 / 30 counts. A full-wave clock is exact iff c/h ∈ ℤ, or c/h ∈ ½+ℤ with φ ∈ {0, π/2} | A-15, A-16, A-17 | p3 (2)(3): A right; D-15, D-16 corrected | D `p3_recheck.json` | [F]; derivations [H] | Φ (AC) | Not composed (outside the composed domain) |
| I-14 | E's AC energy formula: exact on the lattice, sup error r(1+\|sin2φ\|)/(2ω). EF must be converted before integrating | E-3a..c, E-4 | p1 E-3a/b/c, E-4 CONFIRMED; D-17 | D `joule_ac_check.json` | [E][F]; E-3c derivation [H] | Φ (AC/EF) | Not composed |
| I-15 | The six C(T) kernel kinds (constant, atom θ_ε, year cell, gated cell, density, B2-01 gain) are exact 𝒢 netlists in float agreement with refcalc | H-B1 (six kinds) | p2 H-B1 CONFIRMED for six kinds, PARTIAL overall; D-20 | B `code/grammar.py`, `results/kernel_comparison.json`; D `p2_check_b.json` | [F] | Ψ | `psi.json`: EV2/EV9 unit values ≤2.6e-13 |
| I-16 | The late-reset S/H automaton reproduces B1-02/03/04 from raw inputs. Without the late reset it fails inside 𝒟′ | H-B3 (S/H part) | p2 CONFIRMED; D-22 | B `grammar.py` RefrigerantCircuit; D `p2_check_b.json` | [F] | Ψ | `psi.json` (EV2, EV9), `refrigerant_unexpected = []`; mutation M4 detected (8.9e-4 on SUM-03) |
| I-17 | C(T) is one weighted summing node over the 22 COMP rows of units70.json (β = ι_B2 on (B6, B2-01)) | C-1 = H-C1 | p2 C-1 CONFIRMED independently (X4); D-25 | C `results/hc1.json`; D `p2_check_c.json` | [F] | Ψ | `psi.json`: EV2/EV9/EV9-noB2, SUM-03 ≤5.5e-14, stages ≤2.6e-13; mutation M3 detected |
| I-18 | Summing the 21 DIRECT units as independent sources is wrong by exactly B2-01 | C-1n | **NOT_RUN by D** | C `results/hc1.json` | [F] | Ψ | **Executed here**: wrong by 0.056–1.6 %, = B2-01 to ≤3.3e-13 (EV2, EV9) |
| I-19 | Exact ranks: total 1, stage 6/6/7, DIRECT 7/8/9. **Rank ≠ state** | C-3, C-3x | p2 C-3 CONFIRMED exactly; D-26 | D `p2_check_c.json` | [E] | Ψ | Not re-executed |
| I-20 | Annual tables lose event timing (replay counterexample) | C-2r | p2 CONFIRMED; D-27 | D `p2_check_c.json` | [F] | Ψ | Not re-executed |
| I-21 | X2: P0 in the orig convention equals B's θ_ε netlist | A-3/H-B1 | X2 PASS both sides; D-28 | D `p2_gates.json` | [E]/[F] | Φ↔Ψ | `x2_link.json`: Φ hybrid vs B netlist, max rel 0.0 at 17 T |
| I-22 | X5: C − M([0,T]) = Z(T) ≠ 0; dC/dT = ρ + Z′ ≠ ρ; Z′ < 0 | (gate) | X5 PASS (EV6, 5 T); D-29, D-32 | D `p2_gates.json` | [E] | Φ↔Ψ (Ψ only) | `x5.json`: EV9, 5 T, exact; the composed C fits the identity to ≤3.4e-15 |
| I-23 | H-B2: lumped LTI RC with analytic sources cannot equal a kinked or jumping kernel. Switched or ideal-diode passive networks can, so the class labels are relative to 𝒢 | H-B2 (rescoped) | p2 CONFIRMED-as-textbook; D-24 [L]/[H] (not reviewed by B) | B `claims.md` (self-reported rescope) | [L] | Ψ | Not re-executed |
| I-24 | Refrigerant: the automaton and the merged knot form are the same order of stored numbers (1,025 or 1,063 vs 1,072); random access is about 100× faster with knots (time–memory trade-off) | H-B4 (restated, self-reported) | p2 "less state" REFUTED as a metric artefact; D-23 | D `p2_hb4.json`; B `results/hb4_counts.json` | [F] | Ψ | `benchmark.json` (canon KF vs composed sweep) |
| I-25 | No circuit path is faster than the direct Σ/knot form | A-18, E-5, H-B4 | D-18 | D `benchmark.json` | [F] | Φ, Ψ | `benchmark.json` (this run) |

## Not integrated (reason)
| item | reason |
|---|---|
| D-9 (≥2 continuous states, online reset), D-10 minimality, D-16 closed form, D-24, D-12 ρ formula, A-3/A-6/A-10/A-16 general statements, E Walsh cost, E-3c | [H]; no reviewer other than the author. Kept [H] |
| H-B1 for K26/K28/K30/K32/K33 | NOT_RUN (route B). Not needed for C(T)=SUM-03; needed for other outputs |
| C MAPPING constructs, classes and 4-tuples per unit | [H] design rules; no per-unit circuit was simulated in C. Our Ψ run simulates **B's** constructs per unit, not C's MAPPING rows |
| C-2 signature detector, C-4, C-6 | NOT_RUN by D; route-only [F] |
| Single shared resistor with Walsh-orthogonal event pulses | Not implemented as a circuit (E, D NOT_RUN); exact only outside windows |
| H-B3 RC-a/RC-b continuous-decay numbers | NOT_RUN by D |
| SageMath/MATLAB seven-engine | NOT_RUN (no workflow dispatched) |
