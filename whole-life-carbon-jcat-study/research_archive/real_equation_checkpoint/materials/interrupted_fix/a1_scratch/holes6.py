import copy, synth
from refcalc import registry
registry.load_all()
s = synth.make_scenario(11, "RC", "office", "S", 60.0, n_materials=12, n_equipment=6, n_refrigerants=4, included_stages=["B3"])
r0 = registry.run_all(s)
order = sorted(range(len(s.materials)), key=lambda i: -(r0["A13-01"]["by_item"][i] + r0["A13-03"]["by_item"][i]))
for i in order[:3]: s.materials[i].quantity = -abs(s.materials[i].quantity)
r1 = registry.run_all(s)
print("B3-only, 3 largest rows with negative quantity: SUM-03", r0["SUM-03"]["value"], "->", r1["SUM-03"], "X-02", r1["X-02"]["complete"], r1["X-02"]["incomplete_units"],
      "| gates SYS-01", r1["SYS-01"]["ok"], "SYS-02", r1["SYS-02"]["ok"], "SYS-03", r1["SYS-03"]["ok"], "QA-01", r1["QA-01"]["ok"], "QA-02", r1["QA-02"]["ok"], "QA-03", r1["QA-03"]["ok"], "C-05", r1["C-05"]["ok"],
      "| A13-05 n_skipped", r1["A13-05"]["n_skipped"], "A13-01 n_skipped", r1["A13-01"]["n_skipped"], "B3-01 n_skipped", r1["B3-01"]["n_skipped"])
