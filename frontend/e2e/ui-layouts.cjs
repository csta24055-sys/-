// 5種類の UI レイアウト（Original / Research / Public / Commercial / Enterprise）の自動テスト — Playwright（Chromium）
//
//   node e2e/ui-layouts.cjs        # 既定: http://127.0.0.1:47801/（dist-mobile を静的配信しておく。e2e/mobile.cjs と同じ）
//
// 確認すること:
//  1. 各レイアウト × PC / iPhone 13 / Pixel 7 で、全10機能に画面上のメニューから到達できる（URL が正しく変わる）
//  2. 各レイアウトでホーム・主要機能（シミュレーター）・結果（レポート）・設定が表示され、ページエラー・横スクロールがない
//  3. 計算結果（シミュレーターの数値）が全レイアウトで完全に同じ
//  4. スマホで下部ナビが本文を隠さない／上部ヘッダーが本文に重ならない／極端に小さい文字がない
//  5. 設定「デザイン」: プレビュー → 取り消し → 適用 → 再読み込みで維持 → 元に戻す → Original に戻す
//     切替中も入力中の内容が残る／URL が変わらない／端末内の研究データ（IndexedDB）が1バイトも変わらない
//  6. 詳細カスタマイズ（色・サイドバー位置・密度・文字サイズ）が反映・保存・初期化できる
//  7. Ctrl+K のコマンドパレット、壊れた保存値からの復旧
//  8. アクセシビリティ（axe-core）: 重大（serious / critical）の違反数を Original と比較
// 注意: iPhone は Chromium での「iPhone 13 相当（画面サイズ・UA・タッチ）」の再現であり、実機の Safari ではない。
const pw = require('playwright');
const { devices } = pw;
// BROWSER=webkit で Safari と同じ系統のエンジン（Playwright の WebKit）を使う。既定は Chromium
const ENGINE = process.env.BROWSER === 'webkit' ? 'webkit' : 'chromium';
const chromium = pw[ENGINE];
const fs = require('fs');
const path = require('path');

const BASE = (process.env.BASE || 'http://127.0.0.1:47801').replace(/\/$/, '');
const ROOT = path.resolve(__dirname, '../..');
const SHOTS = process.env.SHOTS || path.join(ROOT, 'docs/screenshots/ui-layouts');
const AXE = fs.readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');
fs.mkdirSync(SHOTS, { recursive: true });

const LAYOUTS = ['original', 'research', 'public', 'commercial', 'enterprise'];
const ROUTES = ['/', '/library', '/data', '/simulator', '/graph', '/plan', '/report', '/learn', '/cloud', '/settings'];
const DEVICES = {
  desktop: { viewport: { width: 1440, height: 900 } },
  iphone: { ...devices['iPhone 13'] },
  android: { ...devices['Pixel 7'] },
};
const KEY = 'aqros-ui-prefs-v1';
const results = [];
const ok = (scope, name, cond, extra = '') => { results.push({ scope, name, pass: !!cond, extra: String(extra).slice(0, 400) }); console.log(cond ? 'PASS' : 'FAIL', `[${scope}]`, name, extra ? '— ' + String(extra).slice(0, 200) : ''); };
const prefs = (layout, custom = {}) => JSON.stringify({ version: 1, applied: { layout, custom }, history: [], updatedAt: null });

async function newPage(browser, dev, layout) {
  const ctx = await browser.newContext({ ...DEVICES[dev], ...(dev === 'desktop' ? {} : {}), acceptDownloads: true });
  if (layout) await ctx.addInitScript(([k, v]) => { if (!sessionStorage.getItem('__seeded')) { localStorage.setItem(k, v); sessionStorage.setItem('__seeded', '1') } }, [KEY, prefs(layout)]);
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  return { ctx, page, errors };
}
const shot = async (page, name) => page.screenshot({ path: path.join(SHOTS, `${name}.jpg`), type: 'jpeg', quality: 72 });
const pathname = (page) => new URL(page.url()).pathname;
const ready = async (page) => { await page.waitForSelector('main h1', { timeout: 20000 }); await page.waitForTimeout(250); };

