# 再開手順（台帳から自動生成）

RESEARCH_STATUS = INCOMPLETE（最初に未達の工程：S1）

## いまの状態

- 最後に記録された処理の時刻（UTC）：2026-11-15T15:48:12Z
- テーマ：S1完了 87 / 325、未完了 238
- 旧検索候補：実行済み 336、実行不能 0、未実行 560（計 896）
- 競合候補：S1完了 21 / 80、未完了 59
- 追加仮説のテーマ：S1完了 0 / 7
- 作業員が実際に実行できたWeb検索：844 件。上限超過で拒否された検索：214 件（実行済みに数えていない）
- 採用資料：919（S2精査済み 0）
- 別チャットの1,000候補（`registry/chat1000_candidate_review.csv`、1009行）：NOT_READ 659、READ_NOT_YET_ASSESSED 116、IN_LEDGER_QUOTE_VERIFIED_FOR_TOPIC 74、BLOCKED_FETCH 54、REJECT_OFF_TOPIC 41、IN_LEDGER_OTHER_TOPIC 24、DUPLICATE_ORIGIN 14、HOLD_QUOTE_NOT_ACCEPTED 13、HOLD_NOT_ORIGINAL 5、HOLD_VENDOR_PROMOTION 5、REJECT_NOT_A_SOURCE 4
  - 作業員が実際に開いて判定した候補：164（`registry/candidate_assessments.csv`）。URL候補は証拠ではなく、引用照合を通ったものだけが台帳に入る。

## 未完了のID（先頭）

- テーマ：AXIS_01_T01、AXIS_01_T02、AXIS_01_T03、AXIS_01_T04、AXIS_01_T05、AXIS_01_T06、AXIS_01_T07、AXIS_01_T08、AXIS_03_T01、AXIS_03_T02、AXIS_03_T03、AXIS_03_T04、AXIS_03_T05、AXIS_03_T06、AXIS_03_T07、AXIS_03_T08、AXIS_05_T02、AXIS_05_T03、AXIS_05_T04、AXIS_05_T05、AXIS_05_T06、AXIS_05_T07、AXIS_05_T08、AXIS_06_T01、AXIS_06_T02、AXIS_06_T03、AXIS_06_T04、AXIS_06_T05、AXIS_06_T06、AXIS_06_T07、AXIS_06_T08、AXIS_13_T06、AXIS_13_T07、AXIS_13_T08、AXIS_14_T01、AXIS_14_T02、AXIS_14_T03、AXIS_14_T04、AXIS_14_T05、AXIS_14_T06 ほか198件
- 追加テーマ：ADD_N01_T01、ADD_N01_T02、ADD_N01_T03、ADD_N01_T04、ADD_N02_T01、ADD_N03_T01、ADD_SPD_T01
- 競合：C010、C012、C013、C014、C015、C017、C018、C019、C020、C021、C022、C024、C025、C029、C030、C032、C033、C035、C037、C038、C039、C040、C041、C042、C045、C046、C047、C048、C049、C050、C052、C053、C054、C055、C056、C057、C058、C059、C060、C061 ほか19件
- 全件は `registry/topic_execution_status.csv`、`registry/query_execution_status.csv`、`registry/competitor_execution_status.csv` の `gate_state`・`blockers` 列。

## 未達のゲート

- S1 FAIL、S2 FAIL、S3 FAIL、S4 FAIL、S5 FAIL、S6 FAIL、S7 FAIL、S8 FAIL、S9 FAIL
- 詳細は `research/GATE_AUDIT_DETAIL.md`。

## 制約

- Web検索は1ターンあたり200回が上限で、全作業員で共有される。超過分は実行されず、拒否として記録される（実行済みには数えない）。このため収集は、1ターン200回以内の束（バッチ）に分けて進める。
- 取得を拒否するサイトは迂回しない。検索上限の回避（他の手段での検索）もしない。
- 作業員の実行は、実行記録（transcript）から導いた `registry/execution_manifest.csv` に同じ呼び出しがある場合だけ数える。

## 再開コマンド

```
# 1) 作業員の実行記録と出力を台帳へ取り込む（STAGING・CACHE・実行記録の場所は環境に合わせる）
scripts/refresh.sh "$STAGING" "$CACHE" "$TRANSCRIPTS"
# 2) ゲート評価と監査詳細の更新
python3 scripts/research_gates.py evaluate && python3 scripts/build_resume.py
# 1b) 別チャットの1,000候補の状態と S1 不足一覧を再生成
python3 scripts/import_chat1000.py --cache "$CACHE" && python3 scripts/build_chat1000_docs.py
# 3) 次の束を計画する（検索195回以内、未完了の単位を優先順に、未判定のチャット候補も割当て）
python3 scripts/next_batch.py "$TASKS" "$STAGING" 195 8 "$INFLIGHT" B0n
#    読了だけの束（検索なし。S1完了済みの単位に割り当てられた候補も含む）
python3 scripts/next_batch.py "$TASKS" "$STAGING" 0 4 "$INFLIGHT" R0n --chat-only 16
# 4) 出力された単位を作業員に割り当てて実行し、1) に戻る
```

S1が通過するまで、S2以降の文書と正式成果物は作らない。
