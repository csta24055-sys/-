#!/usr/bin/env python3
"""Independent re-implementation of approximate candidates (checker's own code).

Written from the candidate titles and the reference results; does not call bench.approx_study.
Writes only into the scratch folder.
"""
import copy
import json
import math
import sys
from pathlib import Path

import numpy as np

from refcalc import registry
from synth import population

HERE = Path(__file__).resolve().parent
N = int(sys.argv[1]) if len(sys.argv) > 1 else 400
STUDY_JSON = Path("/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/04_VERIFICATION/approximation_study.json")

registry.load_all()
EPS = 1e-9


def ok_period(c):
    return c is not None and c > 0 and not math.isinf(c)


def nonneg(x):
    return x is not None and x >= 0 and not math.isinf(x)


def count_ref(T, c):
    """reference count by the binding rule: #{n>=1: n*c < T*(1-1e-9)}"""
    if not ok_period(c):
        return 0
    n = 0
    while (n + 1) * c < T * (1 - EPS):
        n += 1
    return n


def ev_year(tau):
    return max(1, math.ceil(tau * (1 - EPS)))


def weights(T):
    Y = math.ceil(T)
    return [0.0] + [min(1.0, T - (y - 1)) for y in range(1, Y + 1)]


def st(xs):
    if not xs:
        return {"n": 0}
    a = np.asarray(xs, float)
    return {"n": len(xs), "mean": float(a.mean()), "p95": float(np.percentile(np.abs(a), 95)), "min": float(a.min()),
            "max": float(a.max()), "share_under": float((a < -1e-12).mean())}


E = {}      # name -> list of stage errors
TOT = {}    # name -> list of total errors (same difference / WLC)
ZERO = {}   # name -> reference zero, candidate nonzero


def add(name, ref, cand, wlc=None):
    if wlc:
        TOT.setdefault(name, []).append((cand - ref) / wlc)
    if ref == 0:
        if cand != 0:
            ZERO[name] = ZERO.get(name, 0) + 1
        return
    E.setdefault(name, []).append((cand - ref) / ref)


F = {"AP-01": lambda T, c: max(0.0, T / c - 1.0), "AP-02": lambda T, c: max(0.0, T / c - 0.5), "AP-03": lambda T, c: T / c}

extra = {}   # free-form lists for additional checks
def ex(name, v):
    extra.setdefault(name, []).append(v)

