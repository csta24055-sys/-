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
//   8. アクセシビリティ（ONLY=a11y）: axe-core の serious / critical が 0 件（5 レイアウト × ライト / 端末ダーク × PC / iPhone × 主要 6 画面）、
//      配色を端末と逆にしたときの色、コマンドパレット・シートのフォーカス、ホームの Tab 順、フォーカスの輪、入力部品の名前、
//      一覧と表の行のキーボード操作、ダーク配色の主色、スクロール位置の余白、選択肢の矢印キー
//   9. select の見た目（ONLY=select）: 追加 4 レイアウトは appearance: none・高さ 40px 以上・矢印あり（WebKit は既定の見た目だと高さが効かない）
//  10. コードレビューの指摘（ONLY=cr）: Original＋サイドバーだけの変更で本文が素の Original と画素一致、パレットのスクロール、読み上げ文言、
//      履歴、別タブとの整合、部品の形、印刷時の配色、Original のアイコンのみ、起動時の配色の先付け
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
  // 末尾の / は起動時に取り除く。/data を直接開くと、配信側が /data/ へ転送してからアプリ本体を返す（確認用サーバー・GitHub Pages 型）。
  // そのまま残ると、Original の下部タブで「解析」と「その他」の両方が選択表示になり、/report/ では成果物の相対リンクが 404 になる
  {
    const ctx = await ctxFor(browser, { ...IPHONE, serviceWorkers: 'block' }, 'original');
    const page = await ctx.newPage(); const out = [];
    for (const [r, want] of [['/data', '/data'], ['/data/', '/data'], ['/settings/', '/settings'], ['/library/', '/library'], ['/report/?x=1#sec', '/report?x=1#sec']]) {
      await page.goto(BASE + r); await page.waitForSelector('main h1', { timeout: 8000 }); await page.waitForTimeout(200);
      out.push({ r, want, got: await page.evaluate(() => location.pathname + location.search + location.hash), active: await page.locator('.tabbar a.active').count() });
    }
    ok('直接アクセス（初回・SWなし）', '開いた後の URL に末尾の / が残らない（?… と #… は保つ）', out.every((o) => o.got === o.want), out.filter((o) => o.got !== o.want).map((o) => `${o.r} → ${o.got}`).join(' | '));
    ok('直接アクセス（初回・SWなし）', 'Original のスマホ下部タブ: どの URL でも選択表示は 1 つだけ', out.every((o) => o.active === 1), out.map((o) => `${o.r}: ${o.active}`).join(' | '));
    await page.goto(BASE + '/report/'); await page.waitForSelector('ul.deliv a', { timeout: 15000 });
    const links = await page.evaluate(() => [...document.querySelectorAll('ul.deliv a')].map((a) => new URL(a.href).pathname));
    const res = await page.evaluate(async (u) => { const r = await fetch(u, { method: 'HEAD' }); return { status: r.status, type: r.headers.get('content-type') || '' }; }, links[0]);
    ok('直接アクセス（初回・SWなし）', '/report/ を直接開いても、成果物リンクが /deliverables/… に解決されて取得できる', links.length > 0 && links.every((h) => h.startsWith('/deliverables/')) && res.status === 200 && !/text\/html/.test(res.type), `${links.length} 件 ${decodeURIComponent(links[0] || '').slice(0, 40)} → ${res.status} ${res.type}`);
    await ctx.close();
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
  const init = await get('/ui-init.js');
  ok('Cloudflare エッジスクリプト', '起動時に配色を先付けする /ui-init.js を JavaScript として返す（CSP の script-src \'self\' で読める外部ファイル）', init.status === 200 && /javascript/.test(init.type) && init.body.includes('aqros-ui-prefs-v1') && /script-src 'self'/.test(init.csp || ''), `${init.status} ${init.type}`);
}

// =====================================================================
// アクセシビリティ（監査 A11Y-02〜15 で直した項目の確認）。ONLY=a11y で単独実行できる。
//   A11Y=axe,theme,…（下の PARTS の名前）で、その部分だけを実行できる（開発用）。
// キーボード操作は実際にキーを送って確かめる（Tab / Shift+Tab / Enter / Esc / 矢印）。
// Chromium で確認済み。WebKit では Tab がリンクに止まらない設定が既定なので Alt+Tab を使う（WebKit での実行はここでは未確認）。
// =====================================================================
const zlib = require('zlib');
const AXE = fs.readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');
const DESKTOP = { viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 };
const PHONE = { ...IPHONE, deviceScaleFactor: 1 };
const TAB = ENGINE === 'webkit' ? 'Alt+Tab' : 'Tab';
const BACKTAB = ENGINE === 'webkit' ? 'Alt+Shift+Tab' : 'Shift+Tab';
const HOME_ORDER = {
  original: ['stats', 'charts', 'timeline', 'findings', 'completeness', 'activity'],
  research: ['stats', 'completeness', 'charts', 'findings', 'timeline', 'activity'],
  public: ['findings', 'stats', 'charts', 'timeline', 'completeness', 'activity'],
  commercial: ['charts', 'stats', 'findings', 'activity', 'timeline', 'completeness'],
  enterprise: ['stats', 'charts', 'completeness', 'activity', 'findings', 'timeline'],
};
// 画面ごとに、中身（非同期に読み込むデータ）が出そろったことを示す要素
const ROUTE_READY = { '/': '.cptable', '/library': '.srclist li', '/data': 'input[type=file]', '/simulator': '.stat-v', '/plan': 'table.rank tbody tr', '/settings': '#design' };
// axe-core の serious / critical を 0 件にできなかった既知の例外。ここに挙げたものだけを差し引く（黙って除外しない）。
//   { layout, device, mode, route, id, max, reason } — 該当する条件・規則の違反が max 件以下なら既知として扱い、結果に件数と理由を出す
const AXE_KNOWN = [];

async function goWait(page, route) {
  await go(page, route);
  if (ROUTE_READY[route]) await page.waitForSelector(ROUTE_READY[route], { timeout: 20000 });
  if (route === '/settings') { if (!(await page.locator('details.ux-custom[open]').count())) await page.locator('details.ux-custom summary').click(); }
  await page.waitForTimeout(250);
}
/** axe-core の serious / critical の違反。rules を渡すとその規則だけ、scope を渡すとその要素の中だけを調べる */
async function axeSerious(page, { rules = null, scope = null } = {}) {
  if (!(await page.evaluate(() => !!window.axe))) await page.addScriptTag({ content: AXE });
  return page.evaluate(async ([rules, scope]) => {
    const opt = { resultTypes: ['violations'] }; if (rules) opt.runOnly = { type: 'rule', values: rules };
    const r = await window.axe.run(scope ? document.querySelector(scope) : document, opt);
    return r.violations.filter((v) => ['serious', 'critical'].includes(v.impact)).map((v) => ({ id: v.id, impact: v.impact, n: v.nodes.length, sample: v.nodes.slice(0, 2).map((n) => n.target.join(' ')).join(' ; ') }));
  }, [rules, scope]);
}
const fmtV = (r, vs) => vs.map((v) => `${r} ${v.id}(${v.impact})×${v.n} ${v.sample}`);

