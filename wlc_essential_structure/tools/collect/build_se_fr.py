import csv, sys, os
from decimal import Decimal
import openpyxl

BASE = sys.argv[1]  # coef dir
DL = os.path.join(BASE, 'downloads', 'se_fr')
OUT = os.path.join(BASE, 'out', 'se_fr.csv')
RET = '2026-11-27'

HDR = 'factor_key,item,category,value,unit,declared_unit,ghg_basis,modules,region,technology_or_route,reference_year,data_type,source_org,source_title,edition_version,url,retrieved,licence_name,licence_url,cite_single_value,research_use,db_incorporation,commercial_use,redistribution,rights_class,notes'.split(',')

def num(v):
    if v is None or v == '':
        return ''
    if isinstance(v, str):
        v = v.strip().replace(',', '.')
    d = Decimal(str(v))
    s = format(d.normalize(), 'f')
    return s

rows = []

# ---------------- Boverket ----------------
BOV_URL = 'https://www.boverket.se/contentassets/4668ed4cc3da447385788ed30bff7d49/boverkets-climate-database-version-02.07.000-en-gb.xlsx'
BOV_PAGE = 'https://www.boverket.se/sv/om-boverket/oppna-data/boverkets-klimatdatabas/'
BOV_LIC = 'Boverket Anvandarvillkor - Licens for anvandning av Boverkets oppna data om klimatdata (dnr 5913/2024; adapted Svensk API-licens)'
BOV_LIC_URL = 'https://www.boverket.se/contentassets/eb39a37752af4f74a61ccf92ac21cd5b/anvandarvillkor-for-oppna-data-for-boverkets-klimatdatabas.pdf'
BOV_LIC_NOTE = ('Licence: non-exclusive licence; "anyone may freely use the content", incl. in own products/services; Boverket must be cited as source; '
                'clause 3.2: other uses need written approval; bulk re-publication of the raw dataset not explicitly addressed (confirm with registraturen@boverket.se).')
BOV_GHG = 'GWP-GHG (EN 15804+A2 indicator) kg CO2e'

wb = openpyxl.load_workbook(os.path.join(DL, 'boverket_climate_database_02.07.000_en-gb.xlsx'), data_only=True)
ws = wb.active
hdr = [c.value for c in ws[1]]
bov = {}
for r in ws.iter_rows(min_row=2, values_only=True):
    bov[r[0]] = dict(zip(hdr, r))

