export const meta = {
  name: 'checkpoint-independent-check',
  description: 'Read-only independent check of the stop record, index and handover of the terminated study (no old-study code is run)',
  phases: [{ title: 'Check', detail: 'four checkers: verified claims (2), stop/save facts, omissions and consistency' }],
}

const ROOT = '/home/user/-'
const ARCH = ROOT + '/whole-life-carbon-jcat-study/research_archive/real_equation_checkpoint'
const OUT = '/tmp/claude-0/-home-user--/49c0bd7e-a786-5ae4-9a1e-e89e7996ede3/scratchpad/checkpoint/review'

const COMMON = `
You are an independent checker. You did not write the documents you check. Default to distrust: your job is to find
statements that are false, broader than their evidence, or misleading. Do not praise. Do not fix anything.

SITUATION
A study in ${ROOT}/whole-life-carbon-jcat-study/09_APPROX_STUDY/ ("the old study": simplification / unification /
approximation of the formulas of an INDEPENDENT whole-life-carbon concept model, on FICTIONAL data) was terminated
unfinished on 2026-11-11 by the user's directive (text: ${ARCH}/STOP_ORDER.md). The executing agent stopped it and wrote
three documents in ${ARCH}/ : STOP_STATUS.md (stop record), INDEX.md (index of outcomes in five categories, generated
from classification JSON in materials/classification/, with per-item detail in index_detail/), HANDOVER.md.
The directive forbids starting the new research until the stop is confirmed and the outcomes are saved and classified,
and forbids treating unverified results as verified. So an error in these documents matters.

HARD RULES (a violation makes your work unusable)
1. READ ONLY for the repository: create, change, delete nothing under ${ROOT}. Allowed git commands: log, show, diff,
   status, ls-files, ls-tree, rev-parse, cat-file, grep, branch --list. Nothing that writes.
2. DO NOT RUN THE OLD STUDY: no tests, no benchmarks, no tools, no generators, no import of refcalc, fastcalc, bench,
   synth, tools, common, and do NOT run any script under materials/round2_review/checker_scripts/ or
   materials/interrupted_fix/ (they import the old study). Python only to parse text / JSON / Markdown (run it with -I
   from your own scratch folder). If something can only be confirmed by running the study, report it as
   "not confirmable without a run" - that is not a defect of the documents unless they claim otherwise.
3. Do not use the web.
4. Write your result file to ${OUT}/<name given below>.json (create the folder if needed) and nothing else outside
   your own scratch folder ${OUT}/work_<your name>/ .
5. Compliance: the repository contains no original J-CAT files, formulas or factors and none may be reproduced. Never
   write that something is compatible with or verified against the original workbooks.
6. If you refer to a person whose pronouns are unknown, use they/them. No e-mail addresses or personal names in output.

KEY FACTS YOU MAY RELY ON (verify them if they matter to a finding)
- Commits: 43ba5d7 = last version where code, measurements, records, reports correspond (the version the SECOND
  independent review examined); 60e720f = + protocol v1.4 draft; 65ff124 = snapshot of the interrupted, unverified
  edits; 0db5c77 = revert of 65ff124; later commits = archive.
- The second review round: 59 findings (NUM-1..11, RED-1..12, REC-1..9, APP-1..9, REP-1..18). Full text with the
  adversarial verifiers' verdicts: ${ARCH}/materials/round2_review/triage/{numeric,rederive,records,approx,reports}.md
  (each has CHECKS PERFORMED / COULD NOT CHECK / ADDITIONAL sections) and res.json.
- Category definitions: INDEX.md section 0.3. Category 1 ("verified") requires: (a) a recorded measurement or
  derivation in the committed version, (b) independent reproduction or cross-check by at least one checker other than
  the author, (c) wording narrowed so that no second-round finding contradicts it. Scope is always fictional data and
  the independent concept model.

OUTPUT (JSON file and the same content as your structured answer)
{ "checker": "<name>", "rule_check": "state explicitly: did you run any old-study code or change any repository file? (must be: no)",
  "findings": [ { "id": "<name>-01", "severity": "HIGH|MEDIUM|LOW", "file": "path relative to the archive folder or repo",
     "where": "section / item id / line", "quoted": "the statement as written (short quote)",
     "problem": "what is wrong or unsupported", "evidence": "file:line or JSON key or git command + output that shows it",
     "suggested_fix": "the corrected wording or the action (one or two sentences)" } ],
  "checked_ok": ["things you checked and found correct, one line each, with what you compared"],
  "not_checked": ["what you could not check and why"] }
Severity: HIGH = a statement that would let unverified work pass as verified, a false statement about the stop, or a
lost outcome; MEDIUM = a wrong number / wrong path / wrong attribution that a successor would act on; LOW = unclear or
imprecise wording. Report only what you actually checked, with the evidence. No finding without evidence.
Language of findings: Japanese (plain style) for "problem" and "suggested_fix"; quotes as written.
Budget: aim for at most about 70 tool calls. Prioritise HIGH-impact checks first; when the budget is used up, write the
file and report what you did not reach under not_checked.
`

