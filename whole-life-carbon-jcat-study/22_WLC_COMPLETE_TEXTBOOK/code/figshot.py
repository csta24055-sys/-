"""SVG・HTML の図を PNG にする（Chromium で描いて切り出す）。PDF・Word に貼る図はすべてこれを通す。

to_png({"name": (kind, text)}, out_dir)  kind は "svg"（SVG の文字列）か "html"（HTML の断片。#fig 要素を切り出す）。
内容が同じなら描き直さない（out_dir/<name>.png と内容のハッシュを比べる）。
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

SCALE = 3
JS = r"""
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const job = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const b = await chromium.launch();
  const p = await b.newPage({ deviceScaleFactor: job.scale, viewport: { width: 1600, height: 1200 } });
  for (const it of job.items) {
    const html = '<html><head><meta charset="utf-8"><style>body{margin:0;background:#fff;font-family:IPAGothic,sans-serif;color:#000}' +
      '#fig{display:inline-block}</style></head><body><div id="fig">' + it.body + '</div></body></html>';
    await p.setContent(html, { timeout: 120000 });
    const el = await p.$('#fig');
    await el.screenshot({ path: it.png });
  }
  await b.close();
})();
"""


def to_png(figs: dict[str, tuple[str, str]], out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp_p = out_dir / "_hash.json"
    stamps = json.loads(stamp_p.read_text()) if stamp_p.exists() else {}
    todo, out = [], {}
    for name, (kind, text) in figs.items():
        h = hashlib.sha1(f"{SCALE}|{kind}|{text}".encode()).hexdigest()
        png = out_dir / f"{name}.png"
        out[name] = png
        if stamps.get(name) != h or not png.exists():
            todo.append((name, kind, text, h, png))
    if todo:
        job = {"scale": SCALE, "items": [{"body": text, "png": str(png)} for _, _, text, _, png in todo]}
        with tempfile.TemporaryDirectory() as td:
            jp, sp = Path(td) / "job.json", Path(td) / "shot.js"
            jp.write_text(json.dumps(job), encoding="utf-8")
            sp.write_text(JS, encoding="utf-8")
            subprocess.run(["node", str(sp), str(jp)], check=True, timeout=1800)
        for name, _, _, h, _ in todo:
            stamps[name] = h
        stamp_p.write_text(json.dumps(stamps, indent=0), encoding="utf-8")
    return out