def bov_row(key, rid, kind, cat='material', extra_note=''):
    d = bov[rid]
    name = d['Product name'].strip()
    unit = d['Unit for climate impact']
    du = unit.split('/')[-1]
    conv = ''
    if d.get('Conversion factor'):
        conv = f"conversion factor {num(d['Conversion factor'])} {d['Unit for conversion factor']}"
    base_note = f"Boverket resource ID {rid}; {conv}; " if conv else f"Boverket resource ID {rid}; "
    if kind == 'cons':
        val = d['A1-A3 resources climate impact, conservative value']; mods = 'A1-A3'
        dt = 'conservative default (typical value x 1.25)'
        n = base_note + f"conservative factor {num(d['A1-A3 conservative factor'])}; typical value {num(d[chr(65)+'1-A3 building product' + chr(39) + 's climate impact GWP-GHG, typical value'])}; mandatory generic value for Swedish climate declarations when no EPD is used"
    elif kind == 'typ':
        val = d["A1-A3 building product's climate impact GWP-GHG, typical value"]; mods = 'A1-A3'
        dt = 'generic average (typical value)'
        n = base_note + 'typical (average) value from Nordic/European EPDs; Boverket states the conservative value is 25 % higher'
    elif kind == 'a4':
        val = d['A4 transport climate impact GWP-GHG']; mods = 'A4'
        dt = 'generic default (transport scenario)'
        legs = []
        for lab in ['Last mile', 'From factory to construction site', 'Import transport to border/warehouse', 'From factory to warehouse/retailer', 'From border/warehouse to retailer or construction site']:
            t = d.get('Transport ' + lab)
            if t and str(t).strip():
                legs.append(f"{t.strip()} {num(d.get('Generic distance ' + lab))} km @ {num(d.get('MJ/tkm ' + lab))} MJ/tkm")
        n = base_note + 'A4 scenario: ' + '; '.join(legs) + ' (fuel Diesel MK1 2024 unless stated; empty returns included)'
    elif kind == 'a5':
        val = d['A5 average waste climate impact GWP-GHG, conservative value']; mods = 'A5 (construction-site waste: A1-A4 of wasted share)'
        dt = 'conservative default'
        n = base_note + f"A5 waste factor {num(d['A5 waste factor'])} (purchased/built-in); value is per kg built-in product"
    elif kind == 'wf':
        val = d['A5 waste factor']; mods = 'A5'
        unit = 'ratio'; du = 'purchased quantity / built-in quantity'
        dt = 'generic default (waste factor)'
        n = base_note + 'construction-site waste factor (spillfaktor); waste share = factor - 1'
        return dict(factor_key=key, item=f'{name} - A5 waste factor', category='waste', value=num(val), unit=unit, declared_unit=du,
                    ghg_basis='n/a', modules=mods, region='Sweden (Swedish market)', technology_or_route=d['Category'],
                    reference_year='valid from 2026-01-21 (v02.07.000)', data_type=dt, notes=n + ('; ' + extra_note if extra_note else '') + '; ' + BOV_LIC_NOTE)
    elif kind == 'energy':
        val = d["Energy product's climate impact GWP-GHG, typical value"]
        mods = 'life cycle of energy carrier (see notes)'
        dt = 'generic average'
        bg = (d.get("Background to the value A1-A3 building product's climate impact") or '').replace('\n', ' ').strip()
        uc = (d.get('Use of product') or '').strip()
        n = base_note + f"use: {uc} | background: {bg[:400]}"
        cat = 'energy'
    tech = d['Category']
    item = name + {'cons': ' - A1-A3 conservative', 'typ': ' - A1-A3 typical', 'a4': ' - A4 transport', 'a5': ' - A5 waste (conservative)', 'energy': ''}[kind]
    upd = d['Updated']
    refy = 'valid from 2026-01-21 (v02.07.000); record updated ' + (upd.strftime('%Y-%m-%d') if upd else '')
    return dict(factor_key=key, item=item, category=cat, value=num(val), unit=unit, declared_unit='1 ' + du,
                ghg_basis=BOV_GHG, modules=mods, region='Sweden (Swedish market)', technology_or_route=tech,
                reference_year=refy, data_type=dt, notes=n + ('; ' + extra_note if extra_note else '') + '; ' + BOV_LIC_NOTE)

mat = [
    ('concrete_ready_mix_c20_25', 6000000026), ('concrete_ready_mix_c25_30', 6000000029), ('concrete_ready_mix_c28_35', 6000000030),
    ('concrete_ready_mix_c30_37', 6000000032), ('concrete_ready_mix_c32_40', 6000000035), ('concrete_ready_mix_c35_45', 6000000036),
    ('concrete_ready_mix_c40_50', 6000000039), ('concrete_ready_mix_c45_55', 6000000042), ('concrete_ready_mix_c50_60', 6000000043),
    ('concrete_ready_mix_c30_37_low_carbon', 6000000033), ('concrete_ready_mix_c25_30_low_carbon', 6000000028),
    ('cement_cem_ii_a_ll', 6000000193),
    ('rebar', 6000000154), ('steel_structural_section', 6000000150), ('steel_structural_section_eaf_scrap', 6000000151),
    ('steel_light_gauge_profile', 6000000152), ('steel_hot_dip_galvanised', 6000000221), ('steel_sheet_cladding', 6000000153),
    ('timber_sawn_softwood', 6000000007), ('timber_planed_softwood', 6000000192), ('timber_glulam', 6000000168), ('timber_clt', 6000000167),
    ('timber_lvl', 6000000185), ('plywood', 6000000023), ('osb', 6000000024), ('particle_board', 6000000000),
    ('glass_float', 6000000122), ('glass_igu_double', 6000000175), ('glass_igu_triple', 6000000176), ('glass_laminated', 6000000177),
    ('aluminium_extrusion_primary', 6000000159), ('aluminium_extrusion_recycled', 6000000160), ('aluminium_sheet_primary', 6000000161),
    ('copper_sheet', 6000000162),
    ('gypsum_board_standard', 6000000020), ('gypsum_board_fire', 6000000016),
    ('mineral_wool_glass', 6000000001), ('mineral_wool_stone', 6000000123),
    ('insulation_eps', 6000000131), ('insulation_xps', 6000000132), ('insulation_pir', 6000000213),
    ('pvc_membrane_roofing', 6000000224), ('pe_film_vapour_barrier', 6000000198), ('plastic_polyolefin_generic', 6000000210),
    ('paint_acrylic_exterior', 6000000144), ('paint_silicate', 6000000145),
    ('brick_clay', 6000000082), ('aac_block', 6000000096), ('precast_hollowcore_slab', 6000000059),
    ('window_pvc_triple', 6000000214), ('window_wood_alu_triple', 6000000103),
]
for k, rid in mat:
    rows.append(bov_row(k, rid, 'cons'))
    rows.append(bov_row(k, rid, 'typ'))

