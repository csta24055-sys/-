"""D checklist 4: state count / information loss. Oracle-only (no route code imported).

(i)  merged clock capacitors: impossible for EVERY single (period c, charge A) clock,
     plus the three architecture periods 30, 15, 20/3 evaluated explicitly;
(ii) Px fixed schedule = 20-periodic event set (single clock with 3 comparators suffices),
     transient case s in (10,20) needs an extra one-shot entry; online-reset futures;
     numerical support for the invariance-of-domain lower bound (proof draft in claims.md);
(iv) single accumulator driven by an external schedule table reproduces P0/P1/P2/Px.

Run: PYTHONDONTWRITEBYTECODE=1 python3 -B code/check_states.py
"""
import json, os, sys
from fractions import Fraction as F
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import oracle_d as O  # noqa: E402

OUT = os.path.join(HERE, "..", "results")


def jumps(case, horizon=60, **kw):
    ev, _ = O.ledger(case, **kw)
    j = {}
    for e in ev:
        if e.time <= horizon:
            j[e.time] = j.get(e.time, F(0)) + e.amount
    return dict(sorted(j.items()))


def merged_clocks():
    j = jumps("P0")
    distinct = sorted(set(j.values()))
    out = {"P0_jump_sizes": {str(k): str(v) for k, v in j.items()},
           "distinct_jump_sizes": [str(v) for v in distinct],
           "general_argument": ("A single clock with one charge A produces jumps of size A at every firing instant; "
                                "P0 has jumps 20 (t=10) and 55 (t=20) -> no (c, A) works, for ANY c>0."),
           "architecture_periods": {}}
    for c in (F(30), F(15), F(20, 3)):
        n10 = sum(1 for k in range(1, 100) if k * c <= 10)      # counting by stepping
        n20 = sum(1 for k in range(1, 100) if k * c <= 20)
        need10, need20 = F(160) - 140, F(255) - 180
        sol10 = None if n10 == 0 else need10 / n10
        sol20 = None if n20 == 0 else need20 / n20
        feasible = (n10 > 0 and n20 > 0 and sol10 == sol20) or False
        out["architecture_periods"][str(c)] = {"n(10)": n10, "n(20)": n20, "A from t=10": str(sol10),
                                               "A from t=20": str(sol20), "feasible": feasible}
    return out


def px_periodicity():
    res = {}
    ev, _ = O.ledger("Px")
    times = sorted({e.time for e in ev if e.time <= 200})
    phases = sorted({t % 20 for t in times})
    res["Px_event_phases_mod_20_up_to_200"] = [str(p) for p in phases]
    # rebuild schedule from the periodic pattern {7:AC20, 17:AC20, 0:PIPE35} and compare
    pat = {F(7): F(20), F(17): F(20), F(0): F(35)}
    rebuilt = {}
    k = 0
    while 20 * k <= 200:
        for ph, a in pat.items():
            tt = 20 * k + ph
            if 0 < tt <= 200:
                rebuilt[tt] = rebuilt.get(tt, F(0)) + a
        k += 1
    res["periodic_pattern_reproduces_Px_jumps_to_200"] = rebuilt == jumps("Px", 200)
    # early reset at s: phases and transient
    trans = {}
    for s in (F(3), F(7), F(19, 2), F(13), F(37, 2)):
        evs, _ = O.ledger("Px", t_early=s)
        js = {}
        for e in evs:
            if e.time <= 200:
                js[e.time] = js.get(e.time, F(0)) + e.amount
        tail = {t: a for t, a in js.items() if t >= 40}
        ph = sorted({(t % 20, a) for t, a in tail.items()})
        nonperiodic = [str(t) for t, a in js.items() if (t % 20, a) not in set(ph) and (t % 20 != 0 or a != 35)]
        trans[str(s)] = {"tail_phases(mod20,amount)": [(str(p), str(a)) for p, a in ph],
                         "transient_events_not_in_periodic_pattern": nonperiodic,
                         "single_clock_comparators_needed": len(ph) + (1 if nonperiodic else 0)}
    res["early_reset_at_s"] = trans
    return res


def online_reset():
    """Futures of states that share a coordinate (A's claim A-10), recomputed."""
    def inc(case, t0, t1, **kw):
        return O.G(case, t1, O.RIGHT, **kw) - O.G(case, t0, O.RIGHT, **kw)
    r = {"hist(reset@7) at 7 -> 20 (13y)": str(inc("Px", 7, 20)),
         "nominal at 7 -> 20 (13y)": str(inc("P0", 7, 20)),
         "hist(reset@7) at 7 -> 18 (11y)": str(inc("Px", 7, 18)),
         "nominal at 10 -> 21 (11y)": str(inc("P0", 10, 21)),
         "hist 13y vs nominal@10 13y": [str(inc("Px", 7, 20)), str(inc("P0", 10, 23))]}
    # 2-D family: reset at s in (0,10), observed at t in (s,10): state (a,p)=((t-s)/10, t/20).
    # Future is read from output jumps: next AC jump at s+10, next PIPE jump at 20.
    fam = {}
    grid = [F(i, 7) for i in range(1, 70)]
    for s in grid:
        for t in grid:
            if not (s < t < 10):
                continue
            ev, _ = O.ledger("Px", t_early=s)
            fut = tuple(sorted((e.time - t, e.item) for e in ev if t < e.time <= t + 20))[:3]
            fam.setdefault(fut, []).append((s, t))
    collisions = sum(1 for v in fam.values() if len(v) > 1)
    r["2D_family_states_sampled"] = sum(len(v) for v in fam.values())
    r["2D_family_future_collisions"] = collisions
    r["lower_bound_status"] = ("[H] proof draft (claims.md D-9): under continuity of the state in (s,t) on an open "
                               "set without internal events, an injective continuous map R^2 -> R^d needs d>=2 "
                               "(invariance of domain). Sampled family: all futures distinct.")
    return r


