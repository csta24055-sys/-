"""Stage C: inventory records from the regions, classification by rules, reconciliation.

Reads the private scan (scan.sqlite3 with the regions) and the received tree v0.1; writes the private
table ``inventory`` into the same file. Nothing here writes into the repository.
Usage: python3 -I classify.py <scan.sqlite3> <tree v0.1 json>
"""
import collections, hashlib, json, os, re, sqlite3, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tree_ext  # noqa: E402

BOOK = {1: "簡易算定", 2: "標準算定", 3: "分類表", 4: "集計表", 5: "詳細算定"}

# base sheet name (without _GHG / _CO2) -> (default node, sheet kind)
SHEETS = [
    (r"^(表紙|修正更新履歴|注意事項)$", "assessment.check.tool_info", "doc"),
    (r"^チェックリスト$", "assessment.check.checklist", "check"),
    (r"^入力シート \(A1", "construction.other", "input_main"),
    (r"^入力シート$", "construction.other", "input"),
    (r"^入力シート \(B1\)", "equipment.other", "input_b1"),
    (r"^入力シート \(B6", "operation.other", "input_b67"),
    (r"^(詳細算定結果|算定結果|算定結果報告用シート.*|Upfront Carbon 算定結果|WLC算定結果|排出量計算集計表)$", "assessment.display.result_tables", "result"),
    (r"^(原単位|排出原単位)$", "assessment.factors.material_factor", "factor"),
    (r"^(CO2|CH4|N2O|SF6|NF3|HFCs|PFCs|GHG)$", "assessment.factors.gas_factor_db", "factor"),
    (r"^排出係数$", "assessment.factors.energy_factor", "factor"),
    (r"^EPD組込$", "assessment.factors.epd", "factor"),
    (r"^複合原単位$", "assessment.factors.composite_factor", "factor"),
    (r"^資材構成$", "assessment.conversions.composite_definition", "composition"),
    (r"^入力-[12]$", "assessment.assumptions.internal_parameter_tables", "internal"),
    (r"^(電|コード表 電|電気主要設備機器)$", "equipment.electrical.standard_table", "equip"),
    (r"^(空|コード表 空)$", "equipment.hvac.standard_table", "equip"),
    (r"^(衛|コード表 衛)$", "equipment.plumbing.standard_table", "equip"),
    (r"^(昇|コード表 昇)$", "equipment.elevator.standard_table", "equip"),
    (r"^配管・ケーブル$", "equipment.eq_details.pipe_cable_length", "equip"),
    (r"^建$", "construction.item_details.code", "equip"),
    (r"^算出分類$", "assessment.conversions.calc_class", "param"),
    (r"^SHASE$", "assessment.conversions.equipment_standard", "param"),
    (r"^(物価補正|物価)$", "assessment.conversions.price_correction", "param"),
    (r"^工事分倍率内訳", "assessment.conversions.work_multiplier", "param"),
    (r"^(設備LCW分析|発生品目別分析|LCR･LCW集計|処理別分析)$", "operation.end_of_life.waste_analysis", "analysis"),
    (r"^標準値管理シート$", "assessment.assumptions.standard_values", "param"),
    (r"^各種パラメータ", "assessment.assumptions.parameters", "param"),
    (r"^エネルギー統計値$", "assessment.assumptions.energy_statistics", "param"),
    (r"^更新周期集計$", "operation.maintenance.cycle_summary", "analysis"),
    (r"^経年表記", "operation.maintenance.yearly_series", "analysis"),
    (r"^木材_炭素貯蔵$", "assessment.assumptions.carbon_coefficients", "param"),
    (r"^コンクリート$", "assessment.assumptions.carbon_coefficients", "param"),
    (r"^LCA参照シート", "assessment.conversions.external_lca_reference", "internal"),
]
CODE_TABLE = re.compile(r"^(コード表|電気主要設備機器)")

