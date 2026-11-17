# -*- coding: utf-8 -*-
"""70 評価単位の完全台帳を原典から作る（WLC_THEORY_RESEARCH_BASE/02 と data/units70.json・units70.csv・unit_dependencies.csv）。

使い方（作業木のどこからでも。python3 -B、WLCSTUDIO_OFFLINE=1）：
    python3 -B tools/check_units70.py --n 60 --t-per-scenario 3 --dirty 6 --special 3 --ref --time-probe 10 \
        --knots 8 --knots-events 40 --knots-lattice 12 --sensitivity 3 --sens-trials 2 --json <OUT.json>   # 照合（約 30 分）
    python3 -B tools/extract_units70.py --check-summary <OUT.json>                 # 台帳と 02 を作り直す
    （--check-summary を省くと、前回の data/units70.json に埋めた照合の結果を引き継ぐ。data/units70_inputs.csv は
      内容が変わるときも既定では書き換えず units70_inputs.csv.new に置く：--write-inputs-csv で書き換える。
      --split-md <名前> で 02 の 5.8 節から後を別のファイルに分ける）
    独立の照合（c2）での訂正は「c2_corrections」の節（FIELDS・UCUR の上書き、SITES・X02_CHK・NOTATION_PATTERNS・
    INDEX_SOURCES・C2_FIXES）にまとめてある。

機械的に抽出するもの：単位の名前・段階・構造の区分・依存（09 章 units.json）、基準計算の定義文と依存の宣言
（refcalc の登録、読み取り専用）、導出・構造の経路・出力キー（UNITS_70.md の表）、仕様のステップ数・スペクトル・
到達する入力（unit_map.json）、統一系と基準計算の照合の件数（verification_*.json）、T への依存の分類
（17 章 units_time.json）、誤り検出の表（VERIFICATION.md 5 節）、各出典の最後のコミット（git log、読み取りだけ）。
手で書いたもの（このファイルの前半の FIELDS・DEFAULT・OVERRIDE・NOTATION・EXTRA_VERIF・UCUR）：入力の記号・単位・
定義域、出力の意味、役割の区分と理由、条件、LaTeX の式と T の形、係数の対応、注記。式の実行形は
tools/units70_eval_src.py（各単位の eval_py）。どれも本研究の架空の係数と独立概念モデルだけを扱い、J-CAT 原版の
式・係数・値は含まない。
"""

# ======== cur_fields.py ========
# 入力の項目（unit_map.json の表.列）ごとの記号・単位・定義域・意味。
# 記号は 17 章 02 の 2.1 節・第 11 章 UNITS_70 の記法に合わせ、無いものは本台帳で導入（NEW と書く）。
# 単位・定義域は架空データの生成器（09 章 synth/model.py の docstring）と、式が値を使う条件（台帳の式の述語）から書いた。
# 「定義域」は式が値を使う範囲。範囲外・欠損（⊥）の値は述語で外され、件数に数えられる（0 とはみなさない）。
FIELDS = {
 # ---- 共通の表 ----
 "factors.key": ("f", "—", "係数の ID", "係数の記録の ID（シナリオ内で一意）"),
 "factors.value": ("F_f", "kgCO2e/u_f", "実数（架空データでは ≥ 0）", "係数の値（係数の単位 u_f あたり）"),
 "factors.unit": ("u_f", "—", "単位の文字列", "係数の分母の単位（kg、m3、tkm、kWh など）"),
 "factors.stages#": ("|\\mathrm{stg}_f|", "—", "整数 ≥ 0", "係数が覆う段階の個数（ちょうど 1 個のときだけ使える）"),
 "factors.stages.value": ("\\mathrm{stg}_f", "—", "段階の名前の一覧", "係数が覆う段階"),
 "factors.licence_status": ("\\mathrm{lic}_f", "—", "PERMITTED_PUBLIC ほか 4 状態", "使用許諾の状態（PERMITTED_PUBLIC のときだけ使える）"),
 "factors.source_url": ("\\mathrm{src}_f", "—", "文字列（空は不可）", "出典（架空の synthetic:// 参照）"),
 "factors.valid_until": ("\\mathrm{vu}_f", "—", "ISO 日付または ⊥", "有効期限（EPD の判定に使う）"),
 "factors.release_year": ("\\mathrm{ry}_f", "年", "整数", "公開年（SUM-08 の「係数の版」の比較）"),
 "factors.gas_amounts.key": ("g", "—", "ガス名", "ガスの名前（CO2、CH4 など 7 種）"),
 "factors.gas_amounts.value": ("\\mathrm{ga}_{f,g}", "kg/u_f", "≥ 0", "係数 f の単位あたりのガス g の量（X-04・X-05）"),
 "gases.value": ("g\\in\\mathrm{GAS}", "—", "ガス名の一覧", "ガスのベクトルの順序"),
 "gwp.key": ("g", "—", "ガス名", "GWP の表のキー"),
 "gwp.value": ("\\mathrm{GWP}_g", "kgCO2e/kg", "≥ 0（CO2 は 1）", "ガス g の地球温暖化係数（架空）"),
 "unit_conversions.from_unit": ("a", "—", "単位", "換算の元の単位"),
 "unit_conversions.to_unit": ("b", "—", "単位", "換算の先の単位"),
 "unit_conversions.factor": ("\\mathrm{cv}(a\\to b)", "b/a", "> 0", "全体の換算倍率（連鎖・逆算はしない）"),
 "provenance.key": ("\\mathrm{pid}", "—", "ID", "出典記録の ID"),
 "provenance.value_state": ("\\delta", "—", "OBSERVED / ESTIMATE / DERIVED", "出典記録が宣言する値の状態（SYS-01）"),
 # ---- 建物・境界 ----
 "project.gross_floor_area": ("A", "m2", "A > 0 で有効", "延床面積"),
 "project.assessment_date": ("t_{\\mathrm{as}}", "—", "ISO 日付", "評価日（EPD の有効期限と比べる）"),
 "project.provenance_id": ("\\mathrm{pid}", "—", "ID", "出典記録の参照（SYS-01）"),
 "project.use_area_breakdown": ("A_v", "m2", "≥ 0", "用途 v ごとの床面積（SYS-04）"),
 "boundary.study_period": ("T", "年", "0 < T ≤ H", "評価期間（実時間 t とは別）"),
 "boundary.included_lifecycle_stages.value": ("\\iota_s", "—", "段階の部分集合", "評価範囲に入る段階（ι_s = 1）"),
 "boundary.reconstruction_scenario": ("\\mathrm{rs}", "—", "NONE / REBUILD_IDENTICAL / MAJOR_REFURBISHMENT", "大型改修・建替のシナリオ"),
 "boundary.reconstruction_scope_fraction": ("\\varphi", "—", "0 ≤ φ ≤ 1 で有効", "大型改修の規模（初期排出に対する割合）"),
 "boundary.replacement_cycle": ("C_{\\mathrm{ren}}", "年", "> 0・有限で事象あり", "大型改修・建替の周期"),
 "boundary.baseline_scenario": ("b", "—", "シナリオ ID または ⊥", "比較の基準案（SUM-08）"),
 "boundary.results_gas_scope": ("\\mathrm{gs}", "—", "CO2E_ALL_GASES / CO2_ONLY", "結果のガスの範囲（SUM-08 の比較条件）"),
 # ---- 資材の行 i ----
 "materials.quantity": ("Q_i", "u_i（行の数量単位）", "Q_i ≥ 0 で有効", "数量"),
 "materials.quantity_unit": ("u_i", "—", "単位", "数量の単位"),
 "materials.quantity_basis": ("\\mathrm{qb}_i", "—", "DESIGN / ORDERED / AS_BUILT", "数量の基準（DESIGN なら端材を足して発注量にする）"),
 "materials.waste_rate": ("w_i", "—", "0 ≤ w_i < 1 で有効", "端材率（年重み w_k(T) とは別物：添字が行 i で引数 T を持たない）"),
 "materials.reuse_rate": ("\\rho^{\\mathrm{reuse}}_i", "—", "0 ≤ ρ ≤ 1 で有効", "端材の再使用率（X-13）"),
 "materials.material_life": ("L_i", "年", "> 0", "資材の寿命（70 単位の式では使わない。valid_domain の刃の判定だけ）"),
 "materials.repair_rate": ("r_i", "1/年", "r_i ≥ 0 で有効", "年間修繕率"),
 "materials.refresh_cycle": ("c_i", "年", "> 0・有限で事象あり", "更新周期（事象 τ_n = n c_i）"),
 "materials.factor_id": ("f_i", "—", "ID または ⊥", "汎用係数の参照（単体の行）"),
 "materials.composition#": ("[\\mathrm{comp}_i\\ne\\bot]", "—", "0/1", "複合品の行か"),
 "materials.composition.factor_id": ("f_{ij}", "—", "ID", "構成材 j の係数（kg あたり）"),
 "materials.composition.mass_fraction": ("\\mathrm{mf}_{ij}", "—", "≥ 0、Σ_j = 1（±1e-6）", "構成材 j の質量比（NEW 記号）"),
 "materials.epd#": ("[\\mathrm{epd}_i\\ne\\bot]", "—", "0/1", "製品固有値（EPD）の宣言があるか"),
 "materials.epd.factor_id": ("f^{\\mathrm{epd}}_i", "—", "ID", "EPD の係数の参照"),
 "materials.epd.declared_stages#": ("|\\mathrm{stg}^{\\mathrm{epd}}_i|", "—", "整数", "EPD が宣言する段階の個数"),
 "materials.epd.declared_stages.value": ("\\mathrm{stg}^{\\mathrm{epd}}_i", "—", "段階の一覧", "EPD が宣言する段階（係数の記録と一致が必要）"),
 "materials.epd.declared_unit": ("u^{\\mathrm{epd}}_i", "—", "単位", "EPD の宣言単位（係数の単位と一致が必要）"),
 "materials.epd.valid_until": ("\\mathrm{vu}^{\\mathrm{epd}}_i", "—", "ISO 日付", "EPD の有効期限（係数の記録と一致し、評価日以後であること）"),
 "materials.conversions.from_unit": ("a", "—", "単位", "行固有の換算の元"),
 "materials.conversions.to_unit": ("b", "—", "単位", "行固有の換算の先"),
 "materials.conversions.factor": ("\\mathrm{cv}_i(a\\to b)", "b/a", "> 0", "行固有の換算倍率（全体の換算より先に探す）"),
 "materials.installation_factor_id": ("f^{\\mathrm{inst}}_i", "—", "ID または ⊥", "更新時の据付の係数（段階 A5、数量単位あたり）"),
 "materials.unquantified_cost_ratio": ("r^{\\mathrm{uq}}_i", "—", "0 < r < 1 で計上（0 は寄与 0）", "数量のない工事の割合（A13-04。NEW 記号：UNITS_70 の r）"),
 "materials.material_class": ("\\mathrm{cls}_i", "—", "13 区分", "資材区分（X-09・X-17）"),
 "materials.construction_division": ("\\mathrm{div}_i", "—", "5 区分", "工事区分（X-17 の ENVELOPE・INTERIOR）"),
 "materials.provenance_id": ("\\mathrm{pid}_i", "—", "ID", "出典記録の参照（SYS-01）"),
 "materials.transport.mass_t": ("M^{\\mathrm{tr}}_i", "t", "≥ 0 で有効", "輸送質量"),
 "materials.transport.distance_km": ("D^{\\mathrm{tr}}_i", "km", "≥ 0 で有効", "輸送距離"),
 "materials.transport.factor_id": ("f^{\\mathrm{tr}}_i", "—", "ID", "輸送手段の係数（tkm あたり、段階 A4）"),
 "materials.transport.load_factor": ("\\lambda^{\\mathrm{load}}_i", "—", "> 0 で有効", "積載率（X-12。NEW 記号）"),
 "materials.transport.delivery_factor_id": ("f^{\\mathrm{del}}_i", "—", "ID または ⊥", "製品別の搬入係数（数量単位あたり。あれば A4-02、なければ A4-01）"),
 "materials.end_of_life.mass_kg": ("m^{\\mathrm{eol}}_i", "kg", "≥ 0 で有効", "廃棄質量"),
 "materials.end_of_life.haul_distance_km": ("D^{\\mathrm{haul}}_i", "km", "≥ 0 で有効", "廃棄物の搬出距離"),
 "materials.end_of_life.haul_factor_id": ("f^{\\mathrm{haul}}_i", "—", "ID", "搬出の係数（tkm あたり、段階 C2）"),
 "materials.end_of_life.routes.route": ("\\mathrm{rt}_{ij}", "—", "REUSE / RECYCLE / PROCESSING / LANDFILL", "処理経路"),
 "materials.end_of_life.routes.fraction": ("\\mathrm{fr}_{ij}", "—", "≥ 0 で有効（Σ_j は 1 を想定）", "経路の比率（NEW 記号：UNITS_70 の 比率_ij）"),
 "materials.end_of_life.routes.factor_id": ("f_{ij}", "—", "ID", "経路の係数（kg あたり。LANDFILL は C4、他は C3）"),
 # ---- 設備の行 j ----
 "equipment.quantity": ("Q_j", "unit", "≥ 0 で有効", "台数"),
 "equipment.quantity_unit": ("u_j", "—", "単位（unit）", "数量の単位"),
 "equipment.factor_id": ("f_j", "—", "ID", "製造の係数（台あたり、段階 A1-A3）"),
 "equipment.service_life": ("c_j", "年", "> 0・有限で事象あり", "耐用年数（交換年一覧が無いときの更新周期）"),
 "equipment.replacement_event_list#": ("[L_j\\ne\\bot]", "—", "0/1", "交換年一覧があるか"),
 "equipment.replacement_event_list.value": ("L_j", "年", "0 < τ < T(1−ε) の要素だけ数える", "交換年一覧（評価開始からの年数）"),
 "equipment.repair_rate": ("r_j", "1/年", "≥ 0 で有効", "年間修繕率"),
 "equipment.end_of_life_mass_kg": ("m^{\\mathrm{eol}}_j", "kg", "≥ 0 で有効", "廃棄質量"),
 "equipment.eol_factor_id": ("f^{\\mathrm{eol}}_j", "—", "ID または ⊥", "廃棄の係数（kg あたり、段階 C3）"),
 "equipment.delivery_factor_id": ("f^{\\mathrm{del}}_j", "—", "ID または ⊥", "搬入の係数（台あたり、段階 A4。更新時だけ使う）"),
 "equipment.installation_factor_id": ("f^{\\mathrm{inst}}_j", "—", "ID または ⊥", "据付の係数（台あたり、段階 A5。更新時だけ使う）"),
 "equipment.provenance_id": ("\\mathrm{pid}_j", "—", "ID", "出典記録の参照（SYS-01）"),
 # ---- 冷媒の機器 d ----
 "refrigerants.charge_mass_kg": ("m_{0,d}", "kg", "≥ 0 で有効", "初期充填量"),
 "refrigerants.gwp": ("\\mathrm{GWP}_d", "kgCO2e/kg", "≥ 0 で有効", "冷媒の GWP（架空）"),
 "refrigerants.annual_leak_rate": ("r_d", "1/年", "0 ≤ r_d ≤ 1 で有効", "年間漏洩率"),
 "refrigerants.replacement_loss_rate": ("\\lambda_{\\mathrm{loss}}", "—", "0 ≤ λ ≤ 1 で有効", "交換時の損失率（機器ごと）"),
 "refrigerants.end_of_life_recovery_rate": ("\\eta_d", "—", "0 ≤ η ≤ 1 で有効", "廃棄時の回収率"),
 "refrigerants.change_years#": ("[L_d\\ne\\bot]", "—", "0/1", "交換年一覧があるか"),
 "refrigerants.change_years.value": ("L_d", "年", "0 < τ < T(1−ε) の要素だけ数える", "交換年一覧"),
 "refrigerants.service_life": ("c_d", "年", "> 0・有限で事象あり", "耐用年数（一覧が無いときの交換周期）"),
 "refrigerants.top_up": ("\\mathrm{tu}_d", "—", "真偽", "毎年補充するか（q_d = 1 か 1 − r_d か）"),
 "refrigerants.provenance_id": ("\\mathrm{pid}_d", "—", "ID", "出典記録の参照（SYS-01）"),
 "refrigerants.__no_value__": ("—", "—", "—", "述語だけが読む行の存在（値は読まない）"),
 # ---- 施工現場 ----
 "construction.electricity_kwh": ("E^{\\mathrm{site}}", "kWh", "≥ 0 で有効", "工事期間の買電量（A5-01）"),
 "construction.fuels.quantity": ("Q_x", "u_x", "≥ 0 で有効", "施工燃料の量（行 x）"),
 "construction.fuels.unit": ("u_x", "—", "単位", "燃料の単位"),
 "construction.fuels.factor_id": ("f_x", "—", "ID", "燃料の係数（段階 A5）"),
 "construction.waste_streams.mass_kg": ("m_x", "kg", "≥ 0 で有効", "工事廃棄物の質量（行 x）"),
 "construction.waste_streams.factor_id": ("f_x", "—", "ID", "工事廃棄物の係数（kg あたり、段階 A5）"),
 "construction.provenance_id": ("\\mathrm{pid}", "—", "ID", "出典記録の参照（SYS-01）"),
 # ---- 運用 ----
 "operation.electricity.kind": ("\\mathrm{kind}", "—", "CONSTANT / LINEAR_TREND / TABLE", "買電需要の記述子の種類"),
 "operation.electricity.base": ("c^{\\mathrm{base}}", "kWh/年", "実数", "記述子の初年の値"),
 "operation.electricity.slope": ("c^{\\mathrm{slope}}", "kWh/年²", "実数", "記述子の傾き"),
 "operation.electricity.table.value": ("c_k", "kWh/年", "≥ 0", "買電需要（自家消費の差し引き前）の年次表"),
 "operation.electricity.unit": ("u^{\\mathrm{el}}", "—", "「X/year」の形（それ以外は aunit が ⊥）", "買電需要の単位"),
 "operation.onsite_generation.unit": ("u^{\\mathrm{gen}}", "—", "「X/year」", "発電の単位"),
 "operation.onsite_export.unit": ("u^{\\mathrm{exp}}", "—", "「X/year」", "売電の単位"),
 "operation.gas.unit": ("u^{\\mathrm{gas}}", "—", "「X/year」", "ガスの単位"),
 "operation.oil.unit": ("u^{\\mathrm{oil}}", "—", "「X/year」", "油の単位"),
 "operation.district_heat.unit": ("u^{\\mathrm{dh}}", "—", "「X/year」", "地域熱の単位"),
 "water_waste.water.unit": ("u^{\\mathrm{wat}}", "—", "「X/year」", "上水の単位"),
 "water_waste.sewage.unit": ("u^{\\mathrm{sew}}", "—", "「X/year」", "下水の単位"),
 "water_waste.municipal_waste.unit": ("u^{\\mathrm{msw}}", "—", "「X/year」", "一般廃棄物の単位"),
 "operation.onsite_generation.kind": ("\\mathrm{kind}", "—", "同上", "発電の記述子"),
 "operation.onsite_generation.base": ("g^{\\mathrm{base}}", "単位/年", "実数", "記述子"),
 "operation.onsite_generation.slope": ("g^{\\mathrm{slope}}", "単位/年²", "実数", "記述子"),
 "operation.onsite_generation.table.value": ("g_k", "単位/年", "≥ 0", "オンサイト発電の年次表"),
 "operation.onsite_export.kind": ("\\mathrm{kind}", "—", "同上", "売電の記述子"),
 "operation.onsite_export.base": ("x^{\\mathrm{base}}", "単位/年", "実数", "記述子"),
 "operation.onsite_export.slope": ("x^{\\mathrm{slope}}", "単位/年²", "実数", "記述子"),
 "operation.onsite_export.table.value": ("x_k", "単位/年", "≥ 0", "売電（系統への送電）の年次表"),
 "operation.gas.kind": ("\\mathrm{kind}", "—", "同上", "ガスの記述子"),
 "operation.gas.base": ("v^{\\mathrm{base}}", "m3/年", "実数", "記述子"),
 "operation.gas.slope": ("v^{\\mathrm{slope}}", "m3/年²", "実数", "記述子"),
 "operation.gas.table.value": ("v^{\\mathrm{gas}}_k", "m3/年", "≥ 0", "ガスの年次表"),
 "operation.gas_factor_id": ("f^{\\mathrm{gas}}", "—", "ID", "ガスの係数（段階 B6）"),
 "operation.oil.kind": ("\\mathrm{kind}", "—", "同上", "油の記述子"),
 "operation.oil.base": ("v^{\\mathrm{base}}", "L/年", "実数", "記述子"),
 "operation.oil.slope": ("v^{\\mathrm{slope}}", "L/年²", "実数", "記述子"),
 "operation.oil.table.value": ("v^{\\mathrm{oil}}_k", "L/年", "≥ 0", "油の年次表"),
 "operation.oil_factor_id": ("f^{\\mathrm{oil}}", "—", "ID", "油の係数（段階 B6）"),
 "operation.district_heat.kind": ("\\mathrm{kind}", "—", "同上", "地域熱の記述子"),
 "operation.district_heat.base": ("v^{\\mathrm{base}}", "MJ/年", "実数", "記述子"),
 "operation.district_heat.slope": ("v^{\\mathrm{slope}}", "MJ/年²", "実数", "記述子"),
 "operation.district_heat.table.value": ("v^{\\mathrm{dh}}_k", "MJ/年", "≥ 0", "地域熱の年次表"),
 "operation.district_heat_factor_id": ("f^{\\mathrm{dh}}", "—", "ID", "地域熱の係数（段階 B6）"),
 "operation.grid.kind": ("\\mathrm{kind}_\\gamma", "—", "CONSTANT / LINEAR_DECLINE_TO_FLOOR / STEPWISE / TABLE", "電力係数の記述子の種類"),
 "operation.grid.start": ("\\gamma^{\\mathrm{start}}", "kgCO2e/kWh", "実数", "記述子の初年の値"),
 "operation.grid.annual_decline": ("\\gamma^{\\mathrm{dec}}", "kgCO2e/kWh/年", "≥ 0（整った記述子）", "直線の低下の幅"),
 "operation.grid.floor": ("\\gamma^{\\mathrm{floor}}", "kgCO2e/kWh", "≤ start（整った記述子）", "下限"),
 "operation.grid.steps#": ("|\\mathrm{steps}|", "—", "整数", "段階の記述子の段数"),
 "operation.grid.table.value": ("\\gamma^{\\mathrm{tab}}_k", "kgCO2e/kWh", "≥ 0", "電力係数の年次表"),
 "operation.grid.construction_value": ("\\gamma^{\\mathrm{con}}", "kgCO2e/kWh", "≥ 0", "工事期間の電力係数（A5-01）"),
 "operation.grid.licence_status": ("\\mathrm{lic}_\\gamma", "—", "PERMITTED_PUBLIC ほか", "電力係数の使用許諾"),
 "operation.grid.unit": ("u_\\gamma", "—", "kgCO2e/<電力の単位>", "電力係数の単位（分母 u_g を読む）"),
 "operation.electricity_per_m2_per_year": ("I^{\\mathrm{el}}", "kWh/m2/年", "≥ 0 で有効", "床面積あたりの電力原単位（X-11）"),
 "operation.facility_management_ratio": ("\\rho_{\\mathrm{B2}}", "—", "0 ≤ ρ ≤ 1 で有効", "施設管理に帰属させる買電の割合"),
 "operation.provenance_id": ("\\mathrm{pid}", "—", "ID", "出典記録の参照"),
 # ---- 水・廃棄物 ----
 "water_waste.water.kind": ("\\mathrm{kind}", "—", "CONSTANT / LINEAR_TREND / TABLE", "上水の記述子"),
 "water_waste.water.base": ("v^{\\mathrm{base}}", "m3/年", "実数", "記述子"),
 "water_waste.water.slope": ("v^{\\mathrm{slope}}", "m3/年²", "実数", "記述子"),
 "water_waste.water.table.value": ("v^{\\mathrm{wat}}_k", "m3/年", "≥ 0", "上水の年次表"),
 "water_waste.water_factor_id": ("f^{\\mathrm{wat}}", "—", "ID", "上水の係数（段階 B7）"),
 "water_waste.sewage.kind": ("\\mathrm{kind}", "—", "同上", "下水の記述子"),
 "water_waste.sewage.base": ("v^{\\mathrm{base}}", "m3/年", "実数", "記述子"),
 "water_waste.sewage.slope": ("v^{\\mathrm{slope}}", "m3/年²", "実数", "記述子"),
 "water_waste.sewage.table.value": ("v^{\\mathrm{sew}}_k", "m3/年", "≥ 0", "下水の年次表"),
 "water_waste.sewage_factor_id": ("f^{\\mathrm{sew}}", "—", "ID", "下水の係数（段階 B7）"),
 "water_waste.municipal_waste.kind": ("\\mathrm{kind}", "—", "同上", "一般廃棄物の記述子"),
 "water_waste.municipal_waste.base": ("v^{\\mathrm{base}}", "kg/年", "実数", "記述子"),
 "water_waste.municipal_waste.slope": ("v^{\\mathrm{slope}}", "kg/年²", "実数", "記述子"),
 "water_waste.municipal_waste.table.value": ("v^{\\mathrm{msw}}_k", "kg/年", "≥ 0", "一般廃棄物の年次表"),
 "water_waste.waste_factor_id": ("f^{\\mathrm{msw}}", "—", "ID", "一般廃棄物の係数（段階 B7）"),
 # ---- 解体 ----
 "end_of_life.demolition_activities.quantity": ("Q_x", "u_x", "≥ 0 で有効", "解体作業の量（行 x）"),
 "end_of_life.demolition_activities.unit": ("u_x", "—", "単位", "解体作業の単位"),
 "end_of_life.demolition_activities.factor_id": ("f_x", "—", "ID", "解体作業の係数（段階 C1）"),
 "end_of_life.waste_hauls.mass_t": ("M_x", "t", "≥ 0 で有効", "資材の行に含まれない廃棄物の搬出質量"),
 "end_of_life.waste_hauls.distance_km": ("D_x", "km", "≥ 0 で有効", "搬出距離"),
 "end_of_life.waste_hauls.factor_id": ("f_x", "—", "ID", "搬出の係数（tkm あたり、段階 C2）"),
 "end_of_life.provenance_id": ("\\mathrm{pid}", "—", "ID", "出典記録の参照（SYS-01）"),
 # ---- 要約数量・費用 ----
 "summary_quantities.reinforcement_kg": ("q_{\\mathrm{REBAR}}", "kg", "実数（0 なら区分は 0）", "鉄筋の要約数量（X-17）"),
 "summary_quantities.steel_kg": ("q_{\\mathrm{STEEL}}", "kg", "実数（0 なら区分は 0）", "鉄骨の要約数量"),
 "summary_quantities.concrete_m3": ("q_{\\mathrm{CONC}}", "m3", "実数（X-17 では 0 なら区分は 0。STO-02 では ≥ 0 で有効）", "コンクリートの要約数量"),
 "summary_quantities.timber_m3": ("q_{\\mathrm{TIMB}}", "m3", "実数（X-17 では 0 なら区分は 0。STO-01 では ≥ 0 で有効）", "木材の要約数量"),
 "summary_quantities.envelope_m2": ("q_{\\mathrm{ENV}}", "m2", "実数（0 なら区分は 0）", "外皮の要約面積"),
 "summary_quantities.interior_m2": ("q_{\\mathrm{INT}}", "m2", "実数（0 なら区分は 0）", "内装の要約面積"),
 "summary_quantities.timber_dry_density_kg_per_m3": ("\\varrho^{\\mathrm{dry}}", "kg/m3", "≥ 0 で有効", "木材の絶乾密度（架空。NEW 記号）"),
 "summary_quantities.timber_carbon_fraction": ("c^{\\mathrm{C}}", "—", "≥ 0 で有効", "木材の炭素含有率（架空。NEW 記号）"),
 "summary_quantities.concrete_uptake_factor_id": ("f^{\\mathrm{upt}}", "—", "ID または ⊥", "炭酸化による吸収の係数（段階 MEMO、m3 あたり）"),
 "cost_items.amount": ("P_x", "通貨（架空）", "≥ 0 で有効", "費用（価格年の水準）"),
 "cost_items.currency": ("u_x", "—", "通貨の名前", "通貨（係数の単位でもある）"),
 "cost_items.price_year": ("y^{\\mathrm{p}}_x", "暦年", "整数", "費用の価格年"),
 "cost_items.factor_base_year": ("y^{\\mathrm{b}}_x", "暦年", "整数", "係数の基準年"),
 "cost_items.factor_id": ("f_x", "—", "ID", "費用あたりの係数（段階 A1-A3）"),
 "price_index.key": ("y", "暦年", "整数", "物価指数の年"),
 "price_index.value": ("I_y", "—", "> 0 で有効", "物価指数（架空）"),
}

