"""Route A tests. Run (from anywhere):
  PYTHONDONTWRITEBYTECODE=1 python3 -B <route>/tests/test_a.py -v
Stdlib only, no network. Expected values below are this route's OWN hand derivations
(written as explicit arithmetic), not copies of architecture.md.
"""
import math
import os
import random
import sys
import unittest
from fractions import Fraction as F

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "code"))
sys.dont_write_bytecode = True

import p0_oracle as O          # noqa: E402
import circuit_a as C          # noqa: E402

R, L, OR = O.RIGHT, O.LEFT, O.ORIG
D = F(1, 10**12)   # exact rational offset for left/right limits

# Hand derivations: G = 100 + 4t + 20 nA + 35 nP
HAND = {
    R:  {"0": 100, "1": 104, "9.999999": F("139.999996"), "10": 100 + 40 + 20,
         "10.000001": F("160.000004"), "19.999999": F("199.999996"),
         "20": 100 + 80 + 40 + 35, "20.000001": F("255.000004"),
         "30": 100 + 120 + 60 + 35, "40": 100 + 160 + 80 + 70, "60": 100 + 240 + 120 + 105},
    L:  {"10": 100 + 40, "20": 100 + 80 + 20, "30": 100 + 120 + 40 + 35,
         "40": 100 + 160 + 60 + 35, "60": 100 + 240 + 100 + 70},
}
# knife points: 10.000000005*(1-1e-9) = 9.999999995... < 10  -> ORIG excludes the t=10 event
#               10.00000002 *(1-1e-9) = 10.00000000999999998 > 10 -> ORIG includes it
HAND_KNIFE = {
    ("10.000000005", R): F("160.00000002"), ("10.000000005", L): F("160.00000002"),
    ("10.000000005", OR): F("140.00000002"),
    ("10.00000002", R): F("160.00000008"), ("10.00000002", L): F("160.00000008"),
    ("10.00000002", OR): F("160.00000008"),
}
EVENT_TIMES = [10, 20, 30, 40, 60]


def hand(conv, t):
    if conv in HAND and t in HAND[conv]:
        return F(HAND[conv][t])
    if conv == OR and t in HAND[L]:      # integer event times: ORIG == LEFT there
        return F(HAND[L][t])
    return F(HAND[R][t])                 # non-event points agree in all conventions


class HA1_Exact(unittest.TestCase):
    """H-A1: R1 == oracle == hand, exactly, 3 conventions."""

    def test_contract_points_all_conventions(self):
        for conv in O.CONVENTIONS:
            c = C.p0_r1(conv)
            for t in O.CONTRACT_POINTS:
                with self.subTest(conv=conv, t=t):
                    self.assertEqual(O.g_p0(F(t), conv), hand(conv, t))
                    self.assertEqual(c.G(F(t)), hand(conv, t))

    def test_limits_at_event_times(self):
        for conv in (R, L):
            c = C.p0_r1(conv)
            for tau in EVENT_TIMES:
                tau = F(tau)
                left_lim = O.g_p0(tau, L)          # value of the left-continuous version
                right_lim = O.g_p0(tau, R)
                with self.subTest(conv=conv, tau=tau):
                    self.assertEqual(c.G(tau - D), left_lim - 4 * D)
                    self.assertEqual(c.G(tau + D), right_lim + 4 * D)
                    self.assertEqual(c.G(tau), right_lim if conv == R else left_lim)
                    # jump size = sum of charges firing at tau
                    jump = 20 * (tau % 10 == 0) + 35 * (tau % 20 == 0)
                    self.assertEqual(right_lim - left_lim, jump)

    def test_reset_semantics(self):
        """right: x=0 at tau; left: x=1 held at tau; orig: x<1 just after tau."""
        self.assertEqual(C.p0_r1(R).run(10)["x"]["A"], 0)
        self.assertEqual(C.p0_r1(L).run(10)["x"]["A"], 1)
        xo = C.p0_r1(OR).run(10)["x"]["A"]
        self.assertEqual(xo, 1 - F(1, 10**9))
        # ORIG clock reaches 1 at 10/(1-eps): band [10, 10/(1-eps))
        band_end = F(10) / (1 - O.EPS)
        self.assertEqual(C.p0_r1(OR).G(band_end), 100 + 4 * band_end)          # held, not counted
        self.assertEqual(O.g_p0(band_end, OR), 100 + 4 * band_end)
        self.assertEqual(C.p0_r1(OR).G(band_end + D), 100 + 4 * (band_end + D) + 20)

    def test_knife_points_exact(self):
        for (t, conv), v in HAND_KNIFE.items():
            with self.subTest(t=t, conv=conv):
                self.assertEqual(O.g_p0(F(t), conv), v)
                self.assertEqual(C.p0_r1(conv).G(F(t)), v)

    def test_float_knife(self):
        """float agrees with exact at the two chosen points; 10.00000001 is the
        real-vs-float knife edge: recorded, the float result is NOT asserted."""
        for (t, conv), v in HAND_KNIFE.items():
            with self.subTest(t=t, conv=conv):
                self.assertAlmostEqual(O.g_p0_float(float(t), conv), float(v), delta=1e-9)
        exact = O.g_p0(F(O.KNIFE_EDGE_UNDEFINED), OR)
        self.assertEqual(exact, F("140.00000004"))   # reals: 10.00000001(1-1e-9) < 10

    def test_scale_invariance_and_separation(self):
        """G readout invariant in (gamma, C_cap); V, P_in, E_cap are not carbon."""
        for t in ["9.999999", "20", "60"]:
            a = C.p0_r1(R, gamma=1, C_cap=1).run(F(t))
            b = C.p0_r1(R, gamma=5, C_cap=2).run(F(t))
            self.assertEqual(a["G"], b["G"])
            self.assertEqual(b["Q"], a["G"] / 5)
            self.assertEqual(b["V"], a["G"] / 10)
            self.assertEqual(b["I"], F(4, 5))
            self.assertNotEqual(a["E_cap"] / b["E_cap"], 1)
        a = C.p0_r1(R).run(60)
        self.assertEqual((a["Q"], a["V"], a["I"], a["P_in"], a["E_cap"]),
                         (565, 565, 4, 2260, F(565**2, 2)))
        # E_cap is quadratic: E(60)/E(30) != G(60)/G(30)
        e30 = C.p0_r1(R).run(30)["E_cap"]
        self.assertNotEqual(a["E_cap"] / e30, F(565, 315))


