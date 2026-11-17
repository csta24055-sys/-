"""Round 14 (the screens): a toast that carries the server's warnings is laid out across the width, never runs off a
phone's screen (its words scroll inside it) and stays until 閉じる; a warning about another project is said with that
project's name and never joined to a 保存して戻る of the project shown; 保存して戻る's late reads (and a late 開く) never
replace the project the user has opened meanwhile; a stopped 保存して戻る names a row its own action changed by what is
stored, also when the action answers after the stop; a server that cannot be reached during use is said in Japanese
everywhere; a tap on the door while the app is still starting opens it once it has started.

Attacks on those fixes: a tap after the stop (開く B, ←) keeps the rows the stopping press took, and the acted row is
named by its state also when another project is open by then; a row put back or emptied after its own 保存 is named once;
a stop's words stay when the user goes back to their project, and name it while another project is shown; a 削除 answered
after the user went back to that project's hub goes home; an unreachable server is said once for a row's 保存.

The flows are run in a real browser (Playwright for node, against a server started on a free port with a temporary
var directory) when node and Playwright are installed; the functions are also checked one by one with node.

Run: cd whole-life-carbon-jcat-study/23_WLC_STUDIO_APP && python3 -B -m unittest discover -s tests -t .
"""
from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
WEB = HERE / "web"


