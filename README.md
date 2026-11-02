# Air Quality Research OS

日本大学 理工学部 井口研究室（住宅班）の**空気清浄度研究（2018〜2026年度）**を、資料台帳・知見・物理モデル・実測データ解析・研究計画として統合したローカル Web アプリです。

> ⚠ **このリポジトリは公開設定です。** Box 資料の原文・原データ・個人名はコミットしていません（要旨は言い換え、出典は Box ID とページ）。研究室外への公開が不適切な場合は、GitHub の Settings → Danger Zone → Change visibility で **Private** に変更してください。

## 7つの画面

| 画面 | 機能 |
|---|---|
| 1 研究ダッシュボード | 資料数・読了/未読・年度別状況・主要成果・未解決問題・進捗・次の作業 |
| 2 研究資料ライブラリ | 68件の Box 資料台帳、全文検索（AND）、年度・状態・テーマ絞込、要点抽出、Box リンク、該当ページ、相互関連、調査状態とメモの編集、ローカル資料登録 |
| 3 実験データ解析 | CSV/Excel 取込（UTF-8/Shift_JIS、複数シート）、プレビュー、欠損・異常値検出（ロバストZ）、時系列（1時間平均）、I/O比・原点通過回帰（95%CI）、粒径別除去効率、差圧–風量の累乗近似、電力–CADR、減衰からβ同定、文献値による複数研究比較、CSV/PNG出力 |
| 4 空気清浄シミュレーター | 2026年度の並列流路モデル（EP∥バイパス, 送風機P-Q）＋単室マスバランス＋**多室（換気回路網）モデル**（SHASE2021 その40 の実験住宅13室回路網をプリセット）。換気量・循環風量・集塵効率・バイパス・室容積・外気濃度（季節プリセット）・発塵率・運転時間。式・単位・根拠・外挿警告を表示 |
| 5 研究ナレッジグラフ | 研究→装置/測定項目→成果→仮説/未解決問題→研究テーマ（99ノード）。クリックで詳細と資料根拠 |
| 6 今後の研究計画 | テーマ9件の多基準評価（重み可変）、15項目の実験設計、採否と理由の記録、競合仮説、ロードマップ、未解決問題の更新 |
| 7 総合研究レポート | 8章の報告書（Markdown管理・画面内編集）、Markdown出力、印刷→PDF |

PC・iPhone 両対応（下部タブバー）。Service Worker と localStorage スナップショットにより、一度開いた画面は**オフラインでも閲覧**でき、シミュレーターと CSV / Excel(.xlsx) 解析はオフラインで動作します（Excel は依存ライブラリなしの自前リーダー）。

## 起動方法

```bash
# 初回のみ
python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
(cd frontend && npm install && npm run build)

# 起動（http://localhost:8000 を開く。スマートフォンは同一LANで http://<PCのIP>:8000）
./run.sh            # = .venv/bin/uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000
```

開発時はフロントのホットリロード: `cd frontend && npm run dev`（:5173、/api は :8000 へプロキシ）。

## テスト

```bash
.venv/bin/python -m pytest              # Python: 計算式の検算・API・永続化・並行アクセス・多室モデル（40件）
(cd frontend && npm test)               # TypeScript: Python 実装との数値一致・xlsx リーダー（26件）
NODE_PATH=$(npm root -g) node frontend/e2e/e2e.cjs   # ブラウザE2E（起動中のサーバーに対して, 29項目）
python scripts/make_crosscheck_fixture.py   # モデル変更時に参照値を再生成
```

ブラウザ E2E（デスクトップ＋iPhone 13 表示, 29項目）の結果とスクリーンショットは `docs/screenshots/` にあります。

## データと構成

```
backend/aqros/        物理モデル(models.py)・解析関数(analysis.py) — 研究用 Python コード
backend/app/          FastAPI + SQLite（db.py, main.py）
frontend/src/         React + TypeScript（core/models.ts は Python の移植）
scripts/knowledge_data.py   研究ナレッジの単一ソース（資料台帳・知見・仮説・テーマ）
scripts/build_knowledge.py  → knowledge/knowledge.json と SOURCES/FINDINGS/HYPOTHESES/OPEN_QUESTIONS.md を生成
scripts/make_figures.py     → docs/figures/（出典付き SVG 図表）
report/*.md           総合研究報告書（8章）
docs/                 年度別研究分析・研究テーマ候補一覧・図表・スクリーンショット
private_data/         SQLite DB・取込データ（Git 管理外）
```

SQLite DB（`private_data/aqros.sqlite3`）は起動時に `knowledge.json` と `report/*.md` を取り込みます。画面で編集した項目（調査状態・メモ・採否・報告書の章）は `user_modified` として保護され、再起動・再シードで上書きされません。

## 根拠管理のルール

全ての重要な記述に区分を付けています: 【確認事実】【当事者の主張】【分析】【仮説】【予測】【不明】【計算結果】。
資料台帳の調査状態は **未確認 → 目録確認 → 読了 → 数値検証済み** の4段階で、本文を読んでいない資料を読了扱いにしません。引用元が不明な数値を実測データとして扱わず、合成デモデータには「合成」と明示しています。

## Box 連携について

本アプリは Box API を直接呼びません（認証情報をリポジトリに置かないため）。Box 資料の調査は Claude Code の Box MCP 連携（読み取り専用）で実施し、結果を `scripts/knowledge_data.py` に記録しました。Box に接続できない環境では、画面2の「＋ローカル資料」と画面3のファイル取込が代替手段です。