class HA2_ImpulseFree(unittest.TestCase):
    def test_r2_equals_r1(self):
        pts = O.CONTRACT_POINTS + O.KNIFE_POINTS + [O.KNIFE_EDGE_UNDEFINED]
        rng = random.Random(20261124)
        pts += [F(rng.randrange(0, 60 * 10**6), 10**6) for _ in range(300)]
        pts += [F(t) + d for t in EVENT_TIMES for d in (-D, 0, D)]
        for conv in O.CONVENTIONS:
            r1, r2 = C.p0_r1(conv), C.p0_r2(conv)
            for t in pts:
                with self.subTest(conv=conv, t=t):
                    self.assertEqual(r2.G(F(t)), r1.G(F(t)))

    def test_slope(self):
        # independently stated expected values (not recomputed from the same formula)
        self.assertEqual(C.p0_r2(R).slope, F("7.75"))
        self.assertEqual(C.p0_r2(L).slope, F("7.75"))
        self.assertEqual(C.p0_r2(OR).slope, F("7.74999999625"))    # 7.75 - 3.75e-9

    def test_sawtooth_bounded(self):
        """residual 20 xA + 35 xP in [0,55) (right) / (0,55] (left, t>0)."""
        for t in [F(k, 7) for k in range(1, 420)]:
            res_r = 100 + F(31, 4) * t - O.g_p0(t, R)
            res_l = 100 + F(31, 4) * t - O.g_p0(t, L)
            self.assertTrue(0 <= res_r < 55)
            self.assertTrue(0 < res_l <= 55)


