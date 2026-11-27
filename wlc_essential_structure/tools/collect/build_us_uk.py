import csv, re, sys, openpyxl, warnings
warnings.filterwarnings('ignore')
import os
BASE = os.environ.get('COEF_BASE', os.path.join(os.getcwd(), 'coef')) + '/'
DL = BASE + 'downloads/us_uk/'
OUT = BASE + 'out/us_uk.csv'
RET = '2026-11-27'
HDR = "factor_key,item,category,value,unit,declared_unit,ghg_basis,modules,region,technology_or_route,reference_year,data_type,source_org,source_title,edition_version,url,retrieved,licence_name,licence_url,cite_single_value,research_use,db_incorporation,commercial_use,redistribution,rights_class,notes".split(',')
rows = []

def slug(s):
    s = s.lower().replace('&', 'and').replace('+', 'plus')
    s = re.sub(r'[^a-z0-9]+', '_', s).strip('_')
    return s

# ---------- licence presets ----------
US_PD = dict(licence_name='US federal government work - public domain (17 U.S.C. 105)',
             licence_url='https://pasteur.epa.gov/license/sciencehub-license.html ; https://www.epa.gov/web-policies-and-procedures/epa-disclaimers',
             cite_single_value='yes', research_use='yes', db_incorporation='yes', commercial_use='yes', redistribution='yes', rights_class=1)
UK_OGL = dict(licence_name='Open Government Licence v3.0', licence_url='https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/',
              cite_single_value='yes', research_use='yes', db_incorporation='yes', commercial_use='yes', redistribution='yes', rights_class=1)

HUB = dict(source_org='U.S. Environmental Protection Agency (Center for Corporate Climate Leadership)',
           source_title='GHG Emission Factors Hub', edition_version='2025 (last modified 15 Jan 2025; latest edition listed on hub page updated 12 Jan 2026)',
           url='https://www.epa.gov/system/files/other-files/2025-01/ghg-emission-factors-hub-2025.xlsx', region='US', **US_PD)
HUB_NOTE = 'Licence: EPA states EPA-produced data are public domain (17 U.S.C. 105; EPA data licence page); EPA disclaimers page notes some documents may carry third-party copyright where marked - none marked in this file. '
WARM = dict(source_org='U.S. Environmental Protection Agency (Office of Resource Conservation and Recovery)',
            source_title='Waste Reduction Model (WARM) - Summary Data sheet', edition_version='Version 16 (December 2023)',
            url='https://www.epa.gov/system/files/documents/2023-12/warm_v16.xls', region='US', **US_PD)
SC = dict(source_org='U.S. Environmental Protection Agency, Office of Research and Development',
          source_title='Supply Chain Greenhouse Gas Emission Factors v1.3 by NAICS-6 (USEEIO-based)', edition_version='v1.3.0 (GHG data year 2022, USD2022; dataset updated 2024-07-05)',
          url='https://pasteur.epa.gov/uploads/10.23719/1531143/SupplyChainGHGEmissionFactors_v1.3.0_NAICS_CO2e_USD2022.csv', region='US', **US_PD)
CFR = dict(source_org='U.S. EPA / Office of the Federal Register (eCFR)',
           source_title='40 CFR Part 98 Subpart A, Table A-1 Global Warming Potentials (100-year)', edition_version='eCFR current as of 2026-11-01 (GWPs updated by final rule 25 Apr 2024)',
           url='https://www.ecfr.gov/api/versioner/v1/full/2026-11-01/title-40.xml?part=98&subpart=A', region='US', **US_PD)
UK = dict(source_org='UK Department for Energy Security and Net Zero (DESNZ)',
          source_title='Government conversion factors for company reporting of greenhouse gas emissions (Conversion factors 2026: flat file)', edition_version='2026, flat file v1.2 (revised 10 Jul 2026); full set v1 published 11 Jun 2026',
          url='https://assets.publishing.service.gov.uk/media/6a6c9748862aaf18d9c62ac9/ghg-conversion-factors-2026-flat-format-revised.xlsx', region='UK', **UK_OGL)

def add(**kw):
    r = {h: '' for h in HDR}
    r['retrieved'] = RET
    r.update(kw)
    rows.append(r)

# ======================= EPA HUB =======================
wb = openpyxl.load_workbook(DL + 'epa_hub_2025.xlsx', data_only=True, read_only=True)
ws = wb['Emission Factors Hub']
H = [[c for c in r] for r in ws.iter_rows(values_only=True)]
def hrow(label, start=0, end=None):
    for i in range(start, end or len(H)):
        cells = [c for c in H[i] if c is not None]
        if len(cells) > 1 and str(cells[0]).strip() == label:
            return cells
    raise KeyError(label)
# Table 1 stationary combustion: rows 12-100 (0-based ~11..99)
fuels = [('Natural Gas', 'fuel_natural_gas', 'scf'), ('Distillate Fuel Oil No. 2', 'fuel_diesel', 'gallon'),
         ('Liquefied Petroleum Gases (LPG)', 'fuel_lpg', 'gallon'), ('Propane', 'fuel_propane', 'gallon'),
         ('Kerosene', 'fuel_kerosene', 'gallon'), ('Motor Gasoline', 'fuel_gasoline', 'gallon'),
         ('Residual Fuel Oil No. 6', 'fuel_heavy_fuel_oil', 'gallon'), ('Bituminous', 'fuel_coal_bituminous', 'short ton'),
         ('Wood and Wood Residuals', 'fuel_wood_biomass', 'short ton')]
