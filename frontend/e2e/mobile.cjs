// スマホ単体版（PWA）の自動テスト — Playwright（Chromium）で iPhone / Android の画面・タッチを再現する。
// 注意: iPhone は Chromium での「iPhone 13 相当（画面サイズ・UA・タッチ）」の再現であり、実機の Safari / WebKit ではない。
//
//   node e2e/mobile.cjs                         # 既定: http://127.0.0.1:47801/（dist-mobile を静的配信しておく）
//   BASE=http://127.0.0.1:47801 node e2e/mobile.cjs
//
// クラウド解析は GitHub API を模したローカルサーバー（このファイル内）で検証する。
// 模擬サーバーはブランチ作成時に cloud/run_job.py を実際に実行して結果を返す（GitHub Actions そのものは動かさない）。
const { chromium, devices } = require('playwright');
const fs = require('fs');
const http = require('http');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');

const BASE = (process.env.BASE || 'http://127.0.0.1:47801').replace(/\/$/, '');
const ROOT = path.resolve(__dirname, '../..');
const PY = process.env.PYTHON || (fs.existsSync(path.join(ROOT, '.venv/bin/python')) ? path.join(ROOT, '.venv/bin/python') : 'python3');
const SHOTS = path.join(ROOT, 'docs/screenshots/mobile');
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'aqros-mobile-'));
fs.mkdirSync(SHOTS, { recursive: true });

const results = [];
const ok = (dev, name, cond, extra = '') => { results.push({ device: dev, name, pass: !!cond, extra: String(extra).slice(0, 300) }); console.log(cond ? 'PASS' : 'FAIL', `[${dev}]`, name, extra ? '— ' + String(extra).slice(0, 160) : ''); };

