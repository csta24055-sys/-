import json, os, sys
R = "/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY"
def shape(x, depth=0, maxd=3):
    pad = "  "*depth
    if isinstance(x, dict):
        ks = list(x.keys())
        print(pad + f"dict[{len(ks)}] keys={ks[:25]}")
        if depth < maxd:
            for k in ks[:6]:
                print(pad + f" .{k}:")
                shape(x[k], depth+1, maxd)
    elif isinstance(x, list):
        print(pad + f"list[{len(x)}]")
        if x and depth < maxd:
            shape(x[0], depth+1, maxd)
    else:
        s = repr(x)
        print(pad + s[:160])
for f in ["03_MODELS/records/units.json","03_MODELS/models.json","03_MODELS/candidates.json","05_DECISIONS/progress_ledger.json",
          "04_VERIFICATION/approximation_study.json","04_VERIFICATION/unified_model_load.json","04_VERIFICATION/unified_model_exactness.json",
          "02_RANKING/axis_a.json","02_RANKING/axis_b.json","02_RANKING/research_priority.json","02_RANKING/axis_a_measurements.json","02_RANKING/axis_b_input_digest.json",
          "01_LEDGER/units.json","01_LEDGER/sheet_families.json","01_LEDGER/sheet_family_coverage.json","01_LEDGER/considered_not_adopted.json","01_LEDGER/unlinked_input_disposition.json"]:
    p = os.path.join(R, f)
    print("=====", f, os.path.getsize(p))
    shape(json.load(open(p, encoding="utf-8")), 0, 2)
