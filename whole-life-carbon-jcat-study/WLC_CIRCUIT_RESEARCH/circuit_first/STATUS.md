# circuit_first — STATUS (stage A + V1 fixes + stage B S3a–S3e)

Date 2026-11-24. Branch `claude/wlc-equivalent-circuit-20261124`. Stage A was committed as `4c5f375`; the V1
verification was committed as `6e93fc8`. Model actually run: self-reported **claude-opus-5-5**. Effort is not
observable from inside the session (the agent definition says medium). The builder did no git operations.
Fictional data only. The frozen oracle (refcalc / synth / tstudy) is imported ONLY in `tests/compare_refcalc.py`,
`tests/compare_stageB_e.py` and `tests/test_stageB.py`. `tstudy.baseline.assert_frozen()` passes before every
comparison (trees refcalc 8976efe…, synth 55caf5c…, common ad3d0b7…).

## Commands
```
cd whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/circuit_first
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -p 'test_*.py'            # 47 tests, ~45 s
PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 python3 -B tests/compare_refcalc.py S3a|S3b|S3c|S3d
PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 python3 -B tests/compare_stageB_e.py full       # S3e
PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 python3 -B tests/compare_stageB_e.py mutations
```
Unit suite: **47 OK** (`results/test_log.txt`). No `__pycache__` anywhere.

## V1 fixes (verifier findings on snapshot 4c5f375)
| item | status | evidence |
|---|---|---|
| V1-D1 comparator falling through 0 not switched at the crossing | **FIXED** (both `sim.py` and the new `hybrid.py`). Reproduced first: charge 3 vs 1 in both simulators | post-phase rule (DESIGN_DEVIATIONS D11); `test_v1_fixes::test_D1_gated_integrator_both_directions` (falling 1, rising 2, events at 0↑/1↓); all stage-B results re-produced after the fix |
| V1-D2 signed inputs silently dropped | **FIXED** | stage A: negative amounts → negative-polarity packets, negative rates → −V0 rail; negative repair base/rate and degradation slope → ValueError; building: negative bank/grid values → ValueError, refcalc skip rules kept (they are specification). `test_D2_signed_inputs` (C = 100−15+3T−5n exactly, 2 conventions) |
| V1-D3 repair rows booked to the first row's stage | **FIXED** | one year cell per (group, stage); `test_D3_mixed_stage_repair_group` B3 = 10, B3eq = 20 (right and original) |
| V1-D4 divider only when ρ ≠ 0; signature from metadata; N_max not run | **FIXED** for the stage-A family; **NOT_RUN** for the full building | VCVS divider always present (53 elements in all three conventions); `model.netlist_signature` derived from the netlist graph (equal for all conventions and for merged equal periods); N_max identical-netlist test `tests/test_nmax.py` (4 variants × 2 conventions, one topology, results equal). Full-building N_max not run: D19 |
| V1-D5 ε dilation undeclared | **FIXED (declared, decided by the oracle)** | D16: a counting rule in the source; the full building is insensitive to the firing time (≤ 6e-14 vs refcalc on all T); stage-A degradation and efficiency are declared "dilated" |
| V1-D6 W_in too broad; control not reported | **FIXED** | narrow W_in (data elements + virtual-ground additions + comparators + diodes + data-path switches); the broad count is also reported; control census (priority classes, sequencers, phase steps, gates, W2/W3/W4) is reported next to h |
| V1-D7 weak tests, missed mutants | **FIXED** | ramp-zero assertion, full-scenario value vs an independent ledger (right convention), L1 bench renamed `test_L1_homogeneity_only`, M17/M18/M04b kill tests; mutation suite now 10/10 (stage A) |

## Stage B results vs the frozen refcalc (tolerance relative 1e-9, original convention)
Buildings: benchmark **S** (SYN-RC-office-S-T60-seed101), benchmark **M** (SYN-RC-office-M-T60-seed102),
evaluation set **E0** (SYN-S-office-S-T60, MAJOR_REFURBISHMENT cycle 82), **E1** (SYN-S-residential-S-T60,
non-top-up refrigerant), **E2** (SYN-S-school-S-T100, all TABLE profiles and TABLE grid). T = 1, 7.5, 20, 33.3, 42.5,
59.9, 60, 60.1, 75, 99.9 (10 per building). All are inside `valid_domain` and not in a band (K, sw(τ)]; no in-band
value was used.

| sub-stage | blocks | stages compared | max relative error | result |
|---|---|---|---|---|
| S3a constants | crossbar → initial packets, terminal readout | A1-A3, A4, A5, C1–C4, Z | 9.2e-16 | **PASS** |
| S3b operation | year banks/MDAC, electricity chain with diode, ρ split | B2, B6, B7 | 2.1e-15 | **PASS** |
| S3c events | groups, B4, B3 year cells, B5 | + B3, B4, B5; event counts | 5.9e-14; counts equal 50/50 | **PASS** |
| S3d refrigerant | B1 cells incl. terminal residual | B1, Z(B1-04) | 3.4e-15 | **PASS** |
| S3e all | everything, 5 buildings | 14 stages, C(T), Z(T), counts | C(T) 1.09e-14, Z 6.3e-16, counts equal | **PASS** |
| S3e ι subsets | no_B2, no_B2_B6, no_B1_C4, {A1-A3,B4,C3} on S and E0 | as above | ≤ 5.9e-14 | **PASS** |

**Coverage:** 1.0 of |C(T)| for every building and every T (every stage inside 1e-9, all produced by P0/P1/H blocks).
B5 events occur in E0 for T > 82. Integer-year equipment and refrigerant events occur at integer T. This confirms
the readout → tick → fire ordering (coordinator decision 3).

