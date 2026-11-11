"""Closed forms against the loops they replace (random and adversarial inputs).

The time rules are checked against literal loops written with ``fractions.Fraction``
(exact rational arithmetic, independent of the integer code under test), for the unified
model's closed forms AND for the counting loop of the reference calculation.

Run:  cd research_code && python3 -m unittest tests.test_closed_forms -v
"""
import math
import random
import types
import unittest
from fractions import Fraction

from fastcalc import closed_forms as cf
from refcalc import base
from refcalc.base import grid_values, grid_well_formed, year_weights

C = Fraction(1.0 - 1e-9)          # the exact value of the double nearest to 1 - 1e-9
KNIFE = 1.000000001               # the double for which period*(1 - 1e-9) rounds to exactly 1.0 in floating point


def close(a, b, tol=1e-11):
    return abs(a - b) <= tol * max(abs(a), abs(b), 1e-300) or abs(a - b) <= 1e-12


def loop_years(T, period):
    """Literal definition: n = 1, 2, ... while n*period < T*c; the event belongs to year max(1, ceil(n*period*c))."""
    limit = Fraction(T) * C
    step = Fraction(period)
    years = []
    n = 1
    while n * step < limit:
        years.append(max(1, math.ceil(n * step * C)))
        n += 1
    return years


def exact_skip_weight(T, years):
    """Sum of the year weights w_y = min(1, T-(y-1)) over the distinct event years, exactly."""
    Tq = Fraction(T)
    return sum(min(Fraction(1), Tq - (y - 1)) for y in set(years))


def neighbours(x, n):
    """x and its n neighbouring doubles on each side."""
    out = [x]
    lo = hi = x
    for _ in range(n):
        lo, hi = math.nextafter(lo, -math.inf), math.nextafter(hi, math.inf)
        out += [lo, hi]
    return out


NEAR_KNIFE = neighbours(KNIFE, 50)


def periods(rng):
    """Study periods and cycles, including exact divisors, decimal pairs and knife-edge floats."""
    T = rng.choice([0.5, 1.0, 10.5, 30.0, 50.0, 55.5, 60.0, 60.000001, 62.5, 75.0, 99.9, 100.0, 0.3, 12.3, 7.0,
                    KNIFE, 29.999999999, round(rng.uniform(0.2, 120), 3)])
    kind = rng.random()
    if kind < 0.30:
        c = T / rng.randint(1, 40)                      # exact divisor in real arithmetic
    elif kind < 0.50:
        c = T / rng.randint(1, 40) * (1 + rng.choice([-1, 1]) * rng.choice([1e-15, 1e-12, 1e-10, 1e-9, 2e-9, 1e-8, 1e-6]))
    elif kind < 0.60:
        c = round(rng.uniform(0.05, 1.0), 3)            # more than one event per year
    elif kind < 0.70:
        c = rng.choice([33.3, 11.1, 16.65, 0.3, 2.2, 18.5, 0.1, 1.2, 7.5, 4.1, 1.23])
    elif kind < 0.80:
        c = rng.randint(1, 12) * (1 + rng.choice([-1, 1]) * 1e-9)   # m*(1 +- 1e-9) for small integers m
    elif kind < 0.85:
        c = rng.choice(NEAR_KNIFE)                      # 1.000000001 and its 50 neighbours on each side
    else:
        c = round(rng.uniform(0.5, 150.0), rng.choice([0, 1, 2, 6]))
    return T, max(c, 0.01)


