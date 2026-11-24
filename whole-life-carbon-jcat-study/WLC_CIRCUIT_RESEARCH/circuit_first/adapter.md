# Adapter: primitive inputs → element values, wiring, observables (stage A)

Not a per-unit circuit list. The adapter (`adapter.py`) maps whole-scenario primitive inputs
onto the fixed cell catalogue of `topology.md`. All data values are wrapped in the counting
type `Tracked`; every arithmetic operation on them is counted (W1 or GREY), predicates (W3),
key matches (W2) and enumerations (W4) are counted separately. The adapter has no `while`,
no `range`, no floor/ceil (checked by `tests/test_audit.py`), computes no event time, count,
year, or amplitude×count, and imports no reference code (AST check).

## 1. Input schema (stage A synthetic scenarios; fictional data only)
| input | meaning | → element value / wiring | op |
|---|---|---|---|
| `initial[].amount` A | amount at τ = 0 | packet cap `C_s = A/(γV₀)` on the rail, triggered by power-on | W1, W3 (A>0), W4 |
| `flows[].rate` r | constant rate per year | conductance `G = r/(γ τ_y V₀)` rail → stage bus | W1, W3 (r≥0), W4 |
| `flows[].rate_after`, `switch_on` | rate after the first renewal of an item | second conductance + switch pair on an SR latch set by the item group's renewal | W1, W2 (flow→item) |
| `flows[].degradation{item, slope δ}` | rate grows ∝ age since last renewal | age integrator (constant) + `G_δ = δ/(γτ_yV₀)` from its output | W1, W2 |
| `items[].amount` A | replacement amount | packet cap `C_s = A/(γV₀)` | W1, W3, W4 |
| `items[].period` c | service period | clock cap `C_j = c·G_uτ_y` and reset cap `= c·G_uτ_y` | W1 ×2, W3 |
| `items[].explicit[]` τ_e, `explicit_policy` | explicit (early) replacement years; `restart` restarts the period | reference source `τ_e·V₀`; restart → short switch on the clock | W1, W3 |
| `items[].repair{base e0, rate r}` | repair flow `e0·r` per year, excluded in years with a renewal of the item's group | conductances `e0·G_u`, `r·G_u` (two op-amp stages realise the product) | W1 ×2, W3 ×2 |
| `renovations[]{amount, years, replaces, policy}` | renovation; `substituted` renews the listed items (their packets suppressed at that instant, clocks restarted), `additional` leaves them | explicit comparators + packet; wiring to groups | W1, W2, W3, W4 |
| `stage` labels | observed stage of each row | wiring row → stage bus | W2 |
| convention `right/left/original` | readout ordering, ε | `ε` in the ramp slopes and the lookahead divider; readout priority | constants |
| units `γ, V₀, τ_y, G_u` | defined simulation scalings (not physical carbon–electric conversion) | appear only as constants in W1 | — |

Grouping (W2): items share one clock / event group iff the key
`(period, explicit years, explicit policy, substituting renovations)` is equal. This is key
equality, not arithmetic; it is the only place where rows are merged.

## 2. Observables
* `C(T) = γ Σ_s q_s(T)`, stage values `S_s(T) = γ q_s(T)` (bus + year-cell capacitor charges);
  `Z(T)=0` in stage A, `M([0,T]) = C(T)`.
* event log: per item, the instants at which its packet sequence started (from the engine's
  event log), in years; per group, the year each renewal belongs to = ticks so far + 1 − P (boolean log).
* audit: data-path heat vs `V₀·Q`.

## 3. Measured operation counts and hiddenness (`h = W_out/(W_in+W_out)`)
| scenario | W1 | W2 | W3 | W4 | GREY | W_in (data elements + KCL adds + comparators + switches) | h |
|---|---|---|---|---|---|---|---|
| pilot (any convention, any units) | 8 | 2 | 8 | 4 | **0** | 49 (8 + 25 + 4 + 12) | **0** |
| CF3 "full" (repair, explicit, degradation, efficiency switch, renovation) | 16 | 4 | 15 | 7 | **0** | 114 (16 + 59 + 6 + 33) | **0** |
Sources: `results/pilot_audit_counts.json`, `results/cf3_catalogue_counts.json`.

Grey-operation list: **empty** for all stage-A scenarios. Places where grey operations would
appear in stage B (to be counted, not hidden): factor-ID lookup with fallbacks, unit conversion
chains with ≥3 factors (need an extra op-amp stage each by L1), `1−x` / ratio inputs.

`.value` extractions in `adapter.py`: 9 occurrences, all inside the counting machinery
(`Tracked` arithmetic, `Builder.val` which counts a data element, W2 key, W3 predicates).
Listed for the verifier's bypass search.

## 4. Not covered in stage A (NOT_RUN)
Factor rails and derived rails, multi-factor amplitude rows, year banks / MDAC, diode
rectification of net purchased energy, `ρ` split B2⇄B6, refrigerant cell, terminal packets
`z_s`, `ι` switches, ratio readouts, N_max same-netlist padding.
