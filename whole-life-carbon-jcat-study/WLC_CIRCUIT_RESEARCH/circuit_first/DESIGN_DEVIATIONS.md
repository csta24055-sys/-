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

---
# Stage B (S3a–S3e) and V1 fixes

## D11 (engine, V1-D1) Comparator equality semantics — FIXED
Defect found by the independent verifier and reproduced here (gated integrator: charge 3 instead of 1 in BOTH
`sim.py` and the new `hybrid.py`). Rule now: during an instant a comparator at y = 0 is high (this is what the
shared look-ahead comparator needs when the tick resets the year ramp to exactly 0); after all priority classes
of the instant are processed, a "post phase" switches every comparator with y = 0 and y falling just after the
instant to low AT THAT INSTANT (before time advances); it cannot re-rise in the same instant. Bench
`tests/test_v1_fixes.py::test_D1_gated_integrator_both_directions` (falling 1, rising 2, both simulators, audited
dump). All stage-B results in `results/stageB_*.json` were produced after this fix.

## D12 (structure) Crossbar / core split with amplitude taps (substitution theorem)
The amplitude crossbar (rails, conversions, one inverting stage per extra data factor, summing junctions) is a
static network: it is solved once by `engine/dc.py` (exact, sparse elimination in dependency order; on all tested
buildings every equation was peeled, dense block 0, KCL residual exactly 0). The lifecycle core sees each
sampled op-amp output as a grounded ideal source valued by that DC solution (`tap.*` elements). This is the
substitution theorem for a stiff ideal op-amp output; it is a solving strategy, not a computation outside element
laws. Both netlists and the tap map are dumped (`results/stageB_netlists_{S,E1}.json`) so an outside simulator can
re-run: crossbar DC → taps → core. A merged single-netlist run was NOT done (the crossbar would form
components of thousands of unknowns in the hybrid solver).

## D13 (engine) Boundary nodes and accumulator sinks in `engine/hybrid.py`
Solving strategies, declared: (a) nodes held by a grounded ideal source are boundary nodes (known potential),
so the network splits into small components; (b) an op-amp integrator tagged `accumulator` (non-inverting input
grounded, one feedback capacitor, optional reset switches, nothing else on its output) is solved as a sink: its
virtual ground is a known-potential node and its capacitor charge = integral + impulses of all currents into it
(KCL at the virtual ground + capacitor law). Equivalence checked: accumulators on/off identical on a truncated
building (`test_stageB.py::SmallBuilding`), and the off-run's full dump has KCL / element-law / impulse-KCL
residuals exactly 0. Speed effect on benchmark S events: 96 s → 5 s. No behaviour is computed outside element
laws; these strategies are not counted in W_out.

## D14 (B3) Negative one-year packet (D3) confirmed for the full building
In the synthetic model every B3 group rate is Σ e0·r of constant row amplitudes (A13 or X-01 row values × repair
rate): constant within each year. So the pending year cell was not needed anywhere (coordinator decision 2).
Year-cell charge is read only through an explicit readout transfer (copy capacitor sampled at the readout,
dumped into the B3 readout integrator), as coordinator decision 4 requires.

## D15 (B1) Refrigerant: tick-time look-ahead
§5.5 needs "an event of this device belongs to the closing year" AT the tick. Periodic devices use an exact
per-device early comparator y = κ·v_global + c·(v_ramp − V0) ≥ 0, κ = ε(2−ε)/(1−ε)², i.e. remaining time to the
firing ≤ κ·elapsed time (holds for every n, unlike the §5.4 rule; D1). Each periodic device has its own copy of
the global ramp, so it does not merge with other components. Explicit change years use the global-ramp early
comparator (exact, absolute). At such a tick: pending loss sample (the year-end charge), reset to m0, year-start
sample; the pending packet is dumped at the firing (P = 1). Mid-year (P = 0) events: loss packet from the live
charge, reset, and a correction flow −λ·GWP·r·m_start until the tick (non-top-up), so the booked loss equals the
year-end charge. During the zero-length sampling phase the drain is gated off (otherwise the mode is
non-nilpotent: hold and charge in one loop). Duplicate event years inside one device list would merge into one
set firing (not present in the tested scenarios; limitation).

## D16 (convention, V1-D5) What the original convention means in the circuit
The source (WLC_THEORY_RESEARCH_BASE/03 §3.2, eq. at line 101) states a counting rule: an event at τ counts iff
τ < T(1−ε). The circuit realises it as a firing at τ/(1−ε) with a readout before firings at T. Year ticks, year
banks, flows, leaks and drains are NOT dilated. In the full building, the firing time affects only quantities that
do not depend on where in the year the firing is: whole-year B3 exclusion, refrigerant loss and reset (packet plus
correction flow = year-end value). So the dilation is invisible there, and the oracle comparison decides it:
relative ≤ 6e-14 on all tested T. The stage-A-only cells degradation and efficiency switch DO see the dilation
(≤ 3.9e-10 relative, verifier). They have no source counterpart and are declared as "dilated" in adapter.md.
In-band T ∈ (K, sw(τ)] (source §D′) are excluded from the comparison by construction of the T list.

## D17 Ordering at an integer tick (coordinator decision 3)
readout → year tick → fire was implemented. It is confirmed by the oracle at integer T (20, 60, 75, 100)
with integer-year equipment replacement lists and refrigerant change years. Event counts are equal for every
scenario and T.

## D18 (V1-D2) Signed inputs
Stage-A adapter: negative amounts and rates are now supported (negative-polarity packet; flow from the −V0 rail).
Negative repair base/rate and negative degradation slope are rejected with ValueError. Building adapter:
negatives follow refcalc's own skip rules (nonneg checks are part of the specification and are counted W3); a
negative year-bank/grid value raises ValueError (outside the valid domain); factor values of either sign are
supported (rails are signed sources). Zero values build no branch (value-equivalent, counted W3).

## D19 (V1-D3, V1-D4) Repair stage per (group, stage); one netlist for every convention
One year cell per (event group, stage). The look-ahead divider is a VCVS of gain ρ (ρ = 0 allowed), so
right/left/original build the same netlist (53 elements each). The signature is now derived from the netlist graph
(`model.netlist_signature`). The N_max identical-netlist test runs for the stage-A cell family
(`tests/test_nmax.py`): unused slots are disabled by static switches, and the W2 grouping becomes a static
item×clock selection matrix. For the full building the N_max template is NOT_RUN: cell variants differ by input
kind (profile kind, grid kind, explicit-list length, refrigerant periodic/explicit), so a template would need
every variant with enable switches.

## D20 Lemma notes (from the verifier, see coordination/CIRCUIT_FIRST_ERRATA.md)
L1: the architecture's homogeneity argument has a gap (conclusion supported by the verifier's multi-affine
sketch, still [H]). The stage-A bench is renamed `test_L1_homogeneity_only`. L3: an ideal DC current source into a
grounded capacitor integrates exactly (P0). An active element is needed for conductance-coded rates and full
SC charge transfer, not for integration as such.
