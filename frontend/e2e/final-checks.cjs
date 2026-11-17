// 公開前の最終点検（5 種類のレイアウト共通）。e2e/ui-layouts.cjs が通していない条件を測る。
//   node e2e/final-checks.cjs                          # 既定: http://127.0.0.1:47801/（dist-mobile を静的配信しておく）
//   WORKER=dist-cf/_worker.js node e2e/final-checks.cjs  # Cloudflare 用のエッジスクリプトの経路も確かめる
//
// 測るもの:
//   1. ライト・ダーク配色（端末のダークモード／配色=ダーク）で、ボタンと進捗バーの文字のコントラスト比（4.5:1 以上。Original を含む）
//   2. 幅 721〜1000px（iPad 縦・iPhone 横）で、ヘッダーの中身がヘッダーからはみ出さないこと・横スクロールがないこと
//   3. 初回の直接アクセス（Service Worker なし）で、全画面の URL が開くこと（/data と末尾 / 付きを含む）
//   4. スマホで押せる部品の高さ（☰ 44px 以上、ボタン 40px 以上）、コマンドパレットの入力欄 16px 以上
//   5. Public のホームで 3 つの層のラベルが見えること、プレビュー帯が画面の上端に止まること
//   6. color-mix() のないブラウザーを想定した代替（進捗バーの塗り・フラットのカードが透明にならない）
//   7. 幅 320px・横向き（844×390）・文字特大での崩れ（Original のサイドバー設定、目次の移動先、Public の層ラベル・識別帯・進捗バー）
// BROWSER=webkit を付けると Playwright の WebKit（Safari と同じ系統のエンジン）で測る（.github/workflows/ui-webkit.yml が macOS で実行）。
// どちらも端末のエミュレーションで、iPhone / iPad の実機の Safari そのものの確認ではない。
const pw = require('playwright');
const { devices } = pw;
// BROWSER=webkit で Safari と同じ系統のエンジン（Playwright の WebKit）を使う。既定は Chromium
const ENGINE = process.env.BROWSER === 'webkit' ? 'webkit' : 'chromium';
const chromium = pw[ENGINE];
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');

const BASE = (process.env.BASE || 'http://127.0.0.1:47801').replace(/\/$/, '');
const OUT = process.env.OUT || '';
const KEY = 'aqros-ui-prefs-v1';
const LAYOUTS = ['original', 'research', 'public', 'commercial', 'enterprise'];
const NEW = LAYOUTS.slice(1);
const ROUTES = ['/', '/library', '/data', '/simulator', '/graph', '/plan', '/report', '/learn', '/cloud', '/settings'];
const IPHONE = { ...devices['iPhone 13'] };
const results = [];
const ok = (scope, name, cond, extra = '') => { results.push({ scope, name, pass: !!cond, extra: String(extra).slice(0, 600) }); console.log(cond ? 'PASS' : 'FAIL', `[${scope}]`, name, extra ? '— ' + String(extra).slice(0, 300) : ''); };
const prefs = (layout, custom = {}) => JSON.stringify({ version: 1, applied: { layout, custom }, history: [], updatedAt: null });

async function ctxFor(browser, opts, layout, custom = {}) {
  const ctx = await browser.newContext(opts);
  await ctx.addInitScript(([k, v]) => { if (!sessionStorage.getItem('__seeded')) { localStorage.setItem(k, v); sessionStorage.setItem('__seeded', '1'); } }, [KEY, prefs(layout, custom)]);
  return ctx;
}
const ready = async (page) => { await page.waitForSelector('main h1', { timeout: 20000 }); await page.waitForTimeout(300); };
async function go(page, route) {
  await page.evaluate((r) => { history.pushState({}, '', r); window.dispatchEvent(new PopStateEvent('popstate')); }, route);
  await page.waitForFunction((r) => location.pathname === r, route);
  await ready(page);
}

