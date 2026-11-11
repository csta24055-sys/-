#!/usr/bin/env python3
"""Verifier's own check of APP-1..APP-9 (pass 1: the 400-scenario study population).
Writes nothing into the repository."""
import copy
import json
import math
import sys
import time
from pathlib import Path

from refcalc import registry
from refcalc.base import periodic_events
from synth import population

N = int(sys.argv[1]) if len(sys.argv) > 1 else 400
STUDY = json.loads(Path("/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/04_VERIFICATION/approximation_study.json").read_text(encoding="utf-8"))["candidates"]
registry.load_all()
EPS = 1e-9


def fin_pos(c):
    return c is not None and c > 0 and not math.isinf(c)


def fin_nonneg(x):
    return x is not None and x >= 0 and not math.isinf(x)


def yw(T):
    return [0.0] + [min(1.0, T - (y - 1)) for y in range(1, math.ceil(T) + 1)]


def eyear(tau):
    return max(1, math.ceil(tau * (1 - EPS)))


def pct(vals, q):
    s = sorted(vals)
    if not s:
        return float("nan")
    pos = (len(s) - 1) * q / 100.0
    lo = int(math.floor(pos)); hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def S(xs):
    if not xs:
        return "n=0"
    a = [abs(x) for x in xs]
    return "n=%d mean %+.5f p95 %.5f min %+.5f max %+.5f under %.1f%% n>|2%%| %d" % (
        len(xs), sum(xs) / len(xs), pct(a, 95), min(xs), max(xs), 100 * sum(x < -1e-12 for x in xs) / len(xs), sum(v > 0.02 for v in a))


D = {}


def put(k, v):
    D.setdefault(k, []).append(v)


