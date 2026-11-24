"""Closing pass measurements (oracle imported here only, after assert_frozen):
1. wall time of the frozen refcalc versus the circuit (S3e, all blocks, original convention) on
   the SAME usable-T list per building (refcalc: one run per T, best of 3 repetitions);
2. value-duplicate op-amp outputs in crossbar v2 (equal DC voltage at distinct op-amp outputs),
   i.e. what value-keyed sharing could still remove; the v2 sharing key is structural (factor id,
   conversion value, object identity of row quantities, one junction per sum call).
Writes results/closing_timing_and_duplicates.json."""
import json
import os
import sys
import time
from collections import Counter

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import compare_refcalc as cr  # noqa: E402  (asserts the frozen baseline)
import adapter_building as ab  # noqa: E402
from adapter import Units  # noqa: E402
from engine.dc import solve_dc  # noqa: E402
from engine.netlist import OpAmp  # noqa: E402
from model_building import simulate_building  # noqa: E402
from tstudy import baseline, scenarios  # noqa: E402


def timing(key, scn):
    Ts, _ = cr.usable_T(scn)
    best = None
    for _ in range(3):
        t0 = time.perf_counter()
        for T in Ts:
            baseline.run_reference(scenarios.with_period(scn, T))
        dt = time.perf_counter() - t0
        best = dt if best is None else min(best, dt)
    t0 = time.perf_counter()
    simulate_building(scn, Ts, "original")
    dc = time.perf_counter() - t0
    return {"T_list": Ts, "n_T": len(Ts), "refcalc_seconds_best_of_3": best, "circuit_seconds": dc}


def duplicates(scn):
    L = ab.LayeredLedger()
    A, _ = ab.build_amplitudes(scn, L, Units(), ab.ALL_BLOCKS, (), "v2")
    ab.operation(None, A, scn, L, set(scn.boundary.included_lifecycle_stages), None)
    ab.refrigerant_amp(A, scn, L)
    A.finalize()
    volts, _, _ = solve_dc(A.nl)
    outs = [(e.name, e.tags.get("cell"), volts[e.out]) for e in A.nl.elements if isinstance(e, OpAmp)]
    cnt = Counter(v for _, _, v in outs)
    dup = [(n, c, v) for n, c, v in outs if cnt[v] > 1]
    extra = sum(c - 1 for c in cnt.values() if c > 1)
    by_cell = Counter(c for _, c, v in dup)
    return {"opamps": len(outs), "distinct_output_values": len(cnt),
            "removable_by_value_sharing": extra, "outputs_in_duplicate_classes_by_cell": dict(by_cell)}


def main():
    rep = {"doc": __doc__, "frozen": cr.FROZEN, "timing": {}, "value_duplicates": {}}
    for key, scn in cr.scenario_set(["S", "E1"]):
        rep["timing"][key] = timing(key, scn)
        rep["value_duplicates"][key] = duplicates(scn)
        print(key, rep["timing"][key], rep["value_duplicates"][key], flush=True)
    with open(os.path.join(cr.ROOT, "results", "closing_timing_and_duplicates.json"), "w") as f:
        json.dump(rep, f, indent=1, default=str)


if __name__ == "__main__":
    main()
