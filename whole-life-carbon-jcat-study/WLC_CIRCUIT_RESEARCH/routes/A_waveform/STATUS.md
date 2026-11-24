# Route A STATUS — G2 batch 1

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
| AC negative test | **PASS** | zero-mean: Q≤2I0/ω=0.05<1, never fires, G(10)=140≠160. Full-wave: exact hits ∀n **iff c/h∈½ℤ** (architecture said "only integer multiple" — c=10.25=20.5h is exact, refines the claim); else |τ_n−nc|<h; operating ripple ≤0.2105·I0/ω |
| P1 both policies | PASS | substitute 250 / 405, additional 305 / 460 (right, t=20/40); left at 20: 200 |
| P2 | PASS | 160, 245, 295, 380, 515 at 10/20/30/40/60; G(10∓δ)=140−4δ / 160+3δ |
| Px | PASS (R1 and single-clock R3i vs oracle) | right/left |

All architecture §1.2 [H] table values, P1 (250/405/305/460) and P2 (160/245/295/380/515) values were **recomputed independently and agree**. Disagreements with architecture: (1) H-A3 Px claim (above); (2) AC "only integer multiple" → "iff half-integer multiple"; (3) minor: TH-11a `N_c=⌈x⌉−1` gives −1 at T=0 (domain T>0); (4) the orig-convention clock fires at physical time c/(1−ε), so R1-orig is a horizon-readout device, not a physical-time model, and the ramp must not be slowed.

## Counterexamples recorded
1. Px fixed schedule with a single clock (refutes H-A3 as stated).
2. Naive sequential simultaneous-event handling at t=20 gives G(20)∈{250,270,285,305} depending on order (two values match neither policy); the order-free set rule is required.
3. Merged clock capacitor (periods 30, 15, 20/3) with one charge cannot give G(10)=160 and G(20)=255.
4. Float knife edge: at T=10.00000001 exact orig = 140.00000004, float gives 160.00000004 (recorded as undefined zone, not asserted).
5. Half-integer-multiple full-wave clock is exact (c=10.25).

## State 4-tuples (cont, discrete, comparators, external table)
R1 P0 (3,0,2,0); R1 P1 (3,0,3,1); R1 P2 (3,1,2,0); R1 Px (3,0,3,1); R2 (3,0,2,0); R3 (2,0,2,0); R3i P0 (2,0,2,0); R3i fixed Px (2,0,3,0); R3k (1,1,2,0); remark (1,0,∞,0) [H, not implemented]. Simulator time t is not counted; ramp integrators are. No lower bound is proven.

## Measured costs (results/benchmark.json; 2000 random rationals in [0,60], seed 20261124, median of 5, Python 3.13.18, x86_64)
closed form Fraction 10.3 µs/pt; R1 46.8; R2 36.0; R3 19.8; closed form float 0.33. tracemalloc peak ≈240 KB for all Fraction paths. R1 mean 3.57 segments/point (max 6). **No speed benefit from the circuit path**; value is representational only.

## Commands run
```
cd /home/user/-/whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/routes/A_waveform
PYTHONDONTWRITEBYTECODE=1 python3 -B tests/test_a.py -v        # 21 tests, OK (log: results/test_output.txt)
PYTHONDONTWRITEBYTECODE=1 python3 -B code/make_results.py      # points.json 490 rows, 0 mismatches; benchmark.json
find /home/user/- -name __pycache__ -o -name '*.pyc'           # empty
```

## NOT_RUN / limits
- P2 and Px under the orig convention: NOT_RUN (not defined for a horizon rule).
- SPICE / physical circuit simulation: NOT_RUN (all realizations are exact event-driven hybrid models).
- AC tests are float only (transcendental); no exact AC oracle; zero-mean AC with threshold below the swing (spurious frequency-driven counts): NOT_RUN.
- Gates X1 (vs E), X2 (vs B), X5: NOT_RUN here (coordinator/D). No claim about C_WLC(T) beyond P0 convention comparison.
- New arguments (A-3 general, A-6 all-t, A-10 necessity, A-16 iff) remain [H] until D reviews.

## Next actions
D: independently recheck §1.2 table, knife points, Px single-clock counterexample and the ½ℤ AC condition. Coordinator: revise H-A3 wording to "online reset input ⇒ two phases"; X2 can use `p0_r1('orig')`/`p0_r2('orig')`.
