# STATUS — Route F (Math7 bridge, item N5)

Date 2026-11-24. Branch `claude/wlc-equivalent-circuit-20261124` @ `c72fa7f` (not committed by F;
the coordinator serializes git). Math7 source `origin/main` @ `c354037`, read via `/opt/math7`
(byte-identical, see README). Model actually run: **Opus 5.5** (`claude-opus-5-5`, self-reported);
effort level is **not observable** from inside the session.

## Verdicts
| item | status | evidence |
|---|---|---|
| Python engine availability (SymPy 1.14.0, NumPy 2.2.6, SciPy 1.15.3, mpmath 1.3.0, DuckDB 1.4.1; Python 3.13.18) — equals `main:math_tools_v2/requirements.txt` pins | **PASS** | `results/engine_versions.txt`, `python_graph.json:engine_versions` |
| Restricted Math IR 0.1 operation inventory (44 probes through real `math7 prepare`) | **PASS** (11 accepted / 33 rejected as the validator predicts) | `results/probes.json`, `probes/*.json`; validator `main:math_interop_v0/phase1.py` `check_node`/`check_envelope`, `main:math_tools_v2/portable.py` `validate_bundle` |
| `inputs/wlc_pilots_p0_p1_p2.json` (17 cases): prepare / verify-python / audit-python | **PASS / PASS / PASS** (87 Python nodes, 87 cache hits, tamper rejected) | `results/wlc_pilots_p0_p1_p2/log.txt` |
| same, route F expected-value check (17/17 cases; DuckDB group) | **PASS** | `results/wlc_pilots_p0_p1_p2/expected_check.json`, `CASES.md` |
| `inputs/wlc_route_e_identities.json` (17 cases): prepare / verify-python / audit-python | **PASS / PASS / PASS** | `results/wlc_route_e_identities/log.txt` |
| same, route F expected-value check (17/17; DuckDB groups `1`, `kgCO2e`) | **PASS** | `results/wlc_route_e_identities/expected_check.json` |
| Negative control `inputs/negative_wrong_expected.json` (2 cases, wrong expected 55 for 1376/25; residual form) — Math7 prepare/verify/audit | **PASS / PASS / PASS** (expected: Math7 has no expected-value field) | `results/negative_wrong_expected/log.txt` |
| Negative control — route F expected-value check | **FAIL as intended** (2/2 cases FAIL on SymPy, NumPy, mpmath, F_Fraction, F_mpmath60; both DuckDB groups FAIL) | `results/negative_wrong_expected/expected_check.json` |
| `check_artifact.py` self-test on local python-five results | PASS (pos.) / FAIL (neg.), both labelled "NOT a seven-engine artifact" | `results/check_artifact_selftest.txt` |
| SageMath 10.10 evaluation of these inputs | **NOT_RUN** | not installed locally; only on GitHub Actions |
| MATLAB + Symbolic Math Toolbox evaluation | **NOT_RUN** | same |
| Seven-engine (`portable-full`) run of these inputs | **BLOCKED** — needs (a) the fixture under `math_tools_v2/examples/` on the dispatched branch (write outside route F; user authorization), and (b) a user-started `workflow_dispatch` | README "How a SageMath + MATLAB run could be done" |
| N5 (i) P0 closed form with floor / A-6 ramp−sawtooth (frac) | **BLOCKED in IR** (floor, frac rejected) — only arithmetic with supplied counts checked | probes `floor`, `frac` |
| N5 (ii) year-cell kernel clip(T−k,0,1), θ_ε | **BLOCKED in IR** (min, max, lt, piecewise rejected) | probes `min`,`max`,`lt_comparison`,`piecewise` |
| N5 (iii) AC energy identity with sin, ρ cross term with sqrt, ripple 1/π at t=3/8 | **BLOCKED in IR** (sin, cos, sqrt, pi, rational exponent rejected) — only post-cancellation r·t and the SQUARED cross term checked | probes `sin`,`sqrt`,`pi_constant`,`pow_rational_exponent_sqrt` |
| General WLC operator adapter (integrals, events, recurrence, masked sum-products) to SageMath/MATLAB | **NOT_RUN / not implemented** — would need new schema, Sage + MATLAB evaluators, tests and separate review | `claims.md` |

## Per-engine summary (34 positive cases)
| engine | role in Math7 portable | per-case result vs published expected |
|---|---|---|
| SymPy | the only Math7 engine that evaluates the AST | 34/34 PASS |
| NumPy | float64 rendering of the SymPy exact value | 34/34 PASS (hex == float(expected)) |
| mpmath | 80-digit decimal rendering of the SymPy exact value | 34/34 PASS (decimal − recorded diff == expected) |
| SciPy | one fixed ∫₀¹x² quadrature reference, independent of the cases | N/A per case (reference PASS inside prepare/verify) |
| DuckDB | per-unit grouping, exact Fraction sum | 3/3 groups PASS |
| route F Fraction evaluator (not Math7) | independent exact AST evaluation | 34/34 PASS |
| route F mpmath 60-dps evaluator (not Math7) | independent floating AST evaluation | 34/34 PASS |
| SageMath / MATLAB | independent AST evaluation (Actions only) | NOT_RUN |

Wall time of `code/run_all.sh` (build + 44 probes + 3 inputs): 40 s real.