# ======== cur_outputs.py ========
# 出力キーの意味・単位。既定（キー名ごと）と単位ごとの上書き。
DEFAULT = {
 "value": ("V_u", "kgCO2e", "単位の値（段階の述語を掛ける前）"),
 "by_item": ("V_{u,i}", "kgCO2e", "入力の行ごとの値（除外の行は 0.0）。行の順は入力と同じ"),
 "n_skipped": ("n_{\\mathrm{skip}}", "件", "述語が偽で除外した行の数（0 とみなさず数える）"),
 "by_year": ("(s_y)_{y=0}^{Y}", "kgCO2e（年次量は kgCO2e/年×重み）", "年 y ごとの値。添字 0 は時点 0 の欄、y = 1..Y は評価年"),
 "computed": ("[\\mathrm{ok}]", "真偽", "述語が真で計算したか"),
 "descriptors_match_tables": ("\\mathrm{same}", "真偽", "年次量の記述子と年次表が相対 1e-12 で一致するか"),
 "ok": ("\\mathrm{ok}", "真偽", "判定の結果"),
 "violations": ("—", "場所の一覧", "違反の場所（文字列）"),
 "complete": ("\\mathrm{complete}", "真偽", "対象段階に除外・部分・未計算の単位が無いか（X-02）"),
 "status": ("—", "列挙", "判定・比較の状態"),
 "n_routes_skipped": ("n_{\\mathrm{routes\\,skip}}", "件", "除外した処理経路の数"),
}
OVERRIDE = {
 ("A13-02", "by_item"): ("F^{\\mathrm{comp}}_i", "kgCO2e/kg", "複合品の行の係数（複合でない行・不良の行は ⊥）"),
 ("A13-02", "n_invalid"): ("n_{\\mathrm{invalid}}", "件", "不良の構成の複合品の行の数"),
 ("A13-05", "q_ord"): ("q^{\\mathrm{ord}}_i", "u_i", "発注量（不良の行は ⊥）"),
 ("A13-05", "q_inst"): ("q^{\\mathrm{inst}}_i", "u_i", "据付量（不良の行は ⊥）"),
 ("A5-04", "parts"): ("—", "kgCO2e", "A5-01・A5-02・A5-03 の値（power・fuels・waste）"),
 ("A5-04", "other_assessed"): ("—", "真偽", "定数の偽（その他の施工負荷は評価しない）"),
 ("B1-02", "by_item"): ("V_{u,d}", "kgCO2e", "機器ごとの漏洩"),
 ("B4-01", "events"): ("E_j(T)", "年の一覧", "設備ごとの数えた事象の時刻"),
 ("B4-01", "n_events"): ("\\sum_j|E_j(T)|", "件", "事象の総数"),
 ("B4-02", "by_item_material"): ("V_{u,i}", "kgCO2e", "資材の行ごとの更新排出"),
 ("B4-02", "by_item_equipment"): ("V_{u,j}", "kgCO2e", "設備の行ごとの更新排出"),
 ("B4-02", "n_partial"): ("n_{\\mathrm{partial}}", "件", "事象を持ち構成要素が欠けた行の数"),
 ("B4-03", "by_item"): ("n_i(T)", "回", "資材の行ごとの更新回数"),
 ("B5-01", "n_events"): ("N_{C_{\\mathrm{ren}}}(T)", "回", "数えた改修の回数（述語が偽なら 0）"),
 ("B6-01", "by_year"): ("(0,e_0,\\dots,e_{Y-1})", "kgCO2e/年", "年ごとの買電排出"),
 ("B6-02", "by_year"): ("(0,f_0,\\dots,f_{Y-1})", "kgCO2e/年", "年ごとの燃料排出"),
 ("B6-04", "by_year"): ("(0,n_0,\\dots,n_{Y-1})", "kWh/年", "年ごとの正味の買電量"),
 ("B7-01", "by_year"): ("(0,b^{\\mathrm{wat}}_k)", "kgCO2e/年", "年ごとの上水の排出"),
 ("B7-02", "by_year"): ("(0,b^{\\mathrm{sew}}_k)", "kgCO2e/年", "年ごとの下水の排出"),
 ("B7-03", "by_year"): ("(0,b^{\\mathrm{msw}}_k)", "kgCO2e/年", "年ごとの一般廃棄物の排出"),
 ("X-06", "by_year"): ("(0,\\gamma_0,\\dots,\\gamma_{Y-1})", "kgCO2e/kWh", "年ごとの電力係数"),
 ("X-06", "matches_table"): ("\\mathrm{same}", "真偽", "記述子と年次表の一致"),
 ("X-06", "source"): ("—", "DESCRIPTOR / TABLE", "使った方"),
 ("C-05", "under_allocated"): ("—", "場所の一覧", "比率の和が 1 未満の行"),
 ("C-05", "n_mass_unchecked"): ("n_{\\mathrm{unchecked}}", "件", "質量を点検できなかった行の数"),
 ("SYS-01", "counts"): ("n_s", "件", "状態ごとの件数"),
 ("SYS-02", "n_checked"): ("|\\mathcal{S}|", "件", "調べた箇所の数"),
 ("SYS-02", "stage_mismatches"): ("—", "係数の一覧", "段階が合わない係数"),
 ("SYS-03", "n_checked"): ("|\\mathcal{S}'|+1", "件", "調べた参照の数"),
 ("SYS-03", "n_references_affected"): ("n_{\\mathrm{affected}}", "件", "違反の参照の数"),
 ("SYS-04", "sum"): ("S_A", "m2", "用途別面積の和"),
 ("SYS-04", "residual"): ("r", "m2", "残差（INVALID なら ⊥）"),
 ("SYS-04", "status"): ("—", "EVALUATED / INVALID", "判定の状態"),
 ("QA-04", "status"): ("—", "EVALUATED / NOT_EVALUATED", "判定の状態"),
 ("QA-02", "warnings"): ("—", "場所の一覧", "時刻 0 を含む一覧"),
 ("QA-03", "n_used"): ("n_{\\mathrm{used}}(T)", "件", "使われた係数の数"),
 ("STO-01", "value"): ("V_u", "kgCO2（貯蔵量、正）", "参考値（欠損なら ⊥）"),
 ("STO-02", "value"): ("V_u", "kgCO2e（吸収、係数の符号のまま）", "参考値（欠損なら ⊥）"),
 ("SUM-01", "value"): ("S_1(T)", "kgCO2e", "アップフロント"),
 ("SUM-02", "value"): ("S_2(T)", "kgCO2e", "エンボディド"),
 ("SUM-03", "value"): ("C(T)", "kgCO2e", "ホールライフ合計"),
 ("SUM-04", "value"): ("C/A", "kgCO2e/m2", "延床面積あたり（⊥ あり）"),
 ("SUM-05", "value"): ("C/(AT)", "kgCO2e/m2/年", "年平均・延床面積あたり（⊥ あり）"),
 ("SUM-06", "value"): ("10^{-3}C", "tCO2e", "t 換算"),
 ("SUM-07", "by_stage"): ("\\mathrm{share}_s", "—", "段階の割合（定義されないとき空）"),
 ("SUM-07", "defined"): ("—", "真偽", "割合が定義されるか"),
 ("SUM-08", "baseline"): ("C^b", "kgCO2e", "基準案の合計（比較したときだけ）"),
 ("SUM-08", "delta"): ("\\Delta", "kgCO2e", "差（比較できなければ ⊥）"),
 ("SUM-08", "saving"): ("\\rho^{\\mathrm{save}}", "—", "削減率（⊥ あり）"),
 ("SUM-08", "reasons"): ("—", "理由の一覧", "比較できない理由"),
 ("SUM-08", "status"): ("—", "NO_BASELINE / NOT_COMPARABLE / COMPARED", "比較の状態"),
 ("X-02", "by_stage"): ("\\mathrm{bs}_s(T)", "kgCO2e", "対象段階の値（対象外の段階はキーなし）"),
 ("X-02", "by_stage_all"): ("\\mathrm{full}_s(T)", "kgCO2e", "述語を掛けない 14 段階の値"),
 ("X-02", "incomplete_units"): ("—", "単位の一覧", "不完全の原因の単位"),
 ("X-03", "mass_by_component"): ("\\mathrm{mass}_f", "kg", "構成材の係数ごとの質量"),
 ("X-03", "emission_by_component"): ("\\mathrm{em}_f", "kgCO2e", "構成材ごとの排出"),
 ("X-04", "by_gas"): ("\\mathrm{bg}_g(T)", "kg（ガス）", "ガスごとの量"),
 ("X-04", "co2e_from_gases"): ("\\sum_g\\mathrm{GWP}_g\\mathrm{bg}_g", "kgCO2e", "ガスからの CO2e"),
 ("X-04", "grid_co2e"): ("\\mathrm{GRID}(T)", "kgCO2e", "買電の擬似の行の和"),
 ("X-04", "refrigerant_co2e"): ("\\mathrm{REFR}(T)", "kgCO2e", "冷媒の擬似の行の和"),
 ("X-04", "by_stage_recomputed"): ("\\mathrm{recomp}_s(T)", "kgCO2e", "行による段階の足し直し（述語なし）"),
 ("X-05", "by_stage_co2"): ("\\mathrm{CO2}_s(T)", "kgCO2", "段階ごとの CO2 だけの値（全 14 段階）"),
 ("X-07", "by_year"): ("(s_y)_{y=0}^{Y}", "kgCO2e", "年ごとの排出（0 は A 段階、最終年に C 段階と B1-04）"),
 ("X-07", "cumulative"): ("(\\mathrm{cum}_y)", "kgCO2e", "累積"),
 ("X-07", "value"): ("\\mathrm{cum}_Y=C(T)", "kgCO2e", "累積の最後"),
 ("X-08", "by_cycle"): ("(N_c,U_c,E_c)", "回・kgCO2e", "周期ごとの回数・1 回の排出・排出"),
 ("X-08", "explicit"): ("\\mathrm{explicit}(T)", "kgCO2e", "交換年一覧の設備の更新排出"),
 ("X-09", "mass"): ("\\mathrm{mass}[c,\\varrho]", "kg", "区分×経路の質量"),
 ("X-09", "emission"): ("\\mathrm{em}[c,\\varrho]", "kgCO2e", "区分×経路の排出"),
 ("X-10", "resource_kg"): ("\\mathrm{res}(T)", "kg", "資源投入量（更新を含む）"),
 ("X-10", "waste_kg"): ("\\mathrm{waste}(T)", "kg", "廃棄物量（更新を含む）"),
 ("X-10", "n_excluded"): ("n_{\\mathrm{excl}}", "件", "除外した行"),
 ("X-11", "value"): ("V_u(T)", "kgCO2e", "推定値（述語が偽なら ⊥）"),
 ("X-13", "by_item"): ("\\mathrm{net}_i", "u_i", "正味の発注量（⊥ あり）"),
 ("X-13", "waste_by_item"): ("\\mathrm{waste}_i", "u_i", "再使用されない端材（⊥ あり）"),
 ("X-15", "kind"): ("\\mathrm{kind}_i", "EPD / COMPOSITE / GENERIC / ⊥", "行ごとの係数の種類"),
 ("X-15", "factor"): ("F^\\ast_i", "kgCO2e/単位", "行ごとの係数"),
 ("X-15", "conv"): ("c^\\ast_i", "倍率", "行ごとの換算倍率"),
 ("X-15", "n_unresolved"): ("n_{\\mathrm{unres}}", "件", "係数を決められない行"),
 ("X-15", "n_epd_declined"): ("n_{\\mathrm{decl}}", "件", "EPD を退けた行"),
 ("X-17", "by_class"): ("(q_c,\\bar f_c,e_c)", "—", "区分ごとの要約数量・代表係数・排出"),
 ("QA-01", "violations"): ("—", "一覧", "(a)(b)(c) の違反"),
}

# ======== cur_notation.py ========
# 本台帳の共通記号（02 の 2 節）。(記号, 定義, 出典・新旧)
NOTATION = [
 (r"$[P]$, $\neg[P]$", r"述語の値（0/1）。欠損 $\bot$ に当てた述語は 0、否定は 1。項の述語がすべて 1 のときだけ項が寄与し、1 つでも 0 なら値が欠けていても寄与は厳密に 0（マスク）。", "14 章 04 の 2 節、SPEC_MSP 2 節"),
 (r"$\bot$", r"未知値（欠損、None）。0 とは区別し、0 とみなさない。", "14 章 04 の 2 節"),
 (r"$[v\ge0]$, $[0\le v\le1]$, $[v>0]$", r"本台帳では値の有無と有限性を含めて読む：$[v\ne\bot][v\text{ は真偽値でない}][0\le v<\infty]$ など。実行形の `nn`・`rat`・`pos`。", "本台帳（実行形の約束）"),
 (r"$\mathrm{cv}_i(a\to b)$, $\mathrm{cv}(a\to b)$", r"単位の換算倍率：$a=b$ なら 1、次に行固有の換算、次に全体の換算。連鎖・逆算はしない。無ければ $\bot$。", "SPEC_MSP 5 節のテンプレート CONV（記号は本台帳で導入）"),
 (r"$\mathrm{G}_s(f,u)$", r"係数ゲート：$[f\ne\bot][f\in\mathtt{factors}][\mathrm{lic}_f=\mathrm{PERMITTED\_PUBLIC}][\mathrm{stg}_f=(s)][\mathrm{cv}(u\to u_f)\ne\bot]$（段階はちょうど $s$ の 1 つ）。UNITS_70 の「係数が使える」。", "SPEC_MSP 5 節の FACTOR・STAGE（記号は本台帳で導入）"),
 (r"$\mathcal{F}_s(f,u)$", r"ゲート付きの換算済み係数 $\mathrm{G}_s(f,u)\cdot\mathrm{cv}(u\to u_f)\cdot F_f$（ゲートが 0 なら $\mathrm{cv}$・$F$ が欠けていても 0）。", "本台帳で導入"),
 (r"$\mathrm{aunit}(u)$, $\mathrm{gunit}(u_\gamma)$", r"年次量の単位「X/year」の X（それ以外は $\bot$）、電力係数の単位「kgCO2e/X」の X。", "本台帳で導入（統一系は文字列を共通表で分割：unit_map の tokens）"),
 (r"$v_k$（年次量）", r"記述子が使えれば記述子（CONSTANT：base、LINEAR_TREND：base + slope·k）、使えなければ年次表の $k$ 番目。", "SPEC_MSP 5 節の PROFILE"),
 (r"$\mathrm{same}(v,t)$", r"2 つの系列が要素ごとに $a=b$ または $\lvert a-b\rvert\le10^{-12}\max(\lvert a\rvert,\lvert b\rvert)$。", "SPEC_MSP 5 節の CLOSE"),
 (r"$T$, $t$, $H$", r"評価期間（年、$0<T\le H$）、実時間（排出の時刻）、年次表の長さ（架空データで 130）。$T$ への依存と実時間 $t$ は別物。", "17 章 02 の 1 節"),
 (r"$Y=\lceil T\rceil$, $k$, $y=k+1$", r"最後の評価年、年セルの番号、年の番号。", "17 章 01 の 7 節"),
 (r"$w_k(T)$", r"年重み $\operatorname{clip}(T-k,0,1)$。実行形の `wy(T,y)` は $w_{y-1}(T)$（$y\le Y$）。端材率 $w_i$（行の添字、$T$ なし）とは別。", "17 章 01 の 2 節"),
 (r"$\theta_\varepsilon(T;\tau)$, $\varepsilon$", r"事象の規則 $[\tau<T(1-\varepsilon)]$、$\varepsilon=10^{-9}$。浮動小数では $\tau<\mathrm{fl}(T\,\mathrm{fl}(1-\varepsilon))$ で、$T\ge\mathrm{sw}(\tau)$ で数える。", "17 章 01 の 2 節、03 の L-2"),
 (r"$k_\tau$, $y(\tau)$", r"事象が属する年セル $\max(1,\lceil\tau(1-\varepsilon)\rceil)-1$ と年 $y(\tau)=k_\tau+1$。", "17 章 02 の 1 節"),
 (r"$E^{\mathrm{per}}(T;c)$, $E^{\mathrm{lst}}(T;L)$", r"周期の事象 $\{nc:n\ge1,\theta_\varepsilon(T;nc)\}$（$c$ が欠損・非正・無限なら空、$nc$ は浮動小数の積）と、一覧の事象 $(\tau\in L:\tau>0,\theta_\varepsilon(T;\tau))$（一覧の順と重複を保つ）。", "SPEC_KNOTS 2 節（記号は本台帳で導入）"),
 (r"$n_i(T)$, $N_c(T)$, $E_j(T)$", r"資材の行の更新回数 $|E^{\mathrm{per}}(T;c_i)|$、周期 $c$ の回数、設備の事象（B4-01）。", "UNITS_70、17 章 02"),
 (r"$V_u(T)$", r"単位 $u$ の値（段階の述語を掛ける前）。14 章 07 の $v_u(T)$。", "17 章 01 の 1 節"),
 (r"$\iota_s$, $\sigma_{s,u}$, $\beta_{s,u}$", r"段階の述語（評価範囲）、構成表の符号（(B6, B2-01) だけ −1）、B2 を数えるときだけ B6 から B2-01 を引く述語（(B6, B2-01) は $\iota_{\mathrm{B2}}$）。", "17 章 02 の 3 節"),
 (r"$a01_i$, $a03_i$, $a41_i$, $a42_i$, $c21_i$, $c31_i$, $c41_i$, $x01_j$, $x14_j$", r"A13-01・A13-03・A4-01・A4-02・C2-01・C3-01・C4-01・X-01・X-14 の行ごとの値（by_item）。UNITS_70 の a01_i・a03_i に揃えた。", "UNITS_70（他は本台帳で同じ形に拡張）"),
 (r"$\mathcal{U}_C$", r"$C(T)$ に直接入る 21 単位の集合（本基盤の 03 で導入）。", "本基盤 03"),
]

# 単位ごとの追加の検証の記録（原典の節を指す）。
EXTRA_VERIF = {
 "B1-02": [
  {"class": "E", "short": "倍化の恒等式を SymPy・SageMath で厳密に確認（D-08）", "claim": "倍化の因数分解 $\\prod_{i<m}(I+N^{2^i})=\\sum_{j<2^m}N^j$ を SymPy（記号の重み、n=8・16）と SageMath（有理数、n=64）で厳密に確認。漸化式と 8 因子の積は有理数で完全一致（40 機器）", "scope": "D-08 の (d)。恒等式そのものは帰納法で証明済み [P]", "source": "DER", "section": "D-08 ⑦⑧"},
  {"class": "F", "short": "状態 u＝基準計算の内部状態（3.4e-15、EXP-U3）", "claim": "状態 $u$（交換直前の量 4,975 個、期末の量 1,689 個）が基準計算の内部状態と 3.4e-15 以内で一致（EXP-U3）", "scope": "第 11 章の検証集合", "source": "DER", "section": "D-08 ⑦⑧"},
 ],
 "B1-03": [
  {"class": "F", "short": "最大相対差 2.6e-14（同じ年に 3 回の交換）", "claim": "相対差の最大 2.6e-14（同じ年に 3 回の交換を置いた特殊条件）", "scope": "第 11 章の 10 集合", "source": "DER", "section": "D-08 ⑦⑧"},
 ],
 "B1-04": [
  {"class": "F", "short": "EXP-U1：区間形 6.6e-15、跳び形 6e+21（真値は mpmath 60 桁）", "claim": "EXP-U1（mpmath 60 桁の漸化式を真値、45 条件）：最大相対誤差は基準計算 4.6e-16、跳び形 6e+21、区間形 6.6e-15、局所形 6.7e-15", "scope": "45 条件（強く減衰する冷媒を含む）。冷媒状態の数値誤差の測定", "source": "DER", "section": "D-09 ⑦⑧"},
  {"class": "F", "short": "跳び形は 9 件不一致、区間形 0 件", "claim": "跳び形を厳密に評価しても強く減衰する冷媒で基準計算と 9 件の不一致（係数が浮動小数で丸められているため）。区間形は 0 件", "scope": "1,293 組", "source": "T07", "section": "1.3 B1-04 の跳び形"},
  {"class": "F", "short": "帯 (K, sw(K)) で 9 組中 2 組が最大相対 5.5e-3 異なる（未解決）", "claim": "帯 $T\\in(K,\\mathrm{sw}(K))$ では区間形・統一系とも基準計算と異なりうる（整数の時刻の 9 組中 2 組で B1-04 の最大相対 5.5e-3、SUM-03 で 1.1e-5）。浮動小数の整数の近くの事象の場合は未確認", "scope": "一覧の交換年（整数）を持つ冷媒のシナリオ。未解決の切り替え境界", "source": "T07", "section": "6. 整数時刻の交換の直後の帯"},
 ],
 "X-11": [
  {"class": "F", "short": "比 X11/G が一定（120 シナリオ・799 点、不一致 0）", "claim": "比 $X11(T)/G(T)$ が各シナリオで一定（相対 1e-12）。125 シナリオ（比が定義される 120）・799 点で不一致 0", "scope": "5 集合の先頭 30 シナリオ、定義域の内側", "source": "T07", "section": "7. 合計に入らない T 依存の出力の式"},
 ],
 "X-07": [
  {"class": "F", "short": "年の分割の式 823 点で不一致 0、TH-4 との違いは条件と完全に対応", "claim": "by_year を核の項の年セルの分割として照合（823 点、不一致 0、最大 2.8e-16）。cumulative・value も 0。TH-4 の年ごとの分解との違いは条件（年セルの年と切り替え点の年が違う事象がある）と完全に対応（776 点）", "scope": "同上", "source": "T07", "section": "7."},
 ],
 "X-08": [
  {"class": "F", "short": "回数の式 295,953 件で不一致 0", "claim": "count が $\\#\\{n\\ge1:\\mathrm{fl}(nc)<\\mathrm{fl}(T\\,\\mathrm{fl}(1-\\varepsilon))\\}$ と一致（295,953 周期×点、不一致 0）。整数の一致だが浮動小数の規則の上での照合なので F とする", "scope": "同上", "source": "T07", "section": "7."},
 ],
 "B4-01": [
  {"class": "F", "short": "一覧と件数の式 199,715 件で不一致 0", "claim": "$T$ での一覧が $T=H$ の一覧の $\\tau<\\mathrm{fl}(T\\,\\mathrm{fl}(1-\\varepsilon))$ の部分、件数がその和（199,715 一覧、不一致 0）", "scope": "同上", "source": "T07", "section": "7."},
 ],
 "B4-03": [
  {"class": "F", "short": "回数の式 664,625 件で不一致 0", "claim": "行ごとの回数の式と一致（664,625 行×点、不一致 0）", "scope": "同上", "source": "T07", "section": "7."},
 ],
 "B5-01": [
  {"class": "F", "short": "n_events の式 823 点で不一致 0", "claim": "n_events の述語つきの回数の式と一致（823 点、不一致 0）", "scope": "同上", "source": "T07", "section": "7."},
 ],
 "X-04": [
  {"class": "F", "short": "by_stage_recomputed 11,522 件で不一致 0（by_gas は未照合）", "claim": "by_stage_recomputed が段階の述語なしの $\\sum\\sigma V_u(T)$ と一致（11,522 段階値、最大 6.2e-15）。by_gas は照合していない", "scope": "同上", "source": "T07", "section": "7."},
 ],
 "X-05": [
  {"class": "F", "short": "区分一次の確認だけ（重みごとの式は未照合）", "claim": "区分一次であることだけを確認（重みごとの式は照合していない）", "scope": "17 章 06 の標本", "source": "T07", "section": "7.（X-05 は照合していない）"},
 ],
 "X-10": [
  {"class": "F", "short": "時間の式は 17 章で未照合", "claim": "時間の式（質量の重みつきの回数の和）は 17 章では照合していない。値は第 11 章で基準計算と一致", "scope": "—", "source": "T07", "section": "7.（X-10 は照合していない）"},
 ],
 "B3-01": [
  {"class": "F", "short": "密度は率で持つ必要（fl(aH) では 0 を再現できない組 1）", "claim": "密度の振幅を浮動小数の積 $\\mathrm{fl}(aH)$ で持つと、基準計算が厳密に 0 を返す B3 の値を 0 にできない組がある（dev_edge の 1 組、-9.8e-12）。率 $a$ で持つと 0 組", "scope": "dev_edge の定義域の内側 62 組", "source": "T07", "section": "1.2 密度の振幅を率で持つ理由"},
 ],
 "SUM-03": [
  {"class": "F", "short": "正準形＝基準計算 1,293 組で不一致 0（最大 1.0e-13）", "claim": "正準形 vs 基準計算：1,293 組で不一致 0、最大相対 1.0e-13。正準形 vs 統一系：相対 1e-12 で不一致 0", "scope": "D'", "source": "T07", "section": "1."},
  {"class": "S", "short": "V1 で失敗 0（95% 上限 1.7e-4／シナリオ）", "claim": "V1（理想方程式の SUM-03 と基準計算）で失敗 0、99% 点 3.1e-14、最大 2.5e-13。シナリオあたりの失敗確率の 95% 片側上限 1.7e-4", "scope": "宣言した分布、定義域の内側 90,055 ケース", "source": "V20", "section": "1. 全体"},
  {"class": "P", "short": "TH-1〜TH-3・TH-13", "claim": "区分一次（TH-1）、跳び（TH-2）、導関数（TH-3）、$H$ によらないこと（TH-13）", "scope": "D'（TH-2 の 3 の帯を除く）", "source": "T03", "section": "TH-1〜TH-3、TH-13"},
 ],
 "X-02": [
  {"class": "S", "short": "V2 で失敗 0（1,376,449 段階値）", "claim": "V2（14 段階の値）で失敗 0（1,376,449 個の段階の値）", "scope": "宣言した分布の定義域の内側", "source": "V20", "section": "1. 全体"},
 ],
 "QA-01": [
  {"class": "F", "short": "故障注入 4/4（入力からは違反を起こせない）", "claim": "QA-01 の違反は入力では起こせない（D-12）。上流の結果を両側で同じように偽る故障注入 4 件で、基準計算と同じ違反一覧になった（4/4）", "scope": "故障注入だけ（入力からの検出力は未確認：LIMITS 7 の 5）", "source": "VER11", "section": "5. 誤り検出の確認（QA-01 の故障注入）"},
 ],
}

UCUR = {}

# ======== cur_units_a.py ========
# 台帳の手書き部分（その 1：検査・製品段階・輸送・施工・参考値）。
# 記法は 02 の 2 節（本台帳の共通記号）。"@A13-01" は \mathrm{A13\text{-}01} に置き換える。
# 各単位：stage（09 章 units.json の段階）、comp（14 章 07 の構成表 COMP での段階と符号）、role / role2、why（役割の理由）、
# inputs（その単位の式が直接読む入力の項目）、cond（条件とマスク）、msp（マスク付き積和の形の式）、time（T の形）、
# coef（係数と元の入力の対応、本研究の架空の係数だけ）、consts（式の中の固定の定数）、notes（注意・未解決）。
U = {}  # この部分の単位

U["SYS-01"] = dict(
 stage="PRE", comp=[], role="DECISION", role2=None,
 why="入力値の状態（欠損・導出・明示の 0・実測・推定）を数えて報告する判定。結果はどの単位の値にも入らない（各単位は自分の述語で欠損を外す）。",
 inputs=["provenance.value_state", "project.gross_floor_area", "materials.quantity", "materials.waste_rate", "materials.reuse_rate",
         "materials.material_life", "materials.repair_rate", "materials.refresh_cycle", "materials.transport.mass_t",
         "materials.transport.distance_km", "materials.end_of_life.mass_kg", "equipment.quantity", "equipment.service_life",
         "equipment.repair_rate", "equipment.end_of_life_mass_kg", "refrigerants.charge_mass_kg", "refrigerants.gwp",
         "refrigerants.annual_leak_rate", "refrigerants.replacement_loss_rate", "refrigerants.end_of_life_recovery_rate",
         "refrigerants.service_life", "construction.electricity_kwh", "construction.fuels.quantity",
         "construction.waste_streams.mass_kg", "end_of_life.demolition_activities.quantity", "end_of_life.waste_hauls.mass_t",
         "end_of_life.waste_hauls.distance_km"],
 cond=r"調べる項目の集合 $P$ は 26 種類（延床面積 1、資材 9、設備 4、冷媒 6、施工 3、解体 3）。設備の耐用年数は交換年一覧があれば調べない。冷媒の耐用年数は耐用年数と交換年一覧の両方が無いときだけ欠損として数える。$\delta_p$ は行の `states` の宣言、無ければ出典記録の `value_state`、記録が無ければ MISSING。",
 msp=r"$$\mathrm{st}(p)=\begin{cases}\mathrm{MISSING}& v_p=\bot\\ \mathrm{DERIVED}& v_p\ne\bot,\ \delta_p=\mathrm{DERIVED}\\ \mathrm{EXPLICIT\_ZERO}& v_p\ne\bot,\ \delta_p\ne\mathrm{DERIVED},\ v_p=0\\ \delta_p & \text{それ以外}\end{cases}\qquad n_s=\sum_{p\in P}[\mathrm{st}(p)=s],\quad \mathrm{ok}=[n_{\mathrm{MISSING}}=0]$$",
 time=r"$T$ によらない。",
 coef="係数なし（数え上げ）。", consts=[],
 notes="値があっても出典記録が無ければ状態は MISSING になり、違反に数える（宣言の欠如を欠損とみなす規則）。場合分けは積和では排他的な述語の和（SPEC_MSP 3 節の型）。",
)

U["SYS-02"] = dict(
 stage="PRE", comp=[], role="DECISION", role2=None,
 why="単位の整合（換算できるか）と係数の段階の整合を報告する判定。各単位の値は自分の係数ゲートで同じ条件を独立に掛けるので、この結果は値に入らない。",
 inputs=["materials.quantity_unit", "materials.conversions.factor", "factors.unit", "factors.stages.value", "unit_conversions.factor",
         "operation.grid.unit", "construction.fuels.unit", "end_of_life.demolition_activities.unit", "cost_items.currency"],
 cond=r"使う箇所の一覧 $\mathcal{S}$（資材の数量・構成・搬入・輸送・据付・搬出・経路、設備の 4 種、工事の電力・燃料・廃棄物、運用の 9 系列、解体・搬出、炭酸化、費用）の各箇所 $\sigma$ は（数量の単位 $a_\sigma$、係数 $f_\sigma$ または換算先の単位、期待する段階 $s_\sigma$）を持つ。年次量の単位は「単位/year」の分母を読む。",
 msp=r"$$\mathrm{viol}_\sigma=[a_\sigma=\bot]+[a_\sigma\ne\bot][f_\sigma\in\mathtt{factors}][\mathrm{cv}(a_\sigma\to u_{f_\sigma})=\bot]\ \ (\text{換算先が単位の箇所は }[a=\bot\lor b=\bot\lor \mathrm{cv}(a\to b)=\bot]),\qquad \mathrm{mis}_f=\textstyle\sum_{\sigma: f_\sigma=f}[\mathrm{stg}_f\ne(s_\sigma)]$$ $$\mathrm{ok}=\Big[\textstyle\sum_\sigma\mathrm{viol}_\sigma=0\Big]\Big[\textstyle\sum_f[\mathrm{mis}_f\ge1]=0\Big],\qquad n_{\mathrm{checked}}=|\mathcal{S}|$$",
 time=r"$T$ によらない。",
 coef="係数なし（判定）。", consts=[],
 notes="違反の場所は重複を除いて整列した一覧。係数の記録が無い箇所は SYS-02 では数えない（SYS-03 が数える）。",
)

U["SYS-03"] = dict(
 stage="PRE", comp=[], role="DECISION", role2=None,
 why="係数の参照（ID の有無・記録の有無・使用許諾・出典）を報告する判定。値への作用は各単位の係数ゲート $\\mathrm{G}_s$ が独立に持つ。",
 inputs=["factors.key", "factors.licence_status", "factors.source_url", "operation.grid.licence_status"],
 cond=r"参照の一覧 $\mathcal{S}'$（`synth.model.factor_references` と同じ順の全参照箇所と、炭酸化・費用の参照）。電力係数の許諾は別に 1 件。",
 msp=r"$$\mathrm{key}(\sigma)=[f_\sigma=\bot]\,\text{“無い参照”}+[f_\sigma\ne\bot][f_\sigma\notin\mathtt{factors}]\,\text{“記録なし”}+[f_\sigma\in\mathtt{factors}]\big[\mathrm{lic}_{f}\ne\mathrm{PERMITTED\_PUBLIC}\ \lor\ \mathrm{src}_f=\text{空}\big]\,\text{“許諾”}$$ $$n_{\mathrm{affected}}=\sum_{\sigma\in\mathcal{S}'}[\mathrm{key}(\sigma)\ne\emptyset]+[\mathrm{lic}_\gamma\ne\mathrm{PERMITTED\_PUBLIC}],\qquad \mathrm{ok}=[n_{\mathrm{affected}}=0],\qquad n_{\mathrm{checked}}=|\mathcal{S}'|+1$$",
 time=r"$T$ によらない。",
 coef="係数なし（判定）。", consts=[],
 notes="SYS-03 は出典が空の係数も違反に数えるが、各単位の係数ゲート $\\mathrm{G}_s$ は出典を見ない（許諾・段階・換算だけ）。出典の欠けは QA-03 と SYS-03 が報告する。",
)

U["SYS-04"] = dict(
 stage="PRE", comp=[], role="DECISION", role2=None,
 why="延床面積と用途別面積の和の整合を判定する。残差は QA-04 が使うが、排出の値には入らない。",
 inputs=["project.gross_floor_area", "project.use_area_breakdown"],
 cond=r"用途名の昇順に足す（浮動小数の和の順序を固定）。",
 msp=r"$$S_A=\sum_{v\ (\text{昇順})}A_v,\qquad r=[A>0]\,(A-S_A),\qquad \mathrm{ok}=[A>0]\,[\,r\le10^{-9}A\,]\,[\,-r\le10^{-9}A\,]$$",
 time=r"$T$ によらない。", coef="係数なし。", consts=["1e-9（相対の許容差）"],
 notes="$A$ が欠損または非正なら status = INVALID、残差は ⊥。",
)

U["QA-04"] = dict(
 stage="QA", comp=[], role="DECISION", role2=None,
 why="SYS-04 の残差を緩い許容差（1e-6）で判定し直す検算。値に入らない。",
 inputs=["project.gross_floor_area"],
 cond=r"SYS-04 の status が EVALUATED のときだけ判定する。",
 msp=r"$$\mathrm{ok}=[\mathrm{status}_{@SYS-04}=\mathrm{EVALUATED}]\,[\,r_{@SYS-04}\le10^{-6}A\,]\,[\,-r_{@SYS-04}\le10^{-6}A\,]$$",
 time=r"$T$ によらない。", coef="係数なし。", consts=["1e-6（相対の許容差）"], notes="",
)

U["A13-05"] = dict(
 stage="A1-A3", comp=[], role="AUXILIARY", role2=None,
 why="資材の行の発注量・据付量を作る補助の量。A13-01・A13-03・A4-02・B4-02・X-10・X-13・C-05 の入力になり、それ自体は段階の値ではない。",
 inputs=["materials.quantity", "materials.waste_rate", "materials.quantity_basis"],
 cond=r"$\mathrm{ok}_i=[Q_i\ge0][0\le w_i<1]$。偽の行は ⊥（None）で、件数に数える。",
 msp=r"$$q^{\mathrm{ord}}_i=\mathrm{ok}_i\Big([\mathrm{qb}_i=\mathrm{DESIGN}]\,Q_i\,\frac{1}{1-w_i}+[\mathrm{qb}_i\ne\mathrm{DESIGN}]\,Q_i\Big),\qquad q^{\mathrm{inst}}_i=\mathrm{ok}_i\Big([\mathrm{qb}_i=\mathrm{DESIGN}]\,Q_i+[\mathrm{qb}_i\ne\mathrm{DESIGN}]\,Q_i(1-w_i)\Big),\qquad n_{\mathrm{skip}}=\sum_i(1-\mathrm{ok}_i)$$",
 time=r"$T$ によらない。", coef=r"$q^{\mathrm{ord}}_i$ は数量 $Q_i$ と端材率 $w_i$ だけから作る（係数なし）。$1/(1-w)$ は積和の 1 列の関数 `inv_one_minus`。", consts=[], notes="",
)

