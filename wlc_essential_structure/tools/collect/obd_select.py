"""Select ÖKOBAUDAT 2024-III datasets from the CSV export and emit JSON of values."""
import csv, json, sys

CSV = sys.argv[1]
OUT = sys.argv[2]

# (factor_key, exact name (de), Typ or None, item (en), category, modules wanted, biogenic split)
SEL = [
 ("concrete_ready_mix_c20_25", "Transportbeton C20/25", "generic dataset", "Ready-mix concrete C20/25", "material", ["A1-A3","C3"], False),
 ("concrete_ready_mix_c25_30", "Transportbeton C25/30", "generic dataset", "Ready-mix concrete C25/30", "material", ["A1-A3","C3"], False),
 ("concrete_ready_mix_c30_37", "Transportbeton C30/37", "generic dataset", "Ready-mix concrete C30/37", "material", ["A1-A3","C3"], False),
 ("concrete_ready_mix_c50_60", "Transportbeton C50/60", "generic dataset", "Ready-mix concrete C50/60", "material", ["A1-A3"], False),
 ("concrete_ready_mix_c30_37_rc", "Recycling Transportbeton C30/37", "generic dataset", "Ready-mix concrete C30/37 with recycled aggregate", "material", ["A1-A3"], False),
 ("concrete_ready_mix_c20_25", "Beton der Druckfestigkeitsklasse C20/25", "average dataset", "Ready-mix concrete C20/25 (IZB industry average)", "material", ["A1-A3"], False),
 ("concrete_ready_mix_c25_30", "Beton der Druckfestigkeitsklasse C25/30", "average dataset", "Ready-mix concrete C25/30 (IZB industry average)", "material", ["A1-A3"], False),
 ("concrete_ready_mix_c30_37", "Beton der Druckfestigkeitsklasse C30/37", "average dataset", "Ready-mix concrete C30/37 (IZB industry average)", "material", ["A1-A3"], False),
 ("concrete_ready_mix_c35_45", "Beton der Druckfestigkeitsklasse C35/45", "average dataset", "Ready-mix concrete C35/45 (IZB industry average)", "material", ["A1-A3"], False),
 ("concrete_ready_mix_c45_55", "Beton der Druckfestigkeitsklasse C45/55", "average dataset", "Ready-mix concrete C45/55 (IZB industry average)", "material", ["A1-A3"], False),
 ("cement_cem_i", "Portlandzement CEM I - Hydraulischer Zement", "average dataset", "Portland cement CEM I (VDZ average)", "material", ["A1-A3"], False),
 ("cement_cem_ii", "Zement (CEM II 42,5)", "generic dataset", "Cement CEM II 42,5", "material", ["A1-A3"], False),
 ("cement_cem_ii_a", "Zement (CEM II/A)", "generic dataset", "Cement CEM II/A", "material", ["A1-A3"], False),
 ("cement_cem_ii_b", "Zement (CEM II/B)", "generic dataset", "Cement CEM II/B", "material", ["A1-A3"], False),
 ("cement_cem_iii", "Zement (CEM III 42,5)", "generic dataset", "Cement CEM III 42,5", "material", ["A1-A3"], False),
 ("cement_cem_iii", "Hochofenzement CEM III/A - Hydraulischer Zement", "average dataset", "Blast-furnace cement CEM III/A (VDZ average)", "material", ["A1-A3"], False),
 ("cement_average_de", "Durchschnittlicher Zement D - Zement als Bindemittel", "average dataset", "Average cement Germany (VDZ)", "material", ["A1-A3"], False),
 ("rebar", "Bewehrungsstahl", "generic dataset", "Reinforcing steel (rebar)", "material", ["A1-A3","C3"], False),
 ("rebar", "Betonstahl in Ringen und Betonstabstahl", "average dataset", "Reinforcing steel coils and bars (Baustahlgewebe)", "material", ["A1-A3"], False),
 ("steel_section", "Baustahl: Profile und Stabstahl", "average dataset", "Structural steel sections and merchant bars (bauforumstahl average)", "material", ["A1-A3"], False),
 ("steel_section_galvanised", "Stahlprofil verzinkt (Elektrolichtbogenroute, hoher Schrottanteil)", "generic dataset", "Galvanised steel section, EAF route", "material", ["A1-A3"], False),
 ("steel_section_galvanised", "Stahlprofil verzinkt (Hochofenroute, geringer Schrottanteil)", "generic dataset", "Galvanised steel section, BF/BOF route", "material", ["A1-A3"], False),
 ("steel_section_galvanised", "Feuerverzinkte Baustähle: Stahlprofile und Stabstähle", "average dataset", "Hot-dip galvanised structural steel sections (IFV average)", "material", ["A1-A3"], False),
 ("steel_plate_heavy", "Baustahl: Grobblech", "average dataset", "Structural steel heavy plate (bauforumstahl average)", "material", ["A1-A3"], False),
 ("steel_sheet", "Stahl Feinblech (0,3-3,0mm)", "generic dataset", "Steel thin sheet 0.3-3.0 mm", "material", ["A1-A3"], False),
 ("steel_sheet_hot_rolled", "Stahl warmgewalzte Bleche (2-20mm)", "generic dataset", "Steel hot-rolled plate 2-20 mm", "material", ["A1-A3"], False),
 ("steel_sheet_galvanised", "Stahl Feinblech (20µm bandverzinkt)", "generic dataset", "Steel thin sheet strip-galvanised 20 um", "material", ["A1-A3"], False),
 ("steel_sheet_galvanised", "Feuerverzinktes Stahlblech", "generic dataset", "Hot-dip galvanised steel sheet", "material", ["A1-A3"], False),
 ("timber_sawn_softwood", "Schnittholz Fichte (generisch, 12% Feuchte/10.7% H2O)", "generic dataset", "Sawn timber spruce (softwood), 12% moisture", "material", ["A1-A3","C3"], True),
 ("timber_sawn_softwood_kvh", "Konstruktionsvollholz (generisch, 15% Feuchte / 13% H2O)", "generic dataset", "Structural solid timber (KVH), softwood", "material", ["A1-A3","C3"], True),
 ("glulam", "Brettschichtholz Nadelholz (generisch)", "generic dataset", "Glued laminated timber, softwood", "material", ["A1-A3","C3"], True),
 ("glulam", "Brettschichtholz - Standardformen (Durchschnitt DE)", "representative dataset", "Glued laminated timber standard shapes (Thünen DE average)", "material", ["A1-A3","C3"], True),
 ("clt", "Brettsperrholz (Durchschnitt DE)", None, "Cross-laminated timber (Thünen DE average)", "material", ["A1-A3","C3"], True),
 ("float_glass", "Fensterglas einfach", "generic dataset", "Single window glass (float)", "material", ["A1-A3","C4"], False),
 ("float_glass", "Flachglas - Bundesverband Flachglas e.V. - Floatglas", "template dataset", "Float glass (Bundesverband Flachglas template)", "material", ["A1-A3"], False),
 ("igu_double", "Isolierglas 2-Scheiben", "generic dataset", "Insulating glass unit, double", "material", ["A1-A3","C4"], False),
 ("igu_triple", "Dreifachverglasung", "generic dataset", "Insulating glass unit, triple", "material", ["A1-A3","C4"], False),
 ("igu_double", "Flachglas - Bundesverband Flachglas e.V. - Mehrscheibenisolierglas 2-fach-Aufbau", "average dataset", "Double IGU (Bundesverband Flachglas average)", "material", ["A1-A3"], False),
 ("igu_triple", "Flachglas - Bundesverband Flachglas e.V. - Mehrscheibenisolierglas 3-fach-Aufbau", "average dataset", "Triple IGU (Bundesverband Flachglas average)", "material", ["A1-A3"], False),
 ("aluminium_sheet", "Aluminiumblech", "generic dataset", "Aluminium sheet", "material", ["A1-A3"], False),
 ("aluminium_extrusion", "Aluminium Profil", "generic dataset", "Aluminium extruded profile", "material", ["A1-A3"], False),
 ("window_frame_aluminium", "Aluminium-Rahmenprofil, thermisch getrennt, pulverbeschichtet", "generic dataset", "Aluminium window frame profile, thermally broken, powder coated", "material", ["A1-A3"], False),
 ("window_aluminium", "Fenster - VFF - Fenster aus Aluminium", "average dataset", "Aluminium window (VFF average, per m2 window)", "material", ["A1-A3"], False),
 ("gypsum_plasterboard", "GIPSPLATTE NACH DIN EN 520 UND DIN 18180 / Tool", "average dataset", "Gypsum plasterboard EN 520 (BV Gips average)", "material", ["A1-A3"], False),
 ("gypsum_plasterboard", "Gipsbauplatte (imprägniert, 12,5mm)", "generic dataset", "Gypsum plasterboard impregnated 12.5 mm", "material", ["A1-A3","C4"], False),
 ("mineral_wool_generic", "Mineralwolle (Fassaden-Dämmung)", "generic dataset", "Mineral wool, facade insulation", "material", ["A1-A3","C4"], False),
 ("mineral_wool_generic", "Mineralwolle (Innenausbau-Dämmung)", "generic dataset", "Mineral wool, interior insulation", "material", ["A1-A3","C4"], False),
 ("mineral_wool_stone", "Steinwolle Flachdämmplatte", "generic dataset", "Stone wool flat insulation board", "material", ["A1-A3","C4"], False),
 ("mineral_wool_stone", "ROCKWOOL Steinwolle-Dämmstoffe im mittleren Rohdichtebereich", "average dataset", "Stone wool medium density (Rockwool DE average)", "material", ["A1-A3"], False),
 ("mineral_wool_glass", "SAGLAN Glaswolle, phenolharzgebunden +A2", "average dataset", "Glass wool phenolic binder (Sager AG, CH)", "material", ["A1-A3"], False),
 ("eps", "EPS-Hartschaumdämmung", "generic dataset", "EPS insulation", "material", ["A1-A3","C3"], False),
 ("eps", "EPS-Hartschaum (Rohdichte 20 kg/m³)", "average dataset", "EPS insulation 20 kg/m3 (industry average)", "material", ["A1-A3"], False),
 ("xps", "Extrudierter Polystyrol Dämmstoff (XPS)", "generic dataset", "XPS insulation", "material", ["A1-A3","C3"], False),
 ("pur_pir", "PUR Hartschaum", "generic dataset", "PUR rigid foam insulation", "material", ["A1-A3","C3"], False),
 ("pur_pir", "PIR Hartschaum", "generic dataset", "PIR rigid foam insulation", "material", ["A1-A3","C3"], False),
 ("pipe_pvc", "Abwasserrohr PVC", "generic dataset", "PVC waste-water pipe", "material", ["A1-A3","C3"], False),
 ("pipe_pe", "Abwasserrohr PE-HD", "generic dataset", "HDPE waste-water pipe", "material", ["A1-A3","C3"], False),
 ("pipe_pe", "Trinkwasserrohr PE-X", "generic dataset", "PE-X drinking-water pipe", "material", ["A1-A3"], False),
 ("paint_wall_dispersion", "Innendispersionsfarbe scheuerfest", "generic dataset", "Interior dispersion wall paint", "material", ["A1-A3"], False),
 ("paint_facade_dispersion", "Fassadenfarbe Dispersionsfarbe", "generic dataset", "Facade dispersion paint", "material", ["A1-A3"], False),
 ("copper_sheet", "Kupferbleche", "generic dataset", "Copper sheet", "material", ["A1-A3"], False),
 ("cable_copper", "Kabel 3-adrig", "generic dataset", "Electric cable, 3-core (per m)", "material", ["A1-A3"], False),
 ("ceramic_tiles", "Steinzeugfliesen glasiert", "generic dataset", "Glazed stoneware tiles", "material", ["A1-A3"], False),
 ("ceramic_tiles", "Keramische Fliesen und Platten", "average dataset", "Ceramic tiles and slabs (BV Keramische Fliesen average)", "material", ["A1-A3"], False),
 ("brick", "Vormauerziegel", "generic dataset", "Facing brick", "material", ["A1-A3"], False),
 ("brick", "Mauerziegel (ungefüllt)", "average dataset", "Clay masonry brick, unfilled (Ziegelindustrie average)", "material", ["A1-A3"], False),
 ("heat_pump_air_water", "Strom-Wärmepumpe (Luft-Wasser) 10 kW", "generic dataset", "Electric heat pump air-water 10 kW (unit)", "equipment", ["A1-A3"], False),
 ("heat_pump_ground_source", "Strom-Wärmepumpe (Sole-Wasser, Erdsonde) 10 kW", "generic dataset", "Electric heat pump brine-water (borehole) 10 kW (unit)", "equipment", ["A1-A3"], False),
 ("ventilation_unit", "Lüfter zentral mit WRG 1000 m3/h", "generic dataset", "Central ventilation unit with heat recovery 1000 m3/h", "equipment", ["A1-A3"], False),
 ("ventilation_unit", "Lüfter zentral mit WRG 5000 m3/h", "generic dataset", "Central ventilation unit with heat recovery 5000 m3/h", "equipment", ["A1-A3"], False),
 ("radiators", "Heizkörper", "generic dataset", "Radiator (steel panel)", "equipment", ["A1-A3"], False),
 ("pv_system", "Photovoltaiksystem 1000 kWh/m2*a ohne Stromgutschrift", "generic dataset", "PV system (per m2 module area)", "equipment", ["A1-A3"], False),
 ("grid_electricity_de", "Strom für Gebäudebetrieb 2023", "generic dataset", "Electricity for building operation, Germany 2023", "energy", ["B6"], False),
 ("natural_gas_heat_de", "Thermische Energie aus Erdgas", "generic dataset", "Thermal energy from natural gas (DE)", "energy", ["B6"], False),
 ("heating_oil_heat_de", "Thermische Energie aus Heizöl el", "generic dataset", "Thermal energy from light heating oil (DE)", "energy", ["B6"], False),
 ("district_heating_de", "Fernwärme Mix Deutschland", "generic dataset", "District heating, German mix", "energy", ["B6"], False),
 ("transport_truck_tkm", "LKW", "generic dataset", "Truck transport", "transport", ["A4"], False),
 ("transport_truck_trailer_tkm", "LKW-Zug", "generic dataset", "Truck-trailer transport", "transport", ["A4"], False),
 ("transport_rail_tkm", "Bahntransport", "generic dataset", "Rail freight transport", "transport", ["A4"], False),
 ("waste_inert_landfill", "Bauschutt-Deponierung", "generic dataset", "Landfill of construction rubble", "waste", ["C4"], False),
 ("waste_rubble_processing", "Bauschuttaufbereitung", "generic dataset", "Processing of construction rubble", "waste", ["C3"], False),
 ("waste_wood_incineration", "Verbrennung Holz naturbelassen in MVA", "generic dataset", "Incineration of untreated wood in MSWI", "waste", ["C3"], True),
 ("waste_plastic_incineration", "Verbrennung Kunststoff in MVA inkl. Gutschrift", "generic dataset", "Incineration of plastics in MSWI", "waste", ["C3"], False),
]

