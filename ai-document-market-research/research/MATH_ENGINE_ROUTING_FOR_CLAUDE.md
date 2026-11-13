# Claude Code用：市場調査の統計ルーターと7数学エンジンの選択的利用

更新日：2026-11-13
適用：`csta24055-sys/-` の `claude/new-session-qm9g7r` ブランチ、`ai-document-market-research/` 以下。**研究専用、アプリ本体禁止、main書換禁止。**

## 1. 最初に理解する制約

- 市場調査は `S1 FAIL`、研究は `INCOMPLETE`。この仕組みは**収集資料を数学的に分類し、将来再計算可能にするための前処理**であり、S2〜S9の正式評価を開始する許可ではない。
- 既存 `registry/quant_results.csv` は、調査ごとの**公表された集計値**が中心。元の個票データではない。平均・中央値・相関・重回帰・ベイズ事後分布等を勝手に再構成するな。値・時間・母集団・定義が異なる調査をプールするな。
- `math_tools_v2/`, `math_interop_v0/`, `.github/workflows/math-ir-efficient.yml` は**同リポジトリのmainにあり、この研究ブランチには存在しない**。無条件のimportは失敗する。公式な研究ブランチだけを対象に研究コードを追加し、数学基盤本体は読み取り専用で参照すること。
- 7エンジン（SymPy, NumPy, SciPy, mpmath, DuckDB, SageMath, MATLAB Symbolic Math Toolbox）を**すべての計算で起動してはいけない**。それは軽量化に逆行する。統計計算の方法論に対して必要な最小のソフトだけ選ぶ。独立検算が必要な重大/厳密数式だけ別エンジンを追加。
- 本リポジトリは公開。非公開資料、個人情報、全文スキャン、個票、APIキー、認証トークン、商用未許諾文書を公開GitHub Actions入力へpushしない。

## 2. 実在コードと既存実証の対応

| 既存の場所（main） | 役割 | 市場調査への再利用 |
|---|---|---|
| `math_interop_v0/phase4.py` | 内容アドレス付きDAG、ハッシュ検査、部分再計算、DuckDB表集計 | **計算依存関係・改ざん検出・キャッシュ設計の参考実装** |
| `math_interop_v0/phase5.py` | 7エンジン実行記録の統合と9つの改ざん検査 | 厳密式の**選択的な独立照合**用。汎用統計エンジンではない |
| `math_tools_v2/portable.py` | Math IR 0.1、可変1～20件、Python5種類/7種類照合 | 整数/有理数/限定的多項式で検証が必要な時だけ |
| `math_tools_v2/lca_ops.py` | 積分、時間関数、マスク付き積和、節点スペクトル候補 | **LCA専用**。調査値の中央値やベイズ推定に流用しない |
| `.github/workflows/math-ir-efficient.yml` | 1ジョブ、`portable-python` / `portable-full` / `lca-operators` | 計算に適切な場合のみ手動起動。大量の起動を避ける |

**重要：Math IR 0.1の演算対象は安全な整数・有理数・記号・加算・乗算・限定的整数べき乗、単位は`1`または`kgCO2e`。任意のデータセットの中央値、階層ベイズ、複雑な統計モデル、一般行列は非対応。7エンジン統合が『すべての統計をそのまま実行できる』という主張は禁止。** `portable-full`は既存研究で合成数式を使った受け渡し検証に成功したが、現実の市場データの計算成功率は未測定。

## 3. 今回追加した読み取り専用分類コード

```bash
cd ai-document-market-research
python3 scripts/market_stat_router.py registry/quant_results.csv --output research/stat_routing.json
python3 -m unittest discover -s tests -p 'test_market_stat_router.py' -v
```

出力 `research/stat_routing.json` は `result_id` 別に証拠区分、許される計算、禁止された計算、候補エンジン、共通の出典IDを保持する。**候補にエンジン名を挙げただけで起動したことにはならない。** `engines_actually_run=[]` とする。

