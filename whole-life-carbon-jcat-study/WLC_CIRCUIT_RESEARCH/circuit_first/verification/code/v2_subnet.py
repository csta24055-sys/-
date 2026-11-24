"""V2: re-simulate a building-scale sub-network of the dumped E1 core with the verifier's own
simulator (vsim) and compare with the snapshot's hybrid.py (accumulators on and off).

Sub-network: rails, time base (year ramp, counter, look-ahead P with VCVS divider), power-on,
event groups g0 (period 10), g7 (period 11) and one explicit-list group, refrigerant devices
rf0 (periodic) and rf2, their taps, the stage buses and readout buses they feed. The
sub-network is closed: every boolean signal it reads is produced inside it (checked).
Readouts with the 'rd' control pulse at several T, original convention (priority 0).
"""
from __future__ import annotations

import json
import os
import sys
import time
from fractions import Fraction as Fr

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import SNAP, save, fstr  # noqa: E402
from vsim import VSim, num  # noqa: E402

sys.path.insert(0, SNAP)
from engine import netlist as N  # noqa: E402
from engine.hybrid import Hybrid  # noqa: E402

KIND = {"R": lambda e: N.Resistor(e["name"], e["a"], e["b"], num(e["G"])),
        "C": lambda e: N.Capacitor(e["name"], e["a"], e["b"], num(e["C"]), num(e.get("v0", 0) or 0)),
        "V": lambda e: N.VSource(e["name"], e["a"], e["b"], num(e["V"])),
        "I": lambda e: N.ISource(e["name"], e["a"], e["b"], num(e["I"])),
        "OA": lambda e: N.OpAmp(e["name"], e["inp"], e["inn"], e["out"]),
        "SW": lambda e: N.Switch(e["name"], e["a"], e["b"], e["ctrl"], e["invert"]),
        "E": lambda e: N.VCVS(e["name"], e["a"], e["b"], e["cp"], e["cn"], num(e["gain"])),
        "CMP": lambda e: N.Comparator(e["name"], e["plus"], e["minus"], e["out"], int(e["priority"])),
        "GATE": lambda e: N.Gate(e["name"], e["op"], list(e["inputs"]), e["out"]),
        "SR": lambda e: N.SRLatch(e["name"], e["set"], e["reset"], e["q"], e["init"]),
        "DFF": lambda e: N.DFF(e["name"], e["d"], e["clk"], e["q"], e["init"]),
        "CNT": lambda e: N.Counter(e["name"], e["clk"], int(e["nbits"]), e["prefix"]),
        "SEQ": lambda e: N.Sequencer(e["name"], e["trigger"], {k: bool(v) for k, v in e["idle"].items()},
                                     [{k: bool(v) for k, v in s.items()} for s in e["steps"]]),
        "POR": lambda e: N.PowerOn(e["name"], e["out"], int(e["priority"]))}


def to_netlist(js):
    nl = N.Netlist()
    for e in js:
        el = KIND[e["kind"]](e)
        el.tags = {k: (v if not isinstance(v, str) or k != "accumulator" else v) for k, v in (e.get("tags") or {}).items()}
        nl.add(el)
    return nl


def produced(e):
    k = e["kind"]
    if k in ("CMP", "GATE", "POR"):
        return {e["out"]}
    if k in ("SR", "DFF"):
        return {e["q"]}
    if k == "CNT":
        return {f"{e['prefix']}{i}" for i in range(int(e["nbits"]))}
    if k == "SEQ":
        out = set(e["idle"])
        for s in e["steps"]:
            out |= set(s)
        return out
    return set()


def consumed(e):
    k = e["kind"]
    if k == "SW":
        return {e["ctrl"]}
    if k == "GATE":
        return set(e["inputs"])
    if k == "SR":
        return {e["set"], e["reset"]}
    if k == "DFF":
        return {e["d"], e["clk"]}
    if k in ("CNT",):
        return {e["clk"]}
    if k == "SEQ":
        return {e["trigger"]}
    return set()


