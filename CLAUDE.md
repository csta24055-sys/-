# CLAUDE.md — Air Quality Research OS

このリポジトリは井口研究室の空気清浄度研究の統合アプリ。作業前に必ず読むこと。

## 絶対ルール
- **リポジトリは公開設定**。Box 資料の原文（文章の転載）、原データ（Excel/CSV）、学生・居住者の氏名、住宅の詳細住所、アンケート内容をコミットしない。原データは `private_data/`（gitignore 済み）へ。
- Box は**読み取り専用**。Box へのアップロード・移動・削除・メタデータ書込をしない。
- 読んでいない資料を「読了」にしない。調査状態: 未確認 / 目録確認 / 読了 / 数値検証済み。
- 記述には区分を付ける: 確認事実 / 当事者の主張 / 分析 / 仮説 / 予測 / 不明 / 計算結果。
- 出典不明の数値を実測値として扱わない。合成データは「合成」と明示する。
- 住宅で得た係数を非住宅（学校・病院・産業施設・発電所関連）へ無条件に外挿しない。

## 構成と編集の流れ
- 研究ナレッジの単一ソース: `scripts/knowledge_data.py` → `python scripts/build_knowledge.py` で `knowledge/knowledge.json` と SOURCES/FINDINGS/HYPOTHESES/OPEN_QUESTIONS.md、`docs/年度別研究分析.md`、`docs/研究テーマ候補一覧.md` を再生成。生成物を直接編集しない。
- 物理モデル: `backend/aqros/models.py`（Python）と `frontend/src/core/models.ts`（TS 移植）は**必ず両方**更新し、`python scripts/make_crosscheck_fixture.py` → `cd frontend && npm test` で一致を確認。
- 報告書: `report/*.md`（ファイル名順が章順）。
- 図表: `python scripts/make_figures.py`。

## コマンド
- テスト: `.venv/bin/python -m pytest` / `cd frontend && npm test`
- ビルド: `cd frontend && npm run build`（`tsc -b` 込み）
- 起動: `./run.sh` → http://localhost:8000
- 注意: `.gitignore` に `lib/` と `dist/` があるため、`lib` という名前のソースディレクトリを作らない。

## 単位系（モデル）
Q m³/h, C μg/m³, G μg/h, V m³, β 1/h（研究室資料の 1/s は ×3600）, ΔP Pa。

## 既知の論点（解決したら FINDINGS/OPEN_QUESTIONS を更新）
- F-2026-03/07/08: 2026年度の差圧値は式(2)からは再現せず、750 m³/h 超を二乗則で外挿すると一致。60ケース照合は verification/R-2026/（二乗則で5/8一致）。多台数CADR最大値は通過風量≤約1000 m³/h の除外条件を仮定しないと再現しない（Q-13）。
- F-2025-06/10: 2025年度住宅Cの条件区分が中間版と最終版で異なり、本論の運転記録（表6）は中間版側と一致（Q-04）。
- F-2025-12/22: センサー記録値の変換式 raw/65535×1000 はメーカー仕様と同一（Q-11 解決）。公称精度は±10 μg/m³ または±10%。本論・プログラムに外部サーバーの接続情報が平文で載っているが、絶対に転載しない。
- F-X-07 / H-01: EP効率 96%（2018仕様）vs 82〜92%（2026実測）。
- F-2025-19/20/25/26, Q-12: 住宅D（周南）の原データSheet1は条件①を10/5 14:00から抜粋（梗概の12/9は誤記の可能性）。全数値は Box 連携で取得不可（ページ画像は見られる）。外気中央値も資料間で矛盾。
- 大きい/画像のBox資料の取得方法は `docs/資料取得の技術的検討.md`（リソース取得 files://ID で PDF 原本、get_preview_page でページ画像）。
- F-SIM-08〜12: 2022年度シミュレーションは本アプリで再現。『まとめ』のLDKは吹抜を含み、『その他』は30分後の浮遊残存＋初回ステップ損失による数値残差（時間刻み依存, F-SIM-13）。EP OFFでも集塵機欄に値あり（F-SIM-14）。検証記録は verification/Y2022_simulation/。
- 検証スクリプト: `scripts/raw_2025.py`（+`dynamic`, `night`）、`scripts/annual_2024.py`、`scripts/validate_multizone.py`、`scripts/validate_fate_2022.py`。入力は `private_data/raw/`（非コミット）、出力は `knowledge/*.json`（集計値のみ）。
- Excel のシート名・ラベルに居住者の姓が入っているものがある（2021ダストサンプラー、2024 EP停止試験など）。住宅は記号でのみ記載する。