/** 画面上のメニューだけを使って route へ移動する（URL 直打ちはしない） */
async function reach(page, route) {
  try { return await reachInner(page, route) } catch (e) { console.log('  reach error', route, String(e.message).split('\n')[0]); return false }
}
async function reachInner(page, route) {
  const direct = page.locator(`header a[href="${route}"]:visible, aside a[href="${route}"]:visible, nav a[href="${route}"]:visible`).first();
  if (await direct.count()) { await direct.click(); }
  else {
    const opener = page.locator('.tabbar a[href="#more"]:visible, .ux-bottom button:visible, .ux-menu-btn:visible, .ux-allbtn:visible').first();
    if (!(await opener.count())) return false;
    await opener.click();
    const link = page.locator(`.sheet a[href="${route}"]:visible, .ux-sheet a[href="${route}"]:visible`).first();
    if (!(await link.count())) return false;
    await link.click();
  }
  await page.waitForFunction((r) => location.pathname === r, route, { timeout: 5000 }).catch(() => undefined);
  return pathname(page) === route;
}

/** 端末内の研究データ（IndexedDB "aqros"）の全内容を文字列にする */
const dbDump = (page) => page.evaluate(() => new Promise((resolve) => {
  const r = indexedDB.open('aqros');
  r.onsuccess = () => {
    const db = r.result; if (!db.objectStoreNames.contains('kv')) return resolve('');
    const out = []; const t = db.transaction('kv', 'readonly'); const c = t.objectStore('kv').openCursor();
    c.onsuccess = () => { const cur = c.result; if (cur) { out.push([String(cur.key), JSON.stringify(cur.value, (k, v) => (v instanceof Uint8Array ? Array.from(v) : v))]); cur.continue(); } };
    t.oncomplete = () => resolve(JSON.stringify(out.sort()));
  };
  r.onerror = () => resolve('ERR');
}));

async function axe(page) {
  await page.addScriptTag({ content: AXE });
  return page.evaluate(async () => {
    const r = await window.axe.run(document, { resultTypes: ['violations'] });
    return r.violations.filter((v) => ['serious', 'critical'].includes(v.impact)).map((v) => ({ id: v.id, impact: v.impact, n: v.nodes.length, sample: v.nodes[0]?.target?.join(' ') }));
  });
}

