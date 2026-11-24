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
| E-2b | (revised, D pass 1) Event×event cross = `2√(A_iA_j)·ρ_ij`, ρ = L² cosine of the two current shapes; \|cross\| ≤ 2√(A_iA_j) (Cauchy–Schwarz). Value 20√7 ≈ 52.915 kg, width-independent, only for equal, aligned, same-sign windows (ρ=1; then 60√7 by t=60). w/4w or half overlap → 26.458; w/9w → 17.638 | [E][F] (derivation [H] until D) | `test_event_cross_term_is_2sqrtAA_rho`, `e_numbers.json` D_pass1 |
| E-2c | Sign of pulse current changes cumulative result (202.10 vs 307.97 at w=1e-6) | [E][F] | `test_polarity_counterexample` |
| E-2d | (revised) Additivity on a resistor at readout t ⇔ Σ_{j<k}∫_0^t i_j i_k = 0; sufficient: pairwise L²-orthogonality of all current components on [0,t]. Realisations: separate resistors / summed powers (all t); one shared resistor with Walsh zero-mean pulses (window 4w+55 exactly; exact only outside windows, 14.27 kg cross inside at w/4; broken by an AC operating current, −0.0397 kg); interleaving removes only event×event terms. Zero-mean pulses carry no charge → not available to route A | [E][F]; state cost [H] | `test_shared_resistor_walsh_and_interleaved` |
| E-1p | P1 both policies by the event-driven circuit = closed form, 3 conventions; tuple (4,0,3,1) | [E] | `test_p1_event_driven_circuit` |
| E-5f | True fixed-step (float) integration misses event instants by a full 20/55 kg for dt∈{1e-2,1e-3,1e-4} (G(10)=140) | [F] | `test_true_fixed_step_misses_events`, `benchmark.json` |
| E-2e | A finite pulse on `[τ,τ+w)` yields the left-continuous value at τ | [E][F] | `test_finite_pulse_cannot_jump` |
| E-3a | AC energy closed form; exact on lattice `sin(2ωt+2φ)=sin2φ` (φ=0, ω=2π: t∈Z/4) and on full periods for any φ | [E] | `test_lattice_exact`, `test_full_periods_any_phase` |
| E-3b | Off-lattice deviation at 9.999999 = +4.0e-6 kg (precisely 3.99999999989e-6) | [E][F] | `test_off_lattice_contract_points` |
| E-3c | Tight bound `sup|κE − r t| = r(1+|sin2φ|)/(2ω) ≤ r/ω` | [H] (derivation) + [F] sampling, [E] attainment at φ=0, t=3/8 | `test_bound_and_tightness` |
| E-4 | With time-varying EF only `∫EF·p dt` is correct; meter-then-convert errs (−10 kg or t−10) and can be non-monotone | [E][F] | `test_convert_then_integrate_vs_meter_then_convert` |
| E-5 | Circuit (hybrid) path has no speed advantage over the closed form on P0 | [F] (one machine) | `benchmark.json` |
| E-N | Joules equal kgCO2e only through an explicit κ; κ=1/3 kg/J is a synthetic scaling (1.2e6 kg/kWh) | [E] (units check) | `test_units_kappa_required` |

Withdrawn: batch-1 "single-resistor integration of events must be dropped" and the
"fixed-step dt=1e-3 max err 3.1e-10" figure (see STATUS, D pass 1).

Candidate contributions (architecture §5) — all [H] until D: the A/E distinction via the
shape-dependent (ρ) event cross term and its removal by zero-charge orthogonal pulses (impossible
for a charge accumulator), and the left-value-at-τ property of finite pulses.
