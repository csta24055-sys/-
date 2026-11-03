"""研究単位ごとの検証記録 verification/<ID>/AUDIT.md を生成する（単一ソース: audit_data.py, knowledge_data.py）。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audit_data as A  # noqa: E402
import knowledge_data as K  # noqa: E402

SCRIPTS = {
    "R-2020": ["scripts/validate_multizone.py"], "R-2022-SIM": ["verification/Y2022_simulation/verify_2022_sim.py", "scripts/validate_fate_2022.py"],
    "R-2024": ["scripts/raw_2024.py", "scripts/events_2024.py"], "R-2025": ["scripts/raw_2025.py（+dynamic, night, confound）", "scripts/annual_2024.py"],
    "R-2026": ["verification/R-2026/verify_2026.py（60ケース照合 → results.md）", "backend/aqros/models.py（ep_* / solve_bypass）", "backend/tests/test_models.py"], "R-2018": ["backend/tests/test_models.py（JEM1467 清浄時間）"],
    "R-2021-FALL": ["backend/tests/test_models.py（落下計算の沈着係数）"], "R-2023": ["backend/tests/test_models.py（β理論式）"], "R-2022-MEAS": ["verification/R-2022-MEAS/verify_2022_meas.py（→ results.md）"],
}
F = {f["id"]: f for f in K.FINDINGS}
S = {s["id"]: s for s in K.SOURCES}
DIR = {"R-2022-SIM": "Y2022_simulation"}


def main():
    idx = ["# 研究単位ごとの検証記録（索引）", "", "| ID | 年度 | 研究 | 分類 | 完成度 | 記録 |", "|---|---|---|---|---|---|"]
    for u in A.UNITS:
        d = ROOT / "verification" / DIR.get(u["id"], u["id"])
        d.mkdir(parents=True, exist_ok=True)
        done = sum(1 for x in u["v"] if x == "済"); appl = sum(1 for x in u["v"] if x != "対象外")
        L = [f"# 検証監査: {u['title']}（{u['year']}年度, {u['id']}）", "", "> scripts/build_verification_docs.py により audit_data.py・knowledge_data.py から自動生成。直接編集しない。", "",
             f"**分類**: {u['cls']}　**完成度**: {done}/{appl}（『済』の項目数）", "", "## 1. 原資料", "", "| ID | 資料 | 調査状態 |", "|---|---|---|"]
        for sid in u["sources"]:
            s = S.get(sid)
            if s:
                L.append(f"| {sid} | {s['title']} | {s['status']} |")
        L += ["", "## 2. 検証項目", "", "| 項目 | 状態 |", "|---|---|"] + [f"| {k} | {v} |" for k, v in zip(A.ITEMS, u["v"])]
        L += ["", "## 3. 再計算コード", ""] + ([f"- `{x}`" for x in SCRIPTS.get(u["id"], [])] or ["- なし（原データ未取得のため独立再計算は未実施）"])
        L += ["", "## 4. 検証結果・所見（根拠）", ""]
        for fid in u["evidence"]:
            f = F[fid]
            L.append(f"- **{fid}**【{f['class']}】{f['text']}")
        L += ["", "## 5. 未確認事項・制約", "", f"- {u['notes']}"]
        missing = [k for k, v in zip(A.ITEMS, u["v"]) if v in ("未", "不能", "一部")]
        if missing:
            L.append(f"- 未完了の項目: {', '.join(missing)}")
        (d / "AUDIT.md").write_text("\n".join(L) + "\n", encoding="utf-8")
        idx.append(f"| {u['id']} | {u['year']} | {u['title']} | {u['cls']} | {done}/{appl} | [AUDIT](./{DIR.get(u['id'], u['id'])}/AUDIT.md) |")
    (ROOT / "verification" / "README.md").write_text("\n".join(idx) + "\n", encoding="utf-8")
    print(len(A.UNITS), "units")


if __name__ == "__main__":
    main()
