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

Read the base's `05_時間スペクトルの理論.md`, `06_建物全体の統一方程式.md`, `07_動的LCAと工程時間.md`, `09_未解決問題と限界.md`, and `15_劣化・寿命・交換モデル研究開始資料.md` before formal conclusions.

## Additional read-only reference repository
- `csta24055-sys/lastdance4-tree-` (`main`) is the Yes/No classification/index of 2,100 development roles. It is **not** the original WLC source or a mathematical proof. Search relevant A3 (math), A6 (verification), A9 (knowledge), optionally A2 (classification), then follow exact role/source references into `csta24055-sys/lastdance` only if needed.
- Use `WLC_CIRCUIT_RESEARCH/05_SOURCE_MAP.md` to keep source repo, branch, file path, role/claim IDs and verification status separately documented.
- Prioritize the WLC theory base for formulas and validity, not ability-tree descriptions.

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
- Start with the two-equipment pilot, not an unsupported claim of mapping all 70 units.

## Delivery definition
A task is not finished merely because diagrams or text exist. Deliver derivation, independent reference computation, tests including event boundaries and overlapping replacements, explicit counterexamples, limitations, operation-count/memory/time comparison, and a short understandable summary. If a phase is incomplete, state precisely what is missing.
