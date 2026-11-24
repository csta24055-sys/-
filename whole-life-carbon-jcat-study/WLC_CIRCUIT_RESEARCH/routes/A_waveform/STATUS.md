# Route A STATUS — G2 batch 1 + D pass 1 fixes (HEAD e4121d6)

- Research question: can a capacitor-charge hybrid circuit (reading Φ, physical time t) reproduce pilot P0/P1/P2/Px exactly, how do event-boundary conventions map to clock reset semantics, and what state 4-tuple does each input class need?
- Branch `claude/wlc-equivalent-circuit-20261124`, HEAD `5a2f898` (verified before work). Inputs read: `coordination/architecture.md` (sha256 1dfb382a0d8a45e5…), `07_SHARED_CONTRACT.md` (3f75b6a04dd11e4a…), `01_FORMAL_MODEL.md`, `12_FINAL_OPERATING_PLAN.md` §1–4, theory-base row 17.TH-11a (grep only). No other route's files read or imported.
- Model actually run (self-reported): **claude-opus-5-5**. Effort level is **not observable** from inside the session (intended: medium).
- Git: no checkout/commit/push performed; files left untracked for the coordinator. No `__pycache__`/`.pyc` created (checked with `find`).

## Verdicts (run in order H-A1 → H-A2 → H-A3; no exact inequality found in H-A1/H-A2, so H-A3 was run)
| hypothesis | verdict | decisive numbers |
|---|---|---|
| H-A1 exact reproduction + convention⇔reset | **PASS** (Fraction, all points) | right/left/orig at 10: 160/140/140; at 20: 255/200/200; 30: 315/295/295; 40: 410/355/355; 60: 565/510/510; 10.000000005: 160.00000002/160.00000002/**140.00000002**; 10.00000002: 160.00000008 ×3; limits τ±1e-12 exact at 10,20,30,40,60; γ,C_cap (1,1) vs (5,2) G-invariant |
| H-A2 impulse-free ramp − sawtooth | **PASS** (Fraction) | slope 7.75 (orig: 4+3.75(1−ε)); R2≡R1 on 11+3 knife+300 random+15 limit points ×3 conventions; residual ∈[0,55) / (0,55] |
| H-A3 state count by input class | **PARTIAL — hypothesis partly refuted** | P0: R3 (2,0,2,0) exact ✓ (also R3k (1,1,2,0)). **Counterexample**: fixed Px is reproduced by one period-20 clock with comparators {7/20,17/20,1} → (2,0,3,0), so "Px needs (3,0,2,0), single clock impossible" is false for a known schedule; it holds only for an online/unknown reset (distinguishing futures 107 vs 127, 64 vs 99) — the necessity claim there is [H] |
| AC negative test | **PASS** (corrected in D pass 1) | zero-mean: Q≤2I0/ω=0.05<1, integrated clock never fires, G(10)=140≠160; below the swing it fires spuriously (3, or 30 with diode clamp, in 10 yr). Full-wave with phase φ: exact ∀n iff c/h∈ℤ, or c/h∈½+ℤ and φ∈{0,π/2} mod π; sharp error 0.10526h (φ∈{0,π/2}) / 0.21051h (general φ); operating ripple ≤0.2105·I0/ω |
| P1 both policies | PASS | substitute 250 / 405, additional 305 / 460 (right, t=20/40); left at 20: 200 |
| P2 | PASS | 160, 245, 295, 380, 515 at 10/20/30/40/60; G(10∓δ)=140−4δ / 160+3δ |
| Px | PASS (R1 and single-clock R3i vs oracle) | right/left |

All architecture §1.2 [H] table values, P1 (250/405/305/460) and P2 (160/245/295/380/515) values were **recomputed independently and agree**. Disagreements with architecture: (1) H-A3 Px claim (above); (2) AC "only integer multiple": false at φ∈{0,π/2} (c/h∈½ℤ exact), true for generic phase; (3) minor: TH-11a `N_c=⌈x⌉−1` gives −1 at T=0 (domain T>0); (4) the orig-convention clock fires at physical time c/(1−ε), so R1-orig is a horizon-readout device, not a physical-time model, and the ramp must not be slowed.

## Counterexamples recorded
1. Px fixed schedule with a single clock (refutes H-A3 as stated).
2. Naive sequential simultaneous-event handling at t=20 gives G(20)∈{250,270,285,305} depending on order (two values match neither policy); the order-free set rule is required.
3. Merged clock capacitor (periods 30, 15, 20/3) with one charge cannot give G(10)=160 and G(20)=255.
4. Float knife edge: at T=10.00000001 exact orig = 140.00000004, float gives 160.00000004 (recorded as undefined zone, not asserted).
5. Half-integer-multiple full-wave clock is exact (c=10.25) — at phase 0 / π/2 only.
6. Zero-mean AC clock with threshold below the swing fires spuriously (3 counts; 30 with a diode clamp) in 10 yr.

## State 4-tuples (cont, discrete, comparators, external table)
R1 P0 (3,0,2,0); R1 P1 (3,0,3,1); R1 P2 (3,1,2,0); R1 Px (3,0,3,1); R2 (3,0,2,0); R3 (2,0,2,0); R3i P0 (2,0,2,0); R3i fixed Px (2,0,3,0); R3k (1,1,2,0); remark (1,0,∞,0) [H, not implemented]. Simulator time t is not counted; ramp integrators are. No lower bound is proven and none of these tuples is claimed minimal: D-10 realizes online Px with 2 continuous states + 2 counters; ≥2 continuous clock phases for online reset is [H] (D-9 proof draft). Readout class: integrators + comparators + linear summing readout, no floor/ceil readout.

## Measured costs (results/benchmark.json; 2000 random rationals in [0,60], seed 20261124, median of 5, Python 3.13.18, x86_64)
closed form Fraction 11.8 µs/pt; R1 47.1; R2 36.6; R3 15.2; closed form float 0.34 (re-run in D pass 1; first run 10.3 / 46.8 / 36.0 / 19.8 / 0.33). tracemalloc peak ≈240 KB for all Fraction paths. R1 mean 3.57 segments/point (max 6). **No speed benefit from the circuit path**; value is representational only.

## Commands run
```
cd /home/user/-/whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/routes/A_waveform
PYTHONDONTWRITEBYTECODE=1 python3 -B tests/test_a.py -v        # first pass 21 tests OK; after D pass 1: 27 tests OK (log: results/test_output.txt)
PYTHONDONTWRITEBYTECODE=1 python3 -B code/make_results.py      # first pass 490 rows; after D pass 1: 595 rows, 0 mismatches; benchmark.json
# D pass 1: pre-fix defect reproduction -> results/d_pass1_prefix_repro.txt, post-fix -> results/d_pass1_postfix_check.txt
# phase/bound exploration script run from the session scratchpad (not part of the route); its findings are encoded in tests
find /home/user/- -name __pycache__ -o -name '*.pyc'           # empty
```

## NOT_RUN / limits
- P2 and Px under the orig convention: not defined (no oracle); now rejected with ValueError instead of silently accepted.
- SPICE / physical circuit simulation: NOT_RUN (all realizations are exact event-driven hybrid models).
- AC tests are float only (transcendental); no exact AC oracle. The diode clamp in simulate_clock is applied per step (dt=1e-3), approximate at that scale.
- Gates X1 (vs E), X2 (vs B), X5: NOT_RUN here (coordinator/D). No claim about C_WLC(T) beyond P0 convention comparison.
- New arguments (A-3 general, A-6 all-t, A-10 necessity, A-16 phase-dependent iff and bounds) remain [H].

## Next actions
D: independently recheck §1.2 table, knife points, Px single-clock counterexample and the ½ℤ AC condition. Coordinator: revise H-A3 wording to "online reset input ⇒ two phases"; X2 can use `p0_r1('orig')`/`p0_r2('orig')`.

## D pass 1 fixes (source: routes/D_verification/VERDICTS.md route A rows; each D point re-executed by A before changing code)
| # | D finding | A re-check (executed) | outcome |
|---|---|---|---|
| 1 | R3i accepts orig but ignores ε | reproduced: R3i(orig)(10.000000005)=160.00000002 vs oracle 140.00000002 (`results/d_pass1_prefix_repro.txt`) | **FIXED**: R3i slows its clock by (1−ε) under orig, rejects unknown conventions; R3i-orig now in `test_r3_single_clock_p0` + hand value 140.00000002; R3k(orig) raises |
| 2 | R1 P1 under orig: clocks slowed, renovation at physical 20 | reproduced: additional@30 = 290 vs 345; substitute@20.00000001 = 250.00000004 vs 200.00000004 | **FIXED**: under orig external events are mapped to τ/(1−ε) (same rule as clocks); `test_p1_orig_consistent` (hand 345, 200.00000004, plus contract/knife/band points vs g_p1). P2/Px under orig and unknown conventions now raise (`test_unsupported_orig_rejected`) |
| 3 | zero-mean AC clock hard-coded 0 | confirmed (old `ac_clock_count` returned 0 after an assert) | **FIXED**: `simulate_clock` integrates the current (exact antiderivative increments, bisection at crossings). Executed negative result: I0=1, ω=2π, θ=0.1 → 3 counts in 10 yr (θ=0.1, ω=4π → 1; θ=0.2 → 1), matching D. **DISPUTED (sub-point)**: D's note "a reset-to-zero clock would count once per positive half-cycle" — executed: reset-to-zero at the exact hit is the same rule as subtract-reset and also gives 3 total; per-cycle counting requires a diode clamp (q≥0), which gives 3 per cycle = 30 |
| 4 | A-16 phase dependent; bound 0.10526h | confirmed: c/h=20.5 off by 0.078 / 0.041 / 0.083 yr at φ=π/4 / 0.3 / 1.0; exact at φ=0, π/2; derivation in claims A-16 | **FIXED** (claim corrected, `test_fullwave_phase_dependence`). Bound **partly DISPUTED**: 0.10526h is sharp only for φ∈{0,π/2} (sampled 0.105257h, matches D); for general φ the sharp bound is 0.21051h (observed 0.2097h at φ=asin(2/π), c/h=20.25; random-phase sample max 0.21049h) — `test_fullwave_sharp_error_bounds` |
| 5 | orig band is closed | confirmed by own test (G_orig(10/(1−ε)) excludes the event) | **FIXED** wording in claims A-3 and README (architecture.md not edited: outside A's write scope) |
| 6 | 3 continuous states not minimal for online reset | not re-implemented by A (D-10 realization not imported); A's own samples unchanged | **FIXED** wording: no minimality claim, pointer to D-9 (draft, [H]) and D-10; readout class stated. D-10 itself: NOT_RUN by A |
| 7 | tautological slope test; set-rule order not tested | confirmed | **FIXED**: slopes compared to stated literals 7.75 and 7.74999999625; set rule actually permuted (clock-list order × renovation split 30+20 / 20+30, both policies, G at 20, 20±δ, 40 → one value each: 250 / 305) |

Tests: 27 run, 27 pass, 0 fail (was 21). points.json: 595 rows (adds R3i all conventions and P1 under orig), 0 mismatches vs oracle.
