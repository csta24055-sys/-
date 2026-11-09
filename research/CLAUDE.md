# Claude Code 作業規則（research/）

1. 会社最上位。作業は必ず `companies/{会社}/` の中で行い、他社の台帳IDを引用しない。
2. セッション開始時：`python3 research/research_gates.py` → 対象会社の `NEXT_STEPS.md` を読み、そこに書かれた次の問いから再開する。
3. 一次資料を取得したら、`ledger/sources.jsonl`（sha256・公開日・取得日時・origin_group_id）、`ledger/passages.jsonl`（ページ・段落位置と最小限の抜粋）、`ledger/search_log.jsonl`（クエリ・件数・採否）に必ず記録する。原文の全文はコミットしない。
4. 主張は `axes/AXIS_XX/CLAIMS.jsonl` に FACT / PARTY_CLAIM / ANALYSIS / HYPOTHESIS / FORECAST / UNKNOWN を区別して書く。台帳は追記型で、既存の主張は消さず、改訂は `claim_status_events.jsonl` に残す。
5. 公開日が2026-11-01より後の資料は `snapshot: monthly_YYYY-MM` として別に扱う。
6. `TOPIC_STATUS.csv` の declared_state を PASS にするのは、ゲートの computed が PASS になってから。
7. 作業の最後に `research/run_all.sh` を実行し、テストがすべて通ってからコミットする。
