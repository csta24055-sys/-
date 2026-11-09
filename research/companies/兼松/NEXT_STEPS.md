# 兼松：次回再開手順（NEXT_STEPS）

1. `python3 research/research_gates.py --company COMPANY_08` で現状のゲートを確認する。
2. 優先順位：P1テーマのうち AXIS_13（銀行・政策金融）/AXIS_14（財務）/AXIS_20（所有ネットワーク）から着手し、
   `axes/AXIS_XX/QUESTIONS.jsonl` のROOT問い `Q-C08-AXX-TYY-00` を原子的な問いに分割する。
3. 一次資料（有価証券報告書・統合報告書・決算短信・JBIC/NEXI等）を取得し、`ledger/sources.jsonl` に
   sha256・取得日時・公開日を記録、`ledger/passages.jsonl` にページ位置を記録する。
4. `ledger/search_log.jsonl` に検索クエリ・結果件数・採否理由を必ず追記する。
5. 基準日 2026-11-01 より後に公開された資料は `snapshot` を `monthly_YYYY-MM` として別扱いにする。
6. 他社フォルダの主張・出典IDを引用しない（ゲートがFAILになる）。
