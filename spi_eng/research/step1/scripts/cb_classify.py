import json, re, sys
src, out = sys.argv[1], sys.argv[2]
NUM = {"1":1,"2":2,"3":3,"4":4,"5":5,"１":1,"２":2,"３":3,"４":4,"５":5,"一":1,"二":2,"三":3,"四":4,"五":5}
pat = re.compile(r"(長文|長文読解)[^。\n]{0,8}?([1-5１-５一二三四五])\s*(題|問|つ|個|本)")
first = re.compile(r"(受けました|受けた|受けてき|受験しました|受検しました|受験した|受検した|受けてみ|受けたの|受けたん|受けたところ)")
rows = []
for l in open(src, encoding="utf-8"):
    d = json.loads(l)
    if not d.get("ok"): continue
    q = d.get("text","") ; ans = " ".join(a["text"] for a in d.get("answers",[]))
    allt = q + " " + ans
    if "英語" not in allt: continue
    if not re.search(r"SPI|ＳＰＩ|spi|テストセンター|テスセン", allt): continue
    # 英語の近く(前後80字)にある長文の題数を、質問文と回答で別々に拾う
    def eng_counts(t):
        res = []
        for m in pat.finditer(t):
            ctx = t[max(0, m.start()-80): m.end()+20]
            if "英語" in ctx:
                res.append((NUM[m.group(2)], ctx))
        return res
    rows.append({"qid": d["qid"], "url": d["url"], "date": d.get("date"), "q_first_person": bool(first.search(q)),
                 "q_counts": eng_counts(q), "a_counts": eng_counts(ans), "q": q[:700], "n_ans": len(d.get("answers", []))})
json.dump(rows, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("eng-related", len(rows), "first-person q", sum(r["q_first_person"] for r in rows),
      "with q_counts", sum(bool(r["q_counts"]) for r in rows), "with a_counts", sum(bool(r["a_counts"]) for r in rows))
