# 建築 LCA の本質的な算定構造：667 式と独自 70 評価単位から 5 つの基本方程式へ（研究報告・再開手順）

研究日：2026-11-27〜28。作業ブランチ `claude/amazing-lovelace-ydhlab`。新しい研究ディレクトリで、既存の研究ディレクトリ・コード・main は変更していない。

> これは J-CAT のコピー・互換品・公式ソフトではない。J-CAT の式本文・係数・排出原単位・更新周期・修繕率・フロン漏洩率・工事分倍率は使っていない。検証の数値はすべて架空データで、実建物の精度や J-CAT との同等性を意味しない。667 式の台帳は権利保留の比較層である（[01_rights](01_rights/README.md)）。

## 1. 結論

| 問い | 答え | 水準 |
|---|---|---|
| 667 式・70 単位から、LCA に本質的な算定構造を少数の基本方程式に統合できるか | **できる。** 内部機構 G の上の 5 族：F1 有理写像（換算・選択・比）、F2 マスク付き積和（活動量×係数）、F3 時間測度の積分（連続運用と時点事象を 1 つに）、F4 状態の漸化式、F5 符号付き線形集計。70 単位の建物全体を 5 族と 5 集計先で組み直し、凍結した基準計算と 1,293 組・単位 27,153 値・段階 17,884 値・総量 3,879 値で不一致 0 | 定義・P（定理 1〜4）・F（照合） |
| 「5」は正解か | **意味の分解としては 5 が自然だが、最小数ではない。** 代数的には 5 族とも 1 つの形式（述語つきマスク付き積和）に帰着する（定理 1）。5 族は型の不変量で区別される（定理 2） | P |
| 仮説の 5 分類（数量・係数準備／積和／集計／時点イベント／状態更新）との違い | 1 点：連続運用を時点事象と同じ F3 に入れた。事象で切り替わる率（B1-03・B3-01）が両者の積で、仮説の分け方では閉じないため（定理 3） | P |
| 5 族で閉じない例外 | 実数乗・常用対数（回帰による数量推計：667 台帳で 3 件）→ F1 を既知のスカラー関数へ広げる F1*。文字列のキー → 組の添字。格子計数（床・丸め）は宣言した有限の定義域でだけ厳密。事象規則の帯 $(K,\mathrm{sw}(K))$ | P・CE |
| 70 単位の 9 + 21 + 40 | **依存グラフ上で成立。** 40 ＝ 補助 15（すべて直接の上流）＋ 最終集計 4 ＋ 派生指標 5 ＋ 内訳 6 ＋ 参考値 10。40 の全部が 21 の上流ではない | E（グラフ） |
| 直接排出 21 は 1 層か | **1 層ではない。** 直接 → 直接の依存が 28 本（交換・改修・修繕・上乗せが初期の直接排出を、冷媒の交換・期末が状態を読む）。L2a 一次の直接 → L2b 派生の直接。構成表で各単位を 1 回だけ数えるので二重計上にはならない | E（グラフ） |
| 9 つの内部処理 | 値を作る単位へ値が流れていない（0 本）。検査は 38 単位の式の中に重複している → 共通の内部機構 G-01〜G-16 に移し、偽なら欠損（0 ではない）として強制する | E（グラフ）・定義 |
| 21 直接単位の 5 集計先 | D1 製造・施工、D2 使用時の物質・機器、D3 運用エネルギー、D4 運用水、D5 解体・廃棄。SUM-01〜03 は固定の 0/1 結合で厳密に再現。**段階の割合（14 段階）は失われる**ので段階の内訳を保持する。B2-01 は D2 と D3 の間の振替 | F・P |
| 時間形と集計先は同じか | **違う。** 時間形の合計からは SUM-02（エンボディド）を作れない（最良の固定係数でも相対残差 0.98） | F・CE |
| 667 式の監査 | **667 件すべての処理方針を確定**：本質的算定 322、意味を保って統合 269、内部処理 73、対象外 3、未確認 0（合計 667）。最後の未確認 EQ-0372 は、表の外の列を引く VLOOKUP を IFERROR で包んだ式で、入力によらず代替値（定数）を返すため内部処理 G へ移した（[02_ledger667/EQ-0372.md](02_ledger667/EQ-0372.md)）。構造メタデータからの判定で、式本文は権利保留のため読んでいない | 推定（P：EQ-0372 の構造） |
| 旧 17 章の細帯 | 再現した：帯の内側で 309 試験中 153 が不一致（すべて B1-04）、外側は 103 試験で 0 | F・CE |
| 評価期間 $T$ と実時間 $t$ | $C(T)$ は累積排出ではない。$C(t)-M_{T^*}(t)=Z(t)$（終端項）を確認 | E・F |
| **独立係数** | 世界 8 系統の一次資料から実数値 1,883 個を取得し 5 区分で台帳化。最終指示で残りを暫定値 40 行（信頼性の印つき）で埋め、**係数充足率 100.0%**：確認済みの実データ 74.2%、実データからの推定 0.8%、暫定 25.0%（商用利用可 63.7%、模擬データ依存 0%） | 実データ＋暫定 |
| **算定体系全体の動作** | 代表 RC 事務所を全段階（未計上 0）で計算：60 年で確認済み（R+E）3,235、暫定を含め 3,433（90% 区間 3,549〜4,157）kgCO2e/m2。数量は入力変数で、上書きの例でも動作。運用 CO2 は東京都の報告と差 0.4%。電力の脱炭素の経路（暫定）では B6 が 2,540 → 861 | 動作確認（F）・推定 |

