"""CF3: state changes on the SAME circuit by parameter change only.

Every expected value comes from a small independent ledger written in this file (explicit
schedules and year loops in the TEST, never in the adapter/model)."""
import itertools
import math
import unittest
from fractions import Fraction as F

from _util import save

from model import hiddenness, schema_signature, simulate, state_counts

EPS = F(1, 10 ** 9)


def inside(tau, T, conv):
    if conv == "right":
        return tau <= T
    if conv == "left":
        return tau < T
    return tau < T * (1 - EPS)


def year_of(tau, conv):
    e = EPS if conv == "original" else 0
    return max(1, math.ceil(tau * (1 - e)))


def schedule(period, explicit=(), policy="restart", subs=(), horizon=F(200)):
    """True-time item schedule. Returns (packet_times, renewal_times)."""
    packets, renewals = [], []
    base = F(0)
    restarts = sorted(set([F(x) for x in explicit] if policy == "restart" else []) | set(F(x) for x in subs))
    explicit_set = set(F(x) for x in explicit)
    subs_set = set(F(x) for x in subs)
    pending_explicit = sorted(explicit_set) if policy == "keep" else []
    t = F(0)
    while True:
        nxt = base + period if period else None
        cand = [x for x in restarts if x > t]
        r = cand[0] if cand else None
        options = [x for x in (nxt, r) if x is not None]
        if not options:
            break
        now = min(options)
        if now > horizon:
            break
        is_periodic = nxt is not None and now == nxt
        is_explicit = now in explicit_set and policy == "restart"
        is_sub = now in subs_set
        if (is_periodic or is_explicit) and not is_sub:
            packets.append(now)
        renewals.append(now)
        if r is not None and now == r:
            base = now
        elif is_periodic:
            base = now
        t = now
    for x in pending_explicit:                       # 'keep': explicit events without restart
        if x not in packets:
            packets.append(x)
            renewals.append(x)
    return sorted(packets), sorted(set(renewals))


def total(T, conv, init=0, rate=0, items=()):
    T = F(T)
    out = F(0)
    if init and inside(F(0), T, conv):
        out += init
    out += rate * T
    for amount, packets in items:
        out += amount * sum(1 for p in packets if inside(p, T, conv))
    return out


