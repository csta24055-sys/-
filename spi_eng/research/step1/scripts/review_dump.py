import json, re, sys, glob
seen = set(json.load(open(sys.argv[2]))) if len(sys.argv) > 2 else set()
out = []
for f in glob.glob(sys.argv[1]):
    for l in open(f, encoding="utf-8"):
        d = json.loads(l)
        if not d.get("ok") or d["qid"] in seen: continue
        parts = [("Q", d.get("text",""))] + [(f"A{i}", a["text"]) for i, a in enumerate(d.get("answers", []))]
        allt = " ".join(p[1] for p in parts)
        if "英語" not in allt or not re.search(r"SPI|ＳＰＩ|spi|テストセンター|テスセン", allt): continue
        sents = []
        for tag, t in parts:
            for s in re.split(r"(?<=[。！？!?\n])", t):
                if "英語" in s and re.search(r"長文|題|問|出|受け|受験|受検|割|手応え|難し|簡単|高得点|通過|落ち", s):
                    sents.append(f"{tag}:{s.strip()[:170]}")
        if sents:
            out.append((d["qid"], (d.get("date") or "")[:10], sents[:4]))
for qid, dt, ss in sorted(out):
    print(f"#{qid} {dt}")
    for s in ss: print("   ", s)
print("TOTAL", len(out), file=sys.stderr)
