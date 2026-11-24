"""Mutation checks: deliberately broken variants of the composed model must DISAGREE with the oracles.
M1 set rule without supersession (P1 substitute); M2 'orig' without moving external events to tau/(1-eps);
M3 beta = iota_B2 ignored (EV9 without B2); M4 refrigerant automaton without late reset (EV9).
Run: PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 python3 -B code/mutation_check.py
"""
import sys
from fractions import Fraction as F

import int_common as IC
import phi_hybrid as PH
import psi_compose as PS


def main():
    OD = IC.route_d_oracle()
    out = {}
    sp = PH.pilot("P1", "substitute")
    sp.ext[0].supersedes = frozenset()
    g, o = PH.Hybrid(sp, "right").G(20), OD.G("P1", 20, "right", "substitute")
    out["M1_no_supersession_P1sub_G20"] = {"mutant": str(g), "oracle": str(o), "detected": g != o}

    class H2(PH.Hybrid):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self.ext = [(e.time, e) for _, e in self.ext]
    t = F("20.00000001")
    g, o = H2(PH.pilot("P1", "additional"), "orig").G(t), OD.G("P1", t, "orig", "additional")
    out["M2_orig_external_unslowed_G(20.00000001)"] = {"mutant": str(g), "oracle": str(o), "detected": g != o}

    scn = IC.psi_scenario("EV9-noB2")
    pc = PS.PsiComposed(scn)
    pc.rows = [(u, s, sg, "1") for u, s, sg, b in pc.rows]
    e = IC.rel(pc.sweep([30.0])[30.0]["total"], IC.refcalc_at(scn, 30.0)["SUM-03"]["value"])
    out["M3_beta_ignored_EV9noB2_T30_rel_err"] = {"rel_err": e, "detected": e > 1e-9}

    B = IC.route_b_grammar()
    scn = IC.psi_scenario("EV9")
    pc = PS.PsiComposed(scn)
    orig = B.RefrigerantCircuit

    class RC(orig):
        def __init__(self, scn, H, late_reset=True):
            super().__init__(scn, H, late_reset=False)
    B.RefrigerantCircuit = RC
    try:
        worst = max(IC.rel(pc.sweep([T])[T]["total"], IC.refcalc_at(scn, T)["SUM-03"]["value"])
                    for T in (5.3, 12.25, 29.5, 47.9))
    finally:
        B.RefrigerantCircuit = orig
    out["M4_no_late_reset_EV9_worst_rel_err_SUM03"] = {"rel_err": worst, "detected": worst > 1e-9}
    out["all_detected"] = all(v["detected"] for v in out.values())
    out["meta"] = {**IC.provenance(), "pycache_after": IC.pycache_dirs()}
    IC.dump("mutation_check.json", out)
    print({k: v for k, v in out.items() if k != "meta"})
    return 0 if out["all_detected"] and not out["meta"]["pycache_after"] else 1


if __name__ == "__main__":
    sys.exit(main())
