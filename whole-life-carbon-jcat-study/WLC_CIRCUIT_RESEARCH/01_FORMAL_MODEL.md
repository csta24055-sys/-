# 01 Formal model — circuit grammar and non-equivalence guards

## Time, units, and observable
Let `t` denote physical elapsed years from a defined origin and `T` an evaluation horizon; do not conflate them. For physical-time emitted quantities, define `G(t)` in kgCO2e and a strictly positive electrical scaling `gamma` in kgCO2e/C. Electrical **charge** `Q(t)=G(t)/gamma` (C), current `I(t)=dQ/dt` (C/year under a mathematically re-scaled clock), and a readout voltage `V(t)=Q(t)/C_acc` for fixed accumulating capacitance `C_acc`. The 'year' to 'second' calibration must be specified for a physical SPICE circuit; use a simulation-time mapping for purely mathematical work.

A synthetic simplified example:
```
G(t) = G0 + integral_0^t [e_oper(s) + e_repair(s)] ds
             + sum_j A_j H(t - tau_j)
```
Here `H` is the Heaviside step under a declared left/right convention and `A_j` is a whole event's kgCO2e. More generally, the event source is a measure with atoms `A_j delta_(tau_j)`; finite-duration maintenance uses a finite pulse integrating to `A_j`. Set `Q0=G0/gamma`, `I_cont=(e_oper+e_repair)/gamma` and pulse **charge** `Delta Q_j=A_j/gamma`. Include fuel, materials, demolition, repair and avoided-event accounting only within the expressly declared boundary; negative adjustments may be bookkeeping currents, not negative physical emissions.

For electricity, if `p(t)` is kWh/year and `EF(t)` is kgCO2e/kWh, `e_oper(t)=p(t)EF(t)` is kgCO2e/year. If power is specified in kW, convert correctly using the time variable and operating schedule. Time-variable EF must be kept inside the integral.

## Circuit grammar: distinct functions
- **Total accumulator:** a fixed nonleaky ideal capacitor plus initial voltage/charge and one or more controlled current sources. KCL at its node sums carbon-rate equivalents. Do not mistake capacitor *stored energy*, `Q^2/(2C)`, for carbon or electrical kWh.
- **Equipment age/timing unit:** *separate* integrator with state `x_i(t)`, e.g. `dx_i/dt = 1/c_i` between events; when `x_i=1`, register a replacement and reset `x_i=0`. Equivalently a current-charged capacitor plus comparator and discharge/reset switch. If current and threshold equal across units, `C_2=2 C_1` doubles their ideal charge time. This is not a claim about actual equipment aging, only a fixed-period clock.
- **Shared excitation:** optionally derive monotonic age progression from a common electrical driving source using rectification or suitable control. **Unrectified zero-mean AC cannot provide monotonically increasing charge in an ideal capacitor**; AC frequency response alone does not make 10- and 20-year replacement counters.
- **Replacement controller:** event trigger generates a pulse of specified total injected charge to the total accumulator and resets the equipment age/state, possibly with coupling to other systems.
- **Efficiency/aging:** a controlled source for `e_oper(t,x_aircon,x_pipe,...)`; after replacing air-conditioning, the operational current may change because device efficiency changes. Include carbon factors and refrigerant state explicitly where modeled.
- **Large refurbishment:** can replace multiple items at once; event precedence and coalescence prevent accidental double counts. Need distinguish 'repair' from 'replacement', and actual event time vs evaluation-window bookkeeping.
- **Terminal term:** original horizon-dependent synthetic model may have `C(T)=M([0,T])+Z(T)`. In general `Z(T)` is not identified by an actual-time current trace and may need a horizon-dependent terminal adjustment/readout network. Never claim that differentiation of `C(T)` reconstructs real-time emission schedule uniquely.

## Pilot: different cycles
For an **illustrative** model, air-con period `c_A=10` years; pipework `c_P=20` years; initial construction emissions `G0`; annual operation rate `r`; replacement charges `A_A` and `A_P` with **invented** values. Use both:
1. **Independent timing nodes** for each piece of equipment (threshold/reset); one total charge accumulator.
2. **Direct mathematical oracle:** `G(t)=G0+rt + A_A N_A(t)+A_P N_P(t)`, using exactly the same event inclusion rule.

At year 20, both triggers may fire. Declare whether year-boundary events are included (`<` vs `<=`); compare left limit, exact time, right limit. A large renovation at 20 can replace both and suppress individual charges if its emissions account for the same works. No silent double-counting. Introduce efficiency shifts as a second pilot, not by altering oracle retroactively.

## What does/does not follow from circuit reduction
- With shared voltage and suitable connection, ideal parallel capacitors yield `C_eq=sum C_i`; series yield `1/C_eq=sum 1/C_i`. These are electrical relationships, **not** automatically a reduction of equipment-specific ages or CO2 sources.
- Sum of multiple carbon-equivalent currents by KCL is mathematically legitimate with common scaling.
- A single capacitor suffices for the **observable sum** if all source currents and event schedules are already specified. It generally cannot replace the separate states required to *generate* those schedules.
- Explore network/state-space reduction (minimal realization, observability and event-state equivalence), not only `C_eq`; prove which observables and event times remain invariant.
- Compare the mapping to existing event-driven sums, integrator systems and hybrid automata; describe novelty honestly and independently verify claims.
