#!/usr/bin/env python3
"""Fetch ONE public page for original-source review and print its readable text.

Research tooling only (no app code). It makes a single polite request per call,
never crawls, never logs in, and never bypasses paywalls. The extracted text is
cached OUTSIDE the repository (directory given by --cache or $RESEARCH_CACHE) so
that third-party page contents are not committed to Git.

Usage:
    python3 scripts/fetch_text.py URL [--grep REGEX] [--context N] [--max CHARS]
                                      [--browser] [--cache DIR]
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'
SKIP = {'script', 'style', 'noscript', 'svg', 'template', 'head'}
BLOCK = {'p', 'div', 'li', 'tr', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'section', 'article',
         'table', 'ul', 'ol', 'td', 'th', 'dt', 'dd', 'blockquote', 'pre', 'header', 'footer'}


class Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.skip = 0
        self.title = ''
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag == 'title':
            self._in_title = True
        if tag in SKIP and tag != 'head':
            self.skip += 1
        if tag in BLOCK:
            self.out.append('\n')

    def handle_endtag(self, tag):
        if tag == 'title':
            self._in_title = False
        if tag in SKIP and tag != 'head' and self.skip:
            self.skip -= 1
        if tag in BLOCK:
            self.out.append('\n')

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self.skip:
            self.out.append(data)


def html_to_text(html: str) -> tuple[str, str]:
    p = Text()
    p.feed(html)
    text = ''.join(p.out)
    text = re.sub(r'[ \t\r\f\v ]+', ' ', text)
    text = re.sub(r'\n\s*\n+', '\n', text)
    return p.title.strip(), text.strip()


def curl(url: str) -> tuple[int, bytes, str]:
    r = subprocess.run(['curl', '-sS', '-L', '-m', '45', '--compressed', '-A', UA,
                        '-H', 'Accept-Language: ja,en;q=0.8', '-w', '\n%{http_code} %{content_type}', url],
                       capture_output=True)
    body, _, tail = r.stdout.rpartition(b'\n')
    parts = tail.decode('utf-8', 'replace').split(' ', 1)
    code = int(parts[0]) if parts and parts[0].isdigit() else 0
    return code, body, (parts[1] if len(parts) > 1 else '')


BROWSER_JS = r"""
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ locale: 'ja-JP' });
  let status = 0;
  try {
    const resp = await page.goto(process.argv[2], { waitUntil: 'domcontentloaded', timeout: 45000 });
    status = resp ? resp.status() : 0;
    await page.waitForTimeout(3500);
    const title = await page.title();
    const text = await page.evaluate(() => document.body ? document.body.innerText : '');
    console.log(JSON.stringify({ status, title, text }));
  } catch (e) {
    console.log(JSON.stringify({ status, title: '', text: '', error: String(e) }));
  }
  await browser.close();
})();
"""


def browser(url: str) -> tuple[int, str, str]:
    r = subprocess.run(['node', '-e', BROWSER_JS, url], capture_output=True, text=True, timeout=120)
    try:
        d = json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return 0, '', r.stderr[-400:]
    return d.get('status', 0), d.get('title', ''), d.get('text', '') or d.get('error', '')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('url')
    ap.add_argument('--grep')
    ap.add_argument('--context', type=int, default=1)
    ap.add_argument('--max', type=int, default=6000)
    ap.add_argument('--browser', action='store_true')
    ap.add_argument('--cache', default=os.environ.get('RESEARCH_CACHE', ''))
    a = ap.parse_args()
    if not a.cache:
        raise SystemExit('set --cache or $RESEARCH_CACHE to a directory outside the repository')
    cache = Path(a.cache)
    cache.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(a.url.encode()).hexdigest()[:16]
    tf = cache / f'{key}.txt'
    fetched_at = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    if tf.exists():
        meta = json.loads((cache / f'{key}.json').read_text(encoding='utf-8'))
        title, text, status = meta['title'], tf.read_text(encoding='utf-8'), meta['status']
        fetched_at = meta['fetched_at']
    else:
        if a.browser:
            status, title, text = browser(a.url)
            method = 'headless_browser'
        else:
            status, body, ctype = curl(a.url)
            method = 'http_get'
            if 'pdf' in ctype or a.url.lower().split('?')[0].endswith('.pdf'):
                pf = cache / f'{key}.pdf'
                pf.write_bytes(body)
                r = subprocess.run(['pdftotext', '-layout', str(pf), '-'], capture_output=True, text=True)
                title, text = 'PDF', r.stdout
            else:
                title, text = html_to_text(body.decode('utf-8', 'replace'))
        tf.write_text(text, encoding='utf-8')
        meta = {'url': a.url, 'status': status, 'title': title, 'chars': len(text),
                'fetched_at': fetched_at, 'method': method}
        (cache / f'{key}.json').write_text(json.dumps(meta, ensure_ascii=False), encoding='utf-8')
        with (cache / 'fetch_log.jsonl').open('a', encoding='utf-8') as f:
            f.write(json.dumps(meta, ensure_ascii=False) + '\n')
    print(f'## status={status} chars={len(text)} fetched_at={fetched_at} title={title[:90]!r}')
    if a.grep:
        lines = text.splitlines()
        rx = re.compile(a.grep, re.I)
        keep: set[int] = set()
        for i, line in enumerate(lines):
            if rx.search(line):
                keep.update(range(max(0, i - a.context), min(len(lines), i + a.context + 1)))
        out, last = [], -2
        for i in sorted(keep):
            if i != last + 1:
                out.append('…')
            out.append(lines[i][:600])
            last = i
        text = '\n'.join(out)
    sys.stdout.write(text[:a.max] + ('\n…[truncated]' if len(text) > a.max else '') + '\n')


if __name__ == '__main__':
    main()
