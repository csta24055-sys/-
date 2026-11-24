"""H-B4: is the grammar circuit only an isomorphic rewriting of the Sigma/knot graph? Count elements,
parameters, states and per-T operations per kernel family, next to the msp step counts and knot counts.

Metrics (per scenario, per family):
  msp side:   P1 static steps of the group that builds the amplitudes; EMIT declarations; knots stored by
              KnotSpectrum; merged shapes (rampstep.merge: the irreducible kernel terms); irreducible
              parameters = sum over merged shapes of (free shape parameters + 1 amplitude)
              (const 1, density 1, atom 2 (tau,a), cell 2 (k,a), gcell 3 (k,tau,a)); per-T operations of the
              knot evaluation = comparisons of two binary searches + 6 flops.
  circuit:    primitive instances by type, parameters = src values + gain coefficients + table entries
              (fixed clip bounds 0/1 and the sweep source are structural, not counted), 4-tuple
              (continuous states, discrete states/counters, comparator thresholds, external table entries),
              per-T primitive evaluations (memoryless) or segments x nodes (sweep from T=0).
A family where circuit parameters (or states) < msp irreducible parameters (or stored table) would refute
H-B4 in that metric; it is reported, not hidden.
"""
from __future__ import annotations

import collections
import json
import math
import os
import sys
import time

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import grammar as G  # noqa: E402
import oracle_io as O  # noqa: E402

FREE = {"const": 1, "density": 1, "atom": 2, "cell": 2, "gcell": 3}
P1_GROUP = {"B4-02": "AMPLITUDES+EVENTS", "B5-01": "AMPLITUDES+EVENTS", "B3-01": "AMPLITUDES+EVENTS",
            "B6-03": "OPERATION", "B7-04": "OPERATION", "B1-03": "REFRIGERANT", "B1-02": "REFRIGERANT"}


def msp_side(sy, unit, usage):
    m = O.setup()
    pieces = sy.pieces.get(unit, [])
    merged = m["rampstep"].merge([p for p in pieces if p.amp != 0.0])
    irr = 0
    for (s, l, g), a in merged.items():
        p = m["rampstep"].Piece(a, s, l, g)
        irr += FREE[G.classify_piece(p, sy.H)]
    K = sy.K[unit]
    ne, npl = len(K.ev_keys), len(K.la_keys)
    groups = P1_GROUP.get(unit, "")
    p1 = sum(usage.get(gname, {}).get("step:sp", 0) + usage.get(gname, {}).get("step:match", 0) for gname in groups.split("+"))
    emit = sum(1 for e in m["system"].EMIT if e["spectrum"] == unit)
    return {"pieces": len(pieces), "merged_shapes": len(merged), "irreducible_params": irr, "knots_stored": K.n_knots,
            "knot_params_stored": 3 * K.n_knots, "per_T_ops_knot": math.ceil(math.log2(ne + 1)) + math.ceil(math.log2(npl + 1)) + 6,
            "p1_static_steps_of_group": p1, "p1_group": groups, "emit_declarations": emit}


def circuit_side(pieces, H, mode):
    net, out, kinds, bps, nk = G.build_kernel(pieces, H, mode)
    c = net.counts()
    params = c.get("src", 0) + c.get("gain", 0) + c.get("table_entries", 0)
    nodes = sum(v for k, v in c.items() if k in G.PRIMITIVES)
    cont = c.get("int", 0)
    thresholds = c.get("cmp", 0)
    tup = (cont, 0 if mode == "clip" else 1, thresholds, c.get("table_entries", 0))
    per_T = nodes if not net.ints else None
    consumers = collections.Counter(i for _, ins, _ in net.ops for i in ins)
    shared_src = sum(1 for n, (p, _, _) in enumerate(net.ops) if p == "src" and consumers[n] > 1)
    extra_uses = sum(consumers[n] - 1 for n, (p, _, _) in enumerate(net.ops) if p == "src" and consumers[n] > 1)
    return {"mode": mode, "primitives": c, "params": params, "nodes": nodes, "state_tuple": tup,
            "src_nodes_with_fanout": shared_src, "params_if_no_fanout": params + extra_uses,
            "per_T_evals_memoryless": per_T, "sweep_segments_to_H": (len(bps) + 1) if net.ints else None}


