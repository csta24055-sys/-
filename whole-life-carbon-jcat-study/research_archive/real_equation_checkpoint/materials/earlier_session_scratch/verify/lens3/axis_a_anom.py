import json
R = "/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY"
m = json.load(open(R+"/02_RANKING/axis_a_measurements.json", encoding="utf-8"))
rows = []
for uid, r in m["units"].items():
    if not r["measured"]: 
        print("not measured", uid, r["not_measured_reason"]); continue
    t = r["time_ns"]; o = r["operations"]
    rows.append((uid, t["S"]/1e6, t["M"]/1e6, t["L"]/1e6, o["S"], o["M"], o["L"], t["L"]/o["L"], t["M"]/o["M"], r["time_share"]["L"], r["time_ns_min"]["L"]/1e6, r["time_ns_max"]["L"]/1e6))
rows.sort(key=lambda x: -x[7])
print("uid  tS tM tL  opsL  ns/op(L) ns/op(M) shareL minL maxL scaling tL/tM opsL/opsM")
for r in rows[:14]:
    print(f"{r[0]:8s} {r[1]:8.2f} {r[2]:8.2f} {r[3]:9.2f} {r[6]:11d} {r[7]:8.1f} {r[8]:8.1f} {r[9]*100:6.2f}% {r[10]:8.1f} {r[11]:8.1f}  {r[3]/r[2]:6.1f} {r[6]/r[5]:6.1f}")
tot = sum(r[3] for r in rows); print("sum of unit L times ms", tot, "total_time_ns L", m["total_time_ns"]["L"]/1e6)
# what would shares be if time were proportional to median ns/op
import statistics
med = statistics.median(r[7] for r in rows)
print("median ns/op L", med)
