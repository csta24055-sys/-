# Claude Code 実行指示：市場調査の統計解析を7エンジン統合基盤へ選択的に接続

適用先：`csta24055-sys/-` の `claude/new-session-qm9g7r`。**このブランチの研究用コードに限る。main、アプリ、UI、デプロイ、課金、認証は変更しない。**

1. `research/MARKET_EVIDENCE_INDEX_20261113.json` と `research/MATH_ROUTER_CATALOG_PREVIEW_20261113.json` の実在を確認する（後者の正しい名前は`MATH_ROUTER_CATALOG_PREVIEW_20261113.json`）。その後 `research/MATH_ENGINE_ROUTING_FOR_CLAUDE.md` を全文読む。
2. 既存の `registry/quant_results.csv` は元の個票ではない。必ず`S1未通過・S2未検証`の扱いを維持し、独立の観測データがないところで中央値・平均・Bayes結果・勝率・市場規模を生成しない。
3. 研究ルートで `python3 scripts/market_stat_router.py registry/quant_results.csv --output research/stat_routing.json` を実行し、22件が欠落せず分類されたか検証。`python3 -m unittest discover -s tests -p test_market_stat_router.py -v` を実行し、ユニットテスト全PASSを確認。失敗したら報告し、中間の完了を宣言しない。
4. 前回の`external_handoff/`中の32軸・325テーマ、896検索、80競合、追加7テーマのID別記録と出典を正本へ取り込む前に重複・実行証跡・独立性を照合する。検索済みと原文確認を区別し、データ未入手を零値にしない。
5. 数値計算の必要性を独立に判定。出典起源と母集団/単位/期間ごとに層別し、観測済みの生データがある場合だけ平均・中央値・分散・分位点等を計算。割合は分子/分母/観測単位を照合。ベイズは尤度・事前分布・個票または正しいカウント・感度検査が揃った場合のみ。形式的な算術は厳密に計算しても、モデル仮定と実証データの区別を外さない。
6. `main` の既存7エンジン実体 `math_interop_v0/phase4.py`・`phase5.py` と `math_tools_v2/portable.py`・`lca_ops.py` を`git show origin/main:...`で確認。**このブランチに数学基盤ファイルはない。**
7. コアを一時的な別ワークツリーに読み取り専用で展開し、依存環境を用意して`scripts/market_math_dag_adapter.py`を起動。**最初はDuckDBと既存DAGキャッシュだけ**を実行し、再実行でハッシュ一致/再利用を検証する。`portable-python`と`portable-full`は既存Math IR 0.1で扱える厳密算術の実検算が必要な場合だけ。7種類すべてを一律に起動しない。
8. 変更した入力1件だけが依存関係に沿って再計算されるか、壊れたキャッシュが拒否されるかを試験する。時間/メモリ/料金/Actionsストレージは比較前後の実測値を記録し、節減率を憶測で報告しない。公開リポジトリに機密・個票・ページ全文を保存しない。
9. **今回のゴールは1-A〜1-Dまでの全対象の研究証拠と解析実行可能性**の整理であり、S1 FAIL中に正式な分析結論/製品推奨/最終報告を出さない。追加7テーマや長文の原資料を無視しない。未解決なテーマや計算は`NON_IDENTIFIABLE`, `BLOCKED_DATA`, `REJECTED_INVALID_METHOD` 等でID別に残す。
10. 終了時に必ず、分析対象ID数、数値演算の成功・未識別・棄却別件数、原文出典独立性、実行したエンジン、キャッシュ再利用率、入力/出力バイト数、実測処理時間、失敗テスト、次回の再開コマンドを研究用引継ぎ文書へ記録。**完成していなければINCOMPLETEを維持**。

実装済み: 研究専用統計分類ルーター、回帰/故障注入用ユニットテスト、既存Math IR DAGをimportする接続器、全IDを保持する小型進捗索引、文書化した計算方法判定。
未完了: 7エンジンで市場データを実際に独立再計算する統合テスト、全325テーマの調査・数学解析、S1通過、S2〜S9。