def adversarial_pairs():
    """(T, period) pairs chosen at the places where rounding could change a count or a year."""
    study = [1.0, 2.0, 7.0, 30.0, 60.0, 99.9, 0.3, 1.5, 10.5, 62.5, KNIFE, 59.999999999, 60.000000001, 100.0]
    out = []
    for T in study:
        for n in (1, 2, 3, 4, 7, 20, 59, 60):
            for eps in (1e-15, 1e-12, 1e-10, 1e-9, 2e-9, 1e-8, 1e-6):
                for sign in (-1, 1):
                    out.append((T, T / n * (1 + sign * eps)))
            out.append((T, T / n))
        for m in range(1, 13):
            out += [(T, m * (1 + 1e-9)), (T, m * (1 - 1e-9)), (T, float(m))]
        for p in (0.999999999, 0.25, 0.3, 0.1, 0.75, 0.007, 0.5000000005, 1 / 3):       # periods below one year
            out.append((T, p))
    for T in (2.0, 7.0, 30.0, 60.0, 99.9, 6.5):
        for p in neighbours(KNIFE, 50):                                                  # 1.000000001 +- 50 doubles
            out.append((T, p))
        for p in neighbours(1.0 / (1.0 - 1e-9), 25) + neighbours(2.0 / (1.0 - 1e-9), 10):   # p*c close to a whole year
            out.append((T, p))
        for p in neighbours(1.0, 10) + neighbours(2.0, 5) + neighbours(0.5, 5):
            out.append((T, p))
    return out


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
        what = rng.choice(["rising", "below_floor", "unsorted", "late", "empty", "kind", "none", "nan", "inf", "negative",
                           "float_index", "bool_index", "step_nan", "negative_floor"])
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
        elif what == "none":
            grid.kind, grid.start = "CONSTANT", None
        elif what == "nan":
            grid.kind = "LINEAR_DECLINE_TO_FLOOR"
            setattr(grid, rng.choice(["start", "floor", "annual_decline"]), float("nan"))
        elif what == "inf":
            grid.kind = rng.choice(["LINEAR_DECLINE_TO_FLOOR", "CONSTANT"])
            grid.start = float("inf")
        elif what == "negative":
            grid.kind, grid.start = "CONSTANT", -0.2
        elif what == "negative_floor":
            grid.kind, grid.floor = "LINEAR_DECLINE_TO_FLOOR", -0.1
        elif what == "float_index":
            grid.kind = "STEPWISE"
            steps[-1].from_index = float(steps[-1].from_index)
        elif what == "bool_index":
            grid.kind = "STEPWISE"
            steps[0].from_index = False
        else:
            grid.kind = "STEPWISE"
            steps[-1].value = rng.choice([float("nan"), float("inf"), -1.0, None])
    return grid


class ExactTimeRuleTests(unittest.TestCase):
    """Counts, years and skip weights are the same numbers as the literal definition, for every input tried."""

    def check_pair(self, T, period):
        years = loop_years(T, period)
        n = len(years)
        self.assertEqual(cf.renewal_count(T, period), n, (T, period))
        self.assertEqual(base.periodic_events(T, period), years, (T, period))       # the reference's counting loop
        self.assertEqual(cf.periodic_years(period, n), years, (T, period))
        if n:
            self.assertEqual(cf.periodic_year(n, period), years[-1], (T, period))
        expected = exact_skip_weight(T, years)
        self.assertLessEqual(abs(Fraction(cf.skip_weight_periodic(T, period, n)) - expected), Fraction(1, 10 ** 12), (T, period))
        self.assertLessEqual(abs(Fraction(cf.skip_weight_years(T, years)) - expected), Fraction(1, 10 ** 12), (T, period))
        if n:
            self.assertLessEqual(years[-1], math.ceil(T), (T, period))              # an event inside never falls after year Y

    def test_adversarial_periods(self):
        pairs = adversarial_pairs()
        self.assertGreater(len(pairs), 3000)
        for T, period in pairs:
            self.check_pair(T, period)

    def test_random_periods(self):
        rng = random.Random(1)
        for _ in range(12000):
            T, period = periods(rng)
            self.check_pair(T, period)

    def test_the_double_1_000000001(self):
        """Its product with (1 - 1e-9) is slightly ABOVE 1, so event n belongs to year n + 1 (the written rule)."""
        self.assertEqual(KNIFE * (1.0 - 1e-9), 1.0)                 # in floating point the product rounds to exactly 1
        self.assertGreater(Fraction(KNIFE) * C, 1)                  # exactly it is above 1
        for T, n_events in ((7.0, 6), (30.0, 29), (60.0, 59), (99.9, 99)):
            years = loop_years(T, KNIFE)
            self.assertEqual(years, list(range(2, n_events + 2)))
            self.assertEqual(cf.renewal_count(T, KNIFE), n_events)
            self.assertEqual(base.periodic_events(T, KNIFE), years)
            self.assertEqual(cf.skip_weight_periodic(T, KNIFE, n_events), float(Fraction(exact_skip_weight(T, years))))

    def test_inside_and_event_year(self):
        rng = random.Random(7)
        times = [0.0, 1.0, 2.0, 55.00000000000001, 25 * 2.2, 59.99999994, 60.0, 1e-300, 5e-324, 1e15, 3, 10, 0]
        times += neighbours(1.0, 20) + neighbours(60.0, 20) + neighbours(60.0 * (1.0 - 1e-9), 20) + neighbours(KNIFE, 20)
        times += [rng.uniform(0, 130) for _ in range(3000)] + [float(rng.randint(0, 130)) for _ in range(300)]
        for T in (0.3, 1.0, 59.999999999, 60.0, 60.000001, 99.9, 60):
            for t in times:
                self.assertEqual(cf.inside(t, T), Fraction(t) < Fraction(T) * C, (t, T))
                self.assertEqual(base.inside(t, T), cf.inside(t, T))
        for t in times:
            year = max(1, math.ceil(Fraction(t) * C))
            self.assertEqual(cf.event_year(t), year, t)
            self.assertEqual(base.event_year(t), year, t)
        for y in range(1, 400):                                       # a whole year (int or float) is its own year
            self.assertEqual(cf.event_year(y), y)
            self.assertEqual(cf.event_year(float(y)), y)

    def test_event_at_the_end_is_not_counted_for_decimal_inputs(self):
        """3 * 33.3 is 99.9 in decimal but not in binary: within a relative 1e-9 of the end it must not count."""
        for T, period, expected in ((99.9, 33.3, 2), (99.9, 11.1, 8), (60.0, 0.1, 599), (12.3, 4.1, 2), (0.3, 0.1, 2),
                                    (60.0, 60.0, 0), (60.0, 20.0, 2), (60.000001, 20.0, 3)):
            self.assertEqual(len(base.periodic_events(T, period)), expected, (T, period))
            self.assertEqual(cf.renewal_count(T, period), expected, (T, period))
        self.assertEqual(base.event_year(25 * 2.2), 55)   # 55.00000000000001 belongs to year 55
        self.assertEqual(cf.event_year(25 * 2.2), 55)

    def test_invalid_periods_give_no_events(self):
        for bad in (None, 0.0, -3.0, float("nan"), float("inf"), float("-inf")):
            self.assertEqual(cf.renewal_count(60.0, bad), 0)
            self.assertEqual(base.periodic_events(60.0, bad), [])
            self.assertFalse(cf.valid_period(bad))
        self.assertTrue(all(base.invalid_period(x) for x in (0.0, -3.0, float("nan"), float("inf"))))
        self.assertFalse(base.invalid_period(None))                    # "not renewed" is not an invalid period
        self.assertFalse(base.invalid_period(12.5))

    def test_explicit_lists(self):
        nan, inf = float("nan"), float("inf")
        entries = [0, 10, 10, 30, None, nan, inf, -inf, -2, 59.99999995, 60, 3.5, 12.25, 61]
        for T in (60.0, 42.5, 12.3):
            want = [max(1, math.ceil(Fraction(t) * C)) for t in entries
                    if t is not None and t == t and abs(t) != inf and t > 0 and Fraction(t) < Fraction(T) * C]
            self.assertEqual(cf.explicit_years(T, entries), want)
            self.assertEqual(base.explicit_events(T, entries), want)
            self.assertLessEqual(abs(Fraction(cf.skip_weight_years(T, want)) - exact_skip_weight(T, want)), Fraction(1, 10 ** 12))
            used = [t for t in entries if base.finite(t) and t > 0 and base.inside(t, T)]
            self.assertEqual(cf.skip_weight_events(T, used), cf.skip_weight_years(T, want))


