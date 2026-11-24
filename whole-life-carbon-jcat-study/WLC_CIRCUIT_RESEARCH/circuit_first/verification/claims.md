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

---

# V2 claims (snapshot 80ec2de, stage B)

| # | claim | tag | evidence |
|---|---|---|---|
| V2-1 | On 57 building runs and 901 (scenario, T) points (evaluation E4, E5, E7, E8, E9; 31 tstudy edge scenarios; 7 ι subsets; 17 adversarial T from 0.3 to 130), the circuit reproduces the frozen refcalc. C(T), all 14 stages, Z, M and the B4/B5 event counts agree within 1e-9 (max C 5.0e-14, max stage 2.4e-13 in B3). | [E] | `results/v2_oracle_*.json` |
| V2-2 | A valid-domain scenario with refrigerant recovery rate η = 1 crashes the building adapter (ZeroDivisionError). | [E] (counterexample) | `v2_oracle_edges.json`, `tests/test_v2.py` |
| V2-3 | The stage-B small-building dump satisfies KCL, element laws, impulse KCL, charge balance and continuity exactly. The crossbars of S and E1 solved independently reproduce every core tap exactly. A 353-element E1 core sub-network re-simulated by the verifier's simulator is state-identical to hybrid.py (accumulators on and off). | [E] | `v2_residuals.json`, `v2_crossbar.json`, `v2_subnet.json` |
| V2-4 | Crossbar → taps → core is a one-way substitution: no shared node, and taps are grounded ideal sources. For ideal op-amp outputs it is exact; it is not valid for finite output impedance. | [E] + textbook | `v2_crossbar.json` |
| V2-5 | hybrid.py's boundary-node and accumulator-sink strategies are exact consequences of the element laws under the structural conditions the engine checks. | proof sketch + [E] | VERDICTS V2; `v2_subnet.json`, `v2_hybrid_vs_sim.json` |
| V2-6 | No arithmetic, comparison or conversion is applied to raw scenario numbers outside the counting type (7 633 fields, S; E1 similar). Element values are primitive inputs × building-independent constants or circuit DC solutions. | [E] | `v2_audit.json` |
| V2-7 | The amplitude crossbar transcribes refcalc's per-row unit formulas and look-up/skip logic: one op-amp stage per data factor, 26 % pure inverters, ≈12.8 op-amps per row on S. The time and aggregation layers are a genuine re-organization: shared clocks per distinct period, packets, year cells, KCL buses. | [E] (counts) + judgement | VERDICTS V2 |
| V2-8 | About 19 % of the 1 018 core capacitors on S carry information needed for future outputs; the rest hold values that can be reconstructed. One clock per distinct period being necessary remains [H]. | [E] counts; lower bound [H] | VERDICTS V2 |
| V2-9 | V1-D1…D7 are fixed: comparator falling crossing in both engines (including adversarial probes), signed inputs, per-stage repair, convention-independent netlist, declaration of the dilation, narrow W_in, and tests (stage-A mutation score 17/19, 2 equivalent). | [E] | `v2_d1_probe.json`, `v2_fresh_cases_on_B2.json`, `v2_stageA_*` |
| V2-10 | Stage-B mutations: builder unit suite 8/11, verifier oracle harness 10/11 (1 equivalent). | [E] | `v2_mutations_summary.json` |

Scope: fictional synthetic scenarios only, inside `valid_domain` and outside the bands. This says nothing about real buildings or J-CAT. No novelty or speed claim.

---

# V3 claims (snapshot 96df403, stage C)

| # | claim | tag | evidence |
|---|---|---|---|
| V3-1 | With crossbar v2 the circuit reproduces refcalc on 917 fresh points across 57 runs: evaluation E4/E5/E7/E8/E9, all 31 edge scenarios, 7 ι subsets, 17 adversarial T. Every stage, C, Z and M is within 1e-9 (C 5.0e-14), event counts are equal, and there are no crashes. | [E] | `v3_oracle_*.json` |
| V3-2 | Endpoint values of every complement site (ρ, r, w, η at 0 and 1 / 0.999999) match refcalc. Exact duplicate refrigerant change years are rejected although refcalc and valid_domain accept them. | [E] | `v3_probes.json` |
| V3-3 | The reduced crossbars of S and E1, solved independently, have zero KCL residual and taps identical to the V2-verified stage-B taps. Every independent source is ±(one primitive)×V0 or ±V0. | [E] | `v3_crossbar.json` |
| V3-4 | No arithmetic on raw inputs. GREY is unchanged (predicates only). No multiplication moved into the adapter. | [E] | `v3_audit.json` |
| V3-5 | 66 op-amp outputs on S duplicate another output's voltage, because sharing is by identity, not by value key (identical composite recipes). | [E] | `v3_crossbar.py` analysis |
| V3-6 | The builder's "L1 lower bound" is the expression count of its own fixed-order, identity-shared graph. A W1-legal factor-grouped and value-shared realization would need about 1 332 expressions on S (< 1 462). | count [E]; realization unbuilt [H] | VERDICTS V3 §2(d) |
| V3-7 | The merged crossbar + core single netlist (truncated S, no OP block) equals the split run. | [E] | `v3_merged_rerun.json` |
| V3-8 | Across 8 buildings the crossbar signature is identical. All 19 varying core patterns are input-kind variants. No strict fixed template exists for the full building. | [E] | `v3_template.json` |
| V3-9 | Final mutation scores: builder 12/12 non-equivalent, verifier 11/11 non-equivalent (on the mutants my data can expose). | [E] | `v3_mutations_summary.json` |
| V3-10 | L1 conclusion: [P]-candidate, still without a second review. | [H] → [P]-candidate | VERDICTS V1/V3 |

Scope: fictional synthetic data only. No claim about real buildings, J-CAT, novelty or speed.
