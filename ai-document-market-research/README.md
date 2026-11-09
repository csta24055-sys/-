# AI資料作成アプリの市場・利用者・競合研究（研究のみ・実装なし）

学校・研究用と仕事用のAI資料作成アプリについて、何を、誰に、どの操作と接続条件で提供すべきかを、出典を追跡できる証拠から判断するための研究フォルダ。**アプリ本体、画面コード、API連携、デプロイ設定は含まない。**

## 最初に読むもの

1. `deliverables/FINAL_RESEARCH_REPORT.md` — 結論と根拠、限界（冒頭に暫定度を明記）
2. `deliverables/DECISION_AND_OPEN_RISKS.md` — 決定10項目と、結論が覆る条件
3. `research/RESEARCH_PROGRESS.md` — 工程ごとの実施状況と未達範囲

## 構成

| 場所 | 内容 |
|---|---|
| `deliverables/` | 最終報告、機能優先度、ボタン操作仕様（文章）、外部接続方針（文章）、決定と未解決リスク |
| `research/` | 監査記録、要件マトリックス、収集範囲の監査、出典依存性、矛盾、セグメント、競合比較、定量、製品案、意思決定、最終QA |
| `registry/` | 研究軸325テーマ、調査計画、競合候補80件、**実行した**検索・アクセスのログ、原文確認した証拠の台帳、定量結果、製品に関する主張 |
| `scripts/` | ゲート検査、範囲監査、台帳追記、原文取得、定量再計算（研究用のみ） |
| `tests/` | 架空の調査を完了扱いにしないための否定テストと、台帳の整合性テスト |
| `templates/`, `original_20261109/` | 依頼者パッケージ由来の出力ひな形と旧版台帳（範囲監査の比較対象） |

## 再現

```
python3 scripts/scope_audit.py                 # 範囲の構造監査（参考画像8枚が必要）
python3 -m unittest discover -s tests -v       # 否定テストと台帳整合性
python3 scripts/research_gates.py check        # 工程ゲートの機械検査
python3 scripts/ledger.py stats                # 台帳の現状
python3 scripts/quant_recompute.py             # 定量結果の再計算
```

## Gitに含めていないもの

このリポジトリは公開のため、依頼者の参考画像8枚、取得した外部ページ本文、指令書の原文は保存していない（`research/REPO_AUDIT.md` §4）。指令の要約は `research/DIRECTIVE_DIGEST.md`。

## 読み方の注意

- 台帳の「採用」は、原文を開いて該当箇所を確認したという意味であり、内容の真偽を保証しない。企業の公式ページは当事者の表明である。
- 機械ゲートのPASSは最低条件の充足であり、標本の代表性や統計的妥当性の証明ではない。
- 数字には `OBSERVED` / `MODEL_BASED` / `MIXED` / `ASSUMPTION_ONLY` / `NON_IDENTIFIABLE` の区分が付く。
