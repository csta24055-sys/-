"""Shared pieces of the approximation study (``bench.approx_study``).

* statistics of signed relative errors and the collectors that hold them;
* reversible in-place rewrites of a scenario, so that the reference calculation itself
  can be re-run with an approximated input (propagated totals);
* the coarse year table (keep every n-th value, interpolate linearly);
* an instruction counter (``sys.monitoring``) and the kernels whose load is compared:
  each candidate kernel next to the exact closed form of the unified model, called on
  the same rows.

All data are synthetic and fictional. Nothing here establishes practical accuracy.
"""
from __future__ import annotations

import sys

from common.compare import percentile
from fastcalc import closed_forms as cf
from refcalc import registry
from refcalc.base import periodic_events, positive

TARGET_TOTAL, TARGET_STAGE = 0.01, 0.02
C_TOL = 1.0 - 1e-9          # the boundary tolerance of the time rules (refcalc.base), as a float


def stats(errors: list[float]) -> dict:
    if not errors:
        return {"n": 0}
    a = [abs(e) for e in errors]
    return {"n": len(errors), "mean_signed": sum(errors) / len(errors), "mean_abs": sum(a) / len(a),
            "p95_abs": percentile(a, 95), "max_abs": max(a), "max_over": max(errors), "max_under": min(errors),
            "share_under_estimated": sum(e < -1e-12 for e in errors) / len(errors)}


class Series:
    """Signed relative errors of one quantity.

    A case whose reference is 0 has no relative error and is dropped; the drops are
    counted, and separately those where the candidate is not 0 (the candidate books
    something where the reference has nothing).
    """

    def __init__(self):
        self.errors: list[float] = []
        self.zero = 0
        self.zero_nonzero = 0

    def add(self, ref, cand, ratio_form: bool = False):
        """Record one case; returns the error, or None when the reference is 0."""
        if ref == 0.0:
            self.zero += 1
            if cand != 0.0:
                self.zero_nonzero += 1
            return None
        e = cand / ref - 1.0 if ratio_form else (cand - ref) / ref
        self.errors.append(e)
        return e

    def result(self) -> dict:
        out = stats(self.errors)
        out["n_reference_zero"] = self.zero
        out["n_reference_zero_candidate_nonzero"] = self.zero_nonzero
        return out


def within(s: dict, target: float) -> bool:
    """A series meets a target: it has cases, none above the target, none with reference 0 and candidate not 0."""
    return bool(s.get("n")) and s["max_abs"] <= target and not s.get("n_reference_zero_candidate_nonzero")


