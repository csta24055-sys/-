# Stage B2 - approximation study (measurement fixes and missing candidates)

Read COMMON.md, then TRIAGE/approx.md completely and REP-5, REP-6, REP-13, REC-8 in the
other triage files, then `bench/approx_study.py` (all of it), `tools/build_records.py`
(function `conclusions` and the candidate plan: they consume your output; a later stage
edits that file, not you), `04_VERIFICATION/approximation_study.json` (current schema).
Stage A1 has just changed `refcalc` (exact time arithmetic: periodic events are now handed
over as event years; new validity rules); read
`/tmp/claude-0/-home-user--/49c0bd7e-a786-5ae4-9a1e-e89e7996ede3/scratchpad/recheck/fix/A1_REPORT.json`
and adapt `bench/approx_study.py` to the new reference API first.

Scope: APP-1..APP-9, REP-5 (measurement side), REP-6, REP-13 (unit lists), REC-8 (the
missing measurement).

Files you may change: `bench/approx_study.py` (and new helper modules under `bench/` if it
gets too long). Nothing else. Add `--out PATH` (default: the current output file) and keep
`--population`. When you test, ALWAYS pass `--out` under your scratch folder.

Keep in mind what the study is allowed to say: every number here is measured on fictional
data; it can refute a candidate but cannot establish practical accuracy.

## Changes

1. APP-2 (reference quantity and labels). Measure electricity candidates (AP-08, AP-09a,
   AP-09b, AP-09c, AP-13 and any other candidate acting on purchased electricity) against
   the real stage values of X-02: stage B6 and stage B2 separately, and unit B6-01 /
   B6-03 where the candidate is attached to those units; keep the B6-03 figure under a
   label that says what it is ("B6-03 = B6 + B2"). `within_stage_target` is decided on the
   WORST affected stage. AP-18c / AP-18: report C3 and C4 separately (stage C3 includes
   equipment disposal X-14) besides the merged figure, labelled for what it contains.
2. APP-3 (propagated totals). `total_error` stays the local difference divided by the
   whole-life total but is named for what it is (`local_total_error`). For candidates that
   change a quantity reused downstream (at least AP-06, AP-07a, AP-07b, AP-17, AP-19a,
   AP-19b; AP-18c if feasible), ALSO measure `propagated_total_error`: rewrite a copy of
   the scenario so that the reference itself computes with the approximated input and take
   SUM-03 (and the per-stage knock-on errors). `within_total_target` uses the propagated
   figure where it exists. State for each candidate which of the two it has.
3. APP-1 (missing candidate). Add the safe-side repair candidate
   "repair years = T - min(T, max(0, T/c - 1))" (explicit lists exact) in row-level form and
   in class-parameter form; measure it on the population AND on stress scenarios with
   fictional lives near the study period (e.g. `service_life_choices` = [29] at T=30,
   [9.9, 14.9, 29] at T=30, [7, 11, 13, 17, 23] at T=30, [49, 24.5] at T=50, 20 seeds each)
   and report both; record that the sign guarantee holds only for cycles >= 1 year.
   Do not describe it as "meets the targets": the verifier showed +3.3 % on such lives.
4. APP-9 (in-sample parameters). Mark AP-18a/b/c, AP-19a and the class form of item 3 with
   `parameters_from: "same building (in-sample)"`, and AP-19a with `keeps_row_membership:
   true`. Add out-of-sample variants measured with the same train/test split the study
   already uses for AP-10 (class parameters pooled from the training half, applied to the
   test half) for AP-18b and for the class form of item 3; add AP-19a with one ratio for
   the whole bill. Candidates that already use a split get `parameters_from: "other
   buildings (train/test split)"`.
5. APP-6 (AP-05). Measure both variants and name them: (A) consistent linearisation (leak
   m0*r*k, remaining mass m0*max(0, 1 - r*k)), (B) "every device treated as topped up" (the
   variant measured so far). Report the per-device guard buckets for both.
6. APP-7. `add_classes` counts (scenario, class) pairs dropped because the reference is 0,
   and separately those where the candidate is not 0; the result carries both counts.
   Give every scenario-level collector the same pair of counts.
7. APP-8 (AP-14). Report the result separately for scenarios whose own study period is
   >= 75 years and < 75 years, and measure once with explicit lists continued beyond the
   scenario's own period (equipment by its service life, refrigerant devices by the mean gap
   of their own list) so that the effect of the truncated lists is a measured number.
8. APP-5. Record for AP-01 / AP-20 the bound as it holds under the (now exact) rule:
   N >= T*c/L - 1 with c = 1 - 1e-9, i.e. the lower bound holds up to the relative 1e-9
   boundary tolerance; add a scenario with a life just below a divisor of T
   (e.g. 19.99999999 at T=60) to the bracket test and report what it gives.
9. APP-4 (AP-17). Measure and store the identity: the error of the simple mean distance
   equals the within-mode sample covariance of mass and distance (report the worst residual
   of the identity), and the realised within-mode correlation statistics.
10. REC-8. Add a measured candidate for annual quantities given as year tables (fuel, water
    etc.: B6-02, B7-01..03): keep every 5th year and interpolate linearly (the analogue of
    AP-09c), error on the stage (B6, B7) and on the unit's own weighted total; and the same
    for the electricity consumption table if not already covered.
11. REP-5 / REP-13 (what a candidate was measured on). Each candidate declares
    `scope`: "UNIT" (uses the unit's own formula and is measured on that unit's own output),
    "STAGE" (measured on a stage total) or "BUILDING" (does not use the unit's formula at
    all, e.g. AP-15 floor-area intensity), and `units` = exactly the units on whose OWN
    output it was measured; `units_stage_level` = further units of the stage it says
    something about only through the stage total. Where a candidate is attached to a unit
    whose own output was not measured (AP-08 on B2-01 and B6-04, AP-05 on B1-03 / B1-04,
    others you find), measure that unit's own output or move it to `units_stage_level`.
    This file becomes the single source of the unit attachment.
12. REP-6 (load and inputs of candidates). For each candidate record
    `inputs`: what it needs versus the exact form, as counts where they can be computed
    from the scenario (e.g. AP-09c: values per series before/after; class models: number of
    parameters vs number of rows) and as a short text otherwise, flagged
    `inputs_measured: true|false`. For the candidates whose rejection says "the exact
    closed form costs the same" (count forms AP-01..03, AP-04 and the item-3 candidate,
    AP-05, AP-08, AP-09a/b, others you find) measure executed bytecode instructions of the
    candidate kernel and of the exact closed form on the same rows (`sys.monitoring`, as in
    `bench/verify_unified.py`) and store both. Add the by-material-class breakdown for the
    row-level candidates that lack it (AP-04, AP-12, AP-17, AP-18b, AP-18c, AP-19a,
    AP-19b) or store `by_material_class: null` with the reason.
13. Keep everything that already exists and was reproduced by the checkers (they reproduced
    every published statistic). If a published number changes for a reason other than the
    items above (e.g. the exact time rule), list it in your report with old and new value.

## Acceptance

a. Unit tests pass.
b. Full run with `--population 400 --out <scratch>/approximation_study.json` completes;
   report run time. Compare with the committed `04_VERIFICATION/approximation_study.json`:
   list every candidate statistic that changed and why.
c. Your report contains the schema of the new JSON (new keys, renamed keys) and, for each
   candidate, one line: scope, units, worst-stage target flag, total target flag (local or
   propagated), under-estimation share, and whether your measurement supports the
   conclusion text currently in `tools/build_records.conclusions` (quote the ones that
   need rewording and propose the corrected sentence in Japanese, plain style).