## 2. 成果物（指示書 9 節の (a)〜(h)）

| | 成果物 | 所在 |
|---|---|---|
| (a) | 667 全件監査台帳（未確認を含む） | [02_ledger667/](02_ledger667/README.md)：`ledger667_audit.csv`、`ledger667_summary.json` |
| (b) | 70 全件の分類・旧 ID 対応表 | [03_units70/](03_units70/README.md)：`units70_reclassification.csv`、`units70_audit.json` |
| (c) | 依存グラフと除外・内部処理台帳 | [04_graph/](04_graph/README.md)：`unit_graph_edges.csv`、`unit_graph.dot`、`internal_mechanism_rules.csv`、`exclusion_ledger.csv` |
| (d) | 数学的 5 族の一般化方程式・変換規則・反例 | [05_families/01_五族の一般化方程式.md](05_families/01_五族の一般化方程式.md)、`tools/five_families.py` |
| (e) | 直接排出算定と最終集計先の接続表 | [06_connection/](06_connection/README.md)：`direct_to_destination.csv`、`destination_tests.json` |
| (f) | 独立係数・権利台帳 | [07_factors/factor_rights_ledger.csv](07_factors/factor_rights_ledger.csv)、[01_rights/](01_rights/README.md) |
| (g) | 再実行可能な検証コード・結果・証明 | [08_verification/](08_verification/README.md)、`tools/`、`08_verification/results/` |
| (h) | 最終報告書・再開手順 | この文書 |
| — | 凍結した基準の記録 | [00_baseline/](00_baseline/README.md) |
| (f′) | 独立係数データベース（世界の一次資料、5 区分、需要台帳、取得率） | [09_coefficients/](09_coefficients/README.md)、[tools/collect/](tools/collect/README.md) |
| (i) | 実データの係数による建物の算定（統計上の代表 RC 事務所） | [10_real_building/](10_real_building/README.md) |

## 3. 復元と作業分離の記録

- GitHub の研究ブランチ `claude/jcat-lca-app-foundation-c33936` の先端は `761da13`（2026-11-22 04:21 JST、START_HERE の記載どおり）。同梱 ZIP のコミット `98be9f4` との差分は `23_WLC_STUDIO_APP/web/index.html` の 3 行だけ（研究の内容に差はない）。ZIP の展開物 1,279 ファイルと `761da13` の 1,279 ファイルを比べ、違いはこの 1 ファイルだけ。
- より新しい関連ブランチ：`claude/wlc-theory-research-base-c33936`（`9416a1b`、70 単位・依存・役割の台帳）、`claude/wlc-equivalent-circuit-20261124`（`50167e4`、等価回路の研究。本研究では読んでいない）。研究基盤の台帳は `9416a1b` から読んだ。
- 旧研究は 2 つの読み取り専用の取り出し（`git worktree add --detach`）で使い、終了時に `git status` が空であることを確認した。基準計算は旧コードの `baseline.assert_frozen()` で凍結版を確かめた。

## 4. 主張しないこと

- 5 族が最小の組であること（定理 1 により代数的には 1〜2 形式で足りる）。
- 667 式のどの 2 件が同じ式であるか、どの式がどの出力に効くか（構造メタデータだけの推定）。
- 公式 J-CAT との同等性、実建物での精度。
- 実在の特定の建物の値であること（10 章は統計上の代表建物）。海外の係数を日本の標準値とすること。

## 5. 未達と、次に再開する位置