# A4 and A5 for selected
for k, rid in [('concrete_ready_mix_c30_37', 6000000032), ('rebar', 6000000154), ('steel_structural_section', 6000000150),
               ('timber_glulam', 6000000168), ('timber_clt', 6000000167), ('gypsum_board_standard', 6000000020),
               ('mineral_wool_glass', 6000000001), ('insulation_eps', 6000000131), ('glass_float', 6000000122),
               ('aluminium_extrusion_primary', 6000000159), ('cement_cem_ii_a_ll', 6000000193), ('precast_hollowcore_slab', 6000000059)]:
    rows.append(bov_row('a4_transport_' + k, rid, 'a4', cat='transport'))
for k, rid in [('concrete_ready_mix_c30_37', 6000000032), ('rebar', 6000000154), ('steel_structural_section', 6000000150),
               ('timber_sawn_softwood', 6000000007), ('timber_glulam', 6000000168), ('gypsum_board_standard', 6000000020),
               ('mineral_wool_glass', 6000000001), ('insulation_eps', 6000000131), ('insulation_xps', 6000000132),
               ('glass_float', 6000000122), ('aluminium_extrusion_primary', 6000000159), ('brick_clay', 6000000082),
               ('precast_hollowcore_slab', 6000000059), ('paint_acrylic_exterior', 6000000144), ('pe_film_vapour_barrier', 6000000198)]:
    rows.append(bov_row('a5_waste_factor_' + k, rid, 'wf'))
for k, rid in [('concrete_ready_mix_c30_37', 6000000032), ('rebar', 6000000154), ('gypsum_board_standard', 6000000020)]:
    rows.append(bov_row('a5_waste_' + k, rid, 'a5', cat='waste'))

# Boverket energy
for k, rid in [('grid_electricity_se', 6000000008), ('district_heating_se', 6000000014), ('diesel_se_mk1_blend_2024', 6000000010),
               ('diesel_fossil', 6000000011), ('hvo100', 6000000017), ('natural_gas', 6100000010), ('lpg', 6100000000),
               ('heating_oil_eo1', 6100000004), ('heavy_fuel_oil_eo2_5', 6100000005), ('petrol_se_mk1_blend_2024', 6000000012)]:
    r = bov_row(k, rid, 'energy', cat='energy')
    d = bov[rid]
    r['region'] = 'Sweden'
    r['technology_or_route'] = d['Product name'].strip()
    r['modules'] = 'well-to-wheel / full fuel life cycle (upstream + combustion)' if 'MJ' in d['Unit for climate impact'] else 'life cycle of supplied energy (production incl. upstream; EN 15804 / FQD method)'
    if rid == 6000000014:
        r['modules'] = 'supplied district heat, Swedish EPA average (method as per Naturvardsverket)'
    rows.append(r)

# Boverket transport energy intensities (MJ/tkm)
for k, lab, mj, n in [('transport_truck_last_mile_energy', 'Lorry, last mile', 2.5, 'default for last-mile lorry leg (153 products), generic distance typically 40 km'),
                      ('transport_truck_regional_energy', 'Lorry, region transport', 1.5, 'default for ready-mix concrete factory-to-site leg (54 products), generic distance 35 km'),
                      ('transport_truck_long_haul_energy', 'Lorry, highroad', 1.0, 'default long-haul lorry leg factory to warehouse (154 products), distances 400-1000 km'),
                      ('transport_ship_container_tanker_energy', 'Boat, tanker/container shipping', 0.11, 'default sea leg (3 products), fuel: Fuel oil 1')]:
    rows.append(dict(factor_key=k, item=f'{lab} - energy use per tkm (A4 input)', category='transport', value=num(mj), unit='MJ/tkm',
                     declared_unit='1 tonne-km', ghg_basis='n/a (energy; multiply by fuel factor in kg CO2e/MJ)', modules='A4',
                     region='Sweden', technology_or_route=lab, reference_year='valid from 2026-01-21 (v02.07.000)', data_type='generic default',
                     notes=f'Taken from the per-product A4 transport columns ("MJ/tkm") of the Boverket climate database; {n}; empty returns included per Boverket A4 guidance (https://www.boverket.se/sv/klimatdeklaration/gor-sa-har/underlag/indata-transport/). ' + BOV_LIC_NOTE))
