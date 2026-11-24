# G4 composed model (fictional data only)

Branch `claude/wlc-equivalent-circuit-20261124` @ `2ae99ce`. Integrator model, self-reported: `claude-opus-5-5`. Effort cannot be observed from inside the session (High was requested).

There are **two different models**, joined by **one identity**. The Φ pilot (P0/P1/P2) is a toy physical-time model with 2 items. The Ψ model is the original 70-unit horizon model. Neither one predicts the other. Their numbers are never overlaid. This model makes no claim about real buildings, novelty or energy saving.

```
 Φ (axis = physical time t)                   Ψ (axis = evaluation horizon T)
 ─────────────────────────                    ─────────────────────────────────
 r(t) ─► [charge: I_Q=r/γ → Q]  ─┐            21 DIRECT signals V_u(T) (B's 𝒢 netlists)
      └► [joule: κI²R → meter] ─┤ readout G   ──► gain σ·β per COMP row (22 rows, units70.json)
 clocks x_AC, x_PIPE ─ comparators ─► set rule│   ──► stage summing nodes ──► total node C(T)
 external events (renovation) ───────────────►┘
                         bridge (Ψ only):  C(T) − M([0,T]) = Z(T)   (canon/timechar, exact)
```

## 1. Declared common domains
| part | domain | arithmetic | oracle (not the composed code) |
|---|---|---|---|
| Φ | P0, P1 (substitute/additional, renovation at 20), P1′ (renovation at 15, declared here), P2, Px; t ∈ [0, 60], plus ε-shifted knife and limit points; conventions right, left, orig (orig only for P0/P1) | `Fraction` (exact) | route D `oracle_d.G` (rational event ledger); route A `results/points.json` (data, 595 rows); hand literals from 07 §5 / architecture §1.2 |
| Ψ | evaluation_set EV2 `SYN-S-school-S-T100-seed990107243` and EV9 `SYN-RC-hospital-M-T30-seed571520556`; EV9 without B2 for β=ι_B2. No route used these scenarios. 0 < T ≤ 130, (scenario, T) ∈ `valid_domain`. Original rule τ < T(1−ε). | float | refcalc SUM-03, X-02 by_stage and the 21 DIRECT unit values; canon KF for X5 |
| bridge | EV9 (B1 included), 5 horizons | exact for canon; float for the composed C | canon/timechar (frozen ch. 17) |

These are **not** in the domain: the float knife window (relative 1e-10 to 1e-8 around event times), P2/Px under orig (undefined), AC currents, EF switching, Joule pulses for events, SUM-05 (division by T), the K26/K28/K30/K32/K33 kinds, and scenario L.

