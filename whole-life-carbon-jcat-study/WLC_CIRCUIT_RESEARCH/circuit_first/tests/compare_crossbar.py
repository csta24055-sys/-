"""Stage C: amplitude-crossbar census before (v1: one stage per data factor per row, explicit
inverters) and after (v2: lazy minimal realisation), with the L1 lower bound.

L1 counting rule (stated in DESIGN_DEVIATIONS D21): with the factor order fixed (factor rail
first, then conversion, then row factors; DESIGN rows may use the shared q/(1-w) root) and
sharing by structural identity, every product of >= 2 data factors that must exist AS A VOLTAGE
(operand of a further product, or a junction input whose last factor cannot be a conductance)
needs one active output (L1), and every sum whose voltage is sampled or multiplied needs one
summing junction. LB = number of such distinct expressions (polarity ignored). The realisation
reaches LB + (expressions needed in both polarities). Single-data voltages are sources (0 op-amps).
"""
import json
import os
import sys
import time

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import compare_refcalc as cr  # noqa: E402  (asserts the frozen baseline)
import adapter_building as ab  # noqa: E402
from adapter import Units  # noqa: E402


def census(scn, crossbar):
    L = ab.LayeredLedger()
    t = time.time()
    A, amp = ab.build_amplitudes(scn, L, Units(), ab.ALL_BLOCKS, (), crossbar)
    ab.operation(None, A, scn, L, set(scn.boundary.included_lifecycle_stages), None)
    ab.refrigerant_amp(A, scn, L)
    A.finalize()
    from engine.dc import kcl_residual, solve_dc
    volts, cur, info = solve_dc(A.nl)
    rows = len(scn.materials) + len(scn.equipment)
    inv = sum(1 for e in A.nl.elements if e.kind == "OA" and e.tags.get("cell") == "inverter")
    out = {"elements": len(A.nl.elements), "opamps": A.opamps, "opamps_per_material_equipment_row": A.opamps / rows,
           "pure_inverters": inv, "rows_materials_equipment": rows, "dense_block": info["dense_block"],
           "kcl_residual": str(kcl_residual(A.nl, volts, cur)), "seconds": round(time.time() - t, 2),
           "taps": len(A.exports)}
    if crossbar == "v2":
        st = dict(A.stats)
        out["realisation"] = st
        out["L1_lower_bound"] = st["stages"] + st["junctions"] - st["polarity_duplicates"]
        out["gap_polarity"] = st["polarity_duplicates"]
    return out, {n: volts[node] for n, (node, sg) in A.exports.items()}


def main():
    rep = {"rule": __doc__}
    for key, scn in cr.scenario_set(["S", "M", "E0", "E1", "E2"]):
        b, tb = census(scn, "v1")
        a, ta = census(scn, "v2")
        same = {n for n in ta if n in tb}
        eq_taps = all(ta[n] == tb[n] for n in same)
        rep[key] = {"id": scn.meta.scenario_id, "before_v1": b, "after_v2": a,
                    "common_taps_equal": eq_taps, "common_taps": len(same)}
        print(key, "v1", b["elements"], b["opamps"], "v2", a["elements"], a["opamps"], "LB", a["L1_lower_bound"],
              "gap", a["gap_polarity"], "taps equal", eq_taps, flush=True)
    with open(os.path.join(cr.ROOT, "results", "stageC_crossbar.json"), "w") as f:
        json.dump(rep, f, indent=1, default=str)


if __name__ == "__main__":
    main()
