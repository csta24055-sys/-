# Brief for the checkpoint readers (read-only classification of a TERMINATED study)

## Situation

The study in `/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/` ("simplification /
unification / approximation of the formulas of an independent whole-life-carbon concept
model", called below "the old study") was TERMINATED by the user's directive on 2026-11-11,
unfinished. It will not be completed. Your job is to help classify what exists, so that an
index and a handover document can be written. You are a reader, not a researcher.

## Hard rules (violating any of them makes your work unusable)

1. READ ONLY. Do not create, change or delete any file inside `/home/user/-`. Do not run any
   git command that changes anything (no add/commit/checkout/reset/stash/revert/apply).
   Allowed git commands: `git log`, `git show`, `git diff`, `git ls-files`, `git grep`.
2. DO NOT RUN THE OLD STUDY. No tests, no benchmarks, no tools, no generators, no import of
   `refcalc`, `fastcalc`, `bench`, `synth`, `tools`, `common` from any Python process. The
   directive forbids resuming any calculation of the old study, even to check something.
   Python may be used ONLY to parse text / JSON / Markdown files (json.load, re, counting).
   Do not "quickly re-check" a number by computing it with the study's code. If a statement
   can only be confirmed by running the study, say "not confirmed (would need a run)".
3. Do not continue, repair or improve anything. No fixes, no new formulas, no new analysis of
   the model. Classification and description only.
4. Compliance (binding, `whole-life-carbon-jcat-study/01_COMPLIANCE/README.md`): the
   repository contains no J-CAT original files, formulas, factors or macros and none may be
   reproduced from memory or the web. Every number in the old study is fictional (synthetic).
   The old study examined an INDEPENDENT CONCEPT MODEL (70 "evaluation units"), not the
   original workbooks. Never write that something is compatible with, equivalent to, or
   verified against J-CAT.
5. Write your only output file under
   `/tmp/claude-0/-home-user--/49c0bd7e-a786-5ae4-9a1e-e89e7996ede3/scratchpad/checkpoint/`
   (file name given in your task). Your final structured answer is a short summary; the
   detail goes into the file.
6. No web access is needed. Do not use it.
7. People: if you must refer to a person whose pronouns are unknown, use they/them. Do not
   put any e-mail address or personal name into your output.

## Where things are

Repository root: `/home/user/-`. Branch `claude/jcat-formula-approximation-study-c33936`.

Commits that matter:
- `43ba5d7`: last version in which code, measurements, records and reports were regenerated
  together (after the FIRST independent review round and its fixes).
- `60e720f`: + a draft of the protocol v1.4 (only parts not depending on later fixes).
- `65ff124`: snapshot of the working tree at the stop = interrupted, UNVERIFIED edits of the
  second-round fix (stage a1 "reference definitions / exact time rule / validity rules" and
  stage b2 "approximation-study measurements" were finished by their agents and are
  self-reported only; stage a2 "membership / mechanism evidence + engine refactor" was
  interrupted mid-way; stage b3, the verify/fix loop, records/reports regeneration: never
  started).
- `0db5c77`: revert of `65ff124`; the working tree of `09_APPROX_STUDY` is again identical
  to `60e720f`. HEAD (plus archive commits) is this state.

Old study (as committed, state `60e720f`):
`whole-life-carbon-jcat-study/09_APPROX_STUDY/` with
`00_POLICY` (directive, amendment, evaluation protocol), `01_LEDGER` (70 units, sheet
families, unlinked inputs), `02_RANKING` (axis A measured load, axis B judged room for
simplification), `03_MODELS` (unified models K1-K7, DERIVATIONS.md, candidates, records),
`04_VERIFICATION` (exactness, load, approximation study, input usage, INDEPENDENT_REVIEW.md),
`05_DECISIONS` (progress ledger, 9 required deliverables), `06_OPEN_ISSUES`,
`07_MATERIAL_TAXONOMY` (classification design draft), `research_code` (`refcalc` reference
calculation, `fastcalc` unified model, `synth` fictional scenario generators, `bench`
measurements, `tools` generators of records/reports, `tests`, `common`).
Chapters `01_COMPLIANCE` .. `08_BUILD_PLAN` one level up are older material of the same
project (requirement analysis); they are context, not part of the old study.

Archive (new, committed):
`whole-life-carbon-jcat-study/research_archive/real_equation_checkpoint/`
- `STOP_STATUS.md` (stop record; read it first)
- `materials/round2_review/triage/{numeric,rederive,records,approx,reports}.md`: the 59
  findings of the SECOND independent review (ids NUM-1..11, RED-1..12, REC-1..9, APP-1..9,
  REP-1..18) with the verdicts of adversarial verifiers (33 CONFIRMED, 8 PARTLY_CONFIRMED:
  RED-3, RED-9, RED-11, REC-3, REC-6, APP-1, APP-4, APP-8; 0 refuted; the 18 REP findings had
  no second verifier, the orchestrator re-ran the checker's script and they reproduced).
  `res.json` is the raw structured result.
- `materials/round2_review/checker_scripts/`: the checkers' reproduction scripts (they ran
  against the code of `43ba5d7`).
- `materials/interrupted_fix/specs/`: what the interrupted fix was supposed to do
  (`SPEC_A1.md`, `SPEC_A2.md`, `SPEC_B2.md`, `SPEC_B3.md`, `STAGE_C_NOTES.md`, verify prompts).
- `materials/interrupted_fix/agent_reports/`: `A1_REPORT.json`, `B2_REPORT.json`,
  `B2_REPORT_long.json` etc. = SELF-REPORTS of the two finished stages. Treat as claims.
- `materials/interrupted_fix/a2_partial_outputs/`, `b2_output/`, `a1_scratch/`: outputs of
  those stages (unverified).
- `materials/interrupted_fix/working_tree_at_stop_65ff124.patch`: the interrupted edits.
- `materials/earlier_session_scratch/`: working files of earlier stages.

The FIRST review round and what was done about it is described in
`09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md`. That file says nothing about the
second round (it was never updated).

## The five categories (directive 0-2)

Every item you report gets exactly one STATE category 1-4, and independently a reuse note
(category 5 is a cross-cutting list built from the reuse notes).

1. 検証済み成果 (verified outcome). Use ONLY if all of these hold:
   (a) there is a recorded check (a measurement on fictional data and/or a derivation) in
       the committed state `60e720f`,
   (b) the outcome was examined by an independent review round and was reproduced or not
       contradicted, OR it is a plain recorded fact that the second-round checkers
       re-computed and matched,
   (c) no CONFIRMED / PARTLY_CONFIRMED second-round finding contradicts or weakens the
       statement AS YOU WORD IT. If a finding weakens the published wording, you must
       narrow the statement to what still stands (field `claim_that_stands`) and list the
       withdrawn wording (field `claims_not_to_rely_on`). If nothing meaningful stands
       after narrowing, the item is not category 1.
   Always state the scope: fictional data only; independent concept model only; which
   population; which tolerance. "Verified" never means practical accuracy on real
   buildings and never means agreement with any original workbook.
2. 暫定・未検証成果 (provisional / unverified outcome): produced, but not independently
   examined, or affected by unresolved second-round findings, or produced by the
   interrupted fix (self-reported), or generated text that is known to be wrong in places.
3. 研究途中の数式・仮説 (formulas and hypotheses in progress): formulas, modelling ideas,
   candidate approximations on hold, design decisions for fixes that were specified but not
   (verifiably) implemented, proposals of judges, unfinished designs.
4. 不具合・未解決事項 (defects and open issues): known defects, open questions, limits,
   things explicitly not done.

When in doubt between 1 and 2, choose 2. Never upgrade.

## Reuse note (for category 5)

The NEW research (not started; you do not do it) will try to re-express the whole
calculation system of building LCA with a very small number of common mathematical
transformations (candidates named by the directive, not limiting: Fourier / Laplace
transforms, SVD, POD, mode decomposition, matrix / tensor operations, convolution,
generating functions, model order reduction), accepting more complicated equations if the
number of transformation kinds drops, and comparing three routes:
Route A = reuse the saved simplification outcome; Route B = rebuild from the original
equations, not bound by the old outcome; Route C = mix. The reference calculation must not
be changed in the new research, and unverified results must not be treated as verified.

For each item say whether it is a reuse candidate, for which routes, how it would be used
and under which conditions / cautions (e.g. "only for well-formed inputs", "definition has
known holes RED-x", "needs the unverified fix of 65ff124").

## Output file format (JSON, UTF-8)

```json
{
  "lens": "R3",
  "read": ["paths you actually read (repo-relative from /home/user/-)"],
  "items": [
    {
      "id": "CK-R3-01",
      "title": "日本語の短い題",
      "what": "何であるか（日本語、常体、1〜3 文。専門用語は必要なものだけ）",
      "locations": ["whole-life-carbon-jcat-study/09_APPROX_STUDY/..."],
      "state_category": 1,
      "checked_how": "どう確かめたものか（測定・導出・試験。母集団、許容差）",
      "checked_by": "作成者のみ | 独立検査（第1回）| 独立検査（第2回）で再現 | 中断した修正の自己申告 | なし",
      "scope": "言える範囲（架空データ、独立概念モデル、など）",
      "round2_findings": ["NUM-1", "REC-5"],
      "round2_effect": "第2回の指摘がこの成果に与える影響（なければ「なし」）",
      "claim_that_stands": "今の時点で言ってよいこと",
      "claims_not_to_rely_on": ["既存の文書にあるが、使ってはいけない記述"],
      "reuse_candidate": true,
      "reuse_routes": ["A", "C"],
      "reuse_how": "新研究での使い道",
      "reuse_conditions": "条件・注意",
      "evidence": ["file:line or JSON key that supports your classification"]
    }
  ],
  "not_covered": ["things in your lens you could not read or classify, with reason"]
}
```

Language of all item text: Japanese, plain style (常体), concrete, no praise words, no vague
words. Use the study's own terms as they appear in its Japanese documents. Keep numbers
exactly as recorded and say where each number comes from.

Granularity: one item per distinct outcome a successor would look up (a model, a
measurement result, a ledger, a derivation, a generator, a design draft, a defect group ...),
typically 8-25 items per lens. Do not make one item per file when several files are one
outcome, and do not merge outcomes with different verification states.