async function matrix(browser) {
  const calc = {};
  const a11y = {};
  for (const dev of Object.keys(DEVICES)) {
    for (const L of LAYOUTS) {
      const scope = `${L}/${dev}`;
      const { ctx, page, errors } = await newPage(browser, dev, L);
      await page.goto(BASE + '/'); await ready(page);
      ok(scope, 'レイアウトが適用されている', (await page.getAttribute('html', 'data-ui')) === L, await page.getAttribute('html', 'data-ui'));
      const vw = await page.evaluate(() => ({ w: innerWidth, sw: document.documentElement.scrollWidth }));
      ok(scope, 'ホーム: 横スクロールなし', vw.sw <= vw.w + 1, JSON.stringify(vw));
      if (dev !== 'android') await shot(page, `${L}_${dev}_1-home`);

      // 1. 全機能への到達（メニュー操作だけで）
      const miss = [];
      for (const r of ROUTES.slice(1).concat(['/'])) { if (!(await reach(page, r))) miss.push(r); else await ready(page); }
      ok(scope, '全10機能に画面のメニューから到達できる', miss.length === 0, miss.length ? '到達不可: ' + miss.join(' ') : '10/10');

      // 2〜4. 主要機能・結果・設定
      await page.goto(BASE + '/simulator'); await page.waitForSelector('.stat-v'); await page.waitForTimeout(400);
      const vals = (await page.locator('main .stat-v').allInnerTexts()).join(' | ');
      calc[scope] = vals;
      ok(scope, 'シミュレーター（主要機能）の計算結果を表示', /\d/.test(vals), vals.slice(0, 120));
      if (dev !== 'android') await shot(page, `${L}_${dev}_2-simulator`);
      await page.goto(BASE + '/report'); await page.waitForSelector('.md h1');
      ok(scope, '総合研究レポート（結果表示）', (await page.locator('.md h1').count()) > 3);
      if (dev !== 'android') await shot(page, `${L}_${dev}_3-report`);
      await page.goto(BASE + '/settings'); await page.waitForSelector('#design');
      ok(scope, '設定に「デザイン」と5種類のカード', (await page.locator('#design [role=radio][data-layout]').count()) === 5);
      if (dev !== 'android') await shot(page, `${L}_${dev}_4-settings`);

      if (dev !== 'desktop') {
        // 下部ナビが本文を隠さない（最下部までスクロールしたとき、本文の最後がナビより上にある）
        await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight)); await page.waitForTimeout(200);
        const cover = await page.evaluate(() => {
          const nav = document.querySelector('.tabbar, .ux-bottom'); const page = document.querySelector('main .page');
          if (!nav || !page) return { ok: false, why: 'nav/page なし' };
          const last = page.lastElementChild.getBoundingClientRect(); const n = nav.getBoundingClientRect();
          return { ok: last.bottom <= n.top + 1, last: Math.round(last.bottom), navTop: Math.round(n.top) };
        });
        ok(scope, 'スマホ: 下部ナビが本文の最後を隠さない', cover.ok, JSON.stringify(cover));
        await page.goto(BASE + '/'); await ready(page);
        const top = await page.evaluate(() => {
          const h = document.querySelector('.ux-top'); const h1 = document.querySelector('main h1, main h2');
          if (!h) return { ok: true, why: 'ヘッダーなし（Original）' };
          const hb = h.getBoundingClientRect(); const b = h1.getBoundingClientRect();
          const css = [...document.styleSheets].flatMap((s) => { try { return [...s.cssRules].map((r) => r.cssText) } catch { return [] } }).join('\n');
          return { ok: hb.top >= 0 && b.top >= hb.bottom - 1 && /safe-area-inset-top/.test(css), headerBottom: Math.round(hb.bottom), firstHeading: Math.round(b.top) };
        });
        ok(scope, 'スマホ: 上部ヘッダーが本文に重ならず、ステータスバーの安全領域を確保', top.ok, JSON.stringify(top));
        const minFs = await page.evaluate(() => {
          let m = 99; const walk = document.createTreeWalker(document.querySelector('.shell'), NodeFilter.SHOW_TEXT);
          while (walk.nextNode()) { const n = walk.currentNode; if (!n.textContent.trim()) continue; const el = n.parentElement; const r = el.getBoundingClientRect(); if (!r.width || !r.height || el.closest('.ux-sr,.recharts-wrapper,svg,.ux-mini')) continue; m = Math.min(m, parseFloat(getComputedStyle(el).fontSize)); }
          return m;
        });
        // Original は改修前の値をそのまま記録する（下部タブの文字 .7rem = 9.8px は改修前からの値で、Original では変更しない）
        if (L === 'original') ok(scope, 'スマホ: 最小の文字サイズ（Original は改修前のまま・記録のみ）', true, `最小 ${minFs}px`);
        else ok(scope, 'スマホ: 極端に小さい文字がない（最小 10px 以上）', minFs >= 10, `最小 ${minFs}px`);
      }
      if (dev === 'desktop') {
        await page.goto(BASE + '/'); await ready(page);
        a11y[L] = { home: await axe(page) };
        await page.goto(BASE + '/settings'); await page.waitForSelector('#design');
        a11y[L].settings = await axe(page);
      }
      ok(scope, 'ページエラーなし', errors.length === 0, errors.join(' / '));
      await ctx.close();
    }
  }
  const ref = calc['original/desktop'];
  const diff = Object.entries(calc).filter(([, v]) => v !== ref).map(([k]) => k);
  ok('all', '計算結果が全レイアウト・全端末で完全一致（計算エンジン共通）', diff.length === 0 && !!ref, diff.length ? '不一致: ' + diff.join(' ') : ref.slice(0, 160));
  // アクセシビリティ: 追加レイアウトが Original より重大な違反を増やしていないこと
  const count = (L) => [...a11y[L].home, ...a11y[L].settings].reduce((s, v) => s + v.n, 0);
  const base = count('original');
  for (const L of LAYOUTS) {
    const ids = [...new Set([...a11y[L].home, ...a11y[L].settings].map((v) => `${v.id}(${v.impact})`))].join(', ');
    ok(`${L}/desktop`, 'axe: 重大な違反が Original 以下', count(L) <= base, `重大な違反 ${count(L)} 件（Original ${base} 件）${ids ? ' — ' + ids : ''}`);
  }
  return { a11y };
}