u_check = 0.0
n_scn = 0
excluded_stage_scn = 0
neg_factor = 0
bracket_viol = 0
for scn in population.verification_population(N, seed=20261111, max_size="M"):
    n_scn += 1
    res = registry.run_all(scn)
    T = scn.boundary.study_period
    w = weights(T)
    Y = len(w) - 1
    S = res["X-02"]["by_stage_all"]
    WLC = sum(S.values())
    if set(scn.boundary.included_lifecycle_stages) != set(S):
        excluded_stage_scn += 1
    if any(f.value < 0 for f in scn.factors.values()):
        neg_factor += 1
    mats, eqs = scn.materials, scn.equipment
    q_ord = res["A13-05"]["q_ord"]
    mfg = [res["A13-01"]["by_item"][i] + res["A13-03"]["by_item"][i] for i in range(len(mats))]

    # ------------------------------------------------ unit emission of one renewal (own derivation)
    um = []
    for i, row in enumerate(mats):
        u = mfg[i] + res["A4-01"]["by_item"][i] + res["A4-02"]["by_item"][i] + res["C2-01"]["by_item"][i] \
            + res["C3-01"]["by_item"][i] + res["C4-01"]["by_item"][i]
        fid = row.installation_factor_id
        if fid is not None and q_ord[i] is not None:
            rec = scn.factors.get(fid)
            if rec is not None and rec.licence_status == "PERMITTED_PUBLIC" and rec.stages == ["A5"]:
                from synth import model as _m
                conv = _m.conversion_factor(scn.unit_conversions, row.quantity_unit, rec.unit, row.conversions)
                if conv is not None:
                    u += q_ord[i] * conv * rec.value
        um.append(u)
        n_i = res["B4-03"]["by_item"][i]
        if n_i:
            e_i = res["B4-02"]["by_item_material"][i]
            if e_i:
                u_check = max(u_check, abs(u * n_i - e_i) / abs(e_i))
    ue = []
    for j, eq in enumerate(eqs):
        ev = res["B4-01"]["events"][j]
        e_j = res["B4-02"]["by_item_equipment"][j]
        if ev:
            ue.append(e_j / len(ev))               # exact unit emission from the reference itself
        else:
            # no event in the reference: rebuild from the row lines
            u = res["X-01"]["by_item"][j] + res["X-14"]["by_item"][j]
            from refcalc.units_b import equipment_extra_lines
            u += sum(act * scn.factors[fid].value for fid, act in equipment_extra_lines(scn, eq)[0])
            ue.append(u)
    B4 = S["B4"]

    # ------------------------------------------------ AP-01/02/03 on B4 and on B5; AP-20 bracket
    for cid, f in F.items():
        a = 0.0
        for i, row in enumerate(mats):
            if ok_period(row.refresh_cycle):
                a += f(T, row.refresh_cycle) * um[i]
        for j, eq in enumerate(eqs):
            if eq.replacement_event_list is not None:
                a += res["B4-02"]["by_item_equipment"][j]            # explicit lists stay exact
            elif ok_period(eq.service_life):
                a += f(T, eq.service_life) * ue[j]
        add(cid + ":B4", B4, a, WLC)
        if cid == "AP-01":
            lo = a
        if cid == "AP-03":
            hi = a
        b = scn.boundary
        if b.reconstruction_scenario != "NONE" and b.reconstruction_scope_fraction is not None \
                and 0 <= b.reconstruction_scope_fraction <= 1 and ok_period(b.replacement_cycle):
            base = sum(S[s] for s in ("A1-A3", "A4", "A5", "C1", "C2", "C3", "C4"))
            add(cid + ":B5", S["B5"], f(T, b.replacement_cycle) * b.reconstruction_scope_fraction * base, WLC)
    if B4 > 0:
        ex("AP-20:inside_strict", lo <= B4 <= hi)
        ex("AP-20:inside_tol", lo <= B4 * (1 + 1e-12) and B4 <= hi * (1 + 1e-12))
        ex("AP-20:width", (hi - lo) / B4)
        ex("AP-20:lo", lo / B4 - 1)
        ex("AP-20:hi", hi / B4 - 1)

    # ------------------------------------------------ AP-04
    add("AP-04", S["B3"], res["B3-02"]["value"], WLC)

    # ------------------------------------------------ AP-05 refrigerants
    # variant A (checker's reading of the title): leak of a charge cycle of k years = m0*r*k (year weighted),
    #   remaining mass before a change / at the end = m0*max(0, 1-r*k)
    # variant B: every non-top-up device treated as if it were topped up (full charge everywhere)
    b1_a = b1_b = 0.0
    for d, dev in enumerate(scn.refrigerants):
        stt = res["B1-02"]["_state"][d]
        if stt is None:
            continue
        m0, r, g = dev.charge_mass_kg, dev.annual_leak_rate, dev.gwp
        ev_years = [y for y, _ in stt["before_events"]]
        L = dev.replacement_loss_rate if (dev.replacement_loss_rate is not None and 0 <= dev.replacement_loss_rate <= 1) else None
        R = dev.end_of_life_recovery_rate if (dev.end_of_life_recovery_rate is not None and 0 <= dev.end_of_life_recovery_rate <= 1) else None
        # variant B
        vb = m0 * r * T
        if L is not None:
            vb += len(ev_years) * m0 * L
        if R is not None:
            vb += m0 * (1 - R)
        b1_b += vb * g
        # variant A
        if dev.top_up:
            va = vb
        else:
            va = m0 * r * T
            acc = 0.0      # weighted years since the last charge
            evset = {}
            for y in ev_years:
                evset[y] = evset.get(y, 0) + 1
            for y in range(1, Y + 1):
                acc += w[y]
                for _ in range(evset.get(y, 0)):
                    if L is not None:
                        va += m0 * max(0.0, 1 - r * acc) * L
                    acc = 0.0
            if R is not None:
                va += m0 * max(0.0, 1 - r * acc) * (1 - R)
        b1_a += va * g
    add("AP-05:A(consistent linear)", S["B1"], b1_a, WLC)
    add("AP-05:B(as topped up)", S["B1"], b1_b, WLC)

    # ------------------------------------------------ AP-06
    a6 = res["X-01"]["value"]
    for i, row in enumerate(mats):
        e = mfg[i] + res["A13-04"]["by_item"][i]
        if row.quantity_basis == "DESIGN" and row.waste_rate is not None and 0 <= row.waste_rate < 1:
            # reference uses Q/(1-w); candidate uses Q*(1+w)
            e = e * (1 - row.waste_rate) * (1 + row.waste_rate)
        a6 += e
    add("AP-06", S["A1-A3"], a6, WLC)

    # ------------------------------------------------ AP-07a/b composites (from the row lines of A13-01)
    kinds = res["X-15"]["kind"]
    ref7 = c7a = c7b = 0.0
    for i, row in enumerate(mats):
        if kinds[i] != "COMPOSITE" or q_ord[i] is None:
            continue
        lines = res["A13-01"]["_row_lines"][i]
        assert len(lines) == len(row.composition)
        full = kept = share = 0.0
        for (fid, act), comp in zip(lines, row.composition):
            assert fid == comp.factor_id
            e = act * scn.factors[fid].value
            full += e
            if comp.mass_fraction >= 0.05:
                kept += e
                share += comp.mass_fraction
        ref7 += full
        c7a += kept
        c7b += kept / share if share else 0.0
    add("AP-07a", ref7, c7a, WLC)
    add("AP-07b", ref7, c7b, WLC)
    ex("AP-07:ref_vs_X03", abs(ref7 - res["X-03"]["value"]) / res["X-03"]["value"] if res["X-03"]["value"] else 0.0)

    # ------------------------------------------------ electricity: AP-08, AP-09a, AP-09c
    op = scn.operation
    net = res["B6-04"]["by_year"]
    g = res["X-06"]["by_year"]
    el = res["B6-01"]["by_year"]
    if res["B6-01"]["computed"]:
        elec = sum(w[y] * el[y] for y in range(1, Y + 1))
        conv_el = None
        for y in range(1, Y + 1):
            if net[y] and g[y]:
                conv_el = el[y] / (net[y] * g[y])
                break
        b603 = res["B6-03"]["value"]
        fuel = b603 - elec
        if elec > 0 and conv_el is not None:
            mean_net = sum(w[y] * net[y] for y in range(1, Y + 1)) / T
            mean_g = sum(w[y] * g[y] for y in range(1, Y + 1)) / T
            a8_el = mean_net * mean_g * T * conv_el
            add("AP-08", b603, a8_el + fuel, WLC)
            share = op.facility_management_ratio
            # the two STAGES that the purchased electricity feeds (by_stage_all): B6 = B6-03 - B2-01, B2 = B2-01
            add("AP-08:stageB6", S["B6"], fuel + a8_el * (1 - share), WLC)
            add("AP-08:stageB2", S["B2"], a8_el * share, WLC)
            pk = {op.electricity.kind, op.onsite_generation.kind, op.onsite_export.kind}
            ex("AP-08:" + ("CONSTANT" if pk == {"CONSTANT"} else "TABLE" if "TABLE" in pk else "LINEAR_TREND"), (a8_el - elec) / b603)
            # 5-year knots: indices 0,5,10,... and the last index; linear in between
            for step, cid in ((5, "AP-09a"), (10, "AP-09b")):
                gy = g[1:]                       # index k = y-1
                knots = sorted(set(list(range(0, Y, step)) + [Y - 1]))
                gi = list(np.interp(range(Y), knots, [gy[k] for k in knots]))
                a9_el = sum(w[y] * net[y] * gi[y - 1] for y in range(1, Y + 1)) * conv_el
                add(cid, b603, a9_el + fuel, WLC)
                ex(cid + ":" + op.grid.kind, (a9_el - elec) / b603)
                if cid == "AP-09a" and res["X-06"]["source"] == "TABLE":
                    add("AP-09c", b603, a9_el + fuel, WLC)
                    add("AP-09c:stageB6", S["B6"], fuel + a9_el * (1 - share), WLC)
                    add("AP-09c:stageB2", S["B2"], a9_el * share, WLC)
                    add("AP-09c:electricity only", elec, a9_el, WLC)
                if cid == "AP-09a":
                    add("AP-09a:stageB2", S["B2"], a9_el * share, WLC)

    # ------------------------------------------------ AP-17 transport
    modes = {}
    a4_rows = 0.0
    for i, row in enumerate(mats):
        ln = res["A4-01"]["_row_lines"][i]
        if not ln:
            continue
        tr = row.transport
        e = res["A4-01"]["by_item"][i]
        a4_rows += e
        per_tkm = e / (tr.mass_t * tr.distance_km) if tr.mass_t * tr.distance_km else None
        m = modes.setdefault(tr.factor_id, {"mass": 0.0, "dist": 0.0, "n": 0, "f": None})
        m["mass"] += tr.mass_t
        m["dist"] += tr.distance_km
        m["n"] += 1
        if per_tkm is not None:
            m["f"] = per_tkm
    a17 = sum(m["mass"] * (m["dist"] / m["n"]) * (m["f"] or 0.0) for m in modes.values())
    add("AP-17", S["A4"], S["A4"] - a4_rows + a17, WLC)

    # ------------------------------------------------ AP-18a/b/c class parameters
    cls = {}
    for i, row in enumerate(mats):
        c = cls.setdefault(row.material_class, {"U": 0.0, "Uc": 0.0, "fix": 0.0, "E0r": 0.0})
        if ok_period(row.refresh_cycle):
            c["U"] += um[i]
            c["Uc"] += um[i] / row.refresh_cycle
        if nonneg(row.repair_rate):
            c["E0r"] += mfg[i] * row.repair_rate
    c = cls.setdefault("EQUIPMENT", {"U": 0.0, "Uc": 0.0, "fix": 0.0, "E0r": 0.0})
    for j, eq in enumerate(eqs):
        if eq.replacement_event_list is not None:
            c["fix"] += res["B4-02"]["by_item_equipment"][j]
        elif ok_period(eq.service_life):
            c["U"] += ue[j]
            c["Uc"] += ue[j] / eq.service_life
        if nonneg(eq.repair_rate):
            c["E0r"] += res["X-01"]["by_item"][j] * eq.repair_rate
    a18a = a18b = 0.0
    for k, c in cls.items():
        cbar = c["U"] / c["Uc"] if c["Uc"] else None
        nb = count_ref(T, cbar) if cbar else 0
        a18a += c["fix"] + nb * c["U"]
        skip = sum(w[y] for y in {ev_year(n * cbar) for n in range(1, nb + 1)}) if nb else 0.0
        a18b += c["E0r"] * (T - skip)
    add("AP-18a", B4, a18a, WLC)
    add("AP-18b", S["B3"], a18b, WLC)

    ref_c = res["C3-01"]["value"] + res["C4-01"]["value"]
    rc = {}
    for i, row in enumerate(mats):
        eol = row.end_of_life
        if not nonneg(eol.mass_kg):
            continue
        c = rc.setdefault(row.material_class, {"mass": 0.0, "rows": 0, "fr": {}, "fac": {}, "nf": {}})
        c["mass"] += eol.mass_kg
        c["rows"] += 1
        for route in eol.routes:
            rec = scn.factors.get(route.factor_id) if route.factor_id else None
            stage = "C4" if route.route == "LANDFILL" else "C3"
            if rec is None or rec.stages != [stage] or rec.licence_status != "PERMITTED_PUBLIC" or rec.unit != "kg" or not nonneg(route.fraction):
                ex("AP-18c:route_unusable", 1)
                continue
            c["fr"][route.route] = c["fr"].get(route.route, 0.0) + route.fraction
            c["fac"][route.route] = c["fac"].get(route.route, 0.0) + rec.value
            c["nf"][route.route] = c["nf"].get(route.route, 0) + 1
    a18c = sum(c["mass"] * sum((c["fr"][r] / c["rows"]) * (c["fac"][r] / c["nf"][r]) for r in c["fr"]) for c in rc.values())
    add("AP-18c", ref_c, a18c, WLC)
    add("AP-18", S["B3"] + B4 + ref_c, a18a + a18b + a18c, WLC)

    # ------------------------------------------------ AP-19a/b
    rr = [(mfg[i], row.unquantified_cost_ratio) for i, row in enumerate(mats)
          if row.unquantified_cost_ratio is not None and 0 < row.unquantified_cost_ratio < 1]
    if rr:
        base = sum(e for e, _ in rr)
        rbar = sum(r for _, r in rr) / len(rr)
        rmax = max(r for _, r in rr)
        add("AP-19a", res["A13-04"]["value"], base * rbar / (1 - rbar), WLC)
        add("AP-19b", res["A13-04"]["value"], base * rmax / (1 - rmax), WLC)
        # checker's variant: ONE ratio for the whole bill (mean over ALL rows, applied to all material emission)
        allr = [row.unquantified_cost_ratio or 0.0 for row in mats]
        rall = sum(allr) / len(allr)
        add("AP-19a:one ratio over all rows", res["A13-04"]["value"], sum(mfg) * rall / (1 - rall), WLC)

    # ------------------------------------------------ AP-22a
    add("AP-22a", res["SUM-03"]["value"], res["X-05"]["value"], res["SUM-03"]["value"])
    ex("SUM03_vs_WLC", res["SUM-03"]["value"] / WLC - 1)

    # ------------------------------------------------ propagation check: AP-06 applied through the whole model
    s2 = copy.deepcopy(scn)
    s2.boundary.baseline_scenario = None
    for row in s2.materials:
        if row.quantity_basis == "DESIGN" and row.quantity is not None and row.waste_rate is not None and 0 <= row.waste_rate < 1:
            row.quantity = row.quantity * (1 - row.waste_rate) * (1 + row.waste_rate)   # order quantity becomes Q*(1+w)
    r2 = registry.run_all(s2, ids=["X-02"])["X-02"]["by_stage_all"]
    ex("AP-06:propagated total", sum(r2.values()) / WLC - 1)
    ex("AP-06:propagated A1-A3", r2["A1-A3"] / S["A1-A3"] - 1)
    for s_ in ("A4", "B3", "B4", "B5", "A5"):
        if S[s_]:
            ex("AP-06:propagated " + s_, r2[s_] / S[s_] - 1)
    ex("AP-06:own A1-A3 vs propagated A1-A3", abs(a6 - r2["A1-A3"]) / S["A1-A3"])

    # ------------------------------------------------ propagation check for AP-19a (A13-04 feeds B5)
    # ------------------------------------------------ candidate not tried by the study: B3 with a continuous skip count
    b3_v1 = b3_v2 = b3_v3 = 0.0
    A = Ac = 0.0
    for i, row in enumerate(mats):
        r = row.repair_rate
        if not nonneg(r):
            continue
        e0r = mfg[i] * r
        c = row.refresh_cycle
        if ok_period(c):
            b3_v1 += e0r * (T - (T / c - 0.5))
            b3_v2 += e0r * (T - max(0.0, T / c - 0.5))
            b3_v3 += e0r * (T - max(0.0, T / c - 1.0))
        else:
            b3_v1 += e0r * T; b3_v2 += e0r * T; b3_v3 += e0r * T
    for j, eq in enumerate(eqs):
        r = eq.repair_rate
        if not nonneg(r):
            continue
        e0r = res["X-01"]["by_item"][j] * r
        if eq.replacement_event_list is not None:
            sk = sum(w[y] for y in {ev_year(t) for t in res["B4-01"]["events"][j]})
            b3_v1 += e0r * (T - sk); b3_v2 += e0r * (T - sk); b3_v3 += e0r * (T - sk)
        elif ok_period(eq.service_life):
            c = eq.service_life
            b3_v1 += e0r * (T - (T / c - 0.5))
            b3_v2 += e0r * (T - max(0.0, T / c - 0.5))
            b3_v3 += e0r * (T - max(0.0, T / c - 1.0))
        else:
            b3_v1 += e0r * T; b3_v2 += e0r * T; b3_v3 += e0r * T
    add("NEW-B3:skip=T/c-1/2 (unclamped)", S["B3"], b3_v1, WLC)
    add("NEW-B3:skip=max(0,T/c-1/2)", S["B3"], b3_v2, WLC)
    add("NEW-B3:skip=max(0,T/c-1) (lower bound of count)", S["B3"], b3_v3, WLC)

