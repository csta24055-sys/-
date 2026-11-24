# VERDICT — DRAFT STUB (builder self-assessment, stage A only; NOT a verdict)

The verdict belongs to the independent verifier (`circuit_first/verification/`). This stub only
lists the builder's own block levels for stage A so the verifier can check them.

| block | level claimed by builder | basis |
|---|---|---|
| rails, flow resistors | P0 | DC sources, Ohm |
| stage buses (virtual-ground integrators) | P1 | nullor + capacitor |
| amount packets | P1 (switched capacitor) + H (phase sequencing) | `Δq = C_sV₀` |
| clocks, time base, explicit events, lookahead | H | comparators, latches, counter; booleans only |
| repair amplitude (`e0·r`) | P1 | two op-amp Ohm stages |
| year cell (exclusion rule) | H | flying capacitor, negative packet, boolean S/S′/P |
| age (degradation) | P1 + H reset | integrator + short switch |
| adapter | h = 0 in all stage-A scenarios (GREY = 0) | `results/*_counts.json` |
| readout | γ × charge, sums | — |

Overall stage-A self-assessment: **H** (limited hybrid) for the pilot and CF3 behaviours; no F
block detected by the builder. Stage B (full synthetic building, oracle comparison) is NOT_RUN.
