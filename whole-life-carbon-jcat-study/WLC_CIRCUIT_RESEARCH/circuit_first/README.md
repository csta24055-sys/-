# Circuit-first research (corrected primary objective)

**Current status: not implemented / not tested.** This directory is reserved for a fresh, genuinely circuit-first approach, *not* a continuation of the old Ψ per-unit netlist.

Read `../13_CIRCUIT_FIRST_OBJECTIVE.md` and `../12_FINAL_OPERATING_PLAN.md`.

Start from actual R/C/L, KCL/KVL and energy/current laws, then design a single reusable topology or a minimal family. Model the WLC **whole-building behavior** through shared parameters and inputs. The 70 evaluation units are the reference specification, constraints and acceptance oracle; do not generate one current source per DIRECT unit or merely import existing WLC functions as each source.

Deliver `topology.md`, `model.py`, `adapter.md`, `tests/`, `results/`, `VERDICT.md`. Distinguish standard physical circuit vs controlled hybrid vs arithmetic re-labeling. No new test has run under this corrected objective yet.
