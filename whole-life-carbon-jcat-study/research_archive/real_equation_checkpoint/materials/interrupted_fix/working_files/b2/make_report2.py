"""Compact final report (the long first version is kept as B2_REPORT_long.json in this folder)."""
import json, sys
sys.path.insert(0, ".")
import proposals
R = "/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/research_code/"
S = "/tmp/claude-0/-home-user--/49c0bd7e-a786-5ae4-9a1e-e89e7996ede3/scratchpad/recheck/fix/b2/"
C = json.load(open("approximation_study.json", encoding="utf-8"))["candidates"]
V = {"SUPPORTED": "OK", "REWORD": "REWORD", "NEW": "NEW"}
f = lambda x: "-" if x is None else ("T" if x else "F")
lines = []
for cid, c in C.items():
    s = c.get("stage_error") or c.get("row_error") or {}
    ws = c.get("worst_stage")
    if ws: worst = f"worst {ws['stage']} {100*ws['max_under']:+.1f}..{100*ws['max_over']:+.1f}%"
    elif s.get("n"): worst = f"primary {100*s['max_under']:+.1f}..{100*s['max_over']:+.1f}%"
    else: worst = "bracket"
    t = c.get("propagated_total_error") or c.get("local_total_error") or {}
    tot = f"{(c['total_error_kind'] or '-')[0]} p95 {100*t['p95_abs']:.2f}%" if t.get("n") else "-"
    under = f"{100*s['share_under_estimated']:.1f}%" if s.get("n") else "-"
    lines.append(f"{cid} {c['step']} {c['scope']} | u={','.join(c['units']) or '-'} | sl={','.join(c['units_stage_level']) or '-'} | {worst} st={f(c.get('within_stage_target'))} | tot {tot} {f(c.get('within_total_target'))} | under {under} | {V[proposals.P[cid]['verdict']]}")
