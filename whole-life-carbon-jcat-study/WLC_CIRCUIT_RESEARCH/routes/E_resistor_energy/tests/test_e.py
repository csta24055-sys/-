"""Route E tests (stdlib unittest; pytest is not installed in math7-py).
Run:  PYTHONDONTWRITEBYTECODE=1 math7-py -B -m unittest discover -s tests -v
(from routes/E_resistor_energy/)
"""
import os, sys, random, unittest
from fractions import Fraction as Fr

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "code"))
import joule as J          # noqa: E402  SymPy analytic oracle
import quad_check as Q     # noqa: E402  mpmath / scipy quadrature oracle
import circuit_e as C      # noqa: E402  E-R1 hybrid realisation
from sympy import Rational, Symbol, sqrt, pi, N, simplify, diff, sin, cos, limit, oo  # noqa: E402
import mpmath as mp        # noqa: E402

CONTRACT = ["0", "1", "9.999999", "10", "10.000001", "19.999999", "20", "20.000001",
            "30", "40", "60"]
EXTRA = ["10.000000005", "10.00000002"]
TOL = 1e-9  # kg


def fr(x):
    x = Rational(x)
    return Fr(int(x.p), int(x.q))


class T0Basics(unittest.TestCase):
    def test_dc_12W_60J(self):
        self.assertEqual(J.power(J.I0), 12)
        self.assertEqual(J.energy(J.I0, 5), 60)
        self.assertEqual(J.to_kg(J.energy(J.I0, 5)), 20)       # only via kappa
        self.assertEqual(J.to_kg(J.energy(J.I0, 5), kappa=Rational(1, 6)), 10)

    def test_units_kappa_required(self):
        from sympy.physics import units as u
        E = 60 * u.joule
        kappa = Rational(1, 3) * u.kilogram / u.joule
        self.assertEqual(u.convert_to(kappa * E, u.kilogram), 20 * u.kilogram)
        # joules are not kilograms: conversion without kappa leaves a non-mass quantity
        self.assertNotEqual(u.convert_to(E, u.kilogram), 60 * u.kilogram)
        # kWh view of the synthetic kappa (shows it is a scaling, not a grid factor)
        self.assertEqual(u.convert_to(kappa * 1000 * u.watt * u.hour, u.kilogram),
                         1200000 * u.kilogram)

    def test_ac_rms2_five_periods_60J(self):
        for phi in (0, pi / 4, Rational(1234, 1000)):
            self.assertEqual(simplify(J.e_ac(5, phi=phi)), 60)              # period 1 s
            self.assertEqual(simplify(J.e_ac(5, phi=phi) - J.e_ac_closed(5, phi=phi)), 0)
            self.assertLess(abs(Q.e_ac_mp(5, phi=mp.mpf(float(phi))) - 60), 1e-25)
            self.assertLess(abs(Q.e_ac_scipy(5, phi=float(phi)) - 60), 1e-9)

    def test_ac_power_vs_energy_and_2w_ripple(self):
        s = J.s
        p = J.power(sqrt(2) * 2 * sin(2 * pi * s))
        self.assertEqual(p.subs(s, 0), 0)                     # instantaneous power 0 ...
        self.assertEqual(p.subs(s, Rational(1, 4)), 24)       # ... to 24 W (2x RMS power)
        t = Symbol("t", positive=True)
        # ripple period is half the current period: E(t+1/2)-E(t)=12*1/2 exactly
        self.assertEqual(simplify(J.e_ac_closed(t + Rational(1, 2)) - J.e_ac_closed(t)), 6)

    def test_resistor_alone_is_not_a_memory(self):
        # E-R0: p(1) == p(30) but G(1) != G(30): cumulative not recoverable from p
        self.assertEqual(C.resistor_only_observable(1), C.resistor_only_observable(30))
        self.assertNotEqual(J.g_dc(1), J.g_dc(30))

    def test_temperature_is_not_cumulative_energy(self):
        th60, th30 = J.thermal_rise(60), J.thermal_rise(30)
        self.assertLess(float(th60), 12)                       # bounded by P*R_th
        self.assertLess(float(th60 - th30), 1e-5)              # saturated
        self.assertEqual(J.energy(J.I0, 60) - J.energy(J.I0, 30), 360)   # energy keeps growing


