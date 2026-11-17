// 公開中の版（改修前）から今回の版へ更新したときの、利用者データの保護を確かめる（Chromium・iPhone 13 相当）。
//   node e2e/upgrade.cjs <改修前のビルド> <今回のビルド>
// 流れ: 1) 改修前の版を配信し、研究計画・資料メモを保存する（IndexedDB）
//       2) 同じ URL の配信物を今回の版に入れ替える（= 本番への反映と同じ状況）
//       3)「新しい版があります」→「更新する」
//       4) 更新後: 保存したデータが残っている／画面は Original のまま（勝手に別のレイアウトにならない）／
//          レイアウトを切り替えて適用してもデータが残る／Original に戻せる
// e2e/update.cjs は同じ版の中での更新、こちらは「改修前 → 改修後」の更新を確かめる。
const { chromium, devices } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const ROOT = path.resolve(__dirname, '../..');
const OLD = path.resolve(process.argv[2] || ''), NEW = path.resolve(process.argv[3] || path.join(ROOT, 'frontend/dist-mobile'));
if (!process.argv[2] || !fs.existsSync(path.join(OLD, 'index.html')) || !fs.existsSync(path.join(NEW, 'index.html'))) { console.error('使い方: node e2e/upgrade.cjs <改修前のビルド> <今回のビルド>'); process.exit(2); }
const DIR = fs.mkdtempSync(path.join(os.tmpdir(), 'aqros-upgrade-'));
fs.cpSync(OLD, DIR, { recursive: true });
const PORT = Number(process.env.PORT || 47804); const BASE = `http://127.0.0.1:${PORT}`;
const PY = fs.existsSync(path.join(ROOT, '.venv/bin/python')) ? path.join(ROOT, '.venv/bin/python') : 'python3';
const results = []; const ok = (n, c, x = '') => { results.push([n, !!c]); console.log(c ? 'PASS' : 'FAIL', n, x ? '— ' + String(x).slice(0, 200) : ''); };
const dump = (page) => page.evaluate(async () => {
  const names = (await indexedDB.databases()).map((d) => d.name).filter(Boolean); const out = {};
  for (const name of names) {
    const db = await new Promise((res, rej) => { const r = indexedDB.open(name); r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error); });
    for (const store of db.objectStoreNames) {
      out[`${name}/${store}`] = await new Promise((res) => { const q = db.transaction(store).objectStore(store).getAll(); q.onsuccess = () => res(JSON.stringify(q.result)); q.onerror = () => res('ERR'); });
    }
    db.close();
  }
  return out;
});

