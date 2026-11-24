"""V1: pilot (CF2) and fresh state-change cases (CF3) against the verifier's own ledger.

The circuit side is the builder's snapshot `model.simulate` (black box: primitive inputs in,
readouts out). The expected side is `ledger.total` (exact rationals). Every case compares
ALL stage values and C(T); for selected cases the event times / years are compared too.
"""
from __future__ import annotations

import itertools
import time
from fractions import Fraction as F

from common import builder, fstr, rel, save
from ledger import EPS, event_years, item_events, total

model, adapter = builder()

POINTS07 = ["0", "1", "9.999999", "10", "10.000001", "19.999999", "20", "20.000001", "30", "40", "60"]
PILOT = {"initial": [{"id": "init", "amount": 100, "stage": "A1-A3"}],
         "flows": [{"id": "op", "rate": 4, "stage": "B6"}],
         "items": [{"id": "A", "amount": 20, "period": 10, "stage": "B4"},
                   {"id": "B", "amount": 35, "period": 20, "stage": "B4"}]}


def run_case(name, scn, convs, Ts, dilate=True, also_undilated=False, check=True):
    rows = []
    ok = True
    t0 = time.time()
    for conv in convs:
        Tc = [F(T) for T in Ts if not (conv != "right" and F(T) == 0)]
        r = model.simulate(scn, Tc, conv)
        for T in Tc:
            got = r["by_T"][T]
            expC, expS = total(scn, T, conv, dilate=dilate)
            stages_ok = all(got["stages"].get(s, F(0)) == v for s, v in expS.items()) and \
                all(expS.get(s, F(0)) == v for s, v in got["stages"].items())
            match = (got["C"] == expC) and stages_ok
            row = {"conv": conv, "T": fstr(T), "circuit_C": fstr(got["C"]), "ledger_C": fstr(expC),
                   "match": match}
            if not match:
                row["stages_circuit"] = {k: fstr(v) for k, v in got["stages"].items()}
                row["stages_ledger"] = {k: fstr(v) for k, v in expS.items()}
                row["rel_err_C"] = float(rel(got["C"], expC))
            if also_undilated:
                uC, _ = total(scn, T, conv, dilate=False)
                row["ledger_undilated_C"] = fstr(uC)
                row["rel_dev_from_undilated"] = float(rel(got["C"], uC))
                row["abs_dev_from_undilated"] = float(got["C"] - uC)
            ok &= match if check else True
            rows.append(row)
    return {"case": name, "pass": ok, "n_points": len(rows), "seconds": round(time.time() - t0, 2),
            "rows": rows}


def events_check(scn, T, conv="right"):
    """Packet times per item (right convention) vs the ledger's nominal schedule."""
    r = model.simulate(scn, [F(T)], conv)
    out = {}
    ok = True
    e = EPS if conv == "original" else F(0)
    for it in scn["items"]:
        if it["id"] not in r["events"]:
            continue
        pk, _ = item_events(it, scn.get("renovations", []), F(T) + 1)
        exp = [p / (1 - e) for p in pk if p / (1 - e) <= F(T)]
        got = r["events"][it["id"]]
        out[it["id"]] = {"circuit": [fstr(x) for x in got], "ledger": [fstr(x) for x in exp], "match": got == exp}
        ok &= got == exp
    return ok, out