for lab, key, u in fuels:
    c = hrow(lab, 11, 100)
    hhv, co2, ch4, n2o, co2u, ch4u, n2ou = c[1:8]
    common = dict(category='energy', ghg_basis='per-gas (not CO2e); convert with AR5 GWP CH4=28, N2O=265 as Hub instructs',
                  modules='combustion only (no upstream/WTT)', technology_or_route='stationary combustion; HHV basis; 40 CFR 98 Tables C-1/C-2',
                  reference_year='2025 edition (40 CFR 98 defaults)', data_type='generic default (regulatory)', **HUB)
    add(factor_key=key, item=f'{lab} - CO2 stationary combustion', value=co2, unit='kg CO2/mmBtu', declared_unit='1 mmBtu (HHV)', notes=HUB_NOTE + f'Hub Table 1. Default HHV {hhv} mmBtu per {u}.' + (' Biogenic CO2 - report separately.' if 'Wood' in lab else ''), **common)
    add(factor_key=key, item=f'{lab} - CO2 per physical unit', value=co2u, unit=f'kg CO2/{u}', declared_unit=f'1 {u}', notes=HUB_NOTE + 'Hub Table 1.', **common)
    add(factor_key=key, item=f'{lab} - CH4 stationary combustion', value=ch4, unit='g CH4/mmBtu', declared_unit='1 mmBtu (HHV)', notes=HUB_NOTE + 'Hub Table 1.', **common)
    add(factor_key=key, item=f'{lab} - N2O stationary combustion', value=n2o, unit='g N2O/mmBtu', declared_unit='1 mmBtu (HHV)', notes=HUB_NOTE + 'Hub Table 1.', **common)
# Table 2 mobile CO2 diesel
c = hrow('Diesel Fuel', 100, 115)
add(factor_key='fuel_diesel', item='Diesel fuel - CO2 mobile combustion', category='energy', value=c[1], unit='kg CO2/gallon', declared_unit='1 US gallon',
    ghg_basis='CO2 only', modules='combustion only (tank-to-wheel)', technology_or_route='mobile combustion', reference_year='2025 edition', data_type='generic default (regulatory)', notes=HUB_NOTE + 'Hub Table 2.', **HUB)
# Table 5 non-road CH4/N2O
for i in range(286, 335):
    cells = [x for x in H[i] if x is not None]
    if not cells: continue
for lab_rowtext, key, it in [(('Construction/Mining EquipmentB', 'Diesel Equipment'), 'construction_equipment_diesel', 'Construction/mining equipment - diesel'),
                             (('Locomotives', 'Diesel'), 'transport_rail_freight', 'Locomotives - diesel'),
                             (('Ships and Boats', 'Residual Fuel Oil'), 'transport_ship_freight', 'Ships and boats - residual fuel oil')]:
    pass
def find_nonroad(veh, fuel):
    cur = None
    for i in range(288, 330):
        r = H[i]
        cells = [x for x in r if x is not None]
        if not cells: continue
        if len(cells) == 4: cur = cells[0]; f, ch4, n2o = cells[1:4]
        else: f, ch4, n2o = cells[0:3]
        if cur == veh and f == fuel: return ch4, n2o
    raise KeyError(veh + fuel)
for veh, fuel, key, it in [('Construction/Mining EquipmentB', 'Diesel Equipment', 'construction_equipment_diesel', 'Construction/mining equipment - diesel equipment'),
                           ('Construction/Mining EquipmentB', 'Diesel Off-Road Trucks', 'construction_equipment_diesel', 'Construction/mining - diesel off-road trucks'),
                           ('Locomotives', 'Diesel', 'transport_rail_freight', 'Locomotives - diesel'),
                           ('Ships and Boats', 'Residual Fuel Oil', 'transport_ship_freight', 'Ships and boats - residual fuel oil')]:
    ch4, n2o = find_nonroad(veh, fuel)
    for g, v in (('CH4', ch4), ('N2O', n2o)):
        add(factor_key=key, item=f'{it} - {g}', category='energy', value=v, unit=f'g {g}/gallon', declared_unit='1 US gallon fuel', ghg_basis='per-gas (not CO2e)',
            modules='combustion only (tank-to-wheel)', technology_or_route='non-road mobile combustion', reference_year='US GHG Inventory 1990-2022 (EPA 2024)', data_type='statistical estimate (national inventory)',
            notes=HUB_NOTE + 'Hub Table 5. Combine with Table 2 CO2 per gallon (diesel 10.21 kg CO2/gal).', **HUB)
