# 08 検証：コード・条件・結果・証明の区別

すべて架空データ（旧研究の凍結した生成器 `09_APPROX_STUDY/research_code/synth`）と、本研究の乱数（シード 20261128）で行った。実建物の精度や J-CAT との同等性は主張しない。

## 1. 再実行

```bash
# 前提：旧研究の 2 つの版を読み取り専用で取り出す（この研究ディレクトリの外）
git fetch origin claude/jcat-lca-app-foundation-c33936 claude/wlc-theory-research-base-c33936
git worktree add --detach ../ref_foundation 761da13d6cab68eb76a7bd7eba0262b82b7fde29
git worktree add --detach ../ref_theorybase 9416a1bbb3c48d6fd9589789dcb045c0eb6e03be
cd wlc_essential_structure
bash tools/run_all.sh ../../ref_foundation ../../ref_theorybase      # 約 15 分（Python 3.13、NumPy 2.5）
```

`run_all.sh` の各段（個別にも実行できる）：

| 段 | コマンド | 時間 | 出力 |
|---|---|---|---|
| 凍結の記録 | `python3 -I tools/freeze_baseline.py F TB 00_baseline/frozen_sources.json` | 1 秒 | 版とハッシュ 25 件 |
| 667 監査 | `python3 -I tools/build_ledger667.py F 02_ledger667` | 1 秒 | 台帳・集計 |
| 70 再編 | `python3 -I tools/build_units70.py F TB 03_units70 04_graph` | 1 秒 | 再分類・依存グラフ・監査 |
| 族の照合 | `python3 -I tools/verify_families.py 08_verification/results/families_exact.json` | 20 秒 | 規則・恒等式・反例 |
| 再構成 | `python3 -B tools/run_reconstruction.py F 08_verification/results` | 約 9 分 | 1,293 組の照合 |
| 帯と実時間 | `python3 -B tools/band_and_realtime.py F 08_verification/results` | 約 4 分 | 帯の再現・実時間 |
| 接続表 | `python3 -I tools/make_connection.py 08_verification/results 06_connection` | 2 秒 | 接続表・集計先の検査 |

F・TB は上の 2 つの取り出し先。`-B` の段は旧研究のコードを読み取りだけで import する（バイトコードを書かない。旧チェックアウトの `git status` が空のままであることを確認済み）。旧コードの基準計算は `baseline.assert_frozen()` で凍結した版であることを確かめてから使う。

## 2. 結果

| # | 検証 | 分母 | 不一致・除外 | 水準 |
|---|---|---|---|---|
| V1 | 変換規則 R-IF・MIN・MAX・ABS・CLIP | 3,049・3,049・3,049・3,049・3,000 組（無作為＋境界の値） | 0 | E |
| V2 | R-FLOOR（定義域 $0\le y<N+1$ の内側） | 2,015 件 | 0（外側の 1,025 件はすべて誤り：定義域が規則の一部であることの反例） | E・CE |
| V3 | R-ROUND（同上の定義域） | 900 件 | 0 | E |
| V4 | R-MOD（年次・周期の判定）・R-COUNT（交換回数）・R-LOOKUP | 4,719・23,541・31 件 | 0 | E |
| V5 | F3：核の和 ＝ 節点形（独立に導出した変換） | 400 関数・56,562 点 | 0 | E |
| V6 | F4：漸化式 ＝ 閉形式 | 300 本 × 61 点 | 0 | E |
| V7 | F3：連続運用と事象 ＝ 1 つの測度 $\mu([0,T))$ | 300 関数 | 帯の外 0。帯の内側に置いた 876 点はすべて事象規則の帯の差（定理 3 の除外どおり） | E |
| V8 | **建物全体の再構成**（5 族の評価器＋独自に再コード化した構成表 F5）vs 凍結した基準計算：直接 21 単位の値 | 1,293 組（10 集合）・27,153 値 | 0（相対 1e-9）。定義域の外の 2 組は除外（旧研究と同じ） | F |
| V9 | 同：14 段階の値 | 17,884 値 | 0 | F |
| V10 | 同：SUM-01・SUM-02・SUM-03 を 5 集計先の 0/1 結合で | 各 1,293 値 | 0 | F |
| V11 | 時間形の合計から SUM-02 を作れるか（最良の固定係数） | 1,293 組 | 作れない（最大相対残差 0.98）＝反例 | F・CE |
| V12 | **旧 17 章の細帯 $(K,\mathrm{sw}(K))$ の再現**：整数の冷媒交換年 $K$ の直後 | 412 試験（(シナリオ, $K$) 103 組） | 帯の内側 309 試験のうち 153 で不一致（51 組。すべて B1-04 の期末残存量。SUM-03 の相対差 7e-9〜2e-3）。帯の外側 103 試験は 0。帯の内側 309 試験のうち、旧研究の定義域 `valid_domain` が「定義域の内側」と判定したのは 247 試験（定義域の穴の再確認） | F・CE |
| V13 | 評価期間 $T$ と実時間 $t$ | 1 シナリオ・240 点 | $C(T^*)=M_{T^*}(T^*)$、$t<T^*$ で差＝終端項 $Z(t)$（全点）。差の最大 8.5×10^5 kgCO2e | E（恒等式）・F |

V8〜V10 の分母は旧研究の第 11・17 章と同じ（1,293 組、単位 27,153 値、段階 17,884 値）。

## 3. 何が証明で、何が照合か

| 主張 | 水準 | 根拠 |
|---|---|---|
| 5 族は 1 形式（述語つき積和）に代数的に帰着する（最小性は主張しない） | P | 05-01 定理 1 |
| 型の制約の下で 5 族は互いに置き換えられない | P | 05-01 定理 2（この主張は型の取り方に依存する） |
| 連続運用と事象は 1 つの測度の積分（帯を除く） | P＋E | 定理 3、V7 |
| 初期量と終端量は $C(T)$ から区別できない | P | 定理 4、CE-5、V13 |
| 70 単位の建物全体が 5 族と 5 集計先で基準計算と一致 | F（標本上の数値の一致） | V8〜V10 |
| 5 集計先で段階の割合が失われる | P（写像の階数） | 06 章 |
| 667 式の判定・族 | 推定（構造メタデータ、権利保留） | 02 章 |

V8〜V10 では、F1・F2・F4 の振幅（核の項の係数）は旧研究の統合系（`canon.py` 経由）が作ったものを使い、本研究が独立に書いたのは F3 の評価・F5 の構成表・集計先・比較である。F1・F2・F4 を入力から独立に書き直して照合することは未実施（README の再開手順 1）。

## 4. 結果ファイル

`results/families_exact.json`（V1〜V7・反例）、`reconstruction.json`・`reconstruction_log.txt`（V8〜V10、集合ごと）、`shape_rows.json`（組ごとの時間形・集計先・総量、V11 の入力）、`direct_unit_time_shapes.json`（直接単位ごとの核の形の数）、`band_test.json`（V12 の全試験）、`realtime_vs_T.csv`・`realtime_vs_T.json`（V13）。
