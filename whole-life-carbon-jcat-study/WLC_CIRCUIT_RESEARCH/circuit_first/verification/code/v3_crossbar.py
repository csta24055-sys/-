"""V3: audit of the reduced amplitude crossbar (v2) of snapshot 96df403.

For benchmark S and evaluation E1 (and S in v1 mode for reference):
  * build the crossbar exactly as simulate_building does (build_amplitudes, operation,
    refrigerant_amp, finalize); solve it with the verifier's own solver (v2_crossbar.solve);
  * KCL residual and unknowns after propagation;
  * every exported tap voltage vs the stage-B (v1) tap values verified in V2 (dumped netlists of
    the B2 snapshot) and vs the v1 path of this snapshot;
  * every independent source value must equal +-(one primitive input) x V0 or +-V0 or
    +-(primitive x a building-independent constant such as 1/1000): no pre-combined product;
  * op-amps per cell, inverters (an op-amp stage whose Rin = Rf and input is another op-amp output
    or source), fan-out of every source / op-amp output (consumers other than own feedback),
    duplicate voltages among op-amp outputs (would indicate a structural duplicate);
  * passive products: junction input conductances driven directly by a source node.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from fractions import Fraction as Fr

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import SNAP, save  # noqa: E402
from vsim import num  # noqa: E402
import v2_crossbar  # noqa: E402

STUDY = "/home/user/-/whole-life-carbon-jcat-study"
sys.path.insert(0, os.path.join(STUDY, "10_TRANSFORM_STUDY", "research_code"))
from tstudy import baseline, scenarios  # noqa: E402

FROZEN = baseline.assert_frozen()
sys.path.insert(0, SNAP)
import adapter_building as ab  # noqa: E402
from adapter import Units  # noqa: E402

B2_RESULTS = ("/tmp/claude-0/-home-user--/d16c9837-8c7c-5bcc-8b70-730caf3a5491/scratchpad/cf_snapshot_B2/"
              "whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/circuit_first/results")


def build_xbar(scn, crossbar):
    L = ab.LayeredLedger()
    L.layer = "amp"
    A, amp = ab.build_amplitudes(scn, L, Units(), ab.ALL_BLOCKS, (), crossbar)
    iota = set(scn.boundary.included_lifecycle_stages)
    ab.operation(None, A, scn, L, iota, None)
    ab.refrigerant_amp(A, scn, L)
    A.finalize()
    return A, L


def primitives(o, acc):
    import dataclasses
    if isinstance(o, bool):
        return
    if isinstance(o, (int, float)):
        acc.add(abs(Fr(o)))
        return
    if dataclasses.is_dataclass(o) and not isinstance(o, type):
        for f in dataclasses.fields(o):
            primitives(getattr(o, f.name), acc)
    elif isinstance(o, (list, tuple)):
        for x in o:
            primitives(x, acc)
    elif isinstance(o, dict):
        for x in o.values():
            primitives(x, acc)


def audit(key, scn):
    A, L = build_xbar(scn, "v2")
    js = A.nl.to_json()
    v, info = v2_crossbar.solve(js)
    taps = {name: v[node] for name, (node, sg) in A.exports.items()}
    # stage-B (v1) taps verified in V2
    b2 = None
    p = os.path.join(B2_RESULTS, f"stageB_netlists_{key}.json")
    if os.path.exists(p):
        d = json.load(open(p))
        core = {e["name"]: e for e in d["core"]}
        b2 = {name: num(core[t["core_source"]]["V"]) for name, t in d["taps"].items()}
    A1, _ = build_xbar(scn, "v1")
    v1v, _ = v2_crossbar.solve(A1.nl.to_json())
    taps_v1 = {name: v1v[node] for name, (node, sg) in A1.exports.items()}
    cmp_b2 = None
    if b2 is not None:
        common = set(b2) & set(taps)
        cmp_b2 = {"common": len(common), "only_v2": sorted(set(taps) - set(b2))[:5], "only_b2": sorted(set(b2) - set(taps))[:5],
                  "mismatch": [n for n in common if b2[n] != taps[n]][:5]}
    common1 = set(taps_v1) & set(taps)
    cmp_v1 = {"common": len(common1), "mismatch": [n for n in common1 if taps_v1[n] != taps[n]][:5],
              "only_v2": len(set(taps) - set(taps_v1)), "only_v1": len(set(taps_v1) - set(taps))}
    # sources
    prim = set()
    primitives(scn, prim)
    V0 = Fr(1)
    srcs = [e for e in js if e["kind"] == "V"]
    bad = []
    kinds = Counter()
    for e in srcs:
        val = abs(num(e["V"]))
        if val == V0:
            kinds["+-V0"] += 1
        elif val in prim:
            kinds["primitive x V0"] += 1
        elif val * 1000 in prim:
            kinds["primitive/1000 x V0"] += 1
        else:
            bad.append((e["name"], float(val)))
    # structure
    oas = [e for e in js if e["kind"] == "OA"]
    outs = {e["out"] for e in oas}
    srcnodes = {e["a"] for e in srcs}
    fb = {}
    rin = defaultdict(list)
    for e in js:
        if e["kind"] == "R":
            for oa in ():
                pass
    by_inn = {e["inn"]: e for e in oas}
    consumers = Counter()
    inverters = 0
    for e in js:
        if e["kind"] != "R":
            continue
        a, b = e["a"], e["b"]
        # a resistor between an op-amp's inn and its out is feedback; otherwise the driven end feeds a junction
        for drv, other in ((a, b), (b, a)):
            if (drv in outs or drv in srcnodes) and other in by_inn and by_inn[other]["out"] != drv:
                consumers[drv] += 1
    for oa in oas:
        x, o = oa["inn"], oa["out"]
        rs = [e for e in js if e["kind"] == "R" and x in (e["a"], e["b"])]
        f = [e for e in rs if o in (e["a"], e["b"])]
        ins = [e for e in rs if o not in (e["a"], e["b"])]
        if len(f) == 1 and len(ins) == 1 and num(f[0]["G"]) == num(ins[0]["G"]):
            inverters += 1
    fan_out = Counter(consumers[n] for n in outs | srcnodes)
    vals = Counter(v[o] for o in outs)
    dup = sum(c - 1 for c in vals.values() if c > 1)
    passive = 0
    for e in js:
        if e["kind"] == "R":
            for drv, other in ((e["a"], e["b"]), (e["b"], e["a"])):
                if drv in srcnodes and other in by_inn:
                    passive += 1
    cells = Counter(e["tags"].get("cell") for e in oas)
    rows = len(scn.materials) + len(scn.equipment)
    return {"solve": info, "taps": len(taps), "vs_B2_stageB_taps": cmp_b2, "vs_v1_path_this_snapshot": cmp_v1,
            "sources": len(srcs), "source_kinds": dict(kinds), "sources_not_single_primitive": bad[:10], "n_bad_sources": len(bad),
            "opamps": len(oas), "opamps_by_cell": dict(cells.most_common()), "pure_inverters": inverters,
            "elements": len(js), "rows_mat_eq": rows, "opamps_per_row": round(len(oas) / rows, 2),
            "fanout_hist_sources_and_opamp_outputs": dict(sorted(fan_out.items())),
            "nodes_with_fanout_ge2": sum(c for k, c in fan_out.items() if k >= 2),
            "duplicate_voltage_values_among_opamp_outputs": dup,
            "passive_branches_from_sources_into_junctions": passive,
            "lazy_stats": getattr(A, "stats", None), "ledger_amp": L.by_layer.get("amp"), "grey_items": len(L.grey_items)}


def main():
    bm, ev = scenarios.benchmark(), scenarios.evaluation_set(10)
    out = {"frozen": FROZEN}
    for key, scn in (("S", bm[0]), ("E1", ev[1]), ("E5", ev[5])):
        out[key] = audit(key, scn)
        print(key, json.dumps(out[key], default=str)[:1800], flush=True)
    save("v3_crossbar.json", out)


if __name__ == "__main__":
    main()