class CF3(unittest.TestCase):
    def test_noninteger_periods(self):
        per = {"a": (1, F(1, 10)), "b": (2, F(7, 10)), "c": (5, F(10, 3))}
        scn = {"items": [{"id": k, "amount": a, "period": c, "stage": "B4"} for k, (a, c) in per.items()]}
        Ts = [F(1), F(10, 3), F(7, 2), F(7), F(10)]
        rows = {}
        for conv in ("right", "left", "original"):
            r = simulate(scn, Ts, conv)
            for T in Ts:
                exp = total(T, conv, items=[(a, schedule(c)[0]) for a, c in per.values()])
                self.assertEqual(r["by_T"][T]["C"], exp, (conv, T))
                rows.setdefault(str(T), {})[conv] = str(exp)
            if conv == "right":
                for k, (a, c) in per.items():
                    self.assertEqual(r["events"][k], [c * n for n in range(1, math.floor(10 / c) + 1)])
        save("cf3_noninteger_periods.json", rows)

    def test_simultaneous_set_order_invariance(self):
        items = [{"id": "A", "amount": 20, "period": 10, "stage": "B4"},
                 {"id": "B", "amount": 35, "period": 20, "stage": "B4"},
                 {"id": "C", "amount": 3, "period": 5, "stage": "B4"}]
        base = None
        for perm in itertools.permutations(items):
            scn = {"initial": [{"id": "i", "amount": 100, "stage": "A"}], "flows": [{"id": "op", "rate": 4, "stage": "B6"}],
                   "items": list(perm)}
            r = simulate(scn, [10, 20, 40], "right")
            res = ({T: v["C"] for T, v in r["by_T"].items()}, {k: tuple(v) for k, v in r["events"].items()})
            if base is None:
                base = res
                sim = r["sim"]
            self.assertEqual(res, base)
        self.assertEqual(base[0][F(40)], 100 + 160 + 4 * 20 + 2 * 35 + 8 * 3)
        # at t = 20 the three packet sequencers start in ONE logic delta (contiguous in the log)
        idx = [i for i, e in enumerate(sim.sol.events) if e["type"] == "seq" and e["t"] == "20" and e["name"].startswith("pk.it.")]
        self.assertEqual(len(idx), 3)
        self.assertTrue(all(sim.sol.events[i]["type"] == "seq" for i in range(idx[0], idx[-1] + 1)))
        save("cf3_simultaneous.json", {"C": {str(k): str(v) for k, v in base[0].items()}, "events": {k: [str(x) for x in v] for k, v in base[1].items()}})

    def test_explicit_early_replacement(self):
        out = {}
        for policy, expect in (("restart", [7, 17, 27, 37]), ("keep", [7, 10, 20, 30, 40])):
            scn = {"items": [{"id": "A", "amount": 20, "period": 10, "explicit": [7], "explicit_policy": policy, "stage": "B4"}]}
            pk, _ = schedule(F(10), [7], policy)
            self.assertEqual([p for p in pk if p <= 40], [F(x) for x in expect])
            for conv in ("right", "original"):
                Ts = [F(7), F(17), F(20), F(27), F(40)]
                r = simulate(scn, Ts, conv)
                for T in Ts:
                    self.assertEqual(r["by_T"][T]["C"], total(T, conv, items=[(20, pk)]), (policy, conv, T))
                if conv == "right":
                    self.assertEqual(r["events"]["A"], [F(x) for x in expect])
                    out[policy] = [str(x) for x in r["events"]["A"]]
        save("cf3_explicit_replacement.json", out)

    def test_degradation_resets_at_replacement(self):
        delta = F(1, 2)
        rows = {}
        for explicit in ([], [7]):
            scn = {"flows": [{"id": "op", "rate": 4, "stage": "B6", "degradation": {"item": "A", "slope": delta}}],
                   "items": [{"id": "A", "amount": 20, "period": 10, "explicit": explicit, "stage": "B4"}]}
            _, ren = schedule(F(10), explicit)
            Ts = [F(5), F(7), F(10), F(23, 2), F(25)]
            r = simulate(scn, Ts, "right")
            for T in Ts:
                pts = [F(0)] + [x for x in ren if x < T] + [T]
                deg = sum((delta * (b - a) ** 2 / 2 for a, b in zip(pts[:-1], pts[1:])), F(0))
                self.assertEqual(r["by_T"][T]["stages"]["B6"], 4 * T + deg, (explicit, T))
                rows[f"explicit={explicit} T={T}"] = str(4 * T + deg)
        save("cf3_degradation.json", rows)

    def test_efficiency_change_after_replacement(self):
        scn = {"flows": [{"id": "op", "rate": 4, "rate_after": 3, "switch_on": "A", "stage": "B6"}],
               "items": [{"id": "A", "amount": 20, "period": 10, "stage": "B4"}]}
        Ts = [F(5), F(10), F(15), F(30)]
        r = simulate(scn, Ts, "right")
        for T in Ts:
            self.assertEqual(r["by_T"][T]["stages"]["B6"], 4 * min(T, 10) + 3 * max(F(0), T - 10))
        save("cf3_efficiency_change.json", {str(T): str(r["by_T"][T]["stages"]["B6"]) for T in Ts})

    def _repair_ledger(self, T, conv, period, base, rate, explicit=()):
        T = F(T)
        pk, _ = schedule(F(period), explicit)
        skip = {year_of(t, conv) for t in pk if inside(t, T, conv)}
        tot = F(0)
        for y in range(1, math.ceil(T) + 1):
            if y in skip:
                continue
            tot += base * rate * min(F(1), T - (y - 1))
        return tot

    def test_repair_year_exclusion(self):
        rows = {}
        cases = [(F(5, 2), [F("7.4"), F("7.6"), F(10), F("10.5"), F(25)]),
                 (F(1, 2), [F("2.5"), F(3), F("3.5"), F("4.25")]),
                 (F(10), [F("9.999999"), F(10), F("10.000001"), F("10.5"), F(30)]),
                 (F(7, 10), [F(1), F("2.8"), F("3.5"), F(7)])]
        for period, Ts in cases:
            scn = {"items": [{"id": "A", "amount": 20, "period": period, "stage": "B4",
                              "repair": {"base": 20, "rate": F(1, 20), "stage": "B3"}}]}
            for conv in ("right", "left", "original"):
                r = simulate(scn, Ts, conv)
                for T in Ts:
                    exp = self._repair_ledger(T, conv, period, 20, F(1, 20))
                    self.assertEqual(r["by_T"][T]["stages"]["B3"], exp, (str(period), conv, str(T)))
                    rows.setdefault(str(period), {}).setdefault(conv, {})[str(T)] = str(exp)
                # the year each event belongs to, read from boolean logs
                yrs = [e["year"] for e in r["group_events"]["g0"]]
                pk, _ = schedule(period)
                self.assertEqual(yrs, [year_of(t, conv) for t in pk[:len(yrs)]])
        # two items in one group (same period): exclusion is per group, amplitudes add
        scn = {"items": [{"id": "A", "amount": 20, "period": F(5, 2), "stage": "B4", "repair": {"base": 20, "rate": F(1, 20), "stage": "B3"}},
                         {"id": "B", "amount": 10, "period": F(5, 2), "stage": "B4", "repair": {"base": 40, "rate": F(1, 10), "stage": "B3"}}]}
        r = simulate(scn, [F(25)], "original")
        self.assertEqual(r["by_T"][F(25)]["stages"]["B3"], self._repair_ledger(25, "original", F(5, 2), 1, 5))
        self.assertEqual(len(r["built"].group_signals), 1)
        save("cf3_repair_exclusion.json", rows)

    def test_renovation_policies(self):
        rows = {}
        for year in (20, 25):
            for policy in ("substituted", "additional"):
                scn = {"initial": [{"id": "i", "amount": 100, "stage": "A"}], "flows": [{"id": "op", "rate": 4, "stage": "B6"}],
                       "items": [{"id": "A", "amount": 20, "period": 10, "stage": "B4"},
                                 {"id": "B", "amount": 35, "period": 20, "stage": "B4"}],
                       "renovations": [{"id": "R", "amount": 50, "years": [year], "replaces": ["A", "B"], "policy": policy, "stage": "B5"}]}
                subs = [year] if policy == "substituted" else []
                pkA, _ = schedule(F(10), subs=subs)
                pkB, _ = schedule(F(20), subs=subs)
                Ts = [F(year), F(30), F(40), F(50)]
                for conv in ("right", "original"):
                    r = simulate(scn, Ts, conv)
                    for T in Ts:
                        exp = total(T, conv, init=100, rate=4, items=[(20, pkA), (35, pkB), (50, [F(year)])])
                        self.assertEqual(r["by_T"][T]["C"], exp, (year, policy, conv, T))
                        rows[f"{year}/{policy}/{conv}/T={T}"] = str(exp)
                    if conv == "right":
                        self.assertEqual(r["events"]["A"], [p for p in pkA if p <= 50])
                        self.assertEqual(r["events"]["B"], [p for p in pkB if p <= 50])
        save("cf3_renovation.json", rows)

    def test_same_cell_catalogue_and_counts(self):
        """All CF2/CF3 variants use cells from one fixed catalogue; h stays 0."""
        scns = {
            "pilot": {"initial": [{"id": "i", "amount": 100, "stage": "A"}], "flows": [{"id": "op", "rate": 4, "stage": "B6"}],
                      "items": [{"id": "A", "amount": 20, "period": 10, "stage": "B4"}, {"id": "B", "amount": 35, "period": 20, "stage": "B4"}]},
            "full": {"initial": [{"id": "i", "amount": 100, "stage": "A"}],
                     "flows": [{"id": "op", "rate": 4, "rate_after": 3, "switch_on": "A", "stage": "B6"},
                               {"id": "dg", "rate": 0, "stage": "B6", "degradation": {"item": "B", "slope": F(1, 2)}}],
                     "items": [{"id": "A", "amount": 20, "period": F(5, 2), "explicit": [7], "stage": "B4",
                                "repair": {"base": 20, "rate": F(1, 20), "stage": "B3"}},
                               {"id": "B", "amount": 35, "period": F(10, 3), "stage": "B4"}],
                     "renovations": [{"id": "R", "amount": 50, "years": [25], "replaces": ["A", "B"], "policy": "substituted", "stage": "B5"}]},
        }
        out = {}
        catalogue = set()
        for name, scn in scns.items():
            r = simulate(scn, [30], "original")
            h = hiddenness(r["built"])
            self.assertEqual(h["W_out"], 0, h["grey_items"])
            sig = schema_signature(r["built"])
            catalogue |= {ct for ct, _ in sig}
            out[name] = {"C(30)": str(r["by_T"][F(30)]["C"]), "hiddenness": {k: (str(v) if isinstance(v, F) else v) for k, v in h.items()},
                         "state_counts": state_counts(r["built"]), "signature": sorted(map(str, sig))}
        self.assertTrue(catalogue <= {"rails", "timebase", "bus", "packet", "flow", "age", "clock", "explicit",
                                      "repair_amp", "yearcell"})
        save("cf3_catalogue_counts.json", out)


if __name__ == "__main__":
    unittest.main()
