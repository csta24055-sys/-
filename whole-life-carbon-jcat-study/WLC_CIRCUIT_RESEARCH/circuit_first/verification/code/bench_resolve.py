"""V1 independent re-solution of CF1 benches and the comparator-falling counterexample.

* exact benches: the dumped netlists are re-simulated with the verifier's own `vsim`
  (charge sharing, SC packet, integrate-and-fire with non-integer periods);
* float benches (RC charge, charge sharing through R, AC energy, series RLC): independent
  numerical integration of the ODE with mpmath (Taylor ODE solver + quadrature, 30 digits),
  NOT the closed forms used in the builder's tests;
* the engine defect probe: comparator output must fall when its input crosses 0 downwards.
Run with math7-py (mpmath, sympy).
"""
from __future__ import annotations

import json
import os
from fractions import Fraction as Fr

import mpmath as mp

from common import SNAP, builder, fstr, save
from vsim import VSim, num

mp.mp.dps = 30
RES = os.path.join(SNAP, "results")


def load(name):
    return json.load(open(os.path.join(RES, name)))


def exact_benches():
    out = {}
    # charge sharing, ideal switch
    d = load("bench_charge_sharing_ideal.json")
    s = VSim(d["dump"]["netlist"]).run(1)
    j = [x for x in s.jumps if x["reason"] != "init"]
    out["charge_sharing_ideal"] = {
        "u_final": {k: fstr(v) for k, v in zip([c["name"] for c in s.net.caps], s.u)},
        "expected_v": "2", "verifier_impulsive_loss": fstr(j[0]["impulsive_loss"]) if j else None,
        "expected_loss": "15", "engine_loss": d["energy_lost"],
        "pass": s.u == [Fr(2), Fr(2)] and j and j[0]["impulsive_loss"] == 15}
    # SC packet
    d = load("bench_sc_packet.json")
    s = VSim(d["dump"]["netlist"]).run(5)
    cb = s.u[s.net.cidx["Cb"]]
    loss = sum((x["impulsive_loss"] for x in s.jumps if x.get("impulsive_loss") is not None), Fr(0))
    # rail energy: work delivered by V0 (absorbed = V*Q, delivered = -absorbed)
    rail = -sum((num(s.net.by["V0"]["V"]) * x["Q"].get("V0", 0) for x in s.jumps), Fr(0))
    out["sc_packet"] = {"q_bus": fstr(cb * 1), "expected_q_bus": "15", "engine_q_bus": d["q_bus"],
                        "rail_energy_verifier": fstr(rail), "expected_rail_energy": "30",
                        "total_impulsive_loss_verifier_incl_reset_packets": fstr(loss),
                        "pass": cb == 15 and rail == 30}
    # integrate-and-fire (non-integer periods, coincident firing as a set)
    d = load("bench_integrate_and_fire.json")
    s = VSim(d["dump"]["netlist"]).run(10)
    fires = {}
    for t, k, n, v in s.events:
        if k == "cmp" and v and n.endswith(".cmp"):
            fires.setdefault(n[0], []).append(t)
    exp = {"a": [Fr(7, 10) * j for j in range(1, 15)], "b": [Fr(7, 5) * j for j in range(1, 8)],
           "c": [Fr(10, 3) * j for j in range(1, 4)]}
    # ramps after every reset: the post-instant state of each clock integrator is exactly 0
    zero_after_reset = True
    for t, u in s.instant_states:
        for nm in ("a", "b", "c"):
            if t in exp[nm] and u[s.net.cidx[f"{nm}.Cj"]] != 0:
                zero_after_reset = False
    out["integrate_and_fire"] = {"fires_match": fires == exp, "counter_coincidences": s.cval.get("cnt"),
                                 "ramp_exactly_zero_after_each_reset": zero_after_reset,
                                 "engine_fires": d["fires"], "pass": fires == exp and s.cval.get("cnt") == 7 and zero_after_reset}
    return out


def rk_ode(f, y0, T):
    sol = mp.odefun(f, 0, y0)
    return sol(T)