/** 指定した要素の文字と実効背景のコントラスト比が limit 未満のもの */
const TEXT_CONTRAST = ([selector, limit]) => {
  // 色の書式は rgb()/rgba() のほか、color-mix() の結果の color(srgb r g b / a) も読む
  const parse = (c) => { let m = c.match(/^rgba?\(([^)]+)\)/); if (m) { const p = m[1].split(/[ ,/]+/).map(Number); return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 }; } m = c.match(/^color\(srgb ([^)]+)\)/); if (m) { const p = m[1].split(/[ /]+/).map(Number); return { r: p[0] * 255, g: p[1] * 255, b: p[2] * 255, a: p.length > 3 ? p[3] : 1 }; } return null; };
  const lum = ({ r, g, b }) => { const f = (x) => { x /= 255; return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
  const bgOf = (e) => { const stack = []; for (let n = e; n; n = n.parentElement) { const c = parse(getComputedStyle(n).backgroundColor); if (c && c.a > 0) { stack.push(c); if (c.a >= 1) break; } } let base = { r: 255, g: 255, b: 255 }; for (const c of stack.reverse()) base = { r: c.r * c.a + base.r * (1 - c.a), g: c.g * c.a + base.g * (1 - c.a), b: c.b * c.a + base.b * (1 - c.a) }; return base; };
  const out = []; let n = 0;
  for (const e of document.querySelectorAll(selector)) {
    const b = e.getBoundingClientRect(); if (!b.width || !b.height || !(e.innerText || '').trim()) continue; n++;
    const a = lum(parse(getComputedStyle(e).color)), c = lum(bgOf(e)); const ratio = (Math.max(a, c) + 0.05) / (Math.min(a, c) + 0.05);
    if (ratio < limit) out.push(`${Math.round(ratio * 100) / 100} ${e.tagName.toLowerCase()}.${String(e.className).trim().split(/\s+/).join('.')} "${(e.innerText || '').trim().slice(0, 12)}"`);
  }
  return { n, low: [...new Set(out)] };
};
const active = (page) => page.evaluate(() => { const e = document.activeElement; return e ? { tag: e.tagName, cls: String(e.className || ''), id: e.id || '', role: e.getAttribute('role') || '', text: (e.getAttribute('aria-label') || e.innerText || '').trim().slice(0, 30) } : null; });
const activeIn = (page, sel) => page.evaluate((s) => { const box = document.querySelector(s); return !!box && box.contains(document.activeElement); }, sel);
const activeIs = (page, sel) => page.evaluate((s) => !!document.activeElement && document.activeElement.matches(s), sel);

// ---------- axe-core: 5 レイアウト × ライト / 端末ダーク × PC / iPhone × 主要 6 画面 ----------
async function a11yAxeMatrix(browser) {
  for (const [devName, dev] of [['desktop', DESKTOP], ['iphone', PHONE]]) {
    for (const [mode, scheme] of [['ライト', 'light'], ['端末ダーク', 'dark']]) {
      for (const layout of LAYOUTS) {
        const ctx = await ctxFor(browser, { ...dev, colorScheme: scheme }, layout);
        const page = await ctx.newPage();
        await page.goto(BASE + '/'); await ready(page);
        const bad = [], known = [];
        for (const r of Object.keys(ROUTE_READY)) {
          await goWait(page, r);
          for (const v of await axeSerious(page)) {
            const k = AXE_KNOWN.find((x) => x.id === v.id && (!x.layout || x.layout === layout) && (!x.device || x.device === devName) && (!x.mode || x.mode === mode) && (!x.route || x.route === r) && v.n <= x.max);
            (k ? known : bad).push(...fmtV(r, [v]).map((s) => (k ? `${s}【既知: ${k.reason}】` : s)));
          }
        }
        ok(`axe/${devName}/${mode}`, `${layout}: 主要 6 画面（設定はカスタマイズを開いた状態）で serious・critical が 0 件`, bad.length === 0, [...bad, ...known].slice(0, 6).join(' | ') || (known.length ? '' : '0 件'));
        await ctx.close();
      }
    }
  }
}

// ---------- A11Y-03 / A11Y-04: 配色を端末と逆にしたとき ----------
async function a11yThemeOpposite(browser) {
  for (const [name, scheme, theme] of [['配色=ダーク・端末ライト', 'light', 'dark'], ['配色=ライト・端末ダーク', 'dark', 'light']]) {
    for (const layout of LAYOUTS) {
      const ctx = await ctxFor(browser, { ...DESKTOP, colorScheme: scheme }, layout, { theme });
      const page = await ctx.newPage();
      await page.goto(BASE + '/'); await ready(page);
      const low = []; let n = 0; const ax = [];
      for (const r of ['/', '/library']) {
        await goWait(page, r);
        const t = await page.evaluate(TEXT_CONTRAST, ['.badge, .pill', 4.5]); n += t.n; low.push(...t.low.map((x) => `${r} ${x}`));
        ax.push(...fmtV(r, await axeSerious(page, { rules: ['color-contrast'] })));
      }
      ok(`A11Y-03 ${name}`, `${layout}: 分類バッジと調査状態の文字が 4.5:1 以上（${n} 個）`, n > 0 && low.length === 0, low.slice(0, 5).join(' | '));
      ok(`A11Y-03 ${name}`, `${layout}: ホームと資料ライブラリで axe のコントラスト違反 0 件`, ax.length === 0, ax.slice(0, 4).join(' | '));
      await ctx.close();
    }
  }
  // Original で「配色: ダーク」を選んでプレビュー帯を出す（端末はライト）。帯は別の画面へ移っても出続ける
  for (const [devName, dev] of [['desktop', DESKTOP], ['iphone', PHONE]]) {
    const ctx = await ctxFor(browser, { ...dev, colorScheme: 'light' }, 'original');
    const page = await ctx.newPage();
    await page.goto(BASE + '/settings'); await page.waitForSelector('#design');
    await page.locator('details.ux-custom summary').click();
    await page.locator('.ux-field:has(.ux-field-l:text-is("配色")) button:text-is("ダーク")').click();
    await page.waitForSelector('.ux-previewbar');
    const bar = await page.evaluate(TEXT_CONTRAST, ['.ux-previewbar > span, .ux-previewbar button', 4.5]);
    ok('A11Y-04 Original 配色=ダーク', `${devName}: プレビュー帯の文字とボタンが 4.5:1 以上`, bar.n >= 3 && bar.low.length === 0, bar.low.join(' | '));
    const ax = fmtV('/settings', await axeSerious(page, { rules: ['color-contrast'] }));
    await goWait(page, '/simulator');
    await page.evaluate(() => document.querySelectorAll('details').forEach((d) => { d.open = true; })); await page.waitForTimeout(200);
    const warn = await page.evaluate(TEXT_CONTRAST, ['td.warn, .miss, .ux-warn, .offline, .warnlist, .error', 4.5]);
    ax.push(...fmtV('/simulator', await axeSerious(page, { rules: ['color-contrast'] })));
    ok('A11Y-04 Original 配色=ダーク', `${devName}: 設定とシミュレーターで axe のコントラスト違反 0 件（警告色の文字 ${warn.n} 個も 4.5:1 以上）`, ax.length === 0 && warn.low.length === 0, [...ax, ...warn.low].slice(0, 4).join(' | '));
    await ctx.close();
  }
}

// ---------- A11Y-05 / A11Y-15(c): コマンドパレット ----------
async function a11yPalette(browser) {
  for (const layout of ['research', 'commercial', 'enterprise']) {
    const scope = `A11Y-05 コマンドパレット/${layout}`;
    const ctx = await ctxFor(browser, DESKTOP, layout);
    const page = await ctx.newPage();
    await page.goto(BASE + '/'); await ready(page);
    await page.locator('.ux-cmd').focus(); await page.keyboard.press('Enter');
    await page.waitForSelector('.ux-palette');
    const inside = [await activeIs(page, '.ux-palette input')];
    for (const k of [TAB, TAB, TAB, BACKTAB, BACKTAB]) { await page.keyboard.press(k); inside.push(await activeIn(page, '.ux-palette')); }
    ok(scope, '開くと入力欄にフォーカスし、Tab / Shift+Tab を押してもフォーカスがパレットの外へ出ない', inside.every(Boolean), JSON.stringify(inside));
    await page.keyboard.press('Escape'); await page.waitForTimeout(150);
    ok(scope, 'Esc で閉じ、開いたボタンへフォーカスが戻る', (await page.locator('.ux-palette').count()) === 0 && await activeIs(page, '.ux-cmd'), JSON.stringify(await active(page)));
    // 入力欄以外にフォーカスがあっても Esc で閉じる（背景を押してフォーカスを外した状態を作る）
    await page.keyboard.press('Control+k'); await page.waitForSelector('.ux-palette');
    await page.evaluate(() => document.activeElement && document.activeElement.blur());
    await page.keyboard.press('Escape'); await page.waitForTimeout(150);
    ok(scope, '入力欄にフォーカスがなくても Esc で閉じる', (await page.locator('.ux-palette').count()) === 0);
    // 該当なし
    await page.keyboard.press('Control+k'); await page.waitForSelector('.ux-palette');
    await page.keyboard.type('zzzz'); await page.waitForTimeout(150);
    const none = await page.evaluate(() => { const i = document.querySelector('.ux-palette input'); const st = document.querySelector('.ux-palette [role="status"]'); const lb = document.querySelector('.ux-palette [role="listbox"]');
      return { expanded: i.getAttribute('aria-expanded'), controls: i.getAttribute('aria-controls'), status: st ? st.textContent.trim() : null, emptyListbox: !!lb && !lb.querySelector('[role="option"]') }; });
    const ax = await axeSerious(page, { scope: '.ux-palette' });
    ok(scope, '該当なしのとき: axe の serious・critical 0 件、aria-expanded=false、案内を role=status で伝える', ax.length === 0 && none.expanded === 'false' && !none.emptyListbox && /該当する機能がありません/.test(none.status || ''), JSON.stringify({ none, ax }));
    // 候補があるときの関係
    await page.locator('.ux-palette input').fill('レポ'); await page.waitForTimeout(150);
    const some = await page.evaluate(() => { const i = document.querySelector('.ux-palette input'); const lb = document.getElementById(i.getAttribute('aria-controls') || ''); const ad = document.getElementById(i.getAttribute('aria-activedescendant') || '');
      return { expanded: i.getAttribute('aria-expanded'), listbox: !!lb && lb.getAttribute('role') === 'listbox', option: !!ad && ad.getAttribute('role') === 'option' && ad.getAttribute('aria-selected') === 'true' }; });
    ok(scope, '候補があるとき: aria-expanded=true、aria-controls が listbox、選択中の候補が aria-activedescendant', some.expanded === 'true' && some.listbox && some.option, JSON.stringify(some));
    await page.keyboard.press('Enter');
    await page.waitForFunction(() => location.pathname === '/report'); await page.waitForTimeout(300);
    ok(`A11Y-15 ${layout}`, 'パレットで移動した後、フォーカスが移動先の本文（main）にある', await activeIs(page, 'main'), JSON.stringify(await active(page)));
    await ctx.close();
  }
}

// ---------- A11Y-06: 「すべての機能／その他」シート ----------
async function a11ySheet(browser) {
  const cases = [
    ['public', 'desktop', DESKTOP, {}, '.ux-allbtn', '.ux-sheet'],
    ['research', 'desktop', DESKTOP, { sidebarMode: 'hidden' }, '.ux-menu-btn', '.ux-sheet'],
    ['enterprise', 'desktop', DESKTOP, { sidebarMode: 'hidden' }, '.ux-menu-btn', '.ux-sheet'],
    ['commercial', 'iphone', PHONE, {}, '.ux-menu-btn', '.ux-sheet'],
    ['research', 'iphone', PHONE, {}, '.ux-bottom button', '.ux-sheet'],
    ['original', 'iphone', PHONE, {}, '.tabbar a[href="#more"]', '.sheet'],
  ];
  for (const [layout, devName, dev, custom, opener, sheet] of cases) {
    const scope = `A11Y-06 シート/${layout}/${devName}`;
    const ctx = await ctxFor(browser, dev, layout, custom);
    const page = await ctx.newPage();
    await page.goto(BASE + '/'); await ready(page);
    await page.locator(opener).focus(); await page.keyboard.press('Enter');
    await page.waitForSelector(sheet); await page.waitForTimeout(150);
    ok(scope, '開くとフォーカスがシートの中（最初のリンク）へ移る', await activeIs(page, `${sheet} a`), JSON.stringify(await active(page)));
    const n = await page.locator(`${sheet} a, ${sheet} button`).count();
    const inside = []; const seen = new Set();
    for (let i = 0; i < n + 2; i++) { await page.keyboard.press(TAB); inside.push(await activeIn(page, sheet)); seen.add((await active(page)).text); }
    await page.keyboard.press(BACKTAB); inside.push(await activeIn(page, sheet));
    ok(scope, `Tab を ${n + 2} 回押してもシートの外へ出ず、中の ${n} 個を巡る`, inside.every(Boolean) && seen.size === n, `中=${inside.filter(Boolean).length}/${inside.length} 種類=${seen.size}/${n}`);
    await page.keyboard.press('Escape'); await page.waitForTimeout(150);
    ok(scope, 'Esc で閉じ、開いたボタンへフォーカスが戻る', (await page.locator(sheet).count()) === 0 && await activeIs(page, opener), JSON.stringify(await active(page)));
    await page.locator(opener).focus(); await page.keyboard.press('Enter'); await page.waitForSelector(sheet);
    await page.locator(`${sheet} button`).last().focus(); await page.keyboard.press('Enter'); await page.waitForTimeout(150);
    ok(scope, '「閉じる」を Enter で押しても、開いたボタンへフォーカスが戻る', (await page.locator(sheet).count()) === 0 && await activeIs(page, opener), JSON.stringify(await active(page)));
    if (layout !== 'original') {
      await page.locator(opener).focus(); await page.keyboard.press('Enter'); await page.waitForSelector(sheet);
      const aria = await page.evaluate(([s, o]) => { const e = document.querySelector(s); const b = document.querySelector(o); return { role: e.getAttribute('role'), modal: e.getAttribute('aria-modal'), name: e.getAttribute('aria-label'), popup: b.getAttribute('aria-haspopup') }; }, [sheet, opener]);
      const ax = await axeSerious(page, { scope: sheet });
      ok(scope, 'シートは role=dialog（名前付き・aria-modal）、開くボタンは aria-haspopup=dialog、axe 0 件', aria.role === 'dialog' && aria.modal === 'true' && !!aria.name && aria.popup === 'dialog' && ax.length === 0, JSON.stringify({ aria, ax }));
      // リンクで移動したときは移動先の本文へ
      await page.locator(`${sheet} a[href="/learn"]`).focus(); await page.keyboard.press('Enter');
      await page.waitForFunction(() => location.pathname === '/learn'); await page.waitForTimeout(300);
      ok(scope, 'シートのリンクで移動した後、フォーカスが移動先の本文（main）にある', await activeIs(page, 'main'), JSON.stringify(await active(page)));
    }
    await ctx.close();
  }
}

// ---------- A11Y-07 / A11Y-15(a): アイコンのみのサイドバー ----------
async function a11yIconSidebar(browser) {
  for (const layout of NEW) {
    const ctx = await ctxFor(browser, DESKTOP, layout, { sidebarMode: 'icons' });
    const page = await ctx.newPage();
    await page.goto(BASE + '/'); await ready(page);
    const ax = await axeSerious(page, { scope: '.ux-side' });
    const r = await page.evaluate(() => {
      // 読み上げ名: aria-label → 見えていて aria-hidden でない文字 → title の順
      const text = (n) => { if (n.nodeType === 3) return n.textContent; if (n.nodeType !== 1 || n.getAttribute('aria-hidden') !== null || getComputedStyle(n).display === 'none') return ''; return [...n.childNodes].map(text).join(''); };
      const name = (e) => (e.getAttribute('aria-label') || text(e).trim() || e.getAttribute('title') || '').trim();
      const names = [...document.querySelectorAll('.ux-side a.ux-navlink')].map(name);
      const box = document.querySelector('.ux-statebox'); const bb = box ? box.getBoundingClientRect() : null;
      const btn = document.querySelector('.ux-side .ux-collapse, .ux-side .ux-rail-toggle'); const b = btn ? btn.getBoundingClientRect() : { width: 0, height: 0 }; // Public には畳むボタンがない
      return { names, statebox: bb ? Math.round(bb.width) : 0, btnName: btn ? name(btn) : '', btnW: Math.round(b.width), btnH: Math.round(b.height), expanded: btn ? btn.getAttribute('aria-expanded') : null };
    });
    ok('A11Y-07 アイコンのみのサイドバー', `${layout}: メニューのリンク 10 個すべてに読み上げ名がある（axe 0 件）`, r.names.length === 10 && r.names.every((x) => x.length > 1) && ax.length === 0, JSON.stringify({ names: r.names.filter((x) => x.length <= 1).length, ax }));
    if (layout === 'public') ok('A11Y-07 アイコンのみのサイドバー', 'public: 「データの状態」欄が幅 60px のサイドバーに潰れて出ない', r.statebox === 0 || r.statebox >= 150, `幅 ${r.statebox}px`);
    else ok('A11Y-15 畳むボタン', `${layout}: サイドバーを開くボタンに名前があり（記号だけでない）、幅 32px 以上`, /開く|展開/.test(r.btnName) && r.btnW >= 32 && r.expanded === 'false', JSON.stringify({ name: r.btnName, w: r.btnW, h: r.btnH, expanded: r.expanded }));
    await ctx.close();
  }
}

// ---------- A11Y-08: ホームの並び順（DOM の順 = 見た目の順 = Tab の順） ----------
const HOME_SECTIONS = () => [...document.querySelectorAll('.page[data-page="dashboard"] > [data-section]')].map((e) => ({ k: e.getAttribute('data-section'), top: Math.round(e.getBoundingClientRect().top + window.scrollY), order: getComputedStyle(e).order }));
async function a11yHomeOrder(browser) {
  const scope = 'A11Y-08 ホームの並び順';
  for (const [devName, dev] of [['desktop', DESKTOP], ['iphone', PHONE]]) {
    for (const layout of LAYOUTS) {
      const ctx = await ctxFor(browser, dev, layout);
      const page = await ctx.newPage();
      await page.goto(BASE + '/'); await ready(page); await page.waitForSelector('.cptable'); await page.waitForTimeout(300);
      const secs = await page.evaluate(HOME_SECTIONS);
      const dom = secs.map((s) => s.k), visual = [...secs].sort((a, b) => a.top - b.top).map((s) => s.k);
      ok(scope, `${layout}/${devName}: DOM の順が見た目の順と同じで、レイアウトの指定どおり（CSS の order を使わない）`, dom.join() === HOME_ORDER[layout].join() && visual.join() === dom.join() && secs.every((s) => s.order === '0'), `DOM ${dom.join('→')} / 見た目 ${visual.join('→')} / order ${[...new Set(secs.map((s) => s.order))].join(',')}`);
      if (devName === 'desktop' && layout !== 'original') {
        // 実際に Tab を押して、フォーカスが通るブロックの順と、上へ戻る動きを数える
        // 「上へ戻る」は、ブロックが変わったときに 120px を超えて上へ動いた回数（同じブロックの中の 2 列目へ移る動きは数えない）
        const seq = []; let back = 0, lastY = -1, lastSec = null, steps = 0, entered = false;
        await page.evaluate(() => window.scrollTo(0, 0));
        for (; steps < 400; steps++) {
          await page.keyboard.press(TAB);
          const a = await page.evaluate(() => { const e = document.activeElement; if (!e || e === document.body) return null; const pg = e.closest('.page[data-page="dashboard"]'); const s = e.closest('[data-section]'); return { inPage: !!pg, sec: s ? s.getAttribute('data-section') : null, y: Math.round(e.getBoundingClientRect().top + window.scrollY) }; });
          if (!a) { if (entered) break; continue; }
          if (!a.inPage) { if (entered) break; continue; }
          entered = true;
          if (a.sec && seq[seq.length - 1] !== a.sec) seq.push(a.sec);
          if (lastY >= 0 && a.sec !== lastSec && a.y < lastY - 120) back++;
          lastY = a.y; lastSec = a.sec;
        }
        const want = HOME_ORDER[layout].filter((k) => seq.includes(k));
        ok(scope, `${layout}/desktop: Tab で進む順が見た目の順と同じ（上へ戻る動き 0 回）`, seq.length >= 3 && seq.join() === want.join() && back === 0, `Tab の順 ${seq.join('→')} / 上へ戻る ${back} 回 / ${steps} 回`);
      }
      await ctx.close();
    }
  }
  // レイアウトを切り替えても、各ブロックは作り直されず位置だけが入れ替わる（同じ DOM 要素のまま）
  {
    const ctx = await ctxFor(browser, DESKTOP, 'research');
    const page = await ctx.newPage();
    await page.goto(BASE + '/settings'); await page.waitForSelector('#design');
    await page.click('#design [data-layout="public"]'); await page.waitForSelector('.ux-public');
    await go(page, '/'); await page.waitForSelector('.cptable'); await page.waitForTimeout(300);
    // 目印: 要素そのものに印を付け、ブロックの中のスクロール位置（利用者が動かした状態）も変えておく
    const before = await page.evaluate(() => { const els = [...document.querySelectorAll('.page[data-page="dashboard"] > [data-section]')]; els.forEach((e, i) => { e.__mark = `m${i}-${e.getAttribute('data-section')}`; }); window.__h1 = document.querySelector('main h1'); return els.map((e) => e.getAttribute('data-section')); });
    await page.locator('.ux-previewbar button', { hasText: '取り消す' }).click(); await page.waitForSelector('.ux-research'); await page.waitForTimeout(300);
    const after = await page.evaluate(() => ({ order: [...document.querySelectorAll('.page[data-page="dashboard"] > [data-section]')].map((e) => e.getAttribute('data-section')), marks: [...document.querySelectorAll('.page[data-page="dashboard"] > [data-section]')].map((e) => (e.__mark || '').split('-')[1] === e.getAttribute('data-section')), h1: window.__h1 === document.querySelector('main h1') }));
    ok(scope, '切替（Public のプレビュー → 取り消して Research）で順は変わるが、各ブロックは同じ DOM 要素のまま（作り直されない）', before.join() === HOME_ORDER.public.join() && after.order.join() === HOME_ORDER.research.join() && after.marks.length === 6 && after.marks.every(Boolean) && after.h1, JSON.stringify({ before, after }));
    await ctx.close();
  }
}

// ---------- A11Y-09: フォーカスの輪の見えやすさ（フォーカスあり／なしの画面を撮って、変わった画素＝輪を測る） ----------
function decodePng(buf) {
  let p = 8, w = 0, h = 0, ct = 0; const idat = [];
  while (p < buf.length) { const len = buf.readUInt32BE(p); const type = buf.toString('ascii', p + 4, p + 8); const data = buf.subarray(p + 8, p + 8 + len); if (type === 'IHDR') { w = data.readUInt32BE(0); h = data.readUInt32BE(4); ct = data[9]; } if (type === 'IDAT') idat.push(data); p += 12 + len; }
  const bpp = ct === 6 ? 4 : 3; const raw = zlib.inflateSync(Buffer.concat(idat)); const stride = w * bpp; const out = Buffer.alloc(w * h * bpp); let prev = Buffer.alloc(stride);
  for (let y = 0; y < h; y++) {
    const f = raw[y * (stride + 1)]; const line = raw.subarray(y * (stride + 1) + 1, (y + 1) * (stride + 1)); const cur = Buffer.alloc(stride);
    for (let x = 0; x < stride; x++) { const a = x >= bpp ? cur[x - bpp] : 0, b = prev[x], c = x >= bpp ? prev[x - bpp] : 0; let v = line[x]; if (f === 1) v += a; else if (f === 2) v += b; else if (f === 3) v += (a + b) >> 1; else if (f === 4) { const pa = Math.abs(b - c), pb = Math.abs(a - c), pc = Math.abs(a + b - 2 * c); v += pa <= pb && pa <= pc ? a : pb <= pc ? b : c; } cur[x] = v & 255; }
    cur.copy(out, y * stride); prev = cur;
  }
  return { w, h, bpp, data: out };
}
async function ringOf(page, sel, nth = 0) {
  const lum = ([r, g, b]) => { const f = (x) => { const s = x / 255; return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4; }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
  const loc = page.locator(sel).nth(nth);
  await loc.scrollIntoViewIfNeeded(); await page.mouse.move(2, 2);
  await page.keyboard.press(TAB); await loc.evaluate((e) => e.focus()); await page.waitForTimeout(150); // キーボード操作の直後にフォーカスする（:focus-visible を有効にする）
  const info = await loc.evaluate((e) => { const cs = getComputedStyle(e); const r = e.getBoundingClientRect(); return { fv: e.matches(':focus-visible'), style: cs.outlineStyle, width: parseFloat(cs.outlineWidth), offset: parseFloat(cs.outlineOffset), color: cs.outlineColor, rect: [r.x, r.y, r.width, r.height] }; });
  const pad = Math.max(0, info.offset) + info.width + 3; const vp = page.viewportSize();
  const clip = { x: Math.max(0, Math.floor(info.rect[0] - pad)), y: Math.max(0, Math.floor(info.rect[1] - pad)) };
  clip.width = Math.min(vp.width - clip.x, Math.ceil(info.rect[2] + pad * 2)); clip.height = Math.min(vp.height - clip.y, Math.ceil(info.rect[3] + pad * 2));
  const on = decodePng(await page.screenshot({ clip, type: 'png' }));
  await loc.evaluate((e) => e.blur()); await page.waitForTimeout(150);
  const off = decodePng(await page.screenshot({ clip, type: 'png' }));
  let n = 0; const ratios = [];
  for (let i = 0; i < on.w * on.h; i++) { const o = i * on.bpp; const a = [on.data[o], on.data[o + 1], on.data[o + 2]], b = [off.data[o], off.data[o + 1], off.data[o + 2]]; if (Math.abs(a[0] - b[0]) + Math.abs(a[1] - b[1]) + Math.abs(a[2] - b[2]) > 12) { n++; const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); ratios.push((x + 0.05) / (y + 0.05)); } }
  ratios.sort((x, y) => x - y);
  const dpr = on.w / clip.width;
  const expected = Math.round((2 * (info.rect[2] + 2 * info.offset + info.width) * info.width + 2 * (info.rect[3] + 2 * info.offset + info.width) * info.width) * dpr * dpr);
  return { focusVisible: info.fv, outline: `${info.style} ${info.width}px ${info.color} offset ${info.offset}px`, coverage: expected ? Math.round((n / expected) * 100) : 0, contrast: ratios.length ? Math.round(ratios[Math.floor(ratios.length / 2)] * 100) / 100 : 0 };
}
async function a11yFocusRing(browser) {
  const scope = 'A11Y-09 フォーカスの輪';
  // [説明, レイアウト, カスタマイズ, 端末, [セレクター, 何番目]...]。輪の 85% 以上が見え、輪と下の色の比が 3:1 以上
  const cases = [
    ['Original＋文字の大きさ=大: 濃いサイドバーのリンク', 'original', { fontScale: 1.15 }, DESKTOP, [['.side nav a', 1]]],
    ['Original＋文字の大きさ=大＋サイドバーを隠す: 下部メニュー', 'original', { fontScale: 1.15, sidebarMode: 'hidden' }, DESKTOP, [['.tabbar a', 1]]],
    ['Enterprise: スコープバーのボタン', 'enterprise', {}, DESKTOP, [['.ux-scopebar .ux-cmd', 0], ['.ux-scopebar .ux-theme', 0]]],
    ['Enterprise スマホ: ☰ と下部ナビ', 'enterprise', {}, PHONE, [['.ux-menu-btn', 0], ['.ux-bottom a', 1], ['.ux-bottom button', 0]]],
    ['Public: 文字サイズ切替（標準・大・特大）', 'public', {}, DESKTOP, [['.ux-seg button', 0], ['.ux-seg button', 1], ['.ux-seg button', 2]]],
    ['Public スマホ: 文字サイズ切替と下部ナビ', 'public', {}, PHONE, [['.ux-seg button', 0], ['.ux-seg button', 2], ['.ux-bottom a', 1]]],
    ['Research スマホ: 下部ナビ', 'research', {}, PHONE, [['.ux-bottom a', 1], ['.ux-bottom button', 0]]],
  ];
  for (const [name, layout, custom, dev, sels] of cases) {
    const ctx = await ctxFor(browser, { ...dev, colorScheme: 'light' }, layout, custom);
    const page = await ctx.newPage();
    await page.goto(BASE + '/'); await ready(page);
    const rs = []; for (const [sel, nth] of sels) rs.push({ sel: `${sel}[${nth}]`, ...(await ringOf(page, sel, nth)) });
    ok(scope, `${name}: 輪の 85% 以上が見え、地との比が 3:1 以上`, rs.every((r) => r.focusVisible && r.coverage >= 85 && r.contrast >= 3), rs.map((r) => `${r.sel} ${r.coverage}% ${r.contrast}:1`).join(' | '));
    await ctx.close();
  }
}

// ---------- A11Y-10 / A11Y-11: 入力部品の名前と、一覧・表の行のキーボード操作 ----------
async function a11yNamesAndRows(browser) {
  for (const layout of ['original', 'research']) {
    const ctx = await ctxFor(browser, DESKTOP, layout);
    const page = await ctx.newPage();
    await page.goto(BASE + '/'); await ready(page);
    await goWait(page, '/simulator');
    const sl = await page.evaluate(() => { const all = [...document.querySelectorAll('main input[type=range]')]; return { n: all.length, unnamed: all.filter((e) => !(e.getAttribute('aria-label') || '').trim() && !(e.labels && e.labels.length)).length }; });
    const ax1 = await axeSerious(page, { rules: ['label', 'select-name'] });
    ok('A11Y-10 入力部品の名前', `${layout}: シミュレーターのスライダー ${sl.n} 本すべてに名前がある（axe label 0 件）`, sl.n >= 19 && sl.unnamed === 0 && ax1.length === 0, JSON.stringify({ sl, ax1 }));
    await goWait(page, '/plan');
    const se = await page.evaluate(() => { const all = [...document.querySelectorAll('main select')]; return { n: all.length, unnamed: all.filter((e) => !(e.getAttribute('aria-label') || '').trim() && !(e.labels && e.labels.length)).length }; });
    const ax2 = await axeSerious(page, { rules: ['label', 'select-name'] });
    ok('A11Y-10 入力部品の名前', `${layout}: 研究計画の select ${se.n} 個すべてに名前がある（axe select-name 0 件）`, se.n >= 14 && se.unnamed === 0 && ax2.length === 0, JSON.stringify({ se, ax2 }));

    // 研究計画の表の行: Tab で行に止まり、Enter / Space で選べる
    await page.evaluate(() => window.scrollTo(0, 0));
    let hit = false; for (let i = 0; i < 80 && !hit; i++) { await page.keyboard.press(TAB); hit = await activeIs(page, 'table.rank tbody tr'); }
    let rowOk = false, detail = '';
    if (hit) {
      await page.keyboard.press(TAB); await page.keyboard.press(TAB); // 3 行目へ
      const id = await page.evaluate(() => document.activeElement.children[1].textContent.trim());
      await page.keyboard.press('Enter'); await page.waitForTimeout(200);
      const a = await page.evaluate(() => ({ active: document.activeElement.classList.contains('active'), open: [...document.querySelectorAll('main .card-h h2')].map((h) => h.textContent.trim()) }));
      await page.keyboard.press(BACKTAB); const id2 = await page.evaluate(() => document.activeElement.children[1].textContent.trim());
      await page.keyboard.press(' '); await page.waitForTimeout(200);
      const b = await page.evaluate(() => ({ active: document.activeElement.classList.contains('active'), open: [...document.querySelectorAll('main .card-h h2')].map((h) => h.textContent.trim()) }));
      rowOk = a.active && a.open.some((t) => t.startsWith(id + ' ')) && b.active && b.open.some((t) => t.startsWith(id2 + ' ')) && id !== id2; detail = JSON.stringify({ id, id2, a: a.active, b: b.active });
    }
    ok('A11Y-11 キーボードで行を選ぶ', `${layout}: 研究計画の表の行に Tab で止まり、Enter と Space で開ける`, hit && rowOk, detail || 'Tab 80 回で行に届かない');

    // 資料ライブラリ: 一覧の題名に Tab で止まり、Enter で詳細が開き、詳細の見出しへフォーカスが移る
    await goWait(page, '/library');
    await page.evaluate(() => window.scrollTo(0, 0));
    hit = false; for (let i = 0; i < 60 && !hit; i++) { await page.keyboard.press(TAB); hit = await activeIs(page, '.srclist li [role="link"]'); }
    let libOk = false; detail = '';
    if (hit) {
      await page.keyboard.press(TAB);
      const title = await page.evaluate(() => document.activeElement.textContent.trim());
      await page.keyboard.press('Enter');
      await page.waitForFunction(() => location.pathname.startsWith('/library/'), null, { timeout: 5000 }).catch(() => undefined);
      await page.waitForSelector('.detail-pane .dtitle', { timeout: 8000 }).catch(() => undefined); await page.waitForTimeout(300);
      const a = await page.evaluate(() => ({ path: decodeURIComponent(location.pathname), focus: document.activeElement.className, text: document.activeElement.textContent.trim(), rows: document.querySelectorAll('.srclist li').length, stops: document.querySelectorAll('.srclist li [role="link"][tabindex="0"]').length }));
      libOk = a.path.startsWith('/library/') && a.focus === 'dtitle' && a.text === title && a.rows > 0 && a.stops === a.rows; detail = JSON.stringify({ path: a.path, focus: a.focus, same: a.text === title, rows: a.rows, stops: a.stops });
    }
    ok('A11Y-11 キーボードで行を選ぶ', `${layout}: 資料ライブラリの一覧に Tab で止まり、Enter で詳細が開いて見出しへフォーカスが移る`, hit && libOk, detail || 'Tab 60 回で一覧に届かない');
    await ctx.close();
  }
}

// ---------- A11Y-12: ダーク配色で主色を選んだとき ----------
async function a11yDarkAccent(browser) {
  const scope = 'A11Y-12 ダーク配色の主色';
  const PRESETS = ['#0f5b5c', '#00687a', '#1f5f8b', '#0f6b5c', '#1d5fa8', '#5b3fa0', '#8a4b0f', '#a1201b'];
  // 8 色すべて: 画面の実際の色（リンク・枠線ボタン・塗りボタン）と、設定に表示されるコントラスト比
  for (const layout of ['research', 'original']) {
    const ctx = await ctxFor(browser, { ...DESKTOP, colorScheme: 'dark' }, layout);
    const page = await ctx.newPage();
    await page.goto(BASE + '/settings'); await page.waitForSelector('#design');
    await page.locator('details.ux-custom summary').click();
    const bad = [];
    for (const h of PRESETS) {
      await page.click(`.ux-sw[aria-label="主色 ${h}"]`); await page.waitForTimeout(120);
      const low = await page.evaluate(TEXT_CONTRAST, ['main a, main button:not(:disabled), .ux-navlink, .side nav a, .stat-v, .ux-pill, .ux-previewbar button', 4.5]);
      const shown = await page.evaluate(() => {
        const parse = (c) => c.match(/[\d.]+/g).slice(0, 3).map(Number); const lum = ([r, g, b]) => { const f = (x) => { x /= 255; return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
        const b = [...document.querySelectorAll('.ux-previewbar button')].find((x) => x.textContent.trim() === '適用'); const cs = getComputedStyle(b);
        const a = lum(parse(cs.color)), c = lum(parse(cs.backgroundColor)); const note = document.querySelector('.ux-accent-ratio');
        return { real: Math.round(((Math.max(a, c) + 0.05) / (Math.min(a, c) + 0.05)) * 100) / 100, note: note ? note.textContent : '' };
      });
      const said = parseFloat((shown.note.match(/コントラスト比 ([\d.]+):1/) || [])[1]);
      if (low.low.length) bad.push(`${h}: ${low.low.slice(0, 2).join(', ')}`);
      if (!(Math.abs(said - shown.real) <= 0.1) || /白い文字/.test(shown.note) || shown.real < 4.5) bad.push(`${h}: 表示 ${said}:1 / 実際の「適用」ボタン ${shown.real}:1「${shown.note.slice(0, 30)}」`);
    }
    ok(scope, `${layout}（端末ダーク）: 主色プリセット 8 色すべてで、リンク・ボタンの文字が 4.5:1 以上、表示される比が実際の塗りボタンの比と一致`, bad.length === 0, bad.slice(0, 4).join(' | '));
    await ctx.close();
  }
  // 5 レイアウト × PC / iPhone: 保存済みの主色 #5b3fa0（監査の再現条件）で axe のコントラスト違反 0 件
  for (const [devName, dev] of [['desktop', DESKTOP], ['iphone', PHONE]]) {
    for (const layout of LAYOUTS) {
      const ctx = await ctxFor(browser, { ...dev, colorScheme: 'dark' }, layout, { accent: '#5b3fa0' });
      const page = await ctx.newPage();
      await page.goto(BASE + '/'); await ready(page);
      const ax = [];
      for (const r of ['/', '/settings']) { await goWait(page, r); ax.push(...fmtV(r, await axeSerious(page, { rules: ['color-contrast'] }))); }
      ok(scope, `${layout}/${devName}（端末ダーク・主色 #5b3fa0）: ホームと設定で axe のコントラスト違反 0 件`, ax.length === 0, ax.slice(0, 4).join(' | '));
      await ctx.close();
    }
  }
  // 配色=ダーク（端末はライト）でも同じ。ライト配色では選んだ色のまま
  {
    const ctx = await ctxFor(browser, { ...DESKTOP, colorScheme: 'light' }, 'public', { accent: '#a1201b', theme: 'dark' });
    const page = await ctx.newPage();
    await page.goto(BASE + '/'); await ready(page); await goWait(page, '/settings');
    const ax = fmtV('/settings', await axeSerious(page, { rules: ['color-contrast'] }));
    const darkAccent = await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--accent').trim());
    await page.locator('.ux-field:has(.ux-field-l:text-is("配色")) button:text-is("ライト")').click(); await page.waitForTimeout(150);
    const lightAccent = await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--accent').trim());
    const saved = await page.evaluate((k) => JSON.parse(localStorage.getItem(k)).applied.custom.accent, KEY);
    ok(scope, 'public（配色=ダーク・端末ライト・主色 #a1201b）: axe のコントラスト違反 0 件。ライトに戻すと選んだ色のまま。保存値は選んだ色', ax.length === 0 && darkAccent !== '#a1201b' && lightAccent === '#a1201b' && saved === '#a1201b', JSON.stringify({ ax, darkAccent, lightAccent, saved }));
    await ctx.close();
  }
}

// ---------- A11Y-13: 固定ヘッダー・下部ナビに隠れない ----------
async function a11yScrollPadding(browser) {
  const scope = 'A11Y-13 スクロール位置の余白';
  // フォーカスしている要素が、固定ヘッダーの下・下部ナビの下に完全に隠れているか
  const HIDDEN = () => {
    const e = document.activeElement; if (!e || e === document.body || !e.closest('main')) return null;
    const r = e.getBoundingClientRect(); if (!r.width || !r.height) return null;
    const top = document.querySelector('.ux-shell > .ux-top'); const fixedTop = top && ['sticky', 'fixed'].includes(getComputedStyle(top).position) ? top.getBoundingClientRect().bottom : 0;
    const nav = document.querySelector('.ux-bottom, .tabbar'); const nb = nav && getComputedStyle(nav).display !== 'none' && getComputedStyle(nav).position === 'fixed' ? nav.getBoundingClientRect().top : window.innerHeight;
    const name = `${e.tagName.toLowerCase()}.${String(e.className).split(/\s+/)[0]} "${(e.innerText || e.getAttribute('aria-label') || '').trim().slice(0, 12)}"`;
    if (r.bottom <= fixedTop + 1) return `ヘッダーの下: ${name}`;
    if (r.top >= nb - 1) return `下部ナビの下: ${name}`;
    return '';
  };
  for (const [devName, dev] of [['desktop', DESKTOP], ['iphone', PHONE]]) {
    for (const layout of ['research', 'commercial', 'enterprise']) {
      const ctx = await ctxFor(browser, dev, layout);
      const page = await ctx.newPage();
      await page.goto(BASE + '/simulator'); await ready(page); await page.waitForSelector('.stat-v');
      await page.keyboard.press(TAB);
      const skip = await activeIs(page, '.ux-skip');
      await page.keyboard.press('Enter'); await page.waitForTimeout(300);
      const r = await page.evaluate(() => { const top = document.querySelector('.ux-shell > .ux-top').getBoundingClientRect(); const h1 = document.querySelector('main h1').getBoundingClientRect(); return { header: Math.round(top.bottom), h1: Math.round(h1.top), focus: document.activeElement.tagName }; });
      ok(scope, `${layout}/${devName}: スキップリンクで本文へ移っても、見出しが固定ヘッダーの下に隠れない`, skip && r.focus === 'MAIN' && r.h1 >= r.header - 1, JSON.stringify(r));
      // 本文の最後から Shift+Tab で戻る
      await page.evaluate(() => { const f = [...document.querySelectorAll('main a[href], main button:not(:disabled), main input, main select, main textarea, main [tabindex="0"]')].filter((e) => e.getClientRects().length); f[f.length - 1].focus(); });
      const hidden = [];
      for (let i = 0; i < 60; i++) { await page.keyboard.press(BACKTAB); const h = await page.evaluate(HIDDEN); if (h === null) break; if (h) hidden.push(h); }
      ok(scope, `${layout}/${devName}: Shift+Tab で戻ったフォーカスが固定ヘッダー・下部ナビの下に隠れない`, hidden.length === 0, hidden.slice(0, 3).join(' | '));
      await ctx.close();
    }
  }
  // スマホのホーム: Tab で進んだフォーカスが下部ナビの下に隠れない（Original の下部タブを含む）
  for (const layout of LAYOUTS) {
    const ctx = await ctxFor(browser, PHONE, layout);
    const page = await ctx.newPage();
    await page.goto(BASE + '/'); await ready(page); await page.waitForSelector('.cptable'); await page.waitForTimeout(300);
    const hidden = []; let n = 0, entered = false;
    for (let i = 0; i < 400; i++) { await page.keyboard.press(TAB); const h = await page.evaluate(HIDDEN); if (h === null) { if (entered) break; continue; } entered = true; n++; if (h) hidden.push(h); }
    ok(scope, `${layout}/iphone: ホームを Tab で進んでも、フォーカスが下部ナビ・ヘッダーの下に隠れない（本文の ${n} 個）`, n > 10 && hidden.length === 0, hidden.slice(0, 3).join(' | '));
    await ctx.close();
  }
}

// ---------- A11Y-14: 詳細カスタマイズの選択肢（radiogroup）の矢印キー ----------
async function a11yRadioKeys(browser) {
  const scope = 'A11Y-14 選択肢の矢印キー';
  for (const layout of ['original', 'public']) {
    const ctx = await ctxFor(browser, DESKTOP, layout);
    const page = await ctx.newPage();
    await page.goto(BASE + '/settings'); await page.waitForSelector('#design');
    await page.locator('details.ux-custom summary').click();
    const groups = await page.evaluate(() => [...document.querySelectorAll('.ux-custom [role="radiogroup"]')].map((g) => ({ radios: g.querySelectorAll('[role="radio"]').length, stops: g.querySelectorAll('[role="radio"][tabindex="0"]').length, checked: g.querySelectorAll('[role="radio"][aria-checked="true"]').length })));
    ok(scope, `${layout}: 8 つのグループとも、Tab で止まるのは 1 か所だけ（選択中の項目）`, groups.length === 8 && groups.every((g) => g.stops === 1 && g.checked === 1), JSON.stringify(groups.map((g) => `${g.stops}/${g.radios}`)));
    const field = '.ux-field:has(.ux-field-l:text-is("文字の大きさ"))';
    const cur = () => page.evaluate(() => { const f = [...document.querySelectorAll('.ux-custom .ux-field')].find((x) => x.querySelector('.ux-field-l').textContent.trim() === '文字の大きさ'); return { checked: f.querySelector('[aria-checked="true"]').textContent.trim(), focus: document.activeElement.textContent.trim(), inGroup: !!document.activeElement.closest('[role="radiogroup"]'), fs: document.documentElement.style.getPropertyValue('--u-fs-scale') }; });
    await page.locator(`${field} [aria-checked="true"]`).focus();
    const s0 = await cur();
    await page.keyboard.press('ArrowRight'); await page.waitForTimeout(120); const s1 = await cur();
    await page.keyboard.press('ArrowDown'); await page.waitForTimeout(120); const s2 = await cur();
    await page.keyboard.press('ArrowRight'); await page.waitForTimeout(120); const s3 = await cur(); // 端から先頭へ回る
    await page.keyboard.press('ArrowUp'); await page.waitForTimeout(120); const s4 = await cur();   // 先頭から端へ回る
    const seq = [s0, s1, s2, s3, s4];
    ok(scope, `${layout}: → ↓ で次、↑ で前の選択肢へ移り（端で反対側へ回る）、選択とフォーカスが一緒に動く`, seq.map((s) => s.checked).join() === '標準,大,特大,小,特大' && seq.every((s) => s.checked === s.focus && s.inGroup) && s2.fs === '1.3', JSON.stringify(seq.map((s) => `${s.checked}/${s.focus}`)));
    // 主色のグループも同じ（自動 → 1 色目）。色の入力欄の矢印キーは奪わない
    await page.locator('.ux-swatches [role="radio"][aria-checked="true"]').focus();
    await page.keyboard.press('ArrowRight'); await page.waitForTimeout(120);
    const sw = await page.evaluate(() => ({ focus: document.activeElement.getAttribute('aria-label'), checked: document.activeElement.getAttribute('aria-checked'), accent: document.documentElement.style.getPropertyValue('--accent') }));
    ok(scope, `${layout}: 主色のグループも矢印キーで選べる`, sw.focus === '主色 #0f5b5c' && sw.checked === 'true' && !!sw.accent, JSON.stringify(sw));
    await ctx.close();
  }
}

// ---------- A11Y-15(b): プレビュー帯の「適用」「取り消す」の後のフォーカス ----------
async function a11yPreviewFocus(browser) {
  for (const [applied, target] of [['original', 'research'], ['research', 'original'], ['public', 'commercial']]) {
    const ctx = await ctxFor(browser, DESKTOP, applied);
    const page = await ctx.newPage();
    const out = [];
    for (const label of ['取り消す', '適用']) {
      await page.goto(BASE + '/settings'); await page.waitForSelector('#design');
      await page.click(`#design [data-layout="${target}"]`); await page.waitForSelector('.ux-previewbar');
      await go(page, '/simulator');
      await page.locator('.ux-previewbar button', { hasText: label }).focus(); await page.keyboard.press('Enter');
      await page.waitForFunction(() => !document.querySelector('.ux-previewbar')); await page.waitForTimeout(250);
      out.push({ label, focus: (await active(page)).tag, ui: await page.getAttribute('html', 'data-ui') });
    }
    ok('A11Y-15 プレビュー帯', `${applied} → ${target}: 帯の「取り消す」「適用」を Enter で押した後、フォーカスが本文（main）へ移る（文書の先頭に落ちない）`, out.every((o) => o.focus === 'MAIN') && out[0].ui === applied && out[1].ui === target, JSON.stringify(out));
    await ctx.close();
  }
}

async function a11yChecks(browser) {
  const PARTS = { axe: a11yAxeMatrix, theme: a11yThemeOpposite, palette: a11yPalette, sheet: a11ySheet, icons: a11yIconSidebar, order: a11yHomeOrder, ring: a11yFocusRing, rows: a11yNamesAndRows, accent: a11yDarkAccent, scroll: a11yScrollPadding, radio: a11yRadioKeys, preview: a11yPreviewFocus };
  const pick = (process.env.A11Y || '').split(',').filter(Boolean);
  for (const [name, fn] of Object.entries(PARTS)) {
    if (pick.length && !pick.includes(name)) continue;
    try { await fn(browser); } catch (e) { ok(`a11y/${name}`, '検査が最後まで実行できる', false, String(e && e.message).split('\n')[0]); }
  }
}

// =====================================================================
// select の見た目（WebKit の CI で見つかった件）。ONLY=select
// WebKit（macOS の Safari 系）は、既定の見た目（menulist）の select に height / min-height が効かない。
// 追加 4 レイアウトでは appearance: none にして枠と矢印を自前で描く。ここでは、その指定が効いていることと高さを測る
// （WebKit での高さそのものは .github/workflows/ui-webkit.yml の「スマホの押しやすさ」が測る）。
// =====================================================================
async function selectAppearance(browser) {
  const scope = 'select の見た目';
  const MEASURE = () => [...document.querySelectorAll('main select')].filter((e) => e.getBoundingClientRect().width > 0).map((e) => {
    const cs = getComputedStyle(e); const lum = (c) => { const p = c.match(/[\d.]+/g).slice(0, 3).map(Number); const f = (x) => { x /= 255; return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; }; return 0.2126 * f(p[0]) + 0.7152 * f(p[1]) + 0.0722 * f(p[2]); };
    const stroke = (cs.backgroundImage.match(/stroke='%23([0-9a-f]{6})'/i) || [])[1];
    let arrow = 0; if (stroke) { const v = parseInt(stroke, 16); const a = lum(`rgb(${(v >> 16) & 255},${(v >> 8) & 255},${v & 255})`), b = lum(cs.backgroundColor); arrow = Math.round(((Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05)) * 100) / 100; }
    return { appearance: cs.appearance || cs.webkitAppearance, h: Math.round(e.getBoundingClientRect().height * 10) / 10, img: cs.backgroundImage.startsWith('url("data:image/svg+xml'), pr: parseFloat(cs.paddingRight), arrow, label: e.getAttribute('aria-label') || '' };
  });
  for (const [mode, scheme] of [['ライト', 'light'], ['端末ダーク', 'dark']]) {
    for (const layout of LAYOUTS) {
      const ctx = await ctxFor(browser, { ...IPHONE, colorScheme: scheme }, layout);
      const page = await ctx.newPage();
      await page.goto(BASE + '/'); await ready(page);
      const all = [];
      for (const [r, sel] of [['/library', '.srclist li'], ['/simulator', '.stat-v'], ['/plan', 'table.rank tbody tr'], ['/cloud', 'main h1']]) {
        await go(page, r); await page.waitForSelector(sel); await page.waitForTimeout(200);
        all.push(...(await page.evaluate(MEASURE)).map((x) => ({ r, ...x })));
        if (OUT && (r === '/library' || r === '/simulator')) { const s = page.locator('main select').first(); if (await s.count()) { await s.scrollIntoViewIfNeeded(); await page.screenshot({ path: path.join(OUT, `select_${layout}_${scheme}${r.replace('/', '_')}.png`) }); } }
      }
      if (layout === 'original') {
        ok(scope, `original/${mode}: select は既定の見た目のまま（改修前と同じ。${all.length} 個）`, all.length > 0 && all.every((x) => x.appearance !== 'none' && !x.img), JSON.stringify(all.filter((x) => x.appearance === 'none' || x.img).slice(0, 3)));
      } else {
        const bad = all.filter((x) => x.appearance !== 'none' || x.h < 39.5 || !x.img || x.pr < 24 || x.arrow < 3);
        ok(scope, `${layout}/${mode}（スマホ）: select ${all.length} 個とも appearance: none・高さ 40px 以上・右端に矢印（地との比 3:1 以上）`, all.length > 0 && bad.length === 0, bad.slice(0, 3).map((x) => `${x.r} ${x.label} ${x.appearance} ${x.h}px 矢印${x.arrow}:1`).join(' | '));
      }
      await ctx.close();
    }
  }
  // カスタマイズを付けた Original（data-ux あり）の select も変えない
  {
    const ctx = await ctxFor(browser, IPHONE, 'original', { fontScale: 1.15, density: 'comfortable' });
    const page = await ctx.newPage();
    await page.goto(BASE + '/'); await ready(page); await go(page, '/library'); await page.waitForSelector('.srclist li');
    const all = await page.evaluate(MEASURE);
    ok(scope, 'original＋カスタマイズ（文字=大・密度=ゆったり）: select は既定の見た目のまま', (await page.getAttribute('html', 'data-ux')) !== null && all.length > 0 && all.every((x) => x.appearance !== 'none' && !x.img), JSON.stringify(all.slice(0, 2)));
    await ctx.close();
  }
}

// =====================================================================
// コードレビューの指摘（CR-01〜10）の確認。ONLY=cr
// =====================================================================
/** 描画が落ち着くまで待つ（グラフは幅を測ってから描くので、負荷の高いときに棒が出る前に撮らないようにする） */
async function settle(page) {
  await page.waitForTimeout(800);
  let last = -1, same = 0;
  for (let i = 0; i < 40 && same < 5; i++) {
    const n = await page.evaluate(() => document.querySelector('.shell').outerHTML.length + document.querySelectorAll('svg path, svg rect, svg circle').length * 100000);
    same = n === last ? same + 1 : 0; last = n;
    await page.waitForTimeout(300);
  }
}
const stored = (page) => page.evaluate((k) => JSON.parse(localStorage.getItem(k) || 'null'), KEY);

async function codeReviewChecks(browser) {
  // ---------- CR-01: Original でサイドバーだけを変えても、サイドバー以外は素の Original のまま ----------
  {
    const scope = 'CR-01 Original＋サイドバーだけの変更';
    // Research でサイドバーを畳んで開く（見た目は元どおり）→ 保存値は「自動」に戻り、履歴を使わない
    {
      const ctx = await ctxFor(browser, DESKTOP, 'research');
      const page = await ctx.newPage();
      await page.goto(BASE + '/'); await ready(page);
      await page.click('.ux-collapse'); await page.waitForSelector('.ux-shell[data-sidebar="left-icons"]');
      const mid = await stored(page);
      await page.click('.ux-collapse'); await page.waitForSelector('.ux-shell[data-sidebar="left-expanded"]');
      const p = await stored(page);
      ok(scope, 'Research: サイドバーを畳んで開くと保存値は「自動」に戻り、「元に戻す」の履歴を使わない', mid.applied.custom.sidebarMode === 'icons' && p.applied.custom.sidebarMode === 'auto' && p.history.length === 0, JSON.stringify({ mid: mid.applied.custom.sidebarMode, after: p.applied.custom.sidebarMode, history: p.history.length }));
      await ctx.close();
    }
    // 基準: 素の Original（1440×900。本文の幅 1204px）。サイドバーを変えたものは、本文の幅が同じになる画面幅で撮って .page を比べる
    const shoot = async (custom, width, route, hideTabbar) => {
      const ctx = await ctxFor(browser, { viewport: { width, height: 900 }, deviceScaleFactor: 1, reducedMotion: 'reduce' }, 'original', custom);
      const page = await ctx.newPage();
      await page.goto(BASE + route); await ready(page); await page.waitForSelector(ROUTE_READY[route]);
      if (hideTabbar) await page.addStyleTag({ content: '.tabbar{visibility:hidden!important}' }); // 画面下に固定のメニューが .page の画像に写り込まないようにする
      await settle(page);
      const info = await page.evaluate(() => { const h = document.documentElement; const st = document.querySelector('.stat'); const cp = document.querySelector('.cptable td.cp'); return { ux: h.hasAttribute('data-ux'), attrs: h.getAttributeNames().filter((a) => a.startsWith('data-')).join(' '), sidebar: document.querySelector('.shell').getAttribute('data-sidebar'), main: Math.round(document.querySelector('main').getBoundingClientRect().width), stat: st ? getComputedStyle(st).borderRadius : '', cp: cp ? getComputedStyle(cp).padding : '', pageH: Math.round(document.querySelector('.page').getBoundingClientRect().height) }; });
      const png = await page.locator('main .page').screenshot({ type: 'png' });
      await ctx.close();
      return { info, png };
    };
    for (const route of ['/', '/plan']) {
      const base = await shoot({}, 1440, route, false);
      for (const [name, custom, width] of [['位置=右', { sidebarPos: 'right' }, 1440], ['表示=アイコンのみ', { sidebarMode: 'icons' }, 1440 - 236 + 64], ['表示=隠す', { sidebarMode: 'hidden' }, 1440 - 236], ['表示=展開（既定と同じ値を明示）', { sidebarMode: 'expanded', sidebarPos: 'left', density: 'standard', card: 'outline', radius: 'standard' }, 1440]]) {
        const v = await shoot(custom, width, route, custom.sidebarMode === 'hidden');
        const same = v.png.equals(base.png);
        ok(scope, `${route} サイドバーの${name}: data-ux が付かず、本文（.page）が素の Original と画素単位で同じ`, !v.info.ux && v.info.main === base.info.main && same, JSON.stringify({ attrs: v.info.attrs, sidebar: v.info.sidebar, main: `${v.info.main}/${base.info.main}`, stat: `${v.info.stat}/${base.info.stat}`, cp: `${v.info.cp}/${base.info.cp}`, pageH: `${v.info.pageH}/${base.info.pageH}`, 画像一致: same }));
      }
    }
    // 見た目のカスタマイズ（文字・密度など）を付けたときは、これまでどおり data-ux が付く
    {
      const ctx = await ctxFor(browser, DESKTOP, 'original', { density: 'compact' });
      const page = await ctx.newPage(); await page.goto(BASE + '/'); await ready(page);
      ok(scope, 'Original＋情報密度=詰める: カスタマイズとして扱う（data-ux と data-density が付く）', (await page.getAttribute('html', 'data-ux')) !== null && (await page.getAttribute('html', 'data-density')) === 'compact');
      await ctx.close();
    }
  }

  // ---------- CR-02: コマンドパレットの選択行が見える範囲に入る ----------
  for (const [w, h] of [[1280, 600], [844, 390]]) {
    const ctx = await ctxFor(browser, { viewport: { width: w, height: h } }, 'research');
    const page = await ctx.newPage();
    await page.goto(BASE + '/'); await ready(page);
    await page.keyboard.press('Control+k'); await page.waitForSelector('.ux-palette');
    const vis = () => page.evaluate(() => { const li = document.querySelector('.ux-palette li.on').getBoundingClientRect(); const ul = document.querySelector('.ux-palette ul').getBoundingClientRect(); return { ok: li.top >= ul.top - 1 && li.bottom <= ul.bottom + 1, li: [Math.round(li.top), Math.round(li.bottom)], ul: [Math.round(ul.top), Math.round(ul.bottom)], text: document.querySelector('.ux-palette li.on b').textContent }; });
    const out = [];
    for (let i = 0; i < 9; i++) { await page.keyboard.press('ArrowDown'); await page.waitForTimeout(60); out.push(await vis()); }
    for (let i = 0; i < 9; i++) { await page.keyboard.press('ArrowUp'); await page.waitForTimeout(60); out.push(await vis()); }
    const bad = out.filter((o) => !o.ok);
    ok('CR-02 コマンドパレット', `${w}×${h}: ↑↓ で選んだ行が、いつも一覧の見える範囲にある（18 回）`, bad.length === 0 && out[8].text === '設定・バックアップ', bad.slice(0, 2).map((o) => `${o.text} 行 ${o.li} 一覧 ${o.ul}`).join(' | '));
    await ctx.close();
  }

  // ---------- CR-03 / CR-04: 読み上げ文言と履歴 ----------
  {
    const ctx = await ctxFor(browser, DESKTOP, 'original');
    const page = await ctx.newPage();
    await page.goto(BASE + '/settings'); await page.waitForSelector('#design');
    await page.click('#design [data-layout="research"]'); await page.waitForSelector('.ux-previewbar');
    const a1 = await page.locator('.ux-sr[role="status"]').textContent();
    await page.click('#design [data-layout="original"]'); await page.waitForFunction(() => !document.querySelector('.ux-previewbar'));
    const a2 = await page.locator('.ux-sr[role="status"]').textContent();
    ok('CR-03 読み上げ', '適用中のカードを押してプレビューをやめたとき、「プレビュー中です」と読み上げない', /プレビュー中です/.test(a1) && !/プレビュー中です/.test(a2) && /適用中/.test(a2), `${a1} → ${a2}`);
    // Enterprise を適用し、ヘッダーの配色ボタンを 6 回押す
    await page.click('#design [data-layout="enterprise"]'); await page.click('#design .ux-design-actions button:text-is("適用")'); await page.waitForSelector('.ux-enterprise');
    const h0 = (await stored(page)).history.map((x) => x.layout);
    for (let i = 0; i < 6; i++) { await page.click('.ux-theme'); await page.waitForTimeout(80); }
    const p = await stored(page);
    await page.click('#design button:has-text("元に戻す")'); await page.waitForTimeout(200);
    const ui = await page.getAttribute('html', 'data-ui');
    ok('CR-04 履歴', '配色ボタンを 6 回押しても履歴は増えず、「元に戻す」1 回で直前のレイアウト（Original）へ戻る', h0.join() === 'original' && p.history.map((x) => x.layout).join() === 'original' && p.applied.layout === 'enterprise' && ui === 'original', JSON.stringify({ before: h0, after: p.history.map((x) => `${x.layout}/${x.custom.theme}`), theme: p.applied.custom.theme, undo: ui }));
    await ctx.close();
  }
  {
    // Public の文字サイズ切替（即時操作）も履歴に積まない
    const ctx = await ctxFor(browser, DESKTOP, 'public');
    const page = await ctx.newPage(); await page.goto(BASE + '/'); await ready(page);
    for (const i of [1, 2, 0, 1]) { await page.locator('.ux-seg button').nth(i).click(); await page.waitForTimeout(80); }
    const p = await stored(page);
    ok('CR-04 履歴', 'Public の文字サイズ切替を 4 回押しても履歴は増えない（設定は保存される）', p.history.length === 0 && p.applied.custom.fontScale === 1.15, JSON.stringify({ history: p.history.length, fontScale: p.applied.custom.fontScale }));
    await ctx.close();
  }

  // ---------- CR-05: 別のタブで適用された設定を、プレビューの取り消し後に読み直す ----------
  {
    const ctx = await browser.newContext(DESKTOP);
    const a = await ctx.newPage(), b = await ctx.newPage();
    await a.goto(BASE + '/settings'); await a.waitForSelector('#design');
    await a.click('#design [data-layout="research"]'); await a.waitForSelector('.ux-previewbar');
    await b.goto(BASE + '/settings'); await b.waitForSelector('#design');
    await b.click('#design [data-layout="commercial"]'); await b.click('#design .ux-design-actions button:text-is("適用")'); await b.waitForTimeout(300);
    await a.bringToFront();
    await a.click('#design .ux-design-actions button:text-is("取り消す")'); await a.waitForTimeout(300);
    const after = { ui: await a.getAttribute('html', 'data-ui'), head: (await a.locator('#design .card-h').textContent()).trim() };
    // 続けて A で別のレイアウトを適用しても、B の設定は履歴に残る（上書きで消えない）
    await a.click('#design [data-layout="public"]'); await a.click('#design .ux-design-actions button:text-is("適用")'); await a.waitForTimeout(300);
    const p = await stored(a);
    ok('CR-05 別タブとの整合', 'プレビュー中に別のタブで適用された設定を、取り消し後に読み直す。その後の適用で別タブの設定が履歴から消えない', after.ui === 'commercial' && /適用中: Commercial/.test(after.head) && p.applied.layout === 'public' && p.history.map((x) => x.layout).join() === 'commercial,original', JSON.stringify({ after, history: p.history.map((x) => x.layout) }));
    await ctx.close();
  }

  // ---------- CR-06: 共通規則が部品の指定を打ち消さない ----------
  {
    const scope = 'CR-06 部品の形';
    for (const layout of NEW) {
      const ctx = await ctxFor(browser, DESKTOP, layout);
      const page = await ctx.newPage();
      await page.goto(BASE + '/'); await ready(page); await page.waitForSelector('.cptable');
      const cp = await page.evaluate(() => ({ td: getComputedStyle(document.querySelector('.cptable td.cp')).padding, th: getComputedStyle(document.querySelector('.cptable th.vert')).padding }));
      await goWait(page, '/settings');
      const sw = await page.evaluate(() => { const e = document.querySelector('.ux-sw'); const b = e.getBoundingClientRect(); return { w: Math.round(b.width), h: Math.round(b.height), r: getComputedStyle(e).borderRadius }; });
      await go(page, '/graph'); await page.waitForSelector('.gnode'); await page.locator('.gnode').first().click(); await page.waitForTimeout(300);
      const link = await page.evaluate(() => { const e = document.querySelector('main button.link'); if (!e) return null; const cs = getComputedStyle(e); return { h: Math.round(e.getBoundingClientRect().height), fs: parseFloat(cs.fontSize), minH: cs.minHeight, r: cs.borderRadius }; });
      ok(scope, `${layout}: 色見本は 36px の円、完成度表の記号のセルは詰めたまま、リンク型のボタンは文字の高さ`, sw.w === 36 && sw.h === 36 && sw.r === '50%' && cp.td === '2px' && cp.th === '4px 2px' && !!link && link.minH === '0px' && link.h <= link.fs * 2, JSON.stringify({ sw, cp, link }));
      await ctx.close();
    }
    for (const layout of ['research', 'commercial']) {
      const ctx = await ctxFor(browser, IPHONE, layout);
      const page = await ctx.newPage(); await page.goto(BASE + '/'); await ready(page);
      const nav = await page.evaluate(() => { const b = document.querySelector('.ux-bottom button'), a = document.querySelector('.ux-bottom a'); return { br: getComputedStyle(b).borderRadius, bh: Math.round(b.getBoundingClientRect().height), ah: Math.round(a.getBoundingClientRect().height) }; });
      ok(scope, `${layout}（スマホ）: 下部ナビの「その他」がほかのタブと同じ形（角丸なし・同じ高さ）`, nav.br === '0px' && nav.bh === nav.ah && nav.bh >= 56, JSON.stringify(nav));
      await ctx.close();
    }
  }

  // ---------- CR-07: 配色をダークに固定したまま印刷しても、紙にはライトの色で出る ----------
  {
    const scope = 'CR-07 印刷';
    const PRINTED = () => {
      const lum = (c) => { const p = c.match(/[\d.]+/g).slice(0, 3).map(Number); const f = (x) => { x /= 255; return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; }; return 0.2126 * f(p[0]) + 0.7152 * f(p[1]) + 0.0722 * f(p[2]); };
      const onWhite = (e) => (e ? Math.round((1.05 / (lum(getComputedStyle(e).color) + 0.05)) * 100) / 100 : null);
      const card = document.querySelector('main .card'); const main = document.querySelector('main');
      return { cardBg: getComputedStyle(card).backgroundColor, muted: onWhite(document.querySelector('main .muted')), th: onWhite(document.querySelector('main th')), badge: onWhite(document.querySelector('main .badge')), stat: document.querySelector('.stat-v') ? getComputedStyle(document.querySelector('.stat-v')).color : '', pad: getComputedStyle(main).padding, scheme: getComputedStyle(document.documentElement).colorScheme };
    };
    for (const layout of ['enterprise', 'public', 'original']) {
      const ctx = await ctxFor(browser, { ...DESKTOP, colorScheme: 'light' }, layout, { theme: 'dark' });
      const page = await ctx.newPage();
      await page.goto(BASE + '/'); await ready(page); await page.waitForSelector('.cptable'); await page.waitForSelector('.badge');
      const screen = await page.evaluate(PRINTED);
      await page.emulateMedia({ media: 'print' }); await page.waitForTimeout(150);
      const r = await page.evaluate(PRINTED);
      ok(scope, `${layout}（配色=ダーク）: 印刷ではカードが白地、補助の文字・表の見出し・分類バッジが白い紙の上で 4.5:1 以上、本文の余白 0`, /^rgb\(255, 255, 255\)$/.test(r.cardBg) && r.muted >= 4.5 && r.th >= 4.5 && r.badge >= 4.5 && r.pad === '0px' && screen.cardBg !== r.cardBg, JSON.stringify({ 画面: screen.cardBg, 印刷: r }));
      await ctx.close();
    }
    {
      // 主色を選んでいるとき: ダーク用に明るくした色ではなく、選んだ色で刷る
      const ctx = await ctxFor(browser, { ...DESKTOP, colorScheme: 'light' }, 'research', { theme: 'dark', accent: '#5b3fa0' });
      const page = await ctx.newPage(); await page.goto(BASE + '/'); await ready(page); await page.waitForSelector('.cptable');
      const screen = await page.evaluate(PRINTED); await page.emulateMedia({ media: 'print' }); await page.waitForTimeout(150); const r = await page.evaluate(PRINTED);
      ok(scope, 'research（配色=ダーク・主色 #5b3fa0）: 画面では明るく調整した色、印刷では選んだ色そのもの', screen.stat !== 'rgb(91, 63, 160)' && r.stat === 'rgb(91, 63, 160)', JSON.stringify({ 画面: screen.stat, 印刷: r.stat }));
      await ctx.close();
    }
  }

  // ---------- CR-08: Original の「アイコンのみ」 ----------
  {
    const ctx = await ctxFor(browser, DESKTOP, 'original', { sidebarMode: 'icons' });
    const page = await ctx.newPage(); await page.goto(BASE + '/'); await ready(page);
    const r = await page.evaluate(() => [...document.querySelectorAll('.side nav a')].map((a) => { const b = a.getBoundingClientRect(), i = a.querySelector('i').getBoundingClientRect(); return { off: Math.round(((i.left + i.width / 2) - (b.left + b.width / 2)) * 10) / 10, title: a.getAttribute('title') || '' }; }));
    ok('CR-08 Original のアイコンのみ', 'アイコンがリンクの中央にあり（ずれ 0.6px 以内）、項目名がツールチップで出る', r.length === 10 && r.every((x) => Math.abs(x.off) <= 0.6 && x.title.length > 1), JSON.stringify(r.slice(0, 3)));
    await ctx.close();
    const c2 = await ctxFor(browser, DESKTOP, 'original');
    const p2 = await c2.newPage(); await p2.goto(BASE + '/'); await ready(p2);
    ok('CR-08 Original のアイコンのみ', '既定（展開）の Original には title を付けない（改修前と同じ DOM）', (await p2.locator('.side nav a[title]').count()) === 0);
    await c2.close();
  }

  // ---------- CR-09: 起動時、本体の JS が動く前に保存済みの配色・レイアウトを反映する ----------
  {
    const scope = 'CR-09 起動時の配色';
    const res = await fetch(BASE + '/ui-init.js'); const html = await (await fetch(BASE + '/index.html')).text(); const sw = await (await fetch(BASE + '/sw.js')).text();
    const iScript = html.indexOf('ui-init.js'), iCss = html.indexOf('rel="stylesheet"'), iMod = html.indexOf('type="module"');
    ok(scope, 'ui-init.js が配信され、index.html で CSS と本体の JS より前に読み込み、Service Worker の事前キャッシュ一覧に入っている', res.status === 200 && /javascript/.test(res.headers.get('content-type') || '') && iScript > 0 && (iCss < 0 || iScript < iCss) && iScript < iMod && /["']ui-init\.js["']/.test(sw), JSON.stringify({ status: res.status, iScript, iCss, iMod, sw: /ui-init\.js/.test(sw) }));
    // 本体の JS の応答を止めておき、その間の <html> と背景を読む
    const boot = async (value, scheme) => {
      const ctx = await browser.newContext({ ...DESKTOP, colorScheme: scheme, serviceWorkers: 'block' });
      if (value !== null) await ctx.addInitScript(([k, v]) => localStorage.setItem(k, v), [KEY, value]);
      let release; const gate = new Promise((r) => { release = r; });
      await ctx.route(/\/assets\/.*\.js(\?.*)?$/, async (route) => { await gate; await route.continue(); });
      const page = await ctx.newPage(); const errors = []; page.on('pageerror', (e) => errors.push(e.message));
      await page.goto(BASE + '/', { waitUntil: 'commit' });
      await page.waitForFunction(() => document.body && [...document.styleSheets].some((s) => { try { return s.cssRules.length > 50; } catch { return false; } }), null, { timeout: 15000 });
      const before = await page.evaluate(() => ({ ui: document.documentElement.getAttribute('data-ui'), theme: document.documentElement.getAttribute('data-theme'), bg: getComputedStyle(document.body).backgroundColor, mounted: document.getElementById('root').childElementCount }));
      release(); await ready(page);
      const after = await page.evaluate(() => ({ ui: document.documentElement.getAttribute('data-ui'), theme: document.documentElement.getAttribute('data-theme'), bg: getComputedStyle(document.body).backgroundColor }));
      await ctx.close();
      return { before, after, errors };
    };
    const d = await boot(prefs('enterprise', { theme: 'dark' }), 'light');
    ok(scope, 'Enterprise＋配色ダーク（端末はライト）: 本体の JS が動く前から data-ui / data-theme が付き、背景がダークの色', d.before.mounted === 0 && d.before.ui === 'enterprise' && d.before.theme === 'dark' && d.before.bg === d.after.bg && d.after.bg === 'rgb(15, 18, 23)' && d.errors.length === 0, JSON.stringify(d));
    const l = await boot(prefs('original', { theme: 'light' }), 'dark');
    ok(scope, 'Original＋配色ライト（端末はダーク）: JS が動く前から明るい背景', l.before.mounted === 0 && l.before.theme === 'light' && l.before.bg === 'rgb(244, 246, 245)' && l.before.bg === l.after.bg && l.errors.length === 0, JSON.stringify(l));
    const n = await boot(null, 'light');
    ok(scope, '保存値なし（既定）: JS が動く前の <html> には何も付けない', n.before.mounted === 0 && n.before.ui === null && n.before.theme === null && n.after.ui === 'original' && n.errors.length === 0, JSON.stringify(n));
    const bad = [];
    for (const v of ['{壊れた', 'null', '[]', '{"version":1}', '{"version":1,"applied":"x"}', '{"version":1,"applied":{"layout":"deleted-layout","custom":{"theme":"neon"}}}', '{"version":1,"applied":{"layout":{"a":1},"custom":null}}']) {
      const r = await boot(v, 'light');
      if (r.errors.length || r.before.ui !== null || r.before.theme !== null || r.after.ui !== 'original') bad.push(`${v} → ${JSON.stringify(r)}`);
    }
    ok(scope, '壊れた・未知の保存値 7 通り: 例外で止まらず、何も付けずに Original で起動する', bad.length === 0, bad.slice(0, 2).join(' | '));
  }

  // ---------- CR-10: 使っていない属性を付けない ----------
  {
    const ctx = await ctxFor(browser, DESKTOP, 'public', { fontScale: 1.15 });
    const page = await ctx.newPage(); await page.goto(BASE + '/'); await ready(page);
    const r = await page.evaluate(() => ({ attrs: document.documentElement.getAttributeNames().filter((a) => a.startsWith('data-')), scale: document.documentElement.style.getPropertyValue('--u-fs-scale'), fs: getComputedStyle(document.documentElement).fontSize }));
    ok('CR-10 整理', '文字の大きさを変えても、どこからも参照されない data-fs 属性を付けない（倍率は CSS 変数で効く）', !r.attrs.includes('data-fs') && r.scale === '1.15' && Math.abs(parseFloat(r.fs) - 16 * 1.15) < 0.1, JSON.stringify(r));
    await ctx.close();
  }
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
  if (want('a11y')) await a11yChecks(browser);
  if (want('select')) await selectAppearance(browser);
  if (want('cr')) await codeReviewChecks(browser);
  await browser.close();
  if (want('worker')) await workerRoutes();
  const pass = results.filter((r) => r.pass).length;
  if (OUT) fs.writeFileSync(path.join(OUT, 'final-checks.json'), JSON.stringify({ base: BASE, engine: ENGINE, at: new Date().toISOString(), seconds: Math.round((Date.now() - t0) / 1000), pass, total: results.length, results }, null, 1));
  console.log(`\n${pass}/${results.length} passed`);
  process.exit(pass === results.length ? 0 : 1);
})().catch((e) => { console.error(e); process.exit(2); });