class HA3_StateCount(unittest.TestCase):
    def test_r3_single_clock_p0(self):
        rng = random.Random(7)
        pts = O.CONTRACT_POINTS + O.KNIFE_POINTS + [F(rng.randrange(0, 6 * 10**7), 10**6) for _ in range(300)]
        pts += [F(t) + d for t in EVENT_TIMES for d in (-D, 0, D)]
        for conv in O.CONVENTIONS:
            r3 = C.R3(conv)
            r3i = C.R3i([(F(1, 2), 20), (1, 55)], conv=conv)
            for t in pts:
                with self.subTest(conv=conv, t=t):
                    self.assertEqual(r3.G(F(t)), O.g_p0(F(t), conv))
                    self.assertEqual(r3i.G(F(t)), O.g_p0(F(t), conv))   # incl. orig (D pass 1 item 1)
        for conv in (R, L):
            r3k = C.R3k(conv)
            for t in pts:
                with self.subTest(conv=conv, t=t, real="R3k"):
                    self.assertEqual(r3k.G(F(t)), O.g_p0(F(t), conv))
        self.assertEqual(C.R3k().states(), (1, 1, 2, 0))
        # D pass 1 item 1: hand value at the knife point, orig, single clock
        self.assertEqual(C.R3i([(F(1, 2), 20), (1, 55)], conv=OR).G(F("10.000000005")), F("140.00000002"))
        with self.assertRaises(ValueError):
            C.R3k(OR)
        with self.assertRaises(ValueError):
            C.R3i([(F(1, 2), 20), (1, 55)], conv="bogus")
        self.assertEqual(C.R3().states(), (2, 0, 2, 0))
        self.assertEqual(C.p0_r1().states(), (3, 0, 2, 0))
        self.assertEqual(C.p0_r2().states(), (3, 0, 2, 0))

    def test_px_fixed_schedule_single_clock_COUNTEREXAMPLE(self):
        """Px as a FIXED, known schedule IS reproduced by ONE clock (period 20,
        comparators 7/20, 17/20, 1): (2,0,3,0). Refutes the architecture's claim that
        Px needs (3,0,2,0) and cannot be done with a single clock."""
        r3x = C.R3i([(F(7, 20), 20), (F(17, 20), 20), (1, 35)])
        rng = random.Random(11)
        pts = O.CONTRACT_POINTS + ["7", "17", "27"] + [F(rng.randrange(0, 6 * 10**7), 10**6) for _ in range(300)]
        pts += [F(t) + d for t in (7, 17, 20, 27, 40) for d in (-D, 0, D)]
        for conv in (R, L):
            r3x_c = C.R3i([(F(7, 20), 20), (F(17, 20), 20), (1, 35)], conv=conv)
            for t in pts:
                with self.subTest(conv=conv, t=t):
                    self.assertEqual(r3x_c.G(F(t)), O.g_px(F(t), conv))
                    self.assertEqual(C.px_r1(conv).G(F(t)), O.g_px(F(t), conv))
        self.assertEqual(r3x.states(), (2, 0, 3, 0))
        self.assertEqual(C.px_r1().states(), (3, 0, 3, 1))

    def test_online_reset_needs_two_phases(self):
        """With the reset time as an ONLINE input, the state must hold both phases:
        three states at t=7 that share one coordinate have different futures."""
        hist = C.px_r1(R).run(7)["x"]                     # reset at 7: (0, 0.35)
        nom = C.p0_r1(R).run(7)["x"]                      # nominal: (0.7, 0.35)
        nom10 = C.p0_r1(R).run(10)["x"]                   # nominal at 10: (0, 0.5)
        self.assertEqual((hist["A"], hist["P"]), (0, F(7, 20)))
        self.assertEqual((nom["A"], nom["P"]), (F(7, 10), F(7, 20)))
        self.assertEqual((nom10["A"], nom10["P"]), (0, F(1, 2)))
        # futures: increments over the next 13 years differ
        fut_hist = O.g_px(20, R) - O.g_px(7, R)    # AC at 17 + pipe at 20
        fut_nom = O.g_p0(20, R) - O.g_p0(7, R)     # AC at 10 + 20, pipe 20
        fut_nom10 = O.g_p0(23, R) - O.g_p0(10, R)  # AC at 20, pipe 20
        self.assertEqual(fut_hist, 52 + 20 + 35)
        self.assertEqual(fut_nom, 52 + 40 + 35)
        self.assertEqual(fut_nom10, 52 + 20 + 35)
        self.assertNotEqual(fut_hist, fut_nom)              # same x_P, different x_A
        self.assertEqual(fut_hist, fut_nom10)                # 13-yr window cannot separate them
        # same x_A (=0) as nom10 but different x_P -> 11-yr futures differ
        self.assertEqual(O.g_px(18, R) - O.g_px(7, R), 44 + 20)
        self.assertEqual(O.g_p0(21, R) - O.g_p0(10, R), 44 + 20 + 35)

    def test_merged_clock_capacitors_fail(self):
        """Merging the two clock caps into one (parallel same I -> 30, parallel summed
        I -> 15, series -> 20/3) with a single charge amount cannot give G(10)=160,
        G(20)=255 simultaneously."""
        for period in (F(30), F(15), F(20, 3)):
            with self.subTest(period=period):
                self.assertEqual(C.single_clock_fit(period), set())


