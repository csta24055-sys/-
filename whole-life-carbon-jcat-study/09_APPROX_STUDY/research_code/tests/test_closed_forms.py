"""Closed forms against the loops they replace (random and adversarial inputs).

Run:  cd research_code && python3 -m unittest tests.test_closed_forms -v
"""
import math
import random
import types
import unittest

from fastcalc import closed_forms as cf
from refcalc.base import event_year, grid_values, grid_well_formed, periodic_events, year_weights


def close(a, b, tol=1e-11):
    return abs(a - b) <= tol * max(abs(a), abs(b), 1e-300) or abs(a - b) <= 1e-12


def periods(rng):
    """Study periods and cycles, including exact divisors, decimal pairs and knife-edge floats."""
    T = rng.choice([0.5, 1.0, 10.5, 30.0, 50.0, 55.5, 60.0, 60.000001, 62.5, 75.0, 99.9, 100.0, 0.3, 12.3,
                    round(rng.uniform(0.2, 120), 3)])
    kind = rng.random()
    if kind < 0.35:
        c = T / rng.randint(1, 40)                      # exact divisor in real arithmetic
    elif kind < 0.5:
        c = T / rng.randint(1, 40) * (1 + rng.choice([-1, 1]) * rng.choice([1e-15, 1e-12, 1e-10, 1e-8, 1e-6]))
    elif kind < 0.6:
        c = round(rng.uniform(0.05, 1.0), 3)            # more than one event per year
    elif kind < 0.7:
        c = rng.choice([33.3, 11.1, 16.65, 0.3, 2.2, 18.5, 0.1, 1.2, 7.5, 4.1, 1.23])
    else:
        c = round(rng.uniform(0.5, 150.0), rng.choice([0, 1, 2, 6]))
    return T, max(c, 0.01)


def random_grid(rng, well_formed=True):
    start = rng.uniform(0.1, 1.0)
    kind = rng.choice(["CONSTANT", "LINEAR_DECLINE_TO_FLOOR", "STEPWISE"])
    floor = start * rng.uniform(0.0, 1.0)
    decline = rng.choice([0.0, start / rng.randint(1, 200), rng.uniform(0, 0.05), (start - floor) / rng.randint(1, 80)])
    steps = [types.SimpleNamespace(from_index=0, value=start)]
    idx = 0
    for _ in range(rng.randint(0, 5)):
        idx += rng.randint(1, 30)
        steps.append(types.SimpleNamespace(from_index=idx, value=rng.uniform(0, 1)))
    grid = types.SimpleNamespace(kind=kind, start=start, floor=floor, annual_decline=decline, steps=steps, table=[])
    if not well_formed:
        what = rng.choice(["rising", "below_floor", "unsorted", "late", "empty", "kind", "none"])
        if what == "rising":
            grid.kind, grid.annual_decline = "LINEAR_DECLINE_TO_FLOOR", -0.01
        elif what == "below_floor":
            grid.kind, grid.floor = "LINEAR_DECLINE_TO_FLOOR", start * 2
        elif what == "unsorted":
            grid.kind, grid.steps = "STEPWISE", list(reversed(steps)) if len(steps) > 1 else []
        elif what == "late":
            grid.kind = "STEPWISE"
            steps[0].from_index = 2
        elif what == "empty":
            grid.kind, grid.steps = "STEPWISE", []
        elif what == "kind":
            grid.kind = "SPLINE"
        else:
            grid.kind, grid.start = "CONSTANT", None
    return grid


class ClosedFormTests(unittest.TestCase):
    def test_renewal_count_equals_counting(self):
        rng = random.Random(1)
        for _ in range(200000):
            T, c = periods(rng)
            self.assertEqual(cf.renewal_count(T, c), len(periodic_events(T, c)), (T, c))
        for bad in (None, 0.0, -3.0, float("nan"), float("inf")):
            self.assertEqual(cf.renewal_count(60.0, bad), 0)
            self.assertEqual(periodic_events(60.0, bad), [])
        self.assertEqual(cf.renewal_count(60.0, 60.0), 0)
        self.assertEqual(cf.renewal_count(60.0, 20.0), 2)
        self.assertEqual(cf.renewal_count(60.000001, 20.0), 3)

    def test_event_at_the_end_is_not_counted_for_decimal_inputs(self):
        """3 * 33.3 is 99.9 in decimal but slightly less in binary: it must not count."""
        for T, c, expected in ((99.9, 33.3, 2), (99.9, 11.1, 8), (60.0, 0.1, 599), (12.3, 4.1, 2), (0.3, 0.1, 2)):
            self.assertEqual(len(periodic_events(T, c)), expected, (T, c))
            self.assertEqual(cf.renewal_count(T, c), expected, (T, c))
        self.assertEqual(event_year(25 * 2.2), 55)       # 55.00000000000001 belongs to year 55
        self.assertEqual(cf.event_year(25 * 2.2), 55)

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

    def test_grid_moments(self):
        rng = random.Random(4)
        for i in range(30000):
            T, _ = periods(rng)
            Y = math.ceil(T)
            grid = random_grid(rng, well_formed=i % 4 != 0)
            segments = cf.grid_segments(grid, Y)
            self.assertEqual(segments is not None, grid_well_formed(grid), vars(grid))
            if segments is None:
                continue
            values = grid_values(grid, Y)                # the year loop of the reference calculation
            w = year_weights(T)
            g_naive = sum(w[k + 1] * values[k] for k in range(Y))
            h_naive = sum(w[k + 1] * k * values[k] for k in range(Y))
            G, H = cf.segment_moments(segments, T)
            self.assertTrue(close(G, g_naive, 1e-10), (T, vars(grid)))
            self.assertTrue(close(H, h_naive, 1e-10), (T, vars(grid)))
            Gt, Ht = cf.table_moments(values, T)
            self.assertTrue(close(Gt, g_naive, 1e-12) and close(Ht, h_naive, 1e-12))

    def test_refrigerant_fractions(self):
        rng = random.Random(5)
        for _ in range(40000):
            T, c = periods(rng)
            w = year_weights(T)
            rate = rng.choice([0.0, 1.0, 1e-12, 1e-9, 1e-7, 1e-4, rng.uniform(0, 0.3)])
            top_up = rng.random() < 0.5
            if rng.random() < 0.5:
                events = periodic_events(T, max(c, 0.3))
            else:
                events = sorted(float(rng.randint(1, max(1, math.ceil(T) - 1))) for _ in range(rng.randint(0, 6)))
                events = [t for t in events if 0 < t < T * (1 - 1e-9)]
            years = [event_year(t) for t in events]
            count = {}
            for y in years:
                count[y] = count.get(y, 0) + 1
            m, leaked, before = 1.0, 0.0, []             # the loop of the reference calculation, per unit of charge
            for y in range(1, len(w)):
                leak = m * rate * w[y]
                leaked += leak
                if not top_up:
                    m -= leak
                for _ in range(count.get(y, 0)):
                    before.append(m)
                    m = 1.0
            got_leak, got_before, got_end = cf.refrigerant_fractions(T, rate, top_up, years)
            # relative tolerance on the leaked share itself, also for very small rates
            self.assertTrue(abs(got_leak - leaked) <= 1e-9 * max(abs(leaked), 1e-300), (T, rate, top_up, years, got_leak, leaked))
            self.assertEqual(len(got_before), len(before))
            self.assertTrue(all(close(a, b, 1e-9) for a, b in zip(got_before, before)))
            self.assertTrue(close(got_end, m, 1e-9))


if __name__ == "__main__":
    unittest.main()