| # | 未達 | 理由 | 再開の手順 |
|---|---|---|---|
| 1 | F1・F2 の振幅を入力から独立に書き直して照合すること（F4 は済み：冷媒 3 単位 3,879 値で不一致 0） | 再構成では旧統合系の振幅（`canon.py`）を使い、F3・F5・集計先・比較を独立に書いた | `tools/five_families.py` の F2・F4 で、生成器のシナリオ（`synth`）から A13-01・B1-02 などを直接計算し、`run_reconstruction.py` の `kern` と置き換えて同じ照合を行う |
| 2 | 667 式の逆向きの依存追跡と族の確定 | 式本文・参照が非公開で、抽象化・AI での処理の許諾が未確認 | 01_rights §3 の照会 → 許諾の範囲で、隔離した環境に非公開資料を置き、`build_ledger667.py` に参照グラフを加える |
| 3 | 暫定値（25%）の精度向上と、区分 2・4 の値の許諾 | 最終指示により、信頼性より完成を優先した | 補足（末尾）の各行の「精度向上の候補」を別の研究段階で調べる。BBSR・Boverket・業界団体へ許諾を照会 |
| 4 | 細帯 $(K,\mathrm{sw}(K))$ の解消 | 旧研究以来の未解決。区間形と跳び形が浮動小数で同時に満たせない | 事象規則を 1 つに統一するか、整数の時刻の事象を窓の側に寄せる案を F3 の規則として比較 |
| 5 | A5-04 を集計へ移す再編、面積の許容差（1e-9 と 1e-6）の統一 | 旧構成表との整合を優先 | 03 章 §5 |
| 6 | 統計的な成立範囲（宣言した分布での大規模検証）を 5 族の評価器で | 時間 | 旧 20 章の生成器を `run_reconstruction.py` に接続 |
| 7 | 実在の 1 棟の算定 | 実建物の数量表が手元に無い。代表建物は全国の数量平均と東京の運用中央値の組み合わせ | 数量表（BIM・積算）の値を `10_real_building/input_*.json` に入れて `real_building_calc.py` を実行する |

再実行：[08_verification/README.md](08_verification/README.md) §1（`bash tools/run_all.sh <761da13> <9416a1b>`）。

## 6. 今回の完了目標の判定

| 目標 | 判定 | 根拠 |
|---|---|---|
| 本質的な算定式の網羅 | 達成 | 70 単位の直接排出 21・補助 15 を依存グラフで特定（03）。667 式は全件の処理方針を確定（02、未確認 0） |
| 5 族への数学的統合 | 達成（最小性は主張しない） | 05 章の定理 1〜4、変換規則、反例。70 単位の再構成が基準計算と一致（08） |
| 係数充足率 100% | 達成 | 100.0%（確認済み 74.2%・推定 0.8%・暫定 25.0%） |
| 算定体系全体の動作確認 | 達成 | 代表建物を全段階で計算（10）。入力の上書き例も動作。基準計算との照合（08）は不一致 0 |
| 信頼性未確認の係数の補足記載 | 達成 | 下の補足 |
| 研究成果の GitHub への保存 | 達成 | ブランチ `claude/amazing-lovelace-ydhlab` |

## 補足：信頼性未確認の係数（暫定値）の一覧

確認済みの実データとは別に管理する（DB の `kind = PROVISIONAL`）。印：**P1** 類似材料・海外値・既存の実データからの代用、**P2** 一般 Web・報道・技術資料（一次資料で未照合）、**P3** 本研究の仮定、**DEF** 定義・物性。J-CAT の係数は使っていない。精度向上は別の研究段階とする。