/** 見えているボタンのうち、文字と実効背景のコントラスト比が limit 未満のもの */
const LOW_CONTRAST = (limit) => {
  const parse = (c) => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null; const p = m[1].split(/[ ,/]+/).map(Number); return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 }; };
  const lum = ({ r, g, b }) => { const f = (x) => { x /= 255; return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
  const bgOf = (e) => { const stack = []; for (let n = e; n; n = n.parentElement) { const c = parse(getComputedStyle(n).backgroundColor); if (c && c.a > 0) { stack.push(c); if (c.a >= 1) break; } } let base = { r: 255, g: 255, b: 255 }; for (const c of stack.reverse()) base = { r: c.r * c.a + base.r * (1 - c.a), g: c.g * c.a + base.g * (1 - c.a), b: c.b * c.a + base.b * (1 - c.a) }; return base; };
  const vis = (e) => { const b = e.getBoundingClientRect(); const s = getComputedStyle(e); return b.width > 0 && b.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; };
  const out = [];
  for (const e of document.querySelectorAll('button, a.ux-btn-primary, .ux-pill, .ux-stage-no')) {
    if (!vis(e) || e.disabled || !(e.innerText || '').trim()) continue;
    const fg = parse(getComputedStyle(e).color), bg = bgOf(e);
    const a = lum(fg), b = lum(bg); const ratio = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
    if (ratio < limit) out.push(`${Math.round(ratio * 100) / 100} ${e.tagName.toLowerCase()}.${String(e.className).trim().split(/\s+/).join('.')} in .${String(e.parentElement.className).split(/\s+/)[0]} "${(e.innerText || '').trim().slice(0, 10)}"`);
  }
  // 進捗バーの中の文字は、塗り（兄弟要素）の上と、塗りの外（バーの地）の上の両方で読めること
  for (const bar of document.querySelectorAll('.bar')) {
    const span = bar.querySelector('span'), fill = bar.querySelector('div'); if (!span || !fill || !vis(bar)) continue;
    const fg = parse(getComputedStyle(span).color);
    const f0 = parse(getComputedStyle(fill).backgroundColor), track = bgOf(bar);
    const op = parseFloat(getComputedStyle(fill).opacity); const a0 = (f0 ? f0.a : 0) * (isNaN(op) ? 1 : op);
    const onFill = f0 ? { r: f0.r * a0 + track.r * (1 - a0), g: f0.g * a0 + track.g * (1 - a0), b: f0.b * a0 + track.b * (1 - a0) } : track;
    for (const [where, bg] of [['塗り', onFill], ['地', track]]) {
      const a = lum(fg), b = lum(bg); const ratio = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
      if (ratio < limit) out.push(`${Math.round(ratio * 100) / 100} 進捗バーの文字（${where}の上）`);
    }
  }
  return out;
};

async function darkContrast(browser) {
  for (const [devName, dev] of [['iphone', IPHONE], ['desktop', { viewport: { width: 1440, height: 900 } }]]) {
    for (const [mode, opts, custom] of [['ライト', { colorScheme: 'light' }, {}], ['端末ダーク', { colorScheme: 'dark' }, {}], ['配色=ダーク', { colorScheme: 'light' }, { theme: 'dark' }]]) {
      for (const layout of LAYOUTS) {
        const ctx = await ctxFor(browser, { ...dev, ...opts }, layout, custom);
        const page = await ctx.newPage();
        await page.goto(BASE + '/'); await ready(page);
        const bad = new Set();
        for (const r of ['/', '/library', '/data', '/simulator', '/settings']) {
          await go(page, r);
          if (r === '/settings') { await page.locator('details.ux-custom summary').click().catch(() => undefined); await page.waitForTimeout(120); }
          for (const x of await page.evaluate(LOW_CONTRAST, 4.5)) bad.add(x);
        }
        ok(`コントラスト/${devName}/${mode}`, `${layout}: ボタンと進捗バーの文字が 4.5:1 以上`, bad.size === 0, [...bad].slice(0, 6).join(' | '));
        if (OUT && devName === 'iphone' && mode === '端末ダーク') { await go(page, '/'); await page.screenshot({ path: path.join(OUT, `dark_${layout}_home.png`) }); }
        await ctx.close();
      }
    }
  }
}

async function midWidth(browser) {
  for (const layout of NEW) {
    const bad = [];
    for (const w of [721, 744, 768, 820, 834, 852, 900, 1000]) {
      for (const sidebarMode of ['auto', 'icons']) {
        const ctx = await ctxFor(browser, { viewport: { width: w, height: 1000 } }, layout, sidebarMode === 'auto' ? {} : { sidebarMode });
        const page = await ctx.newPage();
        await page.goto(BASE + '/simulator'); await ready(page);
        const r = await page.evaluate(() => {
          const top = document.querySelector('.ux-shell > .ux-top'); if (!top) return { out: [], scroll: 0 };
          const pick = getComputedStyle(top).position === 'sticky' || getComputedStyle(top).position === 'fixed' ? top : (top.querySelector('.ux-head') || top);
          const hb = pick.getBoundingClientRect(); const out = [];
          for (const e of pick.querySelectorAll('a, button, b, span, .ux-scope, .ux-role')) {
            const b = e.getBoundingClientRect(); if (!b.width || !b.height) continue;
            if (b.top < hb.top - 1 || b.bottom > hb.bottom + 1 || b.right > hb.right + 1) out.push(`${e.tagName.toLowerCase()}.${String(e.className).split(/\s+/)[0]} y=${Math.round(b.top)}..${Math.round(b.bottom)} (header ${Math.round(hb.top)}..${Math.round(hb.bottom)})`);
          }
          return { out, scroll: document.documentElement.scrollWidth - window.innerWidth };
        });
        if (r.out.length || r.scroll > 1) bad.push(`${w}px/${sidebarMode}: ${r.out.slice(0, 2).join(', ')}${r.scroll > 1 ? ' 横スクロール ' + r.scroll : ''}`);
        if (OUT && w === 820 && sidebarMode === 'auto') await page.screenshot({ path: path.join(OUT, `mid820_${layout}.png`) });
        await ctx.close();
      }
    }
    ok('中間幅 721〜1000px', `${layout}: ヘッダーの中身がはみ出さない・横スクロールなし`, bad.length === 0, bad.slice(0, 4).join(' | '));
  }
}

async function directAccess(browser) {
  // Service Worker を止めた新しい利用者として、各画面の URL を直接開く
  for (const layout of ['original', 'public']) {
    const bad = [];
    for (const r of [...ROUTES, '/data/', '/settings/', '/library/S-2026-01']) {
      const ctx = await ctxFor(browser, { ...IPHONE, serviceWorkers: 'block' }, layout);
      const page = await ctx.newPage();
      try {
        await page.goto(BASE + r); await page.waitForSelector('main h1', { timeout: 8000 });
        const want = r.replace(/\/$/, '') || '/';
        const got = (await page.evaluate(() => location.pathname)).replace(/\/$/, '') || '/';
        if (got !== want) bad.push(`${r} → ${got}`);
        if (r.startsWith('/data') && !(await page.locator('input[type=file]').count())) bad.push(`${r}: データ解析の画面にならない`);
      } catch (e) { bad.push(`${r}: ${String(e.message).split('\n')[0]}`); }
      await ctx.close();
    }
    ok('直接アクセス（初回・SWなし）', `${layout}: 全画面の URL が開く（/data と末尾 / を含む）`, bad.length === 0, bad.join(' | '));
  }
}

async function touchTargets(browser) {
  for (const layout of NEW) {
    const ctx = await ctxFor(browser, IPHONE, layout);
    const page = await ctx.newPage();
    await page.goto(BASE + '/'); await ready(page);
    const low = new Set(); let menu = null;
    for (const r of ROUTES) {
      await go(page, r);
      const m = await page.evaluate(() => {
        const vis = (e) => { const b = e.getBoundingClientRect(); const s = getComputedStyle(e); return b.width > 0 && b.height > 0 && s.visibility !== 'hidden'; };
        const out = [];
        for (const e of document.querySelectorAll('main button, main select, main input:not([type=checkbox]):not([type=radio]):not([type=range]):not([type=color]):not([type=file])')) {
          if (!vis(e) || e.closest('.recharts-wrapper') || e.classList.contains('link')) continue;
          const h = e.getBoundingClientRect().height; if (h < 39.5) out.push(`${e.tagName.toLowerCase()}.${String(e.className).split(/\s+/)[0]} ${Math.round(h * 10) / 10}px`);
        }
        const mb = document.querySelector('.ux-menu-btn'); const b = mb && vis(mb) ? mb.getBoundingClientRect() : null;
        return { out, menu: b ? [Math.round(b.width), Math.round(b.height)] : null };
      });
      m.out.forEach((x) => low.add(`${r} ${x}`)); if (m.menu) menu = m.menu;
    }
    ok('スマホの押しやすさ', `${layout}: main 内のボタン・入力欄の高さが 40px 以上`, low.size === 0, [...low].slice(0, 5).join(' | '));
    if (layout !== 'public') ok('スマホの押しやすさ', `${layout}: ヘッダーの ☰ が 44×44px 以上`, menu && menu[0] >= 44 && menu[1] >= 44, JSON.stringify(menu));
    // コマンドパレット（外付けキーボードの Ctrl+K）
    await go(page, '/');
    await page.keyboard.press('Control+k');
    const pal = await page.waitForSelector('.ux-palette input', { timeout: 3000 }).catch(() => null);
    if (pal) ok('スマホの押しやすさ', `${layout}: コマンドパレットの入力欄が 16px 以上（フォーカス時に拡大しない）`, parseFloat(await pal.evaluate((e) => getComputedStyle(e).fontSize)) >= 16);
    await ctx.close();
  }
}

async function publicLayers(browser) {
  for (const [devName, dev] of [['iphone', IPHONE], ['desktop', { viewport: { width: 1440, height: 900 } }]]) {
    const ctx = await ctxFor(browser, dev, 'public');
    const page = await ctx.newPage();
    await page.goto(BASE + '/'); await ready(page);
    const r = await page.evaluate(() => [...document.querySelectorAll('.page[data-page="dashboard"] [data-section]')].filter((e) => getComputedStyle(e, '::before').content !== 'none').map((e) => {
      const s = getComputedStyle(e); return { sec: e.getAttribute('data-section'), label: getComputedStyle(e, '::before').content.slice(1, 5), clipped: s.overflowY !== 'visible' };
    }));
    ok('Public の3層', `${devName}: 3 つの層のラベルがカードに切り取られない`, r.length === 3 && r.every((x) => !x.clipped), JSON.stringify(r));
    ok('Public の3層', `${devName}: 横スクロールなし`, await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1));
    if (OUT && devName === 'iphone') { await page.locator('[data-section="completeness"]').scrollIntoViewIfNeeded(); await page.screenshot({ path: path.join(OUT, 'public_layer3_iphone.png') }); }
    await ctx.close();
  }
}

