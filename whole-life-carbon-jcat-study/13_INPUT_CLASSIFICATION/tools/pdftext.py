import sys, time
from pypdf import PdfReader
t = time.time()
r = PdfReader(sys.argv[1])
n = len(r.pages)
out = open(sys.argv[2], "w", encoding="utf-8")
chars = 0; empty = 0
for i, page in enumerate(r.pages, 1):
    try:
        text = page.extract_text() or ""
    except Exception as exc:
        text = "[EXTRACT ERROR %s]" % type(exc).__name__
    if len(text.strip()) < 20:
        empty += 1
    chars += len(text)
    out.write("\n=====PAGE %d=====\n%s" % (i, text))
out.close()
print("pages", n, "chars", chars, "pages with <20 chars", empty, "seconds", round(time.time() - t))