rows.append(dict(factor_key='conservative_factor_generic_epd', item='Boverket conservative factor applied to typical A1-A3 values', category='other', value='1.25',
                 unit='ratio', declared_unit='conservative/typical', ghg_basis='n/a', modules='A1-A3', region='Sweden',
                 technology_or_route='all building products', reference_year='valid from 2026-01-21 (v02.07.000)', data_type='methodological parameter',
                 notes='Boverket: generic data are set conservatively, about 25 % above average, to encourage use of specific EPD data (https://www.boverket.se/sv/klimatdeklaration/klimatdatabas/). ' + BOV_LIC_NOTE))

for r in rows:
    r.update(source_org='Boverket (Swedish National Board of Housing, Building and Planning)',
             source_title="Boverket's Climate Database (Boverkets klimatdatabas), Excel open-data export en-gb",
             edition_version='02.07.000', url=BOV_URL, retrieved=RET, licence_name=BOV_LIC, licence_url=BOV_LIC_URL,
             cite_single_value='yes', research_use='yes', db_incorporation='yes', commercial_use='yes', redistribution='unknown', rights_class='1')

# ---------------- ADEME Base Carbone ----------------
AD_URL = 'https://data.ademe.fr/data-fair/api/v1/datasets/base-carboner/raw'
AD_LIC = 'Licence Ouverte / Open Licence (Etalab) as stated on data.ademe.fr dataset base-carboner'
AD_LIC_URL = 'https://www.etalab.gouv.fr/licence-ouverte-open-licence'
bc = list(csv.DictReader(open(os.path.join(DL, 'Base_Carbone_V23.6.csv'), encoding='cp1252', newline=''), delimiter=';'))
el = {}; po = {}
for r in bc:
    i = r["Identifiant de l'élément"]
    if r['Type Ligne'] == 'Elément':
        el[i] = r
    elif r['Type Ligne'] == 'Poste':
        po.setdefault(i, []).append(r)

def ad_row(key, i, cat, modules=None, ghg=None, dt='generic average', tech=None, note='', rc='1', third=None, use_poste=None):
    r = el[str(i)]
    name = ' / '.join(x for x in [r['Nom base français'].strip(), r['Nom attribut français'].strip(), r['Nom frontière français'].strip()] if x)
    name_en = ' / '.join(x for x in [r['Nom base anglais'].strip(), r['Nom attribut anglais'].strip(), r['Nom frontière anglais'].strip()] if x)
    val = r['Total poste non décomposé']
    unit = r['Unité français'].strip()
    if use_poste:
        val = ''
        for p in po.get(str(i), []):
            if p['Type poste'] == use_poste:
                val = p['Total poste non décomposé']
        name += f' [poste: {use_poste}]'
    postes = '; '.join(f"{p['Type poste'] or p['Nom poste français']}={num(p['Total poste non décomposé'])}" for p in po.get(str(i), []))
    loc = (r['Localisation géographique'].strip() + ' ' + r['Sous-localisation géographique français'].strip()).strip()
    src = r['Source'].strip(); prog = r['Programme'].strip()
    n = f"Base Carbone ID {i}; FR name: {name}; status {r[chr(83)+'tatut de l' + chr(39) + 'élément']}; category {r['Code de la catégorie']}"
    if postes: n += f"; breakdown: {postes}"
    if src: n += f"; original source: {src}"
    if prog: n += f" ({prog})"
    if r['Incertitude']: n += f"; uncertainty {r['Incertitude']} %"
    cm = r['Commentaire français'].strip().replace('\n', ' ')
    if cm: n += f"; comment: {cm[:300]}"
    if note: n += '; ' + note
    base_en = r['Nom base anglais'].strip() or r['Nom base français'].strip()
    item = f"{base_en} - {tech or name}" + (f' [{use_poste} only]' if use_poste else '')
    d = dict(factor_key=key, item=item, category=cat, value=num(val), unit=unit,
             declared_unit='1 ' + (unit.split('/')[-1] if '/' in unit else unit),
             ghg_basis=ghg or 'kgCO2e, GWP100 (IPCC GWP set not stated in the export row; see Base Carbone documentation)',
             modules=modules or '', region=loc, technology_or_route=tech or name, reference_year=r['Période de validité'] + (f" (modified {r['Date de modification']})" if r['Date de modification'] else ''),
             data_type=dt, source_org='ADEME (Agence de la transition ecologique)',
             source_title='Base Carbone (Base Empreinte) - open data export Base_Carbone_V23.6.csv',
             edition_version='V23.6 (data updated 2025-07-03)', url=AD_URL, retrieved=RET, licence_name=AD_LIC, licence_url=AD_LIC_URL,
             cite_single_value='yes', research_use='yes', db_incorporation='yes', commercial_use='yes', redistribution='yes', rights_class=rc, notes=n)
    if third:
        d.update(rights_class='4', db_incorporation='unknown', commercial_use='unknown', redistribution='unknown',
                 notes=n + '; ' + third)
    return d