FORM = [
    (r"建物名称|建物名", "building.identity.name"), (r"算定者", "building.identity.assessor"), (r"所在地", "building.identity.location"),
    (r"算定日", "building.identity.calc_date"), (r"竣工年", "building.identity.completion_year"), (r"算定段階", "building.identity.design_stage"),
    (r"延べ?床面積", "building.geometry.gross_floor_area"), (r"^用途$|主用途", "building.geometry.main_use"),
    (r"事務所|ホテル|病院|物販|学校|飲食|集会|独身寮|流通施設|工場|集合住宅|共用部|駐車場|各用途床面積", "building.geometry.use_floor_areas"),
    (r"階数", "building.geometry.floors"), (r"高さ", "building.geometry.height"), (r"基準階面積", "building.geometry.typical_floor_area"),
    (r"建物形状|セットバック", "building.geometry.shape"), (r"最大スパン", "building.geometry.max_span"),
    (r"主要構造", "building.structure.main_structure"), (r"杭・基礎", "building.structure.foundation"),
    (r"屋根", "building.structure.roof_spec"), (r"外壁|外装", "building.structure.facade_spec"),
    (r"評価(対象)?期間", "building.boundary.study_period"), (r"建替周期|建替回数|改修回数", "building.boundary.replacement_cycle"),
    (r"使用する単位", "assessment.method.gas_scope"),
]
COLS = [
    (r"更新周期", "operation.maintenance.material_cycle"), (r"修繕率", "operation.maintenance.repair_rate"),
    (r"端材率", "construction.transport.offcut_waste"), (r"ﾘﾕｰｽ率|リユース率", "construction.transport.reuse_recycle"),
    (r"樹種|炭素固定|炭素貯蔵", "construction.item_details.timber_carbon"), (r"CO2固定", "construction.item_details.concrete_fixation"),
    (r"コード|細目", "construction.item_details.code"), (r"備考|根拠", "assessment.check.basis_notes"),
    (r"工事分倍率", "assessment.conversions.work_multiplier"),
]
GROUPS = [
    (r"杭・基礎", "construction.ground.pile_foundation"), (r"コンクリート", "construction.frame.concrete"), (r"鉄骨", "construction.frame.steel"),
    (r"鉄筋", "construction.frame.rebar"), (r"木材", "construction.frame.timber"), (r"3\.9その他", "construction.frame.other_frame"),
    (r"屋根", "construction.external.roof"), (r"外壁", "construction.external.exterior_wall"), (r"外部開口", "construction.external.exterior_opening"),
    (r"内部床", "construction.internal.floor"), (r"内壁", "construction.internal.partition"), (r"内部開口", "construction.internal.interior_opening"),
    (r"天井", "construction.internal.ceiling"), (r"内部雑", "construction.internal.interior_misc"),
    (r"一式工事分|工事細目以外|小計", "assessment.conversions.unquantified"),
    (r"電気設備", "equipment.electrical.cost"), (r"太陽光", "equipment.electrical.pv"), (r"空調設備", "equipment.hvac.cost"),
    (r"衛生設備", "equipment.plumbing.cost"), (r"昇降機", "equipment.elevator.cost"), (r"共通費|内訳参考", "construction.temporary.common_cost"),
    (r"工事用|工事燃料|ガソリン|軽油|灯油|重油|石油", "construction.temporary.site_fuel"), (r"電気★|都市ガス|代替", "construction.temporary.site_power_gas"),
    (r"上水|下水|上下水", "construction.temporary.site_water"), (r"廃棄物", "construction.transport.offcut_waste"),
]
B1 = [
    (r"物質名|化学式", "equipment.refrigerant_equipment.substance"), (r"温暖化係数|オゾン層", "assessment.factors.gwp"),
    (r"回収・処理|回収処理費用", "equipment.refrigerant_equipment.recovery_cost"), (r"回収率", "operation.leakage.recovery_rate"),
    (r"漏洩|漏えい", "operation.leakage.leak_rate"), (r"更新周期", "operation.leakage.change_timing"),
    (r"評価(対象)?期間", "building.boundary.study_period"), (r"建替|改修回数", "building.boundary.replacement_cycle"),
    (r"建築関連用途", "equipment.refrigerant_equipment.application"),
    (r"使用量|重量|空調冷媒|発泡断熱材|消火剤|遮断器", "equipment.refrigerant_equipment.charge"),
]
B67 = [
    (r"新築または既存", "building.boundary.project_type"), (r"排出係数|行コード|事業者|kg-CO2", "assessment.factors.energy_factor"),
    (r"施設管理諸室", "operation.energy.fm_ratio"), (r"創エネルギー|発電量", "operation.generation.generation"),
    (r"換算係数|換算値|発熱量", "assessment.conversions.conversion_method"),
    (r"上水", "operation.utility.water"), (r"下水|排水", "operation.utility.sewage"), (r"廃棄物", "operation.utility.municipal_waste"),
    (r"m3/年|kg/年", "operation.utility"),
    (r"年間.{0,3}エネルギー|消費電力量|消費ガス量|エネルギー種別", "operation.energy.annual_use"), (r"備考|根拠", "assessment.check.basis_notes"),
]
B67_ROWS = [
    (r"上水", "operation.utility.water"), (r"下水|排水", "operation.utility.sewage"), (r"廃棄物", "operation.utility.municipal_waste"),
    (r"電力|電気", "operation.energy.electricity"), (r"ガス", "operation.energy.city_gas"), (r"油|LPG|石油", "operation.energy.oil_fuel"),
    (r"熱|蒸気|冷水|温水", "operation.energy.other_energy"),
]
LEGEND = ("必須入力項目", "任意入力項目")
TEXT_COLUMN_NODE = {"input_main": "construction.item_details.spec", "input": "construction.item_details.spec",
                    "input_b1": "equipment.refrigerant_equipment.substance", "input_b67": "operation.energy.annual_use"}