class T1_HE1(unittest.TestCase):
    def test_contract_points_all_conventions(self):
        # expected side independent of joule.n_events: explicit P0 event list up to t=60
        ev = [(Fr(10 * k), Fr(20)) for k in range(1, 7)] + [(Fr(20 * k), Fr(35)) for k in range(1, 4)]
        eps = Fr(1, 10**9)
        cnt = {"right": lambda tau, t: tau <= t, "left": lambda tau, t: tau < t,
               "orig": lambda tau, t: tau < t * (1 - eps)}
        for t in CONTRACT + EXTRA:
            tf = Fr(t)
            for conv in J.CONVENTIONS:
                exp = 100 + 4 * tf + sum((A for tau, A in ev if cnt[conv](tau, tf)), Fr(0))
                a = J.g_dc(t, conv)
                self.assertEqual(fr(a), exp, (t, conv))
                self.assertEqual(C.g_er1(t, conv), exp, (t, conv))      # exact, Fraction
                self.assertLess(abs(Q.g_dc_mp(t, conv) - mp.mpf(exp.numerator) / exp.denominator),
                                TOL, (t, conv))
                if t not in EXTRA:   # float64 cannot resolve the eps band reliably
                    self.assertLess(abs(Q.g_dc_scipy(t, conv) - float(exp)), TOL, (t, conv))

    def test_declared_table_values(self):
        exp = {"right": [100, 104, "139.999996", 160, "160.000004", "199.999996", 255,
                         "255.000004", 315, 410, 565],
               "left": [100, 104, "139.999996", 140, "160.000004", "199.999996", 200,
                        "255.000004", 295, 355, 510]}
        for conv, vals in exp.items():
            for t, v in zip(CONTRACT, vals):
                self.assertEqual(J.g_dc(t, conv), Rational(str(v)), (t, conv))
        self.assertEqual(J.g_dc("10.000000005", "orig"), Rational("140.00000002"))
        self.assertEqual(J.g_dc("10.000000005", "left"), Rational("160.00000002"))

    def test_left_right_limits_at_events(self):
        h = Fr(1, 10**12)
        for tau, jump in ((10, 20), (20, 55), (40, 55), (30, 20)):
            lft, at, rgt = (C.g_er1(Fr(tau) - h), C.g_er1(Fr(tau)), C.g_er1(Fr(tau) + h))
            self.assertEqual(at - lft, jump + 4 * h)        # right-continuous: jump at tau
            self.assertEqual(rgt - at, 4 * h)

    def test_p1_and_p2(self):
        self.assertEqual([J.p1(t, "substitute") for t in (20, 40)], [250, 405])
        self.assertEqual([J.p1(t, "additional") for t in (20, 40)], [305, 460])
        self.assertEqual(J.p1("19.999999", "additional"), Rational("199.999996"))
        for t, v in ((10, 160), (20, 245), (30, 295), (40, 380), (60, 515)):
            self.assertEqual(J.p2_fixture(t), v)
            self.assertEqual(C.g_er1(t, ef_step=True), v)           # gain-switched integrator


