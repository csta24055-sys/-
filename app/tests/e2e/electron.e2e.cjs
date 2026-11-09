'use strict';
// Real GUI end-to-end test: drives the Electron app with Playwright (acceptance tests A01–A11, A14).
// Linux needs a display: `xvfb-run -a npm run test:e2e`. Set TAJIMA_SCREENSHOTS=<dir> to save screenshots.
// Set TAJIMA_ELECTRON_BIN=<path to packaged app executable> to run the same checks against a built app.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {_electron} = require('playwright-core');
const {samplePdf} = require('../helpers/make-pdf.cjs');

const appDir = path.resolve(__dirname, '../..');
const work = fs.mkdtempSync(path.join(os.tmpdir(), 'tajima-e2e-'));
const userData = path.join(work, 'userData');
const pdfFile = path.join(work, 'Seismic_sample.pdf');
const backupFile = path.join(work, 'backup.json');
const shots = process.env.TAJIMA_SCREENSHOTS ? path.resolve(process.env.TAJIMA_SCREENSHOTS) : '';
fs.writeFileSync(pdfFile, samplePdf());
if (shots) fs.mkdirSync(shots, {recursive: true});

const problems = [];
let app, win;
async function launch() {
  const packaged = process.env.TAJIMA_ELECTRON_BIN;
  app = await _electron.launch({
    executablePath: packaged || require('electron'),
    args: packaged ? ['--no-sandbox'] : ['--no-sandbox', appDir],
    env: {...process.env, TAJIMA_USER_DATA: userData, ELECTRON_ENABLE_LOGGING: '0'}
  });
  win = await app.firstWindow();
  win.on('console', m => { if (m.type() === 'error') problems.push('console: ' + m.text()); });
  win.on('pageerror', e => problems.push('pageerror: ' + e.message));
  win.on('requestfailed', r => problems.push('requestfailed: ' + r.url()));
  win.on('dialog', d => d.accept());
  await win.setViewportSize({width: 1370, height: 900}).catch(() => {});
  await win.waitForSelector('body[data-ready="true"]');
}
async function shot(name) { if (shots) await win.screenshot({path: path.join(shots, name + '.png')}); }
async function tab(name) { await win.click(`.nav-item[data-tab="${name}"]`); }
async function mockOpenDialog(file) {
  await app.evaluate(({dialog}, f) => { dialog.showOpenDialog = async () => ({canceled: false, filePaths: [f]}); }, file);
}
const rows = () => win.locator('#paperRows [data-paper-id]');

test.before(launch);
test.after(async () => { if (app) await app.close(); try { fs.rmSync(work, {recursive: true, force: true}); } catch (_) { /* Windows may keep files locked briefly */ } });

test('A01 初回起動で52件・デスクトップモード', async () => {
  assert.equal(await win.textContent('#statTotal'), '52');
  assert.equal(await win.textContent('#modePill'), 'DESKTOP · LOCAL');
  await shot('01-dashboard');
  await tab('library');
  assert.equal(await rows().count(), 52);
});

test('A02 研究室公式掲載の絞り込みで6件', async () => {
  await win.selectOption('#collectionFilter', 'lab');
  assert.equal(await rows().count(), 6);
  await win.selectOption('#collectionFilter', 'all');
});

test('A03 「ピロティ」検索で2023・2024の論文', async () => {
  await win.fill('#paperSearch', 'ピロティ');
  const years = await win.locator('#paperRows .paper-year').allTextContents();
  assert.ok(years.includes('2023') && years.includes('2024'), years.join(','));
  await shot('02-library-search');
});

test('A04 論文詳細に著者・掲載誌・年度・出典・全文未登録', async () => {
  await win.click('#paperRows [data-action="paper"][data-id="tajima-002"]');
  const text = await win.textContent('#modal');
  for (const s of ['著者', '伊豆川瞬也', '発表年', '2024年', '掲載先', 'コンクリート工学年次論文集', '全文未登録', 'https://www.arch.cst.nihon-u.ac.jp/lab/lab-258/']) assert.ok(text.includes(s), s);
  await shot('03-paper-detail');
  await win.click('[data-action="close-modal"]');
  await win.fill('#paperSearch', '');
});