SHORT = {
 "AP-01": "「基準を上回ることがなく」→「候補が基準を上回るのは相対 1e-9 の範囲に限られる（N = ceil(T·c0/c) − 1、c0 = 1 − 1e-9。架空の例で +7.5e-10）」",
 "AP-03": "「B5 で平均 +42.7％」→「B5 では基準が 0 でない 89 シナリオの平均が +42.7％ で、ほかに基準が 0 回なのに排出を計上する場合が 133 件ある」",
 "AP-04": "「厳密な閉形式（K2）が同じ手間で使えるため不採用」→「段階 2％ の目標を超えるため不採用。計算は候補のほうが軽い（行ごとの命令数 14 対 112）が、更新周期は更新（B4）の計算に要る入力で、建物の入力は減らない」",
 "AP-05": "式は整合的な線形化、数値は全機器を補充ありとして扱う変種のもの。AP-05a（B1 平均 +23.9％、最大 +164.3％。B1-03・B1-04 は単独では過小）と AP-05b（平均 +28.0％、最大 +180.7％）の 2 件に書き分け、「同じ手間」は「命令数は厳密な閉形式の約 0.7 倍／0.4 倍」とする",
 "AP-08": "「B6 段階で -8.0％〜+11.6％」の後に「買電だけからなる B2 段階（B2-01）と B6-01 では -9.7％〜+14.9％」を加え、「命令数も候補のほうが多い（約 1.1〜1.35 倍）」とする",
 "AP-09a": "「直線低下では B6 段階で最大 +0.6％・B2 段階で最大 +1.1％、段階的な系列では B6 段階で -3.9％〜+3.6％、B2 段階で -5.6％〜+5.3％」。記述子の系列では補間の点のほうが多く（14.2 個対 6.5 個）、命令数も約 3.4 倍",
 "AP-09b": "「10 年刻みでは B6 段階で -5.2％〜+7.4％、B2 段階で -7.6％〜+12.7％」",
 "AP-09c": "「段階 2％ の内側」→「B6 段階では 2％ の内側（-1.3％〜+1.7％）だが、B2 段階と B6-01 では -1.9％〜+2.0％（最大 +2.03％）で 2％ をわずかに超える。入力は平均 60.6 個から 13.2 個に減るが、命令数は約 2.6 倍になる」",
 "AP-13": "「B6 段階で -14.7％〜+69.9％、B2 段階と B6-01 で -19.9％〜+150.5％」",
 "AP-17": "「重い資材ほど遠くから運ぶ傾向が実際にあるかどうかで結果が決まる」→「誤差は輸送手段内の質量と距離の標本共分散に等しい（恒等式）。距離を質量と独立に生成した架空データでも、偶然の共分散だけで A4 段階が -37.2％〜+116.6％ ずれるので、距離または質量がほぼそろう場合のほかは使えない。平均距離は同じ建物の行から作っている」",
 "AP-18a": "「代表周期を評価する建物自身の行から作った場合（最良の場合で、入力は減っていない）でも」を加える",
 "AP-18b": "「（…段階 2％ の内側）」→「代表値を建物自身の行から作った場合の値で、他の建物から与えると（AP-18d）-40.8％〜+327.6％ になる。過小は AP-23b の形で避けられるが、その形は周期が評価期間に近いと過大が 2％ を超える」",
 "AP-18c": "「C3＋C4 で」→「C3-01＋C4-01（資材のみ）で -29.2％〜+40.2％、段階別には C3（設備の廃棄 X-14 を含む）で -34.9％〜+42.8％、C4 で -38.6％〜+118.2％。代表値は建物自身の行から作っている」",
 "AP-18": "「B3＋B4＋C3＋C4 の合計」→「B3＋B4＋C3-01＋C4-01 の合計」。「ホールライフ合計に対して」→「ホールライフ合計に対する局所の差は（更新・建替へ波及させた値ではない）」",
 "AP-19a": "「どの行が比率を持つかはそのまま使い、平均も建物自身の行から作った場合でも -50.1％〜+277.9％（建替へ波及させた合計に対して 95 パーセンタイル 0.3％）。全行に 1 つの比率を使う形（AP-19c）では -92.2％〜+1046.1％」",
 "AP-20": "「基準値は必ずこの上下限の間に入る」→「基準値は上限を超えず、下限を下回るのは相対 1e-9 の範囲に限られる（母集団 400 件はすべて上下限の間。周期が約数を相対 1e-9 以内で下回る架空の例を加えると 401 件中 400 件）」",
}
NEW = {cid: v["suggested_outcome"] for cid, v in proposals.P.items() if v["verdict"] == "NEW"}
findings = [
 ("APP-1", "PARTLY_FIXED", "Added AP-23a (rows, M3), AP-23b (class parameters of the same building, M4), AP-23c (class parameters from other buildings); stress scenarios and sign_guarantee stored; within_stage_target counts the stress scenarios (false). Conclusion text and candidates.json: later stage.",
  "Full run: AP-23a B3 mean +0.297% p95 0.715% max +1.438%, 0/400 under; AP-23b +0.330% / 0.834% / +1.455%; stress T=30 [29] +3.33%, [9.9,14.9,29] +3.38..+3.53%, [7,11,13,17,23] +1.14..+2.33%, T=50 [49,24.5] +2.00% (all equal to the verifier's v1_400.log / v2.log); AP-23c -39.4%..+329.1%."),
 ("APP-2", "PARTLY_FIXED", "Electricity candidates are measured on stage B6 (primary), stage B2 and the attached units' own outputs; the old B6-03 figure is kept under a label; within_stage_target uses the worst stage. AP-18c / AP-18: C3 and C4 separately, merged figures labelled. Texts quoting 'B6 段階': later stage.",
  "Full run: AP-08 B6 -8.00..+11.64%, B2 -9.69..+14.89% (p95 5.75%); AP-09a B2 -5.56..+5.30%; AP-09c B6 -1.313..+1.719%, B2 -1.855..+2.027% -> within_stage_target false; AP-18c C3 -34.9..+42.8%, C4 -38.6..+118.2% (equal to the verifier). Old B6-03 statistics identical (cmp_old_new.py). xcheck_tables.py: reference re-run on the coarse grid table agrees within 1.8e-15."),
 ("APP-3", "PARTLY_FIXED", "total_error renamed local_total_error; propagated_total_error (reference re-run on the rewritten scenario) and knock-on stage errors for AP-06, 07a, 07b, 17, 18c, 19a, 19b, 19c; within_total_target uses the propagated figure; total_error_kind / downstream_reuse say which a candidate has. README column wording: later stage.",
  "Full run: AP-06 propagated mean -0.149% p95 0.284% max -0.655%, B3 max -1.179%; AP-07b -4.338..+2.560% p95 1.203%; AP-17 -1.968..+1.932% p95 0.574%; AP-18c max +0.774% (equal to the checkers). Rewrites reproduce the local candidate value within 4.9e-15. edge_robust.py: 39 edge/defective scenarios, no exception, scenarios restored."),
 ("APP-4", "PARTLY_FIXED", "AP-17 stores covariance_identity and realised_within_mode_correlation, own outputs of A4-01 / X-12 / C2-01 and the propagated total. Reason text: later stage (proposal below).",
  "Full run: identity residual <= 3.3e-15 over 400 scenarios; realised r mean +0.0247 (-0.407..+0.541); correlation with the scenario error -0.822; sign agreement 92.25% (verifier: +0.025, -0.41..+0.54, -0.82, 92.2%)."),
 ("APP-5", "PARTLY_FIXED", "AP-01 / AP-20 carry 'bound' (T*c0/c - 1 <= N < T*c0/c, c0 = double nearest 1 - 1e-9) and the near-boundary scenario; AP-20 title no longer says '必ず成り立つ'. Reason texts: later stage.",
  "Full run: life 19.99999999 at T=60: counts [2], B4 864789.9342628843, lower bound 864789.9349114769 (+7.5e-10); inside false with T/c-1, true with T*c0/c-1 (same as the verifier). Population 400/400 inside; 400/401 with the scenario."),
 ("APP-6", "PARTLY_FIXED", "AP-05 split into AP-05a (consistent linearisation) and AP-05b (every device treated as topped up = the published numbers, renamed_from AP-05); own outputs of B1-02/03/04 and guard buckets for both. Texts: later stage.",
  "Full run: AP-05b = committed AP-05 bit for bit (mean +28.023%, max +180.71%); AP-05a mean +23.894% p95 93.63% max +164.35%; buckets 0.05-0.2: A +0.62..+7.41%, B +1.48..+17.01% (equal to the verifier). New: AP-05a under-estimates the units B1-03 (to -98.6%) and B1-04 (to -90.5%)."),
 ("APP-7", "PARTLY_FIXED", "Every error series counts n_reference_zero and n_reference_zero_candidate_nonzero (per class too, summed in by_material_class_zero_reference). AP-03 reason: later stage.",
  "Full run: AP-01/02/03 5595 class pairs, 850 with reference 0, candidate non-zero in 0 / 694 / 850; B5 133 reference-zero scenarios, non-zero in 0 / 128 / 133 (equal to the verifier)."),
 ("APP-8", "FIXED", "AP-14 has by_own_study_period and explicit_lists_continued; the note states that explicit lists end at the scenario's own period.",
  "Full run: own period >= 75 (n=34) -2.68..+11.80% p95 6.95%; < 75 (n=46) -11.93..+22.77% p95 14.12%; lists continued: p95 11.93%, -11.92..+22.97%; 2 scenarios with a list that could not be continued (equal to the verifier)."),
 ("APP-9", "PARTLY_FIXED", "parameters_from on every candidate (in-sample: AP-08, 12, 17, 18, 18a, 18b, 18c, 19a, 19b, 19c, 23b; split: AP-10, 10b, 11, 15, 16, 21, 22b, 18d, 23c); keeps_row_membership on AP-19a/b (true), AP-19c (false). New out-of-sample AP-18d, AP-23c (AP-10 split, per structure x use) and AP-19c (one ratio for the whole bill). Reason texts: later stage.",
  "Full run: AP-18d -40.76..+327.64% p95 50.25% (verifier -40.7..+327.6%, 50.3%); pooled over all training buildings -41.2..+336.8% (verifier same); AP-19c -92.21..+1046.15% p95 228.9% (verifier -92.2..+1046%, 229%)."),
 ("REP-5", "PARTLY_FIXED", "bench/approx_meta.py declares scope, units, units_stage_level; the JSON repeats them with evidence_scope and by_unit (own outputs); the run fails on an undeclared or unmeasured unit. Own outputs added for 24 units; B6-04 (AP-08), A13-01/A13-03 (AP-10), X-17/A13-01/A13-03 (AP-10b), X-02 (AP-11/16) and 20 units of AP-15 are stage-level. Counts in PROGRESS / README: later stage.",
  "Full run: units_without_a_case_in_this_population = []; 124 attachments: 77 UNIT, 6 STAGE, 41 BUILDING; attachment sets of the 32 existing candidates equal 03_MODELS/candidates.json (script: 0 differ)."),
 ("REP-6", "PARTLY_FIXED", "inputs / inputs_measured for all 40 candidates (29 counted from the scenarios, 11 text); load = executed instructions of candidate kernel vs exact closed form on the same rows for 18 candidates (22 not measured, reason stored); by_material_class added for AP-04, 12, 17, 18b, 18c, 19a, 19b. Wall time and memory of candidates not measured.",
  "Full run, instructions per row candidate / exact: AP-01 47.0 / 63.0; AP-04 14.0 / 112.4; AP-23a 52.0 / 112.4; AP-05a 292.7 / 419.8; AP-05b 180.4 / 419.8; AP-06 16.1 / 16.1; AP-07b 134.4 / 86.9; AP-08 ratio 1.12 (closed) / 1.35 (scan); AP-09a 3.42 / 2.63; AP-24a 3.03. Exact kernels reproduce the reference within 1.6e-13; counts identical in four full runs."),
 ("REP-13", "PARTLY_FIXED", "approximation_study.json is the single source of the attachment. Differences resolved: AP-06 without X-13, AP-17 with C2-01, AP-18a with B4-01, AP-22a without X-05, AP-11/16 with X-02 (stage-level), AP-15 explicit 33 units; AP-06b has under_estimates (true). Generating candidates.json and the README cell: later stage.",
  "Script comparison of units + units_stage_level with 03_MODELS/candidates.json: same sets for all 32 existing candidates."),
 ("REC-8", "PARTLY_FIXED", "New AP-24a (year tables of fuel, water, sewage, waste: B6-02, B7-01..03; stages B6, B7) and AP-24b (electricity tables: B6-04, B6-01; stages B6, B2): every 5th year and the last, linear interpolation; descriptor profiles exact. NOT_APPLICABLE texts: later stage.",
  "Full run: AP-24a (173 scenarios) B7 -4.07..+2.14%, B6 -1.77..+1.37%, B7-03 -4.42..+2.84%; inputs 304.4 -> 65.6 values; instructions 3.03x. AP-24b (153) B6 -2.51..+3.04%, B2 -5.93..+4.56%. xcheck_tables.py: reference re-run on overwritten tables agrees within 1.2e-15 (60 scenarios)."),
]
decisions = [
 "Deviation: new test file " + R + "tests/test_approx_study.py (16 tests) although SPEC_B2 says 'nothing else' (COMMON rule 8).",
 "approx_study.py split into approx_meta.py (declarations), approx_measures.py (per-scenario measurements), approx_support.py (collectors, reversible rewrites, kernels).",
 "total_error renamed local_total_error without alias. AP-05 -> AP-05a / AP-05b. New ids AP-18d, AP-19c, AP-23a/b/c, AP-24a/b; steps: 23a, 19c M3; 23b, 23c, 18d M4; 24a/b M6.",
 "Primary stage_error, by_group, by_profile_kind, by_grid_kind of the electricity candidates are now on stage B6; B6-03 statistics kept under other_targets and *_B6_03.",
 "within_stage_target = primary quantity and every measured real stage (by_stage, propagation.stage_error) within 2%, no reference-0/candidate-non-0 case; AP-23a/b also count the stress scenarios (population alone in within_stage_target_on_population).",
 "No unit added to or removed from the plan's attachment of an existing candidate. B3-02 (AP-04) and X-11 (AP-13) stay in units with role IS_THE_CANDIDATE. AP-10b is scope STAGE.",
 "Out-of-sample class parameters pooled per (structure, use) as ratios of sums over the training half; pooling over all training buildings stored beside it. AP-19c is in-sample (mean over all rows of the same building).",
 "AP-24a primary quantity = B6-02 + B7-04 over scenarios with a year-table quantity. Coarse table = indices 0, 5, 10, ... and the last.",
 "Propagation by in-place rewrite that is undone (a deep copy costs more than a reference run); AP-07a uses fictional zero factors, AP-18c fictional class-mean route factors; AP-10, AP-10b, AP-12, AP-18 not propagated (downstream_reuse NOT_PROPAGATED).",
 "Load: kernels calling one function per row, on every 20th scenario (20 scenarios). AP-14, AP-20, AP-24b and candidates not rejected for cost: not measured.",
 "Near-boundary scenario reported separately; share_reference_inside_bracket stays the population statistic. Candidates written in natural id order.",
 "Added without being asked: units_under_estimated, by_summary_class (AP-10), inputs_by_grid_source (AP-09a/b), class breakdown for AP-18d / AP-23c. A dead computation of the old code was removed.",
]
interface = [
 "CLI: python3 -B -m bench.approx_study [--population 400] [--out PATH]. New modules bench/approx_meta.py, approx_measures.py, approx_support.py (README of research_code should list them).",
 "schema_version 3.0. New top-level keys: target_definition, attachment_definition, row_data_rebuilds_reference_B3_max_rel_diff, row_data_rebuilds_annual_units_max_rel_diff, n_scenarios_with_excluded_stages, n_rows_with_a_cycle_below_one_year, units_without_a_case_in_this_population, load_sample.",
 "Candidates: 40 (was 32). AP-05 -> AP-05a, AP-05b. New AP-18d, AP-19c, AP-23a, AP-23b, AP-23c, AP-24a, AP-24b: conclusions() and the plan need them.",
 "RENAMED total_error -> local_total_error (also in other_targets['B5…'] of AP-01..03).",
 "New keys on every candidate: units_stage_level, scope, evidence_scope{unit: UNIT|STAGE|BUILDING}, parameters_from, propagated_total_error, total_error_kind (PROPAGATED|LOCAL|null), downstream_reuse, propagation{measured, how, n, rewrite_reproduces_local_candidate_max_rel_diff, stage_error | reason}, by_unit{unit: {quantity: {level, role, error}}}, inputs{unit, exact, candidate, n_scenarios, text}, inputs_measured, load{measured, exact_kernel, n_kernel_runs, n_rows, candidate_instructions, exact_closed_form_instructions, ratio_candidate_to_exact, *_per_row, ... | cases | reason}, by_material_class_zero_reference or by_material_class_reason.",
 "Further keys: n_reference_zero, worst_stage{stage, measured_in, max_abs, max_over, max_under}, units_under_estimated, by_stage (AP-08, 09a/b/c, 13, 15, 18, 18c, 24a/b); every error stats dict gained n_reference_zero and n_reference_zero_candidate_nonzero; optional stage_note, units_note, variant_of, renamed_from, parameters_note, keeps_row_membership.",
 "Candidate-specific: bound (AP-01, AP-20); share_reference_inside_bracket_tolerance_form, n_including_near_boundary_scenario, share_reference_inside_bracket_including_near_boundary_scenario, inside_test (AP-20); by_profile_kind_stage_B2 / _B6_03 (AP-08); by_grid_kind_stage_B2 / _B6_03, inputs_by_grid_source (AP-09a/b); n_scenarios_computed_exactly (AP-09c, 24a, 24b); by_summary_class (AP-10); by_own_study_period, explicit_lists_continued (AP-14); covariance_identity, realised_within_mode_correlation (AP-17); pooling, n_test_scenarios_without_parameters, in_sample_on_the_same_test_scenarios, parameters_pooled_over_all_training_buildings (AP-18d, 23c); stress_scenarios, sign_guarantee, within_stage_target_on_population (AP-23a/b); by_rate_times_cycle_years_no_top_up_devices now on AP-05a/b.",
 "Changed labels: stage of AP-10/10b/12 'A1-A3（資材分：A13-01＋A13-03）', AP-18c 'C3-01＋C4-01（資材のみ。段階 C3 に入る設備の廃棄 X-14 を含まない）', AP-18 'B3＋B4＋C3-01＋C4-01（設備の廃棄 X-14 を含まない）'; titles of AP-05b and AP-20; other_targets gained 'B6-03（= B6＋B2。従来「B6 段階」として公表していた量）' and 'C3＋C4（段階の値の合計。設備の廃棄 X-14 を含む）'.",
 "units changed: AP-06 [A13-05]; AP-08 [B6-01,B6-03,B2-01]+sl[B6-04]; AP-10 [X-17]+sl[A13-01,A13-03]; AP-10b []+sl[X-17,A13-01,A13-03]; AP-11/16 +sl[X-02]; AP-15 13 units + 20 stage-level; AP-17 +C2-01; AP-18a +B4-01; AP-22a [X-04].",
 "Breaks in later-stage files: tools/build_records.py lines 333-335 ('AP-05'), 393, 396, 528 (total_error), plan AP('AP-05'); tools/build_reports.py lines 236, 345 (total_error), 353 (c['AP-05'][...]), 343 (list of candidates learned from the population: add AP-18d, AP-23c).",
]
tests = "cd " + R[:-1] + " && PYTHONPATH=. python3 -B -m unittest discover -s tests -t . -> 'Ran 106 tests in 43.903s' / 'OK' (16 in the new tests/test_approx_study.py)."
acceptance = [
 {"item": "a. unit tests", "result": "Ran 106 tests in 43.903s, OK.", "passed": True},
 {"item": "b. full run and comparison with the committed file",
  "result": "--population 400 --out " + S + "approximation_study.json completed; four full runs took 237 s, 229 s, 241 s, 243 s on the shared machine (old code: 105 s); the last used the final code and gives the identical file (480 KB). Committed file untouched. Comparison: (1) the exact time rule changed nothing: the old code on the new reference reproduces the committed file bit for bit (4410 leaves); (2) with the new code every old numeric leaf is still present bit for bit under total_error -> local_total_error, AP-05 -> AP-05b, old electricity stage_error / by_profile_kind / by_grid_kind -> other_targets['B6-03…'] / *_B6_03 (3936 leaves equal, cmp_committed_vs_new.log); (3) changed by item 1 (stage B6 instead of B6-03), old -> new stage_error: AP-08 -8.126..+11.806% -> -7.999..+11.637%; AP-09a -3.950..+3.817% -> -3.923..+3.619%; AP-09b -5.368..+7.490% -> -5.206..+7.411%; AP-09c -1.349..+1.735% -> -1.313..+1.719%; AP-13 -14.863..+70.443% -> -14.654..+69.886%, with their by_group / by_profile_kind / by_grid_kind; (4) flag: AP-09c within_stage_target true -> false (B2 +2.027%), no other flag changed; (5) by_material_class null -> breakdown for AP-04, 12, 17, 18b, 18c, 19a, 19b; (6) labels, titles, units lists, notes, candidate order as in interface_changes.",
  "passed": True},
 {"item": "c. schema, one line per candidate, conclusions to reword",
  "result": "Schema: interface_changes. Full proposed texts (current / proposed / suggested outcome for all 41 entries): " + S + "conclusion_proposals.json; longer version of this report: " + S + "B2_REPORT_long.json.\n"
            "LINES (id step scope | u=units | sl=stage-level units | worst stage range, st=within_stage_target | tot P(ropagated)/L(ocal) p95, within_total_target | share under-estimated | conclusion OK / REWORD / NEW):\n" + "\n".join(lines)
            + "\nAP-23a/b: st=F because the stress scenarios (to +3.5%) count; population alone T."
            + "\nREWORD (16):\n" + "\n".join(f"{cid}: {t}" for cid, t in SHORT.items())
            + "\nOK with a suggested addition: AP-06 / AP-07a / AP-07b (propagated totals: max -0.7% / -7.9% / -4.3..+2.6%), AP-14 (own-period subsets, continued lists), AP-10, AP-12 (unit figures), AP-22b (about 300 keys, 2,700 instructions). OK as written: AP-02, AP-06b, AP-10b, AP-11, AP-15, AP-16 (state scope STAGE / BUILDING), AP-19b, AP-21, AP-22a."
            + "\nNEW, suggested outcome (texts in conclusion_proposals.json): " + "; ".join(f"{k} {v}" for k, v in NEW.items()) + ".",
  "passed": True},
]
open_problems = [
 "tools/build_records.py and tools/build_reports.py do not run on the new JSON until adapted (interface_changes); regenerate records and reports together with the study file.",
 "'The exact closed form costs the same' is not supported for AP-04 (14 vs 112 instructions per row) and AP-05 (0.43-0.70x); it is supported for AP-06 (equal), AP-07b (1.55x), AP-08 (1.12-1.35x), AP-09a/b (2.6-3.4x).",
 "Load = bytecode instructions of small kernels on 20 sample scenarios; no wall time or memory; 22 candidates without a load figure; AP-14's cost sentence (unified model re-using one aggregation) not measured here. Exact-kernel counts depend on fastcalc/closed_forms.py, which stage A2 was editing (unchanged during my four runs).",
 "local_total_error of AP-10, AP-10b, AP-12, AP-18 excludes downstream reuse. Out-of-sample results (AP-18d, AP-23c) depend on the pooling across fictional buildings.",
 "AP-23a/b meet the targets on the population only; records must not say 'meets the targets'. AP-05a: units B1-03 / B1-04 are under-estimated although stage B1 is not.",
 "Whether the plan keeps AP-04 on B3-02 and AP-13 on X-11 (role IS_THE_CANDIDATE) is left to the later stage. AP-16 still uses numpy (as before).",
 "One transient failure of another stage's test (tests/test_mechanism_probe.py, being edited by stage A2) in one earlier full-suite run; it passed alone and in the three later full runs.",
]
report = {"files_changed": [R + "bench/approx_study.py", R + "bench/approx_measures.py", R + "bench/approx_support.py", R + "bench/approx_meta.py", R + "tests/test_approx_study.py"],
          "findings": [{"id": i, "status": s, "what": w, "how_checked": h} for i, s, w, h in findings],
          "decisions": decisions, "interface_changes": interface, "tests": tests, "acceptance": acceptance, "open_problems": open_problems,
          "report_file": "/tmp/claude-0/-home-user--/49c0bd7e-a786-5ae4-9a1e-e89e7996ede3/scratchpad/recheck/fix/B2_REPORT.json"}
json.dump(report, open(report["report_file"], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(json.dumps(report, ensure_ascii=False)), "characters")
print(acceptance[2]["result"])