## 2. Φ side: `code/phi_hybrid.py` (thin INDEPENDENT re-implementation)
This module imports no route code. It is one hybrid automaton with two interchangeable realizations of the same operating term:
- **charge** (A's R1 construct): Q(0)=G0/γ, I_Q=r(t)/γ, each event is a charge impulse ΔQ=A/γ, and G=γQ. V=Q/C_cap and E_cap=Q²/2C_cap are reported, but neither is carbon.
- **joule** (E's E-R1 construct): the source sets I² so that κI²R=r(t). A meter integrates I²R; the resistor stores nothing. G0 and the events are **external additions** S_ext, and G=κE_m+S_ext. Events are not implemented as Joule pulses: on one resistor, pulses add a cross term 2√(AiAj)·ρ (E-2b, D-12).
- **Shared:** one reset clock per item (rate 1/c, comparator at 1); external events with a declared restart set; a **set rule** at each instant (collect all due events, remove superseded clock events as a set, then add amounts and apply restarts); and a P2 latch (rate 4→3 at the first AC firing).
- **Convention parameter:** right (τ≤t); left (τ<t); orig (clock rate (1−ε)/c, external events at τ/(1−ε), strict). Under orig the ramp is not slowed, so the device is a horizon readout, not a physical-time model (A STATUS).
- **P1 substitute** uses explicit ledger supersession (A/D encoding). The renovation at 20 removes AC@20 and PIPE@20, so the ledger is {AC@10, RENOV@20}. E's net −5 table entry gives the same totals but a different ledger, and it cannot express P1′ (see disagreements §4).
- **State 4-tuples** (continuous, discrete, comparators, table) for this realization: charge P0 (3,0,2,0), P1/Px (3,0,3,1), P2 (3,1,2,0); joule adds 1 continuous state (meter + register). None of these is claimed minimal.

## 3. Ψ side: `code/psi_compose.py` (DOCUMENTED COMPOSITION)
- **Per-unit signals** come from route B `grammar.py`, loaded read-only. It is byte-identical to the version D reviewed in pass 2 (`git diff 06e0943 HEAD` is empty for this file); sha256 is in `results/*.json` meta.
  - 12 constants are DC sources (msp P1 scalars, `specs.system.CONST_VALUE`).
  - B3-01, B4-02, B5-01, B6-03 and B7-04 are kernel netlists on the msp P1 amplitude pieces, used as an external table.
  - B2-01 is a gain ρ_B2 on the EL year-cell netlist.
  - B1-02/03/04 come from the late-reset S/H automaton fed with raw inputs.
- **Composition** follows route C's rule (H-C1/X4), re-written here: one weighted summing node per stage over the 22 COMP rows in `units70.json` (σ, β∈{1, ι_B2}, excluded stages absent), then one total node.
- **B2-01 share source:** `psi_compose.py:53-55` reads ρ_B2 from `scn.operation.facility_management_ratio`, with its own [0,1] check, not from msp's `b21.share`. It matches refcalc on every tested scenario. An invalid share is untested (D pass 4 minor; `next_experiments.md` N11).
- **Why this is a composition and not a new circuit:** the kernels are B's and the summing rule is C's. Only the join, the scenarios and the oracle comparisons are new.

## 4. Bridge
Ψ only: on EV9, canon gives C(T) − M([0,T]) = Z(T) exactly (Fraction), with Z ≠ 0, Z′ < 0 and dC/dT = ρ + Z′ ≠ ρ. The composed float C(T) equals canon's C to ≤2.2e-16, so C_composed − M equals Z to ≤3.4e-15.

**The bridge does not connect the Φ pilot to the 70-unit model.** The only Φ–Ψ link executed on common data is X2: P0 recast in the orig convention. There the Φ hybrid (exact, at the same float T) equals B's θ_ε netlist on the P0 pieces at 17 T, with relative difference 0.0. The comparison includes fl(10/(1−ε)) ± 1 ulp and sw(10).

## 5. Results (all reproducible; `results/`)
| check | result | file |
|---|---|---|
| Φ vs D ledger: 19 case×convention combos × 2,118 points × 2 realizations | **0 mismatches** (exact) | `phi.json` |
| Φ vs A published rows (data) | 595/595 equal | `phi.json` |
| γ, C_cap invariance (1,1), (5,2), (1/7,3) | G(40)=410 in all three; E_cap differs | `phi.json` |
| X2 link (Φ orig vs B θ_ε netlist) | max rel 0.0 at 17 T | `x2_link.json` |
| Ψ vs refcalc, EV2 / EV9 / EV9-noB2, 18 T each, 1,926 comparisons (total, stages, 21 units) | max rel **2.6e-13** (B3-01); stage key sets equal | `psi.json` |
| Ψ with the year cells as one shared integrator (EV9) | max rel 2.6e-13 | `psi_integrator_cells_EV9.json` |
| C-1n control (21 DIRECT summed as independent +1 sources) | wrong by 0.056–1.6 %, equal to B2-01 to ≤3.3e-13 | `psi.json` |
| X5 on EV9 | 5/5 exact identity; Z′ ∈ [−5,845, −1,553] | `x5.json` |
| Mutations M1–M4 (no supersession, orig without moving external events, β ignored, no late reset) | **all detected** (305 vs 250; 250.00000004 vs 200.00000004; 1.47 %; 8.9e-4) | `mutation_check.json` |
| Unit tests | **17/17 OK** (16 s) | `results/test_log.txt` |

**Independent re-verification:** D pass 4 (`routes/D_verification/VERDICTS.md` pass 4, `results/p4_integration.json`) recommends **ACCEPT-WITH-CONDITIONS**. Φ: 353,940 fresh points, 0 mismatches. Ψ: EV0/EV7 ≤3.2e-14. X5 exact on EV7 at 6 T. Benchmark reproduced at 5.6× / ~850×.

## 6. Commands
```
cd /home/user/-/whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/integration
export PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0
python3 -B code/run_integration.py      # ~55 s -> results/{phi,x2_link,psi,psi_integrator_cells_EV9,x5}.json
python3 -B code/mutation_check.py       # -> results/mutation_check.json
python3 -B code/bench_int.py            # ~95 s -> results/benchmark.json
python3 -B -m unittest discover -s tests -v   # 17 tests
```
`tstudy.baseline.assert_frozen()` passes before any frozen import (refcalc `8976efea…`, synth `55caf5cd…`, common `ad3d0b7e…`). No `__pycache__` was found anywhere in the checkout after any run.
