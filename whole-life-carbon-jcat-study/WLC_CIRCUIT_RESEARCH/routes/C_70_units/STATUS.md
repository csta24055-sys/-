# STATUS — route C (70 units → circuit roles), G2 batch 1

Date 2026-11-24.  Branch `claude/wlc-equivalent-circuit-20261124` @ `5a2f898` (full SHA in every
`results/*.json` → `provenance`).  `units70.json` sha256 `b5823481…a414a3`, `unit_dependencies.csv` sha256
`df02509e…73e`.  Frozen trees verified by `tstudy.baseline.assert_frozen()` (refcalc `8976efea…`, synth
`55caf5cd…`, common `ad3d0b7e…`); no stray `__pycache__` before or after the runs (checked in code and by
`find`).  Python 3.13.18, stdlib only, no network.  Git: no checkout/commit made (left to the coordinator).

Model actually used: self-reported `claude-opus-5-5` (Opus 5.5).  Effort is **not observable** from inside
the session (intended: medium) — unverified.

## D pass 2 fixes (HEAD 7de1065; source: `routes/D_verification/VERDICTS.md` pass 2, route C rows)
D's points were re-checked here before any change. The truncation was confirmed: before the fix, 5 rows
differed from units70.json (B1-02, B1-03, B1-04, B3-01, B4-02). D named only B1-03 and B3-01.

| # | Item | Outcome | Evidence |
|---|---|---|---|
| 1 | `time_form_text` truncated to 160 characters in `build_mapping.py` | **FIXED**. Full text, CSV-quoted. MAPPING.csv regenerated (70 rows). New test `test_mapping_full_time_form` checks exact equality with units70.json and 70 rows | `results/test_log.txt` |
| 2 | Construct, class and tuple are [H]; the rank is not a minimal state count | **FIXED**. New column `construct_class_tuple_evidence` = "[H] design rule; no per-unit circuit simulated in route C" on every row. Caveat added to README.md and claims.md | `MAPPING.csv`, `README.md` |
| 3 | Record D's independent results | **FIXED**. H-C1 independently confirmed by D (gate X4, ≤3.3e-14 vs SUM-03 in Fraction composition; caveat: non-refrigerant amplitudes come from msp, so the independence is at implementation level, not data level). Ranks confirmed exactly; replay counterexample confirmed (D: B3-01 0.15–0.56 %). The "7 signals" statement is scenario-dependent (D confirms 6 on S and M). C-2 signature detector, C-1n, C-4 and C-6: **NOT_RUN by D** (still route-C-only [F]) | claims.md |
| 4 | 3 ledger-vs-refcalc dependency differences | **Recorded as observation only**. No defect claim against the read-only source | Mismatches item 4 below |
| — | Rerun of compose_check.py | **NOT_RUN** in this pass. Code and data inputs are unchanged, so `results/hc*.json` still carry provenance 5a2f898 | — |

Disputed items: none.

## Research question
Map each of the 70 fictional units to a Ψ-reading circuit role (axis `T`, output `C(T)`); test H-C1..H-C4 of
`coordination/architecture.md` §2 against the frozen refcalc oracle.

## Results (all synthetic; no claim about real buildings)
| Item | Verdict | Decisive numbers | File |
|---|---|---|---|
| Inventory vs architecture [H] counts | all match | 70 units = refcalc registry; 21 DIRECT + 49; AUX/DEC/REF/AGG/BRK 15/9/10/9/6; COMP 22 rows over 21 units, only non-trivial row (B2-01, B6, −1, ι_B2); 7 block types, const t=0 7 units, const t=T 5 units | `results/inventory.json` |
| H-C1 composition = one summing node | **PASS** | 105 (scenario, stage subset, T) cases, all in domain; max rel err total **3.6e-16**, stage vector **0** (and stage key sets equal, incl. absent stages); SUM-01 1.5e-16, SUM-02 4.2e-16. Scenarios: benchmark S/M/L + edge `rebuild_within_period`, `refurbishment_divides_period`; stage subsets all14, no_B2, no_B6, B_only, 2 random (S, M); T ∈ {1, 9.999999, 10, 10.000001, 20, 30, 60} | `results/hc1.json` |
| H-C1 counterexample (21 independent sources) | as predicted | naive Σ of 21 DIRECT values errs by exactly B2-01/C = **0.14 %–3.7 %** (all14 cases) | `results/hc1.json` |
| H-C2 21 DIRECT into 7 block types | **PASS** (with caveats) | 21/21 consistent with their declared blocks on 3 scenarios × 480 grid pts + 60 flatness probes; 0 fit none. Pure year-cell `by_year` replay exact for B1-02 (max rel 0.0); fails for B1-03 (58–22617×), B3-01 (0.18–0.6 %), B4-02 (3.3e3–1.7e4×), B5-01 (edge: 3.1e6×) → annual tables lose event timing | `results/hc2.json` |
| H-C3 state count depends on the observable | **PASS** (core); numeric "7" **only on 1 of 3** | rank mod constants (rtol 1e-7/1e-9/1e-11 identical): total **1**; 14-stage vector **6 / 6 / 7** (S / M / edge); 21 DIRECT **7 / 8 / 9**. Stage rank = number of T-varying stages in every case (drop-one rank = rank−1 → all independent) | `results/hc3.json` |
| H-C4 non-DIRECT roles are not sources | **PASS** | at T=30, S and M: A5-01+A5-02+A5-03 = A5-04 (rel 0.0), adding A5-01 changes C by 0.10 % / 0.28 %; SYS-01 not upstream of SUM-03, C identical without it; B3-02/B3-01 = 1.024 / 1.012, adding it +10.5 % / +14.7 %; SUM-03 as source +100 %; X-07 = C (rel 6e-16 / 3e-15), adding +100 %; X-08 = B4-02, X-09 = C3-01+C4-01 (≤1.5e-15); summing all 44 numeric `value` fields = 6.7× / 7.1× C | `results/hc4.json` |
| MAPPING.csv | generated | 70 rows; class a 21 / b 8 / c 14 / d 27 / e 0; status conditional 30, unverified 40 | `MAPPING.csv` |
| Tests | **16/16 OK** (after the D pass 2 fixes) | `python3 -B -m unittest discover -s tests -v` (3.8 s) | `results/test_log.txt` |

