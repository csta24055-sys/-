# 09 Joule-heating / resistor-energy route — independent investigation

Status: **design and research task**, NOT a verified improvement.

## Motivation
The user asks whether the natural analog for the *linear rise of cumulative operating emissions* is an ordinary resistor receiving a constant current, **without starting from capacitors**. Yes, under ideal constant current `i(t)=I0` and constant resistance `R`:

- Instantaneous dissipated **electrical power**: `p_R(t) = i(t)^2 R = I0^2 R`.
- Cumulative **dissipated electrical energy**: `E_R(t) = E_R(0) + ∫_0^t p_R(s) ds = E_R(0) + I0^2 R t`.
- For a *constant* independent carbon conversion factor `kappa` with correct units, `G_oper(t) = G_oper(0) + kappa (E_R(t)-E_R(0))`; this is an abstract simulated-energy-to-carbon scaling. It **does not** identify a real building's electricity-to-carbon factor unless sourced and matched to actual consumption.
- Resistor **temperature** need not be linear; with heat loss to ambient it often approaches equilibrium. WLC is matched to cumulative *energy dissipated*, not to instantaneous resistance or temperature.
- Do **not** claim a resistor stores dissipated energy: it transforms power into heat. Integration over time is still required if the numerical output desired is the accumulated amount. A watt-hour meter, mathematical integrator, sampled energy register, or current/voltage integrator may provide that readout. Avoid counting `Q^2/(2C)` as this dissipated energy.

## AC as a competing design
For ideal pure sinusoidal resistor current `i(t)=sqrt(2)*I_rms*sin(omega*t)`:
`p(t)=I_rms^2 R (1-cos(2 omega t))`.
Thus with `E(0)=0`,
`E(t) = I_rms^2 R [t - sin(2 omega t)/(2 omega)]`.
The cumulative energy has a **linear secular term and bounded oscillatory correction**. This is an exact example of linear growth from a resistor under AC, rather than the ideal nonleaky capacitor's zero-mean oscillating charge. Check limits `omega>0`, constant R and source, phase assumptions, units and start time. An arbitrary periodic/variable envelope requires `E(t)=∫i(s)^2 R(s) ds`.

## Research E tasks
1. Independently derive and numerically check DC and AC resistor cumulative energy and the related carbon-equivalent observable against a direct numerical or analytic oracle. Test cycle averages and phase boundary cases.
2. Compare **resistive energy integration** vs **capacitor charge accumulation** vs **explicit summation of emissions** under a fixed independent synthetic energy/carbon mapping; identify exact equivalences and mismatched observables.
3. Model each building operation (electricity, fuel where meaningful) as controlled dissipative power, but do not force materials, construction or replacement pulses to be literal Joule heat; keep them as external scheduled additions or separate non-electrical inputs.
4. Study mixing resistive continuous-time operational energy with discrete equipment-maintenance/replacement events: common total ledger with initial embodied emissions and distinct event schedules.
5. Investigate if dynamic electricity carbon intensity `EF(t)`, time-varying resistance `R(t)`, and equipment efficiency break simple linearity. Use `G_oper(t)=∫ EF(s) P_building(s) ds` after aligning the actual building's electricity demand to the proxy power.
6. Benchmark time/operations/states: a resistor is not by itself a memory of total emissions, so do not count removal of an integrator if the cumulative output cannot actually be obtained.
7. Report mathematically verified advantages or an honest negative result; don't claim a newly discovered Joule's law. Cite exact WLC base source and compare the independent unit models on supported domain.

## Coordination and write scope
This is **parallel Route E** under `routes/E_resistor_energy/`, alongside Route A (charge/waveforms), B (equation families), C (70 evaluation units), D (independent validation). Deliver derived equations, code, independent tests, comparison and limitations under E only; Route D challenges E too. Integrate into a common model only after aligning definitions and passing independent validation.

The original WLC research base, archived source and app are read-only. No protected J-CAT originals or user data in new code.