class T2_HE2(unittest.TestCase):
    w = Symbol("w", positive=True)

    def test_symbolic_cross_terms(self):
        w = self.w
        ct = J.cross_terms_kg(w)
        self.assertEqual(simplify(ct["dc_ac_pulse"] - 4 * sqrt(20 * w)), 0)
        self.assertEqual(simplify(ct["dc_pipe_pulse"] - 4 * sqrt(35 * w)), 0)
        self.assertEqual(simplify(ct["simultaneous_ac_pipe"] - 2 * sqrt(20 * 35)), 0)
        self.assertEqual(diff(ct["simultaneous_ac_pipe"], w), 0)    # width independent
        self.assertEqual(ct["simultaneous_ac_pipe"], 20 * sqrt(7))
        # just after the t=20 window (0<w<10): G_single = 255+4w + 2*dcA + dcP + 20 sqrt7
        g = J.g_pulse_single(None, w, after=20)
        exp20 = 255 + 4 * w + 2 * ct["dc_ac_pulse"] + ct["dc_pipe_pulse"] + 20 * sqrt(7)
        self.assertEqual(simplify(g - exp20), 0)
        self.assertEqual(simplify(J.g_pulse_separate(None, w, after=20) - (255 + 4 * w)), 0)
        self.assertEqual(simplify(limit(g, w, 0) - (255 + 20 * sqrt(7))), 0)
        # after t=60+w: three coincidences (20, 40, 60) -> 3*20*sqrt7 = 158.745 kg
        g60 = J.g_pulse_single(None, w, after=60)
        self.assertEqual(simplify(limit(g60, w, 0) - (565 + 60 * sqrt(7))), 0)
        self.assertEqual(simplify(J.g_pulse_separate(None, w, after=60) - (565 + 4 * w)), 0)

    def test_numeric_widths_and_quadrature(self):
        for w in ("1e-6", "1e-4", "1e-2", "1"):
            wr = Rational(w)
            g = N(J.g_pulse_single(None, wr, after=20), 30)
            gq = Q.g_pulse_single_mp(20 + mp.mpf(w), mp.mpf(w))
            self.assertLess(abs(gq - mp.mpf(str(g))), 1e-20, w)
            self.assertLess(abs(Q.g_pulse_separate_mp(20 + mp.mpf(w), mp.mpf(w))
                                - (255 + 4 * mp.mpf(w))), 1e-20, w)
        self.assertLess(abs(N(J.cross_terms_kg(Rational("1e-6"))["dc_ac_pulse"]) - 0.0178885), 1e-6)
        self.assertLess(abs(N(J.cross_terms_kg(Rational("1e-2"))["dc_ac_pulse"]) - 1.788854), 1e-6)
        self.assertLess(abs(N(20 * sqrt(7), 25) - Rational("52.91502622129181181")), 1e-15)

    def test_polarity_counterexample(self):
        wr = Rational(1, 10**6)
        ct = J.cross_terms_kg(wr)
        g = J.g_pulse_single(None, wr, polarity=(1, -1), after=20)
        exp = 255 + 4 * wr + 2 * ct["dc_ac_pulse"] - ct["dc_pipe_pulse"] - 20 * sqrt(7)
        self.assertEqual(simplify(g - exp), 0)
        self.assertLess(float(g), 203)      # same event energies, 202.1 instead of 307.9
        gq = Q.g_pulse_single_mp(20 + mp.mpf("1e-6"), mp.mpf("1e-6"), polarity=(1, -1))
        self.assertLess(abs(gq - mp.mpf(str(N(g, 30)))), 1e-20)

    def test_ac_operating_current_cross(self):
        # with i_op = sqrt2*2 sin(2 pi s), i_op(10)=0: cross is O(w^1.5), not O(w^0.5)
        for w in ("1e-2", "1e-4"):
            c = N(J.ac_operating_cross_kg(Rational(w)), 20)
            self.assertLess(abs(c), 10 * float(Rational(w)) ** 1.5 * 20)
        self.assertGreater(abs(N(J.ac_operating_cross_kg(Rational("1e-2")))), 0)

    def test_finite_pulse_cannot_jump(self):
        # windows [tau, tau+w): at t = tau the pulse has delivered nothing -> left value
        w = mp.mpf("1e-6")
        self.assertLess(abs(Q.g_pulse_separate_mp(10, w) - 140), TOL)    # P0 says 160
        self.assertLess(abs(Q.g_pulse_separate_mp(20, w) - 200), TOL)    # P0 says 255
        self.assertEqual(J.g_pulse_separate(20, Rational(1, 10**6)), 200)
        # separate resistors equal P0 at every contract point outside the windows, and the
        # LEFT-continuous value at event instants 10,20,30,40,60 (a finite pulse cannot jump)
        wr = Rational(1, 10**6)
        for t in CONTRACT:
            conv = "left" if t in ("10", "20", "30", "40", "60") else "right"
            a = J.p0_fixture(t, conv)
            self.assertLess(abs(Q.g_pulse_separate_mp(t, w) - mp.mpf(a.p) / a.q), TOL, t)
            self.assertEqual(J.g_pulse_separate(t, wr), a, t)
        a = J.p0_fixture("20.000001")
        self.assertGreater(Q.g_pulse_single_mp("20.000001", w) - mp.mpf(a.p) / a.q, 52.9)