ANY = [
    (r"修繕率", "operation.maintenance.repair_rate"), (r"ﾘｻｲｸﾙ|リサイクル|処理\s*ｺｰﾄﾞ|再利用率", "operation.end_of_life.treatment_share"),
    (r"積\s*載\s*率|片道|距離", "operation.end_of_life.waste_transport"), (r"物価", "assessment.conversions.price_correction"),
    (r"システム境界|国内|海外|消費支出|資本形成", "assessment.method.system_boundary"), (r"物量", "assessment.conversions.quantity_per_area"),
    (r"オゾン層|温暖化", "assessment.factors.gwp"), (r"炭素含有|気乾密度|木材の密度|スラグ", "assessment.assumptions.carbon_coefficients"),
]
DV_RULES = [
    ("基本計画", "building.identity.design_stage"), ("RC造", "building.structure.main_structure"), ("ホテル・旅館", "building.geometry.main_use"),
    ("国内消費支出", "assessment.method.system_boundary"), ("複合原単位", "construction.item_details.code"),
]
INTERNAL_LABEL = re.compile(r"通し番号|行ｺｰﾄﾞ|行コード|^No\.?$|^番号$|築年|^年$")
UNIT = re.compile(r"kg|CO2|㎡|m2|m3|㎥|kWh|MJ|GJ|円|年|％|%|/|／|台|回|km|^m$|^L$|^t$|個|階|人|kW")
STAGE = re.compile(r"[ABCD]\d(?:\s*[～~\-]\s*[ABCD]?\d)?")


def L(c):
    s = ""
    while c:
        c, r = divmod(c - 1, 26)
        s = chr(65 + r) + s
    return s


def base_name(name):
    return re.sub(r"_(GHG|CO2)$", "", name)


def sheet_rule(base):
    for pat, node, kind in SHEETS:
        if re.search(pat, base):
            return node, kind
    return "review.unknown", "unknown"


def first(rules, text):
    text = re.sub(r"\s+", "", text or "")              # labels are often broken over several lines
    for pat, node in rules:
        if re.search(pat, text):
            return node
    return None


def classify(base, kind, default, role, label, group, dvtext, in_table):
    """(node id, basis) for one record of roles I / C / TD."""
    text = label or ""
    if text.strip() in LEGEND:
        return "assessment.check.basis_notes", "凡例"
    if role == "TD" and kind.startswith("input"):
        return first(COLS, text) or TEXT_COLUMN_NODE[kind], "列見出し" if first(COLS, text) else "シート"
    if dvtext:
        for key, node in DV_RULES:
            if key in dvtext:
                return node, "入力規則"
    if kind == "input_main":
        if in_table:
            node = first(COLS, text.split(" / ")[-1]) or first(COLS, text)     # the nearest header line decides
            if node:
                return node, "列見出し"
            node = first(GROUPS, group or "")
            if node:
                return node, "行区分"
            return "construction.other", "行区分なし"
        node = first(FORM, text)
        return (node, "見出し") if node else ("review.unknown" if not text else "building.other", "見出しなし" if not text else "見出し不一致")
    if kind == "input":
        node = first(FORM, text) or first(COLS, text) or first(GROUPS, text) or first(B67, text) or (
            "construction.item_details.quantity" if re.search(r"数量", text) else None)
        return (node, "見出し") if node else ("review.unknown" if not text else "construction.other", "見出しなし" if not text else "見出し不一致")
    if kind == "input_b1":
        node = first(B1, text)
        return (node, "見出し") if node else ("review.unknown" if not text else "equipment.other", "見出しなし" if not text else "見出し不一致")
    if kind == "input_b67":
        node = first(B67, text)
        return (node, "見出し") if node else ("review.unknown" if not text else "operation.other", "見出しなし" if not text else "見出し不一致")
    if kind == "unknown":
        return "review.unknown", "シート不明"
    if re.search(r"更新周期", text):
        return ("operation.maintenance.equipment_life" if kind == "equip" else "operation.maintenance.material_cycle"), "見出し"
    node = first(ANY, text)
    if node and kind in ("internal", "analysis", "param", "equip", "composition"):
        return node, "見出し"
    if kind == "equip" and CODE_TABLE.search(base):
        return default.replace("standard_table", "code_table"), "シート"
    return default, "シート"


def unit_of(unit, header, numfmt):
    if unit and UNIT.search(unit) and len(unit) <= 14:
        return unit.replace("\n", "")
    m = re.search(r"[（(\[［]([^（）()\[\]［］]{1,14})[）)\]］]", header or "")
    if m and UNIT.search(m.group(1)):
        return m.group(1)
    m = re.search(r'"([^"]{1,8})"', numfmt or "")
    if m and UNIT.search(m.group(1)):
        return m.group(1)
    if numfmt and "%" in numfmt:
        return "%"
    return ""


def kind_of(skind, role, rec):
    if role == "F":
        return "他の入力から自動計算される値"
    if role in ("TD", "L"):
        return "内部処理・参照用の値"
    inputs = skind.startswith("input") or skind == "check"
    if role == "I":
        if rec["n"] == rec["n_blank"]:
            return "入力可能な空欄"
        if rec.get("dv"):
            return "選択式の入力項目"
        if inputs or skind in ("doc", "result"):
            return "利用者が直接入力する値"
        return "排出原単位・各種係数" if skind == "factor" else "標準値・デフォルト値"
    if rec.get("seq") or INTERNAL_LABEL.search(rec.get("label") or ""):
        return "内部処理・参照用の値"
    if skind == "factor":
        return "排出原単位・各種係数"
    if inputs or skind in ("param", "equip", "composition", "internal"):
        return "標準値・デフォルト値"
    return "内部処理・参照用の値"