class Collector:
    """Everything measured for one candidate.

    primary        the quantity named by the candidate's ``stage`` label (with the
                   breakdown by structure and by use, and the local total: the same
                   difference divided by the whole-life total);
    classes        per material class: error of the class sum within one scenario;
    stages         real stage values of X-02 the candidate changes directly;
    units          own outputs of the units the candidate is attached to;
    propagated     whole-life total and stage values after the reference calculation
                   was re-run with the approximated input.
    """

    def __init__(self):
        self.primary = Series()
        self.local_total: list[float] = []
        self.groups: dict[str, list[float]] = {}
        self.classes: dict[str, Series] = {}
        self.class_pairs = 0
        self.stages: dict[str, Series] = {}
        self.units: dict[str, dict[str, dict]] = {}
        self.extra: dict[str, Series] = {}
        self.prop_total: list[float] = []
        self.prop_stages: dict[str, Series] = {}
        self.prop_changed: set[str] = set()
        self.prop_check = 0.0
        self.prop_n = 0

    def add(self, group, ref, cand, wlc=None, total_diff=None):
        """``group`` = (structure, use). ``total_diff`` replaces cand - ref in the local total when the
        candidate changes more than the primary quantity (e.g. purchased electricity feeds B6 and B2)."""
        if wlc:
            self.local_total.append(((cand - ref) if total_diff is None else total_diff) / wlc)
        e = self.primary.add(ref, cand)
        if e is None:
            return
        for key in (f"structure={group[0]}", f"use={group[1]}"):
            self.groups.setdefault(key, []).append(e)

    def add_classes(self, ref_by_class: dict, cand_by_class: dict):
        for k, ref in ref_by_class.items():
            self.class_pairs += 1
            self.classes.setdefault(k, Series()).add(ref, cand_by_class.get(k, 0.0))

    def add_stage(self, stage: str, ref, cand):
        self.stages.setdefault(stage, Series()).add(ref, cand)

    def unit(self, uid: str, quantity: str, level: str = "SCENARIO", role: str = "REPLACED") -> Series:
        """The series of one own output of a unit. level: SCENARIO (one value per scenario) or ROW.
        role: REPLACED (the unit's output is approximated) or IS_THE_CANDIDATE (the unit's own output is the
        candidate value and is compared with the unit it would stand in for)."""
        entry = self.units.setdefault(uid, {}).setdefault(quantity, {"level": level, "role": role, "series": Series()})
        return entry["series"]

    def other(self, label: str) -> Series:
        return self.extra.setdefault(label, Series())

    def add_propagated(self, ref_stage: dict, new_stage: dict, ref_total, new_total, check_ref=None, check_new=None):
        """Result of re-running the reference with the approximated input."""
        self.prop_n += 1
        if ref_total:
            self.prop_total.append((new_total - ref_total) / ref_total)
        for s, ref in ref_stage.items():
            if new_stage[s] != ref:
                self.prop_changed.add(s)
            self.prop_stages.setdefault(s, Series()).add(ref, new_stage[s])
        if check_ref is not None:
            scale = max(abs(check_ref), abs(check_new))
            if scale:
                self.prop_check = max(self.prop_check, abs(check_new - check_ref) / scale)

    def class_result(self):
        if not self.classes:
            return None, None
        by_class = {k: v.result() for k, v in sorted(self.classes.items())}
        zero = {"n_pairs": self.class_pairs,
                "n_reference_zero": sum(v.zero for v in self.classes.values()),
                "n_reference_zero_candidate_nonzero": sum(v.zero_nonzero for v in self.classes.values())}
        return by_class, zero

    def unit_result(self) -> dict:
        return {uid: {q: {"level": e["level"], "role": e["role"], "error": e["series"].result()} for q, e in qs.items()}
                for uid, qs in self.units.items()}


# ----------------------------------------------------------------- reversible scenario rewrites

_MISSING = object()


class Patch:
    """In-place edits of a scenario that can be undone (attributes and dictionary entries).

    A deep copy of a scenario costs more than a reference run; an edit that is undone
    in a ``finally`` block leaves the scenario as it was.
    """

    def __init__(self):
        self._undo = []

    def set(self, obj, name: str, value):
        self._undo.append((obj, name, getattr(obj, name), False))
        setattr(obj, name, value)

    def put(self, mapping: dict, key, value):
        self._undo.append((mapping, key, mapping.get(key, _MISSING), True))
        mapping[key] = value

    def undo(self):
        for obj, key, old, is_item in reversed(self._undo):
            if not is_item:
                setattr(obj, key, old)
            elif old is _MISSING:
                del obj[key]
            else:
                obj[key] = old
        self._undo = []


def rerun(scn, edit, ids):
    """Reference results ``ids`` of the scenario as rewritten by ``edit(patch)``; the scenario is restored."""
    p = Patch()
    try:
        edit(p)
        return registry.run_all(scn, ids=list(ids))
    finally:
        p.undo()


def continue_lists(p: Patch, scn, own_period: float, horizon: float) -> int:
    """Continue every explicit event list beyond the scenario's own study period up to ``horizon`` years.

    The generator writes explicit lists only inside the scenario's own period. Equipment
    lists are continued by the row's service life, refrigerant lists by the mean gap of
    the list itself (rounded to whole years, at least 1); only events at or after the own
    period are added. Returns the number of lists that could not be continued (no life,
    or an empty refrigerant list).
    """
    def continued(entries, gap):
        if not positive(gap):
            return None
        out = list(entries)
        last = out[-1] if out else 0.0
        step = max(1.0, round(gap))
        while last + step < horizon + 1.0:
            last += step
            if last >= own_period:
                out.append(last)
        return out

    failed = 0
    for eq in scn.equipment:
        if eq.replacement_event_list is not None:
            new = continued(eq.replacement_event_list, eq.service_life)
            if new is None:
                failed += 1
            else:
                p.set(eq, "replacement_event_list", new)
    for dev in scn.refrigerants:
        if dev.change_years is not None:
            gap = dev.change_years[-1] / len(dev.change_years) if dev.change_years else None
            new = continued(dev.change_years, gap)
            if new is None:
                failed += 1
            else:
                p.set(dev, "change_years", new)
    return failed


