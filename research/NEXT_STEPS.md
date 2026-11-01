# NEXT_STEPS — 次に実行する研究

## 再開手順
1. `research/RESEARCH_PROGRESS.md` → `FINDINGS.md` → `HYPOTHESES.md` → `10_未解決論点・追加調査/` の順に読む。
2. 原資料は `python3 tools/fetch_source.py --refetch` で再取得する（S053だけは `node tools/fetch_tepco_job_details.js "26-建築-1" ...` で取得）。
3. 有報の要所は `python3 tools/extract_yuho.py S0xx` → `python3 tools/compact_extract.py S0xx` で抽出する。
4. 新しい資料のIDは S054 以降。文書の改訂時は版番号と改訂の内容を冒頭に記す。`bash tools/build_docs.sh` で `dist/` を再生成する。

## 優先順（第3セッション）
1. Q-T08／Q-T09：需要減の要因分解と、JERAの中間期の開示（JERAのIR、TDnetには掲載されないため公式サイトで）。
2. Q-C02：浜岡の調査報告書の原文（中部電力のサイト）。組織的な要因の認定を04章に反映する。
3. Q-B07／Q-B06：原子力・PG・EPの求人詳細と子会社の人員。11章の職能表の確度を上げる。
4. Q-C05：EDINETの原本PDFから各社の役員の経歴を抽出し、「経営者の経歴と戦略」の検証を行う。
5. Q-T10：特重の起算点の変更の審議過程。
6. 世界の比較（米国の原子力・ガス・データセンター需要、欧州の市場設計、中国の供給網）を独立の章として新設する（第2版では未着手）。