rows = list(csv.DictReader(open(CSV, encoding="cp1252", errors="replace"), delimiter=";"))
out = []
for key, name, typ, item, cat, mods, bio in SEL:
    cand = [r for r in rows if r["Name (de)"].strip() == name and (typ is None or r["Typ"] == typ)]
    if not cand:
        out.append({"key": key, "name": name, "missing": True, "item": item, "cat": cat})
        continue
    uuid = cand[0]["UUID"]
    cand = [r for r in cand if r["UUID"] == uuid]
    for m in mods:
        mr = [r for r in cand if r["Modul"] == m]
        if not mr:
            out.append({"key": key, "name": name, "module": m, "missing": True, "item": item, "cat": cat, "uuid": uuid})
            continue
        r = mr[0]
        base = {k: r[k] for k in ["UUID", "Version", "Name (de)", "Name (en)", "Typ", "Referenzjahr", "Gueltig bis", "URL",
                                  "Declaration owner", "Registrierungsnummer", "Laenderkennung", "Bezugsgroesse", "Bezugseinheit",
                                  "Referenzfluss-Name", "Rohdichte (kg/m3)", "Flaechengewicht (kg/m2)", "Umrechungsfaktor auf 1kg",
                                  "biogener Kohlenstoffgehalt in kg", "Konformitaet", "Hintergrunddatenbank(en)", "Szenario", "Szenariobeschreibung",
                                  "Laengengewicht (kg/m)", "Stueckgewicht (kg)", "Schuettdichte (kg/m3)"]}
        base.update({"key": key, "item": item, "cat": cat, "module": m, "n_scen": len(mr),
                     "GWPtotal": r["GWPtotal (A2)"], "GWPfossil": r["GWPfossil (A2)"], "GWPbiogenic": r["GWPbiogenic (A2)"],
                     "GWPluluc": r["GWPluluc (A2)"], "GWP_A1": r["GWP"], "bio": bio})
        out.append(base)
json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
for o in out:
    if o.get("missing"):
        print("MISSING", o["key"], o["name"], o.get("module"))
    else:
        print(o["key"], "|", o["Name (de)"][:50], "|", o["module"], "|", o["Bezugsgroesse"], o["Bezugseinheit"], "|", o["GWPtotal"], o["GWPfossil"], o["GWPbiogenic"], "| A1:", o["GWP_A1"], "| scen", o["n_scen"], o["Szenario"])