# Table 6 electricity
for i in range(338, 366):
    cells = [x for x in H[i] if x is not None]
    acr, name = cells[0], cells[1]
    co2 = cells[2]
    k = 'grid_electricity_us' if acr == 'US Average' else 'grid_electricity_us_' + slug(acr)
    add(factor_key=k, item=f'Grid electricity eGRID subregion {acr} ({name}) - CO2 total output rate', category='energy', value=co2, unit='lb CO2/MWh', declared_unit='1 MWh generated (total output)',
        ghg_basis='CO2 only (CH4/N2O given separately)', modules='generation combustion only; excludes upstream fuel and T&D losses', region='US-' + acr if acr != 'US Average' else 'US',
        technology_or_route='grid average location-based', reference_year='eGRID2023 (2023 data)', data_type='statistical estimate (plant-level data)',
        notes=HUB_NOTE + 'Hub Table 6 from eGRID2023 summary tables (Jan 2025). 1 lb = 0.45359 kg (not converted).' + (f' Grid gross loss {cells[8]} (fraction).' if len(cells) > 8 else ''),
        **{k2: v for k2, v in HUB.items() if k2 != 'region'})
    if acr == 'US Average':
        for g, v in (('CH4', cells[3]), ('N2O', cells[4])):
            add(factor_key='grid_electricity_us', item=f'Grid electricity US average - {g} total output rate', category='energy', value=v, unit=f'lb {g}/MWh', declared_unit='1 MWh', ghg_basis='per-gas',
                modules='generation combustion only', region='US', technology_or_route='grid average', reference_year='eGRID2023', data_type='statistical estimate', notes=HUB_NOTE + 'Hub Table 6.', **{k2: v2 for k2, v2 in HUB.items() if k2 != 'region'})
        add(factor_key='grid_electricity_us_nonbaseload', item='Grid electricity US average - CO2 non-baseload rate', category='energy', value=cells[5], unit='lb CO2/MWh', declared_unit='1 MWh', ghg_basis='CO2 only',
            modules='generation combustion only', region='US', technology_or_route='non-baseload (marginal proxy; for avoided-emission estimates, not inventories)', reference_year='eGRID2023', data_type='statistical estimate', notes=HUB_NOTE + 'Hub Table 6.', **{k2: v2 for k2, v2 in HUB.items() if k2 != 'region'})
        add(factor_key='grid_td_loss_us', item='US average grid gross loss (T&D loss rate)', category='energy', value=cells[8], unit='fraction (shown in column headed %)', declared_unit='per unit electricity', ghg_basis='n/a',
            modules='T&D losses (Scope 3 cat. 3 activity C)', region='US', technology_or_route='grid', reference_year='eGRID2023', data_type='statistical estimate', notes=HUB_NOTE + 'Hub Table 6; value 0.042 = 4.2%.', **{k2: v2 for k2, v2 in HUB.items() if k2 != 'region'})
# Table 7 steam
c = hrow('Steam and Heat', 400, 415)
for g, v, u in (('CO2', c[1], 'kg CO2/mmBtu'), ('CH4', c[2], 'g CH4/mmBtu'), ('N2O', c[3], 'g N2O/mmBtu')):
    add(factor_key='district_heat_steam', item=f'Purchased steam and heat - {g}', category='energy', value=v, unit=u, declared_unit='1 mmBtu steam/heat purchased', ghg_basis='per-gas',
        modules='combustion only (no upstream)', technology_or_route='assumes natural gas boiler at 80% thermal efficiency', reference_year='2025 edition', data_type='generic default', notes=HUB_NOTE + 'Hub Table 7.', **HUB)
# Table 8 transport
for lab, key, unit in [('Medium- and Heavy-Duty Truck', 'transport_truck_freight', 'vehicle-mile'), ('Medium- and Heavy-Duty TruckC', 'transport_truck_freight', 'short ton-mile'),
                       ('Rail', 'transport_rail_freight', 'short ton-mile'), ('Waterborne Craft', 'transport_ship_freight', 'short ton-mile'), ('Aircraft', 'transport_air_freight', 'short ton-mile')]:
    c = hrow(lab, 418, 430)
    for g, v, uu in (('CO2', c[1], 'kg CO2'), ('CH4', c[2], 'g CH4'), ('N2O', c[3], 'g N2O')):
        add(factor_key=key, item=f'Freight {lab.rstrip("C")} - {g} per {unit}', category='transport', value=v, unit=f'{uu}/{unit}', declared_unit='1 ' + unit, ghg_basis='per-gas',
            modules='A4/C2-type transport; combustion only (tank-to-wheel), no WTT', technology_or_route='US fleet average', reference_year='2022 data (US GHG Inventory 1990-2022; BTS NTS 2024)', data_type='statistical estimate',
            notes=HUB_NOTE + 'Hub Table 8 (Scope 3 cat 4/9, distance-based). 1 short ton-mile = 1.45997 t-km (not converted).', **HUB)
# Table 10 business travel (selected)
for lab, key in [('Passenger Car A', 'transport_passenger_car'), ('Bus', 'transport_bus'), ('Air Travel - Medium Haul (>= 300 miles, < 2300 miles)', 'transport_air_passenger_medium_haul')]:
    c = hrow(lab, 500, 516)
    add(factor_key=key, item=f'Business travel {lab} - CO2', category='transport', value=c[1], unit=f'kg CO2/{c[4]}', declared_unit='1 ' + c[4], ghg_basis='CO2 only (CH4 %s g, N2O %s g per unit)' % (c[2], c[3]),
        modules='combustion only (no WTT)', technology_or_route='US average', reference_year='2022 data (air: DEFRA 2022 factors held constant)', data_type='statistical estimate', notes=HUB_NOTE + 'Hub Table 10. Air factors originate from UK DEFRA 2022 (OGL v3).', **HUB)
