# circuit_first — STATUS (stage A: S0 engine + CF1, S1 pilot CF2, S2 state changes CF3)

Date 2026-11-24. Branch `claude/wlc-equivalent-circuit-20261124`, base commit `e4c6d20`
(no git operations by the builder). Model actually run: self-reported **claude-opus-5-5**
(Opus 5.5); effort is **not observable** from inside the session (agent definition says medium).
Fictional data only. No reference/oracle code was imported anywhere (stage A uses only
independent closed forms and ledgers written inside the tests).

## Command
```
cd whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/circuit_first/tests
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s . -p 'test_*.py' -v
```
Python 3.13.18, stdlib only. Result: **34 tests, 34 OK, 0 fail, 0 skip** (~18 s).
Log: `results/test_log.txt`. No `__pycache__` left. No random seeds (all inputs deterministic).

## Gate results (builder's own runs; the verdict belongs to the independent verifier)
| gate | content | result |
|---|---|---|
| CF1 | 14 benches: divider/parallel; R=3Ω,I=2A,t=5s → 12 W, 60 J (metered); RC charge and heat ½CV²(1−e^{−2t/τ}); constant-current integration; AC `E=I²_rms R[t−sin2ωt/2ω]` (LC tank + CCCS, DC sources only); ideal-switch charge sharing (ratio, charge, loss ½C₁C₂/(C₁+C₂)ΔV²) and through R; SC packet (charge `C_sV₀`, loss `C_sV₀²`, rail energy `V₀Q`); inverting summer; feedback `1/(1−w)`; diode half-wave (energy, commutation times); series RLC (S3: q→CV, heat→½CV²); integrate-and-fire periods 7/10, 7/5, 10/3 with 7 coincident set firings; L1 homogeneity (degree 1 in G, never λ²; current drive invariant); impedance and time scale invariance | PASS: exact benches residual 0 (KCL, element laws, impulse KCL, Tellegen, storage); float benches ≤1e-10 |
| CF2 | pilot from primitive inputs (100, 4/yr, 20@10, 35@20); clocks find the events | PASS: right 160/255/315/410, left & original 140/200/295/355 at T=10/20/30/40; all 07 points (0, 1, 9.999999, 10, 10.000001, 19.999999, 20, 20.000001, 30, 40, 60) in 3 conventions equal the ledger exactly; original-convention firings at `10n/(1−10⁻⁹)`; single-rail `E = V₀Q` exactly at 5 horizons; invariance under (γ,V₀,τ_y) ∈ {(1,1,1),(1/1000,5,3600),(7,1/2,1/10)}; full-solution dumps (right, original) audited with all residuals exactly 0 |
| CF3 | same catalogue, parameter changes only | PASS vs independent ledgers: periods 0.1/0.7/10/3 (3 conventions); simultaneous events as a set + order invariance over 6 permutations; explicit early replacement (restart / keep); degradation reset at renewal (incl. explicit renewal); efficiency change after first renewal (07 P2); repair-year exclusion per group for periods 2.5, 0.5, 10, 0.7 incl. ε-band T=10.5 and integer-time events, 3 conventions, two rows in one group; renovation at 20 (coincident) and 25 (non-coincident), substituted vs additional (07 P1) |
| audits | AST imports; engine vocabulary; adapter has no while/range/floor/ceil; hiddenness; schema signature; 7 mutations | PASS: no forbidden imports; h = 0 (GREY = 0) for pilot and CF3 "full"; one signature for all pilot variants (3 conventions × 2 unit sets + permuted input); 7/7 mutations detected |

Decisive numbers: pilot `W_in = 49`, `W_out = 0`, `h = 0`; 13 capacitor states (7 essential),
12 boolean bits, 6 sequencers, 53 elements; runtime pilot to T=40 ≈ 0.13 s exact arithmetic.
Mutations (expected → mutated): clock slope 1 (140.00000002 → 160.00000002), no lookahead
(B3 6.5 → 7), exclusion per event (0.5 → −2.5), sequential simultaneous (250 → 305), strict lookahead
(15 → 16), age not reset (156.25 → 256.25), readout order swapped (140 → 160).

## Results files (`results/`)
`bench_*.json` (with full solution dumps), `pilot_*.json` (`pilot_full_solution_{right,original}.json`
are full dumps: netlist, every record's node voltages / element currents / states / derivatives,
every jump's impulse charges and energies, event log, meters), `cf3_*.json`
(`cf3_full_solution_original.json` full dump of the richest scenario), `audit_*.json`, `test_log.txt`.

## Code SHA-256
engine: `__init__` fdb221de…, `audit` 981254bc…, `linalg` 808a4dd2…, `logic` 7b199e30…,
`mna` ac9a02a7…, `netlist` bbaf6a01…, `sim` 2a6ca077…; `adapter.py` a839649a…, `model.py` 78616d8a…
(computed after the last code edit; the verifier should recompute).

## Findings to review (see DESIGN_DEVIATIONS.md)
D1 architecture §5.4 early-comparator rule wrong for n ≥ 2 (replaced by a shared lookahead
comparator); D2 zero-time hazards and explicit-event disarm; D3 negative one-year packet instead of a
pending year cell; D5 gauge-dependent per-switch energies when a capacitor floats.

## NOT_RUN (stage A scope or not done)
* All stage B items: factor/derived rails and multi-factor amplitudes, year banks/MDAC, diode
  rectification of net purchase, ρ split B2⇄B6, refrigerant cell, terminal packets/`Z(T)`, `ι`,
  multiple synthetic buildings, comparison with the frozen oracle (`refcalc`) — not done, no oracle access used.
* N_max same-netlist padding test (only the schema-signature part of CF5 was run).
* Architecture mutations not applicable without stage-B cells: init-before-leak, refrigerant as RC
  decay, ρ side always drawn, ι upstream of B5 base, diode after integral, terminal packet into accumulator.
* AGG ratios, SPICE/real hardware, Math7 seven-engine checks.
* Independent verification (belongs to `verification/`); VERDICT is a draft only.

## Needed before stage B (decisions for the coordinator/architect)
1. Accept D1 (shared lookahead comparator) as the §5.4 rule, or prescribe another.
2. D3: is a negative one-year packet acceptable for B3, or must a pending year cell be kept
   (needed anyway if year-bank-varying rates ever enter a year cell)?
3. Year-cell placement for refrigerant (§5.5) with set semantics: confirm that "leak then event"
   at an integer tick maps to tick priority 20 < fire 30.
4. Whether `γ·q` readout of the flying year-cell capacitor (always included) is acceptable as "readout".
5. Domain constant `V_hi = 256 V₀` (requires H < 256) — fine with §5.4's domain?
