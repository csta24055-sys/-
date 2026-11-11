"""EXP-01: does one ramp-step kernel carry every dependence on the study period?

For each fictional scenario the reference calculation is run ONCE at the horizon T_max. From
that run and the inputs, T-independent amplitudes are assembled (pieces of the ramp-step
kernel). Then, for every study period T of a sweep, the kernel value is compared with a fresh
reference run at T - for the nine use-stage units that depend on T, the 14 stage values and
the three totals.

What this tests (evidence level N, exploration):  E_unit(T) = sum_j a_j * h_j(T)  with a_j
independent of T. What it does NOT test: the amplitudes of the row units are taken from the
reference results here (the time kernel is isolated); assembling them without the reference
is a separate step.

Run from research_code:  python3 -B -m experiments.exp01_rampstep_sweep [n_scenarios] [max_size]
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

sys.dont_write_bytecode = True

from tstudy import baseline, metrics, rampstep as rs, scenarios

HORIZON = 120.0
STAGES = ("A1-A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "C1", "C2", "C3", "C4")
T_UNITS = ("B1-02", "B1-03", "B1-04", "B2-01", "B3-01", "B4-02", "B5-01", "B6-03", "B7-04")
CONST_UNITS = ("A13-01", "A13-03", "A13-04", "X-01", "A4-01", "A4-02", "A5-04", "C1-01", "C2-01", "C3-01", "C4-01", "X-14")


def _nonneg(x) -> bool:
    return x is not None and x >= 0.0 and not math.isinf(x)


def _ratio(x) -> bool:
    return x is not None and 0.0 <= x <= 1.0


def assemble(scn, res) -> dict[str, list[rs.Piece]]:
    """Pieces per unit from the inputs and ONE reference result at the horizon."""
    H = scn.boundary.study_period
    Y = math.ceil(H)
    P: dict[str, list[rs.Piece]] = {u: [] for u in T_UNITS}

    # B4-02 renewals: atoms at the event times; amplitude = emission of one renewal of the row
    b4 = res["B4-02"]
    mat_events = []
    for i, row in enumerate(scn.materials):
        ev = rs.periodic_times(H, row.refresh_cycle)
        mat_events.append(ev)
        if ev:
            u = b4["by_item_material"][i] / len(ev)
            P["B4-02"] += [rs.atom(u, tau) for tau in ev]
    eq_events = []
    for j, eq in enumerate(scn.equipment):
        if eq.replacement_event_list is not None:
            ev = rs.explicit_times(H, eq.replacement_event_list)
        else:
            ev = rs.periodic_times(H, eq.service_life)
        eq_events.append(ev)
        if ev:
            u = b4["by_item_equipment"][j] / len(ev)
            P["B4-02"] += [rs.atom(u, tau) for tau in ev]

    # B3-01 repairs: a constant density, minus the year cells that hold a renewal of the same row
    def repairs(e0, r, events):
        if not _nonneg(r) or r == 0.0 or e0 == 0.0:
            return
        P["B3-01"].append(rs.density(e0 * r, float(Y)))
        first: dict[int, float] = {}
        for tau in events:
            y = rs.event_year(tau)
            if y not in first or tau < first[y]:
                first[y] = tau
        for y, tau in first.items():
            P["B3-01"].append(rs.year_cell(-e0 * r, y, gate=tau))

    a, b, x = res["A13-01"]["by_item"], res["A13-03"]["by_item"], res["X-01"]["by_item"]
    for i, row in enumerate(scn.materials):
        repairs(a[i] + b[i], row.repair_rate, mat_events[i])
    for j, eq in enumerate(scn.equipment):
        repairs(x[j], eq.repair_rate, eq_events[j])

    # B5-01 rebuild / refurbishment: atoms at multiples of the building replacement cycle
    b5 = res["B5-01"]
    if b5["n_events"]:
        u = b5["value"] / b5["n_events"]
        P["B5-01"] += [rs.atom(u, tau) for tau in rs.periodic_times(H, scn.boundary.replacement_cycle)]

    # B6 / B2 / B7 operation: one year cell per study year
    elec, fuel = res["B6-01"]["by_year"], res["B6-02"]["by_year"]
    share = scn.operation.facility_management_ratio
    for y in range(1, Y + 1):
        P["B6-03"].append(rs.year_cell(elec[y] + fuel[y], y))
        if _ratio(share):
            P["B2-01"].append(rs.year_cell(elec[y] * share, y))
        P["B7-04"].append(rs.year_cell(res["B7-01"]["by_year"][y] + res["B7-02"]["by_year"][y] + res["B7-03"]["by_year"][y], y))

    # B1 refrigerants: state recurrence over full years (T-independent), written as pieces
    for dev in scn.refrigerants:
        if not (_nonneg(dev.charge_mass_kg) and _nonneg(dev.gwp) and _ratio(dev.annual_leak_rate)):
            continue
        if dev.change_years is not None:
            ev = sorted(rs.explicit_times(H, dev.change_years))
        else:
            ev = rs.periodic_times(H, dev.service_life)
        by_year: dict[int, list[float]] = {}
        for tau in ev:
            by_year.setdefault(rs.event_year(tau), []).append(tau)
        m0, r, gwp = dev.charge_mass_kg, dev.annual_leak_rate, dev.gwp
        loss_ok, rec_ok = _ratio(dev.replacement_loss_rate), _ratio(dev.end_of_life_recovery_rate)
        k4 = (1.0 - dev.end_of_life_recovery_rate) * gwp if rec_ok else 0.0
        if rec_ok:
            P["B1-04"].append(rs.constant(k4 * m0))
        m = m0                                    # charge at the start of year y (all earlier years complete)
        for y in range(1, Y + 1):
            P["B1-02"].append(rs.year_cell(m * r * gwp, y))
            if not dev.top_up and rec_ok:
                P["B1-04"].append(rs.year_cell(-k4 * m * r, y))
            taus = sorted(by_year.get(y, []))
            for n, tau in enumerate(taus):
                if n == 0:
                    if loss_ok:
                        P["B1-03"].append(rs.atom(dev.replacement_loss_rate * gwp * m, tau))
                        if not dev.top_up:
                            P["B1-03"].append(rs.year_cell(-dev.replacement_loss_rate * gwp * m * r, y, gate=tau))
                    if not dev.top_up and rec_ok:   # refill to the initial charge
                        P["B1-04"].append(rs.atom(k4 * (m0 - m), tau))
                        P["B1-04"].append(rs.year_cell(k4 * m * r, y, gate=tau))
                elif loss_ok:
                    P["B1-03"].append(rs.atom(dev.replacement_loss_rate * gwp * m0, tau))
            if taus:
                m = m0
            elif not dev.top_up:
                m = m - m * r
    return P


def evaluate(P, const, included, T: float):
    """Unit values, stage values and totals at T from the pieces and the T-independent constants."""
    v = {u: rs.phi(P[u], T) for u in T_UNITS}
    full = {
        "A1-A3": const["A13-01"] + const["A13-03"] + const["A13-04"] + const["X-01"],
        "A4": const["A4-01"] + const["A4-02"], "A5": const["A5-04"],
        "B1": v["B1-02"] + v["B1-03"] + v["B1-04"], "B2": v["B2-01"], "B3": v["B3-01"], "B4": v["B4-02"],
        "B5": v["B5-01"], "B6": v["B6-03"] - v["B2-01"], "B7": v["B7-04"],
        "C1": const["C1-01"], "C2": const["C2-01"], "C3": const["C3-01"] + const["X-14"], "C4": const["C4-01"],
    }
    inc = set(included)
    by_stage = {s: full[s] for s in STAGES if s in inc}
    if "B6" in inc and "B2" not in inc:
        by_stage["B6"] = v["B6-03"]
    tot = metrics.propagate_stage_change(by_stage, list(inc), {})
    return v, by_stage, tot


def main(argv) -> int:
    n = int(argv[1]) if len(argv) > 1 else 60
    max_size = argv[2] if len(argv) > 2 else "M"
    trees = baseline.assert_frozen()
    sets = {"design": scenarios.design_set(n, max_size), "evaluation": scenarios.evaluation_set(n, max_size),
            "edge": [s for _, s in scenarios.edge_set()]}
    stats: dict[str, metrics.ErrorStats] = {}
    excluded: list = []
    n_pairs = n_pieces = n_shapes = n_rows = 0
    worst_any = 0.0
    t0 = time.time()
    for set_name, scns in sets.items():
        for scn in scns:
            top = scenarios.with_period(scn, HORIZON)
            if len(top.operation.grid.table) < math.ceil(HORIZON):
                excluded.append((scn.meta.scenario_id, ["year tables shorter than the horizon"]))
                continue
            if scenarios.valid_domain(top):
                excluded.append((top.meta.scenario_id, scenarios.valid_domain(top)))
                continue
            res_top = baseline.run_reference(top)
            P = assemble(top, res_top)
            const = {u: res_top[u]["value"] for u in CONST_UNITS}
            n_pieces += sum(len(p) for p in P.values())
            n_shapes += len(rs.merge([p for u in T_UNITS for p in P[u]]))
            n_rows += len(scn.materials) + len(scn.equipment) + len(scn.refrigerants)
            periods = sorted(set(scenarios.SWEEP_PERIODS) | {scn.boundary.study_period})
            for T in periods:
                cur = scenarios.with_period(scn, T)
                why = scenarios.valid_domain(cur)
                if why:
                    excluded.append((cur.meta.scenario_id, why))
                    continue
                ref = baseline.run_reference(cur)
                v, by_stage, tot = evaluate(P, const, cur.boundary.included_lifecycle_stages, T)
                n_pairs += 1
                sid = cur.meta.scenario_id
                for u in T_UNITS:
                    stats.setdefault(f"{set_name}|unit|{u}", metrics.ErrorStats(u)).add(v[u], ref[u]["value"], sid)
                for s, x in ref["X-02"]["by_stage"].items():
                    stats.setdefault(f"{set_name}|stage|{s}", metrics.ErrorStats(s)).add(by_stage[s], x, sid)
                for k in ("SUM-01", "SUM-02", "SUM-03"):
                    stats.setdefault(f"{set_name}|total|{k}", metrics.ErrorStats(k)).add(tot[k], ref[k]["value"], sid)
    out = {
        "experiment": "EXP-01", "title": "ramp-step kernel: sweep of the study period from one assembly",
        "evidence_level": "N (numerical, exploration)", "checked_by": "author only",
        "data_statement": "fictional scenarios of the frozen generator; independent concept model; says nothing about real buildings",
        "frozen_trees": trees, "horizon": HORIZON, "sweep_periods": list(scenarios.SWEEP_PERIODS),
        "amplitudes": "row amplitudes taken from ONE reference run at the horizon (time kernel isolated)",
        "n_scenarios": {k: len(v) for k, v in sets.items()}, "n_scenario_period_pairs": n_pairs,
        "n_pieces_total": n_pieces, "n_distinct_shapes_total": n_shapes, "n_input_rows_total": n_rows,
        "excluded": excluded, "seconds": round(time.time() - t0, 1),
        "stats": {k: s.summary() for k, s in sorted(stats.items())},
    }
    for k, s in out["stats"].items():
        if s["max_abs"] is not None:
            worst_any = max(worst_any, s["max_abs"])
    out["max_abs_rel_error_over_all_quantities"] = worst_any
    out["max_abs_when_reference_is_zero"] = max(s["max_abs_when_ref_zero"] for s in out["stats"].values())
    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "03_ROUTES", "experiments")
    os.makedirs(dest, exist_ok=True)
    with open(os.path.join(dest, "EXP-01_rampstep_sweep.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: out[k] for k in ("n_scenarios", "n_scenario_period_pairs", "n_pieces_total",
                                          "n_distinct_shapes_total", "n_input_rows_total", "seconds",
                                          "max_abs_rel_error_over_all_quantities",
                                          "max_abs_when_reference_is_zero")}, indent=1))
    print("excluded:", len(excluded))
    bad = [(k, s["max_abs"], s["worst"]) for k, s in out["stats"].items() if s["max_abs"] and s["max_abs"] > 1e-9]
    for b in sorted(bad, key=lambda z: -z[1])[:25]:
        print("ABOVE 1e-9:", b)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
