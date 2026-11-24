# Route F — Math7 bridge (restricted Math IR 0.1 feasibility, item N5)

Connects the existing Math7 code on **`csta24055-sys/-` `main`** to the WLC circuit
study on branch `claude/wlc-equivalent-circuit-20261124` **without modifying either**.
Status and verdicts: `STATUS.md`. Per-case table: `CASES.md`. Claims and limits: `claims.md`.

## Source provenance (three different refs, one repo name)
| what | ref / location | how it was read |
|---|---|---|
| WLC circuit branch | `claude/wlc-equivalent-circuit-20261124` @ `c72fa7f` | working checkout (not switched) |
| Math7 code | `origin/main` @ `c354037` (last Math7 change 2026-11-13) | read-only copy `/opt/math7` + `git show origin/main:<path>` |
| equality of the two | SHA-256 of `math_tools_v2/portable.py`, `math_interop_v0/phase{1,2,4}.py`, `phase3_matlab.m`, `.github/workflows/math-ir-efficient.yml` identical in `/opt/math7` and `git show origin/main:` | `sha256sum` |

No branch switch, worktree, checkout, commit or push was performed. `git ls-remote`/`git
rev-parse origin/main` (Git read) worked. No GitHub REST/`gh api` call was made, so no API 403
was observed in this task; an API 403 would be a session access limit and does not prevent Git
read or the manual Actions web UI (see `../../11_MATH7_INTEGRATION.md`).

## Layout
```
code/ir.py              IR node builders + independent Fraction / mpmath evaluators (no SymPy, no Math7 import)
code/build_inputs.py    builds inputs/*.json (<=20 cases) + *.expected.json; expected values are READ from
                        routes/A_waveform/results/points.json, routes/E_resistor_energy/results/{points,e_numbers}.json
code/probe_ops.py       runs real `math7 prepare` on 44 one-construct probes -> probes/*.json, results/probes.json
code/check_results.py   per-engine comparison of a math7 output dir with the expected sidecar
code/check_artifact.py  same comparison for a downloaded GitHub Actions result.json (not yet used: no artifact)
code/make_cases_md.py   renders CASES.md
code/run_all.sh         end-to-end local run (5 Python engines only)
inputs/                 wlc_pilots_p0_p1_p2 (17), wlc_route_e_identities (17), negative_wrong_expected (2)
results/<input>/        log.txt (exact commands + outputs), plan/manifest/result/python_graph.json, expected_check.json
results/probes.json     accepted/rejected constructs with the validator's own error messages
```

## Reproduce (local, ~40 s)
```
bash whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/routes/F_math7_bridge/code/run_all.sh <SCRATCH_DIR>
math7-py -B whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/routes/F_math7_bridge/code/make_cases_md.py
```
`math7 prepare` refuses to overwrite a plan, so `SCRATCH_DIR` must be outside the repo and fresh
per run (the cache directories stay there; only compact JSON is copied to `results/`).
The negative input is expected to give `ROUTE-F EXPECTED-VALUE CHECK: FAIL` (exit 1) while
`math7 prepare/verify-python/audit-python` all PASS — that is the point of the control.

## How a SageMath + MATLAB (seven-engine) run could be done — NOT_RUN, user action required
Workflow on `main`: `.github/workflows/math-ir-efficient.yml`, name
**"Math IR Efficient - One Job and Variable Cases"**, mode `portable-full`
(5 Python engines, then `sagemath/sagemath:10.10` Docker running `phase1.py sage`, then
`matlab-actions/setup-matlab@v3` + Symbolic Math Toolbox running `phase3_matlab.m`, then
`portable.py verify-full` / `audit-full`).

Blocking facts (read from the workflow file):
1. `case_file` must match `^math_tools_v2/examples/[A-Za-z0-9_-]+\.json$` **on the dispatched
   branch**. These inputs live on the WLC branch under `routes/F_math7_bridge/inputs/`, and the WLC
   branch has neither the workflow nor `math_tools_v2/`. So the fixture must first be placed at e.g.
   `math_tools_v2/examples/wlc_route_e_identities.json` on `main` or on a separate branch cut from
   `main`. That is a write outside route F and needs the user's explicit authorization.
2. The `pull_request` trigger (paths `math_tools_v2/**`) runs with the DEFAULT fixture
   `six_cases.json`, so a PR alone would not test the WLC fixture; a `workflow_dispatch` with
   `case_file` set is needed.
3. Only the user (or an agent with legitimately granted permission, on the user's explicit request)
   may start it. Manual path: GitHub → `csta24055-sys/-` → **Actions** → "Math IR Efficient - One Job
   and Variable Cases" → **Run workflow** → branch (main, or the reviewed branch holding the fixture)
   → mode `portable-full` → case_file `math_tools_v2/examples/<name>.json` → Run.
4. Completion must be checked on the run page (or `gh run view <id>`), not by dispatch success:
   the "Run SageMath 10.10" and "Independently evaluate in MATLAB" steps must be green, and the job
   must conclude `success`. Download artifact `math-ir-efficient-result` within 1 day (retention), then
   `math7-py -B code/check_artifact.py inputs/<name>.json inputs/<name>.expected.json result.json`.
   Only a `mode: full-seven` artifact whose `engine_coverage` lists SageMath and MATLAB counts.

Inputs are synthetic, contain no J-CAT originals, no personal data and no secrets.
