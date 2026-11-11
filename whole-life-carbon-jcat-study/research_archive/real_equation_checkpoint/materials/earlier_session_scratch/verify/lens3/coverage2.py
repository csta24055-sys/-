import json, collections
R = "/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY"
J = lambda p: json.load(open(R+"/"+p, encoding="utf-8"))
cov = J("01_LEDGER/sheet_family_coverage.json"); units = J("01_LEDGER/units.json")["units"]
fam_units = {f["family_id"]: set(f["related_units"]) for f in cov["families"]}
name = {f["family_id"]: f["family"] for f in cov["families"]}
status = {f["family_id"]: f["status"] for f in cov["families"]}
unit_fams = collections.defaultdict(set)
for u in units:
    for x in u.get("sheet_family_links") or []:
        unit_fams[x].add(u["id"])
n_dis = 0
for fid in sorted(set(fam_units) | set(unit_fams)):
    a, b = fam_units.get(fid, set()), unit_fams.get(fid, set())
    if a != b:
        n_dis += 1
        print(fid, name.get(fid), status.get(fid), "| coverage.related_units only:", sorted(a - b), "| units.sheet_family_links only:", sorted(b - a))
print("families where the two files disagree:", n_dis, "of", len(fam_units))
# units claimed EXISTING-covered etc
print("status counts:", collections.Counter(status.values()))
# top family
top = max(cov["families"], key=lambda f: f["formula_xml_nodes"]); print(top["family_id"], top["family"], top["related_units"], top["status"], top["note"])
print("units linking to SF-01:", sorted(unit_fams.get(top["family_id"], [])))
