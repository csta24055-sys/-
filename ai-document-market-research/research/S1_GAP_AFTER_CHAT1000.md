# S1不足一覧（チャット1,000候補の取込み後・機械生成）

生成時刻（UTC）：2026-11-15T16:13Z　／　生成：`python3 scripts/build_chat1000_docs.py`（`scripts/build_status.py` の再計算結果から）

> RESEARCH_STATUS = INCOMPLETE。S1未通過のためS2以降の分析・正式成果物には進まない。

## 1. 集計（再計算値）

| 対象 | S1完了 | 未完 | 備考 |
|---|---:|---:|---|
| 325テーマ | 125 | 200 | 2026-11-12の過去監査値（16/325）は古い。本値は現台帳からの再計算 |
| 追加7テーマ（ZIP外） | 0 | 7 | N01〜N03・速度 |
| 旧896検索ID | 実行 408 | 未実行 488 | 実行不能確定 0。ログの再索引だけでは実行にしない |
| 80競合 | 32 | 48 | 公式資料の確認 55 社 |

## 2. 不足の種類と数

### テーマ（325＋追加7）

| 不足の種類 | テーマ数 |
|---|---:|
| 研究ユニット記録（定義・計算/識別不能）が未完 | 203 |
| 一次資料ルートの検索なし | 182 |
| 独立資料が未確定（NO） | 165 |
| 反証資料が未確定（NO） | 165 |
| 旧検索IDの未実行が残る | 122 |
| 一次資料が未確定（NO） | 109 |
| 独立資料が未確定（ATTEMPTED_INSUFFICIENT） | 38 |
| 反証資料が未確定（ATTEMPTED_INSUFFICIENT） | 38 |
| 一次資料が未確定（ATTEMPTED_INSUFFICIENT） | 8 |

- 必要な検索操作の下限（見積り式：未実行の旧検索ID数 ＋ 未確定ルートごとに『独自クエリ2本』に足りない本数）：**1534** 回。1ターンの検索上限（全作業員共有で200回）に対し、約9ターン分。
- 必要なページ読了：未判定のチャット候補の割当て 880 件（重複を除くURL 674 件）。読了は検索上限を消費しない。
- 462件（旧予定タスクの未達数）は採用証拠の必要件数ではない。上の不足（ルート・旧ID・競合項目）を満たす分だけ新規に調査し、必要ならそれ以上集める。

### 競合（80）

| 不足の種類 | 社数 |
|---|---:|
| no counter / independent search with results and no third-party-backed counter finding | 48 |
| attributes not recorded | 25 |
| no vendor page read | 18 |

## 3. テーマ別の未達（全件）

凡例：一次/独立/反証＝FOUND・NOT_FOUND_AFTER_SEARCH・ATTEMPTED_INSUFFICIENT・NO。独自＝作業員が設計した検索の本数（旧検索IDは含めない）。チャット候補＝未判定の割当て件数／申告テーマで照合済み件数。

