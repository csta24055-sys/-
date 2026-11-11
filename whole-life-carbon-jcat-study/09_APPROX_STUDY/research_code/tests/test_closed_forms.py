"""Closed forms against the loops they replace (random and adversarial inputs).

Run:  cd research_code && python3 -m unittest tests.test_closed_forms -v
"""
import math
import random
import types
import unittest

from fastcalc import closed_forms as cf
from refcalc.base import event_year, periodic_events, year_weights


def close(a, b, tol=1e-11):
    return abs(a - b) <= tol * max(abs(a), abs(b), 1e-300) or abs(a - b) <= 1e-12


def periods(rng):
    """Study periods and cycles, including exact divisors and knife-edge floats."""
    T = rng.choice([0.5, 1.0, 10.5, 30.0, 50.0, 60.0, 60.000001, 62.5, 75.0, 99.9, 100.0, round(rng.uniform(0.2, 120), 3)])
    kind = rng.random()
    if kind < 0.35:
        c = T / rng.randint(1, 40)                      # exact divisor in real arithmetic
    elif kind < 0.5:
        c = T / rng.randint(1, 40) * (1 + rng.choice([-1, 1]) * rng.choice([1e-15, 1e-12, 1e-9, 1e-6]))
    elif kind < 0.6:
        c = round(rng.uniform(0.05, 1.0), 3)            # more than one event per year
    else:
        c = round(rng.uniform(0.5, 150.0), rng.choice([0, 1, 2, 6]))
    return T, max(c, 0.01)


class ClosedFormTests(unittest.TestCase):
    def test_renewal_count_equals_counting(self):
        rng = random.Random(1)
        for _ in range(200000):
            T, c = periods(rng)
            self.assertEqual(cf.renewal_count(T, c), len(periodic_events(T, c)), (T, c))
        self.assertEqual(cf.renewal_count(60.0, None), 0)
        self.assertEqual(cf.renewal_count(60.0, 60.0), 0)
        self.assertEqual(cf.renewal_count(60.0, 20.0), 2)
        self.assertEqual(cf.renewal_count(60.000001, 20.0), 3)

    def test_skip_weight(self):
        rng = random.Random(2)
        for _ in range(100000):
            T, c = periods(rng)
            events = periodic_events(T, c)
            w = year_weights(T)
            naive = sum(w[y] for y in {event_year(t) for t in events})
            self.assertTrue(close(cf.skip_weight_periodic(T, c, len(events)), naive), (T, c))
            self.assertTrue(close(cf.skip_weight_events(T, events), naive), (T, c))

    def test_linear_weighted_sum(self):
        rng = random.Random(3)
        for _ in range(20000):
            T, _ = periods(rng)
            base, slope = rng.uniform(0, 1e6), rng.choice([0.0, rng.uniform(-1e3, 1e3)])
            w = year_weights(T)
            naive = sum(w[k + 1] * (base + slope * k) for k in range(len(w) - 1))
            self.assertTrue(close(cf.linear_weighted_sum(T, base, slope), naive, 1e-10), (T, base, slope))

    def test_grid_cumulative(self):
        rng = random.Random(4)
        for _ in range(20000):
            T, _ = periods(rng)
            Y = math.ceil(T)
            start = rng.uniform(0.1, 1.0)
            kind = rng.choice(["CONSTANT", "LINEAR_DECLINE_TO_FLOOR", "STEPWISE"])
            floor = start * rng.uniform(0.0, 1.0)
            decline = rng.choice([0.0, start / rng.randint(1, 200), rng.uniform(0, 0.05), (start - floor) / rng.randint(1, 80)])
            steps = [types.SimpleNamespace(from_index=0, value=start)]
            idx = 0
            for _ in range(rng.randint(0, 5)):
                idx += rng.randint(1, 30)
                steps.append(types.SimpleNamespace(from_index=idx, value=rng.uniform(0, 1)))
            grid = types.SimpleNamespace(kind=kind, start=start, floor=floor, annual_decline=decline, steps=steps)
            if kind == "CONSTANT":
                table = [start] * Y
            elif kind == "LINEAR_DECLINE_TO_FLOOR":
                table = [max(floor, start - decline * k) for k in range(Y)]
            else:
                table = [[s.value for s in steps if s.from_index <= k][-1] for k in range(Y)]
            w = year_weights(T)
            naive = sum(w[k + 1] * table[k] for k in range(Y))
            self.assertTrue(close(cf.grid_cumulative(T, grid), naive, 1e-10), (T, kind, start, floor, decline))
        self.assertIsNone(cf.grid_cumulative(60.0, types.SimpleNamespace(kind="TABLE")))

    def test_refrigerant_device(self):
        rng = random.Random(5)
        for _ in range(40000):
            T, c = periods(rng)
            w = year_weights(T)
            m0, rate, top_up = rng.uniform(0.1, 100), rng.choice([0.0, 1.0, rng.uniform(0, 0.3)]), rng.random() < 0.5
            if rng.random() < 0.5:
                events = periodic_events(T, max(c, 0.3))
            else:
                events = sorted(float(rng.randint(1, max(1, math.ceil(T) - 1))) for _ in range(rng.randint(0, 6)))
                events = [t for t in events if 0 < t < T]
            years = [event_year(t) for t in events]
            # the loop of the reference calculation
            count = {}
            for y in years:
                count[y] = count.get(y, 0) + 1
            m, leaked, before = m0, 0.0, []
            for y in range(1, len(w)):
                leak = m * rate * w[y]
                leaked += leak
                if not top_up:
                    m -= leak
                for _ in range(count.get(y, 0)):
                    before.append(m)
                    m = m0
            got_leak, got_before, got_end = cf.refrigerant_device(T, m0, rate, top_up, years)
            self.assertTrue(close(got_leak, leaked, 1e-9), (T, m0, rate, top_up, years))
            self.assertEqual(len(got_before), len(before))
            self.assertTrue(all(close(a, b, 1e-9) for a, b in zip(got_before, before)))
            self.assertTrue(close(got_end, m, 1e-9))


if __name__ == "__main__":
    unittest.main()