class ClosedFormTests(unittest.TestCase):
    def test_linear_weighted_sum(self):
        rng = random.Random(3)
        for _ in range(20000):
            T, _ = periods(rng)
            base_, slope = rng.uniform(0, 1e6), rng.choice([0.0, rng.uniform(-1e3, 1e3)])
            w = year_weights(T)
            naive = sum(w[k + 1] * (base_ + slope * k) for k in range(len(w) - 1))
            self.assertTrue(close(cf.linear_weighted_sum(T, base_, slope), naive, 1e-10), (T, base_, slope))

    def test_weighted_sums_just_above_a_whole_year(self):
        """The last year is ADDED with its weight: no digits are lost when its weight is tiny (exact rational check)."""
        for T in (KNIFE, 1.0 + 1e-12, 2.0 + 1e-10, 30.000000001, 60.0 + 1e-9):
            Y = math.ceil(T)
            wl = Fraction(T) - (Y - 1)
            for b, s in ((0.0, 1000.0), (5.0, -0.01), (1e6, 3.0)):
                exact = sum((wl if k == Y - 1 else 1) * (Fraction(b) + Fraction(s) * k) for k in range(Y))
                got = Fraction(cf.linear_weighted_sum(T, b, s))
                self.assertLessEqual(abs(got - exact), abs(exact) * Fraction(1, 10 ** 12), (T, b, s))
            grid = types.SimpleNamespace(kind="LINEAR_DECLINE_TO_FLOOR", start=0.5, floor=0.1, annual_decline=0.01, steps=None, table=[])
            segments = cf.grid_segments(grid, Y)
            values = [max(Fraction(0.1), Fraction(0.5) - Fraction(0.01) * k) for k in range(Y)]
            g_exact = sum((wl if k == Y - 1 else 1) * values[k] for k in range(Y))
            h_exact = sum((wl if k == Y - 1 else 1) * k * values[k] for k in range(Y))
            G, H = cf.segment_moments(segments, T)
            self.assertLessEqual(abs(Fraction(G) - g_exact), abs(g_exact) * Fraction(1, 10 ** 12), T)
            self.assertLessEqual(abs(Fraction(H) - h_exact), abs(h_exact) * Fraction(1, 10 ** 12), T)

    def test_grid_moments(self):
        rng = random.Random(4)
        for i in range(30000):
            T, _ = periods(rng)
            Y = math.ceil(T)
            grid = random_grid(rng, well_formed=i % 4 != 0)
            segments = cf.grid_segments(grid, Y)
            self.assertEqual(segments is not None, grid_well_formed(grid), vars(grid))
            if i % 4 == 0:
                self.assertIsNone(segments, vars(grid))
            if segments is None:
                self.assertIsNone(grid_values(grid, Y))  # no descriptor and an empty table: the grid factor is unusable
                continue
            values = grid_values(grid, Y)                # the year loop of the reference calculation
            flat = []
            for a, b, alpha, beta in segments:
                flat += [alpha + beta * k for k in range(a, b)]
            self.assertEqual(flat, values, vars(grid))   # the segments describe the same series, value for value
            w = year_weights(T)
            g_naive = sum(w[k + 1] * values[k] for k in range(Y))
            h_naive = sum(w[k + 1] * k * values[k] for k in range(Y))
            G, H = cf.segment_moments(segments, T)
            self.assertTrue(close(G, g_naive, 1e-10), (T, vars(grid)))
            self.assertTrue(close(H, h_naive, 1e-10), (T, vars(grid)))
            Gt, Ht = cf.table_moments(values, T)
            self.assertTrue(close(Gt, g_naive, 1e-12) and close(Ht, h_naive, 1e-12))

    def test_grid_descriptor_with_extreme_but_valid_numbers(self):
        """A valid descriptor never raises, whatever the magnitudes (the division is only a first guess)."""
        for start, floor, decline in ((1e308, 0.0, 1e-300), (0.5, 0.5, 1e-320), (0.5, 0.0, 1e308), (5e-324, 0.0, 5e-324)):
            grid = types.SimpleNamespace(kind="LINEAR_DECLINE_TO_FLOOR", start=start, floor=floor, annual_decline=decline,
                                         steps=None, table=[])
            for Y in (1, 3, 60):
                segments = cf.grid_segments(grid, Y)
                flat = []
                for a, b, alpha, beta in segments:
                    flat += [alpha + beta * k for k in range(a, b)]
                self.assertEqual(flat, grid_values(grid, Y))

    def test_table_usable(self):
        nan = float("nan")
        self.assertTrue(cf.table_usable([1.0, 0.0, 2], 3))
        self.assertTrue(cf.table_usable([1.0, 0.0, nan], 2))           # only the first Y entries count
        for bad in ([1.0, 2.0], [1.0, nan, 1.0], [1.0, None, 1.0], [1.0, float("inf"), 1.0], [1.0, -0.5, 1.0]):
            self.assertFalse(cf.table_usable(bad, 3), bad)

    def test_refrigerant_fractions(self):
        rng = random.Random(5)
        for _ in range(40000):
            T, c = periods(rng)
            w = year_weights(T)
            rate = rng.choice([0.0, 1.0, 1e-12, 1e-9, 1e-7, 1e-4, rng.uniform(0, 0.3)])
            top_up = rng.random() < 0.5
            if rng.random() < 0.5:
                years = base.periodic_events(T, max(c, 0.3))
            else:
                events = sorted(float(rng.randint(1, max(1, math.ceil(T) - 1))) for _ in range(rng.randint(0, 6)))
                years = base.explicit_events(T, events)
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

    def test_refrigerant_remainder_after_a_long_cycle(self):
        """The small share left after many years without a charge change keeps its relative precision."""
        for rate, T, change_year in ((0.1469, 129.5, 128), (0.15, 100.0, 99), (0.3, 120.0, 119), (0.05, 300.0, 299)):
            q = 1 - Fraction(rate)
            exact_before = q ** change_year
            leaked, before, end = cf.refrigerant_fractions(T, rate, False, [change_year])
            self.assertLessEqual(abs(Fraction(before[0]) - exact_before), exact_before * Fraction(1, 10 ** 12), (rate, T))
            Y = math.ceil(T)
            wl = Fraction(T) - (Y - 1)
            whole = Y - change_year - (1 if wl < 1 else 0)
            exact_end = q ** whole * (1 - Fraction(rate) * wl if wl < 1 else 1)
            self.assertLessEqual(abs(Fraction(end) - exact_end), exact_end * Fraction(1, 10 ** 12), (rate, T))
            exact_leak = (1 - exact_before) + (1 - exact_end)
            self.assertLessEqual(abs(Fraction(leaked) - exact_leak), exact_leak * Fraction(1, 10 ** 12), (rate, T))


if __name__ == "__main__":
    unittest.main()
