# Route E STATUS — G2 batch 1 + D pass 1 fixes (HEAD e4121d6)

- Research question: can resistor Joule energy `∫ i²R dt` (with explicit κ) realise the P0 pilot,
  and where does it differ from charge accumulation (A)? (architecture §2 H-E1..H-E4)
- Source: branch `claude/wlc-equivalent-circuit-20261124` @ `5a2f898` (batch 1), fix pass @ `e4121d6` (also read: `routes/D_verification/VERDICTS.md` route E rows and D `results/` JSON, data only, no D code imported) (read-only inputs:
  `coordination/architecture.md`, `07_SHARED_CONTRACT.md`, `09_RESISTOR_ENERGY_ROUTE.md`,
  `12_FINAL_OPERATING_PLAN.md`, `10_MODEL_ROUTING.md`). No other route's code read or imported.
- Model actually run: self-reported `claude-opus-5-5` (Opus 5.5). Effort: intended **medium**;
  **not observable** from inside the session — unverified.
- Date 2026-11-24. No git checkout/commit performed. No `__pycache__` left (checked with `find`).

## Commands run
```
cd whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/routes/E_resistor_energy
PYTHONDONTWRITEBYTECODE=1 math7-py -B -m unittest discover -s tests -v   # after D pass 1: 24 tests, 24 OK, 0 fail (~17 s)
PYTHONDONTWRITEBYTECODE=1 math7-py -B code/make_results.py              # points/e_numbers/benchmark
find ../../.. -name __pycache__                                         # none
```
Log: `results/test_log.txt`. pytest is not installed in math7-py, so stdlib unittest is used.

## Verdicts (all [E]/[F] by this route only; independent review by D still NOT_RUN)
| Hypothesis | Verdict | Decisive numbers |
|---|---|---|
| Basics | PASS | `R=3,I=2,t=5` → 12 W, 60 J (=20 kg only via κ); RMS 2 A, 5 periods of 1 s → 60 J for φ∈{0, π/4, 1.234} (SymPy exact, mpmath <1e-25, SciPy <1e-9) |
| H-E1 | **PASS** | 11 contract points + 10.000000005, 10.00000002 × 3 conventions: SymPy analytic = Fraction hybrid E-R1 = an explicit event list (independent of `n_events`) **exactly**; mpmath abs err ≤1e-9 (all points), SciPy ≤1e-9 (11 points). Jumps at 10/20/30/40 right-continuous with exact left/right limits (h=1e-12). P1 250/405 (substitute), 305/460 (additional) now produced by the **event-driven circuit** (one external table entry, tuple (4,0,3,1)) and equal to the closed form at 13+2 points × 3 conventions; P2 160/245/295/380/515 by the gain-switched circuit. States (4,0,2,0) / merged (3,0,2,0); the resistor contributes 0 |
| H-E2 | **CONFIRMED** for the tested rectangular, aligned, same-sign pulses (superposition fails); general form and fixes revised in D pass 1 below | DC×pulse cross `4√(20w)` kg: 0.0178885 (w=1e-6), 0.178885 (1e-4), 1.78885 (1e-2), 17.8885 (1); pipe `4√(35w)`. **Simultaneous AC×pipe cross at t=20 = `2√(20·35)` = `20√7` = 52.9150262212918 kg, width-independent (∂/∂w = 0 symbolically)**. G(20+w) → 255+20√7 = 307.915 (w→0); 307.9745 at w=1e-6 (SymPy = mpquad to 15 digits). Fixes (separate resistors / sum powers first) give exactly 255+4w. General event×event term = 2√(A_iA_j)·ρ (see D pass 1) |
| H-E3 | **CONFIRMED, bound sharpened** | φ=0, ω=2π/yr: exact on lattice t∈Z/4 (241 points, symbolic); 7/11 contract points exact; t=9.999999 → +3.99999999989e-6 kg, 10.000001 → −4.0e-6, 19.999999 → +4.0e-6, 20.000001 → −4.0e-6 (SymPy = mpquad to 20 digits; all exceed the 1e-9 gate). Exact sup error `r(1+|sin2φ|)/(2ω)` ≤ r/ω; φ=0: 1/π = 0.318310 kg attained at t=3/8 |
| H-E4 | **CONFIRMED** | EF 1/3→1/4 kg/J at t=10 (P2): convert-then-integrate 40/70/130/190 kg at t=10/20/40/60 (correct); meter-then-convert with current EF 30/60/120/180 (−10 kg constant, and cumulative **drops** 39.999996→30 at t=10); with initial EF 40/80/160/240 (error t−10). Full G wrong readout 150/235/505 vs P2 160/245/515 |

