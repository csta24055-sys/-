import json, hashlib, csv, glob, sys
S, out = sys.argv[1], sys.argv[2]
rows = []
for f in glob.glob(S + "/dl/pages/pages*.jsonl"):
    for l in open(f, encoding="utf-8"):
        d = json.loads(l)
        rows.append([d["url"], d["http"], d["len"], hashlib.sha256(d["text"].encode()).hexdigest()[:16], "page", d.get("date") or ""])
for f in [S + "/dl/cb/all.jsonl"]:
    for l in open(f, encoding="utf-8"):
        d = json.loads(l)
        t = d.get("text", "") + " ".join(a["text"] for a in d.get("answers", []))
        rows.append([d["url"], "200" if d["ok"] else "parse_fail", len(t), hashlib.sha256(t.encode()).hexdigest()[:16], "chiebukuro", d.get("date") or ""])
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["url", "http", "text_len", "sha256_16", "kind", "post_date"]); w.writerows(rows)
print(len(rows))
