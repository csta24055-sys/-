"""Stage 1, finding of the independent review: integer-time refrigerant changes and the sliver (K, sw(K)).

A change at an integer time K (explicit change_years are integers) belongs to the year cell K-1 and counts only for
T >= sw(K) ~ K (1 + 1e-9). The interval form of B1-04, and the stock amplitudes u_K of B1-02 (both computed by the
masked sum-product of chapter 11 assuming the change of cell K-1 has counted for every T > K), reset at T > K. For T in
(K, sw(K)) the canonical equation (and the unified system of chapter 11, which uses the same amplitudes) can
therefore differ from the reference. scenarios.valid_domain does not exclude such T for EXPLICIT lists (it checks only
multiples of periods). This script measures the difference at T = K (1 + 3e-10) (inside the sliver) and, as a
control, at T = K (1 + 3e-8) (outside it); also at the first float above K and at K (1 + 5e-11), where T is closer to
the whole year than the lower edge 1e-10 of the excluded band.

Usage (from this folder): python3 -B sliver_test.py <out.json>
"""
import json
import math
import sys

sys.dont_write_bytecode = True
import canon                                   # noqa: E402
import timechar as tc                          # noqa: E402
from checks import sets_unified                # noqa: E402
from tstudy import baseline, scenarios         # noqa: E402


def main(outp):
    baseline.assert_frozen()
    baseline.load()
    from synth import population
    out = []
    for name, label, scn in tc.scenario_entries(["dev_edge", "dev_design", "new_special"], 40):
        devs = [d for d in scn.refrigerants if d.change_years]
        if not devs:
            continue
        sysm = canon.make_system(scn, population.BASELINES)
        can = canon.build(sysm)
        Ks = sorted({int(y) for d in devs for y in d.change_years if 1 <= int(y) < can.H})[:3]
        for K in Ks:
            for rel in ("next", 5e-11, 3e-10, 3e-8):
                T = math.nextafter(float(K), math.inf) if rel == "next" else K * (1.0 + rel)
                cur = scenarios.with_period(scn, T)
                why = scenarios.valid_domain(cur)
                ref = baseline.run_reference(cur)
                got = sysm.at(T)
                row = dict(set=name, label=label, K=K, T=T, rel_offset=rel, in_valid_domain=not why,
                           inside_sliver=(T < tc.tswitch(float(K))))
                for u in ("B1-02", "B1-03", "B1-04", "SUM-03"):
                    w = ref[u]["value"]
                    c = float(tc.KF(can)(T)) if u == "SUM-03" else can.unit_value(T, u)
                    s = got[u]["value"]
                    row[u] = dict(reference=w, canonical=c, unified_system=s,
                                  rel_canon=abs(c - w) / max(abs(w), 1e-300), rel_system=abs(s - w) / max(abs(w), 1e-300))
                out.append(row)
                print(name, label[:30], K, rel if isinstance(rel, str) else "%.1e" % rel, "domain", row["in_valid_domain"], "sliver", row["inside_sliver"],
                      {u: "%.1e/%.1e" % (row[u]["rel_canon"], row[u]["rel_system"]) for u in ("B1-02", "B1-04", "SUM-03")}, flush=True)
        if len(out) >= 36:
            break
    json.dump(out, open(outp, "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main(sys.argv[1])
