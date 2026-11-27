"""Build de_ch.csv from ÖKOBAUDAT selection JSON and the KBOB v9.0 Excel."""
import csv, json, sys
import openpyxl

DL = sys.argv[1]  # downloads/de_ch dir
OUT = sys.argv[2]
RET = "2026-11-27"

HEADER = "factor_key,item,category,value,unit,declared_unit,ghg_basis,modules,region,technology_or_route,reference_year,data_type,source_org,source_title,edition_version,url,retrieved,licence_name,licence_url,cite_single_value,research_use,db_incorporation,commercial_use,redistribution,rights_class,notes".split(",")
rows = []

# ---------------- ÖKOBAUDAT ----------------
OBD_LIC = dict(
    licence_name="ÖKOBAUDAT Nutzungsbedingungen (BMWSB): data provided free of charge and without restriction; unmodified free-of-charge redistribution allowed with source attribution; dataset licenseType 'Free of charge for all users and uses' (not a standard open licence)",
    licence_url="https://www.oekobaudat.de/anleitungen/datennutzer.html",
    cite_single_value="yes", research_use="yes", db_incorporation="yes", commercial_use="yes", redistribution="yes",
    rights_class="2")
EXPORT_URL = "https://www.oekobaudat.de/OEKOBAU.DAT/resource/datastocks/bca3670a-8dcf-44d0-be1f-0633d9ba1a75/exportCSV"
margins = {}
for l in open(f"{DL}/obd_margins.txt", encoding="utf-8"):
    p = l.split(" | ")
    u, m = (p[0].split() + [""])[:2]
    margins[u] = (m, p[1].strip() if len(p) > 1 else "")

DT = {"generic dataset": "generic (conservative, ÖKOBAUDAT/BBSR-commissioned, Sphera MLC background)",
      "average dataset": "industry-average EPD (association/multi-plant)",
      "representative dataset": "representative average dataset (national average)",
      "template dataset": "template EPD (association, worst-case/representative product)",
      "specific dataset": "product-specific EPD"}

