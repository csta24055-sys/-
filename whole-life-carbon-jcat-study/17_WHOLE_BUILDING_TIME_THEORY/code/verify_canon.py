"""Stage 1 verification: the canonical whole-building equation C(T) (exact evaluation of the kernel terms and of the
minimal knot form) against (a) the unified system of chapter 11 and (b) the frozen reference calculation (refcalc),
for every scenario x study period of the named verification sets of chapter 11 (1,293 pairs), whole-life total
(SUM-03) and every stage value (X-02 by_stage).

Usage (from this folder): python3 -B verify_canon.py <out.json> [set names...]"""
import json
import math
import os
import sys
import time

sys.dont_write_bytecode = True
import canon                                            # noqa: E402  (sets the import path)
from checks import sets_unified                         # noqa: E402
from tstudy import baseline, scenarios                  # noqa: E402

REL = 1e-9          # the comparison of chapter 11 (numbers relative 1e-9; a reference of exactly 0 must be 0)


def same(a, b, rel=REL):
    if b == 0.0:
        return a == 0.0 or abs(a) <= 1e-300
    return abs(a - b) <= rel * abs(b)


def reldiff(a, b):
    return 0.0 if a == b else abs(a - b) / max(abs(a), abs(b))


def main(outp, names):
    baseline.assert_frozen()
    baseline.load()
    from synth import population
    sets = sets_unified.build(names or sets_unified.ALL_SETS)
    res = {}
    t0 = time.time()
    for name, cases in sets.items():
        r = dict(n_pairs=0, n_excluded=0, n_failed=0, total_vs_ref_bad=0, total_vs_sys_bad=0, knot_vs_terms_bad=0,
                 stage_vs_ref_bad=0, n_stage=0, n_unit=0, unit_vs_ref_bad=0, max_rel_unit=0.0,
                 n_jumpform=0, jumpform_vs_ref_bad=0, max_rel_jumpform=0.0, max_rel_ref=0.0, max_rel_sys=0.0, max_rel_stage=0.0, examples=[], knots=[])
        check_domain = name not in sets_unified.OUTSIDE_DOMAIN
        for label, scn, periods in cases:
            try:
                sysm = canon.make_system(scn, population.BASELINES)
                can = canon.build(sysm, T_probe=float(periods[0]) if periods else None)
            except Exception as ex:
                r["n_failed"] += len(periods)
                r["examples"].append(("PREPARE", label, type(ex).__name__, str(ex)[:160]))
                continue
            A0, ev, la = can.knot_form()
            r["knots"].append(dict(label=label, H=can.H, n_terms=len(can.terms), n_event_knots=len(ev), n_lattice_knots=len(la)))
            for T in periods:
                cur = scenarios.with_period(scn, T)
                if check_domain and scenarios.valid_domain(cur):
                    r["n_excluded"] += 1
                    continue
                try:
                    ref = baseline.run_reference(cur)
                except Exception as ex:
                    r["n_excluded"] += 1
                    continue
                try:
                    got = sysm.at(T)
                except Exception as ex:
                    r["n_failed"] += 1
                    r["examples"].append(("SYSTEM", label, T, type(ex).__name__, str(ex)[:120]))
                    continue
                r["n_pairs"] += 1
                c = can.value(T)
                ck = can.knot_value(T)
                want, have = ref["SUM-03"]["value"], got["SUM-03"]["value"]
                if not same(c, want):
                    r["total_vs_ref_bad"] += 1
                    r["examples"].append(("C vs ref", label, T, c, want))
                if not same(c, have, 1e-12):
                    r["total_vs_sys_bad"] += 1
                    r["examples"].append(("C vs system", label, T, c, have))
                if not same(ck, c, 1e-12):
                    r["knot_vs_terms_bad"] += 1
                    r["examples"].append(("knot form vs terms", label, T, ck, c))
                r["max_rel_ref"] = max(r["max_rel_ref"], reldiff(c, want))
                r["max_rel_sys"] = max(r["max_rel_sys"], reldiff(c, have))
                for st, w in ref["X-02"]["by_stage"].items():
                    r["n_stage"] += 1
                    cs = can.value(T, st)
                    if not same(cs, w):
                        r["stage_vs_ref_bad"] += 1
                        if len(r["examples"]) < 40:
                            r["examples"].append(("stage vs ref", label, T, st, cs, w))
                    r["max_rel_stage"] = max(r["max_rel_stage"], reldiff(cs, w))
                for u in can.unit_terms:
                    cu = can.unit_value(T, u)
                    if u == "B1-04J":                    # the jump form of B1-04: comparison only (D-09 cancellation)
                        w = ref["B1-04"]["value"]
                        r["n_jumpform"] += 1
                        if not same(cu, w):
                            r["jumpform_vs_ref_bad"] += 1
                            r["examples"].append(("B1-04 jump form vs ref (not used)", label, T, cu, w))
                        r["max_rel_jumpform"] = max(r["max_rel_jumpform"], reldiff(cu, w))
                        continue
                    w = ref[u]["value"]
                    r["n_unit"] += 1
                    if not same(cu, w):
                        r["unit_vs_ref_bad"] += 1
                        if len(r["examples"]) < 40:
                            r["examples"].append(("unit vs ref", label, T, u, cu, w))
                    r["max_rel_unit"] = max(r["max_rel_unit"], reldiff(cu, w))
        r["examples"] = r["examples"][:40]
        r["knots"] = r["knots"][:400]
        res[name] = r
        print("[%-16s] pairs %4d excl %3d failed %d | C~ref bad %d (max rel %.1e) | C~system bad %d (max %.1e) | knot~terms bad %d | "
              "stages %d bad %d (max %.1e) | units %d bad %d (max %.1e) | %.0f s" % (name, r["n_pairs"], r["n_excluded"], r["n_failed"], r["total_vs_ref_bad"], r["max_rel_ref"],
                                                       r["total_vs_sys_bad"], r["max_rel_sys"], r["knot_vs_terms_bad"], r["n_stage"],
                                                       r["stage_vs_ref_bad"], r["max_rel_stage"], r["n_unit"], r["unit_vs_ref_bad"], r["max_rel_unit"], time.time() - t0), flush=True)
        json.dump(res, open(outp, "w"), indent=1)
    tot = {k: sum(v[k] for v in res.values()) for k in ("n_pairs", "n_excluded", "n_failed", "total_vs_ref_bad", "total_vs_sys_bad",
                                                       "knot_vs_terms_bad", "n_stage", "stage_vs_ref_bad", "n_unit", "unit_vs_ref_bad", "n_jumpform", "jumpform_vs_ref_bad")}
    print("TOTAL", tot)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
