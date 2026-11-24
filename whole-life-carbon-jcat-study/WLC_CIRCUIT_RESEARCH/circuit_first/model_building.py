"""Full synthetic building on the circuit: crossbar DC solve + hybrid lifecycle core + readout.

Readout layer only: S_s = gamma * (bus charge + readout-bus charge) of stage s; the stage set
iota is applied here (and as the static steering switch of the rho leg); C = sum over iota;
Z = gamma * readout-bus charge of terminal quantities (C1..C4 packets, B1 residual).
No reference code is imported.
"""
from __future__ import annotations

import time
from fractions import Fraction

import adapter_building as ab
from adapter import CONVENTIONS, Units
from engine.dc import kcl_residual, solve_dc
from engine.hybrid import Hybrid


def simulate_building(scn, T_list, convention="original", blocks=ab.ALL_BLOCKS, units=Units(), mutations=(),
                      record=False, accumulators=True):
    t0 = time.time()
    L = ab.LayeredLedger()
    L.layer = "amp"
    A, amp = ab.build_amplitudes(scn, L, units, blocks, mutations)
    iota = set(scn.boundary.included_lifecycle_stages)
    op_parts = None
    if "OP" in blocks:
        pending, elec, info = ab.operation(None, A, scn, L, iota, None)
        op_parts = (pending, elec)
    ref_parts = ab.refrigerant_amp(A, scn, L) if "REF" in blocks else None
    t1 = time.time()
    volts, cur, dcinfo = solve_dc(A.nl)
    dc_res = kcl_residual(A.nl, volts, cur)
    tapv = {name: volts[node] for name, (node, sign) in A.exports.items()}
    t2 = time.time()
    B, groups, kinds = ab.build_core(scn, L, units, convention, blocks, amp, A, tapv, op_parts, ref_parts, mutations)
    eps, prio = CONVENTIONS[convention]
    if "readout_order_swapped" in mutations:
        prio = 100 if prio == 0 else 0
    Ts = [Fraction(x) for x in T_list]
    caps = [c for lst in B.readout_caps.values() for c in lst]
    t3 = time.time()
    sim = Hybrid(B.nl, record=record, record_jumps=record, accumulators=accumulators).run(max(Ts) * units.tau_y,
                                          [{"t": T * units.tau_y, "priority": prio, "label": T, "signal": "rd",
                                            "caps": caps} for T in Ts])
    t4 = time.time()
    nl = B.nl
    out = {"by_T": {}, "iota": iota, "convention": convention}
    zstages = set(B.zbus)
    for snap in sim.readouts:
        T = snap["label"]
        st, z = {}, Fraction(0)
        for s, lst in B.readout_caps.items():
            st[s] = units.gamma * sum((nl.by_name[c].C * snap["s"][c] for c in lst), Fraction(0))
        for s in zstages:
            if s in ("C1", "C2", "C3", "C4") or s == "B1":
                if s in iota:
                    z += units.gamma * nl.by_name[f"z.{s}.C"].C * snap["s"][f"z.{s}.C"]
        C = sum((v for s, v in st.items() if s in iota), Fraction(0))
        out["by_T"][T] = {"C": C, "stages": {s: v for s, v in st.items() if s in iota}, "Z": z, "M": C - z,
                          "counter": snap["counters"].get("tb.cnt")}
    out["events"] = [e for e in sim.events if e["type"] in ("seq", "cmp")]
    out["groups"] = groups
    out["kinds"] = kinds
    out["sim"], out["core"], out["amp"], out["A"] = sim, B, amp, A
    out["ledger"] = L
    out["dc"] = dict(dcinfo, kcl_residual=dc_res, elements=len(A.nl.elements), opamps=A.opamps)
    out["times"] = {"amp_build": t1 - t0, "dc_solve": t2 - t1, "core_build": t3 - t2, "hybrid": t4 - t3}
    out["sim_stats"] = dict(sim.stats)
    return out


def group_event_counts(out, T):
    """Replacement events per row up to T, read from the comparator log (rows x firings)."""
    tau = out["core"].u.tau_y
    total = 0
    for gt, g in out["groups"].items():
        n = 0
        for e in out["events"]:
            if e["type"] == "cmp" and e["value"] and (e["name"] == f"{gt}.clk.late" or
                                                     (e["name"].startswith(f"{gt}.x") and e["name"].endswith(".late"))):
                t = Fraction(e["t"]) if "/" not in e["t"] else Fraction(*map(int, e["t"].split("/")))
                if t < T * tau:
                    n += 1
        total += n * g["rows"]
    return total


