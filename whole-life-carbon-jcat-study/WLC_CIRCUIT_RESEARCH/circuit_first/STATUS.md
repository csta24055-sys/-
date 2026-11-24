# circuit_first — STATUS (stages A + B + C)

Date 2026-11-24. Branch `claude/wlc-equivalent-circuit-20261124`.
* Commits: stage A `4c5f375`, V1 `6e93fc8`, stage B `80ec2de`, V2 `94c55da`. This pass (stage C) is uncommitted;
  the builder did no git operations.
* Model actually run: self-reported **claude-opus-5-5**. Effort is not observable from inside the session.
* Data: fictional only.
* Oracle (frozen refcalc / synth / tstudy): imported only in `tests/compare_*.py`, `tests/test_stageB.py` and
  `tests/test_v2_fixes.py`. `assert_frozen()` passes before each use.

## Commands
```
cd whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/circuit_first
PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 python3 -B -m unittest discover -s tests -p 'test_*.py'   # 54 tests: 53 OK + 1 skipped (slow), ~90 s
CF_SLOW=1 PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 python3 -B -m unittest tests/test_stageB.py           # + merged-netlist test (~7 min)
PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 python3 -B tests/compare_refcalc.py S3a|S3b|S3c|S3d
PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 python3 -B tests/compare_stageB_e.py full|mutations
PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 python3 -B tests/compare_crossbar.py                       # v1 vs v2 census
```
Log: `results/test_log.txt`. No `__pycache__`.

## V2 fixes (verifier findings on 80ec2de; each reproduced before the fix)
| item | status | evidence |
|---|---|---|
| V2-D1 η = 1 → 0 Ω, ZeroDivisionError | **FIXED** | Reproduced on EDGE-recovery_extremes. The branch is omitted when 1−η = 0 (W3); every pot site was audited (D22). `test_v2_fixes::test_D1_recovery_rate_one` passes against refcalc. All 31 edge scenarios run, max 2.8e-14 (`results/stageC_edge_scenarios.json`); life_near_divisor has no usable T (all knife edges) |
| V2-D2 STEPWISE step index bit-decoded in Python | **FIXED** | Each step is now a reference source k·V0 (W1) and a comparator on the undilated ramp `tb.u`, switching in the tick batch (D23). `test_D2_stepwise_grid_and_D4_mdac_msb` matches refcalc to T = 129.5 |
| V2-D3 dangling `hs3` | **FIXED** | the input exists only under the `init_before_leak` mutation; `test_D3_no_dangling_mutation_input` |
| V2-D4 three surviving mutants | **FIXED** | hooks `b5_without_A4`, `mdac_msb_plus1`, `epd_strict` are killed by `test_D4_b5_base_includes_A4` (E0, B5 at 99.9), `test_D2…mdac_msb` (T = 129.5) and `test_D4_epd_validity_inclusive` (assessment date = valid_until) |
| V2-D5 duplicate years | **FIXED** (refcalc semantics: two events) | equipment: one renewal packet per listed year; the B3 exclusion stays once per year; checked vs refcalc (`test_D5_duplicate_years`). Refrigerant duplicates raise ValueError (D24). The generator never produces duplicates |

## Stage-B comparisons re-run with crossbar v2 (relative 1e-9, original convention)
Buildings S, M, E0, E1, E2 (as in stage B); 10 T each (1 … 99.9); ι subsets on S and E0.

| sub-stage | max relative error | result |
|---|---|---|
| S3a | 9.2e-16 | PASS |
| S3b | 2.1e-15 | PASS |
| S3c | 5.9e-14; event counts equal | PASS |
| S3d | 3.4e-15 | PASS |
| S3e | C(T) 1.1e-14, Z 6.3e-16; coverage 1.0 in 50/50 rows | PASS |
| S3e ι subsets | ≤ 5.9e-14 | PASS |
| stage-B mutations | 6/6 detected | — |
| edge set | 30 runnable edge scenarios × up to 6 T each (incl. 129.5) ≤ 2.8e-14 | PASS |

