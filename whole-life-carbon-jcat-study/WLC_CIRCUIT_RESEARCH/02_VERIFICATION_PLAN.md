# 02 Verification plan — falsification first

## Independent tests
1. **Continuous only**: `G0+r*t` vs single integrator at t=0, 0.5, 10, 20, 60.
2. **Single event**: exact step/pulse-charge area, no missing/double event, before/at/after threshold.
3. **Dual cycles**: aircon 10y and pipe 20y; inspect 10,20,30,40,60; overlapping triggers at 20 and 40; compare `t-ε`, `t`, `t+ε` with declared inclusion.
4. **Renovation precedence**: at 20y replace pipe + aircon during renovation; no double count if renovation ledger encompasses those items; separate ledger if truly extra.
5. **Changing operation**: exchange aircon changes electricity rate; use piecewise integral; independently calculate the reference after replacement.
6. **Different current shapes**: constant, linear changing, seasonal, time-varying emission factors, finite pulse widths; preserve integrated charge.
7. **Initial conditions and calibration**: verify `kgCO2e <-> C`, `year <-> simulation seconds`, stored energy vs charge distinction.
8. **Limits/counterexamples**: raw AC without rectification, charge leakage, series-capacitor mismatch, RC exponential instead of linear rate, random failures and incomplete repair; demonstrate exactly why simple correspondences fail.
9. **Original model**: only after passing synthetic pilot, map each of the **21 direct contribution** units and their 49 supporting/logic units. Cite existing `units70.json` and role entries. Preserve terminal term `Z(T)`, cold-refrigerant remainder, exclusion sliver and floating-point sensitivity.
10. **Independent verification**: use a separately coded direct mathematical oracle, avoid calling the same helper on both sides; exact rational samples where possible, otherwise record absolute/relative errors, tolerance, distribution, domain, and original source commit.
11. **Complexity**: count operations, runtime, memory, internal state dimension for direct sums vs circuit model; compare different numbers of devices and event counts. A novel diagram alone is not a computational improvement.
12. **Proof obligations**: equivalence for ideal timing circuit to `N_i(t)`, correct shared-event counting, exact accumulation across continuous and atomic inputs, and limits of state reduction. New proofs are drafts until independent review.

## Acceptance gate
For deterministic synthetic pilot, match the independent oracle on all non-boundary samples to declared tolerance, test all event boundaries under explicitly chosen conventions, and explain any mismatch. Do not silently reuse an original proof outside its source domain. Record failures and counterexamples; if an equivalence is only conditional/approximate, label it clearly.

## Output artifacts to produce during actual research
- `research_log/YYYY-MM-DD_*.md`: goal, preregistered claim, baseline revision, math, counterexample, conclusion
- `code/`: runnable independent model and oracle (standard-library Python first)
- `tests/`: synthetic reproducible unit/boundary/overlap tests
- `results/`: JSON/CSV, timing tables, state counts, error metrics
- `figures/`: labeled actual-time and horizon-time plots
- `report/`: results and limitations, concise 2-page explanation plus technical appendix

Keep all new artifacts inside `WLC_CIRCUIT_RESEARCH`, never modify upstream reference research code.
