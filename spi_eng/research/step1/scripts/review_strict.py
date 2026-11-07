import json, re, sys
seen = set(json.load(open(sys.argv[2])))
EXCL = re.compile(r"玉手箱|C-?GAB|ＧＡＢ|GAB|SCOA|ＳＣＯＡ|一般常識|教養試験|TOEIC|大学入試|センター試験|共通テスト|英検|高校|TG-?WEB|imag", re.I)
KEEP = re.compile(r"長文|タブ|[1-5１-５一二三四五]題|受けて?き?た|受けました|受験した|受験しました|受検した|受検しました|手応え|手ごたえ|出来|解けた|解けなかった|到達")
FP = re.compile(r"受けて?き?た|受けました|受験した|受験しました|受検した|受検しました|受けたの|受けたん")
hits = []; excluded = []
for l in open(sys.argv[1], encoding="utf-8"):
    d = json.loads(l)
    if d["qid"] in seen: continue
    parts = [("Q", d.get("text",""))] + [(f"A{i}", a["text"]) for i, a in enumerate(d.get("answers", []))]
    allt = " ".join(p[1] for p in parts)
    if "英語" not in allt or not re.search(r"SPI|ＳＰＩ|spi|テストセンター|テスセン", allt): continue
    ss = []
    for tag, t in parts:
        for s in re.split(r"(?<=[。！？!?\n])", t):
            if "英語" in s and KEEP.search(s) and not EXCL.search(s):
                ss.append(f"{tag}:{s.strip()[:180]}")
    if ss and (FP.search(allt) or any("長文" in x or "タブ" in x for x in ss)):
        hits.append((d["qid"], (d.get("date") or "")[:10], ss[:4]))
    else:
        excluded.append(d["qid"])
for q, dt, ss in sorted(hits):
    print(f"#{q} {dt}"); [print("   ", s) for s in ss]
json.dump(excluded, open(sys.argv[3], "w"))
print("HITS", len(hits), "EXCLUDED", len(excluded), file=sys.stderr)
