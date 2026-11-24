# 10 Model/effort allocation — details
**実行順序・並列数の正本は `12_FINAL_OPERATING_PLAN.md`。本表はモデル・担当の割当であり、全担当を毎回起動する命令ではない。**

## User-approved research routing
The researcher requests **different models/effort per phase**. Start agents only as needed by the audited gates; do not repeat expensive planning or validation without new evidence:

| Phase | Agent | Model | Effort | Job |
|---|---|---|---|---|
| P0 strategic architecture | `wlc-architect` | `claude-fable-5-2` | `high` | Read WLC theory, review A/B/C/D/E scope, design falsifiable work plan, select mathematical paths and interfaces |
| P1–P2 implementation/simulation | `wlc-waveform`, `wlc-formula-network`, `wlc-unit-mapper`, `wlc-resistor-energy` | `claude-opus-5-5` | `medium` | Independently derive mappings, write code and synthetic tests, simulate equipment timing and resistor/capacitor alternatives |
| F on-demand mathematical bridge | `wlc-math7-orchestrator` | `claude-opus-5-5` | `medium` | Use five locally available Python engines and authorized main-branch Math7 workflow; build an adapter for WLC cases only as separately tested research, report Sage/MATLAB NOT RUN if unavailable |
| P3 independent validation | `wlc-verifier` | `claude-opus-5-5` | `high` | Oracle, falsification, time boundaries, cross-route comparison, performance and claims |
| P4 evidence-based synthesis | `wlc-integrator` | `claude-opus-5-5` | `high` | Collect validated results, resolve definition/scale/branch/commit conflicts, integrate only verified equivalences |
| P5 new global planning | `wlc-replanner` | `claude-fable-5-2` | `high` | Review accepted proofs, failures, performance and unresolved issues, decide next cycle |
| Repeat only when new independent evidence or a concrete unresolved claim justifies another experiment. | | | | |

Read `11_MATH7_INTEGRATION.md` before delegating mathematical calculations. The Math7 source is on this repo's **main** branch, not on the WLC research branch. Existing seven-engine workflow supports only restricted algebraic cases; LCA operator calculations remain Python-only until adapters are validated. A GitHub API 403 in Claude Cloud cannot be treated as evidence that the math code is broken.

## Practical Claude Code configuration
- `.claude/settings.json` selects `claude-fable-5-2` with `effortLevel: high` as the **project startup default**, NOT a locked global model and NOT a switcher for an already-running main conversation.
- Every named subagent in `.claude/agents/` uses explicit `model: claude-...` and `effort: medium|high` frontmatter. **At runtime** Claude Code selects the appropriate model and effort per delegated subagent.
- Each route must be spawned/selected by the coordinator; merely storing files DOES NOT execute background sessions or automatically launch stages. The main conversation should remain at Fable High as the coordinator, with execution delegated to Opus Medium agents.
- Check model names and requested effort in the actual running agent session or logged model usage; never claim successful model switching based on YAML alone. Models can be unavailable due to subscription/organization/provider restrictions. If unavailable, record actual model/effort and report fallback before treating results as matched to requested routing.
- A session-wide `CLAUDE_CODE_SUBAGENT_MODEL` environment override or per-invocation `model` parameter can supersede agent frontmatter; inspect overrides when mismatches occur. On a provider with versioned aliases, prefer full model IDs specified here.
- `/model` and `/effort` can manually change a main interactive session. To rerun coordinator startup use this project branch, not `main`; project settings do not alter unrelated repositories.
- Do not use undocumented commands or assume an explicit built-in pipeline that alternates arbitrary models at stage boundaries; model routing is achieved by delegated subagents and explicit stage gates.

## Handoff contract
1. **P0:** `wlc-architect` produces `coordination/architecture.md` containing a hypothesis matrix, minimal pilot choice, route dependencies, model/effort log and acceptance criteria. Need not request routine confirmation.
2. **P1–P2:** Route A/B/C/E each owns `routes/<route>/` and produces `STATUS.md`, executable code, independent unit/boundary tests, measured outputs and failed cases. Do not edit shared files or other route folders. If tools support concurrency, run routes in parallel; otherwise interleave.
3. **P3:** Independent D must run actual tests against read-only copies of A/B/C/E outputs. Store `routes/D_verification/STATUS.md` and reproducible summary; don't assume same algorithms count as independent check.
4. **P4:** `wlc-integrator` composes only verified compatible outputs into `integration/`: model, code/tests, coverage, disagreements and benchmark. Failed candidates remain clearly separated.
5. **P5:** `wlc-replanner` issues `coordination/next_cycle.md` with accepted/rejected hypotheses, prioritized falsifiable experiments, exact file/commit lineage and stop criteria. A new cycle should target genuine unresolved questions rather than repeat existing steps.
6. All agents apply the original study restrictions. Evidence [P/E/F/S/L/H] requires provenance and a clear domain; non-sourced mathematical claims are not presented as established.
7. Any tasks requiring external account activation, model access, payment or privileged consent are escalated instead of silently circumvented.

## Security and parallel Git writes
- Original WLC theory, J-CAT sources, archive and WLC Studio remain unchanged.
- In one checkout, no parallel agents perform git checkout/commit on the same branch. Coordinator owns shared Git actions; agents own files in disjoint route directories.
- In separate session/worktree branches, verify HEAD and ensure branch is seeded from the project research branch. Preserve explicit route branch/commit provenance and merge only through review.
- Research setup does not guarantee completed research. Report configuration status separately from actually executed sessions and test evidence.

## Official references (for operational behavior)
- https://code.claude.com/docs/en/sub-agents
- https://code.claude.com/docs/en/model-config
- https://code.claude.com/docs/en/settings
