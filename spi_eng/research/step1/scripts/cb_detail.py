import sys, re, json, time, html, subprocess, os
IDS_JSON, OUTDIR = sys.argv[1], sys.argv[2]
SHARD, NSH = int(sys.argv[3]), int(sys.argv[4])
ids = sorted({i for v in json.load(open(IDS_JSON)).values() for i in v})
ids = ids[SHARD::NSH]
def get(url):
    r = subprocess.run(["curl","-s","-L","-m","12","-A","Mozilla/5.0",url],capture_output=True)
    return r.stdout.decode("utf-8","ignore")
def clean(s): return html.unescape(re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",s or ""))).strip()

done = set()
import glob
done=set()
for p in glob.glob(os.path.join(OUTDIR,"questions*.jsonl")):
  pass
p = os.path.join(OUTDIR,"questions.jsonl")
if os.path.exists(p):
    for l in open(p,encoding="utf-8"):
        try: done.add(json.loads(l)["qid"])
        except: pass
for pp in glob.glob(os.path.join(OUTDIR,"questions*.jsonl")):
    for l in open(pp,encoding="utf-8"):
        try: done.add(json.loads(l)["qid"])
        except: pass
out = open(os.path.join(OUTDIR,f"questions_s{SHARD}.jsonl"),"a",encoding="utf-8")
for qid in ids:
    if qid in done: continue
    t = get(f"https://detail.chiebukuro.yahoo.co.jp/qa/question_detail/q{qid}")
    rec = {"qid": qid, "url": f"https://detail.chiebukuro.yahoo.co.jp/qa/question_detail/q{qid}", "ok": False}
    for m in re.finditer(r'<script[^>]*ld\+json[^>]*>(.*?)</script>', t, re.S):
        try: d = json.loads(m.group(1))
        except Exception: continue
        for x in (d if isinstance(d, list) else [d]):
            if x.get("@type") == "QAPage":
                q = x.get("mainEntity", {})
                ans = ([q["acceptedAnswer"]] if q.get("acceptedAnswer") else []) + (q.get("suggestedAnswer") or [])
                rec.update(ok=True, text=clean(q.get("name")), date=q.get("datePublished"), author=(q.get("author") or {}).get("name"),
                           answers=[{"text": clean(a.get("text")), "date": a.get("datePublished"), "author": (a.get("author") or {}).get("name")} for a in ans])
    out.write(json.dumps(rec, ensure_ascii=False) + "\n"); out.flush()
    time.sleep(0.5)
print("done", len(ids))