**Mutations (stage B, `results/stageB_mutations.json`): 6/6 detected; the unmutated circuit passes in every case.**
init-before-leak (E2 B1), refrigerant as continuous decay (E2 B1), ρ leg always subtracted (S without B2, B6),
ι upstream of the B5 base (E0 without C4/A4, B5 at 99.9), diode after integration (S variant with generation above
demand, B6), terminal packet fed back into integrators (S, C3 at the 2nd readout). Stage A suite: 10/10.

## Hiddenness, counts and size (S3e, `results/stageB_S3e.json` → runs[].counts)
h = W_out/(W_in+W_out) with the narrow W_in. W_out consists only of GREY predicates: the running sums of composite
mass fractions and |Σ−1| ≤ 1e-6, the EPD date comparison, and the grid step order. No element value is grey.

| building | h (h_amp / h_time) | W_in amp / time | GREY amp / time | crossbar elements / op-amps | core elements / op-amps / C / comparators / switches / bits | N_c / N_x / N_r | run (dc / hybrid) |
|---|---|---|---|---|---|---|---|
| S | 0.045 (0.064 / 0) | 6547 / 2918 | 449 / 0 | 13 404 / 3 393 | 9 977 / 389 / 1 018 / 201 / 3 639 / 701 | 161 / 22 / 5 | 26 s (1.0 / 24.6) |
| M | 0.069 (0.078 / 0.0014) | 67285 / 9909 | 5664 / 14 | 134 335 / 33 798 | 48 311 / 2 140 / 5 530 / 1 232 / 16 886 / 4 051 | 869 / 234 / 40 | 94 s (8.4 / 83.0) |
| E0 | 0.058 (0.067 / 0) | 6725 / 1110 | 481 / 0 | 13 189 / 3 273 | 5 355 / 269 / 640 / 121 / 1 856 / 414 | 97 / 7 / 5 | 13 s |
| E1 | 0.060 (0.069 / 0) | 6735 / 1026 | 497 / 0 | 13 197 / 3 273 | 5 524 / 273 / 656 / 128 / 1 903 / 450 | 95 / 19 / 5 | 6 s |
| E2 (T=100) | 0.032 (0.055 / 0) | 6212 / 4918 | 362 / 0 | 13 624 / 3 549 | 15 074 / 558 / 1 498 / 298 / 5 708 / 1 005 | 251 / 34 / 5 | 19 s |

Control census (not counted in h; S / M): 6 priority classes; 1 018 / 5 686 sequencers with 4 258 / 23 921 phase
steps; 1 738 / 9 002 gates; W2 look-ups and equality groupings 8 476 / 86 975; W3 predicates 8 984 / 85 043; W4
enumerations 933 / 3 055. The broad W_in (stage-A style) is reported as `W_in_broad`. The h band
0.02 < h ≤ 0.25 is "PARTIAL" by architecture §6.

Scaling (measured): crossbar op-amps grow with rows (≈ 17 per material row). Core capacitors grow with groups and
devices: ≈ 6 per periodic group (clock + reset + packet + year cell + copy), plus a time base and 14 buses.
Comparators ≈ N_c + N_x + 2·N_r(periodic) + constants. Bits = 8-bit counter + latches. TABLE profiles add one
switched branch per table entry (130), which explains E2's larger core.

**Signature (netlist-derived):** crossbar signature identical for all 5 buildings. Core signature differs by 0–5
element patterns. The differences are input-kind variants (non-top-up refrigerant drain gate in M and E1; explicit
refrigerant change years in E2). The cell catalogue is shared, but the core netlist pattern is NOT identical across
buildings.

## Engine additions (generic, application-agnostic; reproducible from dumped netlists)
`engine/dc.py` is an exact sparse static solver (all tested crossbars fully peeled, dense block 0, KCL residual
exactly 0). `engine/hybrid.py` is an exact event-driven hybrid solver with boundary nodes, lazy per-component time
and accumulator sinks (D13). It matches `sim.py` exactly on all 18 stage-A cases, and with accumulators off its full
dump has zero KCL/law/impulse residuals (`results/stageB_small_building_full_solution.json`). Netlists and tap maps
for S and E1 are in `results/stageB_netlists_{S,E1}.json`, so the verifier can re-run crossbar → taps → core.

## Results files
Stage A: `bench_*`, `pilot_*`, `cf3_*`, `audit_*`. V1: `bench_gated_integrator.json`, `v1_D4_signatures.json`,
`v1_D6_hiddenness_pilot.json`, `nmax_same_netlist.json`. Stage B: `stageB_S3{a,b,c,d,e}.json` + `.log`,
`stageB_mutations.json`, `stageB_netlists_{S,E1}.json`, `stageB_small_building_full_solution.json`.

## NOT_RUN / limits
* N_max identical-netlist template for the FULL building (input-kind variants would all need enable switches; D19).
  It runs for the stage-A cell family.
* A merged single-netlist run of crossbar + core (substitution theorem only argued, D12).
* Grey composite predicates are not yet realised in the circuit. A summing junction plus a window comparator would
  move ~430 (S) / 5 500 (M) GREY operations into H control.
* In-band T ∈ (K, sw(τ)] agreement, AGG ratios (SUM-04/05, shares), decision/reference/breakdown units, X-04/X-07,
  SPICE/hardware, Math7 seven-engine runs.
* Duplicate event years inside one equipment/refrigerant list would merge into one set firing (none in the tested
  data; no guard).
* Energy meters are not computed by `hybrid.py` (only `sim.py`); no Joule audit for buildings.
* No speed claim: refcalc evaluates S in 0.02 s; the circuit takes 26 s.
