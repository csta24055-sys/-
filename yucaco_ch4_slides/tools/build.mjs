// 38枚のスライドを PDF（13.333 x 7.5 in）とページごとの PNG に書き出す。
//   node tools/build.mjs            -> output/ に改善版（v2）の PDF、PNG_DIR（既定: output/pages）に PNG
//   ONLY=5,6 node tools/build.mjs   -> 指定ページの PNG だけ書き出す（確認用）
//   SRC=archive/v1/deck.html OUT=yucaco_ch4_performance_customer.pdf node tools/build.mjs
//                                   -> 保存してある v1 の原稿から v1 の PDF を作り直す（通常は不要）
import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// playwright はグローバル導入版を CommonJS 経由で読み込む（ESM の import では見つからないため）
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright');

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const srcFile = path.resolve(root, process.env.SRC || path.join('src', 'deck.html'));
const src = 'file://' + srcFile;
// v1（前回の完成版）は output/yucaco_ch4_performance_customer.pdf に残し、v2 は別名で書き出す
const outName = process.env.OUT || 'yucaco_ch4_performance_customer_v2.pdf';
const outDir = path.join(root, 'output');
const pngDir = process.env.PNG_DIR || path.join(outDir, 'pages');
const only = process.env.ONLY ? new Set(process.env.ONLY.split(',').map(Number)) : null;
const skipPdf = !!process.env.NO_PDF;
fs.mkdirSync(outDir, { recursive: true });
fs.mkdirSync(pngDir, { recursive: true });

// 同梱フォント（使用文字のサブセット）に無い文字があれば警告する
const charsetPath = path.join(root, 'src', 'assets', 'fonts', 'charset.txt');
if (fs.existsSync(charsetPath)) {
  const charset = new Set(fs.readFileSync(charsetPath, 'utf8'));
  const html = fs.readFileSync(srcFile, 'utf8').replace(/<[^>]+>/g, ' ');
  const missing = [...new Set(html)].filter(ch => ch.trim() && !charset.has(ch) && ch.codePointAt(0) !== 0x2252);
  if (missing.length) console.log('FONT WARNING: サブセットに無い文字があります。tools/subset_fonts.py を再実行してください:', missing.join(''));
}

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
await page.goto(src, { waitUntil: 'load' });
await page.evaluate(async () => { await document.fonts.ready; });

// はみ出し検査：スライドの外に出た要素、親の箱からあふれた文字
const issues = await page.evaluate(() => {
  const out = [];
  document.querySelectorAll('section.slide').forEach((s, i) => {
    const sr = s.getBoundingClientRect();
    s.querySelectorAll('*').forEach(el => {
      const cs = getComputedStyle(el);
      if (cs.display === 'none' || el.closest('svg') && el.tagName !== 'svg') return;
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) return;
      const tol = 1;
      if (r.right > sr.right + tol || r.bottom > sr.bottom + tol || r.left < sr.left - tol || r.top < sr.top - tol) {
        // 写真の裁ち落としは意図どおり
        if (el.closest('.ph, .cv-photo, .dv-photo, .cv-cap, .dv-cap') ) return;
        out.push({ slide: i + 1, kind: 'outside', tag: el.tagName, cls: el.className && el.className.baseVal === undefined ? el.className : '', text: (el.textContent || '').trim().slice(0, 40) });
      }
      if ((el.scrollWidth > el.clientWidth + 2 && cs.overflowX !== 'visible' && el.clientWidth > 0) ||
          (el.scrollHeight > el.clientHeight + 2 && cs.overflowY !== 'visible' && el.clientHeight > 0)) {
        if (el.classList.contains('slide') || el.closest('.ph, .cv-photo, .dv-photo, .ag-ph')) return;
        out.push({ slide: i + 1, kind: 'clipped', tag: el.tagName, cls: String(el.className), text: (el.textContent || '').trim().slice(0, 40) });
      }
    });
    // 本文領域とフッターの重なり
    const ft = s.querySelector('.ft');
    if (ft) {
      const fr = ft.getBoundingClientRect();
      s.querySelectorAll('.bd *').forEach(el => {
        const r = el.getBoundingClientRect();
        if (r.width && r.height && r.bottom > fr.top + 2 && r.top < fr.bottom && r.right > fr.left && r.left < fr.right) {
          if (el.closest('svg') && el.tagName !== 'svg') return;
          out.push({ slide: i + 1, kind: 'over-footer', tag: el.tagName, cls: String(el.className), text: (el.textContent || '').trim().slice(0, 40) });
        }
      });
    }
  });
  return out;
});
if (issues.length) {
  console.log('LAYOUT ISSUES:');
  for (const it of issues) console.log(`  p${it.slide} ${it.kind} <${it.tag} class="${it.cls}"> ${it.text}`);
} else {
  console.log('layout check: no overflow found');
}

const slides = await page.$$('section.slide');
for (let i = 0; i < slides.length; i++) {
  if (only && !only.has(i + 1)) continue;
  await slides[i].screenshot({ path: path.join(pngDir, `p${String(i + 1).padStart(2, '0')}.png`) });
}
console.log(`png: ${only ? only.size : slides.length} page(s) -> ${pngDir}`);

if (!only && !skipPdf) {
  const pdfPath = path.join(outDir, outName);
  await page.pdf({
    path: pdfPath,
    width: '1280px', height: '720px', scale: 2 / 3,
    printBackground: true, margin: { top: 0, right: 0, bottom: 0, left: 0 },
  });
  console.log('pdf:', pdfPath);
}
await browser.close();
