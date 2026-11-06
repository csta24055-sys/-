#!/usr/bin/env python3
"""単語ドリル（出題→採点→単語ごとの習熟度を記録）。

  python3 drill.py make v1 --n 25 --seed 1      # 問題を作り data/quiz_<id>.json に解答を保存
  python3 drill.py grade <quiz_id> "1=Ao 2=Cd ..."  # 採点、data/vocab_state.json を更新
  python3 drill.py status v1                     # 単語ごとの習熟度（box 0-3）一覧

習熟度 box: 正解(o/d)で+1、誤答で0に戻る、勘の正解は据え置き。box>=2 を「定着」とみなす。
"""
import argparse, csv, datetime, json, os, random, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
LET = "ABCDE"


def words(set_id):
    return json.load(open(os.path.join(HERE, f"words_{set_id}.json"), encoding="utf-8"))["words"]


def state():
    p = os.path.join(DATA, "vocab_state.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


def save_state(s):
    json.dump(s, open(os.path.join(DATA, "vocab_state.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def first(x):
    return x.split("/")[0].strip()


def make(a):
    ws = words(a.set_id)
    rng = random.Random(a.seed)
    st = state()
    # 習熟度の低い単語を優先して出題
    pool = sorted(ws, key=lambda w: (st.get(w["w"], {}).get("box", 0), rng.random()))[: a.n]
    rng.shuffle(pool)
    qs = []
    for w in pool:
        kinds = ["ja"] + (["syn"] if w["syn"] else []) + (["ant"] if w["ant"] else [])
        k = rng.choice(kinds)
        if k == "ja":
            others = rng.sample([x["ja"] for x in ws if x is not w], 4)
            opts, ans = others + [w["ja"]], w["ja"]
            prompt = f"{w['w']} の意味"
        else:
            ans = first(w[k])
            # 紛らわしさ：反意語問題には同意語を、同意語問題には反意語を混ぜる
            trap = first(w["ant" if k == "syn" else "syn"]) if w["ant" if k == "syn" else "syn"] else None
            cand = [first(x["syn"]) for x in ws if x is not w and x["syn"]] + \
                   [first(x["ant"]) for x in ws if x is not w and x["ant"]]
            cand = [c for c in cand if c not in (ans, trap)]
            others = ([trap] if trap else []) + rng.sample(cand, 4 - (1 if trap else 0))
            opts = others + [ans]
            prompt = f"{w['w']} の{'同意語' if k == 'syn' else '反意語'}"
        rng.shuffle(opts)
        qs.append({"word": w["w"], "kind": k, "prompt": prompt, "opts": opts, "ans": LET[opts.index(ans)]})
    qid = f"{a.set_id}-{datetime.datetime.now():%m%d%H%M}-s{a.seed}"
    os.makedirs(DATA, exist_ok=True)
    json.dump(qs, open(os.path.join(DATA, f"quiz_{qid}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"quiz_id: {qid}\n")
    for i, q in enumerate(qs, 1):
        print(f"Q{i}. {q['prompt']}　" + "  ".join(f"{LET[j]} {o}" for j, o in enumerate(q["opts"])))


def grade(a):
    qs = json.load(open(os.path.join(DATA, f"quiz_{a.quiz_id}.json"), encoding="utf-8"))
    given = {}
    for tok in re.split(r"[\s,]+", a.answers.strip()):
        m = re.fullmatch(r"Q?(\d+)=([A-Ea-e?])([odg]?)", tok, re.I)
        if m:
            given[int(m.group(1))] = (m.group(2).upper(), (m.group(3) or "d").lower())
    st = state()
    now = datetime.datetime.now().isoformat(timespec="seconds")
    ok = solid = 0
    miss = []
    logp = os.path.join(DATA, "vocab_log.csv")
    new = not os.path.exists(logp)
    with open(logp, "a", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        if new:
            wr.writerow(["ts", "quiz", "word", "kind", "given", "ans", "ok", "conf"])
        for i, q in enumerate(qs, 1):
            g, c = given.get(i, ("?", "g"))
            hit = g == q["ans"]
            s = st.setdefault(q["word"], {"box": 0, "seen": 0, "hit": 0})
            s["seen"] += 1
            if hit and c != "g":
                s["box"] = min(3, s["box"] + 1); s["hit"] += 1; solid += 1
            elif not hit:
                s["box"] = 0
            ok += hit
            if not hit or c == "g":
                miss.append(f"Q{i} {q['prompt']}: 正解 {q['ans']} {q['opts'][LET.index(q['ans'])]}"
                            f"（あなた {g}/{c}）")
            wr.writerow([now, a.quiz_id, q["word"], q["kind"], g, q["ans"], int(hit), c])
    save_state(st)
    print(f"正答 {ok}/{len(qs)}  実力正答 {solid}/{len(qs)}")
    print("\n".join(miss) if miss else "全問 実力正解")


def status(a):
    st = state()
    ws = words(a.set_id)
    boxes = [st.get(w["w"], {}).get("box", 0) for w in ws]
    print(f"{a.set_id}: 定着(box>=2) {sum(b >= 2 for b in boxes)}/{len(ws)}")
    for w, b in zip(ws, boxes):
        if b < 2:
            print(f"  box{b} {w['w']} = {w['ja']}  ≒{w['syn'] or '-'}  ⇔{w['ant'] or '-'}")


ap = argparse.ArgumentParser()
sp = ap.add_subparsers(dest="cmd", required=True)
m = sp.add_parser("make"); m.add_argument("set_id"); m.add_argument("--n", type=int, default=25); m.add_argument("--seed", type=int, default=1)
g = sp.add_parser("grade"); g.add_argument("quiz_id"); g.add_argument("answers")
s = sp.add_parser("status"); s.add_argument("set_id")
a = ap.parse_args()
{"make": make, "grade": grade, "status": status}[a.cmd](a)
