# WLC research repository instructions

For the WLC equivalent-circuit project, follow `CLAUDE.md` and `whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/00_START_HERE.md` through `03_EXECUTION_PLAN.md`. Preserve `WLC_THEORY_RESEARCH_BASE`, original research chapters, and WLC Studio; never invent proofs, real-world carbon accuracy, or permissions for J-CAT original material. Implement only independent synthetic models and verify equivalence, event timing and overlap, model order and actual computation savings.

For parallel task delegation and distinct research approaches, read `whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/06_PARALLEL_ORCHESTRATION.md`, `07_SHARED_CONTRACT.md`, and `08_AUTONOMOUS_START.md`. Keep A/B/C/D in independent branches or route-scoped directories; do not silently merge unverified claims.

The user explicitly adds a fifth **resistor Joule-heating/accumulated-energy** route E (`09_RESISTOR_ENERGY_ROUTE.md`): compare E_R(t)=∫i(t)^2 R(t)dt (linear for constant I and R) to capacitor-charge accumulation. Resistor energy is dissipated, not stored; do not conflate instantaneous power, cumulative heat, resistor temperature, and WLC. Route D independently checks E.
