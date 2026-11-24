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

---

# Pass 2: routes B and C, gates X2 (B side), X3, X4, X5

## Setup
- **Git and frozen code:** HEAD `06e0943faf47756ca0197034eaf2048bf27c8334`, verified before work. `tstudy.baseline.assert_frozen()` passed in every pass-2 script (refcalc `8976efea…`, synth `55caf5cd…`, common `ad3d0b7e…`). No `__pycache__` was found in the frozen trees before or after any run (checked in code and by `find`). No git operations were performed, and routes A and E were not assessed.
- **Model:** self-reported claude-opus-5-5. The effort level cannot be observed from inside the session (high was intended).
- **Scenarios** (out of sample for both routes): EV6 `SYN-RC-office-M-T50-seed389633541` and EV10 `SYN-RC-retail-S-T100-seed169387912`, taken from `evaluation_set`. Benchmark S/M and edge `rebuild_within_period` were used only to re-measure a route's own number.

## Commands
```
cd /home/user/-/whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/routes/D_verification
export PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0
python3 -B code/p2_check_b.py    # 56 s  -> results/p2_check_b.json, p2_check_b_log.txt
python3 -B code/p2_hb4.py        # 10 s  -> results/p2_hb4.json
python3 -B code/p2_gates.py      # 11 s  -> results/p2_gates.json
python3 -B code/p2_check_c.py    # 4 min -> results/p2_check_c.json (run 1 had a D oracle bug, see below)
math7-py -B -m unittest discover -s tests -v     # 23 tests OK -> results/test_log_pass2.txt
```

