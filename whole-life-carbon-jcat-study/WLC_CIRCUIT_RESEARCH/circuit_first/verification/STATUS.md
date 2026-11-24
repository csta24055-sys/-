# circuit_first/verification — STATUS (pass V1: stage A of the builder)

Date 2026-11-24. Branch `claude/wlc-equivalent-circuit-20261124` (HEAD `4c5f375` at the time of the pass; no git
operation by the verifier). Object: frozen snapshot of `4c5f375` extracted by the coordinator to
`/tmp/claude-0/-home-user--/d16c9837-8c7c-5bcc-8b70-730caf3a5491/scratchpad/cf_snapshot_A/whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/circuit_first/`
(read and imported read-only; tree unchanged, no `__pycache__`). Live builder files not read.
**Model actually run: self-reported `claude-opus-5-5` (Opus 5.5). Effort is not observable from inside the session**
(agent definition says high). Python 3.13.18; `math7-py` (same interpreter + SymPy/mpmath) for scripts that need them.
Fictional data only, no network, no oracle (`refcalc`) code executed (refcalc `base.py`/`units_b.py` were only read for
the time conventions: inside = τ < T(1−1e-9), year = ⌈τ(1−1e-9)⌉, per-row B3 exclusion, B5 does not restart cycles).

Verdicts: **CF1 PARTIAL, CF2 PASS, CF3 PARTIAL, CF5 (partial) PARTIAL** — details, defects and fixes in `VERDICTS.md`;
claims with evidence tags in `claims.md`.

## Commands (from `verification/code/`, all with `PYTHONDONTWRITEBYTECODE=1`, `-B`)
| command | output | runtime |
|---|---|---|
| builder suite in a copy: `cp -r <snapshot> …/scratchpad/v1/run_copy; cd run_copy/tests; python3 -B -m unittest discover -s . -p 'test_*.py'` | 34 OK; all 34 result JSONs byte-identical to the snapshot | 18.1 s |
| `math7-py -B run_residuals.py` | `results/residuals_and_resim.json` (own residual checker on 14 dumps; vsim re-simulation of 3 dumps) | 42 s |
| `python3 -B run_fresh.py` | `results/fresh_cases.json` (36 cases, 699 points, events, years) | 35 s |
| `math7-py -B bench_resolve.py` | `results/bench_resolve.json` (vsim + mpmath ODE re-solutions; comparator probe) | 3 s |
| `math7-py -B energy_check.py` | `results/energy_check.json` | 37 s |
| `math7-py -B vsim_fresh.py` | `results/vsim_fresh.json` (3 fresh netlists: vsim = ledger = engine) | 47 s |
| `math7-py -B math_checks.py` | `results/math_checks.json` (D1, L1 search, L3/S3 symbolic) | 47 s |
| `python3 -B audit_static.py` | `results/audit_static.json` (imports, scans, probe, recount, h, WL signatures, census) | ≈20 s |
| `python3 -B mutate.py` and `MUT_ONLY=M17…,M18… MUT_OUT=mutations_v1_extra.json python3 -B mutate.py` | `results/mutations_v1.json`, `mutations_v1_extra.json` | ≈6 min |
| `python3 -B mut_vs_fresh.py M04b…,M05…,M06…,M17…,M18…` | `results/mutations_vs_verifier_suite.json` | ≈3 min |
| inline benchmark (see VERDICTS) | `results/benchmark_pilot.json` | 5 s |
| `cd ../tests; math7-py -B -m unittest -v test_v1` | 7 tests OK (4 assert reproducible defects) | 7 s |

Mutant copies and run copies live under `…/scratchpad/v1/` and are deleted after each mutant run.

## Counts
* Residual checks: 14 dumps, 1 036 records, 31 283 node-KCL checks, 350 jumps; all exact residuals 0, float max 2.8e-17.
* Independent simulator (`code/vsim.py`, written from element laws + documented semantics): 3 dumped + 3 fresh netlists,
  0 readout-state mismatches; comparator-event differences only in the timing of `tb.P` falling edges (engine defect V1-D1).
* Ledger comparisons: 36 cases / 699 points / 3 conventions; 35 PASS, 1 FAIL (signed inputs, V1-D2).
* D1: 3 826 events, 0 errors for the builder's rule, 390 for the architecture's rule.
* L1 search: 400 random symbolic networks, 3 166 responses, 0 exact products.
* Mutations: 20 applied; builder suite caught 15 (2 equivalent, 3 real misses).

