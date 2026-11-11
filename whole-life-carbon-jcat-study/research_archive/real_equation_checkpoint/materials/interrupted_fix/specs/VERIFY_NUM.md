# Verification V-NUM: does the unified model still equal the reference - on every input?

You are an independent checker. You did not write this code. Your job is to find inputs for
which `fastcalc.engine` (full outputs and totals-only, and `sweep`) and
`refcalc.registry.run_all` disagree, or where one raises and the other does not, AFTER the
round-2 fixes. Default to distrust: a claim is only as good as the input that could break it.

Read COMMON.md (rules 1-7 and 9 apply; you change NO file of the repository at all), the
two reports `A1_REPORT.json` and `A2_REPORT.json` in the same folder (what the fixers say
they did - treat as claims), `SPEC_A1.md` (what they were asked to do), TRIAGE/numeric.md
(the earlier findings NUM-1..11 with reproduction scripts) and the code.

Do, at least:
1. Re-run every earlier reproduction (`.../recheck/numeric/repro_findings.py`, `t1.py`,
   `t6.py`, `t7.py`, `t9.py`, `t10.py`, `t12.py`, `t14.py`, `fuzz1.py` + `fuzzlib.py`,
   `cfbrute.py`, `cfbrute2.py`; the verifier's `.../recheck/numeric_verify/v1.py..v7.py`),
   adapted in YOUR scratch folder to the changed API. State for each of NUM-1..NUM-11:
   resolved / not resolved / changed into something else, with the observed output.
2. Closed forms against a literal loop written by you with `fractions.Fraction` from the
   rule text in `refcalc/base.py` (not from the code): at least 2,000,000 (T, period) pairs
   including knife-edges (periods T/n*(1 +- eps) for eps in 1e-15..1e-6 including 1e-9 and
   2e-9, m*(1 +- 1e-9), the neighbourhood of 1/(1 - 1e-9) and of 1.000000001 by ulps,
   periods far below one year, T non-integer, T just above / below an integer by ulps),
   explicit lists (duplicates, entries by ulps around integers and around T*(1-1e-9)),
   refrigerant cycles, weighted sums and grid moments (also T barely above an integer).
3. Random multi-defect fuzz with a strict comparison (relative 1e-9, NO floor; inf, NaN,
   bool/int and extra/missing leaves are differences): at least 20,000 scenarios, 0-10
   mutations each, over all the mutators of `fuzzlib.py` plus new ones for everything
   Stage A1 added (invalid cycles, invalid annual values, grid validity, factor value /
   gas amount validity, conversion validity, pseudo-id collisions, gas-list defects,
   stage subsets combined with upstream defects, baselines with defects, held baseline
   totals).
4. The single-field sweep (every numeric leaf -> nan, +inf, -inf, None, negative, zero,
   1e308, 5e-324) on several scenarios, and a two-field sweep on a sample.
5. Self-consistency of the unified full output (sum of a by_year series equals the unit
   value; X-07 final cumulative equals SUM-03; QA-01) on the inputs where the earlier
   version was inconsistent.
6. `sweep` and re-finishing one Aggregate for many periods, with defects present.
7. The reduced study verification: import `bench.verify_unified` and run `exactness(400, 60)`
   and `sweep_check(40)` from a scratch script WITHOUT writing the study's files (this takes
   a while; run it once, in the background if needed). Report failures, the largest error
   and its path.

Report only what you ran. For every disagreement give a minimal reproduction (script path
under your scratch folder + exact command + the two numbers). Say explicitly what you could
not check. If you find nothing, say what you tried that could have found something.