def refrigerant_family(scn, sy, usage, Ts):
    m = O.setup()
    t0 = time.perf_counter()
    rc = G.RefrigerantCircuit(scn, int(sy.H))
    rc.sweep(Ts)
    t_rc = time.perf_counter() - t0
    t0 = time.perf_counter()
    for T in Ts:
        sy.I14.value(T)
        sy.K["B1-02"].value(T)
        sy.K["B1-03"].value(T)
    t_knots = time.perf_counter() - t0
    tabs = sy.eng
    years_rows = tabs.nrows("refrigerants.years") if "refrigerants.years" in sy.tabs.rows else None
    time_steps = [s["out"] for s in m["unified"].P_TIME.steps if s["out"].startswith(("t.b12", "t.b13", "t.b14", "t.b1_"))]
    nd = len(rc.devs)
    return {
        "msp": {"p1_static_steps_REFRIGERANT": usage["REFRIGERANT"].get("step:sp", 0) + usage["REFRIGERANT"].get("step:match", 0),
                "time_static_steps_B1": len(time_steps), "emit_declarations_B1": sum(1 for e in m["system"].EMIT if e["spectrum"].startswith("B1-")),
                "rows_device_x_year_table": years_rows,
                "knots_stored_B1-02": sy.K["B1-02"].n_knots, "knots_stored_B1-03": sy.K["B1-03"].n_knots,
                "interval_B1-04_n": sy.I14.n_knots,
                "seconds_eval_knots+interval_for_grid": t_knots},
        "circuit": {"devices_active": nd, "state_tuple": rc.state_tuple(), "primitives": dict(rc.prim),
                    "template_instances_per_device": 19, "seconds_build+sweep_for_grid": t_rc,
                    "boundary_updates_to_reach_T": "ceil(T)-1 (sequential)"},
    }


def run():
    m = O.setup()
    usage = m["msp"].static_usage(m["unified"].P1)
    prog = {"P1": len(m["unified"].P1.steps), "TIME": len(m["unified"].P_TIME.steps), "AGG": len(m["unified"].P_AGG.steps)}
    out = {"program_steps": prog, "scenarios": {}}
    Ts = [1.0, 9.999999, 10.0, 10.000001, 19.999999, 20.0, 20.000001, 30.0, 40.0, 60.0]
    for scn in O.representative_scenarios(("S", "M")):
        sy = O.system(scn)
        H = int(sy.H)
        fam = {}
        for unit in ("B4-02", "B5-01", "B6-03", "B7-04", "B3-01", "B1-03", "B1-02"):
            ms = msp_side(sy, unit, usage)
            circ = [circuit_side(sy.pieces.get(unit, []), H, "clip")]
            if unit in ("B6-03", "B7-04", "B1-02"):
                circ.append(circuit_side(sy.pieces.get(unit, []), H, "integrator"))
            verdict = []
            for c in circ:
                if ms["irreducible_params"] and c["params"] < ms["irreducible_params"]:
                    verdict.append(f"{c['mode']}: circuit params {c['params']} < irreducible {ms['irreducible_params']}"
                                   f" (without source fan-out: {c['params_if_no_fanout']})")
            fam[unit] = {"msp": ms, "circuit": circ, "smaller_than_irreducible": verdict}
        fam["refrigerant B1-02/03/04 (raw automaton vs P1 REFRIGERANT + knots + interval)"] = refrigerant_family(scn, sy, usage, Ts)
        out["scenarios"][scn.meta.scenario_id] = fam
    return out


def main():
    res = run()
    with open(os.path.join(O.ROUTE, "results", "hb4_counts.json"), "w") as f:
        json.dump(res, f, indent=1, default=str)
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