このルーター自体はPython標準ライブラリだけで動作し、Math IRや外部LLMの呼出しをしない。大量のCSVを毎回Claudeの文脈へ読み込まないための**前段階**。

## 4. 統計分類ルール（計算方法は一律にしない）

| データ | 許可される手法 | 禁止・保留 |
|---|---|---|
| 個票の実測時刻/作業時間/金額 | NumPy/DuckDBで件数、中央値、平均、分散、四分位、層別 | 同一人の反復測定を独立行として誤カウントしない |
| 同一母集団の成功数`k`と試行数`n` | 正しい分母を確認して率、SciPyでWilson/正確な区間など | 単なる公表の百分率から勝手に個人数を作る |
| 公表済みの割合のみ | 発表元の値と調査枠・標本数を保持、丸め誤差込みの照合 | 異なる調査の平均を人口全体の割合と呼ばない |
| 報告された中央値1値 | **中央値として保存するのみ** | 個票なしで分散・CI・平均を再構成する |
| 英文/和文価格表 | プラン・日時・通貨・税/請求周期を一致させて条件付き比較 | 価格をWTP、課金率、需要曲線とみなさない |
| 複数資料の引用 | 出典起源`origin_group_id`で依存性を統合、転載は別標本に数えない | 共有された引用の数で信頼区間を縮めない |
| 実験なしの利用意向や市場規模 | `NON_IDENTIFIABLE`、記号式、追加データの収集計画 | 0%や50%や一律係数で穴埋めしない |
| 会社の比較スコア/順序点 | 条件付き感度・ミニマックス後悔 | 51/53シナリオを「勝率96%」と呼ばない |
| ベイズ/階層ベイズ | 実観測、尤度、事前分布、標本設計・従属性、感度分析が明記された場合だけ | 『ベイズを使いたいから』という理由で事前分布とサンプルを捏造しない |

原則は**記述統計→母集団/層別→依存性→不確実性→必要に応じて回帰/ベイズ**。特定の手法を全項目へ一律強制しない。全IDについて「実行」「データ不足」「方法上不適当」のいずれかを証拠付きで記録する。

## 5. エンジン選択とキャッシュの推奨構成

1. Claudeは検索・出典原文/単位/観測対象の照合に専念し、CSVや証拠全文を毎回プロンプトに貼らない。
2. `source_id` → `origin_group_id` → `topic_id` → `metric_id` を関連付け、観測行・数値・式に固有ハッシュを付ける。
3. DuckDBを先に使って**独立な出典群・同一調査の複数設問を判別**。件数・合計などはここで処理し、Claudeへ戻すのは要約と異常値リストだけ。
4. **生データがある場合だけ**NumPyで中心傾向、SciPyで信頼区間・検定・回帰/分布推定を行う。標本重み/設計を無視した回帰・有意確率は作らない。
5. 厳密な整数比・有理式の照合を必要とする場合はSymPyで式を検証し、既存Math IRが扱える式だけ `portable-python` に送る。精度の問題があるときに限りmpmathを使う。
6. 重要な厳密値に独立実行の価値があり、対象式がMath IR制約内なら、SageMath → MATLABを追加する`portable-full`を検討する。ただし高負荷かつActions費用を要するため通常は実行しない。
7. 実行した各ジョブに、式、数値入力、母集団、出典ID、起源、観測/仮定区分、エンジンとバージョン、ハッシュ、検算、再実行コマンド、失敗理由を保存する。**入力・コード・条件が不変ならキャッシュを再使用**し、依存が変わった計算のみ再実行する。
8. GitHub ActionsのArtifacts保管容量を浪費しない。既存軽量Workflowは**最終JSONだけ、保持1日**。ML学習済みモデルや取得Web全文など巨大Artifactは保存しない。
9. セッションの各報告では `input_rows, classified_rows, executed_calculations, non_identifiable, rejected_invalid_method, failed_validation, cache_hit, engines_actually_run, wall_seconds, output_bytes` を分ける。**具体的なコスト・時間削減率は実測前には報告しない**。

