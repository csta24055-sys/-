# Route A — capacitor charge / waveform (reading Φ: physical time t)

Owner: `wlc-waveform` worker. Status and verdicts: `STATUS.md`. Evidence-classed claims: `claims.md`.
All coefficients are **fictional** (07 pilot P0). Exact agreement in this synthetic model says nothing about real-building emission accuracy.

## Model and units
- Oracle (`code/p0_oracle.py`, `fractions.Fraction`): `G(t)=100+4t+20·N_10(t)+35·N_20(t)` kgCO2e, t in years.
  `N_c` is a closed form (floor/ceil), evaluated under three event-inclusion conventions for an event at τ:
  `right` τ≤t (declared P0 pilot rule), `left` τ<t, `orig` τ<t(1−ε), ε=1e-9 (original research's **horizon** rule; used on P0 data only to compare conventions — it is a C(T) readout rule, not a physical-time rule).
  `G0=100` is an initial condition (present at t=0 under all conventions).
- Simulation units: 1 simulated time unit ≙ 1 year. `γ` [kgCO2e/C] is a defined scaling. `Q=G/γ` [C], `I=dQ/dt=r/γ` between events, impulse `ΔQ=A/γ` at events, `V=Q/C_cap`.
  **Current, power and energy are kept separate**: `P_in=V·I` (electrical power into the capacitor), `E_cap=Q²/(2C_cap)` (stored electrical energy). Neither P_in nor E_cap is carbon; E_cap is quadratic in G and not invariant under (γ, C_cap) (tested). Only the readout `G=γQ` is invariant.

## Realizations (`code/circuit_a.py`; no floor/ceil on t/c — event times come only from integrating clocks to their thresholds)
| id | construct | P0 state 4-tuple (cont, discrete, comparators, table) |
|---|---|---|
| R1 | accumulator Q + clock integrators x_A (period 10), x_P (20), threshold 1, reset, impulses A/γ; order-free simultaneous-event set rule | (3,0,2,0); P1 (3,0,3,1); P2 (3,1,2,0) mode latch; Px (3,0,3,1) |
| R2 | impulse-free: ramp y, slope `r+ΣA_k ν_k` (=7.75, or 4+3.75(1−ε) for orig), minus sawtooth `ΣA_k x_k` | (3,0,2,0) |
| R3 | single superperiod clock (20): `G=100+7.75t−75x+20·[x≥½]` (`>` for left/orig) | (2,0,2,0) |
| R3i | single clock with several (threshold, charge) comparators; P0 `{½:20, 1:55}`, fixed Px `{7/20:20, 17/20:20, 1:35}` | (2,0,2,0) / (2,0,3,0) |
| R3k | one clock + integer counter of superperiods, no ramp | (1,1,2,0) |
| AC | full-wave rectified and zero-mean AC clocks (float, closed-form hit times) | — |

Boundary convention ⇔ reset semantics: `right` = clock reset to 0 and impulse applied **at** τ; `left` = clock held at x=1 and impulse excluded at τ, applied at τ+; `orig` = `left` with clock rate (1−ε)/c and external scheduled events mapped to τ/(1−ε) (ramp **not** slowed); right and orig disagree exactly on the closed band [nc, nc/(1−ε)]. P2/Px under orig are rejected with ValueError (no oracle). The slowed clock places the impulse at physical time c/(1−ε): it models a horizon readout, not a physical emission time.

## AC rules (derived here)
- Zero-mean `I0 sin ωt` into an ideal capacitor: `Q=(I0/ω)(1−cos ωt)∈[0,2I0/ω]`, no secular growth; with a threshold above 2I0/ω the integrated clock never fires (G(10)=140≠160). Below the swing it fires spuriously (θ=0.1, I0=1, ω=2π: 3 times, or 30 in 10 yr with a diode clamp) — counts unrelated to c.
- Full-wave `|I0 sin ωt|`: `Q` strictly increasing, mean `2I0/π`. Ripple about the mean, `f(u)=(I0/ω)(1−cos u−2u/π)` per half period h=π/ω, has zeros only at u∈{0,π/2,π} and `max|f|=(I0/ω)(√(1−4/π²)+2·asin(2/π)/π−1)≈0.2105·I0/ω`.
  With phase φ, hits are exactly at nc for all n iff c/h∈ℤ, or c/h∈½+ℤ and φ∈{0,π/2} mod π. Sharp error bound 0.10526h for φ∈{0,π/2}, 0.21051h for general φ. Reset at the exact hit time (= subtract threshold) causes no drift.

## Reproduce
```
cd whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/routes/A_waveform
PYTHONDONTWRITEBYTECODE=1 python3 -B tests/test_a.py -v       # 27 tests, stdlib only, no network
PYTHONDONTWRITEBYTECODE=1 python3 -B code/make_results.py     # results/points.json, results/benchmark.json
```
