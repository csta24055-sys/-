"""V2: verifier's own oracle harness for the full synthetic building (stage B, snapshot 80ec2de).

System under test: the snapshot's `model_building.simulate_building` (black box: scenario in,
readouts out). Oracle: the frozen refcalc via tstudy.baseline.run_reference (imported here only,
after tstudy.baseline.assert_frozen()). Scenarios and T are chosen by the verifier, disjoint from
the builder's set (benchmark S, M and evaluation_set(10)[0..2]).

Usage: python3 -B v2_oracle.py TAG KEY[,KEY...] [iota-name]
  KEY = E3..E9 (evaluation_set(10)[k]) or EDGE:<name> (tstudy edge_set)
  iota-name in {full, no_B2, no_B1, only_B6, only_B4, only_B1, B2B6only}
Writes results/v2_oracle_<TAG>.json.
"""
from __future__ import annotations

import copy
import json
import math
import os
import sys
import time
from fractions import Fraction as Fr

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import SNAP, save  # noqa: E402

STUDY = "/home/user/-/whole-life-carbon-jcat-study"
sys.path.insert(0, os.path.join(STUDY, "10_TRANSFORM_STUDY", "research_code"))
from tstudy import baseline, scenarios  # noqa: E402

FROZEN = baseline.assert_frozen()          # stop here if the oracle tree is not the frozen one
if SNAP not in sys.path:
    sys.path.insert(0, SNAP)
from model_building import simulate_building  # noqa: E402  (system under test)

