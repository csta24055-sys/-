'use strict';
// Mobile E2E for the installable web app (PWA), on two real browser engines with phone emulation:
//   • Android Chrome equivalent: Chromium + Pixel 7 emulation
//   • iPhone Safari equivalent:  WebKit   + iPhone 15 emulation
// plus a real "install → launch standalone" check in full Chromium (needs a display: xvfb-run on Linux).
// This is automated emulation, NOT a test on a physical phone.
// Target: a fresh local build of dist-web (default) or a deployed site via TAJIMA_URL=https://…
// Optional: TAJIMA_CHROMIUM / TAJIMA_WEBKIT = browser executables, TAJIMA_SCREENSHOTS=<dir>.
const {describe, it, before, after} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const http = require('node:http');
const {chromium, webkit, devices} = require('playwright-core');
const {samplePdf} = require('../helpers/make-pdf.cjs');
const {build} = require('../../tools/build_web.cjs');

const work = fs.mkdtempSync(path.join(os.tmpdir(), 'tajima-mobile-'));
const pdfFile = path.join(work, 'Seismic_sample.pdf');
fs.writeFileSync(pdfFile, samplePdf());
const shots = process.env.TAJIMA_SCREENSHOTS ? path.resolve(process.env.TAJIMA_SCREENSHOTS) : '';
if (shots) fs.mkdirSync(shots, {recursive: true});
const TYPES = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.webmanifest': 'application/manifest+json', '.png': 'image/png', '.json': 'application/json', '.bcmap': 'application/octet-stream', '.pfb': 'application/octet-stream', '.ttf': 'font/ttf', '.txt': 'text/plain'};
let server = null;
let base = process.env.TAJIMA_URL ? process.env.TAJIMA_URL.replace(/\/?$/, '/') : '';

async function serveLocalBuild() {
  if (base) return;
  const {out} = build();
  server = http.createServer((req, res) => {
    const pathname = decodeURIComponent(new URL(req.url, 'http://x').pathname);
    // Behave like Cloudflare Pages: "/index.html" redirects to "/", unknown paths get 404.html.
    if (pathname === '/index.html') { res.writeHead(308, {location: '/'}); res.end(); return; }
    const rel = pathname.replace(/^\/+/, '') || 'index.html';
    const file = path.resolve(out, rel);
    if (!file.startsWith(out + path.sep) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404, {'content-type': 'text/html; charset=utf-8'}); fs.createReadStream(path.join(out, '404.html')).pipe(res); return; }
    res.writeHead(200, {'content-type': TYPES[path.extname(file)] || 'application/octet-stream', 'cache-control': 'no-cache'});
    fs.createReadStream(file).pipe(res);
  });
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  port = server.address().port;
  base = `http://localhost:${port}/`; // localhost = secure context (service workers allowed)
}
let port = 0;
// "No network": the local server goes away (same origin comes back later); a deployed site is cut off with a dead proxy.
async function stopServer() { if (!server) return; server.closeAllConnections?.(); await new Promise(r => server.close(r)); }
async function startServer() { if (!server) return; await new Promise(r => server.listen(port, '127.0.0.1', r)); }
// Sandboxes that reach the internet only through an HTTP proxy (HTTPS_PROXY) need it passed to the browser.
const webProxy = () => process.env.TAJIMA_URL && (process.env.HTTPS_PROXY || process.env.https_proxy) ? {server: process.env.HTTPS_PROXY || process.env.https_proxy} : undefined;
const ENGINES = [
  {key: 'android', name: 'Android Chrome相当（Chromium・Pixel 7エミュレーション）', device: 'Pixel 7', type: chromium, exe: process.env.TAJIMA_CHROMIUM},
  {key: 'ios', name: 'iPhone Safari相当（WebKit・iPhone 15エミュレーション）', device: 'iPhone 15', type: webkit, exe: process.env.TAJIMA_WEBKIT}
].map(e => ({...e, launch: () => e.type.launch({...(e.exe ? {executablePath: e.exe} : {}), ...(webProxy() ? {proxy: webProxy()} : {})})}));
const deviceOptions = name => { const {defaultBrowserType, ...rest} = devices[name]; return rest; };