for o in json.load(open(f"{DL}/obd_selected.json", encoding="utf-8")):
    if o.get("missing"):
        continue
    unit_ref = f"{o['Bezugsgroesse']} {o['Bezugseinheit']}".replace("0.999999999999999 kg", "1 kg").replace("0.999999999999998", "1").replace("0.999999999999997", "1")
    notes = []
    if o["UUID"].startswith("87371640"):
        unit_ref = "1 t"
        notes.append("CSV lists Bezugsgroesse '1 kg' but the reference flow is '1 t Zement' (conversion factor to 1 kg = 0.001); value is per tonne")
    if unit_ref == "3.6 MJ":
        notes.append("3.6 MJ = 1 kWh final energy")
    if unit_ref == "1000 kgkm":
        notes.append("1000 kgkm = 1 tkm")
    dens = o["Rohdichte (kg/m3)"] or o["Schuettdichte (kg/m3)"]
    if dens: notes.append(f"density {dens} kg/m3")
    if o["Flaechengewicht (kg/m2)"]: notes.append(f"areal mass {o['Flaechengewicht (kg/m2)']} kg/m2")
    if o["Laengengewicht (kg/m)"]: notes.append(f"linear mass {o['Laengengewicht (kg/m)']} kg/m")
    if o["Stueckgewicht (kg)"]: notes.append(f"unit mass {o['Stueckgewicht (kg)']} kg")
    if o["Umrechungsfaktor auf 1kg"] and not o["UUID"].startswith("87371640"):
        notes.append(f"conversion factor to 1 kg {o['Umrechungsfaktor auf 1kg']}")
    if o["biogener Kohlenstoffgehalt in kg"]: notes.append(f"biogenic carbon content {o['biogener Kohlenstoffgehalt in kg']} kg C per declared unit")
    m, lic = margins.get(o["UUID"], ("", ""))
    if m != "": notes.append(f"safety margin (Sicherheitszuschlag) {m}% per dataset XML")
    if lic: notes.append(f"dataset licenseType: {lic}")
    if o["Szenario"]: notes.append(f"scenario {o['Szenario']} {o['Szenariobeschreibung']}".strip())
    owner = o["Declaration owner"]
    if o["Registrierungsnummer"]: notes.append(f"EPD reg. no. {o['Registrierungsnummer']}")
    notes.append(f"dataset '{o['Name (de)']}' UUID {o['UUID']} v{o['Version']}; value read from ÖKOBAUDAT 2024-III CSV export {EXPORT_URL}")
    notes.append(f"GWP-fossil {o['GWPfossil']}; GWP-biogenic {o['GWPbiogenic']}; GWP-luluc {o['GWPluluc']}")
    if o["UUID"].startswith("1fd9f4eb"):
        notes.append("NOTE this dataset declares licenseType 'Free of charge for some user types or use types' - check before incorporation")
    lic_fields = dict(OBD_LIC)
    if o["UUID"].startswith("1fd9f4eb"):
        lic_fields.update(db_incorporation="unknown", commercial_use="unknown", rights_class="4")
    bg = o["Hintergrunddatenbank(en)"].split("(")[0].strip(" '")
    base = dict(
        factor_key=o["key"], item=o["item"], category=o["cat"], unit="kg CO2e/" + unit_ref, declared_unit=unit_ref,
        region=o["Laenderkennung"], technology_or_route=f"{o['Name (de)']} ({o['Name (en)']}); background DB: {bg}",
        reference_year=f"{o['Referenzjahr']} (valid until {o['Gueltig bis']})", data_type=DT.get(o["Typ"], o["Typ"]),
        source_org=("BMWSB/BBSR ÖKOBAUDAT; data owner: " + owner) if owner else "BMWSB/BBSR ÖKOBAUDAT",
        source_title="ÖKOBAUDAT - " + o["Name (de)"], edition_version=f"ÖKOBAUDAT 2024-III (release 13.11.2026), {o['Konformitaet']}",
        url=o["URL"], retrieved=RET, **lic_fields)
    gb = "GWP-total, EN 15804+A2 (EF 3.x, IPCC AR5 GWP100 based), -1/+1 biogenic carbon accounting"
    rows.append(dict(base, value=o["GWPtotal"], ghg_basis=gb, modules=o["module"], notes="; ".join(notes)))
    if o["bio"]:
        rows.append(dict(base, value=o["GWPfossil"], ghg_basis="GWP-fossil, EN 15804+A2", modules=o["module"],
                         notes="fossil part only (excl. biogenic CO2 uptake/release); " + "; ".join(notes[-2:])))
        rows.append(dict(base, value=o["GWPbiogenic"], ghg_basis="GWP-biogenic, EN 15804+A2 (-1/+1)", modules=o["module"],
                         notes="biogenic CO2 (negative = uptake in A1-A3, positive = release in C3); " + "; ".join(notes[-2:])))

# ---------------- KBOB ----------------
KB_URL = "https://www.kbob.admin.ch/dam/de/sd-web/GUOl1trUNEVH/%C3%96kobilanzdaten_im_Baubereich_V9.0.xlsx"
KB_LIC = dict(
    licence_name="admin.ch copyright notice (Bundesbehörden der Schweizerischen Eidgenossenschaft): content publicly accessible, no rights transferred, prior written consent required for reproduction; KBOB/ecobau/IPB disclaimer in Excel",
    licence_url="https://www.admin.ch/gov/de/start/rechtliches.html",
    cite_single_value="yes", research_use="yes", db_incorporation="no", commercial_use="unknown", redistribution="no",
    rights_class="3")
KB_GHG = "THG-Emissionen kg CO2-eq, IPCC 2013 (AR5) GWP100 (specific CF for aviation); biogenic CO2 treated as climate-neutral (no uptake credit, no release) - comparable to GWP-fossil+luluc, NOT GWP-total"
wb = openpyxl.load_workbook(f"{DL}/KBOB_Oekobilanzdaten_V9.0.xlsx", read_only=True, data_only=True)

def sheet_index(name):
    d = {}
    for r in wb[name].iter_rows(values_only=True):
        if isinstance(r[0], float):
            d[f"{r[0]:.3f}"] = r
        elif r[0] is not None and isinstance(r[0], str) and r[0].count(".") >= 1:
            d[r[0].strip()] = r
    return d

MAT = sheet_index("Baumaterialien Matériaux")
GT = sheet_index("Gebäudetechnik Technique")
EN = sheet_index("Energie Énergie")
TR = sheet_index("Transporte Transports")
EG = sheet_index("Entsorgung Déchets")

