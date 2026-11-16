"""Catalogue of the input fields of the four screens and how each reaches the existing engine.

Every field belongs to one screen (基本情報 / 材料 / 設備 / 運用), to one of the five internal
categories of 13_INPUT_CLASSIFICATION (building / construction / equipment / operation / assessment)
and lists the engine input ids (lca-binding/1 ids, i.e. engine model names) it feeds. A field with
no engine id is kept as a record only and is reported as 「計算に反映されない」 with the reason.

Field keys
  label, screen, group, category      display and classification
  type        number | integer | text | enum
  unit        unit of the value as entered (numbers)
  units       other units the bridge accepts for this field (e.g. a quantity read from a document in t)
  enum        [(value, label)] for type enum
  engine      engine ids reached (binding ids); empty = record only
  role        how the bridge uses the field (see bridge.py)
  required    the engine cannot run without it (schema.REQUIRED or a stage that needs it)
  na          meaning of 「適用外」: "zero" = the quantity really is nil (passed as EXPLICIT_ZERO),
              "absent" = the row/table does not exist, "skip" = not passed at all
  na_never    「適用外」 is never possible (there is always such a value): refused on save
  na_context  「適用外」 is possible only where the value cannot act (e.g. the grid factor with no purchased electricity):
              refused on save, with the reason, when the calculation needs the value with the other inputs as they are
  estimable   an estimator exists (estimate.py) that can propose candidates
  range       (lo, hi) admissible numeric range, checked on save
  private     personal / location data: never exported, never sent to an outside service
  help        one line of guidance
Nothing here is a coefficient: the catalogue carries no default values.
"""
from __future__ import annotations