before(serveLocalBuild);
after(() => { server?.close(); try { fs.rmSync(work, {recursive: true, force: true}); } catch (_) { /* ignore */ } });

for (const eng of ENGINES) {
  describe(eng.name, () => {
    let ctx, page, skip = '';
    const profile = fs.mkdtempSync(path.join(os.tmpdir(), `tajima-${eng.key}-profile-`));
    const problems = [];
    const shot = async name => { if (shots) await page.screenshot({path: path.join(shots, `${eng.key}-${name}.png`)}); };
    const tapTab = async name => page.click(`.tab-item[data-tab="${name}"]`);
    const more = async item => { await page.click('.tab-item[data-action="open-sheet"]'); await page.click(`.sheet-item${item}`); };
    const toastHas = text => page.waitForFunction(t => document.getElementById('toast').textContent.includes(t), text);
    const step = (title, fn) => it(title, async t => { if (skip) { t.skip(skip); return; } await fn(); });
    // A persistent profile = the phone's storage: it survives closing and reopening the app.
    async function open({offline = false} = {}) {
      ctx = await eng.type.launchPersistentContext(profile, {...deviceOptions(eng.device), acceptDownloads: true, ...(eng.exe ? {executablePath: eng.exe} : {}), ...(offline && !server ? {proxy: {server: 'http://127.0.0.1:9'}} : webProxy() ? {proxy: webProxy()} : {})});
      page = ctx.pages()[0] || await ctx.newPage();
      page.on('console', m => { if (m.type() === 'error') problems.push((offline ? '[offline] ' : '') + 'console: ' + m.text()); });
      page.on('pageerror', e => problems.push('pageerror: ' + e.message));
      page.on('requestfailed', r => { if (!r.url().startsWith('blob:')) problems.push((offline ? '[offline] ' : '') + 'requestfailed: ' + r.url() + ' ' + (r.failure()?.errorText || '')); });
      page.on('dialog', d => d.accept());
      await page.goto(base);
      await page.waitForSelector('body[data-ready="true"]');
    }
    async function reopen({offline = false} = {}) {
      await ctx.close();
      if (offline) await stopServer(); else await startServer();
      await open({offline});
    }
    before(async () => {
      try { await open(); } catch (e) { skip = `${eng.key} engine not available: ${String(e.message).split('\n')[0]}`; }
    });
    after(async () => { await ctx?.close(); try { fs.rmSync(profile, {recursive: true, force: true}); } catch (_) { /* ignore */ } });

    step('初回アクセス：52件の書誌・下部タブ・ホーム画面追加の案内', async () => {
      assert.equal(await page.textContent('#statTotal'), '52');
      assert.ok(await page.isVisible('.tabbar'));
      assert.ok(!(await page.isVisible('.sidebar')));
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
      assert.ok(overflow <= 0, 'horizontal overflow ' + overflow);
      const install = await page.textContent('#installCard');
      assert.match(install, eng.key === 'ios' ? /共有/ : /アプリをインストール/);
      await shot('01-first-visit');
    });

    step('インストール条件：マニフェスト・専用アイコン・Service Worker', async () => {
      const r = await page.evaluate(async () => {
        const m = await (await fetch('manifest.webmanifest')).json();
        const icons = [];
        for (const i of m.icons) { const res = await fetch(i.src); icons.push({src: i.src, ok: res.ok, type: res.headers.get('content-type'), purpose: i.purpose, sizes: i.sizes}); }
        const apple = document.querySelector('link[rel="apple-touch-icon"]').getAttribute('href');
        const appleRes = await fetch(apple);
        const img = await createImageBitmap(await appleRes.blob());
        const reg = 'serviceWorker' in navigator ? await Promise.race([navigator.serviceWorker.ready, new Promise(r => setTimeout(() => r(null), 15000))]) : null;
        return {m, icons, apple: {ok: appleRes.ok, w: img.width, h: img.height}, appleTitle: document.querySelector('meta[name="apple-mobile-web-app-title"]').content, sw: Boolean(reg && reg.active)};
      });
      assert.equal(r.m.short_name, '田嶋研究室');
      assert.equal(r.m.display, 'standalone');
      assert.equal(r.appleTitle, '田嶋研究室');
      assert.ok(r.icons.length >= 4 && r.icons.every(i => i.ok && /image\/png/.test(i.type)), JSON.stringify(r.icons));
      assert.ok(r.icons.some(i => i.purpose === 'maskable' && i.sizes === '512x512'));
      assert.deepEqual(r.apple, {ok: true, w: 180, h: 180});
      assert.ok(r.sw, 'service worker active');
    });

    step('論文検索と年度・分野の絞り込み', async () => {
      await tapTab('library');
      await page.fill('#paperSearch', 'ピロティ');
      const years = await page.locator('#paperRows .paper-year').allTextContents();
      assert.ok(years.includes('2023') && years.includes('2024'), years.join(','));
      await page.fill('#paperSearch', '');
      await page.selectOption('#yearFilter', '2024');
      const only = await page.locator('#paperRows .paper-year').allTextContents();
      assert.ok(only.length > 0 && only.every(y => y === '2024'), only.join(','));
      await page.selectOption('#categoryFilter', 'seismic');
      assert.ok((await page.locator('#paperRows [data-paper-id]').count()) >= 1);
      await page.selectOption('#yearFilter', 'all');
      await page.selectOption('#categoryFilter', 'all');
      assert.equal(await page.locator('#paperRows [data-paper-id]').count(), 52);
      await shot('02-library');
    });

    step('スマートフォンのファイル選択からPDFを取り込み・閲覧・本文検索', async () => {
      await page.click('.tab-item[data-action="open-sheet"]');
      const chooser = page.waitForEvent('filechooser');
      await page.click('.sheet-item[data-action="import-pdf"]');
      await (await chooser).setFiles(pdfFile);
      await page.waitForSelector('#paperRows [data-paper-id^="user-"]');
      await toastHas('この端末に保存しました');
      await page.fill('#paperSearch', 'crack');
      await page.waitForSelector('.fulltext-hits [data-page="3"]');
      await page.click('.fulltext-hits [data-page="3"]');
      await page.waitForFunction(() => document.getElementById('viewer')?.dataset.page === '3');
      const fit = await page.evaluate(() => { const c = document.getElementById('pdfCanvas'); return {w: c.getBoundingClientRect().width, vw: innerWidth}; });
      assert.ok(fit.w <= fit.vw && fit.w > fit.vw * 0.7, JSON.stringify(fit)); // fit to the phone's width
      await page.click('[data-action="pdf-next"]');
      await page.waitForFunction(() => document.getElementById('viewer')?.dataset.page === '4'); // Japanese page (CMap)
      await shot('03-pdf-viewer');
      await page.click('[data-action="pdf-cite"]');
      await page.click('[data-action="close-viewer"]');
      await page.fill('#paperSearch', '');
    });

    step('要約・研究メモを保存し、再起動（再読み込み）後も残る', async () => {
      await tapTab('summary');
      await page.selectOption('#summaryPaper', 'tajima-002');
      await page.fill('#s-objective', `${eng.key}: 本文確認前のテスト入力`);
      await page.fill('#paperMemo', `${eng.key} メモ 再起動後も残ること`);
      await page.click('#saveSummary');
      await toastHas('要約・研究メモを保存しました');
      await shot('04-notes');
      await page.reload();
      await page.waitForSelector('body[data-ready="true"]');
      await tapTab('summary');
      await page.selectOption('#summaryPaper', 'tajima-002');
      assert.equal(await page.inputValue('#paperMemo'), `${eng.key} メモ 再起動後も残ること`);
      assert.equal(await page.inputValue('#s-objective'), `${eng.key}: 本文確認前のテスト入力`);
    });

    step('研究スケジュールの編集が保存される', async () => {
      await more('[data-tab="plan"]');
      await page.check('[data-done-id="milestone-0"]');
      await page.waitForFunction(() => document.getElementById('planProgress')?.textContent.startsWith('1/9'));
      await page.fill('[data-date-id="milestone-2"]', '2027-01-15');
      await page.dispatchEvent('[data-date-id="milestone-2"]', 'change');
      await toastHas('仮予定を保存しました');
      assert.match(await page.textContent('#planNotice'), /仮予定/);
      await shot('05-plan');
      await page.reload();
      await page.waitForSelector('body[data-ready="true"]');
      await more('[data-tab="plan"]');
      assert.ok(await page.isChecked('[data-done-id="milestone-0"]'));
      assert.equal(await page.inputValue('[data-date-id="milestone-2"]'), '2027-01-15');
    });

    step('分布グラフ（年度別・分野別）', async () => {
      await tapTab('analysis');
      const total = Number(await page.locator('.stats .stat b').first().textContent());
      assert.equal(total, 53);
      assert.equal(Number(await page.textContent('#yearSum')), total);
      assert.ok((await page.locator('.vchart').first().locator('.vcol').count()) >= 10);
      assert.match(await page.textContent('#categoryNote'), /重複計上/);
      await shot('06-analysis');
    });

    step('新しい研究テーマから先行研究を検索', async () => {
      await more('[data-tab="ideas"]');
      await page.click('[data-action="example-topic"][data-topic="旧耐震 RC ピロティ 崩壊"]');
      await page.click('[data-action="recommend"]');
      assert.ok((await page.locator('#recommendList .recommend-row').count()) > 0);
      assert.match(await page.textContent('#recommendList .recommend-row'), /ピロティ/);
      await shot('07-ideas');
    });

    step('オフライン：通信が無い状態でアプリを開き直しても起動・検索・PDF閲覧ができる', async () => {
      await reopen({offline: true});
      try {
        if (server) assert.equal(await new Promise(r => http.get(base, () => r('online')).on('error', () => r('offline'))), 'offline');
        assert.equal(await page.textContent('#statTotal'), '53');
        await tapTab('library');
        await page.fill('#paperSearch', '耐震補強について'); // Japanese text of the imported PDF
        await page.waitForSelector('.fulltext-hits [data-page="4"]');
        await page.click('.fulltext-hits [data-page="4"]');
        await page.waitForFunction(() => document.getElementById('viewer')?.dataset.page === '4');
        await shot('08-offline-viewer');
        await page.click('[data-action="close-viewer"]');
        await page.fill('#paperSearch', '');
      } finally { await reopen({offline: false}); }
    });

    step('バックアップ（共有シート/ダウンロード）と復元', async () => {
      // 1) Share sheet path used on phones: capture the file handed to navigator.share()
      await page.evaluate(() => {
        window.__shared = null;
        Object.defineProperty(navigator, 'canShare', {configurable: true, value: data => Boolean(data && data.files)});
        Object.defineProperty(navigator, 'share', {configurable: true, value: async data => { const f = data.files[0]; window.__shared = {name: f.name, type: f.type, text: await f.text()}; }});
      });
      await more('[data-action="export"]');
      await page.waitForFunction(() => window.__shared);
      const shared = await page.evaluate(() => window.__shared);
      assert.match(shared.name, /^tajima-lab-backup-\d{4}-\d{2}-\d{2}\.json$/);
      assert.equal(shared.type, 'application/json');
      const backup = JSON.parse(shared.text);
      assert.equal(backup.papers.length, 53);
      assert.match(backup.note, /PDFファイル本体は含まれません/);
      // 2) Download path (browsers without the share sheet)
      await page.evaluate(() => { Object.defineProperty(navigator, 'share', {configurable: true, value: undefined}); Object.defineProperty(navigator, 'canShare', {configurable: true, value: undefined}); });
      const download = page.waitForEvent('download');
      await more('[data-action="export"]');
      const file = path.join(work, `${eng.key}-backup.json`);
      await (await download).saveAs(file);
      assert.equal(JSON.parse(fs.readFileSync(file, 'utf8')).papers.length, 53);
      // 3) Change data, then restore from the file
      await tapTab('summary');
      await page.selectOption('#summaryPaper', 'tajima-002');
      await page.fill('#paperMemo', '上書きされるべき一時メモ');
      await page.click('#saveSummary');
      await toastHas('要約・研究メモを保存しました');
      await page.click('.tab-item[data-action="open-sheet"]');
      const chooser = page.waitForEvent('filechooser');
      await page.click('.sheet-item[data-action="import-json"]');
      await (await chooser).setFiles(file);
      await toastHas('データを復元しました');
      await tapTab('summary');
      await page.selectOption('#summaryPaper', 'tajima-002');
      assert.equal(await page.inputValue('#paperMemo'), `${eng.key} メモ 再起動後も残ること`);
    });

    step('設定画面：保存場所・オフライン状態・両OSの追加手順', async () => {
      await more('[data-tab="settings"]');
      await page.waitForFunction(() => !/確認中/.test(document.getElementById('offlineState')?.textContent || '確認中'));
      assert.match(await page.textContent('#offlineState'), /利用できます/);
      const text = await page.textContent('#content');
      assert.match(text, /iPhone（Safari）でホーム画面に追加/);
      assert.match(text, /Android（Chrome）でホーム画面に追加/);
      assert.match(text, /外部のサーバーへ送信されることはありません/);
      await shot('09-settings');
    });

    step('コンソールエラー・未捕捉例外・読み込み失敗がない', () => {
      assert.deepEqual(problems, []);
    });
  });
}