def float_benches():
    out = {}
    # RC charge with heat: dv/dt = (V - v)/(R C); heat = int (V - v)^2 / R dt
    d = load("bench_rc_charge.json")
    V, R, C = mp.mpf(5), mp.mpf(2), mp.mpf("0.5")
    rows = {}
    worst = mp.mpf(0)
    for T, rec in d["results"].items():
        T = mp.mpf(T)
        f = lambda t, y: [(V - y[0]) / (R * C), (V - y[0]) ** 2 / R]
        v, heat = rk_ode(f, [mp.mpf(0), mp.mpf(0)], T)
        e1 = abs(v - rec["v_C"]); e2 = abs(heat - rec["heat"])
        worst = max(worst, e1, e2)
        rows[str(T)] = {"v_ode": float(v), "v_engine": rec["v_C"], "heat_ode": float(heat), "heat_engine": rec["heat"]}
    out["rc_charge"] = {"rows": rows, "max_abs_dev": float(worst), "pass": worst < 1e-10}
    # charge sharing through R (heat -> C1C2/(C1+C2) V1^2/2)
    d = load("bench_charge_sharing_R.json")
    C1, V1, C2, R = mp.mpf(2), mp.mpf(5), mp.mpf(3), mp.mpf("0.7")
    worst = mp.mpf(0)
    rows = {}
    for T, h in d["heat"].items():
        f = lambda t, y: [-(y[0] - y[1]) / (R * C1), (y[0] - y[1]) / (R * C2), (y[0] - y[1]) ** 2 / R]
        a, b, heat = rk_ode(f, [V1, mp.mpf(0), mp.mpf(0)], mp.mpf(T))
        worst = max(worst, abs(heat - h))
        rows[T] = {"heat_ode": float(heat), "heat_engine": h}
    out["charge_sharing_R"] = {"rows": rows, "max_abs_dev": float(worst), "pass": worst < 1e-10}
    # AC energy: LC tank, i = sqrt(C/L) sin(w t), E_R = int i^2 R dt
    d = load("bench_ac_energy.json")
    Ct, Lt, R = mp.mpf(1), mp.mpf("0.25"), mp.mpf(3)
    worst = mp.mpf(0)
    rows = {}
    for T, rec in d["results"].items():
        f = lambda t, y: [-y[1] / Ct, y[0] / Lt, y[1] ** 2 * R]   # vC, iL, energy
        vc, il, e = rk_ode(f, [mp.mpf(1), mp.mpf(0), mp.mpf(0)], mp.mpf(T))
        worst = max(worst, abs(e - rec["E_R"]))
        rows[T] = {"E_ode": float(e), "E_engine": rec["E_R"]}
    out["ac_energy"] = {"rows": rows, "max_abs_dev": float(worst), "pass": worst < 1e-9}
    # series RLC (S3): q'' = (V - R q' - q/C)/L
    d = load("bench_series_rlc.json")
    V, R, L, C = mp.mpf(1), mp.mpf(1), mp.mpf(1), mp.mpf("0.25")
    worst = mp.mpf(0)
    rows = {}
    for T, rec in d["results"].items():
        f = lambda t, y: [y[1], (V - R * y[1] - y[0] / C) / L, R * y[1] ** 2]
        q, i, heat = rk_ode(f, [mp.mpf(0), mp.mpf(0), mp.mpf(0)], mp.mpf(T))
        worst = max(worst, abs(q - rec["q"]), abs(heat - rec["heat"]))
        rows[T] = {"q_ode": float(q), "q_engine": rec["q"], "heat_ode": float(heat), "heat_engine": rec["heat"]}
    out["series_rlc"] = {"rows": rows, "max_abs_dev": float(worst), "pass": worst < 1e-10}
    return out


def falling_comparator_probe():
    """Engine defect probe. Ramp o = t; en = [1 - o >= 0] closes a switch feeding an integrator
    from a 1 V rail through 1 S. Correct charge at T = 3 is 1 (en falls at t = 1)."""
    model, adapter = builder()
    from engine import Netlist, Simulator  # snapshot engine, used only as the system under test

    def build(falling):
        nl = Netlist()
        nl.V("V1", "rail", "0", Fr(1)); nl.V("Vn", "railn", "0", Fr(-1))
        nl.R("Gr", "railn", "x", G=Fr(1)); nl.opamp("A", "0", "x", "o"); nl.C("Cr", "x", "o", Fr(1))
        if falling:
            nl.comparator("K", "rail", "o", "en")
        else:
            nl.comparator("K", "o", "rail", "en")
        nl.R("Gb", "rail", "s", G=Fr(1)); nl.switch("S", "s", "xb", "en")
        nl.opamp("B", "0", "xb", "ob"); nl.C("Cb", "xb", "ob", Fr(1))
        return nl
    res = {}
    for falling in (True, False):
        nl = build(falling)
        sim = Simulator(nl, exact=True, record=False)
        sim.run(Fr(3))
        eng = sim.s[sim.sidx["Cb"]]
        vs = VSim(nl.to_json()).run(3)
        mine = vs.u[vs.net.cidx["Cb"]]
        res["falling" if falling else "rising"] = {
            "expected": 1 if falling else 2, "engine": fstr(eng), "verifier_vsim": fstr(mine),
            "engine_cmp_events": [(e["t"], e["value"]) for e in sim.sol.events if e["type"] == "cmp"],
            "engine_correct": eng == (1 if falling else 2), "vsim_correct": mine == (1 if falling else 2)}
    return res


def main():
    out = {"exact": exact_benches(), "float": float_benches(), "falling_comparator_probe": falling_comparator_probe()}
    save("bench_resolve.json", out)
    return out


if __name__ == "__main__":
    print(json.dumps(main(), indent=1, default=str)[:6000])