def type_of(rec, role):
    if role == "F":
        return "数式"
    if role in ("TD", "L"):
        return "文字列"
    if rec["n"] == rec["n_blank"]:
        return "未設定"
    if rec["n_str"] and (rec["n_num"] or rec["n_bool"]):
        return "混在"
    if rec["n_str"]:
        return "文字列"
    if rec["n_bool"] and not rec["n_num"]:
        return "真偽"
    return "整数" if rec.get("n_int") == rec["n_num"] else "数値"


def main(path, tree_path):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    with open(tree_path, encoding="utf-8") as fh:
        tree = tree_ext.build(json.load(fh))
    nodes = tree_ext.node_index(tree)
    sheets = {r["id"]: dict(r) for r in db.execute("SELECT * FROM sheets")}
    for s in sheets.values():
        s["base"] = base_name(s["name"])
        s["default"], s["kind"] = sheet_rule(s["base"])
    dvs = {r["id"]: dict(r) for r in db.execute("SELECT * FROM validations")}
    recs = []

    def add(sid, role, **kw):
        s = sheets[sid]
        rec = dict(sheet_id=sid, role=role, n=0, n_blank=0, n_num=0, n_str=0, n_bool=0, n_int=0, n_req=0, n_distinct=None, uniform=0,
                   seq=0, label="", header="", group="", unit="", numfmt="", dv=None, cells="", n_patterns=None, vhash="", regions=0,
                   note="", node=None, basis="", in_table=False, pre=None)
        rec.update(kw)
        recs.append(rec)
        return rec

    # --- regions -------------------------------------------------------------------------------------
    for sid, s in sheets.items():
        regs = [dict(r) for r in db.execute("SELECT * FROM regions WHERE sheet_id=? ORDER BY row_min, col1", (sid,))]
        table_from, d_group, c_group = None, {}, {}
        rowtext = collections.defaultdict(list)
        inputs = s["kind"].startswith("input")
        if inputs:
            for row, col, v in db.execute("SELECT row, col, v FROM cells WHERE sheet_id=? AND t='s' AND TRIM(v)<>'' ORDER BY row, col", (sid,)):
                v = v.strip().replace("\n", " ")
                rowtext[row].append((col, v))
                if s["kind"] == "input_main":
                    if col == 4 and v == "細目":
                        table_from = row + 2
                    elif table_from and row >= table_from and col in (3, 4):
                        (d_group if col == 4 else c_group)[row] = v
        section = {}
        if table_from:
            last = ""
            for row in range(table_from, (s["n_cells"] and 2000) or 2000):
                last = c_group.get(row, last)
                section[row] = last

        def group_of(row):
            return d_group.get(row) or c_group.get(row) or section.get(row, "")

        def left_text(row, col):
            best = ""
            for c, v in rowtext.get(row, ()):
                if c < col and col - c <= 14:
                    best = v
            return best

        rules = {"input_b1": B1, "input_b67": B67, "input": FORM + COLS + GROUPS + B67, "input_main": FORM}.get(s["kind"])
        colnode = {}
        if s["kind"] == "input_b1":
            spans = {}
            for (ref,) in db.execute("SELECT ref FROM merges WHERE sheet_id=?", (sid,)):
                m2 = re.match(r"([A-Z]+)(\d+):([A-Z]+)(\d+)", ref)
                if m2:
                    c1 = sum((ord(ch) - 64) * 26 ** i for i, ch in enumerate(reversed(m2.group(1))))
                    c2 = sum((ord(ch) - 64) * 26 ** i for i, ch in enumerate(reversed(m2.group(3))))
                    spans[(int(m2.group(2)), c1)] = c2
            for row in sorted(r for r in rowtext if r <= 9):
                for col, v in rowtext[row]:
                    node = first(B1, v)
                    if node:
                        for c in range(col, spans.get((row, col), col) + 1):
                            colnode[c] = node

        def split(r, key_of):
            """Parts of a one-column region by a key of each row: key -> counts, rows, fingerprint."""
            part = collections.OrderedDict()
            runs = []
            for piece in (r["ranges"] or "").split():
                m2 = re.findall(r"[A-Z]+(\d+)", piece)
                runs.append((int(m2[0]), int(m2[-1])))
            have = {row: (t, v) for row, t, v in db.execute("SELECT row, t, v FROM cells WHERE sheet_id=? AND col=? AND row BETWEEN ? AND ?",
                                                           (sid, r["col1"], r["row_min"], r["row_max"]))}
            for a2, b2 in runs:
                for row in range(a2, b2 + 1):
                    p2 = part.setdefault(key_of(row), dict(rows=[], n=0, n_blank=0, n_num=0, n_str=0, n_bool=0, h=hashlib.sha1()))
                    t, v = have.get(row, ("z", None))
                    blank = t == "z" or (t == "s" and not (v or "").strip())
                    p2["rows"].append(row); p2["n"] += 1
                    p2["n_blank"] += blank; p2["n_num"] += (t == "n" and not blank); p2["n_str"] += (t == "s" and not blank); p2["n_bool"] += t == "b"
                    p2["h"].update(repr((t, v)).encode())
            return part

        def add_parts(r, role, part, label_of, group_of_key, pre_of, common):
            n_first = len(recs)
            for key, p2 in part.items():
                rows = p2["rows"]
                add(sid, role, n=p2["n"], n_blank=p2["n_blank"], n_num=p2["n_num"], n_str=p2["n_str"], n_bool=p2["n_bool"],
                    n_req=p2["n"] if (r["n_req"] or 0) >= r["n"] else 0, label=label_of(key, rows), group=group_of_key(key), dv=r["dv_id"],
                    cells="%s%d:%s%d" % (L(r["col1"]), rows[0], L(r["col1"]), rows[-1]) + ("" if rows[-1] - rows[0] + 1 == len(rows) else "（うち %d セル）" % len(rows)),
                    vhash=p2["h"].hexdigest()[:16], regions=0, in_table=True, pre=pre_of(key), **common)
            recs[n_first]["regions"] = 1

        per_col = collections.Counter((r["role"], r["col1"]) for r in regs if r["role"] in ("I", "C") and r["col1"] == r["col2"])
        noisy = {k for k, n in per_col.items() if n > 15} if s["kind"] in ("composition", "analysis", "equip", "factor", "internal", "param") else set()
        merged = {}
        for r in regs:
            role = r["role"]
            if role in ("L", "F"):
                add(sid, role, n=r["n"], n_str=r["n"] if role == "L" else 0, n_patterns=r["n_patterns"],
                    cells="" if role == "L" else "%s%s:%s%s" % (L(r["col1"]), r["row_min"], L(r["col2"]), r["row_max"]), regions=1,
                    label="見出し・説明の文字列" if role == "L" else "数式")
                continue
            label = (r["left_label"] or "") if r["n"] < 3 and r["left_label"] else (r["header"] or r["left_label"] or "")
            common = dict(n_int=r["n_int"] or 0, unit=r["unit"] or "", numfmt=r["numfmt"] or "", header=r["header"] or "")
            one_col = r["col1"] == r["col2"]
            if (role, r["col1"]) in noisy and one_col:
                m = merged.get((role, r["col1"]))
                if m is None:
                    m = merged[(role, r["col1"])] = add(sid, role, label="", cells="%s列の %d 領域" % (L(r["col1"]), per_col[(role, r["col1"])]),
                                                        note="同じ列に小さな領域が多いため 1 行にまとめた", **common)
                    m["_h"] = hashlib.sha1(); m["_rows"] = [r["row_min"], r["row_max"]]; m["_labels"] = collections.Counter()
                for k in ("n", "n_blank", "n_num", "n_str", "n_bool"):
                    m[k] += r[k] or 0
                m["regions"] += 1
                m["_h"].update((r["vhash"] or "").encode()); m["_rows"] = [min(m["_rows"][0], r["row_min"]), max(m["_rows"][1], r["row_max"])]
                m["_labels"][label] += r["n"]
                continue
            in_table = bool(table_from and r["row_max"] >= table_from)
            if in_table and role in ("I", "C") and one_col:
                # main quantity table: split the column by the work-item group of each row
                part = split(r, lambda row: group_of(row) if row >= table_from else "（表の上）")
                add_parts(r, role, part, lambda key, rows: label, lambda key: key, lambda key: None, common)
                for rec in recs[-len(part):]:
                    rec["in_table"] = rec["group"] != "（表の上）"
                continue
            pre = None
            if rules and role in ("I", "C"):
                node = first(rules, label)
                if s["kind"] == "input_b67" and one_col and r["n"] >= 3 and node in (None, "operation.energy.annual_use"):
                    # table of energy carriers and utilities: the label on the left of each row says which one
                    texts = {}
                    def key_b67(row, node=node):
                        texts[row] = left_text(row, r["col1"])
                        return first(B67_ROWS, texts[row]) or first(B67, texts[row]) or node or ""
                    part = split(r, key_b67)
                    add_parts(r, role, part, lambda key, rows: texts.get(rows[0], ""), lambda key: "",
                              lambda key: (key, "行見出し") if key else None, common)
                    continue
                if node:
                    pre = (node, "見出し")
                elif r["col1"] in colnode and r["row_min"] >= 8 and r["row_max"] <= 38:
                    pre = (colnode[r["col1"]], "列見出し")
                elif one_col and r["n"] >= 3:
                    # no usable column header: classify each row by the label on its left
                    texts = {}
                    def key_of(row):
                        texts[row] = left_text(row, r["col1"])
                        return first(rules, texts[row]) or ""
                    part = split(r, key_of)
                    add_parts(r, role, part, lambda key, rows: texts.get(rows[0], ""), lambda key: "",
                              lambda key: (key, "行見出し") if key else None, common)
                    continue
                elif r["n"] < 3 and r["col1"] in colnode:
                    pre = (colnode[r["col1"]], "列見出し")
            add(sid, role, n=r["n"], n_blank=r["n_blank"] or 0, n_num=r["n_num"] or 0, n_str=r["n_str"] or 0, n_bool=r["n_bool"] or 0,
                n_req=r["n_req"] or 0, n_distinct=r["n_distinct"], uniform=r["uniform"] or 0, seq=r["seq"] or 0, label=label, dv=r["dv_id"],
                group=group_of(r["row_min"]) if in_table else "",
                cells=(r["ranges"] or "")[:120] + ("…" if len(r["ranges"] or "") > 120 else ""), vhash=r["vhash"] or "", regions=1,
                in_table=in_table, pre=pre, **common)
        for m in merged.values():
            m["vhash"] = m.pop("_h").hexdigest()[:16]
            rows = m.pop("_rows"); labels = m.pop("_labels")
            m["cells"] += "（%d～%d 行）" % tuple(rows)
            m["label"] = labels.most_common(1)[0][0] if labels else ""
            m["n_int"] = None

    # --- classification ------------------------------------------------------------------------------
    for rec in recs:
        s = sheets[rec["sheet_id"]]
        role = rec["role"]
        if role in ("L", "F"):
            rec["node"], rec["basis"] = s["default"] if s["kind"] != "unknown" else "review.unknown", "シート"
            if s["kind"].startswith("input"):
                rec["node"] = {"input_main": "construction.item_details", "input": "construction.item_details",
                               "input_b1": "equipment.refrigerant_equipment", "input_b67": "operation.energy"}[s["kind"]]
        else:
            dvtext = (dvs[rec["dv"]]["formula1"] or "") if rec["dv"] else ""
            if rec.get("pre"):
                rec["node"], rec["basis"] = rec["pre"]
            else:
                rec["node"], rec["basis"] = classify(s["base"], s["kind"], s["default"], role, rec["label"], rec["group"], dvtext, rec["in_table"])
        rec["kind"] = kind_of(s["kind"], role, rec)
        rec["dtype"] = type_of(rec, role)
        rec["unit"] = unit_of(rec["unit"], rec["header"], rec["numfmt"]) if role in ("I", "C") else ""
        inputs = s["kind"].startswith("input")
        rec["requirement"] = ("自動算出" if role == "F" else "必須" if (role == "I" and inputs and rec["n_req"]) else
                              "任意" if (role == "I" and (inputs or s["kind"] == "check")) else
                              "任意（既定値あり）" if (role == "C" and inputs) else "参照用")
        stage = {"input_main": "A1-A5, B2-B5, C1-C4", "input_b1": "B1", "input_b67": "B6, B7"}.get(s["kind"], "")
        found = sorted(set(m.group(0).replace(" ", "").replace("~", "～") for m in STAGE.finditer((rec["header"] or "") + " " + rec["label"])))
        rec["stage"] = ", ".join(found) if found else stage
        if role == "I" and rec["n"] == rec["n_blank"]:
            rec["status"], rec["review"] = "空欄等", ("空欄・未入力" if rec["node"].startswith("review") or rec["node"].endswith(".other") else "")
            if rec["node"] == "review.unknown":
                rec["node"] = "review.blank"
        elif rec["node"].startswith("review."):
            rec["status"], rec["review"] = "不明・未分類", "不明・未分類"
        elif rec["node"].endswith(".other"):
            rec["status"], rec["review"] = "その他", ""
        else:
            rec["status"], rec["review"] = "分類済み", ""

    # --- items that are not cells ------------------------------------------------------------------
    extra = []
    outside = collections.defaultdict(int)
    for r in db.execute("SELECT sheet_id, dv_id, n FROM dv_outside"):
        outside[r["dv_id"]] += r["n"]
    host = {}
    for rec in recs:
        if rec["dv"] and rec["dv"] not in host:
            host[rec["dv"]] = rec
    for dv_id, v in dvs.items():
        s = sheets[v["sheet_id"]]
        f1 = v["formula1"] or ""
        if f1.startswith('"'):
            desc = "選択リスト（直接指定 %d 択）" % (f1.count(",") + 1)
        elif "INDIRECT" in f1.upper():
            desc = "選択リスト（INDIRECT による可変の参照）"
        elif f1:
            desc = "選択リスト（セル範囲または名前の参照）"
        else:
            desc = "入力規則（種類の指定なし）"
        node = next((n for k, n in DV_RULES if k in f1), None) or (host[dv_id]["node"] if dv_id in host else None)
        if node is None and s["kind"] != "unknown":
            node = s["default"]                          # the list sits on cells that are not editable: classified by its sheet
        status = "分類済み" if node else "不明・未分類"
        sq = (v["sqref"] or "").split()
        note = "使用範囲の外に %d セル分の範囲指定がある（参照不明）" % outside[dv_id] if outside.get(dv_id) else ""
        extra.append(dict(sheet_id=v["sheet_id"], role="DV", n=0, label="入力規則", cells=" ".join(sq[:4]) + (" …（全 %d 範囲）" % len(sq) if len(sq) > 4 else ""),
                          node=node or "review.unknown", basis="入力規則" if node else "対象セル不明", kind="選択式の入力項目", dtype="選択リスト",
                          requirement="参照用", status=status, review="" if node else "不明・未分類", desc=desc, note=note, stage="", unit="", group=""))
    for sid, s in sheets.items():
        n = db.execute("SELECT COALESCE(SUM(n),0) FROM dv_outside WHERE sheet_id=?", (sid,)).fetchone()[0]
        if n:
            extra.append(dict(sheet_id=sid, role="DVX", n=0, label="入力規則の範囲（使用範囲の外）", cells="", node="review.broken_ref", basis="範囲の位置",
                              kind="内部処理・参照用の値", dtype="範囲指定", requirement="参照用", status="不明・未分類", review="参照不明・参照切れ",
                              desc="使用範囲の外を指す範囲指定 %d セル分（旧形式の折り返しに由来するとみられる）" % n, note="入力欄としては数えていない", stage="", unit="", group=""))
        n = db.execute("SELECT COUNT(*) FROM cells WHERE sheet_id=? AND f LIKE '%#REF!%'", (sid,)).fetchone()[0]
        if n:
            extra.append(dict(sheet_id=sid, role="FX", n=0, label="参照切れを含む数式", cells="", node="review.broken_ref", basis="数式の文字列",
                              kind="他の入力から自動計算される値", dtype="数式", requirement="自動算出", status="不明・未分類", review="参照不明・参照切れ",
                              desc="#REF! を含む数式 %d セル" % n, note="セル数は数式の行に含まれる（重複して数えない）", stage="", unit="", group=""))
        n = db.execute("SELECT COUNT(*) FROM cells WHERE sheet_id=? AND f LIKE '%[%]%'", (sid,)).fetchone()[0]
        if n:
            extra.append(dict(sheet_id=sid, role="FX", n=0, label="外部ブックを参照する数式", cells="", node="review.broken_ref", basis="数式の文字列",
                              kind="他の入力から自動計算される値", dtype="数式", requirement="自動算出", status="不明・未分類", review="参照不明・参照切れ",
                              desc="外部ブック参照を含む数式 %d セル" % n, note="参照先のブックは 6 ファイルに含まれない", stage="", unit="", group=""))
        n = db.execute("SELECT COUNT(*) FROM comments WHERE sheet_id=?", (sid,)).fetchone()[0]
        if n:
            extra.append(dict(sheet_id=sid, role="CM", n=0, label="セルのコメント", cells="", node="assessment.check.basis_notes", basis="種類",
                              kind="内部処理・参照用の値", dtype="文字列", requirement="参照用", status="分類済み", review="",
                              desc="コメント %d 件（内容は非掲載）" % n, note="", stage="", unit="", group=""))
    path_sheet = {(s["file_id"], s["path"]): sid for sid, s in sheets.items()}
    for r in db.execute("SELECT file_id, sheet_path, object_type, COUNT(*) n, SUM(fmla_link IS NOT NULL) linked FROM controls GROUP BY 1,2,3"):
        sid = path_sheet.get((r["file_id"], r["sheet_path"]))
        button = r["object_type"] == "Button"
        extra.append(dict(sheet_id=sid, role="CT", n=0, label="フォーム部品（%s）" % r["object_type"], cells="", node="assessment.display.display_options",
                          basis="種類", kind="内部処理・参照用の値" if button else "選択式の入力項目", dtype="ボタン" if button else "真偽",
                          requirement="任意", status="分類済み", review="",
                          desc="%s %d 個（リンク先セルの指定 %d 個）" % ("マクロ起動ボタン" if button else "チェックボックス", r["n"], r["linked"] or 0),
                          note="結果の表示切替とみられる。リンク先セルが定義にないため、対応する値の位置は未確認" if not button else "マクロの内容は未調査",
                          stage="", unit="", group=""))
    first_sheet = {}
    for sid, s in sheets.items():
        first_sheet.setdefault(s["file_id"], sid)
    name_sheet = {(s["file_id"], s["name"]): sid for sid, s in sheets.items()}
    for r in db.execute("SELECT file_id, name, local_sheet, hidden, refers_to FROM names"):
        ref = r["refers_to"] or ""
        m = re.match(r"'?([^'!]+)'?!", ref)
        sid = name_sheet.get((r["file_id"], m.group(1))) if m else None
        broken = "#REF!" in ref
        s = sheets.get(sid)
        extra.append(dict(sheet_id=sid or first_sheet[r["file_id"]], role="NM", n=0, label="名前定義：" + (r["name"] or "")[:28], cells="" if broken or not m else ref.split("!")[-1][:40],
                          node="review.broken_ref" if broken else (s["default"] if s and s["kind"] != "unknown" else "review.purpose_unknown"),
                          basis="参照先" if not broken else "参照先なし", kind="内部処理・参照用の値", dtype="名前定義", requirement="参照用",
                          status="不明・未分類" if broken or not s else "分類済み",
                          review="参照不明・参照切れ" if broken else ("" if s else "用途不明"),
                          desc="名前定義（%s%s）" % ("参照切れ #REF!" if broken else "参照先あり", "・非表示" if r["hidden"] else ""),
                          note="" if sid else "参照先のシートを特定できない", stage="", unit="", group="", no_sheet=sid is None))
    for fid, has_vba in db.execute("SELECT id, has_vba FROM files"):
        if has_vba:
            extra.append(dict(sheet_id=first_sheet[fid], role="VB", n=0, label="VBA マクロ", cells="", node="review.unknown", basis="未調査",
                              kind="内部処理・参照用の値", dtype="マクロ", requirement="参照用", status="不明・未分類", review="不明・未分類",
                              desc="vbaProject.bin あり（内容は読んでいない）", note="調査できなかった範囲", stage="", unit="", group="", no_sheet=True))

    # --- duplicates ---------------------------------------------------------------------------------
    order = sorted(range(len(recs)), key=lambda i: (sheets[recs[i]["sheet_id"]]["file_id"], sheets[recs[i]["sheet_id"]]["idx"]))
    seen = {}
    for i in order:
        rec = recs[i]
        if rec["role"] not in ("I", "C", "TD") or not rec["vhash"]:
            continue
        key = (sheets[rec["sheet_id"]]["base"], rec["role"], rec["cells"], rec["group"], rec["vhash"])
        if key in seen:
            rec["dup_of"] = seen[key]
        else:
            seen[key] = i

    # --- store ----------------------------------------------------------------------------------------
    db.executescript("""DROP TABLE IF EXISTS inventory;
    CREATE TABLE inventory (id INTEGER PRIMARY KEY, inv TEXT, file_id INTEGER, sheet_id INTEGER, sheet TEXT, state TEXT, skind TEXT, role TEXT,
        node TEXT, basis TEXT, status TEXT, review TEXT, kind TEXT, dtype TEXT, unit TEXT, requirement TEXT, stage TEXT, cells TEXT, n INTEGER,
        n_blank INTEGER, n_values INTEGER, grp TEXT, label TEXT, header TEXT, descr TEXT, note TEXT, dup_of TEXT, regions INTEGER, n_req INTEGER);""")
    rows = []
    for i, rec in enumerate(recs):
        s = sheets[rec["sheet_id"]]
        role = rec["role"]
        if role == "I":
            descr = "入力セル %d 個（値あり %d、空欄 %d）" % (rec["n"], rec["n"] - rec["n_blank"], rec["n_blank"])
            if rec["dv"]:
                descr += "・選択リストあり"
        elif role == "C":
            descr = "定数 %d 個" % rec["n"] + ("・すべて同じ値" if rec["uniform"] else "") + ("・連番" if rec["seq"] else "")
        elif role == "TD":
            descr = "文字列 %d 個" % rec["n"] + ("（%d 種）" % rec["n_distinct"] if rec["n_distinct"] else "")
        elif role == "F":
            descr = "数式 %d セル（式の型 %s 種）" % (rec["n"], rec["n_patterns"])
        else:
            descr = "見出し・説明の文字列 %d 個" % rec["n"]
        rows.append((i + 1, "INV-%06d" % (i + 1), s["file_id"], rec["sheet_id"], s["name"], s["state"], s["kind"], role, rec["node"], rec["basis"],
                     rec["status"], rec["review"], rec["kind"], rec["dtype"], rec["unit"], rec["requirement"], rec["stage"], rec["cells"], rec["n"],
                     rec["n_blank"], rec["n"] - rec["n_blank"], rec["group"], rec["label"], rec["header"], descr, rec["note"],
                     "INV-%06d" % (rec["dup_of"] + 1) if "dup_of" in rec else "", rec["regions"], rec["n_req"]))
    base = len(rows)
    for j, e in enumerate(extra):
        s = sheets[e["sheet_id"]]
        rows.append((base + j + 1, "INV-%06d" % (base + j + 1), s["file_id"], e["sheet_id"], "" if e.get("no_sheet") else s["name"],
                     "" if e.get("no_sheet") else s["state"], s["kind"], e["role"], e["node"], e["basis"], e["status"], e["review"], e["kind"],
                     e["dtype"], e["unit"], e["requirement"], e["stage"], e["cells"], 0, 0, 0, e["group"], e["label"], "", e["desc"], e["note"], "", 0, 0))
    db.executemany("INSERT INTO inventory VALUES (%s)" % ",".join("?" * 29), rows)
    db.commit()
    bad = [r["node"] for r in db.execute("SELECT DISTINCT node FROM inventory") if r["node"] not in nodes]
    print("records", len(rows), "unknown node ids:", bad)

    # --- reconciliation -----------------------------------------------------------------------------
    scan = dict(F=db.execute("SELECT COUNT(*) FROM cells WHERE t='f'").fetchone()[0],
                regions={r[0]: (r[1], r[2]) for r in db.execute("SELECT role, COUNT(*), SUM(n) FROM regions GROUP BY role")})
    inv = {r[0]: (r[1], r[2], r[3]) for r in db.execute("SELECT role, COUNT(*), SUM(n), SUM(regions) FROM inventory GROUP BY role")}
    ok = True
    for role, (k, n) in scan["regions"].items():
        got = inv.get(role, (0, 0, 0))
        same = got[1] == n and (got[2] == k)
        ok &= same
        print("  role %-2s regions %6d cells %8d | inventory rows %6d cells %8d regions covered %6d  %s" % (role, k, n, got[0], got[1], got[2], "OK" if same else "MISMATCH"))
    counts = {"validations": ("DV", "SELECT COUNT(*) FROM validations"), "names": ("NM", "SELECT COUNT(*) FROM names")}
    for name, (role, sql) in counts.items():
        a, b = db.execute(sql).fetchone()[0], inv.get(role, (0,))[0]
        ok &= a == b
        print("  %-12s scanned %5d | inventory rows %5d  %s" % (name, a, b, "OK" if a == b else "MISMATCH"))
    print("reconciliation:", "OK" if ok and not bad else "FAILED")
    return 0 if ok and not bad else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