describe('iPhoneのホーム画面から起動した状態（WebKit・navigator.standaloneを模擬）', () => {
  it('独立画面の表示：ブラウザ用の案内を出さず「WEB APP」表示になる', async t => {
    let browser;
    try { browser = await ENGINES[1].launch(); } catch (e) { t.skip('webkit not installed'); return; }
    try {
      const ctx = await browser.newContext({...devices['iPhone 15']});
      await ctx.addInitScript(() => Object.defineProperty(navigator, 'standalone', {get: () => true}));
      const page = await ctx.newPage();
      await page.goto(base);
      await page.waitForSelector('body[data-ready="true"]');
      assert.equal(await page.evaluate(() => document.body.dataset.display), 'standalone');
      assert.equal(await page.locator('#installCard').count(), 0);
      if (shots) await page.screenshot({path: path.join(shots, 'ios-10-standalone-emulated.png')});
    } finally { await browser.close(); }
  });
});

describe('Chromium（Android Chromeと同じBlinkエンジン）：実際にインストールして独立画面で起動', () => {
  it('インストール可能判定エラーなし → PWAとしてインストール → standaloneで起動', async t => {
    if (process.platform === 'linux' && !process.env.DISPLAY) { t.skip('needs a display (run with xvfb-run)'); return; }
    const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'tajima-pwa-'));
    let ctx;
    try {
      ctx = await chromium.launchPersistentContext(profile, {headless: false, viewport: {width: 412, height: 860}, ...(process.env.TAJIMA_CHROMIUM ? {executablePath: process.env.TAJIMA_CHROMIUM} : {}), ...(webProxy() ? {proxy: webProxy()} : {})});
      const page = ctx.pages()[0] || await ctx.newPage();
      await page.goto(base);
      await page.waitForSelector('body[data-ready="true"]');
      await page.evaluate(() => navigator.serviceWorker.ready);
      const cdp = await ctx.newCDPSession(page);
      const errors = await cdp.send('Page.getInstallabilityErrors');
      assert.deepEqual(errors.installabilityErrors, []);
      const {appId} = await cdp.send('Page.getAppId');
      const bcdp = await ctx.browser().newBrowserCDPSession();
      try { await bcdp.send('PWA.install', {manifestId: appId, installUrlOrBundleUrl: base}); }
      catch (e) { if (/wasn't found/.test(e.message)) { t.skip('this Chromium build has no PWA install API'); return; } throw e; }
      await bcdp.send('PWA.changeAppUserSettings', {manifestId: appId, displayMode: 'standalone'});
      await bcdp.send('PWA.launch', {manifestId: appId});
      let app = null;
      for (let i = 0; i < 40 && !app; i++) {
        for (const p of ctx.pages()) if (await p.evaluate(() => matchMedia('(display-mode: standalone)').matches).catch(() => false)) app = p;
        if (!app) await new Promise(r => setTimeout(r, 250));
      }
      assert.ok(app, 'standalone app window');
      await app.waitForSelector('body[data-ready="true"]');
      assert.equal(await app.textContent('#modePill'), 'WEB APP · LOCAL');
      assert.equal(await app.locator('#installCard').count(), 0);
      if (shots) await app.screenshot({path: path.join(shots, 'android-10-installed-standalone.png')});
    } finally { await ctx?.close(); try { fs.rmSync(profile, {recursive: true, force: true}); } catch (_) { /* ignore */ } }
  });
});