t0 = time.time()
n_cycle_lt1 = 0
min_slack = float("inf")       # min over rows of (true excluded weight) - (T/c - 1)
b3_rebuild = 0.0
pairs = {"all": 0, "ref_nonzero": 0, "drop_AP02": 0, "drop_AP03": 0, "drop_AP01": 0}
b5zero = {"AP-02": 0, "AP-03": 0}
ap14 = []
recs = []
idx = 0
cov_identity_worst = 0.0
for scn in population.verification_population(N, seed=20261111, max_size="M"):
    idx += 1
    res = registry.run_all(scn)
    T = scn.boundary.study_period
    w = yw(T)
    Y = len(w) - 1
    st = res["X-02"]["by_stage_all"]
    wlc = sum(st.values())
    mats, eqs = scn.materials, scn.equipment
    e0m = [res["A13-01"]["by_item"][i] + res["A13-03"]["by_item"][i] for i in range(len(mats))]
    e0e = res["X-01"]["by_item"]

    # ================= APP-1: repairs with the continuous count in the exclusion term =================
    exact = rowc = fixed = 0.0
    cls = {}
    cls_own = {}
    for i, row in enumerate(mats):
        r = row.repair_rate
        if not fin_nonneg(r):
            continue
        a = e0m[i] * r
        c = row.refresh_cycle
        if fin_pos(c):
            if c < 1.0:
                n_cycle_lt1 += 1
            ev = periodic_events(T, c)
            true_skip = sum(w[y] for y in {eyear(t) for t in ev})
            exact += a * (T - true_skip)
            approx_skip = min(T, max(0.0, T / c - 1.0))
            if a > 0:
                min_slack = min(min_slack, true_skip - approx_skip)
            rowc += a * (T - approx_skip)
            q = cls.setdefault(row.material_class, [0.0, 0.0]); q[0] += a; q[1] += a / c
        else:
            exact += a * T; fixed += a * T
    for j, eq in enumerate(eqs):
        r = eq.repair_rate
        if not fin_nonneg(r):
            continue
        a = e0e[j] * r
        ev = res["B4-01"]["events"][j]
        true_skip = sum(w[y] for y in {eyear(t) for t in ev})
        exact += a * (T - true_skip)
        if eq.replacement_event_list is not None:
            fixed += a * (T - true_skip)
        elif fin_pos(eq.service_life):
            c = eq.service_life
            if c < 1.0:
                n_cycle_lt1 += 1
            approx_skip = min(T, max(0.0, T / c - 1.0))
            if a > 0:
                min_slack = min(min_slack, true_skip - approx_skip)
            rowc += a * (T - approx_skip)
            q = cls.setdefault("EQUIPMENT", [0.0, 0.0]); q[0] += a; q[1] += a / c
        else:
            fixed += a * T
    B3 = st["B3"]
    if B3:
        b3_rebuild = max(b3_rebuild, abs(exact - B3) / B3)
        clsv = fixed + sum(q[0] * (T - min(T, max(0.0, T * q[1] / q[0] - 1.0))) for q in cls.values() if q[1] > 0) \
            + sum(q[0] * T for q in cls.values() if not q[1] > 0)
        put("APP1 row-level stage", (fixed + rowc) / B3 - 1)
        put("APP1 row-level total", (fixed + rowc - B3) / wlc)
        put("APP1 class-level stage", clsv / B3 - 1)
        put("APP1 class-level total", (clsv - B3) / wlc)
        put("APP1 AP-04 stage", res["B3-02"]["value"] / B3 - 1)
        put("APP1 row-level stage | T=%g" % T, (fixed + rowc) / B3 - 1)

    # ================= APP-2: electricity candidates per stage =================
    net, g, el = res["B6-04"]["by_year"], res["X-06"]["by_year"], res["B6-01"]["by_year"]
    share = scn.operation.facility_management_ratio
    if res["B6-01"]["computed"]:
        elec = sum(w[y] * el[y] for y in range(1, Y + 1))
        b603 = res["B6-03"]["value"]
        # conversion from the reference itself
        conv = None
        for y in range(1, Y + 1):
            if net[y] and g[y]:
                conv = el[y] / (net[y] * g[y]); break
        if elec > 0 and conv is not None:
            put("chk B2 == share*elec", abs(st["B2"] - share * elec) / st["B2"] if st["B2"] else 0.0)
            put("chk B6 == B603 - B2", abs(st["B6"] - (b603 - st["B2"])) / st["B6"])
            mean_net = sum(w[y] * net[y] for y in range(1, Y + 1)) / T
            mean_g = sum(w[y] * g[y] for y in range(1, Y + 1)) / T
            a8 = mean_net * mean_g * T * conv
            cands = {"AP-08": a8}
            for step, cid in ((5, "AP-09a"), (10, "AP-09b")):
                gi = []
                for k in range(Y):
                    lo = (k // step) * step
                    hi = min(lo + step, Y - 1)
                    if hi <= lo:
                        gi.append(g[lo + 1])
                    else:
                        gi.append(g[lo + 1] + (g[hi + 1] - g[lo + 1]) * (k - lo) / (hi - lo))
                cands[cid] = sum(w[y] * net[y] * gi[y - 1] for y in range(1, Y + 1)) * conv
            if res["X-06"]["source"] == "TABLE":
                cands["AP-09c"] = cands["AP-09a"]
            for cid, a in cands.items():
                d = a - elec
                put(cid + " on B6-03 (study)", d / b603)
                put(cid + " on stage B6", d * (1 - share) / st["B6"])
                if st["B2"]:
                    put(cid + " on stage B2", d * share / st["B2"])
                put(cid + " on electricity only", d / elec)
                put(cid + " total", d / wlc)

    # AP-18c: class route parameters, per stage
    cr = {}
    for i, row in enumerate(mats):
        eol = row.end_of_life
        if not fin_nonneg(eol.mass_kg):
            continue
        c = cr.setdefault(row.material_class, {"mass": 0.0, "rows": 0, "rt": {}})
        c["mass"] += eol.mass_kg; c["rows"] += 1
        for route in eol.routes:
            stg = "C4" if route.route == "LANDFILL" else "C3"
            rec = scn.factors.get(route.factor_id) if route.factor_id else None
            if rec is None or rec.licence_status != "PERMITTED_PUBLIC" or rec.stages != [stg] or not fin_nonneg(route.fraction):
                continue
            from synth import model as _m
            cv = _m.conversion_factor(scn.unit_conversions, "kg", rec.unit, ())
            if cv is None:
                continue
            q = c["rt"].setdefault(route.route, [0.0, 0.0, 0, stg]); q[0] += route.fraction; q[1] += cv * rec.value; q[2] += 1
    c3 = sum(c["mass"] * sum((q[0] / c["rows"]) * (q[1] / q[2]) for q in c["rt"].values() if q[3] == "C3") for c in cr.values())
    c4 = sum(c["mass"] * sum((q[0] / c["rows"]) * (q[1] / q[2]) for q in c["rt"].values() if q[3] == "C4") for c in cr.values())
    r3, r4, x14 = res["C3-01"]["value"], res["C4-01"]["value"], res["X-14"]["value"]
    put("AP-18c on C3-01+C4-01 (study)", (c3 + c4) / (r3 + r4) - 1)
    put("AP-18c on stage C3+C4 (incl X-14)", (c3 + c4 - r3 - r4) / (st["C3"] + st["C4"]))
    put("AP-18c on stage C3 (C3-01+X-14)", (c3 - r3) / st["C3"])
    put("AP-18c on C3-01 only", c3 / r3 - 1)
    put("AP-18c on stage C4", c4 / r4 - 1)
    put("X-14 share of stage C3", x14 / st["C3"])

    # ================= APP-3: propagation through the reference model =================
    def rerun(mut):
        s2 = copy.deepcopy(scn)
        s2.boundary.baseline_scenario = None
        mut(s2)
        return registry.run_all(s2, ids=["X-02"])["X-02"]["by_stage_all"]

    def m6(s2):   # 1/(1-w') = 1+w  <=>  w' = w/(1+w): order quantity becomes Q(1+w), installed quantity unchanged
        for row in s2.materials:
            if row.quantity_basis == "DESIGN" and row.waste_rate is not None and 0 <= row.waste_rate < 1:
                row.waste_rate = row.waste_rate / (1.0 + row.waste_rate)
    r2 = rerun(m6)
    put("AP-06 propagated total", sum(r2.values()) / wlc - 1)
    put("AP-06 local total (A1-A3 diff / WLC)", (r2["A1-A3"] - st["A1-A3"]) / wlc)
    for s_ in ("A1-A3", "A4", "A5", "B3", "B4", "B5", "C2", "C3", "C4"):
        if st[s_]:
            put("AP-06 propagated stage " + s_, r2[s_] / st[s_] - 1)

    md = {}
    for i, row in enumerate(mats):
        if res["A4-01"]["_row_lines"][i]:
            md.setdefault(row.transport.factor_id, []).append(i)
    mean_d = {k: sum(mats[i].transport.distance_km for i in v) / len(v) for k, v in md.items()}

    def m17(s2):
        for k, v in md.items():
            for i in v:
                s2.materials[i].transport.distance_km = mean_d[k]
    r2 = rerun(m17)
    put("AP-17 stage A4 (rerun)", r2["A4"] / st["A4"] - 1)
    put("AP-17 propagated total", sum(r2.values()) / wlc - 1)
    put("AP-17 local total (A4 diff / WLC)", (r2["A4"] - st["A4"]) / wlc)
    if st["B4"]:
        put("AP-17 propagated stage B4", r2["B4"] / st["B4"] - 1)
    if st["B5"]:
        put("AP-17 propagated stage B5", r2["B5"] / st["B5"] - 1)

    def m7b(s2):
        for i, row in enumerate(s2.materials):
            if row.composition is not None and res["X-15"]["kind"][i] == "COMPOSITE":
                kept = [c for c in row.composition if c.mass_fraction >= 0.05]
                tot = sum(c.mass_fraction for c in kept)
                if not kept or not tot:
                    continue
                for c in kept:
                    c.mass_fraction = c.mass_fraction / tot
                row.composition = kept
    r2 = rerun(m7b)
    put("AP-07b propagated total", sum(r2.values()) / wlc - 1)
    put("AP-07b local total (A1-A3 diff / WLC)", (r2["A1-A3"] - st["A1-A3"]) / wlc)
    if st["B3"]:
        put("AP-07b propagated stage B3", r2["B3"] / st["B3"] - 1)

    # ================= APP-4: AP-17 error is n * sample covariance(mass, distance) within a mode =================
    a4rows = sum(res["A4-01"]["by_item"][i] for v in md.values() for i in v)
    cov_term = 0.0
    approx17 = 0.0
    pear = []
    for k, v in md.items():
        ms = [mats[i].transport.mass_t for i in v]
        ds = [mats[i].transport.distance_km for i in v]
        # factor per tkm of the mode from the reference rows
        f = None
        for i in v:
            if ms[v.index(i)] * ds[v.index(i)] > 0:
                f = res["A4-01"]["by_item"][i] / (ms[v.index(i)] * ds[v.index(i)]); break
        if f is None:
            continue
        mb, db = sum(ms) / len(ms), sum(ds) / len(ds)
        sxy = sum((m - mb) * (d - db) for m, d in zip(ms, ds))
        cov_term += f * sxy
        approx17 += f * sum(ms) * db
        sxx = sum((m - mb) ** 2 for m in ms); syy = sum((d - db) ** 2 for d in ds)
        if len(v) >= 5 and sxx > 0 and syy > 0:
            pear.append((sxy / math.sqrt(sxx * syy), len(v), f * sum(m * d for m, d in zip(ms, ds))))
    # identity: reference rows - approximation == sum_modes f * Sxy
    cov_identity_worst = max(cov_identity_worst, abs((a4rows - approx17) - cov_term) / a4rows)
    put("AP-17 own stage A4", (approx17 - a4rows) / st["A4"])
    put("AP-17 -(sum f*Sxy)/A4 (covariance identity)", -cov_term / st["A4"])
    if pear:
        tot_e = sum(p[2] for p in pear)
        put("AP-17 raw Pearson r(mass,distance) within mode, emission-weighted mean per scenario", sum(p[0] * p[2] for p in pear) / tot_e)
        recs.append(((approx17 - a4rows) / a4rows, sum(p[0] * p[2] for p in pear) / tot_e))

    # ================= APP-6: AP-05 variants =================
    b1a = b1b = 0.0
    for d, dev in enumerate(scn.refrigerants):
        s_ = res["B1-02"]["_state"][d]
        if s_ is None:
            continue
        m0, r, gw = dev.charge_mass_kg, dev.annual_leak_rate, dev.gwp
        L = dev.replacement_loss_rate if (dev.replacement_loss_rate is not None and 0 <= dev.replacement_loss_rate <= 1) else None
        R = dev.end_of_life_recovery_rate if (dev.end_of_life_recovery_rate is not None and 0 <= dev.end_of_life_recovery_rate <= 1) else None
        nev = len(s_["before_events"])
        vb = m0 * r * T + (nev * m0 * L if L is not None else 0.0) + (m0 * (1 - R) if R is not None else 0.0)
        if dev.top_up:
            va = vb
        else:
            va = m0 * r * T
            per_year = {}
            for y, _ in s_["before_events"]:
                per_year[y] = per_year.get(y, 0) + 1
            k = 0.0
            for y in range(1, Y + 1):
                k += w[y]
                for _ in range(per_year.get(y, 0)):
                    if L is not None:
                        va += m0 * max(0.0, 1.0 - r * k) * L
                    k = 0.0
            if R is not None:
                va += m0 * max(0.0, 1.0 - r * k) * (1 - R)
        b1a += va * gw; b1b += vb * gw
        if not dev.top_up and gw:
            ex = res["B1-02"]["by_item"][d] / gw
            if L is not None:
                ex += sum(m for _, m in s_["before_events"]) * L
            if R is not None:
                ex += s_["end"] * (1 - R)
            if ex > 0:
                rk = r * T / (nev + 1)
                key = "rk<=0.05" if rk <= 0.05 else "0.05<rk<=0.2" if rk <= 0.2 else "rk>0.2"
                put("AP-05 device A(consistent) " + key, va / ex - 1)
                put("AP-05 device B(full charge) " + key, vb / ex - 1)
    if st["B1"]:
        put("AP-05 B1 variant A (consistent linearisation)", b1a / st["B1"] - 1)
        put("AP-05 B1 variant B (full charge everywhere)", b1b / st["B1"] - 1)

    # ================= APP-7: dropped (scenario, class) pairs =================
    q_ord = res["A13-05"]["q_ord"]
    refc, c1, c2, c3_ = {}, {}, {}, {}
    for i, row in enumerate(mats):
        u = e0m[i] + sum(res[k]["by_item"][i] for k in ("A4-01", "A4-02", "C2-01", "C3-01", "C4-01"))
        fid = row.installation_factor_id
        if fid is not None and q_ord[i] is not None:
            from refcalc.units_b import material_install_line
            inst = material_install_line(scn, row, q_ord[i])
            if inst is not None:
                u += inst[1] * scn.factors[inst[0]].value
        k = row.material_class
        refc[k] = refc.get(k, 0.0) + res["B4-03"]["by_item"][i] * u
        if fin_pos(row.refresh_cycle):
            c1[k] = c1.get(k, 0.0) + max(0.0, T / row.refresh_cycle - 1.0) * u
            c2[k] = c2.get(k, 0.0) + max(0.0, T / row.refresh_cycle - 0.5) * u
            c3_[k] = c3_.get(k, 0.0) + T / row.refresh_cycle * u
    for k, v in refc.items():
        pairs["all"] += 1
        if v:
            pairs["ref_nonzero"] += 1
        else:
            pairs["drop_AP01"] += bool(c1.get(k, 0.0)); pairs["drop_AP02"] += bool(c2.get(k, 0.0)); pairs["drop_AP03"] += bool(c3_.get(k, 0.0))
    b = scn.boundary
    b5 = res["B5-01"]
    if b5["computed"] and b.reconstruction_scenario != "NONE" and fin_pos(b.replacement_cycle) and st["B5"] == 0.0:
        base = b.reconstruction_scope_fraction * sum(st[s] for s in ("A1-A3", "A4", "A5", "C1", "C2", "C3", "C4"))
        b5zero["AP-02"] += bool(max(0.0, T / b.replacement_cycle - 0.5) * base)
        b5zero["AP-03"] += bool(T / b.replacement_cycle * base)

    # ================= APP-8: AP-14 on the first 80 scenarios =================
    if idx <= 80:
        def at(scn0, T2):
            s2 = copy.deepcopy(scn0)
            s2.boundary.study_period = T2
            s2.boundary.baseline_scenario = None
            return registry.run_all(s2, ids=["SUM-03"])["SUM-03"]["value"]
        v = {T2: at(scn, T2) for T2 in (50.0, 60.0, 75.0)}
        e = (v[50.0] + (v[75.0] - v[50.0]) * 10.0 / 25.0) / v[60.0] - 1
        has_eq_list = any(e_.replacement_event_list is not None for e_ in eqs)
        has_ch_list = any(d.change_years is not None for d in scn.refrigerants)
        # variant: explicit lists continued beyond the scenario's own period up to 75 years
        # (equipment: by its service life; refrigerant device: by the mean gap of its own list) -> no truncation
        s3 = copy.deepcopy(scn)
        n_no_life = 0
        def extend(lst, gap):
            if not fin_pos(gap):
                return None
            out = list(lst)
            last = out[-1] if out else 0.0
            gap = max(1.0, round(gap))
            while last + gap < 76.0:
                last += gap
                if last >= T:            # only add events the generator could not have placed
                    out.append(last)
            return out
        if T < 75:
            for e_ in s3.equipment:
                if e_.replacement_event_list is not None:
                    new = extend(e_.replacement_event_list, e_.service_life)
                    if new is None:
                        n_no_life += 1
                    else:
                        e_.replacement_event_list = new
            for d in s3.refrigerants:
                if d.change_years is not None:
                    gap = (d.change_years[-1] / len(d.change_years)) if d.change_years else None
                    new = extend(d.change_years, gap)
                    if new is None:
                        n_no_life += 1
                    else:
                        d.change_years = new
        v3 = {T2: at(s3, T2) for T2 in (50.0, 60.0, 75.0)}
        e3 = (v3[50.0] + (v3[75.0] - v3[50.0]) * 10.0 / 25.0) / v3[60.0] - 1
        ap14.append({"T": T, "e": e, "e_periodic": e3, "lists": has_eq_list or has_ch_list, "eq_lists": has_eq_list, "n_no_life": n_no_life,
                     "max_list_year": max([max(e_.replacement_event_list) for e_ in eqs if e_.replacement_event_list] or [0])})

print("elapsed %.0fs, scenarios %d" % (time.time() - t0, idx))
print("B3 rebuilt from own row data: worst relative difference %.2e" % b3_rebuild)
print("cycles below one year among repair rows: %d ; min over rows of (true excluded weight - min(T,max(0,T/c-1))) = %.3e" % (n_cycle_lt1, min_slack))
print("AP-17 covariance identity worst relative residual: %.2e" % cov_identity_worst)
for k in sorted(D):
    print("%-78s %s" % (k, S(D[k])))
print("APP-7 pairs:", pairs, "| sum of n in study JSON by_material_class AP-03:", sum(v["n"] for v in STUDY["AP-03"]["by_material_class"].values()),
      "AP-02:", sum(v["n"] for v in STUDY["AP-02"]["by_material_class"].values()))
print("APP-7 B5 reference zero & candidate nonzero:", b5zero, "| JSON:", {c: STUDY[c]["other_targets"]["B5（建替・大型改修の回数に適用）"]["n_reference_zero_candidate_nonzero"] for c in ("AP-02", "AP-03")},
      "| B5 n in JSON AP-03:", STUDY["AP-03"]["other_targets"]["B5（建替・大型改修の回数に適用）"]["stage_error"]["n"])
# APP-4: relation of the scenario error to the realised within-mode correlation
if recs:
    xs = [r[1] for r in recs]; ys = [r[0] for r in recs]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    cxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys)); cxx = sum((x - mx) ** 2 for x in xs); cyy = sum((y - my) ** 2 for y in ys)
    print("APP-4: across scenarios, corr(A4-01 row error, emission-weighted realised Pearson r) = %.3f ; mean realised r = %+.4f, range %+.3f..%+.3f ; sign agreement %.1f%%" % (
        cxy / math.sqrt(cxx * cyy), mx, min(xs), max(xs), 100 * sum((x > 0) == (y < 0) for x, y in zip(xs, ys)) / len(xs)))
