export const meta = {
  name: 'apply-round2-findings',
  description: 'Apply the 59 round-2 review findings: core definitions first, then unification evidence, approximation study and ledger, then an adversarial verify/fix loop',
  phases: [
    { title: 'Core', detail: 'reference calculation and unified model: exact time rule, validity rules, completeness' },
    { title: 'Build', detail: 'membership and mechanism evidence, ledger inputs, approximation study' },
    { title: 'Verify', detail: 'independent checkers attack the fixed code' },
    { title: 'Fix', detail: 'apply what the checkers found' },
  ],
}

const FIX = '/tmp/claude-0/-home-user--/49c0bd7e-a786-5ae4-9a1e-e89e7996ede3/scratchpad/recheck/fix'

const REPORT = {
  type: 'object',
  properties: {
    files_changed: { type: 'array', items: { type: 'string' } },
    findings: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' },
      status: { type: 'string', enum: ['FIXED', 'PARTLY_FIXED', 'DOCUMENTED_ONLY', 'NOT_DONE'] },
      what: { type: 'string' },
      how_checked: { type: 'string' },
    }, required: ['id', 'status', 'what', 'how_checked'] } },
    decisions: { type: 'array', items: { type: 'string' } },
    interface_changes: { type: 'array', items: { type: 'string' } },
    tests: { type: 'string' },
    acceptance: { type: 'array', items: { type: 'object', properties: {
      item: { type: 'string' }, result: { type: 'string' }, passed: { type: 'boolean' },
    }, required: ['item', 'result', 'passed'] } },
    open_problems: { type: 'array', items: { type: 'string' } },
    report_file: { type: 'string' },
  },
  required: ['files_changed', 'findings', 'decisions', 'interface_changes', 'tests', 'acceptance', 'open_problems', 'report_file'],
}

const FINDINGS = {
  type: 'object',
  properties: {
    earlier_findings: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' },
      state: { type: 'string', enum: ['RESOLVED', 'NOT_RESOLVED', 'CHANGED', 'NOT_CHECKED'] },
      evidence: { type: 'string' },
    }, required: ['id', 'state', 'evidence'] } },
    new_findings: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' },
      severity: { type: 'string', enum: ['HIGH', 'MEDIUM', 'LOW'] },
      area: { type: 'string' },
      statement: { type: 'string' },
      evidence: { type: 'string' },
      reproduction: { type: 'string' },
      proposed_fix: { type: 'string' },
    }, required: ['id', 'severity', 'area', 'statement', 'evidence', 'reproduction', 'proposed_fix'] } },
    checks_performed: { type: 'string' },
    could_not_check: { type: 'string' },
  },
  required: ['earlier_findings', 'new_findings', 'checks_performed', 'could_not_check'],
}

function stagePrompt(label, spec) {
  return `You are stage "${label}" of a staged fix of a research code base.\n\n` +
    `Read ${FIX}/COMMON.md and then ${FIX}/${spec} and carry the spec out completely and carefully. ` +
    `Your scratch folder is ${FIX}/${label}/ (create it). ` +
    `Take the time the work needs: read the code before changing it, run the acceptance checks for real, and iterate until they pass or you can say exactly why one does not. ` +
    `Before you return, write your final report as JSON (the same object you return) to ${FIX}/${label.toUpperCase()}_REPORT.json and put that path in report_file. ` +
    `Your return value is consumed by a script and by later stages: be exact and complete, no pleasantries.`
}

phase('Core')
const a1 = await agent(stagePrompt('a1', 'SPEC_A1.md'), { label: 'core:definitions+exactness', phase: 'Core', schema: REPORT })
log(`A1 done: ${a1 ? a1.findings.length + ' findings handled, ' + a1.open_problems.length + ' open problems' : 'NO RESULT'}`)

phase('Build')
const [chain, b2] = await parallel([
  async () => {
    const a2 = await agent(stagePrompt('a2', 'SPEC_A2.md'), { label: 'evidence:membership+mechanism', phase: 'Build', schema: REPORT })
    const b3 = await agent(stagePrompt('b3', 'SPEC_B3.md'), { label: 'ledger:inputs+counts', phase: 'Build', schema: REPORT })
    return { a2, b3 }
  },
  () => agent(stagePrompt('b2', 'SPEC_B2.md'), { label: 'approx:measurements', phase: 'Build', schema: REPORT }),
])
log(`Build done: A2 ${chain && chain.a2 ? 'ok' : 'NO RESULT'}, B3 ${chain && chain.b3 ? 'ok' : 'NO RESULT'}, B2 ${b2 ? 'ok' : 'NO RESULT'}`)

