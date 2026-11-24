"""Pass-3 tests: zero-mean AC clock dispute and the phase-dependent rectified-clock bound (D's own code).
Run: PYTHONDONTWRITEBYTECODE=1 math7-py -B -m unittest discover -s tests -v   (skipped without mpmath)"""
import math, os, sys, unittest
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "code"))
try:
    import p3_recheck as P3
    OK = True
except ImportError:
    OK = False


@unittest.skipUnless(OK, "mpmath not available")
class Pass3(unittest.TestCase):
    def test_zero_mean_clock_rules(self):
        self.assertEqual(P3.zero_mean_clock("subtract"), 3)
        self.assertEqual(P3.zero_mean_clock("zero"), 3)          # same rule at an exact hit
        self.assertEqual(P3.zero_mean_clock("zero+clamp"), 30)   # diode clamp: 3 per cycle

    def test_rectified_bound_phase(self):
        m = math.sqrt(1 - 4 / math.pi ** 2) + 2 * math.asin(2 / math.pi) / math.pi - 1
        coh = math.sqrt(2) * 17                                   # irrational c/h
        e0 = P3.hit_err_over_h(coh, 0.0, 300)
        e1 = P3.hit_err_over_h(coh, math.asin(2 / math.pi), 300)
        self.assertLessEqual(e0, m / 2 + 1e-9); self.assertGreater(e0, 0.999 * m / 2)
        self.assertLessEqual(e1, m + 1e-9); self.assertGreater(e1, 0.99 * m)
        self.assertAlmostEqual(P3.hit_err_over_h(20.25, math.asin(2 / math.pi), 400), 0.20974, places=4)


if __name__ == "__main__":
    unittest.main()
