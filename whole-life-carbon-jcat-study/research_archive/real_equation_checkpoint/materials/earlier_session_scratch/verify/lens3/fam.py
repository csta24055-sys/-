import json, collections
R="/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/"
cov=json.load(open(R+"01_LEDGER/sheet_family_coverage.json",encoding="utf-8"))
c=collections.Counter(); z=collections.defaultdict(list); nz=collections.Counter()
for f in cov["families"]:
    c[f["status"]]+=1
    if f["formula_xml_nodes"]==0: z[f["status"]].append(f["family"])
    else: nz[f["status"]]+=1
print("by status:", dict(c)); print("with formulas by status:", dict(nz), "total with formulas:", sum(nz.values()))
print("zero-node families by status:", {k:(len(v),v) for k,v in z.items()})
tot=sum(f["formula_xml_nodes"] for f in cov["families"]); print("total nodes", tot)
print("existing-covered share %.2f%%" % (100*sum(f["formula_xml_nodes"] for f in cov["families"] if f["status"]=="COVERED_BY_EXISTING")/tot))