U["X-13"] = dict(
 stage="A1-A3", comp=[], role="REFERENCE", role2=None,
 why="端材の再使用を考えた正味の発注量（代替値）。どの段階の値・合計にも入らない。",
 inputs=["materials.reuse_rate"],
 cond=r"$[q^{\mathrm{ord}}_i\ne\bot][0\le\rho^{\mathrm{reuse}}_i\le1]$。偽なら ⊥。",
 msp=r"$$\mathrm{waste}_i=[q^{\mathrm{ord}}_i\ne\bot][0\le\rho^{\mathrm{reuse}}_i\le1]\,(q^{\mathrm{ord}}_i-q^{\mathrm{inst}}_i)(1-\rho^{\mathrm{reuse}}_i),\qquad \mathrm{net}_i=[\cdots]\,\big(q^{\mathrm{inst}}_i+\mathrm{waste}_i\big)$$",
 time=r"$T$ によらない。", coef="係数なし（物量）。", consts=[],
 notes="全単位の中で基準計算との相対差が最大（2.2e-12）。$q^{\\mathrm{ord}}-q^{\\mathrm{inst}}$ の引き算の桁落ち（浮動小数の誤差。式の違いではない）。",
)

U["A13-02"] = dict(
 stage="A1-A3", comp=[], role="AUXILIARY", role2=None,
 why="複合品の行の係数（kg あたり）を構成比から作る中間量。X-15 を通して A13-01 の係数になる。値そのものは段階に入らない。",
 inputs=["materials.composition#", "materials.composition.factor_id", "materials.composition.mass_fraction"],
 cond=r"複合品の行（構成あり）だけ。全構成材の係数ゲート $\mathrm{G}_{\mathrm{A1\text{-}A3}}(f_{ij},\mathrm{kg})$ と $[\mathrm{mf}_{ij}\ge0]$、比の和の検査。偽なら ⊥ で $n_{\mathrm{invalid}}$ に数える。",
 msp=r"$$\mathrm{ok}^{\mathrm{c}}_i=\prod_j\mathrm{G}_{\mathrm{A1\text{-}A3}}(f_{ij},\mathrm{kg})\,[\mathrm{mf}_{ij}\ge0]\cdot\Big[\Big|\sum_j\mathrm{mf}_{ij}-1\Big|\le10^{-6}\Big],\qquad F^{\mathrm{comp}}_i=\mathrm{ok}^{\mathrm{c}}_i\sum_j\mathrm{mf}_{ij}\,\mathrm{cv}(\mathrm{kg}\to u_{f_{ij}})\,F_{f_{ij}}$$",
 time=r"$T$ によらない。", coef=r"$F^{\mathrm{comp}}_i$（kgCO2e/kg）＝構成材の架空の係数 $F_{f_{ij}}$ の質量比の重みつきの和。",
 consts=["1e-6（比の和の許容差）"], notes="",
)

U["X-15"] = dict(
 stage="PRE", comp=[], role="AUXILIARY", role2="DECISION",
 why="資材の行ごとに係数の種類（EPD・複合・汎用）を排他的に選び、係数と換算倍率を渡す。A13-01 と A13-03 の切り替え（相互排他）を決めるスイッチでもある。値は段階に入らない。",
 inputs=["materials.epd#", "materials.epd.factor_id", "materials.epd.declared_stages.value", "materials.epd.declared_unit",
         "materials.epd.valid_until", "factors.valid_until", "project.assessment_date", "materials.factor_id",
         "materials.quantity_unit", "materials.conversions.factor"],
 cond=r"$\mathrm{E}_i=[\mathrm{epd}_i\ne\bot][f^{\mathrm{epd}}_i\in\mathtt{factors}][\mathrm{stg}^{\mathrm{epd}}_i=\mathrm{stg}_f][u^{\mathrm{epd}}_i=u_f][\mathrm{vu}^{\mathrm{epd}}_i=\mathrm{vu}_f\ne\bot][\neg(\mathrm{vu}_f<t_{\mathrm{as}})]\,\mathrm{G}_{\mathrm{A1\text{-}A3}}(f^{\mathrm{epd}}_i,u_i)$（日付は ISO 文字列の比較）。",
 msp=r"$$[\mathrm{kind}_i=\mathrm{EPD}]=\mathrm{E}_i,\quad [\mathrm{kind}_i=\mathrm{COMP}]=(1-\mathrm{E}_i)[\mathrm{comp}_i\ne\bot][F^{\mathrm{comp}}_i\ne\bot][\mathrm{cv}_i(u_i\to\mathrm{kg})\ne\bot],\quad [\mathrm{kind}_i=\mathrm{GEN}]=(1-\mathrm{E}_i)[\mathrm{comp}_i=\bot]\,\mathrm{G}_{\mathrm{A1\text{-}A3}}(f_i,u_i)$$ $$(F^{\ast}_i,\ c^{\ast}_i)=[\mathrm{EPD}]\,(F_{f^{\mathrm{epd}}_i},\mathrm{cv}_i(u_i\to u_f))+[\mathrm{COMP}]\,(F^{\mathrm{comp}}_i,\mathrm{cv}_i(u_i\to\mathrm{kg}))+[\mathrm{GEN}]\,(F_{f_i},\mathrm{cv}_i(u_i\to u_{f_i})),\qquad n_{\mathrm{unres}}=\sum_i\big(1-\textstyle\sum_\kappa[\mathrm{kind}_i=\kappa]\big),\ \ n_{\mathrm{decl}}=\sum_i[\mathrm{epd}_i\ne\bot](1-\mathrm{E}_i)$$",
 time=r"$T$ によらない。", coef=r"$F^\ast_i$（係数）と $c^\ast_i$（換算倍率）は排他的な和（3 つの述語のうち高々 1 つが 1）。",
 consts=[], notes="EPD を退けた行は複合・汎用に落ちる（優先順位）。記号 $F^\\ast_i, c^\\ast_i$ は本台帳で導入（出力キー factor・conv）。",
)

U["A13-01"] = dict(
 stage="A1-A3", comp=[("A1-A3", 1)], role="DIRECT", role2=None,
 why="構成表 COMP の A1-A3 の行（符号 +1）。初期の定数 $A^{\\mathrm{init}}$ の一部としてホールライフ合計に直接入る。",
 inputs=[], cond=r"係数の種類が汎用または複合（X-15）で、発注量がある行。EPD の行は A13-03（相互排他）。",
 msp=r"$$V_{@A13-01}=\sum_{i\in\mathtt{materials}}\big([\mathrm{kind}_i=\mathrm{GEN}]+[\mathrm{kind}_i=\mathrm{COMP}]\big)[q^{\mathrm{ord}}_i\ne\bot]\;q^{\mathrm{ord}}_i\,c^\ast_i\,F^\ast_i,\qquad n_{\mathrm{skip}}=\#\{i:\mathrm{kind}_i=\bot\}+\#\{i:\mathrm{kind}_i\in\{\mathrm{GEN},\mathrm{COMP}\},\,q^{\mathrm{ord}}_i=\bot\}$$",
 time=r"定数の核（$T$ によらない）：$V_{@A13-01}(T)\equiv V_{@A13-01}$。実時間では $t=0$（施工時）に置く（$A^{\mathrm{init}}$）。",
 coef=r"行の振幅 $a01_i=q^{\mathrm{ord}}_i c^\ast_i F^\ast_i$（積和①の列 `a01.value` の項）。入力：数量・端材率・数量の基準・換算・係数（架空）。",
 consts=[], notes="by_item は行ごとの値（除外の行は 0.0）。",
)

U["A13-03"] = dict(
 stage="A1-A3", comp=[("A1-A3", 1)], role="DIRECT", role2=None,
 why="COMP の A1-A3 の行（+1）。$A^{\\mathrm{init}}$ の一部。",
 inputs=[], cond=r"EPD を採用した行（X-15 の kind = EPD）だけ。",
 msp=r"$$V_{@A13-03}=\sum_i[\mathrm{kind}_i=\mathrm{EPD}][q^{\mathrm{ord}}_i\ne\bot]\;q^{\mathrm{ord}}_i\,c^\ast_i\,F^\ast_i,\qquad n_{\mathrm{skip}}=\#\{i:\mathrm{kind}_i=\mathrm{EPD},\,q^{\mathrm{ord}}_i=\bot\}$$",
 time=r"定数の核（$T$ によらない）。$t=0$。", coef=r"$a03_i=q^{\mathrm{ord}}_i c^\ast_i F_{f^{\mathrm{epd}}_i}$（`a03.value`）。", consts=[], notes="",
)

U["A13-04"] = dict(
 stage="A1-A3", comp=[("A1-A3", 1)], role="DIRECT", role2=None,
 why="COMP の A1-A3 の行（+1）。数量のない工事の上乗せとして $A^{\\mathrm{init}}$ に入る（本研究が独立に設計した式）。",
 inputs=["materials.unquantified_cost_ratio"], cond=r"$0<r^{\mathrm{uq}}_i<1$ の行だけ計上。$r^{\mathrm{uq}}_i=0$（既定）と ⊥ は寄与 0 で件数に数えない。それ以外の値は件数に数える。",
 msp=r"$$V_{@A13-04}=\sum_i[0<r^{\mathrm{uq}}_i<1]\,\big(a01_i+a03_i\big)\,\frac{r^{\mathrm{uq}}_i}{1-r^{\mathrm{uq}}_i}$$",
 time=r"定数の核（$T$ によらない）。$t=0$。", coef=r"$r/(1-r)$ は積和の 1 列の関数 `ratio_one_minus`。$a01_i,a03_i$ は A13-01・A13-03 の行の値。", consts=[], notes="",
)

U["X-01"] = dict(
 stage="A1-A3", comp=[("A1-A3", 1)], role="DIRECT", role2=None,
 why="COMP の A1-A3 の行（+1）。設備機器の製造排出として $A^{\\mathrm{init}}$ に入る。",
 inputs=["equipment.quantity", "equipment.quantity_unit", "equipment.factor_id"], cond=r"$[Q_j\ge0]\,\mathrm{G}_{\mathrm{A1\text{-}A3}}(f_j,u_j)$。",
 msp=r"$$V_{@X-01}=\sum_{j\in\mathtt{equipment}}[Q_j\ge0]\;Q_j\,\mathcal{F}_{\mathrm{A1\text{-}A3}}(f_j,u_j)$$",
 time=r"定数の核（$T$ によらない）。$t=0$。", coef=r"$x01_j=Q_j\,\mathrm{cv}(u_j\to u_{f_j})F_{f_j}$（`x01.value`）。B3-01・B4-02・B5-01 の振幅にも入る。", consts=[], notes="",
)

U["X-03"] = dict(
 stage="A1-A3", comp=[], role="BREAKDOWN", role2=None,
 why="複合品の行を構成材ごとの質量と排出に分けた内訳。和は A13-01 の複合の行の部分に等しく、合計には二重に入れない。",
 inputs=[], cond=r"$[\mathrm{kind}_i=\mathrm{COMP}][q^{\mathrm{ord}}_i\ne\bot]$ の行だけ。",
 msp=r"$$\mathrm{mass}_f=\sum_{(i,j):\,f_{ij}=f}[\mathrm{kind}_i=\mathrm{COMP}][q^{\mathrm{ord}}_i\ne\bot]\;q^{\mathrm{ord}}_i\,c^\ast_i\,\mathrm{mf}_{ij},\qquad \mathrm{em}_f=\sum_{(i,j):\,f_{ij}=f}[\cdots]\;q^{\mathrm{ord}}_i\,c^\ast_i\,\mathrm{mf}_{ij}\,\mathrm{cv}(\mathrm{kg}\to u_f)\,F_f,\qquad \mathrm{value}=\sum_f\mathrm{em}_f$$",
 time=r"$T$ によらない。", coef=r"構成材の係数 $F_f$（架空）。", consts=[], notes="厳密な算術では value＝A13-01 の複合の行の和（積の結合の順が違うので浮動小数では数 ulp 違いうる）。",
)

U["A4-01"] = dict(
 stage="A4", comp=[("A4", 1)], role="DIRECT", role2=None,
 why="COMP の A4 の行（+1）。$A^{\\mathrm{init}}$ に入る。",
 inputs=["materials.transport.delivery_factor_id", "materials.transport.mass_t", "materials.transport.distance_km", "materials.transport.factor_id"],
 cond=r"搬入係数の無い行だけ（ある行は A4-02：相互排他）。$\mathrm{G}_{\mathrm{A4}}(f^{\mathrm{tr}}_i,\mathrm{tkm})[M^{\mathrm{tr}}_i\ge0][D^{\mathrm{tr}}_i\ge0]$。",
 msp=r"$$V_{@A4-01}=\sum_i[f^{\mathrm{del}}_i=\bot][M^{\mathrm{tr}}_i\ge0][D^{\mathrm{tr}}_i\ge0]\;M^{\mathrm{tr}}_i\,D^{\mathrm{tr}}_i\,\mathcal{F}_{\mathrm{A4}}(f^{\mathrm{tr}}_i,\mathrm{tkm})$$",
 time=r"定数の核（$T$ によらない）。$t=0$。", coef=r"$a41_i=M D\,\mathrm{cv}(\mathrm{tkm}\to u_f)F_f$（`a41.value`）。", consts=[], notes="",
)

U["X-12"] = dict(
 stage="A4", comp=[], role="REFERENCE", role2=None,
 why="積載率で補正した輸送排出（代替値）。A4 の段階の値には A4-01 を使い、X-12 は合計に入らない。",
 inputs=["materials.transport.load_factor"], cond=r"A4-01 の述語に $[\lambda^{\mathrm{load}}_i>0]$ を加える（偽は件数に数える）。",
 msp=r"$$V_{@X-12}=\sum_i[f^{\mathrm{del}}_i=\bot][M^{\mathrm{tr}}_i\ge0][D^{\mathrm{tr}}_i\ge0][\lambda^{\mathrm{load}}_i>0]\;M^{\mathrm{tr}}_i\,D^{\mathrm{tr}}_i\,\frac{1}{\lambda^{\mathrm{load}}_i}\,\mathcal{F}_{\mathrm{A4}}(f^{\mathrm{tr}}_i,\mathrm{tkm})$$",
 time=r"$T$ によらない。", coef=r"$1/\lambda$ は 1 列の関数 `inv`。", consts=[], notes="",
)

U["A4-02"] = dict(
 stage="A4", comp=[("A4", 1)], role="DIRECT", role2=None,
 why="COMP の A4 の行（+1）。$A^{\\mathrm{init}}$ に入る。",
 inputs=["materials.transport.delivery_factor_id", "materials.quantity_unit", "materials.conversions.factor"],
 cond=r"搬入係数のある行だけ。$\mathrm{G}_{\mathrm{A4}}(f^{\mathrm{del}}_i,u_i)[q^{\mathrm{ord}}_i\ne\bot]$。",
 msp=r"$$V_{@A4-02}=\sum_i[f^{\mathrm{del}}_i\ne\bot][q^{\mathrm{ord}}_i\ne\bot]\;q^{\mathrm{ord}}_i\,\mathcal{F}_{\mathrm{A4}}(f^{\mathrm{del}}_i,u_i)$$",
 time=r"定数の核（$T$ によらない）。$t=0$。", coef=r"$a42_i=q^{\mathrm{ord}}_i\,\mathrm{cv}_i(u_i\to u_f)F_f$（`a42.value`）。", consts=[], notes="",
)

U["A5-01"] = dict(
 stage="A5", comp=[], role="AUXILIARY", role2=None,
 why="工事期間の買電排出。A5-04 の和の一部として A5 段階に入る（A5-01 自身は COMP に無い）。",
 inputs=["construction.electricity_kwh", "operation.grid.unit", "operation.grid.construction_value", "operation.grid.licence_status"],
 cond=r"$\mathrm{ok}=[E^{\mathrm{site}}\ge0][\mathrm{gunit}(u_\gamma)\ne\bot][\mathrm{cv}(\mathrm{kWh}\to\mathrm{gunit}(u_\gamma))\ne\bot][\mathrm{lic}_\gamma=\mathrm{PERMITTED\_PUBLIC}]$。偽なら値 0.0 と computed = 偽。",
 msp=r"$$V_{@A5-01}=\mathrm{ok}\;E^{\mathrm{site}}\,\mathrm{cv}(\mathrm{kWh}\to\mathrm{gunit}(u_\gamma))\,\gamma^{\mathrm{con}},\qquad \mathrm{computed}=\mathrm{ok}$$",
 time=r"$T$ によらない。", coef=r"工事期間の電力係数 $\gamma^{\mathrm{con}}$（架空）。", consts=[], notes="X-04 では擬似の行 GRID として数える。",
)

U["A5-02"] = dict(
 stage="A5", comp=[], role="AUXILIARY", role2=None,
 why="施工燃料の排出。A5-04 の一部。",
 inputs=["construction.fuels.quantity", "construction.fuels.unit", "construction.fuels.factor_id"], cond=r"$[Q_x\ge0]\,\mathrm{G}_{\mathrm{A5}}(f_x,u_x)$（行固有の換算を先に探す）。",
 msp=r"$$V_{@A5-02}=\sum_{x\in\mathtt{construction.fuels}}[Q_x\ge0]\;Q_x\,\mathcal{F}_{\mathrm{A5}}(f_x,u_x)$$",
 time=r"$T$ によらない。", coef="燃料の係数（架空）。", consts=[], notes="",
)

U["A5-03"] = dict(
 stage="A5", comp=[], role="AUXILIARY", role2=None,
 why="工事廃棄物の排出。A5-04 の一部。",
 inputs=["construction.waste_streams.mass_kg", "construction.waste_streams.factor_id"], cond=r"$[m_x\ge0]\,\mathrm{G}_{\mathrm{A5}}(f_x,\mathrm{kg})$。",
 msp=r"$$V_{@A5-03}=\sum_{x\in\mathtt{construction.waste\_streams}}[m_x\ge0]\;m_x\,\mathcal{F}_{\mathrm{A5}}(f_x,\mathrm{kg})$$",
 time=r"$T$ によらない。", coef="廃棄物の係数（架空）。", consts=[], notes="",
)

U["A5-04"] = dict(
 stage="A5", comp=[("A5", 1)], role="DIRECT", role2=None,
 why="COMP の A5 の行（+1）。A5-01〜03 の和として $A^{\\mathrm{init}}$ に入る。",
 inputs=[], cond="なし（和だけ）。",
 msp=r"$$V_{@A5-04}=V_{@A5-01}+V_{@A5-02}+V_{@A5-03},\qquad \mathrm{other\_assessed}=\text{偽（定数）}$$",
 time=r"定数の核（$T$ によらない）。$t=0$。", coef="下位 3 単位の値の和。", consts=[], notes="parts は 3 つの値の辞書（power・fuels・waste）。",
)

U["X-17"] = dict(
 stage="A1-A3", comp=[], role="REFERENCE", role2=None,
 why="要約数量×代表係数による簡易算定（参考値）。合計に入らない。",
 inputs=["materials.material_class", "materials.construction_division", "materials.quantity_unit", "summary_quantities.reinforcement_kg",
         "summary_quantities.steel_kg", "summary_quantities.concrete_m3", "summary_quantities.timber_m3", "summary_quantities.envelope_m2",
         "summary_quantities.interior_m2"],
 cond=r"区分 $c\in\{$REBAR, STRUCTURAL_STEEL, CONCRETE, TIMBER, ENVELOPE, INTERIOR$\}$。$\mathrm{cl}(i)$：資材区分が前 4 つならそれ、数量単位が m2 で工事区分が屋根外壁・開口なら ENVELOPE、内装なら INTERIOR、それ以外は区分なし。",
 msp=r"$$\bar f_c=[q_c\ne0]\,\frac{1}{q_c}\sum_{i:\,\mathrm{cl}(i)=c}\big(a01_i+a03_i\big),\qquad e_c=q_c\,\bar f_c,\qquad V_{@X-17}=\sum_c e_c$$",
 time=r"$T$ によらない。", coef=r"代表係数 $\bar f_c$ は詳細な行から作る（外部の係数ではない）。",
 consts=[], notes="厳密な算術では $e_c=[q_c\\ne0]\\sum_{\\mathrm{cl}(i)=c}(a01_i+a03_i)$ で、要約数量 $q_c$ は 0 かどうか以外に効かない [P]（式の代数。浮動小数では $q_c\\cdot(S/q_c)$ の丸めだけ違う）。簡易算定としての意味は、代表係数を外部から与えたときに初めて生じる。",
)

U["X-16"] = dict(
 stage="A1-A3", comp=[], role="REFERENCE", role2=None,
 why="費用ベースの係数による参考値（物価補正）。段階の値には使わない（本研究が新しく置いた入力）。",
 inputs=["cost_items.amount", "cost_items.currency", "cost_items.price_year", "cost_items.factor_base_year", "cost_items.factor_id", "price_index.value"],
 cond=r"$[P_x\ge0]\,\mathrm{G}_{\mathrm{A1\text{-}A3}}(f_x,u_x)\,[I_{y^{\mathrm{p}}_x}>0][I_{y^{\mathrm{b}}_x}>0]$（指数が無い年は ⊥ で偽）。",
 msp=r"$$V_{@X-16}=\sum_{x\in\mathtt{cost\_items}}[P_x\ge0][I_{y^{\mathrm{p}}_x}>0][I_{y^{\mathrm{b}}_x}>0]\;P_x\,\frac{I_{y^{\mathrm{b}}_x}}{I_{y^{\mathrm{p}}_x}}\,\mathcal{F}_{\mathrm{A1\text{-}A3}}(f_x,u_x)$$",
 time=r"$T$ によらない。", coef="費用あたりの係数と物価指数（いずれも架空）。", consts=[], notes="",
)

UCUR.update(U)

# ======== cur_units_b.py ========
# 台帳の手書き部分（その 2：解体・廃棄、参考値、更新・修繕、冷媒、改修）。
U = {}  # この部分の単位

U["C1-01"] = dict(
 stage="C1", comp=[("C1", 1)], role="DIRECT", role2=None,
 why="COMP の C1 の行（+1）。廃棄時の定数 $A^{\\mathrm{term}}$ に入る。",
 inputs=["end_of_life.demolition_activities.quantity", "end_of_life.demolition_activities.unit", "end_of_life.demolition_activities.factor_id"],
 cond=r"$[Q_x\ge0]\,\mathrm{G}_{\mathrm{C1}}(f_x,u_x)$。",
 msp=r"$$V_{@C1-01}=\sum_{x\in\mathtt{demolition\_activities}}[Q_x\ge0]\;Q_x\,\mathcal{F}_{\mathrm{C1}}(f_x,u_x)$$",
 time=r"定数の核（値は $T$ によらない）。実時間では $t=T$（評価期間の終わり）に置く（$A^{\mathrm{term}}$、17 章 03 の TH-4）。",
 coef="解体作業の係数（架空）。", consts=[], notes="",
)

U["C2-01"] = dict(
 stage="C2", comp=[("C2", 1)], role="DIRECT", role2=None,
 why="COMP の C2 の行（+1）。$A^{\\mathrm{term}}$ に入る。",
 inputs=["materials.end_of_life.mass_kg", "materials.end_of_life.haul_distance_km", "materials.end_of_life.haul_factor_id",
         "end_of_life.waste_hauls.mass_t", "end_of_life.waste_hauls.distance_km", "end_of_life.waste_hauls.factor_id"],
 cond=r"資材の行：$\mathrm{G}_{\mathrm{C2}}(f^{\mathrm{haul}}_i,\mathrm{tkm})[m^{\mathrm{eol}}_i\ge0][D^{\mathrm{haul}}_i\ge0]$。資材の行に含まれない搬出 $x$：$\mathrm{G}_{\mathrm{C2}}(f_x,\mathrm{tkm})[M_x\ge0][D_x\ge0]$。",
 msp=r"$$V_{@C2-01}=\sum_i[m^{\mathrm{eol}}_i\ge0][D^{\mathrm{haul}}_i\ge0]\;m^{\mathrm{eol}}_i\cdot10^{-3}\cdot D^{\mathrm{haul}}_i\,\mathcal{F}_{\mathrm{C2}}(f^{\mathrm{haul}}_i,\mathrm{tkm})+\sum_{x\in\mathtt{waste\_hauls}}[M_x\ge0][D_x\ge0]\;M_x\,D_x\,\mathcal{F}_{\mathrm{C2}}(f_x,\mathrm{tkm})$$",
 time=r"定数の核。$t=T$。", coef=r"搬出の係数（架空、tkm あたり）。", consts=["0.001（kg から t。式の中では除算 /1000）"],
 notes="n_skipped は資材の行と搬出の行の除外の和。",
)

U["C3-01"] = dict(
 stage="C3", comp=[("C3", 1)], role="DIRECT", role2=None,
 why="COMP の C3 の行（+1）。$A^{\\mathrm{term}}$ に入る。",
 inputs=["materials.end_of_life.mass_kg", "materials.end_of_life.routes.route", "materials.end_of_life.routes.fraction", "materials.end_of_life.routes.factor_id"],
 cond=r"最終処分（LANDFILL）以外の経路。行：$[m^{\mathrm{eol}}_i\ge0]$（偽は $n_{\mathrm{skip}}$）。経路：$\mathrm{G}_{\mathrm{C3}}(f_{ij},\mathrm{kg})[\mathrm{fr}_{ij}\ge0]$（偽は $n_{\mathrm{routes\,skip}}$）。",
 msp=r"$$V_{@C3-01}=\sum_i[m^{\mathrm{eol}}_i\ge0]\sum_{j:\,\mathrm{rt}_{ij}\ne\mathrm{LANDFILL}}[\mathrm{fr}_{ij}\ge0]\;m^{\mathrm{eol}}_i\,\mathrm{fr}_{ij}\,\mathcal{F}_{\mathrm{C3}}(f_{ij},\mathrm{kg})$$",
 time=r"定数の核。$t=T$。", coef="処理経路の係数（架空、kg あたり）。", consts=[], notes="",
)

U["C4-01"] = dict(
 stage="C4", comp=[("C4", 1)], role="DIRECT", role2=None,
 why="COMP の C4 の行（+1）。$A^{\\mathrm{term}}$ に入る。",
 inputs=["materials.end_of_life.mass_kg", "materials.end_of_life.routes.route", "materials.end_of_life.routes.fraction", "materials.end_of_life.routes.factor_id"],
 cond=r"LANDFILL の経路だけ。述語は C3-01 と同じ形（段階 C4）。",
 msp=r"$$V_{@C4-01}=\sum_i[m^{\mathrm{eol}}_i\ge0]\sum_{j:\,\mathrm{rt}_{ij}=\mathrm{LANDFILL}}[\mathrm{fr}_{ij}\ge0]\;m^{\mathrm{eol}}_i\,\mathrm{fr}_{ij}\,\mathcal{F}_{\mathrm{C4}}(f_{ij},\mathrm{kg})$$",
 time=r"定数の核。$t=T$。", coef="最終処分の係数（架空）。", consts=[], notes="",
)

U["X-14"] = dict(
 stage="C3", comp=[("C3", 1)], role="DIRECT", role2=None,
 why="COMP の C3 の行（+1、C3-01 と並ぶ）。設備の廃棄時排出として $A^{\\mathrm{term}}$ に入る。",
 inputs=["equipment.end_of_life_mass_kg", "equipment.eol_factor_id"], cond=r"$\mathrm{G}_{\mathrm{C3}}(f^{\mathrm{eol}}_j,\mathrm{kg})[m^{\mathrm{eol}}_j\ge0]$。",
 msp=r"$$V_{@X-14}=\sum_j[m^{\mathrm{eol}}_j\ge0]\;m^{\mathrm{eol}}_j\,\mathcal{F}_{\mathrm{C3}}(f^{\mathrm{eol}}_j,\mathrm{kg})$$",
 time=r"定数の核。$t=T$。", coef=r"$x14_j$（`x14.value`）。B4-02・B5-01 の振幅にも入る。", consts=[], notes="",
)

U["C-05"] = dict(
 stage="C1-C4", comp=[], role="DECISION", role2=None,
 why="資材の質量収支（経路の比率と廃棄質量）の検査。値に入らない。",
 inputs=["materials.end_of_life.routes.fraction", "materials.end_of_life.mass_kg", "materials.quantity_unit", "materials.conversions.factor"],
 cond=r"$s_i=\sum_j\mathrm{fr}_{ij}$、$\mathrm{neg}_i=[\exists j:\mathrm{fr}_{ij}<0]$、$c_i=\mathrm{cv}_i(u_i\to\mathrm{kg})$。",
 msp=r"$$v^{(1)}_i=\mathrm{neg}_i+(1-\mathrm{neg}_i)[s_i>1+10^{-6}],\quad \mathrm{under}_i=[v^{(1)}_i=0][s_i<1-10^{-6}],\quad v^{(2)}_i=[c_i\ne\bot][q^{\mathrm{inst}}_i\ne\bot][m^{\mathrm{eol}}_i\ne\bot]\,[m^{\mathrm{eol}}_i>q^{\mathrm{inst}}_i c_i(1+10^{-6})]$$ $$\mathrm{ok}=\Big[\sum_i(v^{(1)}_i+v^{(2)}_i)=0\Big],\qquad n_{\mathrm{unchecked}}=\sum_i\big(1-[c_i\ne\bot][q^{\mathrm{inst}}_i\ne\bot][m^{\mathrm{eol}}_i\ne\bot]\big)$$",
 time=r"$T$ によらない。", coef="係数なし。", consts=["1e-6（比率の和と質量の許容差）"], notes="",
)

U["X-09"] = dict(
 stage="C1-C4", comp=[], role="BREAKDOWN", role2=None,
 why="廃棄物の質量と排出を資材区分×処理経路に分けた内訳。排出の和は C3-01＋C4-01 に（厳密な算術で）等しく、合計には二重に入れない。",
 inputs=["materials.material_class", "materials.end_of_life.mass_kg", "materials.end_of_life.routes.route", "materials.end_of_life.routes.fraction", "materials.end_of_life.routes.factor_id"],
 cond=r"$[m^{\mathrm{eol}}_i\ge0][\mathrm{fr}_{ij}\ge0]$。区分のキーは、質量が有効な行を 1 つ以上持つ区分だけ現れる。",
 msp=r"$$\mathrm{mass}[c,\varrho]=\sum_{(i,j)}[m^{\mathrm{eol}}_i\ge0][\mathrm{fr}_{ij}\ge0][\mathrm{cls}_i=c][\mathrm{rt}_{ij}=\varrho]\;m^{\mathrm{eol}}_i\,\mathrm{fr}_{ij},\qquad \mathrm{em}[c,\varrho]=\sum_{(i,j)}[\cdots]\;m^{\mathrm{eol}}_i\,\mathrm{fr}_{ij}\,\mathcal{F}_{s(\varrho)}(f_{ij},\mathrm{kg})$$ $$s(\mathrm{LANDFILL})=\mathrm{C4},\ s(\text{他})=\mathrm{C3},\qquad \mathrm{value}=\sum_{c,\varrho}\mathrm{em}[c,\varrho]$$",
 time=r"$T$ によらない。", coef="経路の係数（架空）。", consts=[], notes="経路の記号 $\\varrho$ は本台帳で導入（処理経路の値）。",
)

U["X-10"] = dict(
 stage="SUM", comp=[], role="REFERENCE", role2=None,
 why="資源投入量と廃棄物量（kg）の物量の指標。CO2 の合計には入らない。",
 inputs=["materials.quantity_unit", "materials.conversions.factor", "materials.end_of_life.mass_kg", "equipment.end_of_life_mass_kg"],
 cond=r"資材の行：$\mathrm{ok}_i=[\mathrm{cv}_i(u_i\to\mathrm{kg})\ne\bot][q^{\mathrm{ord}}_i\ne\bot][m^{\mathrm{eol}}_i\ge0]$。設備の行：$[m^{\mathrm{eol}}_j\ge0]$。偽の行は $n_{\mathrm{excl}}$。",
 msp=r"$$\mathrm{res}(T)=\sum_i\mathrm{ok}_i\;q^{\mathrm{ord}}_i\,c_i\,\big(1+n_i(T)\big),\qquad \mathrm{waste}(T)=\sum_i\mathrm{ok}_i\big((q^{\mathrm{ord}}_i-q^{\mathrm{inst}}_i)c_i+m^{\mathrm{eol}}_i\big)\big(1+n_i(T)\big)+\sum_j[m^{\mathrm{eol}}_j\ge0]\;m^{\mathrm{eol}}_j\big(1+|E_j(T)|\big)$$",
 time=r"区分的に一定（階段）。区切りは質量 $\mu_i\ne0$ の行の事象だけ：$\sum_i\mu_i(1+N_i(T))$（17 章 01 の 7 節、TH-14）。",
 coef=r"$c_i=\mathrm{cv}_i(u_i\to\mathrm{kg})$、$n_i(T)$ は B4-03、$|E_j(T)|$ は B4-01 の事象の数。",
 consts=[], notes="時間の式は 17 章で照合していない（17 章 01 の 7 節に「照合していない」と記録）。本台帳の照合（末尾）は値の一致だけ。",
)

