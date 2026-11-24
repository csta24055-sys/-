# Coverage (G4)

Legend:
- ✔ executed and passing in that route
- ✔D independently re-computed by D
- ✔I re-executed by the integration against a non-composed oracle
- ○ route claim only (D NOT_RUN)
- — not in scope
- ✗ NOT covered

All data are fictional.

## Φ (physical time) observations
| observation / identity | A | E | D | Integration |
|---|---|---|---|---|
| P0 at 11 contract points, 3 conventions | ✔ | ✔ | ✔D (490+83 rows, 1e5 random) | ✔I 2,118 pts, both realizations |
| Exact one-sided limits / jumps at τ | ✔ | ✔ | ✔D | ✔I (τ ± 1e-12, ± 1e-15) |
| Knife points 10.000000005 / 10.00000002 (exact) | ✔ | ✔ | ✔D | ✔I |
| Float knife edge 10.00000001 | recorded, undefined | — | ✔D (float counts, exact excludes) | ✗ not asserted (undefined zone) |
| Closed band [nc, nc/(1−ε)] | ✔ (after fix) | — | ✔D | ✔I (endpoint test) |
| P1 substitute / additional at 20 | ✔ | ✔ (net −5 encoding) | ✔D (ledger) | ✔I (supersession encoding, 3 conv.) |
| P1′ renovation at 15 (restart) | ✔ (A.R1 agrees, D run) | ✗ (not expressible in the net −5 encoding) | ✔D (D-7) | ✔I |
| Set-rule order independence | ✔ | — | ✔D (200 shuffles) | ✔I (clock order × policy) |
| P2 rate latch | ✔ | ✔ (gain switch) | ✔D | ✔I |
| Px (early AC reset at 7) | ✔ | — | ✔D | ✔I (right/left) |
| P2/Px under orig | rejected (undefined) | — | NOT_RUN (undefined) | rejected (ValueError) |
| γ, C_cap invariance; E_cap ≠ carbon | ✔ | — | ✔D (algebraic only) | ✔I (executed, 3 pairs) |
| Joule: 60 J sanity, κ explicit, resistor stateless | — | ✔ | ✔D | ✔I (R, κ varied) |
| One-resistor event cross term 2√(AiAj)·ρ | — | ✔ | ✔D | — (reason the composed joule realization keeps events external) |
| L²-orthogonal (Walsh) single-resistor pulses | — | ✔ numerics; design cost [H] | ✔D numerics | ✗ not implemented as a circuit |
| Zero-mean AC, rectified clock, phase condition | ✔ | — | ✔D | ✗ not composed (float/transcendental) |
| AC Joule energy, lattice, bound; EF convert-then-integrate | — | ✔ | ✔D | ✗ not composed |
| Merged clocks fail; known-schedule Px single clock | ✔ | — | ✔D | — (counterexamples, not a model part) |
| Online reset ≥2 continuous states | samples ✔, necessity [H] | — | D-9 draft [H], D-10 realization [E] | ✗ minimality unreviewed |
| Fixed-step integration misses event charges | — | ✔ | ✔D | — |

## Ψ (horizon sweep) observations
| observation / identity | B | C | D | Integration |
|---|---|---|---|---|
| Six C(T) kernel kinds = 𝒢 netlists | ✔ S, M, EV3, EV11 | — | ✔D EV6, EV10 | ✔I EV2, EV9 (21 unit values each) |
| Year cells as one shared integrator | ✔ | — | — | ✔I EV9 |
| Late-reset refrigerant automaton | ✔ | — | ✔D | ✔I EV2, EV9 (mutation M4 detected) |
| Automaton matches inside the open band (K, sw(τ)) | ✔ 4 scenarios | — | ✔D 2 scenarios | ✗ no band points in the integration grid |
| Composition = one summing node over COMP | ✔ (SUM-03) | ✔ 105 cases | ✔D X4 exact composition | ✔I EV2, EV9, EV9-noB2 (+ stages) |
| Naive 21-source sum wrong by B2-01 (C-1n) | — | ○ | NOT_RUN | ✔I EV2, EV9 |
| Inventory 70 / 21 / 22 COMP | — | ✔ | ✔D | ✔I (22 rows, 21 units asserted) |
| Exact ranks; rank ≠ state | — | ✔ | ✔D exact | — |
| Annual-table replay counterexample | — | ✔ | ✔D | — |
| H-C2 block-type detector | — | ○ | NOT_RUN | ✗ |
| H-C4 non-DIRECT roles not sources | — | ○ | NOT_RUN | ✗ |
| C-6 t=0 vs t=T placement unobservable | — | ○ | NOT_RUN | ✗ |
| Per-unit circuit for DIRECT 21 | B constructs only | MAPPING [H], NOT_RUN | — | ✔I **B's constructs** for all 21 DIRECT units vs refcalc unit values; **C's MAPPING constructs and tuples ✗** |
| H-B2 LTI RC impossibility | ✔ illustration | — | ✔D textbook [L] | — |
| H-B4 refrigerant state vs merged knots | ✔ (restated, self-reported) | — | ✔D (refuted "less state") | ✔I timing only (`benchmark.json`) |
| K26, K28, K30, K32, K33 | ✗ NOT_RUN | — | ✗ | ✗ |
| Scenario L for kernels | ✗ | H-C1 only | ✗ | ✗ |
| SUM-05 (division by T), shares, `match`, inv | class d (not in 𝒢) | — | — | ✗ (outside the composed domain) |

## Cross gates
| gate | D | Integration |
|---|---|---|
| X1 A vs E | PASS | ✔I only that both realizations give identical exact values (outside pulse windows; no pulses used) |
| X2 A/Φ vs B θ_ε | PASS | ✔I through the composed Φ code, max rel 0.0 at 17 T |
| X3 B kinds ⊇ C DIRECT time forms | PASS (set level) | not re-run |
| X4 C vs refcalc | PASS (EV6, EV10, BM-S + subsets) | ✔I EV2, EV9, EV9-noB2 |
| X5 C − M = Z | PASS (EV6, 5 T) | ✔I EV9, 5 T |

## NOT covered by anyone (explicit)
- A physical/SPICE circuit for any part: every realization here is an exact event-driven hybrid model or a 𝒢 netlist interpreter.
- Any formal review of the [H] items (see `next_experiments.md` E1).
- Seven-engine (SageMath + MATLAB) checks of any WLC identity: NOT_RUN.
- Real buildings, J-CAT original formulas: out of scope (gate 5).