IEA = ('third-party data: values originate from IEA "CO2 emissions from fuel combustion"; Licence Ouverte 2.0 excludes information subject to third-party IP rights, '
       'and IEA data carry their own restrictive terms - treat as terms not confirmed; IEA-based values are combustion CO2 (likely no upstream)')
GLEC = ('third-party data: values from GLEC Framework (Smart Freight Centre, Feb 2020) republished by ADEME; Licence Ouverte excludes third-party IP rights - confirm GLEC terms before embedding')
ELEC_MOD = 'consumption: combustion at plant + upstream (fuel upstream, plant amortisation, ancillary) + grid losses'
BOTH = 'combustion + upstream (well-to-tank) - both'
A = []
A.append(ad_row('grid_electricity_fr', 43642, 'energy', ELEC_MOD, tech='France mainland grid mix, annual average (smoothed 2021-2024)'))
A.append(ad_row('grid_electricity_fr', 43273, 'energy', ELEC_MOD, tech='France mainland grid mix, 2023 average'))
A.append(ad_row('grid_electricity_fr', 42513, 'energy', ELEC_MOD, tech='France mainland grid mix, 2022 average'))
A.append(ad_row('grid_electricity_fr_heating_seasonal', 43276, 'energy', ELEC_MOD, tech='France grid, heating use, seasonalised method 2023'))
A.append(ad_row('grid_electricity_fr_cooling_seasonal', 43278, 'energy', ELEC_MOD, tech='France grid, air-conditioning use, seasonalised method 2023'))
for k, i in [('grid_electricity_jp', 15582), ('grid_electricity_se', 15606), ('grid_electricity_de', 15592), ('grid_electricity_uk', 15609),
             ('grid_electricity_us', 15579), ('grid_electricity_cn', 15680), ('grid_electricity_eu27', 15714)]:
    A.append(ad_row(k, i, 'energy', 'combustion (generation) only, per IEA', ghg='as published (IEA-derived; likely CO2 only)', tech='national grid average mix (IEA highlights 2013 edition)', third=IEA))