class P1_P2(unittest.TestCase):
    def test_p1_policies(self):
        for t in O.CONTRACT_POINTS:
            for conv in (R, L):
                for pol in ("substitute", "additional"):
                    with self.subTest(t=t, conv=conv, pol=pol):
                        self.assertEqual(C.p1_r1(pol, conv).G(F(t)), O.g_p1(F(t), conv, pol))
        # hand: substitute 255-55+50, additional 255+50
        self.assertEqual(O.g_p1(20, R, "substitute"), 250)
        self.assertEqual(O.g_p1(40, R, "substitute"), 405)
        self.assertEqual(O.g_p1(20, R, "additional"), 305)
        self.assertEqual(O.g_p1(40, R, "additional"), 460)
        self.assertEqual(O.g_p1(20, L, "substitute"), 200)

    def test_p1_orig_consistent(self):
        """D pass 1 item 2: under 'orig' external events are mapped to tau/(1-eps) like
        the clocks. Hand: additional@30 = 295 + 50 = 345; substitute@20.00000001 =
        100 + 80.00000004 + 20 = 200.00000004 (20.00000001(1-1e-9) < 20: nothing at 20)."""
        self.assertEqual(C.p1_r1("additional", OR).G(30), 345)
        self.assertEqual(C.p1_r1("substitute", OR).G(F("20.00000001")), F("200.00000004"))
        pts = O.CONTRACT_POINTS + O.KNIFE_POINTS + ["20.00000001", "20.00000003"]
        pts += [F(20) / (1 - O.EPS) + d for d in (-D, 0, D)]
        for pol in ("substitute", "additional"):
            for t in pts:
                with self.subTest(pol=pol, t=t):
                    self.assertEqual(C.p1_r1(pol, OR).G(F(t)), O.g_p1(F(t), OR, pol))

    def test_unsupported_orig_rejected(self):
        for fn in (lambda: C.p2_r1(OR), lambda: C.px_r1(OR),
                   lambda: C.R1([], conv="bogus")):
            with self.assertRaises(ValueError):
                fn()

    def test_p1_order_invariance_and_naive_counterexample(self):
        import itertools
        # (a) the SET rule, actually permuted: clock-list order x split renovation
        # (two external entries 30+20 at t=20, listed in both orders), both policies
        for pol, expect in (("substitute", 250), ("additional", 305)):
            vals = set()
            for clocks in itertools.permutations(["A", "P"]):
                for parts in ((30, 20), (20, 30)):
                    ks = [C.Clock(n, 10 if n == "A" else 20, 20 if n == "A" else 35) for n in clocks]
                    ext = [C.ExtEvent(20, a, resets=("A", "P"), replaces=("A", "P"), kind="renovation")
                           for a in parts]
                    r = C.R1(ks, ext=ext, policy=pol)
                    vals.add((r.G(20), r.G(F(20) - D), r.G(F(20) + D), r.G(40)))
            self.assertEqual(len(vals), 1, (pol, vals))
            self.assertEqual(vals.pop()[0], expect)
        # (b) naive sequential implementation
        res = {}
        for order in itertools.permutations(["renovation", "A", "P"]):
            res[order] = C.p1_r1("additional", R, sequential_order=list(order)).G(20)
        self.assertEqual(res[("renovation", "A", "P")], 250)   # looks like substitute
        self.assertEqual(res[("A", "P", "renovation")], 305)   # looks like additional
        self.assertEqual(res[("A", "renovation", "P")], 100 + 80 + 20 + 20 + 50)  # 270: neither policy
        self.assertEqual(res[("P", "renovation", "A")], 100 + 80 + 20 + 35 + 50)  # 285: neither policy
        self.assertEqual(len(set(res.values())), 4)
        # clocks restart at 20 under the set rule (coincide with nominal)
        x = C.p1_r1("substitute", R).run(20)["x"]
        self.assertEqual((x["A"], x["P"]), (0, 0))

    def test_p2(self):
        hand_p2 = {"10": 100 + 40 + 20, "20": 100 + 40 + 30 + 40 + 35,
                   "30": 100 + 40 + 60 + 60 + 35, "40": 100 + 40 + 90 + 80 + 70,
                   "60": 100 + 40 + 150 + 120 + 105}
        for t, v in hand_p2.items():
            self.assertEqual(O.g_p2(F(t), R), v)
        for t in O.CONTRACT_POINTS:
            for conv in (R, L):
                with self.subTest(t=t, conv=conv):
                    self.assertEqual(C.p2_r1(conv).G(F(t)), O.g_p2(F(t), conv))
        self.assertEqual(C.p2_r1(R).G(F(10) - D), 140 - 4 * D)
        self.assertEqual(C.p2_r1(R).G(F(10) + D), 160 + 3 * D)
        self.assertEqual(C.p2_r1().states(), (3, 1, 2, 0))


