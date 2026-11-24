# Claims — verification pass V1 (snapshot 4c5f375, stage A)

Tags: [P] proven in a declared domain (needs an independent review first), [E] exact sample checks, [F] numerical tests,
[H] hypothesis. Nothing below is promoted to [P]; the verifier's own proof sketches are marked "[P]-candidate".

| # | claim | tag | evidence |
|---|---|---|---|
| V1-1 | All dumped stage-A solutions satisfy KCL, element laws (R, C, V, I, switch, op-amp, L, diode), impulse-charge KCL, capacitor charge balance at every switching instant and inter-instant continuity exactly (exact dumps) / ≤ 2.8e-17 (float dumps). | [E] | `results/residuals_and_resim.json` |
| V1-2 | The dumped netlists alone (with the documented event semantics) determine the behaviour: an independent simulator reproduces every readout state of the pilot (right, original) and CF3-full dumps and of 3 fresh netlists. | [E] | `residuals_and_resim.json`, `vsim_fresh.json` |
| V1-3 | Pilot from primitive inputs: right 160/255/315/410, left/original 140/200/295/355; all 07 points in 3 conventions equal the verifier's ledger, all stages. | [E] | `fresh_cases.json` (pilot_*) |
| V1-4 | Single-rail pilot: data-path Joule heat = V₀·Q exactly (verifier meters); fails with voltage-coded amplitudes / negative packets (CF3 full: 377.77 vs 340.83 at T = 12). | [E] | `energy_check.json` |
| V1-5 | CF3 catalogue (incommensurate-like periods 7/3 and 11/5, period 1/1000, quadruple coincidences under 4 input orders, explicit early replacement restart/keep, degradation and efficiency change incl. ε ≠ 0 under the dilated convention, repair-year exclusion incl. integer-time events and ε-band T, renovation at non-coincident times under both policies, explicit-only items) equals the verifier's ledger on 642 points (CF3 cases; 55 further pilot points under V1-3). | [E] | `fresh_cases.json` |
| V1-6 | Under the original convention the circuit dilates event times by 1/(1−ε); time-dependent quantities then differ from the undilated semantics by ≤ 3.9e-10 relative (cases run). | [E] | `fresh_cases.json` (`rel_dev_from_undilated`) |
| V1-7 | Engine defect: a comparator input crossing 0 downwards continuously does not switch the output at the crossing (gated integrator: 3 instead of 1). | [E] (counterexample) | `bench_resolve.json`, `tests/test_v1.py` |
| V1-8 | Adapter silently drops negative amounts/rates (C(10) 160 vs 135); multi-stage repair groups are booked to the first row's stage. | [E] (counterexamples) | `fresh_cases.json`, `tests/test_v1.py` |
| V1-9 | Netlist topology depends on the convention (53 vs 55 elements) and on equality of periods (45 elements); the builder's schema signature is declared metadata and does not detect this. | [E] | `audit_static.json` |
| V1-10 | Adapter arithmetic on data is W1 only (8 pilot / 16 full); 0 operations on raw inputs; h = 0. W_in by narrower counting: 22 (pilot), 47 (full) vs builder 49/114. | [E] | `audit_static.json` |
| V1-11 | Architecture §5.4 early-comparator rule misassigns the year of events n ≥ 2 (lag cε(2−ε)(n−1)/(1−ε)); the builder's shared comparator with ρ = ε(2−ε)/(1−ε) reproduces ⌈τ(1−ε)⌉ exactly while τε(2−ε)/(1−ε) < 1. | algebra [P]-candidate (identity checked symbolically); samples [E] 3 826 events | `math_checks.json` |
| V1-12 | L1 conclusion: no node voltage / branch or source current of a network of positive conductances and independent sources equals c·G₁·G₂ identically. The homogeneity argument of the architecture is insufficient (G₁G₂/G₀ is degree-1 homogeneous). | conclusion [P]-candidate (multi-affinity proof sketch in VERDICTS) + [E] 0/3 166 in random search; argument gap [E] | `math_checks.json` |
| V1-13 | L3 as stated holds; "exact integration needs an active element" is false in general (ideal current source into grounded C is exact). | textbook / [E] | `math_checks.json` |
| V1-14 | S3 (a), (b), (d), (e) and §3(ii) hold as stated (textbook / proof sketch); S3 (c) holds for S3, the general incommensurate-period lower bound stays [H]. | textbook, [H] for the general bound | VERDICTS |
| V1-15 | Builder's 34 tests catch 15 of 20 verifier mutations; 2 equivalent, 3 missed (ρ = 2ε narrow, repair-stage source, renovation not renewing). | [E] | `mutations_v1*.json`, `mutations_vs_verifier_suite.json` |
| V1-16 | Pilot circuit simulation is ≈1.3e4× slower than the ledger (T = 40) and needs one simulated instant per year. No speed claim. | [F] (single machine) | `benchmark_pilot.json` |

Scope: fictional stage-A scenarios only; agreement says nothing about real-building accuracy or about the 70-unit model
(CF4 NOT_RUN). No novelty claim.
