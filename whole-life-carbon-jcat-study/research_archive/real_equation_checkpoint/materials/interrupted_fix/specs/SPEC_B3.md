# Stage B3 - ledger: inputs actually read, counts, sheet-family labels

Read COMMON.md, then REP-1, REP-7, REP-8, REP-10 (the A13-04 part), REP-18 in
TRIAGE/reports.md, then `bench/input_usage.py`, `tools/sync_ledger.py`,
`01_LEDGER/units.json` (structure; it is partly hand-written, partly synced),
`01_LEDGER/unlinked_input_disposition.json`, `01_LEDGER/sheet_family_coverage.json`,
`04_VERIFICATION/input_usage.json`, `tools/build_reports.py` (functions `ledger_report`,
`verification_report`, `decisions_report`: they consume these files; a later stage edits
that file, not you) and how `synth/model.py` maps dataclass fields to input-spec ids.
Stages A1 and A2 have just changed `refcalc` and `fastcalc`; read
`.../scratchpad/recheck/fix/A1_REPORT.json` and `A2_REPORT.json`.

Files you may change: `bench/input_usage.py`, `tools/sync_ledger.py`,
`01_LEDGER/units.json`, `01_LEDGER/unlinked_input_disposition.json`,
`01_LEDGER/sheet_family_coverage.json` (only through the rule in item 4, by script),
`tests/` (new tests). Nothing else.

## Changes

1. REP-7 (inputs per unit, measured). Extend `bench/input_usage.py` so that it also traces
   the attribute reads of the reference calculation **per unit** (the registry runs units
   one by one: mark the current unit while its function runs) on enough fictional scenarios
   to exercise every branch (benchmark S, the edge cases, some defective ones). Output per
   unit: the specified inputs (spec ids) and the study-added fields it read.
   `tools/sync_ledger.py` writes them into each unit of `01_LEDGER/units.json` as
   `inputs_read_by_reference` (sorted) and keeps the hand-declared `inputs` untouched but
   adds `inputs_declared_not_read` and `inputs_read_not_declared` so that the difference is
   visible; `n_inputs` stays the declared count and a new `n_inputs_read` is added.
   Where a declared "NEW:" name does not correspond to any field of `synth/model.py`,
   list it (do not invent a mapping).
2. REP-1. `input_usage.json`: replace the `metadata_only_inputs` figure that came from an
   unused sentinel by measured lists: specified inputs read by no calculation
   (`specified_inputs_never_read`, with the ids), study-added fields never read, and the
   reconciliation with the ledger's classification in `unlinked_input_disposition.json`
   (for each of its entries: is it read by the reference or not?). Update
   `unlinked_input_disposition.json` so that its three classes agree with the measurement
   (an input classed "connected by an additional unit" or "implicitly used" that is never
   read must be reclassified, with a short reason); keep its authorship note honest.
3. REP-8. `structure_class_counts` in the header of `units.json` is computed from the
   units by `tools.sync_ledger` every time.
4. REP-18. Sheet-family status by rule, applied by `tools.sync_ledger`:
   a family with zero formula nodes is NON_CALCULATION whatever units name it;
   otherwise COVERED_BY_ADDITIONAL if any related unit is an additional (X-..) unit and no
   existing unit is related, COVERED_BY_EXISTING if only existing units are related,
   COVERED_BY_BOTH if both kinds are related, NOT_INSPECTED if no unit is related.
   (If the file already uses other status names, keep the names and add what is missing;
   report the before/after table of families and node counts per status.) Remember the
   label of NOT_INSPECTED families: no correspondence can be inferred from the name and the
   original formulas were not inspected - nothing here may suggest that any original
   workbook content was read.
5. REP-10 (A13-04). In `01_LEDGER/units.json`, unit A13-04 still says it is not implemented
   in the reference although `computable_in_reference` is true and a reference function
   exists (an uplift model designed independently by this study). Correct the hand-written
   fields (`structure_subclass`, `not_computable_reason`, `ambiguities`, any text saying
   "基準計算には実装しない") so they describe the present state: the model is this
   study's own design, it is implemented in the reference, and it has no counterpart whose
   accuracy could be compared.
6. Run `python3 -B -m tools.sync_ledger` at the end (allowed) and
   `python3 -B -m bench.input_usage --out <scratch>/input_usage.json` (add `--out`).

## Acceptance

a. Unit tests pass (add one that fails if `structure_class_counts` or the per-unit read
   lists are stale relative to a fresh trace on benchmark S).
b. Report: the new JSON fields; counts (specified inputs read / never read, added fields
   read / never read, per-unit totals); the reclassified entries; the sheet-family
   before/after table; anything in `tools/build_reports.py` that will now print a wrong
   sentence or number (quote the line and propose the corrected Japanese sentence).
