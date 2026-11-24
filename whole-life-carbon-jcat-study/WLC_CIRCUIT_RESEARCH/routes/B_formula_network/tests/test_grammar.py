"""Oracle-free tests of the grammar primitives and kernels (no frozen code imported, no network)."""
import math
import os
import sys
import unittest
from fractions import Fraction
from types import SimpleNamespace

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "code"))
import grammar as G  # noqa: E402


class P:  # minimal stand-in for rampstep.Piece (amp, start, length, gate)
    def __init__(self, amp, start, length, gate=G.NEG_INF):
        self.amp, self.start, self.length, self.gate = amp, start, length, gate


class TestPrimitives(unittest.TestCase):
    def test_atom_convention(self):
        net = G.Net()
        out = net.gate(net.theta(10.0), net.src(20.0))
        self.assertEqual(net.value(10.0, out), 0.0)            # event at T is not counted
        self.assertEqual(net.value(10.000000005, out), 0.0)    # inside the band [10, 10/(1-eps))
        self.assertEqual(net.value(10.00000002, out), 20.0)    # after the band
        self.assertEqual(net.value(9.999999, out), 0.0)
        self.assertEqual(net.value(10.000001, out), 20.0)

    def test_switch_point(self):
        for tau in (10.0, 20.0, 29.0, 8.73, 0.7, 10.0 / 3.0, 99.9):
            sw = G.switch_point(tau)
            self.assertTrue(tau < sw * G.D)
            self.assertFalse(tau < math.nextafter(sw, -math.inf) * G.D)
            self.assertGreater(sw, tau)
        # real-arithmetic switch point 10/(1-eps) vs float: within a few ulp (knife edge is undefined territory)
        self.assertLess(abs(Fraction(G.switch_point(10.0)) - Fraction(10) / (1 - Fraction(1, 10 ** 9))), Fraction(1, 10 ** 13))

    def test_year_weight_sum_is_min_T_H(self):
        H = 130
        net = G.Net()
        out = net.sum([net.w(k) for k in range(H)])
        for T in (0.5, 1.0, 7.3, 59.999999, 130.0):
            self.assertAlmostEqual(net.value(T, out), min(T, H), places=12)

    def test_cell_and_gcell(self):
        net = G.Net()
        c = net.gain(3.0, net.w(9))
        g = net.gate(net.theta(9.5), net.gain(-2.0, net.w(9)))
        self.assertEqual(net.value(9.25, c), 0.75)
        self.assertAlmostEqual(net.value(9.75, c), 2.25)
        self.assertEqual(net.value(9.25, g), 0.0)
        self.assertAlmostEqual(net.value(9.75, g), -1.5)
        self.assertEqual(net.value(12.0, c), 3.0)

    def test_integrator_density_and_table_cells(self):
        pieces = [P(4.0 * 130, 0.0, 130.0)] + [P(float(k + 1), float(k), 1.0) for k in range(130)]
        Ts = [0.5, 1.0, 2.5, 10.0, 60.0]
        a, _, _ = G.eval_kernel(pieces, 130, Ts, cell_mode="clip")
        b, net, _ = G.eval_kernel(pieces, 130, Ts, cell_mode="integrator")
        for T in Ts:
            K = math.ceil(T) - 1
            exact = 4.0 * T + sum(k + 1 for k in range(K)) + (K + 1) * (T - K)
            self.assertAlmostEqual(a[T]["total"], exact, places=9)
            self.assertAlmostEqual(b[T]["total"], exact, places=9)
        self.assertEqual(net.counts()["int"], 2)

    def test_no_multiplier_in_grammar(self):
        with self.assertRaises(G.GrammarError):
            G.Net()._add("mul", (0, 0), None)

    def test_memoryless_eval_refuses_integrators(self):
        net = G.Net()
        x = net.integrator(net.src(1.0))
        with self.assertRaises(G.GrammarError):
            net.value(1.0, x)


def _dev(**kw):
    base = dict(charge_mass_kg=10.0, gwp=2.0, annual_leak_rate=0.1, top_up=False, replacement_loss_rate=0.5,
                end_of_life_recovery_rate=0.25, change_years=None, service_life=None)
    base.update(kw)
    return SimpleNamespace(**base)


def hand_refrigerant(dev, T):
    """Independent row-by-row restatement of the model rules (03 5.5 / refcalc docstrings), written here."""
    Y = math.ceil(T)
    evs = [t for t in (dev.change_years or []) if t > 0 and t < T * G.D] if dev.change_years is not None else []
    if dev.change_years is None and dev.service_life:
        n = 1
        while n * dev.service_life < T * G.D:
            evs.append(n * dev.service_life)
            n += 1
    per = {}
    for t in evs:
        y = max(1, math.ceil(t * G.D))
        per[y] = per.get(y, 0) + 1
    m, b12, b13 = dev.charge_mass_kg, 0.0, 0.0
    for y in range(1, Y + 1):
        w = min(1.0, T - (y - 1))
        leak = m * dev.annual_leak_rate * w
        b12 += leak * dev.gwp
        if not dev.top_up:
            m -= leak
        for _ in range(per.get(y, 0)):
            b13 += m * dev.replacement_loss_rate * dev.gwp
            m = dev.charge_mass_kg
    return b12, b13, m * (1 - dev.end_of_life_recovery_rate) * dev.gwp


class TestRefrigerantAutomaton(unittest.TestCase):
    def check(self, dev, Ts):
        rc = G.RefrigerantCircuit(SimpleNamespace(refrigerants=[dev]), 130)
        r = rc.sweep(Ts)
        for T in Ts:
            h = hand_refrigerant(dev, T)
            for got, want in zip((r[T]["B1-02"], r[T]["B1-03"], r[T]["B1-04"]), h):
                self.assertLessEqual(abs(got - want), 1e-12 * max(1.0, abs(want)), (T, got, want))
        self.assertEqual(rc.unexpected, [])

    def test_mid_year_and_integer_events(self):
        Ts = [0.5, 1.0, 6.9, 7.3, 7.9, 8.0, 8.5, 10.0, 10.000000005, 10.00000002, 10.5, 14.99, 15.0, 20.000001, 30.0]
        self.check(_dev(change_years=[7.3, 10, 10.6]), Ts)
        self.check(_dev(service_life=5.0), Ts)
        self.check(_dev(service_life=5.0, top_up=True), Ts)
        self.check(_dev(change_years=[10, 10.000000001]), Ts)   # two events in one cell, one in the knife zone

    def test_late_reset_is_needed(self):
        dev = _dev(service_life=5.0)
        rc = G.RefrigerantCircuit(SimpleNamespace(refrigerants=[dev]), 130, late_reset=False)
        r = rc.sweep([7.5])
        self.assertGreater(abs(r[7.5]["B1-04"] - hand_refrigerant(dev, 7.5)[2]), 1e-3)


if __name__ == "__main__":
    unittest.main()