A.append(ad_row('natural_gas', 37132, 'energy', BOTH, tech='French natural gas mix 2022, per kWh LHV (PCI)'))
A.append(ad_row('natural_gas', 37133, 'energy', BOTH, tech='French natural gas mix 2022, per kWh HHV (PCS)'))
A.append(ad_row('natural_gas', 37138, 'energy', BOTH, tech='French natural gas mix 2022, per m3'))
A.append(ad_row('natural_gas_combustion_only', 37132, 'energy', 'combustion only', tech='French natural gas mix 2022, per kWh LHV', use_poste='Combustion'))
A.append(ad_row('heating_oil', 14085, 'energy', BOTH, tech='domestic heating oil (fioul domestique), per kWh LHV'))
A.append(ad_row('heating_oil', 14087, 'energy', BOTH, tech='domestic heating oil (fioul domestique), per litre'))
A.append(ad_row('heating_oil_combustion_only', 14087, 'energy', 'combustion only', tech='domestic heating oil, per litre', use_poste='Combustion'))
A.append(ad_row('diesel', 25775, 'energy', BOTH, tech='road diesel B7 (7 % biodiesel), per litre'))
A.append(ad_row('diesel', 34421, 'energy', BOTH, tech='road diesel B10, per litre'))
A.append(ad_row('diesel_non_road', 14015, 'energy', BOTH, tech='non-road diesel (GNR, construction machinery), per litre'))
A.append(ad_row('diesel_combustion_only', 25775, 'energy', 'combustion only', tech='road diesel B7, per litre', use_poste='Combustion'))
A.append(ad_row('lpg', 13556, 'energy', BOTH, tech='propane, per kg'))
A.append(ad_row('lpg', 13558, 'energy', BOTH, tech='propane, per kWh LHV'))
A.append(ad_row('lpg', 14031, 'energy', BOTH, tech='LPG for road vehicles, per litre'))
A.append(ad_row('district_heating_fr_default', 37089, 'energy', 'combustion only (DPE value, no LCA)', tech='France "other heat networks" default 2021 (Arrete DPE 21 Oct 2021)', note='used for networks not individually listed; individual network factors also exist in Base Carbone'))
A.append(ad_row('district_cooling_fr_default', 37090, 'energy', 'combustion/operation only (DPE value)', tech='France "other cooling networks" default 2021'))
# freight
A.append(ad_row('transport_road_truck_articulated_34_40t', 43643, 'transport', 'fuel upstream + combustion + vehicle manufacturing', tech='articulated truck 34-40 t, diesel B7'))
A.append(ad_row('transport_road_truck_articulated_40_44t', 43647, 'transport', 'fuel upstream + combustion + vehicle manufacturing', tech='articulated truck 40-44 t, diesel B7'))
A.append(ad_row('transport_road_truck_rigid_12_20t', 43716, 'transport', 'fuel upstream + combustion + vehicle manufacturing', tech='rigid truck 12-20 t, diesel B7'))
A.append(ad_row('transport_road_truck_rigid_20_26t', 43718, 'transport', 'fuel upstream + combustion + vehicle manufacturing', tech='rigid truck 20-26 t, diesel B7'))
A.append(ad_row('transport_road_lcv_3_5t', 43735, 'transport', 'fuel upstream + combustion + vehicle manufacturing', tech='light commercial vehicle <3.5 t, diesel B7'))
A.append(ad_row('transport_rail_freight', 43728, 'transport', 'energy upstream + combustion + rolling stock manufacturing', tech='freight train, average traction, average load'))
A.append(ad_row('transport_rail_freight_electric', 43734, 'transport', 'energy upstream + combustion + rolling stock manufacturing', tech='freight train, electric traction, average load'))
A.append(ad_row('transport_rail_freight_diesel', 43731, 'transport', 'energy upstream + combustion + rolling stock manufacturing', tech='freight train, diesel traction, average load'))
A.append(ad_row('transport_sea_container', 28193, 'transport', 'fuel upstream + combustion (WtW)', tech='container ship, dry, world average', third=GLEC))
A.append(ad_row('transport_sea_bulk', 28228, 'transport', 'fuel upstream + combustion (WtW)', tech='bulk carrier 10 000-100 000 t, HFO-MGO', third=GLEC))
A.append(ad_row('transport_sea_general_cargo', 28241, 'transport', 'fuel upstream + combustion (WtW)', tech='general cargo ship 10 000-20 000 t, HFO-MGO', third=GLEC))
A.append(ad_row('transport_inland_barge', 43711, 'transport', 'fuel upstream + combustion', tech='inland self-propelled barge >3000 t deadweight'))
# water
A.append(ad_row('water_supply', 24283, 'water', 'operation of drinking-water production and distribution, excluding infrastructure', tech='mains drinking water, France (ASTEE sector guide)'))
A.append(ad_row('wastewater_treatment', 24284, 'water', 'collection and treatment incl. process N2O/CH4 and sludge, excluding infrastructure', tech='urban wastewater treatment, France (ASTEE sector guide)'))
# waste
W = 'end-of-life treatment impacts (avoided emissions reported separately)'
A.append(ad_row('waste_incineration_mixed', 34650, 'waste', W, tech='residual household waste - incineration'))
A.append(ad_row('waste_landfill_mixed', 34652, 'waste', W, tech='residual household waste - landfill (storage)'))
A.append(ad_row('waste_mixed_average_eol', 34654, 'waste', W, tech='residual household waste - average French end of life'))
A.append(ad_row('waste_construction_mixed_non_hazardous', 34682, 'waste', W, tech='mixed non-hazardous C&D waste (DIB) - average end of life'))
A.append(ad_row('waste_construction_mixed_non_hazardous_no_recycling', 34692, 'waste', W, tech='mixed non-hazardous C&D waste (DIB) - end of life without recycling'))
A.append(ad_row('waste_inert', 34680, 'waste', W, tech='mixed inert C&D waste (rubble) - average end of life'))
A.append(ad_row('waste_inert_no_recycling', 34690, 'waste', W, tech='mixed inert C&D waste (rubble) - end of life without recycling'))
A.append(ad_row('waste_concrete_brick_ceramic', 34674, 'waste', W, tech='concrete, bricks, tiles and ceramics - average end of life'))
A.append(ad_row('waste_gypsum', 34676, 'waste', W, tech='plaster/gypsum waste - average end of life'))
A.append(ad_row('waste_wood_class_b', 34678, 'waste', W, tech='class B wood waste - average end of life'))
A.append(ad_row('waste_ferrous_metals', 34666, 'waste', W, tech='ferrous metal C&D waste - average end of life'))
# refrigerants
AR6 = 'GWP100 IPCC AR6 (as listed by ADEME)'
AR5 = 'GWP100 IPCC AR5 (as listed by ADEME)'
for k, i in [('refrigerant_gwp_r32', 43152), ('refrigerant_gwp_r134a', 43133), ('refrigerant_gwp_r410a', 43632), ('refrigerant_gwp_r404a', 43628),
             ('refrigerant_gwp_r407c', 43630), ('refrigerant_gwp_r1234yf', 43586), ('refrigerant_gwp_r1234ze', 43199), ('refrigerant_gwp_r22', 43119),
             ('refrigerant_gwp_r290', 43625), ('refrigerant_gwp_r125', 43131), ('refrigerant_gwp_r744', 43014)]:
    A.append(ad_row(k, i, 'refrigerant', 'n/a (characterisation factor)', ghg=AR6, dt='characterisation factor', tech='GWP100'))
