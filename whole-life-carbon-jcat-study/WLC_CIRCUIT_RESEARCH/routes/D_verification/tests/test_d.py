"""Route D tests. Expected values are HAND arithmetic written in this file (not produced by
the oracle code path), so a defect in oracle_d would fail them.

Run: cd routes/D_verification && PYTHONDONTWRITEBYTECODE=1 math7-py -B -m unittest discover -s tests -v
(stdlib unittest; mpmath-dependent tests are skipped if mpmath is unavailable; no network)
"""
import itertools, os, random, sys, unittest
from fractions import Fraction as F
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "code"))
import oracle_d as O  # noqa: E402

try:
    import mpmath as mp  # noqa: F401
    HAVE_MP = True
except ImportError:
    HAVE_MP = False


def hand_p0(t, conv):
    """Hand rule written independently: count multiples of 10 and 20 by listing them."""
    t = F(t)
    eff = {"right": lambda tau: tau <= t, "left": lambda tau: tau < t,
           "orig": lambda tau: tau < t * (1 - F(1, 10**9))}[conv]
    ac = [tau for tau in (10, 20, 30, 40, 50, 60, 70) if eff(tau)]
    pp = [tau for tau in (20, 40, 60) if eff(tau)]
    return 100 + 4 * t + 20 * len(ac) + 35 * len(pp)


