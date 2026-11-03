# RESTART_GUIDE — 中断後の再開手順

1. `CLAUDE.md`（絶対ルール）→ `EXECUTION_STATE.json`（`next_task`）→ `RESEARCH_COMPLETENESS.json`（研究単位ごとの完成度）を読む。
2. `git status` / `git log -5` で未コミットの作業がないか確認する。あれば内容を検証してからコミットする。
3. 環境: `.venv`（`pip install -r backend/requirements.txt`）、`frontend/`（`npm install`）。原データは `private_data/`（Git管理外, 消えていたら Box から再取得: `docs/資料取得の技術的検討.md`）。
4. `next_task` を実施する。完了済み（`status: done`）のタスクはやり直さない。
5. 節目ごとに:
   - `python scripts/build_knowledge.py`（ナレッジ再生成）
   - `python scripts/build_state.py --done <完了ID,...> --current <実行中ID>`（状態保存）
   - `.venv/bin/python -m pytest` と `cd frontend && npm test`
   - commit / push（ブランチ `claude/air-quality-research-os-19gu2g`）、`RUN_HISTORY.md` に1行追記
6. 自動再開: 毎時の定期タスク（このセッションに届く）。終了条件は第19章（全タスク done ＋ `QUALITY_AUDIT.md` の監査）。恒久的ブロック（Box取得不能など）は `EXECUTION_STATE.json` の blocked に理由を書き、同じ処理を繰り返さない。

## タスクID
| ID | 内容 |
|---|---|
| P1 | 研究資産の棚卸し（SOURCES.md, RESEARCH_COMPLETENESS.json） |
| P2-2022SIM | 2022年度シミュレーション全シート検証（verification/Y2022_simulation） |
| P2-OTHERS | 他年度研究の検証記録（verification/ 以下に研究単位ごと） |
| P5-LIT | 国内外文献レビュー（docs/文献レビュー.md, DOI確認済みのみ） |
| P6-SYNTH | 統合分析（因果関係図・系統図） |
| P7-BOOK1 / P7-BOOK2 | 2027年度向け2冊（deliverables/ に md・docx・pdf） |
| P8-APP | アプリ（学習モード・研究計画編集・資料出力） |
| P9-TEST / P11-AUDIT | 全体テスト、完成度監査（QUALITY_AUDIT.md） |


## 状態の保存（2026-11-03 追記）
`.venv/bin/python scripts/build_state.py --done <完了ID,...> --current <ID> --blocked "<ID>=<理由>"`。P2-OTHERS は取得可能な資料の検証を終え、残りがユーザー操作待ちのため blocked。次は P11-AUDIT（QUALITY_AUDIT.md・IMPLEMENTATION_PROGRESS.md・README 更新・全テスト・最終報告）。blocked の再試行は、ユーザーが分割CSV等を用意したときのみ行う。
