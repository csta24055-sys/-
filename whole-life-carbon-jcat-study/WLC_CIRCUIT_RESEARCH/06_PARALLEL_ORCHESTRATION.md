# 06 Research route definitions — independent approaches A/B/C/D/E and support F
**本書は研究内容・担当の詳細であり、実行順序と並列数は `12_FINAL_OPERATING_PLAN.md` が優先。** A/Eは異なる回路の小型実証、Bは数式種別、Cは70単位の台帳、Dは独立検証、Fは必要時の数式処理支援。初回から全研究をフル実装しない。
Status: task architecture, **not validated research**. User intent: let Claude investigate broadly and autonomously; do not lock the whole effort to a single favored equivalence.

## High-level question
Can the existing independent, synthetic WLC model be **represented, evaluated, or reduced** using electrical circuit mathematics in a way that adds real analytical/computational value? Evaluate competing constructions rather than forcing every expression into ordinary R/C elements.

## Five independently explored routes (scheduled in small batches)

### Route A — start with the TIME PROFILE, not 70 separate formulas
Owns `routes/A_waveform/`.
- Construct (i) fixed initial charge; (ii) constant-current/continuous driven integrator giving a ramp; (iii) discrete replacement/maintenance impulses producing stairs; (iv) periodic counts decomposed into secular linear trend + bounded sawtooth **residual**.
- For synthetic aircon 10 y and piping 20 y, model independent charge-to-threshold/reset timing nodes, common drive when justified, and a separate single cumulative-emissions charge integrator. Compare DC, current pulses, zero-mean AC (negative test), rectified AC, and controlled-source alternatives.
- Distinguish ramp of Q,V from electric power and energy, which obey different equations. For constant I and ideal fixed C, Q and V ramp, E_cap = Q²/(2C) grows quadratically; P_cap = IV ramps if V ramps.
- Develop exact continuous/event-time formulae and show all timing boundary behavior. Do not confuse actual-time G(t) with evaluation-horizon C(T).
- Deliver code + oracle + tests + circuit diagram + failure conditions, not only prose.

### Route B — begin with ALL EQUATION FAMILIES
Owns `routes/B_formula_network/`.
- Independently enumerate distinct arithmetic/logic/time formula families in existing independent research model: masked sum-products, indices/lookup/logic, schedules, knots, gating, renewal, refrigerant state, terminal adjustments, aggregation, and comparison.
- Classify each as (a) passive R/C network possible, (b) active controlled-source circuit, (c) switched/hybrid analog computation, (d) external digital/logic/state machine required, (e) not supported / ill-defined on available data. For each, provide constructive encoding OR a rigorously scoped counterexample/obstacle.
- Propose a minimal **network grammar** (sources, integrators, comparators, reset switches, arithmetic blocks, external state) without presuming every function belongs to a capacitor. Explore whether the circuit system simply renames the existing Sigma graph.
- Map formal circuit operations and complexity against the existing math before claiming improvement. Use the full set of formula families, but start with a small complete end-to-end case.
- Deliver mapping table, interpreter/prototype, exact/approx conditions, unit tests, exceptions.

### Route C — independently start from 70 EVALUATION UNITS
Owns `routes/C_70_units/`.
- Read `WLC_THEORY_RESEARCH_BASE/data/units70.json`, `02_70評価単位の完全台帳.md`, and `06_建物全体の統一方程式.md` thoroughly. All 70 units have roles; only 21 directly contribute to total, the others are support/gates/aggregation/metrics, NOT 70 independent physical carbon sources.
- Produce 70/70 individually traceable coverage rows with original role, inputs, outputs, time behavior, circuit candidate, exactness/status, evidence tag, limitations, required dependencies and reproducible test.
- Test a representative unit from each distinct mathematical role and all 21 direct contributors; extend to full applicable set where possible. Identify non-circuitable behavior explicitly, never invent a physical RC equivalent.
- Explore whether common circuit subassemblies can replace many units without loss of inputs, timing or calculation boundary.
- Deliver machine-readable matrix + scripts + tests, with unresolved/blocked classifications clearly separated from failures.

### Route E — start from RESISTOR JOULE HEATING instead of capacitor charge
Owns `routes/E_resistor_energy/`.
- Independently investigate the user's core insight: constant current through a fixed resistor `P_R=I²R` dissipates energy at a constant rate, so cumulative `E_R(t)=E_R(0)+I²Rt` is linear in time, without requiring the capacitor-based starting analogy.
- For sinusoidal AC, derive `P(t)=I_rms²R[1−cos(2ωt)]` and `E_R(t)=E_R(0)+I_rms²R[t−sin(2ωt)/(2ω)]`. Compare its rising energy integral to capacitor charge accumulation; distinguish instantaneous power, cumulative heat/energy, temperature, electric current and stored electric energy.
- Apply a declared, correctly dimensioned emissions factor to obtain synthetic operational carbon only under calibrated conditions; use actual load and time-varying factor where applicable. Do not force discrete material/repair carbon into literal resistor heat.
- Test DC, AC, multiple resistive sources, finite pulse events, dynamic load/emissions, and whether resistor-plus-energy-meter is smaller or more accurate than capacitor-plus-current-source and existing sum/integrator equations. A resistor dissipates energy but doesn't remember its cumulative value.
- Follow `09_RESISTOR_ENERGY_ROUTE.md`. Produce independent executable tests, explicit counterexamples and benchmark.

