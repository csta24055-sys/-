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
- F-2026-03: 2026年度の差圧値は式(2)からは再現せず、750 m³/h 超を二乗則で外挿すると一致。
- F-2025-06: 2025年度住宅Cの条件区分が中間版と最終版で異なる（Q-04）。
- F-X-07 / H-01: EP効率 96%（2018仕様）vs 82〜92%（2026実測）。