async function switchingFlow(browser, dev) {
  const scope = `切替/${dev}`;
  const { ctx, page, errors } = await newPage(browser, dev, null);
  await page.goto(BASE + '/'); await ready(page);
  ok(scope, '初回は Original', (await page.getAttribute('html', 'data-ui')) === 'original' && (await page.locator('.shell:not(.ux-shell)').count()) === 1);
  // 研究データを作る（資料メモと研究計画）
  await page.goto(BASE + '/library'); await page.waitForSelector('.srclist li');
  await page.locator('.srclist li').first().click(); await page.waitForSelector('.detail-pane textarea');
  await page.fill('.detail-pane textarea', 'UI切替テスト メモ'); await page.click('text=メモを保存'); await page.waitForTimeout(400);
  await page.goto(BASE + '/settings'); await page.waitForSelector('#design');
  const before = await dbDump(page);
  ok(scope, '研究データ（IndexedDB）を作成', before.length > 50 && before.includes('UI切替テスト'), `${before.length} 文字`);

  // 入力中の内容（未保存）
  const owner = page.locator('input[placeholder="例: csta24055-sys"]');
  await owner.fill('typing-in-progress');
  const url0 = page.url();

  // プレビュー → 画面全体が切り替わるが、入力・URL は保たれる
  await page.click('#design [data-layout="research"]');
  await page.waitForSelector('.ux-research');
  ok(scope, 'カードを押すと画面全体が Research の構成に切り替わる（プレビュー）', (await page.locator('.ux-research .ux-top').count()) === 1 && (await page.getAttribute('html', 'data-ui')) === 'research');
  ok(scope, 'プレビュー帯（適用・取り消す）が出る', await page.locator('.ux-previewbar').isVisible());
  ok(scope, '切替後も入力中の内容が残る（ページを作り直さない）', (await owner.inputValue()) === 'typing-in-progress');
  ok(scope, '切替で URL が変わらない', page.url() === url0, page.url());
  ok(scope, 'プレビューは保存しない', (await page.evaluate((k) => localStorage.getItem(k), KEY)) === null);
  for (const L of ['public', 'commercial', 'enterprise']) {
    await page.click(`#design [data-layout="${L}"]`); await page.waitForSelector(`.ux-${L}`);
  }
  ok(scope, '4種類を続けて切り替えても入力が残る', (await owner.inputValue()) === 'typing-in-progress');
  // プレビュー中に別の画面へ移動しても、帯から適用・取り消しができる
  await page.goto(BASE + '/settings').catch(() => undefined); // 再読み込み相当（プレビューは破棄される）
  await page.waitForSelector('#design');
  ok(scope, '再読み込みするとプレビューは破棄され、保存済み（Original）に戻る', (await page.getAttribute('html', 'data-ui')) === 'original');
  await page.click('#design [data-layout="enterprise"]'); await page.waitForSelector('.ux-enterprise');
  if (!(await reach(page, '/simulator'))) ok(scope, 'プレビュー中の移動', false);
  await page.waitForSelector('.stat-v');
  ok(scope, 'プレビュー中に別画面へ移動してもプレビューが続く', (await page.getAttribute('html', 'data-ui')) === 'enterprise' && await page.locator('.ux-previewbar').isVisible());
  await page.click('.ux-previewbar button:has-text("取り消す")');
  ok(scope, '取り消すで Original に戻る（同じ画面のまま）', (await page.getAttribute('html', 'data-ui')) === 'original' && pathname(page) === '/simulator');

  // 適用 → 再読み込みで維持
  await page.goto(BASE + '/settings'); await page.waitForSelector('#design');
  await page.click('#design [data-layout="commercial"]'); await page.waitForSelector('.ux-commercial');
  await page.click('#design .ux-design-actions button:text-is("適用")');
  await page.waitForTimeout(200);
  ok(scope, '適用で保存（localStorage の専用キー）', JSON.parse(await page.evaluate((k) => localStorage.getItem(k), KEY)).applied.layout === 'commercial');
  await page.reload(); await page.waitForSelector('#design');
  ok(scope, '再読み込みしても Commercial を維持', (await page.getAttribute('html', 'data-ui')) === 'commercial' && (await page.locator('.ux-commercial').count()) === 1);
  // 元に戻す
  await page.click('#design button:has-text("元に戻す")'); await page.waitForTimeout(200);
  ok(scope, '元に戻すで直前の設定（Original）に戻る', (await page.getAttribute('html', 'data-ui')) === 'original');
  // ワンタップで Original に戻す
  await page.click('#design [data-layout="public"]'); await page.click('#design .ux-design-actions button:text-is("適用")'); await page.waitForSelector('.ux-public');
  await page.click('#design button:has-text("Original に戻す")'); await page.waitForTimeout(200);
  await page.reload(); await page.waitForSelector('#design');
  ok(scope, 'Original に戻す（1回押すだけ・再読み込み後も Original）', (await page.getAttribute('html', 'data-ui')) === 'original' && (await page.locator('.shell:not(.ux-shell)').count()) === 1);

  const after = await dbDump(page);
  ok(scope, '切替・適用・取り消しで研究データ（IndexedDB）が一切変わらない', after === before, `${before.length} → ${after.length} 文字`);
  await page.goto(BASE + '/library'); await page.waitForSelector('.srclist li'); await page.locator('.srclist li').first().click(); await page.waitForSelector('.detail-pane textarea');
  ok(scope, '保存済みのメモがそのまま読める', (await page.locator('.detail-pane textarea').inputValue()) === 'UI切替テスト メモ');
  ok(scope, 'ページエラーなし', errors.length === 0, errors.join(' / '));
  await ctx.close();
}