U["STO-01"] = dict(
 stage="MEMO", comp=[], role="REFERENCE", role2=None,
 why="木材の炭素貯蔵の参考値（段階の値・合計に入れない MEMO）。",
 inputs=["summary_quantities.timber_m3", "summary_quantities.timber_dry_density_kg_per_m3", "summary_quantities.timber_carbon_fraction"],
 cond=r"3 量とも $\ge0$。偽なら ⊥（None）。",
 msp=r"$$V_{@STO-01}=[q_{\mathrm{TIMB}}\ge0][\varrho^{\mathrm{dry}}\ge0][c^{\mathrm{C}}\ge0]\;q_{\mathrm{TIMB}}\,\varrho^{\mathrm{dry}}\,c^{\mathrm{C}}\,\frac{44}{12}$$",
 time=r"$T$ によらない。", coef="密度・炭素含有率は架空。", consts=["44/12（CO2 と C の分子量の比）"], notes="符号は正（貯蔵量）で、合計から引かない。",
)

U["STO-02"] = dict(
 stage="MEMO", comp=[], role="REFERENCE", role2=None,
 why="コンクリート炭酸化等による吸収の参考値（MEMO）。合計に入らない。",
 inputs=["summary_quantities.concrete_m3", "summary_quantities.concrete_uptake_factor_id"], cond=r"$\mathrm{G}_{\mathrm{MEMO}}(f^{\mathrm{upt}},\mathrm{m3})[q_{\mathrm{CONC}}\ge0]$。偽なら ⊥。",
 msp=r"$$V_{@STO-02}=[q_{\mathrm{CONC}}\ge0]\;q_{\mathrm{CONC}}\,\mathcal{F}_{\mathrm{MEMO}}(f^{\mathrm{upt}},\mathrm{m3})\quad(\text{ゲートが偽なら }\bot)$$",
 time=r"$T$ によらない。", coef="吸収の係数（架空）。", consts=[], notes="",
)

U["B4-01"] = dict(
 stage="B4", comp=[], role="AUXILIARY", role2=None,
 why="設備の更新事象の時刻の一覧と件数。B4-02・B3-01・X-08・X-10 の入力（事象の格子）で、それ自体は排出ではない。",
 inputs=["equipment.replacement_event_list.value", "equipment.service_life"],
 cond=r"一覧があれば一覧（$\tau>0$ かつ $\theta_\varepsilon(T;\tau)$、一覧の順・重複を保つ）、無ければ耐用年数の倍数（$c_j$ が正・有限のときだけ）。",
 msp=r"$$E_j(T)=[L_j\ne\bot]\,\big(\tau\in L_j:\tau>0,\ \theta_\varepsilon(T;\tau)\big)+[L_j=\bot]\,\{n c_j:\ n\ge1,\ \theta_\varepsilon(T;nc_j)\},\qquad n_{\mathrm{events}}(T)=\sum_j|E_j(T)|$$",
 time=r"件数は階段関数（事象の時刻 $\mathrm{sw}(\tau)$ で 1 ずつ増える）。一覧の要素は $T$ とともに現れる。区切りは振幅 0 の行の事象を含み、$C(T)$ の節点より細かいことがある（TH-14）。",
 coef="係数なし。時刻は浮動小数の積 $\\mathrm{fl}(n c_j)$。", consts=["ε = 1e-9（事象の規則）"],
 notes="一覧は整列しない（基準計算と同じ）。",
)

U["B4-03"] = dict(
 stage="B4", comp=[], role="AUXILIARY", role2=None,
 why="資材の行の更新回数 $n_i(T)$。B4-02・B3-01・X-08・X-10 の入力。",
 inputs=["materials.refresh_cycle"], cond=r"$c_i$ が正・有限のときだけ（それ以外は 0 回）。",
 msp=r"$$n_i(T)=\sum_{n\ge1}\theta_\varepsilon(T;\,n c_i)=\#\{n\ge1:\ \mathrm{fl}(nc_i)<\mathrm{fl}(T\,\mathrm{fl}(1-\varepsilon))\}$$",
 time=r"階段関数（周期の格子 $n c_i$ で跳ぶ）。", coef="係数なし。", consts=["ε = 1e-9"],
 notes="17 章 06 で「その他」に分類された葉が 1 つある（数量 0 の品目：正準形の区間の内側で回数が変わる）。",
)

U["B4-02"] = dict(
 stage="B4", comp=[("B4", 1)], role="DIRECT", role2=None,
 why="COMP の B4 の行（+1）。更新の原子 $\\Gamma^{(\\mathrm{B4\\text{-}02})}$ として合計に入る。",
 inputs=["materials.installation_factor_id", "equipment.delivery_factor_id", "equipment.installation_factor_id", "equipment.quantity"],
 cond=r"1 回の更新の排出 $u_i$ は初期の行の値（製造・輸送・搬出・処理・処分）と据付の和。設備は製造・搬入・据付・廃棄。部分的な除外（構成要素のどれかが除外）を持つ行が事象を持てば $n_{\mathrm{partial}}$ に数える。",
 msp=r"$$u_i=a01_i+a03_i+a41_i+a42_i+c21_i+c31_i+c41_i+[f^{\mathrm{inst}}_i\ne\bot][q^{\mathrm{ord}}_i\ne\bot]\,q^{\mathrm{ord}}_i\,\mathcal{F}_{\mathrm{A5}}(f^{\mathrm{inst}}_i,u_i)$$ $$u_j=x01_j+x14_j+\sum_{(f,s)\in\{(f^{\mathrm{del}}_j,\mathrm{A4}),(f^{\mathrm{inst}}_j,\mathrm{A5})\}}[f\ne\bot][Q_j\ge0]\,Q_j\,\mathcal{F}_s(f,u_j)$$ $$V_{@B4-02}(T)=\sum_i\sum_{n\ge1}u_i\,\theta_\varepsilon(T;nc_i)+\sum_j\sum_{\tau\in E_j(T)}u_j,\qquad \mathrm{by\_year}_y=\sum_{\text{数えた事象 }\tau:\ y(\tau)=y}u$$",
 time=r"原子の和（区分的に一定、事象 $\mathrm{sw}(\tau)$ で跳び $u$）：$V(T)=\sum_{j}\Gamma_j\,\theta_\varepsilon(T;\tau_j)$。年セルの位置は $y(\tau)=\max(1,\lceil\tau(1-\varepsilon)\rceil)$。",
 coef=r"$\Gamma^{(\mathrm{B4\text{-}02})}_{i,n}=u_i$（列 `me.b4`、`ee.b4`）。$u_i$ は A13-01・A13-03・A4-01・A4-02・C2-01・C3-01・C4-01 の行の値と据付の係数（架空）。",
 consts=["ε = 1e-9"], notes="振幅 0 の行の事象は $C(T)$ の節点にならない（回数には数える）。",
)

U["X-08"] = dict(
 stage="B4", comp=[], role="BREAKDOWN", role2=None,
 why="更新の排出を周期ごとに分けた内訳（明示の一覧の設備は別掲）。厳密な算術で value＝B4-02。",
 inputs=["materials.refresh_cycle", "equipment.service_life", "equipment.replacement_event_list.value"],
 cond=r"周期の値 $c$（浮動小数の値で同一視、キーは repr）。資材は $n_i(T)>0$、設備は $E_j(T)\ne\emptyset$ の行だけ。",
 msp=r"$$U_c=\sum_{i:\,c_i=c,\ n_i(T)>0}u_i+\sum_{j:\,L_j=\bot,\ c_j=c,\ E_j(T)\ne\emptyset}u_j,\qquad E_c(T)=N_c(T)\,U_c,\qquad \mathrm{explicit}(T)=\sum_{j:\,L_j\ne\bot}u_j\,|E_j(T)|,\qquad V_{@X-08}=\mathrm{explicit}+\sum_cE_c$$",
 time=r"階段関数（周期の格子）。$U_c$ の集合も $T$ で変わる（初めて事象が数えられた行が加わる）。", coef=r"$u_i,u_j$ は B4-02 と同じ。$N_c(T)=\#\{n\ge1:nc<T(1-\varepsilon)\}$。",
 consts=[], notes="",
)

U["B3-01"] = dict(
 stage="B3", comp=[("B3", 1)], role="DIRECT", role2=None,
 why="COMP の B3 の行（+1）。年間修繕の密度 $B^{(\\mathrm{B3})}_\\ast$ と事象の年の補正 $\\Delta^{(\\mathrm{B3})}$ として合計に入る。",
 inputs=["materials.repair_rate", "equipment.repair_rate"],
 cond=r"$[r\ge0]$ の行（偽は $n_{\mathrm{skip}}$）。更新事象を含む年（$y(\tau)$）はその行の修繕を数えない。",
 msp=r"$$a_i=[r_i\ge0]\,e_{0,i}\,r_i,\quad e_{0,i}=a01_i+a03_i;\qquad a_j=[r_j\ge0]\,x01_j\,r_j$$ $$V_{@B3-01}(T)=\sum_{\rho\in\mathtt{materials}\cup\mathtt{equipment}}\ \sum_{y=1}^{Y}\big[y\notin\{y(\tau):\tau\in E_\rho(T)\}\big]\;a_\rho\,w_{y-1}(T)$$",
 time=r"密度＋ゲート付き年セル：$$V(T)=\Big(\sum_\rho a_\rho\Big)\min(T,H)-\sum_{(\rho,k)}a_\rho\,\theta_\varepsilon(T;\tau^{\mathrm{first}}_{\rho,k})\,w_k(T)$$（$\tau^{\mathrm{first}}_{\rho,k}$ は行 $\rho$ の年セル $k$ の最初の事象）。区分一次。格子では連続。事象 $\mathrm{sw}(\tau)$ で跳び $-a_\rho\,w_k(\mathrm{sw}(\tau))$（その年にそれまで積んだ修繕を除く）と傾きの変化 $-a_\rho$（TH-2 の 4）。",
 coef=r"$B^{(\mathrm{B3})}_\ast=\sum a_\rho$（`b3.a_mat`、`b3.a_eq`）、$\Delta^{(\mathrm{B3})}_{\rho,k}=-a_\rho$（`me.b3`、`ee.b3`）。率で持つ（17 章 01 の 2 節）。",
 consts=[], notes="積和での展開は UNITS_70 の「Σ a_i T − Σ a_i [最初の事象 < T′] w_k(T)」と同じ。",
)

U["B3-02"] = dict(
 stage="B3", comp=[], role="REFERENCE", role2=None,
 why="期間中の反復修繕の推計（更新年の除外なし）。X-02 の B3 は B3-01 を使い、B3-02 は合計に入らない。",
 inputs=["materials.repair_rate", "equipment.repair_rate"], cond=r"$[r\ge0]$。",
 msp=r"$$V_{@B3-02}(T)=T\Big(\sum_i[r_i\ge0]\,(a01_i+a03_i)\,r_i+\sum_j[r_j\ge0]\,x01_j\,r_j\Big)$$",
 time=r"$T$ の一次式（原点を通る直線、跳びなし）。", coef="B3-01 と同じ率。", consts=[], notes="",
)

U["B1-01"] = dict(
 stage="B1", comp=[], role="REFERENCE", role2=None,
 why="冷媒の CO2e 充填量（在庫の指標）。B1 段階の値は B1-02〜04 で、B1-01 は合計に入らない。",
 inputs=["refrigerants.charge_mass_kg", "refrigerants.gwp"], cond=r"$[m_{0,d}\ge0][\mathrm{GWP}_d\ge0]$。",
 msp=r"$$V_{@B1-01}=\sum_d[m_{0,d}\ge0][\mathrm{GWP}_d\ge0]\;m_{0,d}\,\mathrm{GWP}_d$$",
 time=r"$T$ によらない。", coef="GWP（架空）。", consts=[], notes="",
)

U["B1-02"] = dict(
 stage="B1", comp=[("B1", 1)], role="DIRECT", role2=None,
 why="COMP の B1 の行（+1）。冷媒の年間漏洩の年セル $B^{(\\mathrm{B1\\text{-}02})}_{d,k}$ として合計に入る。",
 inputs=["refrigerants.charge_mass_kg", "refrigerants.gwp", "refrigerants.annual_leak_rate", "refrigerants.top_up", "refrigerants.change_years.value", "refrigerants.service_life"],
 cond=r"$\mathrm{ok}_d=[m_{0,d}\ge0][\mathrm{GWP}_d\ge0][0\le r_d\le1]$（偽は $n_{\mathrm{skip}}$）。交換は一覧（整列）または耐用年数の倍数。$\chi_{d,k}$＝年セル $k$ に数えた交換があるか。",
 msp=r"$$q_d=1-[\neg\mathrm{tu}_d]\,r_d,\qquad u_{d,0}=m_{0,d},\qquad u_{d,k+1}=\chi_{d,k}\,m_{0,d}+(1-\chi_{d,k})\,q_d\,u_{d,k}\quad(k+1\le Y-1)$$ $$V_{@B1-02}(T)=\sum_d\mathrm{ok}_d\sum_{k=0}^{Y-1}\mathrm{GWP}_d\,r_d\,u_{d,k}\,w_k(T),\qquad u=(I+N)(I+N^2)(I+N^4)\cdots(I+N^{128})\,b\ \ (\text{積和 8 段、D-08})$$",
 time=r"年セルの和：$V(T)=\sum_{d,k}B_{d,k}\,w_k(T)$、$B_{d,k}=r_d\mathrm{GWP}_d\,u_{d,k}=r_d\mathrm{GWP}_d\,m_{0,d}\,q_d^{\nu_{d,k}}$。連続な区分一次（格子だけで傾きが変わる）。状態 $u$ は切り替わるアフィンの漸化式（TH-9）。",
 coef=r"$B^{(\mathrm{B1\text{-}02})}_{d,k}$（列 `b1.a2`）。$\nu_{d,k}$＝最後の交換からの年数。$N$ はべき零のずらし（$(Nu)_k=(1-\chi_{d,k-1})q_d u_{k-1}$）、$b_0=m_0$、$b_k=\chi_{d,k-1}m_0$。",
 consts=["8 因子（H < 256 の条件）", "ε = 1e-9"],
 notes="最後の年の端数の重みは最後の年の漏洩と期末の量にだけ効く。交換の時刻が年セルの終わり $K$ の帯にあると、$T\\in(K,\\mathrm{sw}(\\tau))$ で統一系・正準形は基準計算と異なりうる（未解決の切り替え境界、TH-2 の 3）。",
)

U["B1-03"] = dict(
 stage="B1", comp=[("B1", 1)], role="DIRECT", role2=None,
 why="COMP の B1 の行（+1）。交換時の冷媒損失の原子 $\\Gamma^{(\\mathrm{B1\\text{-}03})}$ とゲート付き年セル $\\Delta^{(\\mathrm{B1\\text{-}03})}$ として合計に入る。",
 inputs=["refrigerants.replacement_loss_rate"], cond=r"B1-02 で有効な機器かつ $[0\le\lambda_{\mathrm{loss}}\le1]$（偽は $n_{\mathrm{skip}}$）。",
 msp=r"$$V_{@B1-03}(T)=\sum_{e=(d,k,\tau)}\theta_\varepsilon(T;\tau)\,\lambda_{\mathrm{loss}}\,\mathrm{GWP}_d\Big([e\text{ がその年の最初}]\;u_{d,k}\big(1-[\neg\mathrm{tu}_d]\,r_d\,w_k(T)\big)+[\text{2 回目以降}]\;m_{0,d}\Big)$$",
 time=r"原子＋ゲート付き年セル：$\Gamma_e=\lambda\mathrm{GWP}([\text{最初}]u+[\text{2 回目以降}]m_0)$ が $\theta_\varepsilon(T;\tau_e)$ で、$\Delta_e=-\lambda\mathrm{GWP}\,u\,r[\neg\mathrm{tu}]$ が $\theta_\varepsilon(T;\tau_e)\,w_{k_e}(T)$ で入る。区分一次、事象で跳ぶ。",
 coef=r"`b1.a3`（原子）、`b1.g3`（ゲート付き年セル）。$u_{d,k}$ は B1-02 の状態。",
 consts=["ε = 1e-9"], notes="by_year は事象の年 $y(\\tau)$ ごと。相対差の最大は同じ年に 3 回の交換を置いた特殊条件（2.6e-14）。",
)

U["B1-04"] = dict(
 stage="B1/C", comp=[("B1", 1)], role="DIRECT", role2=None,
 why="COMP の B1 の行（+1）。期末の冷媒残存量の未回収分 $\\iota_{\\mathrm{B1}}R(T)$ として合計に入る（本研究の基準計算は B1 段階に帰属させ、C 段階には入れない）。",
 inputs=["refrigerants.end_of_life_recovery_rate"], cond=r"B1-02 で有効な機器かつ $[0\le\eta_d\le1]$（偽は $n_{\mathrm{skip}}$。回収率 100% とはみなさない）。",
 msp=r"$$\kappa_{R,d}=(1-\eta_d)\,\mathrm{GWP}_d,\qquad V_{@B1-04}(T)=\sum_d\mathrm{ok}_d\,[0\le\eta_d\le1]\;\kappa_{R,d}\,u^{\mathrm{end}}_d(T)$$ $$u^{\mathrm{end}}_d(T)=\begin{cases}m_{0,d}&\text{年セル }K\text{ の交換を数えた（}\theta_\varepsilon(T;\tau^{\mathrm{first}})=1\text{）}\\ u_{d,K}\big(1-[\neg\mathrm{tu}_d]\,r_d\,(T-K)\big)&\text{それ以外}\end{cases}\qquad K=\lceil T\rceil-1$$",
 time=r"区間形（採用）：$$R(T)=\mathcal{A}_K+\mathcal{B}_K\,(T-K)+\sum_{j\in\text{セル }K}\theta_\varepsilon(T;\tau_j)\big(\alpha^R_j+\gamma^R_j(T-K)\big)$$ $\mathcal{A}_K=\sum_d\kappa_{R,d}u_{d,K}$、$\mathcal{B}_K=-\sum_d\kappa_{R,d}[\neg\mathrm{tu}_d]u_{d,K}r_d$、$\alpha^R=\kappa_R(m_0-u)$、$\gamma^R=\kappa_R u r$。区分一次。格子 $K$ で連続（厳密な入力で、帯の交換が無いとき）、事象で跳ぶ。",
 coef=r"`b1.iA`、`b1.iB`（年セル）、`b1.e4a`、`b1.e4g`（機器×年）、交換の時刻 `b1.tau1`。",
 consts=["ε = 1e-9"],
 notes="冷媒状態の数値誤差（跳び形の桁落ち）と未解決の切り替え境界（帯 $T\\in(K,\\mathrm{sw}(\\tau))$）の主要な所在。数値は検証の欄。",
)

U["B5-01"] = dict(
 stage="B5", comp=[("B5", 1)], role="DIRECT", role2=None,
 why="COMP の B5 の行（+1）。大型改修・建替の原子 $\\Gamma^{(\\mathrm{B5\\text{-}01})}$ として合計に入る。",
 inputs=["boundary.reconstruction_scenario", "boundary.reconstruction_scope_fraction", "boundary.replacement_cycle"],
 cond=r"$[\mathrm{rs}\ne\mathrm{NONE}][0\le\varphi\le1]$。NONE なら値 0・件数 0・computed 真。$\varphi$ が範囲外なら値 0・computed 偽。",
 msp=r"$$A^{\mathrm{base}}=\sum_{u\in\{A13\text{-}01,A13\text{-}03,A13\text{-}04,X\text{-}01,A4\text{-}01,A4\text{-}02,A5\text{-}04,C1\text{-}01,C2\text{-}01,C3\text{-}01,C4\text{-}01,X\text{-}14\}}V_u$$ $$V_{@B5-01}(T)=[\mathrm{rs}\ne\mathrm{NONE}][0\le\varphi\le1]\sum_{n\ge1}\theta_\varepsilon(T;nC_{\mathrm{ren}})\;\varphi\,A^{\mathrm{base}},\qquad n_{\mathrm{events}}=[\cdots]\,N_{C_{\mathrm{ren}}}(T)$$",
 time=r"原子の和（周期 $C_{\mathrm{ren}}$ の格子で跳び $\varphi A^{\mathrm{base}}$、区分的に一定）。",
 coef=r"$\Gamma^{(\mathrm{B5\text{-}01})}_n=\varphi A^{\mathrm{base}}$（`be.b5`）。$A^{\mathrm{base}}$ は段階の述語 $\iota_s$ を掛ける前の単位の値の和（評価範囲によらない）。",
 consts=["ε = 1e-9"], notes="",
)

UCUR.update(U)

# ======== cur_units_c.py ========
# 台帳の手書き部分（その 3：運用・水、合成・内訳・合計・指標・検査）。
U = {}  # この部分の単位

U["X-06"] = dict(
 stage="B6", comp=[], role="AUXILIARY", role2=None,
 why="電力の排出係数の年次系列 $\\gamma_k$。B6-01・X-11 の入力で、それ自体は排出ではない。",
 inputs=["operation.grid.kind", "operation.grid.start", "operation.grid.annual_decline", "operation.grid.floor", "operation.grid.steps#", "operation.grid.table.value"],
 cond=r"整った記述子：CONSTANT（start あり）、LINEAR_DECLINE_TO_FLOOR（start・floor・decline があり decline ≥ 0、start ≥ floor）、STEPWISE（段が空でなく、最初が 0、from_index が狭義増加）。それ以外は年次表。",
 msp=r"$$\gamma_k=[\mathrm{CONST}]\,\gamma^{\mathrm{start}}+[\mathrm{LIN}]\max(\gamma^{\mathrm{floor}},\gamma^{\mathrm{start}}-\gamma^{\mathrm{dec}}k)+[\mathrm{STEP}]\sum_s[f_s\le k<f_{s+1}]\,\mathrm{val}_s+[\text{整っていない}]\,\gamma^{\mathrm{tab}}_k\qquad(0\le k<Y)$$ $$\mathrm{by\_year}=(0,\gamma_0,\dots,\gamma_{Y-1}),\qquad \mathrm{matches\_table}=\mathrm{same}\big(\gamma,\gamma^{\mathrm{tab}}_{0:Y}\big)$$",
 time=r"要素の値は $T$ によらず、列の長さ $Y+1$（$Y=\lceil T\rceil$）だけが $T$ で変わる（期間で現れる）。matches_table は $T$ とともに比べる年が増える階段。",
 coef=r"電力係数の記述子・年次表（架空）。$\max(p,q)$ は排他的な述語の和（SPEC_MSP 3 節）。", consts=["1e-12（same の相対の許容差）"],
 notes="by_year の 0 番目は時点 0（施工）の欄で常に 0.0。",
)

U["B6-04"] = dict(
 stage="B6", comp=[], role="AUXILIARY", role2=None,
 why="オンサイト発電を差し引いた正味の買電量 $n_k$（kWh/年）。B6-01 の入力。",
 inputs=["operation.electricity.table.value", "operation.onsite_generation.table.value", "operation.onsite_export.table.value"],
 cond=r"$e_u=\mathrm{aunit}(u^{\mathrm{el}})$、$c_g=\mathrm{cv}(\mathrm{aunit}(u^{\mathrm{gen}})\to e_u)$、$c_x=\mathrm{cv}(\mathrm{aunit}(u^{\mathrm{exp}})\to e_u)$ がすべて ⊥ でないとき computed。年次量は記述子（CONSTANT・LINEAR_TREND）があれば記述子、なければ表。",
 msp=r"$$d_k=c_k-\big(g_k\,c_g-x_k\,c_x\big),\qquad n_k=\mathrm{computed}\cdot[d_k\ge0]\,d_k\qquad(0\le k<Y),\qquad \mathrm{by\_year}=(0,n_0,\dots,n_{Y-1})$$",
 time=r"要素は $T$ によらない（列の長さだけ $Y$ で変わる）。", coef=r"需要 $c_k$・発電 $g_k$・売電 $x_k$ の年次量（架空）。", consts=[],
 notes="$\\max(0,d)$ は $[d\\ge0]d$。descriptors_match_tables は 3 系列の記述子と表の一致（相対 1e-12）。",
)

U["B6-01"] = dict(
 stage="B6", comp=[], role="AUXILIARY", role2=None,
 why="年ごとの買電排出 $e_k$。B6-03 と B2-01 の入力（年セルの振幅の材料）。",
 inputs=["operation.grid.licence_status", "operation.electricity.unit", "operation.grid.unit"],
 cond=r"$\mathrm{ok}=[\mathrm{lic}_\gamma=\mathrm{PERMITTED\_PUBLIC}][\mathrm{computed}_{@B6-04}][\mathrm{cv}(\mathrm{aunit}(u^{\mathrm{el}})\to\mathrm{gunit}(u_\gamma))\ne\bot]$。",
 msp=r"$$e_k=\mathrm{ok}\;n_k\,\mathrm{cv}(\mathrm{aunit}(u^{\mathrm{el}})\to\mathrm{gunit}(u_\gamma))\,\gamma_k\qquad(0\le k<Y)$$",
 time=r"要素は $T$ によらない（期間で現れる）。", coef=r"$e_k$（列 `b61.e`）。", consts=[], notes="",
)

U["B6-02"] = dict(
 stage="B6", comp=[], role="AUXILIARY", role2=None,
 why="年ごとの燃料（ガス・油・地域熱）の排出 $f_k$。B6-03 の入力。",
 inputs=["operation.gas.table.value", "operation.oil.table.value", "operation.district_heat.table.value", "operation.gas_factor_id", "operation.oil_factor_id", "operation.district_heat_factor_id"],
 cond=r"燃料ごとに $\mathrm{G}_{\mathrm{B6}}(f,\mathrm{aunit}(u))$（単位が「単位/year」でなければ偽）。偽は $n_{\mathrm{skip}}$。",
 msp=r"$$f_k=\sum_{\phi\in\{\mathrm{gas},\mathrm{oil},\mathrm{dh}\}}v^{\phi}_k\,\mathcal{F}_{\mathrm{B6}}\big(f^{\phi},\mathrm{aunit}(u^{\phi})\big)\qquad(0\le k<Y)$$",
 time=r"要素は $T$ によらない。", coef="燃料の係数（架空）。", consts=[], notes="燃料の添字 $\\phi$ は本台帳で導入（gas・oil・dh）。",
)

U["B6-03"] = dict(
 stage="B6", comp=[("B6", 1)], role="DIRECT", role2=None,
 why="COMP の B6 の行（+1）。年セル $B^{(\\mathrm{B6\\text{-}03})}_k=e_k+f_k$ として合計に入る（B2 を数えるときは B2-01 が B6 から引かれる）。",
 inputs=[], cond="なし（B6-01・B6-02 の年ごとの値の重みつきの和）。",
 msp=r"$$V_{@B6-03}(T)=\sum_{k=0}^{Y-1}w_k(T)\,\big(e_k+f_k\big)$$",
 time=r"年セルの和、連続な区分一次（格子 $k$ だけで傾きが変わる）。", coef=r"$B^{(\mathrm{B6\text{-}03})}_k=e_k+f_k$（`b63.a`）。", consts=[], notes="",
)

U["B2-01"] = dict(
 stage="B2", comp=[("B2", 1), ("B6", -1)], role="DIRECT", role2=None,
 why="COMP に 2 行（B2 に +1、B6 に −1 で $\\beta=\\iota_{\\mathrm{B2}}$）。B2 を数えるときは B6 からの付け替えで、合計への正味の寄与は 0。B2 を数えず B6 を数えるときは B6 から引かない。",
 inputs=["operation.facility_management_ratio"], cond=r"$[0\le\rho_{\mathrm{B2}}\le1]$。偽なら値 0.0、computed 偽。",
 msp=r"$$V_{@B2-01}(T)=[0\le\rho_{\mathrm{B2}}\le1]\;\rho_{\mathrm{B2}}\,EL(T),\qquad EL(T)=\sum_{k=0}^{Y-1}e_k\,w_k(T)$$",
 time=r"年セルの和（振幅 $\rho_{\mathrm{B2}}e_k$）、連続な区分一次。", coef=r"$B^{(\mathrm{B2\text{-}01})}_k=\rho_{\mathrm{B2}}e_k$（`b61.e`×`b21.share`）。TIME のスペクトル EL を使う。", consts=[],
 notes="段階の値では B2 の $+B_k$ と B6 の $-B_k$ は別の役割の項として残す（17 章 01 の 3 節）。",
)

U["X-11"] = dict(
 stage="B6", comp=[], role="REFERENCE", role2=None,
 why="床面積あたりの統計値による運用電力の推定（推定値）。B6 の段階の値には B6-03 を使い、X-11 は合計に入らない。",
 inputs=["project.gross_floor_area", "operation.electricity_per_m2_per_year", "operation.grid.unit", "operation.grid.licence_status"],
 cond=r"$[A>0][I^{\mathrm{el}}\ge0][\mathrm{cv}(\mathrm{kWh}\to\mathrm{gunit}(u_\gamma))\ne\bot][\mathrm{lic}_\gamma=\mathrm{PERMITTED\_PUBLIC}]$。偽なら ⊥（0 ではない）。",
 msp=r"$$V_{@X-11}(T)=[\cdots]\;A\,I^{\mathrm{el}}\,\mathrm{cv}(\mathrm{kWh}\to\mathrm{gunit}(u_\gamma))\,G(T),\qquad G(T)=\sum_{k=0}^{Y-1}\gamma_k\,w_k(T)$$",
 time=r"連続な区分一次（格子だけ）。比 $X11(T)/G(T)$ は一定。", coef=r"$c_{11}=A\,I\,\mathrm{cv}$（$T$ によらない）、スペクトル G（`x06.g`）。", consts=[], notes="",
)

U["B7-01"] = dict(
 stage="B7", comp=[], role="AUXILIARY", role2=None,
 why="上水の年ごとの排出。B7-04 の入力。",
 inputs=["water_waste.water.table.value", "water_waste.water_factor_id"], cond=r"$\mathrm{G}_{\mathrm{B7}}(f^{\mathrm{wat}},\mathrm{aunit}(u^{\mathrm{wat}}))$。偽なら $n_{\mathrm{skip}}=1$、年の値は 0。",
 msp=r"$$b^{\mathrm{wat}}_k=v^{\mathrm{wat}}_k\,\mathcal{F}_{\mathrm{B7}}\big(f^{\mathrm{wat}},\mathrm{aunit}(u^{\mathrm{wat}})\big)\qquad(0\le k<Y)$$",
 time=r"要素は $T$ によらない（期間で現れる）。", coef="上水の係数（架空）。", consts=[], notes="記号 $b^{\\mathrm{wat}}_k$ は本台帳で導入。",
)

U["B7-02"] = dict(
 stage="B7", comp=[], role="AUXILIARY", role2=None,
 why="下水の年ごとの排出。B7-04 の入力。",
 inputs=["water_waste.sewage.table.value", "water_waste.sewage_factor_id"], cond=r"B7-01 と同じ形（下水）。",
 msp=r"$$b^{\mathrm{sew}}_k=v^{\mathrm{sew}}_k\,\mathcal{F}_{\mathrm{B7}}\big(f^{\mathrm{sew}},\mathrm{aunit}(u^{\mathrm{sew}})\big)$$",
 time=r"要素は $T$ によらない。", coef="下水の係数（架空）。", consts=[], notes="",
)

U["B7-03"] = dict(
 stage="B7", comp=[], role="AUXILIARY", role2=None,
 why="一般廃棄物の年ごとの排出。B7-04 の入力。",
 inputs=["water_waste.municipal_waste.table.value", "water_waste.waste_factor_id"], cond=r"B7-01 と同じ形（一般廃棄物）。",
 msp=r"$$b^{\mathrm{msw}}_k=v^{\mathrm{msw}}_k\,\mathcal{F}_{\mathrm{B7}}\big(f^{\mathrm{msw}},\mathrm{aunit}(u^{\mathrm{msw}})\big)$$",
 time=r"要素は $T$ によらない。", coef="一般廃棄物の係数（架空）。", consts=[], notes="",
)

