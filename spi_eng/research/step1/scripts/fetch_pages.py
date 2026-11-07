import sys, re, html, json, subprocess, hashlib, os, time
urls = [l.strip() for l in open(sys.argv[1]) if l.strip()]
out = open(sys.argv[2], "a", encoding="utf-8")
for u in urls:
    r = subprocess.run(["curl","-s","-L","-m","30","-A","Mozilla/5.0","-w","\n%{http_code}",u],capture_output=True)
    raw = r.stdout.decode("utf-8","ignore"); code = raw.rsplit("\n",1)[-1]; t = raw.rsplit("\n",1)[0]
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", t, flags=re.S)
    txt = html.unescape(re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",t))).strip()
    date = (re.search(r'"datePublished"\s*:\s*"([^"]+)"', raw) or re.search(r'(20\d\d[-/年]\d{1,2}[-/月]\d{1,2})', txt) or [None,None])[1] if True else None
    out.write(json.dumps({"url":u,"http":code,"len":len(txt),"date":date,"text":txt[:60000]},ensure_ascii=False)+"\n"); out.flush()
    print(code, len(txt), u, flush=True); time.sleep(0.8)