refcalc dependency closure of SUM-03 (37 units) = all 21 DIRECT + all 15 AUXILIARY + X-02; **no** DECISION,
REFERENCE or BREAKDOWN unit and no other AGGREGATE is upstream of C.  This is the structural basis of "not
70 currents".

## Mismatches / exceptions vs architecture [H]
1. **H-C3 "14 stages need 7 T-dependent signals"**: true only when all of B1..B7 vary. In benchmark S and M
   B5-01 is constant on (0,60] (S: no rebuild; M: rebuild cycle 75 > 60), so rank = 6. The general
   statement that holds on all three: stage rank = number of T-varying stages (≤7), all independent.
2. **H-C2 "7 types"** is a covering, not a partition: B1-03 (atom+gated year cell) and B3-01 (density+gated
   year cell) need two types → 23 memberships for 21 units. Empirically B1-03's gated year-cell part was not
   exercised (features {inner, jump}, no slope) in these scenarios; B1-04 was constant in S; B5-01 only
   exercised in the edge scenario.
3. **H-C2 detector artefact (fixed, recorded)**: on an 8-points-per-year grid, B4-02 (dense atoms from
   200–2000 rows) looked like a ramp with kinks and was first flagged as not fitting "atom". Local flatness
   probes `(T, T+1e-6)` show 0–6.7 % non-flat → piecewise constant. First run kept in history of this
   STATUS only; the recorded `results/hc2.json` is the corrected run.
4. Observation only (no defect claim against the read-only source): the dependencies declared in the ledger
   and in refcalc differ for 3 units. A13-03: refcalc also lists A13-02. X-05: the ledger lists X-04, refcalc
   lists the 23 underlying units. X-07: the ledger also lists B2-01. The set of units upstream of SUM-03
   is unchanged.
5. Architecture §1.3 [F] observation re-checked on S: SUM-03(9.999999) = 8798889.845, SUM-03(10) =
   8798890.207, jump to T=10.000001 = +189936.96 (architecture: ≈ +1.9e5) — consistent.
6. t=0 vs t=T placement of the 12 constants is **not observable** from V(T) (both constant); it comes only
   from the ledger text (TH-4 non-uniqueness).

## Limits (read before using)
- H-C1 is partly circular: refcalc's X-02 implements the same COMP rule. What is independently tested is
  that the COMP rows **as stored in units70.json** (incl. β = ι_B2 under stage subsets) reproduce refcalc's
  composition; float agreement, not exact arithmetic [F].
- H-C2 allowances for gated_year_cell/interval admit every piecewise-affine shape, so for B1-03, B1-04, B3-01
  the empirical check is weak (only "features exercised" information).
- The H-C3 rank is a lower bound for a fixed linear read-out of accumulator outputs. It is **not** a minimal
  state count: each waveform still needs its knot schedule, and rank 1 for the total does not mean one
  capacitor is enough. D confirmed the ranks exactly with rational elimination.
- Circuit constructs, classes a–e and state tuples in MAPPING.csv are **design rules [H]**: no per-unit
  circuit was simulated here (`circuit_simulation:NOT_RUN` on every DIRECT row). 40 non-representative
  non-DIRECT rows have only the structural dependency-closure check.
- Knife-edge T (e.g. 10.000000005) was not part of the grid; `valid_domain` flags it (seen in a probe).
- L scenario used only in H-C1 (cost). H-C2/H-C3 on S, M and one edge scenario.

## Measured cost
Full `compose_check.py`: 2 m 40 s wall (H-C1 60 s, 105 refcalc runs, L ≈ 3 s/run; H-C2 69 s, ~4,300 runs on
S/M/edge; H-C3 28 s, 720 runs; H-C4 0.4 s). Tests 4.1 s.

## NOT_RUN
Per-unit circuit interpreters (route B scope, gate X3); Φ-reading/X5 gate; exact-arithmetic (Fraction)
version of H-C1; H-C2/H-C3 on the L scenario and on `evaluation_set`; benchmark vs Σ/knots baseline;
SageMath/MATLAB (not needed).

## Next actions
1. Coordinator: compare `time_form_blocks` column with route B's kernel list (gate X3) without B reading C.
2. D: re-derive H-C1 with an independent Fraction composition and the B5-exercised edge scenarios.
3. If wanted: H-C3 on more edge scenarios to test whether any B stage pair becomes collinear.
