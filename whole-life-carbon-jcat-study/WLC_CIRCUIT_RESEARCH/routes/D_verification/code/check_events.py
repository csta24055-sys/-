"""D checklist 2 & 3: simultaneous events (P1 ledgers), naive sequential processing,
clock restart after renovation, P2 rate-change precedence and the year-cell rounding
alternative. Oracle-only (no route code imported).

Run: PYTHONDONTWRITEBYTECODE=1 python3 -B code/check_events.py
"""
import itertools, json, os, random, sys
from fractions import Fraction as F
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import oracle_d as O  # noqa: E402

OUT = os.path.join(HERE, "..", "results")


def p1_ledgers():
    res = {}
    for pol in ("substitute", "additional"):
        ev, _ = O.ledger("P1", pol)
        keys = [e.key() for e in ev]
        at20 = sorted((e.item, str(e.amount), e.ledger) for e in ev if e.time == 20)
        # order invariance: shuffle the raw ledger (before supersession) many times
        raw = O.item_events("AC", 10, 20, [0, 20]) + O.item_events("PIPE", 20, 35, [0, 20])
        sup = [e.key() for e in raw if e.time == 20] if pol == "substitute" else []
        raw.append(O.Event(20, "RENOV", 50, "renovation", sup))
        rng = random.Random(1)
        vals = set()
        for _ in range(200):
            rr = raw[:]; rng.shuffle(rr)
            kept = O.apply_supersession(rr)
            vals.add(F(100) + 80 + sum((e.amount for e in kept if e.time <= 20), F(0)))
        res[pol] = {
            "events_at_20": at20,
            "duplicate_item_time_pairs": len(keys) - len(set(keys)),
            "G": {t: O.dec(O.G("P1", t, O.RIGHT, pol)) for t in ("19.999999", "20", "20.000001", "30", "40", "60")},
            "G_left_20": O.dec(O.G("P1", 20, O.LEFT, pol)),
            "G_orig_20": O.dec(O.G("P1", 20, O.ORIG, pol)),
            "G20_over_200_random_ledger_orders": sorted(O.dec(v) for v in vals),
            "next_AC_after_20": str(min(e.time for e in ev if e.item == "AC" and e.time > 20)),
            "next_PIPE_after_20": str(min(e.time for e in ev if e.item == "PIPE" and e.time > 20)),
        }
    naive = {"-".join(o): O.dec(O.naive_sequential_G20(o)) for o in itertools.permutations(["RENOV", "AC", "PIPE"])}
    res["naive_sequential_G20_by_order"] = naive
    res["naive_distinct_values"] = sorted(set(naive.values()), key=lambda s: F(s))
    # restart semantics probe: renovation at a NON-coincident time 15 (declared here, P1')
    p1p = {}
    for pol in ("substitute", "additional"):
        ev, _ = O.ledger("P1", pol, tau_R=F(15))
        p1p[pol] = {"events_le_60": sorted((str(e.time), e.item) for e in ev if e.time <= 60),
                    "G": {t: O.dec(O.G("P1", t, O.RIGHT, pol, tau_R=F(15))) for t in ("15", "20", "25", "35", "60")}}
    res["P1prime_renovation_at_15_declared_by_D"] = p1p
    res["P1prime_note"] = ("At a non-coincident renovation time nothing is superseded, so substitute == additional; "
                           "clocks restart at 15: AC 25,35,...; PIPE 35,55. This is a D-declared variant, not 07/architecture.")
    return res


def p2_checks():
    res = {"declared": {t: O.dec(O.G("P2", t)) for t in ("9.5", "9.999999", "10", "10.000001", "20", "30", "40", "60")},
           "left": {t: O.dec(O.G("P2", t, O.LEFT)) for t in ("10", "20", "10.000001")}}
    # alternative 1: year-cell rounding, rate switch in the event's year cell k=ceil(tau(1-eps))-1=9
    def yearcell(t):
        t = F(t)
        k = 9   # cell index of tau=10 in the original convention (max(1,ceil(10(1-eps)))-1)
        op = 4 * min(t, F(k)) + 3 * max(t - k, F(0))
        ev, _ = O.ledger("P0")
        return F(100) + op + sum((e.amount for e in ev if e.time <= t), F(0))
    # alternative 2: rate switch applied one event late (switch at second AC event, t=20)
    def late(t):
        t = F(t)
        op = 4 * min(t, F(20)) + 3 * max(t - 20, F(0))
        ev, _ = O.ledger("P0")
        return F(100) + op + sum((e.amount for e in ev if e.time <= t), F(0))
    res["alt_year_cell_rounding"] = {t: O.dec(yearcell(t)) for t in ("9.5", "10", "20", "30", "40", "60")}
    res["alt_switch_late"] = {t: O.dec(late(t)) for t in ("10", "20", "30", "40", "60")}
    res["note"] = ("Routes A and E report P2 = 160/245/295/380/515 at 10/20/30/40/60, equal to 'declared' and "
                   "different from year-cell rounding (159/244/294/379/514) and late switch -> no silent rounding.")
    return res


def main():
    res = {"P1": p1_ledgers(), "P2": p2_checks()}
    os.makedirs(OUT, exist_ok=True)
    json.dump(res, open(os.path.join(OUT, "events_check.json"), "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
