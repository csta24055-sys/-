# Agent instructions for WLC equivalent-circuit research

Read `CLAUDE.md` and the specifications under `whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/` first.

Scope: independent mathematical modeling of building whole-life carbon as electrical equivalent circuits (current sources, integrating capacitors, clocks, thresholds, switches and state variables). Keep the original WLC theory base and WLC Studio unchanged.

Use synthetic data only. Treat electronic equivalence as a formal modeling choice, not physical identity. Compare against original reference equations and preserve all uncertainties, especially timing, terminal terms, equipment overlap, refrigerant and numerical boundary behavior. Log verified evidence and counterexamples. Work only on a new research branch.

Also consult `whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/05_SOURCE_MAP.md` and `csta24055-sys/lastdance4-tree-` (`main`, relevant A3/A6/A9 classification branches) as read-only **navigation** to relevant work in `csta24055-sys/lastdance`. For equations rely on the original WLC research base and independent verification, not the classification index.


## Parallel WLC research
Read `whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/06_PARALLEL_ORCHESTRATION.md`, `07_SHARED_CONTRACT.md`, `08_AUTONOMOUS_START.md`. Five project subagents under `.claude/agents/wlc-*.md` address A capacitor/waveform, B formulas, C 70-unit coverage, D independent validation, and E resistor/Joule-energy. Their output directories are disjoint. Same-checkout agents must not commit/checkout concurrently. In separate cloud sessions check out the correct route branch seeded from this project branch. Original theory and apps stay unchanged. Do not assert these files automatically start sessions.