| テーマ | 状態 | 未実行の旧検索ID | 一次 | 独立 | 反証 | 独自(一/独/反) | 読了 | ユニット | チャット候補 |
|---|---|---|---|---|---|---|---|---|---|
| AXIS_01_T01 | 未完 | Q1,Q2,Q3,Q4 | FOUND | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 1/1 | NO | 0/0 |
| AXIS_01_T02 | 未完 | Q1,Q2,Q3,Q4 | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_01_T03 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_01_T04 | 未完 | Q1,Q2,Q3,Q4 | FOUND | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 1/1 | NO | 0/0 |
| AXIS_01_T05 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_01_T06 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_01_T07 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_01_T08 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_02_T01 | 完了 | — | FOUND | FOUND | FOUND | 3/2/2 | 27/33 | YES | 12/6 |
| AXIS_02_T02 | 完了 | — | FOUND | FOUND | FOUND | 2/2/2 | 3/5 | YES | 16/1 |
| AXIS_02_T03 | 完了 | — | FOUND | FOUND | FOUND | 3/2/2 | 15/18 | YES | 16/5 |
| AXIS_02_T04 | 完了 | — | FOUND | FOUND | FOUND | 4/2/2 | 18/20 | YES | 18/4 |
| AXIS_02_T05 | 完了 | — | FOUND | FOUND | FOUND | 3/1/1 | 16/17 | YES | 13/3 |
| AXIS_02_T06 | 完了 | — | FOUND | FOUND | FOUND | 2/2/2 | 17/18 | YES | 17/5 |
| AXIS_02_T07 | 完了 | — | FOUND | FOUND | FOUND | 4/2/2 | 16/19 | YES | 17/5 |
| AXIS_02_T08 | 完了 | — | FOUND | FOUND | FOUND | 4/1/2 | 16/18 | YES | 21/3 |
| AXIS_03_T01 | 未完 | Q1,Q2,Q3,Q4 | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 1/0 |
| AXIS_03_T02 | 未完 | Q1,Q2,Q3,Q4 | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_03_T03 | 未完 | Q1,Q2,Q3,Q4 | FOUND | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 1/1 | NO | 0/0 |
| AXIS_03_T04 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_03_T05 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 2/0 |
| AXIS_03_T06 | 未完 | Q1,Q2,Q3,Q4 | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_03_T07 | 未完 | Q1,Q2,Q3,Q4 | FOUND | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 1/1 | NO | 3/0 |
| AXIS_03_T08 | 未完 | Q1,Q2,Q3,Q4 | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_04_T01 | 完了 | — | FOUND | FOUND | FOUND | 2/2/2 | 12/19 | YES | 15/3 |
| AXIS_04_T02 | 完了 | — | FOUND | FOUND | FOUND | 4/2/2 | 14/17 | YES | 14/6 |
| AXIS_04_T03 | 完了 | — | FOUND | FOUND | FOUND | 1/1/1 | 7/11 | YES | 18/0 |
| AXIS_04_T04 | 完了 | — | FOUND | FOUND | FOUND | 3/1/1 | 37/41 | YES | 15/4 |
| AXIS_04_T05 | 完了 | — | FOUND | FOUND | FOUND | 1/1/1 | 8/13 | YES | 10/0 |
| AXIS_04_T06 | 完了 | — | FOUND | FOUND | FOUND | 2/1/2 | 12/16 | YES | 19/0 |
| AXIS_04_T07 | 完了 | — | FOUND | FOUND | FOUND | 1/1/1 | 24/26 | YES | 10/4 |
| AXIS_04_T08 | 完了 | — | FOUND | FOUND | FOUND | 0/1/1 | 22/25 | YES | 14/6 |
| AXIS_05_T01 | 完了 | — | FOUND | FOUND | FOUND | 2/1/1 | 17/18 | YES | 12/4 |
| AXIS_05_T02 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_05_T03 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_05_T04 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_05_T05 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_05_T06 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_05_T07 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_05_T08 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_06_T01 | 未完 | Q1,Q2,Q3,Q4 | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_06_T02 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_06_T03 | 未完 | Q1,Q2,Q3,Q4 | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_06_T04 | 未完 | Q1,Q2,Q3,Q4 | FOUND | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 1/1 | NO | 0/0 |
| AXIS_06_T05 | 未完 | Q1,Q2,Q3,Q4 | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_06_T06 | 未完 | Q1,Q2,Q3,Q4 | FOUND | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 1/1 | NO | 0/0 |
| AXIS_06_T07 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 1/0 |
| AXIS_06_T08 | 未完 | Q1,Q2,Q3,Q4 | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 1/0 |
| AXIS_07_T01 | 完了 | — | FOUND | FOUND | FOUND | 1/1/1 | 6/8 | YES | 14/0 |
| AXIS_07_T02 | 完了 | — | FOUND | FOUND | FOUND | 3/1/1 | 27/32 | YES | 10/2 |
| AXIS_07_T03 | 完了 | — | FOUND | FOUND | FOUND | 0/2/1 | 25/28 | YES | 11/3 |
| AXIS_07_T04 | 完了 | — | FOUND | FOUND | FOUND | 2/2/1 | 26/28 | YES | 11/3 |
| AXIS_07_T05 | 完了 | — | FOUND | FOUND | FOUND | 1/1/1 | 9/11 | YES | 13/0 |
| AXIS_07_T06 | 完了 | — | FOUND | FOUND | FOUND | 1/2/1 | 7/7 | YES | 14/1 |
| AXIS_07_T07 | 完了 | — | FOUND | FOUND | FOUND | 1/3/1 | 7/10 | YES | 12/0 |
| AXIS_07_T08 | 完了 | — | FOUND | FOUND | FOUND | 1/1/1 | 5/5 | YES | 12/0 |
| AXIS_08_T01 | 完了 | — | FOUND | FOUND | FOUND | 1/2/1 | 20/32 | YES | 10/4 |
| AXIS_08_T02 | 完了 | — | FOUND | FOUND | FOUND | 3/1/1 | 9/11 | YES | 13/0 |
| AXIS_08_T03 | 完了 | — | FOUND | FOUND | FOUND | 0/1/1 | 6/9 | YES | 15/0 |
| AXIS_08_T04 | 完了 | — | FOUND | FOUND | FOUND | 2/2/1 | 7/7 | YES | 17/1 |
| AXIS_08_T05 | 完了 | — | FOUND | FOUND | FOUND | 2/1/1 | 24/29 | YES | 10/1 |
| AXIS_08_T06 | 完了 | — | FOUND | FOUND | FOUND | 1/1/1 | 5/8 | YES | 14/0 |
| AXIS_08_T07 | 完了 | — | FOUND | FOUND | FOUND | 1/1/1 | 5/6 | YES | 5/0 |
| AXIS_08_T08 | 完了 | — | FOUND | FOUND | FOUND | 1/1/1 | 5/6 | YES | 3/0 |
| AXIS_09_T01 | 完了 | — | FOUND | FOUND | FOUND | 0/1/1 | 8/8 | YES | 8/0 |
| AXIS_09_T02 | 完了 | — | FOUND | FOUND | FOUND | 1/1/2 | 9/10 | YES | 5/0 |
| AXIS_09_T03 | 完了 | — | FOUND | FOUND | FOUND | 1/1/2 | 7/7 | YES | 3/0 |
| AXIS_09_T04 | 完了 | — | FOUND | FOUND | FOUND | 0/2/2 | 7/9 | YES | 3/0 |
| AXIS_09_T05 | 完了 | — | FOUND | FOUND | FOUND | 0/1/1 | 6/6 | YES | 5/0 |
| AXIS_09_T06 | 完了 | — | FOUND | FOUND | FOUND | 0/1/1 | 5/5 | YES | 4/0 |
| AXIS_09_T07 | 完了 | — | FOUND | FOUND | FOUND | 1/1/1 | 5/8 | YES | 6/0 |
| AXIS_09_T08 | 完了 | — | FOUND | FOUND | FOUND | 1/2/2 | 12/13 | YES | 3/2 |
| AXIS_10_T01 | 完了 | — | FOUND | FOUND | FOUND | 1/1/1 | 5/6 | YES | 2/0 |
| AXIS_10_T02 | 完了 | — | FOUND | FOUND | FOUND | 2/1/1 | 6/9 | YES | 0/0 |
| AXIS_10_T03 | 完了 | — | FOUND | FOUND | FOUND | 1/1/1 | 4/5 | YES | 0/0 |
| AXIS_10_T04 | 完了 | — | FOUND | FOUND | FOUND | 0/2/2 | 6/6 | YES | 0/0 |
| AXIS_10_T05 | 完了 | — | FOUND | FOUND | FOUND | 2/1/1 | 6/6 | YES | 0/0 |
| AXIS_10_T06 | 完了 | — | FOUND | FOUND | FOUND | 1/1/1 | 5/5 | YES | 0/0 |
| AXIS_10_T07 | 完了 | — | FOUND | FOUND | FOUND | 2/2/1 | 5/6 | YES | 0/0 |
| AXIS_10_T08 | 完了 | — | FOUND | FOUND | FOUND | 0/2/1 | 5/5 | YES | 0/0 |
| AXIS_11_T01 | 完了 | — | FOUND | FOUND | FOUND | 0/2/1 | 10/12 | YES | 0/0 |
| AXIS_11_T02 | 完了 | — | FOUND | FOUND | FOUND | 0/2/2 | 9/10 | YES | 0/1 |
| AXIS_11_T03 | 完了 | — | FOUND | FOUND | FOUND | 1/1/1 | 9/10 | YES | 0/0 |
| AXIS_11_T04 | 完了 | — | FOUND | FOUND | FOUND | 2/1/1 | 10/12 | YES | 0/0 |
| AXIS_11_T05 | 完了 | — | FOUND | FOUND | FOUND | 1/2/1 | 8/11 | YES | 0/0 |
| AXIS_11_T06 | 完了 | — | FOUND | FOUND | FOUND | 1/2/1 | 10/12 | YES | 0/0 |
| AXIS_11_T07 | 完了 | — | FOUND | FOUND | FOUND | 1/2/1 | 8/9 | YES | 0/0 |
| AXIS_11_T08 | 完了 | — | FOUND | FOUND | FOUND | 1/1/2 | 7/10 | YES | 0/0 |
| AXIS_12_T01 | 完了 | — | FOUND | FOUND | FOUND | 1/2/1 | 8/11 | YES | 0/0 |
| AXIS_12_T02 | 完了 | — | FOUND | FOUND | FOUND | 2/2/1 | 19/20 | YES | 18/4 |
| AXIS_12_T03 | 完了 | — | FOUND | FOUND | FOUND | 2/1/2 | 8/9 | YES | 0/0 |
| AXIS_12_T04 | 完了 | — | FOUND | FOUND | FOUND | 2/2/1 | 11/11 | YES | 0/1 |
| AXIS_12_T05 | 完了 | — | FOUND | FOUND | FOUND | 0/1/2 | 14/14 | YES | 0/0 |
| AXIS_12_T06 | 完了 | — | FOUND | FOUND | FOUND | 2/2/1 | 7/8 | YES | 0/0 |
| AXIS_12_T07 | 完了 | — | FOUND | FOUND | FOUND | 0/2/1 | 10/10 | YES | 0/0 |
| AXIS_12_T08 | 完了 | — | FOUND | FOUND | FOUND | 1/1/1 | 9/9 | YES | 0/0 |
| AXIS_13_T01 | 完了 | — | FOUND | FOUND | FOUND | 2/2/1 | 12/14 | YES | 0/2 |
| AXIS_13_T02 | 完了 | — | FOUND | FOUND | FOUND | 1/1/2 | 10/11 | YES | 0/1 |
| AXIS_13_T03 | 完了 | — | FOUND | FOUND | FOUND | 0/1/1 | 7/8 | YES | 0/2 |
| AXIS_13_T04 | 完了 | — | FOUND | FOUND | FOUND | 3/1/1 | 11/16 | YES | 0/0 |
| AXIS_13_T05 | 完了 | — | FOUND | FOUND | FOUND | 0/2/1 | 16/21 | YES | 10/2 |
| AXIS_13_T06 | 完了 | — | FOUND | FOUND | FOUND | 3/1/1 | 11/12 | YES | 0/0 |
| AXIS_13_T07 | 完了 | — | FOUND | FOUND | FOUND | 1/1/1 | 12/13 | YES | 0/0 |
| AXIS_13_T08 | 完了 | — | FOUND | FOUND | FOUND | 0/2/1 | 8/9 | YES | 0/1 |
| AXIS_14_T01 | 完了 | — | FOUND | FOUND | FOUND | 1/2/1 | 8/9 | YES | 0/0 |
| AXIS_14_T02 | 完了 | — | FOUND | FOUND | FOUND | 1/3/1 | 9/10 | YES | 0/0 |
| AXIS_14_T03 | 完了 | — | FOUND | FOUND | FOUND | 0/2/2 | 14/17 | YES | 0/1 |
| AXIS_14_T04 | 完了 | — | FOUND | FOUND | FOUND | 1/1/1 | 13/14 | YES | 0/0 |
| AXIS_14_T05 | 完了 | — | FOUND | FOUND | FOUND | 1/1/1 | 9/10 | YES | 0/0 |
| AXIS_14_T06 | 完了 | — | FOUND | FOUND | FOUND | 1/1/1 | 9/9 | YES | 0/1 |
| AXIS_14_T07 | 完了 | — | FOUND | FOUND | FOUND | 1/2/1 | 7/10 | YES | 0/2 |
| AXIS_14_T08 | 完了 | — | FOUND | FOUND | FOUND | 0/3/1 | 8/8 | YES | 0/1 |
| AXIS_15_T01 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_15_T02 | 未完 | Q1,Q2,Q3,Q4 | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_15_T03 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_15_T04 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_15_T05 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 1/0 |
| AXIS_15_T06 | 未完 | Q1,Q2,Q3,Q4 | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 0/1 | NO | 1/0 |
| AXIS_15_T07 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_15_T08 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_16_T01 | 未完 | Q1,Q2,Q3,Q4 | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_16_T02 | 未完 | Q1,Q2,Q3,Q4 | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_16_T03 | 未完 | Q1,Q2,Q3,Q4 | ATTEMPTED_INSUFFICIENT | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_16_T04 | 未完 | Q1,Q2,Q3,Q4 | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_16_T05 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_16_T06 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_16_T07 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_16_T08 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_17_T01 | 完了 | — | FOUND | FOUND | FOUND | 1/2/1 | 27/35 | YES | 11/3 |
| AXIS_17_T02 | 完了 | — | FOUND | FOUND | FOUND | 1/1/1 | 11/17 | YES | 0/0 |
| AXIS_17_T03 | 未完 | Q1,Q2,Q3,Q4 | FOUND | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 16/18 | NO | 0/0 |
| AXIS_17_T04 | 完了 | — | FOUND | FOUND | FOUND | 0/3/1 | 9/10 | YES | 0/0 |
| AXIS_17_T05 | 完了 | — | FOUND | FOUND | FOUND | 1/1/2 | 10/16 | YES | 0/0 |
| AXIS_17_T06 | 完了 | — | FOUND | FOUND | FOUND | 0/2/1 | 10/13 | YES | 0/0 |
| AXIS_17_T07 | 完了 | — | FOUND | FOUND | FOUND | 0/2/1 | 11/14 | YES | 0/0 |
| AXIS_17_T08 | 未完 | Q1,Q2,Q3,Q4 | FOUND | FOUND | FOUND | 0/0/0 | 17/19 | YES | 37/8 |
| AXIS_18_T01 | 未完 | Q1,Q2,Q3,Q4 | FOUND | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 1/3 | NO | 0/0 |
| AXIS_18_T02 | 未完 | Q1,Q2,Q3,Q4 | FOUND | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 1/2 | NO | 0/0 |
| AXIS_18_T03 | 未完 | Q1,Q2,Q3,Q4 | FOUND | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 0/1 | NO | 0/0 |
| AXIS_18_T04 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_18_T05 | 未完 | Q1,Q2,Q3,Q4 | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_18_T06 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_18_T07 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_18_T08 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_19_T01 | 完了 | — | FOUND | FOUND | FOUND | 2/1/2 | 11/14 | YES | 0/0 |
| AXIS_19_T02 | 完了 | — | FOUND | FOUND | FOUND | 2/1/1 | 13/15 | YES | 0/0 |
| AXIS_19_T03 | 完了 | — | FOUND | FOUND | FOUND | 1/1/1 | 7/10 | YES | 0/0 |
| AXIS_19_T04 | 完了 | — | FOUND | FOUND | FOUND | 1/1/1 | 10/14 | YES | 0/0 |
| AXIS_19_T05 | 完了 | — | FOUND | FOUND | FOUND | 1/2/1 | 9/10 | YES | 0/0 |
| AXIS_19_T06 | 未完 | Q1,Q2,Q3,Q4 | FOUND | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 8/9 | NO | 0/0 |
| AXIS_19_T07 | 完了 | — | FOUND | FOUND | FOUND | 1/2/1 | 9/14 | YES | 0/0 |
| AXIS_19_T08 | 完了 | — | FOUND | FOUND | FOUND | 1/2/2 | 8/11 | YES | 0/0 |
| AXIS_20_T01 | 完了 | — | FOUND | FOUND | FOUND | 0/1/1 | 11/12 | YES | 0/1 |
| AXIS_20_T02 | 完了 | — | FOUND | FOUND | FOUND | 0/2/2 | 11/12 | YES | 0/0 |
| AXIS_20_T03 | 完了 | — | FOUND | FOUND | FOUND | 2/1/1 | 9/10 | YES | 0/0 |
| AXIS_20_T04 | 完了 | — | FOUND | FOUND | FOUND | 0/1/1 | 7/8 | YES | 0/0 |
| AXIS_20_T05 | 完了 | — | FOUND | FOUND | FOUND | 1/2/1 | 9/10 | YES | 0/0 |
| AXIS_20_T06 | 完了 | — | FOUND | FOUND | FOUND | 0/2/1 | 8/10 | YES | 0/0 |
| AXIS_20_T07 | 完了 | — | FOUND | FOUND | FOUND | 1/1/1 | 8/9 | YES | 0/0 |
| AXIS_20_T08 | 完了 | — | FOUND | FOUND | FOUND | 0/1/1 | 6/9 | YES | 0/1 |
| AXIS_21_T01 | 未完 | Q1,Q2,Q3,Q4 | FOUND | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 1/1 | NO | 0/0 |
| AXIS_21_T02 | 未完 | Q1,Q2,Q3,Q4 | FOUND | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 1/1 | NO | 0/0 |
| AXIS_21_T03 | 未完 | Q1,Q2,Q3,Q4 | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_21_T04 | 未完 | Q1,Q2,Q3,Q4 | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_21_T05 | 未完 | Q1,Q2,Q3,Q4 | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_21_T06 | 未完 | Q1,Q2,Q3,Q4 | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_21_T07 | 未完 | Q1,Q2,Q3,Q4 | FOUND | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 1/1 | NO | 1/0 |
| AXIS_21_T08 | 未完 | Q1,Q2,Q3,Q4 | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_22_T01 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_22_T02 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_22_T03 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_22_T04 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_22_T05 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_22_T06 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_22_T07 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_22_T08 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_23_T01 | 未完 | Q1,Q2,Q3,Q4 | FOUND | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 1/1 | NO | 1/0 |
| AXIS_23_T02 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_23_T03 | 未完 | Q1,Q2,Q3,Q4 | FOUND | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 1/1 | NO | 0/0 |
| AXIS_23_T04 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_23_T05 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_23_T06 | 未完 | Q1,Q2,Q3,Q4 | FOUND | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 1/1 | NO | 0/0 |
| AXIS_23_T07 | 未完 | Q1,Q2,Q3,Q4 | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_23_T08 | 未完 | Q1,Q2,Q3,Q4 | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_24_T01 | 未完 | Q1,Q2,Q3,Q4 | FOUND | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 0/1 | NO | 1/0 |
| AXIS_24_T02 | 未完 | Q1,Q2,Q3,Q4 | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_24_T03 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 2/0 |
| AXIS_24_T04 | 未完 | Q1,Q2,Q3,Q4 | FOUND | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 2/2 | NO | 5/0 |
| AXIS_24_T05 | 未完 | Q1,Q2,Q3,Q4 | FOUND | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 1/1 | NO | 0/0 |
| AXIS_24_T06 | 未完 | Q1,Q2,Q3,Q4 | FOUND | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 1/1 | NO | 0/0 |
| AXIS_24_T07 | 未完 | Q1,Q2,Q3,Q4 | FOUND | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 0/1 | NO | 0/0 |
| AXIS_24_T08 | 未完 | Q1,Q2,Q3,Q4 | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 2/0 |
| AXIS_25_T01 | 未完 | Q1,Q2,Q3,Q4 | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 0/1 | NO | 0/0 |
| AXIS_25_T02 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_25_T03 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_25_T04 | 未完 | Q1,Q2,Q3,Q4 | FOUND | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 1/1 | NO | 0/0 |
| AXIS_25_T05 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_25_T06 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_25_T07 | 未完 | Q1,Q2,Q3,Q4 | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_25_T08 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 4/0 |
| AXIS_26_T01 | 未完 | Q1,Q2,Q3,Q4 | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_26_T02 | 未完 | Q1,Q2,Q3,Q4 | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_26_T03 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_26_T04 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_26_T05 | 未完 | Q1,Q2,Q3,Q4 | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_26_T06 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_26_T07 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_26_T08 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_27_T01 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_27_T02 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_27_T03 | 未完 | Q1,Q2,Q3,Q4 | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_27_T04 | 未完 | Q1,Q2,Q3,Q4 | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_27_T05 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 2/0 |
| AXIS_27_T06 | 未完 | Q1,Q2,Q3,Q4 | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_27_T07 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_27_T08 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_28_T01 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_28_T02 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_28_T03 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_28_T04 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_28_T05 | 未完 | Q1,Q2,Q3,Q4 | FOUND | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 1/1 | NO | 0/0 |
| AXIS_28_T06 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_28_T07 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_28_T08 | 未完 | Q1,Q2,Q3,Q4 | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_01_T09 | 未完 | — | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_01_T10 | 未完 | — | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_02_T09 | 完了 | — | FOUND | FOUND | FOUND | 3/2/3 | 4/6 | YES | 17/0 |
| AXIS_02_T10 | 完了 | — | FOUND | FOUND | FOUND | 2/3/2 | 4/6 | YES | 12/0 |
| AXIS_03_T09 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 1/0 |
| AXIS_04_T09 | 完了 | — | FOUND | FOUND | FOUND | 2/1/2 | 7/9 | YES | 11/0 |
| AXIS_04_T10 | 未完 | — | FOUND | FOUND | FOUND | 0/2/1 | 40/55 | YES | 0/2 |
| AXIS_05_T09 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_05_T10 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_06_T09 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_06_T10 | 未完 | — | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_07_T09 | 完了 | — | FOUND | FOUND | FOUND | 0/3/1 | 7/8 | YES | 10/0 |
| AXIS_07_T10 | 完了 | — | FOUND | FOUND | FOUND | 1/1/2 | 10/11 | YES | 5/0 |
| AXIS_08_T09 | 完了 | — | FOUND | FOUND | FOUND | 2/1/1 | 12/17 | YES | 5/2 |
| AXIS_09_T09 | 完了 | — | FOUND | FOUND | FOUND | 1/1/2 | 8/9 | YES | 3/3 |
| AXIS_09_T10 | 完了 | — | FOUND | FOUND | FOUND | 0/2/2 | 6/7 | YES | 6/0 |
| AXIS_09_T11 | 完了 | — | FOUND | FOUND | FOUND | 2/1/1 | 5/6 | YES | 1/0 |
| AXIS_10_T09 | 完了 | — | FOUND | FOUND | FOUND | 2/2/1 | 5/6 | YES | 0/0 |
| AXIS_10_T10 | 完了 | — | FOUND | FOUND | FOUND | 2/2/1 | 9/12 | YES | 0/0 |
| AXIS_11_T09 | 完了 | — | FOUND | FOUND | FOUND | 2/1/1 | 5/7 | YES | 0/0 |
| AXIS_11_T10 | 未完 | — | FOUND | FOUND | FOUND | 0/2/2 | 33/45 | YES | 0/0 |
| AXIS_12_T09 | 完了 | — | FOUND | FOUND | FOUND | 3/1/1 | 7/8 | YES | 0/0 |
| AXIS_12_T10 | 完了 | — | FOUND | FOUND | FOUND | 2/2/1 | 10/13 | YES | 0/0 |
| AXIS_13_T09 | 完了 | — | FOUND | FOUND | FOUND | 1/3/1 | 8/9 | YES | 0/0 |
| AXIS_13_T10 | 完了 | — | FOUND | FOUND | FOUND | 3/1/1 | 9/13 | YES | 0/0 |
| AXIS_14_T09 | 完了 | — | FOUND | NOT_FOUND_AFTER_SEARCH | FOUND | 1/2/1 | 8/8 | YES | 0/0 |
| AXIS_14_T10 | 完了 | — | FOUND | FOUND | FOUND | 1/1/2 | 7/11 | YES | 0/0 |
| AXIS_14_T11 | 完了 | — | FOUND | FOUND | FOUND | 1/1/1 | 8/11 | YES | 0/0 |
| AXIS_15_T09 | 未完 | — | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 0/1 | NO | 0/0 |
| AXIS_15_T10 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_16_T09 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 2/0 |
| AXIS_17_T09 | 未完 | — | FOUND | FOUND | FOUND | 0/2/2 | 14/18 | YES | 0/0 |
| AXIS_18_T09 | 未完 | — | FOUND | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 1/1 | NO | 0/0 |
| AXIS_19_T09 | 完了 | — | FOUND | FOUND | FOUND | 2/2/1 | 13/20 | YES | 0/0 |
| AXIS_19_T10 | 完了 | — | FOUND | FOUND | FOUND | 1/2/2 | 9/12 | YES | 0/0 |
| AXIS_20_T09 | 未完 | — | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_21_T09 | 未完 | — | ATTEMPTED_INSUFFICIENT | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_21_T10 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 1/0 |
| AXIS_21_T11 | 未完 | — | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_22_T09 | 未完 | — | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_23_T09 | 未完 | — | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_23_T10 | 未完 | — | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_23_T11 | 未完 | — | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_23_T12 | 未完 | — | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_24_T09 | 未完 | — | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_24_T10 | 未完 | — | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_25_T09 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_25_T10 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_25_T11 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_26_T09 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_26_T10 | 未完 | — | FOUND | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 1/1 | NO | 0/0 |
| AXIS_27_T09 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_28_T09 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_28_T10 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_28_T11 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_29_T01 | 未完 | — | FOUND | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 0/1 | NO | 1/0 |
| AXIS_29_T02 | 未完 | — | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 1/1 | NO | 4/0 |
| AXIS_29_T03 | 完了 | — | FOUND | FOUND | FOUND | 2/2/2 | 16/18 | YES | 11/3 |
| AXIS_29_T04 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 1/0 |
| AXIS_29_T05 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_29_T06 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 1/0 |
| AXIS_29_T07 | 未完 | — | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 2/0 |
| AXIS_29_T08 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_29_T09 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_29_T10 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 1/0 |
| AXIS_29_T11 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_29_T12 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 1/0 |
| AXIS_30_T01 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_30_T02 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 5/0 |
| AXIS_30_T03 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_30_T04 | 未完 | — | FOUND | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 1/1 | NO | 0/0 |
| AXIS_30_T05 | 未完 | — | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 2/0 |
| AXIS_30_T06 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_30_T07 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_30_T08 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_30_T09 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 9/0 |
| AXIS_30_T10 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_30_T11 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_30_T12 | 未完 | — | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 1/0 |
| AXIS_31_T01 | 未完 | — | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_31_T02 | 未完 | — | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 1/0 |
| AXIS_31_T03 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_31_T04 | 未完 | — | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_31_T05 | 完了 | — | FOUND | FOUND | FOUND | 2/2/1 | 5/5 | YES | 16/1 |
| AXIS_31_T06 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_31_T07 | 未完 | — | FOUND | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 1/1 | NO | 0/0 |
| AXIS_31_T08 | 未完 | — | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_31_T09 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_31_T10 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_31_T11 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_32_T01 | 未完 | — | FOUND | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 1/1 | NO | 3/0 |
| AXIS_32_T02 | 未完 | — | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_32_T03 | 未完 | — | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_32_T04 | 未完 | — | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 2/0 |
| AXIS_32_T05 | 未完 | — | FOUND | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 1/1 | NO | 0/0 |
| AXIS_32_T06 | 未完 | — | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_32_T07 | 未完 | — | FOUND | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_32_T08 | 未完 | — | FOUND | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 0/1 | NO | 2/0 |
| AXIS_32_T09 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_32_T10 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| AXIS_32_T11 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| ADD_N01_T01 | 未完 | — | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 4/5 | NO | 1/0 |
| ADD_N01_T02 | 未完 | — | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | ATTEMPTED_INSUFFICIENT | 0/0/0 | 4/5 | NO | 3/0 |
| ADD_N01_T03 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| ADD_N01_T04 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| ADD_N02_T01 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| ADD_N03_T01 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |
| ADD_SPD_T01 | 未完 | — | NO | NO | NO | 0/0/0 | 0/0 | NO | 0/0 |