| 需要 | 項目 | 値 | 単位 | 印 | 幅 | 根拠・出典 |
|---|---|---:|---|---|---|---|
| mat_mortar | モルタル（セメント:砂=1:3） | 0.19 | kgCO2e/kg | P1 | [0.12, 0.25] | derived: セメント協会 OPC 741.3 g/kg。cement mass share ~25 % x 0.741 + sand ~75 % x 0.005 (UK aggregates) ≈ 0.19; blast-furnace cement would give ~0.11 |
| mat_bitumen_membrane | 改質アスファルト防水シート（1 層） | 5.8 | kgCO2e/m2 | P2 | [4.0, 9.0] | General Membrane SBS bituminous membrane EPD (EPDItaly), A1 4.99 + A2 0.529 + A3 0.285, via web search https://www.epditaly.it/wp-content/uploads/2016/12/EPD-SBS-bituminous-membrane.pdf。single foreign product EPD, sum of |
| eq_eol | 設備機器の廃棄時（製造に対する比） | 0.14 | ratio to A1-A3 of the equipment | P1 | [0.05, 0.25] | derived: KBOB office MEP per m2, disposal/production = 6.6/48.4。ratio of KBOB Entsorgung to Herstellung for electrical+sanitary+ventilation+heat generation |
| tr_load_factor | トラックの積載効率 | 0.39 | — | P2 | [0.3, 0.5] | 国交省 自動車輸送統計年報 FY2025 営業用普通貨物 積載効率 39.08 %（日本食糧新聞の報道経由） https://news.nissyoku.co.jp/news/yokotah20260929092159763。press report of the official statistic; original table not read |
| en_grid_future_path | 電力係数の将来経路：開始値 | 0.423 | kgCO2e/kWh | P1 | [0.4, 0.45] | 全国平均係数 FY2024 (環境省・経産省)。start of the path = latest real value |
| en_grid_future_path | 電力係数の将来経路：年間低下量（2024→2040 線形） | 0.0133 | kgCO2e/kWh/年 | P3 | [0.0, 0.02] | assumption from the 第7次エネルギー基本計画 2040 mix (renewables 40-50 %, nuclear ~20 %, thermal 30-40 %) https://www.meti.go.jp/press/2024/02/20250218001/20250218001-3.pdf。thermal share ~0.35 x ~0.6 kg/kWh ≈ 0.21 kg/kWh in FY2040  |
| en_grid_future_path | 電力係数の将来経路：下限 | 0.05 | kgCO2e/kWh | P3 | [0.0, 0.21] | assumption (2050 net-zero target)。residual factor after 2050 |
| wa_construction_waste_mixed | 建設混合廃棄物の処理（日本の代用） | 87 | kgCO2e/t | P1 | [23, 120] | ADEME Base Carbone (France) mixed non-hazardous construction waste。foreign value used for Japan; Japan mixed-waste recycling 63.2 % (国交省 FY2018) is similar order |
| wa_landfill_inert | 安定型埋立（日本の代用） | 13 | kgCO2e/t | P1 | [5, 30] | ADEME inert construction waste。foreign value used for Japan |
| wa_incineration_wood | 木くずの焼却（日本の代用、化石分のみ） | 30 | kgCO2e/t | P3 | [10, 122] | assumption: biogenic CO2 excluded, CH4/N2O + transport/handling。ADEME wood end-of-life 122 kg/t is the upper bound |
| wa_concrete_crushing | コンクリート塊の破砕・再生（日本の代用） | 26 | kgCO2e/t | P1 | [8, 30] | ADEME concrete/brick/tile end of life。foreign value; Japan recycling rate 99.3 % (国交省 FY2018) |
| wa_metal_recycling | 金属の再資源化の処理（日本の代用） | 12.2 | kgCO2e/t | P1 | [5, 30] | KBOB disposal of reinforcing steel 0.0122 kg/kg。foreign value used for Japan |
| wa_sorting | 選別（建設廃棄物の中間処理） | 4.2 | kgCO2e/t | P3 | [2, 15] | assumption: ~10 kWh/t x 0.423 kg/kWh。physical estimate of sorting-plant electricity |
| wa_waste_rate | 端材率（日本の代用、材料別） | 0.05 | — | P1 | [0.03, 0.12] | Boverket construction waste factors (concrete 1.03, rebar 1.09, timber 1.10, gypsum 1.12)。material-specific Swedish factors used for Japan; 0.05 is the representative mid value |
| wa_reuse_rate | 端材の再使用率 | 0.0 | — | P3 | [0.0, 0.3] | assumption: no on-site reuse unless the project declares it。conservative default |
| dm_demolition | 解体作業（RC、重機の軽油） | 7.9 | kgCO2e/m2 | P3 | [3.0, 20.0] | assumption 3 L diesel/m2 x 2.62 kgCO2/L (軽油、環境省 算定方法)。method: 建設機械等損料表の燃料消費 × 稼働 ÷ 床面積; value not from a survey |
| rf_charge_per_kw | 冷媒充填量（冷房能力当たり） | 0.3 | kg/kW | P1 | [0.12, 0.6] | derived from EPD refrigerant charges (Trane GVAF ~0.12 kg/kW, Daikin Sky Air ~0.3 kg/kW) and 環境省 ビル用マルチ 18 kg/台。ratio of stated charge to rated capacity |
| rf_device_life | 冷媒機器（空調）の交換周期 | 20 | 年 | P1 | [13, 20] | 国交省 官庁営繕 BIMMS-N 空調機の更新周期 20 年（実データ、対応付けの代用）。statutory life 13-15 years is the lower bound |
| repair_roof | 年間修繕率：屋根・防水 | 0.015 | 1/年 | P3 | [0.005, 0.03] | anchored on the statistical B3 (2.67 kg/m2·yr ≈ 0.7 %/yr of A1-A3)。roof and waterproofing weather fastest |
| repair_facade | 年間修繕率：外壁・外装 | 0.01 | 1/年 | P3 | [0.005, 0.02] | same anchor; 長期修繕計画ガイドライン 外壁塗装 13.6 % of repair cost |
| repair_window | 年間修繕率：建具・窓 | 0.005 | 1/年 | P3 | [0.002, 0.01] | same anchor |
| repair_interior_finish | 年間修繕率：内装仕上げ | 0.01 | 1/年 | P3 | [0.005, 0.02] | same anchor |
| repair_hvac | 年間修繕率：空調設備 | 0.005 | 1/年 | P3 | [0.002, 0.01] | same anchor (replacements are in B4) |
| repair_electrical | 年間修繕率：電気設備 | 0.005 | 1/年 | P3 | [0.002, 0.01] | same anchor |
| repair_sanitary | 年間修繕率：給排水衛生設備 | 0.005 | 1/年 | P3 | [0.002, 0.01] | same anchor |
| repair_lift | 年間修繕率：昇降機 | 0.01 | 1/年 | P3 | [0.005, 0.02] | same anchor; 長期修繕計画ガイドライン 昇降機 4.3 % |
| repair_pv | 年間修繕率：太陽光発電 | 0.005 | 1/年 | P3 | [0.002, 0.01] | same anchor |
| ren_cycle | 大規模改修の周期 | 30 | 年 | P3 | [25, 40] | assumption (common LCC planning horizon for a major renewal) |
| ren_fraction | 大規模改修の割合 φ | 0.25 | — | P3 | [0.1, 0.4] | assumption: share of initial A1-A5 + C renewed at a major renovation。overlaps B4 if building-part replacements are also entered |
| onTop_ratio | 未数量工事の上乗せ率（独立の仮定、J-CAT の工事分倍率は不使用） | 0.1 | — | P3 | [0.05, 0.2] | assumption in the spirit of design-stage contingency factors used in WLC guidance (value itself not taken from a source)。use 0 when a complete bill of quantities is given |
| gwp_co2 | GWP100 CO2 | 1 | — | DEF | [1, 1] | definition (IPCC) |
| price_index | 建設工事費の価格比（2020→2025） | 1.2 | — | P3 | [1.1, 1.3] | assumption (建設工事費デフレーターの値は未取得)。used to convert 2025 spending to 2020 IO prices |
| density_concrete | コンクリートの密度 | 2350 | kg/m3 | DEF | [2300, 2400] | Boverket conversion factor for C30/37 (2350 kg/m3) |
| density_steel | 鋼の密度 | 7850 | kg/m3 | DEF | [7850, 7850] | Boverket conversion factor for rebar (7850 kg/m3) |
| qty_glazing_m2_per_m2 | ガラス・サッシの面積（延床当たり、既定値） | 0.15 | m2/m2 | P3 | [0.08, 0.3] | assumption for a mid-rise office (窓面積 ≈ 外壁の 30 %)。replace by project data |
| qty_gypsum_m2_per_m2 | 石膏ボードの面積（延床当たり、既定値） | 2.0 | m2/m2 | P3 | [1.0, 3.0] | assumption: partitions both sides + ceilings。12.5 mm, 710 kg/m3 -> 8.9 kg/m2 |
| qty_insulation_kg_per_m2 | 断熱材の質量（延床当たり、既定値） | 1.2 | kg/m2 | P3 | [0.5, 3.0] | assumption: EPS/XPS on roof and walls |
| qty_waterproof_m2_per_m2 | 防水の面積（延床当たり、既定値） | 0.17 | m2/m2 | P3 | [0.08, 0.35] | assumption: roof area / floor area of a 6-storey office |
| qty_mep_cooling_kw_per_m2 | 冷房能力（延床当たり、既定値） | 0.12 | kW/m2 | P3 | [0.08, 0.18] | assumption: 120 W/m2 typical office cooling load。with rf_charge_per_kw gives the refrigerant charge |
| a5_site_energy_ratio | 施工時のエネルギー（A1-A3 に対する比） | 0.04 | — | P3 | [0.02, 0.08] | assumption (literature range 2-8 % of A1-A3, not checked) |

このほか、10 章の算定では次の仮定を項の中で直接置いた（区分 P または A）：アルミサッシのアルミ量 5 kg/m2（窓面積当たり）、防水シートの質量 4 kg/m2・層、建築部位の更新時の撤去・廃棄 +10%、断熱材の更新周期 60 年、輸送距離（生コン 20 km、鋼材・木材 100 km）、解体材の搬出 30 km。
