# VERDICT — DRAFT (builder self-assessment; NOT a verdict)

The verdict belongs to the independent verifier (`circuit_first/verification/`). The V1 verdicts on stage A are in
`verification/VERDICTS.md`. This draft lists the builder's own block levels for stages A + B so they can be checked.

| block | level claimed | basis | stage-B evidence |
|---|---|---|---|
| crossbar v2: ±V factor rails, passive rail×conductance terms, stages only for products that must be voltages, summing junctions | P0 (rails, R) + P1 (stages/junctions) | Ohm, KCL; op-amps S 3 393 → 1 593 (L1 bound 1 462, gap 131 = both-polarity expressions), 0 inverters | S3a max 9.2e-16 |
| pot segments for 1/(1−w), r/(1−r), (1−η) | P0 | complementary pot segments | — |
| taps (crossbar outputs into the core) | P0 by substitution | stiff ideal op-amp outputs as sources (D12; merged run NOT_RUN) | — |
| stage buses, readout buses | P1 | integrators (accumulator sink = solving strategy) | — |
| packets (initial, terminal readout, renewal, B5, negative one-year) | P1 + H | Δq = C·v, phase sequencers | S3a/S3c |
| clocks, explicit comparators, time base, shared look-ahead P, refrigerant early comparators | H | comparators, latches, counter; booleans only | event counts equal |
| year banks / MDAC / decoders | P0 + H | switched conductances selected by the counter | S3b |
| electricity net purchase | P1 + ideal diode (P0) | KCL, VCCS, diode clamp | S3b; diode mutation detected |
| ρ split with ι_B2 steering | P1 + static switch | charge conservation | S3b, ι subsets |
| year cell (B3) | H | flying capacitor, negative packet, S/S′/P booleans | S3c B3 5.9e-14 |
| refrigerant device (B1) | H | integrator, sample-hold, constant leak/drain, packets, reset | S3d 3.4e-15 |
| adapter | h = 0.029–0.061 (GREY = composite fraction sums, EPD date, grid step order; no element value grey) | `results/stageB_S3e.json` | PARTIAL band (0.02 < h ≤ 0.25) |
| readout | γ × charge, sums over ι | — | — |

Stage C: V2-D1..D5 fixed. All stage-B comparisons were re-run with crossbar v2: C(T) ≤ 1.1e-14, coverage 1.0,
and 30 runnable edge scenarios ≤ 2.8e-14. The merged single-netlist test passes on a tiny building (AC, EV, REF).
The full-building template is NOT_RUN.

Self-assessment:
* Overall level **H** (limited hybrid). No F block was found by the builder.
* Coverage is 1.0 of |C(T)| on 5 buildings × 10 T, inside 1e-9.
* By architecture §6 the result would be **PARTIAL** only because h > 0.02, which is entirely composite and EPD
  predicates. Another reason is that the full-building N_max template is NOT_RUN.
* Control that h does not count is substantial: thousands of sequencer phase steps and tens of thousands of W2
  look-ups (STATUS.md census).

NOT_RUN: full-building N_max template, merged crossbar+core run, in-band values, AGG ratios, decision/reference units,
SPICE, Math7.
