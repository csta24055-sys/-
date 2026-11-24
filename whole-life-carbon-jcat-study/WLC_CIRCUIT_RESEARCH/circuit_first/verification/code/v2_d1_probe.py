"""V2: adversarial probes of the post-phase comparator rule (D11) in sim.py AND hybrid.py of
snapshot 80ec2de, compared with the verifier's vsim and with the exact set-valued meaning
out(t) = [y(t) >= 0].

Cases
  gated_fall      y = 1 - t gates an integrator (expected charge 1 at T = 3)          [V1-D1]
  gated_rise      y = t - 1 (expected 2)
  touch_above     y = (t-1)^2/2 >= 0 touches 0 at t = 1 and rises (out stays 1; charge 3)
  touch_below     y = -(t-1)^2/2 touches 0 from below at t = 1 (out = 1 only at t = 1:
                  integral unaffected, charge 0; a zero-width pulse is counted by a counter)
  rise_fall_and   A = [t-1 >= 0], B = [1-t >= 0], AND(A,B) counted: true only at t = 1
  self_feedback   comparator output opens the switch that keeps its own input >= 0
                  (chattering at t = 0: a non-terminating instant must be reported, not hang)
"""
from __future__ import annotations

import json
import os
import sys
import signal
from fractions import Fraction as F

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import SNAP, save  # noqa: E402
from vsim import VSim  # noqa: E402

sys.path.insert(0, SNAP)
from engine import Netlist, Simulator  # noqa: E402
from engine.hybrid import Hybrid  # noqa: E402


def ramp(nl, tag, src="railn"):
    nl.R(f"{tag}.G", src, f"{tag}.x", G=F(1)); nl.opamp(f"{tag}.A", "0", f"{tag}.x", f"{tag}.o")
    nl.C(f"{tag}.C", f"{tag}.x", f"{tag}.o", F(1))
    return f"{tag}.o"


def base():
    nl = Netlist()
    nl.V("V1", "rail", "0", F(1)); nl.V("Vn", "railn", "0", F(-1)); nl.V("Vh", "half", "0", F(1, 2))
    return nl


def gated(nl, ctrl):
    nl.R("Gb", "rail", "s", G=F(1)); nl.switch("S", "s", "xb", ctrl)
    nl.opamp("B", "0", "xb", "ob"); nl.C("Cb", "xb", "ob", F(1))


def quad(nl, sign):
    """v = sign*((t-1)^2/2) built from integrators: o1 = t, o2 = -t^2/2 (second inverting integrator),
    summer: out = -(Ga o2 + ...)"""
    o1 = ramp(nl, "r1")                                   # +t
    nl.R("r2.G", o1, "r2.x", G=F(1)); nl.opamp("r2.A", "0", "r2.x", "r2.o"); nl.C("r2.C", "r2.x", "r2.o", F(1))  # -t^2/2
    # w = -(r2.o) - t + 1/2 = t^2/2 - t + 1/2 via summer with inverted terms
    nl.R("s.a", "r2.o", "s.x", G=F(1)); nl.R("s.b", o1, "s.x", G=F(-1) if False else F(1))
    nl.opamp("s.A", "0", "s.x", "s.o"); nl.R("s.f", "s.x", "s.o", G=F(1))      # s.o = -(r2.o + t) = t^2/2 - t
    nl.R("s.c", "half", "s.x2", G=F(1)); nl.R("s.d", "s.o", "s.x2", G=F(1))
    nl.opamp("s.B", "0", "s.x2", "s.o2"); nl.R("s.f2", "s.x2", "s.o2", G=F(1))  # s.o2 = -(1/2 + t^2/2 - t) = -(t-1)^2/2
    if sign > 0:
        nl.R("s.e", "s.o2", "s.x3", G=F(1)); nl.opamp("s.C", "0", "s.x3", "s.o3"); nl.R("s.f3", "s.x3", "s.o3", G=F(1))
        return "s.o3"
    return "s.o2"


def build(case):
    nl = base()
    if case == "gated_fall":
        o = ramp(nl, "r"); nl.comparator("K", "rail", o, "en"); gated(nl, "en")
    elif case == "gated_rise":
        o = ramp(nl, "r"); nl.comparator("K", o, "rail", "en"); gated(nl, "en")
    elif case == "touch_above":
        y = quad(nl, +1); nl.comparator("K", y, "0", "en"); gated(nl, "en"); nl.counter("cnt", "en", 8, "c")
    elif case == "touch_below":
        y = quad(nl, -1); nl.comparator("K", y, "0", "en"); gated(nl, "en"); nl.counter("cnt", "en", 8, "c")
    elif case == "rise_fall_and":
        o = ramp(nl, "r"); nl.comparator("KA", o, "rail", "a"); nl.comparator("KB", "rail", o, "b")
        nl.gate("g", "AND", ["a", "b"], "ab"); nl.counter("cnt", "ab", 8, "c"); gated(nl, "ab")
    elif case == "self_feedback":
        o = ramp(nl, "r")                                    # o = t
        # y = o - 1 + 2*[switch closed]; switch closed while out is FALSE
        nl.R("f.a", o, "f.x", G=F(1)); nl.R("f.b", "railn", "f.x", G=F(1))
        nl.R("f.c", "rail", "f.n", G=F(2)); nl.switch("f.S", "f.n", "f.x", "en", invert=True)
        nl.opamp("f.A", "0", "f.x", "f.o"); nl.R("f.f", "f.x", "f.o", G=F(1))   # f.o = -(t - 1 + 2*closed)
        nl.R("f.i", "f.o", "f.x2", G=F(1)); nl.opamp("f.B", "0", "f.x2", "f.y"); nl.R("f.g", "f.x2", "f.y", G=F(1))
        nl.comparator("K", "f.y", "0", "en"); gated(nl, "en")
    return nl


EXPECT = {"gated_fall": 1, "gated_rise": 2, "touch_above": 3, "touch_below": 0, "rise_fall_and": 0, "self_feedback": None}


class Timeout(Exception):
    pass


def _alarm(*_):
    raise Timeout()


def run_engine(kind, nl):
    signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(60)
    try:
        if kind == "sim":
            s = Simulator(nl, exact=True, record=False); s.run(F(3))
            q = s.s[s.sidx["Cb"]]
            cnt = s.logic.count_val.get("cnt")
        else:
            h = Hybrid(nl).run(F(3), [])
            q = h.state("Cb")
            cnt = h.logic.count_val.get("cnt")
        return {"charge": str(q), "counter": cnt}
    except Timeout:
        return {"error": "TIMEOUT 60 s"}
    except Exception as e:  # noqa
        return {"error": f"{type(e).__name__}: {str(e)[:160]}"}
    finally:
        signal.alarm(0)


def main():
    out = {}
    for case, exp in EXPECT.items():
        row = {"expected_charge": exp}
        for kind in ("sim", "hybrid"):
            row[kind] = run_engine(kind, build(case))
        signal.signal(signal.SIGALRM, _alarm); signal.alarm(120)
        try:
            v = VSim(build(case).to_json()).run(3)
            row["vsim"] = {"charge": str(v.u[v.net.cidx["Cb"]]), "counter": v.cval.get("cnt")}
        except Timeout:
            row["vsim"] = {"error": "TIMEOUT"}
        except Exception as e:  # noqa
            row["vsim"] = {"error": f"{type(e).__name__}: {str(e)[:160]}"}
        finally:
            signal.alarm(0)
        out[case] = row
        print(case, json.dumps(row), flush=True)
    save("v2_d1_probe.json", out)


if __name__ == "__main__":
    main()
