#!/usr/bin/env python3
"""公式サイトのトップから採用（新卒）ページを2階層たどり、建築・設備・職種・選考に関する行を抜き出す。
使い方: python3 tools/site_probe.py 名前 https://www.example.co.jp/ [キーワード正規表現]
出力: data/probe/<名前>.txt（.gitignore対象）と標準出力の要約"""
import os, re, sys, html, urllib.request, urllib.parse
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/124", "Accept-Language": "ja"}
def get(u):
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25)
        return r.geturl(), r.read().decode("utf-8", "ignore")
    except Exception: return u, ""
def links(base, h):
    for m in re.finditer(r'href="([^"#]+)"[^>]*>(.*?)</a>', h, re.S):
        yield urllib.parse.urljoin(base, m.group(1)), re.sub(r"<[^>]+>|\s+", "", m.group(2))
def lines(h):
    h = re.sub(r"<script.*?</script>|<style.*?</style>", "", h, flags=re.S)
    return [l.strip() for l in html.unescape(re.sub(r"<[^>]+>", "\n", h)).split("\n") if l.strip()]
name, top = sys.argv[1], sys.argv[2]
kw = re.compile(sys.argv[3] if len(sys.argv) > 3 else r"建築|設備|空調|職種|学科|選考|募集|インターン|技術系|配属|エントリー")
seen, queue, pages = set(), [top], []
lvl_pat = re.compile(r"recruit|saiyo|saiyou|career|採用|新卒|graduate|fresh|job|職種|仕事|募集|course|entry|intern", re.I)
for depth in range(3):
    nxt = []
    for u in queue:
        if u in seen or len(pages) > 40: continue
        seen.add(u); b, h = get(u)
        if not h: continue
        pages.append((b, h))
        for l, t in links(b, h):
            if lvl_pat.search(l + t) and not re.search(r"\.(pdf|jpg|png|zip)$|mid|chuto|中途|キャリア採用|experienced", l + t, re.I):
                nxt.append(l)
    queue = list(dict.fromkeys(nxt))[:25]
os.makedirs(os.path.join(ROOT, "data", "probe"), exist_ok=True)
with open(os.path.join(ROOT, "data", "probe", f"{name}.txt"), "w", encoding="utf-8") as f:
    hits = set()
    for b, h in pages:
        for l in lines(h):
            if kw.search(l) and 6 < len(l) < 260 and l not in hits:
                hits.add(l); f.write(f"{b}\t{l}\n")
print(f"{name}: pages={len(pages)} hits={len(hits)}")
