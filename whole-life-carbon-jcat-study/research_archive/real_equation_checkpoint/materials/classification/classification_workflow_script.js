export const meta = {
  name: 'checkpoint-classify-old-study',
  description: 'Read-only classification of the terminated simplification study into the five checkpoint categories (no calculation of the old study is run)',
  phases: [
    { title: 'Read', detail: 'seven read-only lenses classify outcomes, defects and reuse candidates' },
  ],
}

const SCRATCH = '/tmp/claude-0/-home-user--/49c0bd7e-a786-5ae4-9a1e-e89e7996ede3/scratchpad/checkpoint'
const BRIEF = `${SCRATCH}/BRIEF.md`
const STUDY = 'whole-life-carbon-jcat-study/09_APPROX_STUDY'
const ARCH = 'whole-life-carbon-jcat-study/research_archive/real_equation_checkpoint'

const RET = {
  type: 'object',
  properties: {
    file: { type: 'string' },
    n_items: { type: 'integer' },
    counts_by_state_category: { type: 'object', properties: { c1: { type: 'integer' }, c2: { type: 'integer' }, c3: { type: 'integer' }, c4: { type: 'integer' } }, required: ['c1', 'c2', 'c3', 'c4'] },
    n_reuse_candidates: { type: 'integer' },
    summary: { type: 'string' },
    rule_check: { type: 'string', description: 'State explicitly: did you run any code of the old study or change any repository file? (must be: no)' },
    problems: { type: 'array', items: { type: 'string' } },
  },
  required: ['file', 'n_items', 'counts_by_state_category', 'summary', 'rule_check', 'problems'],
}

const head = (lens, file) => `You are checkpoint reader ${lens}. First read ${BRIEF} completely and follow its hard rules (READ ONLY; do NOT run or import any code of the old study; classification only). Then read ${ARCH}/STOP_STATUS.md.
Write your output to ${SCRATCH}/${file} in the JSON format of the brief (lens "${lens}"), then validate with python that the file parses and that every item has all fields. Your final answer is the short structured summary.

Your lens:
`

