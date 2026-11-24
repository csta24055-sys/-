"""V3: parameter-only reuse status. Builds crossbar (v2) and core netlists for several buildings and
compares netlist-derived signatures (the builder's count-free model.netlist_signature and the
verifier's WL count-free colour set), lists the differing element patterns, and the cell
multiplicities that vary with building size."""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import SNAP, save  # noqa: E402

STUDY = "/home/user/-/whole-life-carbon-jcat-study"
sys.path.insert(0, os.path.join(STUDY, "10_TRANSFORM_STUDY", "research_code"))
from tstudy import baseline, scenarios  # noqa: E402

FROZEN = baseline.assert_frozen()
sys.path.insert(0, SNAP)
import adapter_building as ab  # noqa: E402
from adapter import Units  # noqa: E402
from engine.dc import solve_dc  # noqa: E402
from model import netlist_signature  # noqa: E402
import audit_static  # noqa: E402,F401  (verifier WL signature; imports snapshot adapter/model too)


def build(scn):
    L = ab.LayeredLedger(); L.layer = "amp"
    A, amp = ab.build_amplitudes(scn, L, Units(), ab.ALL_BLOCKS, (), "v2")
    iota = set(scn.boundary.included_lifecycle_stages)
    pending, elec, info = ab.operation(None, A, scn, L, iota, None)
    ref = ab.refrigerant_amp(A, scn, L)
    A.finalize()
    volts, cur, _ = solve_dc(A.nl)
    tapv = {name: volts[node] for name, (node, sg) in A.exports.items()}
    B, groups, kinds = ab.build_core(scn, L, Units(), "original", ab.ALL_BLOCKS, amp, A, tapv, (pending, elec), ref, ())
    return A, B, kinds


def describe(p):
    return str(p)[:220]


def main():
    bm, ev = scenarios.benchmark(), scenarios.evaluation_set(10)
    pool = {"S": bm[0], "E0": ev[0], "E1": ev[1], "E2": ev[2], "E4": ev[4], "E5": ev[5], "E7": ev[7], "E8": ev[8]}
    sig_core, sig_x, wl_core, mult, kinds_all = {}, {}, {}, {}, {}
    for k, scn in pool.items():
        A, B, kinds = build(scn)
        sig_core[k], sig_x[k] = netlist_signature(B.nl), netlist_signature(A.nl)
        wl_core[k] = audit_static.wl_signature(B.nl.to_json())[1]
        mult[k] = {"crossbar_elements": len(A.nl.elements), "core_elements": len(B.nl.elements),
                   "core_kind_counts": dict(Counter(e.kind for e in B.nl.elements))}
        kinds_all[k] = {kk: vv for kk, vv in kinds.items()}
        print(k, len(sig_core[k]), len(sig_x[k]), kinds_all[k], flush=True)
    union = frozenset().union(*sig_core.values())
    inter = frozenset.intersection(*sig_core.values())
    var = sorted(union - inter, key=str)
    out = {"frozen": FROZEN,
           "crossbar_signature_identical": len({v for v in sig_x.values()}) == 1,
           "core_signature_identical": len({v for v in sig_core.values()}) == 1,
           "core_patterns_common": len(inter), "core_patterns_varying": len(var),
           "varying_patterns": {describe(p): sorted(k for k, s in sig_core.items() if p in s) for p in var},
           "wl_count_free_core_identical": len(set(wl_core.values())) == 1,
           "wl_core": wl_core, "multiplicities": mult, "input_kinds": kinds_all}
    save("v3_template.json", out)
    print(json.dumps({k: v for k, v in out.items() if k not in ("multiplicities",)}, default=str, indent=1)[:4000])


if __name__ == "__main__":
    main()
