# 07 Shared research interface: terms, route outputs and comparison gates

## Canonical quantities (do not conflate)
- `t`: elapsed physical time under explicitly specified origin, units years unless transformed.
- `T`: WLC evaluation horizon. Existing time-dependent `C(T)` need not equal realized emissions `G(t)` at `t=T`.
- `G(t)`: actual-time cumulative kgCO2e, when schedule is specified.
- `C_WLC(T)=M([0,T])+Z(T)`: original horizon-dependent research model in its restricted domain; terminal `Z(T)` may not represent a physical-time emission at `T`.
- `gamma>0`: kgCO2e per coulomb, a **defined simulation scaling**, not a physical carbon-electric conversion.
- `Q(t)=G(t)/gamma`; `I_Q=dQ/dt` on intervals without events. At events use current impulses (distribution) with integrated charge `Delta Q=A/gamma`, or finite pulses of equal area.
- `C_cap>0`: electrical capacitance, `V=Q/C_cap`. `C_cap` is not the same symbol as carbon `C_WLC`. With constant I, V rises linearly; `P=V I` and `E=Q²/(2 C_cap)` are different.
- `H`: time horizon in supported synthetic model; `H(x)` in a Heaviside expression needs unambiguous notation, preferably `Theta(x)`.
- Periodic replacement counts use the original research's event-inclusion convention when comparing to original `C_WLC(T)`; for a separately declared right-continuous physical-time pilot, state `tau<=t` and compare left/right limits.
- A sawtooth may appear as a **residual in the decomposition of periodic event counts**, not as the necessarily declining total cumulative emissions. Avoid conflating ramp+stairs with a resetting sawtooth.

## Resistor-energy route E comparison
- `p_R(t)=i(t)^2 R` is instantaneous Joule dissipation power (W).
- `E_R(t)=∫p_R dt` is dissipated energy (J), not resistor temperature or capacitor stored energy. At constant current/resistance it rises linearly with time.
- With `i(t)=sqrt(2) I_rms sin(ωt)`, `E_R(t)=I_rms² R[t−sin(2ωt)/(2ω)]` for zero initial energy and phase zero. The AC ripple term is bounded; average energy growth is linear over full periods.
- To map energy to emissions use a specified and dimensionally consistent `EF(t)` (kgCO2e/J or converted from kgCO2e/kWh); resistor energy is only a synthetic proxy unless matched to actual electricity demand. Avoid falsely requiring DC rectification for resistor Joule heating.
- Resistor dissipated energy requires an external cumulative readout/measurement. If an approach outputs only instantaneous power it has not calculated cumulative WLC.
- Routes A (capacitor charge) and E (resistor energy) are deliberately competing formulations; both must be validated, not conflated.

## Controlled comparison cases
- Pilot set P0: `G0=100` kgCO2e, `r=4` kgCO2e/year, 10-year AC-equipment events of 20 kgCO2e, 20-year pipework events of 35 kgCO2e (all illustrative).
- Test elapsed years: 0, 1, 9.999999, 10, 10.000001, 19.999999, 20, 20.000001, 30, 40, 60.
- Pilot P1: renovating at year 20 includes both replacements; state explicitly whether charges are substituted or additionally incurred. Test both distinct policies with clear accounting.
- Pilot P2: operational rate changes after AC replacement; independently specify before/after rates, event precedence and whether T counts event at exact boundary.
- Original 70-unit synthetic model is a separate, more complex benchmark; its inputs and domain MUST come from `WLC_THEORY_RESEARCH_BASE`, not from the simplified P0.

## Route output contract
Each route owns `routes/A_waveform/`, `routes/B_formula_network/`, `routes/C_70_units/`, or `routes/D_verification/`, or `routes/E_resistor_energy/`, respectively. It writes:
- `STATUS.md`: research question, source branch/commit, precise current status, completed tests, counterexamples, blockers, next actions.
- `README.md`: conceptual/mathematical summary, domain and units.
- `code/`, `tests/`, `results/`: executable synthetic test models, independent fixture results, test commands and dependencies.
- `MAPPING.csv` or `MAPPING.json`: where applicable; clear `source_path`, `claim_or_unit_id`, `target_circuit_construct`, `status` (exact/conditional/approximate/unsupported/unverified), `validation`.
- `claims.md`: [P] proven in a declared domain, [E] exact sample checks, [F] numerical tests, [S] statistical, [L] cited literature, [H] hypothesis. New independent proofs require an independent review before [P].
Artifacts may be partial; state no-test vs pass. Do not create success badges without actual execution.

## Cross-route merge protocol
The coordinator makes a separate `integration/` directory containing:
- `coverage.md`: which observation/identity is covered by A/B/C/E and by D's independent tests.
- `disagreements.md`: conflicting assumptions, counterexamples, unsolved boundaries.
- `composed_model.md` and `code/`, `tests/` ONLY if equivalent on an explicitly declared common domain.
- `benchmark.md`: direct Sigma/knots baseline vs circuit path, memory/time/operations/state count. If smaller state count means lost information, do not count as successful reduction.
- `next_experiments.md` with reproducible next experiments, not generic speculation.
No integration before source-version and unit conventions align. Maintain provenance down to the specific branch/file/claim.