Route-level (architecture §2 PASS criteria): H-E1 analytic+quadrature agree within 1e-9, H-E2..E4
predictions independently recomputed and confirmed (no refuting value), both 60 J cases
reproduced → **PASS candidate pending D**. Not "established".

## Counterexamples found
1. Resistor alone: p(1)=p(30)=12 W but G(1)=104, G(30)=315 → no cumulative readout without integrator.
2. Temperature: leaky thermal node (R_th=1 K/W, C_th=2 J/K) θ(60)=11.9999999999989 K (bounded), E(60)=720 J.
3. H-E2 (aligned equal rectangles) accumulates at every coincident event: after t=60+w, limit 565+60√7 = 723.745 (723.923 at w=1e-6) vs 565.
4. Polarity: reversing the pipe pulse sign gives G(20+w)=202.097 (w=1e-6) with identical event energies — single-resistor energy is not a function of the event amounts.
5. Finite pulses on `[τ,τ+w)` cannot produce the right-continuous jump: even the separated fix gives the **left** value at τ (G(10)=140, G(20)=200), matching P0 only outside windows.
6. AC operating current with a zero at τ=10: pulse cross only O(w^{3/2}) (7.95e-8 kg at w=1e-6) — the cross term depends on the operating waveform phase.
7. Meter-then-convert under changing EF makes cumulative carbon non-monotone.