U["B7-04"] = dict(
 stage="B7", comp=[("B7", 1)], role="DIRECT", role2=None,
 why="COMP の B7 の行（+1）。年セル $B^{(\\mathrm{B7\\text{-}04})}_k$ として合計に入る。",
 inputs=[], cond="なし。",
 msp=r"$$V_{@B7-04}(T)=\sum_{k=0}^{Y-1}w_k(T)\,\big(b^{\mathrm{wat}}_k+b^{\mathrm{sew}}_k+b^{\mathrm{msw}}_k\big)$$",
 time=r"年セルの和、連続な区分一次。", coef=r"$B^{(\mathrm{B7\text{-}04})}_k$（`b74.a`）。", consts=[], notes="",
)

U["X-02"] = dict(
 stage="SUM", comp=[], role="AGGREGATE", role2="DECISION",
 why="段階×単位の 0/±1 行列で 14 段階の値を作る合成（合計の直前の層 L3）。完全性の判定（complete）も持つ。",
 inputs=["boundary.included_lifecycle_stages.value"],
 cond=r"$\iota_s=[s\in\text{評価範囲}]$。B2 が対象外で B6 が対象なら B6 から B2-01 を引かない（$\beta=\iota_{\mathrm{B2}}$）。完全性：対象段階の単位（CHK：COMP の単位と A5-01〜03・B6-01・B6-02・B7-01〜03）に除外・部分・未計算があれば偽。",
 msp=r"$$\mathrm{full}_s(T)=\sum_{u}\sigma_{s,u}\,V_u(T),\qquad \mathrm{bs}_s(T)=\iota_s\sum_u\sigma_{s,u}\,\beta_{s,u}\,V_u(T)\ \ (\iota_s=1\text{ の段階だけキーを持つ}),\qquad \beta_{\mathrm{B6},@B2-01}=\iota_{\mathrm{B2}}$$ $$\mathrm{complete}(T)=\Big[\sum_{(s,u)\in\mathrm{CHK}}\iota_s\,[\mathrm{bad}_u(T)\ge1]=0\Big],\quad \mathrm{bad}_u=[n_{\mathrm{skip}}>0]+[n_{\mathrm{routes\,skip}}>0]+[n_{\mathrm{partial}}>0]+[\mathrm{computed}=\text{偽}]\ (\text{論理和})$$",
 time=r"段階の値は区分一次（TH-1）。complete・incomplete_units は階段（B4-02 の $n_{\mathrm{partial}}$ が事象とともに変わる）。対象外の段階はキーごと無い（0 ではない）。",
 coef=r"$\sigma$（COMP の符号、(B6, B2-01) だけ −1）、$\beta$、$\iota$（17 章 02 の 3 節）。", consts=[],
 notes="by_stage_all は述語を掛けない 14 段階（$\\mathrm{full}_s$、QA-01・X-07 が使う）。",
)

U["SUM-01"] = dict(
 stage="SUM", comp=[], role="AGGREGATE", role2=None,
 why="アップフロント（A 段階の和）。合計そのものではなく、その一部の集計。",
 inputs=[], cond="対象の A 段階だけ。complete は X-02 の値。",
 msp=r"$$S_1(T)=\sum_{s\in\{\mathrm{A1\text{-}A3},\mathrm{A4},\mathrm{A5}\}}\iota_s\,\mathrm{bs}_s(T)$$",
 time=r"value は $T$ によらない（A 段階は定数の核だけ）。complete は X-02 の値で、事象とともに変わりうる階段（17 章 06 の標本では変化なし：「T 依存の構造だが標本では変化なし」）。", coef="段階の値の和。", consts=[], notes="",
)

U["SUM-02"] = dict(
 stage="SUM", comp=[], role="AGGREGATE", role2=None,
 why="エンボディド（B6・B7 以外の段階の和）。",
 inputs=[], cond="B6・B7 以外の対象段階。",
 msp=r"$$S_2(T)=\sum_{s\notin\{\mathrm{B6},\mathrm{B7}\}}\iota_s\,\mathrm{bs}_s(T)$$",
 time=r"区分一次（TH-1）。", coef="段階の値の和。", consts=[], notes="",
)

U["SUM-03"] = dict(
 stage="SUM", comp=[], role="AGGREGATE", role2=None,
 why="ホールライフ合計 $C(T)$ そのもの（L4）。直接寄与する 21 単位の値から作り、自身は合計に「寄与する」単位ではない。",
 inputs=[], cond="対象の全段階。",
 msp=r"$$C(T)=S_3(T)=\sum_s\iota_s\,\mathrm{bs}_s(T)=\sum_s\iota_s\sum_u\sigma_{s,u}\beta_{s,u}V_u(T)$$",
 time=r"$$C(T)=A_0+\sum_{t\in\Lambda}[t<T](P_t+Q_tT)+\sum_{g\in E}\theta_\varepsilon(T;g)(p_g+q_gT)$$ 区分一次（TH-1）、格子と事象で跳びうる（TH-2）。",
 coef=r"17 章 02 の全係数（$A^{\mathrm{init}}$、$A^{\mathrm{term}}$、$B^{(u)}_k$、$\Gamma$、$\Delta$、$\mathcal{A}_K$ ほか）。", consts=[],
 notes="区分一次なのは $T$ についてで、実時間 $t$ の排出の配分（TH-4 の $M([0,T])+Z(T)$）は別の問題（時間配分の非一意性：TH-4(c)、18 章 05）。",
)

U["SUM-04"] = dict(
 stage="SUM", comp=[], role="AGGREGATE", role2=None,
 why="延床面積あたりの合計（指標）。",
 inputs=["project.gross_floor_area"], cond=r"$[A>0]$。偽なら ⊥。",
 msp=r"$$\mathrm{SUM04}(T)=[A>0]\;C(T)\,\frac{1}{A}$$",
 time=r"区分一次（$C$ の定数倍）。", coef="—", consts=[], notes="",
)

U["SUM-05"] = dict(
 stage="SUM", comp=[], role="AGGREGATE", role2=None,
 why="年平均・延床面積あたり（指標）。",
 inputs=["project.gross_floor_area"], cond=r"$[A>0][T>0]$。偽なら ⊥。",
 msp=r"$$\mathrm{SUM05}(T)=[A>0]\;\frac{C(T)}{A\,T}$$",
 time=r"区間ごとの双曲線：$C=\alpha+\beta T$ の区間で $\beta/A+\alpha/(AT)$。区分一次ではない（TH-14）。$T\to0^+$ で $C(0^+)>0$ なら発散。", coef="—", consts=[], notes="",
)

U["SUM-06"] = dict(
 stage="SUM", comp=[], role="AGGREGATE", role2=None,
 why="t-CO2e への換算（指標）。",
 inputs=[], cond="なし。",
 msp=r"$$\mathrm{SUM06}(T)=10^{-3}\,C(T)$$",
 time=r"区分一次。", coef="—", consts=["1/1000（kg から t。式の中では除算）"], notes="",
)

U["SUM-07"] = dict(
 stage="SUM", comp=[], role="AGGREGATE", role2=None,
 why="段階別の割合（指標）。",
 inputs=[], cond=r"$[C(T)>0][\text{対象段階に負の値が 0 個}]$。偽なら defined = 偽、by_stage は空。",
 msp=r"$$\mathrm{share}_s(T)=[C>0]\,[\#\{s':\iota_{s'}=1,\ \mathrm{bs}_{s'}<0\}=0]\;\frac{\mathrm{bs}_s(T)}{C(T)}$$",
 time=r"区間ごとの一次分数関数（比）。定義される区間は $T$ で変わりうる（TH-14）。", coef="—", consts=[], notes="",
)

U["SUM-08"] = dict(
 stage="SUM", comp=[], role="AGGREGATE", role2="DECISION",
 why="基準案との差・削減率（指標）と、比較できるかの判定。",
 inputs=["boundary.baseline_scenario", "project.gross_floor_area", "boundary.included_lifecycle_stages.value", "boundary.results_gas_scope", "factors.release_year"],
 cond=r"比較可能 $=[b\ne\bot][A=A^b][T=T^b][\text{段階の集合が一致}][\mathrm{gs}=\mathrm{gs}^b][\{\mathrm{ry}_f\}=\{\mathrm{ry}^b_f\}]$（$T^b$ は基準案の評価期間）。理由は AREA・PERIOD・STAGES・GAS_SCOPE・FACTOR_VERSION の順。",
 msp=r"$$\Delta(T)=C(T)-C^b(T^b),\qquad \rho^{\mathrm{save}}(T)=[C^b>0]\,\frac{C^b-C(T)}{C^b}\qquad(\text{比較可能なときだけ。}C^b\text{ は基準案を同じ式で最初から計算した値})$$",
 time=r"比較可能なのは $T=T^b$ のときだけ（PERIOD の条件）なので、$T$ を動かすと状態が階段的に変わる。17 章 06 の標本では変化なし。", coef="—", consts=[],
 notes="集合の一致は互いに外れる要素の個数が両方 0（SPEC_MSP 3 節）。",
)

U["X-04"] = dict(
 stage="SUM", comp=[], role="BREAKDOWN", role2=None,
 why="ガス別の内訳と CO2e の再合算、段階の足し直し（QA-01 の検査に使う）。合計には入らない。",
 inputs=["factors.gas_amounts.value", "gwp.value", "gases.value"],
 cond=r"排出の行 $L_s=\{(f,\ \mathrm{act})\}$：係数 $f$ と活動量（係数を掛ける前の量）。電力は擬似の行 GRID（排出そのもの）、冷媒は REFR。B5 の行は初期と C 段階の行を $N_{C_{\mathrm{ren}}}(T)\,\varphi$ 倍したもの。**段階の述語を掛けない**（全 14 段階）。",
 msp=r"$$\mathrm{bg}_g(T)=\sum_s\sum_{(f,\mathrm{act})\in L_s(T),\,f\ne\mathrm{GRID,REFR}}\mathrm{act}\cdot\mathrm{ga}_{f,g},\qquad \mathrm{value}(T)=\sum_g\mathrm{GWP}_g\,\mathrm{bg}_g(T)+\mathrm{GRID}(T)+\mathrm{REFR}(T)$$ $$\mathrm{recomp}_s(T)=\sum_{(f,\mathrm{act})\in L_s(T)}\big([f\in\{\mathrm{GRID},\mathrm{REFR}\}]\,\mathrm{act}+[f\notin\{\cdot\}]\,\mathrm{act}\cdot F_f\big)$$",
 time=r"区分一次（活動量が年セル・事象の和）。17 章 06 で一部の葉は階段（行が事象とともに現れる）。", coef=r"ガス量 $\mathrm{ga}_{f,g}$、GWP（架空。$F_f=\sum_g\mathrm{GWP}_g\mathrm{ga}_{f,g}$ が生成器の約束）。",
 consts=[], notes="初版の 17 章 01 の 7 節は述語つきで書いて誤り（独立レビューで訂正）。by_stage_recomputed は述語なし。",
)

U["X-05"] = dict(
 stage="SUM", comp=[], role="BREAKDOWN", role2=None,
 why="CO2 だけの範囲の並行算定（ガスの範囲別の内訳）。合計には入らない。",
 inputs=["factors.gas_amounts.value"],
 cond=r"X-04 と同じ行。重み：係数の行は CO2 のガス量、GRID は 1、REFR は 0。値だけ段階の述語を掛ける（B2 を数えないときは B2 の分を加える）。",
 msp=r"$$\mathrm{CO2}_s(T)=\sum_{(f,\mathrm{act})\in L_s(T)}\big([f=\mathrm{GRID}]\,\mathrm{act}+[f\notin\{\mathrm{GRID},\mathrm{REFR}\}]\,\mathrm{act}\cdot\mathrm{ga}_{f,\mathrm{CO2}}\big),\qquad V_{@X-05}=\sum_s\iota_s\mathrm{CO2}_s+\iota_{\mathrm{B6}}(1-\iota_{\mathrm{B2}})\,\mathrm{CO2}_{\mathrm{B2}}$$",
 time=r"区分一次。", coef="CO2 のガス量（架空）。", consts=[], notes="重みごとの式は 17 章で照合していない（区分一次であることだけ 06 で確認）。",
)

U["X-07"] = dict(
 stage="SUM", comp=[], role="BREAKDOWN", role2=None,
 why="合計を年ごとに並べた系列と累積（年の配分の内訳）。累積の最後は $C(T)$。",
 inputs=["operation.facility_management_ratio"],
 cond=r"対象段階だけ。時点 0 に A 段階、各年に年次の排出（B6・B2・B7・B1 の漏洩と交換・B3）と事象（B4・B5）、最終年に C 段階と B1-04。B2/B6 の振り分けは X-02 と同じ（$\rho_{\mathrm{B2}}$、B2-01 が未計算なら 0）。",
 msp=r"$$s_0=\sum_{s\in\{\mathrm{A1\text{-}A3,A4,A5}\}}\iota_s\,\mathrm{full}_s,\qquad s_y(T)=\sum_{j:\,\mathrm{cell}(j)=y-1}a_j\,\kappa_j(T)+[y=Y]\,Z(T)\ \ (1\le y\le Y),\qquad \mathrm{cum}_y=\sum_{y'\le y}s_{y'},\quad \mathrm{value}=\mathrm{cum}_Y=C(T)$$",
 time=r"要素は区分一次で、列の長さは $Y$ で変わる。年の配分は $C$ からは一意に決まらない（TH-4(c)）：整数の時刻の事象は X-07 では年 $K$、TH-4 の実時間の測度では年 $K{+}1$ に置かれる。", coef=r"$Z(T)=A^{\mathrm{term}}+\iota_{\mathrm{B1}}R(T)$（17 章 01）。",
 consts=[], notes="X-07 はモデル自身の年配分の 1 つで、18 章の工程関数の年配分と異なる（非一意性の具体例）。",
)

U["QA-01"] = dict(
 stage="QA", comp=[], role="DECISION", role2=None,
 why="相互排他（A13-01/A13-03、A4-01/A4-02）と段階の足し直しの一致を判定する。値に入らない。",
 inputs=[], cond=r"(a) 14 段階について X-02 の $\mathrm{full}_s$ と X-04 の足し直し、(b) 資材の行で A13-01 と A13-03 の両方が 0 でない、(c) A4-01 と A4-02 の両方が 0 でない。",
 msp=r"$$\mathrm{viol}=\sum_s\big[\,|\mathrm{full}_s-\mathrm{recomp}_s|>10^{-9}\max(|\mathrm{full}_s|,1)\big]+\sum_i[a01_i\ne0][a03_i\ne0]+\sum_i[a41_i\ne0][a42_i\ne0],\qquad \mathrm{ok}=[\mathrm{viol}=0]$$",
 time=r"$T$ 依存の構造だが、標本では変化なし（17 章 06）。", coef="—", consts=["1e-9（相対の許容差、下限 1）"],
 notes="故障注入で検出力を確認（第 11 章 check_unified_controls）。",
)

U["QA-02"] = dict(
 stage="QA", comp=[], role="DECISION", role2=None,
 why="交換年一覧が評価期間の内側にあるかの検査。値に入らない（範囲外の交換は各単位の式が数えないだけ）。",
 inputs=["equipment.replacement_event_list.value", "refrigerants.change_years.value"],
 cond=r"設備の交換年一覧と冷媒の交換年一覧の各行。",
 msp=r"$$\mathrm{viol}_\rho(T)=\Big[\sum_{t\in L_\rho}\big([\neg(t\ge0)]+[t\ge0](1-\theta_\varepsilon(T;t))\big)\ge1\Big],\qquad \mathrm{warn}_\rho=\Big[\sum_{t\in L_\rho}[t=0]\ge1\Big],\qquad \mathrm{ok}=\Big[\sum_\rho\mathrm{viol}_\rho=0\Big]$$",
 time=r"階段（一覧の時刻 $\mathrm{sw}(t)$ で違反が消える）。", coef="—", consts=["ε = 1e-9"], notes="",
)

U["QA-03"] = dict(
 stage="QA", comp=[], role="DECISION", role2=None,
 why="実際に使われた係数（X-04 の行に現れる係数）の許諾と出典を検査する。値に入らない。",
 inputs=["factors.licence_status", "factors.source_url"],
 cond=r"使用 $\mathrm{use}_f(T)=[\text{X-04 の行に }f\text{ が 1 回以上現れる}]$。更新の行は事象があるときだけ現れるので $T$ に依る。",
 msp=r"$$\mathrm{viol}(T)=\sum_f\mathrm{use}_f(T)\,\big[\mathrm{lic}_f\ne\mathrm{PERMITTED\_PUBLIC}\ \lor\ \mathrm{src}_f=\text{空}\big],\qquad n_{\mathrm{used}}(T)=\sum_f\mathrm{use}_f(T),\qquad \mathrm{ok}=[\mathrm{viol}=0]$$",
 time=r"階段（初めて更新が数えられた時刻に係数が使用に加わる）。", coef="—", consts=[], notes="",
)

UCUR.update(U)

# ======== c2_corrections.py ========
# 独立の照合（check_units70.py の (d)〜(g)、2026-11-17）で見つけた台帳の誤り・不足の訂正。上の手書きの内容を置き換える。
# どれも本研究の独立概念モデル（架空データ）の定義で、J-CAT 原版の式・係数・セルは含まない。統一系の仕様
# （10_TRANSFORM_STUDY/research_code/specs/*.py）を読んで精密にし、独立の評価（check_units70.py の run・run_all）で照合した。

FIELDS.update({
 "project.states": ("\\delta_p^{\\mathrm{ovr}}", "—", "項目名 → 状態", "行ごとの値の状態の宣言（SYS-01。無ければ出典記録の状態）"),
 "materials.states": ("\\delta_{i,p}^{\\mathrm{ovr}}", "—", "項目名 → 状態", "資材の行の値の状態の宣言（SYS-01）"),
 "equipment.states": ("\\delta_{j,p}^{\\mathrm{ovr}}", "—", "項目名 → 状態", "設備の行の値の状態の宣言（SYS-01）"),
 "refrigerants.states": ("\\delta_{d,p}^{\\mathrm{ovr}}", "—", "項目名 → 状態", "冷媒の行の値の状態の宣言（SYS-01）"),
 "construction.states": ("\\delta^{\\mathrm{ovr}}", "—", "「一覧[行].項目」→ 状態", "施工の値（燃料・廃棄物の行を含む）の状態の宣言（SYS-01）"),
 "end_of_life.states": ("\\delta^{\\mathrm{ovr}}", "—", "「一覧[行].項目」→ 状態", "解体の値（作業・搬出の行を含む）の状態の宣言（SYS-01）"),
})

# 共通の部分式（cv・G_s・F_s・v_k・aunit・gunit・状態 δ・GWP）が読む項目。各単位の inputs_notation は、統一系の記録
# （inputs_reached）のうちこの型に当たるものを機械的に集めた一覧（02 の 2.2 節）。
NOTATION_PATTERNS = [
 (r"^factors\.", "係数ゲート G_s・換算済み係数 F_s"), (r"^unit_conversions\.", "換算 cv"), (r"\.conversions\.", "行固有の換算 cv_i"),
 (r"^gwp\.|^gases\.", "GWP・ガスのベクトル"),
 (r"^(operation|water_waste)\.[a-z_]+\.(kind|base|slope|table)$", "年次量 v_k（記述子と年次表）"),
 (r"^(operation|water_waste)\.[a-z_]+\.unit$", "年次量の単位 aunit・gunit"),
 (r"^provenance\.|\.provenance_id$|\.states$", "値の状態 δ（SYS-01）"),
]

# 索引の表（統一系の index.py が作る事象の格子など）の元になる入力の項目。unit_map.json の inputs には現れないので、
# inputs_reached に加える（入力の感度の照合で、これらが抜けていたことが分かった）。
INDEX_SOURCES = {
 "materials.events": ["materials.refresh_cycle"],
 "equipment.events": ["equipment.service_life", "equipment.replacement_event_list.value", "equipment.replacement_event_list#"],
 "refrigerants.events": ["refrigerants.service_life", "refrigerants.change_years.value", "refrigerants.change_years#"],
 "boundary.events": ["boundary.replacement_cycle"],
 "CYC": ["materials.refresh_cycle", "equipment.service_life"], "CYC.events": ["materials.refresh_cycle", "equipment.service_life"],
 "CLS": ["materials.material_class"], "CLS.x": ["materials.material_class"],
 "project.use_area_sorted": ["project.use_area_breakdown"],
 "operation.grid.steps": ["operation.grid.steps.from_index", "operation.grid.steps.value"],
 "project.states": ["project.states"], "materials.states": ["materials.states"], "equipment.states": ["equipment.states"],
 "refrigerants.states": ["refrigerants.states"], "construction.states": ["construction.states"], "end_of_life.states": ["end_of_life.states"],
 "construction.fuels.conversions": ["construction.fuels.conversions.factor", "construction.fuels.conversions.from_unit",
                                    "construction.fuels.conversions.to_unit"],
}

# X-02 の完全性の対 CHK（specs/system.py の STAGE_UNITS。COMP とは別）。
X02_CHK = [("A1-A3", "A13-01"), ("A1-A3", "A13-03"), ("A1-A3", "A13-04"), ("A1-A3", "X-01"), ("A4", "A4-01"), ("A4", "A4-02"),
           ("A5", "A5-01"), ("A5", "A5-02"), ("A5", "A5-03"), ("B1", "B1-02"), ("B1", "B1-03"), ("B1", "B1-04"), ("B2", "B2-01"),
           ("B2", "B6-01"), ("B3", "B3-01"), ("B4", "B4-02"), ("B5", "B5-01"), ("B6", "B6-01"), ("B6", "B6-02"), ("B7", "B7-01"),
           ("B7", "B7-02"), ("B7", "B7-03"), ("C1", "C1-01"), ("C2", "C2-01"), ("C3", "C3-01"), ("C3", "X-14"), ("C4", "C4-01")]

# 判定の単位が調べる箇所の表（02 の SYS-01〜03 の P・S・S' を復元できる形。行の添字 i・j・d・x は 02 の 2.2 節）。
SITES = {
 "SYS-01": {
  "doc": "値の状態を調べる 26 種類の項目。δ は owner の states[key]、無ければ owner の provenance_id の記録の value_state、記録が無ければ MISSING。"
         "一覧の行（燃料・廃棄物・作業・搬出）は owner＝construction・end_of_life、key＝「一覧[行].項目」。違反の並びは（組の順、行、項目の順）。",
  "columns": ["組", "項目", "owner", "適用の条件"],
  "rows": [["project", "gross_floor_area", "project", "常に"]]
          + [["materials[i]", f, "行", "常に"] for f in ("quantity", "waste_rate", "reuse_rate", "material_life", "repair_rate", "refresh_cycle",
                                                     "transport.mass_t", "transport.distance_km", "end_of_life.mass_kg")]
          + [["equipment[j]", "quantity", "行", "常に"], ["equipment[j]", "service_life", "行", "値がある、または交換年一覧が無い"],
             ["equipment[j]", "repair_rate", "行", "常に"], ["equipment[j]", "end_of_life_mass_kg", "行", "常に"]]
          + [["refrigerants[d]", f, "行", "常に"] for f in ("charge_mass_kg", "gwp", "annual_leak_rate", "replacement_loss_rate",
                                                         "end_of_life_recovery_rate")]
          + [["refrigerants[d]", "service_life（値は常に ⊥ とみなす）", "行", "耐用年数と交換年一覧の両方が無い"],
             ["construction", "electricity_kwh", "construction", "常に"], ["construction.fuels[x]", "quantity", "construction", "常に"],
             ["construction.waste_streams[x]", "mass_kg", "construction", "常に"],
             ["end_of_life.demolition_activities[x]", "quantity", "end_of_life", "常に"],
             ["end_of_life.waste_hauls[x]", "mass_t", "end_of_life", "常に"], ["end_of_life.waste_hauls[x]", "distance_km", "end_of_life", "常に"]],
 },
 "SYS-02": {
  "doc": "係数を使う箇所（24 種）と単位の換算だけの箇所（5 種）。違反＝[適用][活動の単位が ⊥]＋[適用][単位あり][係数の記録あり][換算 ⊥]"
         "（単位を調べない箇所は後半だけ）。換算だけの箇所は述語のどれかが偽なら違反。段階の不一致＝[適用][単位あり][記録あり][stg_f ≠ (s)]。"
         "n_checked＝適用の数の和。違反の場所は「場所の名前」の重複を除いて整列。",
  "columns": ["行", "適用の条件", "活動の単位（調べるか）", "係数", "換算（元 → 係数の単位）", "段階", "場所の名前"],
  "rows": [
   ["materials[i]", "composition = ⊥", "quantity_unit（調べる）", "factor_id", "u_i → u_f（行固有の換算あり）", "A1-A3", "materials[i].quantity_unit"],
   ["materials[i].composition[c]", "常に", "—", "factor_id", "kg → u_f", "A1-A3", "materials[i].composition"],
   ["materials[i]", "transport.delivery_factor_id ≠ ⊥", "quantity_unit（調べる）", "transport.delivery_factor_id", "u_i → u_f（行固有）", "A4", "materials[i].quantity_unit"],
   ["materials[i]", "transport.delivery_factor_id = ⊥", "—", "transport.factor_id", "tkm → u_f", "A4", "materials[i].transport"],
   ["materials[i]", "installation_factor_id ≠ ⊥", "quantity_unit（調べる）", "installation_factor_id", "u_i → u_f（行固有）", "A5", "materials[i].quantity_unit"],
   ["materials[i]", "常に", "—", "end_of_life.haul_factor_id", "tkm → u_f", "C2", "materials[i].end_of_life"],
   ["materials[i].end_of_life.routes[r]", "route ≠ LANDFILL", "—", "factor_id", "kg → u_f", "C3", "materials[i].end_of_life"],
   ["materials[i].end_of_life.routes[r]", "route = LANDFILL", "—", "factor_id", "kg → u_f", "C4", "materials[i].end_of_life"],
   ["equipment[j]", "常に", "quantity_unit（調べる）", "factor_id", "u_j → u_f", "A1-A3", "equipment[j].quantity_unit"],
   ["equipment[j]", "delivery_factor_id ≠ ⊥", "quantity_unit（調べる）", "delivery_factor_id", "u_j → u_f", "A4", "equipment[j].quantity_unit"],
   ["equipment[j]", "installation_factor_id ≠ ⊥", "quantity_unit（調べる）", "installation_factor_id", "u_j → u_f", "A5", "equipment[j].quantity_unit"],
   ["equipment[j]", "eol_factor_id ≠ ⊥", "—", "eol_factor_id", "kg → u_f", "C3", "equipment[j].end_of_life"],
   ["construction.fuels[x]", "常に", "unit（調べる）", "factor_id", "u_x → u_f（行固有）", "A5", "construction.fuels[x].unit"],
   ["construction.waste_streams[x]", "常に", "—", "factor_id", "kg → u_f", "A5", "construction.waste_streams[x]"],
   ["operation", "常に", "aunit(gas.unit)（調べる）", "gas_factor_id", "aunit → u_f", "B6", "operation.gas"],
   ["operation", "常に", "aunit(oil.unit)（調べる）", "oil_factor_id", "aunit → u_f", "B6", "operation.oil"],
   ["operation", "常に", "aunit(district_heat.unit)（調べる）", "district_heat_factor_id", "aunit → u_f", "B6", "operation.district_heat"],
   ["water_waste", "常に", "aunit(water.unit)（調べる）", "water_factor_id", "aunit → u_f", "B7", "water_waste.water"],
   ["water_waste", "常に", "aunit(sewage.unit)（調べる）", "sewage_factor_id", "aunit → u_f", "B7", "water_waste.sewage"],
   ["water_waste", "常に", "aunit(municipal_waste.unit)（調べる）", "waste_factor_id", "aunit → u_f", "B7", "water_waste.municipal_waste"],
   ["end_of_life.demolition_activities[x]", "常に", "unit（調べる）", "factor_id", "u_x → u_f", "C1", "end_of_life.demolition_activities[x].unit"],
   ["end_of_life.waste_hauls[x]", "常に", "—", "factor_id", "tkm → u_f", "C2", "end_of_life.waste_hauls[x]"],
   ["summary_quantities", "concrete_uptake_factor_id ≠ ⊥", "—", "concrete_uptake_factor_id", "m3 → u_f", "MEMO", "summary_quantities.concrete_uptake"],
   ["cost_items[x]", "常に", "currency（調べる）", "factor_id", "currency → u_f", "A1-A3", "cost_items[x]"],
   ["materials[i]（換算だけ）", "composition ≠ ⊥", "—", "—", "述語：cv_i(u_i → kg) ≠ ⊥", "—", "materials[i].quantity_unit"],
   ["construction（換算だけ）", "常に", "—", "—", "述語：gunit(u_γ) ≠ ⊥、cv(kWh → gunit) ≠ ⊥", "—", "construction.electricity"],
   ["operation（換算だけ）", "常に", "—", "—", "述語：aunit(u_el) ≠ ⊥、gunit ≠ ⊥、cv(aunit(u_el) → gunit) ≠ ⊥", "—", "operation.electricity"],
   ["operation（換算だけ）", "常に", "—", "—", "述語：aunit(u_gen) ≠ ⊥、aunit(u_el) ≠ ⊥、cv(aunit(u_gen) → aunit(u_el)) ≠ ⊥", "—", "operation.onsite_generation"],
   ["operation（換算だけ）", "常に", "—", "—", "述語：aunit(u_exp) ≠ ⊥、aunit(u_el) ≠ ⊥、cv(aunit(u_exp) → aunit(u_el)) ≠ ⊥", "—", "operation.onsite_export"],
  ]},
 "SYS-03": {
  "doc": "係数の参照（24 種）。参照ごとに：ID が ⊥ なら「場所 (no factor)」、記録が無ければ「factors{ID} (no record)」、記録があれば"
         "その係数の参照の数に足す。許諾が PERMITTED_PUBLIC でないか出典が空の係数（参照が 1 つ以上）は「factors{ID}.licence_status」、"
         "電力係数の許諾が PERMITTED_PUBLIC でなければ「operation.grid」。n_references_affected＝無い参照の数＋記録の無い参照の数"
         "＋許諾・出典の欠けた係数への参照の数＋[電力係数の許諾が不可]。n_checked＝適用の数の和＋1。",
  "columns": ["行", "適用の条件", "係数の ID の列", "場所の名前"],
  "rows": [
   ["materials[i]", "composition = ⊥", "factor_id", "materials[i].factor_id"],
   ["materials[i].composition[c]", "常に", "factor_id", "materials[i].composition[c].factor_id"],
   ["materials[i]", "epd ≠ ⊥", "epd.factor_id", "materials[i].epd.factor_id"],
   ["materials[i]", "installation_factor_id ≠ ⊥", "installation_factor_id", "materials[i].installation_factor_id"],
   ["materials[i]", "transport.delivery_factor_id ≠ ⊥", "transport.delivery_factor_id", "materials[i].transport.delivery_factor_id"],
   ["materials[i]", "transport.delivery_factor_id = ⊥", "transport.factor_id", "materials[i].transport.factor_id"],
   ["materials[i]", "常に", "end_of_life.haul_factor_id", "materials[i].end_of_life.haul_factor_id"],
   ["materials[i].end_of_life.routes[r]", "常に", "factor_id", "materials[i].end_of_life.routes[r].factor_id"],
   ["equipment[j]", "常に", "factor_id", "equipment[j].factor_id"],
   ["equipment[j]", "eol_factor_id ≠ ⊥", "eol_factor_id", "equipment[j].eol_factor_id"],
   ["equipment[j]", "delivery_factor_id ≠ ⊥", "delivery_factor_id", "equipment[j].delivery_factor_id"],
   ["equipment[j]", "installation_factor_id ≠ ⊥", "installation_factor_id", "equipment[j].installation_factor_id"],
   ["construction.fuels[x]", "常に", "factor_id", "construction.fuels[x].factor_id"],
   ["construction.waste_streams[x]", "常に", "factor_id", "construction.waste_streams[x].factor_id"],
   ["operation", "常に", "gas_factor_id", "operation.gas_factor_id"], ["operation", "常に", "oil_factor_id", "operation.oil_factor_id"],
   ["operation", "常に", "district_heat_factor_id", "operation.district_heat_factor_id"],
   ["water_waste", "常に", "water_factor_id", "water_waste.water_factor_id"], ["water_waste", "常に", "sewage_factor_id", "water_waste.sewage_factor_id"],
   ["water_waste", "常に", "waste_factor_id", "water_waste.waste_factor_id"],
   ["end_of_life.demolition_activities[x]", "常に", "factor_id", "end_of_life.demolition_activities[x].factor_id"],
   ["end_of_life.waste_hauls[x]", "常に", "factor_id", "end_of_life.waste_hauls[x].factor_id"],
   ["summary_quantities", "concrete_uptake_factor_id ≠ ⊥", "concrete_uptake_factor_id", "summary_quantities.concrete_uptake_factor_id"],
   ["cost_items[x]", "常に", "factor_id", "cost_items[x].factor_id"],
  ]},
 "X-04": {
  "doc": "排出の行 L_s(T)：係数 f ごとに活動量（係数を掛ける前の量）を足す。マスクは各単位の述語と同じ。段階の述語は掛けない（全 14 段階）。"
         "擬似の行：GRID（買電の排出そのもの）、REFR（冷媒の排出そのもの）。by_gas_g＝Σ_f（全段階の活動量の和）·ga_{f,g}（g はシナリオのガスのベクトル）、"
         "co2e_from_gases＝Σ_g GWP_g·by_gas_g、grid_co2e＝V(A5-01)＋EL(T)＋N_ren(T)φ·V(A5-01)、refrigerant_co2e＝V(B1-02)＋V(B1-03)＋V(B1-04)。"
         "QA-03 の使用：行のマスクが真（活動量が 0 でもよい）の係数。更新のときだけ現れる行（資材の据付、設備の搬入・据付）は回数が 1 以上のとき。",
  "columns": ["段階", "行（マスク）", "活動量"],
  "rows": [
   ["A1-A3", "資材の汎用の行（kind=GENERIC、q_ord ≠ ⊥）", "q_ord_i·c*_i"], ["A1-A3", "EPD の行（kind=EPD、q_ord ≠ ⊥）", "q_ord_i·c*_i"],
   ["A1-A3", "複合品の構成材（kind=COMPOSITE、q_ord ≠ ⊥）", "q_ord_i·c*_i·mf_ij·cv(kg→u_f)"],
   ["A1-A3", "上の 3 種で 0<r^uq_i<1 の行（A13-04）", "上の活動量 × r/(1−r)"], ["A1-A3", "設備（X-01 の述語）", "Q_j·cv(u_j→u_f)"],
   ["A4", "A4-01 の述語", "M·D·cv(tkm→u_f)"], ["A4", "A4-02 の述語", "q_ord_i·cv_i(u_i→u_f)"],
   ["A5", "A5-02・A5-03 の述語", "Q·cv、m·cv"], ["A5", "擬似 GRID", "V(A5-01)"], ["B1", "擬似 REFR", "V(B1-02)＋V(B1-03)＋V(B1-04)"],
   ["B2", "擬似 GRID", "V(B2-01)"],
   ["B3", "修繕率 r ≥ 0・r ≠ 0 で初期排出が 0 でない行の A1-A3 の行（資材は汎用・EPD・構成材、設備は X-01）", "活動量 × r × (T − Σ_{更新のある年セル k} w_k(T))"],
   ["B4", "n_i(T) ≥ 1 の資材の A1-A3・A4・C2・C3・C4 の行と据付の行、|E_j(T)| ≥ 1 の設備の X-01・X-14・搬入・据付の行", "活動量 × n_i(T)、× |E_j(T)|"],
   ["B5", "A1-A3（A13-04 を含む）・A4・A5・C1〜C4 の行と A5 の GRID", "活動量 × N_ren(T)·φ（rs ≠ NONE かつ 0≤φ≤1 のとき）"],
   ["B6", "燃料の行（ゲートが真）", "Σ_k w_k(T)·v^φ_k·cv(aunit→u_f)"], ["B6", "擬似 GRID", "EL(T) − V(B2-01)（B2 を数えるかによらない）"],
   ["B7", "水・下水・廃棄物の行（ゲートが真）", "Σ_k w_k(T)·v_k·cv"],
   ["C1", "C1-01 の述語", "Q·cv"], ["C2", "C2-01 の資材の行と搬出の行", "m·0.001·D·cv、M·D·cv"],
   ["C3", "C3-01 の経路と X-14", "m·fr·cv、m·cv"], ["C4", "C4-01 の経路", "m·fr·cv"],
  ]},
}