## Code SHA-256 (prefix) of the verifier's files
`code/vsim.py` dd5562be6d6e, `nlcheck.py` 5e07c612fe76, `ledger.py` 033803f370f4, `run_fresh.py` f3c6fd5b0176,
`bench_resolve.py` 0559bb108187, `energy_check.py` 338c7bcf5a6e, `vsim_fresh.py` f56b0d6189b9,
`math_checks.py` e98b2262838a, `audit_static.py` 71e01dc7331c, `mutate.py` aa678201a421,
`mut_vs_fresh.py` 18488efe6fb3, `common.py` f32985bc169f, `run_residuals.py` 2873f24b00e0,
`tests/test_v1.py` 2dedd71ecf42 (final state of this pass).

## Independence notes
* Not used as oracle: builder solver (`engine/sim.py`, `mna.py`, `linalg.py`), `engine/audit.py`, builder test ledgers.
  The builder's `model.simulate` / `adapter.build` are used only as the system under test; the snapshot `engine` is
  imported only to reproduce the comparator defect and to build the probe netlist.
* `vsim` shares the *documented* event semantics (priority classes, set processing, lock-step sequencer phases) with the
  engine, because these semantics are part of the circuit's definition; it differs in formulation and code. It switches
  a falling comparator at the true crossing (physically exact), unlike the engine.
* The ledger encodes the meanings in `adapter.md` §1, contract 07 and refcalc's time rules; where the builder's
  synthetic semantics have no refcalc counterpart (substituting renovation renews items, keep/restart explicit policy,
  degradation, efficiency switch) the ledger follows `adapter.md` and this is stated in `ledger.py`.

## NOT_RUN
CF4 (refcalc comparison, synthetic buildings), stage-B cells, N_max same-netlist test, Math7 seven-engine run,
SPICE/hardware, AGG ratios, vsim for inductor/diode netlists (ODE re-solution only), proof review of the verifier's own
L1 sketch by a second reviewer.

---

# V2 pass: stage B and V1 fixes (snapshot `80ec2de`)

Date 2026-11-24.

**Object:** the frozen snapshot at `/tmp/claude-0/-home-user--/d16c9837-8c7c-5bcc-8b70-730caf3a5491/scratchpad/cf_snapshot_B2/whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/circuit_first/`. It was read and run only. No file in it changed after my runs started, and no `__pycache__` exists anywhere.

**Oracle:** frozen refcalc / synth / common (`8976efe…` / `55caf5c…` / `ad3d0b7…`). `tstudy.baseline.assert_frozen()` passed in every oracle process.

**Model actually run:** self-reported `claude-opus-5-5`. Effort is not observable.

**No git operations.**

**Verdicts:**

| gate | verdict |
|---|---|
| CF1 | PASS |
| CF2 | PASS |
| CF3 | PASS |
| CF4 | PARTIAL (901 / 901 points within 1e-9; one valid-domain crash, V2-D1) |
| CF5 | PARTIAL |
| CF6 | present |

Overall recommendation: **PARTIAL** (see VERDICTS.md V2).

## Commands
All run from `verification/code`, with:
```
CF_SNAPSHOT=<B2 snapshot path above>
PYTHONDONTWRITEBYTECODE=1
GIT_OPTIONAL_LOCKS=0
```

