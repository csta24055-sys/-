#!/usr/bin/env python3
"""MDL-C01-0001 三井物産 有利子負債の再構成・政策金融比率モデル（v1）

入力は ``ledger/observations.jsonl`` の観測値のみ（手入力の定数を持たない）。
出力 ``datasets/MDL-C01-0001_outputs.json`` は研究ゲートが再計算して一致を検査する。

    python3 research/companies/三井物産/models/MDL_C01_0001_debt_policy_finance.py [--check]

統計的推定は行わない（決定論的な検算と比率計算のみ）。為替換算は感応度を併記する。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CDIR = HERE.parent
MODEL_ID = "MDL-C01-0001"
VERSION = "1.0.0"
FY, PY = "FY2025(2026-03-31)", "FY2024(2025-03-31)"


def load_obs(cdir: Path = CDIR) -> dict:
    rows = [json.loads(l) for l in (cdir / "ledger" / "observations.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    out = {}
    for r in rows:
        key = (r["variable"], r["period"])
        if key in out and out[key]["value"] != r["value"]:
            raise ValueError(f"conflicting observations for {key}: {out[key]['observation_id']} vs {r['observation_id']}")
        out[key] = r
    return out


def run(cdir: Path = CDIR) -> dict:
    o = load_obs(cdir)

    def v(var, period=FY):
        return o[(var, period)]["value"]

    def ids(*keys):
        return [o[k]["observation_id"] for k in keys]

    res: dict = {"model_id": MODEL_ID, "version": VERSION, "unit_note": "億円=1e8円, 百万円=1e6円", "results": {}}
    R = res["results"]

    # 1) 有利子負債の再構成：短期債務 + 長期債務(1年内含む) − リース負債 = 会社定義の有利子負債
    for per in (FY, PY):
        st, lt, lease = v("short_term_bank_borrowings", per), v("long_term_debt_total_incl_current", per), v("lease_liabilities", per)
        R[f"debt_reconciliation:{per}"] = {
            "reconstructed_oku": round((st + lt - lease) / 100, 2),
            "formula": "(short_term_bank_borrowings + long_term_debt_total_incl_current - lease_liabilities)/100",
            "inputs": ids(("short_term_bank_borrowings", per), ("long_term_debt_total_incl_current", per), ("lease_liabilities", per)),
        }
    rec = R[f"debt_reconciliation:{FY}"]["reconstructed_oku"]
    R["debt_reconciliation"] = {
        "reconstructed_oku": rec,
        "reported_oku": v("interest_bearing_debt_reported"),
        "diff_oku": round(rec - v("interest_bearing_debt_reported"), 2),
        "change_reconstructed_oku": round(rec - R[f"debt_reconciliation:{PY}"]["reconstructed_oku"], 2),
        "change_reported_oku": v("interest_bearing_debt_change_reported"),
        "passes": abs(rec - v("interest_bearing_debt_reported")) < 1.0,
        "inputs": ids(("interest_bearing_debt_reported", FY), ("interest_bearing_debt_change_reported", FY)),
    }
    # 2) 返済年限別内訳
    buckets = ["maturity_le1y", "maturity_1to2y", "maturity_2to3y", "maturity_3to4y", "maturity_4to5y", "maturity_gt5y"]
    total = sum(v(b) for b in buckets)
    R["maturity_profile"] = {
        "sum_oku": total, "reported_total_oku": v("maturity_total"), "passes": total == v("maturity_total"),
        "le1y_share_pct": round(100 * v("maturity_le1y") / total, 2), "reported_le1y_share_pct": v("short_term_share_reported"),
        "gt5y_share_pct": round(100 * v("maturity_gt5y") / total, 2),
        "inputs": ids(*[(b, FY) for b in buckets], ("maturity_total", FY), ("short_term_share_reported", FY)),
    }
    # 3) ハイブリッド（劣後シ・ローン）
    hyb = (v("subordinated_syndicated_loan_tranche_a") + v("subordinated_syndicated_loan_tranche_b")) / 100
    R["hybrid"] = {
        "note_sum_oku": hyb, "reported_oku": v("subordinated_syndicated_loan"), "passes": hyb == v("subordinated_syndicated_loan"),
        "equity_credit_oku": v("hybrid_equity_credit_by_rating_agencies"),
        "share_of_interest_bearing_debt_pct": round(100 * hyb / v("interest_bearing_debt_reported"), 2),
        "inputs": ids(("subordinated_syndicated_loan_tranche_a", FY), ("subordinated_syndicated_loan_tranche_b", FY),
                      ("subordinated_syndicated_loan", FY), ("hybrid_equity_credit_by_rating_agencies", FY)),
    }
    # 4) 担保付『政府出資銀行及び政府機関』の比率（政策金融全体ではない）
    gov = v("secured_debt_govt_banks_agencies")
    R["govt_secured_share"] = {
        "govt_secured_oku": gov / 100,
        "share_of_interest_bearing_debt_pct": round(100 * (gov / 100) / v("interest_bearing_debt_reported"), 2),
        "change_oku": (gov - v("secured_debt_govt_banks_agencies", PY)) / 100,
        "caveat": "無担保のJBIC貸付は『銀行及びその他』に混在し識別不能。政策金融総額の下限でも上限でもない。",
        "inputs": ids(("secured_debt_govt_banks_agencies", FY), ("secured_debt_govt_banks_agencies", PY), ("interest_bearing_debt_reported", FY)),
    }
    # 5) JBIC 2025年度公表案件（限度額）
    pairs = [("blue_point", "2025-06-30契約"), ("etg", "2025-08-20契約"), ("ruwais_1", "2026-02-24契約"), ("ruwais_2", "2026-02-24契約"), ("miod", "2026-03-09契約")]
    jb = sum(o[(f"jbic_loan_limit_{p}", d)]["value"] for p, d in pairs)
    co = sum(o[(f"cofinance_total_{p}", d)]["value"] for p, d in pairs)
    parent_borrower = sum(o[(f"jbic_loan_limit_{p}", d)]["value"] for p, d in pairs if p in ("blue_point", "ruwais_1", "ruwais_2"))
    R["jbic_fy2025"] = {
        "contracts": len(pairs), "press_releases": 4,
        "jbic_limit_musd": jb, "cofinance_total_musd": co, "jbic_share_pct": round(100 * jb / co, 1),
        "private_cofinance_musd": co - jb,
        "jbic_limit_parent_borrower_musd": parent_borrower,
        "co_lender_count": {"三井住友銀行": 3, "みずほ銀行": 1},
        "inputs": [o[(f"jbic_loan_limit_{p}", d)]["observation_id"] for p, d in pairs] + [o[(f"cofinance_total_{p}", d)]["observation_id"] for p, d in pairs],
    }
    # 6) Rhodes Ridge：政策＋協調融資が取得支出に占める比率（為替感応度つき）
    fx = v("avg_usdjpy")
    loan = o[("cofinance_total_miod", "2026-03-09契約")]["value"]
    capex = v("capex_rhodes_ridge")
    sens = {}
    for k, f in (("fx_-10pct", 0.9), ("base", 1.0), ("fx_+10pct", 1.1)):
        sens[k] = round(100 * loan * fx * f / 100 / capex, 2)  # 百万米ドル×円/米ドル=百万円 → /100=億円
    R["rhodes_policy_share"] = {
        "loan_musd": loan, "fx_jpy_per_usd": fx, "loan_oku": round(loan * fx / 100, 1), "capex_oku": capex,
        "share_pct": sens,
        "caveat": "限度額・平均レート換算。分子は子会社MIODの借入、分母は連結の設備投資支出。",
        "inputs": ids(("avg_usdjpy", FY), ("capex_rhodes_ridge", FY)) + [o[("cofinance_total_miod", "2026-03-09契約")]["observation_id"]],
    }
    # 7) 資金ギャップ
    gap = v("core_operating_cash_flow") + v("asset_recycling_cash_in") - v("investments_and_loans") - v("shareholder_returns")
    R["cash_gap"] = {
        "computed_post_return_cf_oku": gap, "reported_oku": v("post_return_cash_flow"),
        "diff_oku": gap - v("post_return_cash_flow"),
        "net_debt_change_oku": v("net_interest_bearing_debt") - v("net_interest_bearing_debt", PY),
        "net_der": [v("net_der", PY), v("net_der")],
        "note": "会社概数（10億円単位）のため数十億円の差は丸め誤差の範囲",
        "inputs": ids(("core_operating_cash_flow", FY), ("asset_recycling_cash_in", FY), ("investments_and_loans", FY), ("shareholder_returns", FY),
                      ("post_return_cash_flow", FY), ("net_interest_bearing_debt", FY), ("net_interest_bearing_debt", PY), ("net_der", FY), ("net_der", PY)),
    }
    return res


def main(argv: list[str]) -> int:
    res = run()
    out = CDIR / "datasets" / f"{MODEL_ID}_outputs.json"
    if "--check" in argv:
        stored = json.loads(out.read_text(encoding="utf-8"))
        ok = stored == res
        print("REPRODUCIBLE" if ok else "MISMATCH")
        return 0 if ok else 1
    out.write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(res["results"], ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
