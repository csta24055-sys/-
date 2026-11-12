"""EXP-U1: three representations of the end residual of the refrigerants (B1-04) and their conditioning.

  jump      knot spectrum in jump form (changes accumulated from T = 0):  kappa*(m0 - cumulative leaks + refills)
  interval  knot spectrum in interval form (``tstudy.interval``): coefficients valid inside the year cell
  local     masked sum-product at T over the device-year rows of the cell that holds T (``t.b14`` of specs/at_t.py)

Ground truth: the recurrence of the concept model evaluated with mpmath at 60 significant digits from the same
binary inputs (independent of every floating-point path, including the reference calculation).

Run from ``research_code`` with the mathematics environment:
    PYTHONDONTWRITEBYTECODE=1 $HOME/.lca-math/bin/python -B -m experiments.expU1_b14_forms
Writes ``11_UNIFIED_SYSTEM/results/expU1_b14_forms.json``. Fictional data; evidence level N (implementer only).
"""
import copy
import json
import math
import os
import sys

sys.dont_write_bytecode = True

import mpmath as mp

from tstudy import baseline, scenarios, unified

OUT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "11_UNIFIED_SYSTEM", "results",
                                    "expU1_b14_forms.json"))
EPS = mp.mpf(10) ** -9


def truth_b14(scn, T):
    """B1-04 by the recurrence of the definition in 60-digit arithmetic (time rules as in the concept model)."""
    mp.mp.dps = 60
    Tm = mp.mpf(T)
    Y = math.ceil(T)
    total = mp.mpf(0)
    for dev in scn.refrigerants:
        ok = lambda x, hi=None: x is not None and x >= 0.0 and not math.isinf(x) and (hi is None or x <= hi)
        if not (ok(dev.charge_mass_kg) and ok(dev.gwp) and ok(dev.annual_leak_rate, 1.0) and ok(dev.end_of_life_recovery_rate, 1.0)):
            continue
        if dev.change_years is not None:
            ev = [mp.mpf(t) for t in dev.change_years if t > 0 and mp.mpf(t) < Tm * (1 - EPS)]
        else:
            ev, n = [], 1
            L = dev.service_life
            if L is not None and L > 0 and not math.isinf(L):
                while mp.mpf(n) * mp.mpf(L) < Tm * (1 - EPS):
                    ev.append(mp.mpf(n) * mp.mpf(L)); n += 1
        years = {}
        for tau in ev:
            y = max(1, int(mp.ceil(tau * (1 - EPS))))
            years[y] = years.get(y, 0) + 1
        m0 = mp.mpf(dev.charge_mass_kg)
        m, r = m0, mp.mpf(dev.annual_leak_rate)
        for y in range(1, Y + 1):
            w = min(mp.mpf(1), Tm - (y - 1))
            if not dev.top_up:
                m -= m * r * w
            if years.get(y):
                m = m0
        total += m * (1 - mp.mpf(dev.end_of_life_recovery_rate)) * mp.mpf(dev.gwp)
    return total


def rel(x, truth):
    return float(abs(mp.mpf(x) - truth) / truth) if truth != 0 else float(abs(mp.mpf(x)))


def main():
    baseline.assert_frozen(); baseline.load()
    base = next(s for s in scenarios.evaluation_set(60) if len(s.refrigerants) >= 5)
    cases = [("generated scenario (unchanged)", lambda c: None)]
    def no_events(leak):
        def f(c):
            for d in c.refrigerants:
                d.top_up, d.change_years, d.annual_leak_rate = False, [], leak
        return f
    def life(L, leak):
        def f(c):
            for d in c.refrigerants:
                d.top_up, d.change_years, d.service_life, d.annual_leak_rate = False, None, L, leak
        return f
    cases += [("no replacement, leak %g" % k, no_events(k)) for k in (0.02, 0.05, 0.12, 0.35, 0.60)]
    cases += [("life 15 years, leak 0.10", life(15.0, 0.10)), ("life 25 years, leak 0.30", life(25.0, 0.30)), ("life 7.3 years, leak 0.12", life(7.3, 0.12))]
    rows = []
    for label, f in cases:
        scn = copy.deepcopy(base); f(scn)
        systems = {mode: unified.System(scn, with_base=False, b14=mode) for mode in unified.B14_MODES}
        for T in (20.0, 60.0, 62.5, 99.9, 130.0):
            truth = truth_b14(scn, T)
            ref = baseline.run_reference(scenarios.with_period(scn, T), ["B1-04", "B1-02"])
            row = {"case": label, "T": T, "truth": float(truth), "residual_share_of_B1_02": float(truth / mp.mpf(ref["B1-02"]["value"])),
                   "rel_err_reference": rel(ref["B1-04"]["value"], truth)}
            for mode, sysm in systems.items():
                row["rel_err_" + mode] = rel(sysm.at(T)["B1-04"]["value"], truth)
            rows.append(row)
            print("%-34s T=%6.1f truth %.6e | reference %.1e | jump %.1e | interval %.1e | local %.1e" % (
                label, T, row["truth"], row["rel_err_reference"], row["rel_err_jump"], row["rel_err_interval"], row["rel_err_local"]))
    summary = {k: max(r[k] for r in rows) for k in ("rel_err_reference", "rel_err_jump", "rel_err_interval", "rel_err_local")}
    print("max over all cases:", {k: "%.2e" % v for k, v in summary.items()})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump({"experiment": "EXP-U1", "ground_truth": "mpmath, 60 digits, recurrence of the definition", "scenario": base.meta.scenario_id,
                   "n_devices": len(base.refrigerants), "rows": rows, "max": summary}, fh, indent=1)


if __name__ == "__main__":
    main()
