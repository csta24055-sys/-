# Stage C (orchestrator): records, ledger roll-up, reports, hand-written documents

Done by the orchestrator after workflow wf_47846e85-a79 (stages a1, a2, b3, b2 + verify/fix loop).
Inputs: fix/A1_REPORT.json, A2_REPORT.json, B2_REPORT.json, B3_REPORT.json, FIX*_REPORT.json, VERIFY*_FINDINGS.json.
Triage of round 2: recheck/triage/{numeric,rederive,records,approx,reports}.md

## tools/build_records.py
1. Evidence of an EX record (REC-5, REP-3):
   (1) output equality (unified_model_exactness.json);
   (2) M2: membership evidence from 04_VERIFICATION/membership_check.json - the unit's public result changes when
       the shared object of its model is broken (fault injection). MODELS[k] gets "shared_objects". Build FAILS if an
       M2 SUCCESS has no such evidence. Units that are not sensitive -> not unified (M2 = NOT_APPLICABLE with reason).
       Expected outside: A13-05, X-13, SYS-03 (+ whatever a2 reports). B1-01 only if the device table is real.
   (2') M1: mechanism = statement P1..P7 of 04_VERIFICATION/mechanism_probe.json (global, measured, labelled as
       "全体の測定（単位ごとではない）"); for closed-form M1 records add "detected_by" = units that fail when the closed
       form is broken (REC-6) instead of quoting the unit's own leaf count.
   (3) derivation in DERIVATIONS.md.
   verification = VERIFIED_ANALYTIC_AND_SYNTHETIC only with (1)+(2 or 2')+(3); else VERIFIED_SYNTHETIC_ONLY.
   The note in records/units.json states the actual counts (computed), not "all three for every record".
2. Titles (REC-7): A5-01 M1 -> NOT_APPLICABLE (single scalar x grid factor, already minimal), M2 formal ->
   decide from membership_check; QA-03 M1 "排出の表に現れる係数キーから得る"; B4-02 M1 add "明示の更新年一覧を持つ行は行ごと";
   B1-01 / D6 wording per a2.
3. NA reasons (REC-8, REP-14): B6-04 M4 own reason; NA_HYBRID only where an M1 record exists and the exact form
   is input independent; operation units: "記述子なら閉形式、年次表なら走査（どちらも厳密）" + the new table-interpolation
   candidate from b2; units without M1 record get a reason without "M1 に記録した".
4. AP attachment single-sourced from approximation_study.json (`units`, `units_stage_level`, `scope`): plan's AP
   lists must equal it (assert); records carry `evidence_scope` UNIT / STAGE / BUILDING (REP-5, REP-13).
5. conclusions(): reword per b2 report (AP-01/20 bound up to 1e-9; AP-03 mention zero-reference cases; AP-05 two
   variants; AP-09c worst stage B2; AP-17 covariance identity; AP-18a-c / AP-19a in-sample; AP-14 subsets; new
   candidates). Stage labels: say B6-03 where it is B6-03.
6. Judge trace (REP-2): criteria per protocol P5: b1->M1; b2,b3,b4->M2; b5,b6->M3; b8->M4 (also M5);
   b7 (inputs) -> any measured candidate in M3..M6. Report per criterion.
7. REC-9: "検査の 3 単位" computed; table read-out count named for what it is.

## tools/progress_ledger.py
- step conclusion keeps precedence; add per-step `evidence_scope` so that HOLD through a BUILDING-level surrogate
  only is shown as such; status_note counts unit-specific vs building-level holds (REP-5).

## tools/build_reports.py
- REP-1 (input usage sentence from measured lists), REP-7 (05 table: declared vs measured rows), REP-8, REP-9,
  REP-11 (ranking wording: A 22, plus 6 sensitivity-only, B 30, union 42 (A|B = 38)), REP-12, REP-13 (AP-06b flag),
  REP-15, REP-16 (sweep scope), REP-18; headline: unified count from membership evidence + how many units have the
  same form already in the reference (REP-4); approximations: unit-specific vs building-level (REP-5); load and
  inputs of candidates (REP-6); new sections for membership_check and mechanism_probe; exactness with floor 0.

## Hand-written
- 03_MODELS/DERIVATIONS.md: D2/D3 with exact arithmetic (q = L*c >= 1 <=> distinct years; proof), D6 last line,
  D8 (what is memoised), "導出が当てはまらない範囲".
- 00_POLICY/EVALUATION_PROTOCOL.md -> v1.4: P3/P4 (a2 = executed bytecode instructions; unmeasured rule unused),
  P7 vocabulary (remove or map), P8 evidence rules as in 1 above, membership by fault injection.
- 06_OPEN_ISSUES/README.md: B-11 (+ material initial installation, 41.1 % of A5 / 0.096 % of SUM-03 on S - re-measure),
  B-15 (exact arithmetic), B-17 (data-flow completeness), B-18 (+ annual values, grid, factor value, conversion;
  clamp is a definition), new: A13-04 uplift not in B3/B4 but in B5 (+0.54 % B4, +3.93 % B3 on S - re-measure),
  invalid periods, duplicate explicit years, no error except period; D-3/D-4 (conditioning limits NUM-10 a,c,d,e;
  wrong types out of scope), G (what was not done), second-round review status.
- 04_VERIFICATION/INDEPENDENT_REVIEW.md: section for round 2 (59 findings: table of ids -> disposition) and for the
  verify/fix loop (what the third-party checkers of the fixed code found); remove "まだ行っていない".
- research_code/README.md, synth/README.md: commands, new bench files.

## Regeneration order (quiet machine, nothing else running)
tests -> tools.sync_ledger -> bench.measure_axis_a -> tools/rank_axes.py -> bench.verify_unified ->
bench.membership_check -> bench.mechanism_probe -> bench.input_usage -> bench.approx_study -> tools.build_records ->
progress_ledger init/merge/check/report -> tools.build_reports -> scripts/validate_registry.py -> forbidden-file scan
