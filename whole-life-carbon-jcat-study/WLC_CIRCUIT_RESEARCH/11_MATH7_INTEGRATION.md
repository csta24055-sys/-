# 11 Math7 integration — existing capabilities and actual limits
**研究実行ゲートの正本は `12_FINAL_OPERATING_PLAN.md`。Math7は必要な数式の検証に用いる支援機能であって、WLCの各ケースに7エンジンすべてを強制起動しない。**
Status: configuration and usage protocol (2026-11-24), NOT a claim that 7 engines have all run on WLC models.

## Where the actual Math7 code lives
Repo: `csta24055-sys/-`, **branch `main`**.
Source: `math_tools_v2/`, `math_interop_v0/`.
Workflow: `.github/workflows/math-ir-efficient.yml` (on `main`).
Verified as source files: `math_tools_v2/requirements.txt`, `math_tools_v2/README.md`, `README-operators.md`, `examples/six_cases.json`, `examples/lca_ops_demo.json`.

**Important branch distinction:** WLC circuit experiment branch `claude/wlc-equivalent-circuit-20261124` was branched from an old WLC theory branch and **does not contain** Math7 source or the workflow. Do not assume that sharing the repository name `csta24055-sys/-` means the WLC experiment branch already contains the `main` Math7 files. `workflow_dispatch` is registered from the default branch, so select `main` when running the existing Math7 workflow unless relevant code is safely merged to a separately tested branch.

## User-facing setup — Claude Code Cloud (Math7 Cloud)
1. Start a NEW session, choose cloud environment `Math7 Cloud` and primary repo `csta24055-sys/-` with the **WLC circuit branch** `claude/wlc-equivalent-circuit-20261124` (or compatible session-allowed working branch derived from it). Do not attach the same repo twice merely to read `main`; safely fetch its ref and inspect the files in a separate temporary location. `main` and the circuit branch require separate directories/worktrees to access both simultaneously.
2. If only ONE repo selector is available, that's sufficient for Git reading: inside the existing checkout first `git fetch origin main:refs/remotes/origin/main`, then use `git show origin/main:math_tools_v2/README.md` and, if needed, `mkdir -p /tmp/wlc_math7_source && git archive origin/main math_tools_v2 math_interop_v0 | tar -x -C /tmp/wlc_math7_source`, or use a **separate read-only worktree** based on `origin/main` to access these directories. Never switch the experiment's main checkout away from its WLC branch while an agent is working.
3. Environment must have SymPy, NumPy, SciPy, mpmath, DuckDB; check imports and versions first. If unavailable, use environment setup/install only with permitted package access. Use the existing version pins from `main:math_tools_v2/requirements.txt`; no tokens, secrets or user information.
4. SageMath and MATLAB do not automatically become installed inside Claude Cloud when selected in a workflow file. Use Github Actions remote runner for portable-full, or supported local binaries only after checking they are genuinely installed; do not fake execution.
5. 403 for `gh api`/GitHub REST inside a Claude environment is an **access limitation of that session**. It does not prevent Git read or manual GitHub Actions web UI. Do not change security modes, add tokens or credentials just to bypass it. For creating or running workflows via GitHub API require legitimate authorized permissions, or have user launch manually.

## Modes and limits (READ BEFORE CLAIMING 'all seven')
- `portable-python`: existing five Python engines; `portable-full`: existing five + SageMath Docker + MATLAB Symbolic on Actions, for **safe restricted Math IR 0.1** inputs.
- `portable-full` currently covers 1–20 public JSON test cases from `math_tools_v2/examples/`, integer/rational/symbol/add/mul/integer powers, restricted unit labels, NOT arbitrary WLC differential equations, integrations, switching events or whole 70-unit models. Furthermore not every one of the seven engines performs every mathematical operation independently; follow actual `portable.py` implementation.
- `lca-operators` supports integration, piecewise time functions, masked sum products and node-spectrum cases but **currently runs as a Python-only path**. It does NOT automatically feed those operators into SageMath/MATLAB.
- `baseline-compact` is an older regression suite, NOT a generic WLC oracle.
- Public repo and GitHub Actions: only synthetic, public and independently created fixtures; absolutely no restricted J-CAT originals or personally identifying data.
- The source workflow was checked for structure, **not executed** here; SageMath/MATLAB jobs may fail due to image, package, runner, action, licensing or API differences. Do not mark 7/7 PASS without successful action logs and artifacts.
- GitHub's MATLAB Actions may automatically license common MATLAB products on **public repos**; verify the action's actual log and terms rather than storing a license key.

## Run existing supported Math7 tests now (without GitHub API in Claude)
On GitHub browser:
1. Open `https://github.com/csta24055-sys/-/actions/workflows/math-ir-efficient.yml`.
2. Choose **Run workflow** and the branch **main**.
3. Choose `portable-python` for five-engine smoke test or `portable-full` with `math_tools_v2/examples/six_cases.json` for seven-engine Math IR regression; `lca-operators` runs Python-only WLC operator experiment.
4. Open completed run → inspect individual Sage and MATLAB steps, logs, job conclusion. Download `math-ir-efficient-result` JSON artifact (retained **1 day**) immediately if needed.
5. Do not state a WLC circuit model was verified merely because `six_cases.json` passed.

## Connecting actual WLC circuit experiments
- Research agent: `.claude/agents/wlc-math7-orchestrator.md`; scope `WLC_CIRCUIT_RESEARCH/routes/F_math7_bridge/`.
- Phase I: use local five Python engines (SymPy for symbolic derivation, mpmath for high precision, NumPy/SciPy for numerical simulation and event boundaries, DuckDB for test/benchmark audit). Create independent checks for WLC route A/B/C/E synthetic equations.
- Phase II: adapt only **supported algebraic** expressions to Math IR 0.1 JSON, after unit/domain validation. For 7-engine GH Actions, a fixture must exist on the `main` branch in `math_tools_v2/examples/` (or a safely reviewed branch with matching workflow/code and appropriate dispatch). Don't publish unlicensed/private formulas.
- Phase III: **new adapter needed** for full WLC math: define safe AST/schema for integrals, piecewise/time events, impulses, recurrence and circuit differential equations; implement independent evaluation in SageMath/MATLAB as well as Python; test against direct oracle and restrictive input guards. Do not modify old Math7 code or WLC original blindly. Prototype only inside the circuit research route F; upstream integration later via explicit reviewed PR if needed.
- Phase IV: compare results and failure cases across engines; different numerical defaults and tolerances count as a research question. Record exact engine version, input SHA, Git ref/commit, boundary conventions, output file hashes and which engine really computed which expression.

## Runtime permissions and source integrity
- Read Math7 from `main`, WLC theory from `claude/wlc-theory-research-base-c33936`, new circuit code from `claude/wlc-equivalent-circuit-20261124`; these are THREE different refs even though they share one repo name.
- No writing into `main`, original WLC research or WLC Studio without explicit later authorization. New code goes into `WLC_CIRCUIT_RESEARCH/routes/F_math7_bridge/` on circuit research route branch.
- If GitHub Actions API remains blocked, provide exact artifact/Actions UI link and the manual steps. Do not assert a workflow was triggered if it wasn't.