def kb(base_key, item, cat, sheet, kid, value, modules, unit_ref, notes, ghg=KB_GHG, tech=None):
    rows.append(dict(factor_key=base_key, item=item, category=cat, value=value, unit=f"kg CO2-eq/{unit_ref}", declared_unit=unit_ref,
                     ghg_basis=ghg, modules=modules, region="CH", technology_or_route=tech or "",
                     reference_year="KBOB/ecobau-Liste 2009/1:2022 (background UVEK LCI DQRv2:2022)",
                     data_type="generic average, Swiss market (KBOB/ecobau/IPB)", source_org="KBOB / ecobau / IPB (Plattform Ökobilanzdaten im Baubereich)",
                     source_title=f"Ökobilanzdaten im Baubereich - {sheet} - ID {kid}", edition_version="KBOB/ecobau-Liste 2022, Version 9.0 (XLSX dated 14 July 2026)",
                     url=KB_URL, retrieved=RET, notes=notes, **KB_LIC))

HERST = "Herstellung (cradle-to-gate, ~A1-A3 incl. packaging; excl. transport to site)"
ENTS = "Entsorgung (end-of-life ~C1-C4 per Swiss disposal routes; no module D credit)"
# materials: (key, KBOB id, item)
MATS = [
 ("concrete_ready_mix_generic", "01.002", "Building concrete (Hochbaubeton), without reinforcement"),
 ("concrete_ready_mix_civil", "01.003", "Civil-engineering concrete (Tiefbaubeton), without reinforcement"),
 ("concrete_lean", "01.001", "Lean concrete, without reinforcement"),
 ("concrete_precast", "01.042", "Precast concrete element, normal concrete, ex works"),
 ("brick", "02.001", "Clay brick (Backstein)"),
 ("brick_sand_lime", "02.002", "Sand-lime brick (Kalksandstein)"),
 ("float_glass", "03.006", "Flat glass, uncoated"),
 ("gypsum_plasterboard", "03.008", "Gypsum plasterboard (Gipskartonplatte)"),
 ("gypsum_fibreboard", "03.007", "Gypsum fibreboard"),
 ("ceramic_tiles", "03.010", "Ceramic / stoneware tile (per kg)"),
 ("ceramic_tiles", "11.008", "Ceramic / stoneware floor tile 9 mm (per m2)"),
 ("igu_double", "05.001", "Insulating glazing double, Ug 1.1, 24 mm"),
 ("igu_triple", "05.003", "Insulating glazing triple, Ug 0.5, 36 mm"),
 ("igu_triple", "05.012", "Insulating glazing triple, Ug 0.6, 40 mm"),
 ("window_frame_aluminium", "05.004", "Window frame aluminium (frame share ~ per m2 frame area)"),
 ("window_frame_pvc", "05.007", "Window frame PVC"),
 ("window_frame_timber", "05.005", "Window frame timber"),
 ("aluminium_sheet", "06.001", "Aluminium sheet, bare"),
 ("aluminium_extrusion", "06.002", "Aluminium profile, bare"),
 ("rebar", "06.003", "Reinforcing steel (Armierungsstahl)"),
 ("steel_sheet", "06.010", "Steel sheet, bare"),
 ("steel_sheet_galvanised", "06.011", "Steel sheet, galvanised"),
 ("steel_section", "06.012", "Steel section, bare"),
 ("copper_sheet", "06.008", "Copper sheet, bare"),
 ("stainless_steel_sheet", "06.004", "Chromium-nickel steel sheet 18/8, bare"),
 ("glulam", "07.003", "Glued laminated timber (Brettschichtholz)"),
 ("clt", "07.020", "Cross-laminated timber (Brettsperrholz)"),
 ("timber_sawn_softwood", "07.009", "Solid softwood spruce/fir/larch, air-dried, rough"),
 ("timber_sawn_softwood_planed", "07.011", "Solid softwood spruce/fir/larch, kiln-dried, planed"),
 ("timber_sawn_softwood_kvh", "07.023", "Structural solid timber (Konstruktionsvollholz)"),
 ("mineral_wool_glass", "10.001", "Glass wool"),
 ("mineral_wool_stone", "10.008", "Stone wool"),
 ("eps", "10.004", "Expanded polystyrene (EPS)"),
 ("xps", "10.005", "Extruded polystyrene (XPS)"),
 ("pur_pir", "10.006", "Polyurethane (PUR/PIR)"),
 ("pipe_pe", "13.002", "Pipe, polyethylene (PE)"),
 ("pipe_pvc", "13.004", "Pipe, polyvinyl chloride (PVC)"),
 ("paint_wall_dispersion", "14.001", "Paint, water-borne, 2 coats (per m2)"),
 ("screed_cement", "04.006", "Cement screed 85 mm"),
]
TIMBER = {"07.003", "07.020", "07.009", "07.011", "07.023", "05.005"}
for key, kid, item in MATS:
    r = MAT[kid]
    name, dens, ref = r[2], r[5], r[6]
    tot, h, e, bc = r[25], r[26], r[27], r[28]
    nn = f"KBOB name '{name}' (ID {kid}, UUID {r[1]}); density/areal mass {dens} ({'kg/m3' if ref=='kg' else 'kg/m2' if ref=='m2' else ''}); total Herstellung+Entsorgung = {tot}"
    kb(key, item, "material", "Baumaterialien", kid, h, HERST, ref, nn, tech=name)
    kb(key, item + " - end of life", "waste", "Baumaterialien", kid, e, ENTS, ref, nn + f"; disposal via KBOB route ID {r[3]} ({r[4]})", tech=name)
    if kid in TIMBER:
        rows.append(dict(rows[-2], item=item + " - biogenic carbon content", value=bc, unit=f"kg C/{ref}", ghg_basis="biogenic carbon content (kg C, not CO2), EN 15804+A2 definition; KBOB reports no negative emissions",
                         modules="content in product", notes=nn + "; multiply by 44/12 for kg CO2 stored"))