# APP-8
for name, sel in (("all 80", lambda r: True), ("own T >= 75", lambda r: r["T"] >= 75), ("own T < 75", lambda r: r["T"] < 75), ("own T < 60", lambda r: r["T"] < 60),
                  ("own T < 75 with explicit lists", lambda r: r["T"] < 75 and r["lists"])):
    sub = [r for r in ap14 if sel(r)]
    print("AP-14 %-32s study-definition: %s" % (name, S([r["e"] for r in sub])))
    print("AP-14 %-32s lists continued to 75 years: %s" % (name, S([r["e_periodic"] for r in sub])))
print("AP-14: scenarios where some list could not be continued (empty list, no life):", sum(r["n_no_life"] > 0 for r in ap14))
print("AP-14 study JSON:", {k: STUDY["AP-14"]["stage_error"][k] for k in ("n", "mean_signed", "p95_abs", "max_over", "max_under")})
for cid in ("AP-04", "AP-05", "AP-06", "AP-07b", "AP-08", "AP-09a", "AP-09c", "AP-17", "AP-18b", "AP-18c"):
    s, t = STUDY[cid]["stage_error"], STUDY[cid]["total_error"]
    print("STUDY %-7s stage n=%d mean %+.5f p95 %.5f min %+.5f max %+.5f | total mean %+.5f p95 %.5f min %+.5f max %+.5f" % (
        cid, s["n"], s["mean_signed"], s["p95_abs"], s["max_under"], s["max_over"], t["mean_signed"], t["p95_abs"], t["max_under"], t["max_over"]))
