# 実装進捗（アプリ）

最終確認: 2026-11-03。テスト: pytest 56件、vitest 26件、ブラウザE2E 37/37（デスクトップ＋iPhone 13 表示）すべて通過。

| 機能（指令の区分） | 状態 | 実装場所 | 確認方法 |
|---|---|---|---|
| A ダッシュボード（資料数・調査状態・完成度一覧・次の作業） | 完了 | frontend/src/pages/Dashboard.tsx | E2E（完成度表） |
| B 資料ライブラリ（Box台帳95件・文献23件・検索・状態編集） | 完了 | Library.tsx（LiteraturePanel） | E2E（文献パネル・検索） |
| C データ解析（CSV/Excel取込・I/O・回帰・β同定・出力） | 完了 | DataAnalysis.tsx, core/xlsx.ts | vitest（合成xlsx）, E2E |
| D シミュレーション（単室・多室・EPバイパス、プリセット、外挿警告、非住宅への外挿注意） | 完了 | Simulator.tsx, core/models.ts | vitest（Python と数値一致）, E2E |
| E ナレッジグラフ | 完了 | KnowledgeGraph.tsx | E2E |
| F テーマ比較（重み可変）・研究計画の作成/編集/保存 | 完了 | ResearchPlan.tsx, components/PlanEditor.tsx, /api/plans | pytest（CRUD・検証）, E2E（保存の永続化） |
| G レポート（Markdown編集・出力、2冊の資料の md/docx/pdf ダウンロード） | 完了 | Report.tsx, /api/deliverables | pytest, E2E（docx の ZIP 署名とヘッダー） |
| H 学習モード（13段階・進捗保存） | 完了 | pages/Learning.tsx, /api/state/learning | pytest, E2E（再読込後の保持） |
| オフライン閲覧（Service Worker・スナップショット） | 完了 | public/sw.js | E2E |

## 既知の制約
- ヘッドレス Chromium は UTF-8 のファイル名（filename*）を無視して "download" と保存する。サーバーは ASCII 代替名と filename* の両方を返しており、通常のブラウザでは日本語名で保存される（静的サーバーで同じ挙動を確認済み）。
- 実機の iPhone では未確認（E2E は iPhone 13 のエミュレーション）。
- 研究計画・学習進捗はローカルの SQLite に保存される単一利用者向けの設計で、ログイン・共有機能はない。
