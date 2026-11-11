export const meta = {
  name: 'checkpoint-fix-verification',
  description: 'Read-only verification that the 57 findings of the independent check were applied correctly to the archive documents',
  phases: [{ title: 'Verify', detail: 'two checkers: verified-claim findings, stop/save and completeness findings' }],
}
const ROOT = '/home/user/-'
const ARCH = ROOT + '/whole-life-carbon-jcat-study/research_archive/real_equation_checkpoint'
const OUT = '/tmp/claude-0/-home-user--/49c0bd7e-a786-5ae4-9a1e-e89e7996ede3/scratchpad/checkpoint/review2'
const COMMON = `
You are an independent checker. You did not write the documents or the corrections you check. Default to distrust.

SITUATION. A study (${ROOT}/whole-life-carbon-jcat-study/09_APPROX_STUDY, "the old study") was terminated. Its stop
record, index and handover are in ${ARCH} (STOP_STATUS.md, INDEX.md with index_detail/, HANDOVER.md). An independent
check found 57 findings: ${ARCH}/materials/classification/review/{V1,V2,F1,C1}.json (fields id, severity, file,
where, quoted, problem, evidence, suggested_fix). The author then applied corrections (commit c6bf26e; compare with
the version before the check: git diff b2b8a6e c6bf26e -- <file>). Corrections to item texts are listed in
${ARCH}/materials/classification/overrides.json and rendered into INDEX.md and index_detail/*.md; hand-written parts
are materials/classification/INDEX_head.md, INDEX_reuse_intro.md, INDEX_tail.md, and HANDOVER.md, STOP_STATUS.md.
A new study has started in ${ROOT}/whole-life-carbon-jcat-study/10_TRANSFORM_STUDY - not your concern, ignore it.

HARD RULES
1. READ ONLY for the repository. Allowed git commands: log, show, diff, status, ls-files, ls-tree, rev-parse, cat-file, grep.
2. DO NOT RUN THE OLD STUDY: no tests, benchmarks, tools, generators, no import of refcalc, fastcalc, bench, synth,
   tools, common; do not run any script under ${ARCH}/materials (the index renderer render_index.py may be READ, not run).
   Python only to parse text / JSON (with -I, from your own scratch folder ${OUT}/work_<name>/).
3. No web. No personal data in the output. They/them for people.
4. Write only ${OUT}/<name>.json and your scratch folder.

YOUR JOB, for each finding assigned to you:
 (a) is the correction present in the current documents (quote the new text with file and line)?
 (b) does the new text actually resolve the problem, and is the new text itself correct and supported - check it
     against the evidence the finding cites (triage files under materials/round2_review/triage/, classification JSON,
     the old study's JSON files, git)? A correction can introduce a new error: look for one.
 (c) is the same problem still present somewhere else (another section of INDEX.md, HANDOVER.md, STOP_STATUS.md, an
     index_detail file, the 09_APPROX_STUDY README note) where it was not corrected?
Then look for NEW inconsistencies introduced by the corrections: numbers that now differ between INDEX.md, HANDOVER.md
and STOP_STATUS.md (e.g. counts of categories 34 / 80 / 25 / 32, 171 items, 133 reuse candidates, 57 findings and
their split, 400 / 316 / 61 / 15 / 5 / 3 working files), section numbers referred to that do not exist, links that do
not resolve, statements in the new hand-written text that have no source.

OUTPUT (the JSON file and the same as structured answer):
{ "checker": "<name>", "rule_check": "did you run old-study code or change a repository file? (must be: no)",
  "results": [ { "finding": "V1-02", "status": "RESOLVED | PARTLY | NOT_APPLIED | NEW_ERROR", "where_now": "file:line",
                 "note": "short; for PARTLY / NOT_APPLIED / NEW_ERROR say exactly what is wrong and the corrected wording" } ],
  "new_findings": [ { "id": "<name>-N01", "severity": "HIGH|MEDIUM|LOW", "file": "...", "where": "...", "quoted": "...",
                      "problem": "...", "evidence": "...", "suggested_fix": "..." } ],
  "not_checked": ["..."] }
Language: Japanese (plain style) for notes, problems and fixes. Report only what you checked, with evidence.
Budget: about 70 tool calls.
`
const SCHEMA = {
  type: 'object',
  properties: {
    checker: { type: 'string' }, rule_check: { type: 'string' },
    results: { type: 'array', items: { type: 'object', properties: {
      finding: { type: 'string' }, status: { type: 'string' }, where_now: { type: 'string' }, note: { type: 'string' } },
      required: ['finding', 'status'] } },
    new_findings: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, severity: { type: 'string' }, file: { type: 'string' }, where: { type: 'string' },
      quoted: { type: 'string' }, problem: { type: 'string' }, evidence: { type: 'string' }, suggested_fix: { type: 'string' } },
      required: ['id', 'severity', 'file', 'problem', 'suggested_fix'] } },
    not_checked: { type: 'array', items: { type: 'string' } },
  },
  required: ['checker', 'rule_check', 'results', 'new_findings', 'not_checked'],
}
const TASKS = [
  { name: 'FV1', what: 'the 34 findings V1-01 .. V1-16 and V2-01 .. V2-18 (claims classified as verified, and the hand-written summaries in INDEX.md sections 1.1, 1.2, 6.1, 6.2 and HANDOVER.md sections 2.1, 2.2, 4.4)' },
  { name: 'FV2', what: 'the 23 findings F1-01 .. F1-09 and C1-01 .. C1-14 (facts about the stop and the save, omissions, scripts that must not be run, reuse wording, the added working files under materials/interrupted_fix/working_files/ and its README, NEW_DIRECTIVE.md against STOP_ORDER.md, the list of 32 candidates in INDEX.md 6.3 against 09_APPROX_STUDY/03_MODELS/candidates.json, the task table in 5.3, HANDOVER.md section 7)' },
]
phase('Verify')
const res = await parallel(TASKS.map(t => () =>
  agent(COMMON + `\nYOUR NAME: ${t.name}. Result file: ${OUT}/${t.name}.json\nASSIGNED: ${t.what}\n`, { label: 'verify-fix:' + t.name, phase: 'Verify', schema: SCHEMA })
    .then(r => r ? { ...r, checker: t.name } : null)))
const ok = res.filter(Boolean)
const bad = ok.flatMap(r => (r.results || []).filter(x => x.status !== 'RESOLVED').map(x => ({ ...x, checker: r.checker })))
const news = ok.flatMap(r => (r.new_findings || []).map(x => ({ ...x, checker: r.checker })))
log(`not resolved: ${bad.length}, new findings: ${news.length}`)
return { n_checked: ok.reduce((a, r) => a + (r.results || []).length, 0), not_resolved: bad, new_findings: news,
         rule_checks: ok.map(r => ({ checker: r.checker, rule_check: r.rule_check, not_checked: r.not_checked })),
         missing: TASKS.map(t => t.name).filter(n => !ok.some(r => r.checker === n)) }
