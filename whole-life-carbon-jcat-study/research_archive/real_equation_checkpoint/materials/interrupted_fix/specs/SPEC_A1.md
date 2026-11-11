# Stage A1 - definitions and exactness (reference calculation + unified model)

Read COMMON.md first, then TRIAGE/numeric.md and TRIAGE/rederive.md completely, then
`refcalc/base.py`, `refcalc/units_*.py`, `refcalc/registry.py`, `fastcalc/closed_forms.py`,
`fastcalc/engine.py`, `common/compare.py`, `bench/mutations.py`, `bench/verify_unified.py`
(functions `scenarios`, `run_both`, `exactness`, `sweep_check`), the tests, and the parts of
`synth/model.py` you need.

Scope: findings NUM-1..NUM-11, RED-1..RED-12 (and REC-1, APP-5, REP-17 which are the same
issues seen from other lenses).

Files you may change: `refcalc/*.py`, `fastcalc/*.py`, `common/compare.py`,
`synth/model.py` (only `conversion_factor`, `factor_references` and small helpers; do not
change the data model or the generators' random streams), `synth/generate.py` and
`synth/population.py` ONLY to add edge cases (existing scenarios must stay bit-identical:
do not consume random numbers differently), `bench/mutations.py`, `bench/verify_unified.py`
(only `scenarios`, `run_both`, `exactness`, `sweep_check` and constants: see items 16-17),
`tests/*.py`, `01_LEDGER/units.json` (by `python3 -B -m tools.sync_ledger`, plus hand edits
of the non-synced fields named below), `research_code/README.md` only if a command changes.
Do NOT touch `fastcalc` membership/counter design beyond what the items below need (Stage
A2 does that), nor `bench/approx_study.py` (Stage B2), nor `tools/*` except running
`tools.sync_ledger`.

The decisions below are taken; implement them in BOTH calculations so that they agree, and
rewrite the unit docstrings and the convention docstring of `refcalc/base.py` so that the
text says exactly what the code does.

## General principle (applies to every item)

> A numeric input that is missing (None), not finite (NaN, +-inf) or outside its range is
> never used in arithmetic. The smallest thing that needs it (row, route, yearly series,
> class, unit) is left out and counted, and every total that depends on it is marked
> incomplete. No input other than an invalid study period makes the calculation raise.

"Counted" means a count or flag in the unit's public result (`n_skipped`,
`n_routes_skipped`, `n_partial`, `n_invalid`, `computed: False`, ...). Use the existing
key names where a unit already has one.

## Time rules: exact arithmetic (NUM-1, REC-1, APP-5)

1. All time tests are evaluated in **exact rational arithmetic on the given binary
   floating-point values**, so that no result depends on rounding or operation order:
   - `c` = the double nearest to 1 - 1e-9 (as an exact ratio, `(1.0 - 1e-9).as_integer_ratio()`);
   - inside(tau, T)  <=>  tau < T*c   (exactly);
   - year(tau) = max(1, ceil(tau*c))  (exactly);
   - the n-th periodic event of period L is at tau = n*L **exactly** (not the rounded product).
   Implement with `as_integer_ratio()` (works for float and int) and integer arithmetic
   only (no `fractions.Fraction` in hot loops; precompute the per-row integers once).
   Validate finiteness before calling `as_integer_ratio()`.
2. Reference: keep the literal "count up event by event" structure
   (`n = 1; while inside(n*L, T): ...`) but with the exact test, and hand the **event years**
   (ints) to the callers instead of float times (callers only use `event_year(tau)`).
   Explicit lists: an entry is used when it is a finite number, t > 0 and exactly inside.
   Entries that are None / NaN / infinite are ignored by the calculation and make QA-02
   fail (listed like out-of-period entries). Duplicate years in an explicit list are each
   counted (as now); QA-02 lists them in `warnings` (RED-11(4)).
