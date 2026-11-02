"""2022年度 多室シミュレーション（粉塵の行方の割合）を本アプリの多室モデルで再現する。

入力: private_data/raw/S-2022-03_deposition.txt（Box『01 沈着計算＆まとめ.xlsx』のテキスト抽出, 非コミット）の「まとめ」表、
      および Box『00 シミュレーション入力値.xlsx』の入力値（風量 m³/h・室別沈着係数 β 1/s）。入力値は数値パラメータのみを本スクリプトに転記。
条件: 条件2=弱/EP OFF, 3=弱/ON, 4=強/OFF, 5=強/ON。LDK で 10 秒間発生（本論: 実験BOXの発生量の1/10を個/sで入力）、30 分間、EP 集塵効率 90%（本論）。
出力: knowledge/validation_fate_2022.json（割合の比較のみ）

使い方: .venv/bin/python scripts/validate_fate_2022.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from aqros import models as M  # noqa: E402

OUT = M.OUTDOOR
SIZES = ["5-10", "10-20", "20-30", "30-45"]
# 室別沈着係数 β [1/s]（2022年度入力値, 重力沈降の理論値）
BETA = {
    "空調室": [0.0009711053, 0.003842285, 0.0114734284, 0.0257604773],
    "建築ダクト": [0.0007833583, 0.0030994433, 0.0092552323, 0.0207801183],
    "階間": [0.0058751873, 0.0232458245, 0.069414242, 0.1558508875],
    "床下": [0.0058751873, 0.0232458245, 0.069414242, 0.1558508875],
    "吹抜": [0.0008333599, 0.0032972801, 0.0098459918, 0.0221065089],
    "洋室(中)": [0.0009592143, 0.0037952367, 0.0113329375, 0.0254450429],
    "クローゼット": [0.0009592143, 0.0037952367, 0.0113329375, 0.0254450429],
    "洋室(大)": [0.0009592143, 0.0037952367, 0.0113329375, 0.0254450429],
    "2階廊下・レターン": [0.0009711053, 0.003842285, 0.0114734284, 0.0257604773],
    "洗面所": [0.00094003, 0.0037193319, 0.0111062787, 0.024936142],
    "LDK": [0.00094003, 0.0037193319, 0.0111062787, 0.024936142],
    "1階廊下・玄関": [0.00094003, 0.0037193319, 0.0111062787, 0.024936142],
    "小屋裏": [0.0, 0.0, 0.0, 0.0],
}
# 風量 [m³/h]（弱, 強）— 2022年度入力値
FLOWS = [
    (OUT, "空調室", 20, 20), ("空調室", OUT, 20, 20), ("空調室", "建築ダクト", 923, 1408),
    ("建築ダクト", "階間", 409, 656), ("建築ダクト", "床下", 515, 752),
    ("階間", "洋室(中)", 163, 237), ("階間", "クローゼット", 41, 66), ("階間", "洋室(大)", 148, 264), ("階間", "2階廊下・レターン", 57, 90),
    ("床下", "洗面所", 56, 78), ("床下", "LDK", 397, 590), ("床下", "1階廊下・玄関", 61, 83),
    ("吹抜", "2階廊下・レターン", 397, 590), ("洋室(中)", "2階廊下・レターン", 163, 237), ("クローゼット", "洋室(大)", 41, 66),
    ("洋室(大)", "2階廊下・レターン", 189, 330), ("2階廊下・レターン", "空調室", 923, 1408),
    ("洗面所", "1階廊下・玄関", 56, 78), ("LDK", "吹抜", 397, 590), ("1階廊下・玄関", "2階廊下・レターン", 117, 161),
]
CONDS = {"条件2": ("弱", False), "条件3": ("弱", True), "条件4": ("強", False), "条件5": ("強", True)}
NONLIVING = ["空調室", "建築ダクト", "階間", "床下"]
OTHER_ROOMS = ["1階廊下・玄関", "洗面所", "クローゼット", "洋室(大)"]
# 2022年度「まとめ」表（右側の整合版, %）【当事者の計算結果】
REPORTED = {
    "5-10": {"LDK": [53.9, 51.1, 46.4, 41.3], "非居室": [22.6, 2.5, 31.6, 2.9], "集塵機": [0.0, 32.0, 0.0, 47.3], "残留": [12.7, 7.2, 8.1, 1.9]},
    "10-20": {"LDK": [84.3, 83.9, 77.4, 76.3], "非居室": [6.5, 1.0, 12.6, 1.7], "集塵機": [0.0, 6.5, 0.0, 13.6], "残留": [3.1, 3.1, 1.8, 1.8]},
    "20-30": {"LDK": [91.4, 91.4, 88.9, 88.8], "非居室": [0.8, 0.2, 2.5, 0.5], "集塵機": [0.0, 0.7, 0.0, 2.2], "残留": [5.6, 5.6, 5.3, 5.3]},
    "30-45": {"LDK": [98.0, 98.0, 97.2, 97.2], "非居室": [0.2, 0.1, 0.4, 0.1], "集塵機": [0.0, 0.2, 0.3, 0.3], "残留": [1.2, 1.2, 0.9, 1.2]},
}


def fate(setting: str, ep: bool, size_i: int, eta: float = 0.9, dt: float = 1.0, minutes: float = 30.0) -> dict:
    """30分後の粉塵の行方 [%]（発生総量に対する割合）"""
    vol = dict(M.SHASE2021_VOLUMES)
    k = 2 if setting == "弱" else 3
    flows = [(f, t, row[k]) for row in FLOWS for f, t in [row[:2]]]
    beta_h = {z: BETA[z][size_i] * 3600 for z in vol}
    g_total = 1.0
    res = M.multizone_simulate(vol, flows, hours=minutes / 60, sources={"LDK": g_total / (10 / 3600)},
                               source_hours=(0, 10 / 3600), beta=beta_h, ep_edge=M.SHASE2021_EP_EDGE if ep else None,
                               eta_ep=eta, dt_s=dt, record_every_s=dt)
    t = res["t_h"]
    dep = {z: 0.0 for z in vol}
    ep_cap = vent = 0.0
    for i in range(1, len(t)):
        h = t[i] - t[i - 1]
        for z in vol:
            dep[z] += beta_h[z] * vol[z] * res["series"][z][i - 1] * h
        if ep:
            ep_cap += eta * 923 * 0 + eta * dict(((f, tt), q) for f, tt, q in flows)[M.SHASE2021_EP_EDGE] * res["series"]["空調室"][i - 1] * h
        vent += 20 * res["series"]["空調室"][i - 1] * h
    remain = sum(vol[z] * res["series"][z][-1] for z in vol)
    pct = lambda x: 100 * x / g_total  # noqa: E731
    return {"LDK": pct(dep["LDK"]), "吹抜": pct(dep["吹抜"]), "LDK+吹抜": pct(dep["LDK"] + dep["吹抜"]), "レターン": pct(dep["2階廊下・レターン"]), "洋室中": pct(dep["洋室(中)"]),
            "他居室": pct(sum(dep[z] for z in OTHER_ROOMS)), "非居室": pct(sum(dep[z] for z in NONLIVING)),
            "集塵機": pct(ep_cap), "換気": pct(vent), "残留": pct(remain),
            "収支": pct(sum(dep.values()) + ep_cap + vent + remain)}


def main():
    out = {"note": "2022年度の多室シミュレーション（粉塵の行方, 30分）を本アプリの多室モデルで再計算し、同年度の『まとめ』表と比較【計算結果】。入力は同年度の風量・沈着係数・EP効率90%・LDK 10秒発生。",
           "source_data": "Box 1516298663163（01 沈着計算＆まとめ）, 1516296688535（00 シミュレーション入力値）", "rows": []}
    worst = 0.0
    for si, s in enumerate(SIZES):
        for ci, (cn, (st, ep)) in enumerate(CONDS.items()):
            f = fate(st, ep, si)
            rep = {k: v[ci] for k, v in REPORTED[s].items()}
            # 『まとめ』右表の LDK は吹抜への沈着を含む（左表 LDK 45.2 等は吹抜を含まず、本モデルの LDK 単独と一致）
            key = {"LDK": "LDK+吹抜", "非居室": "非居室", "集塵機": "集塵機", "残留": "残留"}
            diff = {k: f[key[k]] - rep[k] for k in rep}
            worst = max(worst, max(abs(v) for k, v in diff.items() if k != "残留"))
            out["rows"].append({"size_um": s, "cond": cn, "fan": st, "ep": ep, "model": f, "reported": rep, "diff_pt": diff})
            print(s, cn, {k: (round(f[key[k]], 1), rep[k]) for k in rep}, "収支%.1f" % f["収支"])
    out["max_abs_diff_pt_excl_residual"] = worst
    out["left_table_LDK_only_5_10"] = {"reported": [45.2, 42.8, 38.5, 34.2], "note": "『まとめ』左表のLDK（吹抜を含まない版）"}
    (ROOT / "knowledge" / "validation_fate_2022.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("max |diff| (残留除く) =", round(worst, 2), "pt")


if __name__ == "__main__":
    main()
