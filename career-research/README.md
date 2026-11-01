# career-research — 建築環境・設備系学部生のキャリア選択肢研究（公開版）

研究基準日：2026年11月1日／第1版

建築学科の環境・設備系を専攻する学部生が到達し得る企業・職種・公務・進学・独立の選択肢を体系化し、多軸で比較するための公開資料と分析プログラムである。個人に固有の情報（氏名・成績・選考状況・価値観の分析）は含まない。個人用の研究は非公開の保存先で管理している。

## 構成

| パス | 内容 |
|---|---|
| `docs/第2・3巻_全産業職業調査と比較研究（公開版）.md` | 本文（Markdown） |
| `dist/` | 閲覧用PDF・編集用Word |
| `data/options_catalog.csv` | 34の選択肢（採用法人・職種・給与の根拠・採用規模・選考の特徴・9軸の評価） |
| `data/sources.csv` | 出典台帳（取得日・発行日・URL・信頼性・使用箇所） |
| `data/model_public/` | 公開版モデルの出力（評価体系別順位・パレート集合・感度分析） |
| `tools/strategy_model.py` | 多軸評価・パレート分析・感度分析・ルート期待値の再現可能なモデル |
| `tools/make_figures.py` | 図表の生成 |
| `tools/build_docs.sh` | Markdown→PDF（目次・ページ番号）・Word |

## 再現手順

```bash
cd career-research
python3 tools/strategy_model.py --catalog data/options_catalog.csv --out data/model_public
python3 tools/make_figures.py data/model_public data/options_catalog.csv figures
tools/build_docs.sh docs dist
```

個人用の重なり（適合・到達可能性・失敗時の損失）とルート表は `--overlay`・`--routes` で別途与える。これらは公開リポジトリに置かない。

## 注意

評価点（1〜5）は分析者の判断であり、採用確率ではない。未確認の数値は「未確認」と表記した。
