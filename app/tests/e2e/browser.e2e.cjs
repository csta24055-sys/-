'use strict';
// Browser-preview end-to-end test (no Electron): serves app/ over HTTP and drives Chromium.
// Uses the Chromium that Playwright manages; set TAJIMA_CHROMIUM=<path> to use another binary.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const http = require('node:http');
const {chromium} = require('playwright-core');
const {samplePdf} = require('../helpers/make-pdf.cjs');

const appDir = path.resolve(__dirname, '../..');
const work = fs.mkdtempSync(path.join(os.tmpdir(), 'tajima-browser-'));
const pdfFile = path.join(work, 'sample_paper.pdf');
fs.writeFileSync(pdfFile, samplePdf());
const shots = process.env.TAJIMA_SCREENSHOTS ? path.resolve(process.env.TAJIMA_SCREENSHOTS) : '';
const TYPES = {'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.mjs':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json','.bcmap':'application/octet-stream','.pfb':'application/octet-stream','.ttf':'font/ttf'};

let server, base, browser, page;
const problems = [];
test.before(async () => {
  server = http.createServer((req, res) => {
    const rel = decodeURIComponent(new URL(req.url, 'http://x').pathname).replace(/^\/+/, '') || 'index.html';
    const file = path.resolve(appDir, rel);
    if (!file.startsWith(appDir + path.sep) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); res.end(); return; }
    res.writeHead(200, {'content-type': TYPES[path.extname(file)] || 'application/octet-stream'});
    fs.createReadStream(file).pipe(res);
  });
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  base = `http://127.0.0.1:${server.address().port}/`;
  browser = await chromium.launch(process.env.TAJIMA_CHROMIUM ? {executablePath: process.env.TAJIMA_CHROMIUM} : {});
  page = await browser.newPage({viewport: {width: 1370, height: 900}});
  page.on('console', m => { if (m.type() === 'error') problems.push('console: ' + m.text()); });
  page.on('pageerror', e => problems.push('pageerror: ' + e.message));
  page.on('requestfailed', r => problems.push('requestfailed: ' + r.url()));
  page.on('dialog', d => d.accept());
  await page.goto(base);
  await page.waitForSelector('body[data-ready="true"]');
});
test.after(async () => { await browser?.close(); server?.close(); try { fs.rmSync(work, {recursive: true, force: true}); } catch (_) { /* Windows may keep files locked briefly */ } });

test('ブラウザプレビュー：52件・プレビュー表示', async () => {
  assert.equal(await page.textContent('#statTotal'), '52');
  assert.equal(await page.textContent('#modePill'), 'BROWSER · PREVIEW');
});

test('ブラウザプレビュー：同義語検索（FEM → 有限要素/FEMの題名）', async () => {
  await page.click('.nav-item[data-tab="library"]');
  await page.fill('#paperSearch', 'FEM');
  const n = await page.locator('#paperRows tr[data-paper-id]').count();
  assert.ok(n >= 1);
  await page.fill('#paperSearch', '');
});

test('ブラウザプレビュー：PDF取り込み → ビューア表示・本文検索', async () => {
  await page.click('.sidebar [data-action="import-pdf"]');
  await page.setInputFiles('#pdfInput', pdfFile);
  await page.waitForSelector('#paperRows tr[data-paper-id^="user-"]');
  await page.fill('#paperSearch', 'finite element');
  await page.waitForSelector('.fulltext-hits [data-page="2"]');
  await page.click('.fulltext-hits [data-page="2"]');
  await page.waitForFunction(() => document.getElementById('viewer')?.dataset.page === '2');
  await page.click('[data-action="pdf-next"]');
  await page.waitForFunction(() => document.getElementById('viewer')?.dataset.page === '3');
  if (shots) await page.screenshot({path: path.join(shots, '10-browser-preview-pdf.png')});
  await page.click('[data-action="close-viewer"]');
  await page.fill('#paperSearch', '');
});

test('ブラウザプレビュー：メモは再読み込み後も残る（PDF本体は残らない旨を表示）', async () => {
  await page.click('.nav-item[data-tab="summary"]');
  await page.selectOption('#summaryPaper', 'tajima-001');
  await page.fill('#paperMemo', 'ブラウザメモ');
  await page.click('.panel-head [data-action="save-summary"]');
  await page.reload();
  await page.waitForSelector('body[data-ready="true"]');
  assert.equal(await page.textContent('#statTotal'), '53');
  await page.click('.nav-item[data-tab="summary"]');
  await page.selectOption('#summaryPaper', 'tajima-001');
  assert.equal(await page.inputValue('#paperMemo'), 'ブラウザメモ');
  await page.click('.nav-item[data-tab="library"]');
  const userId = await page.locator('#paperRows tr[data-paper-id^="user-"]').getAttribute('data-paper-id');
  await page.click(`#paperRows [data-action="paper"][data-id="${userId}"]`);
  assert.match(await page.textContent('#modal'), /全文未登録/);
});

test('ブラウザプレビュー：コンソールエラーなし', () => assert.deepEqual(problems, []));
