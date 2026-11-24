# Route D STATUS — G3 pass 1 (routes A and E)

- Research question: do routes A (capacitor charge) and E (resistor Joule energy) reproduce the fictional pilots P0/P1/P2/Px exactly under declared boundary conventions, and which of their equivalence, state-count, AC and performance claims survive an independent oracle and adversarial probes?
- Branch `claude/wlc-equivalent-circuit-20261124`, HEAD `e182105c52019a4abe07fbdd61eb0e057b257f93` (verified before work). Routes B and C were still running and were **not** read or assessed.
- Inputs (sha256 prefix): `coordination/architecture.md` 1dfb382a…, `07_SHARED_CONTRACT.md` 3f75b6a0…, `02_VERIFICATION_PLAN.md`, `12_FINAL_OPERATING_PLAN.md`; A `p0_oracle.py` e679edff…, `circuit_a.py` 4d258fb4…, `points.json` a060fdf7…; E `joule.py` d4f8b12c…, `circuit_e.py` 0a3503f9…, `quad_check.py` eeaf35d7…, `make_results.py` dc92336e…, `points.json` 2d2c6abf….
- Model actually run (self-reported): **claude-opus-5-5**. Effort is **not observable** from inside the session (intended: high).
- Git: no checkout/commit/push. Files written only under `routes/D_verification/`. No `__pycache__`/`.pyc` anywhere in the checkout (checked with `find`).

## Commands run
```
cd /home/user/-/whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/routes/D_verification
PYTHONDONTWRITEBYTECODE=1 math7-py -B code/run_all.py        # all six scripts exit 0, 2 min 22 s; logs results/*_log.txt
PYTHONDONTWRITEBYTECODE=1 math7-py -B -m unittest discover -s tests -v   # 17 tests OK (results/test_log.txt)
find /home/user/- -name __pycache__ -o -name '*.pyc'         # empty
```

## Results (details: `VERDICTS.md`, `claims.md`)
| check (architecture §3) | status | headline |
|---|---|---|
| 1 boundary, knife points, limits, float | PASS (values) / 1 wording error | 14 points × 3 conventions + exact limits recomputed. All 490 A rows and 83 E rows match. **Band is closed** [nc, nc/(1−ε)], not half-open (architecture §1.2, A-3). Float slip-through: c=0.1 gives floor(t/c)≠n at 196/600 exact event instants (first n=3); P0 integer periods hide this from all route tests |
| 2 simultaneous events P1 | PASS | substitute 250/405, additional 305/460, left 200; no duplicated (item,time); 200 shuffled ledgers → one value; naive sequential {250,270,285,305} reproduced; restart at 20 (AC 30, pipe 40); D-declared renovation at 15 restarts AC 25/pipe 35, A.R1 agrees |
| 3 P2 precedence / rounding | PASS | 160/245/295/380/515; no route used year-cell rounding (would give −1 kg) |
| 4 state count / information loss | PASS with corrections | (i) single-charge merged clock fails for **every** period; (ii) A's Px single-clock counterexample confirmed; online futures 107/127, 64/99 confirmed; D lower-bound draft d≥2 [H] and a 2-continuous-state realization (2 clocks + 2 counters) → A's 3 continuous states are not minimal; (iii) 20√7 confirmed for equal aligned windows only (general: 2√(AiAj)·ρ, ρ=L² cosine; widths w,4w → √700); a **single** resistor is exactly additive with time-interleaved or Walsh-orthogonal pulses; (iv) single accumulator suffices iff the schedule is external (table grows with H) |
| 5 Z(T) / X5 | NOT_RUN | out of scope this pass (B/C) |
| 6 AC / Joule | PASS with corrections | zero-mean charge bounded for all phases; A-16 "iff c/h∈½ℤ" holds only for φ∈{0,π/2} mod π (general: iff c/h∈ℤ); A's "< h" error bound is ~9.5× loose (sharp 0.10526 h); E bound r(1+|sin2φ|)/(2ω): 0 violations by quadrature, attained; E lattice incl. second family confirmed; H-E4 table confirmed |
| 7 benchmark | PASS (measured) | see below; **no speed gain on any circuit path** |
| X1 A vs E | PASS | identical outside pulse windows; E separate pulses = left value at τ; one-resistor deviation = DC cross + 2√(AiAj)ρ; A's charge additive |
| X2 | A-side PASS, B-side NOT_RUN | A's orig realizations = D orig on 20 044 points |
| large random cross-check | PASS | A.R1/R2/R3/R3k/R3i/px/p1/p2 and E.ER1 vs D: 0 mismatches on 100 044 (right) and 20 044 (left, orig) points |

