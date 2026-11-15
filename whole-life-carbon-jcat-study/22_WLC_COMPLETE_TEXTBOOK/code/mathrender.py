"""表示式（TeX の部分集合）を Chromium の MathML 組版で PNG にする（まとめて 1 ページで描き、要素ごとに切り出す）。

結果は式の文字列の SHA-1 でキャッシュする（同じ式は描き直さない）。数式フォントは FreeSerif（OpenType の MATH 表を持つ）。
戻り値: {tex: (png のパス, 幅 pt, 高さ pt)}。幅・高さは本文 11pt 相当の大きさで紙面に置くときの寸法。
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from tex2mml import VERSION, to_mathml

SCALE = 4                 # 画面の倍率（解像度）
FONT_PX = 16.0            # 式の文字の大きさ（CSS px。1 px = 0.75 pt なので約 11.25 pt）
JS = r"""
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const job = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const b = await chromium.launch();
  const p = await b.newPage({ deviceScaleFactor: job.scale, viewport: { width: 1400, height: 900 } });
  let html = '<html><head><meta charset="utf-8"><style>body{margin:0;background:#fff;color:#000}' +
    '.e{display:inline-block;padding:3px 4px;font-size:' + job.font + 'px;font-family:FreeSerif}' +
    'math{font-family:FreeSerif;math-style:normal} .w{margin:6px}</style></head><body>';
  for (const it of job.items) html += '<div class="w"><div class="e" id="' + it.id + '">' + it.mml + '</div></div>';
  html += '</body></html>';
  await p.setContent(html, { timeout: 120000 });
  const out = {};
  for (const it of job.items) {
    const el = await p.$('#' + it.id);
    const box = await el.boundingBox();
    await el.screenshot({ path: it.png });
    out[it.id] = { w: box.width, h: box.height };
  }
  fs.writeFileSync(process.argv[3], JSON.stringify(out));
  await b.close();
})();
"""


def render_all(texs: list[str], cache: Path) -> dict[str, tuple[Path, float, float]]:
    cache.mkdir(parents=True, exist_ok=True)
    meta_path = cache / "meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    todo, out = [], {}
    for tex in dict.fromkeys(texs):
        h = hashlib.sha1(f"{VERSION}|{FONT_PX}|{SCALE}|{tex}".encode()).hexdigest()[:16]
        png = cache / f"m{h}.png"
        if h in meta and png.exists():
            out[tex] = (png, meta[h]["w"] * 0.75, meta[h]["h"] * 0.75)
        else:
            todo.append((tex, h, png))
    if todo:
        job = {"scale": SCALE, "font": FONT_PX,
               "items": [{"id": "m" + h, "mml": to_mathml(tex, True), "png": str(png)} for tex, h, png in todo]}
        with tempfile.TemporaryDirectory() as td:
            jp, op, sp = Path(td) / "job.json", Path(td) / "out.json", Path(td) / "shot.js"
            jp.write_text(json.dumps(job), encoding="utf-8")
            sp.write_text(JS, encoding="utf-8")
            subprocess.run(["node", str(sp), str(jp), str(op)], check=True, timeout=1800)
            res = json.loads(op.read_text())
        for tex, h, png in todo:
            r = res["m" + h]
            meta[h] = {"w": r["w"], "h": r["h"], "tex": tex}
            out[tex] = (png, r["w"] * 0.75, r["h"] * 0.75)
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=0), encoding="utf-8")
    return out
