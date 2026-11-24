"""V3: the verifier's stage-B mutant set re-run on snapshot 96df403 (crossbar v2), with anchors
re-targeted to the v2 code path where the V2 anchors no longer exist or only hit the v1 path,
plus two mutants specific to the reduced crossbar. Judges as in v2_mutate: the builder's unit
suite (now with test_v2_fixes) and the verifier's oracle harness.
Usage: MUT_TAG=<tag> python3 -B v3_mutate.py name[,name...] | all
"""
from __future__ import annotations

import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v2_mutate as m  # noqa: E402
from common import save  # noqa: E402

AB = "adapter_building.py"
NEW = {
    # re-anchored to the v2 (LazyAmpNet) path
    "B01_conversion_skipped": (AB, '        if conv is None:\n            return rail\n        self.L.note("W2", "derived rail key")\n        return VSig(',
                               '        if conv is None or True:\n            return rail\n        self.L.note("W2", "derived rail key")\n        return VSig('),
    "B02_wrong_rail_transport_delivery": (AB, 'a4 = q_ord_chain(A, A.derived_rail(*hit), row, q, w, "transport", root_form)',
                                          'a4 = q_ord_chain(A, rail if rail is not None else A.derived_rail(*hit), row, q, w, "transport", root_form)'),
    "B09_mdac_msb_weight": (AB, 'wb = 2 ** b + (1 if (b == 7 and "mdac_msb_plus1" in B.mut) else 0)', 'wb = 2 ** b + (1 if b == 7 else 0)'),
    "B10_epd_validity_strict": (AB, "else (rec.valid_until >= scn.project.assessment_date):", "else (rec.valid_until > scn.project.assessment_date):"),
    # new, crossbar v2 specific
    "X1_passive_branch_drops_scale": (AB, "G = last[2] * Gu if last[0] == \"conv\" else last[2] * (last[4] * Gu)",
                                      "G = last[2] * Gu if last[0] == \"conv\" else last[2] * Gu"),
    "X2_design_root_ignores_waste": (AB, 'root = (("rail", "unit", None), ("q", ("qd", id(q), id(w)), q, w, Fraction(1)))',
                                     'root = (("rail", "unit", None), ("q", ("qd", id(q), id(w)), q, None, Fraction(1)))'),
}
m.MUT.update(NEW)


def main():
    names = sys.argv[1].split(",") if sys.argv[1:] and sys.argv[1] != "all" else ["BASELINE"] + list(m.MUT)
    out = {}
    for nm in names:
        out[nm] = m.run_one(nm)
        b, v = out[nm].get("builder_suite", {}), out[nm].get("verifier_oracle", {})
        print(nm, out[nm].get("applied"), "builder:", b.get("result"), "| verifier caught:", v.get("caught"),
              {k: f"{x:.1e}" for k, x in (v.get("max") or {}).items() if isinstance(x, (int, float)) and x > 1e-9},
              (v.get("error") or "")[:200], flush=True)
    save(f"v3_mutations_{os.environ.get('MUT_TAG', 'all')}.json", out)


if __name__ == "__main__":
    main()