## Bugs / defects / weak tests found
1. `circuit_a.py:333-335` `ac_clock_count(..., "zero")` returns 0 without integrating; `tests/test_a.py:272,276` are therefore tautological.
2. `circuit_a.py:250-280` R3i accepts `conv='orig'` but ignores ε (returns left values: 160.00000002 instead of 140.00000002 at 10.000000005); untested (`test_a.py:158` skips it). Outside A's claimed domain.
3. A's R1 under `orig` with external events (P1): `circuit_a.py:40` slows only clocks, `:123` fires the renovation at physical 20 → additional@30 gives 290 vs 345 (A's own `g_p1(orig)`, E and D agree on 345). Not claimed or tested by A, but accepted silently.
4. `test_a.py:234-236` declares set-rule order invariance "trivial" and does not test it (D tested reversed clock list and shuffled ledgers: invariant). `test_a.py:134-136` (slope) recomputes the code's formula.
5. A claims.md A-3 band `[nc, nc/(1−ε))` contradicts A's own `test_a.py:85` (closed band).
6. E `make_results.py:35-39`: P1 rows labelled "E-R1 + one-shot external addition", value from closed form `joule.py:74-78`; `circuit_e.py` has no renovation. STATUS "P1 reproduced" is closed-form only; P1 tuple `[4,0,3,0]` omits the table entry A counts.
7. E `make_results.py:113-118` "fixed step": events by closed-form floor on the grid with a `+1e-12` fudge; the reported 3.1e-10 max error hides event-detection error. True fixed-step integration (D) is off by a full 20/55 kg charge at event instants for dt=1e-2…1e-4.
8. E `test_e.py:76-77`: `g_dc` and `p0_fixture` share `n_events` (`joule.py:45-55`), so the event part of that comparison is tautological (E-R1 and mpmath loop counting remain independent). `test_e.py:200-212` checks the trig inequality on the closed-form ripple, not on integrated energy (one quadrature point only).
9. E STATUS conclusion "single-resistor integration of events is dropped" (architecture early stop 2) is refuted as a necessity: L²-orthogonal excitations make one shared resistor exactly additive (D-13).
Evidence labels: neither A nor E claims [P]; their [E]/[F]/[H] labels are justified, except that A-16's iff is stated without its phase condition and E-2b's "general 2√(AiAj) form" is false for unequal shapes.

## Benchmark (results/benchmark.json; 11 contract + 1e5 uniform k/1e6 points in [0,60], seed 20261124; CPython 3.13.18, x86_64 Linux; median of 5 perf_counter runs)
| method | µs/point | ops/query (instrumented estimate) | tracemalloc peak | state 4-tuple | exact? |
|---|---|---|---|---|---|
| (a) closed form Fraction | 5.17 | 9 | 12.0 MB | (0,0,0,0) | yes |
| (a) closed form float | 0.15 | 9 | 3.2 MB | (0,0,0,0) | max err 5.7e-14 |
| (b) knots + bisect Fraction | 3.49 | 7 | 12.0 MB | (0,0,0,6) at H=60 | yes |
| (b) knots + bisect float | 0.11 | 7 | 3.2 MB | (0,0,0,6) | max err 5.7e-14 |
| (c) D hybrid circuit, per query | 20.4 | 41.5 (3.50 segments) | 12.0 MB | (3,0,2,0) | yes |
| (c) D hybrid circuit, sorted sweep | 12.4 | 22.6 amortized | 16.0 MB | (3,0,2,0) | yes |
| (d) fixed step float sweep dt=1e-2 / 1e-3 / 1e-4 | 0.43 / 0.55 / 1.24 | 22 / 27 / 76 amortized (per query from 0: 5.4e4…5.4e6) | 7.2 MB | (3,0,2,0) | **no**: 75 / 9 / 7 points off by a full charge; G(10)=140 |
Peaks are dominated by the 1e5-element output list. Best circuit path is 2.4× slower than the Fraction closed form and 3.6× slower than knots. **No speed gain from any circuit path; value is representational only.** Timings are one machine, one run of 5 repetitions.

## NOT_RUN / limits
- Routes B and C, gates X2 (B-side), X3, X4, X5, Z(T), C(0+)≠A^init, refrigerant, 70-unit model: NOT_RUN in this pass.
- SPICE/physical circuits, SageMath/MATLAB, Math7 seven-engine workflow: NOT_RUN (Python only: stdlib + mpmath; SymPy only inside E's code).
- D-9 lower bound, D-12 ρ formula, D-16 phase condition: new proof drafts [H]; they need an independent reviewer before [P].
- AC results are high-precision floating point (mpmath 25–40 digits), not exact.

## Next actions
- A: qualify A-3 (closed band), A-16 (phase), A-10 (2 continuous + counters achievable); guard R3i/R1 against `orig` with external events; replace the hard-coded zero-mean clock with a simulated one; add a set-rule permutation test.
- E: implement P1 in E-R1 or relabel; relabel the fixed-step benchmark; restate E-2b with ρ; keep orthogonal-excitation single-resistor designs open.
- Coordinator: fix architecture §1.2 band wording and early-stop (2); run D pass 2 on B/C (X2 B-side, X3–X5, Z(T), refrigerant) when those routes finish.
