const { chromium, devices } = require('playwright');
const fs = require('fs');
const path = require('path');
const OUT = path.resolve(__dirname, '../../docs/screenshots');
const BASE = process.env.BASE || 'http://127.0.0.1:8000';
const TMP = require('os').tmpdir();
const log = (...a) => console.log(...a);
(async () => {
  const browser = await chromium.launch();
  const errors = [];
  const results = [];
  const ok = (name, cond, extra='') => { results.push([name, !!cond, extra]); log((cond ? 'PASS' : 'FAIL'), name, extra); };
  // ---------- desktop ----------
  const ctx = await browser.newContext({ viewport: { width: 1366, height: 900 }, locale: 'ja-JP' });
  const page = await ctx.newPage();
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  await page.goto(BASE + '/'); await page.waitForSelector('.stat-v');
  const statText = await page.locator('.stats').first().innerText();
  const apiDash = await (await fetch(BASE + '/api/dashboard')).json();
  ok('dashboard shows counts', /収集済み資料/.test(statText) && statText.includes(String(apiDash.counts.sources)), statText.replace(/\n/g,' '));
  await page.screenshot({ path: OUT + '/01_dashboard.png', fullPage: true });
  // library search
  await page.click('text=研究資料ライブラリ'); await page.waitForSelector('.srclist li');
  await page.fill('input[type=search]', 'バイパス');
  await page.waitForTimeout(200);
  const n1 = await page.locator('.srclist li').count();
  ok('library search バイパス', n1 >= 1 && n1 < 10, `${n1} hits`);
  await page.fill('input[type=search]', '');
  await page.selectOption('select[aria-label=年度]', '2025'); await page.selectOption('select[aria-label=調査状態]', '読了');
  const n2 = await page.locator('.srclist li').count();
  const exp2 = (await (await fetch(BASE + '/api/sources?year=2025&status=' + encodeURIComponent('読了'))).json()).length;
  ok('library filter 2025×読了 matches API', n2 === exp2 && n2 > 0, `${n2}/${exp2}`);
  await page.locator('.srclist li', { hasText: '最終梗概.pdf' }).first().click();
  await page.waitForSelector('.dtitle');
  const det = await page.locator('.detail-pane').innerText();
  ok('detail shows Box link & pages & findings', /Box で開く/.test(det) && /p\.3/.test(det) && /F-2025-02/.test(det));
  await page.screenshot({ path: OUT + '/02_library.png', fullPage: true });
  // status persist
  await page.selectOption('select[aria-label=調査状態]', '');
  await page.selectOption('select[aria-label=年度]', '2025');
  await page.locator('.srclist li', { hasText: '本論 .pdf（2025年度）' }).click();
  await page.waitForSelector('.statusbar');
  await page.click('.statusbar button:has-text("読了")'); await page.waitForTimeout(500);
  await page.fill('.detail-pane textarea', 'E2Eテスト: p.1-5 確認'); await page.click('text=メモを保存'); await page.waitForTimeout(500);
  await page.reload(); await page.waitForSelector('.statusbar button.on');
  const on = await page.locator('.statusbar button.on').innerText();
  const memo = await page.locator('.detail-pane textarea').inputValue();
  ok('status+memo persist after reload', on === '読了' && memo.includes('E2E'), on + ' / ' + memo);
  // data analysis: CSV upload
  const csv = ['日時,外気,室内,上流,下流'];
  for (let i = 0; i < 180; i++) { const t = new Date(Date.UTC(2025,8,17,0,i)).toISOString().slice(0,16).replace('T',' ');
    const o = 10 + 5*Math.sin(i/20); csv.push(`${t},${o.toFixed(2)},${(0.55*o + (i%7)*0.05).toFixed(2)},${1000+i},${(50+i*0.05).toFixed(1)}`); }
  csv[50] = csv[50].replace(/,[^,]+,([^,]+),([^,]+)$/, ',,$1,$2'); csv[90] = csv[90].replace(/^([^,]+),[^,]+/, '$1,400');
  fs.writeFileSync(path.join(TMP, 'aqros_sample.csv'), csv.join('\n'));
  await page.goto(BASE + '/data'); await page.waitForSelector('input[type=file]');
  await page.setInputFiles('input[type=file]', path.join(TMP, 'aqros_sample.csv'));
  await page.waitForSelector('text=異常値・欠損値の検出', { timeout: 10000 });
  const q = await page.locator('.card', { hasText: '異常値・欠損値の検出' }).innerText();
  ok('quality detects missing & outlier', /室内\s+1（/.test(q) && /外気\s+0（0\.0%）\s+1/.test(q), q.split('\n').slice(2,6).join(' | '));
  await page.selectOption('.card:has-text("解析") select >> nth=0', '外気');
  await page.selectOption('.card:has-text("解析") select >> nth=1', '室内');
  await page.click('text=異常値を解析から除外する');
  await page.waitForTimeout(400);
  const kv = await page.locator('.kvtable').innerText();
  const k = parseFloat(kv.match(/回帰係数 k（原点通過）\s+([\d.]+)/)[1]);
  ok('I/O regression k≈0.56', Math.abs(k - 0.567) < 0.03, 'k=' + k);
  await page.screenshot({ path: OUT + '/03_data_analysis.png', fullPage: true });
  await page.click('.tabs button:has-text("粒径別除去効率")');
  await page.selectOption('.card:has-text("解析") select >> nth=0', '上流');
  await page.selectOption('.card:has-text("解析") select >> nth=1', '下流');
  await page.waitForTimeout(300);
  const eff = await page.locator('.kvtable').innerText();
  ok('removal efficiency computed', /除去効率 η/.test(eff) && /9[45]\./.test(eff), eff.split('\n')[0]);
  const [dl] = await Promise.all([page.waitForEvent('download'), page.click('text=結果をCSV出力')]);
  ok('result CSV export', (await dl.suggestedFilename()).endsWith('.csv'), await dl.suggestedFilename());
  const [dl2] = await Promise.all([page.waitForEvent('download'), page.locator('.chartbox button:has-text("画像保存")').first().click()]);
  ok('chart PNG export', (await dl2.suggestedFilename()).endsWith('.png'), await dl2.suggestedFilename());
  // demo dataset
  await page.click('text=合成デモデータを作成'); await page.waitForSelector('text=【合成デモ】', { timeout: 10000 });
  ok('synthetic demo dataset created', true);
  // simulator
  await page.goto(BASE + '/simulator'); await page.waitForSelector('.stat-v');
  await page.locator('.row4 input[type=number]').first().fill('5');
  await page.selectOption('.row4 select >> nth=2', 'fit');
  await page.locator('.slider').first().locator('input[type=number]').fill('0');
  await page.waitForTimeout(300);
  const cadr = await page.locator('.stat-v').first().innerText();
  ok('simulator reproduces CADR≈741 (5台,0%)', cadr.replace(/,/g,'') === '741', cadr);
  await page.locator('.row4 input[type=number]').first().fill('10');
  await page.waitForTimeout(300);
  const warnTxt = await page.locator('.warnlist').first().innerText().catch(() => '');
  ok('extrapolation warning shown', /実測範囲/.test(warnTxt), warnTxt.slice(0, 60));
  await page.click('text=この運転点を室内濃度モデルに反映');
  await page.screenshot({ path: OUT + '/04_simulator.png', fullPage: true });
  // graph
  await page.goto(BASE + '/graph'); await page.waitForSelector('svg .gnode');
  await page.locator('.gnode', { hasText: '2025年度' }).first().click();
  const gd = await page.locator('.graph-detail').innerText();
  ok('graph node detail with sources', /資料根拠/.test(gd) && /S-2025-01/.test(gd));
  await page.screenshot({ path: OUT + '/05_graph.png', fullPage: true });
  // plan
  await page.goto(BASE + '/plan'); await page.waitForSelector('table.rank');
  page.once('dialog', d => d.accept('E2E: 外挿依存の解消が最優先'));
  await page.click('.card-actions button:has-text("採択")'); await page.waitForTimeout(600);
  await page.reload(); await page.waitForSelector('table.rank');
  ok('theme decision persisted', /採択/.test(await page.locator('table.rank').innerText()));
  await page.screenshot({ path: OUT + '/06_plan.png', fullPage: true });
  // report
  await page.goto(BASE + '/report'); await page.waitForSelector('.md h1');
  const rep = await page.locator('.md').first().innerText();
  ok('report renders markdown', /研究史/.test(rep));
  const [dl3] = await Promise.all([page.waitForEvent('download'), page.click('text=Markdown出力')]);
  ok('report markdown export', (await dl3.suggestedFilename()).endsWith('.md'));
  await page.screenshot({ path: OUT + '/07_report.png' });
  const pdf = await page.pdf({ path: path.join(TMP, 'aqros_report.pdf'), format: 'A4' }).catch(e => null);
  ok('report print to PDF', !!pdf, pdf ? `${pdf.length} bytes` : '');
  // offline: service worker cached → go offline and reload
  await page.goto(BASE + '/'); await page.waitForTimeout(1500);
  await page.goto(BASE + '/library'); await page.waitForSelector('.srclist li'); await page.waitForTimeout(800);
  await ctx.setOffline(true);
  await page.reload().catch(()=>{}); await page.waitForTimeout(1500);
  const offTxt = await page.content();
  ok('offline reload still shows library', /S-2026-01/.test(offTxt) || /研究資料ライブラリ/.test(offTxt));
  await page.goto(BASE + '/simulator').catch(()=>{}); await page.waitForTimeout(800);
  ok('offline simulator works', /CADR/.test(await page.content()));
  await ctx.setOffline(false);
  // ---------- iPhone ----------
  const ip = await browser.newContext({ ...devices['iPhone 13'], locale: 'ja-JP' });
  const mp = await ip.newPage();
  mp.on('pageerror', e => errors.push('mobile pageerror: ' + e.message));
  for (const [path, name] of [['/', 'm01_dashboard'], ['/library/S-2026-01', 'm02_library'], ['/data', 'm03_data'], ['/simulator', 'm04_simulator'], ['/graph', 'm05_graph'], ['/plan', 'm06_plan'], ['/report', 'm07_report']]) {
    await mp.goto(BASE + path); await mp.waitForTimeout(900);
    const sw = await mp.evaluate(() => document.documentElement.scrollWidth); const vw = await mp.evaluate(() => window.innerWidth);
    ok(`mobile ${path} no horizontal page scroll`, sw <= vw + 1, `${sw}/${vw}`);
    await mp.screenshot({ path: `${OUT}/${name}.png` });
  }
  ok('mobile tabbar visible', await mp.locator('.tabbar').isVisible());
  ok('no JS errors', errors.length === 0, errors.slice(0, 5).join(' || '));
  fs.writeFileSync(OUT + '/e2e_results.json', JSON.stringify(results, null, 1));
  await browser.close();
  log(`\n${results.filter(r=>r[1]).length}/${results.length} passed`);
})();