STAGES = ("A1-A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "C1", "C2", "C3", "C4")
T_ADV = [0.3, 0.999999, 1.000001, 7.5, 14.000001, 15.999999, 16.000001, 20.000001, 28.000001, 33.3,
         47.000001, 59.999999, 60.000001, 94.000001, 99.9, 129.999999, 130.0]
IOTA = {"full": list(STAGES), "no_B2": [s for s in STAGES if s != "B2"], "no_B1": [s for s in STAGES if s != "B1"],
        "only_B6": ["B6"], "only_B4": ["B4"], "only_B1": ["B1"], "B2B6only": ["B2", "B6"],
        "no_B2_B6": [s for s in STAGES if s not in ("B2", "B6")]}
EPS = 1e-9
TOL = 1e-9


def pool(key):
    if key.startswith("EDGE:"):
        name = key[5:]
        return dict(scenarios.edge_set())[name]
    k = int(key[1:])
    return scenarios.evaluation_set(10)[k]


def event_times(scn, T):
    """All nominal event times (float, as the source builds them) up to T + 2."""
    out = []

    def per(c):
        if c is None or not (c > 0) or math.isinf(c):
            return
        n = 1
        while n * c <= T + 2 and n < 100000:
            out.append(n * c)
            n += 1
    for m in scn.materials:
        per(m.refresh_cycle)
    for e in scn.equipment:
        if e.replacement_event_list is not None:
            out += [float(t) for t in e.replacement_event_list if t > 0]
        else:
            per(e.service_life)
    for d in scn.refrigerants:
        if d.change_years is not None:
            out += [float(t) for t in d.change_years if t > 0]
        else:
            per(d.service_life)
    if scn.boundary.reconstruction_scenario != "NONE":
        per(scn.boundary.replacement_cycle)
    return out


def in_band(scn, T):
    """T in (K, sw(tau)] for some event: K = ceil(fl(tau (1-eps))), sw = tau/(1-eps)."""
    for tau in event_times(scn, T):
        K = math.ceil(tau * (1.0 - EPS))
        sw = tau / (1.0 - EPS)
        if K < sw and K < T <= sw:
            return True
    return False


def rel(a, b):
    a, b = float(a), float(b)
    if b == 0:
        return abs(a)
    return abs(a - b) / abs(b)


def circuit_counts(out, T):
    tau = out["core"].u.tau_y
    lim = Fr(T) * tau
    n_b4 = n_b5 = 0
    for gt, g in out["groups"].items():
        n = 0
        for e in out["events"]:
            if e["type"] != "cmp" or not e["value"]:
                continue
            nm = e["name"]
            if nm == f"{gt}.clk.late" or (nm.startswith(f"{gt}.x") and nm.endswith(".late")):
                t = Fr(e["t"]) if isinstance(e["t"], (int, Fr)) else Fr(*map(int, e["t"].split("/"))) if "/" in e["t"] else Fr(int(e["t"]))
                if t < lim:
                    n += 1
        n_b4 += n * g["rows"]
    for e in out["events"]:
        if e["type"] == "cmp" and e["value"] and e["name"] == "b5.clk.late":
            t = Fr(*map(int, e["t"].split("/"))) if "/" in str(e["t"]) else Fr(int(e["t"]))
            if t < lim:
                n_b5 += 1
    return n_b4, n_b5


def run(tag, keys, iota_name="full", Tlist=None):
    rep = {"frozen": FROZEN, "tolerance": TOL, "iota": iota_name, "runs": [], "max_rel": {}, "in_band_rows": []}
    for key in keys:
        scn = copy.deepcopy(pool(key))
        scn.boundary.included_lifecycle_stages = list(IOTA[iota_name])
        cand = Tlist or T_ADV
        Ts, excl = [], []
        for T in cand:
            why = scenarios.valid_domain(scenarios.with_period(scn, T))
            if why:
                excl.append((T, why[:1]))
            elif in_band(scn, T):
                excl.append((T, ["in band (K, sw]"]))
                rep["in_band_rows"].append((key, T))
            else:
                Ts.append(T)
        if not Ts:
            rep["runs"].append({"key": key, "id": scn.meta.scenario_id, "T_used": [], "excluded": excl})
            continue
        t0 = time.time()
        try:
            out = simulate_building(scn, Ts, "original")
        except Exception as e:  # a crash of the system under test is a finding, not a harness error
            import traceback
            tb = traceback.extract_tb(e.__traceback__)
            where = [f"{os.path.basename(f.filename)}:{f.lineno}" for f in tb if "cf_snapshot" in f.filename][-3:]
            rep["runs"].append({"key": key, "id": scn.meta.scenario_id, "T_used": Ts, "excluded": excl,
                                "CRASH": f"{type(e).__name__}: {e}", "where": where})
            rep["max_rel"]["crashes"] = rep["max_rel"].get("crashes", 0) + 1
            print(tag, key, "CRASH", type(e).__name__, e, where, flush=True)
            continue
        t_c = time.time() - t0
        rows = []
        t_ref = 0.0
        for T in Ts:
            t1 = time.time()
            res = baseline.run_reference(scenarios.with_period(scn, T))
            t_ref += time.time() - t1
            st = res["X-02"]["by_stage"]
            inc = set(scn.boundary.included_lifecycle_stages)
            zr = sum(st.get(s, 0.0) for s in ("C1", "C2", "C3", "C4") if s in inc) + \
                (res["B1-04"]["value"] if "B1" in inc else 0.0)
            got = out["by_T"][Fr(T)]
            row = {"T": T, "stages": {}, "complete": res["X-02"]["complete"]}
            for s in STAGES:
                if s in st:
                    e = rel(got["stages"].get(s, 0), st[s])
                    row["stages"][s] = e
                    rep["max_rel"][s] = max(rep["max_rel"].get(s, 0.0), e)
                elif s in got["stages"] and got["stages"][s] != 0:
                    row["stages"][s] = "circuit nonzero for excluded stage"
                    rep["max_rel"][s + "_excluded_nonzero"] = 1
            for nm, a, b in (("C", got["C"], res["SUM-03"]["value"]), ("Z", got["Z"], zr), ("M", got["M"], res["SUM-03"]["value"] - zr)):
                e = rel(a, b)
                row[nm] = {"circuit": float(a), "oracle": b, "rel": e}
                rep["max_rel"][nm] = max(rep["max_rel"].get(nm, 0.0), e)
            nb4, nb5 = circuit_counts(out, T)
            rb4 = sum(res["B4-03"]["by_item"]) + res["B4-01"]["n_events"]
            rb5 = res["B5-01"]["n_events"]
            row["events"] = {"B4": [nb4, rb4], "B5": [nb5, rb5], "equal": nb4 == rb4 and nb5 == rb5}
            rep["max_rel"]["event_mismatch"] = rep["max_rel"].get("event_mismatch", 0) + (0 if row["events"]["equal"] else 1)
            rows.append(row)
        rep["runs"].append({"key": key, "id": scn.meta.scenario_id, "T_used": Ts, "excluded": excl,
                            "circuit_s": round(t_c, 1), "refcalc_s_total": round(t_ref, 3),
                            "times": {k: round(v, 2) for k, v in out["times"].items()}, "rows": rows,
                            "b5_events_at_max_T": rows[-1]["events"]["B5"]})
        print(tag, key, scn.meta.scenario_id, f"{t_c:.1f}s", len(Ts), "T",
              {k: f"{v:.1e}" for k, v in rep["max_rel"].items()}, flush=True)
    rep["pass"] = all(v <= TOL for k, v in rep["max_rel"].items() if k not in ("event_mismatch", "crashes") and not k.endswith("_nonzero")) \
        and rep["max_rel"].get("event_mismatch", 0) == 0 and rep["max_rel"].get("crashes", 0) == 0 and not any(k.endswith("_nonzero") for k in rep["max_rel"])
    save(f"v2_oracle_{tag}.json", rep)
    return rep


if __name__ == "__main__":
    tag, keys = sys.argv[1], sys.argv[2].split(",")
    iota = sys.argv[3] if len(sys.argv) > 3 else "full"
    r = run(tag, keys, iota)
    print("PASS" if r["pass"] else "FAIL", {k: f"{v:.2e}" for k, v in r["max_rel"].items()})
