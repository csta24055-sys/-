# Stage A2 - evidence for "unified" and for the stated mechanisms

Read COMMON.md, then TRIAGE/records.md completely and REP-3, REP-4, REP-12 in
TRIAGE/reports.md, then `fastcalc/engine.py`, `fastcalc/closed_forms.py`,
`bench/verify_unified.py` (function `mechanisms` and how its result is stored),
`tools/build_records.py` (`MODELS`, `mechanism_checks`, `plan`) and
`03_MODELS/DERIVATIONS.md`. Stage A1 has just changed `refcalc` and `fastcalc` (exact time
arithmetic, validity rules, completeness); read
`/tmp/claude-0/-home-user--/49c0bd7e-a786-5ae4-9a1e-e89e7996ede3/scratchpad/recheck/fix/A1_REPORT.json`
for what changed.

Scope: REC-2, REC-3, REC-4, REC-5 (the code/measurement side), REC-6, REC-7 (code side),
REC-9 (the counter), REP-4, REP-12.

Files you may change: `fastcalc/engine.py`, `fastcalc/closed_forms.py` (refactors that keep
every result identical), `bench/verify_unified.py` (function `mechanisms` only, and the
place its result is stored), new files `bench/membership_check.py` and
`bench/mechanism_probe.py`, `tests/test_engine.py` (+ a new test file if you like).
Do NOT change `refcalc`, `tools/*`, the reports or DERIVATIONS.md (a later stage rewrites
records and reports from your outputs); do NOT change any result of the unified model.

## Background

The study counts a unit as "unified into model K" only if its value is **read from a shared
table or produced by a shared parameterised function**; being computed "in the same scan"
does not count. The re-check showed (a) several memberships fail that rule in the code,
(b) the "mechanism counters" inside the engine are tallies placed by hand that cannot fail,
(c) for several units the cited agreement does not exercise the closed form at all.
The cure is to replace assertion by measurement.

## 1. Make the shared structure real where it is cheap and natural (results unchanged)

- K5 indicators: one shared function, e.g. `indicator(by_stage, subset, divisor)`, used for
  SUM-01..SUM-06 (subset sum / 1, / area, / (area*T), / 1000 ...) and for the shares of
  SUM-07; SUM-08 builds on the SUM-03 value it returns. No inline copies.
- K4 refrigerant: build ONE per-device table of charge x GWP in `aggregate`; B1-01 is the
  sum of that table, B1-02..04 multiply the same table entries by the fractions from
  `refrigerant_fractions` in `finish` (no second product, no second read of the rows).
- Factor resolution (REC-3): memoise the record part (exists, licence, stage, value/gas
  validity) per (factor id, stage) and the unit conversion per unit pair; a row-specific
  conversion is necessarily resolved per row, but must not repeat the record part.
- Anything else in REC-2 / REC-7 where the code can honestly be routed through the shared
  table or function at no cost. Where it cannot (A13-05, X-13, SYS-03 are expected to stay
  outside), leave the code alone: the unit will simply be recorded as not unified.
- Remove the hand-placed counters that cannot fail (`rows_scanned`, `row_factor_products`,
  `event_lists_built`, and any other tally that only counts its own position), or keep a
  counter only if it counts a real operation at every place the operation happens and name
  it for what it counts. `_stats` may shrink; tell the later stage exactly what remains.
  Put every construction of an event-year list behind a named helper function so that it
  can be counted from outside.

## 2. `bench/membership_check.py` - fault injection (the membership evidence)

For every shared object of the unified model (the table read-out `tot`, the K2 count and
skip-weight functions, the K3 weighted-sum / moment functions and the series function,
the K4 device table and `refrigerant_fractions`, the K5 `indicator`, the K6 `_within`, the
K7 resolver, plus any other shared helper you find), break it on purpose (e.g. multiply
its result by 1.5, or flip a boolean) by patching the module attribute or a hook you add,
run the unified model on a small set of fictional scenarios chosen so that every branch is
exercised (parametric profiles and year-table profiles; with a rebuild scenario; with
explicit event lists; composite rows; baseline attached; stage subsets are not needed),
in full-output and totals-only mode, and record **which units' public results change**
against the unbroken run (use `common.compare.compare`, tolerance 1e-9, floor 0).

