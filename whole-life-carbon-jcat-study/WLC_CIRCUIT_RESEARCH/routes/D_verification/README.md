# Route D — independent verification / falsification

Owner: `wlc-verifier`. Status: `STATUS.md`. Per-claim verdicts: `VERDICTS.md`. D's own evidence-classed findings: `claims.md`.
All data are **fictional** pilot fixtures (07 P0/P1/P2/Px, architecture §1.2). Agreement here says nothing about real-building emissions.

## Independence rule
- `code/oracle_d.py` (stdlib, `fractions.Fraction`) does **not** import route code and uses a different algorithm from the routes: it builds an explicit **event ledger** by integer stepping `τ = r + k·c` from each reset time, applies P1 supersession as a set difference, and evaluates `G(t) = G0 + ∫rate + Σ{amount : event included at t}` with the inclusion predicate of the convention (`right` τ≤t, `left` τ<t, `orig` τ<t(1−ε), ε=1e-9). No floor/ceil and no clock integrators. Exact one-sided limits are computed with effective jump times τ (right/left) or τ/(1−ε) (orig).
- The check scripts import only `oracle_d` and read route outputs as JSON data.
- `code/probe_routes.py` is the **only** module that loads route A/E code (read-only, `importlib`, bytecode off). It is a falsification harness, not part of the oracle.

## Units and conventions
kgCO2e, t in years. The orig convention is a horizon rule for C(T), applied only to P0 data; P2/Px under orig are undefined (raise). G0 is present at t=0 under every convention. Route E fixture: R=3 Ω, I0=2 A, κ=1/3 kgCO2e/J (synthetic), 1 s ≙ 1 yr; joules become kg only through κ.

## Files
| file | what |
|---|---|
| `code/oracle_d.py` | ledger-sweep oracle, exact limits, naive-sequential counterexample model |
| `code/check_boundary.py` | boundary table, exact limits, closed band, row-by-row comparison with A/E `points.json`, float slip-through |
| `code/check_events.py` | P1 ledgers, order shuffles, naive sequential orders, restart probe (τ_R=15), P2 alternatives |
| `code/check_states.py` | merged clocks (all periods), Px periodicity/transients, online-reset futures, 2-continuous-state realization, single accumulator |
| `code/check_joule_ac.py` | exact Joule cross-term bookkeeping (equal/unequal/misaligned/interleaved/Walsh), X1, zero-mean AC, rectified clocks with phase, E bound search by quadrature, H-E4 |
| `code/probe_routes.py` | route code vs oracle on 1e5 + 2e4 points; latent-defect probes |
| `code/bench.py` | gate-4 benchmark (a) closed form, (b) knots+bisect, (c) D's hybrid circuit, (d) fixed-step |
| `code/run_all.py` | regenerates every `results/*` file |
| `tests/test_d.py` | 17 unittest cases with hand-written expected values |

## Reproduce (no network)
```
cd whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/routes/D_verification
PYTHONDONTWRITEBYTECODE=1 math7-py -B -m unittest discover -s tests -v   # 17 tests
PYTHONDONTWRITEBYTECODE=1 math7-py -B code/run_all.py                    # ~2.5 min, writes results/
```
Dependencies: oracle, events, states, bench: Python 3.13 stdlib only. `check_joule_ac.py`, `check_boundary.py` (E's AC rows) and `probe_routes.py` (E's modules) need math7-py (mpmath 1.3.0; SymPy 1.14.0 via E's code).
