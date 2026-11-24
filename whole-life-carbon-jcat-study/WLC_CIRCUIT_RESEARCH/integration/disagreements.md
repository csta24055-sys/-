# Disagreements, refuted claims, open boundaries (G4)

Status words used below:
- RESOLVED: settled by an independent execution.
- OPEN: no adjudicating evidence yet.
- BOUNDARY: a documented zone where the models are not defined or not compared.

## 1. Event boundaries
1. **Three conventions** (right τ≤t, left τ<t, orig τ<T(1−ε)). These are declarations, not errors.
   - Right and left differ only at T=nc. Left and orig differ on (nc, nc/(1−ε)]. Right and orig differ on the **closed** band [nc, nc/(1−ε)].
   - Architecture §1.2 wrote the band half-open. That is refuted (ERRATA #1, D-4). RESOLVED.
   - Under orig, the Φ device is a horizon readout: the clocks are slowed and the ramp is not. P2/Px under orig are **undefined**. A, D and the integration all reject them. BOUNDARY.
2. **Float knife edge** T = 10.00000001. The exact rule excludes the event; the float rule counts it (fl(10/(1−ε)) = sw(10) is 0.46 ulp above the real endpoint, so the closed real endpoint has no float representative).
   - A-5, D-5, D-28. The integration's X2 link compares at the same float T and gets 0.0 difference, including fl(10/(1−ε)) ± 1 ulp. It does not assert decimal-vs-float behaviour.
   - Recorded as an undefined zone. BOUNDARY.
3. **Float slip-through for non-integer periods.** c=0.1 gives floor(t/c) ≠ n at 196/600 event instants (D-5). P0's integer periods hide this from every route test, including ours. OPEN (no non-integer-period pilot exists).
4. **Refrigerant band (K, sw(τ))**:
   - msp's interval form deviates from refcalc there, by up to 1.24 relative for B1-04 (D-21).
   - The late-reset automaton matches refcalc inside the band (B: 4 scenarios; D: 2 scenarios).
   - 03 §5.4 writes the open band; 03 §3.4 excludes the closed (K, sw] conservatively from 𝒟′.
   - B1-02 [P1 cells] in the band is 8.9e-10 from refcalc on EV6, close to the 1e-9 tolerance, and is not relied upon.
   - The integration grid has no band points. Recorded as a documented unresolved boundary of the original (not a defect). BOUNDARY / OPEN for more scenarios.

## 2. Encodings that agree in value but differ in content
4. **P1 "substitute"**:
   - **A and D** (and the integration) use ledger supersession: the renovation at 20 removes AC@20 and PIPE@20, so S(20) = {AC@10 20, RENOV@20 50} = 70.
   - **E** lets the clocks fire at 20 and adds a **net −5** table entry: 20+20+35−5 = 70.
   - The totals are equal at every tested point (D p3 (7), 0 mismatches). The ledger content differs.
   - E's encoding cannot express per-ledger readouts or a **non-coincident renovation restart** (P1′, τ_R=15: AC → 25, 35; pipe → 35, 55). The integration implements P1′ and matches D-7.
   - Integration choice: supersession. E's net −5 stays an accepted *value* encoding, with the condition D attached. RESOLVED (documented choice).
5. **State 4-tuples depend on the counting rule.** A's R1 P1 is (3,0,3,1); E's is (4,0,3,1) (meter + register), and the merged form is (3,0,3,1). Tuples are only comparable for a fixed readout class (A-19 note). None is claimed minimal. RESOLVED (convention stated).

## 3. Refuted or corrected claims (kept as findings)
| claim | outcome | evidence |
|---|---|---|
| H-A3 "Px needs (3,0,2,0); single clock impossible" | REFUTED for a known schedule (one period-20 clock, 3 comparators); the online-reset part ≥2 continuous is [H] (D-9, unreviewed); A's 3 continuous are not minimal (D-10: 2 clocks + 2 counters) | ERRATA #2; D-9..D-11 |
| A-16 rectified clock "c/h ∈ ½ℤ" | Phase-dependent; the bound dispute was settled in **A's** favour (0.21051h general φ); D withdrew its m·h/2 for general φ | D-16 (corrected), p3 |
| D pass-1 sub-note on zero-mean reset-to-zero clock | **Withdrawn** (A right: 3 / 3 / 30) | p3, D-15 corrected |
| H-E2 "cross term 2√(20·35) width-independent" | Only for equal aligned windows; general form 2√(AiAj)·ρ | D-12; E-2b revised |
| Architecture early stop (2) "drop the single shared resistor" | REFUTED: interleaved or Walsh-orthogonal pulses are additive at readouts outside windows; exactness at every t is impossible under a DC operating current | ERRATA #5; D-13; E p3 (6b) |
| E "fixed-step dt=1e-3 max err 3.1e-10" | Withdrawn: true fixed-step integration misses a full 20/55 kg at event instants. E's 2/0/0 and D's 75/9/7 differ only by point-set size and query rule | p3 (8) |
| E STATUS "P1 reproduced by circuit" (batch 1) | Was the closed form. Fixed: implemented in `circuit_e.py` | p1, p3 (7) |
| H-B4 refrigerant "stores less state" | REFUTED as a metric artefact (unmerged table). Merged knots 1,025 (D/canon) or 1,063 (B's count) vs automaton 1,072; time–memory trade-off | ERRATA #9; D-23; B restatement confirmed by D pass 4 |
| H-B2 "passive RC cannot…" | Must say lumped **LTI** with analytic sources: switched and ideal-diode passive networks reproduce kinks and jumps; the class labels are relative to 𝒢 | D-24 (not reviewed by B) |
| H-C3 "14 stages need 7 signals" | Scenario-dependent (6/6/7); rank = number of T-varying stages; rank ≠ state | ERRATA #6; D-26 |
| H-C2 "7 types cover DIRECT 21" | Covering, not partition (23 memberships); B2-01 labelled year_cell (C) vs K21 gain × cells (B) | ERRATA #7; X3 |
| Architecture §1.2: float points 10.000000005 / 10.00000002 are "inside 𝒟′" | Both are in `valid_domain`'s knife window when an event at 10 exists; Φ-only points | ERRATA #8 |

## 4. Open disputes and unresolved items
- **B merged-knot count 1,063 vs D canon 1,025.** D pass 4 confirmed this is a count definition: B counts B1-04 in jump form (60 event knots), canon in interval form (41). Both are the same order as the automaton's 1,072. RESOLVED (D p4 B #1).
- **Unreviewed [H] items:** D-9, D-10 minimality, D-16 closed form, D-24, D-12 (re-derived by E, no formal review), A-3/A-6/A-10/A-16 general statements, the E Walsh cost estimate, E-3c. None is promoted. OPEN.
- **B and C fix passes after D pass 2.** D pass 4 confirmed them (`routes/D_verification/VERDICTS.md` pass 4 §5). Confirmed for B: the H-B4 restatement (1,063; 343× / 56×), the H-B2 ramp column and LTI scope, the band wording, the K19 totals and the EV3/EV11 assertions. Confirmed for C: the full time-form text (0 mismatches over 70 rows) and the [H] column. B is ACCEPT, with H-B1 overall PARTIAL; C is ACCEPT, with the constructs [H]. RESOLVED.
- **Untested edge in the composed Ψ code (D pass 4 minor).** `code/psi_compose.py:53-55` takes the B2-01 share from `scn.operation.facility_management_ratio`, with its own [0,1] check, not from msp's `b21.share`. It matches refcalc on every tested scenario (EV2, EV9; D: EV0, EV7), but no scenario with a missing or out-of-range share was tried. OPEN (untested).
- **Consolidated open items** for the whole study: see `routes/D_verification/VERDICTS.md` pass 4, table "Consolidated open items". It is referenced here, not duplicated.
- **timechar docstring** writes M([0,T)), while `RT.M` counts sw(τ) ≤ T (closed, 03 §7). Documentation inconsistency in frozen code; not edited. OPEN (record only).
- **Ledger vs refcalc dependency lists differ** for A13-03, X-05 and X-07 (C observation). The SUM-03 closure is unchanged. OPEN (record only).
- **C(T) kinds beyond SUM-03:** K26/K28/K30/K32/K33 are NOT_RUN, so H-B1 stays PARTIAL.

## 5. Integration's own errors (found and fixed in this pass)
- **X5 derivative check, first run:** at EV9, T=47.9 the forward difference with h=1e-6 straddled an atom of M in (47.9, 47.9+1e-6] and reported dC/dT ≠ ρ+Z′.
  - Diagnosis: with h=1e-8 or a backward difference the identity is exact.
  - Fix: the step is now chosen as the largest h ∈ {1e-6, 1e-8, 1e-10, 1e-12} whose interval holds no atom (M(T+h)−M(T) = ρh); `h_used` is recorded.
  - A test asserts that the step was reduced at 47.9. This is a test-design error, not a model defect.
- **`ops` counters** accumulated across repeated benchmark runs (first benchmark: 140,063 "segments" for 7 sweeps). They are now reset per sweep; the published `benchmark.json` is from the corrected code.

## 6. Category boundaries (must not be crossed)
- Φ G(t) and Ψ C(T) are different quantities. dC/dT is not an emission rate (TH-4a; X5 shows Z′ < 0). The Φ pilot is not a reduction of the 70-unit model.
- Joules ≠ kgCO2e without the explicit synthetic κ. Capacitor energy Q²/2C ≠ carbon. Resistor temperature ≠ cumulative energy (E-1t).
- A rank is not a state count. A smaller tuple that loses future events is not a reduction (merged clocks, replay counterexample).
