# 23 WLC Studio — 建物のホールライフカーボンを、かんたんに（研究用の試作アプリ）

扉の起動画面 → 赤べこのホーム → 構造の選択（S・RC・SRC・木造）→ 4 大ボタン（基本情報・材料・設備・運用）→ 結果、のスマホ向けアプリ。
住所から公開データ（国土地理院・PLATEAU）を調べ、資料（数量表・IFC・PDF）から数量を読み、足りないところは出典と範囲のある統計で補い、
**既存の 70 評価単位の計算体系（10・12 章）をそのまま使って**計算する。新しいのは外側の層（自動調査・統計概算・行列化した橋渡し・確認の画面）だけ。

> **名称と権利。** 計算の核は独立に作った概念モデル（架空の係数で検証した研究のエンジン）で、J-CAT の複製・認定品・互換品ではない。
> J-CAT の係数・数式・マクロ・有償データ・名称は使っていない。**いま登録されている原単位は架空（研究用）なので、表示される排出量は実在の建物の排出量ではない。**

## 動かし方

必要なもの：Python 3.11 以上と NumPy（既存のエンジンが使う）。PDF を読むときだけ poppler-utils（`pdftotext`）。外部のライブラリは追加していない。

```bash
cd whole-life-carbon-jcat-study/23_WLC_STUDIO_APP
python3 -B -m wlcstudio serve                 # http://127.0.0.1:8770/ （ローカル専用。--keep-uploads で資料の原本を残す）
python3 -B -m wlcstudio demo                  # 架空デモを作って計算（実在の建物ではない）
python3 -B -m wlcstudio validate              # 材料の統計概算の精度検証 → docs/accuracy_report.md
python3 -B -m wlcstudio ledger --md docs/unconnected_inputs.md
python3 -B -m wlcstudio sources --md docs/sources_rights.md
WLCSTUDIO_OFFLINE=1 python3 -B -m unittest discover -s tests -t .     # 試験 41 件（約 4 秒、外部に出ない）
```

保存先は `var/`（Git に入れない）。外部から取ったデータのキャッシュは `cache/`（同じく Git に入れない）。赤べこの写真は利用者のものを
`web/assets/akabeko.jpg` に置くと表示され、無ければ「プレースホルダー画像」と書いた絵を出す（写真があるふりをしない）。

## 何ができるか

| 機能 | 中身 | 状態 |
|---|---|---|
| 7 つの状態 | 取得・確認済み／図面から計算／統計推定／仮定／未取得／適用外／計算不能を別に保存・表示。欠損を 0 にしない。出典・場所・版・取得日・単位・許諾・範囲を持つ | 実装・試験済み |
| 4 画面 75 項目 | 5 大分類とエンジンの入力に結び付け。構造ごとに材料の欄の並びを変える。各項目に 保存（手直し）・根拠を表示・自動概算・適用外・あとで確認 | 実装・画面で確認 |
| 住所から調べる | 国土地理院の住所検索 → 逆ジオコーダ（市区町村）→ PLATEAU のデータカタログ → 3D Tiles のバッチテーブルだけを HTTP Range で読む → 近くの建物の候補（階数・高さ・用途・住所・記録があれば延床面積・構造・建築年）。延床面積の記録が無ければ「屋根面積×階数×換算係数」を仮定として出す | 実データで動作確認（千代田区） |
| 資料の読み込み | CSV・XLSX（数式は計算しない、マクロは読まない）・IFC（数量セット、形状は測らない）・PDF（文字のあるページだけ、1 行ずつ要確認）。読んだ数は「図面から計算」の候補で、場所（シート!行列、#部材、ページ/行）を残す。合計行を足さない、同じ資料を二度読まない | 実装・試験済み |
| 統計概算 | 材料：国交省「建設資材・労働力需要実態調査」の面積原単位（構造別：生コン・鋼材・木材）と RASMI（kg/m2 の範囲、CC BY 4.0）。範囲は「仮の範囲」で、検証での当たり率を候補に書く。運用：経産省「エネルギー消費統計調査」の参考値だけ（電力・ガスに分けられないので入力にしない）。設備の台数・水の量は出典が無いので概算しない | 実データで動作 |
| 計算 | 既存の `lcaapp.service.Service` を呼ぶ。評価範囲を必ず渡す、SYS-01 用の状態を渡す、同じ入力の版を再利用して評価期間だけの再計算を速くする。範囲のある値を下端・上端にした合計の幅も出す | 実装・試験済み |
| 結果 | 合計・段階別（不完全な段階に印と埋め方の案内）・年ごとの排出・「少なめ（下限）」の警告・推定の影響・反映されない入力・エンジンの点検（SYS-01〜04 ほか）・計算の記録 | 実装・画面で確認 |
| 精度検証 | 公開の実データ（Material Intensity Research Database, CC BY 4.0）で、同じ文献を除いた取り置き検証 | 実行済み：**目標未達**（下） |

## 精度（目標と、実際に測ったもの）