### Route D — an INDEPENDENT verifier and reducer
Owns `routes/D_verification/`.
- Build an independent oracle, fixtures and rigorous cross-route test/benchmark harness; do not import the same algorithm from a proposed circuit to calculate reference values.
- Falsify incorrect modeling of sawtooth/ramp, overlapping replacements, thresholds, states/efficiency, double counting, terminal Z(T), floating-point boundary slivers, AC charge behavior **and resistor DC/AC energy claims (Route E)**.
- Compare different representations by equality/absolute+relative error/domain, operation count, memory, runtime and internal state dimensionality; report if result only redisplays existing equations.
- Try circuit reduction/state elimination only while preserving the requested observables and future event schedules; counterexamples are valuable.

## Mathematical verification service (Route F)
- The `wlc-math7-orchestrator` is a **shared read-only verification support route** alongside A/B/C/D/E, not a claim that all seven engines can evaluate arbitrary WLC equations today.
- Consult `11_MATH7_INTEGRATION.md`: Math7 code lives in `main` of this repo; the experiment branch does not contain it. Use a separate read-only checkout/worktree. Existing `portable-full` is restricted algebraic Math IR, while `lca-operators` runs Python-only.
- Collect verified math oracles and experiment results from routes A/B/C/E, test using SymPy/NumPy/SciPy/mpmath/DuckDB, and prepare appropriate safe SageMath/MATLAB GitHub Actions runs. If external API is blocked, give web UI steps and report tests unrun; do not broaden permissions or publish nonpublic inputs.
- Store F files only in `routes/F_math7_bridge/`. D reviews evidence independently.

## Model/effort ownership
See `10_MODEL_ROUTING.md`. Start with strategic architect Fable 5.2 High, delegate A/B/C/E implementation to Opus 5.5 Medium, D independent verifier and final evidence integrator to Opus 5.5 High, then Fable 5.2 High replanning. The orchestration is via explicit subagents and actual tasks; no GitHub file automatically starts sessions. Keep startup model selection and individual delegated execution distinct.

## Coordination
1. Coordinator records the baseline SHA, then follows the small-batch research gates in `12_FINAL_OPERATING_PLAN.md`. Do not start all five heavy agents just because parallelism is possible; schedule A/E pilots and B/C inventories first, with D independent tests as results appear. If separate execution contexts and quotas permit, run a bounded batch concurrently, otherwise interleave without blocking on routine approvals.
2. Each route writes only inside its own `routes/<route>/` directory. This allows same-repository subagents with disjoint writes; never have multiple agents commit or edit shared top-level files concurrently.
3. If using distinct independent cloud sessions, use separate route branches seeded from this project branch. Do not assume a new worktree is based on the correct ref: verify `git rev-parse HEAD`, ensure instructions and files exist, and switch to the correct route branch before running.
4. A, B and E pursue **distinct proof/implementation routes**. C must independently cover the 70 units, not just copy B's conclusion. D challenges all routes and preserves a separate oracle. Agents should ask the coordinator only when external authorization/irreversible action is required.
5. Stop conditions are evidence-based, not 'keep trying until it passes'. A counterexample or mathematically impossible mapping is a valid result. Avoid wasting effort on trivial relabeling.
6. **Integration gate:** After A has reproducible continuous/discrete pilot and B has a verified constructive mapping for supported arithmetic/time classes (or precisely scoped exceptions), compare their observable outputs and units; integrate only validated pieces. C and E continue in parallel; C fills coverage gaps. D independently checks any merged candidate.
7. Avoid deadlock when B cannot represent all equations: a hybrid model with explicit non-R/C components or a proof of non-representability can be a correct endpoint. Do not label this as full conversion.
8. Preserve the original WLC source; do not modify application or J-CAT original code. New evidence and experiments only here. Do not commit sensitive/restricted inputs.
9. At the end provide: comparative matrix A/B/C/E, verified integrated prototype (if justified), failures/counterexamples, state/complexity benchmark, next steps, exact Git branch/commit paths. State whether parallel sessions **actually ran**, rather than merely being configured.

## How autonomous is this?
- A file in GitHub is an instruction **when a Claude Code session reads it**, not a running background service. Setup does not initiate execution.
- Claude Code supports project subagents defined in `.claude/agents/`; invoke them from the coordinator. Different cloud sessions can be started to work on separate branches and later reviewed/merged; all consume the account's Claude usage allowance.
- Keep original `03_EXECUTION_PLAN.md` as the technical reference; the parallel plan changes **ordering and delegation**, not correctness or permissions.
