// アプリ更新時のデータ保護テスト（Chromium・Pixel 7 相当）
// 1) 旧版で研究計画を保存 → 2) 配信物の sw.js を新しい版に差し替え → 3)「新しい版があります」→「更新する」
// → 4) 再読み込み後も研究計画が残っていること、初回訪問では自動再読み込みしないことを確認する。
//   node e2e/update.cjs <dist-mobile ディレクトリ>
const { chromium, devices } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const ROOT = path.resolve(__dirname, '../..');
const SRC = path.resolve(process.argv[2] || path.join(ROOT, 'frontend/dist-mobile'));
const DIR = fs.mkdtempSync(path.join(os.tmpdir(), 'aqros-update-'));
fs.cpSync(SRC, DIR, { recursive: true });
const PORT = 47803; const BASE = `http://127.0.0.1:${PORT}`;
const results = []; const ok = (n, c, x = '') => { results.push([n, !!c]); console.log(c ? 'PASS' : 'FAIL', n, x) };

(async () => {
  const srv = spawn('python3', [path.join(ROOT, 'scripts/serve_static.py'), DIR, String(PORT)], { stdio: 'ignore' });
  await new Promise((r) => setTimeout(r, 800));
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ ...devices['Pixel 7'], locale: 'ja-JP' });
  const page = await ctx.newPage();
  await page.goto(BASE + '/plan'); await page.waitForSelector('table.rank');
  await page.evaluate(() => { window.__marker = 'same-document' });
  await page.evaluate(() => navigator.serviceWorker.ready);
  await page.waitForTimeout(2000);
  const marker = await page.evaluate(() => window.__marker || null);
  const controlled = await page.evaluate(() => !!navigator.serviceWorker.controller);
  ok('初回訪問で自動再読み込みしない（Service Worker の制御開始後も同じ画面）', marker === 'same-document', `marker=${marker} controlled=${controlled}`);
  await page.locator('select', { hasText: 'テーマから新規作成' }).selectOption('T-02');
  await page.waitForSelector('#plan-edit');
  await page.fill('#plan-edit input', '更新前に保存した計画');
  await page.click('#plan-edit button:has-text("保存")'); await page.waitForTimeout(500);
  // 新しい版を配信（sw.js の版を書き換える＝ブラウザは別の Service Worker として扱う）
  const swp = path.join(DIR, 'sw.js');
  fs.writeFileSync(swp, fs.readFileSync(swp, 'utf8').replace(/const VERSION = '([^']+)'/, "const VERSION = '$1-next'"));
  await page.evaluate(() => navigator.serviceWorker.getRegistration().then((r) => r.update()));
  await page.waitForSelector('text=新しい版があります', { timeout: 20000 });
  ok('新しい版の通知が出る', true);
  await Promise.all([page.waitForNavigation({ timeout: 20000 }), page.click('button:has-text("更新する")')]);
  await page.waitForSelector('table.rank');
  const ver = await page.evaluate(() => caches.keys());
  ok('新しい版に切り替わった', ver.some((k) => k.endsWith('-next')), ver.join(','));
  ok('更新後も研究計画が残る', /更新前に保存した計画/.test(await page.locator('.page').innerText()));
  await browser.close(); srv.kill();
  const pass = results.filter((r) => r[1]).length; console.log(`${pass}/${results.length} passed`);
  process.exit(pass === results.length ? 0 : 1);
})().catch((e) => { console.error(e); process.exit(1) });