class T3_HE3(unittest.TestCase):
    def test_lattice_exact(self):
        for k in range(0, 241):
            t = Rational(k, 4)
            self.assertEqual(simplify(J.to_kg(J.e_ac_closed(t)) - 4 * t), 0, t)
        on = [t for t in CONTRACT if (Rational(t) * 4).is_integer]
        self.assertEqual(len(on), 7)
        for t in on:
            self.assertEqual(simplify(J.to_kg(J.e_ac(Rational(t))) + J.G0
                                      + J.event_sum(Rational(t), "right") - J.p0_fixture(t)), 0)

    def test_off_lattice_contract_points(self):
        exp = {"9.999999": +4e-6, "10.000001": -4e-6, "19.999999": +4e-6, "20.000001": -4e-6}
        for t, e in exp.items():
            tr = Rational(t)
            err_sym = N(J.to_kg(J.e_ac(tr)) - 4 * tr, 30)
            err_q = Q.e_ac_mp(t) / 3 - 4 * mp.mpf(t)
            self.assertLess(abs(err_sym - e), 1e-15, t)        # 4e-6 - O(1e-16)
            self.assertLess(abs(err_q - mp.mpf(str(err_sym))), 1e-25, t)
            self.assertGreater(abs(err_sym), TOL)              # fails the 1e-9 H-E1 gate

    def test_bound_and_tightness(self):
        """Numerical search over t and phi with SciPy quadrature (not the closed form):
        sup_t |kappa E - 4t| must equal 4(1+|sin 2phi|)/(2 omega); global sup 4/omega."""
        import math
        from scipy.optimize import minimize_scalar
        for om in (2 * math.pi, 3.0):
            per = math.pi / om                     # ripple period
            t0 = 37.0
            glob = 0.0
            for j in range(24):
                phi = math.pi * j / 24
                E0 = Q.e_ac_scipy(t0, omega=om, phi=phi)
                f = lambda t: (E0 + Q.squad(lambda x: 3 * (2 * math.sqrt(2) * math.sin(om * x + phi)) ** 2,
                                            t0, t, epsabs=1e-13, epsrel=1e-13)[0]) / 3 - 4 * t
                grid = [t0 + per * k / 60 for k in range(61)]
                vals = [abs(f(t)) for t in grid]
                k = max(range(61), key=vals.__getitem__)
                lo, hi = grid[max(k - 1, 0)], grid[min(k + 1, 60)]
                r = minimize_scalar(lambda t: -abs(f(t)), bounds=(lo, hi), method="bounded",
                                    options=dict(xatol=1e-12))
                best = max(vals[k], -r.fun)
                bound = 4 * (1 + abs(math.sin(2 * phi))) / (2 * om)
                self.assertLessEqual(best, bound + 1e-9, (om, phi))
                self.assertGreater(best, bound - 1e-8, (om, phi))   # attained
                glob = max(glob, best)
            self.assertLessEqual(glob, 4 / om + 1e-9)
            self.assertGreater(glob, 4 / om * 0.99)                  # phi near pi/4 on the grid
        # exact attainment phi=0 at t=3/8: error = r/(2 omega) = 1/pi, checked by mpmath quad
        self.assertLess(abs(Q.e_ac_mp(mp.mpf(3) / 8) / 3 - mp.mpf(3) / 2 - 1 / mp.pi), 1e-30)

    def test_full_periods_any_phase(self):
        for phi in (0, Rational(1, 3), pi / 4):
            for n in (1, 7, 60):
                self.assertEqual(simplify(J.e_ac_closed(n, phi=phi)), 12 * n)


