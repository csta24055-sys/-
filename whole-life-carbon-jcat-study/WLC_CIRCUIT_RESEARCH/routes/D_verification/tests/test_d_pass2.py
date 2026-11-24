"""Pass-2 unit tests of D's horizon-side oracle (no frozen code, no route code; hand-written expected values).
Run: cd routes/D_verification && PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -v
"""
import math, os, sys, unittest
from fractions import Fraction as F
from types import SimpleNamespace
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "code"))
import p2_oracle_kernels as K   # noqa: E402
import oracle_d as OD           # noqa: E402

NI = -math.inf


class Kernels(unittest.TestCase):
    def test_shapes(self):
        self.assertEqual(K.h(10.0, 10.0, 0.0, 10.0), 0)               # event at T not counted
        self.assertEqual(K.h(10.00000002, 10.0, 0.0, 10.0), 1)
        self.assertEqual(K.h(9.25, 9.0, 1.0, NI), F(1, 4))           # w_9(9.25)
        self.assertEqual(K.h(12.0, 9.0, 1.0, NI), 1)
        self.assertEqual(K.h(9.75, 9.0, 1.0, 9.5), F(3, 4))          # gated cell after its event
        self.assertEqual(K.h(9.25, 9.0, 1.0, 9.5), 0)
        P = SimpleNamespace
        self.assertEqual(K.kernel_sum([P(amp=4.0 * 130, start=0.0, length=130.0, gate=NI)], 37.5), F(150))  # 4*min(T,H)

    def test_rate_form_matches_amplitude_form(self):
        # 03 S5.1: density a*H*clip(T/H,0,1) == a*r_H(T); year cell identical in both forms
        self.assertEqual(K.h_rate(37.5, 0.0, 130.0, NI) * 4, K.h(37.5, 0.0, 130.0, NI) * 4 * 130)
        self.assertEqual(K.h_rate(9.25, 9.0, 1.0, NI), K.h(9.25, 9.0, 1.0, NI))
        self.assertEqual(K.h_rate(200.0, 0.0, 130.0, NI), 130)

    def test_p0_pieces_equal_rational_orig(self):
        ps = K.p0_pieces()
        for t in ["1", "9.999999", "10", "10.000001", "20", "30", "40", "60"]:
            self.assertEqual(K.kernel_sum(ps, float(t)), OD.G("P0", F(float(t)), OD.ORIG))


class Refrigerant(unittest.TestCase):
    def dev(self, **kw):
        d = dict(charge_mass_kg=10.0, gwp=2.0, annual_leak_rate=0.5, top_up=False, replacement_loss_rate=0.5,
                 end_of_life_recovery_rate=0.25, change_years=None, service_life=None)
        d.update(kw)
        return SimpleNamespace(**d)

    def test_no_event(self):
        # year 1: leak 10*0.5=5 (B1-02 10), m=5; T=1.5: leak 5*0.5*0.5=1.25 (B1-02 +2.5), m=3.75
        r = K.refrigerant([self.dev()], 1.5)
        self.assertEqual(r["B1-02"], F(25, 2))
        self.assertEqual(r["B1-04"], F(375, 100) * F(3, 4) * 2)
        self.assertEqual(r["B1-03"], 0)

    def test_integer_event_band(self):
        # event at 1 (year 1): applied at end of year 1 once counted (T > 1/(1-eps) in float)
        d = self.dev(change_years=[1.0])
        r_in = K.refrigerant([d], 1.0 * (1 + 2.5e-10))     # inside band: not yet counted
        r_out = K.refrigerant([d], 1.5)
        self.assertEqual(r_in["B1-03"], 0)
        self.assertEqual(r_out["B1-03"], F(5) * F(1, 2) * 2)     # m before = 5
        self.assertEqual(r_out["B1-02"], 10 + F(10) * F(1, 2) * F(1, 2) * 2)


class Rank(unittest.TestCase):
    def test_exact_rank(self):
        import p2_check_c
        r = p2_check_c.exact_rank
        self.assertEqual(r([[F(1), F(2)], [F(2), F(4)]]), 1)
        self.assertEqual(r([[F(1), F(0), F(1)], [F(0), F(1), F(1)], [F(1), F(1), F(2)]]), 2)


if __name__ == "__main__":
    unittest.main()