const SCHEMA = {
  type: 'object',
  properties: {
    checker: { type: 'string' },
    rule_check: { type: 'string' },
    file: { type: 'string', description: 'path of the JSON result file you wrote' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' }, severity: { type: 'string' }, file: { type: 'string' }, where: { type: 'string' },
          quoted: { type: 'string' }, problem: { type: 'string' }, evidence: { type: 'string' }, suggested_fix: { type: 'string' },
        },
        required: ['id', 'severity', 'file', 'where', 'problem', 'evidence', 'suggested_fix'],
      },
    },
    checked_ok: { type: 'array', items: { type: 'string' } },
    not_checked: { type: 'array', items: { type: 'string' } },
  },
  required: ['checker', 'rule_check', 'findings', 'checked_ok', 'not_checked'],
}

const CHECKERS = [
  {
    name: 'V1',
    prompt: `YOUR TASK (checker V1, file V1.json): the "verified" claims about the reference calculation, the unified model and the measurements.
Read INDEX.md sections 0, 1.1, 1.3 and 2. For EACH of these category-1 items check the text under "言ってよいこと"
(INDEX.md section 2; full detail incl. "確かめ方", "確かめた者", "使ってはいけない記述" in index_detail/T02_ledger.md,
T04_reference_calculation.md, T06_unified_models.md, T07_exactness_load.md):
CK-R1-05, CK-R1-09, CK-R7-01, CK-R7-02, CK-R2-01, CK-R2-02, CK-R7-17, CK-R7-28, CK-R3-01, CK-R3-02, CK-R3-03, CK-R3-05,
CK-R3-07, CK-R3-09, CK-R3-10, CK-R3-12, CK-R3-13, CK-R3-14, CK-R3-15, CK-R3-16, CK-R7-23, CK-R3-18, CK-R3-19, CK-R3-20, CK-R7-22.
For each: (1) is every number in the claim present in the triage files (numeric.md, rederive.md, records.md,
reports.md) or in the committed JSON under 09_APPROX_STUDY/04_VERIFICATION/, 03_MODELS/, 01_LEDGER/ ? quote where;
(2) does any CONFIRMED / PARTLY_CONFIRMED finding (or a verifier's ADDITIONAL remark) contradict or limit the claim as
worded - i.e. is the claim still too broad? (3) is "確かめた者" right - did a checker other than the author really
reproduce it, and how many (one checker, or checker + adversarial verifier)? Compare with the note "根拠の強さ" where
present; (4) should the item be category 2 rather than 1 under the definition? Say so with the reason.
Also check the rows of INDEX.md table 1.1 that cite these items (the table is hand-written: is each row supported by
the item it cites, and are the numbers the same?). Do not spend effort on items outside this list.`,
  },
  {
    name: 'V2',
    prompt: `YOUR TASK (checker V2, file V2.json): the "verified" claims about the approximation study and the records, and the hand-written summary text.
(A) For EACH of these category-1 items check the text under "言ってよいこと" (INDEX.md section 2; detail in
index_detail/T08_approximation.md and T09_records_reports.md): CK-R4-04, CK-R4-05, CK-R4-09, CK-R4-19, CK-R4-20,
CK-R4-22, CK-R7-26, CK-R5-01, CK-R5-11, CK-R5-17. For each: (1) every number against
09_APPROX_STUDY/04_VERIFICATION/approximation_study.json, 03_MODELS/candidates.json, 03_MODELS/records/units.json,
05_DECISIONS/progress_ledger.json and the triage files approx.md, reports.md, records.md; (2) does any CONFIRMED /
PARTLY_CONFIRMED finding or verifier's remark contradict or limit the claim as worded; (3) is "確かめた者" right;
(4) should it be category 2 instead?
(B) Check the HAND-WRITTEN text line by line against the triage files and the classification JSON
(materials/classification/R*.json): INDEX.md section 1.2 (table of statements not to use: is the column "実際" right,
are the cited finding ids the right ones, are the numbers right - e.g. 92 %, 62.8 %, 96 of 118, 47 of 124, 204 of 280,
21 of 44), section 6.1 and 6.2 (e.g. the unit counts of the 11 formula families must sum to 70 and match
R7.json; 183 edges; depth 0-7; 29 units into X-02; 37 units upstream of SUM-03; 30 / 10 structure classes),
HANDOVER.md section 2.1, 2.2 and 4.4 (what round 2 found; are REC-2, REP-4, REC-5, APP-2, APP-3, APP-9, NUM-1 described
correctly and not exaggerated or softened?). Report every number or attribution that does not match its source.`,
  },
  {
    name: 'F1',
    prompt: `YOUR TASK (checker F1, file F1.json): the facts about the stop and the save.
Check every factual statement of STOP_STATUS.md, of HANDOVER.md sections 1, 3, 4.1, 4.2, 5 and 7, and of INDEX.md
sections 0.1, 0.4, 1.3, 8 and 9 against git and the file system:
- commit hashes and what each commit contains (git show --stat, git diff --stat between the named commits); is
  09_APPROX_STUDY at HEAD identical to 60e720f except the hand-written note at the top of README.md? is the code under
  research_code identical in 43ba5d7, 60e720f and HEAD? was any file deleted since 60e720f (git diff --diff-filter=D)?
  was history rewritten (is 65ff124 an ancestor of HEAD)? are the tree ids in HANDOVER 4.2 right (git rev-parse HEAD:<path>)?
  is everything pushed (git status, git rev-parse HEAD origin/claude/jcat-formula-approximation-study-c33936)?
  were other folders (ai-document-market-research, chapters 01-08 of whole-life-carbon-jcat-study) left untouched by
  the commits from 65ff124 on (git diff --stat 60e720f HEAD -- <path>)?
- the stop: is any process of the old study running now (ps aux: python processes importing refcalc / fastcalc / bench,
  pytest, a workflow)? any cron / at entries, any auto-resume or progress file in the repository (.claude settings,
  hooks, TODO / RESUME files) that would restart the old study? (You cannot see the session's scheduled-task list; say so.)
- the save: does every path named in STOP_STATUS.md, HANDOVER.md, INDEX.md section 8 exist? do the counts in INDEX.md
  0.4 (171 items; categories 35 / 79 / 25 / 32; 133 reuse candidates; 59 findings) and in section 5.2 (33 / 8 / 18;
  3 / 27 / 29; states 38 / 10 / 10 / 1) match materials/classification/R*.json and materials/round2_review/triage/res.json
  and the triage files (count them by parsing)? is the statement in HANDOVER 5 about 75 files / 72 covered / 3 empty
  __init__.py right (are those three files really empty)? are there forbidden file types (.xlsx .xlsm .xls .zip .pdf)
  anywhere under whole-life-carbon-jcat-study? does materials/ contain __pycache__ or compiled files?
- the claim "no code of the old study was run after the stop": look for evidence against it (files under
  09_APPROX_STUDY newer than the stop that are not explained by the commits, __pycache__ directories, changed JSON
  outputs: git status must be clean and git diff 60e720f HEAD -- 09_APPROX_STUDY must show README.md only).
- internal consistency between STOP_STATUS.md, HANDOVER.md and INDEX.md (same commits, same counts, same names of
  stages a1 / a2 / b2 / b3 and their states), and with STOP_ORDER.md (does each of the five transition conditions of
  0-3 have real evidence?). Is anything described as done that is only planned?
Report false, unsupported or outdated statements.`,
  },
  {
    name: 'C1',
    prompt: `YOUR TASK (checker C1, file C1.json): omissions, misclassification outside category 1, compliance.
(A) Omissions: walk the old study (README.md and the README of each of 00_POLICY .. 07_MATERIAL_TAXONOMY, the list of
JSON outputs, 06_OPEN_ISSUES/README.md sections A-H, 03_MODELS/DERIVATIONS.md headings, 03_MODELS/candidates.json ids,
05_DECISIONS) and the archive materials (triage sections ADDITIONAL and COULD NOT CHECK; interrupted_fix/specs and
agent_reports). For each distinct outcome, hypothesis, open issue or defect, check that INDEX.md (sections 2-6 and
the topic table in 7) has an item that covers it. Report what a successor would look for and not find. In particular:
every K1..K7, D1..D8, every candidate id AP-xx, every open issue group of 06_OPEN_ISSUES, the 9 required deliverables,
the material taxonomy draft, the judges' proposals, the four unfinished old tasks, and the verifiers' ADDITIONAL remarks.
(B) Misclassification: take 20 items of categories 2, 3 and 4 spread over the topics T01..T12 (index_detail/T*.md) and
check each against its sources: is an item placed in 2 or 3 actually a known defect (4)? is an item marked as a reuse
candidate although its own text says it must not be used? is "確かめた者" overstated (e.g. says independent although
only the author measured)? is the text of "内容" faithful to the source? List the ids you sampled.
(C) Compliance and wording, over INDEX.md, HANDOVER.md, STOP_STATUS.md and a text search of index_detail/*.md and
materials/classification/*.json: any sentence that claims or implies agreement / compatibility / equivalence with the
original workbooks or practical accuracy on real buildings; any reproduction of original factors, service lives,
rates or formula text presented as coming from the original (numbers of the FICTIONAL model are fine); any e-mail
address or personal name; any place where the old study is said to be only paused or to be completed later.
(D) Section 6 of INDEX.md (reuse candidates): does the text make clear that reuse does not make an item verified, and
that the frozen reference is the committed version? Is any category-4 defect that limits the reference calculation
missing from the conditions in 6.1 (compare with groups 1 and 2 of index_detail/FINDINGS_59.md)?`,
  },
]

phase('Check')
const results = await parallel(CHECKERS.map(c => () =>
  agent(COMMON + '\n' + c.prompt, { label: 'check:' + c.name, phase: 'Check', schema: SCHEMA })
    .then(r => r ? { ...r, checker: c.name } : null)
))
const ok = results.filter(Boolean)
const missing = CHECKERS.map(c => c.name).filter(n => !ok.some(r => r.checker === n))
const all = ok.flatMap(r => (r.findings || []).map(f => ({ ...f, checker: r.checker })))
const bySev = { HIGH: 0, MEDIUM: 0, LOW: 0 }
for (const f of all) bySev[f.severity] = (bySev[f.severity] || 0) + 1
log(`findings: ${all.length} (${JSON.stringify(bySev)}), missing checkers: ${missing.join(',') || 'none'}`)
return {
  bySev, missing,
  rule_checks: ok.map(r => ({ checker: r.checker, rule_check: r.rule_check, n_ok: (r.checked_ok || []).length, not_checked: r.not_checked })),
  findings: all,
}