class T4_HE4(unittest.TestCase):
    def test_convert_then_integrate_vs_meter_then_convert(self):
        rows = {"9.999999": (Rational("39.999996"),) * 3,
                "10": (40, 30, 40), "20": (70, 60, 80), "60": (190, 180, 240)}
        for t, (good, cur, ini) in rows.items():
            self.assertEqual(J.op_convert_then_integrate(t), good, t)
            self.assertEqual(J.op_meter_then_convert(t, "current"), cur, t)
            self.assertEqual(J.op_meter_then_convert(t, "initial"), ini, t)
            self.assertLess(abs(Q.op_convert_then_integrate_mp(t) - mp.mpf(str(N(good, 30)))), TOL)
            self.assertLess(abs(Q.op_meter_then_convert_mp(t) - mp.mpf(str(N(cur, 30)))), TOL)
        # meter-then-convert makes cumulative carbon DECREASE at t=10 (39.999996 -> 30)
        self.assertGreater(J.op_meter_then_convert("9.999999"), J.op_meter_then_convert("10"))
        # full G: P2 vs wrong readout
        for t, v in ((10, 160), (20, 245), (60, 515)):
            wrong = 100 + J.op_meter_then_convert(t) + J.event_sum(Rational(t), "right")
            self.assertEqual(J.p2_fixture(t) - wrong, 10)


