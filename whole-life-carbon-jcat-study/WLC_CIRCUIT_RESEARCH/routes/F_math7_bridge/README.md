# Route F — Math7 integration bridge

This research route connects existing Math7 sources from **`csta24055-sys/-` `main`** with the WLC circuit research on a **different branch**, without overwriting either.

Read `../../11_MATH7_INTEGRATION.md` before executing.

Status: **configured, NOT executed** as part of setting up this route.

The Math7 7-engine workflow on `main` currently accepts restricted algebraic Math IR JSON; the more relevant LCA integral, time-function, masked sum-product and node-spectrum runner is Python-only. The goal here is to verify WLC circuit math with the available five Python engines immediately, and only then design a safe adapter to get comparable WLC computations through SageMath and MATLAB using GitHub Actions. Keep independent mathematical oracles, source commit pinning and exact status records.

Deliver `STATUS.md`, runnable code, synthetic fixtures, tests, results, engine/version matrix, and reusable instructions, stored only in this route.