## 4. 競合別の未達（全件）

| ID | 名称 | 優先 | 状態 | 公式確認 | 公式ページ読了 | 反証 | 未記録の項目・理由 | チャット候補 |
|---|---|---|---|---|---|---|---|---|
| C001 | Adobe Acrobat AI Assistant | P0 | 完了 | YES | 4（遮断9） | YES | — | 14 |
| C002 | Gamma | P0 | 完了 | YES | 13（遮断11） | YES | — | 10 |
| C003 | Microsoft Copilot PowerPoint | P0 | 完了 | YES | 17（遮断0） | YES | — | 17 |
| C004 | Google Slides Gemini | P0 | 完了 | YES | 8（遮断1） | YES | — | 6 |
| C005 | Gemini Notebook / NotebookLM | P0 | 完了 | YES | 14（遮断2） | YES | — | 6 |
| C006 | Genspark AI Slides | P0 | 完了 | YES | 8（遮断6） | YES | — | 1 |
| C007 | Canva | P0 | 完了 | YES | 4（遮断6） | YES | — | 2 |
| C008 | Beautiful.ai | P0 | 完了 | YES | 10（遮断1） | YES | — | 0 |
| C009 | Plus AI | P0 | 完了 | YES | 13（遮断5） | YES | — | 0 |
| C010 | SlidesAI | P1 | 完了 | YES | 8（遮断7） | YES | — | 0 |
| C011 | ChatGPT | P0 | 完了 | YES | 4（遮断5） | YES | — | 0 |
| C012 | Claude | P1 | 完了 | YES | 9（遮断2） | YES | — | 0 |
| C013 | Gemini | P1 | 完了 | YES | 19（遮断1） | YES | — | 6 |
| C014 | Perplexity | P1 | 完了 | YES | 15（遮断2） | YES | — | 0 |
| C015 | Google Slides without AI | P1 | 未完 | YES | 22（遮断0） | NO | no counter / independent search with results and no third-party-backed counter finding | 6 |
| C016 | PowerPoint without AI | P1 | 完了 | YES | 19（遮断1） | YES | — | 17 |
| C017 | Pitch | P1 | 未完 | YES | 9（遮断7） | NO | no counter / independent search with results and no third-party-backed counter finding | 0 |
| C018 | Prezi AI | P2 | 未完 | YES | 6（遮断4） | NO | no counter / independent search with results and no third-party-backed counter finding | 1 |
| C019 | Decktopus | P1 | 完了 | YES | 7（遮断2） | YES | — | 0 |
| C020 | Presentations.AI | P1 | 完了 | YES | 17（遮断0） | YES | — | 0 |
| C021 | Slidesgo AI Presentation Maker | P1 | 完了 | YES | 7（遮断2） | YES | — | 0 |
| C022 | MagicSlides | P1 | 未完 | YES | 8（遮断0） | NO | no counter / independent search with results and no third-party-backed counter finding | 1 |
| C023 | SlideSpeak | P0 | 完了 | YES | 8（遮断6） | YES | — | 0 |
| C024 | Alai | P1 | 未完 | YES | 10（遮断3） | NO | no counter / independent search with results and no third-party-backed counter finding | 1 |
| C025 | Chronicle | P2 | 未完 | YES | 8（遮断0） | NO | no counter / independent search with results and no third-party-backed counter finding | 0 |
| C026 | Felo AI Slides | P0 | 完了 | YES | 5（遮断10） | YES | — | 1 |
| C027 | イルシル | P0 | 完了 | YES | 10（遮断8） | YES | — | 0 |
| C028 | MiriCanvas AI Presentation | P0 | 完了 | YES | 12（遮断3） | YES | — | 0 |
| C029 | PageOn.ai | P1 | 未完 | YES | 6（遮断7） | NO | no counter / independent search with results and no third-party-backed counter finding | 2 |
| C030 | Slidebean | P2 | 未完 | YES | 8（遮断5） | NO | no counter / independent search with results and no third-party-backed counter finding | 1 |
| C031 | Adobe Express | P1 | 完了 | YES | 3（遮断9） | YES | — | 14 |
| C032 | Visme | P1 | 未完 | YES | 9（遮断4） | NO | no counter / independent search with results and no third-party-backed counter finding | 2 |
| C033 | Zoho Show Zia | P1 | 未完 | YES | 8（遮断3） | NO | no counter / independent search with results and no third-party-backed counter finding | 0 |
| C034 | WPS AI Presentation | P0 | 完了 | YES | 8（遮断3） | YES | — | 4 |
| C035 | Figma Slides | P2 | 未完 | YES | 8（遮断0） | NO | no counter / independent search with results and no third-party-backed counter finding | 0 |
| C036 | ChatPDF | P0 | 完了 | YES | 10（遮断14） | YES | — | 0 |
| C037 | AskYourPDF | P1 | 未完 | NO | 5（遮断3） | NO | attributes not recorded: official_site,features_processing,pricing_limits,io_formats,pptx_editability,speed_claims,quality_claims,source_verification,data_handl | 5 |
| C038 | PDF.ai | P1 | 未完 | YES | 1（遮断12） | NO | no counter / independent search with results and no third-party-backed counter finding | 0 |
| C039 | Humata | P1 | 未完 | YES | 8（遮断4） | NO | no counter / independent search with results and no third-party-backed counter finding | 8 |
| C040 | UPDF AI | P1 | 未完 | NO | 8（遮断1） | NO | attributes not recorded: official_site,features_processing,pricing_limits,io_formats,pptx_editability,speed_claims,quality_claims,source_verification,data_handl | 8 |
| C041 | Foxit PDF AI | P1 | 未完 | NO | 0（遮断4） | NO | no vendor page read (read 0, blocked attempts on distinct vendor pages 4/2, searches 0); attributes not recorded: official_site,features_processing,pricing_limi | 0 |
| C042 | Smallpdf AI PDF | P2 | 未完 | YES | 8（遮断0） | NO | no counter / independent search with results and no third-party-backed counter finding | 0 |
| C043 | PDFelement AI | P1 | 完了 | YES | 7（遮断4） | YES | — | 3 |
| C044 | SciSpace | P0 | 完了 | YES | 8（遮断9） | YES | — | 0 |
| C045 | Elicit | P1 | 未完 | YES | 7（遮断6） | NO | no counter / independent search with results and no third-party-backed counter finding | 0 |
| C046 | Consensus | P1 | 未完 | YES | 8（遮断8） | NO | no counter / independent search with results and no third-party-backed counter finding | 0 |
| C047 | Scholarcy | P1 | 未完 | YES | 8（遮断7） | NO | no counter / independent search with results and no third-party-backed counter finding | 0 |
| C048 | Jenni AI | P1 | 未完 | YES | 8（遮断4） | NO | no counter / independent search with results and no third-party-backed counter finding | 0 |
| C049 | Paperpal | P1 | 未完 | YES | 8（遮断4） | NO | no counter / independent search with results and no third-party-backed counter finding | 0 |
| C050 | scite | P1 | 未完 | YES | 8（遮断0） | NO | no counter / independent search with results and no third-party-backed counter finding | 0 |
| C051 | Microsoft Copilot Chat | P1 | 完了 | YES | 21（遮断0） | YES | — | 17 |
| C052 | Kimi AI | P2 | 未完 | YES | 11（遮断6） | NO | no counter / independent search with results and no third-party-backed counter finding | 0 |
| C053 | Notion AI | P1 | 未完 | YES | 8（遮断0） | NO | no counter / independent search with results and no third-party-backed counter finding | 0 |
| C054 | Coda AI | P2 | 未完 | NO | 6（遮断2） | NO | attributes not recorded: official_site,features_processing,pricing_limits,io_formats,pptx_editability,speed_claims,quality_claims,source_verification,data_handl | 0 |
| C055 | Jasper | P2 | 未完 | YES | 8（遮断1） | NO | no counter / independent search with results and no third-party-backed counter finding | 0 |
| C056 | Grammarly | P1 | 未完 | NO | 8（遮断0） | NO | attributes not recorded: official_site,features_processing,pricing_limits,io_formats,pptx_editability,speed_claims,quality_claims,source_verification,data_handl | 1 |
| C057 | Glean | P0 | 完了 | YES | 7（遮断2） | YES | — | 0 |
| C058 | StudyFetch | P1 | 未完 | NO | 1（遮断0） | NO | attributes not recorded: official_site,features_processing,pricing_limits,io_formats,pptx_editability,speed_claims,quality_claims,source_verification,data_handl | 0 |
| C059 | Knowt | P2 | 未完 | NO | 8（遮断0） | NO | attributes not recorded: official_site,features_processing,pricing_limits,io_formats,pptx_editability,speed_claims,quality_claims,source_verification,data_handl | 0 |
| C060 | Quizlet AI | P1 | 未完 | NO | 0（遮断0） | NO | no vendor page read (read 0, blocked attempts on distinct vendor pages 0/2, searches 0); attributes not recorded: official_site,features_processing,pricing_limi | 0 |
| C061 | Mindgrasp | P2 | 未完 | NO | 2（遮断1） | NO | attributes not recorded: official_site,features_processing,pricing_limits,io_formats,pptx_editability,speed_claims,quality_claims,source_verification,data_handl | 0 |
| C062 | LibreOffice Impress | P2 | 未完 | NO | 0（遮断0） | NO | no vendor page read (read 0, blocked attempts on distinct vendor pages 0/2, searches 0); attributes not recorded: official_site,features_processing,pricing_limi | 0 |
| C063 | Zapier AI Workflows | P2 | 未完 | NO | 0（遮断0） | NO | no vendor page read (read 0, blocked attempts on distinct vendor pages 0/2, searches 0); attributes not recorded: official_site,features_processing,pricing_limi | 1 |
| C064 | n8n Workflows | P2 | 未完 | NO | 0（遮断0） | NO | no vendor page read (read 0, blocked attempts on distinct vendor pages 0/2, searches 0); attributes not recorded: official_site,features_processing,pricing_limi | 0 |
| C065 | SlidesPilot | P0 | 完了 | YES | 6（遮断3） | YES | — | 0 |
| C066 | Smallppt | P1 | 未完 | NO | 0（遮断0） | NO | no vendor page read (read 0, blocked attempts on distinct vendor pages 0/2, searches 0); attributes not recorded: official_site,features_processing,pricing_limi | 0 |
| C067 | AIPPT | P1 | 未完 | NO | 0（遮断0） | NO | no vendor page read (read 0, blocked attempts on distinct vendor pages 0/2, searches 0); attributes not recorded: official_site,features_processing,pricing_limi | 0 |
| C068 | Piktochart AI | P1 | 未完 | NO | 0（遮断0） | NO | no vendor page read (read 0, blocked attempts on distinct vendor pages 0/2, searches 0); attributes not recorded: official_site,features_processing,pricing_limi | 0 |
| C069 | Napkin AI | P1 | 未完 | NO | 0（遮断0） | NO | no vendor page read (read 0, blocked attempts on distinct vendor pages 0/2, searches 0); attributes not recorded: official_site,features_processing,pricing_limi | 0 |
| C070 | Storydoc | P2 | 未完 | NO | 0（遮断0） | NO | no vendor page read (read 0, blocked attempts on distinct vendor pages 0/2, searches 0); attributes not recorded: official_site,features_processing,pricing_limi | 0 |
| C071 | DeckRobot | P1 | 未完 | NO | 0（遮断0） | NO | no vendor page read (read 0, blocked attempts on distinct vendor pages 0/2, searches 0); attributes not recorded: official_site,features_processing,pricing_limi | 0 |
| C072 | Templafy | P0 | 完了 | YES | 7（遮断1） | YES | — | 0 |
| C073 | MagicSchool AI | P1 | 未完 | NO | 0（遮断0） | NO | no vendor page read (read 0, blocked attempts on distinct vendor pages 0/2, searches 0); attributes not recorded: official_site,features_processing,pricing_limi | 0 |
| C074 | Brisk Teaching | P1 | 未完 | NO | 0（遮断0） | NO | no vendor page read (read 0, blocked attempts on distinct vendor pages 0/2, searches 0); attributes not recorded: official_site,features_processing,pricing_limi | 0 |
| C075 | Curipod | P1 | 未完 | NO | 0（遮断0） | NO | no vendor page read (read 0, blocked attempts on distinct vendor pages 0/2, searches 0); attributes not recorded: official_site,features_processing,pricing_limi | 0 |
| C076 | StudyPocket | P0 | 完了 | YES | 4（遮断3） | YES | — | 0 |
| C077 | Marp | P2 | 未完 | NO | 0（遮断0） | NO | no vendor page read (read 0, blocked attempts on distinct vendor pages 0/2, searches 0); attributes not recorded: official_site,features_processing,pricing_limi | 0 |
| C078 | Quarto | P1 | 未完 | NO | 0（遮断0） | NO | no vendor page read (read 0, blocked attempts on distinct vendor pages 0/2, searches 0); attributes not recorded: official_site,features_processing,pricing_limi | 0 |
| C079 | Pandoc | P2 | 未完 | NO | 0（遮断0） | NO | no vendor page read (read 0, blocked attempts on distinct vendor pages 0/2, searches 0); attributes not recorded: official_site,features_processing,pricing_limi | 0 |
| C080 | Docling | P1 | 未完 | NO | 0（遮断0） | NO | no vendor page read (read 0, blocked attempts on distinct vendor pages 0/2, searches 0); attributes not recorded: official_site,features_processing,pricing_limi | 0 |

## 5. 次の作業ID（順序）

1. 未実行の旧検索IDを持つ未完テーマ（優先度順、`scripts/next_batch.py` が自動選択）：各作業員が旧検索IDを原文どおり実行し、ルートごとに独自クエリ2本、割当てのチャット候補を全件開いて判定。
2. 未完の競合：公式ページの読了（検索不要）、反証・独立の検索1本、割当てのチャット候補の判定。
3. S1完了済みテーマに割り当てられた未判定のチャット候補の判定パス（検索なし、読了のみ）。
4. 全件後、`research/COLLECTION_COVERAGE_AUDIT.md` を再生成してS1ゲートを再判定。