class T5_DPass1(unittest.TestCase):
    """Fixes requested by route D pass 1 (items 1-4)."""

    def test_event_cross_term_is_2sqrtAA_rho(self):
        w = Rational(1, 100)
        rect, nz = J.rect, J.normalize
        cases = {  # name: (shape_a, support_a, shape_b, support_b, expected rho)
            "equal_aligned": (rect(20, 20 + w), (20, 20 + w), rect(20, 20 + w), (20, 20 + w), 1),
            "widths_w_4w": (rect(20, 20 + w), (20, 20 + w), rect(20, 20 + 4 * w), (20, 20 + 4 * w), Rational(1, 2)),
            "half_overlap": (rect(20, 20 + w), (20, 20 + w), rect(20 + w / 2, 20 + 3 * w / 2), (20 + w / 2, 20 + 3 * w / 2), Rational(1, 2)),
            "widths_w_9w": (rect(20, 20 + w), (20, 20 + w), rect(20, 20 + 9 * w), (20, 20 + 9 * w), Rational(1, 3)),
            "interleaved": (rect(20, 20 + w), (20, 20 + w), rect(20 + w, 20 + 2 * w), (20 + w, 20 + 2 * w), 0),
            "walsh_pair": (J.walsh(20, w, J.WALSH_AC), (20, 20 + w), J.walsh(20, w, J.WALSH_PIPE), (20, 20 + w), 0),
            "walsh_vs_rect": (J.walsh(20, w, J.WALSH_AC), (20, 20 + w), rect(20, 20 + w), (20, 20 + w), 0),
            "rect_vs_half_walsh": (rect(20, 20 + w), (20, 20 + w), J.walsh(20, w, (1, 1, 1, -1)), (20, 20 + w), Rational(1, 2)),
        }
        lo, hi = 19, 21
        for name, (fa, sa, fb, sb, r_exp) in cases.items():
            ia, ib = nz(fa, 20, *sa), nz(fb, 35, *sb)
            r = J.rho(fa, fb, lo, hi)
            self.assertEqual(simplify(r - r_exp), 0, name)
            c = J.cross_kg_shapes(ia, ib, lo, hi)
            self.assertEqual(simplify(c - 2 * sqrt(20 * 35) * r_exp), 0, name)
            self.assertLessEqual(float(abs(c)), float(20 * sqrt(7)) + 1e-12, name)   # Cauchy-Schwarz
            # independent quadrature on the same configuration
            def pcs(shape_sa):
                f, (a, b) = shape_sa
                n = 40
                pts = [a + (b - a) * Rational(k, n) for k in range(n + 1)]
                return [(float(pts[k]), float(pts[k + 1]), float(f.subs(J.s, (pts[k] + pts[k + 1]) / 2)))
                        for k in range(n)]
            pa, pb = Q.norm_pieces(pcs((fa, sa)), 20), Q.norm_pieces(pcs((fb, sb)), 35)
            cq = Q.shared_kg_mp([pa, pb], lo, hi) - Q.separate_kg_mp([pa, pb], lo, hi)
            self.assertLess(abs(cq - mp.mpf(str(N(c, 30)))), 1e-9, name)
        self.assertEqual(simplify(2 * sqrt(700) * Rational(1, 2) - sqrt(700)), 0)   # 26.4575

    def test_shared_resistor_walsh_and_interleaved(self):
        w = Rational(1, 100)
        dc = J.rect(0, 61, J.I0)
        # Walsh-orthogonal zero-mean pulses at t=20 on ONE resistor: window energy 4w+55
        ia = J.normalize(J.walsh(20, w, J.WALSH_AC), 20, 20, 20 + w)
        ib = J.normalize(J.walsh(20, w, J.WALSH_PIPE), 35, 20, 20 + w)
        self.assertEqual(J.shared_resistor_kg([dc, ia, ib], 20, 20 + w), 4 * w + 55)
        pa = Q.norm_pieces(Q.walsh_pieces(20, "0.01", J.WALSH_AC), 20)
        pb = Q.norm_pieces(Q.walsh_pieces(20, "0.01", J.WALSH_PIPE), 35)
        pdc = [(mp.mpf(0), mp.mpf(61), mp.mpf(2))]
        self.assertLess(abs(Q.shared_kg_mp([pdc, pa, pb], 20, mp.mpf("20.01")) - (mp.mpf("0.04") + 55)), 1e-25)
        self.assertEqual(Q.charge_mp(pa, 20, 21), 0)          # zero net charge: invisible to route A
        # whole P0 with Walsh pulses on one resistor: exact at every readout outside windows
        comps = J.p0_walsh_components(w)
        for t, conv in ((Rational(5), "right"), (20 + w, "right"), (Rational(30) - w, "right"),
                        (60 + w, "right")):
            g = J.G0 + J.shared_resistor_kg(comps, 0, t)
            self.assertEqual(g, J.p0_fixture(t, conv), t)
        # ... but NOT inside a window (orthogonality holds only over the whole window)
        t_in = 20 + w / 4
        g_in = J.G0 + J.shared_resistor_kg(comps, 0, t_in)
        sep_in = J.G0 + J.separate_kg(comps, 0, t_in)
        self.assertNotEqual(simplify(g_in - sep_in), 0)
        # time-interleaved rectangular pulses: event x event term 0, DC x pulse remains
        ra = J.normalize(J.rect(20, 20 + w), 20, 20, 20 + w)
        rb = J.normalize(J.rect(20 + w, 20 + 2 * w), 35, 20 + w, 20 + 2 * w)
        self.assertEqual(J.cross_kg_shapes(ra, rb, 19, 21), 0)
        dcx = J.shared_resistor_kg([dc, ra, rb], 19, 21) - J.separate_kg([dc, ra, rb], 19, 21)
        self.assertEqual(simplify(dcx - 4 * sqrt(20 * w) - 4 * sqrt(35 * w)), 0)
        # orthogonality is w.r.t. the ACTUAL operating current: AC op current breaks it
        iop = sqrt(2) * J.I0 * sin(2 * pi * J.s)
        c_ac = J.cross_kg_shapes(iop, ia, 20, 20 + w)
        self.assertNotEqual(simplify(c_ac), 0)
        self.assertLess(abs(float(c_ac)), 0.1)                 # 0.0397 kg at w=0.01

    def test_p1_event_driven_circuit(self):
        ts = CONTRACT + EXTRA + ["20.00000001", "20.00000002"]
        for pol in ("substitute", "additional"):
            amt = Fr(-5) if pol == "substitute" else Fr(50)
            for conv in J.CONVENTIONS:
                for t in ts:
                    a = J.p1(t, pol, conv)
                    self.assertEqual(C.g_er1(t, conv, p1=pol), fr(a), (pol, conv, t))
            self.assertEqual([C.g_er1(t, p1=pol) for t in (20, 40)],
                             [255 + amt, 410 + amt])
        self.assertEqual(C.ER1.STATES_P1, (4, 0, 3, 1))

    def test_true_fixed_step_misses_events(self):
        qs = CONTRACT
        exact = {t: float(J.p0_fixture(t)) for t in qs}
        for dt in (1e-2, 1e-3):
            out = Q.fixed_step_true(dt, qs)
            errs = {t: abs(out[t] - exact[t]) for t in qs}
            self.assertGreater(max(errs.values()), 19.9)          # a full event charge
            self.assertAlmostEqual(out["10"], 140.0, delta=1e-6)   # G(10)=140, not 160


if __name__ == "__main__":
    unittest.main(verbosity=2)