Output (JSON, default path `STUDY/04_VERIFICATION/membership_check.json`, `--out` to
override; when you test it write to your scratch folder):
```
{ "shared_objects": { "<name>": {"kind": "table|function", "where": "module.attr",
                                 "perturbation": "...", "units_changed_full": [...],
                                 "units_changed_totals": [...]} },
  "units": { "<unit id>": {"sensitive_to": [names], "numeric_leaves_full": n,
                           "numeric_leaves_totals": n, "flag_only_in_totals": bool} },
  "scenarios": [...], "notes": [...] }
```
Also include, per closed form, the list of units that detect a broken closed form (REC-6
needs "the closed form of B6-02 is verified through B6-03, B7-04, ...").
The script must be deterministic and finish in a few minutes.
Design the injection so that a later reader can see it is not circular: the shared object
is patched from outside; nothing in the engine knows about the test.

## 3. `bench/mechanism_probe.py` - measured operation counts (replaces the hand tallies)

Measure, on the mechanism scenario used today (seed 5, 400 material rows, 120 equipment
rows, 10 refrigerant devices; once with parametric inputs, once with year tables) and on
benchmark sizes S / M / L, in totals-only and full-output mode, separately for `aggregate`
and `finish`:
- multiplications in which a factor-record value is an operand (wrap the values in a
  counting float subclass), split into "per material/equipment row" and "per table entry";
- how many times each row list (materials, equipment, refrigerants) is iterated and how
  many row objects are read (proxy objects);
- factor-record look-ups and unit-conversion calls (identity calls counted separately),
  and how many distinct (factor, stage, unit) triples they cover;
- event-year lists constructed (by kind: periodic material/equipment, explicit equipment,
  refrigerant) and calls of the exact year function;
- yearly-loop iterations (values computed per year) by purpose (value vs. consistency scan).
The checkers' instruments are good models:
`.../recheck/records/instr1.py .. instr5.py` and `.../recheck/records_verify/v3_counts.py`,
`v4_products.py`. Output JSON `STUDY/04_VERIFICATION/mechanism_probe.json` (`--out`).
From these counts state, as booleans computed from the numbers (never typed by hand):
  P1 totals mode: zero factor-value multiplications per material/equipment row;
  P2 totals mode: material and equipment rows are read exactly once and not in `finish`;
  P3 totals mode: no periodic material/equipment event-year list is built
     (explicit lists and refrigerant change years are enumerated: report their counts);
  P4 parametric inputs, totals mode: no per-year value loop (report the consistency scan);
  P5 recipes: one computation per distinct composition;
  P6 a second study period re-reads no material/equipment row (refrigerant rows: report);
  P7 factor records are resolved once per (factor, stage); per-row work is limited to
     row-specific conversions and EPD applicability (report the counts).
If a statement is false after your refactor, report it as false; do not bend the probe.
`bench/verify_unified.mechanisms()` should then return the probe result (or be removed in
favour of it; say which).

## Acceptance

a. Unit tests pass, including tests for the two new scripts on a tiny scenario.
b. A reduced exactness run (import `bench.verify_unified`; e.g. `exactness(60, 20)`,
   `sweep_check(16)`) still passes with floor 0 after your refactor: report the largest error.
c. Run both new scripts with `--out` in your scratch folder; put the two JSON paths in your
   report and summarise: per model, which units are sensitive to which shared object in
   which mode; which of the 66 previously claimed members are NOT sensitive to any shared
   object of their model; the P1..P7 values.
d. Instruction-count sanity: on benchmark M, totals-only, report executed bytecode
   instructions before and after your refactor (use `sys.monitoring` as
   `bench/verify_unified._Instr...` does); the refactor must not make the unified model
   slower by more than a few percent - if it does, say so.