# Table 9 waste
mat_keys = {'Concrete': 'concrete', 'Structural Steel': 'structural_steel', 'Dimensional Lumber': 'dimensional_lumber', 'Medium-density Fiberboard': 'mdf',
            'Drywall': 'plasterboard_drywall', 'Glass': 'glass', 'Asphalt Concrete': 'asphalt_concrete', 'Asphalt Shingles': 'asphalt_shingles', 'Carpet': 'carpet',
            'Fiberglass Insulation': 'insulation_glass_wool', 'Clay Bricks': 'clay_brick', 'Vinyl Flooring': 'vinyl_flooring', 'Wood Flooring': 'wood_flooring',
            'Aluminum Ingot': 'aluminium', 'Copper Wire': 'copper_wire', 'PVC': 'pvc', 'Mixed MSW': 'mixed_msw', 'Fly Ash': 'fly_ash', 'Mixed Metals': 'mixed_metals'}
paths = ['recycling', 'landfill', 'combustion']
for i in range(435, 497):
    cells = [x for x in H[i] if x is not None]
    if not cells or cells[0] not in mat_keys: continue
    for j, p in enumerate(paths):
        v = cells[1 + j]
        if v == 'NA': continue
        add(factor_key=f'waste_{mat_keys[cells[0]]}_{p}', item=f'{cells[0]} - {p} (end-of-life, Scope 3 cat 5/12)', category='waste', value=v, unit='metric t CO2e/short ton material', declared_unit='1 short ton (2000 lb) material',
            ghg_basis='CO2e, IPCC AR4 GWP100 (per Hub note)', modules='C2+C3/C4 (transport to facility + processing/landfill); excludes avoided emissions/credits (no module D)', technology_or_route=f'US average {p} practice (WARM-derived)',
            reference_year='WARM documentation Dec 2023', data_type='generic average', notes=HUB_NOTE + 'Hub Table 9; derived from WARM v16 excluding avoided emissions and carbon storage. Landfill CH4 uses typical LFG collection and US non-baseload grid.', **HUB)
# Table 11/12 GWP
gwp_rows = {}
for i in range(520, len(H)):
    cells = [x for x in H[i] if x is not None]
    if len(cells) >= 2: gwp_rows[str(cells[0]).strip()] = cells
for name, key in [('HFC-32', 'refrigerant_gwp_r32'), ('HFC-134a', 'refrigerant_gwp_r134a'), ('HFC-125', 'refrigerant_gwp_r125'), ('HFC-143a', 'refrigerant_gwp_r143a'),
                  ('R-404A', 'refrigerant_gwp_r404a'), ('R-407C', 'refrigerant_gwp_r407c'), ('R-410A', 'refrigerant_gwp_r410a'), ('R-507A', 'refrigerant_gwp_r507a'),
                  ('Sulfur hexafluoride', 'gwp_sf6'), ('Methane', 'gwp_ch4'), ('Nitrous oxide', 'gwp_n2o')]:
    c = gwp_rows[name]
    v = c[2] if len(c) >= 3 and name not in ('R-404A', 'R-407C', 'R-410A', 'R-507A') else c[1]
    comp = c[2] if name.startswith('R-') else c[1]
    add(factor_key=key, item=f'GWP100 {name}', category='refrigerant', value=v, unit='kg CO2e/kg', declared_unit='1 kg gas released', ghg_basis='IPCC AR5 GWP100 (no climate-carbon feedback)',
        modules='B1/B3 refrigerant leakage; C1 end-of-life loss', technology_or_route=('blend: ' + str(comp)) if name.startswith('R-') else 'pure substance (' + str(comp) + ')', reference_year='AR5 (2013)',
        data_type='physical constant (IPCC)', notes=HUB_NOTE + ('Hub Table 12 (blend GWP from HFC/PFC constituents only; SNAP compositions).' if name.startswith('R-') else 'Hub Table 11.'), **HUB)

# ======================= 40 CFR 98 Table A-1 =======================
for key, item, v, nt in [('refrigerant_gwp_r1234ze', 'GWP100 HFO-1234ze(E) (trans-1,3,3,3-tetrafluoropropene)', 0.97, 'Listed as HFC-1234ze(E), CAS 1645-83-6.'),
                         ('refrigerant_gwp_r1234yf', 'GWP100 HFO-1234yf', 0.31, 'Listed as HFC-1234yf; HFO-1234yf, CAS 754-12-1.'),
                         ('refrigerant_gwp_r744', 'GWP100 carbon dioxide (R744)', 1, 'CO2 reference gas.'),
                         ('refrigerant_gwp_r32', 'GWP100 HFC-32 (R32)', 677, 'Cross-check with Hub Table 11.'),
                         ('refrigerant_gwp_r134a', 'GWP100 HFC-134a', 1300, 'Cross-check with Hub Table 11.')]:
    add(factor_key=key, item=item, category='refrigerant', value=v, unit='kg CO2e/kg', declared_unit='1 kg gas released', ghg_basis='GWP100 per 40 CFR 98 Table A-1 (AR5-based values adopted by 2024 rule; AR5 for some new compounds)',
        modules='B1/B3 leakage; C1', technology_or_route='pure substance', reference_year='rule effective 1 Jan 2025', data_type='regulatory constant', notes='US regulation text (public domain). ' + nt, **CFR)
