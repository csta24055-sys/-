// Original の見た目の回帰テスト: 改修前のビルド（BASE_OLD）と改修後のビルド（BASE_NEW）を同じ条件で撮影し、
// ピクセル単位で比較する。設定画面は「デザイン」項目を追加したため比較対象外（その下の既存部分は e2e/mobile.cjs で確認）。
//   BASE_OLD=http://127.0.0.1:47802 BASE_NEW=http://127.0.0.1:47801 OUT=/tmp/x node e2e/original-regression.cjs
const { chromium, devices } = require('playwright');
const fs = require('fs'); const path = require('path');
const OLD = process.env.BASE_OLD, NEW = process.env.BASE_NEW, OUT = process.env.OUT || 'regression';
fs.mkdirSync(OUT, { recursive: true });
const PAGES = ['/', '/library', '/simulator', '/graph', '/plan', '/report', '/learn', '/cloud'];
const DEVS = { desktop: { viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 }, iphone: { ...devices['iPhone 13'], deviceScaleFactor: 1 } };
(async () => {
  const b = await chromium.launch();
  const rows = [];
  for (const [dev, opt] of Object.entries(DEVS)) for (const p of PAGES) {
    const shots = {};
    for (const [tag, base] of [['old', OLD], ['new', NEW]]) {
      const ctx = await b.newContext({ ...opt, reducedMotion: 'reduce' }); const page = await ctx.newPage();
      await page.goto(base + p); await page.waitForSelector('main h1'); await page.waitForTimeout(2500);
      const f = path.join(OUT, `${dev}${p.replace(/\//g, '_')}-${tag}.png`); await page.screenshot({ path: f, fullPage: true }); shots[tag] = f;
      rows.push({ dev, p, tag, dom: await page.evaluate(() => document.querySelector('.shell').outerHTML.replace(/ (aria-label|aria-valuemin|aria-valuemax|data-section|data-page|id)="[^"]*"/g, '').replace(/<div class="ux-sr"[^>]*>.*?<\/div>/g, '').length) });
      await ctx.close();
    }
  }
  fs.writeFileSync(path.join(OUT, 'dom.json'), JSON.stringify(rows));
  await b.close();
})();
