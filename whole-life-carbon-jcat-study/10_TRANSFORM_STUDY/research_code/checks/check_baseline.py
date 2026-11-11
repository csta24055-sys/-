"""Smoke checks of the harness: frozen baseline, scenario sets, valid domain, metrics.

Run from ``research_code``:  python3 -B -m checks.check_baseline
"""
import json
import sys

sys.dont_write_bytecode = True

from tstudy import baseline, metrics, scenarios


def main() -> int:
    trees = baseline.assert_frozen()
    reg = baseline.load()
    assert len(reg.UNITS) == 70, len(reg.UNITS)
    bench = scenarios.benchmark()
    res = baseline.run_reference(bench[0])
    tot = baseline.totals(res)
    stages = baseline.stage_vector(res)
    again = metrics.propagate_stage_change(stages, bench[0].boundary.included_lifecycle_stages, {})
    for k in tot:
        assert abs(again[k] - tot[k]) <= 1e-9 * abs(tot[k]), (k, again[k], tot[k])
    design = scenarios.design_set(24, "S")
    evaluation = scenarios.evaluation_set(24, "S")
    assert not {s.meta.scenario_id for s in design} & {s.meta.scenario_id for s in evaluation}
    ok_d, out_d = scenarios.usable(design)
    edge = [s for _, s in scenarios.edge_set()]
    ok_e, out_e = scenarios.usable(edge)
    st = metrics.ErrorStats("demo")
    for scn in ok_d[:5]:
        r = baseline.run_reference(scn, ["SUM-03"])
        st.add(r["SUM-03"]["value"] * 1.01, r["SUM-03"]["value"], scn.meta.scenario_id)
    s = st.summary()
    assert abs(s["mean_signed"] - 0.01) < 1e-12
    print(json.dumps({"frozen_trees": trees, "units": len(reg.UNITS),
                      "benchmark_S_totals": tot,
                      "design_usable": len(ok_d), "design_excluded": out_d,
                      "edge_usable": len(ok_e), "edge_excluded": out_e}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