# cement: not in KBOB
rows.append(dict(factor_key="cement_cem_i", item="Cement CEM I (KBOB)", category="material", value="", unit="", declared_unit="", ghg_basis="",
                 modules="A1-A3", region="CH", technology_or_route="", reference_year="", data_type="", source_org="KBOB / ecobau / IPB",
                 source_title="Ökobilanzdaten im Baubereich v9.0", edition_version="KBOB/ecobau-Liste 2022, Version 9.0", url=KB_URL, retrieved=RET,
                 notes="not published: KBOB list has no separate cement position (cement only embedded in concrete/mortar items); alternative: KBOB Betonsortenrechner https://rechner.pawis.ch/ or ÖKOBAUDAT/VDZ CEM I row in this file", **KB_LIC))
rows.append(dict(rows[-1], factor_key="concrete_ready_mix_c30_37", item="Ready-mix concrete by strength class (KBOB)",
                 notes="not published by strength class: KBOB gives Hochbaubeton/Tiefbaubeton averages per kg (plus manufacturer NPK A/B/C mixes); strength-class values via KBOB Betonsortenrechner https://rechner.pawis.ch/ (not downloaded)"))

GTS = [
 ("heat_pump_air_water", "31.019", "Air-water heat pump 7 kW (per unit)"),
 ("heat_pump_air_water", "31.020", "Air-water heat pump 7 kW (per kg)"),
 ("heat_pump_ground_source", "31.017", "Brine-water heat pump 7 kW (per unit)"),
 ("borehole_heat_exchanger", "31.016", "Borehole heat exchanger for brine-water heat pump (per m)"),
 ("heat_generator_per_m2", "31.002", "Heat generator, specific heat load 30 W/m2 (per m2 EBF)"),
 ("heat_distribution_residential", "31.021", "Heat distribution, residential (per m2 EBF)"),
 ("radiators", "31.023", "Heat emission via radiators (per m2 EBF)"),
 ("underfloor_heating", "31.024", "Heat emission via underfloor heating (per m2 EBF)"),
 ("ventilation_system_per_m2", "32.005", "Ventilation system, 2 m3/h per m2 EBF (per m2 EBF)"),
 ("ventilation_system_per_m2", "32.001", "Residential ventilation system, sheet-metal ducts (per m2 EBF)"),
 ("ventilation_unit", "32.010", "Single-room ventilator window model 10-30 m3/h (per unit)"),
 ("sanitary_installation_per_m2", "33.003", "Sanitary installation, residential, incl. fixtures and pipes (per m2 EBF)"),
 ("sanitary_installation_per_m2", "33.001", "Sanitary installation, office simple (per m2 EBF)"),
 ("electrical_installation_per_m2", "34.001", "Electrical installation, residential (per m2 EBF)"),
 ("electrical_installation_per_m2", "34.002", "Electrical installation, office (per m2 EBF)"),
 ("pv_system", "34.024", "PV system, market mix (per kWp)"),
 ("pv_system", "34.028", "PV system pitched roof, small, mono-Si (per kWp)"),
 ("pv_panel", "34.027.09", "PV panel mono-Si facade, Eternit Sunskin 18% (per m2 panel)"),
 ("pv_inverter", "34.033", "Inverter 5 kW (per kWp)"),
 ("battery_li_ion", "34.038", "Li-ion battery 20 kWh, 30 a service life (per kWh capacity)"),
]
for key, kid, item in GTS:
    r = GT[kid]
    name, basis, ref, tot, h, e = r[2], r[5], r[6], r[19], r[20], r[21]
    nn = f"KBOB name '{name}' (ID {kid}, UUID {r[1]}); reference basis: {basis}; EBF = Energiebezugsfläche (heated floor area, SIA 380/1)"
    if e == "inkl.":
        nn += "; Herstellung includes take-back and recycling (Entsorgung 'inkl.')"
    kb(key, item, "equipment", "Gebäudetechnik", kid, h, HERST, ref, nn, tech=name)
    if e not in (None, "inkl."):
        kb(key, item + " - end of life", "equipment", "Gebäudetechnik", kid, e, ENTS, ref, nn, tech=name)

