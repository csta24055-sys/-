# cross_company/（会社別研究の上に載る派生レイヤー）

- `relations.jsonl`：会社間エッジ。各行は `company_a`・`company_b` と、**双方の会社台帳の** passage ID（`evidence_a`・`evidence_b`）を必ず持つ。
- 会社別の正本（`companies/*/`）を上書きしない。片方の会社の資料でしか確認できない関係は、その会社の `ledger/relations.jsonl` に置き、ここには載せない。
- 現状：**NOT_STARTED**（検証済みの会社間エッジは0件。三井物産以外の7社は研究が未着手）。
