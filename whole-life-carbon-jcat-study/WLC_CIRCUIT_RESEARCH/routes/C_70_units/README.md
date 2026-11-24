# C_70_units — 70 evaluation units → circuit roles (Ψ reading)

Owner: route C (`wlc-unit-mapper`).  Status and numbers: `STATUS.md`.  Claims with evidence classes: `claims.md`.

## Question
Which circuit role does each of the 70 units of the fictional independent WLC model play, when the circuit
is read in the **Ψ sense** of `coordination/architecture.md` §1.4 (sweep axis = evaluation horizon `T`,
output = `C(T)` of the original research model, current ≙ `ρ+Z'`, **not** a physical emission rate)?
The 70 units are **not 70 emission currents**: only 21 DIRECT units enter `C(T)` through the composition
table COMP (22 rows); the other 49 are pre-stage parameters, logic, alternative estimates, read-out
arithmetic or branch read-outs.

## Domain, units, conventions
- `T` in years, `0 < T ≤ 60` here (`H = 130` year tables of the generator); values in kgCO2e (fictional).
- Event rule of the original: an event at `τ` counts iff `τ < T(1−ε)`, `ε = 1e-9` (`refcalc/base.py`).
  This is **not** the right-continuous P0 convention of routes A/E. `T=10` excludes 10-year events.
- Domain: `tstudy.scenarios.valid_domain` (knife edges `1e-10 < d < 1e-8` excluded). All tested
  `(scenario, T)` pairs are recorded with their domain reasons in `results/hc1.json` etc.
- Scenarios: frozen generator `synth` via `tstudy.scenarios.benchmark()` (S/M/L, T60) and two named edge
  scenarios `rebuild_within_period` (B5 events at 25, 50) and `refurbishment_divides_period` (30, 60).
  The study period is changed on a deep copy (`boundary.study_period`); stage subsets likewise
  (`boundary.included_lifecycle_stages`).  Nothing real is modelled.

## Method (what is executed)
| Hypothesis | Executed check | Oracle |
|---|---|---|
| inventory | counts/roles/COMP/blocks from `units70.json`; ids vs refcalc registry; ledger vs refcalc dependency edges; refcalc dependency closure of SUM-03 | units70.json, refcalc registry |
| H-C1 | rebuild `C(T)=Σ_s ι_s Σ_u σβ V_u(T)` from the 21 DIRECT refcalc values and the COMP rows **read from JSON**; compare to SUM-03 and X-02 `by_stage` (key sets too), plus SUM-01/02 | refcalc SUM-03 / X-02 |
| H-C2 | text classification of each DIRECT `time_form` into 7 block types + empirical shape signature of `V_u(T)` on a grid of 8 interior points per year cell over (0,60] and 60 local-flatness probes `(T, T+1e-6)`; `by_year` replay through a pure year-cell integrator | refcalc per-unit values |
| H-C3 | numerical rank modulo constants of the 14-stage matrix, the 21-DIRECT matrix and the total over `T = 0.25..60` (240 pts), rtol 1e-7/1e-9/1e-11 | refcalc X-02, SUM-03 |
| H-C4 | one executed not-a-source example per non-DIRECT role (A5-01 & B4-01, SYS-01, B3-02, SUM-03, X-07) | refcalc |

Block-type keyword rules (`common.blocks_from_text`): `定数の核` → const (`t=T` in text → const_tT else
const_t0), `区間形` → interval, `密度` → density, `原子` → atom, `ゲート付き年セル` → gated_year_cell,
`年セルの和` → year_cell.  Shape features (`common.block_signature`): const, slope, int_kink (slope change at
an integer), jump (discontinuity in the gap around an integer), inner (jump/slope change inside a cell).
Allowed features: const→{const}; year_cell→{slope,int_kink}; density→{slope}; atom→{jump,inner} (no slope);
gated_year_cell, interval→all.

Rank modulo constants: columns centred and divided by their own norm, pivoted Gram–Schmidt with
re-orthogonalisation (pure Python).  It is the number of linearly independent T-varying waveforms that a
fixed linear read-out of accumulator outputs must span — a lower bound on independent accumulator outputs
under that read-out assumption, not a minimal-realisation theorem.

## Circuit vocabulary of MAPPING.csv
**Read first:** the columns `target_circuit_construct`, `circuit_class` and `state_tuple` are **[H] design
rules**. Route C simulated no per-unit circuit; each row repeats this in `construct_class_tuple_evidence`.
`time_form_text` holds the full ledger `time_form`, untruncated and CSV-quoted (newlines kept). It is
tested against units70.json.
The H-C3 rank is **not a minimal state count**. It counts the independent T-varying waveforms that a fixed
linear read-out needs. Each waveform still needs its own knot schedule (comparator thresholds or table
entries, thousands for B3-01 and B4-02). A total of rank 1 does not mean one capacitor is enough.

Class: (a) passive, (b) active (summing/inverting/gain/divider amplifiers, integrators with constant source),
(c) switched/hybrid (comparators, table-switched sources, resets, sample-hold), (d) external digital,
(e) unsupported.  State 4-tuple `(continuous, discrete/counters, comparator thresholds, table entries)`,
symbolic: `Y=ceil(T)`, `F` = number of event families of the unit, `n` = rows.  **All construct/class/tuple
entries are design rules [H]**; no per-unit circuit was simulated in route C (that is route B's kernel
work, compared later at gate X3).  What route C executed is the composition node, the role checks, the
shape signatures and the ranks.

## Files
- `code/common.py` helpers (oracle loader with `assert_frozen`, ledger access, rebuild, signatures, rank).
- `code/compose_check.py` H-C1..H-C4 and inventory → `results/{inventory,hc1,hc2,hc3,hc4}.json`.
- `code/build_mapping.py` → `MAPPING.csv` (70 rows, machine-generated).
- `tests/test_c.py` unit + oracle + artefact tests.
- `results/run_log.txt`, `results/test_log.txt` logs of the recorded run.

## Reproduce
```
cd whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/routes/C_70_units
export PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0
python3 -B code/compose_check.py            # ~2.5 min (L scenario dominates H-C1)
python3 -B code/build_mapping.py
python3 -B -m unittest discover -s tests -v
```
Python 3.13 stdlib only; no network; frozen trees are verified by `tstudy.baseline.assert_frozen()` and
the absence of stray `__pycache__` is checked before and after.