| command | output | runtime |
|---|---|---|
| `python3 -B v2_oracle.py evalS E4,E5,E7,E8` | `results/v2_oracle_evalS.json` | 16–21 s per building |
| `python3 -B v2_oracle.py evalM E9` | `results/v2_oracle_evalM.json` | 97 s (refcalc 9 s for 16 T) |
| `python3 -B v2_oracle.py edges <31 edge scenarios>` | `results/v2_oracle_edges.json` | 2–7 s each |
| `python3 -B v2_oracle.py iota_<name> E5,EDGE:refurbishment_divides_period,EDGE:generation_exceeds_consumption <name>` (7 subsets) | `results/v2_oracle_iota_*.json` | — |
| `math7-py -B v2_d1_probe.py` | `results/v2_d1_probe.json` | — |
| `math7-py -B v2_crossbar.py` | `results/v2_crossbar.json` | 0.6 s |
| `math7-py -B v2_subnet.py` | `results/v2_subnet.json` (353-element E1 core sub-network: vsim vs hybrid) | vsim 16.7 s, hybrid 1.4 s |
| `math7-py -B v2_hybrid_vs_sim.py` | `results/v2_hybrid_vs_sim.json` | — |
| inline `nlcheck.check` on the B2 dumps | `results/v2_residuals.json` | — |
| `python3 -B v2_audit.py` | `results/v2_audit.json` (imports, scan, 7 633-field raw probe, counts) | — |
| `python3 -B v2_mutate.py all` with `V2_ONLY=builder` and with `MUT_TAG=part0..2` | `results/v2_mutations_*.json`, `v2_mutations_summary.json` | ≈4 min per mutant for the verifier judge |
| `MUT_BASELINE=1 MUT_ONLY=… MUT_OUT=v2_stageA_mutations_partN.json python3 -B mutate.py <scratch>` | stage-A mutations on B2 | — |
| `CF_RESULTS=<scratch> python3 -B run_fresh.py` | `results/v2_fresh_cases_on_B2.json` (36/36) | 33 s |
| `cd ../tests; math7-py -B -m unittest -v test_v2` | 5 OK (1 asserts the V2-D1 crash) | 21 s |
| `cd ../tests; math7-py -B -m unittest test_v1` | V1 tests; with CF_SNAPSHOT=B2 the 4 DEFECT tests now FAIL as expected (defects fixed) | — |

## Counts
- **Oracle:** 57 building runs and 901 (scenario, T) points; every stage, C, Z and M within 1e-9. Maximum relative errors: C 5.0e-14, B3 2.4e-13. B4/B5 event counts are equal at all 901 points. 52 T were excluded by `valid_domain` (all of them knife edges at 129.999999). There were 0 in-band T and 1 crash.
- **Residuals on the stage-B small-building dump:** 89 096 node-KCL checks over 86 instants and 271 jumps, all exactly 0. The only chain mismatches are the 11 init jumps, which happen before the first recorded state.
- **Crossbars S / E1:** 13 404 / 13 197 elements solved independently, KCL residual 0, 354 / 232 taps exact, no node shared with the core.
- **Mutations:**
  - stage B: builder suite 8/11, verifier harness 10/11 (B10 equivalent);
  - stage A on B2: 17/19 caught (2 equivalent).
  - The builder baseline passes 47/47 in the copy after one harness path fix: `STUDY` in `tests/test_stageB.py`, because the copy lives outside the git repository.

## Changes to V1 verifier code (backward compatible; the V1 tests still pass on snapshot 4c5f375)
- `vsim.py`: sparse RREF (instead of the dense one); VCVS/VCCS support; readouts that carry a control pulse (`rd`).
- `nlcheck.py`: inter-instant continuity check that is jump-aware, for dumps that record arrivals only (hybrid).
- `mutate.py`: baseline run, B2 harness path fix, re-anchored M16b/M18b.

## Code SHA-256 (prefix)
| file | hash |
|---|---|
| `v2_audit.py` | 1ef97337dbf4 |
| `v2_crossbar.py` | 1ec45fa25a35 |
| `v2_d1_probe.py` | 26d83fb0b9ee |
| `v2_hybrid_vs_sim.py` | 148557b4c0c0 |
| `v2_mutate.py` | f1829a415e37 |
| `v2_oracle.py` | 22f67f622c5d |
| `v2_subnet.py` | 48bc89735b37 |
| `vsim.py` | 6230f6513190 |
| `nlcheck.py` | 19bdd04ecfa0 |
| `mutate.py` | aa69fc28a867 |
| `tests/test_v2.py` | 1b96c07374ee |

## NOT_RUN (V2)
- In-band T ∈ (K, sw(τ)].
- Benchmark L.
- Evaluation scenarios E3 and E6 (M size; E9 was run instead).
- A merged crossbar + core single-netlist run (substitution checked instead).
- Full-building N_max template.
- vsim on the full building core (only a 353-element sub-network).
- The builder's long `compare_stageB_e.py` mutations re-run on my mutants.
- AGG ratios, decision/reference units.
- Energy meters for buildings.
- SPICE/hardware, Math7.
- Second review of the L1 proof sketch.
