"""Python 実装の計算結果を TypeScript テスト用の参照値として出力する（言語間クロスチェック）"""
import json
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from aqros import analysis as A, models as M  # noqa: E402

out = {"bypass": [], "zone": [], "deposition": [], "stats": {}}
for n, s, law, b in [(5, "中", "fit", "0.3-0.5"), (10, "中", "quadratic_ext", "0.3-0.5"), (20, "強", "quadratic_ext", "1.0-2.0"), (8, "弱", "fit", "5.0-")]:
    for r in (0, 0.25, 0.5, 1.0):
        res = asdict(M.solve_bypass(r, n, s, size_bin=b, ep_law=law))
        res.pop("warnings")
        out["bypass"].append({"args": [r, n, s, b, law], "res": res})
zp = M.ZoneParams(volume=240, q_oa=120, eta_oa_filter=0.3, q_inf=20, penetration_inf=0.8, q_recirc=1200, bypass_ratio=0.3,
                  eta_ep=0.8, deposition=0.15, c_out=12, generation=3000, c0=40)
ts = M.zone_time_series(zp, 6, 0.05)
out["zone"].append({"params": asdict(zp), "steady": M.zone_steady_state(zp), "io": M.zone_io_ratio(zp), "t12": M.time_to_fraction(zp, 0.12),
                    "series_last": ts[-1][1], "series_10": ts[10][1]})
v, f = M.shase2021_network("強")
mz = M.multizone_simulate(v, f, hours=0.5, c_out=0.007, c0=0.01, sources={"LDK": 0.0144 * 3600}, source_hours=(0, 1020 / 3600),
                          beta=M.decay_rate_to_beta(0.0003), ep_edge=M.SHASE2021_EP_EDGE, eta_ep=0.9, record_every_s=300)
out["multizone"] = {"t_h": mz["t_h"], "series": mz["series"]}
out["deposition"] = [[d, M.deposition_coefficient(d)] for d in (0.3, 1, 5, 10, 30)]
rng = np.random.default_rng(1)
x = rng.uniform(1, 30, 200); y = 0.55 * x + rng.normal(0, 1, 200)
out["stats"]["xy"] = [x.tolist(), y.tolist()]
out["stats"]["origin"] = A.regression_through_origin(x, y)
out["stats"]["power"] = A.power_law_fit(x, np.abs(y) + 0.1)
out["stats"]["linear"] = A.linear_regression(x, y)
dst = ROOT / "frontend" / "src" / "core" / "python_reference.json"
dst.write_text(json.dumps(out, ensure_ascii=False))
print("wrote", dst)