async function previewBar(browser) {
  // 設定でカードを押してプレビュー状態にし、長い画面をスクロールしても帯が画面の上端に残ること
  for (const target of LAYOUTS) {
    // 適用中は別のレイアウトにしておき、target のカードを押して target をプレビューする
    const ctx = await ctxFor(browser, IPHONE, target === 'research' ? 'commercial' : 'research');
    const page = await ctx.newPage();
    await page.goto(BASE + '/settings'); await page.waitForSelector('#design');
    await page.click(`#design [data-layout="${target}"]`);
    await page.waitForSelector('.ux-previewbar');
    const shown = await page.getAttribute('html', 'data-ui');
    await go(page, '/report');
    await page.evaluate(() => window.scrollTo(0, 700)); await page.waitForTimeout(200);
    const top = await page.evaluate(() => { const b = document.querySelector('.ux-previewbar'); return b ? Math.round(b.getBoundingClientRect().top) : null; });
    const header = await page.evaluate(() => { const t = document.querySelector('.ux-shell > .ux-top'); if (!t || getComputedStyle(t).position !== 'sticky') return 0; return Math.round(t.getBoundingClientRect().bottom); });
    ok('プレビュー帯', `${target}（スマホ）: スクロールしても帯が上端（固定ヘッダーの直下）に残る`, shown === target && top !== null && Math.abs(top - header) <= 1, `top=${top} header=${header} shown=${shown}`);
    await ctx.close();
  }
}