UCUR["X-02"]["cond"] = (r"$\iota_s=[s\in\text{評価範囲}]$。B2 が対象外で B6 が対象なら B6 から B2-01 を引かない（$\beta=\iota_{\mathrm{B2}}$）。"
    r"完全性の対 CHK（`specs/system.py` の STAGE_UNITS。COMP とは別。JSON の `x02_chk`）：A1-A3｛A13-01・A13-03・A13-04・X-01｝、A4｛A4-01・A4-02｝、"
    r"A5｛A5-01・A5-02・A5-03｝、B1｛B1-02・B1-03・B1-04｝、B2｛B2-01・B6-01｝、B3｛B3-01｝、B4｛B4-02｝、B5｛B5-01｝、B6｛B6-01・B6-02｝、"
    r"B7｛B7-01・B7-02・B7-03｝、C1｛C1-01｝、C2｛C2-01｝、C3｛C3-01・X-14｝、C4｛C4-01｝（A5-04・B6-03・B7-04 は除外の件数を持たないので入らない）。"
    r"incomplete_units は、$\iota_s=1$ の対で $\mathrm{bad}_u\ge1$ の単位の整列した一覧。")
UCUR["SYS-01"]["cond"] = (r"調べる 26 種類の項目 $P$（延床面積 1、資材 9、設備 4、冷媒 6、施工 3、解体 3。全表は JSON の `sites.SYS-01`）。設備の耐用年数は、値が ⊥ で交換年一覧があるときだけ調べない。冷媒の耐用年数は、耐用年数と交換年一覧の両方が無いときだけ MISSING として数える。$\delta_p$ は owner の `states` の宣言（一覧の行はキー「一覧[行].項目」）、無ければ owner の出典記録の `value_state`、記録が無ければ MISSING。")
UCUR["SYS-01"]["inputs"] = UCUR["SYS-01"]["inputs"] + [
    "provenance.key", "project.provenance_id", "materials.provenance_id", "equipment.provenance_id", "refrigerants.provenance_id",
    "construction.provenance_id", "end_of_life.provenance_id", "project.states", "materials.states", "equipment.states", "refrigerants.states",
    "construction.states", "end_of_life.states", "equipment.replacement_event_list#", "refrigerants.change_years#"]
_FACTOR_REFS = ["materials.factor_id", "materials.composition#", "materials.composition.factor_id", "materials.transport.delivery_factor_id",
                "materials.transport.factor_id", "materials.installation_factor_id", "materials.end_of_life.haul_factor_id",
                "materials.end_of_life.routes.factor_id", "equipment.factor_id", "equipment.delivery_factor_id", "equipment.installation_factor_id",
                "equipment.eol_factor_id", "construction.fuels.factor_id", "construction.waste_streams.factor_id", "operation.gas_factor_id",
                "operation.oil_factor_id", "operation.district_heat_factor_id", "water_waste.water_factor_id", "water_waste.sewage_factor_id",
                "water_waste.waste_factor_id", "end_of_life.demolition_activities.factor_id", "end_of_life.waste_hauls.factor_id",
                "summary_quantities.concrete_uptake_factor_id", "cost_items.factor_id"]
UCUR["SYS-02"]["inputs"] = UCUR["SYS-02"]["inputs"] + [p for p in _FACTOR_REFS if p != "materials.composition#"] + [
    "materials.composition#", "materials.end_of_life.routes.route", "equipment.quantity_unit", "operation.electricity.unit",
    "operation.onsite_generation.unit", "operation.onsite_export.unit", "operation.gas.unit", "operation.oil.unit", "operation.district_heat.unit",
    "water_waste.water.unit", "water_waste.sewage.unit", "water_waste.municipal_waste.unit"]
UCUR["SYS-02"]["cond"] = (r"使う箇所の表 $\mathcal{S}$（JSON の `sites.SYS-02`：係数を使う 24 種と単位の換算だけの 5 種）。各箇所 $\sigma$ は（適用の条件、活動の単位 $a_\sigma$ を調べるか、係数 $f_\sigma$、換算、期待する段階 $s_\sigma$、場所の名前）を持つ。年次量の単位は「単位/year」の分母を読む。")
UCUR["SYS-03"]["inputs"] = UCUR["SYS-03"]["inputs"] + _FACTOR_REFS + ["materials.epd#", "materials.epd.factor_id"]
UCUR["SYS-03"]["cond"] = (r"参照の表 $\mathcal{S}'$（JSON の `sites.SYS-03`、24 種）。$n_{\mathrm{affected}}$ は参照ごとに数える（同じ係数への参照は別々）。電力係数の許諾は別に 1 件。違反の一覧は重複を除いて整列。")
UCUR["X-12"]["inputs"] = ["materials.transport.delivery_factor_id", "materials.transport.mass_t", "materials.transport.distance_km",
                          "materials.transport.factor_id", "materials.transport.load_factor"]
UCUR["X-05"]["inputs"] = ["factors.gas_amounts.value", "boundary.included_lifecycle_stages.value"]
UCUR["X-05"]["cond"] = (r"X-04 と同じ行（JSON の `sites.X-04`）。重み：係数の行は CO2 のガス量 $\mathrm{ga}_{f,\mathrm{CO2}}$（無ければ 0）、GRID は 1、REFR は 0。"
    r"B6 は B2 を数えるかによらず GRID の $-V_{\mathrm{B2\text{-}01}}$ を含むので、値だけ段階の述語を掛け、B2 を数えず B6 を数えるときは $\mathrm{CO2}_{\mathrm{B2}}$ を加える。")
UCUR["X-04"]["cond"] = (r"排出の行 $L_s(T)=\{(f,\ \mathrm{act})\}$：係数 $f$ ごとの活動量（係数を掛ける前の量。マスクは各単位の述語）。行・マスク・活動量の全表は JSON の `sites.X-04`。B3 は修繕の行×率×修繕年数 $T-\sum_k w_k(T)$（更新のある年セル $k$）、B4 は更新した行×回数、B5 は A・C 段階の行×$N_{C_{\mathrm{ren}}}(T)\varphi$、B6 は燃料の行と GRID $EL(T)-V_{\mathrm{B2\text{-}01}}$。**段階の述語を掛けない**（全 14 段階）。$\mathrm{GRID}(T)=V_{\mathrm{A5\text{-}01}}(1+N_{C_{\mathrm{ren}}}(T)\varphi)+EL(T)$、$\mathrm{REFR}=V_{\mathrm{B1\text{-}02}}+V_{\mathrm{B1\text{-}03}}+V_{\mathrm{B1\text{-}04}}$。")
UCUR["QA-03"]["cond"] = (r"使用 $\mathrm{use}_f(T)=1$ ⇔ $f$ が X-04 の行（JSON の `sites.X-04`）の係数でその行のマスクが真（活動量が 0 でもよい）。更新のときだけ現れる行（資材の据付、設備の搬入・据付）は回数が 1 以上のときだけなので $T$ に依る。")
UCUR["B4-02"]["cond"] = (r"1 回の更新の排出 $u_i$ は初期の行の値（製造・輸送・搬出・処理・処分）と据付の和。設備は製造・搬入・据付・廃棄。"
    r"$n_{\mathrm{partial}}(T)=\sum_i[\mathrm{pt}_i][n_i(T)\ge1]+\sum_j[\mathrm{pt}_j][|E_j(T)|\ge1]$。$\mathrm{pt}_i$＝行 $i$ が A13-01・A13-03・A4-01・A4-02・C2-01 のどれかで除外、"
    r"$\neg[m^{\mathrm{eol}}_i\ge0]$、C3-01・C4-01 で除外された経路がある、または据付の係数があるのにゲートが偽か $q^{\mathrm{ord}}_i=\bot$。"
    r"$\mathrm{pt}_j$＝X-01 か X-14 で除外、または搬入・据付の係数があるのにゲートが偽か $\neg[Q_j\ge0]$。")
UCUR["B2-01"]["why"] = (r"COMP に 2 行（B2 に +1、B6 に −1 で $\beta=\iota_{\mathrm{B2}}$）。合計への正味の寄与は $\iota_{\mathrm{B2}}(1-\iota_{\mathrm{B6}})V_{\mathrm{B2\text{-}01}}$〔P〕"
    r"（代数：$\iota_{\mathrm{B2}}V+\iota_{\mathrm{B6}}(V_{\mathrm{B6\text{-}03}}-\iota_{\mathrm{B2}}V)$）。B2 と B6 をともに数えるときは B6 からの付け替えで 0、B2 だけなら $+V$、B6 だけなら B6 から引かない（0）。")
UCUR["SUM-08"]["notes"] = (r"集合の一致は互いに外れる要素の個数が両方 0（SPEC_MSP 3 節）。基準案が無い（$b=\bot$ または基準案の登録に無い）ときは NO_BASELINE。"
    r"出力キー baseline は COMPARED、reasons は NOT_COMPARABLE のときだけ現れる。$C^b$ は基準案を自身の評価期間 $T^b$ で計算した値。")
for _u in ("A13-01", "X-03"):
    UCUR[_u]["notes"] = (UCUR[_u]["notes"] + " " if UCUR[_u]["notes"] else "") + \
        "依存の A13-02 は値の式には現れない（実行形が X-04 の行のために構成材の受け渡しのキー `_parts` を読む）。"



# 記号の衝突の訂正：1 回の更新の排出を u_i・u_j と書いていたが、u_i・u_j は行の数量単位（2.2 節）と同じ記号なので
# e^{ren}_i・e^{ren}_j に改める（本台帳で導入）。
def _ren(uid, key, pairs):
    t = UCUR[uid][key]
    for a, b in pairs:
        assert a in t, (uid, key, a)
        t = t.replace(a, b)
    UCUR[uid][key] = t
_ren("B4-02", "msp", [(r"$$u_i=a01_i", r"$$e^{\mathrm{ren}}_i=a01_i"), (r"$$u_j=x01_j", r"$$e^{\mathrm{ren}}_j=x01_j"),
                      (r"u_i\,\theta_\varepsilon(T;nc_i)", r"e^{\mathrm{ren}}_i\,\theta_\varepsilon(T;nc_i)"),
                      (r"\sum_{\tau\in E_j(T)}u_j", r"\sum_{\tau\in E_j(T)}e^{\mathrm{ren}}_j"), (r"y(\tau)=y}u$$", r"y(\tau)=y}e^{\mathrm{ren}}$$")])
_ren("B4-02", "time", [(r"跳び $u$", r"跳び $e^{\mathrm{ren}}$")])
_ren("B4-02", "coef", [(r"=u_i$（列", r"=e^{\mathrm{ren}}_i$（列"), (r"$u_i$ は A13-01", r"$e^{\mathrm{ren}}_i$ は A13-01")])
_ren("B4-02", "cond", [(r"1 回の更新の排出 $u_i$ は", r"1 回の更新の排出 $e^{\mathrm{ren}}_i$（本台帳で導入。行の数量単位 $u_i$ とは別の記号）は")])
_ren("X-08", "msp", [(r"n_i(T)>0}u_i+", r"n_i(T)>0}e^{\mathrm{ren}}_i+"), (r"E_j(T)\ne\emptyset}u_j,", r"E_j(T)\ne\emptyset}e^{\mathrm{ren}}_j,"),
                     (r"u_j\,|E_j(T)|", r"e^{\mathrm{ren}}_j\,|E_j(T)|")])
_ren("X-08", "coef", [(r"$u_i,u_j$ は B4-02 と同じ", r"$e^{\mathrm{ren}}_i,e^{\mathrm{ren}}_j$ は B4-02 と同じ")])


# 件数の定義の補い（独立の評価で、式の述語だけでは決まらなかったもの）
def _note(uid, text):
    UCUR[uid]["notes"] = (UCUR[uid]["notes"] + " " if UCUR[uid]["notes"] else "") + text
_note("A4-01", "n_skipped は搬入係数の無い行のうち述語が偽の行（搬入係数のある行は A4-02 の対象で、ここでは数えない）。")
_note("X-12", "n_skipped は A4-01 と同じく搬入係数の無い行のうち述語が偽の行。")
_note("C3-01", "n_skipped＝$\\neg[m^{\\mathrm{eol}}_i\\ge0]$ の資材の行（C4-01 と同じ行を数える）、n_routes_skipped＝質量が有効な行の LANDFILL 以外の経路のうち $[\\mathrm{fr}\\ge0]$ かゲートが偽のもの。")
_note("C4-01", "n_skipped は C3-01 と同じ行、n_routes_skipped は LANDFILL の経路について同じ規則。")
_note("X-15", "出力 kind の文字列は EPD・COMPOSITE・GENERIC（式の GEN・COMP）、どれにも当たらない行は ⊥。")


# 独立の照合（c2）で直した点（単位ごと。JSON の units[].c2_check.fixes）
C2_FIXES = {
 "X-02": ["完全性の対 CHK の記述を訂正（COMP の単位の集合ではなく specs/system.py STAGE_UNITS の 27 対。A5-04・B6-03・B7-04 は入らず、B6-01 は B2 と B6 の両方）"],
 "SYS-01": ["設備の耐用年数の適用条件を訂正（値があれば交換年一覧があっても数える）", "26 項目の全表を sites.SYS-01 に置き、δ の決め方（一覧の行のキー）を補った",
            "入力に出典記録の ID・states・交換年一覧の有無を加えた"],
 "SYS-02": ["箇所の表（29 種）を sites.SYS-02 に置いた", "入力に係数の参照の列・活動の単位の列を加えた"],
 "SYS-03": ["参照の表（24 種）を sites.SYS-03 に置き、n_references_affected が参照ごとの数であることを明記", "入力に係数の参照の列を加えた"],
 "X-12": ["入力の不足（輸送の質量・距離・係数・搬入係数の有無）を加えた", "n_skipped の範囲（搬入係数の無い行）を明記", "02 の理由の文が途中で切れていたのを訂正"],
 "X-05": ["入力に評価範囲の段階を加えた", "重みと B2・B6 の扱いを精密にした"],
 "X-04": ["行・マスク・活動量の全表を sites.X-04 に置き、B3 の修繕年数・B4 の回数・B5 の倍率・GRID・REFR の式を明記"],
 "QA-03": ["使用の定義（行のマスクが真、更新だけの行は回数が 1 以上）を精密にした"],
 "B4-02": ["n_partial を式で定義した", "1 回の更新の排出の記号 u_i・u_j を e^ren_i・e^ren_j に改めた（行の数量単位 u_i と衝突）"],
 "X-08": ["記号 u_i・u_j を e^ren_i・e^ren_j に改めた（B4-02 と同じ）"],
 "B2-01": ["合計への正味の寄与 ι_B2(1−ι_B6)V を明記（B2 だけを数える場合の記述が抜けていた）"],
 "SUM-08": ["条件つきの出力キー（baseline・reasons）と NO_BASELINE の条件を明記"],
 "A13-01": ["A13-02 への依存は受け渡しのキー _parts だけであることを明記"],
 "X-03": ["A13-02 への依存は受け渡しのキー _parts だけであることを明記", "02 の理由の文が途中で切れていたのを訂正"],
 "A4-01": ["n_skipped の範囲（搬入係数の無い行）を明記"],
 "C3-01": ["n_skipped・n_routes_skipped の定義を明記"], "C4-01": ["n_skipped・n_routes_skipped の定義を明記"],
 "X-15": ["出力 kind の文字列（EPD・COMPOSITE・GENERIC、⊥）を明記"],
 "X-09": ["02 の理由の文が途中で切れていたのを訂正"], "B1-01": ["02 の理由の文が途中で切れていたのを訂正"],
 "B3-02": ["02 の理由の文が途中で切れていたのを訂正"], "X-11": ["02 の理由の文が途中で切れていたのを訂正"],
 "X-10": ["02 の理由の文が途中で切れていたのを訂正"],
}


NOTATION.append((r"$e^{\mathrm{ren}}_i$, $e^{\mathrm{ren}}_j$", r"1 回の更新の排出（B4-02・X-08。資材の行 $i$・設備の行 $j$）。行の数量単位 $u_i$・$u_j$ とは別。", "本台帳で導入（c2 の訂正）"))


_note("X-04", "by_gas・co2e_from_gases も本照合の独立の評価 IND で統一系と一致した（6 節 (d)。17 章 07 では未照合）。")
_note("X-05", "重みごとの式は本照合の IND で統一系と一致した（6 節 (d)・(e)。17 章では区分一次の確認だけ）。")
UCUR["X-10"]["notes"] = "時間の式は 17 章では照合していない（17 章 01 の 7 節）。本照合の独立の評価 IND で、節点そのものとその前後を含めて統一系と一致した（6 節 (d)・(e)）。"

# ======== extract_render.py ========
import re
# -*- coding: utf-8 -*-
# ==== 02 の本文の書き出し（data/units70.json の内容から。数値は手で書かない） ====

STAGE_ORDER = ["PRE", "A1-A3", "A4", "A5", "B1", "B1/C", "B2", "B3", "B4", "B5", "B6", "B7", "C1", "C2", "C3", "C4", "C1-C4", "MEMO", "SUM", "QA"]
CHAPTERS = [
    ("5.1 入力の検査（PRE）", ["SYS-01", "SYS-02", "SYS-03", "SYS-04", "X-15"]),
    ("5.2 製品段階 A1-A3", ["A13-05", "A13-02", "A13-01", "A13-03", "A13-04", "X-01", "X-03", "X-13", "X-16", "X-17"]),
    ("5.3 輸送 A4・施工 A5", ["A4-01", "A4-02", "X-12", "A5-01", "A5-02", "A5-03", "A5-04"]),
    ("5.4 使用 B1（冷媒）", ["B1-01", "B1-02", "B1-03", "B1-04"]),
    ("5.5 使用 B3〜B5（修繕・更新・改修）", ["B3-01", "B3-02", "B4-01", "B4-03", "B4-02", "X-08", "B5-01"]),
    ("5.6 運用 B2・B6・B7", ["X-06", "B6-04", "B6-01", "B6-02", "B6-03", "B2-01", "X-11", "B7-01", "B7-02", "B7-03", "B7-04"]),
    ("5.7 解体・廃棄 C1〜C4", ["C1-01", "C2-01", "C3-01", "C4-01", "X-14", "C-05", "X-09"]),
    ("5.8 参考値（MEMO）と物量", ["STO-01", "STO-02", "X-10"]),
    ("5.9 合成・合計・指標", ["X-02", "SUM-01", "SUM-02", "SUM-03", "SUM-04", "SUM-05", "SUM-06", "SUM-07", "SUM-08"]),
    ("5.10 内訳（ガス・年・周期）", ["X-04", "X-05", "X-07"]),
    ("5.11 検査（QA）", ["QA-01", "QA-02", "QA-03", "QA-04"]),
]



def blockify(w, prefix, text):
    """文の中の $$…$$ を独立の行に出す（GitHub の表示式は行頭から）。prefix は最初の文の頭（箇条書きの記号など）。"""
    parts = re.split(r"(\$\$.*?\$\$)", text)
    first, pending = True, ""
    for p in parts:
        if p.startswith("$$") and p.endswith("$$") and len(p) > 4:
            if pending.strip() or first:
                w((prefix if first else "  ") + pending.strip())
                first = False
            pending = ""
            w("")
            w(p)
            w("")
        else:
            pending += p
    if pending.strip():
        w((prefix if first else "  ") + pending.strip())
    elif first:
        w(prefix)


def _fmt_e(x):
    if x is None:
        return "—"
    if x == 0:
        return "0"
    return "%.1e" % x


def _src(out, key, section=None):
    s = out["sources"][key]
    return "%s@%s%s" % (key, s["commit"] or "?", ("「%s」" % section) if section else "")


_MATH_OR_CODE = re.compile(r"(`[^`]*`|\$[^$]+\$)")


def _bars_in_math(m):
    """数式の中の縦棒を \\lvert・\\rvert（対にならないときは \\vert）にする。GitHub の表は数式の中の | でも列を分けるため。"""
    m = re.sub(r"\\\|(?=[A-Za-z])", r"\\Vert ", m)
    m = re.sub(r"\\\|", r"\\Vert", m)
    n = m.count("|")
    if n == 0:
        return m
    out, left = [], True
    for i, ch in enumerate(m):
        if ch != "|":
            out.append(ch)
            continue
        cmd = "\\vert" if n % 2 else ("\\lvert" if left else "\\rvert")
        left = not left
        nxt = m[i + 1] if i + 1 < len(m) else ""
        out.append(cmd + (" " if nxt.isascii() and nxt.isalpha() else ""))
    return "".join(out)


def _table_row(line):
    """表の行（| で始まる行）の数式・コードの中の | を、列の区切りと読まれない形にする（c3 の指摘：$|E^{per}(T;c_i)|$ が表を壊していた）。"""
    def f(mo):
        t = mo.group(0)
        if t.startswith("`"):
            return re.sub(r"(?<!\\)\|", r"\\|", t)
        return "$" + _bars_in_math(t[1:-1]) + "$"
    return _MATH_OR_CODE.sub(f, line)


def _inputs(w, r):
    """単位の入力：式が直接読む項目（記号・意味・単位・定義域・項目名）。正本は JSON の inputs_direct（data/units70_inputs.csv も同じ）。"""
    d = r["inputs_direct"]
    more = "共通の記号を通す項目 `inputs_notation` %d・到達する項目 `inputs_reached` %d（依存の閉包を含む）は JSON（2.2 節）" % (
        len(r["inputs_notation"]), len(r["inputs_reached"]))
    if not d:
        w("- 入力：式が直接読む項目は無い（依存の単位の出力を読む）。" + more + "。")
        return
    w("- 入力：式が直接読む項目 %d 個（下の表）。%s。" % (len(d), more))
    w("")
    w("| 記号 | 意味 | 単位 | 定義域 | 項目 |")
    w("|---|---|---|---|---|")
    for x in d:
        sym = x["symbol"] if x["symbol"] not in ("", "—") else None
        w("| %s | %s | %s | %s | `%s` |" % (("$%s$" % sym) if sym else "—", x["meaning"] or "—", x["unit"] or "—", x["domain"] or "—", x["path"]))
    w("")


