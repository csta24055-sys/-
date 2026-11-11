import json, sys
R="/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/02_RANKING/axis_b_judges/"
names=("judge_algebraic_unification","judge_numerical_approximation","judge_input_data_model")
D={n: {r["id"]: r for r in json.load(open(R+n+".json",encoding="utf-8"))["scores"]} for n in names}
want = sys.argv[1:] 
for uid in want:
    print("=====", uid)
    for n in names:
        r = D[n][uid]
        print(f"  [{n.split('_',1)[1]}] b5={r['b5']} b6={r['b6']} b7={r['b7']} b8={r['b8']} | {r['replacement_idea']}")
