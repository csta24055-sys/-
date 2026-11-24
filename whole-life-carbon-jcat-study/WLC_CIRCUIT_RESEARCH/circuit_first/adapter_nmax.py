"""N_max same-netlist generator for the stage-A cell family (initial rows, constant flows,
periodic replacement items).

Every scenario of the family is mapped onto ONE netlist with fixed slot counts
dims = {"init": I, "flow": Fn, "item": N, "clock": K}. A scenario only changes
  * element values (data in used slots; the building-independent placeholder 1 in unused slots),
  * static switch states (boolean configuration constants "CFG1"/"CFG0"): slot enable, and the
    item -> clock selection matrix that replaces the W2 grouping decision.
Unused clocks have their ramp input switch open (they never fire); unused packets are never
selected. Signed amounts use the polarity switch pair of the packet cell (both polarities built).
"""
from __future__ import annotations

from fractions import Fraction

from adapter import CONVENTIONS, PH, PRIO, Builder, OpLedger, Tracked, Units, w3_sign, w2_key


def _cfg(flag):
    return "ONE" if flag else "ZERO"


def build_padded(scn, units: Units, convention, dims):
    eps, _ = CONVENTIONS[convention]
    L = OpLedger()
    B = Builder(units, eps, L)
    u = units
    B.rails()
    B.timebase()
    B.nl.power_on("por", "por", priority=PRIO["por"])
    stages = sorted({r["stage"] for k in ("initial", "flows", "items") for r in scn.get(k, [])})
    bus_slots = dims["bus"]
    if len(stages) > bus_slots:
        raise ValueError("more stages than bus slots")
    for k in range(bus_slots):
        B.bus(f"s{k}")
    stage_of = {s: f"s{k}" for k, s in enumerate(stages)}
    one = Fraction(1)

    def tr(x, lab):
        return Tracked(Fraction(x), lab, L) if x is not None else None

    def packet_slot(tag, A, stage, trig):
        """Both polarities exist; the value and the active polarity come from the input."""
        sg = w3_sign(A) if A is not None else 0
        C = B.val(A * (sg / (u.gamma * u.V0))) if sg else one
        dst = {s: B.bus(st) for s, st in stage_of.items()}
        # destination selection: one dump switch per bus slot, closed only for the row's stage
        a, b = f"{tag}.a", f"{tag}.b"
        nl = B.nl
        nl.C(f"{tag}.Cs", a, b, C, v0=u.V0)
        nl.switch(f"{tag}.St", a, "rail", f"{tag}.trk")
        nl.switch(f"{tag}.Sbg", b, "0", f"{tag}.trk")
        for k in range(bus_slots):
            bx = B.bus(f"s{k}")
            hit = stage is not None and stage_of.get(stage) == f"s{k}"
            for pol, (pa, pb) in ((1, ("a", "b")), (-1, ("b", "a"))):
                en = f"{tag}.en{k}{'p' if pol > 0 else 'n'}"
                nl.gate(en, "AND", [f"{tag}.dmp", _cfg(hit and sg == pol)], en)
                nl.switch(f"{tag}.Sx{k}{'p' if pol > 0 else 'n'}", {"a": a, "b": b}[pa], bx, en)
                nl.switch(f"{tag}.Sg{k}{'p' if pol > 0 else 'n'}", {"a": a, "b": b}[pb], "0", en)
        nl.sequencer(f"{tag}.seq", trig, {f"{tag}.trk": True, f"{tag}.dmp": False},
                     [{(f"{tag}.trk" if kk == "trk" else f"{tag}.dmp"): v} for kk, v in PH])

    rows = scn.get("initial", [])
    for k in range(dims["init"]):
        row = rows[k] if k < len(rows) else None
        A = tr(row["amount"], f"init[{k}]") if row else None
        packet_slot(f"init{k}", A, row["stage"] if row else None, "por")
    flows = scn.get("flows", [])
    for k in range(dims["flow"]):
        fl = flows[k] if k < len(flows) else None
        r = tr(fl["rate"], f"flow[{k}]") if fl else None
        sg = w3_sign(r) if r is not None else 0
        G = B.val(r * (sg / (u.gamma * u.tau_y * u.V0))) if sg else one
        for pol, src in ((1, "rail"), (-1, "railn")):
            nl = B.nl
            nl.R(f"fl{k}.{pol}.G", src, f"fl{k}.{pol}.n", G=G)
            for j in range(bus_slots):
                hit = fl is not None and stage_of[fl["stage"]] == f"s{j}" and sg == pol
                nl.switch(f"fl{k}.{pol}.S{j}", f"fl{k}.{pol}.n", B.bus(f"s{j}"), _cfg(hit))
    items = scn.get("items", [])
    # clock slots: W2 grouping is replaced by a static selection matrix
    keys, clock_of = [], {}
    for it in items:
        P = tr(it["period"], f"item[{it['id']}].period")
        key = w2_key(L, P)
        if key not in keys:
            keys.append(key)
            clock_of[key] = P
    if len(keys) > dims["clock"] or len(items) > dims["item"]:
        raise ValueError("scenario exceeds the N_max dimensions")
    fires = []
    for k in range(dims["clock"]):
        used = k < len(keys)
        per = clock_of[keys[k]] if used else None
        Cj = B.val(per * (u.Gu * u.tau_y)) if used else one
        tag = f"c{k}"
        x, o = B.integrator(tag, Cj, "clock")
        B.nl.R(f"{tag}.G", "railn", f"{tag}.gn", G=u.Gu * (1 - eps))
        B.nl.switch(f"{tag}.Sen", f"{tag}.gn", x, _cfg(used))
        B.nl.comparator(f"{tag}.late", o, "vth", f"{tag}.fire", priority=PRIO["fire"])
        Cr = B.val(per * (u.Gu * u.tau_y)) if used else one
        B.packet(f"{tag}.rst", Cr, "vth", x, f"{tag}.fire", v0=u.V0, cell="clock", datapath=False)
        fires.append(f"{tag}.fire")
    for i in range(dims["item"]):
        it = items[i] if i < len(items) else None
        terms = []
        for k in range(dims["clock"]):
            sel = it is not None and k < len(keys) and keys[k] == w2_key(L, tr(it["period"], "p"))
            g = f"it{i}.sel{k}"
            B.nl.gate(g, "AND", [fires[k], _cfg(sel)], g)
            terms.append(g)
        B.nl.gate(f"it{i}.trig", "OR", terms, f"it{i}.trig")
        A = tr(it["amount"], f"item[{i}]") if it else None
        packet_slot(f"it{i}", A, it["stage"] if it else None, f"it{i}.trig")
    return B, stage_of, L


def topology_key(nl):
    """Exact topology of a netlist, values and static configuration ignored: element names,
    kinds, node connections, gate inputs (CFG constants collapsed), sequencer step structure."""
    out = []
    for e in nl.elements:
        d = {"name": e.name, "kind": e.kind}
        for k in ("a", "b", "inp", "inn", "out", "plus", "minus", "cp", "cn", "trigger", "clk", "set", "reset", "d", "q"):
            if hasattr(e, k):
                d[k] = getattr(e, k)
        if hasattr(e, "ctrl"):
            d["ctrl"] = "CFG" if e.ctrl in ("ONE", "ZERO") else e.ctrl
        if hasattr(e, "inputs"):
            d["inputs"] = tuple("CFG" if x in ("ONE", "ZERO") else x for x in e.inputs)
            d["op"] = e.op
        if hasattr(e, "steps"):
            d["steps"] = tuple(tuple(sorted(s)) for s in e.steps)
        out.append(tuple(sorted(d.items())))
    return tuple(out)
