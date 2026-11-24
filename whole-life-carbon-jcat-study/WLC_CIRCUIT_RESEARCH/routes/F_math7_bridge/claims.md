# claims — Route F

Evidence classes per `07_SHARED_CONTRACT.md`. Source refs: WLC branch `c72fa7f`, Math7 `origin/main` `c354037`.

## Established here
- **[E] F-1 IR inventory.** Restricted Math IR 0.1 (`math-ir/0.1`, portable `math-ir-portable/1`) accepts
  exactly: `integer`, canonical `rational`, declared `symbol` (domain `rational`, constraint
  `nonnegative`, nonnegative rational substitution required, ≤ 8 symbols), binary `add`, binary `mul`,
  `pow` with integer exponent 0..8; depth ≤ 18; unit `"1"` or `"kgCO2e"`; `exact: true`; 1..20 cases;
  no extra envelope fields. Rejected (validator message in `results/probes.json`): `sub`, `div`, `neg`,
  negative / rational / symbolic exponents, exponent 9, `sqrt`, `sin`, `cos`, `exp`, `pi`, `floor`,
  `frac`, `min`, `max`, `abs`, `lt`, `piecewise`, `integral`, `sum`, ternary `add`, `float`,
  non-canonical rationals, depth 19, units `J`/`kg`, `exact:false`, real domain, negative or missing
  substitution, 21 cases, an `expected` field. Subtraction = `add(a, mul(-1,b))`; division only by a
  rational constant. Source: `main:math_interop_v0/phase1.py` (`check_node`, `check_envelope`),
  `main:math_tools_v2/portable.py` (`validate_bundle`, `MAX_CASES=20`).
- **[E] F-2 arithmetic agreement.** For 34 cases, the restricted-IR expressions evaluate exactly to
  the values published by routes A and E (`CASES.md`), confirmed by Math7's SymPy (+ NumPy/mpmath
  renderings, DuckDB group sums) and by route F's two independent evaluators.
- **[E] F-3 negative control.** Math7 portable `prepare/verify-python/audit-python` PASS for an input
  whose route-F expected value is deliberately wrong; route F's comparator FAILs it on every engine.
  Math7's own audit negative control (rehashed cached float corruption) is rejected in all 3 runs.

## Explicitly NOT established
- **Not a seven-engine validation**, and not a validation of the WLC model. SageMath and MATLAB were
  NOT_RUN. Only five Python libraries ran, and of those only SymPy evaluates each case; NumPy and
  mpmath re-render SymPy's exact value, SciPy runs one fixed unrelated quadrature, DuckDB sums groups.
  The Math7 pipeline proves internal consistency and tamper-resistance, **not** correctness against an
  external expected value (F-3).
- **Event counting is not checked.** n10, n20, nR, the P1 policy σ, min(t,10), max(t−10,0) and the
  H-E4 branch κ(t)=1/4 are computed in Python by `code/build_inputs.py` and passed in as constants.
  Boundary conventions (right/left/orig) are therefore outside the IR; only the `right` convention
  values were encoded.
- **Kernels, comparators, θ_ε, the A-6 ramp−sawtooth identity**: not expressible (floor/frac/min/max/lt).
- **Route E transcendental content**: the sin-term cancellation of the AC energy over whole periods,
  the ripple sup 1/π at t=3/8, and the cross term 2√(A1A2)ρ itself (only its square 4A1A2ρ² is
  checked; sign and the L2 inner product producing ρ are not), Walsh orthogonality (cross integrals
  assumed 0), thermal θ(60) with exp. Joules are labelled unit `"1"` because `J` is not an allowed unit.
- **Refrigerant recurrence, masked sum-products, 70-unit model, integrals/time functions**: outside
  restricted IR. `lca-operators` handles some of these but is Python-only (not run here).

## Would SageMath + MATLAB add meaningful evidence for these inputs?
Little. Both would independently evaluate the same rational add/mul/pow ASTs (`phase1.sage_eval`,
`phase3_matlab.m` `eval_ast` with `sym`), adding implementation diversity for arithmetic that is
already exactly confirmed by two independent evaluators. It would mostly exercise the Math7 pipeline
on new fixtures. It would add nothing about event counting, kernels, trig/sqrt identities or circuit
dynamics, which is where the study's open questions are. Meaningful seven-engine evidence for WLC
requires a **new adapter** (schema for floor/min/max/compare/piecewise, sqrt/sin/pi, definite integrals
of piecewise-polynomial and trig integrands, bounded recurrences; matching Sage and MATLAB evaluators;
fail-closed validation; direct-oracle tests; separate review). Not implemented in this task.
