"""H-B2 illustration and H-B3 refrigerant comparison (executed numbers; H-B2 is an illustration only)."""
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "code"))


class TestHB2(unittest.TestCase):
    def test_exponential_sums_never_reach_kinked_or_jumping_kernel(self):
        import hb2_passive
        r = hb2_passive.run()
        for row in r["jump_atom"]:
            self.assertGreaterEqual(row["sup_error"], 0.5 - 1e-9)
        for row in r["kink_w0"]:
            self.assertGreater(row["sup_error"], 1e-3)


class TestHB3(unittest.TestCase):
    def test_rc_vs_sample_hold(self):
        import hb3_refrigerant
        r = hb3_refrigerant.run(single=True, step=1.0, T_max=30.0)
        self.assertEqual(r["B1-04"]["SH"]["max_rel_fractional_T"], 0.0)
        self.assertEqual(r["B1-04"]["SH"]["max_rel_integer_T"], 0.0)
        rcb = r["B1-04"]["RC-b (RC in cell, S/H resets)"]
        self.assertLess(rcb["max_rel_integer_T"], 1e-12)       # RC with exp(-1/RC)=q agrees at whole years
        self.assertGreater(rcb["max_rel_fractional_T"], 1e-3)  # ... but not inside a year cell
        self.assertGreater(r["B1-02"]["RC-b (RC in cell, S/H resets)"]["max_rel_fractional_T"], 1e-3)


if __name__ == "__main__":
    unittest.main()
