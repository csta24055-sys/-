# Common rules for every agent of the round-2 fix

## What this is

A research study (not a product) on computing building whole-life carbon with few, simple
formulas. It lives in

    STUDY = /home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY
    CODE  = STUDY/research_code          (Python 3, standard library only)

`refcalc/` is the **reference calculation**: one literal function per evaluation unit; the
function's docstring is the binding definition of the unit (synced to
`01_LEDGER/units.json` -> `reference_semantics`). `fastcalc/` is the **unified model**
(`closed_forms.py`, `engine.py`); it must return the same results as the reference and must
NOT import `refcalc` (the rules are restated on purpose). `synth/` generates fictional
scenarios. `bench/` holds measurements, `tools/` generators of records and reports.

An independent re-check (five lenses, each finding attacked by a second agent) produced 59
findings. They are in

    TRIAGE = /tmp/claude-0/-home-user--/49c0bd7e-a786-5ae4-9a1e-e89e7996ede3/scratchpad/recheck/triage
    numeric.md   (NUM-1..11)   unified model vs reference on adversarial inputs
    rederive.md  (RED-1..12)   reference vs its written definitions
    records.md   (REC-1..9)    records vs code
    approx.md    (APP-1..9)    approximation study
    reports.md   (REP-1..18)   reports vs data / directive

Each finding has the checker's text, then `--- VERDICT` with the verifier's reasoning and a
`CORRECTED:` statement. **Where the two differ, the CORRECTED statement is the one to act on.**
The checkers' reproduction scripts are in
`/tmp/claude-0/-home-user--/49c0bd7e-a786-5ae4-9a1e-e89e7996ede3/scratchpad/recheck/<lens>/`
and `.../<lens>_verify/` (read them, reuse them; they were written against the code before
your change, so adapt copies of them, do not edit the originals).

## Hard rules

1. Work only on the files your spec lists. Do not touch anything outside STUDY, do not
   touch `STUDY/../01_*` .. `08_*` chapters, other research folders, or `main`.
2. **No git commands that change anything** (no add / commit / push / checkout / stash /
   reset). The orchestrator commits. `git status` and `git diff` are fine.
3. Compliance: all data are fictional. Never add real emission factors, service lives,
   repair rates, leakage rates, or any J-CAT content (numbers, formulas, macro logic), and
   never recall them from memory or the web. Never write that anything is compatible with,
   equivalent to, or verified against J-CAT or any other tool. No UI / web / API code.
4. Honesty: do not claim what you did not run. A check on fictional data is not evidence of
   accuracy on real buildings. If something in your spec turns out wrong or impossible, say
   so in your report instead of working around it silently.
5. Run Python as `python3 -B` from CODE with `PYTHONPATH=.` (no `__pycache__` in the repo).
6. **Do not run the generators that overwrite study outputs** (the orchestrator regenerates
   everything at the end on a quiet machine): `bench.verify_unified` (as a program),
   `bench.approx_study` (as a program writing its default output), `bench.measure_axis_a`,
   `bench.input_usage` (default output), `tools.build_records`, `tools.build_reports`,
   `tools/progress_ledger.py`, `tools/rank_axes.py`. Import their functions, or run them
   with an output path under your scratch folder. `python3 -B -m tools.sync_ledger` IS
   allowed where your spec says so.
7. Your own scripts and outputs go under
   `/tmp/claude-0/-home-user--/49c0bd7e-a786-5ae4-9a1e-e89e7996ede3/scratchpad/recheck/fix/<your label>/`.
8. Tests: `cd CODE && python3 -B -m unittest discover -s tests -t .` must pass when you finish
   (add tests for what you change).
9. Style: unit docstrings in `refcalc` are Japanese, plain declarative ("〜する。〜である。"),
   and are the binding definitions; keep that style and keep them accurate to the code.
   Code comments and module docstrings are English. No model names anywhere in files.
10. Other agents may be editing OTHER files of the same working tree at the same time. Do
    not "fix" a file that is not yours; report the problem instead.

## Final report (your return value)

Return the structured object asked for. Be exact:
- every file you created or changed;
- for every finding id in your scope: FIXED / DOCUMENTED_ONLY / NOT_DONE, in one or two
  sentences what you did and how you checked it (command + observed result);
- every decision you took where the spec left a choice, and every place where you deviated
  from the spec, with the reason;
- new or renamed result keys, function names, CLI options and JSON fields that later stages
  (records, reports) need to know;
- test command and its actual final output line; anything still failing or unverified.
