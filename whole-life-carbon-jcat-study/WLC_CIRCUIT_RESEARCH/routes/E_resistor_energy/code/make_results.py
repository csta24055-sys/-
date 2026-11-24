"""Write results/points.json, results/e_numbers.json, results/benchmark.json.
Run from routes/E_resistor_energy:  PYTHONDONTWRITEBYTECODE=1 math7-py -B code/make_results.py
"""
import json, os, platform, random, statistics, sys, time, tracemalloc
from fractions import Fraction as Fr

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import joule as J, quad_check as Q, circuit_e as C   # noqa: E402
import mpmath as mp                                    # noqa: E402
from sympy import Rational, N, sqrt, Symbol, simplify, limit  # noqa: E402

OUT = os.path.join(HERE, "..", "results")
CONTRACT = ["0", "1", "9.999999", "10", "10.000001", "19.999999", "20", "20.000001",
            "30", "40", "60"]
EXTRA = ["10.000000005", "10.00000002"]


def q(x):
    x = Rational(x)
    return f"{x.p}/{x.q}"


def points():
    pts = []
    for conv in J.CONVENTIONS:
        for t in CONTRACT + EXTRA:
            a = J.g_dc(t, conv)
            h = C.g_er1(t, conv)
            assert Fr(int(a.p), int(a.q)) == h and a == J.p0_fixture(t, conv)
            pts.append(dict(case="P0", convention=conv, t=t, value=q(a), realization="E-R1",
                            states=list(C.ER1.STATES_SEPARATE),
                            checks=dict(sympy_eq_hybrid_fraction=True, eq_fixture=True,
                                        mpmath_abs_err=float(abs(Q.g_dc_mp(t, conv) - mp.mpf(a.p) / a.q)))))
    for pol in ("substitute", "additional"):
        for t in CONTRACT:
            pts.append(dict(case=f"P1-{pol}", convention="right", t=t, value=q(J.p1(t, pol)),
                            realization="E-R1 + one-shot external addition at t=20",
                            states=[4, 0, 3, 0]))
    for t in CONTRACT:
        v = J.p2_fixture(t)
        assert Fr(int(v.p), int(v.q)) == C.g_er1(t, ef_step=True)
        pts.append(dict(case="P2", convention="right", t=t, value=q(v),
                        realization="E-R1 with EF gain switch (convert-then-integrate)",
                        states=list(C.ER1.STATES_EF_SWITCH)))
    for t in CONTRACT:   # AC realisation of P0 (omega=2pi/yr, phi=0, Irms=2)
        tr = Rational(t)
        g = J.G0 + J.to_kg(J.e_ac_closed(tr)) + J.event_sum(tr, "right")
        exact = simplify(g - J.p0_fixture(t)) == 0
        pts.append(dict(case="P0-AC", convention="right", t=t,
                        value=q(J.p0_fixture(t)) if exact else None,
                        value_decimal=str(N(g, 25)), dev_from_P0_kg=str(N(g - J.p0_fixture(t), 6)),
                        realization="E-R1 with AC source sqrt2*2*sin(2*pi*t)", states=[4, 0, 2, 0],
                        note="source oscillator external; +2 continuous states if internal"))
    return pts