class Boundary(unittest.TestCase):
    TABLE = {  # t: (right, left, orig) -- written by hand
        "0": (100, 100, 100), "1": (104, 104, 104), "9.999999": ("139.999996",) * 3,
        "10": (160, 140, 140), "10.000001": ("160.000004",) * 3, "19.999999": ("199.999996",) * 3,
        "20": (255, 200, 200), "20.000001": ("255.000004",) * 3, "30": (315, 295, 295),
        "40": (410, 355, 355), "60": (565, 510, 510),
        "10.000000005": ("160.00000002", "160.00000002", "140.00000002"),
        "10.00000002": ("160.00000008",) * 3,
        "10.00000001": ("160.00000004", "160.00000004", "140.00000004"),
    }

    def test_table_exact(self):
        for t, vals in self.TABLE.items():
            for conv, v in zip(O.CONVENTIONS, vals):
                with self.subTest(t=t, conv=conv):
                    self.assertEqual(O.G("P0", F(t), conv), F(str(v)))
                    self.assertEqual(hand_p0(t, conv), F(str(v)))

    def test_exact_limits(self):
        for tau, jump in ((10, 20), (20, 55), (30, 20), (40, 55), (60, 55)):
            for conv in ("right", "left"):
                lo, hi = O.limits("P0", tau, conv)
                self.assertEqual(hi - lo, jump)
                self.assertEqual(lo, hand_p0(tau, "left"))
                self.assertEqual(hi, hand_p0(tau, "right"))
            lo, hi = O.limits("P0", tau, "orig")
            self.assertEqual(lo, hi)                           # orig is continuous at tau
            lo, hi = O.limits("P0", F(tau) / (1 - O.EPS), "orig")
            self.assertEqual(hi - lo, jump)                    # ...and jumps at tau/(1-eps)

    def test_orig_band_is_closed(self):
        """right vs orig differ at T=10/(1-eps) itself (architecture/A-3 wrote half-open)."""
        b = F(10) / (1 - O.EPS)
        self.assertEqual(O.G("P0", b, "right") - O.G("P0", b, "orig"), 20)
        self.assertEqual(O.G("P0", b + F(1, 10**15), "right") - O.G("P0", b + F(1, 10**15), "orig"), 0)

    def test_random_vs_hand(self):
        rng = random.Random(3)
        for _ in range(300):
            t = F(rng.randrange(0, 60 * 10**6), 10**6)
            for conv in O.CONVENTIONS:
                self.assertEqual(O.G("P0", t, conv), hand_p0(t, conv))

    def test_float_slip_through_c01(self):
        # fl(3*0.1) = 0.30000000000000004 > fl(0.3): event at 3c 'slips' past t = 0.3
        self.assertGreater(3 * 0.1, 0.3)
        self.assertEqual(int((0.3) // 0.1), 2)      # float floor count is 2, exact is 3
        self.assertEqual(F(3, 10) // F(1, 10), 3)


class Events(unittest.TestCase):
    def test_p1_hand(self):
        hand = {("substitute", 20): 100 + 80 + 20 + 50, ("substitute", 40): 100 + 160 + 20 + 50 + 20 + 20 + 35,
                ("additional", 20): 100 + 80 + 40 + 35 + 50, ("additional", 40): 100 + 160 + 80 + 70 + 50}
        for (pol, t), v in hand.items():
            self.assertEqual(O.G("P1", t, "right", pol), v)
        self.assertEqual(O.G("P1", 20, "left", "substitute"), 200)

    def test_p1_no_double_count_and_order_free(self):
        for pol in ("substitute", "additional"):
            ev, _ = O.ledger("P1", pol)
            keys = [e.key() for e in ev]
            self.assertEqual(len(keys), len(set(keys)))
            at20 = sorted(e.item for e in ev if e.time == 20)
            self.assertEqual(at20, ["RENOV"] if pol == "substitute" else ["AC", "PIPE", "RENOV"])
            rev = O.apply_supersession(list(reversed(ev)))
            self.assertEqual(sorted(e.key() for e in rev), sorted(keys))

    def test_naive_sequential_values(self):
        vals = {O.naive_sequential_G20(o) for o in itertools.permutations(["RENOV", "AC", "PIPE"])}
        self.assertEqual(vals, {200 + 50, 200 + 20 + 50, 200 + 35 + 50, 200 + 55 + 50})

    def test_p2_hand_and_not_year_cell(self):
        hand = {10: 100 + 40 + 20, 20: 100 + 40 + 30 + 40 + 35, 30: 100 + 40 + 60 + 60 + 35,
                40: 100 + 40 + 90 + 80 + 70, 60: 100 + 40 + 150 + 120 + 105}
        for t, v in hand.items():
            self.assertEqual(O.G("P2", t), v)
            self.assertEqual(v - 1, 100 + 36 + 3 * (t - 9) + 20 * (t // 10) + 35 * (t // 20))  # year-cell alt = -1

    def test_px_and_restart(self):
        self.assertEqual(O.G("Px", 7), 100 + 28 + 20)
        self.assertEqual(O.G("Px", 20), 100 + 80 + 20 + 20 + 35)
        self.assertEqual(O.G("Px", 7, "left"), 128)
        # renovation at 15 restarts clocks: next AC 25, next pipe 35
        ev, _ = O.ledger("P1", "additional", tau_R=F(15))
        self.assertEqual(sorted(str(e.time) for e in ev if e.item == "PIPE" and e.time <= 60), ["35", "55"])
        self.assertEqual(O.G("P1", 25, "right", "additional", tau_R=F(15)), 100 + 100 + 20 + 50 + 20)


class States(unittest.TestCase):
    def test_px_is_20_periodic(self):
        ev, _ = O.ledger("Px")
        self.assertEqual({e.time % 20 for e in ev if e.time <= 200}, {F(0), F(7), F(17)})

    def test_online_futures(self):
        self.assertEqual(O.G("Px", 20) - O.G("Px", 7), 52 + 20 + 35)        # 107
        self.assertEqual(O.G("P0", 20) - O.G("P0", 7), 52 + 40 + 35)        # 127
        self.assertEqual(O.G("Px", 18) - O.G("Px", 7), 44 + 20)             # 64
        self.assertEqual(O.G("P0", 21) - O.G("P0", 10), 44 + 20 + 35)       # 99

    def test_merged_clock_any_period_impossible(self):
        # every single-charge clock gives equal jumps; P0 jump at 10 is 20 and at 20 is 55
        lo10, hi10 = O.limits("P0", 10)
        lo20, hi20 = O.limits("P0", 20)
        self.assertNotEqual(hi10 - lo10, hi20 - lo20)


@unittest.skipUnless(HAVE_MP, "mpmath not available")
class JouleAC(unittest.TestCase):
    def setUp(self):
        import check_joule_ac as J
        self.J = J

    def test_cross_term_equal_width(self):
        J = self.J
        for w in (F(1, 10**6), F(1)):
            q = {"AC": J.q_for(20, w), "PIPE": J.q_for(35, w)}
            d = J.window_kg([(w, {"AC": 1, "PIPE": 1})], q)
            self.assertEqual(d[2][("AC", "PIPE")] * w, 2 * F(1, 3) * 3 * w * w)     # coefficient kappa R w * 2
            self.assertLess(abs(J.cross_only(d, q) - 20 * J.mp.sqrt(7)), J.mp.mpf(10) ** -30)

    def test_cross_term_unequal_width_halves(self):
        J = self.J
        w = F(1, 1000)
        q = {"AC": J.q_for(20, w), "PIPE": J.q_for(35, 4 * w)}
        d = J.window_kg([(w, {"AC": 1, "PIPE": 1}), (3 * w, {"PIPE": 1})], q)
        self.assertLess(abs(J.cross_only(d, q) - J.mp.sqrt(700)), J.mp.mpf(10) ** -30)

    def test_walsh_single_resistor_additive(self):
        J = self.J
        w = F(1, 100); s = w / 4
        q = {"AC": J.q_for(20, w), "PIPE": J.q_for(35, w)}
        segs = [(s, {"AC": 1, "PIPE": 1}), (s, {"AC": 1, "PIPE": -1}), (s, {"AC": -1, "PIPE": 1}), (s, {"AC": -1, "PIPE": -1})]
        const, lin, cross = J.window_kg(segs, q)
        self.assertEqual(const, 4 * w + 55)
        self.assertTrue(all(v == 0 for v in lin.values()) and all(v == 0 for v in cross.values()))

    def test_rectified_half_integer_phase(self):
        J = self.J
        mp = J.mp
        h = mp.mpf(1) / 2
        self.assertLess(J.rect_hits(h * mp.mpf("20.5"), 0, 4), mp.mpf(10) ** -10)          # A-16 at phi=0
        self.assertGreater(J.rect_hits(h * mp.mpf("20.5"), mp.pi / 4, 4), mp.mpf("0.01"))  # fails at phi=pi/4
        self.assertLess(J.rect_hits(h * 20, mp.pi / 4, 4), mp.mpf(10) ** -10)              # integer still exact
        self.assertGreater(J.rect_hits(h * mp.mpf("20.25"), 0, 1), mp.mpf("0.01"))         # quarter multiple


if __name__ == "__main__":
    unittest.main()