def render_md(out, summary, commits, inputs_csv_current=False):
    U = {r["id"]: r for r in out["units"]}
    allids = [u for _, us in CHAPTERS for u in us]
    assert sorted(allids) == sorted(U), "章立てが 70 単位を覆わない"
    L = []
    w = L.append
    w("# 02 70 評価単位の完全台帳")
    w("")
    w("対象：独立概念モデルの 70 評価単位（第 09 章で定義し、第 10 章で 2 つの構造（マスク付き積和・節点スペクトル）に統一した計算体系）。データはすべて架空で、J-CAT 原版の式・係数・セル・値は含まない（原版の 667 式の変換実験は 15・16・19 章の別の研究で、本台帳の単位とは独立。19 章までの公開の記述以上のことは書かない）。"
      "本台帳の一致・照合は計算結果どうしの一致であり、**現実の建物の CO2 予測精度の主張ではない**。")
    w("")
    w("**70 単位は 70 個の独立な物理法則ではない。** ホールライフ合計 $C(T)$ に直接寄与するのは %d 単位（DIRECT）で、残りは補助の量・判定・内訳・合計と指標・参考値である（3 節）。"
      % out["role_counts"].get("DIRECT", 0))
    w("")
    w("機械可読の台帳：`data/units70.json`（全項目。`eval_py` は各単位の式の実行形）、`data/units70.csv`（1 単位 1 行の要約）、`data/unit_dependencies.csv`（依存の辺）。"
      "作り方：`tools/extract_units70.py`（原典の JSON・コード・表から抽出し、手で書いた式・役割と合わせる）。照合：`tools/check_units70.py`（6 節）。基準のコミット：作業木の HEAD `%s`。" % (out["worktree_head"] or "?"))
    w("")
    w("## 1. 読み方")
    w("")
    w("- 証拠の区分：" + "、".join("[%s] %s" % (k, v) for k, v in out["evidence_classes"].items()) + "。各主張の成立範囲と出典を併記する。原典が曖昧なときは弱い区分にする。")
    w("- 出典は略号@コミット「節」で書く。略号の一覧：")
    w("")
    w("| 略号 | ファイル（`whole-life-carbon-jcat-study/` から） | コミット |")
    w("|---|---|---|")
    for k, s in out["sources"].items():
        if k in ("VERJ", "LIM", "SMSP", "SKN", "E05B", "T06J", "ENG", "SPECS"):
            continue
        w("| %s | `%s` | %s |" % (k, s["path"].replace("whole-life-carbon-jcat-study/", ""), s["commit"] or "?"))
    w("")
    w("JSON の `sources` には、このほか VERJ（verification_*.json）・LIM（LIMITS.md）・SMSP（SPEC_MSP.md）・SKN（SPEC_KNOTS.md）・E05B（05b 対応表）・T06J（units_time.json）・ENG（unified.py）・SPECS（specs/system.py）の所在とコミットがある。")
    w("")
    w("- 各単位の節：1 行目に**役割**（構成表の行）｜段階｜導出（DERIVATIONS の D 番号）｜構造（① 積和①、K 節点スペクトル、②a TIME、②b AGG）｜スペクトル｜「T 非依存」｜出力キー（＝記号）｜依存（台帳の式が読む単位。基準計算の宣言と違えば併記）。続いて理由・入力（式が直接読む項目の記号・意味・単位・定義域・項目名の表）・条件とマスク・式・$T$ の形・係数と元の入力の対応・検証・注。式に述語がすべて現れる単位は条件の行を省いた（JSON の `conditions`）。ステップ数・スペクトルの全体は CSV。")
    w("- 検証の略記：**V11** の照合は第 11 章 VERIFICATION 2 節（10 集合・1,293 組）〔F〕。**NEG** k＝第 11 章の誤り検出（仕様を 1 か所壊す）でこの単位を期待先とした k 件がすべて検出された〔F〕。"
      "**共通の照合**（全 70 単位。断りが無ければどれも不一致 0、単位ごとの数は CSV の ver11_*・ledger_check_*・ind_*・knot_*・pred_* 列）：V11（統一系と基準計算、第 11 章）、L（本台帳の式の実行形 eval_py と統一系）、IND（本台帳の式を eval_py・基準計算を見ずに手で写した独立の評価と統一系）、KN（節点そのものとその前後での IND と統一系。帯 $(K,\\mathrm{sw}(K))$ の違いは単位の節に書く）〔いずれも F、6 節〕。**JMP** n/m＝時間の形から求めた跳びの理論値（0 でないもの n 個）と統一系の跳びの照合、不一致 m〔F〕。**§4**＝直接寄与する単位の共通の記録（[P][E][F][S]）。17 章 06 の $T$ 依存の分類（T06）は JSON・CSV の time_classification_17。他は〔区分〕要旨（出典の略号）。各記録の主張・範囲・出典の節・コミットの全文は JSON の `verification`。")
    w("- 「マスク付き積和で書けた」ことは、その形が**最小の表現である**ことを意味しない（最小性は本台帳では調べていない。17 章 05 の 3 節：保存した係数のままの節点形は最小でない）。")
    w("- $T$ は評価期間（算定に含める期間の長さ）で、排出が実際に起きる時刻 $t$ ではない。$T$ について区分一次であることは、排出を実時間に配分する方法を一意に決めない（17 章 03 の TH-4(c)、18 章 05）。")
    w("")
    w("## 2. 共通の記号")
    w("")
    w("既存の原典の記号（17 章 01・02、SPEC_MSP、SPEC_KNOTS、14 章 07）をそのまま使う。本台帳で新しく置いた記号は「本台帳で導入」と書く。")
    w("")
    w("### 2.1 共通の記号")
    w("")
    w("| 記号 | 定義 | 出典 |")
    w("|---|---|---|")
    for sym, d, src in out["notation"]:
        w("| %s | %s | %s |" % (sym, d, src))
    w("")
    w("### 2.2 入力の項目（各単位の式が直接読むもの）")
    w("")
    w("単位ごとの入力は JSON の 3 つの一覧：`inputs_direct`（その単位の式が直接読む項目。%d 項目）、`inputs_notation`（2.1 節の共通の部分式 $\\mathrm{cv}$・$\\mathrm{G}_s$・$\\mathcal{F}_s$・$v_k$・$\\mathrm{aunit}$・$\\mathrm{gunit}$・状態 $\\delta$・GWP が読む項目。統一系の記録から機械的に集めた）、`inputs_reached`（統一系の記録 unit_map.json の inputs と、事象の格子などの索引の表の元の項目）。"
      "依存の閉包の単位の入力も、その単位の値に効く（6 節 (f) の入力の感度で照合）。項目ごとの記号・単位・定義域（式が値を使う範囲。範囲外・欠損は述語で外して件数に数える）・意味は、各単位の節の「入力」の表と JSON の `inputs_direct`%s。架空データの生成器のデータモデル（%s）と式の述語から書いた。"
      "行の添字は $i$＝資材、$j$＝設備、$d$＝冷媒の機器、$x$＝施工・解体・費用の小さな表の行。判定の単位が調べる箇所の表と X-04 の行の表は JSON の `sites`。" % (len(set(x["path"] for r in out["units"] for x in r["inputs_direct"])),
                                                                     ("、項目ごとの一覧（直接読む単位つき）は `data/units70_inputs.csv`（`tools/extract_units70.py --write-inputs-csv` で JSON から作り、JSON と一致する）" if inputs_csv_current else ""),
                                                                     _src(out, "MODEL")))
    w("")
    w("### 2.3 出力キーの既定の意味")
    w("")
    w("| キー | 記号 | 単位 | 意味 |")
    w("|---|---|---|---|")
    for k, (sym, un, mean) in DEFAULT.items():
        w("| `%s` | $%s$ | %s | %s |" % (k, sym, un, mean))
    w("")
    w("単位ごとに意味が違うキーは各単位の節で記号を示す（`key`＝記号）。全キーの記号・単位・意味は JSON の `outputs`。")
    w("")
    w("式の中の $V_{\\mathrm{X}}$ は単位 X の値（`value`）、$a01_i$ などは行ごとの値（`by_item`）。式の実行形は JSON の `helpers_py`（共通の部分式）と各単位の `eval_py` で、記号と 1 対 1 に対応する。")
    w("")
    w("## 3. 役割の区分（合計に直接寄与する単位と、それ以外）")
    w("")
    w("指示の 4 区分（DIRECT／AUXILIARY／DECISION／BREAKDOWN）に、どれにも当たらない 2 区分（AGGREGATE：合計そのものと指標、REFERENCE：合計に入らない別の推計）を本台帳で加えた。副の役割（例：X-15 はスイッチでもある）は `role_secondary`。")
    w("")
    w("| 区分 | 意味 | 数 | 単位 |")
    w("|---|---|---|---|")
    for k in ["DIRECT", "AGGREGATE", "AUXILIARY", "REFERENCE", "DECISION", "BREAKDOWN"]:
        w("| %s | %s | %d | %s |" % (k, out["role_classes"][k], out["role_counts"].get(k, 0), "、".join(out["role_members"].get(k, []))))
    w("")
    w("判定の単位（SYS-01〜03 など）は、各単位の値が独立に掛けている述語（欠損・許諾・段階・換算）を**報告する**もので、その結果が別の単位の値に代入されることはない（台帳の式の依存に現れない：`data/unit_dependencies.csv` の kind=formula）。第 09 章の台帳の gated_by（前提の検査）はデータの流れではない。")
    w("")
    w("## 4. 直接寄与する 21 単位から $C(T)$ への再構成")
    w("")
    w("14 章 07 の 3 節の構成表 COMP（22 行）による：")
    w("")
    w("$$C(T)=\\sum_{s}\\iota_s\\sum_{u\\in\\mathcal{U}_C}\\sigma_{s,u}\\,\\beta_{s,u}\\,V_u(T)$$")
    w("")
    rows = {}
    for r in out["units"]:
        for c in r["composition"]:
            rows.setdefault(c["stage"], []).append((r["id"], c["sign"], c["beta"]))
    w("| 段階 | 構成（符号・β） |")
    w("|---|---|")
    for s in ["A1-A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "C1", "C2", "C3", "C4"]:
        w("| %s | %s |" % (s, " ".join(("%s%s%s" % ("+" if sg > 0 else "−", u, "·ι_B2" if b != "1" else "")) for u, sg, b in rows.get(s, []))))
    w("")
    w("直接寄与する単位の共通の検証の記録（各単位の節では繰り返さず「§4 の共通」と書く）：")
    w("")
    w("- [P] 核の和（L2）と節点形（L5）は $T\\in(0,H]$ で有理数として等しい（TH-0(i)。浮動小数の振幅・時刻を有理数とみなしたとき）。%s。" % _src(out, "T03", "TH-0"))
    w("- [E] 同じ恒等式を、区間の中点・区切り点とその隣・照合の評価期間で有理数として照合（単位ごとの節点形を含む）。%s。" % _src(out, "T03", "TH-0 の検証"))
    w("- [F] 合計に入る 21 単位の値 27,153 個が基準計算と相対 1e-9 で一致（1,293 組、縮めた定義域 $\\mathcal{D}'$）。%s。" % _src(out, "T07", "1."))
    w("- [S] 大規模ランダム検証：V1〜V5（V3 が合計に入る単位の値）のどれかが不一致となった定義域の内側のケースは 0（90,055 ケース・18,011 シナリオ）。照合した単位の値は全体で 2,127,153 個。シナリオあたりの失敗確率の 95%% 片側上限 1.7e-4（宣言した抽出分布についての上限で、全入力での一致の主張ではない）。%s。" % _src(out, "V20", "1. 全体"))
    w("- 未解決：年セルの終わり $K$ を越える事象の直後の帯 $T\\in(K,\\mathrm{sw}(\\tau))$（TH-2 の 3）は $\\mathcal{D}'$ の外で、そこでは統一系・正準形が基準計算と異なりうる（B1-04）。")
    w("")
    w("## 5. 単位ごとの台帳")
    w("")
    for title, us in CHAPTERS:
        w("### " + title)
        w("")
        for uid in us:
            r = U[uid]
            unit_section(w, out, r)
    # 6. 照合
    w("## 6. 台帳の式の照合（`tools/check_units70.py`）")
    w("")
    if summary is None:
        w("（照合の結果はまだ書かれていない。`python3 -B tools/check_units70.py --json <出力>` のあと `tools/extract_units70.py --check-summary <出力>` で書き込む。）")
    else:
        render_check(w, summary)
    w("")
    w("**本照合で直した台帳の誤り・不足**（単位ごとの全文は JSON の `units[].c2_check.fixes`）：定義の誤りの訂正＝X-02（CHK）・SYS-01（設備の耐用年数の適用条件）・B2-01（合計への正味の寄与 $\\iota_{\\mathrm{B2}}(1-\\iota_{\\mathrm{B6}})V$）；"
      "定義の補い＝SYS-01〜03（箇所・参照の全表を `sites`）・X-04（行の全表）・X-05・QA-03（使用）・B4-02（$n_{\\mathrm{partial}}$）・SUM-08（条件つきのキー）・A4-01・X-12・C3-01・C4-01（件数の範囲）・X-15（出力の文字列）；"
      "入力の不足＝X-12・X-05・SYS-01〜03；記号の衝突＝B4-02・X-08（1 回の更新の排出 $u_i\\to e^{\\mathrm{ren}}_i$）；依存の注記＝A13-01・X-03；書き出しの不具合（理由の文の欠け）＝X-03・X-09・X-10・X-11・X-12・B1-01・B3-02。"
      "全単位で `inputs_notation` を新設し、事象の格子などの索引の表の元の項目を `inputs_reached` に加えた。")
    w("")
    w("## 7. この台帳でできていないこと・限界")
    w("")
    w("- 照合はすべて浮動小数どうしの標本照合〔F〕（厳密な算術でも統計的な上限でもない）。架空データで、現実の建物の CO2 予測精度は意味しない。最小の表現かどうかは調べていない。$T$ について区分一次であることは、排出の実時間 $t$ への配分を一意に決めない（17 章 03 の TH-4(c)）。")
    w("- LaTeX の式は機械的には評価していない。照合したのは、式と 1 対 1 に書いた実行形 eval_py（基準計算と同じ計算順序）と、式を手で写した独立の評価 IND。SYS-01〜03 の箇所の表・X-04 の行・QA-03 の使用・B4-02 の n_partial・X-02 の CHK は本照合で統一系の仕様を読んで書き足した定義なので、それらの IND は仕様から完全には独立していない。")
    w("- 未解決の切り替え境界：整数の時刻 $K$ の交換の直後の帯 $T\\in(K,\\mathrm{sw}(K))$ では統一系（区間形）が台帳の式・基準計算と異なる（6 節 (e)）。整数の相対 1e-9 程度の近くの浮動小数の時刻の帯、$H\\ge256$、定義域の刃の帯は調べていない（統一系の成立範囲の外）。")
    w("- 入力の感度 (f) は値のある所を型に合わせて動かす摂動だけ（⊥ にする・型を変える・非有限にする摂動は無い）。変化を起こせなかった宣言の項目（`ledger_check_summary.sensitivity.declared_not_exercised`）は、値の有無・0 かどうかだけを見る項目などで、読まれないことを意味しない。")
    w("- 依存の記録は 3 つ（本台帳の式 kind=formula：受け渡しのキー `_parts`・`_row_lines` を含む、基準計算の宣言、第 09 章の台帳）で、A13-03・X-05・X-07 で異なる（JSON・CSV）。A13-01・X-03 の A13-02 は受け渡しのキーだけを読む。")
    if not inputs_csv_current:
        w("- `data/units70_inputs.csv` は JSON の `inputs_direct` と一致していない（`tools/extract_units70.py --write-inputs-csv` で作り直せる）。単位ごとの入力の正本は JSON の `inputs_direct`・`inputs_notation`。")
    w("")
    L = [_table_row(x) if x.startswith("|") else x for x in L]
    return "\n".join(L) + "\n"


# 条件の文がすべて式の述語に現れている単位（02 では条件の行を省き、JSON の conditions に残す）
COND_IN_FORMULA = {"X-01", "A4-02", "A5-02", "A5-03", "A5-04", "C1-01", "C4-01", "X-14", "B1-01", "B3-02", "B6-03", "B7-02", "B7-03",
                   "B7-04", "SUM-01", "SUM-02", "SUM-03", "SUM-06", "STO-01", "STO-02", "X-12", "A13-03", "QA-04", "SYS-04",
                   "X-13", "A4-01", "X-16", "C2-01", "C3-01", "B4-03", "B6-02", "B7-01", "SUM-04", "SUM-05", "SUM-07", "B2-01"}
REASON_KEEP_DIRECT = {"B2-01", "B1-04", "A13-04", "B5-01"}


def unit_section(w, out, r):
    uid = r["id"]
    w("#### %s %s" % (uid, r["name"]))
    w("")
    comp = "・".join("%s %+d%s" % (c["stage"], c["sign"], "·ι_B2" if c["beta"] != "1" else "") for c in r["composition"])
    role = r["role"] + ("／" + r["role_secondary"] if r["role_secondary"] else "")
    stg = r["stage"] + ("（09 章 %s）" % r["stage_09"] if r["stage_09"] != r["stage"] else "")
    st = r["unit_map"]["steps"]
    steps = "P1 %d/%d" % (st.get("P1:sp", 0), st.get("P1:match", 0))
    if st.get("TIME:sp"):
        steps += "・TIME %d" % st["TIME:sp"]
    if st.get("AGG:sp") or st.get("AGG:match"):
        steps += "・AGG %d/%d" % (st.get("AGG:sp", 0), st.get("AGG:match", 0))
    sps = r["unit_map"]["spectra"]
    spec = "、".join(sps) if len(sps) <= 3 else "スペクトル %d 本" % len(sps)
    outs = []
    for o in r["outputs"]:
        if (uid, o["key"]) in OVERRIDE and o["symbol"] != "—":
            outs.append("`%s`＝$%s$" % (o["key"], o["symbol"]))
        else:
            outs.append("`%s`" % o["key"])
    dset = [u["id"] for u in out["units"] if u["role"] == "DIRECT"]

    def _dl(lst):                                  # 直接寄与の 21 単位をすべて含む一覧は短く書く（全体は JSON・CSV）
        if lst and set(dset) <= set(lst):
            rest = [u for u in lst if u not in dset]
            return "直接寄与の 21 単位" + ("・" + "・".join(rest) if rest else "")
        return "・".join(lst) or "なし"
    dep = _dl(r["depends_on_units"])
    same = set(r["depends_on_units"]) == set(r["depends_on_refcalc"])
    depx = "" if same else ("（基準計算の宣言 ← %s）" % _dl(r["depends_on_refcalc"]))
    tind = r["time_form"].startswith("$T$ によらない")
    kconst = r["role"] == "DIRECT" and r["time_form"].startswith("定数の核")   # T によらない直接寄与の単位：時間の形は見出しに短く書く
    if kconst:
        tind = True
    w("**%s**%s｜%s｜%s｜%s%s%s｜出力 %s｜依存 ← %s%s" % (role, ("（%s）" % comp) if comp else "", stg, r["derivation"], r["route"],
                                              ("｜" + spec) if spec else "", ("｜T 非依存（定数の核、実時間 %s）" % ("$t=T$" if r["stage"].startswith("C") else "$t=0$")) if kconst else ("｜T 非依存" if tind else ""), "、".join(outs), dep, depx))
    w("")
    reason = r["role_reason"]                     # 文を途中で切らない（c2 の訂正：末尾を削る処理が文を壊していた）
    if r["role"] != "DIRECT" or uid in REASON_KEEP_DIRECT:
        w("- 理由：" + reason)
    _inputs(w, r)
    if uid not in COND_IN_FORMULA:
        w("- 条件：" + r["conditions"])
    w("")
    for blk in re.findall(r"\$\$.*?\$\$", r["formula_latex"]):
        w(blk)
        w("")
    if not tind:
        blockify(w, "- $T$：", r["time_form"])
    coef = r["coefficients"]
    cst = ("定数 " + "、".join(r["constants"])) if r["constants"] else ""
    if ("$" in coef or "`" in coef or len(coef) > 40) and r["role"] in ("DIRECT", "AUXILIARY", "AGGREGATE"):
        w("- 係数：" + coef + (("（%s）" % cst) if cst else ""))
    elif cst:
        w("- " + cst)
    vs, nneg = [], 0
    for v in r["verification"]:
        if v.get("common") or v.get("ledger"):
            continue
        if "counts" in v:
            c = v["counts"]
            if c.get("n_mismatch"):
                vs.append("[F] V11 %s/%s/%s" % ("{:,}".format(c["n_compared"]) if c["n_compared"] is not None else "—", c["n_mismatch"], _fmt_e(c["max_rel"])))
        elif v["claim"].startswith("誤り検出の確認"):
            nneg += 1
        elif v["claim"].startswith("T への依存の分類"):
            continue                                  # 17 章 06 の分類は JSON・CSV（time_classification_17）だけに置く
        else:
            vs.append("[%s] %s（%s）" % (v["class"], v.get("short", v["claim"]), v["source"]))
    if nneg:
        vs.append("[F] NEG %d" % nneg)
    lc = r.get("ledger_check")
    if lc:                                            # 照合の数は CSV（ver11_*・ledger_check_*・ind_*・knot_*・pred_*）。02 には不一致と帯の違いだけを書く
        if lc.get("n_mismatch") or lc.get("n_mismatch_ref"):
            vs.append("[F] L 不一致 %d（基準計算と %d）" % (lc["n_mismatch"], lc.get("n_mismatch_ref", 0)))
        if lc.get("n_mismatch_ind"):
            vs.append("[F] IND 不一致 %d" % lc["n_mismatch_ind"])
        if lc.get("knot_n_mismatch") or lc.get("knot_led_n_mismatch"):
            vs.append("[F] KN 不一致 %d" % (lc.get("knot_n_mismatch", 0) + lc.get("knot_led_n_mismatch", 0)))
        if lc.get("knot_band_n_mismatch"):
            vs.append("[F] 帯 $(K,\\mathrm{sw}(K))$ で統一系と %d 値が異なる（%s未解決の切り替え境界、6 節 (e)）" % (
                lc["knot_band_n_mismatch"], ("値の最大相対差 %s。" % _fmt_e(lc["knot_band_max_rel_value"])) if lc.get("knot_band_max_rel_value") else ""))
        if lc.get("pred_nonzero"):
            vs.append("[F] JMP %d/%d" % (lc["pred_nonzero"], lc.get("pred_bad", 0)))
    if r["role"] == "DIRECT":
        vs.append("§4")
    if vs:
        w("- 検証：" + "；".join(vs))
    if r["notes"]:
        w("- 注：" + r["notes"])
    w("")


def render_check(w, s):
    w("実行：`%s`（%s、%s 秒）。比較の規則は第 11 章と同じ（数値は相対 1e-9、基準が厳密に 0 なら 0、ほかは型を含めて完全一致）。比べるのは各単位の公開出力（`_` で始まる受け渡しのキーを除く）。全体は JSON の `ledger_check_summary`、単位ごとの数は CSV。" % (s["command"], s["when"], s.get("seconds", "?")))
    w("")
    w("(b)・(d) 組：" + "；".join("%s %d 組（除外 %d）" % (x["name"], x["pairs"], x["excluded"]) for x in s["sets"]) + "（R＝無作為、E＝境界条件、D＝欠陥入り、X＝特殊条件。種と件数は命令の通り）。L は台帳の式の実行形 eval_py、IND は 02 の式を手で写した独立の評価（`check_units70.py` の `run`・`run_all`）%s。" % ("、基準計算は L とだけ比べた" if s.get("with_reference") else ""))
    w("")
    w("区分ごとの比べた値（不一致 L・L と基準計算・IND、IND の最大相対差）：" + "、".join("%s %d 単位 %s（%d・%s・%s、%s）" % (
        g["role"], g["n_units"], "{:,}".format(g["n_values"]), g["n_mismatch"], g.get("n_mismatch_ref", "—"), g.get("n_mismatch_ind", "—"), _fmt_e(g.get("max_rel_ind")))
        for g in s["by_role"]) + "。")
    w("")
    tp = s.get("time_probe")
    kn = s.get("knots")
    if kn:
        def tot(nm, zone):
            return sum(z.get(zone, {}).get("n_values", 0) for z in kn[nm].values()), sum(z.get(zone, {}).get("n_mismatch", 0) for z in kn[nm].values())
        io_, im_ = tot("ind", "out")
        lo_, lm_ = tot("led", "out")
        ib_, ibm_ = tot("ind", "band")
        ro_, rm_ = tot("ref_ind", "out")
        rb_, rbm_ = tot("ref_ind", "band")
        j_, p_, c_ = kn["jump"], kn["pred"], kn["cont"]
        w("(e) 節点：シナリオ %d 件（無作為 %d 件・種 %d と境界条件）の事象の切り替え点 $\\mathrm{sw}(\\tau)$（$\\tau<\\mathrm{fl}(T\\,\\mathrm{fl}(1-\\varepsilon))$ となる最小の浮動小数）%d 個（整数の時刻 %d 個）と整数年 %d 個で、節点そのもの・直前・直後の浮動小数・$\\tau$・$\\tau$ と $\\mathrm{sw}(\\tau)$ の中点の %d 点（帯 $(K,\\mathrm{sw}(K))$ の中 %d 点）。跳びの理論値は 02 の時間の形から：B4-02 は事象の $e^{\\mathrm{ren}}$ の和、B5-01 は $\\varphi A^{\\mathrm{base}}$、B3-01 は $-a_\\rho w_k(\\mathrm{sw})$、B1-03 は $\\Gamma_e+\\Delta_e w_k(\\mathrm{sw})$、B1-04 は $\\kappa(m_0-u_K(1-[\\neg\\mathrm{tu}]r(\\mathrm{sw}-K)))$、SUM-03 はその段階の述語つきの和。"
          % (kn["n_scen"], kn.get("n_random", 0), kn.get("seed", 0), kn["n_knots_event"], kn["n_knots_integer_event"], kn["n_knots_lattice"], kn["n_probe"], kn["n_probe_band"]))
        w("")
        bu = kn["pred"].get("by_unit", {})
        if bu:
            w("跳びの理論値（節点／0 でない／不一致）：" + "、".join("%s %d／%d／%d" % (u, v["n"], v["nonzero"], v["bad"]) for u, v in sorted(bu.items())) + "。")
            w("")
        bd = kn["band"]
        if bd["units"]:
            w("**帯 $(K,\\mathrm{sw}(K))$ の違い（未解決の切り替え境界、17 章 03 の TH-2 の 3）**：整数の時刻 $K$ の交換の直後の帯では、統一系が台帳の式（IND・eval_py）%sと異なった："
              % ("・基準計算" if (ro_ or rb_) else "")
              + "、".join(("%s %d 点（値の最大相対差 %s）" % (u, n, _fmt_e(bd["max_rel"][u])) if u in bd["max_rel"] else "%s %d 点" % (u, n)) for u, n in sorted(bd["units"].items())) + "。"
              "原因は B1-04 の区間形と B1-02 の年セルの振幅が交換の初期化を $T>K$ で効かせ、台帳の式と基準計算は $T\\ge\\mathrm{sw}(K)$ で効かせること（17 章 01 の 3 節）。合計などの違いはこの 2 単位の伝播。"
              "%s17 章 07 の 6 節の記録（9 組中 2 組、B1-04 で最大 5.5e-3）より大きい違いがありうる。" % (("帯の中でも IND と基準計算は一致した（不一致 %d）。" % rbm_) if rb_ else ""))
            w("")
    se = s.get("sensitivity")
    if se:
        w("(f) 入力の感度：シナリオ %d 件（種 %d）で入力の項目 %d 個を値のある 1 か所ずつ型に合わせて動かし（%d 回、統一系が評価できなかったもの %d）、公開出力が変わった単位（%s 件）について、項目が宣言した入力（依存の閉包の `inputs_direct`・`inputs_notation`）と統一系の記録（`inputs_reached`）にあるかを調べた：宣言に無い %d 件、記録に無い %d 件。宣言したが摂動で変化を起こせなかった（単位、項目）%d 組（7 節）。"
          % (se.get("n_scenarios", 0), se.get("seed", 0), se["n_fields"], se["n_perturbations"], se["n_engine_errors"], "{:,}".format(se["n_unit_effects"]),
             len(se["missing_declared"]), len(se["missing_reached"]), sum(len(v) for v in se["declared_not_exercised"].values()))
          + (("無かった組：" + "；".join(sorted(set(list(se["missing_declared"]) + list(se["missing_reached"])))[:12]) + ("ほか" if len(set(list(se["missing_declared"]) + list(se["missing_reached"]))) > 12 else "") + "。")
             if (se["missing_declared"] or se["missing_reached"]) else ""))
        w("")
    co = s.get("consistency")
    if co:
        w("(g) 整合：" + "、".join("%s %s" % (k, ("はい" if v is True else v) if not isinstance(v, (dict, list)) else (len(v) if v else "なし")) for k, v in co.items()) + "。")
        w("")
    w("照合できなかった単位：" + ("、".join("%s（%s）" % (k, v) for k, v in s["not_checked"].items()) if s["not_checked"] else "なし（70 単位すべてを L と IND の両方で照合）") + "。")
    w("")
    w("**最終の照合の数と証拠の区分**（範囲：%s。架空データで、現実の建物の予測精度は意味しない）：" % s["scope"])
    w("")
    w("| 照合 | 対象 | 数 | 不一致 | 区分 |")
    w("|---|---|---|---|---|")
    w("| (a)(g) 構造と整合（単位・ID・依存・入力の名前・依存の辺・構成表・役割の閉包・CHK・出力キー） | 70 単位 | 依存の辺 %s | 問題 %d | 機械的な検査 |" % (s["structure"].get("依存の辺（解決できたもの／全体）", "?"), len(s.get("problems", []))))
    nv = sum(g["n_values"] for g in s["by_role"])
    w("| (b) L と統一系 | 70 単位 × %d 組 | %s 値 | %d | [F] |" % (s["n_pairs"], "{:,}".format(nv), sum(g["n_mismatch"] for g in s["by_role"])))
    if s.get("with_reference"):
        w("| (b) L と凍結した基準計算（同じ計算順序なので独立な検証ではない） | 同上 | 同上 | %d | [F] |" % sum(g.get("n_mismatch_ref", 0) for g in s["by_role"]))
    w("| (d) IND と統一系 | 70 単位 × %d 組 | %s 値 | %d | [F] |" % (s["n_pairs"], "{:,}".format(sum(g.get("n_values_ind", 0) for g in s["by_role"])), sum(g.get("n_mismatch_ind", 0) for g in s["by_role"])))
    if tp:
        w("| (c) 区間の内側の区分一次・一定 | 直接寄与の 21 単位と SUM-03・SUM-05 | %d | %d | [F] |" % (tp["n_affine_checks"] + tp["n_const_checks"] + tp["n_sum05_checks"],
                                                                                    tp["n_affine_fail"] + tp["n_const_fail"] + tp["n_sum05_fail"]))
    if kn:
        w("| (e) 節点と前後（帯の外）：IND と統一系／L と統一系 | 69 単位（SUM-08 を除く）、%d 点 | %s／%s 値 | %d／%d | [F] |" % (
            kn["n_probe"] - kn["n_probe_band"], "{:,}".format(io_), "{:,}".format(lo_), im_, lm_))
        if ro_ or rb_:
            w("| (e) 節点（帯の内外）：IND と凍結した基準計算 | 同上と帯の %d 点 | %s 値 | %d | [F] |" % (kn["n_probe_band"], "{:,}".format(ro_ + rb_), rm_ + rbm_))
        w("| (e) 跳び $V(b)-V(b^-)$：IND と統一系（帯の外） | 値を持つ 19 単位 | %d | %d（最大の差 %s） | [F] |" % (j_["n"] - j_["bad_band"], j_["bad"], _fmt_e(j_["worst"])))
        w("| (e) 跳びの理論値と統一系の跳び（帯の外） | B4-02・B5-01・B3-01・B1-03・B1-04・SUM-03 | %d | %d（最大の差 %s） | [F] |" % (p_["n"] - p_["bad_band"], p_["bad"], _fmt_e(p_["worst"])))
        w("| (e) 跳ばないはずの単位の連続性（帯の外） | B1-02・B2-01・B6-03・B7-04・X-11、格子の B3-01 | %d | %d | [F] |" % (c_["n"] - c_["bad_band"], c_["bad"]))
        w("| (e) 帯 $(K,\\mathrm{sw}(K))$ の中：IND と統一系 | 整数の時刻の交換の直後 %d 点 | %s 値 | %d（跳び %d・理論値 %d・連続性 %d）：未解決 | [F] |" % (
            kn["n_probe_band"], "{:,}".format(ib_), ibm_, j_["bad_band"], p_["bad_band"], c_["bad_band"]))
    if se:
        w("| (f) 入力の感度：宣言に無い／統一系の記録に無い | %d 項目、%d 回 | %s 件の変化 | %d／%d | [F] |" % (se["n_fields"], se["n_perturbations"], "{:,}".format(se["n_unit_effects"]),
                                                                                  len(se["missing_declared"]), len(se["missing_reached"])))
    w("")
    w("区分の根拠：どれも浮動小数の計算どうしの標本照合なので [F]（厳密な算術の照合 [E] でも、宣言した分布の統計的な上限 [S] でもない）。§4 の [P]・[E]・[S] は 17 章・20 章の原典の記録で、本照合で格上げしたものではない。")


# ======== extract_main.py ========
# ==== 抽出の本体（ここから下は機械的な抽出と書き出し。手書きの内容は上の FIELDS・DEFAULT・OVERRIDE・UCUR） ====
import argparse
import csv
import io
import json
import math
import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))


def find_study(arg):
    if arg:
        return os.path.abspath(arg)
    p = os.path.normpath(os.path.join(HERE, "..", ".."))           # tools/ -> WLC_THEORY_RESEARCH_BASE/ -> study
    if os.path.isdir(os.path.join(p, "10_TRANSFORM_STUDY")):
        return p
    raise SystemExit("whole-life-carbon-jcat-study が見つからない：--study で指定する")


ROLE_DEF = {
    "DIRECT": "ホールライフ合計 C(T) に直接寄与する（14 章 07 の構成表 COMP に行を持つ 21 単位。COMP は 22 行で、B2-01 が B2 と B6 に現れる）",
    "AGGREGATE": "合成・合計・指標（直接寄与する単位の値から作る。SUM-03 は C(T) そのもの）。本台帳で加えた区分",
    "AUXILIARY": "補助の量（直接寄与する単位の入力になる中間量：数量・係数・事象の格子・年次系列・部分和）",
    "REFERENCE": "参考値・代替推計（合計に入らない別の推計・物量・在庫の指標）。本台帳で加えた区分",
    "DECISION": "判定（ゲート・マスク・スイッチ・検査）。値を報告するだけで、合計への作用は各単位の述語が独立に持つ",
    "BREAKDOWN": "内訳（合計またはその一部を別の軸に分けたもの。和は元の量に等しく、合計に二重に入れない）",
}

EV_DEF = {
    "P": "数学的に証明済み", "E": "厳密な算術（有理数）で標本照合済み", "F": "浮動小数の計算で検証済み",
    "S": "統計的に検証済み", "L": "文献で支持される", "H": "未検証の新仮説",
}

SRC = {  # 台帳の中で使う出典の略号 -> (path（study からの相対）, 該当節)
    "U70": ("10_TRANSFORM_STUDY/11_UNIFIED_SYSTEM/UNITS_70.md", "表の全体（単位ごとの行）"),
    "UMAP": ("10_TRANSFORM_STUDY/11_UNIFIED_SYSTEM/results/unit_map.json", "単位ごとのキー（UNIT_MAP.md の元）"),
    "VER11": ("10_TRANSFORM_STUDY/11_UNIFIED_SYSTEM/VERIFICATION.md", "2. 単位ごとの結果（全集合の合計）"),
    "VERJ": ("10_TRANSFORM_STUDY/11_UNIFIED_SYSTEM/results/verification_dev_design.json", "units（10 集合の verification_*.json を合計）"),
    "DER": ("10_TRANSFORM_STUDY/11_UNIFIED_SYSTEM/DERIVATIONS.md", "D-01〜D-13"),
    "LIM": ("10_TRANSFORM_STUDY/11_UNIFIED_SYSTEM/LIMITS.md", "全体"),
    "SMSP": ("10_TRANSFORM_STUDY/11_UNIFIED_SYSTEM/SPEC_MSP.md", "3. 書き換えの型、5. テンプレート"),
    "SKN": ("10_TRANSFORM_STUDY/11_UNIFIED_SYSTEM/SPEC_KNOTS.md", "4. スペクトルの一覧、5. 成立条件"),
    "E07": ("14_EQUATION_DISCLOSURE/07_建物全体の統一方程式_完全版.md", "3. 段階の構成表（COMP、22 行）、4. 単位の値の出どころ"),
    "E05B": ("14_EQUATION_DISCLOSURE/05b_評価単位から統一式への変換対応表.csv", "単位ごとの行"),
    "T01": ("17_WHOLE_BUILDING_TIME_THEORY/01_理想方程式.md", "3. 完全理想方程式、7. C(T) の項ではない T 依存の出力の式"),
    "T02": ("17_WHOLE_BUILDING_TIME_THEORY/02_係数表.md", "2. 理想方程式の係数、2.1 振幅を作る入力の量"),
    "T03": ("17_WHOLE_BUILDING_TIME_THEORY/03_時間特性の定理と証明.md", "TH-0〜TH-14"),
    "T06": ("17_WHOLE_BUILDING_TIME_THEORY/06_70単位の時間特性.md", "表（単位ごとの行）"),
    "T06J": ("17_WHOLE_BUILDING_TIME_THEORY/results/units_time.json", "units"),
    "T07": ("17_WHOLE_BUILDING_TIME_THEORY/07_検証の結果.md", "1. 理想方程式と 70 単位モデルとの一致、6. 帯、7. 合計に入らない T 依存の出力"),
    "V20": ("20_LARGE_RANDOM_VERIFICATION/02_結果.md", "1. 全体（V3：合計に入る単位の値）"),
    "L09": ("09_APPROX_STUDY/01_LEDGER/units.json", "units（name・stage・structure_class・depends_on・gated_by）"),
    "REF": ("09_APPROX_STUDY/research_code/refcalc/registry.py", "UNITS（各単位の depends_on と定義文。units_pre_a.py・units_b.py・units_c_sum.py）"),
    "ENG": ("10_TRANSFORM_STUDY/research_code/tstudy/unified.py", "System.at（統一系の本体）"),
    "SPECS": ("10_TRANSFORM_STUDY/research_code/specs/system.py", "SPEC1・EMIT・COMP（仕様データ）"),
    "MODEL": ("09_APPROX_STUDY/research_code/synth/model.py", "入力のデータモデル（Scenario）"),
}

STAGE_UNITS = {  # 14 章 07 の 3 節（COMP）。(段階, 単位, 符号, β の注記)
}

