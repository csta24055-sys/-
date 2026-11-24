# claims — route C

Evidence classes per `07_SHARED_CONTRACT.md`: [P] proven in a declared domain, [E] exact sample checks,
[F] floating-point numerical tests, [H] hypothesis.  No claim of novelty; no real-building accuracy.
Domain: fictional synth scenarios, `0<T≤60`, inside `tstudy.scenarios.valid_domain`, original event rule
`τ < T(1−ε)`.  Source: branch `claude/wlc-equivalent-circuit-20261124` @ `5a2f898`.

| # | Claim | Class | Evidence |
|---|---|---|---|
| C-0 | units70.json has 70 units equal to the refcalc registry; roles DIRECT 21, AUX 15, DEC 9, REF 10, AGG 9, BRK 6; COMP 22 rows over 21 units; only non-trivial row (B2-01, B6, −1, ι_B2). | [E] (exact count of data) | `results/inventory.json` |
| C-1 | The 22 COMP rows from units70.json, as one weighted summing node per stage plus one total node, reproduce refcalc SUM-03 and X-02 by_stage within rel 3.6e-16 (105 cases, 5 scenarios, 6 stage subsets, 7 T). | [F] | `results/hc1.json` |
| C-1n | Treating the 21 DIRECT units as 21 independent +1 sources is wrong by exactly B2-01/C (0.14–3.7 %). | [F] | `results/hc1.json` |
| C-2 | Each of the 21 DIRECT units' V(T) is consistent with the block types named in its ledger time_form (7 types; B1-03 and B3-01 need two); none fits no type. | [F] (weak for B1-03, B1-04, B3-01) | `results/hc2.json` |
| C-2r | An annual table read at T=60 replayed through a pure year-cell integrator reproduces B1-02 exactly but not B1-03, B3-01, B4-02, B5-01: event times inside a year must be kept as comparator thresholds (state preservation). | [F] | `results/hc2.json` by_year_replay |
| C-3 | Rank modulo constants: total 1; 14-stage vector = number of T-varying stages (6, 6, 7 in S, M, edge); 21 DIRECT 7/8/9. The number of independent waveforms depends on the observable. "70 capacitors" and "21 capacitors" are both not what the data need. | [F] | `results/hc3.json` |
| C-3x | The architecture's "7" for the stage vector is scenario-dependent (fails on benchmark S and M where B5 is constant). | [F] counterexample | `results/hc3.json` |
| C-4 | No DECISION, REFERENCE, BREAKDOWN unit (and no AGGREGATE except X-02) is in the refcalc dependency closure of SUM-03; adding a representative of each non-DIRECT role as a source double counts (A5-01, B3-02, SUM-03, X-07) or is dimensionally void (SYS-01, B4-01). | [F] (closure: [E] structural) | `results/hc4.json`, `results/inventory.json` |
| C-5 | Circuit constructs, classes a–e and state 4-tuples per unit in MAPPING.csv. | [H] | `MAPPING.csv`, `code/build_mapping.py` |
| C-6 | Constants placed at t=0 (A stages) vs t=T (C stages) cannot be told apart from V(T); the distinction exists only in the Φ reading. | [F] for indistinguishability on the grid; placement itself from ledger text | `results/hc2.json` note |
