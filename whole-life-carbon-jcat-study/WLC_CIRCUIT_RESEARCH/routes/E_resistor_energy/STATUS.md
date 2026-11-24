# Route E STATUS — G2 batch 1

- Research question: can resistor Joule energy `∫ i²R dt` (with explicit κ) realise the P0 pilot,
  and where does it differ from charge accumulation (A)? (architecture §2 H-E1..H-E4)
- Source: branch `claude/wlc-equivalent-circuit-20261124` @ `5a2f898` (read-only inputs:
  `coordination/architecture.md`, `07_SHARED_CONTRACT.md`, `09_RESISTOR_ENERGY_ROUTE.md`,
  `12_FINAL_OPERATING_PLAN.md`, `10_MODEL_ROUTING.md`). No other route's code read or imported.
- Model actually run: self-reported `claude-opus-5-5` (Opus 5.5). Effort: intended **medium**;
  **not observable** from inside the session — unverified.
- Date 2026-11-24. No git checkout/commit performed. No `__pycache__` left (checked with `find`).

## Commands run
```
cd whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/routes/E_resistor_energy
PYTHONDONTWRITEBYTECODE=1 math7-py -B -m unittest discover -s tests -v   # 20 tests, 20 OK, 0 fail
PYTHONDONTWRITEBYTECODE=1 math7-py -B code/make_results.py              # points/e_numbers/benchmark
find ../../.. -name __pycache__                                         # none
```
Log: `results/test_log.txt`. pytest is not installed in math7-py, so stdlib unittest is used.

## Verdicts (all [E]/[F] by this route only; independent review by D still NOT_RUN)
| Hypothesis | Verdict | Decisive numbers |
|---|---|---|
| Basics | PASS | `R=3,I=2,t=5` → 12 W, 60 J (=20 kg only via κ); RMS 2 A, 5 periods of 1 s → 60 J for φ∈{0, π/4, 1.234} (SymPy exact, mpmath <1e-25, SciPy <1e-9) |
| H-E1 | **PASS** | 11 contract points + 10.000000005, 10.00000002 × 3 conventions: SymPy analytic = Fraction hybrid E-R1 = P0 closed form **exactly** (rational); mpmath abs err ≤1e-9 (all points), SciPy ≤1e-9 (11 points). Jumps at 10/20/30/40 right-continuous with exact left/right limits (h=1e-12). P1 250/405, 305/460; P2 160/245/295/380/515 reproduced. States (4,0,2,0) / merged (3,0,2,0); the resistor contributes 0 |
| H-E2 | **CONFIRMED** (superposition fails) | DC×pulse cross `4√(20w)` kg: 0.0178885 (w=1e-6), 0.178885 (1e-4), 1.78885 (1e-2), 17.8885 (1); pipe `4√(35w)`. **Simultaneous AC×pipe cross at t=20 = `2√(20·35)` = `20√7` = 52.9150262212918 kg, width-independent (∂/∂w = 0 symbolically)**. G(20+w) → 255+20√7 = 307.915 (w→0); 307.9745 at w=1e-6 (SymPy = mpquad to 15 digits). Fixes (separate resistors / sum powers first) give exactly 255+4w |
| H-E3 | **CONFIRMED, bound sharpened** | φ=0, ω=2π/yr: exact on lattice t∈Z/4 (241 points, symbolic); 7/11 contract points exact; t=9.999999 → +3.99999999989e-6 kg, 10.000001 → −4.0e-6, 19.999999 → +4.0e-6, 20.000001 → −4.0e-6 (SymPy = mpquad to 20 digits; all exceed the 1e-9 gate). Exact sup error `r(1+|sin2φ|)/(2ω)` ≤ r/ω; φ=0: 1/π = 0.318310 kg attained at t=3/8 |
| H-E4 | **CONFIRMED** | EF 1/3→1/4 kg/J at t=10 (P2): convert-then-integrate 40/70/130/190 kg at t=10/20/40/60 (correct); meter-then-convert with current EF 30/60/120/180 (−10 kg constant, and cumulative **drops** 39.999996→30 at t=10); with initial EF 40/80/160/240 (error t−10). Full G wrong readout 150/235/505 vs P2 160/245/515 |

Route-level (architecture §2 PASS criteria): H-E1 analytic+quadrature agree within 1e-9, H-E2..E4
predictions independently recomputed and confirmed (no refuting value), both 60 J cases
reproduced → **PASS candidate pending D**. Not "established".

## Counterexamples found
1. Resistor alone: p(1)=p(30)=12 W but G(1)=104, G(30)=315 → no cumulative readout without integrator.
2. Temperature: leaky thermal node (R_th=1 K/W, C_th=2 J/K) θ(60)=11.9999999999989 K (bounded), E(60)=720 J.
3. H-E2 accumulates at every coincident event: after t=60+w, limit 565+60√7 = 723.745 (723.923 at w=1e-6) vs 565.
4. Polarity: reversing the pipe pulse sign gives G(20+w)=202.097 (w=1e-6) with identical event energies — single-resistor energy is not a function of the event amounts.
5. Finite pulses on `[τ,τ+w)` cannot produce the right-continuous jump: even the separated fix gives the **left** value at τ (G(10)=140, G(20)=200), matching P0 only outside windows.
6. AC operating current with a zero at τ=10: pulse cross only O(w^{3/2}) (7.95e-8 kg at w=1e-6) — the cross term depends on the operating waveform phase.
7. Meter-then-convert under changing EF makes cumulative carbon non-monotone.

## Benchmark (results/benchmark.json; 1000 random t∈[0,60), seed 12345, median of 5, Python 3.13.18 x86_64)
closed-form Fraction 4.1 ms; E-R1 hybrid per query 42.8 ms; E-R1 sorted sweep 17.2 ms;
fixed-step dt=1e-3 float 73 ms for only 100 points (max err 3.1e-10 kg). Hybrid = closed form
exactly on all 1000. **No speed gain from the circuit path** [F]; value is representational only.

## NOT_RUN / limits
- Independent review by D; X1 comparison with A (A's results not read by design).
- R(t) variation, equipment efficiency, non-sinusoidal AC envelopes, float knife edge 10.00000001.
- Mapping to real electricity demand/grid EF (out of scope: synthetic only); 70-unit model not touched.

## Next actions
D: re-derive the 20√7 cross term and the tight AC bound; X1 against A outside pulse windows.
Per architecture §5 early stop (2): single-resistor integration of events is dropped; keep only
separate-resistor / power-summing designs or external additions.
