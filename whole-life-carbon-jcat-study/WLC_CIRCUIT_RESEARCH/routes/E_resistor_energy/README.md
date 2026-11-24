# Route E — resistor Joule energy as the cumulative-operation analog (Φ, real time t)

User's starting idea: with constant current `I` and resistance `R`, the resistor dissipates the
constant power `p = I²R`, so the **time integral** `E_R(t) = E_R(0) + I²R t` rises linearly, like
constant-rate operational emissions. This is ordinary Joule heating (textbook [L]); nothing here
claims it is new. Route A (capacitor charge) is a separate, competing representation.

## Fixture (synthetic, coordination/architecture.md §1.2, §2)
- `R = 3 Ω`, `I0 = 2 A` → `p = 12 W`; simulated clock **1 s ≙ 1 year**.
- `κ = 1/3 kgCO2e/J` (a declared scaling, = 1.2e6 kgCO2e/kWh — physically meaningless, so it is
  *not* a grid emission factor). `κ·p = 4 kgCO2e/yr`. Joules become kgCO2e **only** via `to_kg(E, κ)`.
- P0: `G(t) = 100 + 4t + 20⌊t/10⌋ + 35⌊t/20⌋`, right-continuous (`τ ≤ t`); also left (`τ < t`) and
  original (`τ < t(1−ε)`, ε=1e-9). G0=100 and replacements are **external scheduled additions**,
  not Joule heat (except in the deliberate H-E2 pulse experiment). P1/P2 as in architecture §1.2.

## What is computed
| Quantity | Meaning | Not to be confused with |
|---|---|---|
| `p_R(t) = i²R` [W] | instantaneous dissipation | cumulative WLC (a p-only output has not computed G) |
| `E_R(t) = ∫ p_R` [J] | dissipated energy, needs a meter/integrator | resistor temperature (bounded with heat loss), `Q²/(2C)` |
| `κ E_R` [kgCO2e] | synthetic carbon proxy | real electricity-carbon accounting |

AC: `i = √2·I_rms·sin(ωt+φ)` ⇒ `E = I_rms²R[t − (sin(2ωt+2φ) − sin 2φ)/(2ω)]` — linear secular term
plus a bounded ripple at 2ω; exact over whole periods for any φ; no rectification needed.

## State / readout requirement (4-tuple: continuous, discrete/counters, thresholds, table entries)
A resistor stores nothing (`p` at t=1 equals `p` at t=30); **the integrator is the state**.
| Realisation | Tuple | Note |
|---|---|---|
| E-R0 resistor alone | (0,0,0,0) | outputs only p → cannot give G(t) (test) |
| E-R1 meter E[J] + event ledger S[kg] + clocks x_A,x_P | (4,0,2,0) | used in code |
| E-R1 with one merged readout register | (3,0,2,0) | equal to A's R1 count as described in architecture §2 (A's code not read) |
| table-driven (H=60) meter + pointer + comparator + 6 (time, kg) rows | (1,1,1,6) | table grows with horizon |
| P2 via EF gain switch | (4,1,2,0) | integrator then stores carbon, not joules |
| H-E2 fix: separate resistors, summed power, one meter | (4,0,2,0) + pulse timers | resistors add no state |

## Layout
- `code/joule.py` SymPy analytic oracle; `code/quad_check.py` mpmath(dps 40)/SciPy quadrature
  (waveforms re-coded numerically, events counted by loop); `code/circuit_e.py` E-R1 hybrid
  event-driven realisation in exact `Fraction`; `code/make_results.py` writes `results/*.json`.
- `tests/test_e.py` (unittest, 20 tests). Results: `results/test_log.txt`, `points.json`,
  `e_numbers.json`, `benchmark.json`. Verdicts in `STATUS.md`, evidence classes in `claims.md`.

```
cd whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/routes/E_resistor_energy
PYTHONDONTWRITEBYTECODE=1 math7-py -B -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 math7-py -B code/make_results.py
```
Dependencies: math7-py (Python 3.13.18, SymPy 1.14.0, mpmath 1.3.0, SciPy 1.15.3, NumPy 2.2.6).