for key, item, nt in [('refrigerant_gwp_r22', 'GWP100 HCFC-22 (R22) - US EPA', 'HCFC-22 is an ozone-depleting substance not listed in EPA Hub Table 11 nor 40 CFR 98 Table A-1. Alternative: UK DESNZ 2026 R22 = 1760 (AR5) in this file; EPA SNAP/ODS pages.'),
                      ('refrigerant_gwp_r290', 'GWP100 propane (R290) - US EPA', 'Propane not listed in EPA Hub Table 11 nor 40 CFR 98 Table A-1 (not a fluorinated GHG). Alternative: UK DESNZ 2026 R290 = 0.06 in this file.')]:
    add(factor_key=key, item=item, category='refrigerant', value='', unit='kg CO2e/kg', declared_unit='1 kg', ghg_basis='', modules='', technology_or_route='', reference_year='', data_type='',
        notes='NOT OBTAINED from US source. Tried: EPA GHG Emission Factors Hub 2025 Tables 11-12 and 40 CFR 98 Table A-1. ' + nt, **CFR)

# ======================= WARM v16 =======================
wr = list(csv.reader(open(DL + 'converted/warm_v16-Summary Data.csv', encoding='utf-8', errors='ignore')))
warm_mat = {'Concrete': 'concrete', 'Structural Steel': 'structural_steel', 'Dimensional Lumber': 'dimensional_lumber', 'Medium-density Fiberboard': 'mdf', 'Drywall': 'plasterboard_drywall',
            'Glass': 'glass', 'Asphalt Concrete': 'asphalt_concrete', 'Asphalt Shingles': 'asphalt_shingles', 'Carpet': 'carpet', 'Fiberglass Insulation': 'insulation_glass_wool',
            'Clay Bricks': 'clay_brick', 'Vinyl Flooring': 'vinyl_flooring', 'Wood Flooring': 'wood_flooring', 'Aluminum Ingot': 'aluminium', 'Copper Wire': 'copper_wire', 'PVC': 'pvc', 'Fly Ash': 'fly_ash', 'Mixed MSW': 'mixed_msw'}
cols = {1: 'source_reduction', 2: 'recycling', 4: 'landfill', 8: 'combustion'}
for r in wr[1:]:
    if not r or r[0] not in warm_mat: continue
    for ci, p in cols.items():
        v = r[ci].strip()
        if v in ('NA', '', '--'): continue
        mk = warm_mat[r[0]]
        if p == 'source_reduction':
            key, cat = f'{mk}_warm_source_reduction', 'material'
            mods = 'A1-A3 avoided (raw material acquisition + manufacturing, current recycled-content mix); negative = emissions avoided'
            nt = 'WARM source-reduction factor = negative of cradle-to-gate production emissions for current mix (incl. forest carbon effects for wood/paper where applicable); can be read as an approximate A1-A3 value with sign reversed.'
        else:
            key, cat = f'waste_{mk}_{p}_warm_net', 'waste'
            mods = 'C2-C4 plus module-D-type credits (net life-cycle incl. avoided virgin production for recycling, avoided utility for combustion, landfill carbon storage)'
            nt = 'Net WARM factor relative to zero baseline; NOT comparable to Hub Table 9 gross values. Landfill = national average LFG recovery, default transport.'
        add(factor_key=key, item=f'{r[0]} - WARM {p.replace("_", " ")}', category=cat, value=v, unit='metric t CO2e/short ton', declared_unit='1 short ton material managed',
            ghg_basis='CO2e, IPCC AR4 GWP100 (CH4=25, N2O=298; WARM background chapter)', modules=mods, technology_or_route=f'US average {p.replace("_", " ")} pathway',
            reference_year='WARM v16 (Dec 2023)', data_type='generic average (LCA model)', notes='Licence: EPA tool, US government work (public domain), no copyright notice in file. ' + nt, **WARM)
add(factor_key='waste_mixed_cd_landfill_warm_net', item='Mixed construction & demolition debris - WARM', category='waste', value='', unit='metric t CO2e/short ton', declared_unit='1 short ton',
    notes='NOT OBTAINED: WARM v16 Summary Data sheet has no "Mixed C&D" material (only individual C&D materials). Alternative: compose from individual materials; UK DESNZ "Average construction" waste factors in this file.', **WARM)

# ======================= Supply chain EEIO =======================
core = {'327310', '327320', '331110', '321113', '327211', '331313', '333415', '335311', '332913', '335999'}
want = ['327310', '327320', '327390', '327331', '331110', '331210', '331221', '332312', '332311', '321113', '321212', '321213', '327211', '327215', '331313', '331315',
        '331420', '333415', '333414', '335311', '335313', '335929', '335931', '335122', '335999', '332913', '326191', '332919', '326122', '327420', '327993', '326140', '326150',
        '324121', '324122', '327120', '325510', '332321', '333921', '236220', '236116']