async function customizeFlow(browser) {
  const scope = 'カスタマイズ/desktop';
  const { ctx, page, errors } = await newPage(browser, 'desktop', 'research');
  await page.goto(BASE + '/settings'); await page.waitForSelector('#design');
  await page.click('.ux-custom summary');
  const seg = (label, text) => page.locator(`.ux-field:has(.ux-field-l:text-is("${label}")) button:text-is("${text}")`).click();
  await seg('サイドバーの位置', '右'); await seg('情報密度', 'ゆったり'); await seg('文字の大きさ', '大'); await seg('カード', '影');
  await page.click('.ux-sw[aria-label="主色 #5b3fa0"]');
  const st = await page.evaluate(() => {
    const side = document.querySelector('.ux-side').getBoundingClientRect(); const main = document.querySelector('main').getBoundingClientRect();
    const h = document.documentElement;
    return { right: side.left > main.left, density: h.dataset.density, card: h.dataset.card, accent: getComputedStyle(h).getPropertyValue('--accent').trim(), fs: getComputedStyle(h).fontSize };
  });
  ok(scope, 'サイドバーが右に移る・密度・カード・主色・文字サイズがすぐ反映（プレビュー）', st.right && st.density === 'comfortable' && st.card === 'shadow' && st.accent === '#5b3fa0' && parseFloat(st.fs) > 13, JSON.stringify(st));
  await page.click('#design .ux-design-actions button:text-is("適用")'); await page.reload(); await page.waitForSelector('#design');
  const st2 = await page.evaluate(() => ({ density: document.documentElement.dataset.density, accent: getComputedStyle(document.documentElement).getPropertyValue('--accent').trim() }));
  ok(scope, 'カスタマイズが再読み込み後も残る', st2.density === 'comfortable' && st2.accent === '#5b3fa0', JSON.stringify(st2));
  await page.click('.ux-custom summary').catch(() => undefined);
  if (!(await page.locator('.ux-custom[open]').count())) await page.click('.ux-custom summary');
  await seg('サイドバーの表示', '隠す');
  ok(scope, 'サイドバーを隠しても ☰ から全機能を開ける', (await page.locator('.ux-side').count()) === 0 && await page.locator('.ux-menu-btn').isVisible());
  await page.click('.ux-custom button:has-text("カスタマイズを初期値に戻す")'); await page.click('#design .ux-design-actions button:text-is("適用")');
  ok(scope, 'カスタマイズを初期値に戻せる', (await page.getAttribute('html', 'data-density')) === 'compact' && (await page.locator('.ux-side').count()) === 1);
  // 暗い/明るすぎる主色はコントラスト警告
  await page.locator('.ux-sw-custom input[type=color]').fill('#ffee58');
  ok(scope, '読みにくい主色にはコントラスト警告を出す', await page.locator('.ux-custom [role=alert]').isVisible());
  await page.click('#design .ux-design-actions button:text-is("取り消す")');
  // Original にカスタマイズ（サイドバー右）を付けても全機能に届く
  await page.click('#design [data-layout="original"]'); await page.click('.ux-custom summary').catch(() => undefined);
  if (!(await page.locator('.ux-custom[open]').count())) await page.click('.ux-custom summary');
  await seg('サイドバーの表示', '隠す');
  ok(scope, 'Original でサイドバーを隠すと下部メニューが出る', await page.locator('.tabbar').isVisible());
  await page.click('#design .ux-design-actions button:text-is("取り消す")');
  // Ctrl+K
  await page.goto(BASE + '/'); await ready(page);
  await page.keyboard.press('Control+k'); await page.waitForSelector('.ux-palette');
  await page.keyboard.type('レポート'); await page.keyboard.press('Enter');
  await page.waitForFunction(() => location.pathname === '/report');
  ok(scope, 'Ctrl+K のコマンドパレットで機能へ移動', pathname(page) === '/report');
  ok(scope, 'ページエラーなし', errors.length === 0, errors.join(' / '));
  await ctx.close();

  // 壊れた保存値
  const c2 = await browser.newContext(DEVICES.desktop);
  await c2.addInitScript((k) => localStorage.setItem(k, '{"version":1,"applied":{"layout":"deleted-layout","custom":{"accent":"javascript:x"}}}'), KEY);
  const p2 = await c2.newPage(); const e2 = []; p2.on('pageerror', (e) => e2.push(e.message));
  await p2.goto(BASE + '/'); await ready(p2);
  ok('復旧/desktop', '壊れた・未知の保存値でも Original で起動する', (await p2.getAttribute('html', 'data-ui')) === 'original' && e2.length === 0, e2.join(' / '));
  await c2.close();
}

(async () => {
  const browser = await chromium.launch();
  const t0 = Date.now();
  const { a11y } = await matrix(browser);
  await switchingFlow(browser, 'desktop');
  await switchingFlow(browser, 'iphone');
  await customizeFlow(browser);
  await browser.close();
  const pass = results.filter((r) => r.pass).length;
  fs.writeFileSync(path.join(SHOTS, 'results.json'), JSON.stringify({ base: BASE, engine: ENGINE, at: new Date().toISOString(), seconds: Math.round((Date.now() - t0) / 1000), pass, total: results.length, results, a11y }, null, 1));
  console.log(`\n${pass}/${results.length} passed`);
  process.exit(pass === results.length ? 0 : 1);
})().catch((e) => { console.error(e); process.exit(2); });