def numbers():
    w = Symbol("w", positive=True)
    ct = J.cross_terms_kg(w)
    tab = []
    for ws in ("1e-6", "1e-4", "1e-2", "1"):
        wr = Rational(ws)
        tab.append(dict(w=ws, dc_ac_pulse_kg=str(N(ct["dc_ac_pulse"].subs(w, wr), 12)),
                        dc_pipe_pulse_kg=str(N(ct["dc_pipe_pulse"].subs(w, wr), 12)),
                        simultaneous_kg=str(N(ct["simultaneous_ac_pipe"], 15)),
                        G_single_after20=str(N(J.g_pulse_single(None, wr, after=20), 15)),
                        G_single_after20_mpquad=mp.nstr(Q.g_pulse_single_mp(20 + mp.mpf(ws), mp.mpf(ws)), 15),
                        G_separate_after20=str(N(J.g_pulse_separate(None, wr, after=20), 15)),
                        G_single_after60=str(N(J.g_pulse_single(None, wr, after=60), 15)),
                        G_single_after20_reversed_pipe=str(N(J.g_pulse_single(None, wr, (1, -1), after=20), 15)),
                        ac_operating_cross_t10_kg=str(N(J.ac_operating_cross_kg(wr), 6))))
    ac = {}
    for t in ("9.999999", "10", "10.000001", "19.999999", "20.000001", "0.375"):
        tr = Rational(t)
        ac[t] = dict(sympy=str(N(J.to_kg(J.e_ac(tr)) - 4 * tr, 20)),
                     mpquad=mp.nstr(Q.e_ac_mp(t) / 3 - 4 * mp.mpf(t), 20))
    ef = {t: dict(convert_then_integrate=str(J.op_convert_then_integrate(t)),
                  meter_then_convert_current=str(J.op_meter_then_convert(t, "current")),
                  meter_then_convert_initial=str(J.op_meter_then_convert(t, "initial")))
          for t in ("9.999999", "10", "20", "40", "60")}
    return dict(
        basics=dict(P_W=str(J.power(J.I0)), E_5s_J=str(J.energy(J.I0, 5)),
                    ac_5periods_J=str(J.e_ac(5)), kappa_kg_per_J="1/3",
                    kappa_kg_per_kWh="1200000 (synthetic scaling only)"),
        HE2=dict(symbolic={k: str(v) for k, v in ct.items()},
                 limit_w0_after20=str(limit(J.g_pulse_single(None, w, after=20), w, 0)),
                 limit_w0_after60=str(simplify(limit(J.g_pulse_single(None, w, after=60), w, 0))),
                 widths=tab),
        HE3=dict(kappaE_minus_4t_kg=ac,
                 bound="sup_t |kappaE-4t| = 4(1+|sin2phi|)/(2omega) <= 4/omega; phi=0: 1/pi=0.318310 at t=3/8",
                 lattice_phi0="t in Z/4 (omega=2pi)"),
        HE4=ef,
        thermal=dict(theta60=str(N(J.thermal_rise(60), 15)), E60_J="720"))


# ---------------------------- benchmark --------------------------------------------
def closed_form(t):
    return 100 + 4 * t + 20 * (t // 10) + 35 * (t // 20)


def hybrid_per_query(t):
    return C.ER1().run_to(t)


def hybrid_sweep(ts):
    m = C.ER1(); out = []
    for t in sorted(ts):
        out.append(m.run_to(t))
    return out


def fixed_step(t, dt=1e-3):
    n = int(t / dt); E = 0.0; G = 100.0
    for k in range(n):
        E += 12.0 * dt
    ev = 20 * int(n * dt // 10 + 1e-12) + 35 * int(n * dt // 20 + 1e-12)
    return G + E / 3.0 + ev + 4.0 * (t - n * dt)


def bench():
    rng = random.Random(12345)
    ts = [Fr(rng.randrange(0, 60_000_000), 1_000_000) for _ in range(1000)]
    tf = [float(t) for t in ts]
    meth = {"closed_form_Fraction": lambda: [closed_form(t) for t in ts],
            "ER1_hybrid_per_query": lambda: [hybrid_per_query(t) for t in ts],
            "ER1_hybrid_sorted_sweep": lambda: hybrid_sweep(ts),
            "fixed_step_dt1e-3_float(100 pts)": lambda: [fixed_step(t) for t in tf[:100]]}
    res = {}
    ref = [closed_form(t) for t in ts]
    assert [hybrid_per_query(t) for t in ts] == ref and hybrid_sweep(ts) == sorted(ref)
    for name, f in meth.items():
        times = []
        for _ in range(5):
            t0 = time.perf_counter(); f(); times.append(time.perf_counter() - t0)
        tracemalloc.start(); f(); peak = tracemalloc.get_traced_memory()[1]; tracemalloc.stop()
        res[name] = dict(median_s=statistics.median(times), peak_bytes=peak)
    errs = [abs(fixed_step(t) - float(closed_form(Fr(t)))) for t in tf[:100]]
    res["fixed_step_dt1e-3_float(100 pts)"]["max_abs_err_kg"] = max(errs)
    res["exact_agreement_hybrid_vs_closed_form"] = all(hybrid_per_query(t) == closed_form(t) for t in ts)
    res["states"] = {"closed_form": "(0,0,0,0) + formula", "ER1_separate": [4, 0, 2, 0],
                     "ER1_merged_register": [3, 0, 2, 0], "table_driven_H60": [1, 1, 1, 6]}
    res["env"] = dict(python=sys.version.split()[0], machine=platform.machine(),
                      platform=platform.platform(), seed=12345, n_points=1000)
    return res


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    json.dump(points(), open(os.path.join(OUT, "points.json"), "w"), indent=1)
    json.dump(numbers(), open(os.path.join(OUT, "e_numbers.json"), "w"), indent=1)
    json.dump(bench(), open(os.path.join(OUT, "benchmark.json"), "w"), indent=1)
    print("wrote", OUT)
