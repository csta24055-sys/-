# NEXT_STEPS — 次回の再開手順

## 再開手順（新しいセッション）
1. `CLAUDE.md` と `RESEARCH_PROGRESS.md` を読む。
2. 環境構築: `python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt && (cd frontend && npm install && npm run build)`
3. テスト: `.venv/bin/python -m pytest && (cd frontend && npm test)`
4. 起動: `./run.sh` → http://localhost:8000
5. Box 連携が使える場合は Box MCP（読み取り専用）で下記の資料を読み、`scripts/knowledge_data.py` の該当 `S(...)` の status・各フィールドを更新 → `python scripts/build_knowledge.py`。

## 優先タスク（資料）
1. ~~S-2025-05 2025年度本論PDF を読了~~（完了: 運転記録と条件表の矛盾 F-2025-10、センサーの暫定換算 F-2025-12 を発見）。
   → **住宅Cの原データ（S-2025-21 直方測定データ.xlsx）を private_data/ に取得し、運転記録（本論 表6）で条件を再区分して回帰係数を再計算**（Q-04）。
   → **watty_説明書.pdf（S-2025-13, 画像PDF）を Box 上で目視し換算式を確認**（Q-11）。
2. **S-2025-18 パーティクルカウンタとWatty.xlsx** と **S-2024-09 wattyとリオンの比較.xlsm** を `private_data/` に取得 → 画面3で取込 → 校正係数を算出（T-02, H-07）。
3. **S-REF-01 清浄度-計算式_by井口.pdf** を Box 上で目視し、式を台帳に転記（Q-08）。
4. 2024年度サブフォルダ（wattyについて・外気フィルタ・分析）の個別ファイル目録化。
5. 2015〜2017年度・2019年度の清浄度関連研究の有無をキーワード検索（清浄度、粉塵、集塵、PM2.5、YUCACO）。
6. 2020年度 シミュレーション-iguchi.xlsx（S-2020-03）を読み、多室モデル実装の検証データにする。

## 優先タスク（解析・追加実験不要）
- 2025年度原データ（S-2025-19〜24）を取込み、夜間（0〜5時）抽出・住宅別の回帰係数を算出（H-02b, F-2025-07）。

## 優先タスク（アプリ）
- ~~多室換気回路網モデル~~（完了）。次: 回路網の編集UI（任意の住宅の室・風量を入力）、SHASE2021 図-9〜11 の実測値（数値表の入手後）との定量比較。
- SHASE 2019（S-REF-16, その31と推定）・2020（S-REF-17）の読了。
- ~~Excel のオフライン解析~~（完了: frontend/src/core/xlsx.ts）。.xls（旧形式）・.xlsb は未対応。
- 研究室内 LAN で共有する場合は認証（現在は無認証のローカル用途）を追加。

## 研究（2027年度班への提案）
短期: T-01 EP高風量域特性、T-02 センサー校正 → 中期: T-04 統合評価、T-03 季節別係数、T-05 発塵率、T-06 多室/CFD → 長期: T-07〜T-09。
