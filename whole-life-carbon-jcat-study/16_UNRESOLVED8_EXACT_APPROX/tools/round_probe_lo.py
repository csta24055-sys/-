"""LibreOffice's ROUND / ROUNDDOWN / ROUNDUP on the discriminating inputs of round_probe.xlsx (a copy; never saved).
Usage: round_probe_lo.py <copy.xlsx> <round_probe.json> <out.json> <port>"""
import os, sys, json
sys.dont_write_bytecode = True
S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(S, "conv")); sys.path.insert(0, os.path.join(S, "jcat_tools"))
import lo_engine

xlsx, js, outp, port = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
rows = json.load(open(js))
lo = lo_engine.LO(port, os.path.join(S, "lo", "lo_profile_%d" % port))
lo.load(xlsx)
lo.recalc()
sh = lo.sheets["round_probe"]
res = []
for i, o in enumerate(rows):
    x = sh.getCellByPosition(0, i + 1).getValue()
    v = sh.getCellByPosition(3, i + 1).getValue()
    res.append(dict(o, LO=v, x_read_by_LO=repr(x), read_exact=(repr(x) == o["x"])))
lo.close()
bad_read = sum(1 for o in res if not o["read_exact"])
res = [o for o in res if o["read_exact"]]       # compare only where LibreOffice read the same double
c = dict(read_differently=bad_read, n=len(res), LO_eq_M15=sum(1 for o in res if o["LO"] == o["M15"]), LO_eq_BIN=sum(1 for o in res if o["LO"] == o["BIN"]),
         LO_eq_HU=sum(1 for o in res if o["LO"] == o["HU"]),
         A_ne_B=sum(1 for o in res if o["M15"] != o["HU"]),
         A_ne_B__LO_eq_A=sum(1 for o in res if o["M15"] != o["HU"] and o["LO"] == o["M15"]),
         A_ne_B__LO_eq_B=sum(1 for o in res if o["M15"] != o["HU"] and o["LO"] == o["HU"]))
json.dump(dict(summary=c, rows=res), open(outp, "w"), indent=0)
print(c)
