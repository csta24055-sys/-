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
        self.assertEqual(C.p0_r2(R).slope, F(4) + F(20, 10) + F(35, 20))   # 7.75
        self.assertEqual(C.p0_r2(OR).slope, 4 + (1 - O.EPS) * F(15, 4))

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
                    if conv != OR:
                        self.assertEqual(r3i.G(F(t)), O.g_p0(F(t), conv))
        for conv in (R, L):
            r3k = C.R3k(conv)
            for t in pts:
                with self.subTest(conv=conv, t=t, real="R3k"):
                    self.assertEqual(r3k.G(F(t)), O.g_p0(F(t), conv))
        self.assertEqual(C.R3k().states(), (1, 1, 2, 0))
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

    def test_p1_order_invariance_and_naive_counterexample(self):
        import itertools
        # set semantics: order is not an input -> trivially invariant; check the
        # naive sequential implementation instead
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
        self.assertEqual(C.ac_clock_count(60, c, self.W, "zero"), 0)
        # mean charge over a full period does not grow
        self.assertAlmostEqual(C.q_zero_mean(10.0, I0, self.W), 0.0, delta=1e-12)
        # an AC-driven clock therefore fails G(10)=160
        self.assertEqual(100 + 4 * 10 + 20 * C.ac_clock_count(10, c, self.W, "zero"), 140)

    def test_fullwave_integer_multiple_exact(self):
        """c = m * h (m integer): hits exactly at n c (to float precision)."""
        for c in (10.0, 20.0):
            I0 = math.pi / (2 * c)
            for n in range(1, 7):
                self.assertAlmostEqual(C.hit_fullwave(n, I0, self.W), n * c, delta=1e-9)
        self.assertEqual(C.ac_clock_count(60.0, 10.0, self.W), 6)
        self.assertEqual(C.ac_clock_count(59.999999, 10.0, self.W), 5)

    def test_fullwave_half_integer_multiple_exact_COUNTEREXAMPLE(self):
        """Ripple f(u)=1-cos u-2u/pi vanishes at u in {0, pi/2, pi} only (f''=cos u:
        convex on [0,pi/2], concave on [pi/2,pi]). Hence hits are exact at every n c iff
        c/h is in (1/2)Z, not only for integer c/h. c = 10.25 = 20.5 h is exact."""
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
