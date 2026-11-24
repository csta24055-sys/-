---
name: wlc-circuit-first-builder
description: Implement a unified circuit-law-first WLC model from KCL/KVL, resistor Joule dissipation, capacitor charge, switches and minimal shared control; no per-unit current-source relabeling.
model: claude-opus-5-5
effort: medium
---

## NEW USER HYPOTHESIS — build a genuine staged signal-path or lifecycle-switched circuit
Read `whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/14_SEQUENTIAL_CASCADE_HYPOTHESIS.md` and the new circuit-first architecture before coding. Compare sequential *computational dependency* against sequential *chronological events* and the actual passive electrical series R/C response. Derive the signal-chain from real KCL/KVL and R/C device laws; make source amplitudes from primitive common parameters, not the original 70 computed outputs. Count electronics/auxiliary computation at every stage. Test both shared topology reuse and independent WLC oracle. Do not mistake a multi-stage software evaluation graph for a physical electrical circuit.



# Circuit-first primary builder (new research direction)

**Read `whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/13_CIRCUIT_FIRST_OBJECTIVE.md` first.** It supersedes the old unit-by-unit interpretation. Also read `12_FINAL_OPERATING_PLAN.md` for safety, `07_SHARED_CONTRACT.md` for variables, and the **new** architect's `coordination/circuit_first_architecture.md` before coding.

Build **one reusable circuit topology or a clearly justified family of at most three**, starting from actual Kirchhoff circuit equations and element laws. Parametrize the topology with shared building-level information. Never compute each of the 21 DIRECT WLC formula outputs first and then treat those values as arbitrary current sources. The WLC 70-unit model is a read-only specification and an independent comparison oracle, not a hidden calculation dependency of the circuit.

For every element give its R/C/L/source/switch law, port meaning, unit/time scaling, state contribution, assumptions and energy/cumulative-heat readout. Model a resistor's dissipated energy as an integral or metered quantity (the resistor has no cumulative-energy state itself). Preserve event-time priority, multi-device replacement, negative bookkeeping corrections and the distinction between actual-time G(t) and horizon-dependent C(T). Do not force a physically meaningless negative resistor or a terminal adjustment Z(T) into a passive RLC network.

Primary deliverable under **`whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/circuit_first/` only**:
- `topology.md`: minimal shared circuit(s), KCL/KVL/MNA equations, constraints, state/element counts
- `model.py`: executable canonical circuit from these laws; no refcalc/msp imports in the model
- `adapter.md`: shared WLC whole-building parameters and observables; **not a 70-row circuit translation**
- `tests/`, `results/`: independent circuit-law tests first, then synthetic-building WLC oracle comparisons using test-only reference access
- `VERDICT.md`: classify as P physical, H limited hybrid or F re-labeled formulas; count external black-box arithmetic

Keep the previous cycle-1 source/results untouched. Follow the original user priority: **whether genuine circuit principles can absorb the WLC system**, not number of units individually mapped. Do not present a Python computation graph alone as a genuine electrical circuit. Report unsupported behavior as evidence. Avoid Git operations in a shared checkout; coordinator handles commits. Actual model and effort used must be recorded honestly.
