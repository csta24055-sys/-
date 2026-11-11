import sys, os, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
OPT = {"generic_stage_check": True}
s0 = base(composite_share=0.0, epd_share=0.0)
ref0 = registry.run_all(s0)

def run(label, mut, units=None, opts=None, extra=None, src=None):
    s = copy.deepcopy(src or s0); mut(s)
    o = dict(OPT); o.update(opts or {})
    ref, me, bad = diff(s, opts=o, label=label, show=False, units=units)
    print(f"[{label}] diff={bad}")
    if extra and ref is not None and me is not None:
        extra(s, ref, me)
    return s, ref, me

def setunit(fid, unit, stages=None):
    def f(s):
        s.factors[fid].unit = unit
        if stages is not None:
            s.factors[fid].stages = stages
    return f
def show(uid, i, key="by_item"):
    def f(s, r, m):
        sy = r.get("SYS-02", {})
        print(f"   {uid}[{i}] base {ref0[uid][key][i]} | ref {r[uid][key][i]} n_skipped {r[uid].get('n_skipped')} | mine {m[uid][key][i]} n_skipped {m[uid].get('n_skipped')} | SYS-02 ok={sy.get('ok')} n_viol={len(sy.get('violations', []))}")
    return f
print("SYS-02 base:", {k: (v if not isinstance(v, list) else v[:3]) for k, v in ref0["SYS-02"].items()})
r0 = s0.materials[0]
# A4-01 transport factor
run("A4-01 transport factor unit 't' (not tkm)", setunit(r0.transport.factor_id, "t"), extra=show("A4-01", 0))
run("A4-01 transport factor unit 'kgkm'", setunit(r0.transport.factor_id, "kgkm"), extra=show("A4-01", 0))
run("A4-01 transport factor stages ['A1-A3']", setunit(r0.transport.factor_id, "tkm", ["A1-A3"]), extra=show("A4-01", 0))
# C2 haul
run("C2-01 haul factor unit 'kgkm'", setunit(r0.end_of_life.haul_factor_id, "kgkm"), extra=show("C2-01", 0))
# C3 / C4 route factor
rt = {x.route: x for x in r0.end_of_life.routes}
print("row0 routes", [(x.route, x.fraction, x.factor_id, s0.factors[x.factor_id].unit, s0.factors[x.factor_id].stages) for x in r0.end_of_life.routes])
run("C3-01 RECYCLE factor unit 't'", setunit(rt["RECYCLE"].factor_id, "t"), extra=show("C3-01", 0))
run("C3-01 RECYCLE factor unit 'm3' (no conversion)", setunit(rt["RECYCLE"].factor_id, "m3"), extra=show("C3-01", 0))
run("C4-01 LANDFILL factor unit 't'", setunit(rt["LANDFILL"].factor_id, "t"), extra=show("C4-01", 0))
run("C4-01 LANDFILL factor unit 'm3'", setunit(rt["LANDFILL"].factor_id, "m3"), extra=show("C4-01", 0))
def nofac(route):
    def f(s):
        for x in s.materials[0].end_of_life.routes:
            if x.route == route:
                x.factor_id = None
    return f
run("C3-01 RECYCLE factor_id None", nofac("RECYCLE"), extra=show("C3-01", 0))
run("C4-01 LANDFILL factor_id None", nofac("LANDFILL"), extra=show("C4-01", 0))
def badid(route):
    def f(s):
        for x in s.materials[0].end_of_life.routes:
            if x.route == route:
                x.factor_id = "F-DOES-NOT-EXIST"
    return f
run("C3-01 RECYCLE factor id unknown", badid("RECYCLE"), extra=show("C3-01", 0))
# X-14
e0 = s0.equipment[0]
run("X-14 eol factor unit 't'", setunit(e0.eol_factor_id, "t"), extra=show("X-14", 0))
run("X-14 eol factor unit 'm3'", setunit(e0.eol_factor_id, "m3"), extra=show("X-14", 0))
# material installation factor
r1 = s0.materials[1]
print("row1", r1.quantity_unit, r1.installation_factor_id, s0.factors[r1.installation_factor_id].unit, [(c.from_unit, c.to_unit, c.factor) for c in r1.conversions])
run("B4-02 material installation factor unit 'kg' (row unit t; t->kg exists)", setunit(r1.installation_factor_id, "kg"), extra=show("B4-02", 1, "by_item_material"))
run("B4-02 material installation factor unit 'zz' (no conversion)", setunit(r1.installation_factor_id, "zz"), extra=show("B4-02", 1, "by_item_material"))
# A4-02 delivery factor
r3 = s0.materials[3]
print("row3", r3.quantity_unit, r3.transport.delivery_factor_id, s0.factors[r3.transport.delivery_factor_id].unit, s0.factors[r3.transport.delivery_factor_id].stages)
run("A4-02 delivery factor unit 'kg' (row unit t)", setunit(r3.transport.delivery_factor_id, "kg"), extra=show("A4-02", 3))
run("A4-02 delivery factor unit 'zz'", setunit(r3.transport.delivery_factor_id, "zz"), extra=show("A4-02", 3))
run("A4-02 delivery factor stages ['A1-A3']", setunit(r3.transport.delivery_factor_id, "t", ["A1-A3"]), extra=show("A4-02", 3))
# row with delivery factor AND mass/distance: exclusivity
def both(s):
    pass
print("row3 transport", r3.transport)
run("A4: delivery factor unlicensed -> falls back to A4-01?", lambda s: s.factors[r3.transport.delivery_factor_id].__setattr__("licence_status", "UNKNOWN"), extra=lambda s, r, m: print("   ref A4-01[3]", r["A4-01"]["by_item"][3], "A4-02[3]", r["A4-02"]["by_item"][3], "n_skipped", r["A4-01"]["n_skipped"], r["A4-02"]["n_skipped"]))
