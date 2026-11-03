"""2022年度 多室シミュレーション（01 沈着計算＆まとめ.xlsx の全20シート）の粒子収支検証。

各シート（条件2〜5 × 粒径4区分の10秒刻み16シート、30–45 μm の1秒刻み4シート）について、
発生量M、初回ステップで室内に入った量、30分間の累積沈着（室別）・集塵機・換気、30分後の浮遊残存を集計し、
『まとめ』表との一致と収支の残差を検証する。

入力: private_data/raw/S-2022-03_deposition.txt（非コミット）
出力: verification/Y2022_simulation/results.json, results.md, fig_residual.png（集計値のみ）
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "private_data" / "raw" / "S-2022-03_deposition.txt"
OUT = Path(__file__).resolve().parent
ROOMS_C = ["外部", "空調室", "建築ダクト", "階間", "床下", "吹抜", "洋室中", "クローゼット", "洋室大", "レターン", "洗面所", "LDK", "玄関", "小屋裏"]
ROOMS_D = ["空調室", "建築ダクト", "階間", "床下", "吹抜", "洋室中", "クローゼット", "洋室大", "レターン", "洗面所", "LDK", "玄関", "集塵機", "換気"]
VOL = {"空調室": 3.97, "建築ダクト": 2.76, "階間": 25.51, "床下": 30.61, "吹抜": 23.85, "洋室中": 23.85, "クローゼット": 15.9,
       "洋室大": 39.75, "レターン": 40.35, "洗面所": 12.17, "LDK": 91.3, "玄関": 20.97, "小屋裏": 75.05}
SIZES = {"5-10": 0, "10-20": 1, "20-30": 2, "30-45": 3}
BETA_LDK = [0.00094003, 0.0037193319, 0.0111062787, 0.024936142]
COND = {"2": "弱・EP OFF", "3": "弱・EP ON", "4": "強・EP OFF", "5": "強・EP ON"}
NONLIVING = ["空調室", "建築ダクト", "階間", "床下"]
OTHER = ["玄関", "洗面所", "クローゼット", "洋室大"]
# 『まとめ』右表（%）: LDK, 非居室, 集塵機, その他
REPORTED = {"5-10": [[53.9, 22.6, 0.0, 12.7], [51.1, 2.5, 32.0, 7.2], [46.4, 31.6, 0.0, 8.1], [41.3, 2.9, 47.3, 1.9]],
            "10-20": [[84.3, 6.5, 0.0, 3.1], [83.9, 1.0, 6.5, 3.1], [77.4, 12.6, 0.0, 1.8], [76.3, 1.7, 13.6, 1.8]],
            "20-30": [[91.4, 0.8, 0.0, 5.6], [91.4, 0.2, 0.7, 5.6], [88.9, 2.5, 0.0, 5.3], [88.8, 0.5, 2.2, 5.3]],
            "30-45": [[98.0, 0.2, 0.0, 1.2], [98.0, 0.1, 0.2, 1.2], [97.2, 0.4, 0.3, 0.9], [97.2, 0.1, 0.3, 1.2]]}


def num(x):
    try:
        return float(x.replace(",", ""))
    except ValueError:
        return None


def sheets():
    L = RAW.read_text(encoding="utf-8").split("\n")
    starts = [(i, l.strip()) for i, l in enumerate(L) if re.match(r"^\d-\d+-\d+", l)]
    for k, (i, name) in enumerate(starts):
        j = starts[k + 1][0] if k + 1 < len(starts) else len(L)
        yield name, [l.split("\t") for l in L[i + 1:j]]


def analyze(name, rows):
    cond, lo, hi = re.match(r"^(\d)-(\d+)-(\d+)", name).groups()
    size = f"{lo}-{hi}"
    dt1 = "秒" in name
    d0 = 17 if dt1 else 18  # 1秒刻みシートは濃度列と沈着列の間に空列がない
    data = [f for f in rows if len(f) > d0 + 13 and num(f[3]) is not None and num(f[14]) is not None and num(f[d0 + 10]) is not None]
    dt = 1 if dt1 else 10
    last = data[-1]
    conc = {r: num(last[3 + i]) or 0.0 for i, r in enumerate(ROOMS_C)}
    dep = {r: num(last[d0 + i]) or 0.0 for i, r in enumerate(ROOMS_D)}
    singles = []
    for f in rows:
        cells = [c for c in f if c.strip()]
        if len(cells) == 1 and num(cells[0]) is not None and num(cells[0]) > 1000:
            singles.append(num(cells[0]))
    M = singles[0] if singles else None
    c1 = num(data[1][3 + ROOMS_C.index("LDK")])
    injected = c1 * VOL["LDK"]
    airborne = sum(conc[r] * VOL.get(r, 0) for r in ROOMS_C if r not in ("外部",))
    ep_on = cond in ("3", "5")
    ep_col_raw = dep["集塵機"]
    if not ep_on:
        dep["集塵機"] = 0.0  # EP OFF 条件ではシートの集塵機欄は数式上の値（濃度計算には効いていない）→ 収支から除外
    accounted = sum(dep.values())
    b = BETA_LDK[SIZES[size]]
    pct = lambda x: 100 * x / M  # noqa: E731
    res = {"sheet": name, "cond": cond, "cond_label": COND[cond], "size_um": size, "dt_s": dt, "M": M,
           "injected_pct": pct(injected), "pred_injected_pct_exp_beta": 100 * (1 - math.exp(-b * dt)) / (b * dt),
           "LDK": pct(dep["LDK"]), "吹抜": pct(dep["吹抜"]), "LDK+吹抜": pct(dep["LDK"] + dep["吹抜"]),
           "レターン": pct(dep["レターン"]), "洋室中": pct(dep["洋室中"]), "他居室": pct(sum(dep[r] for r in OTHER)),
           "非居室": pct(sum(dep[r] for r in NONLIVING)), "集塵機": pct(dep["集塵機"]), "換気": pct(dep["換気"]),
           "accounted_pct": pct(accounted), "airborne_end_pct": pct(airborne), "residual_pct": 100 - pct(accounted) - pct(airborne),
           "beta_ldk_dt": b * dt, "ep_on": ep_on, "ep_column_raw_pct_when_off": None if ep_on else pct(ep_col_raw),
           "first_step_loss_pct": 100 - pct(injected), "n_rows": len(data)}
    if not dt1:
        rep = REPORTED[size][int(cond) - 2]
        res["reported"] = {"LDK": rep[0], "非居室": rep[1], "集塵機": rep[2], "その他": rep[3]}
    return res


def main():
    rs = [analyze(n, rows) for n, rows in sheets()]
    (OUT / "results.json").write_text(json.dumps(rs, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = ["| シート | 条件 | 粒径μm | Δt s | 初回投入% (予測) | LDK+吹抜% (表) | 非居室% (表) | 集塵機% (表) | 浮遊残存% | 未計上% (表の『その他』) | β·Δt |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rs:
        rep = r.get("reported", {})
        f = lambda k, rk: f"{r[k]:.1f}" + (f" ({rep[rk]})" if rk in rep else "")  # noqa: E731
        lines.append(f"| {r['sheet']} | {r['cond_label']} | {r['size_um']} | {r['dt_s']} | {r['injected_pct']:.2f} ({r['pred_injected_pct_exp_beta']:.2f}) | {f('LDK+吹抜','LDK')} | {f('非居室','非居室')} | {f('集塵機','集塵機')} | {r['airborne_end_pct']:.2f} | {r['residual_pct']:.2f}" + (f" ({rep['その他']})" if rep else "") + f" | {r['beta_ldk_dt']:.3f} |")
    (OUT / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(6, 4))
        for dtv, mk in ((10, "o"), (1, "s")):
            xs = [r["beta_ldk_dt"] for r in rs if r["dt_s"] == dtv]
            ys = [r["residual_pct"] for r in rs if r["dt_s"] == dtv]
            ax.scatter(xs, ys, marker=mk, label=f"Δt={dtv} s")
        ax.set_xscale("log"); ax.set_xlabel("β_LDK·Δt [-]"); ax.set_ylabel("unaccounted [% of M]")
        ax.set_title("2022 simulation: mass-balance residual vs β·Δt"); ax.legend(); fig.tight_layout()
        fig.savefig(OUT / "fig_residual.png", dpi=120)
    except Exception as e:  # noqa: BLE001
        print("plot skipped:", e)


if __name__ == "__main__":
    main()