## Benchmark (results/benchmark.json; 1000 random t∈[0,60), seed 12345, median of 5, Python 3.13.18 x86_64)
closed-form Fraction 4.3 ms; E-R1 hybrid per query 45.2 ms; E-R1 sorted sweep 17.5 ms;
true fixed-step dt=1e-3 sweep 16.2 ms. Hybrid = closed form exactly on all 1000. **No speed gain
from the circuit path** [F]; value is representational only.
The earlier "fixed-step dt=1e-3, max err 3.1e-10" figure is **withdrawn**: that code stepped only
the ramp and computed events by closed-form floor with a +1e-12 fudge. The true fixed-step
integrator (meter and both clocks stepped in float, event at first step end with clock ≥ period)
misses event instants by a whole charge:
| dt | G(10) (exact 160) | G(20) (exact 255) | G(40) / G(60) (exact 410 / 565) | max err at contract points | random pts >1 kg | max err elsewhere |
|---|---|---|---|---|---|---|
| 1e-2 | 140 | 235 | 390 / 545 | 35.000004 | 2 / 1000 | 0.02 |
| 1e-3 | 140 | 235 | 390 / 545 | 35.000004 | 0 / 1000 | 0.002 |
| 1e-4 | 140 | 200 | 355 / 510 | 55.000004 | 0 / 1000 | 0.0002 |
(Event-instant misses of 20 or 55 kg, agreeing with D's G(10)=140; the exact counts of random
misses differ from D's 75/9/7 because the point sets and rounding rule differ.)

8. True fixed-step integration misses event instants by a full 20 or 55 kg charge (table above).
9. Walsh-orthogonal pulses on one resistor are exact only at readouts outside the windows: cross 14.2676 kg at t=20+w/4 (w=0.01); and they are not orthogonal to an AC operating current (cross −0.0397 kg at w=0.01).

## D pass 1 fixes (route D VERDICTS.md, HEAD e4121d6) — each point re-checked by my own execution first
| # | D's point | Outcome | Own evidence |
|---|---|---|---|
| 1 | E-2b "2√(AiAj)" false in general; needs ρ | **FIXED (D correct)** | Derivation: i_k = a_k f_k with a_k²R‖f_k‖² = A_k/κ ⇒ κ·2R∫i_1i_2 = 2√(A_1A_2)·⟨f_1,f_2⟩/(‖f_1‖‖f_2‖) = 2√(A_1A_2)·ρ. SymPy exact + mpmath quadrature (`test_event_cross_term_is_2sqrtAA_rho`): ρ=1 equal aligned → 20√7=52.9150; widths w,4w → ρ=1/2 → 10√7=√700=26.4575; half overlap → 26.4575; widths w,9w → ρ=1/3 → 17.6383; rect vs Walsh(1,1,1,−1) → ρ=1/2 → 26.4575; interleaved, Walsh pair → 0. 20√7 is the Cauchy–Schwarz maximum (|cross| ≤ 52.915 checked) |
| 2 | "single shared resistor must be dropped" refuted | **FIXED (D correct; my early-stop conclusion withdrawn), with a qualification** | One resistor, DC + Walsh pulses (AC (+,+,−,−), pipe (+,−,+,−), lone AC (+,−)): window energy at t=20 = 1376/25 = 4w+55 exactly (SymPy) and to 1e-25 (mpmath); whole P0 after 60+w = 14126/25 = 565+4w. Time-interleaved rectangles: event×event 0, DC×pulse 4√(20w)+4√(35w) remains. **Condition**: at readout t, ∫(Σi_k)²R = Σ∫i_k²R ⇔ Σ_{j<k}∫_0^t i_j i_k = 0; sufficient: pairwise L²-orthogonality of all components (including the operating current) on [0,t]. **Qualification (beyond D)**: orthogonality over a full window gives exactness only at readouts outside windows (inside, cross 14.2676 kg at t=20+w/4); exactness at every t needs disjoint supports, impossible while a DC operating current flows; and orthogonality is w.r.t. the actual operating waveform (AC op current: −0.0397 kg). Cost: pulse shaping and scheduling (sub-window timing, ≥3 extra thresholds or a counter per window, [H] count), amplitudes √(A/(κRw)). Zero-mean pulses carry zero net charge (∫i = 0, tested), so this trick is unavailable to a charge accumulator (route A) |
| 3 | P1 rows labelled E-R1 came from the closed form | **FIXED** | P1 (both policies) implemented in `circuit_e.py` (external table entry τ=20 compared on the same time base as the clocks, so `orig` maps it to 20/(1−ε)); equals `joule.p1` at 13 points + 20.00000001, 20.00000002 × 3 conventions × 2 policies (`test_p1_event_driven_circuit`, `points.json` assert). Tuple corrected to (4,0,3,1) (merged (3,0,3,1)) |
| 4 | fixed-step benchmark hid event errors | **FIXED (D correct)** | `quad_check.fixed_step_true`; table above; `test_true_fixed_step_misses_events` |
| 5a | test compared two sides sharing `n_events` | **FIXED** | expected side now an explicit list of 9 (τ, A) events with per-convention comparisons |
| 5b | AC bound test used closed form + 1 quad point | **FIXED** | numerical search over 24 φ × 61-point grid + bounded refinement, ω∈{2π, 3}, SciPy quadrature: max equals 4(1+|sin2φ|)/(2ω) within 1e-8, never exceeds it by >1e-9; global ≈ 4/ω; φ=0, t=3/8 attains 1/π (mpmath, 1e-30) |
No point disputed.

## NOT_RUN / limits
- Independent review by D; X1 comparison with A (A's results not read by design).
- R(t) variation, equipment efficiency, non-sinusoidal AC envelopes, float knife edge 10.00000001.
- Mapping to real electricity demand/grid EF (out of scope: synthetic only); 70-unit model not touched.

- Walsh/orthogonal-pulse state cost is estimated, not implemented as a circuit; no non-rectangular smooth pulse shapes tested.

## Next actions
D: re-check the ρ-generalization, the in-window non-additivity of orthogonal pulses, and the
event-driven P1 (all conventions). Single shared resistor is **kept** as an option only with
pairwise L²-orthogonal excitations and readouts outside windows; otherwise use separate
resistors / power summing / external additions. (Supersedes the batch-1 "dropped" conclusion.)
