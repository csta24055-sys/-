"""V1: own residual checker on every dumped solution + independent re-simulation of the
pilot (right, original) and CF3-full dumps from the dumped netlist only."""
import glob, json, os
from fractions import Fraction as F
from common import SNAP, save, fstr
from nlcheck import check
from vsim import VSim, readout_C, num

def main():
    out = {"residuals": {}, "resim": {}}
    for f in sorted(glob.glob(os.path.join(SNAP, "results", "*.json"))):
        o = json.load(open(f))
        d = o.get("dump") or o.get("dump_last") if isinstance(o, dict) else None
        if not d:
            continue
        r = check(d)
        out["residuals"][os.path.basename(f)] = {"exact": r["exact"], "counts": r["counts"],
            "max": {k: (fstr(v) if isinstance(v, F) else v) for k, v in r["max"].items()}, "violations": r["violations"]}
    for name, Ts, prio, Tend, labels in (("pilot_full_solution_right.json", [10, 20, 30, 40], 100, 40, None),
                                         ("pilot_full_solution_original.json", [10, 20, 30, 40], 0, 40, None),
                                         ("cf3_full_solution_original.json", [F(12), F(51, 2), F(30)], 0, 30, None)):
        d = json.load(open(os.path.join(SNAP, "results", name)))["dump"]
        s = VSim(d["netlist"]).run(Tend, [(T, prio, T) for T in Ts])
        state_diffs = sum(1 for sn, rd in zip(s.snaps, d["readouts"]) for k in rd["s"] if num(rd["s"][k]) != sn["u"][k])
        mine = [(fstr(t), n, v) for (t, k, n, v) in s.events if k == "cmp"]
        theirs = [(e["t"], e["name"], e["value"]) for e in d["events"] if e["type"] == "cmp"]
        only_m = [x for x in mine if x not in theirs]; only_t = [x for x in theirs if x not in mine]
        out["resim"][name] = {"C": [fstr(readout_C(s, sn)[0]) for sn in s.snaps], "readout_state_mismatches": state_diffs,
                              "cmp_events_verifier": len(mine), "cmp_events_engine": len(theirs),
                              "only_verifier": only_m[:6], "only_engine": only_t[:6],
                              "differences_only_in_tb.P": all(x[1] == "tb.P" for x in only_m + only_t)}
    save("residuals_and_resim.json", out)
    return out

if __name__ == "__main__":
    o = main()
    for k, v in o["residuals"].items():
        print(k, {a: b for a, b in v["max"].items() if b not in (0, "0", 0.0)}, v["counts"]["records"], v["counts"]["jumps"])
    for k, v in o["resim"].items():
        print(k, {a: b for a, b in v.items() if a not in ("only_verifier", "only_engine")})
