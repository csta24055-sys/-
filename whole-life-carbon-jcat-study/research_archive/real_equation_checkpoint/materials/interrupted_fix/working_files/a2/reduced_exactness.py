"""Acceptance b: reduced exactness run of the unified model against the reference (nothing is written to the study)."""
import json
import sys
import time

from bench import verify_unified as vu
from refcalc import registry

registry.load_all()
t0 = time.perf_counter()
ex = vu.exactness(60, 20)
sw = vu.sweep_check(16)
ex["period_sweep"] = sw
out = sys.argv[1]
json.dump(ex, open(out, "w"), ensure_ascii=False, indent=1)
worst = max(u["max_abs_rel_error"] for u in ex["units"].values())
print(f"exactness(60, 20): scenarios {ex['scenarios']}, all_exact {ex['all_exact']}, floor {ex['absolute_floor']}, "
      f"largest relative difference {worst:.3e}, largest_difference {ex['largest_difference']}")
print(f"  failures {len(ex['failures'])}, invalid periods refused {ex['invalid_periods_refused_by_both']}, "
      f"baseline reuse {ex['baseline_reuse_checked']}, units without output in totals mode {ex['units_without_output_in_totals_mode']}")
print(f"sweep_check(16): scenarios {sw['scenarios']} (with baseline {sw['scenarios_with_baseline']}), units {sw['n_units']}, "
      f"values {sw['values_compared']}, largest {sw['max_abs_rel_error']:.3e} at {sw['largest_difference']}, all_exact {sw['all_exact']}")
print(f"elapsed {time.perf_counter() - t0:.0f}s")