// ------------------------------------------------------------------ GitHub API の模擬
function mockGitHub({ isPrivate }) {
  const refs = {}; const blobs = {}; const trees = {}; const commits = { base: { tree: { sha: 'tree0' } } };
  const files = {}; // branch -> { path: Buffer }
  const runs = {};
  let n = 0; const sha = () => 'sha' + (++n);
  const server = http.createServer((req, res) => {
    const send = (code, body, raw) => {
      res.writeHead(code, { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': '*', 'Access-Control-Allow-Methods': '*', 'Content-Type': raw ? 'application/octet-stream' : 'application/json' });
      res.end(raw ? body : body === undefined ? '' : JSON.stringify(body));
    };
    if (req.method === 'OPTIONS') return send(204);
    let data = ''; req.on('data', (c) => (data += c)); req.on('end', () => {
      const u = new URL(req.url, 'http://x'); const p = decodeURIComponent(u.pathname); const b = data ? JSON.parse(data) : {};
      if ((req.headers.authorization || '') !== 'Bearer test-token') return send(401, { message: 'Bad credentials' });
      const R = '/repos/lab/aq-jobs';
      if (req.method === 'GET' && p === R) return send(200, { full_name: 'lab/aq-jobs', private: isPrivate, permissions: { push: true } });
      if (req.method === 'GET' && p === `${R}/contents/.github/workflows/cloud-jobs.yml`) return send(200, { name: 'cloud-jobs.yml' });
      if (req.method === 'GET' && p.startsWith(`${R}/git/ref/heads/`)) return send(200, { object: { sha: 'base' } });
      if (req.method === 'GET' && p.startsWith(`${R}/git/commits/`)) return send(200, commits[p.split('/').pop()] || commits.base);
      if (req.method === 'POST' && p === `${R}/git/blobs`) { const s = sha(); blobs[s] = Buffer.from(b.content, 'base64'); return send(201, { sha: s }); }
      if (req.method === 'POST' && p === `${R}/git/trees`) { const s = sha(); trees[s] = b.tree; return send(201, { sha: s }); }
      if (req.method === 'POST' && p === `${R}/git/commits`) { const s = sha(); commits[s] = { tree: { sha: b.tree } }; return send(201, { sha: s }); }
      if (req.method === 'POST' && p === `${R}/git/refs`) {
        const branch = b.ref.replace('refs/heads/', ''); refs[branch] = b.sha;
        const work = fs.mkdtempSync(path.join(TMP, 'job-'));
        for (const e of trees[commits[b.sha].tree.sha]) { const fp = path.join(work, e.path); fs.mkdirSync(path.dirname(fp), { recursive: true }); fs.writeFileSync(fp, blobs[e.sha]); }
        const id = branch.replace('aqros-job/', '');
        // GitHub Actions の代わりに run_job.py を実行（AQROS_REPO_PRIVATE は実際のワークフローと同じく「リポジトリ設定」から与える）
        execFileSync(PY, ['-c', `import sys; sys.path.insert(0, ${JSON.stringify(path.join(ROOT, 'cloud'))}); import run_job as R; from pathlib import Path; R.run(${JSON.stringify(id)}, Path(${JSON.stringify(work)}))`],
          { env: { ...process.env, AQROS_REPO_PRIVATE: String(isPrivate) }, stdio: 'pipe' });
        const out = path.join(work, 'cloud_jobs/outbox', id);
        files[branch] = {}; for (const f of fs.readdirSync(out)) files[branch][`cloud_jobs/outbox/${id}/${f}`] = fs.readFileSync(out + '/' + f);
        files[branch].__inbox_inputs_left = fs.existsSync(path.join(work, 'cloud_jobs/inbox', id, 'inputs'));
        runs[branch] = { status: 'completed', conclusion: 'success', html_url: 'https://example.invalid/run' };
        return send(201, { ref: b.ref });
      }
      if (req.method === 'GET' && p === `${R}/actions/runs`) { const r = runs[u.searchParams.get('branch')]; return send(200, { workflow_runs: r ? [r] : [] }); }
      if (req.method === 'GET' && p.startsWith(`${R}/contents/`)) {
        const fp = p.slice(`${R}/contents/`.length); const fsb = files[u.searchParams.get('ref')] || {};
        if (fsb[fp]) return send(200, fsb[fp], true);
        const list = Object.keys(fsb).filter((k) => k.startsWith(fp + '/')).map((k) => ({ type: 'file', name: k.split('/').pop(), path: k }));
        return list.length ? send(200, list) : send(404, { message: 'Not Found' });
      }
      if (req.method === 'DELETE' && p.startsWith(`${R}/git/refs/heads/`)) { const br = p.slice(`${R}/git/refs/heads/`.length); delete refs[br]; delete files[br]; return send(204); }
      send(404, { message: 'mock: ' + req.method + ' ' + p });
    });
  });
  return new Promise((resolve) => server.listen(0, '127.0.0.1', () => resolve({ server, url: `http://127.0.0.1:${server.address().port}`, refs, files })));
}

async function shot(page, dev, name) { await page.screenshot({ path: path.join(SHOTS, `${dev}_${name}.png`) }); }

async function run(dev, devName, ghPrivate) {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ ...devices[devName], locale: 'ja-JP', acceptDownloads: true });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => { if (m.type() === 'error' && !/favicon|ERR_INTERNET_DISCONNECTED|Failed to load resource/.test(m.text())) errors.push(m.text()); });

  // 1. 起動・ダッシュボード（公開データ seed.json から）
  await page.goto(BASE + '/'); await page.waitForSelector('.stat-v', { timeout: 20000 });
  const stats = await page.locator('.stats').first().innerText();
  ok(dev, 'ダッシュボード表示（サーバーなし）', /収集済み資料/.test(stats) && /95/.test(stats), stats.replace(/\s+/g, ' '));
  await shot(page, dev, '01_dashboard');
  const vw = await page.evaluate(() => ({ w: innerWidth, sw: document.documentElement.scrollWidth }));
  ok(dev, '横スクロールなし', vw.sw <= vw.w + 1, JSON.stringify(vw));

  // 2. PWA 設定
  const man = await page.evaluate(async () => { const l = document.querySelector('link[rel=manifest]'); const r = await fetch(l.href); return r.json(); });
  ok(dev, 'マニフェスト（名前・独立画面・アイコン）', man.short_name === '空気清浄度研究' && man.display === 'standalone' && man.icons.some((i) => i.sizes === '512x512' && i.purpose === 'maskable') && man.icons.some((i) => i.sizes === '192x192'), `${man.short_name} / ${man.display} / icons ${man.icons.length}`);
  const apple = await page.evaluate(() => ({ icon: document.querySelector('link[rel=apple-touch-icon]')?.getAttribute('href'), title: document.querySelector('meta[name=apple-mobile-web-app-title]')?.getAttribute('content') }));
  const iconRes = await page.evaluate(async (h) => (await fetch(h)).headers.get('content-type'), apple.icon);
  ok(dev, 'iPhone ホーム画面用アイコン（PNG）と名前', /png/.test(iconRes) && apple.title === '空気清浄度研究', `${apple.icon} ${iconRes} ${apple.title}`);
  await page.evaluate(() => navigator.serviceWorker.ready.then(() => true));
  await page.reload(); await page.waitForSelector('.stat-v');
  const sw = await page.evaluate(() => !!navigator.serviceWorker.controller);
  ok(dev, 'Service Worker が制御中', sw);

  // 3. 下部タブとその他メニュー
  ok(dev, '下部タブバー表示', await page.locator('.tabbar').isVisible());
  await page.locator('.tabbar a', { hasText: 'その他' }).tap();
  await page.waitForSelector('.sheet');
  await shot(page, dev, '02_more_menu');
  await page.locator('.sheet a', { hasText: '総合研究レポート' }).tap();
  await page.waitForSelector('.md h1');
  ok(dev, 'その他メニューからレポートへ', /\/report$/.test(page.url()));

  // 4. 資料・文献検索
  await page.goto(BASE + '/library'); await page.waitForSelector('.srclist li');
  await page.fill('input[type=search]', 'バイパス'); await page.waitForTimeout(300);
  const nSrc = await page.locator('.srclist li').count();
  ok(dev, '研究資料の検索（バイパス）', nSrc >= 1 && nSrc < 20, `${nSrc} 件`);
  await page.fill('input[type=search]', 'Indoor Air'); await page.waitForTimeout(300);
  const nLit = await page.locator('.litlist li').count();
  ok(dev, '国内外文献の検索（Indoor Air）', nLit >= 1, `${nLit} 件`);
  await shot(page, dev, '03_library');
  await page.fill('input[type=search]', ''); await page.waitForTimeout(200);
  await page.locator('.srclist li').first().tap(); await page.waitForSelector('.dtitle');
  await page.click('.statusbar button:has-text("読了")'); await page.waitForTimeout(300);
  await page.fill('.detail-pane textarea', 'スマホE2E メモ'); await page.click('text=メモを保存'); await page.waitForTimeout(300);
  await page.reload(); await page.waitForSelector('.detail-pane textarea');
  ok(dev, '資料メモの保存（再読み込み後も残る）', (await page.locator('.detail-pane textarea').inputValue()) === 'スマホE2E メモ');

  // 5. CSV・Excel 取込と解析
  const csv = path.join(TMP, 'sample.csv');
  fs.writeFileSync(csv, '日時,外気,室内\n' + Array.from({ length: 60 }, (_, i) => `2026-01-01T${String(Math.floor(i / 6)).padStart(2, '0')}:${String((i % 6) * 10).padStart(2, '0')}:00,${(10 + 3 * Math.sin(i / 5)).toFixed(2)},${(4 + Math.sin(i / 5)).toFixed(2)}`).join('\n'));
  await page.goto(BASE + '/data'); await page.waitForSelector('input[type=file]');
  await page.setInputFiles('input[type=file]', csv);
  await page.waitForSelector('text=異常値・欠損値の検出', { timeout: 15000 });
  ok(dev, 'CSV 取込と品質確認', /保存しました/.test(await page.locator('.page').first().innerText()));
  const xlsx = path.join(TMP, 'sample.xlsx');
  execFileSync(PY, ['-c', `import openpyxl; wb=openpyxl.Workbook(); ws=wb.active; ws.title='測定'; ws.append(['時刻','PM2.5']); [ws.append([i, 5+i%7]) for i in range(40)]; wb.save(${JSON.stringify(xlsx)})`]);
  await page.setInputFiles('input[type=file]', xlsx);
  await page.waitForSelector('text=保存しました（1 シート）', { timeout: 15000 }).catch(() => undefined);
  const dsCount = await page.evaluate(() => new Promise((r) => { const q = indexedDB.open('aqros', 1); q.onsuccess = () => { const t = q.result.transaction('kv').objectStore('kv').getAllKeys(); t.onsuccess = () => r(t.result.filter((k) => String(k).startsWith('dataset:')).length) } }));
  ok(dev, 'Excel 取込（端末内に保存）', dsCount >= 2, `データセット ${dsCount} 件`);
  await shot(page, dev, '04_data');

  // 6. シミュレーター（Python と同じモデル。数値一致は vitest の crosscheck で全ケース検証）
  await page.goto(BASE + '/simulator'); await page.waitForSelector('.stat-v');
  const cadr = await page.locator('.stat-v').first().innerText();
  ok(dev, 'シミュレーター計算', /\d/.test(cadr), cadr);
  await shot(page, dev, '05_simulator');

  // 7. 研究計画（IndexedDB に保存）
  await page.goto(BASE + '/plan'); await page.waitForSelector('table.rank');
  await page.locator('select', { hasText: 'テーマから新規作成' }).selectOption('T-01').catch(async () => page.selectOption('.card select >> nth=0', 'T-01'));
  await page.waitForSelector('#plan-edit');
  await page.fill('#plan-edit input', 'スマホE2E 研究計画');
  await page.click('#plan-edit button:has-text("保存")'); await page.waitForTimeout(500);
  await page.reload(); await page.waitForSelector('table.rank');
  ok(dev, '研究計画の保存（再読み込み後も残る）', /スマホE2E 研究計画/.test(await page.locator('.page').innerText()));
  await shot(page, dev, '06_plan');

  // 8. レポート編集・ダウンロード
  await page.goto(BASE + '/report'); await page.waitForSelector('.md h1');
  await page.locator('.sec button:has-text("編集")').first().tap();
  await page.fill('.editor textarea', '# スマホで編集した章\n\nE2E');
  await page.locator('.sec button:has-text("保存")').first().tap(); await page.waitForTimeout(400);
  await page.reload(); await page.waitForSelector('.md h1');
  ok(dev, 'レポート編集の保存', /スマホで編集した章/.test(await page.locator('.md').first().innerText()));
  const [dl] = await Promise.all([page.waitForEvent('download'), page.click('text=Markdown出力')]);
  ok(dev, 'ファイルとして保存（Markdown）', /\.md$/.test(dl.suggestedFilename()), dl.suggestedFilename());
  const nDeliv = await page.locator('ul.deliv a').count();
  ok(dev, '成果物のダウンロード一覧', nDeliv >= 5, `${nDeliv} 件`);
  await shot(page, dev, '07_report');

  // 9. 学習モード
  await page.goto(BASE + '/learn'); await page.waitForSelector('.learn');
  await page.locator('.learn input[type=checkbox]').nth(0).check(); await page.waitForTimeout(300);
  await page.reload(); await page.waitForSelector('.learn');
  ok(dev, '学習進捗の保存', await page.locator('.learn input[type=checkbox]').nth(0).isChecked());

  // 10. ナレッジグラフ
  await page.goto(BASE + '/graph'); await page.waitForSelector('svg .gnode');
  ok(dev, 'ナレッジグラフ表示', (await page.locator('svg .gnode').count()) > 10);

  // 11. オフライン起動
  await ctx.setOffline(true);
  await page.goto(BASE + '/plan').catch(() => undefined); await page.waitForSelector('table.rank', { timeout: 15000 }).catch(() => undefined);
  const offTxt = await page.locator('body').innerText().catch(() => '');
  ok(dev, 'オフラインで起動し端末内データを表示', /スマホE2E 研究計画/.test(offTxt) && /オフライン/.test(offTxt));
  await shot(page, dev, '08_offline');
  await ctx.setOffline(false);

  // 12. バックアップ → 全消去 → 復元
  await page.goto(BASE + '/settings'); await page.waitForSelector('text=バックアップを書き出す');
  const [bk] = await Promise.all([page.waitForEvent('download'), page.click('text=バックアップを書き出す（JSON）')]);
  const bkPath = path.join(TMP, `${dev}-backup.json`); await bk.saveAs(bkPath);
  const bkObj = JSON.parse(fs.readFileSync(bkPath, 'utf8'));
  ok(dev, 'バックアップ書き出し', bkObj.format === 'aqros-backup' && bkObj.entries.length > 5, `${bkObj.entries.length} 件`);
  await shot(page, dev, '09_settings');
  const ctx2 = await browser.newContext(  // 別の端末を想定（空の保存領域）
   { ...devices[devName], locale: 'ja-JP' }); const p2 = await ctx2.newPage();
  await p2.goto(BASE + '/settings'); await p2.waitForSelector('text=バックアップを書き出す');
  await p2.setInputFiles('input[aria-label="バックアップを追加で復元"]', bkPath);
  await p2.waitForTimeout(1500);
  await p2.goto(BASE + '/plan'); await p2.waitForSelector('table.rank');
  ok(dev, '別の環境へ復元（研究計画が戻る）', /スマホE2E 研究計画/.test(await p2.locator('.page').innerText()));
  await ctx2.close();

  // 13. クラウド解析（GitHub API 模擬・run_job.py は実行）
  const gh = await mockGitHub({ isPrivate: ghPrivate });
  await page.goto(BASE + '/settings'); await page.waitForSelector('text=クラウド解析の接続先');
  await page.evaluate(async (api) => {
    const open = () => new Promise((r) => { const q = indexedDB.open('aqros', 1); q.onsuccess = () => r(q.result) });
    const db = await open(); const t = db.transaction('kv', 'readwrite'); const s = t.objectStore('kv');
    s.put({ owner: 'lab', repo: 'aq-jobs', base_branch: 'main', api }, 'cloud:settings'); s.put('test-token', 'cloud:token');
    await new Promise((r) => (t.oncomplete = r));
  }, gh.url);
  await page.goto(BASE + '/cloud'); await page.waitForSelector('text=新しいジョブ');
  await page.waitForSelector(`text=${ghPrivate ? '非公開リポジトリ' : '公開リポジトリ'}`, { timeout: 10000 });
  // 13a パラメータ計算
  await page.click('button:has-text("解析開始")'); await page.waitForSelector('text=送信しました', { timeout: 20000 });
  await page.locator('button:has-text("結果を確認")').first().click(); await page.waitForSelector('text=完了', { timeout: 20000 });
  const [csvDl] = await Promise.all([page.waitForEvent('download'), page.locator('button:has-text("sweep.csv")').first().click()]);
  const csvTxt = fs.readFileSync(await csvDl.path(), 'utf8');
  ok(dev, 'クラウド: パラメータ計算（結果 CSV を受信）', csvTxt.split('\n').length > 50, `${csvTxt.split('\n').length} 行`);
  await shot(page, dev, '10_cloud');
  // 13b 研究データの詳細解析（取り込んだ CSV は研究データ扱い）
  await page.selectOption('select[aria-label="ジョブ種別"]', 'analysis');
  await page.locator('.checklist label', { hasText: 'sample' }).first().locator('input').check();
  await page.click('button:has-text("解析開始")'); await page.waitForTimeout(800);
  const msg1 = await page.locator('[role=status]').last().innerText();
  if (!ghPrivate) {
    ok(dev, 'クラウド: 公開リポジトリには研究データを送らない', /公開リポジトリ/.test(msg1) && Object.keys(gh.refs).length === 1, msg1);
  } else {
    ok(dev, 'クラウド: 同意なしでは研究データを送らない', /同意/.test(msg1) && Object.keys(gh.refs).length === 1, msg1);
    await page.locator('.consent input').check();
    await page.click('button:has-text("解析開始")'); await page.waitForSelector('text=送信しました', { timeout: 20000 });
    await page.locator('button:has-text("結果を確認")').first().click(); await page.waitForSelector('button:has-text("analysis.xlsx")', { timeout: 20000 });
    const br = Object.keys(gh.files).find((k) => gh.files[k]['__inbox_inputs_left'] === false);
    ok(dev, 'クラウド: 同意ありで Python 解析（Excel 結果を受信、入力は削除）', !!br);
    await page.locator('button:has-text("クラウド側を削除")').first().click(); await page.waitForTimeout(500);
    ok(dev, 'クラウド: 受信後にジョブ用ブランチを削除', Object.keys(gh.refs).length === 1);
  }
  gh.server.close();

  ok(dev, 'ページエラーなし', errors.length === 0, errors.slice(0, 3).join(' | '));
  await browser.close();
}

(async () => {
  await run('iphone', 'iPhone 13', true);
  await run('android', 'Pixel 7', false);
  const pass = results.filter((r) => r.pass).length;
  fs.writeFileSync(path.join(SHOTS, 'mobile_results.json'), JSON.stringify({ base: BASE, engine: 'chromium (device emulation)', pass, total: results.length, results }, null, 1));
  console.log(`${pass}/${results.length} passed`);
  process.exit(pass === results.length ? 0 : 1);
})().catch((e) => { console.error(e); process.exit(1); });