def node(script: str, arg: str | None = None, timeout: int = 60):
    """Run `script` with node (process.argv[1] is `arg`, by default app.js's path); the parsed JSON it prints, or None
    without node."""
    try:
        proc = subprocess.run(["node", "-e", script, arg or str(WEB / "app.js")], capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        raise AssertionError(proc.stderr)
    return json.loads(proc.stdout)


# the functions under test are taken out of app.js as they are written there
TAKE = r"""
const src = require('fs').readFileSync(process.argv[1], 'utf8');
const take = (re) => { const m = src.match(re); if (!m) throw new Error('not found: ' + re); return m[0]; };
"""

# the flows of the findings, each in a fresh phone-size page; prints {flow: result}
FLOWS = r"""
const { chromium, devices } = require('playwright');
const BASE = process.argv[1];
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
// the server's own sentences (three 適用外 made unusable at once): the longest warnings a save can carry
const LONG = [
  '「解体後の処理（シナリオ）」の「適用外」は、いまの入力では使えない（解体時の質量が分かる材料の行があり、解体後の段階が評価範囲にあるので、処理シナリオが要る。材料の行が無いとき、質量の分かる行が無いとき、解体後の段階（C2〜C4・B4・B5）を評価範囲から外したときは適用外にできる）。計算は止まる。値を入れるか「未取得」に戻す',
  '「運用時の電力の排出係数」の「適用外」は、いまの入力では使えない（購入電力があるので、電力の B6・B2 に係数が要る。購入電力が 0・適用外のときや、B6・B2 を評価範囲から外したときは適用外にできる）。計算は止まる。値を入れるか「未取得」に戻す',
  '「工事中の電力の排出係数」の「適用外」は、いまの入力では使えない（工事中の電力があるので、A5 の電力の分に係数が要る。工事中の電力が 0・適用外のときや、A5 を評価範囲から外したときは適用外にできる）。計算は止まる。値を入れるか「未取得」に戻す'];
async function page0(browser, vp) {
  const ctx = await browser.newContext({ ...devices['iPhone 13'], ...(vp ? { viewport: vp } : {}), deviceScaleFactor: 1, reducedMotion: 'reduce', serviceWorkers: 'block' });
  const page = await ctx.newPage();
  page.setDefaultTimeout(60000);                                       // a slow, busy machine
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  page.on('dialog', (d) => d.accept());
  await page.addInitScript(() => {
    window.__toasts = [];
    document.addEventListener('DOMContentLoaded', () => {
      const t = document.getElementById('toast');
      new MutationObserver(() => { if (t.textContent && window.__toasts[window.__toasts.length - 1] !== t.textContent) window.__toasts.push(t.textContent); })
        .observe(t, { childList: true, characterData: true, subtree: true });
    });
  });
  return { ctx, page, errors };
}
// the app at home (the door opened once the app has started)
async function home(browser, vp) {
  const { ctx, page, errors } = await page0(browser, vp);
  await page.goto(BASE + '/');
  await page.waitForFunction(() => typeof state !== 'undefined' && !!state.meta && !!document.getElementById('splash').onclick);
  await page.click('#splash');
  await page.waitForSelector('#main:not([hidden]) #demo');
  return { ctx, page, errors };
}
async function open(browser, vp) {
  const { ctx, page, errors } = await home(browser, vp);
  await page.click('#demo');
  await page.waitForFunction(() => state.view === 'hub' && !!document.querySelector('[data-screen]'));
  return { ctx, page, errors, pid: await page.evaluate(() => state.project.id) };
}
const api = (page, method, path, body) => page.evaluate(async ([method, path, body]) => {
  const r = await fetch('/api' + path, { method, headers: { 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : undefined });
  return { status: r.status, body: await r.json() };
}, [method, path, body]);
const newProject = async (page, name) => (await api(page, 'POST', '/projects', { structure: 'RC', name })).body.id;
const put = (page, pid, fid, body) => api(page, 'PUT', `/projects/${pid}/fields/${fid}`, body);
const openP = (page, pid) => page.evaluate((pid) => openProject(pid), pid).then(() => page.waitForFunction((pid) => state.view === 'hub' && state.project.id === pid, pid));
const screen = (page, sid) => page.click(`[data-screen="${sid}"]`).then(() => page.waitForFunction((s) => state.view === 'screen' && state.arg === s && !!document.querySelector('#bb-hub'), sid));
const hold = (page, method, re, ms) => page.route((u) => re.test(u.pathname), async (route) => {
  if (route.request().method() !== method) return route.continue();
  await sleep(ms); return route.continue();
});
const stored = (page, pid, fid) => page.evaluate(async ([pid, fid]) => {
  const f = (await (await fetch('/api/projects/' + pid)).json()).fields[fid] || {};
  return { state: f.value ? f.value.state : null, value: f.value ? f.value.value : null, hist: (f.history || []).map((h) => [h.state, h.value]) };
}, [pid, fid]);
const toasts = (page) => page.evaluate(() => window.__toasts.splice(0));
const toastNow = (page) => page.evaluate(() => { const t = document.getElementById('toast'); return t.classList.contains('show') ? t.textContent : ''; });
const answered = (page) => page.waitForFunction(() => state.pending.size === 0 && !state.busy, null, { timeout: 30000 }).then(() => page.waitForTimeout(150));
const retype = async (page, fid, text) => { await page.click('#in-' + fid); await page.keyboard.press('Control+A'); await page.keyboard.type(text); };
const where = (page) => page.evaluate(() => ({ view: state.view, name: state.project && state.project.name, title: document.getElementById('title').textContent }));
const closeWarn = async (page) => { if (await page.isVisible('#toast-close')) await page.click('#toast-close'); };
// the toast's box, the bottom bar's top, 閉じる, and whether the page scrolls sideways
const box = (page) => page.evaluate(() => {
  const t = document.getElementById('toast'), r = t.getBoundingClientRect(), bb = document.querySelector('.bottombar');
  const c = document.getElementById('toast-close'), body = document.getElementById('toast-body');
  return { shown: t.classList.contains('show'), role: t.getAttribute('role'), top: r.top, bottom: r.bottom, left: r.left, right: r.right, w: r.width,
    h: r.height, iw: innerWidth, ih: innerHeight, bbTop: bb ? bb.getBoundingClientRect().top : innerHeight,
    sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth, len: t.textContent.length,
    close: c ? { visible: !c.hidden && c.getBoundingClientRect().height > 0, label: c.getAttribute('aria-label'), tag: c.tagName, tab: c.tabIndex,
      bottom: c.getBoundingClientRect().bottom } : null,
    scrolls: body ? body.scrollHeight > body.clientHeight : null, taps: getComputedStyle(t).pointerEvents };
});
const F = {};

// ui-flows#0: a save whose answer carries 1, 2 and 3 long warnings (added to the server's answer), at 390 and 320 px
const fit = async (b, vp) => {
  const { page, errors } = await open(b, vp);
  const cfg = { n: 0 };
  await page.route((u) => /\/fields\/o_gas_m3$/.test(u.pathname), async (route) => {
    if (route.request().method() !== 'PUT') return route.continue();
    const res = await route.fetch(), j = await res.json();
    if (res.ok() && cfg.n) j.warnings = LONG.slice(0, cfg.n);
    return route.fulfill({ response: res, body: JSON.stringify(j), contentType: 'application/json' });
  });
  await screen(page, 'operation');
  const out = { boxes: [] };
  for (const n of [1, 2, 3]) {
    cfg.n = n;
    await retype(page, 'o_gas_m3', String(100 + n));
    await page.click('[data-save="o_gas_m3"]');
    await answered(page);
    await page.waitForSelector('#toast-close', { state: 'visible', timeout: 15000 });
    out.boxes.push(await box(page));
    if (n === 3) { await page.waitForTimeout(7500); out.later = await box(page); }
    if (n === 2) { await page.focus('#toast-close'); await page.keyboard.press('Escape'); } else await page.click('#toast-close');
    out['closed' + n] = await page.evaluate(() => ({ shown: document.getElementById('toast').classList.contains('show'),
      focusInToast: document.getElementById('toast').contains(document.activeElement) }));
  }
  // an ordinary message keeps its timer and lets taps through
  cfg.n = 0;
  await page.click('[data-save="o_gas_m3"]');
  await page.waitForFunction(() => document.getElementById('toast').classList.contains('show'));
  out.plain = await box(page);
  await page.waitForFunction(() => !document.getElementById('toast').classList.contains('show'), null, { timeout: 10000 });
  out.plainGone = true;
  return { ...out, errors };
};
F.fit390 = (b) => fit(b, null);
F.fit320 = (b) => fit(b, { width: 320, height: 568 });
// the toast's own rules, run in the page: a warning stays; a later action's message is shown above it and goes after its
// time, the warning stays; 閉じる removes both
F.toastRules = async (b) => {
  const { page, errors } = await open(b);
  const r = {};
  await page.evaluate(() => { toast('保存しました', 901); toast('警告X', 901, true); });
  r.first = await page.evaluate(() => [document.getElementById('toast-text').textContent, document.getElementById('toast-kept').hidden]);
  await page.evaluate(() => toast('変更はありません', 902));
  r.second = await page.evaluate(() => [document.getElementById('toast-text').textContent, document.getElementById('toast-kept').textContent]);
  await page.waitForTimeout(3600);
  r.third = await page.evaluate(() => [document.getElementById('toast').classList.contains('show'), document.getElementById('toast-text').textContent,
    document.getElementById('toast-kept').textContent]);
  await page.click('#toast-close');
  r.closed = await page.evaluate(() => document.getElementById('toast').classList.contains('show'));
  return { ...r, errors };
};

// ui-flows#2: project A's save answers late (A's 適用外 becomes unusable) while the user has opened project B and runs
// B's 保存して戻る (held so that A's answer comes while it runs); variant: only B's hub is open
const wrongProject = async (b, batch) => {
  const { page, errors } = await home(b);
  const pA = await newProject(page, 'A社ビル'), pB = await newProject(page, 'B社ビル');
  await put(page, pA, 'o_elec_kwh', { value: 0, unit: 'kWh/年', state: 'confirmed', method: 'user_entered' });
  await put(page, pA, 'o_grid_value', { value: null, state: 'not_applicable', method: 'user_entered' });
  await openP(page, pA); await screen(page, 'operation');
  await hold(page, 'PUT', new RegExp('projects/' + pA + '/fields/o_elec_kwh$'), 3000);
  await retype(page, 'o_elec_kwh', '1000'); await page.click('[data-save="o_elec_kwh"]');
  await page.waitForTimeout(100);
  await page.click('#btn-settings'); await page.waitForFunction(() => state.view === 'settings' && !!document.querySelector('[data-open]'));
  await page.click(`[data-open="${pB}"]`); await page.waitForFunction((pB) => state.view === 'hub' && state.project.id === pB, pB);
  if (batch) {
    await screen(page, 'basic');
    await hold(page, 'PUT', new RegExp('projects/' + pB + '/fields/b_floors_above$'), 2500);
    await retype(page, 'b_floors_above', '4');
    await page.click('#bb-hub');
  }
  await page.waitForFunction(() => /A社ビル/.test(document.getElementById('toast').textContent) && !state.busy, null, { timeout: 15000 });
  await page.waitForTimeout(300);
  return { where: await where(page), t: await toasts(page), now: await toastNow(page), a: await stored(page, pA, 'o_elec_kwh'),
    bGrid: await stored(page, pB, 'o_grid_value'), errors };
};
F.wrongProjectBatch = (b) => wrongProject(b, true);
F.wrongProjectHub = (b) => wrongProject(b, false);
// a warning said on its own project stays (until 閉じる) while the user goes to 設定, opens project B, and A again: it
// names A whenever A is not shown
F.warnStaysNamed = async (b) => {
  const { page, errors } = await home(b);
  const pA = await newProject(page, 'A社ビル'), pB = await newProject(page, 'B社ビル');
  await put(page, pA, 'o_elec_kwh', { value: 0, unit: 'kWh/年', state: 'confirmed', method: 'user_entered' });
  await put(page, pA, 'o_grid_value', { value: null, state: 'not_applicable', method: 'user_entered' });
  await openP(page, pA); await screen(page, 'operation');
  await retype(page, 'o_elec_kwh', '1000'); await page.click('[data-save="o_elec_kwh"]'); await answered(page);
  const r = { onA: await toastNow(page) };
  await page.click('#btn-settings'); await page.waitForFunction(() => state.view === 'settings' && !!document.querySelector('[data-open]'));
  r.onSettings = await toastNow(page);
  await page.click(`[data-open="${pB}"]`); await page.waitForFunction((pB) => state.view === 'hub' && state.project.id === pB, pB);
  r.onB = await toastNow(page);
  await page.click('#btn-settings'); await page.waitForFunction(() => state.view === 'settings' && !!document.querySelector('[data-open]'));
  await page.click(`[data-open="${pA}"]`); await page.waitForFunction((pA) => state.view === 'hub' && state.project.id === pA, pA);
  r.onAagain = await toastNow(page);
  return { ...r, errors };
};

// ui-flows#3: 保存して戻る's read of project A answers late; the user stops it and opens project B meanwhile; then edits
const loadRace = async (b) => {
  const { page, errors } = await home(b);
  const pA = await newProject(page, 'ProjA'), pB = await newProject(page, 'ProjB');
  await openP(page, pA); await screen(page, 'basic');
  let slow = false;
  await page.route((u) => u.pathname === '/api/projects/' + pA, async (route) => {
    if (slow && route.request().method() === 'GET') await sleep(3000);
    return route.continue();
  });
  await retype(page, 'b_floors_above', '5');
  slow = true;
  await page.click('#bb-hub');
  await page.waitForTimeout(300);
  await page.click('#btn-settings'); await page.waitForTimeout(500); await page.click('#btn-settings');
  await page.waitForFunction(() => state.view === 'settings' && !!document.querySelector('[data-open]'));
  slow = false;
  await page.click(`[data-open="${pB}"]`); await page.waitForFunction((pB) => state.view === 'hub' && state.project.id === pB, pB);
  await page.waitForFunction(() => !state.busy, null, { timeout: 15000 }); await page.waitForTimeout(800);
  const after = await where(page);
  await screen(page, 'basic');
  await retype(page, 'b_height', '31'); await page.click('[data-save="b_height"]'); await answered(page);
  return { after, a: await stored(page, pA, 'b_height'), b: await stored(page, pB, 'b_height'), aFloors: await stored(page, pA, 'b_floors_above'), errors };
};
F.loadRace = loadRace;
// a 開く answered late: a later 開く, or a move elsewhere, wins
F.openLate = async (b) => {
  const { page, errors } = await home(b);
  const pA = await newProject(page, 'LateA'), pB = await newProject(page, 'LateB');
  await page.evaluate(() => render());
  await page.waitForSelector(`[data-open="${pB}"]`);
  await hold(page, 'GET', new RegExp('^/api/projects/' + pA + '$'), 1500);
  await page.click(`[data-open="${pA}"]`); await page.waitForTimeout(100);
  await page.click(`[data-open="${pB}"]`);
  await page.waitForTimeout(2500);
  const twoOpens = await where(page);
  await page.click('#btn-back'); await page.waitForFunction(() => state.view === 'home' && !!document.querySelector('#start'));
  await page.click(`[data-open="${pA}"]`); await page.waitForTimeout(100);
  await page.click('#start');
  await page.waitForTimeout(2500);
  return { twoOpens, moved: await where(page), errors };
};

// ui-flows#4: 建物の高さ stored as 50; 77 typed in it and 5 in 地上階数; 未取得に戻す (answered after 1.5 s); 保存して戻る;
// the user stops it (⚙ twice) before the action answers. Variant: 55 typed into 建物の高さ after 未取得に戻す was sent
const stopBefore = async (b, retyped) => {
  const { page, errors } = await home(b);
  const p = await newProject(page, 'Stop');
  await put(page, p, 'b_height', { value: 50, unit: 'm', state: 'confirmed', method: 'user_entered' });
  await openP(page, p); await screen(page, 'basic');
  await hold(page, 'PUT', /fields\/b_height$/, 1500);
  await retype(page, 'b_height', '77'); await retype(page, 'b_floors_above', '5');
  await page.click('[data-unset="b_height"]');
  await page.waitForTimeout(100);
  if (retyped) await retype(page, 'b_height', '55');
  await toasts(page);
  await page.click('#bb-hub');
  await page.waitForTimeout(100);
  await page.click('#btn-settings'); await page.waitForTimeout(500); await page.click('#btn-settings');
  await page.waitForFunction(() => !state.busy, null, { timeout: 15000 }); await page.waitForTimeout(500);
  return { t: await toasts(page), height: await stored(page, p, 'b_height'), floors: await stored(page, p, 'b_floors_above'), errors };
};
F.stopBefore = (b) => stopBefore(b, false);
F.stopBeforeRetyped = (b) => stopBefore(b, true);

// ui-flows#6: the server cannot be reached during use (every request fails as offline): a row's 保存, 保存して戻る, ← ←
F.offlineInUse = async (b) => {
  const { page, errors } = await open(b);
  await screen(page, 'operation');
  await page.route('**/api/**', (route) => route.abort('internetdisconnected'));
  await toasts(page);
  await retype(page, 'o_gas_m3', '5'); await page.click('[data-save="o_gas_m3"]'); await page.waitForTimeout(800);
  await page.click('#bb-hub'); await page.waitForTimeout(800);
  await page.click('#btn-back'); await page.waitForTimeout(500); await page.click('#btn-back'); await page.waitForTimeout(800);
  return { t: await toasts(page), view: await page.evaluate(() => state.view), main: await page.locator('#main').innerText(),
    sw: await page.evaluate(() => document.documentElement.scrollWidth), errors };
};

// ui-flows#8: the door tapped while /api/meta is on its way (1.5 s); variant: /api/meta then fails
const door = async (b, fail) => {
  const { ctx, page, errors } = await page0(b);
  await page.route('**/api/meta', async (route) => { await sleep(1500); return fail ? route.abort('internetdisconnected') : route.continue(); });
  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' });
  await page.click('#splash');
  const early = await page.evaluate(() => ({ sub: (document.querySelector('.splash-sub') || {}).textContent, busy: document.getElementById('splash').getAttribute('aria-busy') }));
  await page.waitForTimeout(3500);
  const r = await page.evaluate(() => ({ splashHidden: document.getElementById('splash').hidden, mainHidden: document.getElementById('main').hidden,
    bootError: !!document.querySelector('.boot-error'), body: document.body.innerText }));
  return { early, ...r, errors: errors.filter((e) => !/Failed to fetch/.test(e)) };
};
F.doorEarly = (b) => door(b, false);
F.doorEarlyFails = (b) => door(b, true);

// attack on ui-flows#4: the same stop (未取得に戻す answered after 3 s, ⚙ twice), then one more tap before the answer:
// 開く B in settings, or ← from settings (back to the screen)
const stopThenMove = async (b, mode) => {
  const { page, errors } = await home(b);
  const p = await newProject(page, 'MoveA'), pB = await newProject(page, 'MoveB');
  await put(page, p, 'b_height', { value: 50, unit: 'm', state: 'confirmed', method: 'user_entered' });
  await openP(page, p); await screen(page, 'basic');
  await hold(page, 'PUT', /fields\/b_height$/, 3000);
  await retype(page, 'b_height', '77'); await retype(page, 'b_floors_above', '5');
  await page.click('[data-unset="b_height"]');
  await page.waitForTimeout(100);
  await toasts(page);
  await page.click('#bb-hub');
  await page.waitForTimeout(100);
  await page.click('#btn-settings'); await page.waitForTimeout(500); await page.click('#btn-settings');
  await page.waitForFunction(() => state.view === 'settings' && !!document.querySelector('[data-open]'));
  await page.click(mode === 'openB' ? `[data-open="${pB}"]` : '#btn-back');
  const busyAtTap = await page.evaluate(() => state.busy && state.pending.size > 0);   // the tap came before the answer
  await page.waitForFunction(() => !state.busy, null, { timeout: 15000 }); await page.waitForTimeout(500);
  return { busyAtTap, t: await toasts(page), where: await where(page), height: await stored(page, p, 'b_height'),
    floors: await stored(page, p, 'b_floors_above'), errors };
};
F.stopThenOpen = (b) => stopThenMove(b, 'openB');
F.stopThenBack = (b) => stopThenMove(b, 'back');

// attack: 建物の高さ stored as 50; 77 typed and its own 保存 (answered after 2.5 s); 保存して戻る; while it waits the row is put
// back to 50 (or emptied); the user stops (⚙ twice) before the answer
const revertStop = async (b, mode) => {
  const { page, errors } = await home(b);
  const p = await newProject(page, 'Rev' + mode);
  await put(page, p, 'b_height', { value: 50, unit: 'm', state: 'confirmed', method: 'user_entered' });
  await openP(page, p); await screen(page, 'basic');
  await hold(page, 'PUT', /fields\/b_height$/, 2500);
  await retype(page, 'b_height', '77');
  await page.click('[data-save="b_height"]');
  await page.waitForTimeout(100);
  await page.click('#bb-hub');
  await page.waitForTimeout(150);
  if (mode === 'revert') await retype(page, 'b_height', '50');
  else { await page.click('#in-b_height'); await page.keyboard.press('Control+A'); await page.keyboard.press('Delete'); }
  await toasts(page);
  await page.click('#btn-settings'); await page.waitForTimeout(500); await page.click('#btn-settings');
  const busyAtStop = await page.evaluate(() => state.busy && state.pending.size > 0);
  await page.waitForFunction(() => !state.busy, null, { timeout: 15000 }); await page.waitForTimeout(500);
  return { busyAtStop, t: await toasts(page), height: await stored(page, p, 'b_height'), errors };
};
F.revertStop = (b) => revertStop(b, 'revert');
F.emptyStop = (b) => revertStop(b, 'empty');

// attack on ui-flows#2: A社ビル (購入電力 0 and 運用時係数 適用外 stored): 購入電力 1000 and 都市ガス 5 typed, 保存して戻る (the
// 購入電力 PUT, which carries the warning, answers after 1.5 s), stopped with ⚙ twice. 'back': the stop's words are said in
// settings, then ← goes back to A's 運用. 'late': the stop's read answers after 2.5 s, and B社ビル (with its own 都市ガス) is
// opened before the stop's words are said
const stopWarn = async (b, mode) => {
  const { page, errors } = await home(b);
  const pA = await newProject(page, 'A社ビル'), pB = await newProject(page, 'B社ビル');
  await put(page, pA, 'o_elec_kwh', { value: 0, unit: 'kWh/年', state: 'confirmed', method: 'user_entered' });
  await put(page, pA, 'o_grid_value', { value: null, state: 'not_applicable', method: 'user_entered' });
  await put(page, pB, 'o_gas_m3', { value: 9, unit: 'm3/年', state: 'confirmed', method: 'user_entered' });
  await openP(page, pA); await screen(page, 'operation');
  await hold(page, 'PUT', new RegExp('projects/' + pA + '/fields/o_elec_kwh$'), 1500);
  let slowGet = false;
  await page.route((u) => u.pathname === '/api/projects/' + pA, async (route) => {
    if (slowGet && route.request().method() === 'GET') await sleep(2500);
    return route.continue();
  });
  await retype(page, 'o_elec_kwh', '1000'); await retype(page, 'o_gas_m3', '5');
  await page.click('#bb-hub'); await page.waitForTimeout(150);
  if (mode === 'late') slowGet = true;
  await page.click('#btn-settings'); await page.waitForTimeout(500); await page.click('#btn-settings');
  if (mode === 'late') {
    await page.waitForFunction(() => state.view === 'settings' && !!document.querySelector('[data-open]'));
    await page.click(`[data-open="${pB}"]`);
  }
  await page.waitForFunction(() => !state.busy, null, { timeout: 15000 }); await page.waitForTimeout(400);
  const said = { ...(await where(page)), text: await toastNow(page) };
  if (mode === 'back') { await page.click('#btn-back'); await page.waitForFunction(() => state.view === 'screen'); }
  await page.waitForTimeout(1000);
  const later = { ...(await where(page)), text: await toastNow(page) };
  return { said, later, gasA: await stored(page, pA, 'o_gas_m3'), errors };
};
F.stopWarnBack = (b) => stopWarn(b, 'back');
F.stopWarnLate = (b) => stopWarn(b, 'late');

// attack: 削除 in settings answered after 2 s; meanwhile ← goes back to the hub of the project being deleted (DelA), or (the
// other way) another project (DelB) is deleted while DelA's hub is back on screen
F.deleteLate = async (b) => {
  const { page, errors } = await home(b);
  const out = {};
  for (const which of ['open', 'other']) {
    const pA = await newProject(page, 'DelA' + which), pB = await newProject(page, 'DelB' + which);
    await openP(page, pA);
    await page.click('#btn-settings'); await page.waitForSelector(`[data-del="${pA}"]`);
    const del = which === 'open' ? pA : pB;
    await hold(page, 'DELETE', new RegExp('^/api/projects/' + del + '$'), 2000);
    await page.click(`[data-del="${del}"]`); await page.waitForTimeout(200);
    await page.click('#btn-back'); await page.waitForFunction(() => state.view === 'hub');
    const before = await where(page);
    await page.waitForFunction(() => window.__toasts.includes('削除しました'), null, { timeout: 15000 });
    await page.waitForTimeout(400);
    const after = { ...(await where(page)), project: await page.evaluate(() => !!state.project), start: !!(await page.$('#start')) };
    let next = null;
    if (await page.$('[data-screen="basic"]')) {
      await page.click('[data-screen="basic"]'); await page.waitForTimeout(800);
      next = await page.evaluate(() => ({ view: state.view, main: document.getElementById('main').innerText.slice(0, 80) }));
    }
    out[which] = { before, after, next };
    await toasts(page);
    await page.evaluate(() => { state.stack = []; back(true); });
    await page.waitForFunction(() => state.view === 'home' && !!document.querySelector('#start'));
  }
  return { ...out, errors };
};

(async () => {
  const browser = await chromium.launch();
  const out = {};
  const run = async (k) => {
    const t0 = Date.now();
    try { out[k] = await F[k](browser); } catch (e) { out[k] = { error: String(e.stack || e).slice(0, 2000) }; }
    out[k].ms = Date.now() - t0;
  };
  try {
    // two flows at a time (the server has one worker: more would queue its answers behind each other)
    const rest = Object.keys(F);
    await Promise.all([0, 1].map(async () => { while (rest.length) await run(rest.shift()); }));
  } finally { await browser.close(); }
  console.log(JSON.stringify(out));
})();
"""

_FLOWS = {}


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def flows():
    """The results of FLOWS (run once), or a reason to skip."""
    if "out" in _FLOWS or "skip" in _FLOWS:
        return _FLOWS
    try:
        probe = subprocess.run(["node", "-e", "require('playwright')"], capture_output=True, text=True, timeout=60)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        _FLOWS["skip"] = "node is not installed"
        return _FLOWS
    if probe.returncode != 0:
        _FLOWS["skip"] = "Playwright for node is not installed"
        return _FLOWS
    td = tempfile.TemporaryDirectory()
    port = _free_port()
    env = dict(os.environ, WLCSTUDIO_OFFLINE="1", PYTHONDONTWRITEBYTECODE="1")
    srv = subprocess.Popen([sys.executable, "-B", "-m", "wlcstudio", "--var", td.name, "serve", "--port", str(port)], cwd=str(HERE),
                           env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = "http://127.0.0.1:%d" % port
    try:
        for _ in range(300):
            try:
                with urllib.request.urlopen(base + "/api/meta", timeout=2) as r:
                    if r.status == 200:
                        break
            except OSError:
                time.sleep(0.1)
        else:
            _FLOWS["skip"] = "the server did not start"
            return _FLOWS
        proc = subprocess.run(["node", "-e", FLOWS, base], capture_output=True, text=True, timeout=480)
        if proc.returncode != 0 and "Executable doesn't exist" in proc.stderr:
            _FLOWS["skip"] = "no browser for Playwright"
        elif proc.returncode != 0:
            _FLOWS["out"] = {"error": proc.stderr[-3000:]}
        else:
            _FLOWS["out"] = json.loads(proc.stdout)
    finally:
        srv.terminate()
        try:
            srv.wait(timeout=10)
        except subprocess.TimeoutExpired:
            srv.kill()
        td.cleanup()
    return _FLOWS


WARN_GRID = "「運用時の電力の排出係数」の「適用外」は、いまの入力では使えない"


class FourteenthRoundUiTests(unittest.TestCase):
    """Regression tests for the fourteenth verification round, screens (docs/review_fixes.md, round 14)."""

    @classmethod
    def setUpClass(cls):
        cls.js = (WEB / "app.js").read_text(encoding="utf-8")
        cls.css = (WEB / "style.css").read_text(encoding="utf-8")

    def flow(self, name):
        f = flows()
        if "skip" in f:
            self.skipTest(f["skip"])
        self.assertNotIn("error", f["out"], f["out"].get("error"))
        r = dict(f["out"][name])
        self.assertNotIn("error", r, r.get("error"))
        self.assertEqual(r.pop("errors", []), [], "page errors")
        r.pop("ms", None)
        return r

    # ---- ui-flows#0: a toast with warnings fits the screen and stays until 閉じる ----

    def check_fit(self, r):
        for n, x in enumerate(r["boxes"], 1):
            self.assertTrue(x["shown"], (n, x))
            self.assertGreaterEqual(x["top"], 0, (n, x))                      # never above the screen
            self.assertLessEqual(x["bottom"], x["bbTop"], (n, x))              # never over the bottom bar
            self.assertGreaterEqual(x["left"], 15, (n, x))
            self.assertLessEqual(x["right"], x["iw"] - 15, (n, x))
            self.assertLessEqual(x["sw"], x["cw"], (n, x))                     # no sideways scroll
            self.assertGreater(x["w"], x["iw"] * 0.8, (n, x))                  # laid out across the width (was 195 px)
            self.assertEqual(x["role"], "alert", (n, x))
            self.assertEqual(x["taps"], "auto", (n, x))
            self.assertTrue(x["close"]["visible"], (n, x))
            self.assertEqual((x["close"]["tag"], x["close"]["label"]), ("BUTTON", "閉じる"), (n, x))
            self.assertGreaterEqual(x["close"]["tab"], 0, (n, x))             # focusable
            self.assertLessEqual(x["close"]["bottom"], x["bbTop"], (n, x))     # 閉じる is on screen
        self.assertTrue(r["boxes"][2]["scrolls"], r["boxes"][2])               # three warnings scroll inside the toast
        self.assertGreater(r["boxes"][2]["len"], 400)
        # it stays (it went after 6.6 s before) until 閉じる or Escape
        self.assertTrue(r["later"]["shown"], r["later"])
        for n in (1, 2, 3):
            self.assertFalse(r["closed%d" % n]["shown"], r)
            self.assertFalse(r["closed%d" % n]["focusInToast"], r)
        # an ordinary message: a status that lets taps through and goes after its time
        self.assertEqual((r["plain"]["role"], r["plain"]["taps"], r["plain"]["close"]["visible"]), ("status", "none", False), r["plain"])
        self.assertTrue(r["plainGone"], r)

    def test_warning_toast_fits_390_px_and_stays_until_closed(self):
        self.check_fit(self.flow("fit390"))

    def test_warning_toast_fits_320_px(self):
        self.check_fit(self.flow("fit320"))

    def test_toast_keeps_warnings_under_a_later_message(self):
        r = self.flow("toastRules")
        self.assertEqual(r["first"], ["保存しました ／ 警告X", True], r)
        self.assertEqual(r["second"], ["変更はありません", "前の保存の知らせ：警告X"], r)
        self.assertEqual(r["third"], [True, "", "警告X"], r)              # the later message went, the warning stayed
        self.assertFalse(r["closed"], r)
        self.assertIn("left: 16px; right: 16px;", self.css)
        self.assertNotIn("translateX(-50%)", self.css)
        self.assertIn("max-width: min(560px, 100% - 32px)", self.css)

    # ---- ui-flows#2: a warning about another project is said with its name ----

    def test_warning_of_another_project_is_named_and_not_joined_to_the_batch(self):
        r = self.flow("wrongProjectBatch")
        self.assertEqual(r["where"]["name"], "B社ビル", r)
        self.assertTrue(any("「A社ビル」：" + WARN_GRID in x for x in r["t"]), r["t"])
        self.assertTrue(any("1 項目を保存しました（「地上階数」）" in x for x in r["t"]), r["t"])
        # never joined to B's message as if B's save had said it, and never said without A's name
        self.assertFalse(any("（「地上階数」） ／ " in x for x in r["t"]), r["t"])
        self.assertFalse(any(x.startswith(WARN_GRID) or "／ " + WARN_GRID in x for x in r["t"]), r["t"])
        self.assertEqual(r["a"]["value"], 1000, r)
        self.assertEqual(r["bGrid"]["state"], None, r)
        r = self.flow("wrongProjectHub")
        self.assertEqual(r["where"]["name"], "B社ビル", r)
        self.assertIn("「A社ビル」：" + WARN_GRID, r["now"], r)
        self.assertFalse(r["now"].startswith(WARN_GRID), r)

    def test_warning_kept_on_screen_names_its_project_elsewhere(self):
        r = self.flow("warnStaysNamed")
        self.assertTrue(r["onA"].startswith(WARN_GRID), r)                  # said on its own project as it is
        self.assertTrue(r["onSettings"].startswith("「A社ビル」：" + WARN_GRID), r)
        self.assertTrue(r["onB"].startswith("「A社ビル」：" + WARN_GRID), r)  # never read as one about B
        self.assertTrue(r["onAagain"].startswith(WARN_GRID), r)

    def test_warn_of_names_the_project_of_the_answer(self):
        out = node(TAKE + r"""
var state = { busy: false, warnings: [], batch: null, view: 'hub', project: { id: 2, created_at: 9, name: 'B', fields: {} } };
const said = [];
eval(take(/function projectKey[\s\S]*?\n}\n/));
eval(take(/function shownKey[^\n]*\n/));
eval(take(/const toastText = [^\n]*\n/).replace('const toastText', 'var toastText'));
function toast(msg, act, warn) { said.push([toastText(msg), act, !!warn || typeof msg !== 'string']); }   // as it reads when said
eval(take(/function warnOf[\s\S]*?\n}\n/));
eval(take(/function sayWarning\([^\n]*\n/));
eval(take(/function sayWarnings[^\n]*\n/));
const A = (act) => ({ key: '1@5', act, name: 'A社ビル' }), B = (act) => ({ key: '2@9', act, name: 'B' });
warnOf({ warnings: ['wB'] }, B(1));                                   // the project shown, no batch: said as it is
warnOf({ warnings: ['wA'] }, A(2));                                   // another project: named
state.busy = true; state.batch = { n: 4, key: '2@9' };
warnOf({ warnings: ['wA2'] }, A(3));                                  // another project while B's batch runs: said now, named
warnOf({ warnings: ['wB2'] }, B(4));                                  // the batch's project: kept for its message
const kept = state.warnings.map((x) => x.w);
state.view = 'settings'; sayWarnings(5);                              // said once no project is shown: named
state.busy = false; state.batch = null; state.view = 'home';
warnOf({ warnings: ['wB3'] }, B(6));
console.log(JSON.stringify({ said, kept, left: state.warnings.length }));
""")
        if out is None:
            self.skipTest("node is not installed")
        self.assertEqual(out["kept"], ["wB2"])
        self.assertEqual(out["left"], 0)
        self.assertEqual(out["said"], [["wB", 1, True], ["「A社ビル」：wA", 2, True], ["「A社ビル」：wA2", 3, True], ["「B」：wB2", 5, True],
                                       ["「B」：wB3", 6, True]])

    # ---- ui-flows#3: a late read never replaces the project the user opened ----

    def test_late_read_of_the_batch_does_not_replace_the_project_opened(self):
        r = self.flow("loadRace")
        self.assertEqual(r["after"], {"view": "hub", "name": "ProjB", "title": "ProjB"}, r)
        self.assertEqual(r["b"]["value"], 31, r)                              # an edit made then goes to B
        self.assertEqual(r["a"]["hist"], [], r)
        self.assertEqual(r["aFloors"]["value"], 5, r)                         # A's row was saved before the stop

    def test_late_open_does_not_replace_a_later_choice(self):
        r = self.flow("openLate")
        self.assertEqual(r["twoOpens"]["name"], "LateB", r)
        self.assertEqual(r["twoOpens"]["view"], "hub", r)
        self.assertEqual(r["moved"]["view"], "structures", r)

    # ---- ui-flows#4: a stop names a row its own action changed by what is stored ----

    def test_stop_before_the_action_answers_names_its_stored_state(self):
        r = self.flow("stopBefore")
        self.assertEqual(r["height"]["state"], "not_obtained", r)
        msg = [x for x in r["t"] if x.startswith("保存して戻るを途中でやめました")]
        self.assertEqual(len(msg), 1, r["t"])
        self.assertIn("「建物の高さ」は「未取得」になりました", msg[0])
        self.assertIn("「地上階数」は保存していません", msg[0])
        self.assertNotIn("「建物の高さ」は保存していません", msg[0])
        self.assertEqual(r["floors"]["hist"], [], r)
        # typed into again after its action was sent: what it holds was never sent (named), and its stored state is said
        r = self.flow("stopBeforeRetyped")
        msg = [x for x in r["t"] if x.startswith("保存して戻るを途中でやめました")]
        self.assertEqual(len(msg), 1, r["t"])
        self.assertIn("「建物の高さ」は「未取得」になりました", msg[0])
        self.assertIn("「地上階数」「建物の高さ」は保存していません", msg[0])
        self.assertNotIn(55, [h[1] for h in r["height"]["hist"]], r)

    # ---- ui-flows#6: an unreachable server during use is said in Japanese ----

    def test_unreachable_server_during_use_is_said_in_japanese(self):
        r = self.flow("offlineInUse")
        self.assertTrue(r["t"], r)
        self.assertFalse(any("Failed to fetch" in x for x in r["t"]), r["t"])
        self.assertTrue(any("「都市ガス」：WLC Studio のサーバーに接続できません（サーバーが動いているか確かめてください）" in x for x in r["t"]), r["t"])
        self.assertEqual(r["view"], "home", r)
        self.assertIn("表示できなかった：WLC Studio のサーバーに接続できません", r["main"], r)
        self.assertNotIn("Failed to fetch", r["main"], r)
        self.assertLessEqual(r["sw"], 390, r)

    def test_api_keeps_the_browser_words_as_a_detail(self):
        out = node(TAKE + r"""
eval(take(/async function api[\s\S]*?\n}\n/));
const res = (status, body) => ({ ok: status < 400, status, text: async () => body });
const runs = [
  ['down', () => Promise.reject(new TypeError('Failed to fetch'))],
  ['body cut', () => Promise.resolve({ ok: true, status: 200, text: () => Promise.reject(new TypeError('network error')) })],
  ['refused', () => Promise.resolve(res(400, JSON.stringify({ error: '理由' })))],
  ['500 text', () => Promise.resolve(res(500, 'Internal'))],
  ['ok', () => Promise.resolve(res(200, JSON.stringify({ a: 1 })))]];
(async () => {
  const out = {};
  for (const [k, f] of runs) {
    global.fetch = f;
    try { out[k] = { ok: await api('/x') }; } catch (e) { out[k] = { message: e.message, detail: e.detail ?? null, offline: !!e.offline }; }
  }
  console.log(JSON.stringify(out));
})();
""")
        if out is None:
            self.skipTest("node is not installed")
        jp = "WLC Studio のサーバーに接続できません（サーバーが動いているか確かめてください）"
        self.assertEqual(out["down"], {"message": jp, "detail": "Failed to fetch", "offline": True})
        self.assertEqual(out["body cut"], {"message": jp, "detail": "network error", "offline": True})
        self.assertEqual(out["refused"], {"message": "理由", "detail": None, "offline": False})
        # an answer that is not JSON is never shown as it is (round 16): said with its status, its start kept as a detail
        self.assertEqual(out["500 text"], {"message": "サーバーから読めない答え（HTTP 500）", "detail": "Internal", "offline": False})
        self.assertEqual(out["ok"], {"ok": {"a": 1}})

    # ---- ui-flows#8: a tap on the door while the app starts is kept ----

    def test_door_tapped_while_starting_opens_once_started(self):
        r = self.flow("doorEarly")
        self.assertEqual(r["early"], {"sub": "読み込み中…", "busy": "true"}, r)
        self.assertTrue(r["splashHidden"], r)
        self.assertFalse(r["mainHidden"], r)
        r = self.flow("doorEarlyFails")
        self.assertEqual(r["early"]["sub"], "読み込み中…", r)
        self.assertTrue(r["bootError"], r)
        self.assertIn("WLC Studio のサーバーに接続できません", r["body"], r)
        self.assertNotIn("読み込み中", r["body"], r)
        self.assertTrue(r["mainHidden"], r)

    # ---- attacks on the fixes above (the second pass of round 14) ----

    def test_a_later_press_keeps_the_rows_the_stopping_press_took(self):
        out = node(TAKE + r"""
var state = { busy: true, busyWarned: 0, act: 0, view: 'screen', cancel: false, cancelRows: null };
function toast() {}
let n = 0;
function rowsNow() { return { snap: ++n, view: state.view }; }
eval(take(/function blocked\(\)[\s\S]*?\n}\n/));
const r = [blocked()];                                                 // the first press warns
state.busyWarned = Date.now() - 600;
r.push(blocked(), state.cancel, JSON.stringify(state.cancelRows));    // the press that stops, on the screen
state.view = 'settings';
r.push(blocked(), JSON.stringify(state.cancelRows));                  // 開く B or ← in settings before the answer
state.view = 'screen';
r.push(blocked(), JSON.stringify(state.cancelRows));                  // a press on the screen drawn again
console.log(JSON.stringify(r));
""")
        if out is None:
            self.skipTest("node is not installed")
        first = '{"snap":1,"view":"screen"}'
        self.assertEqual(out, [True, False, True, first, False, first, False, first])

    def check_stop_names_the_unset_row(self, r):
        self.assertTrue(r["busyAtTap"], r)                                  # the extra tap came before the action's answer
        self.assertEqual(r["height"]["state"], "not_obtained", r)
        msg = [x for x in r["t"] if "保存して戻るを途中でやめました" in x]
        self.assertEqual(len(msg), 1, r["t"])
        self.assertIn("「建物の高さ」は「未取得」になりました", msg[0])
        self.assertIn("「地上階数」は保存していません", msg[0])
        self.assertNotIn("「建物の高さ」は保存していません", msg[0])
        self.assertNotIn("「地上階数」「建物の高さ」", msg[0])
        self.assertEqual(r["floors"]["hist"], [], r)
        return msg[0]

    def test_stop_then_open_another_project_names_the_acted_row_by_its_state(self):
        r = self.flow("stopThenOpen")
        msg = self.check_stop_names_the_unset_row(r)
        self.assertEqual(r["where"]["name"], "MoveB", r)
        # said while MoveB is shown: the words name the project they are about (MoveB has the same rows)
        self.assertTrue(msg.startswith("「MoveA」：保存して戻るを途中でやめました："), msg)

    def test_stop_then_back_names_the_acted_row_by_its_state(self):
        r = self.flow("stopThenBack")
        msg = self.check_stop_names_the_unset_row(r)
        self.assertEqual((r["where"]["view"], r["where"]["name"]), ("screen", "MoveA"), r)
        self.assertTrue(msg.startswith("保存して戻るを途中でやめました："), msg)    # its own project shown: no name

    def test_stop_names_a_row_put_back_after_its_own_save_once(self):
        for name in ("revertStop", "emptyStop"):
            r = self.flow(name)
            self.assertTrue(r["busyAtStop"], (name, r))
            self.assertEqual(r["height"]["value"], 77, (name, r))           # the row's own 保存 stored 77
            msg = [x for x in r["t"] if "保存して戻るを途中でやめました" in x]
            self.assertEqual(len(msg), 1, (name, r["t"]))
            self.assertIn("「建物の高さ」は直す前の値を保存しました（あとで直した値は保存していません）", msg[0])
            # never both saved and not saved
            self.assertNotIn("「建物の高さ」は保存しました", msg[0])
            self.assertNotIn("「建物の高さ」は保存していません", msg[0])

    def test_stop_words_stay_on_their_project_and_name_it_elsewhere(self):
        r = self.flow("stopWarnBack")
        # the rows not saved are named first (round 15: the end of a long message was cut and went after its time)
        words = "保存して戻るを途中でやめました：「都市ガス」は保存していません。「購入電力」は保存しました"
        self.assertEqual(r["said"]["view"], "settings", r)
        self.assertTrue(r["said"]["text"].startswith(words), r)
        self.assertIn("「A社ビル」：" + WARN_GRID, r["said"]["text"])
        # back on A's 運用: the words are about A, and stay with its warning (they went at once before)
        self.assertEqual((r["later"]["view"], r["later"]["name"]), ("screen", "A社ビル"), r)
        self.assertTrue(r["later"]["text"].startswith(words + " ／ " + WARN_GRID), r)
        self.assertEqual(r["gasA"]["hist"], [], r)
        r = self.flow("stopWarnLate")
        # said while B社ビル (which has its own 都市ガス) is shown: the words name A, as its warning does
        self.assertEqual((r["said"]["view"], r["said"]["name"]), ("hub", "B社ビル"), r)
        self.assertTrue(r["said"]["text"].startswith("「A社ビル」：" + words), r)
        self.assertIn("「A社ビル」：" + WARN_GRID, r["said"]["text"])
        self.assertTrue(r["later"]["text"].startswith("「A社ビル」：" + words), r)

    def test_a_late_delete_of_the_project_shown_goes_home(self):
        r = self.flow("deleteLate")
        self.assertEqual(r["open"]["before"]["view"], "hub", r)
        self.assertEqual(r["open"]["after"]["view"], "home", r)              # not a hub of a project that is gone
        self.assertFalse(r["open"]["after"]["project"], r)
        self.assertTrue(r["open"]["after"]["start"], r)
        self.assertIsNone(r["open"]["next"], r)
        # another project deleted: the project shown stays, and works
        self.assertEqual((r["other"]["after"]["view"], r["other"]["after"]["name"]), ("hub", "DelAother"), r)
        self.assertEqual(r["other"]["next"]["view"], "screen", r)
        self.assertNotIn("表示できなかった", r["other"]["next"]["main"], r)

    def test_unreachable_server_is_said_once_for_a_row_save(self):
        r = self.flow("offlineInUse")
        row = [x for x in r["t"] if "「都市ガス」：" in x]
        self.assertTrue(row, r["t"])
        for x in row:                                                       # the reload after the refusal is not said again
            self.assertEqual(x.count("WLC Studio のサーバーに接続できません"), 1, x)

    def test_service_worker_cache_is_new(self):
        sw = (WEB / "sw.js").read_text(encoding="utf-8")
        m = re.search(r'"wlcstudio-shell-v(\d+)"', sw)                     # v13 or later (a later round bumps it again)
        self.assertTrue(m, sw)
        self.assertGreaterEqual(int(m.group(1)), 13)
        self.assertNotIn('"wlcstudio-shell-v12"', sw)


if __name__ == "__main__":
    unittest.main()