def main():
    cases = []
    # ---------------- CF2 pilot
    cases.append(run_case("pilot_07_points", PILOT, ["right", "left", "original"], POINTS07))
    cases.append(run_case("pilot_extra_T", PILOT, ["right", "left", "original"],
                          ["1/2", "333/10", "59999999/1000000", "60000001/1000000", "100", "255"]))
    perm = dict(PILOT, items=list(reversed(PILOT["items"])))
    cases.append(run_case("pilot_items_reversed", perm, ["right", "original"], ["10", "20", "40"]))
    # ---------------- CF3 fresh
    irr = {"items": [{"id": "p73", "amount": 3, "period": F(7, 3), "stage": "B4"},
                     {"id": "p115", "amount": 5, "period": F(11, 5), "stage": "B4"}],
           "flows": [{"id": "op", "rate": F(3, 7), "stage": "B6"}]}
    cases.append(run_case("periods_7_3_and_11_5", irr, ["right", "left", "original"],
                          ["7/3", "11/5", "7", "11", "22", "231/10", "33", "231/5", "55", "60", "77"]))
    tiny = {"items": [{"id": "m", "amount": F(1, 1000), "period": F(1, 1000), "stage": "B4"}]}
    cases.append(run_case("tiny_period_1_1000", tiny, ["right", "left", "original"],
                          ["1/1000", "1/2", "1", "20001/20000"]))
    triple_items = [{"id": "a", "amount": 2, "period": 2, "stage": "B4"},
                    {"id": "b", "amount": 3, "period": 3, "stage": "B4"},
                    {"id": "c", "amount": 4, "period": 4, "stage": "B4"},
                    {"id": "d", "amount": 7, "period": 6, "stage": "B4",
                     "repair": {"base": 10, "rate": F(1, 10), "stage": "B3"}}]
    for k, p in enumerate(itertools.permutations(triple_items)):
        if k % 6 != 0:                     # 4 of the 24 orders (runtime)
            continue
        scn = {"initial": [{"id": "i", "amount": 50, "stage": "A"}],
               "flows": [{"id": "op", "rate": 2, "stage": "B6"}], "items": list(p)}
        cases.append(run_case(f"quad_simultaneous_perm{k}", scn, ["right", "left", "original"],
                              ["6", "12", "24", "49/2", "25"]))
    for pol in ("restart", "keep"):
        for ex in ([F(7, 2), 13], [10], [F(9999999, 1000000)], [5, 15]):
            scn = {"items": [{"id": "A", "amount": 20, "period": 10, "explicit": ex, "explicit_policy": pol,
                              "stage": "B4"}]}
            cases.append(run_case(f"explicit_{pol}_{'_'.join(fstr(F(x)) for x in ex)}", scn,
                                  ["right", "left", "original"],
                                  ["7/2", "9999999/1000000", "10", "13", "15", "20", "47/2", "30", "35"]))
    deg = {"flows": [{"id": "op", "rate": 4, "stage": "B6", "degradation": {"item": "A", "slope": F(1, 2)}}],
           "items": [{"id": "A", "amount": 20, "period": 10, "explicit": [7], "stage": "B4"}]}
    cases.append(run_case("degradation_right_left", deg, ["right", "left"], ["5", "7", "10", "17", "23/2", "25", "40"]))
    cases.append(run_case("degradation_original_eps", deg, ["original"], ["5", "7", "10", "17", "23/2", "25", "40", "100"],
                          dilate=True, also_undilated=True))
    eff = {"flows": [{"id": "op", "rate": 4, "rate_after": 3, "switch_on": "A", "stage": "B6"}],
           "items": [{"id": "A", "amount": 20, "period": 10, "stage": "B4"}]}
    cases.append(run_case("efficiency_change_left", eff, ["left"], ["5", "10", "15", "30"]))
    cases.append(run_case("efficiency_change_original_eps", eff, ["original"], ["5", "10", "15", "30", "100"],
                          dilate=True, also_undilated=True))
    for per in (F(1), F(4, 3), F(2, 5), F(5, 2), F(5)):
        scn = {"items": [{"id": "A", "amount": 1, "period": per, "stage": "B4",
                          "repair": {"base": 20, "rate": F(1, 20), "stage": "B3"}}]}
        cases.append(run_case(f"repair_period_{fstr(per)}", scn, ["right", "left", "original"],
                              ["1", "4/3", "2", "5", "5000000001/1000000000", "500000001/100000000", "21/2", "12", "15"]))
    rep_ex = {"items": [{"id": "A", "amount": 1, "period": 3, "explicit": [F(7, 2), 8], "stage": "B4",
                         "repair": {"base": 10, "rate": F(1, 10), "stage": "B3"}},
                        {"id": "B", "amount": 1, "period": 3, "stage": "B4",
                         "repair": {"base": 30, "rate": F(1, 30), "stage": "B3"}}],
              "renovations": [{"id": "R", "amount": 9, "years": [11], "replaces": ["B"], "policy": "substituted",
                               "stage": "B5"}]}
    cases.append(run_case("repair_explicit_and_renovation_groups", rep_ex, ["right", "left", "original"],
                          ["3", "7/2", "4", "8", "9", "11", "23/2", "14", "15"]))
    for years in ([13], [7, 33]):
        for pol in ("substituted", "additional"):
            scn = dict(PILOT, initial=[{"id": "i", "amount": 100, "stage": "A"}],
                       renovations=[{"id": "R", "amount": 50, "years": years, "replaces": ["A", "B"],
                                     "policy": pol, "stage": "B5"}])
            cases.append(run_case(f"renovation_{pol}_{'_'.join(map(str, years))}", scn, ["right", "left", "original"],
                                  ["7", "13", "20", "23", "33", "40", "43", "50"]))
    reno_order = {"initial": [{"id": "i", "amount": 100, "stage": "A"}],
                  "items": [{"id": "B", "amount": 35, "period": 20, "stage": "B4"},
                            {"id": "A", "amount": 20, "period": 10, "stage": "B4"}],
                  "renovations": [{"id": "S", "amount": 5, "years": [30], "replaces": ["A"], "policy": "substituted", "stage": "B5"},
                                  {"id": "R", "amount": 50, "years": [20], "replaces": ["A", "B"], "policy": "substituted", "stage": "B5"}],
                  "flows": [{"id": "op", "rate": 4, "stage": "B6"}]}
    cases.append(run_case("renovations_permuted_two", reno_order, ["right", "original"], ["20", "30", "40", "50"]))
    full = {"initial": [{"id": "i", "amount": 100, "stage": "A"}],
            "flows": [{"id": "op", "rate": 4, "rate_after": 3, "switch_on": "A", "stage": "B6"},
                      {"id": "dg", "rate": 0, "stage": "B6", "degradation": {"item": "B", "slope": F(1, 2)}}],
            "items": [{"id": "A", "amount": 20, "period": F(5, 2), "explicit": [7], "stage": "B4",
                       "repair": {"base": 20, "rate": F(1, 20), "stage": "B3"}},
                      {"id": "B", "amount": 35, "period": F(10, 3), "stage": "B4"}],
            "renovations": [{"id": "R", "amount": 50, "years": [25], "replaces": ["A", "B"], "policy": "substituted", "stage": "B5"}]}
    cases.append(run_case("builder_full_scenario_unchecked_by_builder_right", full, ["right", "left"], ["12", "51/2", "30"]))
    cases.append(run_case("builder_full_scenario_original", full, ["original"], ["12", "51/2", "30"],
                          dilate=True, also_undilated=True))
    # signed inputs (negative atom / negative rate): semantic ledger keeps the sign
    neg = {"initial": [{"id": "i", "amount": 100, "stage": "A"}, {"id": "credit", "amount": -15, "stage": "D"}],
           "flows": [{"id": "op", "rate": 4, "stage": "B6"}, {"id": "export", "rate": -1, "stage": "B6"}],
           "items": [{"id": "A", "amount": 20, "period": 10, "stage": "B4"}]}
    cases.append(run_case("signed_inputs_negative_amount_and_rate", neg, ["right"], ["10", "20"]))
    expl_only = {"items": [{"id": "X", "amount": 9, "explicit": [3, F(17, 2)], "stage": "B4",
                            "repair": {"base": 10, "rate": F(1, 5), "stage": "B3"}}]}
    cases.append(run_case("explicit_only_no_period", expl_only, ["right", "left", "original"], ["3", "4", "17/2", "9", "12"]))
    # event-time comparisons
    ev = {}
    for nm, scn, T in (("irr", irr, 60), ("triple", {"items": triple_items}, 25), ("reno", reno_order, 50),
                       ("explicit", {"items": [{"id": "A", "amount": 20, "period": 10, "explicit": [F(7, 2), 13],
                                                "stage": "B4"}]}, 40)):
        for conv in ("right", "original"):
            ok, out = events_check(scn, T, conv)
            ev[f"{nm}/{conv}"] = {"pass": ok, "items": out}
    # year-of-event from boolean logs (repair groups) vs ceil(tau(1-eps))
    yrs = {}
    for per in (F(5, 2), F(4, 3), F(1)):
        scn = {"items": [{"id": "A", "amount": 1, "period": per, "stage": "B4",
                          "repair": {"base": 1, "rate": 1, "stage": "B3"}}]}
        for conv in ("right", "left", "original"):
            r = model.simulate(scn, [F(15)], conv)
            got = [e["year"] for e in r["group_events"]["g0"]]
            exp = [y for _, y in event_years(scn, "A", F(15) + 1, conv)][:len(got)]
            yrs[f"{fstr(per)}/{conv}"] = {"circuit": got, "ledger": exp, "pass": got == exp}
    summary = {"cases": len(cases), "pass": sum(c["pass"] for c in cases),
               "fail": [c["case"] for c in cases if not c["pass"]],
               "points": sum(c["n_points"] for c in cases),
               "event_checks_pass": all(v["pass"] for v in ev.values()),
               "year_checks_pass": all(v["pass"] for v in yrs.values())}
    save("fresh_cases.json", {"summary": summary, "cases": cases, "events": ev, "years": yrs})
    return summary


if __name__ == "__main__":
    import json
    print(json.dumps(main(), indent=1, default=str))