const rounds = []
for (let i = 1; i <= 2; i++) {
  phase('Verify')
  const prior = i === 1 ? '' : ` This is verification round ${i}: a fixer has just worked on the findings of round ${i - 1}; its report is ${FIX}/FIX${i - 1}_REPORT.json and the findings it worked on are ${FIX}/VERIFY${i - 1}_FINDINGS.json. Check that each was really resolved, then keep hunting for new problems.`
  const [vnum, vdef] = await parallel([
    () => agent(`You are an independent, adversarial checker (lens V-NUM, round ${i}).\n\nRead ${FIX}/COMMON.md and then ${FIX}/VERIFY_NUM.md and do what it says. Your scratch folder is ${FIX}/vnum${i}/ (create it). You must not change any file of the repository.${prior}\nNumber new findings VN${i}-1, VN${i}-2, ... Return the structured object; be exact, report only what you ran.`,
      { label: `verify:numeric#${i}`, phase: 'Verify', schema: FINDINGS }),
    () => agent(`You are an independent, adversarial checker (lens V-DEF, round ${i}).\n\nRead ${FIX}/COMMON.md and then ${FIX}/VERIFY_DEF.md and do what it says. Your scratch folder is ${FIX}/vdef${i}/ (create it). You must not change any file of the repository.${prior}\nNumber new findings VD${i}-1, VD${i}-2, ... Return the structured object; be exact, report only what you ran.`,
      { label: `verify:definitions#${i}`, phase: 'Verify', schema: FINDINGS }),
  ])
  const found = [vnum, vdef].filter(Boolean)
  const fresh = found.flatMap(v => v.new_findings)
  const unresolved = found.flatMap(v => v.earlier_findings.filter(e => e.state === 'NOT_RESOLVED' || e.state === 'CHANGED'))
  log(`Verify round ${i}: ${fresh.length} new findings, ${unresolved.length} earlier findings not resolved`)
  const round = { round: i, vnum, vdef }
  rounds.push(round)
  if (!fresh.length && !unresolved.length) break
  if (i === 2) { log('Second verification still has findings: left for the orchestrator'); break }
  phase('Fix')
  round.fix = await agent(
    `You are the fixer after verification round ${i} of a staged fix of a research code base.\n\n` +
    `Read ${FIX}/COMMON.md, ${FIX}/SPEC_A1.md and ${FIX}/SPEC_A2.md (the decisions already taken: they stay binding), and the reports ${FIX}/A1_REPORT.json and ${FIX}/A2_REPORT.json. ` +
    `Two independent checkers then attacked the fixed code. First write their findings, exactly as given below, to ${FIX}/VERIFY${i}_FINDINGS.json. Then, for each new finding and each earlier finding that is NOT_RESOLVED or CHANGED: reproduce it yourself first; if it is real, fix it in BOTH calculations (reference and unified model) following the general principle of SPEC_A1, keep docstrings exact, add a test and a mutation that would have caught it; if it is not real, say why with evidence. ` +
    `Files you may change: refcalc/*.py, fastcalc/*.py, common/compare.py, synth/model.py (small helpers only), bench/mutations.py, bench/verify_unified.py (scenarios/exactness/sweep_check only), bench/membership_check.py, bench/mechanism_probe.py, tests/*.py, and 01_LEDGER/units.json through "python3 -B -m tools.sync_ledger". ` +
    `Keep every function name and signature that bench/approx_study.py, bench/input_usage.py, bench/membership_check.py and bench/mechanism_probe.py import (other stages already adapted to them); at the end run: python3 -B -c "import bench.approx_study, bench.input_usage, bench.membership_check, bench.mechanism_probe, bench.verify_unified" and the unit tests, and a reduced exactness run (import bench.verify_unified; exactness(120, 30); sweep_check(16); no study file written). ` +
    `Your scratch folder is ${FIX}/fix${i}/. Write your report JSON to ${FIX}/FIX${i}_REPORT.json and return the same object.\n\n` +
    `FINDINGS OF THE CHECKERS (JSON):\n${JSON.stringify({ new_findings: fresh, earlier_not_resolved: unresolved }, null, 1)}`,
    { label: `fix:after-verify#${i}`, phase: 'Fix', schema: REPORT })
}

return { a1, a2: chain ? chain.a2 : null, b3: chain ? chain.b3 : null, b2, rounds }