# ----------------------------------------------------------------- coarse year tables

def coarse(values, step: int) -> list[float]:
    """Keep every ``step``-th value and the last one; interpolate linearly in between."""
    Y = len(values)
    out = []
    for k in range(Y):
        lo = (k // step) * step
        hi = min(lo + step, Y - 1) if Y > 1 else lo
        out.append(values[lo] if hi <= lo else values[lo] + (values[hi] - values[lo]) * (k - lo) / (hi - lo))
    return out


def n_nodes(Y: int, step: int) -> int:
    """Number of values the coarse table of ``Y`` years holds."""
    return len({(k // step) * step for k in range(Y)} | {Y - 1}) if Y > 0 else 0


# ----------------------------------------------------------------- repair years of one row

def exact_repair_years(T, w, row) -> float:
    """Sum of the year weights of the years without a renewal of the row (reference rule)."""
    events = row["events"] if row["events"] is not None else (periodic_events(T, row["cycle"]) if row["n"] else [])
    skip = set(events)
    return sum(w[y] for y in range(1, len(w)) if y not in skip)


def safe_side_years(T, cycle) -> float:
    """Repair years with the continuous count in the exclusion term: T - min(T, max(0, T/c - 1))."""
    return T - min(T, max(0.0, T / cycle - 1.0))


# ----------------------------------------------------------------- refrigerant: the two linear variants

def linear_refrigerant(T, dev, event_years, consistent: bool):
    """(leak, mass before the changes summed, mass at the end) per device, in kg, linearised.

    consistent=True   leak of a cycle of k years = m0*r*k, remaining mass m0*max(0, 1 - r*k);
    consistent=False  "every device treated as topped up": the remaining mass is always m0.
    A device that is topped up every year is exact in both variants. ``event_years`` are the
    years of the charge changes in non-decreasing order; k counts year weights, so the
    weighted years up to the end of study year y are min(y, T).
    """
    m0, r = dev.charge_mass_kg, dev.annual_leak_rate
    leak = m0 * r * T
    if dev.top_up or not consistent:
        return leak, len(event_years) * m0, m0
    before = 0.0
    done = 0.0
    for y in event_years:
        upto = min(float(y), T)
        before += m0 * max(0.0, 1.0 - r * (upto - done))
        done = upto
    return leak, before, m0 * max(0.0, 1.0 - r * (T - done))


# ----------------------------------------------------------------- load: executed bytecode instructions

class InstructionCounter:
    """Counts executed bytecode instructions with ``sys.monitoring`` (as bench/verify_unified.py does)."""

    def __init__(self):
        self.n = 0
        self.mon = sys.monitoring
        self.tool = self.mon.PROFILER_ID

    def run(self, fn, *args) -> int:
        self.n = 0
        self.mon.use_tool_id(self.tool, "approx_load")
        self.mon.register_callback(self.tool, self.mon.events.INSTRUCTION, self._tick)
        self.mon.set_events(self.tool, self.mon.events.INSTRUCTION)
        try:
            fn(*args)
        finally:
            self.mon.set_events(self.tool, 0)
            self.mon.register_callback(self.tool, self.mon.events.INSTRUCTION, None)
            self.mon.free_tool_id(self.tool)
        return self.n

    def _tick(self, code, offset):
        self.n += 1


# Kernels. Every kernel is a plain loop over prepared rows that calls ONE function per row, so
# that a candidate and the exact closed form are measured doing the same job on the same rows.

def count_ap01(T, period):
    return max(0.0, T / period - 1.0) if cf.valid_period(period) else 0.0


def count_ap02(T, period):
    return max(0.0, T / period - 0.5) if cf.valid_period(period) else 0.0


def count_ap03(T, period):
    return T / period if cf.valid_period(period) else 0.0


def k_count(fn, T, rows):
    """sum of count(T, cycle) * emission of one renewal."""
    total = 0.0
    for cycle, u in rows:
        total += fn(T, cycle) * u
    return total


def years_exact(T, period):
    n = cf.renewal_count(T, period)
    return T - cf.skip_weight_periodic(T, period, n) if n else T


def years_ap04(T, period):
    return T


def years_ap23(T, period):
    return T - min(T, max(0.0, T / period - 1.0)) if cf.valid_period(period) else T


def k_repair(fn, T, rows):
    """sum of e0*r * repair years(T, cycle)."""
    total = 0.0
    for cycle, e0r in rows:
        total += e0r * fn(T, cycle)
    return total


def k_repair_class(T, classes):
    """AP-23b: one evaluation per class from (sum e0*r, sum e0*r/c)."""
    total = 0.0
    for a, b in classes:
        total += a * (T - min(T, max(0.0, T * b / a - 1.0)))
    return total


def device_years(T, dev):
    """Years of the charge changes of one device, with the closed forms of the unified model."""
    if dev.change_years is not None:
        return sorted(cf.explicit_years(T, dev.change_years))
    n = cf.renewal_count(T, dev.service_life)
    return cf.periodic_years(dev.service_life, n) if n else []


def device_exact(T, dev):
    years = device_years(T, dev)
    leaked, before, end = cf.refrigerant_fractions(T, dev.annual_leak_rate, dev.top_up, years)
    m0 = dev.charge_mass_kg
    return m0 * leaked, m0 * sum(before), m0 * end


def device_ap05a(T, dev):
    return linear_refrigerant(T, dev, device_years(T, dev), True)


def device_ap05b(T, dev):
    if dev.change_years is not None:
        n = len(cf.explicit_years(T, dev.change_years))
    else:
        n = cf.renewal_count(T, dev.service_life)
    m0 = dev.charge_mass_kg
    return m0 * dev.annual_leak_rate * T, n * m0, m0


def k_devices(fn, T, devices):
    """B1 of the devices: (leak + loss rate * mass before changes + (1 - recovery) * end mass) * GWP."""
    total = 0.0
    for dev in devices:
        leak, before, end = fn(T, dev)
        total += (leak + before * dev.replacement_loss_rate + end * (1.0 - dev.end_of_life_recovery_rate)) * dev.gwp
    return total


def order_exact(q, w):
    return q / (1.0 - w)


def order_ap06(q, w):
    return q * (1.0 + w)


def k_order(fn, rows):
    total = 0.0
    for q, w in rows:
        total += fn(q, w)
    return total


def net_exact(q_inst, w, rho):
    return q_inst * (1.0 + w * (1.0 - rho) / (1.0 - w))


def net_ap06b(q_inst, w, rho):
    return q_inst * (1.0 + w * (1.0 - rho))


def k_net(fn, rows):
    total = 0.0
    for q_inst, w, rho in rows:
        total += fn(q_inst, w, rho)
    return total


def recipe_exact(parts):
    value = 0.0
    for frac, f in parts:
        value += frac * f
    return value


def recipe_ap07a(parts):
    value = 0.0
    for frac, f in parts:
        if frac >= 0.05:
            value += frac * f
    return value


def recipe_ap07b(parts):
    value = share = 0.0
    for frac, f in parts:
        if frac >= 0.05:
            value += frac * f
            share += frac
    return value / share if share else 0.0


def k_recipes(fn, rows):
    """sum of mass * composite factor(recipe)."""
    total = 0.0
    for kg, parts in rows:
        total += kg * fn(parts)
    return total


def elec_exact_closed(T, B, S, segments):
    """Purchased-electricity emission for a linear net demand B + S*k and a piecewise-linear grid factor."""
    G, H = cf.segment_moments(segments, T)
    return B * G + S * H


def elec_ap08_closed(T, B, S, segments):
    """Mean demand x mean factor x T with the same closed forms."""
    G, _ = cf.segment_moments(segments, T)
    return cf.linear_weighted_sum(T, B, S) * G / T


def elec_exact_scan(T, w, net, g):
    total = 0.0
    for y in range(1, len(w)):
        total += w[y] * net[y] * g[y]
    return total


def elec_ap08_scan(T, w, net, g):
    a = b = 0.0
    for y in range(1, len(w)):
        a += w[y] * net[y]
        b += w[y] * g[y]
    return a * b / T


def moments_from_nodes(T, Y, step, nodes):
    """Grid moments (G, H) from a coarse table: rebuild the yearly values, then one scan."""
    table = []
    last = len(nodes) - 1
    for k in range(Y):
        i = k // step
        lo = i * step
        if i >= last:
            table.append(nodes[last])
            continue
        hi = min(lo + step, Y - 1)
        table.append(nodes[i] + (nodes[i + 1] - nodes[i]) * (k - lo) / (hi - lo))
    return cf.table_moments(table, T)


def weighted_table(T, table):
    """sum of year weight * yearly value (one scan), the exact form for a year table."""
    Y = cf.n_years(T)
    wl = cf.last_weight(T)
    total = 0.0
    for k in range(Y):
        total += (wl if k == Y - 1 else 1.0) * table[k]
    return total


def weighted_from_nodes(T, Y, step, nodes):
    """The same sum from a coarse table: rebuild the yearly values while scanning."""
    wl = cf.last_weight(T)
    last = len(nodes) - 1
    total = 0.0
    for k in range(Y):
        i = k // step
        lo = i * step
        if i >= last:
            v = nodes[last]
        else:
            v = nodes[i] + (nodes[i + 1] - nodes[i]) * (k - lo) / (min(lo + step, Y - 1) - lo)
        total += (wl if k == Y - 1 else 1.0) * v
    return total


def co2_exact(entries):
    """CO2-only total read from the table of the unified model: one product per factor key."""
    total = 0.0
    for activity, co2 in entries:
        total += activity * co2
    return total


def co2_ap22b(kappa, total):
    return kappa * total


class Load:
    """Executed instructions of candidate kernels and of the exact closed form on the same rows.

    Each call of ``pair`` runs the two kernels once (``n_kernel_runs``) over ``n_rows`` rows
    (rows, devices, recipes or years, as the kernel loops); the counts are summed.
    """

    def __init__(self):
        self.counter = InstructionCounter()
        self.acc: dict[str, dict] = {}
        self.scenarios: list[str] = []

    def pair(self, key: str, n_rows: int, candidate, exact, check=None, extra=None):
        """``candidate`` and ``exact`` are (function, *args). ``check`` = (kernel value, reference value)
        records how closely the exact kernel reproduces the reference on these rows. ``extra`` holds
        further counts of the rows (summed over the scenarios)."""
        a = self.acc.setdefault(key, {"n_kernel_runs": 0, "n_rows": 0, "candidate_instructions": 0,
                                      "exact_closed_form_instructions": 0, "exact_kernel_max_rel_diff_to_reference": None})
        a["n_kernel_runs"] += 1
        a["n_rows"] += n_rows
        a["candidate_instructions"] += self.counter.run(*candidate)
        a["exact_closed_form_instructions"] += self.counter.run(*exact)
        if check is not None and check[1]:
            d = abs(check[0] - check[1]) / abs(check[1])
            a["exact_kernel_max_rel_diff_to_reference"] = max(a["exact_kernel_max_rel_diff_to_reference"] or 0.0, d)
        for name, value in (extra or {}).items():
            a[name] = a.get(name, 0) + value

    def result(self, key: str, exact_kernel: str, note: str | None = None) -> dict:
        a = self.acc.get(key)
        if not a:
            return {"measured": False, "reason": "負荷を測る標本のシナリオに、この候補が当てはまる行がなかった。"}
        out = {"measured": True, "unit": "executed bytecode instructions (sys.monitoring, INSTRUCTION events)",
               "exact_kernel": exact_kernel}
        out.update(a)
        c, e = a["candidate_instructions"], a["exact_closed_form_instructions"]
        out["ratio_candidate_to_exact"] = c / e if e else None
        if a["n_rows"]:
            out["candidate_instructions_per_row"] = c / a["n_rows"]
            out["exact_closed_form_instructions_per_row"] = e / a["n_rows"]
        if note:
            out["note"] = note
        return out