3. Closed forms (`fastcalc/closed_forms.py`), now provably exact:
   - `renewal_count(T, L) = ceil(T*c / L) - 1` in integer arithmetic (0 for an invalid L);
   - `periodic_year(n, L) = max(1, ceil(n*L*c))` in integer arithmetic;
   - `skip_weight_periodic`: with q = L*c (exact): if q >= 1 the N event years are distinct;
     if q < 1 they are exactly the years 1..year(N-th event). Weight = distinct - (1 - w_last)
     if the last event year equals Y. Decide the branch with exact integers.
   - `skip_weight_events` unchanged in form, with the exact year.
   Update `tests/test_closed_forms.py`: compare against a literal loop written with
   `fractions.Fraction` (independent of your integer code), include periods
   T/n*(1 +- {1e-15, 1e-12, 1e-10, 1e-9, 2e-9, 1e-8, 1e-6}), m*(1 +- 1e-9) for small integers m,
   the double 1.000000001 and its 50 neighbours on each side, periods below 1 year, and the
   doubles around 1/(1-1e-9). Add 1.000000001 to `bench/mutations.DECIMAL_BOUNDARIES` (or the
   equivalent list) and to an edge case.
4. Invalid periods (RED-3). For a material refresh cycle, an equipment service life (when no
   explicit list is given), a refrigerant service life (when no change list is given):
   - None = "not renewed": no events, nothing counted (SYS-01 already lists the missing value);
   - present but not a finite positive number (<= 0, NaN, +-inf): no events AND counted
     (`n_invalid` in B4-01 / B4-03; the refrigerant device is skipped and counted in the
     B1 units). These counts make the dependent stages incomplete (item 8).
   - Building replacement cycle: when the reconstruction scenario is not NONE the cycle
     must be a finite positive number, otherwise B5-01 is not computed (`computed: False`).
   Update the docstrings of B4-01, B4-03, B5-01, B1-02 (and B1-03/04 if they repeat the rule).

## Values that were used without a check (RED-2, NUM-2, RED-10, NUM-4, NUM-7, REP-17)

5. Factor records. A factor may be used only if, in addition to the existing conditions,
   its `value` is a finite number >= 0 and every gas amount is a finite number >= 0.
   Otherwise the use is skipped and counted exactly like an unlicensed factor (and SYS-03 /
   QA-03 are unaffected unless their own text says otherwise). Put the test in the one
   place each calculation resolves a factor.
6. Conversions. `synth.model.conversion_factor` returns None ("no conversion") when the
   registered or row-specific multiplier is not a finite number > 0. Both calculations use
   this function, so they stay symmetric.
7. Annual quantities (electricity consumption, generation, export, gas, oil, district heat,
   water, sewage, operational waste, ...): the Y yearly values that count (descriptor values
   for CONSTANT / LINEAR_TREND, table values for TABLE) must all be finite and >= 0;
   a TABLE-kind series needs at least Y entries. Otherwise the series is unusable: the unit
   skips it and counts it (for electricity: B6-04 and B6-01 `computed: False`).
   For the parametric kinds the table is a copy: a copy that is shorter than Y, or differs,
   is reported through `descriptors_match_tables: False` and never raises.
   Unified model: CONSTANT -> test base; LINEAR_TREND -> base and slope finite and the two
   end values (k = 0 and k = Y-1) >= 0 and finite (a float linear function of k is monotone,
   so the ends bound every year); TABLE -> one scan (it is scanned anyway).
   The clamp max(0, consumption - (generation - export)) of B6-04 stays: it is the definition
   of purchased electricity, not a rounding of an invalid quantity; say so in the B6-04 text.
8. Grid factor. Well-formed descriptor: CONSTANT with start finite >= 0;
   LINEAR_DECLINE_TO_FLOOR with start, floor, decline finite, decline >= 0, start >= floor,
   floor >= 0; STEPWISE with non-empty steps whose `from_index` are ints (type int, not
   bool/float), strictly increasing from 0, values finite >= 0. Otherwise the table is used,
   and it needs at least Y entries, all finite >= 0; if that fails too the grid is unusable:
   X-06 reports it, B6-01 / B2-01 / X-11 are not computed, totals incomplete.
   `construction_value` must be finite >= 0, otherwise A5-01 is not computed.
   **Remove the ValueError for a short grid table from `check_period`** on both sides: the
   only refusal left is an invalid study period (keep the open-issue convention B-21 true).
