"""2026年度 バイパス並列流路モデルの独立検証（中間梗概 S-2026-01 の数値記述との照合）。

対象: 送風機「中」(190 m³/h/台) × 台数 5/10/15/20 × バイパス開口率 0/25/50/75/100% × 抵抗則3種 = 60ケース。
抵抗則:
  fit    : 式(2) Q=78.611ΔP^0.828 を全域に適用（本文が明記する方法）
  quad   : 750 m³/h まで式(2)、超過分は ΔP∝Q²（乱流抵抗則の仮定）
  linear : 750 m³/h まで式(2)、超過分は ΔP∝Q（層流の仮定, 下限側の感度）
"所要差圧" = 送風機が設定風量を保つと仮定したときに並列部で必要な差圧（本文の「0%で95〜350Pa程度に達して…超過」の意味）。
"運転点" = 送風機 P-Q（限界静圧80 Pa以降は直線降下の仮定）と釣り合う点（backend/aqros/models.py の solve_bypass）。
出力: results.json, results.md（集計値のみ。原文の転載なし）
"""
import json, math, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from aqros import models as M  # noqa: E402

QMAX, DPMAX = 750.0, (750.0 / M.EP_COEF) ** (1 / M.EP_EXP)
RHO, ALPHA, AFULL = 1.2, 0.65, 0.25


def q_ep(dp, law):
    if law == "fit" or dp <= DPMAX:
        return M.EP_COEF * max(dp, 0) ** M.EP_EXP
    if law == "quad":
        return QMAX * math.sqrt(dp / DPMAX)
    return QMAX * dp / DPMAX  # linear


def q_bp(dp, r):
    return 3600 * ALPHA * AFULL * r * math.sqrt(2 * max(dp, 0) / RHO)


def required_dp(q_total, r, law):
    lo, hi = 0.0, 1e5
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if q_ep(mid, law) + q_bp(mid, r) < q_total else (lo, mid)
    return (lo + hi) / 2


def eta(q):  # 0.3–0.5 μm, 端点線形（models.ep_efficiency と同じ仮定）
    return M.ep_efficiency(q, "0.3-0.5")


CLAIMS = [
    ("C1", "多台数・開口0%の所要差圧が約95〜350 Pa（10台→下端, 20台→上端と解釈）", lambda R, law: (R[(10, 0.0, law)]["dp_req"], R[(20, 0.0, law)]["dp_req"]), lambda v: 80 <= v[0] <= 110 and 300 <= v[1] <= 400),
    ("C2", "開口25〜50%で差圧が約13〜47 Pa（10〜20台の範囲）", lambda R, law: (min(R[(n, r, law)]["dp_req"] for n in (10, 15, 20) for r in (0.25, 0.5)), max(R[(n, r, law)]["dp_req"] for n in (10, 15, 20) for r in (0.25, 0.5))), lambda v: 8 <= v[0] <= 20 and 35 <= v[1] <= 60),
    ("C2b", "（解釈B）開口50%・10〜20台で差圧が約13〜47 Pa", lambda R, law: tuple(R[(n, 0.5, law)]["dp_req"] for n in (10, 15, 20)), lambda v: 8 <= min(v) <= 20 and 35 <= max(v) <= 55),
    ("C3", "5台・開口0%で CADR 最大 約740 m³/h", lambda R, law: (R[(5, 0.0, law)]["cadr_req"],), lambda v: 700 <= v[0] <= 780),
    ("C4", "多台数で最大 CADR 約730〜770 m³/h（開口25〜50%）", lambda R, law: tuple(round(max(R[(n, r, law)]["cadr_req"] for r in (0.25, 0.5)), 0) for n in (10, 15, 20)), lambda v: all(700 <= x <= 800 for x in v)),
    ("C4b", "（仮説）集塵機通過風量 ≤1000 m³/h の点に限ると多台数の最大 CADR が約730〜770", lambda R, law: tuple(max(R[(n, r, law)]["cadr_req"] for r in (0.0, 0.25, 0.5, 0.75, 1.0) if R[(n, r, law)]["q_ep_req"] <= 1000) for n in (10, 15, 20)), lambda v: all(700 <= x <= 800 for x in v)),
    ("C5", "5台は開口0%で CADR 最大（開口で単調減少）", lambda R, law: tuple(round(R[(5, r, law)]["cadr_req"]) for r in (0.0, 0.25, 0.5, 0.75, 1.0)), lambda v: all(v[i] >= v[i + 1] for i in range(len(v) - 1))),
    ("C6", "開口100%で送風機電力 約4 W/台（運転点）", lambda R, law: tuple(round(R[(n, 1.0, law)]["w_unit"], 2) for n in (5, 10, 15, 20)), lambda v: all(3.5 <= x <= 5.0 for x in v)),
]


