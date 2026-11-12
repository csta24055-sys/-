# 2 構造間のデータ受け渡し仕様

宣言はすべて `research_code/specs/system.py` にデータとして書いてある。実行は `research_code/tstudy/unified.py`。受け渡しの途中で値の算術はしない。

## 1. 入力 → 共通表（`INDEX_PLAN`、15 操作）

| 操作 | 作る表 | 内容 |
|---|---|---|
| `tokenise` | （全表） | 文字列の列ごとに `~h`・`~t`（最初の「/」の前後）、`~p`・`~i`・`~s`（`名前[番号].残り`） |
| `product` | `operation.grid.table.xsteps` | 年 × 電力係数の段 |
| `product` | `refrigerants.years` | 機器 × 年 |
| `events` | `materials.events` | 材料の行の更新（周期の格子） |
| `events` | `equipment.events` | 設備の更新（周期の格子と一覧の格子） |
| `events` | `refrigerants.events` | 冷媒機器の交換（同上） |
| `events` | `boundary.events` | 建替（周期の格子） |
| `sorted` | `project.use_area_sorted` | 用途別面積を用途名の昇順に |
| `distinct` | `CLS`、`CYC` | 材料区分の相異なる値、周期の相異なる値 |
| `events` | `CYC.events` | 周期の値ごとの格子（X-08） |
| `static` | `STG`、`COMP`、`CHK`、`ROUTES` | 14 段階、段階の構成（22 行）、完全性の点検（27 行）、処理経路 4 種 |
| `product` | `CLS.x`、`Y0.x` | 材料区分 × 経路、年 × 年（累積） |
| `range` | `Y0` | 時点 0 と年 1..H |

ほかに、基準案の入力の 5 表を `base:` を付けて加える（基準案が無ければ空の表）。

## 2. 積和① → 節点スペクトル（`EMIT`、32 行）

1 行が「どの表の、どの振幅の列を、どの形の節点として、どのスペクトルに置くか」を表す。

```
{"spectrum": "B4-02", "table": "materials.events", "shape": "atom", "amp": "me.b4", "tau": "tau"}
{"spectrum": "B3-01", "table": "materials.events", "shape": "gcell", "amp": "me.b3", "k": "cell", "tau": "tau"}
{"spectrum": "B6-03", "table": "operation.grid.table", "shape": "cell", "amp": "b63.a", "k": "_pos"}
```

振幅が 0 の行は節点にしない。振幅に欠損があれば計算を止める（`Unusable`）。区間形（B1-04）は `System._interval` が `b1.iA`・`b1.iB`・`b1.e4a`・`b1.e4g`・`b1.tau1` を読んで作る。

## 3. 節点スペクトル → 積和②（表 `TT`）

`System.at(T)` は 1 行の表 `TT` を作る：列 `T`、スペクトルの値 `K.<名前>`（23 列）、基準案の合計 `base_sum3`（基準案があるとき）。
TIME が `Tin = T·(1 − 1e-9)` を加える。

## 4. TIME → AGG（表 `U` と `TT` の `V.<単位>`）

単位の値と、完全性の判定に使う件数を、名前付きのスカラーから「単位の行を持つ表 `U`」（29 行：`id`、`value`、`bad`）に並べ直す。

| 値の出どころ（`CONST_VALUE`、`VALUE_AT_T`） | 単位 |
|---|---|
| 積和①のスカラー | A13-01、A13-03、A13-04、X-01、A4-01、A4-02、A5-04、C1-01、C2-01、C3-01、X-14、C4-01 |
| 節点スペクトル（跳び形）の値 | B1-02、B1-03、B3-01、B4-02、B5-01、B6-03、B7-04 |
| 節点スペクトル（区間形）の値 | B1-04 |
| TIME の値（スペクトルの値 × 入力） | B2-01（`EL(T)·比率`） |

`bad` は積和①のスカラー `bad.<単位>`（25 個）と、B4-02 だけ節点スペクトル `N.b42` の値。同じ値を `TT` の列 `V.<単位>` にも置く（AGG がスカラーとして読むため）。

## 5. 積和② → 結果

読み出し（`_static_results`、`_results`）が、結果の列から基準計算と同じ形の辞書を作る。行う操作は、列を一覧にする、印の付いた行の番号から場所の文字列を作る、
キーの文字列を付ける、整数・真偽値に型を変える、重複を除いて並べる、だけである。読み出しが使った列は `System.read_from` に残る。

## 6. 2 通りに計算して突き合わせている量

| 量 | 経路 1 | 経路 2 | 扱い |
|---|---|---|---|
| B4-02 の n_partial | 節点スペクトル `N.b42` | TIME の行ごとの件数 `t.np` | 食い違えば停止 |
| B1-04 | 区間形 | TIME の局所形 `t.b14`、跳び形 | `System.last["b14"]` に 3 つとも残す |
| 段階の値 | 単位の値の和（X-02） | 排出の行の足し直し（X-04） | QA-01 (a) が比べる |