9. Everything in RED-10 and in the verifier's additions (route fraction None in C-05, None
   in a table, factor value None, summary quantity None, None in the use-area breakdown, None
   in an explicit list, annual table shorter than the period): no exception; skip and count
   by the general principle. C-05: a fraction that is missing / not finite / negative is a
   violation; a disposal mass that is missing / not finite / negative cannot be checked and
   is counted in `n_mass_unchecked`. SYS-04: a missing / not finite / negative use area makes
   the status INVALID. X-17: a class whose declared summary quantity is missing, not finite
   or <= 0 is left out and counted (`n_classes_skipped`); fix the text (the identity with
   the re-aggregated manufacturing emission holds for the classes that have a positive
   summary quantity) (RED-12(5)). X-13: add `n_skipped` (RED-12(6)).
10. Acceptance for 5-9: adapt a copy of
    `/tmp/claude-0/-home-user--/49c0bd7e-a786-5ae4-9a1e-e89e7996ede3/scratchpad/recheck/numeric/t7.py`
    (every numeric leaf of three small scenarios set to nan, +inf, -inf, None, one at a time;
    uses `h.py` in the same folder as strict comparison). Target: **0 disagreements between
    reference, unified full and unified totals, and no exception at all except for
    `boundary.study_period`.** If a remaining field cannot reasonably be guarded, list it in
    your report with the reason; do not hide it.

## Completeness (RED-1, RED-5, RED-12(2), NUM-9)

11. A stage value is incomplete when ANY unit whose results flow into it left something
    out, whether or not that unit's own stage is in the boundary. Implement it from the
    data flow, not from a hand list: for each stage take the units X-02 composes it from and
    their transitive `depends_on` closure (registry); a unit "left something out" when one
    of its exclusion counts is > 0 or `computed` is False. `incomplete_units` lists exactly
    those units (sorted), `complete` is False when the list is not empty; SUM-01..03 and
    the other totals carry the flag as now. The unified model mirrors it with its own
    restated table (a test must assert that the engine's table equals the closure computed
    from the registry). Update the X-02 / base.py texts. Add verification scenarios
    "stage subset + defect in an upstream row" (e.g. included = [B3], [B5], [B3, B5], [B4],
    [B6] without B2, with a missing quantity / unlicensed factor / invalid cycle) to
    `bench/verify_unified.scenarios` and tests that assert `complete is False` there.
12. B2-01 reports `computed: False` when B6-01 is not computed.
13. SUM-08: the comparison additionally requires that both totals are complete. Statuses:
    keep the existing ones and add `BASELINE_NOT_FOUND` (an id was given but no such
    scenario is registered) and `INCOMPLETE` (either total incomplete: delta and saving are
    None; report `proposal_complete` and `baseline_complete`). Update the text.
    Unified model: totals held by the caller are keyed by `boundary.baseline_scenario` (the
    input), never by `meta` (NUM-9), and carry the baseline's completeness. State in the
    docstring of `finish`/`evaluate` that the key identifies the baseline by name only and
    that any change of the baseline, of the period or of the boundary invalidates it.

## Gas breakdown and pseudo lines (RED-4, NUM-3, NUM-5, NUM-6, NUM-8)

14. X-04 returns a real check: `matches_stage_total` (bool) = the sum of gas amounts x GWP
    + purchased electricity + refrigerant equals the sum of the 14 stage values within
    relative 1e-9 (absolute 1e-9 when the sum is below 1), and QA-01 gets a check (d) that
    fails with a violation entry when it is False. In the engine use the shared `_within`.
    B3-01 (NUM-3): remove the `e0 == 0.0` shortcut; a row whose manufacturing result was not
    computed upstream contributes nothing (item 11 already marks B3 incomplete), a row with
    a computed e0 (even 0.0) and a valid repair rate > 0 emits its lines, so the gas
    breakdown is kept. Make both sides identical (check with the checker's `t14.py`).
    Pseudo lines (NUM-5): purchased electricity and refrigerant lines are identified by
    module-level sentinel objects that cannot equal a factor id (give them a stable `repr`
    for any place they become a dictionary key in a result), never by the strings "GRID" /
    "REFRIGERANT". Gas list (NUM-6): X-04 / X-05 use the listed gases without duplicates
    (first occurrence wins, order kept) and read each record's own gas amounts (a gas not
    present in a record counts 0); X-05 does not need "CO2" to be in the list. SYS-02
    (NUM-8): pass the unit as a value, not as formatted text.

## Gates and texts (RED-6, RED-7, RED-8, RED-9, RED-11, RED-12)