D_TITLES = {
    "D-01": "活動量×係数の総和", "D-02": "係数の検索・換算・適用の優先順位", "D-03": "時間の核", "D-04": "更新",
    "D-05": "修繕", "D-06": "大規模改修・建替", "D-07": "運用", "D-08": "冷媒の漸化式から積和 8 段へ",
    "D-09": "冷媒の期末残存量（跳び形の桁落ちと区間形）", "D-10": "段階ベクトル・合計・指標・比較",
    "D-11": "排出の行による再集計", "D-12": "検査・品質", "D-13": "集計表と参考値",
}


def git_short(study, rel):
    try:
        out = subprocess.run(["git", "-C", study, "log", "-1", "--format=%h", "--", rel], capture_output=True, text=True, check=True).stdout.strip()
        return out or None
    except Exception:
        return None


def git_head(study):
    try:
        return subprocess.run(["git", "-C", study, "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return None


def ltx(s):
    """@A13-01 -> \\mathrm{A13\\text{-}01}"""
    if s is None:
        return s
    return re.sub(r"@([A-Z0-9]+)-([0-9]+)", lambda m: "\\mathrm{%s\\text{-}%s}" % (m.group(1), m.group(2)), s)


def parse_eval_source(path):
    src = open(path, encoding="utf-8").read()
    parts = re.split(r"^#@", src, flags=re.M)
    helpers, units, order = None, {}, []
    for p in parts:
        if not p.strip() or p.startswith("!"):
            continue
        head, _, body = p.partition("\n")
        if head.strip() == "helpers":
            helpers = body
        elif head.startswith("unit "):
            uid = head.split()[1]
            units[uid] = body.rstrip() + "\n"
            order.append(uid)
    return helpers, units, order


def parse_units70(path):
    rows = {}
    for line in open(path, encoding="utf-8"):
        if not line.startswith("| ") or line.startswith("| 単位") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 6:
            continue
        uid = cells[0]
        rows[uid] = {"ref_def_head": cells[1], "unified_text": cells[2], "derivation": cells[3], "route": cells[4],
                     "output_keys": [k.strip() for k in cells[5].split(",") if k.strip()]}
    return rows


def aggregate_verification(resdir):
    tot = {}
    sets = []
    for fn in sorted(os.listdir(resdir)):
        if not fn.startswith("verification_") or fn == "verification_quick.json":
            continue
        d = json.load(open(os.path.join(resdir, fn), encoding="utf-8"))
        sets.append((d["set"], d["n_pairs"], d["n_excluded"]))
        for u, v in d["units"].items():
            t = tot.setdefault(u, {"n_compared": 0, "n_mismatch": 0, "max_rel": 0.0, "n_bit_identical": 0, "n_float": 0})
            for k, kv in v["keys"].items():
                t["n_compared"] += kv["n_compared"]
                t["n_mismatch"] += kv["n_mismatch"]
                t["max_rel"] = max(t["max_rel"], kv["max_rel"] or 0.0)
                t["n_bit_identical"] += kv.get("n_bit_identical", 0)
                t["n_float"] += kv.get("n_float", 0)
    return tot, sets


def parse_negative_controls(path):
    """VERIFICATION.md の 5 節の表：壊した内容 -> 検出を期待した単位。"""
    out, on = {}, False
    for line in open(path, encoding="utf-8"):
        if line.startswith("## 5."):
            on = True
            continue
        if on and line.startswith("## "):
            break
        if on and line.startswith("| ") and not line.startswith("| 壊した") and not line.startswith("| 偽った"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 3 and cells[2] == "検出":
                for u in [x.strip() for x in cells[1].split(",")]:
                    out.setdefault(u, []).append(cells[0])
    return out


def time_summary(tu):
    cls = {}
    for leaf, d in tu.items():
        if leaf == "__list_length_varies__":
            cls["length_varies"] = cls.get("length_varies", 0) + sum(d.values())
            continue
        for c, n in d.items():
            cls[c] = cls.get(c, 0) + n
    return cls


TCLASS_JA = {"const": "一定", "step": "階段", "affine": "区分一次", "hyper": "双曲", "ratio": "比", "other": "その他",
             "shape": "期間で現れる", "length_varies": "長さが変わる列"}


def _canon(path):
    """入力の項目の名前の正規形（check_units70.py の canon と同じ）。"""
    p = path.replace(".__no_value__", "")
    p = re.sub(r"~[ht]$", "", p)
    p = p.replace("#", "")
    if p.endswith(".value") and not p.startswith("factors.value"):
        p = p[: -len(".value")]
    return p


def _clean_summary(sm):
    """JSON に埋める照合の要約から、例の長い文字列を除く（数と範囲は残す）。"""
    sm = json.loads(json.dumps(sm, ensure_ascii=False))
    kn = sm.get("knots")
    if kn:
        for nm in ("ind", "led", "ref_ind"):
            for z in kn.get(nm, {}).values():
                for zz in z.values():
                    zz.pop("examples", None)
    se = sm.get("sensitivity")
    if se:
        for k in ("missing_declared", "missing_reached"):
            se[k] = {kk: str(v)[:160] for kk, v in se.get(k, {}).items()}
    return sm


def summarize_check(summary):
    """check_units70.py --json の出力から、単位ごとの数（ledger_check に入れる）を作る。"""
    if not summary:
        return {}
    out = {}
    kn, se = summary.get("knots") or {}, summary.get("sensitivity") or {}
    for x in summary["units"]:
        d = dict(x)
        uid = x["id"]
        if kn:
            z = kn.get("ind", {}).get(uid, {})
            if z:
                d["knot_n_values"] = z.get("out", {}).get("n_values", 0)
                d["knot_n_mismatch"] = z.get("out", {}).get("n_mismatch", 0)
                d["knot_max_rel"] = z.get("out", {}).get("max_rel", 0.0)
                d["knot_band_n_values"] = z.get("band", {}).get("n_values", 0)
                d["knot_band_n_mismatch"] = z.get("band", {}).get("n_mismatch", 0)
                if uid in kn.get("band", {}).get("max_rel", {}):
                    d["knot_band_max_rel_value"] = kn["band"]["max_rel"][uid]
            zl = kn.get("led", {}).get(uid, {})
            if zl:
                d["knot_led_n_mismatch"] = zl.get("out", {}).get("n_mismatch", 0)
            zr = kn.get("ref_ind", {}).get(uid, {})
            if zr:
                d["knot_ref_n_mismatch"] = zr.get("out", {}).get("n_mismatch", 0) + zr.get("band", {}).get("n_mismatch", 0)
            pu = kn.get("pred", {}).get("by_unit", {}).get(uid)
            if pu:
                d["pred_n"], d["pred_bad"], d["pred_nonzero"] = pu["n"], pu["bad"], pu["nonzero"]
        if se:
            d["sens_missing_declared"] = sorted(k.split(" <- ")[1] for k in se.get("missing_declared", {}) if k.split(" <- ")[0] == uid)
            d["sens_missing_reached"] = sorted(k.split(" <- ")[1] for k in se.get("missing_reached", {}) if k.split(" <- ")[0] == uid)
        for k in ("examples", "examples_ind", "examples_ref"):
            d.pop(k, None)
        out[uid] = d
    return out


def c2_confirmation(uid, c, lc, summary, notation, reached, m):
    """独立の照合（check_units70.py の (a)〜(g)）で、この単位の各項目が確かめられたか。数は照合の要約から。"""
    fixes = list(C2_FIXES.get(uid, []))
    if any(tb in INDEX_SOURCES for tb in m.get("index_tables", {})):
        fixes.append("inputs_reached に索引の表（事象の格子など）の元の項目を加えた")
    if not summary or not lc:
        return {"fixes": fixes, "confirmed": None}
    co = summary.get("consistency") or {}
    keyd = co.get("出力キーの集合（台帳と、比べた全組の統一系の公開出力の和集合）が違う単位", {}) or {}
    extra = co.get("独立の評価が読んだが台帳の依存の閉包に無い単位", {}) or {}
    conf = {
        "id": "統一系の出力に同じ ID がある（(b) で比べた）",
        "role": "構成表の行・依存の閉包と矛盾しない（(g)）" if not (co.get("AUXILIARY のうち直接寄与する単位の入力にならないもの") or co.get("REFERENCE・BREAKDOWN・DECISION のうち C(T) の依存の閉包に入るもの")) else "要確認",
        "outputs": "キーの集合が統一系と一致（(g)）" if uid not in keyd else ("条件つきのキー：%s" % keyd[uid]),
        "formula_conditions": "IND 不一致 %d／%d 値、節点（帯の外）不一致 %s" % (lc.get("n_mismatch_ind", -1), lc.get("n_values_ind", 0), lc.get("knot_n_mismatch", "—")),
        "inputs": ("入力の感度で宣言に無い項目 %d・統一系の記録に無い項目 %d" % (len(lc.get("sens_missing_declared", [])), len(lc.get("sens_missing_reached", []))))
                  if "sens_missing_declared" in lc else "入力の感度は未実行",
        "dependencies": "式が読む単位は宣言に含まれ循環なし（(a)）、独立の評価の読む単位は依存の閉包の中" + ("" if uid not in extra else "（例外 %s）" % extra[uid]),
    }
    return {"fixes": fixes, "confirmed": conf}


def eval_deps(body, ids):
    found = set(re.findall(r'"([A-Z0-9]+-[0-9]+)"', body))
    return sorted(found & set(ids))


def main():
    ap = argparse.ArgumentParser(description="70 評価単位の台帳（data/units70.json・csv、unit_dependencies.csv、02 の本文）を原典から作る")
    ap.add_argument("--study", default=None, help="whole-life-carbon-jcat-study のパス（既定：このファイルの位置から）")
    ap.add_argument("--base", default=None, help="WLC_THEORY_RESEARCH_BASE のパス（既定：study の下）")
    ap.add_argument("--eval-src", default=None, help="台帳の式の実行形（既定：base/tools/units70_eval_src.py）")
    ap.add_argument("--check-summary", default=None, help="check_units70.py --json の出力（02 の末尾に書く）")
    ap.add_argument("--no-md", action="store_true")
    ap.add_argument("--write-inputs-csv", action="store_true", help="data/units70_inputs.csv を書き換える（既定では変わるときも書き換えない）")
    ap.add_argument("--inputs-csv-out", default=None, help="書き換えないときに新しい units70_inputs.csv を置く場所")
    ap.add_argument("--split-md", default=None, help="02 を 2 つに分ける：5.8 節から後をこの名前のファイル（base からの相対）に書く（既定では分けない）")
    a = ap.parse_args()
    study = find_study(a.study)
    base = a.base or os.path.join(study, "WLC_THEORY_RESEARCH_BASE")
    evsrc = a.eval_src or os.path.join(base, "tools", "units70_eval_src.py")
    rc = os.path.join(study, "10_TRANSFORM_STUDY", "research_code")
    head = git_head(study)
    commits = {k: git_short(study, v[0]) for k, v in SRC.items()}
    commits["VERJ"] = git_short(study, "10_TRANSFORM_STUDY/11_UNIFIED_SYSTEM/results")
    commits["T06J"] = git_short(study, SRC["T06J"][0])

    helpers, evb, evorder = parse_eval_source(evsrc)
    l09 = json.load(open(os.path.join(study, SRC["L09"][0]), encoding="utf-8"))
    l09u = {u["id"]: u for u in l09["units"]}
    umap = json.load(open(os.path.join(study, SRC["UMAP"][0]), encoding="utf-8"))
    u70 = parse_units70(os.path.join(study, SRC["U70"][0]))
    ver, vsets = aggregate_verification(os.path.join(study, "10_TRANSFORM_STUDY", "11_UNIFIED_SYSTEM", "results"))
    ut = json.load(open(os.path.join(study, SRC["T06J"][0]), encoding="utf-8"))["units"]
    negc = parse_negative_controls(os.path.join(study, SRC["VER11"][0]))
    # 基準計算の登録（読み取り専用。依存の宣言と定義文）
    sys.path.insert(0, rc)
    cwd = os.getcwd()
    os.chdir(rc)
    from tstudy import baseline
    reg = baseline.load()
    os.chdir(cwd)

    summary = json.load(open(a.check_summary, encoding="utf-8")) if a.check_summary and os.path.exists(a.check_summary) else None
    if summary is not None:                                    # 作業場所のパスを資料に残さない
        summary["command"] = re.sub(r"\s--(ledger|deps)\s+\S+", "", summary["command"])
    old_json = os.path.join(base, "data", "units70.json")
    if summary is None and os.path.exists(old_json):           # 照合の結果を指定しなければ、前回の units70.json に埋めた結果を引き継ぐ
        prev = json.load(open(old_json, encoding="utf-8"))
        if prev.get("ledger_check_summary"):
            summary = dict(prev["ledger_check_summary"])
            summary["units"] = [dict(u["ledger_check"], id=u["id"], role=u["role"]) for u in prev["units"] if u.get("ledger_check")]
            print("check summary carried over from the previous data/units70.json")
    lchk = summarize_check(summary)
    ids = [u["id"] for u in l09["units"]]
    assert len(ids) == 70 and set(ids) == set(evb) == set(UCUR) == set(umap) == set(u70), "70 単位の集合が原典の間で一致しない"

    records, edges = [], []
    for uid in ids:
        c, L, m, t = UCUR[uid], l09u[uid], umap[uid], u70[uid]
        deps = eval_deps(evb[uid], ids)
        deps = [d for d in deps if d != uid]
        refdeps = list(reg.UNITS[uid].depends_on)
        # 入力：直接（手書き）と、到達する全項目（unit_map.json の inputs と tokens）
        reached = []
        for tb, cols in sorted(m["inputs"].items()):
            for col in cols:
                reached.append(tb + "." + col)
        for tb, cols in sorted(m.get("tokens", {}).items()):
            for col in cols:
                reached.append(tb + "." + col)
        for tb in sorted(m.get("index_tables", {})):            # 索引の表の元の項目（c2 の訂正。unit_map の inputs に無い）
            for p in INDEX_SOURCES.get(tb, []):
                if p not in reached:
                    reached.append(p)
        dcanon = {_canon(p) for p in c["inputs"]}
        notation = sorted({_canon(p) for p in reached if any(re.search(pt, _canon(p)) for pt, _ in NOTATION_PATTERNS)} - dcanon)
        direct = []
        for p in c["inputs"]:
            fi = FIELDS.get(p)
            if fi is None:
                raise KeyError("no FIELDS entry: %s (%s)" % (p, uid))
            direct.append({"path": p, "symbol": fi[0], "unit": fi[1], "domain": fi[2], "meaning": fi[3]})
        outs = []
        for k in t["output_keys"]:
            o = OVERRIDE.get((uid, k)) or DEFAULT.get(k) or ("—", "—", "")
            outs.append({"key": k, "symbol": o[0], "unit": o[1], "meaning": o[2]})
        vv = ver.get(uid, {})
        tsum = time_summary(ut.get(uid, {}))
        dnum = t["derivation"].strip()
        verif = []
        verif.append({"class": "F", "claim": "統一系（2 構造）の全出力キーが凍結した基準計算と一致（数値は相対 1e-9、基準が 0 なら 0、他は型を含めて完全一致）",
                      "counts": {"n_compared": vv.get("n_compared"), "n_mismatch": vv.get("n_mismatch"), "max_rel": vv.get("max_rel"),
                                 "bit_identical_share": (vv["n_bit_identical"] / vv["n_float"]) if vv.get("n_float") else None},
                      "scope": "架空データの 10 集合・1,293 組（定義域の刃の 2 組を除外）。浮動小数どうしの一致で、厳密な等号ではない。現実の建物の予測精度ではない",
                      "source": "VER11", "section": "2. 単位ごとの結果（全集合の合計）", "code": "10_TRANSFORM_STUDY/research_code/checks/check_unified.py"})
        if c["role"] == "DIRECT":
            verif.append({"common": True, "class": "P", "claim": "核の和（L2）と節点形（L5）は T∈(0,H] のすべてで有理数として等しい（TH-0(i)）。単位ごとの項についても同じ",
                          "scope": "浮動小数で与えた振幅・時刻を有理数とみなしたとき", "source": "T03", "section": "TH-0"})
            verif.append({"common": True, "class": "E", "claim": "TH-0(i) の恒等式を区間の中点・区切り点とその隣・照合の評価期間で有理数として照合（単位ごとの節点形を含む）",
                          "scope": "保存した 10 集合のシナリオ", "source": "T03", "section": "TH-0 の検証"})
            verif.append({"common": True, "class": "F", "claim": "合計に入る 21 単位の値（27,153 個）が基準計算と相対 1e-9 で一致（正準形・有理数の評価 vs 浮動小数の基準計算）",
                          "scope": "1,293 組、縮めた定義域 D'（年セルの終わりを越える事象の直後の帯を除く）", "source": "T07", "section": "1. 理想方程式と 70 単位モデル（基準計算）との一致"})
            verif.append({"common": True, "class": "S", "claim": "大規模ランダム検証：V1〜V5（V3 が合計に入る単位の値）のどれかが不一致となった定義域の内側のケースは 0。照合した単位の値は全体で 2,127,153 個。シナリオあたりの失敗確率の 95% 片側上限 1.7e-4",
                          "scope": "宣言した抽出分布（層 N・B・G・E・S）の定義域の内側 90,055 ケース・18,011 シナリオ。分布についての統計的な上限で、全入力での一致の主張ではない",
                          "source": "V20", "section": "1. 全体"})
        if tsum:
            verif.append({"class": "F", "claim": "T への依存の分類（出力の葉ごと）：" + "、".join("%s %d" % (TCLASS_JA.get(k, k), v) for k, v in sorted(tsum.items())),
                          "scope": "54 シナリオ×幅 1e-6 年を超える無作為の 30 区間×3 点、相対 1e-8（幅 1e-6 年以下の区間は標本にない）", "source": "T06", "section": "表（単位ごとの行）"})
        for nc in negc.get(uid, []):
            verif.append({"class": "F", "claim": "誤り検出の確認：仕様を 1 か所壊すと比較が不一致を報告した（" + nc + "）",
                          "scope": "第 11 章の誤り検出 24 件（24 件で検出）", "source": "VER11", "section": "5. 誤り検出の確認"})
        for e in EXTRA_VERIF.get(uid, []):
            verif.append(e)
        lc = None
        if uid in lchk:
            x = lchk[uid]
            lc = {k: x[k] for k in ("pairs", "n_values", "n_mismatch", "max_rel", "bit_identical", "n_mismatch_ref", "max_rel_ref", "bit_identical_ref",
                                    "n_values_ind", "n_mismatch_ind", "max_rel_ind", "knot_n_values", "knot_n_mismatch", "knot_max_rel",
                                    "knot_band_n_values", "knot_band_n_mismatch", "knot_band_max_rel_value", "knot_led_n_mismatch",
                                    "knot_ref_n_mismatch", "pred_n", "pred_bad", "pred_nonzero", "sens_missing_declared", "sens_missing_reached") if k in x}
            kn = (summary or {}).get("knots") or {}
            if "n_values_ind" in x:
                verif.append({"ledger": True, "kind": "independent", "class": "F",
                              "claim": "独立の評価（02 の式・条件・記号を eval_py・基準計算を見ずに手で写した別の実装）の公開出力が統一系と一致：比べた値 %d、不一致 %d、最大相対差 %.1e" % (
                                  x["n_values_ind"], x["n_mismatch_ind"], x["max_rel_ind"]),
                              "scope": summary["scope"], "source": "本台帳", "code": "tools/check_units70.py（run・run_all）", "command": summary["command"]})
            if "knot_n_values" in x:
                verif.append({"ledger": True, "kind": "knots", "class": "F",
                              "claim": "節点（事象の切り替え点 sw(τ)・整数年）そのものと直前・直後の浮動小数・τ・τ と sw(τ) の中点で、独立の評価が統一系と一致：比べた値 %d、不一致 %d（帯の外）。"
                                       "帯 (K, sw(K))（整数の時刻の事象の直後）では比べた値 %d、不一致 %d%s。eval_py と統一系の不一致（帯の外）%d%s" % (
                                  x["knot_n_values"], x["knot_n_mismatch"], x.get("knot_band_n_values", 0), x.get("knot_band_n_mismatch", 0),
                                  ("（値の最大相対差 %.1e）" % x["knot_band_max_rel_value"]) if x.get("knot_band_max_rel_value") else "",
                                  x.get("knot_led_n_mismatch", 0),
                                  ("。独立の評価と基準計算の不一致（帯の内外とも）%d" % x["knot_ref_n_mismatch"]) if "knot_ref_n_mismatch" in x else ""),
                              "scope": "無作為のシナリオ %s 件と境界条件の一部、節点 %s 個（事象 %s・格子 %s）。浮動小数の規則の上での照合" % (
                                  kn.get("n_random"), kn.get("n_knots_event", 0) + kn.get("n_knots_lattice", 0), kn.get("n_knots_event"), kn.get("n_knots_lattice")),
                              "source": "本台帳", "code": "tools/check_units70.py（knot_check）", "command": summary["command"]})
            if x.get("pred_n"):
                verif.append({"ledger": True, "kind": "jumps", "class": "F",
                              "claim": "時間の形から求めた跳びの理論値が統一系の跳び V(sw)−V(sw の直前) と一致：事象の節点 %d（理論値が 0 でないもの %d）、不一致 %d（帯の外）" % (
                                  x["pred_n"], x.get("pred_nonzero", 0), x.get("pred_bad", 0)),
                              "scope": "同上", "source": "本台帳", "code": "tools/check_units70.py（predicted_jumps）"})
            verif.append({"ledger": True, "class": "F", "claim": "台帳の式（eval_py）の公開出力が統一系（System.at）と一致：比べた値 %d、不一致 %d、最大相対差 %.1e%s" % (
                x["n_values"], x["n_mismatch"], x["max_rel"], ("。凍結した基準計算とは不一致 %d、最大相対差 %.1e（台帳の実行形は基準計算と同じ計算順序なので独立な検証ではない）" % (x["n_mismatch_ref"], x["max_rel_ref"])) if "n_mismatch_ref" in x else ""),
                "scope": summary["scope"], "source": "本台帳", "code": "tools/check_units70.py", "command": summary["command"]})
        CODE = {"T06": "17_WHOLE_BUILDING_TIME_THEORY/code/units_time.py", "T07": "17_WHOLE_BUILDING_TIME_THEORY/code/verify_canon.py（1 節）・units_eq.py（7 節）・sliver_test.py（6 節）・density_check.py（1.2 節）",
                "V20": "20_LARGE_RANDOM_VERIFICATION/code/run4.py・agg4.py", "T03": "17_WHOLE_BUILDING_TIME_THEORY/code/timechar.py・timechar_terms.py",
                "VER11": "10_TRANSFORM_STUDY/research_code/checks/check_unified.py・check_unified_controls.py",
                "DER": "10_TRANSFORM_STUDY/research_code/experiments/expU1_b14_forms.py・expU2_cross_engines.py・expU3_intermediate_state.py"}
        for v in verif:
            k = v.get("source")
            if k in SRC:
                v.setdefault("source_path", "whole-life-carbon-jcat-study/" + SRC[k][0])
                v.setdefault("source_commit", commits.get(k))
                v.setdefault("code", CODE.get(k))
        fn = reg.UNITS[uid].fn
        rec = {
            "id": uid, "name": L["name"], "name_source": "L09",
            "reference_function": "%s.%s" % (fn.__module__, fn.__name__),
            "engine": {"code": "10_TRANSFORM_STUDY/research_code/tstudy/unified.py（System.at の読み出し）、specs/*.py（仕様データ）",
                       "result_columns": m.get("read_from", [])},
            "stage": c["stage"], "stage_09": L["stage"],
            "composition": [{"stage": s, "sign": sg, "beta": ("iota_B2" if (uid == "B2-01" and s == "B6") else "1")} for s, sg in c["comp"]],
            "role": c["role"], "role_secondary": c["role2"], "role_reason": c["why"],
            "structure_class_09": L["structure_class"], "origin_09": L["origin"], "output_09": L["output"],
            "reference_definition": reg.UNITS[uid].doc, "reference_definition_source": "REF",
            "unified_text_U70": t["unified_text"], "derivation": dnum, "derivation_title": D_TITLES.get(dnum, ""),
            "route": t["route"], "time_dependent": ("K" in t["route"] or "②" in t["route"]),
            "inputs_direct": direct, "inputs_notation": notation, "inputs_reached": reached,
            "outputs": outs, "conditions": ltx(c["cond"]),
            "formula_latex": ltx(c["msp"]), "time_form": ltx(c["time"]),
            "coefficients": ltx(c["coef"]), "constants": c["consts"], "notes": ltx(c["notes"]),
            "depends_on_units": deps, "depends_on_refcalc": refdeps,
            "depends_on_09": L.get("depends_on", []), "gated_by_09": L.get("gated_by", []),
            "unit_map": {"steps": m.get("steps", {}), "spectra": m.get("spectra", []), "read_from": m.get("read_from", []),
                         "index_tables": m.get("index_tables", {})},
            "time_classification_17": tsum,
            "verification": verif,
            "ledger_check": lc,
            "eval_py": evb[uid],
            "c2_check": c2_confirmation(uid, c, lchk.get(uid), summary, notation, reached, m),
        }
        records.append(rec)
        for d in deps:
            edges.append((d, uid, "formula", "台帳の式（eval_py）が提供元の出力を読む", "tools/units70_eval_src.py"))
        for d in refdeps:
            edges.append((d, uid, "refcalc_declared", "凍結した基準計算の depends_on", "REF"))
        for d in L.get("depends_on", []):
            edges.append((d, uid, "ledger09_depends_on", "第 09 章の台帳の depends_on（定義上の受け渡し）", "L09"))
        for d in L.get("gated_by", []):
            edges.append((d, uid, "ledger09_gated_by", "第 09 章の台帳の gated_by（前提の検査。データの流れではない）", "L09"))
        for s, sg in c["comp"]:
            edges.append((uid, "X-02", "composition", "stage=%s;sign=%+d;beta=%s" % (s, sg, "iota_B2" if (uid == "B2-01" and s == "B6") else "1"), "E07"))
        for p in c["inputs"]:
            edges.append(("input:" + p, uid, "input_direct", "", "本台帳"))
        for p in reached:
            edges.append(("input:" + p, uid, "input_reached", "", "UMAP"))

    roles = {}
    for r in records:
        roles.setdefault(r["role"], []).append(r["id"])
    out = {
        "schema": "wlc-theory-research-base/units70/1",
        "generated_by": "tools/extract_units70.py",
        "worktree_head": head,
        "scope": "独立概念モデルの 70 評価単位（架空データ）。J-CAT 原版の式・係数・セル・値は含まない。現実の建物の CO2 予測精度についての主張はしない。",
        "evidence_classes": EV_DEF,
        "role_classes": ROLE_DEF,
        "role_counts": {k: len(v) for k, v in roles.items()},
        "role_members": roles,
        "sources": {k: {"path": "whole-life-carbon-jcat-study/" + v[0], "section": v[1], "commit": commits.get(k)} for k, v in SRC.items()},
        "verification_sets_11": [{"set": s, "pairs": n, "excluded": e} for s, n, e in vsets],
        "notation": NOTATION,
        "notation_patterns": NOTATION_PATTERNS,
        "index_sources": INDEX_SOURCES,
        "x02_chk": X02_CHK,
        "sites": SITES,
        "ledger_check_summary": (_clean_summary({k: summary[k] for k in summary if k != "units"}) if summary else None),
        "helpers_py": helpers,
        "eval_order_hint": evorder,
        "units": records,
    }
    os.makedirs(os.path.join(base, "data"), exist_ok=True)
    with open(os.path.join(base, "data", "units70.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    cols = ["id", "name", "stage", "stage_09", "composition", "role", "role_secondary", "role_reason", "structure_class_09", "derivation",
            "route", "time_dependent", "inputs_direct", "n_inputs_reached", "outputs", "depends_on_units", "depends_on_refcalc",
            "spectra", "steps_P1_sp", "steps_P1_match", "steps_TIME_sp", "steps_AGG_sp", "steps_AGG_match", "time_classification_17",
            "ver11_n_compared", "ver11_n_mismatch", "ver11_max_rel", "ledger_check_n_values", "ledger_check_n_mismatch",
            "ledger_check_max_rel", "ledger_check_n_mismatch_ref", "ledger_check_max_rel_ref", "ind_n_values", "ind_n_mismatch", "ind_max_rel",
            "knot_n_values", "knot_n_mismatch", "knot_band_n_mismatch", "pred_n", "pred_bad", "n_inputs_notation", "formula_latex", "time_form"]
    with open(os.path.join(base, "data", "units70.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in records:
            st = r["unit_map"]["steps"]
            v0 = r["verification"][0]["counts"]
            w.writerow([r["id"], r["name"], r["stage"], r["stage_09"],
                        ";".join("%s:%+d" % (x["stage"], x["sign"]) for x in r["composition"]),
                        r["role"], r["role_secondary"] or "", r["role_reason"], r["structure_class_09"], r["derivation"], r["route"],
                        r["time_dependent"], ";".join(x["path"] for x in r["inputs_direct"]), len(r["inputs_reached"]),
                        ";".join(x["key"] for x in r["outputs"]), ";".join(r["depends_on_units"]), ";".join(r["depends_on_refcalc"]),
                        ";".join(r["unit_map"]["spectra"]), st.get("P1:sp", 0), st.get("P1:match", 0), st.get("TIME:sp", 0),
                        st.get("AGG:sp", 0), st.get("AGG:match", 0),
                        ";".join("%s=%d" % (k, v) for k, v in sorted(r["time_classification_17"].items())),
                        v0["n_compared"], v0["n_mismatch"], v0["max_rel"],
                        *([r["ledger_check"].get(k, "") for k in ("n_values", "n_mismatch", "max_rel", "n_mismatch_ref", "max_rel_ref")] if r["ledger_check"] else [""] * 5),
                        *([r["ledger_check"].get(k, "") for k in ("n_values_ind", "n_mismatch_ind", "max_rel_ind", "knot_n_values", "knot_n_mismatch",
                                                                  "knot_band_n_mismatch", "pred_n", "pred_bad")] if r["ledger_check"] else [""] * 8),
                        len(r["inputs_notation"]),
                        r["formula_latex"], r["time_form"]])
    with open(os.path.join(base, "data", "unit_dependencies.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["from", "to", "kind", "detail", "source"])
        for e in edges:
            w.writerow(e)
    used = {}
    for r in records:
        for x in r["inputs_direct"]:
            used.setdefault(x["path"], (x, []))[1].append(r["id"])
    buf = io.StringIO(newline="")
    w = csv.writer(buf)
    w.writerow(["path", "symbol_latex", "unit", "domain", "meaning", "used_directly_by"])
    for pth in sorted(used):
        x, us = used[pth]
        w.writerow([pth, x["symbol"], x["unit"], x["domain"], x["meaning"], ";".join(us)])
    ipath = os.path.join(base, "data", "units70_inputs.csv")
    old = open(ipath, encoding="utf-8", newline="").read() if os.path.exists(ipath) else None
    inputs_csv_current = old == buf.getvalue()
    if inputs_csv_current:
        pass
    elif a.write_inputs_csv:
        open(ipath, "w", encoding="utf-8", newline="").write(buf.getvalue())
        inputs_csv_current = True
        print("data/units70_inputs.csv written")
    else:                                          # この表は別の担当の成果物：既定では書き換えず、新しい版を別の場所に置く
        alt = a.inputs_csv_out or os.path.join(base, "data", "units70_inputs.csv.new")
        open(alt, "w", encoding="utf-8", newline="").write(buf.getvalue())
        print("WARNING: data/units70_inputs.csv differs from the ledger; new version written to", alt, "(use --write-inputs-csv to replace)")
    print("units", len(records), "edges", len(edges), "roles", out["role_counts"])
    if not a.no_md:
        md = render_md(out, summary, commits, inputs_csv_current)
        p = os.path.join(base, "02_70評価単位の完全台帳.md")
        if a.split_md:                                  # 約 80 KB を超えるとき、5.8 節から後を別のファイルに分ける
            cut = md.index("### 5.8 ")
            name = os.path.basename(a.split_md)
            part2 = ("# 02（続き） 70 評価単位の完全台帳：5.8〜5.11 節、照合、限界\n\n"
                     "02_70評価単位の完全台帳.md の続き（記号・読み方・役割の区分は 02 の 1〜4 節）。\n\n") + md[cut:]
            md = md[:cut] + "### 5.8〜5.11 節、6 節（照合）、7 節（限界）\n\n続きは `%s`。\n" % name
            open(os.path.join(base, a.split_md), "w", encoding="utf-8").write(part2)
            print("02 part 2 bytes", len(part2.encode("utf-8")))
        open(p, "w", encoding="utf-8").write(md)
        print("02 bytes", len(md.encode("utf-8")))


if __name__ == "__main__":
    main()
