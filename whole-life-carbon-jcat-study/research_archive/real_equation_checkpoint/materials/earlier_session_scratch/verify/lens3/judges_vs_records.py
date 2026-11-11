import json, statistics, collections
R="/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/"
names=("judge_algebraic_unification","judge_numerical_approximation","judge_input_data_model")
D={n: {r["id"]: r for r in json.load(open(R+"02_RANKING/axis_b_judges/"+n+".json",encoding="utf-8"))["scores"]} for n in names}
led={u["id"]: u for u in json.load(open(R+"05_DECISIONS/progress_ledger.json",encoding="utf-8"))["units"]}
med=lambda uid,c: statistics.median(D[n][uid][c] for n in names)
mx=lambda uid,c: max(D[n][uid][c] for n in names)
con=lambda uid,s: led[uid]["steps"][s]["conclusion"]
ids=list(led)
a=[u for u in ids if med(u,"b6")>=2 and con(u,"M3")=="NOT_APPLICABLE"]
print("median b6>=2 (clearly replaceable by a simple linear/polynomial/interpolation model) but M3 = NOT_APPLICABLE:", len(a), a)
b=[u for u in ids if med(u,"b5")>=2 and con(u,"M3")=="NOT_APPLICABLE"]
print("median b5>=2 (branches replaceable by approximation) but M3 = NOT_APPLICABLE:", len(b), b)
c=[u for u in ids if med(u,"b7")>=2 and con(u,"M4") in ("NOT_APPLICABLE",)]
print("median b7>=2 (inputs can clearly be reduced) but M4 = NOT_APPLICABLE:", len(c), c)
c2=[u for u in ids if med(u,"b7")>=2]
print("median b7>=2 units:", len(c2), {u: (con(u,"M3"),con(u,"M4"),con(u,"M5"),con(u,"M6")) for u in c2})
d=[u for u in ids if med(u,"b8")>=2 and con(u,"M4")=="NOT_APPLICABLE" and con(u,"M5")=="NOT_APPLICABLE"]
print("median b8>=2 (common surrogate) but M4 and M5 both NOT_APPLICABLE:", len(d), d)
e=[(u,[c for c in ("b5","b6","b7","b8") if mx(u,c)==3]) for u in ids if any(mx(u,c)==3 for c in ("b5","b6","b7","b8")) and all(con(u,s) in ("NOT_APPLICABLE","NOT_DONE") for s in ("M3","M4","M5")) ]
print("some judge scored 3 on b5-b8 (concrete replacement idea) but M3, M4, M5 all NOT_APPLICABLE/NOT_DONE:", len(e), e)
tot=collections.Counter()
for u in ids:
    for cc in ("b5","b6","b7","b8"):
        if mx(u,cc)==3: tot[cc]+=1
print("units with a max score of 3 per criterion:", dict(tot))
