# ChatGPT調査・引継ぎ監査（2026-11-13）

RESEARCH_STATUS = **INCOMPLETE**
FIRST_UNMET_GATE = **S1**
DOCUMENT_TYPE = EXECUTION_AND_EVIDENCE_HANDOFF（正式な最終報告ではない）
SOURCE_REPOSITORY = `csta24055-sys/-`
SOURCE_BRANCH = `claude/new-session-qm9g7r`
APP_CODE_CHANGED = NO

## 第1群：旧896検索候補全件の検索リクエスト

前回の`research/NEXT_STEPS.md`には「48件実行」と残っているが、2026-11-13にGitHubの現行 `registry/query_execution_status.csv` を直接読み、896行の内訳を **EXECUTED 151 / NOT_EXECUTED 745** と確認。再開手順書は古い可能性があり、正本ファイルそのものを優先した。

ChatGPTは、正本で `NOT_EXECUTED` の745 IDすべてに、各CSVの `query_verbatim` を一度ずつWeb検索リクエストとして投入した。

- バッチ01〜11の各64検索＝704件、バッチ12＝41件、合計745件。各バッチは当該IDの原文検索語を保持するCSVとして`external_handoff/`以下に保存。
- GitHubに保存した21 CSVを再取得し、正本の `NOT_EXECUTED` 745 IDを**順序まで含めて全件突合**した結果、745/745件が完全一致。重複、欠落、正本の既EXECUTED IDとの交差はなし。
- したがって**検索リクエストを送信した記録としては151＋745＝896/896件**。検索結果の件数、各検索の時刻、検索語ごとの原文資料の取得成否は一括検索ツールが返す粒度のため全件について確定しておらず、正本ゲートで未監査。指定検索結果の「全文を読んだ」「証拠が得られた」「325テーマが完了」とは解釈しない。
- 上記CSVの新規745件には検索実行日 `2026-11-13` と検索文、ID、経路を記録。秒単位の個別検索時刻は記録できなかったため、後から捏造しないこと。
- 正本`registry/query_execution_status.csv`、`registry/search_log.csv`、`research/gate_evaluation.json`は**未変更**。本ファイルがあるからといって機械的にS1 PASSにしないこと。

## 第2群：競合80候補の個別調査

GitHub現行`registry/competitor_execution_status.csv`を直接確認：**S1_DONE 12/80、S1_INCOMPLETE 68/80**。再開手順書に記載の4/80は古い。
S1未完了68件すべてに対し、各社の固有名詞を入れた公式サイト・価格・機能探索Web検索を実行。`competitors_discovery_batch01_17.csv`〜`batch04_17.csv`の4ファイルに68候補の検索式とIDを記録。
**この段階は候補の探索であり、68件のS1競合監査完了を意味しない。** 全社の入出力、料金、データ条件、編集可能性、実機比較等は依然として未確認が残る。正本競合台帳は改変していない。

公式原文を別途開いて確認した新候補（`chatgpt_20261113_vendor_official_candidates.csv`）：
- C009 Plus AI：公式料金・Google Slides / PowerPoint連携（https://plusai.com/pricing）
- C034 WPS AI Presentation：文書起点のスライド生成・PPTX対応（https://www.wps.com/office/presentation/）
- C041 Foxit PDF AI：文書処理・ローカルAI・ワークスペースの公式製品説明（https://www.foxit.com/ai/pricing/）
各社の生成品質・速度・PPTX崩れは実機未測定であり、事業者の機能表明として区別する。
既存URLと一致する他社公式資料（Beautiful.ai、Claude、Alai、PageOn.ai、think-cell等）は原則二重登録しない。

## 第3群：原文確認できた追加資料と限界

S1の**新しい一次ページ候補16件**を4つのCSVへ保存した。S2検証済みとして正本へ自動昇格しない：
- batch01：5件（Microsoftの文書作成仕様、大学の生成AI指針整備調査、IPSJ、学会研究の抄録、企業の資料作成アンケート）
- batch02：2件（京都大学、滋賀県立大学の公式AI利用規則）
- batch03：2件（Microsoft旧Word→PPT機能の廃止、IPAのAI説明責任調査）
- batch10_to12：4件（IPA営業秘密管理調査、JIPDEC/ITR企業IT調査、エイトレッドのバックオフィス調査、東京大学の2023年暫定AI利用指針）
- vendor_official：3件（Plus AI、WPS AI、Foxit AI）

