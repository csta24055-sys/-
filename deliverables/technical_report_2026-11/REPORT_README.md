# 室内空気質・空気清浄度 既存研究の統合的分析（中間統合技術調査報告書 2026-11）

井口研究室（住宅班）関連資料を対象とした自主調査。研究室の公式見解ではない。版 1.0（2026-11-04）。

## 成果物

| ファイル | 内容 |
|---|---|
| AQ_Research_Integrated_Technical_Report_2026-11.docx | 正式報告書（Word, 編集可能。目次・図表番号・ページ番号・数式） |
| AQ_Research_Integrated_Technical_Report_2026-11.pdf | 閲覧用 PDF（Word 版を LibreOffice で出力, 97 ページ） |
| AQ_Research_Integrated_Technical_Report_2026-11.md | 本文の Markdown（生成元） |
| SOURCE_INVENTORY.csv | 研究資料台帳（研究室資料・外部文献・未取得資料, 根拠区分 A〜G） |
| EVIDENCE_LEDGER.csv | 根拠・主張対応表（Claim ID, 区分 FACT/CALC/ANALYSIS/HYPOTHESIS/UNRESOLVED/NOT VERIFIED） |
| NUMERICAL_AUDIT.csv | 数値検証結果（96 項目: 原資料値・再計算値・差・判定） |
| UNRESOLVED_ISSUES.md | 未解決問題・数値の不一致・仮説・未取得資料 |
| REFERENCES.md | 参考文献・出典（性格別） |
| REPORT_QA.md | 品質監査の結果 |
| figures/ | 本文の図（PNG, 本報告書で作成） |

## 再生成

```bash
.venv/bin/python scripts/build_knowledge.py
.venv/bin/python scripts/build_tech_report.py   # docx・pdf（LibreOffice と libreoffice-math が必要）
```

本文の分析テキストは `scripts/tech_report_text.py`、表・台帳は `knowledge/knowledge.json`・`scripts/audit_data.py`・`verification/` から自動生成する。

## 読み方

1. 要旨・主要な結論（Claim ID 付き）→ 2. 第18章（再計算）・第19章（未解決）→ 3. 年度別の第7〜12章。
数値の根拠は Claim ID で EVIDENCE_LEDGER.csv、計算 ID で NUMERICAL_AUDIT.csv をたどる。

## 変更履歴

- 1.0（2026-11-04）初版。2026年11月時点の取得済み資料に基づく中間統合版。
