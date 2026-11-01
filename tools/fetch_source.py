#!/usr/bin/env python3
"""一次資料の取得・テキスト化・台帳登録ツール。

使い方:
  python3 tools/fetch_source.py ID URL "資料名" "発行主体" "発行年月"
  python3 tools/fetch_source.py --refetch   # 台帳に登録済みの全資料を再取得（新セッション用）

- data/raw/<ID>.<ext> に原資料を保存（.gitignore 対象、再取得可能）
- data/text/<ID>.txt にテキストを保存（.gitignore 対象、再取得可能）
- research/09_資料台帳・証拠管理/source_registry.csv に URL・SHA256・確認日を追記
TEPCO公式サイト(www.tepco.co.jp)は本環境のIPから403となるため、同一資料をNDF・政府サイト等で取得する。
"""
import csv, datetime, hashlib, os, subprocess, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
TXT = os.path.join(ROOT, "data", "text")
REG = os.path.join(ROOT, "research", "09_資料台帳・証拠管理", "source_registry.csv")
FIELDS = ["id", "title", "publisher", "pub_date", "url", "retrieved", "sha256", "bytes", "status"]
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"


def fetch(sid, url):
    os.makedirs(RAW, exist_ok=True); os.makedirs(TXT, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ja,en"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read(); ctype = r.headers.get("Content-Type", "")
    ext = "pdf" if (data[:4] == b"%PDF" or "pdf" in ctype) else "html"
    raw = os.path.join(RAW, f"{sid}.{ext}")
    with open(raw, "wb") as f:
        f.write(data)
    txt = os.path.join(TXT, f"{sid}.txt")
    if ext == "pdf":
        subprocess.run(["pdftotext", "-layout", raw, txt], check=False, stderr=subprocess.DEVNULL)
    else:
        subprocess.run(["pandoc", "-f", "html", "-t", "plain", "--wrap=none", raw, "-o", txt], check=False)
    return hashlib.sha256(data).hexdigest(), len(data)


def load():
    if not os.path.exists(REG):
        return []
    with open(REG, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save(rows):
    os.makedirs(os.path.dirname(REG), exist_ok=True)
    with open(REG, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)


def main():
    rows = load()
    if sys.argv[1:] == ["--refetch"]:
        for r in rows:
            try:
                fetch(r["id"], r["url"]); print("ok", r["id"])
            except Exception as e:
                print("NG", r["id"], e)
        return
    sid, url, title, pub, date = sys.argv[1:6]
    today = datetime.date.today().isoformat()
    try:
        sha, n = fetch(sid, url); status = "取得済"
    except Exception as e:
        sha, n, status = "", 0, f"取得失敗:{e}"
    rows = [r for r in rows if r["id"] != sid]
    rows.append(dict(id=sid, title=title, publisher=pub, pub_date=date, url=url,
                     retrieved=today, sha256=sha, bytes=n, status=status))
    rows.sort(key=lambda r: r["id"]); save(rows)
    print(status, sid, n)


if __name__ == "__main__":
    main()
