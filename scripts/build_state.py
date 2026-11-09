"""RESEARCH_COMPLETENESS.json / EXECUTION_STATE.json の生成（再開時の機械可読な状態）。"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audit_data as A  # noqa: E402

TASKS = [
    ("P1", "研究資産の棚卸し（資料台帳・完成度台帳）"),
    ("P2-2022SIM", "2022年度シミュレーション全シート検証"),
    ("P2-OTHERS", "他年度研究の検証記録（verification/ 以下）"),
    ("P5-LIT", "国内外文献レビュー（DOI付き）"),
    ("P6-SYNTH", "統合分析（因果関係図・系統図）"),
    ("P7-BOOK1", "2027年度 研究継承総合資料（md/docx/pdf）"),
    ("P7-BOOK2", "2027年度 研究方針・テーマ戦略提案書（md/docx/pdf）"),
    ("P8-APP", "アプリ: 学習モード・研究計画編集・資料出力"),
    ("P9-TEST", "全体テスト・E2E"),
    ("P11-AUDIT", "完成度監査・QUALITY_AUDIT.md"),
    ("P12-REPORT", "中間統合技術調査報告書 2026-11（docx/pdf＋台帳・根拠台帳・数値監査）"),
    ("P13-DESKTOP", "デスクトップ配布版（ランチャー・PyInstaller・Linux版ビルドと起動確認・インストール手順）"),
    ("P13-DESKTOP-CI", "Windows / macOS 版のビルド（GitHub Actions desktop.yml の実行）"),
    ("P14-MOBILE", "スマホ単体版 PWA（端末内バックエンド・IndexedDB・バックアップ・オフライン・クラウド解析ジョブ・漏えい検査）"),
    ("P14-MOBILE-PUBLISH", "スマホ版の HTTPS 公開（Cloudflare Pages）・公開 URL での E2E・実際の GitHub Actions でのクラウドジョブ実行"),
    ("P14-DEVICE-CHECK", "iPhone / Android 実機での確認、研究データ用の非公開ジョブリポジトリ"),
]


def main(done: list[str], current: str | None, blocked: dict[str, str]):
    units = []
    for u in A.UNITS:
        items = dict(zip(A.ITEMS, u["v"]))
        n_done = sum(1 for x in u["v"] if x == "済")
        n_app = sum(1 for x in u["v"] if x != "対象外")
        units.append({k: u[k] for k in ("id", "year", "title", "sources", "cls", "evidence", "notes")} | {"items": items, "score": f"{n_done}/{n_app}"})
    (ROOT / "RESEARCH_COMPLETENESS.json").write_text(json.dumps({"generated_by": "scripts/build_state.py", "items": A.ITEMS, "units": units}, ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        commit = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:  # noqa: BLE001
        commit = None
    state = {"updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "last_commit": commit,
             "tasks": [{"id": t, "title": n, "status": ("done" if t in done else "blocked" if t in blocked else "in_progress" if t == current else "todo"),
                        **({"blocked_reason": blocked[t]} if t in blocked else {})} for t, n in TASKS],
             "next_task": next((t for t, _ in TASKS if t not in done and t not in blocked), None),
             "resume": "RESTART_GUIDE.md を読み、next_task から再開。完了済みタスクはやり直さない"}
    (ROOT / "EXECUTION_STATE.json").write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(state["tasks"], ensure_ascii=False))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--done", default="")
    ap.add_argument("--current", default=None)
    ap.add_argument("--blocked", action="append", default=[], help="ID=理由（複数可）")
    a = ap.parse_args()
    main([x for x in a.done.split(",") if x], a.current, dict(x.split("=", 1) for x in a.blocked))
