# Design deviations from `coordination/circuit_first_architecture.md` (stage A)

Each item: what the architecture says, what was found, evidence, what was implemented.
Builder findings are [E] on the executed cases, not reviewed yet.

## D1 (error in §5.4) Early comparator `V_th(1−ε)²` on a resetting clock ramp is wrong for n ≥ 2
* Architecture: "属する年：同じランプのしきい値 `V_th(1−ε)²` で早い比較器が働く（`t_m=τ(1−ε)`）".
* Finding: the clock ramp restarts at the previous LATE firing `(n−1)c/(1−ε)`, so the early crossing
  of event n is at `(n−1)c/(1−ε) + c(1−ε) = nc(1−ε) + c·ε·(2−ε)(n−1)/(1−ε)` — later than `nc(1−ε)`.
  Only the first event of a ramp started at 0 is right.
* Evidence: period 2.5, original convention: the 4th event (τ=10) had its early crossing at
  t = 10.000000005 (exact `1333333332666666667/133333333200000000`), AFTER the year tick at 10, so the
  event was assigned to year 11; B3 at T=10.5 came out 7 instead of the ledger 6.5.
* Implemented: ONE shared lookahead comparator in the time base, `P = [v_year ≤ ρ·v_global]` with
  `ρ = ε(2−ε)/(1−ε)` realised by a divider on the global ramp (`v_global = (1−ε)V₀t/τ_y`). At a late
  firing `t_f = τ/(1−ε)` after the last tick K it gives `P=1 ⇔ t_f−K ≤ ε(2−ε)t_f ⇔ K ≥ τ(1−ε)`, exact
  for every n; equality (e.g. ε=0, τ=K, tick processed before fire) gives P=1 as §5.4 requires.
  Per-clock early comparators, E bits and P latches are removed (fewer comparators: 1 total).
* Tests: `test_cf3.test_repair_year_exclusion` (periods 2.5, 0.5, 10, 0.7; three conventions;
  ε-band T=10.5) and the year-of-event log; mutation `lookahead_strict`.

## D2 (incomplete in §5.2/§5.5) Zero-time logic hazards; explicit comparators need a disarm
* Found twice: (a) clearing P on the same edge that uses it produced, one delta later, a spurious
  `fire ∧ ¬P` and stopped the next year's flow (B3 one unit low); (b) an explicit event comparator on
  the never-reset global ramp stays high forever; as a one-delta pulse it ended before a coincident
  clock fire fell, re-enabling a substituted item's packet (renovation at 20: 305 instead of 250).
* Implemented: P is now a comparator level (D1), no clearing edge; explicit comparators are
  physically disarmed by their own phase generator (comparator input switched from the data
  reference to a high rail `V_hi = 256V₀`, valid for H < 256), so they fall in the same comparator
  batch as clock fires. Set semantics now hold for all event sources.

## D3 (choice) P=1 cancellation by a negative one-year packet instead of a pending year cell
* Architecture §5.5: discard the "closed year cell" (pending hold capacitor).
* Implemented: the year cell is committed at every tick (one flying capacitor per group); a P=1
  event with S′=0 takes a negative packet `−C_n·v(N_A)` = exactly one year of the group's repair flow.
  Valid because the group repair rate `Σ e0·r` is constant over the year. If a later stage needs a
  time-varying rate inside the year cell, a second (pending) flying capacitor is required.

## D4 (clarification) The product `e0 × r` uses two op-amp stages (L1)
Repair amplitude = rail → `G(e0)` → inverter → `G(r)` → summer. Both data enter as conductances; the
product exists because the first stage turns `e0` into a voltage (L1 requires one factor as a source).

## D5 (engine semantics) Impulsive energies and floating potentials
Impulsive transfers use the linear-path rule `W = ½(v⁻+v⁺)Q`; it reproduces the analytic losses
(charge sharing, SC packet) exactly. During zero-length phases a flying capacitor can float; its
plate potentials are then gauge-dependent: per-switch energies use a fixed particular solution
(listed as `gauge_dependent_terms` in each jump record); totals are gauge-independent (Tellegen sum 0).

## D6 (engine) Crossing times
Analytic only for polynomial segments (exact rational roots up to degree 2, else bisection flagged
`inexact_events`); exponential (float) segments use bracketing + bisection. All stage-A model runs
have `inexact_events = 0`.

## D7 Initialisation
Capacitors that track a source voltage computed by the circuit (negative packet sampling `N_A`) are
initialised by an impulsive init jump at t=0; energy/charge accounting starts after initialisation.

## D8 §3(ii) confirmed, not a deviation
Joule ∝ charge holds only for one rail and positive packets; with amplitude-as-voltage and negative
packets it fails (measured, `cf3_full_solution_original.json`).

## D9 Test-design note on the mutation "simultaneous events processed sequentially"
In creation order (renovation first) the renovation's restart shorts the clock ramps before their
crossings are processed and the wrong rule happens to give the right number; the mutation is
detected with the reverse order (clocks first: 305 vs 250). Mutation tests should vary the order.

## D10 Degradation under ε > 0
The age reset happens at the late firing `τ/(1−ε)`. This is a convention of the circuit; degradation
was validated only with ε = 0 (right/left). No oracle exists for it yet.