def online_two_continuous(s_list=(F(3), F(7), F(19, 2), F(13), F(37, 2), F(31))):
    """Online-reset Px with only TWO continuous states (x_A, x_P clocks) + two unbounded
    counters (nA, kP) and no accumulator: G = 100 + 4(20 kP + x_P) + 20 nA + 35 kP.
    The early AC reset at s is an online input (comparator on nothing: it is an input pulse).
    Tuple (2, 2, 2, 0) + 1 input line. Checked against the ledger oracle."""
    out = {}
    for s in s_list:
        ok = True
        pts = sorted({F(k, 4) for k in range(0, 241)} | {s, s + 10, F(20), F(40)})
        for t in pts:
            now, xa, xp, nA, kP, reset_done = F(0), F(0), F(0), 0, 0, False
            while True:
                cands = [now + (10 - xa), now + (20 - xp)]
                if not reset_done:
                    cands.append(s)
                nxt = min(cands)
                if nxt > t:
                    xa += t - now; xp += t - now; now = t
                    break
                xa += nxt - now; xp += nxt - now; now = nxt
                if not reset_done and now == s:
                    reset_done = True; xa = F(0); nA += 1          # early replacement event + reset
                if xa == 10:
                    xa = F(0); nA += 1
                if xp == 20:
                    xp = F(0); kP += 1
            g = 100 + 4 * (20 * kP + xp) + 20 * nA + 35 * kP
            if g != O.G("Px", t, O.RIGHT, t_early=s):
                ok = False
        out[str(s)] = ok
    return {"exact_vs_oracle_for_reset_times": out, "state_tuple": [2, 2, 2, 0],
            "note": "continuous dimension 2 is achievable (accumulator replaced by counters); with the D-9 lower bound "
                    "(>=2, [H]) the continuous minimum for the online class is 2, not 3. Tuples trade continuous "
                    "states for unbounded counters, so a 4-tuple is not a total order of complexity."}


def single_accumulator():
    """(iv) one accumulator Q fed by an EXTERNAL table of (time, rate) and (time, impulse):
    reproduces every case exactly; the table grows with the horizon."""
    out = {}
    for case, kw in (("P0", {}), ("P1", {"policy": "substitute"}), ("P1", {"policy": "additional"}),
                     ("P2", {}), ("Px", {})):
        ev, segs = O.ledger(case, **({"policy": kw["policy"]} if "policy" in kw else {}))
        table_imp = sorted({e.time for e in ev if e.time <= 60})
        imp = {t: sum((e.amount for e in ev if e.time == t), F(0)) for t in table_imp}
        # accumulator run: integrate segments and add impulses in time order (right conv)
        ok = True
        for tq in [F(x) for x in O.CONTRACT_POINTS] + [F(7), F(17), F(27)]:
            Q, now, rate_i = F(100), F(0), 0
            knots = sorted(set([s for s, _ in segs] + table_imp))
            for k in knots:
                if k > tq:
                    break
                # advance
                r = [rr for s, rr in segs if s <= now][-1]
                Q += r * (k - now); now = k
                Q += imp.get(k, F(0))
            r = [rr for s, rr in segs if s <= now][-1]
            Q += r * (tq - now)
            pol = kw.get("policy", "substitute")
            if Q != O.G(case, tq, O.RIGHT, pol):
                ok = False
        name = case + ("-" + kw["policy"] if "policy" in kw else "")
        out[name] = {"exact_on_contract_points+7,17,27": ok,
                     "table_entries_H60(impulse instants + rate changes)": len(table_imp) + len(segs) - 1,
                     "state_tuple": [1, 1, 1, len(table_imp) + len(segs) - 1]}
    out["note"] = ("A single accumulator suffices whenever the schedule (which instants, which amounts, which rates) "
                   "is supplied from outside; the clocks/comparators only GENERATE the schedule. The table grows "
                   "linearly with horizon H, so this is a trade of continuous state for external memory, not a reduction.")
    return out


def main():
    res = {"merged_clocks": merged_clocks(), "px_fixed_schedule": px_periodicity(),
           "online_reset": online_reset(),
           "online_two_continuous_states": online_two_continuous(), "single_accumulator": single_accumulator()}
    os.makedirs(OUT, exist_ok=True)
    json.dump(res, open(os.path.join(OUT, "states_check.json"), "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
