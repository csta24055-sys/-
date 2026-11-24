"""CF2 minimal pilot from primitive inputs only (100 initial, 4 /yr, A 20 every 10 y,
B 35 every 20 y). The engine's integrate-and-fire clocks discover the event times.
Expected values come from a small independent ledger written here (integer loops in the
TEST only), never from the engine or the adapter."""
import unittest
from fractions import Fraction as F

from _util import audit_dump, save

from adapter import Units
from model import hiddenness, schema_signature, simulate, state_counts

PILOT = {"initial": [{"id": "init", "amount": 100, "stage": "A1-A3"}],
         "flows": [{"id": "op", "rate": 4, "stage": "B6"}],
         "items": [{"id": "A", "amount": 20, "period": 10, "stage": "B4"},
                   {"id": "B", "amount": 35, "period": 20, "stage": "B4"}]}
EPS = F(1, 10 ** 9)
POINTS = ["0", "1", "9.999999", "10", "10.000001", "19.999999", "20", "20.000001", "30", "40", "60"]


def ledger(T, conv):
    """Independent reference for the pilot."""
    T = F(T)
    def inside(tau):
        if conv == "right":
            return tau <= T
        if conv == "left":
            return tau < T
        return tau < T * (1 - EPS)
    total = F(0)
    if inside(F(0)):
        total += 100
    total += 4 * T
    for amt, c in ((20, 10), (35, 20)):
        n = 1
        while inside(F(n * c)):
            total += amt
            n += 1
    return total


class Pilot(unittest.TestCase):
    def test_headline_values(self):
        exp = {"right": [160, 255, 315, 410], "left": [140, 200, 295, 355], "original": [140, 200, 295, 355]}
        out = {}
        for conv, vals in exp.items():
            r = simulate(PILOT, [10, 20, 30, 40], conv)
            got = [r["by_T"][F(T)]["C"] for T in (10, 20, 30, 40)]
            self.assertEqual(got, vals, conv)
            out[conv] = [str(x) for x in got]
        save("pilot_headline.json", out)

    def test_contract_boundary_points(self):
        rows = {}
        for conv in ("right", "left", "original"):
            pts = [p for p in POINTS if not (conv == "original" and p == "0")]
            r = simulate(PILOT, [F(p) for p in pts], conv)
            for p in pts:
                got = r["by_T"][F(p)]["C"]
                self.assertEqual(got, ledger(p, conv), (conv, p))
                rows.setdefault(p, {})[conv] = str(got)
        save("pilot_boundary_points.json", {"points": rows, "note": "original convention: domain 0<T; T=0 not evaluated"})

    def test_event_discovery_and_stages(self):
        r = simulate(PILOT, [60], "original")
        evA = r["events"]["A"]
        self.assertEqual(evA, [F(10 * n) / (1 - EPS) for n in range(1, 6)])   # fire at tau/(1-eps)
        r2 = simulate(PILOT, [60], "right")
        self.assertEqual(r2["events"]["A"], [F(10 * n) for n in range(1, 7)])
        self.assertEqual(r2["events"]["B"], [F(20 * n) for n in range(1, 4)])
        st = r2["by_T"][F(60)]["stages"]
        self.assertEqual(st, {"A1-A3": 100, "B6": 240, "B4": 6 * 20 + 3 * 35})
        years = r2["group_events"]
        self.assertEqual([e["year"] for e in years["g0"]], [10 * n for n in range(1, 7)])
        save("pilot_events.json", {"original_A_fire_times": [str(x) for x in evA],
                                   "right_A": [str(x) for x in r2["events"]["A"]],
                                   "right_B": [str(x) for x in r2["events"]["B"]],
                                   "stages_T60_right": {k: str(v) for k, v in st.items()},
                                   "group_events_right": {g: [{"t": str(e["t"]), "year": e["year"]} for e in v] for g, v in years.items()}})

    def test_single_rail_joule_audit(self):
        r = simulate(PILOT, [F(1, 2), 10, 20, F(333, 10), 40], "right")
        rows = {}
        for T, v in r["by_T"].items():
            self.assertEqual(v["datapath_heat"], v["V0_Q"], T)      # E = V0 * Q exactly
            rows[str(T)] = {"heat": str(v["datapath_heat"]), "V0Q": str(v["V0_Q"])}
        # same with another rail voltage: heat scales with V0, emissions do not
        u = Units(V0=F(5))
        r5 = simulate(PILOT, [40], "right", units=u)
        self.assertEqual(r5["by_T"][F(40)]["C"], 410)
        self.assertEqual(r5["by_T"][F(40)]["datapath_heat"], 5 * r5["by_T"][F(40)]["Q_total"])
        save("pilot_joule_audit.json", {"single_rail": rows, "V0=5_T40_heat": str(r5["by_T"][F(40)]["datapath_heat"])})

    def test_rescaling_invariance(self):
        res = []
        for u in (Units(), Units(gamma=F(1, 1000), V0=F(5), tau_y=F(3600)), Units(gamma=F(7), V0=F(1, 2), tau_y=F(1, 10))):
            for conv in ("right", "original"):
                r = simulate(PILOT, [F("9.999999"), 10, F("20.000001"), 40], conv, units=u)
                res.append((conv, [r["by_T"][T]["C"] for T in sorted(r["by_T"])], r["events"]["A"]))
        for conv in ("right", "original"):
            sel = [x for x in res if x[0] == conv]
            for x in sel[1:]:
                self.assertEqual(x[1], sel[0][1])
                self.assertEqual(x[2], sel[0][2])
        save("pilot_rescaling.json", [{"conv": c, "C": [str(v) for v in vals], "A_events": [str(e) for e in ev]} for c, vals, ev in res])

    def test_full_solution_dump_and_residuals(self):
        for conv in ("right", "original"):
            r = simulate(PILOT, [10, 20, 30, 40], conv, record=True)
            d = r["sim"].dump()
            s = audit_dump(self, d)
            save(f"pilot_full_solution_{conv}.json", {"audit": s, "dump": d})

    def test_hiddenness_and_counts(self):
        r = simulate(PILOT, [40], "right")
        h = hiddenness(r["built"])
        self.assertEqual(h["W_out"], 0)
        self.assertEqual(h["h"], 0)
        sc = state_counts(r["built"])
        sig = schema_signature(r["built"])
        sigs = set()
        for conv in ("right", "left", "original"):
            for u in (Units(), Units(gamma=F(3), V0=F(2), tau_y=F(5))):
                sigs.add(schema_signature(simulate(PILOT, [40], conv, units=u)["built"]))
        perm = dict(PILOT, items=list(reversed(PILOT["items"])))
        sigs.add(schema_signature(simulate(perm, [40], "right")["built"]))
        self.assertEqual(len(sigs), 1)
        save("pilot_audit_counts.json", {"hiddenness": h, "state_counts": sc,
                                         "schema_signature": sorted(map(str, sig))})


if __name__ == "__main__":
    unittest.main()