## Amplitude-layer reduction (Part 2; D21, `results/stageC_crossbar.json`)
| building | op-amps v1 → v2 | elements v1 → v2 | op-amps per row v1 → v2 | L1 bound | gap |
|---|---|---|---|---|---|
| S | 3 393 → **1 593** | 13 404 → 8 148 | 13.0 → 6.1 | 1 462 | 131 (both polarities) |
| M | 33 798 → **14 468** | 134 335 → 77 150 | 13.0 → 5.5 | 13 740 | 728 |
| E0 | 3 273 → 1 453 | 13 189 → 7 849 | 12.6 → 5.6 | 1 342 | 111 |
| E1 | 3 273 → 1 456 | 13 197 → 7 854 | 12.6 → 5.6 | 1 337 | 119 |
| E2 | 3 549 → 1 748 | 13 624 → 8 353 | 13.7 → 6.7 | 1 612 | 136 |

* Pure inverters: 868 → 0 (S).
* Tap voltages are identical between v1 and v2. All comparisons above were re-run with v2.
* The netlist-derived crossbar signature is identical across all 5 buildings.
* L1 counting rule:
  - the factor order is fixed (rail, conversion, row factors);
  - sharing is by structural identity;
  - each distinct expression that must be a voltage needs one active output, and each sampled or multiplied sum
    needs one junction.
* Remaining gap: expressions needed in both polarities. Value-equality sharing was not used: the data has almost
  no repeated values.
* No reduction changed an observable. The failed attempt was the q/(1−w) root form for every DESIGN row. It gave
  1 661 instead of 1 605 op-amps, so it is used only per row when it is cheaper (final 1 593).

## Structure tests (Part 3)
* **(d) Merged single netlist: PASS (subset).**
  - What ran: crossbar + core as one netlist, tap sources removed and tap nodes joined to the op-amp outputs, on a
    truncated S (3 materials, 2 equipment rows, 1 refrigerant device), blocks AC, EV, REF.
  - Result: readouts identical to the split run (`results/stageC_merged_netlist.json`).
  - Excluded: the OP block, for solver cost only. Without tap sources the year-bank branches hang off non-fixed
    op-amp outputs, and the whole static crossbar becomes one component re-solved at every event.
  - The same cost limits the merged run to tiny buildings (≈7 min).
* **(e) Fixed full-building template: NOT_RUN** for the building.
  - It exists and passes for the stage-A cell family (initial packets, constant flows, periodic clocks, renewal
    packets, stage buses; `tests/test_nmax.py`).
  - Blockers for the building: input-kind variants are different cells (TABLE / LINEAR / CONSTANT banks, grid kind,
    explicit vs periodic groups and devices, top-up or not). The crossbar is per-row and would need slot chains with
    enable switches.
  - The core netlist signature differs between buildings by 3–4 element patterns.

## Counts (S3e, crossbar v2)
| building | h (amp / time) | crossbar elements / op-amps | core elements / op-amps / C / comparators / switches / bits | N_c / N_x / N_r | run (s) |
|---|---|---|---|---|---|
| S | 0.041 (0.055 / 0) | 8 148 / 1 593 | 10 028 / 390 / 1 031 / 201 / 3 663 / 701 | 161 / 22 / 5 | 13.4 |
| M | 0.061 (0.068 / 0.0014) | 77 150 / 14 468 | 48 949 / 2 141 / 5 686 / 1 247 / 17 196 / 4 051 | 869 / 234 / 40 | 76.8 |
| E0 | 0.051 | 7 849 / 1 453 | 5 370 / 270 / 644 / 121 / 1 862 / 414 | 97 / 7 / 5 | 12.6 |
| E1 | 0.053 | 7 854 / 1 456 | 5 559 / 274 / 665 / 128 / 1 919 / 450 | 95 / 19 / 5 | 4.7 |
| E2 | 0.029 | 8 353 / 1 748 | 15 185 / 559 / 1 526 / 298 / 5 762 / 1 005 | 251 / 34 / 5 | 15.6 |

Control census and configuration counts not covered by h are in adapter.md (stage C table) and
`results/stageB_S3e.json`. h stays in the PARTIAL band (0.02 < h ≤ 0.25); all of it is GREY predicates.

## NOT_RUN / limits
* Full-building N_max template.
* The OP block in the merged run.
* In-circuit realisation of the GREY predicates.
* In-band T; AGG ratios and decision/reference/breakdown units.
* SPICE / hardware; Math7.
* Building energy meters.
* Refrigerant duplicate change years: rejected, not supported.
* No speed claim.