test('A05 要約・メモを保存', async () => {
  await tab('summary');
  await win.selectOption('#summaryPaper', 'tajima-002');
  await win.fill('#s-objective', 'E2E: 本文確認前のテスト入力');
  await win.fill('#paperMemo', 'E2Eメモ 再起動後も残ること');
  await win.click('#saveSummary');
  await win.waitForSelector('#toast.show');
  await shot('04-summary');
});

test('A09 研究計画の日付と完了を保存・仮予定表示', async () => {
  await tab('plan');
  assert.match(await win.textContent('#planNotice'), /仮予定/);
  await win.fill('#planStart', '2026-04-01');
  await win.click('[data-action="reset-plan"]');
  await win.waitForFunction(() => document.querySelector('[data-date-id="milestone-1"]')?.value === '2026-04-15');
  await win.fill('[data-date-id="milestone-1"]', '2026-05-07');
  await win.dispatchEvent('[data-date-id="milestone-1"]', 'change');
  await win.check('[data-done-id="milestone-0"]');
  await win.waitForFunction(() => document.getElementById('planProgress')?.textContent.startsWith('1/9'));
  await shot('05-plan');
});

test('A06/A07 分布分析：年度合計＝登録件数、重複計数の注記', async () => {
  await tab('analysis');
  assert.equal(await win.textContent('#yearSum'), '52');
  assert.match(await win.textContent('#categoryNote'), /重複計上/);
  await shot('06-analysis');
});

test('A08 新規研究テーマ → 実在する候補と理由', async () => {
  await tab('ideas');
  await win.fill('#topicInput', '旧耐震 RC ピロティ 崩壊');
  await win.click('[data-action="recommend"]');
  const n = await win.locator('#recommendList .recommend-row').count();
  assert.ok(n > 0);
  const first = await win.textContent('#recommendList .recommend-row');
  assert.match(first, /ピロティ/);
  assert.match(await win.textContent('#recommendList .recommend-reason'), /分野一致|文字列一致|同義語/);
  await shot('07-ideas');
});

test('A10 PDF取り込み → userData/pdfs に保存・本文索引・内蔵ビューア・根拠ページ', async () => {
  await mockOpenDialog(pdfFile);
  await win.click('.sidebar [data-action="import-pdf"]');
  await win.waitForSelector('#paperRows [data-paper-id^="user-"]');
  const saved = fs.readdirSync(path.join(userData, 'pdfs'));
  assert.equal(saved.length, 1);
  assert.match(saved[0], /^[0-9a-f]{64}\.pdf$/);
  // Title candidate comes from the PDF metadata, not invented.
  const userRow = win.locator('#paperRows [data-paper-id^="user-"]');
  assert.match(await userRow.textContent(), /Seismic Damage Evaluation of RC Piloti Columns/);
  // Full-text search over the imported PDF (synonym: クラック not used; English word on page 3)
  await win.fill('#paperSearch', 'crack');
  await win.waitForSelector('.fulltext-hits [data-page="3"]');
  await win.click('.fulltext-hits [data-page="3"]');
  await win.waitForFunction(() => document.getElementById('viewer')?.dataset.page === '3');
  const painted = await win.evaluate(() => { const c = document.getElementById('pdfCanvas'); const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let dark = 0; for (let i = 0; i < d.length; i += 16) if (d[i] < 128) dark++; return {w: c.width, dark}; });
  assert.ok(painted.w > 100 && painted.dark > 20, JSON.stringify(painted));
  await shot('08-pdf-viewer');
  await win.click('[data-action="pdf-cite"]');
  // Japanese text via predefined CMap (UniJIS-UCS2-H) is extracted and searchable.
  await win.click('[data-action="close-viewer"]');
  await win.fill('#paperSearch', '耐震補強について');
  await win.waitForSelector('.fulltext-hits [data-page="4"]');
  await win.click('.fulltext-hits [data-page="4"]');
  await win.waitForFunction(() => document.getElementById('viewer')?.dataset.page === '4');
  await shot('08b-pdf-viewer-japanese');
  await win.click('[data-action="close-viewer"]');
  await win.fill('#paperSearch', '');
  // Detail of the imported paper shows extracted candidates with their evidence
  const id = await userRow.getAttribute('data-paper-id');
  await win.click(`#paperRows [data-action="paper"][data-id="${id}"]`);
  const modalText = await win.textContent('#candidateBox');
  assert.match(modalText, /PDFメタデータ/);
  assert.match(modalText, /Taro Test/);
  await shot('09-pdf-candidates');
  await win.click('[data-action="close-modal"]');
  // Attach the same PDF to an official record: bibliography stays untouched.
  await mockOpenDialog(pdfFile);
  await win.click('#paperRows [data-action="paper"][data-id="tajima-002"]');
  await win.click('#modal [data-action="attach-pdf"]');
  await win.waitForFunction(() => document.getElementById('modal').textContent.includes('PDF登録済み'));
  assert.match(await win.textContent('#modal .modal-title'), /旧耐震基準で設計されたRC造ピロティ建物/);
  await win.click('[data-action="close-modal"]');
});