def main():
    R, rows = {}, []
    for law in ("fit", "quad", "linear"):
        for n in (5, 10, 15, 20):
            for r in (0.0, 0.25, 0.5, 0.75, 1.0):
                qt = 190.0 * n
                dp = required_dp(qt, r, law)
                qe = q_ep(dp, law)
                op = M.solve_bypass(r, n_units=n, setting="中", ep_law="fit" if law == "fit" else "quadratic_ext") if law != "linear" else None
                rec = dict(law=law, n=n, r=r, q_total=qt, dp_req=round(dp, 2), q_ep_req=round(qe, 1), q_bp_req=round(qt - qe, 1),
                           cadr_req=round(eta(qe) * qe, 1), over_fan_limit=dp > 80, ep_out_of_range=qe > QMAX * 1.05,
                           dp_op=round(op.dp, 2) if op else None, cadr_op=round(op.cadr, 1) if op else None, w_unit=round(op.power_per_unit if op else M.fan_power_per_unit(min(dp, 80), "中"), 2))
                R[(n, r, law)] = rec
                rows.append(rec)
    verdict = []
    for cid, text, get, ok in CLAIMS:
        for law in ("fit", "quad", "linear"):
            v = get(R, law)
            verdict.append(dict(claim=cid, text=text, law=law, value=[round(x, 1) for x in v], match=bool(ok(v))))
    out = Path(__file__).parent
    (out / "results.json").write_text(json.dumps(dict(cases=rows, claims=verdict), ensure_ascii=False, indent=1), encoding="utf-8")
    L = ["# 2026年度 並列流路モデルの数値照合結果（自動生成: verify_2026.py）", "", "区分: 【計算結果】。60ケース（4台数×5開口率×3抵抗則）。○=本文の記述範囲に一致。", "",
         "| 記述 | 内容 | fit（式(2)全域） | quad（750超 Q²） | linear（750超 Q） |", "|---|---|---|---|---|"]
    for cid, text, *_ in CLAIMS:
        cells = []
        for law in ("fit", "quad", "linear"):
            v = next(x for x in verdict if x["claim"] == cid and x["law"] == law)
            cells.append(("○ " if v["match"] else "× ") + ", ".join(str(x) for x in v["value"]))
        L.append(f"| {cid} | {text} | " + " | ".join(cells) + " |")
    L += ["", "## 所要差圧 ΔP [Pa]（送風機が設定風量を保つと仮定）", "", "| 台数 | 開口率 | fit | quad | linear | 集塵機通過風量 fit / quad [m³/h] |", "|---|---|---|---|---|---|"]
    for n in (5, 10, 15, 20):
        for r in (0.0, 0.25, 0.5, 0.75, 1.0):
            a, b, c = (R[(n, r, l)] for l in ("fit", "quad", "linear"))
            L.append(f"| {n} | {int(r*100)}% | {a['dp_req']} | {b['dp_req']} | {c['dp_req']} | {a['q_ep_req']:.0f} / {b['q_ep_req']:.0f} |")
    L += ["", "## CADR ≈ 750 m³/h を与えるのに必要な実効集塵効率（quad 則の集塵機通過風量に対して）", "", "| 台数 | 開口率 | 集塵機通過風量 [m³/h] | 必要 η = 750/Q_EP | 線形外挿 η |", "|---|---|---|---|---|"]
    for n in (10, 15, 20):
        for r in (0.25, 0.5):
            q = R[(n, r, "quad")]["q_ep_req"]
            L.append(f"| {n} | {int(r*100)}% | {q:.0f} | {750/q:.2f} | {eta(q):.2f} |")
    m = {l: sum(v["match"] for v in verdict if v["law"] == l) for l in ("fit", "quad", "linear")}
    L += ["", f"一致数: fit {m['fit']}/{len(CLAIMS)}, quad {m['quad']}/{len(CLAIMS)}, linear {m['linear']}/{len(CLAIMS)}"]
    (out / "results.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