scd = {r[0]: r for r in csv.reader(open(DL + 'sc_ghg_v1.3.0_naics_co2e_usd2022.csv', encoding='utf-8'))}
for n in want:
    r = scd[n]
    key = 'eeio_us_' + n + '_' + slug(r[1])[:40].rstrip('_')
    base = dict(category='eeio', unit='kg CO2e/USD (2022, purchaser price)', declared_unit='1 USD2022 spent at purchaser price', ghg_basis='CO2e, IPCC AR5 GWP100, all GHGs',
                modules='cradle-to-gate supply chain (A1-A3 equivalent, spend-based)', technology_or_route=f'NAICS-2017 {n} (USEEIO code {r[7]})', reference_year='2022 GHG data, USD2022',
                data_type='statistical estimate (environmentally-extended input-output)')
    add(factor_key=key, item=f'{r[1]} - supply chain EF with margins (SEF+MEF)', value=r[6], notes='Licence: EPA ScienceHub data licence - public domain. Includes margins (transport, wholesale, retail) - use for purchaser-price spend.', **base, **SC)
    if n in core:
        add(factor_key=key, item=f'{r[1]} - supply chain EF without margins (SEF)', value=r[4], notes='Licence: EPA ScienceHub data licence - public domain. Excludes margins (producer-price basis of supply chain).', **base, **SC)

# ======================= UK DESNZ 2026 =======================
uk = list(csv.reader(open(BASE + 'scripts_us_uk/uk_flat.csv', encoding='utf-8')))
U = {r[0]: r for r in uk[1:] if r and r[0]}
def ukget(l1, l2, l3, l4='', col='', uom='', ghg='kg CO2e'):
    for r in uk[1:]:
        if r[2] == l1 and r[3] == l2 and r[4] == l3 and r[5] == l4 and r[6] == col and r[7] == uom and r[8] == ghg:
            return r
    raise KeyError((l1, l2, l3, l4, col, uom))
def ukadd(r, key, item, category, modules, tech, dtype='generic average (national)', notes='', ghg='CO2e, IPCC AR5 GWP100 (CO2, CH4, N2O combined)', declared=None):
    v = r[9]
    add(factor_key=key, item=item, category=category, value=v, unit=f'kg CO2e/{r[7]}', declared_unit=declared or f'1 {r[7]}', ghg_basis=ghg, modules=modules,
        technology_or_route=tech, reference_year='2026 reporting year', data_type=dtype,
        notes=(f'UK factor ID {r[0]} ({r[1]}). ' + notes + ('' if v != '' else ' Cell blank in source (no data available).')).strip(), **UK)
# fuels
for fname, key in [('Natural gas', 'fuel_natural_gas'), ('LPG', 'fuel_lpg'), ('Propane', 'fuel_propane')]:
    for uom in (['kWh (Gross CV)', 'kWh (Net CV)', 'cubic metres'] if fname == 'Natural gas' else ['kWh (Gross CV)', 'litres']):
        ukadd(ukget('Fuels', 'Gaseous fuels', fname, uom=uom), key, f'{fname} combustion (Scope 1)', 'energy', 'combustion only (Scope 1)', 'stationary combustion; natural gas = UK average biomethane blend' if fname == 'Natural gas' else 'stationary combustion')
    uom = 'kWh (Gross CV)'
    ukadd(ukget('WTT- fuels', 'Gaseous fuels', fname, uom=uom), key, f'{fname} well-to-tank', 'energy', 'well-to-tank only (extraction, processing, transport)', 'upstream fuel supply')
for fname, key in [('Diesel (average biofuel blend)', 'fuel_diesel'), ('Diesel (100% mineral diesel)', 'fuel_diesel_mineral'), ('Petrol (average biofuel blend)', 'fuel_gasoline'),
                   ('Burning oil', 'fuel_kerosene'), ('Gas oil', 'fuel_gas_oil'), ('Fuel oil', 'fuel_heavy_fuel_oil')]:
    for uom in ['litres', 'kWh (Gross CV)']:
        ukadd(ukget('Fuels', 'Liquid fuels', fname, uom=uom), key, f'{fname} combustion (Scope 1)', 'energy', 'combustion only (Scope 1)', 'combustion; biofuel blend share per UK 2026 average' if 'blend' in fname else 'combustion')
    ukadd(ukget('WTT- fuels', 'Liquid fuels', fname, uom='litres'), key, f'{fname} well-to-tank', 'energy', 'well-to-tank only', 'upstream fuel supply')