独立起源・重複・出版日・母集団をS2で再確認すること。既存 `registry/source_evidence.csv` の全464行は`review_state=S2_PENDING`であり、この16件は正本へ未統合。

## 計算・検証の実施例（S1付帯。S5完了の代替ではない）

- 大学の指針調査：`113 / 1165 × 100 = 9.69957…%` → 小数第1位で **9.7%**。原著の表示「9.8%」と0.1ポイントずれるため`REVIEW_REQUIRED`。原著の分母定義と丸め方を再確認せず勝手に改変しない。
- 同じ調査の `45.1 + 23.0 = 68.1` ポイント（調査回答機関における策定済みと策定中の合計）。全国の大学の割合には外挿しない。
- エイトレッドの回答者 n=110。業務生成AI利用者 n=84 とすれば `84/110×100=76.3636…%` →公表76.4%と整合。
- 同じ n=84 の利用者のうち「質問の仕方が難しい」公表66.7%は、`56/84=66.666…%`に整合。「検証に時間がかかる」48.8%は`41/84=48.8095…%`に整合。56人・41人は**公表百分率から逆算した整合的な度数候補**であり、個票の度数として確認したわけではない。
- JIPDEC/ITR調査はパネル n=1107（企業規模・職責限定）。「積極的なAI活用36%」の概数から、正確な人数 `1107×.36=398.52` を**観測済み度数として丸めない**。
- `REJECTED_INVALID_METHOD`の例：異なる母集団の調査値を加算して全国の導入率と呼ぶこと、別製品の価格を実支払意思額と呼ぶこと、競合の一点生成テストを普遍的品質差と呼ぶこと。
- 本研究の製品に関する継続率・広告効果・買収確率は、観測データがなく`NON_IDENTIFIABLE`のまま。

## 現行正本の進捗（S1ゲートは未通過）

| 指標 | GitHub現行正本 | ChatGPT外部引き継ぎ（今回） |
|---|---:|---:|
| 全32軸／325テーマ | 39件S1_DONE / 286件未完了 | 新規テーマの正式PASSなし |
| 旧896検索候補 | 151件EXECUTED / 745件NOT_EXECUTED | 未実行745件のリクエストを送信、ID完全照合 |
| 80競合候補 | 12件S1_DONE / 68件未完了 | 未完了68件すべての公式サイト探索リクエスト送信 |
| 採用証拠台帳 | 464件（全件S2_PENDING） | 新規原文確認候補16件（未統合） |
| 全計算・S2以降 | 完了確認なし | 一部の原資料数値を検算、正式な全計算なし |

上記の手続だけでは**S1 PASSにならない**。テーマ別一次資料・独立資料・反証・取得不能の理由、競合属性、全計算ID、原文と引用箇所、独立起源を指定手順で監査する必要がある。成果物5件はPROVISIONALのまま。

## 次の取り込み順序

1. `external_handoff/`内の実行ログ（21 CSV）と新たな原文候補（5 CSV）を正本のID・URLと重複照合する。
2. ツールが返さなかった検索時刻・結果数は`UNKNOWN`のまま残し、観測済みの値を後から作らない。
3. 正本CSVへ安全に統合できる項目だけを追加し、`scripts/sync_registry.py`、`scripts/build_tables.py`、`scripts/research_gates.py` 等の既存スクリプトで再計算・矛盾検査を行う。
4. 325テーマのうち286件、80競合のうち68件について、個別の原文確認・独立性・反証・演算適用可能性を1件ずつ確認する。必要な数値がなければ`NON_IDENTIFIABLE`または`BLOCKED_DATA`と記録。
5. S1 FAIL中にS2〜S9の正式報告へ進まず、研究再開可能な中間記録だけを残す。

**これは途中経過の事実記録であり、ユーザー指定の325テーマ・80競合・全計算・正式最終報告が終わったという意味ではない。**