async function noColorMix(browser) {
  // color-mix() を知らないブラウザーの再現: 配信される CSS / JS の color-mix( を未知の関数名に置き換える（@supports の判定も同じ結果になる）
  for (const layout of ['research', 'enterprise']) {
    const ctx = await ctxFor(browser, { viewport: { width: 1440, height: 900 } }, layout, { card: 'flat', accent: '#7a3fb0' });
    await ctx.route(/\.(css|js)(\?.*)?$/, async (route) => {
      const res = await route.fetch(); const body = (await res.text()).replace(/color-mix\(/g, 'color-nomix(');
      await route.fulfill({ response: res, body });
    });
    const page = await ctx.newPage();
    await page.goto(BASE + '/'); await ready(page);
    const r = await page.evaluate(() => {
      const t = (e) => (e ? getComputedStyle(e).backgroundColor : null);
      return { bar: t(document.querySelector('.bar div')), card: t(document.querySelector('.card')), sel: getComputedStyle(document.documentElement).getPropertyValue('--sel').trim() };
    });
    const solid = (c) => c && !/rgba\(0, 0, 0, 0\)|transparent/.test(c);
    ok('color-mix なし', `${layout}: 進捗バーの塗りとフラットのカードが透明にならない`, solid(r.bar) && solid(r.card), JSON.stringify(r));
    ok('color-mix なし', `${layout}: 主色を選んだときの選択色が有効な色になる`, /^#[0-9a-f]{8}$/i.test(r.sel), r.sel);
    await ctx.close();
  }
}

async function narrowAndLandscape(browser) {
  const scope = 'スマホ・横向き';
  // Original でサイドバーを右／アイコンのみにしても、スマホでは本文が全幅のまま
  for (const custom of [{ sidebarPos: 'right' }, { sidebarPos: 'right', sidebarMode: 'icons' }, { sidebarMode: 'icons' }]) {
    for (const w of [320, 390]) {
      const ctx = await ctxFor(browser, { ...IPHONE, viewport: { width: w, height: 760 } }, 'original', custom);
      const page = await ctx.newPage();
      await page.goto(BASE + '/'); await ready(page);
      const mw = await page.evaluate(() => Math.round(document.querySelector('main').getBoundingClientRect().width));
      ok(scope, `Original ${JSON.stringify(custom)} 幅${w}: 本文が全幅`, mw >= w - 1, `main ${mw}px`);
      await ctx.close();
    }
  }
  // Original の「アイコンのみ」は、位置が左（既定）でも効く
  {
    const ctx = await ctxFor(browser, { viewport: { width: 1280, height: 800 } }, 'original', { sidebarMode: 'icons' });
    const page = await ctx.newPage(); await page.goto(BASE + '/'); await ready(page);
    const sw = await page.evaluate(() => Math.round(document.querySelector('.side').getBoundingClientRect().width));
    ok(scope, 'Original「アイコンのみ」（左）: サイドバーが 64px になる', sw === 64, `side ${sw}px`);
    await ctx.close();
  }
  // Original の横向きスマホ: サイドバーの一番下の項目（設定）に届く
  {
    const ctx = await ctxFor(browser, { ...IPHONE, viewport: { width: 844, height: 390 } }, 'original');
    const page = await ctx.newPage(); await page.goto(BASE + '/'); await ready(page);
    const link = page.locator('.side a[href="/settings"]');
    await link.scrollIntoViewIfNeeded();
    const hit = await link.evaluate((e) => { const b = e.getBoundingClientRect(); const t = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2); return !!t && (t === e || e.contains(t)); });
    ok(scope, 'Original 844×390: サイドバーの「設定」を押せる', hit);
    await ctx.close();
  }
  // レポートの目次で移動しても、見出しが固定ヘッダーの下に隠れない
  for (const layout of ['research', 'commercial', 'enterprise']) {
    const ctx = await ctxFor(browser, IPHONE, layout);
    const page = await ctx.newPage(); await page.goto(BASE + '/report'); await page.waitForSelector('.md h1');
    const toc = page.locator('main a[href^="#"]');
    const n = await toc.count();
    if (!n) { ok(scope, `${layout}: レポートの目次リンクがある`, false); await ctx.close(); continue; }
    await toc.nth(Math.min(2, n - 1)).click(); await page.waitForTimeout(400);
    const r = await page.evaluate(() => {
      const id = decodeURIComponent(location.hash.slice(1)); const t = document.getElementById(id); const top = document.querySelector('.ux-shell > .ux-top');
      return { target: t ? Math.round(t.getBoundingClientRect().top) : null, header: top ? Math.round(top.getBoundingClientRect().bottom) : 0 };
    });
    ok(scope, `${layout}: 目次で移動した先が固定ヘッダーの下に隠れない`, r.target !== null && r.target >= r.header, JSON.stringify(r));
    await ctx.close();
  }
  // Public: 幅 320px で層のラベルが 1 行、識別帯が全幅。文字「特大」でも進捗バーの数値が切れない
  {
    const ctx = await ctxFor(browser, { ...IPHONE, viewport: { width: 320, height: 700 } }, 'public', { fontScale: 1.3 });
    const page = await ctx.newPage(); await page.goto(BASE + '/'); await ready(page);
    const r = await page.evaluate(() => {
      const lab = [...document.querySelectorAll('.page[data-page="dashboard"] [data-section]')].filter((e) => getComputedStyle(e, '::before').content !== 'none').map((e) => parseFloat(getComputedStyle(e, '::before').height));
      const band = document.querySelector('.ux-idband').getBoundingClientRect();
      const clipped = [...document.querySelectorAll('.bar')].filter((b) => { const s = b.querySelector('span'); return s && s.scrollHeight > b.clientHeight + 1; }).length;
      const fs = parseFloat(getComputedStyle(document.documentElement).fontSize);
      const nav = document.querySelector('.ux-bottom').getBoundingClientRect();
      return { lab, fs, band: [Math.round(band.left), Math.round(band.width)], clipped, sw: document.documentElement.scrollWidth, navTop: Math.round(nav.top), pad: parseFloat(getComputedStyle(document.querySelector('main')).paddingBottom), navH: Math.round(nav.height) };
    });
    ok(scope, 'Public 幅320・文字特大: 層のラベルが 1 行', r.lab.length === 3 && r.lab.every((h) => h < r.fs * 2.2), JSON.stringify(r.lab));
    ok(scope, 'Public 幅320: 識別帯が画面の全幅', r.band[0] === 0 && r.band[1] === 320, JSON.stringify(r.band));
    ok(scope, 'Public 幅320・文字特大: 進捗バーの数値が切れない', r.clipped === 0, `切れ ${r.clipped} 本`);
    ok(scope, 'Public 幅320・文字特大: 横スクロールなし・本文の下余白が下部ナビ以上', r.sw <= 321 && r.pad >= r.navH, JSON.stringify({ sw: r.sw, pad: r.pad, navH: r.navH }));
    await ctx.close();
  }
  // Research 横向き: 段階のラベルが 1 行
  {
    const ctx = await ctxFor(browser, { ...IPHONE, viewport: { width: 844, height: 390 } }, 'research');
    const page = await ctx.newPage(); await page.goto(BASE + '/'); await ready(page);
    const hs = await page.evaluate(() => [...document.querySelectorAll('.ux-pipeline .ux-pipe a b')].map((e) => { const r = document.createRange(); r.selectNodeContents(e); return new Set([...r.getClientRects()].map((x) => Math.round(x.top))).size; }));
    ok(scope, 'Research 844×390: 段階のラベルが折れない', hs.length > 0 && hs.every((n) => n <= 1), JSON.stringify(hs));
    await ctx.close();
  }
  // 追加した部品の最小文字サイズ
  for (const layout of ['research', 'enterprise']) {
    const ctx = await ctxFor(browser, { ...IPHONE, viewport: { width: 844, height: 390 } }, layout);
    const page = await ctx.newPage(); await page.goto(BASE + '/settings'); await page.waitForSelector('#design');
    const small = await page.evaluate(() => { const out = []; for (const e of document.querySelectorAll('.ux-top *, .ux-side *, .ux-pill, .ux-tag, kbd')) { if (!e.childNodes.length || ![...e.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim())) continue; const b = e.getBoundingClientRect(); if (!b.width) continue; const f = parseFloat(getComputedStyle(e).fontSize); if (f < 9.8) out.push(`${e.tagName.toLowerCase()}.${String(e.className).split(/\s+/)[0]} ${f}px`); } return out; });
    ok(scope, `${layout} 844×390: 枠の部品の文字が 10px 前後以上`, small.length === 0, small.slice(0, 5).join(' | '));
    await ctx.close();
  }
}

async function workerRoutes() {
  const file = process.env.WORKER; if (!file) return;
  const mod = await import(pathToFileURL(path.resolve(file)).href);
  const get = async (p, method = 'GET') => { const res = await mod.default.fetch(new Request('https://example.invalid' + p, { method })); return { status: res.status, type: res.headers.get('content-type') || '', body: method === 'GET' ? await res.text() : '', csp: res.headers.get('content-security-policy') }; };
  const bad = [];
  for (const r of [...ROUTES, '/data/', '/settings/', '/library/S-2026-01']) { const x = await get(r); if (x.status !== 200 || !x.type.startsWith('text/html') || !x.body.includes('<div id="root">') || !x.csp) bad.push(`${r} → ${x.status} ${x.type}`); }
  ok('Cloudflare エッジスクリプト', '画面の URL（/data・末尾 / 付きを含む）がアプリ本体を返す', bad.length === 0, bad.join(' | '));
  const seed = await get('/data/seed.json');
  ok('Cloudflare エッジスクリプト', '同梱データ /data/seed.json は JSON のまま返る', seed.status === 200 && seed.type.includes('json'));
  ok('Cloudflare エッジスクリプト', '存在しないファイルは 404', (await get('/assets/none.js')).status === 404 && (await get('/data/none.json')).status === 404);
  ok('Cloudflare エッジスクリプト', 'GET / HEAD 以外は 405', (await get('/', 'POST')).status === 405);
}

(async () => {
  if (OUT) fs.mkdirSync(OUT, { recursive: true });
  const only = (process.env.ONLY || '').split(',').filter(Boolean);
  const want = (n) => !only.length || only.includes(n);
  const browser = await chromium.launch();
  const t0 = Date.now();
  if (want('dark')) await darkContrast(browser);
  if (want('mid')) await midWidth(browser);
  if (want('direct')) await directAccess(browser);
  if (want('touch')) await touchTargets(browser);
  if (want('public')) await publicLayers(browser);
  if (want('preview')) await previewBar(browser);
  if (want('nomix')) await noColorMix(browser);
  if (want('narrow')) await narrowAndLandscape(browser);
  await browser.close();
  if (want('worker')) await workerRoutes();
  const pass = results.filter((r) => r.pass).length;
  if (OUT) fs.writeFileSync(path.join(OUT, 'final-checks.json'), JSON.stringify({ base: BASE, engine: ENGINE, at: new Date().toISOString(), seconds: Math.round((Date.now() - t0) / 1000), pass, total: results.length, results }, null, 1));
  console.log(`\n${pass}/${results.length} passed`);
  process.exit(pass === results.length ? 0 : 1);
})().catch((e) => { console.error(e); process.exit(2); });
