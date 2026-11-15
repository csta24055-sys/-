# 世界水準 UI・UX 研究 — 4用途別デザイン体系とプロトタイプ

研究支援・公共・商用・大企業品質の4用途について、世界の実在事例48件を調べました。そのうえで、各用途に3案（計12案）の UI コンセプトを作って重み付きで評価し、採用案を動くプロトタイプにしました。

- 実施日: 2026-11-15（作業時間は指示どおり開始から1時間以内。15:59 UTC 開始）
- 既存アプリの本番 UI・既存コードは**一切変更していません**。成果物はすべてこの `design-research/` フォルダにあります。
- データはすべてダミーです。機密情報・個人情報は外部サービスに送っていません。

## 成果物

| # | 成果物 | ファイル | 状態 |
|---|---|---|---|
| 1 | 世界の優良UI・UX事例 調査台帳（48件） | [research-ledger.md](research-ledger.md)（元データ: [data/](data/)） | 完了 |
| 2 | 4分類のUI・UX設計原則 | [design-principles.md](design-principles.md) ＋ 各分類の `principles.md` | 完了 |
| 3 | 12種類のUIコンセプト比較 | [concepts-comparison.md](concepts-comparison.md) ＋ 各分類の `concepts.md` / `concepts.html` ＋ [評価グラフ](assets/concepts-weighted-score.png)（[動画](assets/concepts-weighted-score.mp4)） | 完了 |
| 4 | 推奨デザインシステム | 各分類の `design-system.md` ＋ [recommended-design-system.md](recommended-design-system.md) | <!--STATUS4-->作成中 |
| 5 | プロトタイプ | 各分類の `prototype.html`（4画面＋部品一覧、デスクトップ/モバイル）、`screens.md`、`screenshots/`、Figma ボード | <!--STATUS5-->作成中 |
| 6 | 既存アプリへの適用計画 | [existing-projects-analysis.md](existing-projects-analysis.md) ＋ [application-plan.md](application-plan.md) | <!--STATUS6-->作成中 |

## 分類ごとの採用案

点数は各分類の重みで計算した加重合計（5点満点）です。**重みが分類ごとに違うため、点数は同じ分類の中でだけ比べてください。**

| 分類 | 案A | 案B | 案C（採用） | フォルダ |
|---|---|---|---|---|
| A 研究室内部用 | 表計算・台帳型 Grid Ledger 3.94 | ノートブック型 Evidence Notebook 3.26 | **パイプライン＋台帳 Pipeline Ledger 4.30** | [A-research-lab/](A-research-lab/) |
| B 国家規模・公共 | 市民優先タスク直行型 4.12 | 専門家優先 分析ワークベンチ型 3.17 | **段階的開示 3層レイヤー型 4.42** | [B-public/](B-public/) |
| C 収益追求型の商用 | ワークベンチ 3.34 | ショーケース 3.44 | **アウトカム・ハブ 4.37** | [C-commercial/](C-commercial/) |
| D 大企業品質 | Operations Console 4.14 | Insight Workspace 3.34 | **Federated Shell 4.36** | [D-enterprise/](D-enterprise/) |

> 注意：4分類すべてで統合型（案C）が最高点になりました。どの分類でも案Aの効率・案Bの表現力を取り込める統合型が有利になるという評価軸の構造が影響している可能性があります。評価は設計者側の採点であり、実ユーザーでの検証（ユーザビリティテスト）はまだ行っていません。

各分類フォルダの中身:

- `principles.md`：その分類の設計原則と、避けるべき設計
- `concepts.md`：3案の詳細と評価
- `concepts.html`：3案の視覚比較
- `prototype.html`：採用案のプロトタイプ（`#dashboard` `#workspace` `#detail` `#settings` `#components`）
- `screens.md`：画面一覧と操作説明
- `design-system.md`：その分類のデザインシステム
- `a11y-report.md`：WCAG 2.2 AA の検証結果
- `screenshots/`：デスクトップとモバイルの画面

<!--QA-->

## 外部ツールの利用状況（実際に行ったことだけ）

| ツール | 実施内容 | 結果・リンク |
|---|---|---|
| Web 検索 / Web 取得 | 48件の公式サイト・公式デザインシステムを確認 | 44件は公式ページを本セッションで取得、4件は検索結果のみ（台帳に件ごとに明記） |
| GitHub | このリポジトリのコード・文書を読み、ユーザーのリポジトリ一覧を検索 | 他リポジトリ（`structural-experiment-ai`, `architecture-exam-ai` ほか）は**中身を読めていません**。このセッションのアクセス範囲外で、追加は権限設定により拒否されました |
| Canva | 4分類の設計思想を比較するインフォグラフィックを AI 生成し、候補1をアカウントに保存 | 「インフォグラフィック - UI・UX設計思想マップ」 https://www.canva.com/d/f74bQrdDPIK6NfC （編集用・非公開） |
| Picsart Media Studio | 12案の加重評価スコアをアニメーション棒グラフとして描画し、PNG と MP4 を書き出し | [assets/concepts-weighted-score.png](assets/concepts-weighted-score.png)、[assets/concepts-weighted-score.mp4](assets/concepts-weighted-score.mp4)（Picsart Drive にも自動保存）。日本語フォントが無かったためラベルは英語 |
| Figma | 新規デザインファイルを作成 | https://www.figma.com/design/rioC98xeuRVf34PkEFFzC6 <!--FIGMA--> |
| 「ピクスタ」「メディカルスタジオ」 | 接続一覧を確認 | 該当名のサービスは接続されていません。ユーザー指定の「Picsart Media Studio」が接続されていたため、それを使いました |

## 工程の完了状況

<!--PROGRESS-->

## 未達成・限界

<!--GAPS-->