def nodes(e):
    return [e[k] for k in ("a", "b", "inp", "inn", "out", "plus", "minus", "cp", "cn") if k in e and e["kind"] not in
            ("GATE", "SR", "DFF", "CNT", "SEQ", "POR") and not (e["kind"] == "CMP" and k == "out")]


def extract(core, groups):
    seeds = ("rail.", "tb.", "por") + tuple(f"{g}." for g in groups) + tuple(f"pk.{g}." for g in groups)
    sel = {e["name"]: e for e in core if e["name"].startswith(seeds) or e["name"] == "por"}
    byname = {e["name"]: e for e in core}
    # include elements on nodes touched (taps, buses, readout buses) until closure on analog nodes
    changed = True
    while changed:
        changed = False
        used = {n for e in sel.values() for n in nodes(e)} - {"0"}
        for e in core:
            if e["name"] in sel:
                continue
            if e["name"].startswith(("tap.", "bus.", "z.")) and set(nodes(e)) & used:
                sel[e["name"]] = e; changed = True
        # bus / z cells complete (op-amp, capacitor, reset switch, reset sequencer)
        for e in core:
            if e["name"] not in sel and e["name"].startswith(("bus.", "z.")):
                stem = ".".join(e["name"].split(".")[:2])
                if any(x.startswith(stem + ".") for x in sel):
                    sel[e["name"]] = e; changed = True
    sigs_needed = set().union(*(consumed(e) for e in sel.values())) - {"ONE", "ZERO", "rd"}
    sigs_made = set().union(*(produced(e) for e in sel.values()))
    missing = sorted(sigs_needed - sigs_made)
    # decoders of the counter used by banks (none expected here)
    return [e for e in core if e["name"] in sel], missing


def main():
    d = json.load(open(os.path.join(SNAP, "results", "stageB_netlists_E1.json")))
    core = d["core"]
    expl = sorted({e["name"].split(".")[0] for e in core if ".x0.late" in e["name"] and e["name"].startswith("g")})[:1]
    groups = ["g0", "g7"] + expl + ["rf0", "rf2"]
    sub, missing = extract(core, groups)
    info = {"groups": groups, "elements": len(sub), "missing_signals": missing,
            "kinds": {k: sum(1 for e in sub if e["kind"] == k) for k in sorted({e["kind"] for e in sub})}}
    print(json.dumps(info), flush=True)
    Ts = [Fr(9999999, 1000000), Fr(10000001, 1000000), Fr(33, 1), Fr(333, 10), Fr(60, 1)]
    caps = [e["name"] for e in sub if e["kind"] == "C"]
    t0 = time.time()
    hyb = {}
    for acc in (True, False):
        h = Hybrid(to_netlist(sub), accumulators=acc).run(max(Ts), [{"t": T, "priority": 0, "label": T, "signal": "rd", "caps": caps} for T in Ts])
        hyb[acc] = {r["label"]: r["s"] for r in h.readouts}
    t1 = time.time()
    vs = VSim(sub).run(max(Ts), [(T, 0, T, "rd") for T in Ts])
    t2 = time.time()
    mism = []
    for sn in vs.snaps:
        T = sn["label"]
        for c in caps:
            a, b, b2 = sn["u"][c], hyb[True][T][c], hyb[False][T][c]
            if not (a == b == b2):
                mism.append((fstr(T), c, float(a), float(b), float(b2)))
    taps_out = {c: [fstr(sn["u"][c]) for sn in vs.snaps] for c in caps if c.startswith(("bus.", "z."))}
    res = dict(info, T=[fstr(T) for T in Ts], capacitors=len(caps), mismatches=mism[:20], n_mismatches=len(mism),
               hybrid_s=round(t1 - t0, 1), vsim_s=round(t2 - t1, 1), vsim_modes=vs.n_modes, readout_states=taps_out,
               cmp_events_vsim=sum(1 for e in vs.events if e[1] == "cmp"))
    save("v2_subnet.json", res)
    print(json.dumps({k: v for k, v in res.items() if k != "readout_states"}, default=str)[:1500])


if __name__ == "__main__":
    main()