STAGES_ALL = ("A1-A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "C1", "C2", "C3", "C4")

USES = [("office", "事務所"), ("residential", "住宅（共同住宅）"), ("school", "学校"), ("hospital", "病院"),
        ("retail", "店舗・商業"), ("warehouse", "倉庫")]
STRUCTURES = [
    {"id": "S", "label": "S造（鉄骨造）", "desc": "柱と梁が鉄骨。床はコンクリートスラブが多い。", "img": "assets/structure-s.svg"},
    {"id": "RC", "label": "RC造（鉄筋コンクリート造）", "desc": "柱・梁・壁・床が鉄筋コンクリート。", "img": "assets/structure-rc.svg"},
    {"id": "SRC", "label": "SRC造（鉄骨鉄筋コンクリート造）", "desc": "鉄骨のまわりを鉄筋コンクリートで包む。高層に多い。", "img": "assets/structure-src.svg"},
    {"id": "W", "label": "木造", "desc": "柱・梁が木。基礎はコンクリート。", "img": "assets/structure-w.svg"},
]
STAGE_PRESETS = [
    ("ALL", "全段階（A1-A3〜C4）", STAGES_ALL),
    ("EMBODIED", "建設時まで（A1-A3・A4・A5）", ("A1-A3", "A4", "A5")),
    # B2 in this engine is the facility-management share of purchased electricity, so it goes with B6
    ("NO_OPERATION", "運用のエネルギー・水と施設管理の電力を除く（B2・B6・B7 なし）",
     tuple(s for s in STAGES_ALL if s not in ("B2", "B6", "B7"))),
    ("UPFRONT_EOL", "建設時と解体時（A・C 段階）", ("A1-A3", "A4", "A5", "C1", "C2", "C3", "C4")),
]

# material classes of the engine (synth.model.MATERIAL_CLASSES) used by the material screen
MATERIALS = [
    # fid, class, label, unit, accepted units, division, group
    ("m_concrete", "CONCRETE", "コンクリート（上部構造）", "m3", ("m3", "t", "kg"), "STRUCTURE", "構造材"),
    ("m_concrete_fdn", "CONCRETE", "コンクリート（基礎・杭）", "m3", ("m3", "t", "kg"), "FOUNDATION", "構造材"),
    ("m_rebar", "REBAR", "鉄筋", "t", ("t", "kg"), "STRUCTURE", "構造材"),
    ("m_steel", "STRUCTURAL_STEEL", "鉄骨（構造用鋼材）", "t", ("t", "kg"), "STRUCTURE", "構造材"),
    ("m_timber", "TIMBER", "木材（構造材）", "m3", ("m3", "t", "kg"), "STRUCTURE", "構造材"),
    ("m_glass", "GLASS", "ガラス", "m2", ("m2", "t", "kg"), "OPENINGS", "外装・開口"),
    ("m_aluminium", "ALUMINIUM", "アルミニウム（サッシ等）", "t", ("t", "kg"), "OPENINGS", "外装・開口"),
    ("m_masonry", "MASONRY", "組積・ALC・押出成形板", "m2", ("m2", "t", "kg"), "ROOF_EXTERIOR_WALL", "外装・開口"),
    ("m_membrane", "MEMBRANE", "防水", "m2", ("m2", "t", "kg"), "ROOF_EXTERIOR_WALL", "外装・開口"),
    ("m_insulation", "INSULATION", "断熱材", "m2", ("m2", "t", "kg"), "INTERIOR", "内装・断熱"),
    ("m_board", "BOARD", "ボード類（石膏ボード等）", "m2", ("m2", "t", "kg"), "INTERIOR", "内装・断熱"),
    ("m_finish", "FINISH", "仕上げ材", "m2", ("m2", "t", "kg"), "INTERIOR", "内装・断熱"),
    ("m_plastic", "PLASTIC", "樹脂（配管・シート等）", "t", ("t", "kg"), "INTERIOR", "内装・断熱"),
    ("m_mortar", "MORTAR", "モルタル", "t", ("t", "kg"), "INTERIOR", "内装・断熱"),
]
TRADES = [("HVAC", "空調"), ("ELECTRICAL", "電気"), ("PLUMBING", "給排水衛生"), ("CONVEYANCE", "昇降機")]

FIELDS: dict[str, dict] = {}


def _f(fid, **kw):
    kw.setdefault("type", "number")
    kw.setdefault("unit", "")
    kw.setdefault("engine", [])
    kw.setdefault("required", False)
    kw.setdefault("na", "skip")
    kw.setdefault("estimable", False)
    kw.setdefault("help", "")
    kw.setdefault("private", False)
    FIELDS[fid] = kw


# ---------------------------------------------------------------- 基本情報 -----------------------------------
G = ("basic", "建物の概要", "building")
_f("b_name", label="建物名称", type="text", screen=G[0], group=G[1], category=G[2], engine=[],
   role="record", private=True, help="記録のみ。計算には使わず、エンジンの保存にも渡さない。")
_f("b_address", label="所在地", type="text", screen=G[0], group=G[1], category=G[2], engine=[], role="record", private=True,
   help="住所は自動調査に使うだけで、計算と書き出しには使わない。")
_f("b_use", label="主な用途", type="enum", enum=USES, screen=G[0], group=G[1], category=G[2],
   engine=["project.building_use", "project.use_area_breakdown"], role="use", required=True,
   help="延床面積と組み合わせて、用途別面積（エンジンの必須入力）になる。")
_f("b_structure", label="構造", type="enum", enum=[(s["id"], s["label"]) for s in STRUCTURES], screen=G[0], group=G[1],
   category=G[2], engine=["project.structure_type"], role="scalar")
_f("b_gfa", label="延床面積", unit="m2", screen=G[0], group=G[1], category=G[2],
   engine=["project.gross_floor_area", "project.use_area_breakdown"], role="gfa", required=True, estimable=True,
   range=(1, 3e6), help="PLATEAU の屋根面積×階数は推定であり、延床面積の記録ではない。")
_f("b_floors_above", label="地上階数", type="integer", unit="階", screen=G[0], group=G[1], category=G[2],
   engine=["project.floors_above"], role="scalar", estimable=True, range=(1, 200))
_f("b_floors_below", label="地下階数", type="integer", unit="階", screen=G[0], group=G[1], category=G[2],
   engine=["project.floors_below"], role="scalar", na="zero", estimable=True, range=(0, 20),
   help="地下が無いときは「適用外」（0 階として渡す）。")
_f("b_height", label="建物の高さ", unit="m", screen=G[0], group=G[1], category=G[2], engine=["project.building_height"],
   role="scalar", estimable=True, range=(1, 700))
_f("b_footprint", label="建築面積", unit="m2", screen=G[0], group=G[1], category=G[2], engine=["project.building_footprint"],
   role="scalar", estimable=True, range=(1, 1e6))
_f("b_completion_year", label="竣工年（予定）", type="integer", unit="年", screen=G[0], group=G[1], category=G[2],
   engine=["project.completion_year", "boundary.study_start_year"], role="year", range=(1868, 2200))
_f("b_project_type", label="新築・既存", type="enum", screen=G[0], group=G[1], category=G[2],
   enum=[("NEW_BUILD", "新築"), ("EXISTING", "既存建物"), ("EXTENSION_RENOVATION", "増改築・改修")],
   engine=["project.project_type"], role="scalar")

G = ("basic", "地盤と基礎（参考）", "building")
_f("g_foundation", label="基礎の形式", type="enum", screen=G[0], group=G[1], category=G[2],
   enum=[("DIRECT", "直接基礎"), ("PILE", "杭基礎"), ("IMPROVEMENT", "地盤改良＋直接基礎"), ("UNKNOWN", "未定（場合分けで比べる）")],
   engine=["project.foundation_system"], role="scalar",
   help="基礎コンクリートの概算の場合分けに使う。地盤調査の代わりにも、構造設計の判断にもならない。")
_f("g_borehole", label="近くのボーリング調査（国土地盤情報）", type="text", screen=G[0], group=G[1], category=G[2],
   engine=[], role="record",
   help="KuniJiban の検索サイトで調べた地点・距離・調査年を書き留める。敷地そのものの地盤ではない。")

G = ("basic", "評価の条件", "assessment")
_f("a_stages", label="評価範囲（ライフサイクル段階）", type="enum", screen=G[0], group=G[1], category=G[2],
   enum=[(k, lab) for k, lab, _ in STAGE_PRESETS], engine=["boundary.included_lifecycle_stages"], role="stages",
   required=True, help="これが無いと、エンジンはどの段階も合計しない（0 になる）ので必須。")
_f("a_eol_route", label="解体後の処理（シナリオ）", type="enum", screen=G[0], group=G[1], category=G[2],
   enum=[("RECYCLE", "再資源化"), ("PROCESSING", "中間処理"), ("LANDFILL", "埋立"), ("REUSE", "再使用")],
   engine=["materials[].end_of_life.routes[].route"], role="eol_route", required=True, na_context=True,
   help="材料の行ごとに必須。1 つのシナリオを全部の材料に当てる（割合 1）。「適用外」は、材料の行が無いときや解体後の段階を"
        "評価範囲から外したときだけ。")
_f("a_eol_haul_km", label="解体材の運搬距離", unit="km", screen=G[0], group=G[1], category=G[2],
   engine=["end_of_life.haul_distance_km"], role="mat_common", range=(0, 2000), na_never=True)
_f("a_reconstruction", label="大規模改修・建替えの想定", type="enum", screen=G[0], group=G[1], category=G[2],
   enum=[("NONE", "想定しない"), ("MAJOR_REFURBISHMENT", "大規模改修"), ("REBUILD_IDENTICAL", "同じ建物に建替え")],
   engine=["boundary.reconstruction_scenario"], role="scalar", na_note="改修・建替えなし")
_f("a_replacement_cycle", label="改修・建替えの周期", unit="年", screen=G[0], group=G[1], category=G[2],
   engine=["boundary.replacement_cycle"], role="scalar", range=(1, 200), na_never=True)
_f("a_recon_fraction", label="改修の範囲（割合）", unit="", screen=G[0], group=G[1], category=G[2],
   engine=["boundary.reconstruction_scope_fraction"], role="scalar", range=(0, 1), na="zero")

# ---------------------------------------------------------------- 材料 -------------------------------------
for fid, cls, label, unit, units, div, grp in MATERIALS:
    _f(fid, label=label, unit=unit, units=list(units), screen="material", group=grp, category="construction",
       engine=["materials[].quantity", "materials[].material_class"], role="material", material_class=cls,
       division=div, na="absent", estimable=True, range=(0, 1e8),
       help="図面・数量表から。無いときは統計の概算（範囲つき）を候補にできる。")
G = ("material", "材料の共通条件", "construction")
_f("m_waste_rate", label="施工時の廃棄率（共通）", unit="", screen=G[0], group=G[1], category=G[2],
   engine=["materials[].waste_rate"], role="mat_common", range=(0, 0.95), na="zero")
_f("m_reuse_rate", label="再使用材の割合（共通）", unit="", screen=G[0], group=G[1], category=G[2],
   engine=["materials[].reuse_rate"], role="mat_common", range=(0, 1), na="zero")
_f("m_quantity_basis", label="数量の基準", type="enum", screen=G[0], group=G[1], category=G[2],
   enum=[("DESIGN", "設計数量"), ("ORDERED", "発注数量"), ("AS_BUILT", "竣工数量")],
   engine=["materials[].quantity_basis"], role="mat_common", na_never=True)
_f("m_transport_km", label="材料の運搬距離（共通）", unit="km", screen=G[0], group=G[1], category=G[2],
   engine=["materials[].transport.distance_km"], role="mat_common", range=(0, 20000), na_never=True)
_f("m_transport_mode", label="材料の運搬手段（共通）", type="enum", screen=G[0], group=G[1], category=G[2],
   enum=[("TRUCK_SMALL", "小型トラック"), ("TRUCK_LARGE", "大型トラック"), ("RAIL", "鉄道"), ("SHIP", "船")],
   engine=["materials[].transport.factor_id"], role="mat_common",
   help="距離・手段・質量がそろう行は トンキロ で、そろわない行は参照セットの配送原単位（数量あたり）で計算する。", na_never=True)
_f("m_repair_rate", label="修繕率（年あたり・共通）", unit="", screen=G[0], group=G[1], category=G[2],
   engine=["materials[].repair_rate"], role="mat_common", range=(0, 0.5), na="zero")
_f("m_refresh_cycle", label="更新周期（共通）", unit="年", screen=G[0], group=G[1], category=G[2],
   engine=["materials[].refresh_cycle"], role="mat_common", range=(1, 200), na_note="更新しない")
G = ("material", "施工（現場）", "construction")
_f("c_site_electricity", label="工事中の電力", unit="kWh", screen=G[0], group=G[1], category=G[2],
   engine=["construction.electricity_kwh"], role="scalar", na="zero", range=(0, 1e9))
_f("c_diesel", label="工事中の軽油", unit="L", screen=G[0], group=G[1], category=G[2],
   engine=["construction.fuels"], role="fuel", fuel="DIESEL", na="absent", range=(0, 1e9))

# ---------------------------------------------------------------- 設備 -------------------------------------
for trade, tl in TRADES:
    t = trade.lower()
    G = ("equipment", tl, "equipment")
    _f("e_%s_count" % t, label="%s機器の台数" % tl, unit="台", screen=G[0], group=G[1], category=G[2],
       engine=["equipment[].quantity"], role="equipment", trade=trade, part="quantity", na="absent",
       estimable=True, range=(0, 1e6), help="台数が分からないときは、少・中・多の場合分けを候補にできる。")
    _f("e_%s_life" % t, label="%s機器の耐用年数" % tl, unit="年", screen=G[0], group=G[1], category=G[2],
       engine=["equipment[].service_life"], role="equipment", trade=trade, part="service_life", range=(1, 120),
       na_note="交換しない")
    _f("e_%s_mass" % t, label="%s機器 1 台の解体時質量" % tl, unit="kg", screen=G[0], group=G[1], category=G[2],
       engine=["equipment[].end_of_life_mass_kg"], role="equipment", trade=trade, part="end_of_life_mass_kg",
       range=(0, 1e6), na_never=True, help="メーカーの仕様書の質量（製品の性能値であって、製造時の CO2 ではない）。")
G = ("equipment", "設備の共通条件", "equipment")
_f("e_repair_rate", label="設備の修繕率（年あたり）", unit="", screen=G[0], group=G[1], category=G[2],
   engine=["equipment[].repair_rate"], role="eq_common", range=(0, 0.5), na="zero")
G = ("equipment", "冷媒", "equipment")
_f("r_charge_kg", label="冷媒の充填量（合計）", unit="kg", screen=G[0], group=G[1], category=G[2],
   engine=["refrigerants[].charge_mass_kg"], role="refrigerant", part="charge_mass_kg", na="absent", range=(0, 1e6),
   help="機器の銘板・仕様書の値。冷媒を使わないときは「適用外」。")
_f("r_gwp", label="冷媒の地球温暖化係数（GWP）", unit="kgCO2e/kg", screen=G[0], group=G[1], category=G[2],
   engine=["refrigerants[].gwp"], role="refrigerant", part="gwp", range=(0, 30000),
   help="冷媒の種類に対する公的な値を、出典つきで入れる。", na_never=True)
_f("r_leak_rate", label="年あたりの漏えい率", unit="", screen=G[0], group=G[1], category=G[2],
   engine=["refrigerants[].annual_leak_rate"], role="refrigerant", part="annual_leak_rate", range=(0, 1), na="zero")
_f("r_loss_rate", label="交換時の損失率", unit="", screen=G[0], group=G[1], category=G[2],
   engine=["refrigerants[].replacement_loss_rate"], role="refrigerant", part="replacement_loss_rate", range=(0, 1), na="zero")
_f("r_recovery_rate", label="廃棄時の回収率", unit="", screen=G[0], group=G[1], category=G[2],
   engine=["refrigerants[].end_of_life_recovery_rate"], role="refrigerant", part="end_of_life_recovery_rate", range=(0, 1), na_never=True)
_f("r_life", label="冷媒機器の交換周期", unit="年", screen=G[0], group=G[1], category=G[2],
   engine=["refrigerants[].service_life"], role="refrigerant", na_note="交換しない", part="service_life", range=(1, 120))
_f("r_top_up", label="漏えい分の補充", type="enum", enum=[("yes", "補充する"), ("no", "補充しない")], screen=G[0],
   group=G[1], category=G[2], engine=["refrigerants[].top_up"], role="refrigerant", part="top_up", na_note="補充しないとして計算")

# ---------------------------------------------------------------- 運用 -------------------------------------
G = ("operation", "エネルギー（年あたり）", "operation")
_f("o_source", label="運用データの種類", type="enum", screen=G[0], group=G[1], category=G[2],
   enum=[("BILLS", "請求書・検針の実績"), ("BEMS", "BEMS の計測"), ("PHYSICS", "設計の計算（物理モデル）"), ("STATISTICS", "統計の原単位")],
   engine=["operation.energy_simulation_basis"], role="scalar",
   help="優先順位：実績・計測 ＞ 物理計算 ＞ 統計。")
for fid, label, unit, name, help_ in (
        ("o_elec_kwh", "購入電力", "kWh/年", "electricity", "請求書の 12 か月分の合計が一番よい。"),
        ("o_gas_m3", "都市ガス", "m3/年", "gas", ""),
        ("o_oil_l", "灯油・重油", "L/年", "oil", ""),
        ("o_dheat_mj", "地域熱供給", "MJ/年", "district_heat", ""),
        ("o_pv_kwh", "太陽光などの自家発電", "kWh/年", "onsite_generation", ""),
        ("o_export_kwh", "自家発電のうち外へ売った電力", "kWh/年", "onsite_export", "")):
    _f(fid, label=label, unit=unit, screen=G[0], group=G[1], category=G[2], engine=["operation.%s" % name],
       role="profile", profile="operation.%s" % name, na="zero", range=(0, 1e10), help=help_,
       estimable=(fid in ("o_elec_kwh", "o_gas_m3")))
_f("o_fm_ratio", label="購入電力のうち施設管理（B2）分の割合", unit="", screen=G[0], group=G[1], category=G[2],
   engine=["operation.facility_management_ratio"], role="scalar", range=(0, 1), na="zero")
G = ("operation", "電力の排出係数", "operation")
_f("o_grid_value", label="運用時の電力の排出係数", unit="kgCO2e/kWh", screen=G[0], group=G[1], category=G[2],
   engine=["operation.grid.kind", "operation.grid.start", "operation.grid.table"], role="grid", required=True,
   na_context=True, range=(0, 3),
   help="電気事業者の公表値などを出典つきで。評価期間中は一定として扱う。「適用外」は、購入電力が 0 のときや B6・B2 を評価範囲から外したときだけ。")
_f("o_grid_construction", label="工事中の電力の排出係数", unit="kgCO2e/kWh", screen=G[0], group=G[1], category=G[2],
   engine=["operation.grid.construction_value"], role="scalar", required=True, na_context=True, range=(0, 3),
   help="「適用外」は、工事中の電力が 0 のときだけ。")
G = ("operation", "水と廃棄物（年あたり）", "operation")
for fid, label, unit, name in (("o_water_m3", "上水の使用量", "m3/年", "water"),
                               ("o_sewage_m3", "下水の排出量", "m3/年", "sewage"),
                               ("o_waste_kg", "一般廃棄物", "kg/年", "municipal_waste")):
    _f(fid, label=label, unit=unit, screen=G[0], group=G[1], category=G[2], engine=["water_waste.%s" % name],
       role="profile", profile="water_waste.%s" % name, required=True, na="zero", range=(0, 1e10),
       estimable=False)

SCREENS = [
    {"id": "basic", "label": "基本情報"},
    {"id": "material", "label": "材料"},
    {"id": "equipment", "label": "設備"},
    {"id": "operation", "label": "運用"},
]
for s in SCREENS:
    groups = []
    for fid, F in FIELDS.items():
        if F["screen"] != s["id"]:
            continue
        g = next((g for g in groups if g["label"] == F["group"]), None)
        if g is None:
            g = {"label": F["group"], "fields": []}
            groups.append(g)
        g["fields"].append(fid)
    s["groups"] = groups

# Order of the material fields by structure (higher first). These are display priorities only, from the
# general make-up of each structure type; they do not enter any calculation.
_PRI = {
    "RC": ("m_concrete", "m_rebar", "m_concrete_fdn"),
    "SRC": ("m_steel", "m_concrete", "m_rebar", "m_concrete_fdn"),
    "S": ("m_steel", "m_concrete", "m_concrete_fdn", "m_rebar"),
    "W": ("m_timber", "m_concrete_fdn", "m_board"),
}
PRIORITY = {k: {fid: len(v) - i for i, fid in enumerate(v)} for k, v in _PRI.items()}

# Inputs of the engine that no screen field reaches, grouped with the reason (the 「反映外」 ledger
# beyond the 241-entry binding is built in bridge.unconnected()).
NOT_ON_SCREENS = {
    "materials[].epd.*": "EPD（製品の環境宣言）の入力欄は未実装。メーカーの EPD があっても今は反映しない。",
    "materials[].composition": "複合材の構成比は未実装。",
    "materials[].unquantified_cost_ratio": "金額だけの項目の比率は未実装。",
    "cost_items": "金額からの推計（X-16）は未実装。",
    "equipment[].replacement_event_list": "交換年の個別指定は未実装（耐用年数で周期交換とみなす）。",
    "refrigerants[].change_years": "冷媒の交換年の個別指定は未実装（交換周期を使う）。",
    "construction.waste_streams": "現場の廃棄物の内訳は未実装。",
    "end_of_life.demolition_activities": "解体工事（C1）の作業量は未実装。",
    "end_of_life.waste_hauls": "材料の行に含まれない解体材の運搬は未実装。",
    "operation.*.LINEAR_TREND": "年ごとに変わる運用量は未実装（一定とみなす）。",
    "operation.grid.LINEAR_DECLINE_TO_FLOOR/STEPWISE": "将来の排出係数の低下は未実装（一定）。",
    "summary_quantities.timber_*": "木材の炭素貯蔵（STO-01）の密度・炭素率は未実装。",
}


def field_count() -> dict:
    by = {}
    for F in FIELDS.values():
        by.setdefault(F["screen"], 0)
        by[F["screen"]] += 1
    return {"total": len(FIELDS), "by_screen": by}


def meta_fields() -> dict:
    """The catalogue as the front end reads it (GET /api/meta)."""
    out = {}
    for fid, F in FIELDS.items():
        out[fid] = {"label": F["label"], "unit": F.get("unit", ""), "type": "number" if F["type"] == "integer" else F["type"],
                    "enum": [{"value": v, "label": lab} for v, lab in F.get("enum", [])],
                    "help": F["help"], "required": F["required"], "estimable": F["estimable"], "engine": F["engine"],
                    "category": F["category"], "units": F.get("units", [F.get("unit", "")]), "na": F["na"],
                    "na_note": F.get("na_note", ""), "na_never": bool(F.get("na_never"))}
    return out