ENS = [
 ("grid_electricity_ch", "45.020", "Electricity CH consumer mix (Verbrauchermix)"),
 ("grid_electricity_ch_production", "45.019", "Electricity CH production mix"),
 ("grid_electricity_ch_supplier", "45.025", "Electricity CH supplier mix (HKN)"),
 ("grid_electricity_entsoe", "45.021", "Electricity ENTSO-E mix"),
 ("natural_gas", "41.002", "Natural gas (final energy)"),
 ("heating_oil", "41.001", "Heating oil EL (final energy)"),
 ("wood_pellets", "41.008", "Wood pellets (final energy)"),
 ("district_heating_ch", "42.016", "District heating, average Swiss networks"),
 ("heat_boiler_gas", "43.002", "Useful heat, natural gas boiler"),
 ("heat_heat_pump_air_new", "44.009", "Useful heat, air-water heat pump new build JAZ 4.4, CH electricity"),
 ("pv_electricity_ch", "45.011", "Electricity from PV, market mix (grid)"),
]
for key, kid, item in ENS:
    r = EN[kid]
    name, basis, ref, thg = r[2], r[3], r[4], r[10]
    nn = f"KBOB name '{name}' (ID {kid}, UUID {r[1]}); basis {basis}; supply chain incl. combustion (Scope 1-3)"
    if kid.startswith("41"):
        nn += "; fuel kWh based on upper heating value (Brennwert/GCV) per KBOB footnote"
    if kid == "41.001": nn += "; Scope-1 combustion only per CH GHG inventory 2022: 0.26532 kg CO2/kWh (KBOB page)"
    if kid == "41.002": nn += "; Scope-1 combustion only per CH GHG inventory 2022: 0.2016 kg CO2/kWh (KBOB page)"
    kb(key, item, "energy", "Energie", kid, thg, "use stage energy supply (B6), well-to-tank + combustion (life-cycle)", ref, nn, tech=name)
TRS = [
 ("transport_truck_tkm", "62.016", "Truck, average"),
 ("transport_truck_tkm_32_40t", "62.010", "Truck 32-40 t"),
 ("transport_rail_tkm", "62.003", "Freight train"),
 ("transport_sea_tkm", "62.005", "Ocean ship"),
 ("transport_barge_tkm", "62.002", "Inland barge"),
]
for key, kid, item in TRS:
    r = TR[kid]
    name, basis, ref, tot, op, veh, inf = r[2], r[3], r[4], r[21], r[22], r[23], r[24]
    nn = f"KBOB name '{name}' (ID {kid}, UUID {r[1]}); total = operation {op} + vehicle {veh} + infrastructure {inf}"
    kb(key, item, "transport", "Transporte", kid, tot, "A4/C2 transport (operation incl. fuel chain + vehicle + infrastructure)", ref, nn, tech=name)