# electricity, heat
ukadd(ukget('UK electricity', 'Electricity generated', 'Electricity: UK', 'kWh', '', 'kWh'), 'grid_electricity_uk', 'UK grid electricity generation (Scope 2, location-based)', 'energy', 'generation combustion only (excl. T&D, excl. WTT)', 'UK grid average', notes='Based on 2024 generation data (DESNZ 1-in-arrears convention; see methodology).')
ukadd(ukget('Transmission and distribution', 'T&D- UK electricity', 'Electricity: UK', 'kWh', '', 'kWh'), 'grid_td_loss_uk', 'UK electricity T&D losses', 'energy', 'T&D losses (Scope 3 cat 3)', 'UK grid')
ukadd(ukget('WTT- UK electricity', 'WTT- UK electricity (generation)', 'Electricity: UK', 'kWh', '', 'kWh'), 'grid_electricity_uk_wtt', 'UK electricity WTT (generation)', 'energy', 'well-to-tank of fuels for generation', 'UK grid')
ukadd(ukget('WTT- UK electricity', 'WTT- UK electricity (T&D)', 'Electricity: UK', 'kWh', '', 'kWh'), 'grid_td_loss_uk_wtt', 'UK electricity WTT (T&D)', 'energy', 'well-to-tank of T&D losses', 'UK grid')
ukadd(ukget('Heat and steam', 'Heat and steam', 'District heat and steam', 'kWh', '', 'kWh'), 'district_heat_steam', 'District heat and steam (Scope 2)', 'energy', 'generation only', 'UK average heat network')
ukadd(ukget('WTT- heat and steam', 'WTT- heat and steam', 'District heat and steam', 'kWh', '', 'kWh'), 'district_heat_steam_wtt', 'District heat and steam WTT', 'energy', 'well-to-tank', 'UK average heat network')
ukadd(ukget('Transmission and distribution', 'Distribution - district heat & steam', '5% loss', 'kWh', '', 'kWh'), 'district_heat_steam_distribution_loss', 'District heat distribution losses (5% loss)', 'energy', 'distribution losses', 'UK heat network')
# water
ukadd(ukget('Water supply', 'Water supply', 'Water supply', uom='cubic metres'), 'water_supply', 'Mains water supply', 'water', 'B7 operational water use (supply)', 'UK water industry average')
ukadd(ukget('Water treatment', 'Water treatment', 'Water treatment', uom='cubic metres'), 'water_treatment', 'Wastewater treatment', 'water', 'B7 operational water use (treatment)', 'UK water industry average')
# freight
for l3 in ['Rigid (>3.5 - 7.5 tonnes)', 'Rigid (>7.5 tonnes-17 tonnes)', 'Rigid (>17 tonnes)', 'Average non-refrigerated rigids', 'Articulated (>3.5 - 33t)', 'Articulated (>33t)', 'Average non-refrigerated artics', 'Average non-refrigerated HGVs']:
    for lad in ['50% Laden', '100% Laden', 'Average laden']:
        ukadd(ukget('Freighting goods', 'HGV (non-refrigerated, all diesel)', l3, '', lad, 'tonne.km'), 'transport_truck_freight', f'HGV non-refrigerated diesel {l3}, {lad}', 'transport', 'A4/C2 transport; tank-to-wheel (excl. WTT)', f'UK HGV fleet, {lad}')
for lad in ['50% Laden', '100% Laden', 'Average laden']:
    ukadd(ukget('WTT- delivery vehs & freight', 'WTT- HGV (non-refrigerated, all diesel)', 'Average non-refrigerated HGVs', '', lad, 'tonne.km'), 'transport_truck_freight_wtt', f'HGV non-refrigerated average WTT, {lad}', 'transport', 'WTT of diesel for A4/C2', f'UK HGV fleet, {lad}')
ukadd(ukget('Freighting goods', 'Vans', 'Average (up to 3.5 tonnes)', '', 'Diesel', 'tonne.km'), 'transport_van_freight', 'Freight van average up to 3.5 t, diesel', 'transport', 'A4 transport; tank-to-wheel', 'UK van fleet')
ukadd(ukget('Freighting goods', 'Rail', 'Freight train', '', '', 'tonne.km'), 'transport_rail_freight', 'Freight train', 'transport', 'A4/C2 transport; tank-to-wheel (incl. electric traction at UK grid)', 'UK rail freight average')
ukadd(ukget('WTT- delivery vehs & freight', 'WTT- rail', 'Freight train', '', '', 'tonne.km'), 'transport_rail_freight_wtt', 'Freight train WTT', 'transport', 'WTT for A4/C2', 'UK rail freight')
for l3, l4 in [('Bulk carrier', 'Average'), ('Bulk carrier', '0–9999 dwt'), ('General cargo', 'Average'), ('Container ship', 'Average'), ('RoRo-Ferry', 'Average')]:
    ukadd(ukget('Freighting goods', 'Cargo ship', l3, l4, '', 'tonne.km'), 'transport_ship_freight', f'Cargo ship {l3} {l4}', 'transport', 'A4 transport; tank-to-wheel', f'international shipping {l3} {l4}')
    if l4 == 'Average':
        ukadd(ukget('WTT- delivery vehs & freight', 'WTT- cargo ship', l3, l4, '', 'tonne.km'), 'transport_ship_freight_wtt', f'Cargo ship {l3} average WTT', 'transport', 'WTT for A4', f'international shipping {l3}')
