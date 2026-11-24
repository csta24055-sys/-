"""S3e: full model (all blocks) on several buildings, iota subsets, schema signatures,
state/element counts versus size, and the six stage-B mutations. Oracle (frozen refcalc)
imported here only. Writes results/stageB_S3e.json and results/stageB_mutations.json."""
import copy
import json
import os
import sys
import time
from fractions import Fraction

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import compare_refcalc as cr  # noqa: E402  (asserts the frozen baseline)
from model_building import simulate_building  # noqa: E402

ROOT = cr.ROOT
STAGES = ("A1-A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "C1", "C2", "C3", "C4")


def signature(out):
    """Derived from the netlists themselves (V1-D4): element kinds + connection pattern."""
    from model import netlist_signature
    return netlist_signature(out["core"].nl), netlist_signature(out["A"].nl)


def dump_netlists(key, out):
    """Both netlists and the tap map, so that an outside simulator can re-run stage B:
    crossbar (static DC) -> tap values -> core (hybrid)."""
    taps = {name: {"crossbar_node": node, "sign": sg, "core_source": f"tap.{name}"} for name, (node, sg) in out["A"].exports.items()}
    with open(os.path.join(ROOT, "results", f"stageB_netlists_{key}.json"), "w") as f:
        json.dump({"crossbar": out["A"].nl.to_json(), "core": out["core"].nl.to_json(), "taps": taps,
                   "readout_caps": out["core"].readout_caps,
                   "by_T": {str(T): {"C": str(v["C"]), "stages": {k: str(x) for k, x in v["stages"].items()}}
                            for T, v in out["by_T"].items()}}, f)


def main(keys):
    rep = cr.run("S3e", keys)
    # iota subsets on benchmark S and on E0 (which has B5 events for T > 82)
    subsets = {"no_B2": [s for s in STAGES if s != "B2"],
               "no_B2_B6": [s for s in STAGES if s not in ("B2", "B6")],
               "no_B1_C4": [s for s in STAGES if s not in ("B1", "C4")],
               "A13_B4_C3": ["A1-A3", "B4", "C3"]}
    rep["iota_subsets"] = {}
    for name, iota in subsets.items():
        sub = cr.run("S3e", ["S", "E0"], iota=iota)
        rep["iota_subsets"][name] = {"max_rel": sub["max_rel"], "pass": sub["pass"], "rows": sub["rows"]}
        print("iota", name, sub["pass"], sub["max_rel"], flush=True)
    # schema signatures
    sigs = {}
    for key, scn in cr.scenario_set(keys):
        out = simulate_building(scn, [1, 33.3, 60], "original")
        sigs[key] = signature(out)
        if key in ("S", "E1"):
            dump_netlists(key, out)
    base = sigs[keys[0]]
    rep["signature"] = {"core_equal_all": all(v[0] == base[0] for v in sigs.values()),
                        "crossbar_celltypes_equal_all": all(v[1] == base[1] for v in sigs.values()),
                        "core_signature_sizes": {k: len(v[0]) for k, v in sigs.items()},
                        "per_building_core_diff": {k: sorted(map(str, v[0] ^ base[0]))[:40] for k, v in sigs.items()},
                        "per_building_crossbar_diff": {k: sorted(map(str, v[1] ^ base[1]))[:40] for k, v in sigs.items()}}
    rep["pass_all"] = rep["pass"] and all(v["pass"] for v in rep["iota_subsets"].values())
    with open(os.path.join(ROOT, "results", "stageB_S3e.json"), "w") as f:
        json.dump(rep, f, indent=1, default=str)
    print("S3e", "PASS" if rep["pass_all"] else "FAIL", rep["max_rel"], rep["signature"]["core_equal_all"], flush=True)


def mutations():
    bm = cr.scenarios.benchmark()
    ev = cr.scenarios.evaluation_set(10)
    S, E0, E2 = bm[0], ev[0], ev[2]
    gen = copy.deepcopy(S)                      # fictional variant: on-site generation above demand
    gen.operation.onsite_generation.kind = "CONSTANT"
    gen.operation.onsite_generation.base = 3 * max(gen.operation.electricity.table[:60])
    gen.operation.onsite_generation.slope = None
    gen.operation.onsite_generation.table = [gen.operation.onsite_generation.base] * len(gen.operation.onsite_generation.table)
    noB2 = copy.deepcopy(S)
    noB2.boundary.included_lifecycle_stages = [s for s in STAGES if s != "B2"]
    noC4 = copy.deepcopy(E0)
    noC4.boundary.included_lifecycle_stages = [s for s in STAGES if s not in ("C4", "A4")]
    cases = {
        "init_before_leak": (E2, [33.3, 59.9], "B1"),
        "refrigerant_rc_decay": (E2, [33.3, 59.9], "B1"),
        "rho_always_subtracted": (noB2, [33.3, 60], "B6"),
        "iota_upstream_b5": (noC4, [99.9], "B5"),
        "diode_after_integration": (gen, [33.3, 60], "B6"),
        "terminal_into_integrator": (S, [33.3, 60], "C3"),
    }
    out = {}
    for name, (scn, Ts, stage) in cases.items():
        ref = {T: cr.baseline.run_reference(cr.scenarios.with_period(scn, T))["X-02"]["by_stage"] for T in Ts}
        good = simulate_building(scn, Ts, "original")
        bad = simulate_building(scn, Ts, "original", mutations=(name,))
        rows = []
        for T in Ts:
            g = float(good["by_T"][Fraction(T)]["stages"].get(stage, 0))
            b = float(bad["by_T"][Fraction(T)]["stages"].get(stage, 0))
            r = ref[T][stage]
            rows.append({"T": T, "stage": stage, "refcalc": r, "unmutated": g, "mutated": b,
                         "unmutated_rel": cr.rel(g, r), "mutated_rel": cr.rel(b, r)})
        det = any(x["mutated_rel"] > cr.TOL for x in rows)
        ok = all(x["unmutated_rel"] <= cr.TOL for x in rows)
        out[name] = {"scenario": scn.meta.scenario_id, "rows": rows, "unmutated_passes": ok, "detected": det}
        print("mutation", name, "unmutated ok" if ok else "UNMUTATED FAILS", "detected" if det else "NOT DETECTED", flush=True)
    with open(os.path.join(ROOT, "results", "stageB_mutations.json"), "w") as f:
        json.dump(out, f, indent=1, default=str)


if __name__ == "__main__":
    what = sys.argv[1]
    if what == "full":
        main(sys.argv[2].split(",") if len(sys.argv) > 2 else ["S", "M", "E0", "E1", "E2"])
    else:
        mutations()