for k, i in [('refrigerant_gwp_r32', 22584), ('refrigerant_gwp_r134a', 22586), ('refrigerant_gwp_r410a', 22600), ('refrigerant_gwp_r404a', 22596), ('refrigerant_gwp_r407c', 22598)]:
    d = ad_row(k, i, 'refrigerant', 'n/a (characterisation factor)', ghg=AR5, dt='characterisation factor', tech='GWP100')
    d['unit'] = 'kgCO2e/kg'; d['declared_unit'] = '1 kg'
    d['notes'] += '; unit field empty in export (dimensionless GWP); recorded as kgCO2e/kg'
    A.append(d)
# buildings (ratios)
BR = 'construction of building (product + construction stage), whole building, per m2'
A.append(ad_row('building_embodied_ratio_residential_detached', 24300, 'other', BR, dt='statistical estimate (HQE Performance experiment)'))
A.append(ad_row('building_embodied_ratio_residential_apartment', 24301, 'other', BR, dt='statistical estimate (HQE Performance experiment)'))
A.append(ad_row('building_embodied_ratio_office', 24302, 'other', BR, dt='statistical estimate (HQE Performance experiment)'))
A.append(ad_row('building_embodied_ratio_retail_concrete', 20734, 'other', BR, dt='generic average (Bilan Carbone ratio)'))
A.append(ad_row('building_embodied_ratio_industrial_concrete', 20730, 'other', BR, dt='generic average (Bilan Carbone ratio)'))
A.append(ad_row('building_embodied_ratio_industrial_steel', 20731, 'other', BR, dt='generic average (Bilan Carbone ratio)'))
A.append(ad_row('building_embodied_ratio_education_concrete', 20738, 'other', BR, dt='generic average (Bilan Carbone ratio)'))
# materials (ADEME, older generic values)
MA = 'cradle-to-gate (production)'
A.append(ad_row('concrete_ready_mix_c25_30', 20719, 'material', MA, tech='concrete C25/30 CEM II'))
A.append(ad_row('concrete_reinforced_generic', 20722, 'material', MA, tech='reinforced concrete, generic'))
A.append(ad_row('cement_portland_cem_i', 20723, 'material', MA, tech='Portland cement'))
A.append(ad_row('steel_generic_primary', 26729, 'material', MA, tech='steel or tinplate, virgin (FEDEREC/ADEME)'))
A.append(ad_row('aluminium_generic_primary', 26731, 'material', MA, tech='aluminium, virgin (FEDEREC/ADEME)'))
A.append(ad_row('aluminium_primary_fr', 37156, 'material', MA, tech='primary aluminium produced in France (plate, ingot, bars)'))
A.append(ad_row('glass_float', 24265, 'material', MA, tech='flat float glass, Europe (Base IMPACT)'))
A.append(ad_row('pvc_generic', 20834, 'material', MA, tech='PVC, virgin'))
A.append(ad_row('pe_hd_generic', 20830, 'material', MA, tech='HDPE, virgin'))
A.append(ad_row('pe_ld_generic', 20831, 'material', MA, tech='LDPE, virgin'))
A.append(ad_row('timber_sawn_softwood', 20909, 'material', 'manufacturing only (biogenic carbon excluded)', tech='construction timber, manufacture'))
A.append(ad_row('paint_varnish_acrylic', 24255, 'material', MA, tech='acrylic varnish (world)'))
rows.extend(A)

