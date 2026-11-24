import json
import os
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RESULTS = os.path.join(ROOT, "results")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from engine.audit import energy_balance, residuals  # noqa: E402


def _default(o):
    if isinstance(o, Fraction):
        return f"{o.numerator}/{o.denominator}" if o.denominator != 1 else str(o.numerator)
    if isinstance(o, (set, frozenset)):
        return sorted(o)
    return str(o)


def save(name, obj):
    os.makedirs(RESULTS, exist_ok=True)
    path = os.path.join(RESULTS, name)
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, default=_default)
    return path


def audit_dump(tc, dump, exact=True, tol=1e-9):
    r = residuals(dump)
    eb = energy_balance(dump)
    if exact:
        tc.assertEqual(r["kcl_max"], 0, r["violations"])
        tc.assertEqual(r["law_max"], 0, r["violations"])
        tc.assertEqual(r["jump_kcl_max"], 0, r["violations"])
        tc.assertEqual(r["jump_tellegen_max"], 0, r["violations"])
        tc.assertEqual(r["jump_cap_energy_max"], 0, r["violations"])
        tc.assertEqual(eb["tellegen_total"], 0)
        tc.assertEqual(eb["storage_vs_meter_max"], 0)
    else:
        tc.assertLessEqual(float(r["kcl_max"]), tol, r["violations"])
        tc.assertLessEqual(float(r["law_max"]), tol, r["violations"])
        tc.assertLessEqual(float(r["jump_kcl_max"]), tol)
        tc.assertLessEqual(abs(float(eb["tellegen_total"])), tol)
        tc.assertLessEqual(float(eb["storage_vs_meter_max"]), tol)
    summary = {k: (float(v) if isinstance(v, Fraction) else v) for k, v in r.items() if k != "violations"}
    summary.update({k: float(v) for k, v in eb.items()})
    return summary