test('A11 JSONバックアップの書き出しと復元（PDF本体は含まない旨を明示）', async () => {
  await app.evaluate(({dialog}, f) => { dialog.showSaveDialog = async () => ({canceled: false, filePath: f}); }, backupFile);
  await win.click('.sidebar [data-action="export"]');
  await win.waitForFunction(() => document.getElementById('toast').textContent.includes('PDF本体は含みません'));
  const backup = JSON.parse(fs.readFileSync(backupFile, 'utf8'));
  assert.equal(backup.papers.length, 53);
  assert.match(backup.note, /PDFファイル本体は含まれません/);
  const userPaper = backup.papers.find(p => p.isUserAdded);
  assert.match(userPaper.summary.sourcePages, /p\.3/);
  assert.equal(userPaper.pdfText.length, 4);
  assert.match(userPaper.pdfText[3], /ひび割れと耐震補強/);
  // change something, then restore
  await tab('summary');
  await win.selectOption('#summaryPaper', 'tajima-002');
  await win.fill('#paperMemo', '上書きされるべき一時メモ');
  await win.click('#saveSummary');
  await win.setInputFiles('#jsonInput', backupFile);
  await win.waitForFunction(() => document.getElementById('toast').textContent.includes('復元しました'));
  await tab('summary');
  await win.selectOption('#summaryPaper', 'tajima-002');
  assert.equal(await win.inputValue('#paperMemo'), 'E2Eメモ 再起動後も残ること');
});

test('再起動後もメモ・予定・PDF紐づけが保持される', async () => {
  await app.close();
  await launch();
  assert.equal(await win.textContent('#statTotal'), '53');
  await tab('summary');
  await win.selectOption('#summaryPaper', 'tajima-002');
  assert.equal(await win.inputValue('#paperMemo'), 'E2Eメモ 再起動後も残ること');
  assert.equal(await win.inputValue('#s-objective'), 'E2E: 本文確認前のテスト入力');
  await tab('plan');
  assert.equal(await win.inputValue('[data-date-id="milestone-1"]'), '2026-05-07');
  assert.ok(await win.isChecked('[data-done-id="milestone-0"]'));
  await tab('library');
  await win.click('#paperRows [data-action="view-pdf"][data-id="tajima-002"]');
  await win.waitForFunction(() => document.getElementById('viewer')?.dataset.page === '1');
  await win.click('[data-action="close-viewer"]');
});

test('保存ファイル破損時はバックアップから復元し、破損ファイルを保管', async () => {
  await app.close();
  fs.writeFileSync(path.join(userData, 'tajima-state.json'), '{broken json');
  await launch();
  const kept = fs.readdirSync(userData).filter(f => f.includes('.corrupt-'));
  assert.equal(kept.length, 1);
  assert.ok(Number(await win.textContent('#statTotal')) >= 52);
  await win.waitForFunction(() => document.getElementById('toast').textContent.includes('バックアップから復元'));
});

test('A14 コンソールエラー・未捕捉例外・資源取得失敗がない', () => {
  assert.deepEqual(problems, []);
});
