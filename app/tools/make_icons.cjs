'use strict';
// Renders every app icon from one HTML/SVG design (needs Playwright's Chromium):
//   node tools/make_icons.cjs  → PWA/iOS/Android icons in app/icons/ and the desktop icon buildres/icon.png
// Motif: a reinforced-concrete section (outline, stirrup, rebar dots) on a base line — the lab's field.
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright-core');

const appDir = path.resolve(__dirname, '..');
const BG_TOP = '#356b69', BG_BOTTOM = '#245452', INK = '#eef6f5';
// Drawing on a 100×100 grid; `pad` shrinks the motif into the platform's safe zone.
function motif(pad) {
  const s = (100 - pad * 2) / 100, o = pad;
  const t = (x, y) => `${(o + x * s).toFixed(2)},${(o + y * s).toFixed(2)}`;
  const r = v => (v * s).toFixed(2);
  return `
    <rect x="${o + 30 * s}" y="${o + 18 * s}" width="${r(40)}" height="${r(52)}" rx="${r(5)}" fill="none" stroke="${INK}" stroke-width="${r(4.2)}"/>
    <rect x="${o + 36 * s}" y="${o + 24 * s}" width="${r(28)}" height="${r(40)}" rx="${r(3)}" fill="none" stroke="${INK}" stroke-opacity=".55" stroke-width="${r(1.8)}"/>
    <circle cx="${t(40, 29).split(',')[0]}" cy="${t(40, 29).split(',')[1]}" r="${r(3.6)}" fill="${INK}"/>
    <circle cx="${t(60, 29).split(',')[0]}" cy="${t(60, 29).split(',')[1]}" r="${r(3.6)}" fill="${INK}"/>
    <circle cx="${t(40, 59).split(',')[0]}" cy="${t(40, 59).split(',')[1]}" r="${r(4.4)}" fill="${INK}"/>
    <circle cx="${t(50, 59).split(',')[0]}" cy="${t(50, 59).split(',')[1]}" r="${r(4.4)}" fill="${INK}"/>
    <circle cx="${t(60, 59).split(',')[0]}" cy="${t(60, 59).split(',')[1]}" r="${r(4.4)}" fill="${INK}"/>
    <rect x="${o + 18 * s}" y="${o + 78 * s}" width="${r(64)}" height="${r(4.2)}" rx="${r(2.1)}" fill="${INK}"/>`;
}
const grad = `<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${BG_TOP}"/><stop offset="1" stop-color="${BG_BOTTOM}"/></linearGradient></defs>`;
const designs = {
  // Rounded tile with a transparent margin (desktop app, PWA "any" icon, sidebar logo)
  tile: () => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">${grad}<rect x="5" y="5" width="90" height="90" rx="21" fill="url(#g)"/><g transform="translate(5 5) scale(.9)">${motif(7)}</g></svg>`,
  // Full-bleed square: iOS rounds the corners itself; Android "maskable" crops to its own shape (80% safe zone)
  full: () => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">${grad}<rect width="100" height="100" fill="url(#g)"/>${motif(7)}</svg>`,
  // Android adaptive ("maskable"): keep the motif inside the central 80% circle
  mask: () => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">${grad}<rect width="100" height="100" fill="url(#g)"/>${motif(11)}</svg>`
};

async function main() {
  const browser = await chromium.launch(process.env.TAJIMA_CHROMIUM ? {executablePath: process.env.TAJIMA_CHROMIUM} : {});
  const page = await (await browser.newContext({deviceScaleFactor: 1})).newPage();
  async function render(design, size, out, opaque) {
    await page.setViewportSize({width: size, height: size});
    await page.setContent(`<html><body style="margin:0;background:transparent"><div style="width:${size}px;height:${size}px">${designs[design]().replace('<svg ', `<svg width="${size}" height="${size}" `)}</div></body></html>`);
    fs.mkdirSync(path.dirname(out), {recursive: true});
    await page.screenshot({path: out, omitBackground: !opaque});
    console.log('icon', path.relative(path.resolve(appDir, '..'), out), size);
  }
  await render('tile', 1024, path.join(appDir, 'buildres', 'icon.png'), false);   // desktop installers
  await render('tile', 192, path.join(appDir, 'icons', 'icon-192.png'), false);
  await render('tile', 512, path.join(appDir, 'icons', 'icon-512.png'), false);
  await render('mask', 192, path.join(appDir, 'icons', 'maskable-192.png'), true);
  await render('mask', 512, path.join(appDir, 'icons', 'maskable-512.png'), true);
  await render('full', 180, path.join(appDir, 'icons', 'apple-touch-icon.png'), true); // iPhone home screen
  await render('tile', 32, path.join(appDir, 'icons', 'favicon-32.png'), false);
  await browser.close();
}
main().catch(e => { console.error(e); process.exit(1); });
