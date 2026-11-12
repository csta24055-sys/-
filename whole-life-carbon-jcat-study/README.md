# 建築物ホールライフカーボン／独立ソフト開発のための研究台帳
> **最初に必ず [第1章：禁止事項と必須対応](01_COMPLIANCE/README.md) を読むこと。**
>
> これは **J-CATのコピー・互換品・公式ソフトではない**。公開可能な独立実装の要求分析。原版ファイルと原版由来の原単位・数式・マクロ・全文は掲載していない。
>
> 検査基準日：2026-11-11 / 取扱資料：ユーザー提供「260824_J-CAT_v2_3_2.zip」。
> 調査ステータス: STRUCTURE_INSPECTED / FORMULA_INVENTORY_PARTIAL / CALCULATION_PARITY_UNVERIFIED / LICENSE_CLEARANCE_PENDING。

## 全体構成（ここから読む）

| 順 | 位置 | 目的 |
|---|---|---|
| **01 最重要** | [01_COMPLIANCE/README.md](01_COMPLIANCE/README.md) | **禁止・許可・未許可、取るべき行動／避けるべき行動** |
| 02 | [02_SOURCES/README.md](02_SOURCES/README.md) | 元資料・5つのExcel・マニュアル・198シートの調査範囲 |
| 03 | [03_INPUTS/README.md](03_INPUTS/README.md) / [inputs.json](03_INPUTS/inputs.json) | 前提条件、入力項目、単位、必須性、出典 |
| 04 | [04_FORMULAS/README.md](04_FORMULAS/README.md) / [formulas.json](04_FORMULAS/formulas.json) | **独立実装用**計算概念、式ID、段階区分、単位、根拠、未解決条件 |
| 05 | [05_OUTPUTS/outputs.json](05_OUTPUTS/outputs.json) | 総量、年平均、面積原単位、段階別・資材別出力 |
| 06 | [06_LINEAGE/README.md](06_LINEAGE/README.md) / [links.json](06_LINEAGE/links.json) | **入力→式→出力**の対応関係と未実装依存 |
| 07 | [07_AUDIT/README.md](07_AUDIT/README.md) | 既知エラー、未検証点、根拠と検証ゲート |
| 08 | [08_BUILD_PLAN/README.md](08_BUILD_PLAN/README.md) | 何を作るか／作らないか、段階ごとの検証 |
| 09 | [09_APPROX_STUDY/README.md](09_APPROX_STUDY/README.md) | 計算式の近似化・統合研究（独立モデルの 70 評価単位、架空データでの検証。アプリは作らない）。**2026-11-11 に未完成のまま終了** |
| 保存 | [research_archive/real_equation_checkpoint/INDEX.md](research_archive/real_equation_checkpoint/INDEX.md) | 第9章の研究の停止記録・成果の分類・引継ぎ（`STOP_STATUS.md`、`INDEX.md`、`HANDOVER.md`） |
| 10 | [10_TRANSFORM_STUDY/README.md](10_TRANSFORM_STUDY/README.md) | 数学的変換による計算体系の再構成の研究（独立概念モデル、架空データ。研究中。アプリは作らない） |
| 12 | [12_APP_BASE/README.md](12_APP_BASE/README.md) | 建築 LCA アプリの基礎システム（②共通入力データ・変換、④結果表示、⑤保存）。計算は第10章の 2 構造エンジンを呼ぶ。独立概念モデル・架空データ。入力画面と実データは含まない。 |
| 付録 | [scripts/README.md](scripts/README.md) | 許可された環境で原ファイルをローカル監査する際の方針 |

## 基本思想
- 初心者：建物用途、構造、面積、資料の有無を選択 → 足りない項目は **「不明」「推定」** と明示。
- 上級者：材料・設備・冷媒・耐用年数・排出係数・輸送・施工条件を個別編集。
- 両画面とも同一の **独立算定エンジン** に接続。
- 算定境界を先に決め、**排出原単位は再利用許可のある独立データソースからのみ取得**。
- 計算結果には「値・単位・年度・前提・方法・ソース・版・未確定フラグ」を必ず持たせる。

## 現在の限界
- 原版のExcel数式ノード約3,818,483件は構造走査済みだが、全式を数学的に意味分類・再計算できたわけではない。
- 標準77、簡易73、詳細24、分類表13、集計表11＝198シート。詳細版は外部AIJ-LCA計算ソフトへの依存がある。
- VBAの実行・完全解析、原版との数値一致検証は未実施。
- 公式データ流用が許可されていないため、 **実数の係数DBはこの公開リポジトリに存在しない**。
- これは研究仕様であり、完成したWebアプリではない。検証ステータスをごまかさない。

## 公的・公式の一次資料
- J-CAT使用条件: https://www.ibecs.or.jp/zero-carbon_building/jcat/licenseterms.html
- J-CAT FAQ: https://www.ibecs.or.jp/zero-carbon_building/jcat/faq.html
- J-CAT公式: https://www.ibecs.or.jp/zero-carbon_building/jcat/
- 法的解釈は最終的に権利者へ書面確認。