### mainの数学基盤への安全な接続（後続Claude Code用）

研究ブランチをcheckoutした作業ツリーから、`git fetch origin main` をした上で、**読み取り専用**で以下を確認する：

```bash
git show origin/main:math_interop_v0/phase4.py
git show origin/main:math_tools_v2/portable.py
git show origin/main:math_tools_v2/README.md
git show origin/main:.github/workflows/math-ir-efficient.yml
```

実行する必要があるなら、元ブランチを変更せず、一時的な別ワークツリー `git worktree add --detach /tmp/market-math-main origin/main` を用意し、承認済みの**公開・匿名・非機密の検証用式**のみを扱う。既存ツールの入力は`math_tools_v2/examples/*.json`、1〜20件、最大64KiBであり、外部の数値表をそのまま食わせない。異なるIRへの安全な変換器を研究専用として作成し、失敗時は`UNSUPPORTED_EXPRESSION`で停止する。

## 6. 正式研究への取り込み

- `market_stat_router.py`とCSV/JSONは**計算を行うべき場所の分類**まで。まだ市場研究結果の完全な再計算でも、7エンジンの市場データ実行でもない。
- `registry/quant_results.csv`に登録済みの22結果のうち、原資料がS2未検証なら最終結果として確定扱いしない。
- 前回`external_handoff/phase1d_calculation_inventory_20261113.csv`の16件と`PHASE1A_AXIS01_CALCULATION_INVENTORY_20261113.csv`の12件の計算IDも個別に分類・検算した上で、元の全325テーマの`CALCULATION_INVENTORY`へ統合する。
- S1がPASSするまで市場全体の完成・正式製品推奨の判定を出さない。中間の計算方法・検証失敗の記録は可。
- 原ZIPの統計方法規定 `03_RESEARCH_METHOD_AND_STATS.md` の「偽口コミ・架空の百分率・同一起源の二重計上・未較正の成功確率禁止」を引き続き厳守。

**完了と宣言できるのは、対象ID全件の分類・原文入力の検証・適切な演算の実行/適正な不実施理由・独立検算・ゲートの全条件が整合した時のみ。**

## 7. 既存DAGを実際に呼ぶ接続器（新規追加）

`scripts/market_math_dag_adapter.py` は `main` の `math_interop_v0/phase4.CalcDAG` を**コピーせずimport**し、現在の22集計結果について内容アドレス付きノードとDuckDBの出典ID別集計を構築する。計算内容が不変であれば、同じキャッシュディレクトリの結果を再利用できる。これは**7エンジンの一括実行ではない**。この接続器で実行する数学ライブラリはDuckDBのみで、sourceノードと分類はPython標準ライブラリによる。

```bash
# 研究ブランチ上で実行する。mainは別ワークツリーから読み取り専用で使用。
git fetch origin main
git worktree add --detach /tmp/market-math-main origin/main
python3 -m pip install -r /tmp/market-math-main/math_tools_v2/requirements.txt
cd ai-document-market-research
python3 scripts/market_math_dag_adapter.py registry/quant_results.csv \
  --math-core /tmp/market-math-main/math_interop_v0 \
  --cache /tmp/market-stat-cache \
  --output research/market_dag_summary.json
# 同一入力でもう一度実行し computed_nodes と reused_nodes を比較。
```

**現時点では実行用コードをGitHubへ追加した段階**。この研究ブランチ上でのmainワークツリーの依存パッケージ準備と、実際の初回/再利用DAG実行は未実施。実行成功や処理時間短縮を実測済みとは記載しない。今後のClaude Code作業で、入力22行のカウント一致・初回の計算・2回目のキャッシュ再利用・1行変更時の部分再計算・破損キャッシュの拒否を必ず検査する。

数学IRと市場調査統計をフル統合するには、次に**個票データ→集計モデル→正式な統計IR→各エンジンの有効な入力**への橋渡しが必要。既存`Math IR 0.1`が未対応の中央値/階層ベイズ等を、既に実装済みかのように扱わない。