(async () => {
  const srv = spawn(PY, [path.join(ROOT, 'scripts/serve_static.py'), DIR, String(PORT)], { stdio: 'ignore' });
  await new Promise((r) => setTimeout(r, 1200));
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ ...devices['iPhone 13'], locale: 'ja-JP' });
  const page = await ctx.newPage(); const errors = []; page.on('pageerror', (e) => errors.push(e.message));
  // 1) 改修前の版でデータを作る
  await page.goto(BASE + '/plan'); await page.waitForSelector('table.rank');
  await page.evaluate(() => navigator.serviceWorker.ready); await page.waitForTimeout(1500);
  const oldHasDesign = await page.evaluate(() => !!document.querySelector('#design'));
  await page.locator('select', { hasText: 'テーマから新規作成' }).selectOption('T-02');
  await page.waitForSelector('#plan-edit');
  await page.fill('#plan-edit input', '改修前の版で保存した計画');
  await page.click('#plan-edit button:has-text("保存")'); await page.waitForTimeout(500);
  await page.evaluate(() => { history.pushState({}, '', '/library'); window.dispatchEvent(new PopStateEvent('popstate')); });
  await page.waitForSelector('.srclist li'); await page.locator('.srclist li').first().click();
  await page.waitForSelector('.detail-pane textarea');
  await page.fill('.detail-pane textarea', '改修前の版で書いたメモ'); await page.click('text=メモを保存'); await page.waitForTimeout(600);
  const before = await dump(page);
  const size = Object.values(before).reduce((a, v) => a + v.length, 0);
  ok('改修前の版でデータを保存（IndexedDB。研究計画と資料メモ）', size > 200 && JSON.stringify(before).includes('改修前の版で保存した計画') && JSON.stringify(before).includes('改修前の版で書いたメモ'), `${Object.keys(before).length} ストア・${size} 文字`);
  ok('改修前の版にはデザイン設定がない（比較の前提）', !oldHasDesign && (await page.evaluate(() => localStorage.getItem('aqros-ui-prefs-v1'))) === null);
  // 2) 配信物を今回の版に入れ替える（本番への反映と同じ）
  for (const f of fs.readdirSync(DIR)) fs.rmSync(path.join(DIR, f), { recursive: true, force: true });
  fs.cpSync(NEW, DIR, { recursive: true });
  // 3) 更新の通知 → 更新する
  await page.evaluate(() => navigator.serviceWorker.getRegistration().then((r) => r.update()));
  await page.waitForSelector('text=新しい版があります', { timeout: 30000 });
  ok('新しい版の通知が出る（勝手に再読み込みしない）', true);
  await Promise.all([page.waitForNavigation({ timeout: 30000 }), page.click('button:has-text("更新する")')]);
  await page.waitForSelector('main h1'); await page.waitForTimeout(800);
  // 4) 更新後
  const after = await dump(page);
  ok('更新後も IndexedDB の全ストアが 1 文字も変わらない', JSON.stringify(after) === JSON.stringify(before), `${Object.keys(after).length} ストア`);
  ok('更新後の画面は Original のまま（保存されたレイアウト設定なし）', (await page.getAttribute('html', 'data-ui')) === 'original' && !(await page.evaluate(() => document.documentElement.hasAttribute('data-ux'))));
  await page.goto(BASE + '/plan'); await page.waitForSelector('table.rank');
  ok('更新後も研究計画が読める', /改修前の版で保存した計画/.test(await page.locator('.page').innerText()));
  await page.goto(BASE + '/settings'); await page.waitForSelector('#design');
  ok('更新後は設定に「デザイン」がある', (await page.locator('#design [data-layout]').count()) === 5);
  for (const layout of ['research', 'public', 'commercial', 'enterprise']) {
    await page.click(`#design [data-layout="${layout}"]`); await page.waitForTimeout(150);
    await page.click('#design .ux-design-actions button:text-is("適用")'); await page.waitForTimeout(250);
  }
  const mid = await dump(page);
  ok('4 種類のレイアウトを順に適用しても研究データは変わらない', JSON.stringify(mid) === JSON.stringify(before));
  await page.goto(BASE + '/library'); await page.waitForSelector('.srclist li'); await page.locator('.srclist li').first().click();
  await page.waitForSelector('.detail-pane textarea');
  ok('別のレイアウト（Enterprise）でも保存済みのメモが読める', (await page.inputValue('.detail-pane textarea')) === '改修前の版で書いたメモ');
  await page.goto(BASE + '/settings'); await page.waitForSelector('#design');
  await page.click('#design button:has-text("Original に戻す")'); await page.waitForTimeout(300);
  await page.reload(); await page.waitForSelector('main h1');
  ok('Original に戻せて、再読み込み後も Original', (await page.getAttribute('html', 'data-ui')) === 'original');
  ok('最後まで研究データは変わらない', JSON.stringify(await dump(page)) === JSON.stringify(before));
  ok('ページエラーなし', errors.length === 0, errors.join(' / '));
  await browser.close(); srv.kill();
  fs.rmSync(DIR, { recursive: true, force: true });
  const pass = results.filter((r) => r[1]).length; console.log(`\n${pass}/${results.length} passed`);
  process.exit(pass === results.length ? 0 : 1);
})().catch((e) => { console.error(e); process.exit(1); });
