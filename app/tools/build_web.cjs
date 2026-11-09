'use strict';
// Builds the public web app (PWA) into app/dist-web/ for HTTPS hosting (Cloudflare Pages, GitHub Pages, …).
// Only an explicit allow-list of files is copied: the UI, the 52 public bibliography records (seed.js),
// PDF.js and icons. No PDFs, user data, tests or desktop-only code end up on the public site.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const appDir = path.resolve(__dirname, '..');
const out = path.join(appDir, 'dist-web');
const ALLOW = [
  'index.html', 'styles.css', 'manifest.webmanifest', 'sw.js',
  'src/domain.js', 'src/storage.js', 'src/pdf.js', 'src/app.js',
  'data/seed.js',
  'vendor/pdfjs/pdf.min.js', 'vendor/pdfjs/pdf.worker.min.js', 'vendor/pdfjs/LICENSE', 'vendor/pdfjs/VERSION',
  'vendor/pdfjs/cmaps', 'vendor/pdfjs/standard_fonts',
  'icons'
];
// Precached on install (offline from the first launch). Other CMaps/fonts are cached when first used.
const JAPANESE_CMAPS = ['UniJIS-UCS2-H', 'UniJIS-UCS2-V', 'UniJIS-UTF16-H', 'UniJIS-UTF16-V', 'Adobe-Japan1-UCS2', '90ms-RKSJ-H', '90ms-RKSJ-V'].map(n => `vendor/pdfjs/cmaps/${n}.bcmap`);

function walk(rel, list = []) {
  const abs = path.join(appDir, rel);
  const st = fs.statSync(abs);
  if (st.isDirectory()) for (const f of fs.readdirSync(abs).sort()) walk(path.posix.join(rel, f), list);
  else list.push(rel);
  return list;
}
function build() {
  fs.rmSync(out, {recursive: true, force: true});
  const files = ALLOW.flatMap(r => walk(r));
  const forbidden = files.filter(f => /\.pdf$/i.test(f) || /tajima-state|node_modules|\/tests?\//.test(f));
  if (forbidden.length) throw new Error('Refusing to publish: ' + forbidden.join(', '));
  const hash = crypto.createHash('sha256');
  for (const f of files) {
    const dest = path.join(out, f);
    fs.mkdirSync(path.dirname(dest), {recursive: true});
    fs.copyFileSync(path.join(appDir, f), dest);
    if (f !== 'sw.js') hash.update(f).update(fs.readFileSync(path.join(appDir, f)));
  }
  const version = hash.digest('hex').slice(0, 12);
  // './' is the app shell; 'index.html' itself is not precached because some hosts redirect it to '/'.
  const core = ['./', ...files.filter(f => f !== 'sw.js' && f !== 'index.html' && !f.startsWith('vendor/pdfjs/cmaps/') && !f.startsWith('vendor/pdfjs/standard_fonts/') && !/LICENSE|VERSION/.test(f)), ...JAPANESE_CMAPS];
  for (const c of JAPANESE_CMAPS) if (!files.includes(c)) throw new Error('missing ' + c);
  let sw = fs.readFileSync(path.join(appDir, 'sw.js'), 'utf8');
  if (!/const VERSION = '[^']*';/.test(sw) || !/\/\*CORE_START\*\/[\s\S]*\/\*CORE_END\*\//.test(sw)) throw new Error('sw.js markers not found');
  sw = sw.replace(/const VERSION = '[^']*';/, `const VERSION = '${version}';`)
    .replace(/\/\*CORE_START\*\/[\s\S]*\/\*CORE_END\*\//, '/*CORE_START*/\n' + core.map(c => `  '${c}'`).join(',\n') + '\n/*CORE_END*/');
  fs.writeFileSync(path.join(out, 'sw.js'), sw);
  // Cloudflare Pages headers. noindex: this unofficial student tool should not appear in search results
  // next to the lab's official pages; people open it from the shared URL.
  fs.writeFileSync(path.join(out, '_headers'), [
    '/*',
    '  X-Content-Type-Options: nosniff',
    '  Referrer-Policy: no-referrer',
    '  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=()',
    '  X-Robots-Tag: noindex, nofollow',
    '/sw.js',
    '  Cache-Control: no-cache',
    '/index.html',
    '  Cache-Control: no-cache',
    '/',
    '  Cache-Control: no-cache',
    '/manifest.webmanifest',
    '  Content-Type: application/manifest+json',
    '  Cache-Control: no-cache',
    ''
  ].join('\n'));
  fs.writeFileSync(path.join(out, 'robots.txt'), 'User-agent: *\nDisallow: /\n');
  // Unknown paths get a real 404 instead of the hosting provider's fallback to index.html.
  fs.writeFileSync(path.join(out, '404.html'), '<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex"><title>ページが見つかりません｜田嶋研究室</title><style>body{font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans","Noto Sans JP",sans-serif;background:#f3f5f4;color:#1c2828;display:grid;place-items:center;min-height:100vh;margin:0;padding:24px;text-align:center}a{color:#155c5b;font-weight:700}</style></head><body><main><h1>ページが見つかりません</h1><p><a href="/">田嶋研究室 Research Navigator のホームへ</a></p></main></body></html>\n');
  const bytes = files.reduce((s, f) => s + fs.statSync(path.join(appDir, f)).size, 0);
  console.log(`dist-web: ${files.length} files, ${(bytes / 1048576).toFixed(1)} MB, sw version ${version}, precache ${core.length}`);
  return {out, version, files, core};
}
module.exports = {build};
if (require.main === module) build();