def _netcounts(nl):
    from engine.netlist import Capacitor, Comparator, Counter, DFF, Diode, OpAmp, SRLatch, Switch
    deg = {}
    for e in nl.analog():
        for n in e.nodes():
            if n != "0":
                deg[n] = deg.get(n, 0) + 1
    bits = sum(1 for e in nl.digital() if isinstance(e, (SRLatch, DFF, Comparator))) + \
        sum(e.nbits for e in nl.digital() if isinstance(e, Counter))
    return {"elements": len(nl.elements),
            "opamps": sum(1 for e in nl.analog() if isinstance(e, OpAmp)),
            "capacitors": sum(1 for e in nl.analog() if isinstance(e, Capacitor)),
            "comparators": sum(1 for e in nl.digital() if isinstance(e, Comparator)),
            "switches": sum(1 for e in nl.analog() if isinstance(e, Switch)),
            "diodes": sum(1 for e in nl.analog() if isinstance(e, Diode)),
            "bits": bits, "kcl_additions": sum(max(0, d - 2) for d in deg.values())}


def audit_counts(out):
    from model import _vg_additions, control_census
    L = out["ledger"]
    amp, core = _netcounts(out["A"].nl), _netcounts(out["core"].nl)
    amp["vg_additions"], core["vg_additions"] = _vg_additions(out["A"].nl), _vg_additions(out["core"].nl)
    la, lt = L.by_layer.get("amp", {}), L.by_layer.get("time", {})
    # narrow W_in (V1-D6): data elements + virtual-ground additions + comparators + diodes
    w_in_amp = la.get("data_elements", 0) + amp["vg_additions"] + amp["comparators"] + amp["diodes"]
    w_in_time = lt.get("data_elements", 0) + core["vg_additions"] + core["comparators"] + core["diodes"]
    broad = {"amp": la.get("data_elements", 0) + amp["kcl_additions"] + amp["comparators"] + amp["switches"] + amp["diodes"],
             "time": lt.get("data_elements", 0) + core["kcl_additions"] + core["comparators"] + core["switches"] + core["diodes"]}
    g_amp, g_time = la.get("GREY", 0), lt.get("GREY", 0)
    grey = {}
    for x in L.grey_items:
        k = x.split("(")[0].split("[")[0] if not x.startswith("(") else x
        grey[x if len(grey) < 0 else _grey_kind(x)] = grey.get(_grey_kind(x), 0) + 1
    tot_in, tot_out = w_in_amp + w_in_time, g_amp + g_time
    sc = scn_size(out)
    return {"h": float(Fraction(tot_out, tot_in + tot_out)), "h_amp": float(Fraction(g_amp, w_in_amp + g_amp)),
            "h_time": float(Fraction(g_time, w_in_time + g_time) if (w_in_time + g_time) else 0),
            "W_in_amp": w_in_amp, "W_in_time": w_in_time, "W_out_amp": g_amp, "W_out_time": g_time,
            "W_in_broad": broad, "control_not_counted_in_h": control_census(out["core"].nl, L, (0, 100)),
            "ops_by_layer": L.by_layer, "grey_by_kind": grey,
            "crossbar": amp, "core": core, "dc": out["dc"], "size": sc}


def _grey_kind(x):
    for k in ("EPD validity", "sum fraction", "grid start", "step order"):
        if k in x:
            return k
    if ".comp[" in x and "+" in x:
        return "composite: running sum of mass fractions"
    if ".comp[" in x and "-" in x:
        return "composite: sum - 1"
    return "OTHER: " + x


def scn_size(out):
    g = out["groups"]
    core = out["core"]
    n_c = sum(1 for v in g.values() if v["key"][0] == "P")
    n_x = sum(len(v["key"][1]) for v in g.values() if v["key"][0] == "X")
    n_r = sum(1 for e in core.nl.elements if e.name.endswith(".Cm") and e.name.startswith("rf"))
    return {"N_c_periodic_groups": n_c, "N_x_explicit_events": n_x, "N_r_devices": n_r, "groups": len(g)}
