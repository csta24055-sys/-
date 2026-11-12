"""Writes one worked example: every public output of the 70 units for the fictional benchmark scenario S at
T = 62.5 years, from the unified system and from the reference calculation, side by side.

Run from ``research_code``:  PYTHONDONTWRITEBYTECODE=1 python3 -B tools_example.py
Writes ``11_UNIFIED_SYSTEM/results/example_benchmark_S_T62.5.json`` (numbers are written with full precision).
A third party can re-run this and compare the file byte by byte. Fictional data; not a statement about any other tool.
"""
import json
import os
import sys

sys.dont_write_bytecode = True

from checks.check_msp_pre_a import public
from tstudy import baseline, scenarios, unified

OUT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "11_UNIFIED_SYSTEM", "results",
                                    "example_benchmark_S_T62.5.json"))


def main():
    baseline.assert_frozen(); baseline.load()
    from synth import population
    scn = scenarios.benchmark()[0]
    T = 62.5
    system = unified.System(scn, baselines=population.BASELINES)
    got = system.at(T)
    ref = baseline.run_reference(scenarios.with_period(scn, T))
    doc = {"scenario": scn.meta.scenario_id, "seed": scn.meta.seed, "generator": "synth.population.standard_benchmark()[0]", "study_period": T,
           "rows": {"materials": len(scn.materials), "equipment": len(scn.equipment), "refrigerants": len(scn.refrigerants)},
           "knot_values_at_T": system.last["K"], "b1_04_three_forms": system.last["b14"],
           "unified": {uid: got[uid] for uid in sorted(got)}, "reference": {uid: public(ref[uid]) for uid in sorted(ref)}}
    with open(OUT, "w") as f:
        json.dump(doc, f, indent=None, separators=(",", ":"), sort_keys=True)
    print("written", OUT, os.path.getsize(OUT), "bytes; units", len(doc["unified"]))


if __name__ == "__main__":
    main()
