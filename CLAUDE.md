# Project instructions — WLC equivalent-circuit research

This branch is an isolated research workspace for constructing and testing **electrical equivalent circuits for building whole-life carbon (WLC)**.

## Mandatory startup
For any WLC/circuit task, read, in order:
1. `whole-life-carbon-jcat-study/WLC_THEORY_RESEARCH_BASE/00_README.md`
2. `whole-life-carbon-jcat-study/WLC_THEORY_RESEARCH_BASE/13_別チャット引継ぎ文.md`
3. `whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/00_START_HERE.md`
4. `whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/01_FORMAL_MODEL.md`
5. `whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/02_VERIFICATION_PLAN.md`
6. `whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/03_EXECUTION_PLAN.md`
7. `whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/05_SOURCE_MAP.md` — cross-repository source navigation.
8. `whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/06_PARALLEL_ORCHESTRATION.md` — **current primary autonomous execution policy**.
9. `whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/07_SHARED_CONTRACT.md` — fixed names, units, boundaries and route outputs.
10. `whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/08_AUTONOMOUS_START.md` — one-message start instructions.
11. `whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/09_RESISTOR_ENERGY_ROUTE.md` — **independent Joule-heating route**, a user-prioritized alternative to capacitor charging.

Read the base's `05_時間スペクトルの理論.md`, `06_建物全体の統一方程式.md`, `07_動的LCAと工程時間.md`, `09_未解決問題と限界.md`, and `15_劣化・寿命・交換モデル研究開始資料.md` before formal conclusions.

## Additional read-only reference repository
- `csta24055-sys/lastdance4-tree-` (`main`) is the Yes/No classification/index of 2,100 development roles. It is **not** the original WLC source or a mathematical proof. Search relevant A3 (math), A6 (verification), A9 (knowledge), optionally A2 (classification), then follow exact role/source references into `csta24055-sys/lastdance` only if needed.
- Use `WLC_CIRCUIT_RESEARCH/05_SOURCE_MAP.md` to keep source repo, branch, file path, role/claim IDs and verification status separately documented.
- Prioritize the WLC theory base for formulas and validity, not ability-tree descriptions.

## Mandatory model / effort orchestration
- Read `whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/10_MODEL_ROUTING.md` **before launching work**. This project starts at Fable 5.2 High through `.claude/settings.json`. Delegate **architecture and re-planning** to `wlc-architect` and `wlc-replanner` (Fable 5.2 High); **implementation and simulation** to the four independent route workers (Opus 5.5 Medium); **independent verification** to `wlc-verifier` (Opus 5.5 High); **evidence integration** to `wlc-integrator` (Opus 5.5 High).
- Sequence P0 (architecture) → P1/P2 (A/B/C/E parallel execution) → P3 (D verification) → P4 (integration) → P5 (Fable review/replanning). Iterate selectively after actual evidence. Do not accidentally have all subagents inherit the startup model.
- Validate actual selected models/efforts in logs; if subscription/provider disallows requested models, record fallback and notify rather than claiming success. Project config is not an ongoing daemon and does not start subagents automatically. Each agent must be invoked.
- Where session-level/CLI overrides take precedence over frontmatter, inspect and report mismatches.

## Parallel execution policy (supersedes serial phase ordering only)
- Prefer **five independent research routes A capacitor/waveform, B formula-network, C 70-unit map, D independent verifier, and E resistor/Joule-energy**, as specified by `06_PARALLEL_ORCHESTRATION.md`. Launch concurrently when supported; otherwise interleave. Crucially, **Route E starts from cumulative resistor dissipation `E_R(t)=∫i²R dt` rather than capacitor charge**. Do not require E to adopt A's capacitor approach.
- Project subagents `.claude/agents/wlc-waveform.md`, `wlc-formula-network.md`, `wlc-unit-mapper.md`, `wlc-verifier.md`, `wlc-resistor-energy.md` define route-specific behavior. In independent sessions verify you have checked out a project-seeded route branch. Unrelated worktrees may start from `main`; never presume a newly created worktree contains this research.
- **Each worker owns only its route subfolder** under `WLC_CIRCUIT_RESEARCH/routes/`; coordinator alone edits shared files and the future `integration/` folder. Do not let concurrent agents change a shared branch HEAD or commit in one shared checkout. Separate branch/session work is preferable for independent writes.
- A, B and E attempt different constructive routes, C independently maps all 70 unit roles (21 direct, 49 other), D tests and challenges all routes. Integrate supported results only after meeting a documented compatibility/verification gate. Unsupported mapping, non-existence and hybrid exceptions are valid findings, not prompts for unending retries.
- Do not block on routine approvals; act within documented permissions, execute tests, record status and counterexamples. The presence of instructions or named agents does not mean the research sessions are running.

## Non-negotiable boundaries
- Never edit `whole-life-carbon-jcat-study/WLC_THEORY_RESEARCH_BASE/`, existing research chapters 09–23, the original `research_archive/`, or the WLC Studio application. Treat all as immutable references.
- Put new work only under `whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/` on a dedicated research branch. Never push the experiment to `main` or to the preserved source branches.
- No licensed J-CAT formula bodies, coefficients, values, cell addresses, original documents, restricted data, personal identifiers, or credentials in GitHub. Only use independent synthetic examples and authorized public data.
- Distinguish cumulative **actual-time emissions** `G(t)` from the existing **evaluation-horizon-dependent WLC model** `C(T)=M([0,T])+Z(T)`. Do not infer actual release timing from a WLC total alone.
- A waveform resemblance or a capacitor analogy is **not** a novel discovery. Measure exact equivalence, assumptions, state requirements, approximation error, runtime, and usefulness against the existing canonical model.
- One single capacitor can accumulate the sum of currents but cannot preserve independently different replacement ages without additional state/control logic.
- An unrectified, zero-mean AC input does not create monotonic accumulated charge in an ideal capacitor. Use a separately justified clock/rectifier/integrator/trigger scheme where appropriate.
- Follow the base evidence tags [P] proof, [E] exact rational samples, [F] numerical comparisons, [S] statistical, [L] literature, [H] hypothesis. Document domain and provenance; self-authored proofs await independent review.
- Python checks: `python3 -B` with `PYTHONDONTWRITEBYTECODE=1`; no network or repository writes from tests. Preserve original test oracles.
- Route A starts with the two-equipment pilot. Routes B and C may **independently begin** broad formula/70-unit taxonomy from the outset; don't claim full equivalence before tests.

## Delivery definition
A task is not finished merely because diagrams or text exist. Deliver derivation, independent reference computation, tests including event boundaries and overlapping replacements, explicit counterexamples, limitations, operation-count/memory/time comparison, and a short understandable summary. If a phase is incomplete, state precisely what is missing.