15. Wording / small code changes; after each, the docstring must describe the code:
    - SYS-01 (RED-6): keep the set of examined fields; list them in the text; say that
      inputs outside the list are reported by the unit that needs them (count / `computed`)
      and make X-02 incomplete; a NaN / infinite value in an examined field is reported as
      `NOT_FINITE` (a violation). In `01_LEDGER/units.json` correct the hand-written
      `branches` field of SYS-01 accordingly.
    - SYS-03 vs X-14 (RED-11(2)): a factor slot is required whenever the calculation would
      skip-and-count without it; make SYS-03 report an equipment row without a disposal
      factor the same way it reports a route without a factor. SYS-02 text: the EPD factor
      is not examined there (its fallback is reported by X-15).
    - QA-01 text: state the absolute floor (relative 1e-9, absolute 1e-9 when |value| < 1).
    - B4-02 text: manufacturing = A13-01 + A13-03 (+ X-01 for equipment), **without** the
      unquantified uplift A13-04; equipment delivery (factor of stage A4) and installation
      (factor of stage A5) are added per renewal; material installation factor must be of
      stage A5. B3-01 / B3-02: e0 excludes the uplift. B5-01: the base includes A13-04.
      B1-02: "x GWP". A5-04: installation by factor is not part of A5 (materials and
      equipment are installed "by factor" only at renewals).
    - X-02 / X-05 texts: describe `by_stage_all` and `by_stage_co2` (all 14 stages, B6
      after the B2 rule) or remove them if nothing uses them (check `tools/`, `bench/`).
    - SUM-05: remove the unreachable branch or its text.
    Do not change numbers by these wording items.

## Numerics and the comparison (NUM-10, NUM-11, REP-16)

16. `segment_moments` / `linear_weighted_sum`: sum the full years and ADD the weighted last
    year (no subtraction of (1-w)*last from a full sum). `common/compare.py`: a mismatch
    when exactly one side is infinite or two infinities have different signs; bool is only
    equal to bool (never to 0/1). `bench/verify_unified.exactness`: compare with
    **floor = 0** (purely relative, as the report says) and treat extra leaves in totals
    mode as a failure; if a leaf then exceeds 1e-9 on the study's scenarios, find out why
    and report it (do not re-introduce a floor silently).
17. `bench/verify_unified.sweep_check` (REP-16): compare **every unit** the sweep returns
    (not a hand list of 22) and keep the baseline comparison on where the scenario has one;
    record in its result which units and how many scenarios were compared.
    Extend `bench/mutations.py` with: NaN / inf / negative / None in annual profiles (base,
    slope, table entry), grid (start, floor, decline, step value, table entry,
    construction_value), factor value, gas amount, conversion multiplier; short annual
    table alone and combined with an unusable factor / unit; factor value 0 with a non-zero
    gas vector; float step index; factor ids "GRID" / "REFRIGERANT"; duplicate / missing
    "CO2" in the gas list with composite rows; invalid cycles; None in an explicit list;
    period 1.000000001.

## What NOT to change (document instead)

- Ill-conditioned inputs of NUM-10 (a), (c), (d), (e): no code change beyond item 16; list
  them in your report (the orchestrator documents the limit).
- RED-11(3) (a zero-fraction route without a factor marks the total incomplete): keep.
- Wrong TYPES (strings, Decimal, numpy scalars) are out of scope; say so in base.py.

## Acceptance (run all, report actual output)

a. Unit tests pass.
b. Item 10 sweep: 0 disagreements, no exception except the study period.
c. Adapted copies of the checkers' scripts show agreement for NUM-1..NUM-9
   (`numeric/repro_findings.py`, `t14.py`, `t12.py`, `t10.py`, `t6.py`, `t1.py`) and
   the RED cases (`rederive/holes1.py`, `holes4.py`, `holes5.py`, `holes6.py`) now
   show `complete False` / counts where the findings ask for them.
d. A reduced exactness run from a scratch script (import `bench.verify_unified`, e.g.
   `exactness(60, 20)` and `sweep_check(16)`; do not write the study's JSON): all units
   within 1e-9 with floor 0, no extra leaves; report the largest error and its path.
e. The checker's random fuzz (`numeric/fuzz1.py` with `fuzzlib.py`, adapted): at least
   5,000 scenarios, strict comparison, report the number of disagreements (target 0).
f. `python3 -B -m tools.sync_ledger` run; `git diff --stat` in your report.
