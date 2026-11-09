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

## 自動停止・自動再開（cc-autoresume, 2026-11-04 導入）
- 共通モジュール: `.claude/autoresume/`（移植元 csta24055-sys/-1 `tools/cc-autoresume/` v1.0.0）、設定 `.claude/autoresume.json`、状態 `AUTORESUME_STATE.json`、記録 `AUTORESUME_LOG.md`、非公開ログ `private_data/autoresume/`。
- 新しいコンテナでは最初に `python3 .claude/autoresume/install.py . --scope user`（冪等）。
- 区切りごとに `python3 .claude/autoresume/ccar.py checkpoint --done … --todo … --next … --test --push`。終了前に `plan-wake` → 一回限りの予約3件（primary/backup/weekly）を同じIDのまま run_once_at 更新 → `lock release`。
- クラウドセッションでは公式の使用率が取得できないため、85%準備・90%停止の判定は発動しない。リセット時刻は推定（実行開始＋5時間, official:false）。

## 2026-11-04 中間統合技術調査報告書（P12-REPORT）
- 成果物: `deliverables/technical_report_2026-11/`（docx・pdf・SOURCE_INVENTORY.csv・EVIDENCE_LEDGER.csv・NUMERICAL_AUDIT.csv・UNRESOLVED_ISSUES.md・REFERENCES.md・REPORT_QA.md・REPORT_README.md）。再生成は `.venv/bin/python scripts/build_tech_report.py`（libreoffice と libreoffice-math が必要。新しいコンテナでは `apt-get install -y libreoffice-math`）。
- **ユーザー指示（2026-11-04）: 許可のない GitHub push を行わない。** 自動再開の checkpoint では `--push` を付けず、コミットのみ行う。push はユーザーの明示的な許可後。
- 2018・2019年度の原データは「未取得資料」（付録H, M-01/M-02）として扱い、所在確認をユーザーに繰り返し求めない。
- 報告書の完成後は、アプリ開発・解析作業（RESTART_GUIDE の next_task）に戻る。

## 2026-11-09 デスクトップ配布版（P13-DESKTOP）
- 入口: `desktop/aqros_desktop.py`（ランチャー）、`desktop/aqros.spec`（PyInstaller）、`desktop/build.py`（ビルド＋アーカイブ）、`desktop/smoke_test.py`、`desktop/aqros.iss`（Windows インストーラー）、`.github/workflows/desktop.yml`（3 OS ビルド、v* タグで下書きリリース）。利用者向け手順は `docs/DESKTOP_INSTALL.md`。
- 保存先の決定は `backend/app/paths.py`。開発時（リポジトリから起動）は従来どおり `private_data/aqros.sqlite3`。
- 手元ビルド: `.venv/bin/pip install -r desktop/requirements-build.txt && .venv/bin/python desktop/build.py`（このコンテナでは Linux 版のみ）。
- 残り（P13-DESKTOP-CI）: Windows/macOS 版は push 後に Actions の desktop ワークフローを実行して作る。push・リリース公開はユーザー許可が必要。

## 2026-11-09 スマホ単体版（P14-MOBILE）
- 入口:
  - `frontend/src/core/local.ts`（端末内バックエンド）、`idb.ts`（IndexedDB）、`cloud.ts`（クラウド解析クライアント）
  - `pages/Settings.tsx`、`pages/Cloud.tsx`
  - `cloud/run_job.py`、`.github/workflows/cloud-jobs.yml`、`.github/workflows/mobile-pwa.yml`
  - `scripts/build_mobile.py`（ビルドと漏えい検査）、`deploy/pages-repo/`（公開用リポジトリのワークフロー）
  - 説明は `docs/MOBILE.md`
- 確認方法: `python scripts/build_mobile.py && python scripts/serve_static.py frontend/dist-mobile 47801 & (cd frontend && node e2e/mobile.cjs)`
- 漏えい検査の氏名リストは `private_data/privacy_patterns.txt`（非コミット）。新しいコンテナでは消えているので、検査語を入れ直すこと（無い場合、氏名検査は「確認不能」と表示される）。
- 残り（P14-MOBILE-PUBLISH）: push の許可、公開用リポジトリと Secret、ジョブ用の非公開リポジトリとトークン、実機確認。

## 2026-11-09 公開状況
- スマホ版: https://aqros-mobile.pages.dev（Cloudflare Pages、プロジェクト aqros-mobile）。
  - 更新は `python scripts/deploy_cloudflare.py` で行う（ビルド → 漏えい検査 → 公開）。
  - トークンはクラウド環境のネットワーク設定に保存済み。値をコマンドやファイルに書かない。
- デスクトップ版: Actions「desktop」の Artifacts（4 OS）。リリースは v* タグで下書きを作る。
- 残り（P14-DEVICE-CHECK）: 実機確認と、研究データ用の非公開ジョブリポジトリ。いずれもユーザー側の作業。
