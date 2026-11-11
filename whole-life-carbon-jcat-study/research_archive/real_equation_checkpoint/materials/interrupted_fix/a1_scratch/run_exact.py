"""Reduced exactness run (imports the functions, writes only under the scratch folder)."""
import json, sys, time
sys.dont_write_bytecode = True
from bench import verify_unified as vu
from refcalc import registry
registry.load_all()
n_pop = int(sys.argv[1]) if len(sys.argv) > 1 else 60
n_dirty = int(sys.argv[2]) if len(sys.argv) > 2 else 20
n_sweep = int(sys.argv[3]) if len(sys.argv) > 3 else 16
out = sys.argv[4] if len(sys.argv) > 4 else None
t0 = time.time()
ex = vu.exactness(n_pop, n_dirty)
print(f"exactness({n_pop}, {n_dirty}): scenarios {ex['scenarios']}, all_exact {ex['all_exact']}, floor {ex['absolute_floor']}, "
      f"largest {ex['largest_difference']}, incomplete totals {ex['scenarios_with_incomplete_total']}, "
      f"invalid periods refused {ex['invalid_periods_refused_by_both']}, baseline reuse {ex['baseline_reuse_checked']}, "
      f"empty in totals mode {ex['units_without_output_in_totals_mode']}, {time.time() - t0:.0f}s")
for g, v in ex["by_group"].items():
    print("   ", g, v)
for f in ex["failures"][:40]:
    print("  FAIL", json.dumps(f, ensure_ascii=False, default=str)[:600])
t0 = time.time()
sw = vu.sweep_check(n_sweep)
print(f"sweep_check({n_sweep}): scenarios {sw['scenarios']} (with baseline {sw['scenarios_with_baseline']}), units {sw['n_units']}, "
      f"values {sw['values_compared']}, statuses {sw['sum_08_status_counts']}, worst {sw['max_abs_rel_error']:.3e} at {sw['largest_difference']}, "
      f"all_exact {sw['all_exact']}, no output in totals mode {sw['units_without_output_in_totals_mode']}, {time.time() - t0:.0f}s")
for f in sw["failures"][:20]:
    print("  SWEEP FAIL", json.dumps(f, ensure_ascii=False, default=str)[:400])
if out:
    ex["period_sweep"] = sw
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(ex, fh, ensure_ascii=False, indent=1, default=str)
