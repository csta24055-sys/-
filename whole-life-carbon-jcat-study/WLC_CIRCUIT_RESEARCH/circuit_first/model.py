"""Circuit-first model: build the shared netlist from primitive inputs (adapter), run the
generic hybrid engine, read out stage charges.

Readout layer (the only arithmetic on results): S_s = gamma * sum of tap-capacitor charges
of stage s, C = sum_s S_s. No event list, year loop or reference code is used anywhere.
"""
from __future__ import annotations

from fractions import Fraction

from adapter import CONVENTIONS, Units, build
from engine import Simulator
from engine.netlist import Capacitor, Comparator, Diode, Switch


def simulate(scn, T_list, convention="right", units=Units(), mutations=(), record=False):
    built = build(scn, units, convention, mutations)
    eps, prio = CONVENTIONS[convention]
    if "readout_order_swapped" in mutations:
        prio = 100 if prio == 0 else 0
    Ts = [Fraction(str(T)) if isinstance(T, float) else Fraction(T) for T in T_list]
    readouts = [(T * units.tau_y, prio, T) for T in Ts]
    sim = Simulator(built.netlist, exact=True, record=record, record_midpoints=False)
    sim.run(max(Ts) * units.tau_y, readouts)
    nl = built.netlist
    out = {"convention": convention, "epsilon": eps, "units": units, "by_T": {}}
    for snap in sim.sol.readouts:
        T = snap["label"]
        stages = {}
        Q = Fraction(0)
        for st, caps in built.taps.items():
            q = sum((nl.by_name[c].C * snap["s"][c] for c in caps), Fraction(0))
            stages[st] = units.gamma * q
            Q += q
        diss = sum((snap["meters_cont"][e] + (snap["meters_jump"][e] or 0) for e in built.datapath), Fraction(0))
        out["by_T"][T] = {"C": units.gamma * Q, "stages": stages, "Q_total": Q,
                          "datapath_heat": diss, "V0_Q": units.V0 * Q}
    out["events"] = item_events(sim, built, units)
    out["group_events"] = group_events(sim, built, units)
    out["sim"] = sim
    out["built"] = built
    return out


def item_events(sim, built, units):
    """Times (in years) at which each item's replacement packet was taken."""
    inv = {v: k for k, v in built.item_seq.items()}
    ev = {k: [] for k in built.item_seq}
    for e in sim.sol.events:
        if e["type"] == "seq" and e["name"] in inv:
            ev[inv[e["name"]]].append(_frac(e["t"]) / units.tau_y)
    return ev


def group_events(sim, built, units):
    """Group replacement events with the year they belong to, read from boolean logs only:
    year = (number of year ticks before the event) + 1 - P (P = shared lookahead level)."""
    out = {}
    fires = {gs["fire"]: gt for gt, gs in built.group_signals.items()}
    ticks = 0
    P = False
    for e in sim.sol.events:
        if e["type"] != "edge":
            continue
        sig, val = e["signal"], e["value"]
        if sig == "P":
            P = val
        if sig == "tick" and val:
            ticks += 1
        if sig in fires and val:
            out.setdefault(fires[sig], []).append({"t": _frac(e["t"]) / units.tau_y, "year": ticks + 1 - int(P)})
    return out


def _frac(s):
    if isinstance(s, Fraction):
        return s
    if "/" in s:
        a, b = s.split("/")
        return Fraction(int(a), int(b))
    return Fraction(int(s))


# ----------------------------------------------------------------- audits


def hiddenness(built):
    """h = W_out / (W_in + W_out) with the counting rules of architecture section 4."""
    nl = built.netlist
    deg = {}
    for e in nl.analog():
        for n in e.nodes():
            if n != "0":
                deg[n] = deg.get(n, 0) + 1
    kcl_adds = sum(max(0, d - 2) for d in deg.values())
    n_cmp = sum(1 for e in nl.digital() if isinstance(e, Comparator))
    n_dio = sum(1 for e in nl.analog() if isinstance(e, Diode))
    n_sw = sum(1 for e in nl.analog() if isinstance(e, Switch))
    L = built.ledger
    W_in = L.data_elements + kcl_adds + n_cmp + n_dio + n_sw
    W_out = L.counts["GREY"]
    return {"h": Fraction(W_out, W_in + W_out) if (W_in + W_out) else Fraction(0),
            "W_in": W_in, "W_out": W_out,
            "W_in_parts": {"data_elements": L.data_elements, "kcl_additions": kcl_adds,
                           "comparators": n_cmp, "diodes": n_dio, "switches": n_sw},
            "construction_ops": dict(L.counts), "grey_items": list(L.grey_items)}


def schema_signature(built):
    """Cell types with their port connection pattern, ignoring counts and values."""
    return frozenset((ct, tuple(sorted(ports.items()))) for ct, _, ports in built.cells)


def state_counts(built):
    nl = built.netlist
    caps = [e for e in nl.analog() if isinstance(e, Capacitor)]
    by_cell = {}
    for c in caps:
        by_cell[c.tags.get("cell", "?")] = by_cell.get(c.tags.get("cell", "?"), 0) + 1
    from engine.netlist import Counter, DFF, SRLatch, Sequencer
    bits = 0
    for e in nl.digital():
        if isinstance(e, (SRLatch, DFF)):
            bits += 1
        elif isinstance(e, Counter):
            bits += e.nbits
        elif isinstance(e, Comparator):
            bits += 1
    kinds = {}
    for e in nl.elements:
        kinds[e.kind] = kinds.get(e.kind, 0) + 1
    return {"continuous_states": len(caps), "by_cell": by_cell, "boolean_bits": bits,
            "sequencers": sum(1 for e in nl.digital() if isinstance(e, Sequencer)),
            "element_kinds": kinds, "elements": len(nl.elements)}
