"""Stage-B oracle comparison (results-producing script; the ONLY place the frozen reference
is imported). Usage:
  PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 python3 -B tests/compare_refcalc.py SUBSTAGE [scenario-keys]
SUBSTAGE in S3a S3b S3c S3d S3e. Writes results/stageB_<SUBSTAGE>.json.
"""
import copy
import json
import math
import os
import sys
import time
from fractions import Fraction

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STUDY = os.path.normpath(os.path.join(ROOT, "..", ".."))
sys.path.insert(0, os.path.join(STUDY, "10_TRANSFORM_STUDY", "research_code"))
sys.path.insert(0, ROOT)

from tstudy import baseline, scenarios  # noqa: E402  (oracle, test-side only)

FROZEN = baseline.assert_frozen()
from model_building import audit_counts, group_event_counts, simulate_building  # noqa: E402

TOL = 1e-9
T_CAND = [1, 7.5, 20, 33.3, 42.5, 59.9, 60, 60.1, 75, 99.9, 100]
SUB = {"S3a": (("AC",), ("A1-A3", "A4", "A5", "C1", "C2", "C3", "C4")),
       "S3b": (("OP",), ("B2", "B6", "B7")),
       "S3c": (("AC", "EV"), ("A1-A3", "A4", "A5", "C1", "C2", "C3", "C4", "B3", "B4", "B5")),
       "S3d": (("REF",), ("B1",)),
       "S3e": (("AC", "OP", "EV", "REF"), tuple(scenarios.baseline.load() and __import__("synth").model.LIFECYCLE_STAGES))}


def scenario_set(keys):
    bm = scenarios.benchmark()
    ev = scenarios.evaluation_set(10)
    pool = {"S": bm[0], "M": bm[1], "E0": ev[0], "E1": ev[1], "E2": ev[2], "E3": ev[3]}
    return [(k, pool[k]) for k in keys]


def usable_T(scn):
    out, band = [], []
    for T in T_CAND:
        why = scenarios.valid_domain(scenarios.with_period(scn, T))
        (band if why else out).append(T)
    return out[:10], band


def ref_values(scn, T, stages):
    res = baseline.run_reference(scenarios.with_period(scn, T))
    st = res["X-02"]["by_stage"]
    inc = set(scn.boundary.included_lifecycle_stages)
    z = sum(st.get(s, 0.0) for s in ("C1", "C2", "C3", "C4") if s in inc) + \
        (res["B1-04"]["value"] if "B1" in inc else 0.0)
    events = sum(res["B4-03"]["by_item"]) + res["B4-01"]["n_events"]
    return {"stages": {s: st[s] for s in stages if s in st}, "SUM-03": res["SUM-03"]["value"], "Z": z,
            "events": events, "complete": res["X-02"]["complete"]}


def rel(a, b):
    a, b = float(a), float(b)
    return abs(a - b) / max(abs(b), 1e-300) if b != 0 else abs(a)


def run(sub, keys, iota=None):
    blocks, stages = SUB[sub]
    report = {"substage": sub, "frozen_trees": FROZEN, "tolerance": TOL, "blocks": blocks, "rows": [], "max_rel": {}}
    for key, scn in scenario_set(keys):
        if iota is not None:
            scn = copy.deepcopy(scn)
            scn.boundary.included_lifecycle_stages = list(iota)
        Ts, band = usable_T(scn)
        t0 = time.time()
        out = simulate_building(scn, Ts, "original", blocks)
        dt = time.time() - t0
        counts = audit_counts(out)
        for T in Ts:
            ref = ref_values(scn, T, stages)
            got = out["by_T"][Fraction(T)]
            row = {"scenario": key, "id": scn.meta.scenario_id, "T": T, "stages": {}}
            covered_abs = covered_ok = 0.0
            for s in stages:
                if s not in ref["stages"]:
                    continue
                a, b = got["stages"].get(s, 0), ref["stages"][s]
                e = rel(a, b)
                row["stages"][s] = {"circuit": float(a), "refcalc": b, "rel": e}
                report["max_rel"][s] = max(report["max_rel"].get(s, 0.0), e)
                covered_abs += abs(b)
                covered_ok += abs(b) if e <= TOL else 0.0
            part_c = sum(float(got["stages"].get(s, 0)) for s in row["stages"])
            part_r = sum(v["refcalc"] for v in row["stages"].values())
            row["partial_C"] = {"circuit": part_c, "refcalc": part_r, "rel": rel(part_c, part_r)}
            report["max_rel"]["partial_C"] = max(report["max_rel"].get("partial_C", 0.0), row["partial_C"]["rel"])
            if sub in ("S3a", "S3d", "S3e"):
                zr = ref["Z"] if sub != "S3a" else sum(ref["stages"].get(s, 0) for s in ("C1", "C2", "C3", "C4"))
                if sub == "S3d":
                    zr = ref["Z"] - sum(baseline.run_reference(scenarios.with_period(scn, T))["X-02"]["by_stage"].get(s, 0)
                                        for s in ("C1", "C2", "C3", "C4") if s in set(scn.boundary.included_lifecycle_stages))
                row["Z"] = {"circuit": float(got["Z"]), "refcalc": zr, "rel": rel(got["Z"], zr)}
                report["max_rel"]["Z"] = max(report["max_rel"].get("Z", 0.0), row["Z"]["rel"])
            if sub == "S3e":
                row["C_total"] = {"circuit": float(got["C"]), "refcalc": ref["SUM-03"], "rel": rel(got["C"], ref["SUM-03"])}
                report["max_rel"]["C_total"] = max(report["max_rel"].get("C_total", 0.0), row["C_total"]["rel"])
                row["M"] = float(got["M"])
            if sub in ("S3c", "S3e"):
                n = group_event_counts(out, Fraction(T))
                row["events"] = {"circuit": n, "refcalc": ref["events"], "equal": n == ref["events"]}
                report["max_rel"]["event_count_mismatch"] = report["max_rel"].get("event_count_mismatch", 0) + (n != ref["events"])
            row["coverage"] = covered_ok / covered_abs if covered_abs else 1.0
            report["rows"].append(row)
        report.setdefault("runs", []).append({"scenario": key, "id": scn.meta.scenario_id, "T_used": Ts,
                                               "T_excluded_valid_domain": band, "seconds": dt,
                                               "times": out["times"], "sim_stats": out["sim_stats"],
                                               "counts": counts, "kinds": out["kinds"],
                                               "iota": sorted(scn.boundary.included_lifecycle_stages)})
        print(sub, key, scn.meta.scenario_id, f"{dt:.1f}s", {k: f"{v:.2e}" for k, v in report["max_rel"].items()}, flush=True)
    report["pass"] = all(v <= TOL for k, v in report["max_rel"].items() if k != "event_count_mismatch") and \
        report["max_rel"].get("event_count_mismatch", 0) == 0
    return report


if __name__ == "__main__":
    sub = sys.argv[1]
    keys = sys.argv[2].split(",") if len(sys.argv) > 2 else ["S", "M", "E0", "E1", "E2"]
    rep = run(sub, keys)
    with open(os.path.join(ROOT, "results", f"stageB_{sub}.json"), "w") as f:
        json.dump(rep, f, indent=1, default=str)
    print("PASS" if rep["pass"] else "FAIL", rep["max_rel"])
