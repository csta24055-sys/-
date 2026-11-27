# tools/collect：係数の取得（再収集の手順）

係数の調査は 8 つの調査担当が、共通の指示書 [BRIEF.md](BRIEF.md)（出力形式・権利の 5 区分・禁止事項）に従って行った（2026-11-27）。

| 系統 | ここに置いたスクリプト | 置かなかった理由 |
|---|---|---|
| ドイツ ÖKOBAUDAT・スイス KBOB | `obd_select.py`、`build_de_ch.py`（公式の CSV・Excel を読むだけ。値を含まない） | — |
| スウェーデン Boverket・フランス ADEME | `build_se_fr.py`（公式の Excel・CSV を読むだけ） | — |
| 米国 EPA・英国 DESNZ | `build_us_uk.py`（公式の xlsx を読むだけ。`COEF_BASE` に `downloads/us_uk/` を置く） | — |
| 日本の一次資料、耐用年数・冷媒・IPCC、EPD・設備、日本の数量統計、修繕統計 | なし | PDF から読み取った値（区分 3・4 を含む）をスクリプト内に持つため、公開リポジトリに置くと値の再配布になる。出典 URL・表の名前・取得日は `09_coefficients/factor_db_public.csv` の各行にある |

再収集：`09_coefficients/factor_db_public.csv` の `url` から一次資料を取得し（ログインや有償の取得はしない）、BRIEF.md の形式で `coef/out/*.csv` を作る。そのあと `tools/build_factor_db.py` と `tools/real_building_calc.py` を実行する（09・10 章の README）。
