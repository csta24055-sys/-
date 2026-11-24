# Route E claims (evidence classes per 07_SHARED_CONTRACT.md)

Source commit `5a2f898`. [E]=exact sample checks (SymPy/Fraction), [F]=numerical tests (mpmath/SciPy),
[L]=textbook, [H]=hypothesis/new derivation not independently reviewed. Nothing here is [P]: the
derivations below are elementary but have not been reviewed by D.

| ID | Claim | Class | Evidence |
|---|---|---|---|
| E-L0 | `p=i²R`, `E=∫i²R dt`, AC RMS-power relations are ordinary Joule heating; not novel | [L] | textbook |
| E-1 | E-R1 (meter + external additions + 2 clocks) equals P0 at 11+2 points in 3 conventions | [E][F] | `test_contract_points_all_conventions`, `points.json` |
| E-1s | Resistor holds no cumulative value; integrator is the state. E-R1 (4,0,2,0), merged (3,0,2,0) ≥ resistor-only (0,0,0,0) which cannot output G | [E] (tuple counting is a design claim [H]) | `test_resistor_alone_is_not_a_memory` |
| E-1t | Bounded resistor temperature is not cumulative energy | [E] (one thermal model) | `test_temperature_is_not_cumulative_energy` |
| E-2a | Single shared resistor: pulse×DC cross `κ·2 I0 a R w = 4√(20w)` kg (AC), `4√(35w)` (pipe) | [E][F] | `test_symbolic_cross_terms`, `test_numeric_widths_and_quadrature` |
| E-2b | Simultaneous pulse cross at t=20 = `2√(A_A A_P)` = `20√7` ≈ 52.915 kg, independent of w; accumulates per coincidence (60√7 by t=60) | [E][F]; general `2√(A_i A_j)` form [H] | same + `e_numbers.json` |
| E-2c | Sign of pulse current changes cumulative result (202.10 vs 307.97 at w=1e-6) | [E][F] | `test_polarity_counterexample` |
| E-2d | Separate resistors or summing powers before integration restore exact additivity (255+4w) | [E][F] | tests above |
| E-2e | A finite pulse on `[τ,τ+w)` yields the left-continuous value at τ | [E][F] | `test_finite_pulse_cannot_jump` |
| E-3a | AC energy closed form; exact on lattice `sin(2ωt+2φ)=sin2φ` (φ=0, ω=2π: t∈Z/4) and on full periods for any φ | [E] | `test_lattice_exact`, `test_full_periods_any_phase` |
| E-3b | Off-lattice deviation at 9.999999 = +4.0e-6 kg (precisely 3.99999999989e-6) | [E][F] | `test_off_lattice_contract_points` |
| E-3c | Tight bound `sup|κE − r t| = r(1+|sin2φ|)/(2ω) ≤ r/ω` | [H] (derivation) + [F] sampling, [E] attainment at φ=0, t=3/8 | `test_bound_and_tightness` |
| E-4 | With time-varying EF only `∫EF·p dt` is correct; meter-then-convert errs (−10 kg or t−10) and can be non-monotone | [E][F] | `test_convert_then_integrate_vs_meter_then_convert` |
| E-5 | Circuit (hybrid) path has no speed advantage over the closed form on P0 | [F] (one machine) | `benchmark.json` |
| E-N | Joules equal kgCO2e only through an explicit κ; κ=1/3 kg/J is a synthetic scaling (1.2e6 kg/kWh) | [E] (units check) | `test_units_kappa_required` |

Candidate contributions (architecture §5) — all [H] until D: the A/E distinction via the
width-independent coincident-event cross term, and the left-value-at-τ property of finite pulses.