- 目標（指示書）：同じ範囲・同じ原単位・同じ期間で、APE ≤ 10% の建物が 90% 以上（できれば 95%）。
- 測れたもの：**材料の量の誤差**だけ。日本の建物 17 件の総質量で APE ≤ 10% は **12%**、誤差の中央値 43%、5〜95% の範囲の当たり率 88%（`docs/accuracy_report.md`）。**目標は達成していない。**
- **ライフサイクルの排出量の精度は検証していない（できない）。** 合法な実際の原単位セットと、同じ範囲で算定した正解の実例が無いため。架空の原単位で重みを付けた「A1-A3 の代理」は参考で、実際の誤差ではない。
- だから「住所だけで 90〜95% の精度」とは言わない。図面・数量表・BIM の数量（図面から計算）を入れるほど推定の割合が減る（結果に「推定の影響」として出る）。

## 資料

| 資料 | 中身 |
|---|---|
| `docs/architecture.md` | 依存関係図、7 つの状態の渡し方、行列にした範囲・しなかった範囲、速さ |
| `docs/schema.md` | 値・候補・プロジェクトの保存のスキーマ |
| `docs/sources_rights.md` | データ源の権利台帳（`wlcstudio/sources/registry.json` から生成） |
| `docs/unconnected_inputs.md` | 計算に反映されない入力の一覧（未接続台帳） |
| `docs/accuracy_report.md`・`docs/validation_results.json` | 精度の検証（生成） |
| `docs/security.md` | セキュリティ・個人情報、外部公開の前に要ること |

## 試験（41 件）と指示書の対応

| 指示書の項目 | 試験 |
|---|---|
| 欠損・不明 | `test_missing_is_not_passed_as_zero`、`test_states_are_kept_apart_and_missing_is_not_zero` |
| 境界・期間の端 | `test_period_ends`（1 年・130 年・131 年は止める）、API の 0／−1／131／文字 |
| 冷媒の状態 | `test_refrigerant_states`（漏えい率あり・適用外＝0・未取得＝不完全・冷媒なし） |
| 地盤のシナリオ | `test_ground_scenarios_do_not_change_the_total`（基礎形式は記録だけで構造判断をしない） |
| 図面の読み違い | `test_csv_total_rows_and_non_numbers`、`test_ifc_quantities_and_missing_quantity_sets`、`test_document_twice_is_refused` |
| メーカー仕様の更新 | `test_history_is_kept_and_latest_is_used` |
| 単位 | `test_units_select_factor_and_conversion`、`test_tonnes_and_kilograms_give_the_same_a13` |
| 二重計上 | `test_double_counting_whole_concrete_and_foundation`、合計行・同じ資料 |
| 実例との比較 | `test_holdout_never_uses_the_same_publication`（と `validate` の実行） |
| 版つきの再計算 | `test_versioned_recalculation_reuses_prepared_system` |
| 権限・安全 | `test_http_guards`、`test_refuses_non_loopback_bind`、手入力で「統計推定」にできない |
| 回帰 | `test_research_folders_and_engine_unchanged`（23 章の外は変えていない）、`test_no_bytecode_written`、エンジンの版の確認 |
| 行列化の等価性 | `test_vectorised_a13_equals_engine`、`test_masks_partition_and_unknown_is_not_zero` |

## 指示書の Phase と到達点

| Phase | 到達点 |
|---|---|
| 0 監査 | 済み（既存アプリ・エンジン・入力の結び付け・データ源の権利を 4 つの監査で確認） |
| 1 スキーマと変換 | 済み。結び付け 241 項目のうち 4 画面から届くのは 155。未接続台帳と「計算に反映されたか」を出す |
| 2 画面 | 済み（扉・赤べこ・構造・4 大ボタン・結果。ボタンは全部動くことを Playwright で確認、減らした動き・タップの大きさ・ラベル） |
| 3 調査・読み込み | 国土地理院・PLATEAU は実データで動作。KuniJiban はリンクと書き留めだけ（自動取得しない）。メーカーのデータは利用者が読み込むだけ。CSV・XLSX・IFC・PDF |
| 4 概算 | 材料（国交省・RASMI）は動作。設備・水は出典が無いので概算しない。運用は参考値だけ |
| 5 エンジン接続と高速化 | 済み（入力の版の再利用、at(T) の再利用、要素積の等価性） |
| 6 実データでの精度 | 材料の量は検証した（目標未達）。LCA の精度は未検証（実際の原単位が無い） |
| 7 公開前の品質 | ローカル専用としての防御だけ。外部公開には認証・暗号化・分離・記録が要る（未実装） |

## 未完了・課題

1. 合法な実際の原単位セットの登録（今は架空）。それまで結果は実在の排出量ではない。
2. LCA の精度の検証（正解の実例と、同じ範囲・原単位・期間の比較）。
3. 設備（台数・質量）、上水・下水・廃棄物、運用の電力・ガスの内訳の、権利を確認できた統計。
4. EPD・複合材・解体工事（C1）・年ごとに変わる運用量・将来の排出係数の入力欄。
5. 材料の密度（m3・m2 → 質量）を出典つきで入れる仕組み（今は仮定しないので C2〜C4 の一部が不完全）。
6. 外部公開の準備（認証・権限・TLS・データの分離・記録）。
7. PLATEAU の空間 ID の属性 API（`spatialid_attributes`）への切り替え（今は 3D Tiles のバッチテーブル。読む量は少ないが自治体により属性が少ない）。