# materials
MATS = [('Construction', 'Aggregates', 'aggregates'), ('Construction', 'Average construction', 'construction_material_average'), ('Construction', 'Asphalt', 'asphalt'),
        ('Construction', 'Bricks', 'clay_brick'), ('Construction', 'Concrete', 'concrete'), ('Construction', 'Insulation', 'insulation'), ('Construction', 'Metals', 'metals_construction'),
        ('Construction', 'Mineral oil', 'mineral_oil'), ('Construction', 'Plasterboard', 'plasterboard_drywall'), ('Construction', 'Wood', 'timber_wood'), ('Construction', 'Soils', 'soils'),
        ('Other', 'Glass', 'glass'), ('Metal', 'Metal: scrap metal', 'scrap_metal'), ('Plastic', 'Plastics: average plastics', 'plastics_average'),
        ('Plastic', 'Plastics: average plastic rigid', 'plastics_rigid'), ('Plastic', 'Plastics: PVC (incl. forming)', 'pvc'), ('Plastic', 'Plastics: HDPE (incl. forming)', 'hdpe'),
        ('Plastic', 'Plastics: PS (incl. forming)', 'polystyrene')]
for l2, l3, mk in MATS:
    for col, suffix, mod in [('Primary material production', '', 'cradle-to-gate (A1-A3) incl. transport to point of sale; biogenic CO2 excluded'),
                             ('Re-used', '_reused', 're-use: collection/sorting/processing and transport to point of sale'),
                             ('Closed-loop source', '_recycled_closed_loop', 'recycled (closed-loop source) material: sorting, reprocessing, manufacture, transport to point of sale; no avoided-burden credit')]:
        r = ukget('Material use', l2, l3, '', col, 'tonnes')
        if r[9] == '': continue
        ukadd(r, mk + suffix, f'{l3} - material use, {col}', 'material', mod, f'UK procured {l3.lower()}, {col.lower()}', notes='Kyoto basket; data sources are trade-association LCIs listed in DESNZ methodology Appendix 1.')
# waste
WST = [('Construction', 'Aggregates', 'aggregates'), ('Construction', 'Average construction', 'construction_average'), ('Construction', 'Asphalt', 'asphalt'), ('Construction', 'Bricks', 'clay_brick'),
       ('Construction', 'Concrete', 'concrete'), ('Construction', 'Insulation', 'insulation'), ('Construction', 'Metals', 'metals'), ('Construction', 'Plasterboard', 'plasterboard_drywall'),
       ('Construction', 'Wood', 'timber_wood'), ('Construction', 'Soils', 'soils'), ('Other', 'Glass', 'glass'), ('Plastic', 'Plastics: average plastics', 'plastics_average'),
       ('Refuse', 'Commercial and industrial waste', 'commercial_industrial_waste')]
pmap = {'Open-loop': 'recycling_open_loop', 'Closed-loop': 'recycling_closed_loop', 'Combustion': 'combustion', 'Landfill': 'landfill'}
for l2, l3, mk in WST:
    for col, p in pmap.items():
        r = ukget('Waste disposal', l2, l3, '', col, 'tonnes')
        if r[9] == '': continue
        mod = 'C2+C4 landfill: collection, transport and landfill emissions (gate-to-grave); biogenic CO2 excluded' if col == 'Landfill' else 'C2 only: transport to energy-recovery / materials reclamation facility (processing attributed to next user; no module D credit)'
        ukadd(r, f'waste_{mk}_{p}', f'{l3} - waste disposal, {col}', 'waste', mod, f'UK {col.lower()}', notes='GHG Protocol Scope 3 allocation (cut-off).')
# refrigerants
for l2, l3, key in [('Kyoto protocol products', 'HFC-32', 'refrigerant_gwp_r32'), ('Blends', 'R410A', 'refrigerant_gwp_r410a'), ('Kyoto protocol products', 'HFC-134a', 'refrigerant_gwp_r134a'),
                    ('Blends', 'R404A', 'refrigerant_gwp_r404a'), ('Blends', 'R407C', 'refrigerant_gwp_r407c'), ('Blends', 'R507A', 'refrigerant_gwp_r507a'),
                    ('Montreal protocol products', 'HCFC-22/R22 = chlorodifluoromethane', 'refrigerant_gwp_r22'), ('Other products', 'R1234ze*', 'refrigerant_gwp_r1234ze'),
                    ('Other products', 'R1234yf*', 'refrigerant_gwp_r1234yf'), ('Other products', 'R290 = propane', 'refrigerant_gwp_r290'), ('Other products', 'R600A = isobutane', 'refrigerant_gwp_r600a'),
                    ('Kyoto protocol products', 'Carbon dioxide', 'refrigerant_gwp_r744')]:
    r = ukget('Refrigerant & other', l2, l3, '', 'Total emissions including non-Kyoto products', 'kg')
    nt = 'Total incl. non-Kyoto components. '
    if '*' in l3: nt += 'Asterisk in source: AR5 GWP <1, shown rounded to 1. '
    if l3 == 'Carbon dioxide': nt += 'R744 = carbon dioxide. '
    ukadd(r, key, f'GWP {l3.rstrip("*")}', 'refrigerant', 'B1/B3 refrigerant leakage; C1 recovery losses', 'refrigerant release (mass emitted)', dtype='physical constant (IPCC)', ghg='IPCC AR5 GWP100', notes=nt)

with open(OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=HDR)
    w.writeheader()
    for r in rows: w.writerow(r)
import collections
print('rows', len(rows), 'with values', sum(1 for r in rows if str(r['value']) != ''))
print(collections.Counter((r['region'], r['rights_class']) for r in rows if str(r['value']) != ''))
print(collections.Counter(r['category'] for r in rows))
