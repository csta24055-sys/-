# Route A claims (evidence classes per 07: [P] proven in declared domain, [E] exact sample checks, [F] numerical/float tests, [H] hypothesis / new argument not yet independently reviewed)

Domain: fictional P0/P1/P2/Px, t∈[0,60] (tests), Fraction arithmetic unless marked float. Source commit 5a2f898. No claim of real-building accuracy, novelty, or universal circuit equivalence.

| id | claim | class | evidence |
|---|---|---|---|
| A-1 | R1 (Q + 2 reset clocks + impulses) equals the closed-form oracle and this route's hand values at all 11 contract points, under right/left/orig conventions | [E] | `test_contract_points_all_conventions`; points.json 490 rows, 0 mismatches |
| A-2 | At τ∈{10,20,30,40,60}: R1(τ−δ)=G_left(τ)−4δ, R1(τ+δ)=G_right(τ)+4δ, R1(τ)=G_right or G_left per convention; jump = 20 or 55 | [E] (δ=1e-12 exact) | `test_limits_at_event_times` |
| A-3 | Convention ⇔ reset semantics: right ⇔ x reset to 0 at τ; left ⇔ x held at 1 at τ; orig ⇔ left with clock rate (1−ε)/c; orig band is [nc, nc/(1−ε)) | [E] on P0; general statement [H] (elementary, but not independently reviewed) | `test_reset_semantics`, `test_knife_points_exact`. Equivalent to TH-11a `N_c=⌈x⌉−1`, x=T(1−ε)/c (note: TH-11a's formula gives −1 at T=0; domain T>0) |
| A-4 | Knife points: 10.000000005 → right/left 160.00000002, orig 140.00000002; 10.00000002 → 160.00000008 all three | [E] exact, [F] float agrees within 1e-9 | `test_knife_points_exact`, `test_float_knife` |
| A-5 | Float knife edge: at 10.00000001 the exact orig value is 140.00000004 but float evaluation gives 160.00000004 | [F] observed | points.json `float_at_knife_edge_10.00000001`; recorded as undefined zone for float, not asserted |
| A-6 | R2 impulse-free `G=G0+(r+ΣA_kν_k)t−ΣA_k x_k` equals R1 everywhere tested (all 3 conventions, 300 random rationals + limits); residual ∈[0,55) right, (0,55] left | [E]; identity itself [P]-elementary (frac(s)=s−⌊s⌋) but not independently reviewed → keep [H] for "all t" | `test_r2_equals_r1`, `test_sawtooth_bounded` |
| A-7 | Readout G invariant under (γ,C_cap)=(1,1)→(5,2); V=G/(γC_cap), I=r/γ; E_cap=Q²/2C_cap not invariant and not proportional to G | [E] | `test_scale_invariance_and_separation` |
| A-8 | P0 single superperiod clock R3 / R3i reproduces P0 exactly with (2,0,2,0); counter variant R3k with (1,1,2,0) | [E] | `test_r3_single_clock_p0` |
| A-9 | **Counterexample to architecture H-A3**: fixed Px schedule (AC reset at 7) is reproduced by ONE clock of period 20 with comparators {7/20,17/20,1}: (2,0,3,0). The "needs (3,0,2,0), single clock impossible" claim holds only when the reset time is an online/unknown input (or periods incommensurate) | [E] for the counterexample | `test_px_fixed_schedule_single_clock_COUNTEREXAMPLE` |
| A-10 | With an online reset, futures differ for states (0,0.35) vs (0.7,0.35) (13-yr increment 107 vs 127) and (0,0.35) vs (0,0.5) (11-yr increment 64 vs 99), so two clock phases must be stored | [E] distinguishing samples; "two continuous states are necessary" in general [H] | `test_online_reset_needs_two_phases` |
| A-11 | Merged clock capacitor (periods 30, 15, 20/3) with one charge amount cannot satisfy G(10)=160 and G(20)=255 | [E] | `test_merged_clock_capacitors_fail` |
| A-12 | P1 substitute 250/405, additional 305/460 at t=20/40 (right); left at 20: 200 under both policies (renovation not yet counted) | [E] | `test_p1_policies` |
| A-13 | Order-free set rule is order invariant by construction; a NAIVE sequential implementation gives 4 different G(20) values {250, 270, 285, 305} over the 6 orderings — two of them match neither policy | [E] | `test_p1_order_invariance_and_naive_counterexample` |
| A-14 | P2 (rate 4→3 latched by first AC firing): 160, 245, 295, 380, 515 at 10/20/30/40/60; continuous kink at 10 (slopes 4 and 3) | [E] | `test_p2` |
| A-15 | Zero-mean AC into ideal capacitor: charge ≤2I0/ω, no accumulation, cannot drive the clock (G(10)=140) | [F] (closed form + grid) | `test_zero_mean_ac_negative` |
| A-16 | Full-wave rectified clock hits exactly at nc ∀n iff c/h∈½ℤ (ripple zeros only at u∈{0,π/2,π}); else error <h. **Refines architecture's "only when c is an integer multiple of the half period"**: c=10.25=20.5h is exact | [F] numerics; the iff argument (convexity f''=cos u) is [H] | `test_fullwave_half_integer_multiple_exact_COUNTEREXAMPLE`, `test_fullwave_non_multiple_error_below_half_period` |
| A-17 | Full-wave rectified operating current (mean 4): G deviates from the DC ramp by ≤(I0/ω)(√(1−4/π²)+2asin(2/π)/π−1) ≈0.2105·I0/ω (=0.2105 kg for I0=2π, ω=2π), exact on the half-period grid | [F] | `test_rectified_operational_ripple` |
| A-18 | No speed benefit from the circuit path: closed form Fraction 10.3 µs/pt vs R1 46.8, R2 36.0, R3 19.8 µs/pt; float closed form 0.33 µs/pt | [F] measured (one machine) | results/benchmark.json |
| A-19 | Single continuous state Q alone is possible only with an unbounded comparator table (G strictly increasing ⇒ Q encodes t, thresholds 140,200,295,…): (1,0,∞,0) | [H] remark, not implemented | — |

Not claimed: minimality of any 4-tuple (no lower-bound proof); P2/Px under the orig convention (NOT_RUN, undefined); any relation to C_WLC(T) beyond P0 data (X2/X5 are coordinator/D gates).
