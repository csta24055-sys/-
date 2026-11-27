# Coefficient research brief (shared by all research agents)

Goal: collect REAL numeric emission factors and life-cycle parameters, from primary public sources worldwide,
for an independent building whole-life-carbon model (Japan is the target; foreign values are kept with their region,
never silently used as Japanese defaults). Do NOT use J-CAT (IBECs) data, AIJ-LCA defaults copied via J-CAT, or IDEA values.

## Rules
- Primary sources only: government agencies, official databases, universities/research institutes, peer-reviewed
  papers, manufacturers' published EPDs, open-data portals. Record the exact URL you actually read/downloaded.
- Never circumvent terms: no login bypass, no paywalled content, no scraping that the site's terms forbid.
  Free downloads (xlsx/csv/pdf/API) that the publisher offers openly are fine. Use `curl -sL` to download files into
  the downloads directory given in your task, then read them with python3 -I (openpyxl may be missing: use
  `python3 -m pip install --user openpyxl` if needed, or read csv/pdf text).
- For each value record: numeric value, unit, declared/functional unit, GHG basis (CO2e and which GWP set, or CO2 only),
  life-cycle modules covered (A1-A3, A4, C3, D...; for fuels: combustion only / well-to-tank / both), region,
  production route/technology, reference year / validity, data type (generic average / conservative default /
  product-specific EPD / statistical estimate), source organisation, title, edition/version, URL, retrieval date 2026-11-27.
- Prefer several independent sources for the same item (e.g. concrete from ÖKOBAUDAT AND Boverket AND an EPD).
- If a value cannot be obtained, still write a row with value empty, and state: source tried, reason (not published /
  blocked HTTP code / paywall / licence forbids), and an alternative candidate.
- Licence: read the source's terms page and classify EVERY row:
  1 = embeddable in a public app (open licence allowing commercial use AND redistribution with attribution: CC0, CC BY 4.0,
      UK OGL v3, US federal public domain, Etalab Licence Ouverte 2.0, dl-de/by-2-0, Japanese PDL1.0 / 政府標準利用規約2.0)
  2 = research/validation use only (non-commercial licence, or terms allow use but forbid redistribution/commercial)
  3 = external reference only (copyrighted document without an open licence, e.g. a manufacturer EPD PDF or a paper:
      an individual value may be cited with attribution, the dataset may not be incorporated/redistributed)
  4 = terms not confirmed
  5 = not usable (explicit prohibition, paid licence)
  Also fill the separate yes/no/unknown flags: cite_single_value, research_use, db_incorporation, commercial_use, redistribution.

## Output (mandatory)
Write ONE CSV file (UTF-8, comma separated, header exactly as below, one row per value) at the path given in your task:
factor_key,item,category,value,unit,declared_unit,ghg_basis,modules,region,technology_or_route,reference_year,data_type,source_org,source_title,edition_version,url,retrieved,licence_name,licence_url,cite_single_value,research_use,db_incorporation,commercial_use,redistribution,rights_class,notes

- factor_key: snake_case key from the demand list (e.g. concrete_ready_mix_c30_37, rebar, refrigerant_gwp_r32,
  grid_electricity_jp, service_life_chiller). Use the same key for the same item across sources.
- category: material | equipment | energy | transport | waste | water | refrigerant | lifetime | repair | storage | eeio | other
- value must be a plain number (no thousand separators). Use the source's unit as given (convert nothing; note conversions in notes).
Then reply with a short summary: number of rows with values, per rights class, and the list of items not obtained.