print("scenarios", n_scn, "| max rel diff of own unit emission vs reference rows", u_check,
      "| scenarios with excluded stages", excluded_stage_scn, "| scenarios with a negative factor", neg_factor)

study = json.loads(STUDY_JSON.read_text(encoding="utf-8"))["candidates"]


def study_stat(cid):
    if cid.endswith(":B4"):
        return study[cid[:-3]]["stage_error"], study[cid[:-3]]["total_error"]
    if cid.endswith(":B5"):
        o = study[cid[:-3]]["other_targets"]["B5（建替・大型改修の回数に適用）"]
        return o["stage_error"], o["total_error"]
    if cid in study and "stage_error" in study[cid]:
        return study[cid]["stage_error"], study[cid]["total_error"]
    return None, None


out = {}
print(f"{'candidate':46s} {'n':>5s} {'mean':>10s} {'p95|e|':>9s} {'min':>10s} {'max':>10s} {'under%':>7s}   study: n mean p95 min max   | zero")
for name in sorted(set(E) | set(ZERO)):
    s = st(E.get(name, []))
    t = st(TOT.get(name, []))
    out[name] = {"stage": s, "total": t, "zero_reference_candidate_nonzero": ZERO.get(name, 0)}
    line = f"{name:46s} {s['n']:5d} {s['mean']:+10.5f} {s['p95']:9.5f} {s['min']:+10.5f} {s['max']:+10.5f} {s['share_under']*100:6.1f}%"
    ss, tt = study_stat(name.split(":")[0] if name.split(":")[-1] not in ("B4", "B5") else name)
    if name.count(":") and name.split(":")[-1] not in ("B4", "B5"):
        ss = tt = None
    if ss and ss.get("n"):
        line += f"   {ss['n']:4d} {ss['mean_signed']:+.5f} {ss['p95_abs']:.5f} {ss['max_under']:+.5f} {ss['max_over']:+.5f}"
        if N == 400:
            d = max(abs(s['mean'] - ss['mean_signed']), abs(s['p95'] - ss['p95_abs']), abs(s['min'] - ss['max_under']), abs(s['max'] - ss['max_over']))
            line += f"  maxdiff {d:.2e}" + ("  n differs" if s['n'] != ss['n'] else "")
    line += f" | {ZERO.get(name, 0)}"
    print(line)
    if t.get("n"):
        line = f"{'   total':46s} {t['n']:5d} {t['mean']:+10.5f} {t['p95']:9.5f} {t['min']:+10.5f} {t['max']:+10.5f} {t['share_under']*100:6.1f}%"
        if tt and tt.get("n"):
            line += f"   {tt['n']:4d} {tt['mean_signed']:+.5f} {tt['p95_abs']:.5f} {tt['max_under']:+.5f} {tt['max_over']:+.5f}"
        print(line)
print()
for k in sorted(extra):
    v = extra[k]
    if all(isinstance(x, bool) for x in v):
        print(f"{k:46s} n={len(v)} true={sum(v)}")
        out[k] = {"n": len(v), "true": int(sum(v))}
    else:
        s = st(v)
        out[k] = s
        print(f"{k:46s} {s['n']:5d} {s['mean']:+10.5f} {s['p95']:9.5f} {s['min']:+10.5f} {s['max']:+10.5f} {s['share_under']*100:6.1f}%")
(HERE / f"recheck_out_{N}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