## Results (details in `VERDICTS.md` pass 2, `claims.md` D-20..D-30)
| check | status | headline |
|---|---|---|
| B (1) kernels re-derived and compared with refcalc and grammar.py on new scenarios/grid | PASS | D vs refcalc ≤4.8e-13 in 𝒟′; B's netlists vs D ≤8.2e-16; automaton vs D ≤8.2e-16 |
| B (2) late reset; band agreement; which oracle is the reference | PASS (B's claims confirmed, magnitudes larger) | Without late reset the error is up to 0.97 relative inside 𝒟′. In the band the automaton equals refcalc, while msp's interval form is off by up to 1.24 and agrees at T=sw(τ). refcalc is the reference (03 §3.2/§3.4). The band is a documented unresolved boundary, not a defect. |
| B (3) H-B2 review | CONFIRMED-as-textbook / GAP | The claim needs "LTI" and analytic sources. Switched or ideal-diode passive networks realise kinks exactly. The illustration basis is not a superset of RC responses (it lacks the T term). |
| B (4) H-B4 refrigerant "less state" | REFUTED as stated (metric artefact) | Merged knot form 1,025 vs automaton 1,072 numbers (BM-M); random access 100× slower for the automaton |
| B (5) test audit, boundary handling | no tautology; weak points | Tests run only on benchmark S/M (no out-of-sample scenario); B1-02 [P1 cells] in the band sits at 8.9e-10, close to the 1e-9 tolerance; boundary points are correctly declared outside 𝒟 |
| C (6) = X4 independent composition | PASS | Exact D composition vs refcalc ≤3.3e-14 (stage ≤2.2e-13), 5 cases × 9 T, including β=ι_B2 and a stage subset. COMP rows in units70.json are identical to specs COMP_ROWS. |
| C (7) ranks | PASS (exact) | 1 / 6,6,7(,7) / 7,8,9(,9) = number of T-varying columns. The rank is not a state count. |
| C (8) MAPPING spot check | PASS with 1 flag | 70 rows; role counts match; 10 sampled rows match. `time_form_text` is truncated to 160 chars (`build_mapping.py:148`). Design columns are correctly labelled [H]. |
| C (9) year-table replay | PASS | B1-02 exact; B3-01 0.15–0.56 % |
| X2 B-side | PASS | B's θ_ε netlist = D's rational ledger at every float T; the closed endpoint 10/(1−ε) has no float representative (sw(10) is 0.46 ulp above it) |
| X3 | PASS (set level) | Same 7 block types on both sides; one-sided items listed (27 B-only non-shape kinds; B2-01 labelling) |
| X5 | PASS | C−M=Z exactly; Z′<0; dC/dT≠ρ; C(0+)≠A^init (EV6) |

## D's own error, recorded
In run 1 of `p2_check_c.py`, D applied the amplitude-form kernel h (density amplitude a·H) to canon.py's rate-form Terms (density amplitude a). That mis-scaled B3-01 by 1/H and gave false 1–21 % composition errors. It was fixed by adding `h_rate` (03 §5.1, second form) with a unit test, and the script was rerun. The run-1 log is kept as `results/p2_check_c_log_run1_density_convention_bug.txt`. No route was blamed for this.

## G4 recommendations
- **B: ACCEPT-WITH-CONDITIONS**, covering the six kernels and the late-reset automaton.
- **C: ACCEPT-WITH-CONDITIONS**, covering the inventory, the composition (independently verified), the exact ranks and the replay counterexample.

The conditions are listed in `VERDICTS.md`.

## Pass-2 NOT_RUN
- **Route B:** K26/K28/K30/K32 netlists (B's own NOT_RUN); the RC-a/RC-b numbers (H-B3 continuous part); B's step counts 1,528/95/166.
- **Route C:** the H-C2 signature detector; C-1n; C-4 role checks; C-6.
- **Other:** SageMath/MATLAB/Math7 seven-engine runs; any real-building validation.
- **Not tested:** band behaviour for floats near (but not equal to) integer event times, which 03 §3.4 lists as unverified.

---

# Pass 3: re-check of the A/E fixes; disputes settled (HEAD 7de1065)
- Model, self-reported: claude-opus-5-5. The effort level cannot be observed from inside the session. No git operations; only `routes/D_verification/` was written; no `__pycache__` anywhere. Routes B and C were not assessed: their working-tree edits are in progress by those routes.
- Commands:
  ```
  PYTHONDONTWRITEBYTECODE=1 math7-py -B code/p3_recheck.py          # 93 s -> results/p3_recheck.json, p3_recheck_log.txt
  PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 python3 -B code/p2_gates.py   # rerun after helper rename: byte-identical output
  PYTHONDONTWRITEBYTECODE=1 math7-py -B -m unittest discover -s tests -v       # 25 tests OK (results/test_log_pass3.txt)
  python3 -B A_waveform/tests/test_a.py ; (E) math7-py -B -m unittest discover -s tests   # 27 OK / 24 OK
  ```
- **X5 erratum:** D's pass-2 hand-back statement that X5 rested on T=0.5 only was wrong. All 5 T are inside the domain (`results/p3_x5_domain_check.txt`). The helper is renamed `domain_violations`. The VERDICTS/STATUS pass-2 text ("At 5 T", PASS) stands.
- **Route A:** all fixes CONFIRMED (0 mismatches on 20,044 fresh points × all realizations and conventions; 595/595 points.json rows match).
  - Zero-mean clock dispute: **A right** (3/3/30). D's sub-note is withdrawn.
  - A-16 bound dispute: **A right**. D's m·h/2 holds only at φ∈{0, π/2}. D's new closed form is \|τ_n−nc\| ≤ (h/2)(m+\|g(φ)\|) ≤ 0.21051h (sharp; 0.209736h at φ=asin(2/π), c/h=20.25).
- **Route E:** all fixes CONFIRMED.
  - ρ table: 7/7 rows.
  - Walsh qualifications: 14.2676 kg, the impossibility of exactness at every t, and −0.0397 kg, all confirmed.
  - P1 circuit: 0 mismatches.
  - Fixed-step count difference explained by point-set size and query rule.
  - points.json: 139/139 rows match.
  - Caveat: 'substitute' is encoded as a net −5 entry.
- **G4:** A **ACCEPT**; E **ACCEPT-WITH-CONDITIONS** (see VERDICTS pass 3).
- **Pass-3 NOT_RUN:** routes B/C; the Walsh design as an implemented circuit; a formal written review of the [H] items listed in VERDICTS pass 3.