class AC(unittest.TestCase):
    W = 2 * math.pi   # 1 cycle per year; half period h = 0.5 yr

    def test_zero_mean_ac_negative(self):
        c = 10.0
        I0 = math.pi / (2 * c)
        qmax = max(C.q_zero_mean(k / 1000, I0, self.W) for k in range(60001))
        self.assertLessEqual(qmax, 2 * I0 / self.W + 1e-15)
        self.assertLess(qmax, 1.0)                       # never reaches clock threshold
        # integrated (simulate_clock), not hard-coded
        self.assertEqual(C.ac_clock_count(60, c, self.W, "zero"), 0)
        self.assertEqual(len(C.simulate_clock(60, lambda s: C.q_zero_mean(s, I0, self.W), 1.0)), 0)
        # mean charge over a full period does not grow
        self.assertAlmostEqual(C.q_zero_mean(10.0, I0, self.W), 0.0, delta=1e-12)
        # an AC-driven clock therefore fails G(10)=160
        self.assertEqual(100 + 4 * 10 + 20 * C.ac_clock_count(10, c, self.W, "zero"), 140)

    def test_zero_mean_threshold_below_swing_spurious(self):
        """Executed negative result (D pass 1 item 3): I0=1, w=2pi, swing 2I0/w=1/pi.
        theta=0.1: cumulative charge reaches levels 0.1, 0.2, 0.3 < 1/pi in the first
        half cycle, 0.4 never -> 3 counts in 10 yr with subtract-reset; reset-to-zero at
        the exact hit is the same rule (3). A diode-clamped clock (q>=0) restarts every
        cycle -> 3 per cycle = 30. Counts are set by amplitude/frequency/threshold, not c."""
        q = lambda s: C.q_zero_mean(s, 1.0, self.W)
        sub = C.simulate_clock(10, q, 0.1, "subtract")
        self.assertEqual(len(sub), 3)
        self.assertTrue(all(h < 0.5 for h in sub))
        self.assertEqual(len(C.simulate_clock(10, q, 0.1, "zero")), 3)
        self.assertEqual(len(C.simulate_clock(10, q, 0.1, "subtract", clamp=True)), 30)
        q2 = lambda s: C.q_zero_mean(s, 1.0, 2 * self.W)
        self.assertEqual(len(C.simulate_clock(10, q2, 0.1, "subtract")), 1)   # swing 1/(2pi)
        self.assertEqual(len(C.simulate_clock(10, q, 0.2, "subtract")), 1)

    def test_simulated_clock_matches_closed_form_fullwave(self):
        I0 = math.pi / 20
        hs = C.simulate_clock(60, lambda s: C.q_fullwave_phase(s, I0, self.W, 0.3), 1.0)
        self.assertEqual(len(hs), 6)
        for n, hit in enumerate(hs, 1):
            self.assertAlmostEqual(hit, C.hit_fullwave(n, I0, self.W, 0.3), delta=1e-9)

    def test_fullwave_phase_dependence(self):
        """D pass 1 item 4. Ripple g(v)=(I0/w)(1-cos u-2u/pi), u=v mod pi; hit n exact iff
        f(u0+n*pi*c/h)=f(u0), u0=phi mod pi. Integer c/h: exact for every phi.
        c/h in 1/2+Z: exact iff f(u0+pi/2)=f(u0) <=> sin u0+cos u0=1 <=> u0 in {0,pi/2}."""
        h = 0.5
        for phi in (0.0, math.pi / 2, math.pi / 4, 0.3, 1.0):
            for ch, exact in ((20, True), (20.5, phi in (0.0, math.pi / 2))):
                c = ch * h
                I0 = math.pi / (2 * c)
                err = max(abs(C.hit_fullwave(n, I0, self.W, phi) - n * c) for n in range(1, 41))
                with self.subTest(phi=phi, ch=ch):
                    if exact:
                        self.assertLess(err, 1e-6)      # sqrt-conditioned near current zeros
                    else:
                        self.assertGreater(err, 0.04)

    def test_fullwave_sharp_error_bounds(self):
        """phi in {0,pi/2}: |tau_n - nc| <= (m/2) h, m=max|f|=0.21051 -> 0.10526 h.
        General phi: <= m h = 0.21051 h (ripple can swing from min to max). Observed
        0.2097 h at phi=asin(2/pi), c/h=20.25, which exceeds 0.10526 h."""
        h = 0.5
        m = math.sqrt(1 - 4 / math.pi**2) + 2 * math.asin(2 / math.pi) / math.pi - 1
        self.assertAlmostEqual(m, 0.2105136623530186, places=12)
        rng = random.Random(1)
        w0 = wg = 0.0
        for _ in range(3000):
            c = rng.uniform(1, 15); I0 = math.pi / (2 * c); phi = rng.uniform(0, math.pi)
            for n in range(1, 6):
                w0 = max(w0, abs(C.hit_fullwave(n, I0, self.W, 0.0) - n * c) / h)
                wg = max(wg, abs(C.hit_fullwave(n, I0, self.W, phi) - n * c) / h)
        self.assertLessEqual(w0, m / 2 + 1e-9)
        self.assertGreater(w0, 0.99 * m / 2)
        self.assertLessEqual(wg, m + 1e-9)
        self.assertGreater(wg, m / 2 * 1.5)
        c = 20.25 * h; I0 = math.pi / (2 * c)
        e = max(abs(C.hit_fullwave(n, I0, self.W, math.asin(2 / math.pi)) - n * c) for n in range(1, 41))
        self.assertGreater(e / h, m / 2)

    def test_fullwave_integer_multiple_exact(self):
        """c = m * h (m integer): hits exactly at n c (to float precision)."""
        for c in (10.0, 20.0):
            I0 = math.pi / (2 * c)
            for n in range(1, 7):
                self.assertAlmostEqual(C.hit_fullwave(n, I0, self.W), n * c, delta=1e-9)
        self.assertEqual(C.ac_clock_count(60.0, 10.0, self.W), 6)
        self.assertEqual(C.ac_clock_count(59.999999, 10.0, self.W), 5)

    def test_fullwave_half_integer_multiple_exact_COUNTEREXAMPLE(self):
        """PHASE 0 ONLY (see test_fullwave_phase_dependence for general phase).
        Ripple f(u)=1-cos u-2u/pi vanishes at u in {0, pi/2, pi} only (f''=cos u).
        At phi=0 hits are exact at every n c iff c/h in (1/2)Z: c = 10.25 = 20.5 h."""
        c = 10.25
        I0 = math.pi / (2 * c)
        for n in range(1, 7):
            self.assertAlmostEqual(C.hit_fullwave(n, I0, self.W), n * c, delta=1e-9)
        c = 10.125   # 20.25 h: n=1 not exact, n=2 (40.5 h) exact
        I0 = math.pi / (2 * c)
        self.assertGreater(abs(C.hit_fullwave(1, I0, self.W) - c), 1e-3)
        self.assertAlmostEqual(C.hit_fullwave(2, I0, self.W), 2 * c, delta=1e-9)

    def test_fullwave_non_multiple_error_below_half_period(self):
        h = math.pi / self.W
        worst = 0.0
        for c in (10.3, 7.77, 3.1415):
            I0 = math.pi / (2 * c)
            for n in range(1, 30):
                err = abs(C.hit_fullwave(n, I0, self.W) - n * c)
                worst = max(worst, err)
                self.assertLess(err, h)
        self.assertGreater(worst, 1e-3)    # not exact in general

    def test_rectified_operational_ripple(self):
        I0 = 2 * math.pi          # mean 2 I0/pi = 4 kg/yr (gamma = 1)
        bound = C.fullwave_ripple_bound(I0, self.W)
        dev = [abs(C.q_fullwave(k / 997, I0, self.W) - 4 * (k / 997)) for k in range(1, 997 * 20)]
        self.assertLessEqual(max(dev), bound + 1e-12)
        self.assertGreater(max(dev), 0.99 * bound)
        for k in range(0, 41):            # exact on the half-period grid
            self.assertAlmostEqual(C.q_fullwave(k / 2, I0, self.W), 2.0 * k, delta=1e-9)


if __name__ == "__main__":
    unittest.main()
