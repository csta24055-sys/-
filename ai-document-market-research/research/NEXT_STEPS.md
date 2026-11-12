# 再開手順（台帳から自動生成）

RESEARCH_STATUS = INCOMPLETE（最初に未達の工程：S1）

## いまの状態

- 最後に記録された処理の時刻（UTC）：2026-11-12T14:39:50.187Z
- テーマ：S1完了 16 / 325、未完了 309
- 旧検索候補：実行済み 48、実行不能 0、未実行 848（計 896）
- 競合候補：S1完了 4 / 80、未完了 76
- 追加仮説のテーマ：S1完了 0 / 7
- 作業員が実際に実行できたWeb検索：200 件。上限超過で拒否された検索：211 件（実行済みに数えていない）
- 採用資料：152（S2精査済み 0）

## 未完了のID（先頭）

- テーマ：AXIS_01_T01、AXIS_01_T02、AXIS_01_T03、AXIS_01_T04、AXIS_01_T05、AXIS_01_T06、AXIS_01_T07、AXIS_01_T08、AXIS_03_T01、AXIS_03_T02、AXIS_03_T03、AXIS_03_T04、AXIS_03_T05、AXIS_03_T06、AXIS_03_T07、AXIS_03_T08、AXIS_04_T03、AXIS_04_T04、AXIS_04_T05、AXIS_04_T06、AXIS_04_T07、AXIS_04_T08、AXIS_05_T02、AXIS_05_T03、AXIS_05_T04、AXIS_05_T05、AXIS_05_T06、AXIS_05_T07、AXIS_05_T08、AXIS_06_T01、AXIS_06_T02、AXIS_06_T03、AXIS_06_T04、AXIS_06_T05、AXIS_06_T06、AXIS_06_T07、AXIS_06_T08、AXIS_07_T01、AXIS_07_T02、AXIS_07_T03 ほか269件
- 追加テーマ：ADD_N01_T01、ADD_N01_T02、ADD_N01_T03、ADD_N01_T04、ADD_N02_T01、ADD_N03_T01、ADD_SPD_T01
- 競合：C005、C006、C007、C008、C009、C010、C011、C012、C013、C014、C015、C016、C017、C018、C019、C020、C021、C022、C023、C024、C025、C026、C027、C028、C029、C030、C031、C032、C033、C034、C035、C036、C037、C038、C039、C040、C041、C042、C043、C044 ほか36件
- 全件は `registry/topic_execution_status.csv`、`registry/query_execution_status.csv`、`registry/competitor_execution_status.csv` の `gate_state`・`blockers` 列。

## 未達のゲート

- S1 FAIL、S2 FAIL、S3 FAIL、S4 FAIL、S5 FAIL、S6 FAIL、S7 FAIL、S8 FAIL、S9 FAIL
- 詳細は `research/GATE_AUDIT_DETAIL.md`。

## 制約

- Web検索は1ターンあたり200回が上限で、全作業員で共有される。超過分は実行されず、拒否として記録される（実行済みには数えない）。このため収集は、1ターン200回以内の束（バッチ）に分けて進める。
- 取得を拒否するサイトは迂回しない。検索上限の回避（他の手段での検索）もしない。

## 再開コマンド

```
# 1) 作業員の実行記録と出力を台帳へ取り込む（STAGING・CACHE・実行記録の場所は環境に合わせる）
scripts/refresh.sh "$STAGING" "$CACHE" "$TRANSCRIPTS"
# 2) ゲート評価と監査詳細の更新
python3 scripts/research_gates.py evaluate && python3 scripts/build_resume.py
# 3) 次の束を計画する（検索200回以内、未完了の単位を優先順に）
python3 scripts/next_batch.py "$TASKS" "$STAGING" 200 5
# 4) 出力された単位を作業員に割り当てて実行し、1) に戻る
```

S1が通過するまで、S2以降の文書と正式成果物は作らない。
