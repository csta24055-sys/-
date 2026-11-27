"""(e) Connection table: direct emission units -> time shape -> stage -> final destination, and the tests that
decide whether five destinations (or five time shapes) can carry the totals without loss.

Usage: python3 -I tools/make_connection.py <results_dir> <out_dir>
Reads results_dir/direct_unit_time_shapes.json and shape_rows.json written by run_reconstruction.py.
"""
import collections
import csv
import json
import os
import sys

import numpy as np

STAGE_OF = {"A13-01": "A1-A3", "A13-03": "A1-A3", "A13-04": "A1-A3", "X-01": "A1-A3", "A4-01": "A4", "A4-02": "A4",
            "A5-04": "A5", "B1-02": "B1", "B1-03": "B1", "B1-04": "B1", "B2-01": "B2(+), B6(−[B2 を数える])",
            "B3-01": "B3", "B4-02": "B4", "B5-01": "B5", "B6-03": "B6", "B7-04": "B7", "C1-01": "C1", "C2-01": "C2",
            "C3-01": "C3", "X-14": "C3", "C4-01": "C4"}
DEST_OF = {"A1-A3": "D1", "A4": "D1", "A5": "D1", "B1": "D2", "B2": "D2", "B3": "D2", "B4": "D2", "B5": "D2",
           "B6": "D3", "B7": "D4", "C1": "D5", "C2": "D5", "C3": "D5", "C4": "D5"}
UPSTREAM_DIRECT = {"A13-04": "A13-01;A13-03（上乗せ率 r/(1−r) の比例）", "B1-03": "B1-02（状態 u）", "B1-04": "B1-02（状態 u）",
                   "B3-01": "A13-01;A13-03;X-01（修繕率 × 初期排出）", "B4-02": "A13-01;A13-03;A4-01;A4-02;C2-01;C3-01;C4-01;X-01;X-14（1 回あたり＝初期の製造・輸送・撤去）",
                   "B5-01": "A13-01;A13-03;A13-04;A4-01;A4-02;A5-04;C1-01;C2-01;C3-01;C4-01;X-01;X-14（改修割合 φ × 初期と解体の和）"}
AUX_UP = {"A13-01": "A13-02;A13-05;X-15", "A13-03": "A13-05;X-15", "A4-02": "A13-05", "A5-04": "A5-01;A5-02;A5-03",
          "B2-01": "B6-01（→B6-04;X-06）", "B3-01": "B4-01;B4-03", "B4-02": "A13-05;B4-01;B4-03", "B6-03": "B6-01;B6-02（→B6-04;X-06）",
          "B7-04": "B7-01;B7-02;B7-03"}


def main(res, out):
    shapes = json.load(open(os.path.join(res, "direct_unit_time_shapes.json"), encoding="utf-8"))
    rows = json.load(open(os.path.join(res, "shape_rows.json"), encoding="utf-8"))
    os.makedirs(out, exist_ok=True)
    table = []
    for u, st in STAGE_OF.items():
        c = shapes.get(u, {})
        kshape = collections.Counter()
        amp = set()
        for k, n in c.items():
            sh, src = k.split("|")
            kshape[sh] += n
            amp.add(src)
        first = st.split("(")[0].split(",")[0].strip()
        table.append(dict(unit=u, stage=st, destination=DEST_OF[first] + ("（B6 側は D3 に −）" if u == "B2-01" else ""),
                          time_shapes=";".join("%s=%d" % kv for kv in sorted(kshape.items())),
                          amplitude_source="/".join(sorted(amp)) or "—",
                          upstream_auxiliary=AUX_UP.get(u, "（入力のみ）"), upstream_direct=UPSTREAM_DIRECT.get(u, ""),
                          sign="+1" if u != "B2-01" else "+1(B2), −1(B6)"))
    with open(os.path.join(out, "direct_to_destination.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(table[0]))
        w.writeheader()
        w.writerows(table)
    # ---- tests -------------------------------------------------------------------------------------------------
    keys = sorted({k for r in rows for k in r["shapes"]})
    good = [r for r in rows if r["SUM01"] is not None and r["SUM02"] is not None and r["SUM03"] is not None]
    X = np.array([[r["shapes"].get(k, 0.0) for k in keys] for r in good])
    Dk = list(good[0]["dest"])
    XD = np.array([[r["dest"][k] for k in Dk] for r in good])
    out_t = {"pairs": len(good), "shape_keys": keys, "destination_keys": Dk}
    FIXED = {"SUM01": [1, 0, 0, 0, 0], "SUM02": [1, 1, 0, 0, 1], "SUM03": [1, 1, 1, 1, 1]}   # 0/1 over D1..D5
    for name in ("SUM01", "SUM02", "SUM03"):
        y = np.array([r[name] for r in good])
        scale = np.maximum(np.abs(y), 1.0)
        fixed = np.array(FIXED[name], dtype=float)
        rr = np.abs(XD @ fixed - y) / scale
        out_t["%s_from_destinations_fixed01" % name] = dict(coef=dict(zip(Dk, FIXED[name])), max_rel_residual=float(rr.max()),
                                                           exact=bool(rr.max() <= 1e-9))
        for lab, M in (("time_shapes", X), ("destinations", XD)):
            coef, *_ = np.linalg.lstsq(M / scale[:, None], y / scale, rcond=None)
            resid = (M @ coef - y) / scale
            out_t["%s_from_%s" % (name, lab)] = dict(coef=dict(zip(keys if lab == "time_shapes" else Dk, [round(float(c), 6) for c in coef])),
                                                    max_rel_residual=float(np.max(np.abs(resid))),
                                                    exact=bool(np.max(np.abs(resid)) < 1e-9))
    out_t["rank_time_shapes"] = int(np.linalg.matrix_rank(X))
    out_t["rank_destinations"] = int(np.linalg.matrix_rank(XD))
    out_t["note"] = ("SUM-0x is exactly a fixed 0/1 combination of the five destinations; it is NOT a fixed linear combination "
                     "of the time-shape totals when max_rel_residual >> 0. Stage shares (SUM-07) need the 14 stages: "
                     "the 14 -> 5 map has rank 5 and is not injective, so the five destinations lose the stage detail.")
    json.dump(out_t, open(os.path.join(out, "destination_tests.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps(out_t, ensure_ascii=False, indent=1))
    for r in table:
        print(r["unit"], r["destination"], r["time_shapes"], r["amplitude_source"])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