EGS = [
 ("waste_concrete", "91.060", "Disposal, concrete"),
 ("waste_rebar", "91.142", "Disposal, reinforcing steel"),
 ("waste_steel", "91.143", "Disposal, steel"),
 ("waste_timber_solid", "91.052", "Disposal, solid wood"),
 ("waste_glulam", "91.047", "Disposal, glued laminated timber"),
 ("waste_mineral_insulation", "91.173", "Disposal, mineral insulation"),
 ("waste_eps", "91.028", "Disposal, organic insulation polystyrene"),
 ("waste_pur", "91.039", "Disposal, polyurethane insulation"),
 ("waste_gypsum_board", "91.064", "Disposal, gypsum plasterboard"),
 ("waste_flat_glass", "91.032", "Disposal, flat glass"),
 ("waste_brick", "91.138", "Disposal, brick"),
 ("waste_pipe_pvc", "91.040", "Disposal, PVC pipes"),
 ("waste_pipe_pe_pp", "91.174", "Disposal, PE or PP pipes"),
 ("waste_pv_module", "92.037", "Take-back and recycling, c-Si PV module"),
 ("waste_heat_pump", "92.012", "Disposal, air-water heat pump 7 kW (per unit)"),
]
for key, kid, item in EGS:
    r = EG[kid]
    name, ref, thg = r[2], r[3], r[16]
    nn = f"KBOB name '{name}' (ID {kid}, UUID {r[1]}); same value as the Entsorgung column of the corresponding material/technique row"
    kb(key, item, "waste", "Entsorgung", kid, thg, ENTS, ref, nn, tech=name)

# ---------------- not obtained / gaps ----------------
GAPS = [
 ("copper_pipe", "Copper pipe", "material", "ÖKOBAUDAT 2024-III generic datasets contain only 'End of life - Kupferrohr' (C2-C4/D) and 'Kupferbleche'; no A1-A3 copper pipe dataset found in CSV; KBOB v9.0 has only copper sheet (06.008)", "ÖKOBAUDAT 2024-III CSV export / KBOB v9.0", EXPORT_URL, "alternative: European Copper Institute / KME / Wieland copper tube EPDs (ibu-epd.com), or ÖKOBAUDAT 'Kupferbleche' as proxy"),
 ("concrete_ready_mix_c35_45", "Ready-mix concrete C35/45 (ÖKOBAUDAT generic)", "material", "no generic ÖKOBAUDAT dataset for C35/45 (generic only C20/25, C25/30, C30/37, C50/60 + recycled); IZB average C35/45 provided instead", "ÖKOBAUDAT 2024-III CSV export", EXPORT_URL, "IZB 'Beton der Druckfestigkeitsklasse C35/45' row in this file"),
 ("cement_cem_i", "Cement CEM I (ÖKOBAUDAT generic)", "material", "no generic CEM I dataset in ÖKOBAUDAT 2024-III (generic only CEM II, CEM III, CEM IV); VDZ average CEM I EPD provided instead", "ÖKOBAUDAT 2024-III CSV export", EXPORT_URL, "VDZ 'Portlandzement CEM I' row in this file"),
]
for key, item, cat, reason, title, url, alt in GAPS:
    rows.append(dict(factor_key=key, item=item, category=cat, value="", unit="", declared_unit="", ghg_basis="", modules="A1-A3", region="DE/CH",
                     technology_or_route="", reference_year="", data_type="", source_org="BMWSB/BBSR ÖKOBAUDAT; KBOB", source_title=title,
                     edition_version="ÖKOBAUDAT 2024-III; KBOB v9.0", url=url, retrieved=RET, notes=f"not obtained: {reason}; alternative: {alt}", **OBD_LIC))

with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=HEADER)
    w.writeheader()
    for r in rows:
        r = {k: ("" if r.get(k) is None else r.get(k)) for k in HEADER}
        w.writerow(r)
print(len(rows), "rows;", sum(1 for r in rows if str(r.get("value", "")) != ""), "with values")