# ---------------- INIES / RE2020 MDEGD (not obtained) ----------------
INIES_URL = 'https://www.inies.fr/le-webservice/demander-un-acces/'
for k, item in [('concrete_ready_mix_c25_30', 'RE2020 default environmental data (DED/MDEGD) - ready-mix concrete'),
                ('rebar', 'RE2020 default environmental data (DED/MDEGD) - reinforcing steel'),
                ('mineral_wool_glass', 'RE2020 default environmental data (DED/MDEGD) - mineral wool insulation')]:
    rows.append(dict(factor_key=k, item=item, category='material', value='', unit='', declared_unit='', ghg_basis='', modules='',
                     region='France', technology_or_route='RE2020 DED (majorant/conservative default values)', reference_year='',
                     data_type='conservative default', source_org='INIES (Alliance HQE-GBC / CSTB) for French Ministry (DHUP)',
                     source_title='Base INIES - Donnees environnementales par defaut (DED)', edition_version='', url=INIES_URL, retrieved=RET,
                     licence_name='INIES webservice: paid annual commercial licence (2 800 EUR HT); public web consultation only', licence_url=INIES_URL,
                     cite_single_value='unknown', research_use='unknown', db_incorporation='no', commercial_use='no', redistribution='no', rights_class='5',
                     notes=('Not obtained: INIES states data are consultable publicly and free of charge on its JS consultation site, but digital/bulk access requires a paid webservice licence '
                            '(https://www.inies.fr/le-webservice/demander-un-acces/); no open-licence download of DED found (https://www.inies.fr/contenu-de-la-base/autres-donnees-de-la-base-inies/); '
                            'not scraped, no login used. Alternative: Boverket conservative generic values (this file), ADEME Base Carbone, OEKOBAUDAT generic data.')))

rows.append(dict(factor_key='equipment_embodied_ratio_per_m2', item='Building services equipment embodied carbon per m2 (lot forfaitaire)', category='equipment', value='', unit='', declared_unit='',
                 ghg_basis='', modules='', region='France', technology_or_route='', reference_year='', data_type='', source_org='ADEME',
                 source_title='Base Carbone (Base Empreinte) - open data export Base_Carbone_V23.6.csv', edition_version='V23.6', url=AD_URL, retrieved=RET,
                 licence_name=AD_LIC, licence_url=AD_LIC_URL, cite_single_value='yes', research_use='yes', db_incorporation='yes', commercial_use='yes', redistribution='yes', rights_class='1',
                 notes='Not obtained: no per-m2 building-equipment ratio found in Base Carbone V23.6 (only whole-building ratios kgCO2e/m2 and per-item equipment such as cables). RE2020 "lots forfaitaires" for equipment are published via INIES/RE2020 methodology (not open-licensed download). Alternative: RE2020 methode annex (Arrete 4 Aug 2021) or CIBSE TM65.'))

with open(OUT, 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=HDR)
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, '') for k in HDR})
print(len(rows), 'rows;', sum(1 for r in rows if r['value'] != ''), 'with value')
