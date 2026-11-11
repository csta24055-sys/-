# Verification V-DEF: does the reference calculation do what its definitions say - and do the
# definitions still have holes?

You are an independent checker. You did not write this code. After the round-2 fixes, find
(a) places where a unit's binding text (the docstring in `refcalc`, identical to
`reference_semantics` in `01_LEDGER/units.json`) and the code differ, (b) inputs for which a
total is wrong or silently partial while every flag says it is fine, (c) inputs that raise
although the conventions say only an invalid study period may raise, (d) conventions the
code follows that the convention docstring of `refcalc/base.py` does not state.
Default to distrust.

Read COMMON.md (rules 1-7 and 9 apply; you change NO file of the repository at all),
`A1_REPORT.json` (claims of the fixer), `SPEC_A1.md` (what was asked), TRIAGE/rederive.md
(the earlier findings RED-1..12 with scripts under `.../recheck/rederive/` and
`.../recheck/rederive_verify/`), then the code.

Do, at least:
1. For each of RED-1..RED-12 (using the CORRECTED statements): re-run the reproduction
   adapted in your scratch folder and state resolved / not resolved / changed, with output.
2. Completeness by data flow: for EVERY stage and for boundaries that include the stage
   without its upstream stages, inject one defect at a time into each kind of upstream input
   (missing / negative / NaN quantity, unknown / unlicensed / wrong-stage / wrong-unit /
   NaN-valued factor, invalid cycle, invalid annual value, invalid grid, invalid ratio,
   missing route factor ...) and check: whenever the stage value changes because something
   was left out, `complete` is False and the responsible unit is in `incomplete_units`;
   and the reverse: `complete` is not False for a defect that cannot touch any included
   stage. Check SUM-08 with incomplete totals and unknown baseline ids.
3. Exact time rule: re-derive event counts and event years from the rule text with
   `fractions.Fraction` for periodic and explicit events and compare with the reference on
   knife-edge periods; check that B4, B3 (skip years), B5, B1 and X-07 use the same years.
4. Validity rules: for every numeric input class named in `refcalc/base.py`, check that
   None / NaN / +-inf / negative / out-of-range values are left out and counted, never used
   and never raising; look for numeric inputs the docstring does not name.
5. Text vs code for every unit whose docstring changed (diff `01_LEDGER/units.json` against
   `git show HEAD:whole-life-carbon-jcat-study/09_APPROX_STUDY/01_LEDGER/units.json`), and a
   sample of 15 unchanged units: re-implement from the text alone where feasible (the
   earlier checker's `mine.py` is a starting point) and compare on the edge cases, the
   mutations and stage subsets.
6. Anything the fix made worse: a convention that now contradicts
   `06_OPEN_ISSUES/README.md` section B (B-1..B-21), an output key that disappeared, a count
   that changed meaning.

Report only what you ran, with minimal reproductions (script path + command + numbers), and
what you could not check.
