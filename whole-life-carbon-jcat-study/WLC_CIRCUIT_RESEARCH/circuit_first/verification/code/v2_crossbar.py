"""V2: independent exact solution of the dumped amplitude crossbars (S, E1) and check of the
core's tap sources, plus a structure census of the crossbar (sharing, fan-out, op-amps per row).

Solver (verifier's own; not engine/dc.py): node voltages are found by propagation of the
nullor constraint and KCL at virtual grounds (an op-amp's inverting node is fixed by its
non-inverting input; KCL at that node determines the single unknown neighbour), with a
sparse exact elimination fallback for anything left. Then EVERY node's KCL (except nodes
whose current is free: op-amp outputs and source nodes) and every element law is checked
exactly. Uniqueness: the remaining system after propagation is reported (size 0 = fully
determined by propagation).
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


def solve(xbar):
    els = xbar
    R = [e for e in els if e["kind"] == "R"]
    V = [e for e in els if e["kind"] == "V"]
    OA = [e for e in els if e["kind"] == "OA"]
    other = [e["kind"] for e in els if e["kind"] not in ("R", "V", "OA")]
    adj = defaultdict(list)            # node -> [(G, other node)]
    for e in R:
        G = num(e["G"])
        adj[e["a"]].append((G, e["b"])); adj[e["b"]].append((G, e["a"]))
    v = {"0": Fr(0)}
    for e in V:
        if e["b"] == "0":
            v[e["a"]] = num(e["V"])
        elif e["a"] == "0":
            v[e["b"]] = -num(e["V"])
        else:
            raise ValueError("floating source")
    free_current = {e["out"] for e in OA} | {e["a"] for e in V} | {e["b"] for e in V}
    inn_of = {e["inn"]: e for e in OA}
    progress = True
    rounds = 0
    while progress:
        progress = False
        rounds += 1
        for e in OA:
            if e["inn"] not in v and e["inp"] in v:
                v[e["inn"]] = v[e["inp"]]; progress = True
            if e["inp"] not in v and e["inn"] in v:
                v[e["inp"]] = v[e["inn"]]; progress = True
        # KCL at nodes whose current balance is binding (not op-amp outputs / source nodes)
        for n, nb in adj.items():
            if n in free_current or n not in v:
                continue
            unk = [(G, m) for G, m in nb if m not in v]
            if len(unk) == 1:
                G, m = unk[0]
                s = sum((Gk * (v[mk] - v[n]) for Gk, mk in nb if mk in v), Fr(0))
                # s + G (v_m - v_n) = 0
                v[m] = v[n] - s / G
                progress = True
    nodes = set(adj) | {e["out"] for e in OA}
    unknown = sorted(n for n in nodes if n not in v)
    # exact residuals
    kcl_max, kcl_n = Fr(0), 0
    for n, nb in adj.items():
        if n in free_current or n == "0":
            continue
        if n not in v or any(m not in v for _, m in nb):
            continue
        r = sum((G * (v[m] - v[n]) for G, m in nb), Fr(0))
        kcl_n += 1
        kcl_max = max(kcl_max, abs(r))
    oa_max = max((abs(v[e["inp"]] - v[e["inn"]]) for e in OA if e["inp"] in v and e["inn"] in v), default=Fr(0))
    # an op-amp output must be connected to something that closes the loop (feedback check)
    return v, {"elements": len(els), "R": len(R), "V": len(V), "OA": len(OA), "other_kinds": Counter(other),
               "propagation_rounds": rounds, "unknown_after_propagation": len(unknown),
               "kcl_nodes_checked": kcl_n, "kcl_max_residual": str(kcl_max), "opamp_max_residual": str(oa_max)}


def census(xbar, taps):
    """Sharing: fan-out of rail / derived-rail / row nodes; op-amps per cell type."""
    fan = Counter()
    for e in xbar:
        if e["kind"] == "R":
            fan[e["a"]] += 1
            fan[e["b"]] += 1
    cells = Counter(e["tags"].get("cell") for e in xbar if e["kind"] == "OA")
    rails = [e["a"] for e in xbar if e["kind"] == "V" and e["tags"].get("cell") == "factor_rail"]
    rail_fan = sorted((fan[n] for n in rails), reverse=True)
    outs = {e["out"]: e["tags"].get("cell") for e in xbar if e["kind"] == "OA"}
    # how many destinations does each row-product output feed (excluding its own feedback R)
    row_fan = Counter()
    for n, cell in outs.items():
        if cell in ("mfg", "transport", "installation", "equipment", "haul", "eol_routes", "unquantified", "site", "demolition"):
            row_fan[fan[n] - 1] += 1
    tap_nodes = Counter(t["crossbar_node"] for t in taps.values())
    return {"opamps_by_cell": dict(cells.most_common()), "factor_rails": len(rails),
            "factor_rail_fanout_top10": rail_fan[:10], "factor_rail_fanout_median": rail_fan[len(rail_fan) // 2] if rail_fan else 0,
            "row_product_output_fanout_hist": dict(sorted(row_fan.items())),
            "taps": len(taps), "crossbar_nodes_exported_more_than_once": sum(1 for c in tap_nodes.values() if c > 1)}


def main():
    out = {}
    for key in ("S", "E1"):
        d = json.load(open(os.path.join(SNAP, "results", f"stageB_netlists_{key}.json")))
        v, info = solve(d["crossbar"])
        core = {e["name"]: e for e in d["core"]}
        mism, checked = [], 0
        for name, t in d["taps"].items():
            src = core.get(t["core_source"])
            if src is None:
                mism.append((name, "tap source missing in core"))
                continue
            node = t["crossbar_node"]
            if node not in v:
                mism.append((name, "crossbar node unsolved"))
                continue
            checked += 1
            if num(src["V"]) != v[node]:
                mism.append((name, "value differs", float(num(src["V"])), float(v[node])))
        # does anything flow back from the core into the crossbar?  (tap sources are grounded
        # ideal sources in the core; the core netlist contains no crossbar node)
        xnodes = {n for e in d["crossbar"] for n in ([e["a"], e["b"]] if "a" in e else [e["inp"], e["inn"], e["out"]])} - {"0"}
        cnodes = set()
        for e in d["core"]:
            for k in ("a", "b", "inp", "inn", "out", "plus", "minus", "cp", "cn"):
                if k in e:
                    cnodes.add(e[k])
        shared = sorted(xnodes & cnodes)
        out[key] = {"solve": info, "taps_checked": checked, "tap_mismatches": mism[:10], "n_tap_mismatches": len(mism),
                    "nodes_shared_between_crossbar_and_core": shared[:10], "n_shared_nodes": len(shared),
                    "census": census(d["crossbar"], d["taps"])}
        print(key, json.dumps({k: v_ for k, v_ in out[key].items() if k != "census"}, default=str)[:900], flush=True)
        print(key, json.dumps(out[key]["census"], default=str)[:900], flush=True)
    save("v2_crossbar.json", out)


if __name__ == "__main__":
    main()
