import json, sys, glob
ids = set(sys.argv[2:])
for f in glob.glob(sys.argv[1]):
    for l in open(f, encoding="utf-8"):
        d = json.loads(l)
        if d["qid"] in ids:
            print(f"\n######## q{d['qid']} {d.get('date')}\nQ: {d['text'][:1500]}")
            for i, a in enumerate(d.get("answers", [])[:4]): print(f"A{i} ({(a.get('date') or '')[:10]}): {a['text'][:700]}")