const LENSES = [
  {
    lens: 'R1', file: 'R1.json',
    body: `GOVERNANCE, LEDGER, RANKING.
Read: ${STUDY}/00_POLICY/* (directive, amendment 01, EVALUATION_PROTOCOL.md - note it is a v1.4 DRAFT committed as work in progress), ${STUDY}/01_LEDGER/* (README.md, units.json: structure and header, a sample of units, sheet_families.json, sheet_family_coverage.json, unlinked_input_disposition.json, considered_not_adopted.json), ${STUDY}/02_RANKING/* (README.md, axis_a.json, axis_a_measurements.json, axis_b.json structure, axis_b_judges/, research_priority.json).
Then the second-round findings that touch them: in ${ARCH}/materials/round2_review/triage/reports.md (REP-1, REP-7, REP-8, REP-10, REP-11, REP-18 at least; read all REP items and pick those about ledger / ranking / protocol) and records.md where it concerns the protocol.
Classify: the evaluation-unit ledger (70 units: 53 existing + 17 added), the binding definitions (reference_semantics), declared inputs per unit, structure classes, sheet-family coverage labels, the unlinked-input disposition, axis A (measured load: what was measured, on what), axis B (three-judge scoring: what it is and is not), the research order, the protocol itself (which parts were followed, which are draft), the directive documents (received texts).
Be exact about what "70 units" means (units of the independent concept model; the original ~3.82 million formula nodes were NOT inspected) and about every count that a finding says is wrong or stale.`,
  },
  {
    lens: 'R2', file: 'R2.json',
    body: `REFERENCE CALCULATION, FICTIONAL DATA, COMPARISON HARNESS, TESTS (as committed, state 60e720f).
Read (source text only, do not import): ${STUDY}/research_code/README.md, research_code/refcalc/* (base.py conventions docstring completely; registry; the unit modules: skim all, read several units fully), research_code/synth/* (model.py dataclasses, generators, population, benchmark scenarios, edge cases, README), research_code/common/compare.py, research_code/tests/* (what is tested), research_code/bench/mutations.py, ${STUDY}/06_OPEN_ISSUES/README.md section B (conventions B-1..B-21) and D.
Then the second-round findings about the reference: ${ARCH}/materials/round2_review/triage/rederive.md (RED-1..12, all) and numeric.md (NUM-1..11: which are about the reference side), and what the interrupted stage a1 says it changed: ${ARCH}/materials/interrupted_fix/specs/SPEC_A1.md and agent_reports/A1_REPORT.json (claims only).
Classify, as separate items: the reference calculation as a whole (what it is: one literal function per unit of an independent concept model; its role as the baseline), its time rules (event counting, year assignment with the 1e-9 tolerance) and the known knife-edge defect, its completeness flags and the known data-flow hole, its handling of invalid values and the known gaps, the conventions list, the fictional scenario model and generators (population sizes, benchmark sizes S/M/L if present, edge cases, mutations), the comparison harness, the unit tests (how many, what they cover - from the text, not by running), and the interrupted a1 changes (exact rational time arithmetic, validity rules, data-flow completeness, SUM-08 statuses ...) as provisional / hypothesis items.
For the reuse note, be concrete about which parts of the reference and of the fictional data generators a new study could use as a FROZEN baseline, on which class of inputs the committed reference is known to behave as its definitions say, and which inputs must be avoided.`,
  },
  {
    lens: 'R3', file: 'R3.json',
    body: `UNIFIED MODEL (EXACT SIMPLIFICATION AND UNIFICATION) AND ITS EVIDENCE.
Read (source text only): ${STUDY}/03_MODELS/README.md, DERIVATIONS.md (all derivations D1..), models.json (K1..K7), ${STUDY}/research_code/fastcalc/closed_forms.py and engine.py (structure; the closed forms fully), ${STUDY}/04_VERIFICATION/README.md, unified_model_exactness.json, unified_model_load.json, input_usage.json, research_code/bench/verify_unified.py and measure_axis_a.py (what they measure).
Then the second-round findings: ${ARCH}/materials/round2_review/triage/numeric.md (NUM-1..11), records.md (REC-1..9), the parts of reports.md about unification counts and load (REP-3, REP-4, REP-6, REP-12, REP-15, REP-16 at least), and the interrupted work: specs/SPEC_A1.md items on closed forms, specs/SPEC_A2.md, a2_partial_outputs/* (interrupted, unverified), agent_reports/A1_REPORT.json.
Classify as separate items: each unified model K1..K7 (what shared object / parameterised function it is, which units were counted as members, what the membership rule is, what second-round findings say about the membership count "66 of 70"), each closed form / derivation (renewal count, skip-year weight, year-weighted sums, grid segments and moments, refrigerant cycle mass balance, indicators, ...: is it a proven identity, under which arithmetic, and what the knife-edge finding does to it), the exactness result (681 fictional scenarios, 7,406,182 numbers, relative tolerance 1e-9: reproduced by the second-round checker; what it does NOT show; the counterexample period 1.000000001; comparison weaknesses such as floors / inf handling), the load measurements (instruction counts and times; what was compared; caveats), the input-usage measurement, the "mechanism" evidence based on hand-placed counters (finding), the period sweep / re-finish capability, and the planned evidence redesign (fault-injection membership check, external mechanism probe) as hypothesis / in-progress items.
The reuse note matters most here: say precisely which structural facts about the concept model are established by derivation (e.g. emissions as sums of activity x factor over rows with life-cycle multipliers that depend only on period and cycle; counts as ceiling functions; year-weighted sums; geometric refrigerant cycles) and which are only observed on fictional data, because the new research will build on these structures.`,
  },
  {
    lens: 'R4', file: 'R4.json',
    body: `APPROXIMATION STUDY (M3..M6 candidates).
Read: ${STUDY}/04_VERIFICATION/approximation_study.json (schema and every candidate: id, what it approximates, measured errors, decision), ${STUDY}/03_MODELS/candidates.json, the approximation parts of ${STUDY}/03_MODELS/README.md and ${STUDY}/04_VERIFICATION/README.md, research_code/bench/approx_study.py (source text: what each candidate computes, populations, train/test split), the protocol's accuracy targets (${STUDY}/00_POLICY/EVALUATION_PROTOCOL.md: total <= 1 %, stage <= 2 %, no serious under-estimation, fall back to exact outside range).
Then the second-round findings: ${ARCH}/materials/round2_review/triage/approx.md (APP-1..9, all), REP-5, REP-6, REP-13 in reports.md, REC-8 in records.md; and the interrupted stage b2: specs/SPEC_B2.md, agent_reports/B2_REPORT.json, B2_REPORT_long.json, conclusion_proposals.json, candidate_lines.json, cmp_committed_vs_new.log.txt, b2_output/approximation_study_UNVERIFIED.json (schema, new candidates) - all self-reported, measured against the UNVERIFIED modified reference of 65ff124.
Classify: one item per candidate family (the 32 committed candidates AP-01.. grouped sensibly: renewal-count continuous approximations, repair-year forms, refrigerant linearisations, electricity / grid series approximations, class-parameter (representative parameter) models, floor-area intensity surrogate, transport mean distance, disposal aggregates, ...), each with its committed decision (rejected / on hold for real data), the measured error figures as recorded, and what the second round says about that measurement (wrong reference quantity, unpropagated totals, in-sample parameters, dropped classes ...). Separate items for: the overall conclusion "no approximation adopted" and what supports it; the error-measurement method itself and its confirmed flaws; the new candidates and re-measurements of b2 (provisional); the statement that practical accuracy cannot be established on fictional data.
For the reuse note: which candidates are examples of "one common approximate model for structurally different formulas" (most relevant to the new research), what error behaviour was observed and why (as far as recorded), and which measured failures are useful counterexamples.`,
  },
  {
    lens: 'R5', file: 'R5.json',
    body: `RECORDS, PROGRESS LEDGER, REPORTS, DELIVERABLES, MATERIAL CLASSIFICATION DRAFT, REVIEW HISTORY.
Read: ${STUDY}/README.md (generated summary + the hand-written stop notice on top), ${STUDY}/05_DECISIONS/README.md, PROGRESS.md, progress_ledger.json (structure, status counts, a sample), ${STUDY}/03_MODELS/records/ (structure; sample several unit records), judge_proposal_trace.json, ${STUDY}/04_VERIFICATION/INDEPENDENT_REVIEW.md (round 1: findings and dispositions), ${STUDY}/06_OPEN_ISSUES/README.md (all sections), ${STUDY}/07_MATERIAL_TAXONOMY/* (README.md, REVIEW_LOG.md, the JSON files' structure), research_code/tools/* (source text: which generator writes which file).
Then ALL of ${ARCH}/materials/round2_review/triage/reports.md (REP-1..18) and records.md (REC-1..9), and ${ARCH}/materials/interrupted_fix/specs/STAGE_C_NOTES.md (planned but never started revisions of records / reports / documents).
Classify: the per-unit step records M1..M6 (454 records: what a record is, the evidence model it claims and what REC-5 etc. say), the progress ledger and its status counts (3 / 66 / 0 / 0 / 0 / 1 of 70) and which of these counts second-round findings contradict, the generated reports and each headline statement of ${STUDY}/README.md (items 1-7 under "結果の要点": for EACH statement say what stands and what must not be relied on, citing finding ids), the nine required deliverables of the old directive (which exist, in which state), the judge-proposal trace (known wrong mapping), the open-issues list, the first-review record, the material-classification design draft (07_MATERIAL_TAXONOMY: what it is, its review state, that it is a design draft and not a data set), and the list of planned-but-not-done revisions (Stage C).
This lens decides how a successor may quote the old study's published text, so be strict and specific.`,
  },
  {
    lens: 'R6', file: 'R6.json',
    body: `REGISTER OF THE 59 SECOND-ROUND FINDINGS AND THEIR STATE AT THE STOP.
Read ALL FIVE triage files in ${ARCH}/materials/round2_review/triage/ completely (numeric.md, rederive.md, records.md, approx.md, reports.md; res.json for structure if needed), then ${ARCH}/materials/interrupted_fix/specs/* (SPEC_A1.md, SPEC_A2.md, SPEC_B2.md, SPEC_B3.md, STAGE_C_NOTES.md: which finding was assigned to which stage and what decision was taken), then agent_reports/A1_REPORT.json and B2_REPORT.json (per-finding status claimed by the two finished stages), and the journal facts in STOP_STATUS.md (a2 interrupted, b3 / verify loop / stage C never started). You may read ${ARCH}/materials/interrupted_fix/working_tree_at_stop_65ff124.patch (text) to see whether a claimed change is present in the diff, but do not run anything.
This lens uses a DIFFERENT output format. Write ${SCRATCH}/R6.json as:
{"lens":"R6","read":[...],"findings":[{"id":"NUM-1","severity":"HIGH|MEDIUM|LOW as given by the checker","verdict":"CONFIRMED|PARTLY_CONFIRMED|NOT_SECOND_VERIFIED (REP: reproduced by re-running the checker's script)","statement":"日本語・常体で 1〜2 文（PARTLY の場合は検証担当の訂正後の内容）","affects":["成果物やファイル（日本語の短い語句）"],"repro":"archive path of the reproduction script(s) if any","assigned_stage":"a1|a2|b2|b3|C|none (documented only)","decision":"決めていた対応（日本語 1 文）","state_at_stop":"未対応 | 中断時の編集で対応（自己申告・未検証）| 途中で停止 | 対応しない（文書化のみの予定で未実施）","state_evidence":"どこを見てそう判断したか","in_committed_tree":"公開中の版（60e720f）に指摘の問題が残っているか：残っている | 該当なし"}],"groups":[{"title":"日本語の題","finding_ids":[...],"what":"まとめて言うと何が問題か（日本語 2〜3 文）","consequence_for_reuse":"新研究で旧成果を使うときの注意（日本語）"}],"counts":{"total":59,"by_verdict":{...},"by_state_at_stop":{...},"by_severity":{...}},"not_covered":[...]}
Every one of the 59 ids must appear exactly once in "findings". Make 6-10 groups that a successor can read in two minutes. The counts must be computed from your list with python (parse your own file), not typed by hand.
In your structured answer put the number of findings in n_items and zeros in counts_by_state_category.`,
  },
  {
    lens: 'R7', file: 'R7.json',
    body: `REUSE SCOUT FOR THE NEW RESEARCH (structure inventory; you do not do the new research).
Read (source text only): ${STUDY}/01_LEDGER/units.json (every unit: id, stage, structure class, reference_semantics text, depends_on), ${STUDY}/03_MODELS/DERIVATIONS.md and models.json, ${STUDY}/research_code/refcalc/base.py and the unit modules, research_code/fastcalc/closed_forms.py, research_code/synth/model.py (the input data model), ${STUDY}/04_VERIFICATION/approximation_study.json (candidate list), ${STUDY}/06_OPEN_ISSUES/README.md, ${ARCH}/materials/round2_review/triage/*.md (for cautions).
Produce items in the brief's format (lens "R7"), state_category as it applies, with reuse_candidate true, one item per reusable asset or structural fact, for example:
- the unit dependency graph (which unit feeds which; stages A1-A5, B1-B7, C1-C4, D if present, sums and indicators, QA units),
- the mathematical shape of each family of units as written in the binding definitions: bilinear row sums (quantity x factor), event counting over the study period (ceiling / floor functions of period and cycle), year-indexed weighted sums (annual quantity x year-dependent grid factor), piecewise-linear / stepwise factor series, refrigerant charge-leak-top-up cycles (recurrences / geometric sums), ratios and indicators, conditional branches (stage boundaries, licences, validity), aggregation trees, comparison with a baseline,
- which variables each family depends on (period T, cycle L, year index, row index, material class, stage), linear vs non-linear dependence, periodicity, branching: give a compact table per family in the "what" / "evidence" fields, naming the unit ids,
- the input data model (tables and scalar fields) and the fictional scenario generators,
- the reference calculation as a frozen baseline and the comparison harness,
- the exact closed forms (as candidate "Route A" material),
- measured approximation errors as counterexamples,
- the conventions and known holes a new formulation must respect or avoid.
Do NOT propose transformations or new formulations; only inventory what exists, where, in which verification state, and what a successor must know before using it. Give counts (how many units per family) computed from units.json with python (JSON parsing only).`,
  },
]

phase('Read')
const results = await parallel(LENSES.map(l => () =>
  agent(head(l.lens, l.file) + l.body, { label: `read:${l.lens}`, phase: 'Read', schema: RET })
    .then(r => ({ lens: l.lens, ...r }))
))
const ok = results.filter(Boolean)
log(`${ok.length}/${LENSES.length} readers returned`)
return { results: ok, missing: LENSES.map(l => l.lens).filter(x => !ok.some(r => r.lens === x)) }
