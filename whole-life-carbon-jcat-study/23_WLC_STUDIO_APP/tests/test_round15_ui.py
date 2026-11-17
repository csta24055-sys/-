"""Round 15 (the screens): a warning that a stored 適用外 cannot be used is not said once the same 保存して戻る has given
that field another state (the server says which field each warning is about: warning_fields), and a warning kept on
screen goes when the user gives the field a value or 未取得; a project made by 架空デモを開く or a structure card is not
opened over a project the user opened meanwhile (it is said where to find it), and its late answer is never taken for a
press during 保存して戻る; a refused or failed この候補を採用 keeps what was typed in its row (保存して戻る saves it, its
stop names it); words too long for the toast, and the words of 保存して戻る that name rows not saved, stay until 閉じる
and can be scrolled (the rows not saved are named first); a failed read of the stored result is said on the result
screen; a toast that stays is not written again (said again) at every view.

The fix-up of those fixes (an attack on them): words once too long for the toast stay with 閉じる on a later view where
they fit (they were left with neither 閉じる nor a timer); a late answer is said after the words that name rows not saved,
it does not replace them; the late answer of an earlier save of a field (stored before the warning's write: the answers'
updated_at) does not take back a warning about its 適用外; words that name rows not saved stay, named, on another
project's view also when a warning was said with them.

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
os.environ.setdefault("WLCSTUDIO_OFFLINE", "1")
HERE = Path(__file__).resolve().parents[1]
WEB = HERE / "web"
sys.path.insert(0, str(HERE))

from wlcstudio import fields as FL  # noqa: E402
from wlcstudio.provenance import Value  # noqa: E402
from wlcstudio.server import App  # noqa: E402


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
  return { state: f.value ? f.value.state : null, value: f.value ? f.value.value : null, method: f.value ? f.value.method : null };
}, [pid, fid]);
const toasts = (page) => page.evaluate(() => window.__toasts.splice(0));
const answered = (page) => page.waitForFunction(() => state.pending.size === 0 && !state.busy, null, { timeout: 30000 }).then(() => page.waitForTimeout(300));
const retype = async (page, fid, text) => { await page.click('#in-' + fid); await page.keyboard.press('Control+A'); await page.keyboard.type(text); };
const where = (page) => page.evaluate(() => ({ view: state.view, arg: state.arg || null, name: state.project && state.project.name }));
const value = (page, fid) => page.evaluate((f) => { const e = document.getElementById('in-' + f); return e ? e.value : null; }, fid);
// the toast now: shown, sticky, its role, 閉じる, whether its words scroll, whether it takes taps, and the page's width
const box = (page) => page.evaluate(() => {
  const t = document.getElementById('toast'), b = document.getElementById('toast-body'), r = t.getBoundingClientRect();
  const shown = t.classList.contains('show');                          // the words of a toast shown (a closed one keeps its old text)
  return { shown, sticky: t.classList.contains('sticky'), role: t.getAttribute('role'),
    close: !document.getElementById('toast-close').hidden, taps: getComputedStyle(t).pointerEvents, text: shown ? document.getElementById('toast-text').textContent : '',
    kept: !shown || document.getElementById('toast-kept').hidden ? '' : document.getElementById('toast-kept').textContent,
    all: shown ? t.textContent : '', scrolls: b.scrollHeight > b.clientHeight, top: r.top, bottom: r.bottom, ih: innerHeight,
    sw: document.documentElement.scrollWidth, iw: innerWidth };
});
const F = {};

// sweep#0: 購入電力 0 and 運用時係数 適用外 stored; one 保存して戻る gives the purchase 1000 AND the factor 0.45 (its first PUT
// answers with the warning, the second gives the factor a value). Control: the purchase alone (the warning holds)
const WARN_GRID = '「運用時の電力の排出係数」の「適用外」は、いまの入力では使えない';
const WARN_ROUTE = '「解体後の処理（シナリオ）」の「適用外」は、いまの入力では使えない';
F.staleBatch = async (b) => {
  const { page, errors } = await home(b);
  const out = {}, warned = [];
  page.on('response', async (r) => { if (r.request().method() === 'PUT') { try { const j = await r.json(); if (j.warnings) warned.push([j.warnings.length, j.warning_fields]); } catch {} } });
  for (const mode of ['grid', 'gridControl', 'route']) {
    const p = await newProject(page, 'Stale_' + mode);
    if (mode === 'route') {
      await put(page, p, 'm_rebar', { value: 30, unit: 't', state: 'assumption', method: 'user_entered' });
      await put(page, p, 'm_quantity_basis', { value: 'DESIGN', state: 'assumption', method: 'user_entered' });
      await put(page, p, 'a_stages', { value: 'EMBODIED', state: 'assumption', method: 'user_entered' });
      await put(page, p, 'a_eol_route', { value: null, state: 'not_applicable', method: 'user_entered' });
      await openP(page, p); await screen(page, 'basic');
      await page.selectOption('#in-a_stages', 'ALL'); await page.selectOption('#in-a_eol_route', 'LANDFILL');
    } else {
      await put(page, p, 'o_elec_kwh', { value: 0, unit: 'kWh/年', state: 'confirmed', method: 'user_entered' });
      await put(page, p, 'o_grid_value', { value: null, state: 'not_applicable', method: 'user_entered' });
      await openP(page, p); await screen(page, 'operation');
      await retype(page, 'o_elec_kwh', '1000');
      if (mode === 'grid') await retype(page, 'o_grid_value', '0.45');
    }
    await toasts(page); warned.splice(0);
    await page.click('#bb-hub'); await answered(page);
    out[mode] = { where: await where(page), toast: await box(page), warned: warned.splice(0),
      factor: await stored(page, p, mode === 'route' ? 'a_eol_route' : 'o_grid_value') };
    if (out[mode].toast.close) await page.click('#toast-close');
    await page.evaluate(() => { state.stack = []; }); await page.click('#btn-back');
  }
  return { ...out, errors };
};

// sweep#0 (kept on screen): the warning of a row's own 保存 stays; giving the factor a value (its 保存) or 未取得 takes it
// back; a save of another row leaves it
F.staleKept = async (b) => {
  const { page, errors } = await home(b);
  const out = {};
  for (const mode of ['value', 'unset', 'other']) {
    const p = await newProject(page, 'Kept_' + mode);
    await put(page, p, 'o_elec_kwh', { value: 0, unit: 'kWh/年', state: 'confirmed', method: 'user_entered' });
    await put(page, p, 'o_grid_value', { value: null, state: 'not_applicable', method: 'user_entered' });
    await openP(page, p); await screen(page, 'operation');
    await retype(page, 'o_elec_kwh', '1000'); await page.click('[data-save="o_elec_kwh"]'); await answered(page);
    const before = await box(page);
    if (mode === 'value') { await retype(page, 'o_grid_value', '0.45'); await page.click('[data-save="o_grid_value"]'); }
    else if (mode === 'unset') await page.click('[data-unset="o_grid_value"]');
    else { await retype(page, 'o_gas_m3', '5'); await page.click('[data-save="o_gas_m3"]'); }
    await answered(page);
    out[mode] = { before, after: await box(page), factor: await stored(page, p, 'o_grid_value') };
    await page.waitForTimeout(mode === 'other' ? 0 : 7000);              // what is left without the warning goes after its time
    out[mode].later = await box(page);
    if (out[mode].later.close) await page.click('#toast-close');
    await page.evaluate(() => { state.stack = []; }); await page.click('#btn-back'); await page.waitForFunction(() => state.view === 'home');
  }
  return { ...out, errors };
};

// ui-flows#0: 架空デモを開く (or a structure card) answered after the user has opened B and typed on its 材料; and during B's
// 保存して戻る (no press of the user's). Control: the demo answered while the user is still at home opens it
F.lateMade = async (b) => {
  const out = {};
  for (const kind of ['demo', 'card', 'batch', 'control']) {
    const { ctx, page, errors } = await home(b);
    const pB = await newProject(page, 'LateB_' + kind);
    await page.evaluate(() => render()); await page.waitForSelector(`[data-open="${pB}"]`);
    if (kind === 'control') {
      await hold(page, 'POST', /\/api\/demo$/, 1200);
      await page.click('#demo');
      await page.waitForFunction(() => state.view === 'hub', null, { timeout: 15000 });
      out[kind] = { where: await where(page), t: await toasts(page), errors };
      await ctx.close(); continue;
    }
    if (kind === 'card') {
      await page.click('#start'); await page.waitForSelector('[data-s="RC"]');
      await hold(page, 'POST', /\/api\/projects$/, 2500);
      await page.fill('#pname', 'CardLate'); await page.click('[data-s="RC"]'); await page.waitForTimeout(150);
      await page.click('#btn-back'); await page.waitForSelector(`[data-open="${pB}"]`);
    } else {
      await hold(page, 'POST', /\/api\/demo$/, kind === 'batch' ? 2500 : 2500);
      await page.click('#demo'); await page.waitForTimeout(150);
    }
    await page.click(`[data-open="${pB}"]`); await page.waitForFunction((p) => state.view === 'hub' && state.project.id === p, pB);
    if (kind === 'batch') {
      await screen(page, 'operation');
      await retype(page, 'o_gas_m3', '5'); await retype(page, 'o_oil_l', '7'); await retype(page, 'o_water_m3', '300');
      await hold(page, 'PUT', /\/fields\/o_gas_m3$/, 4000);
      await toasts(page);
      await page.click('#bb-hub');
      await answered(page);
      out[kind] = { where: await where(page), t: await toasts(page),
        gas: await stored(page, pB, 'o_gas_m3'), oil: await stored(page, pB, 'o_oil_l'), water: await stored(page, pB, 'o_water_m3'), errors };
    } else {
      await screen(page, 'material');
      await retype(page, 'm_concrete', '300'); await retype(page, 'm_rebar', '30');
      await toasts(page);
      await page.waitForTimeout(3200);
      const list = (await api(page, 'GET', '/projects')).body.map((p) => p.name);
      out[kind] = { where: await where(page), concrete: await value(page, 'm_concrete'), rebar: await value(page, 'm_rebar'),
        t: await toasts(page), list, errors };
    }
    await ctx.close();
  }
  return out;
};

// ui-flows#1: この候補を採用 refused (the candidate was adopted in another tab meanwhile) with 3000 typed in its row: alone,
// during 保存して戻る, and with 保存して戻る stopped (⚙ twice) before the refusal comes
const CSV = '名称,規格,数量,単位\nコンクリート,Fc24,300,m3\n';
const acceptRefused = async (b, mode) => {
  const { page, errors } = await home(b);
  const p = await newProject(page, 'Acc_' + mode);
  await openP(page, p); await screen(page, 'material');
  await page.setInputFiles('#docfile', { name: 'bill.csv', mimeType: 'text/csv', buffer: Buffer.from(CSV) });
  await page.waitForSelector('[data-accept="m_concrete"]');
  await answered(page);
  const cid = await page.evaluate(() => +document.querySelector('[data-accept="m_concrete"]').dataset.cid);
  const other = await api(page, 'POST', `/projects/${p}/fields/m_concrete/accept`, { id: cid });   // another tab adopts it
  await retype(page, 'm_concrete', '3000'); await retype(page, 'm_rebar', '30');
  await toasts(page);
  if (mode !== 'alone') await hold(page, 'POST', /\/fields\/m_concrete\/accept$/, mode === 'stop' ? 2500 : 800);
  await page.click(`[data-accept="m_concrete"][data-cid="${cid}"]`);
  if (mode === 'batch') { await page.waitForTimeout(150); await page.click('#bb-hub'); }
  if (mode === 'stop') {
    await page.waitForTimeout(150); await page.click('#bb-hub'); await page.waitForTimeout(150);
    await page.click('#btn-settings'); await page.waitForTimeout(600); await page.click('#btn-settings');
  }
  await answered(page);
  return { other: other.status, where: await where(page), concrete: await value(page, 'm_concrete'), t: await toasts(page),
    stored: await stored(page, p, 'm_concrete'), rebar: await stored(page, p, 'm_rebar'), toast: await box(page), errors };
};
F.acceptAlone = (b) => acceptRefused(b, 'alone');
F.acceptBatch = (b) => acceptRefused(b, 'batch');
F.acceptStop = (b) => acceptRefused(b, 'stop');

// ui-flows#2: at 320 x 568 every numeric row of 設備 typed, 保存して戻る with the 8th PUT slow, stopped with ⚙ twice: the long
// stop message names the rows not saved first, stays until 閉じる and scrolls. An ordinary message too long for the toast
// stays too; a short one goes after its time
F.longStop = async (b) => {
  const { page, errors } = await home(b, { width: 320, height: 568 });
  const p = await newProject(page, 'LongStop');
  await openP(page, p); await screen(page, 'equipment');
  const rows = await page.evaluate(() => [...document.querySelectorAll('#main [data-save]')].map((x) => x.dataset.save).filter((f) => state.meta.fields[f].type === 'number'));
  for (const [i, f] of rows.entries()) await page.evaluate(([f, v]) => { const e = document.getElementById('in-' + f); e.value = v; e.dispatchEvent(new Event('input')); }, [f, String(i + 1)]);
  let n = 0;
  await page.route((u) => /\/fields\//.test(u.pathname), async (r) => { if (r.request().method() === 'PUT' && ++n === 8) await sleep(2500); return r.continue(); });
  await page.click('#bb-hub'); await page.waitForTimeout(1200);
  await page.click('#btn-settings'); await page.waitForTimeout(600); await page.click('#btn-settings');
  await answered(page);
  const said = await box(page);
  await page.waitForTimeout(7000);
  const later = await box(page);
  await page.mouse.move(160, (later.top + later.bottom) / 2); await page.mouse.wheel(0, 400); await page.waitForTimeout(300);
  const scrolled = await page.evaluate(() => document.getElementById('toast-body').scrollTop);
  await page.click('#toast-close'); await page.waitForTimeout(300);
  const closed = await box(page);
  // an ordinary message (no warning) too long for the toast, then a short one
  await page.evaluate(() => toast('長い知らせ：' + '「冷媒機器の交換周期」'.repeat(40)));
  const plainLong = await box(page);
  await page.waitForTimeout(7000);
  const plainLongLater = await box(page);
  await page.click('#toast-close');
  await page.evaluate(() => toast('変更はありません'));
  const plainShort = await box(page);
  await page.waitForTimeout(3500);
  const plainShortLater = await box(page);
  return { rows: rows.length, said, later, scrolled, closed, plainLong, plainLongLater, plainShort, plainShortLater, errors };
};

// ui-flows#2 (stay): 保存して戻る that stays (an emptied row) names rows not saved: its words stay until 閉じる
F.stayHolds = async (b) => {
  const { page, errors } = await home(b);
  const p = await newProject(page, 'StayHold');
  await put(page, p, 'b_height', { value: 50, unit: 'm', state: 'confirmed', method: 'user_entered' });
  await openP(page, p); await screen(page, 'basic');
  await page.click('#in-b_height'); await page.keyboard.press('Control+A'); await page.keyboard.press('Delete');
  await retype(page, 'b_floors_above', '5');
  await page.click('#bb-hub'); await answered(page);
  const said = await box(page);
  await page.waitForTimeout(7000);
  return { said, later: await box(page), where: await where(page), errors };
};

// ui-flows#3: 結果を見る when the read of the stored result fails (the server cannot be reached; it answers 500); a project
// never calculated shows nothing
F.resultRead = async (b) => {
  const { page, errors } = await home(b);
  await page.click('#demo'); await page.waitForFunction(() => state.view === 'hub' && !!document.querySelector('[data-screen]'));
  const pid = await page.evaluate(() => state.project.id);
  await api(page, 'POST', `/projects/${pid}/calculate`, { period: 60 });
  const out = {};
  const isResult = (u) => u.pathname === `/api/projects/${pid}/result`;
  for (const mode of ['offline', 'fail500']) {
    await page.route(isResult, (r) => (mode === 'offline' ? r.abort('connectionrefused')
      : r.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ error: '内部エラー' }) })));
    await page.click('#to-result'); await page.waitForTimeout(800);
    out[mode] = await page.evaluate(() => ({ msg: document.getElementById('res-msg').textContent, res: document.getElementById('res').textContent }));
    await page.unroute(isResult);
    await page.click('#btn-back'); await page.waitForFunction(() => state.view === 'hub');
  }
  await page.click('#to-result'); await page.waitForFunction(() => document.getElementById('res').textContent.length > 0);
  out.ok = await page.evaluate(() => ({ msg: document.getElementById('res-msg').textContent, res: document.getElementById('res').textContent.trim().slice(0, 40) }));
  const p2 = await newProject(page, 'NeverCalculated');
  await openP(page, p2); await page.click('#to-result'); await page.waitForTimeout(800);
  out.none = await page.evaluate(() => ({ msg: document.getElementById('res-msg').textContent, res: document.getElementById('res').textContent }));
  out.sw = await page.evaluate(() => document.documentElement.scrollWidth);
  return { ...out, errors };
};

// ui-flows#4: a warning that stays is not written again at each view of its project; it is named (written) on another one
F.quietViews = async (b) => {
  const { page, errors } = await home(b);
  const pA = await newProject(page, 'QuietA'), pB = await newProject(page, 'QuietB');
  await put(page, pA, 'o_elec_kwh', { value: 0, unit: 'kWh/年', state: 'confirmed', method: 'user_entered' });
  await put(page, pA, 'o_grid_value', { value: null, state: 'not_applicable', method: 'user_entered' });
  await openP(page, pA); await screen(page, 'operation');
  await retype(page, 'o_elec_kwh', '1000'); await page.click('[data-save="o_elec_kwh"]'); await answered(page);
  await page.evaluate(() => {
    window.__mut = 0;
    new MutationObserver((ms) => { window.__mut += ms.length; }).observe(document.getElementById('toast'), { childList: true, subtree: true, characterData: true, attributes: true,
      attributeFilter: ['role', 'aria-live', 'hidden', 'class'] });
  });
  const counts = [];
  for (const step of ['back', 'basic', 'back', 'material', 'back']) {
    if (step === 'back') { await page.click('#btn-back'); await page.waitForFunction(() => state.view === 'hub'); }
    else await screen(page, step);
    await page.waitForTimeout(200);
    counts.push(await page.evaluate(() => window.__mut));
  }
  const onA = await box(page);
  await openP(page, pB); await page.waitForTimeout(200);
  return { counts, onA, onB: await box(page), mutB: await page.evaluate(() => window.__mut), errors };
};

// ---- the fix-up of the round-15 screens (an attack on the fixes) ----
// the app at home with the toast's timers watched (window.__live: the timers still to come)
async function watched(browser, vp) {
  const { ctx, page, errors } = await page0(browser, vp);
  await page.addInitScript(() => {
    const st = window.setTimeout, ct = window.clearTimeout; window.__live = new Set();
    window.setTimeout = (fn, ms, ...a) => { const id = st(() => { window.__live.delete(id); if (typeof fn === 'function') fn(...a); }, ms); window.__live.add(id); return id; };
    window.clearTimeout = (id) => { window.__live.delete(id); ct(id); };
  });
  await page.goto(BASE + '/');
  await page.waitForFunction(() => typeof state !== 'undefined' && !!state.meta && !!document.getElementById('splash').onclick);
  await page.click('#splash');
  await page.waitForSelector('#main:not([hidden]) #demo');
  return { ctx, page, errors };
}
// the toast now, with whether its timer is still to come
const tnow = (page) => page.evaluate(() => {
  const t = document.getElementById('toast'), b = document.getElementById('toast-body'), shown = t.classList.contains('show');
  return { shown, sticky: t.classList.contains('sticky'), close: !document.getElementById('toast-close').hidden, taps: getComputedStyle(t).pointerEvents,
    timed: !!toast._t && window.__live.has(toast._t), over: b.scrollHeight > b.clientHeight + 1, role: t.getAttribute('role'),
    text: shown ? document.getElementById('toast-text').textContent : '', all: shown ? t.textContent : '' };
});
// fix-up 1: words too long on an input screen (its bottom bar wraps on a narrow phone), shown next on a view where they
// fit: never left shown with neither 閉じる nor a timer. (a) every numeric row of 設備 saved by 保存して戻る at 375 x 548;
// (b) 「まだ保存していない入力」 of 17 rows at 320 x 568, then ← to the hub and 基本情報; (c) the same rule over lengths,
// kinds and paths through the app's own functions
F.stuckToast = async (b) => {
  const out = {};
  {
    const { ctx, page, errors } = await watched(b, { width: 375, height: 548 });
    const p = await newProject(page, 'StuckA');
    await openP(page, p); await screen(page, 'equipment');
    const rows = await page.evaluate(() => [...document.querySelectorAll('#main [data-save]')].map((x) => x.dataset.save).filter((f) => state.meta.fields[f].type === 'number'));
    // a count, a life, a mass: 1, 2, 3 …; a rate (no unit): 0.1 (within its range)
    for (const [i, f] of rows.entries()) await page.evaluate(([f, i]) => { const e = document.getElementById('in-' + f); e.value = state.meta.fields[f].unit ? String(i + 1) : '0.1'; e.dispatchEvent(new Event('input')); }, [f, i]);
    await page.evaluate(() => { window.__first = null; const d = window.drawToast; window.drawToast = function (x) { d(x); if (!window.__first) window.__first = { view: state.view, over: (() => { const b = document.getElementById('toast-body'); return b.scrollHeight > b.clientHeight + 1; })() }; }; });
    await page.click('#bb-hub'); await answered(page);
    out.a = { rows: rows.length, first: await page.evaluate(() => window.__first), hub: await tnow(page) };
    if (out.a.hub.close) await page.click('#toast-close'); else await page.evaluate(() => closeToast());
    await page.waitForTimeout(200);
    out.a.closed = await tnow(page);
    out.a.errors = errors;
    await ctx.close();
  }
  {
    const { ctx, page, errors } = await watched(b, { width: 320, height: 568 });
    const p = await newProject(page, 'StuckB');
    await openP(page, p); await screen(page, 'equipment');
    const rows = await page.evaluate(() => [...document.querySelectorAll('#main [data-save]')].map((x) => x.dataset.save).filter((f) => state.meta.fields[f].type === 'number').slice(0, 17));
    for (const [i, f] of rows.entries()) await page.evaluate(([f, v]) => { const e = document.getElementById('in-' + f); e.value = v; e.dispatchEvent(new Event('input')); }, [f, String(i + 1)]);
    await page.click(`[data-save="${rows[0]}"]`); await answered(page);
    const onScreen = await tnow(page);
    await page.click('#btn-back'); await page.waitForFunction(() => state.view === 'hub'); await page.waitForTimeout(200);
    const hub = await tnow(page);
    await page.evaluate(() => go('screen', 'basic')); await page.waitForFunction(() => state.view === 'screen'); await page.waitForTimeout(200);
    const basic = await tnow(page);
    await page.keyboard.press('Escape');                                // Escape outside the toast closes nothing
    await page.focus('#toast-close'); await page.keyboard.press('Escape'); await page.waitForTimeout(200);
    out.b = { onScreen, hub, basic, closed: await tnow(page), errors };
    await ctx.close();
  }
  for (const [w, h] of [[320, 568], [375, 548]]) {
    const { ctx, page, errors } = await watched(b, { width: w, height: h });
    const p = await newProject(page, 'StuckC');
    await openP(page, p);
    out['c' + w] = await page.evaluate(async () => {
      const P = state.project, key = projectKey(P), r = { steps: 0, stuck: [], overThenFits: 0 };
      const to = async (v) => { state.nav++; state.act++; state.view = v[0]; state.arg = v[1]; await render(); };
      const now = () => { const t = document.getElementById('toast'), b = document.getElementById('toast-body');
        return { shown: t.classList.contains('show'), sticky: t.classList.contains('sticky'), close: !document.getElementById('toast-close').hidden,
          timed: !!toast._t && window.__live.has(toast._t), over: toastOverflows() }; };       // measured without 閉じる
      for (const first of [['screen', 'equipment'], ['hub', undefined]]) for (let k = 2; k <= 20; k += 2) for (const kind of ['plain', 'about']) {
        await to(first); closeToast();
        const msg = 'まだ保存していない入力：' + '「空調機器の耐用年数」'.repeat(k);
        if (kind === 'plain') toast(msg, 50); else toast(msg, 50, false, { key, name: P.name });
        const seen = [now()];
        for (const v of [['hub', undefined], ['screen', 'basic'], ['hub', undefined]]) { await to(v); seen.push(now()); }
        seen.forEach((s, i) => { r.steps++; if (s.shown && !s.timed && !(s.sticky && s.close)) r.stuck.push([first[0], k, kind, i]); });
        if (seen[0].over && seen.slice(1).some((s) => !s.over)) r.overThenFits++;
      }
      closeToast();
      return r;
    });
    out['c' + w].errors = errors;
    await ctx.close();
  }
  return out;
};

// fix-up 2: a late answer (架空デモを開く answered after B's 保存して戻る was stopped with ⚙ ⚙) does not replace the stop's
// words that name rows not saved; and the rule through toast() itself (older, same and newer acts, a warning)
F.lateOverHeld = async (b) => {
  const { page, errors } = await watched(b);
  const pB = await newProject(page, 'HeldB');
  await page.evaluate(() => render()); await page.waitForSelector(`[data-open="${pB}"]`);
  await hold(page, 'POST', /\/api\/demo$/, 5000);
  await page.click('#demo'); await page.waitForTimeout(150);
  await page.click(`[data-open="${pB}"]`); await page.waitForFunction((p) => state.view === 'hub' && state.project.id === p, pB);
  await screen(page, 'operation');
  await retype(page, 'o_gas_m3', '5'); await retype(page, 'o_oil_l', '7'); await retype(page, 'o_water_m3', '300');
  await hold(page, 'PUT', /\/fields\/o_gas_m3$/, 1500);
  await page.click('#bb-hub'); await page.waitForTimeout(300);
  await page.click('#btn-settings'); await page.waitForTimeout(600); await page.click('#btn-settings');
  await page.waitForFunction(() => !state.busy && document.getElementById('toast-text').textContent.includes('途中でやめました'));
  const stop = await tnow(page);
  await page.waitForFunction(() => document.getElementById('toast-text').textContent.includes('を作りました'), null, { timeout: 15000 });
  await page.waitForTimeout(300);
  const after = await tnow(page);
  const st = { gas: await stored(page, pB, 'o_gas_m3'), oil: await stored(page, pB, 'o_oil_l'), water: await stored(page, pB, 'o_water_m3') };
  // the rule itself, on B's hub
  await openP(page, pB);
  const rule = await page.evaluate(() => {
    const P = state.project, about = { key: projectKey(P), name: P.name }, W = { w: '「運用時の電力の排出係数」の「適用外」は、いまの入力では使えない（甲）', key: projectKey(P), name: P.name };
    const HELD = '保存して戻るを途中でやめました：「都市ガス」は保存していません', LATE = '「架空デモ」を作りました（開いていません。ホームの「続きから」から開けます）';
    const text = () => document.getElementById('toast-text').textContent, sticky = () => document.getElementById('toast').classList.contains('sticky');
    const r = {};
    closeToast(); toast(HELD, 10, false, about, true); toast(LATE, 5); toast('まだ保存していない入力：「鉄筋」', 5);
    r.older = [text(), sticky()];
    toast('変更はありません', 20); r.newer = [text(), sticky()];               // a newer action's words replace them (as before)
    closeToast(); toast(HELD, 10, false, about, true); toast(W, 5); r.olderWarn = [text(), sticky(), document.getElementById('toast').getAttribute('role')];
    closeToast(); toast('2 項目を保存しました', 10, false, about); toast(LATE, 5); r.notHeld = [text()];   // not held: replaced (as before)
    closeToast();
    return r;
  });
  return { stop, after, stored: st, rule, errors };
};

// fix-up 3: the answer of an earlier save of the factor (its value 0.45, stored before the user made it 適用外 again) comes
// after the warning that the later purchase made about the 適用外: the warning stays. And the rule through warnOf itself,
// with the server's write times
F.lateSettle = async (b) => {
  const { page, errors } = await watched(b);
  const p = await newProject(page, 'LateSettle');
  await put(page, p, 'o_elec_kwh', { value: 0, unit: 'kWh/年', state: 'confirmed', method: 'user_entered' });
  await openP(page, p); await screen(page, 'operation');
  let n = 0;
  await page.route((u) => /\/fields\/o_grid_value$/.test(u.pathname), async (route) => {
    if (route.request().method() !== 'PUT' || ++n !== 1) return route.continue();
    const resp = await route.fetch(); await sleep(3000); return route.fulfill({ response: resp });   // stored now, answered late
  });
  await retype(page, 'o_grid_value', '0.45'); await page.click('[data-save="o_grid_value"]'); await page.waitForTimeout(300);
  await page.click('[data-na="o_grid_value"]'); await page.waitForTimeout(500);
  await retype(page, 'o_elec_kwh', '1000'); await page.click('[data-save="o_elec_kwh"]');
  await page.waitForFunction(() => document.getElementById('toast-text').textContent.includes('いまの入力では使えない'));
  const warned = await tnow(page);
  await answered(page); await page.waitForTimeout(300);
  const late = await tnow(page);
  const factor = await stored(page, p, 'o_grid_value');
  const rule = await page.evaluate(() => {
    const P = state.project, nav = { n: 1, pid: P.id, key: projectKey(P), act: 70, name: P.name };
    const W = (at) => ({ field_id: 'o_elec_kwh', state: 'confirmed', ...(at === null ? {} : { updated_at: at }), warnings: ['WX'], warning_fields: ['o_grid_value'] });
    const S = (st, at) => ({ field_id: 'o_grid_value', state: st, ...(at === null ? {} : { updated_at: at }) });
    const shown = () => document.getElementById('toast').classList.contains('show') && document.getElementById('toast-text').textContent.includes('WX');
    const r = {};
    for (const [k, w, s] of [['older', 2, S('confirmed', 1)], ['newer', 2, S('confirmed', 3)], ['olderUnset', 2, S('not_obtained', 1)],
      ['newerUnset', 2, S('not_obtained', 3)], ['noTime', null, S('confirmed', null)], ['answerNoTime', 2, S('confirmed', null)], ['same', 2, S('confirmed', 2)]]) {
      closeToast(); state.warnings = []; state.busy = false; state.batch = null;
      warnOf(W(w), nav); warnOf(s, nav); r[k] = shown();
      // kept for 保存して戻る (said at its end): the same rule
      closeToast(); state.busy = true; state.batch = { n: 1, key: nav.key };
      warnOf(W(w), nav); warnOf(s, nav); r[k + 'Batch'] = state.warnings.map((x) => x.w);
      state.busy = false; state.batch = null; state.warnings = [];
    }
    closeToast();
    return r;
  });
  return { warned, late, factor, rule, errors };
};

// fix-up 4: A's 保存して戻る stopped (⚙ ⚙) while its slow purchase PUT carries a warning: the stop names a row not saved and
// says the warning; then B is opened: the words naming the row not saved stay, named by A
F.heldNamedElsewhere = async (b) => {
  const { page, errors } = await watched(b);
  const pA = await newProject(page, 'HeldA'), pB = await newProject(page, 'HeldOther');
  await put(page, pA, 'o_elec_kwh', { value: 0, unit: 'kWh/年', state: 'confirmed', method: 'user_entered' });
  await put(page, pA, 'o_grid_value', { value: null, state: 'not_applicable', method: 'user_entered' });
  await openP(page, pA); await screen(page, 'operation');
  await hold(page, 'PUT', new RegExp('projects/' + pA + '/fields/o_elec_kwh$'), 1500);
  await retype(page, 'o_elec_kwh', '1000'); await retype(page, 'o_gas_m3', '5');
  await page.click('#bb-hub'); await page.waitForTimeout(150);
  await page.click('#btn-settings'); await page.waitForTimeout(500); await page.click('#btn-settings');
  await answered(page);
  const said = await tnow(page);
  const where0 = await where(page);
  await page.click(`[data-open="${pB}"]`);                           // the list of projects in 設定 await page.waitForFunction((p) => state.view === 'hub' && state.project.id === p, pB);
  await page.waitForTimeout(1000);
  const onB = await tnow(page);
  await openP(page, pA); await page.waitForTimeout(200);
  return { where0, said, onB, onA: await tnow(page), gas: await stored(page, pA, 'o_gas_m3'), errors };
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
WARN_ROUTE = "「解体後の処理（シナリオ）」の「適用外」は、いまの入力では使えない"
MADE = "を作りました（開いていません。ホームの「続きから」から開けます）"
STOP = "保存して戻るを途中でやめました："


class FifteenthRoundUiTests(unittest.TestCase):
    """Regression tests for the fifteenth verification round, screens (docs/review_fixes.md, round 15)."""

    @classmethod
    def setUpClass(cls):
        cls.js = (WEB / "app.js").read_text(encoding="utf-8")

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

    # ---- sweep#0: a warning whose field the same 保存して戻る has given another state is not said ----

    def test_put_and_accept_name_the_field_of_each_warning(self):
        td = tempfile.TemporaryDirectory()
        app = App(td.name)
        try:
            def put(pid, fid, body):
                return app.handle("PUT", "/api/projects/%d/fields/%s" % (pid, fid), body)
            pid = app.projects.create("r15", "RC")
            # the route 適用外 (accepted while the boundary ends at construction) made unusable by the boundary set to every
            # stage: the answer names its field with the sentence
            for fid, body in (("o_elec_kwh", {"state": "confirmed", "value": 1000}), ("m_rebar", {"state": "confirmed", "value": 30, "unit": "t"}),
                              ("m_quantity_basis", {"state": "confirmed", "value": "DESIGN"}), ("a_stages", {"state": "confirmed", "value": "EMBODIED"})):
                self.assertEqual(put(pid, fid, body)[0], 200)
            st, out = put(pid, "a_eol_route", {"state": "not_applicable"})
            self.assertEqual(st, 200)
            self.assertNotIn("warnings", out)
            self.assertNotIn("warning_fields", out)
            st, out = put(pid, "a_stages", {"state": "confirmed", "value": "ALL"})
            self.assertEqual(st, 200)
            self.assertEqual(len(out["warnings"]), len(out["warning_fields"]))
            self.assertEqual(out["warning_fields"], ["a_eol_route"], out)
            for f, w in zip(out["warning_fields"], out["warnings"]):
                self.assertTrue(w.startswith("「%s」の「適用外」は、いまの入力では使えない" % FL.FIELDS[f]["label"]), w)
            # two at once (the boundary set to every stage while the grid factor, with a purchase, and the route, with a
            # mass row, are 適用外): one field per sentence, in the same order
            pid = app.projects.create("r15b", "RC")
            for fid, body in (("o_elec_kwh", {"state": "confirmed", "value": 1000}), ("m_rebar", {"state": "confirmed", "value": 30, "unit": "t"}),
                              ("m_quantity_basis", {"state": "confirmed", "value": "DESIGN"}), ("a_stages", {"state": "confirmed", "value": "EMBODIED"})):
                self.assertEqual(put(pid, fid, body)[0], 200)
            for fid in ("o_grid_value", "a_eol_route"):
                self.assertEqual(put(pid, fid, {"state": "not_applicable"})[0], 200, fid)
            st, out = put(pid, "a_stages", {"state": "confirmed", "value": "ALL"})
            self.assertEqual(st, 200)
            self.assertEqual(sorted(out.get("warning_fields") or []), ["a_eol_route", "o_grid_value"], out)
            self.assertEqual(len(out["warnings"]), 2)
            for f, w in zip(out["warning_fields"], out["warnings"]):
                self.assertTrue(w.startswith("「%s」の「適用外」は、いまの入力では使えない" % FL.FIELDS[f]["label"]), (f, w))
            # adopting a candidate names the field too
            pid = app.projects.create("r15c", "RC")
            for fid, body in (("o_elec_kwh", {"state": "confirmed", "value": 0}), ("o_grid_value", {"state": "not_applicable"})):
                self.assertEqual(put(pid, fid, body)[0], 200)
            cid = app.projects.propose(pid, Value("o_elec_kwh", "from_drawing", 900.0, "kWh/年", method="document",
                                                  source_id="doc1-test.csv", source_detail="Sheet1!B2"), "test")
            st, out = app.handle("POST", "/api/projects/%d/fields/o_elec_kwh/accept" % pid, {"id": cid})
            self.assertEqual(st, 200)
            self.assertEqual(out.get("warning_fields"), ["o_grid_value"], out)
            self.assertEqual(len(out["warnings"]), 1)
            # no warning: neither key (the answer is the stored value as before)
            st, out = put(pid, "o_gas_m3", {"state": "confirmed", "value": 5})
            self.assertNotIn("warnings", out)
            self.assertNotIn("warning_fields", out)
        finally:
            app.engine.close()
            app.projects.close()
            td.cleanup()

    def test_batch_does_not_say_a_warning_its_later_save_answered(self):
        r = self.flow("staleBatch")
        for mode, warn, field in (("grid", WARN_GRID, "o_grid_value"), ("route", WARN_ROUTE, "a_eol_route")):
            x = r[mode]
            self.assertEqual(x["warned"], [[1, [field]]], (mode, x))          # the first PUT of the batch said it
            self.assertEqual(x["factor"]["state"], "confirmed", (mode, x))
            self.assertEqual(x["where"]["view"], "hub", (mode, x))
            self.assertTrue(x["toast"]["text"].startswith("2 項目を保存しました"), (mode, x))
            self.assertNotIn(warn, x["toast"]["all"], (mode, x))            # it no longer holds: not said
            self.assertFalse(x["toast"]["sticky"], (mode, x))
            self.assertLessEqual(x["toast"]["sw"], x["toast"]["iw"], (mode, x))
        # control: the factor left 適用外 by the batch: the warning holds, and is said with the batch's words
        x = r["gridControl"]
        self.assertEqual(x["factor"]["state"], "not_applicable", x)
        self.assertIn("1 項目を保存しました（「購入電力」） ／ " + WARN_GRID, x["toast"]["all"])
        self.assertTrue(x["toast"]["sticky"] and x["toast"]["close"], x)
        self.assertEqual(x["toast"]["role"], "alert", x)

    def test_warning_kept_on_screen_goes_when_its_field_is_given_another_state(self):
        r = self.flow("staleKept")
        for mode, st in (("value", "confirmed"), ("unset", "not_obtained")):
            x = r[mode]
            self.assertIn(WARN_GRID, x["before"]["all"], (mode, x))
            self.assertTrue(x["before"]["sticky"], (mode, x))
            self.assertEqual(x["factor"]["state"], st, (mode, x))
            self.assertNotIn(WARN_GRID, x["after"]["all"], (mode, x))
            self.assertFalse(x["later"]["shown"], (mode, x))                   # nothing left that stays
        # a save of another row does not touch it
        x = r["other"]
        self.assertIn(WARN_GRID, x["after"]["all"], x)
        self.assertTrue(x["after"]["sticky"], x)
        self.assertEqual(x["factor"]["state"], "not_applicable", x)

    def test_warnings_are_dropped_only_for_their_field_and_project(self):
        out = node(TAKE + r"""
var state = { busy: false, warnings: [], batch: null, view: 'hub', project: { id: 2, created_at: 9, name: 'B', fields: {} } };
const said = [], dropped = [];
eval(take(/function projectKey[\s\S]*?\n}\n/));
eval(take(/function shownKey[^\n]*\n/));
function settleWarnings(key, f) { dropped.push([key, f]); state.warnings = state.warnings.filter((x) => !(x.f === f && x.nav.key === key)); }
function toast(msg, act) { said.push([msg.w, msg.f, msg.key, act]); }
eval(take(/function warnOf[\s\S]*?\n}\n/));
eval(take(/function sayWarning\([^\n]*\n/));
eval(take(/function sayWarnings[^\n]*\n/));
eval(take(/const storedNa = [^\n]*\n/).replace('const storedNa', 'var storedNa'));
const B = (act) => ({ key: '2@9', act, name: 'B' }), A = (act) => ({ key: '1@5', act, name: 'A' });
state.busy = true; state.batch = { n: 4, key: '2@9' };
// the batch's first PUT says two warnings (fields g and r); a write of A answers with field g given a value
warnOf({ field_id: 'e', state: 'confirmed', warnings: ['wg', 'wr'], warning_fields: ['g', 'r'] }, B(1));
warnOf({ field_id: 'g', state: 'confirmed' }, A(2));                  // another project: B's warning about g stays
const k1 = state.warnings.map((x) => x.w);
warnOf({ field_id: 'g', state: 'not_applicable' }, B(3));             // 適用外 again: nothing is taken back
warnOf({ field_id: 'g', state: 'confirmed' }, B(4));                  // B's g given a value: its warning goes
const k2 = state.warnings.map((x) => x.w);
// the batch's last read: r is still 適用外 (said); then one where r is not (not said); without a read: said as it is
const pNa = { id: 2, created_at: 9, fields: { r: { value: { state: 'not_applicable' } } } };
const pVal = { id: 2, created_at: 9, fields: { r: { value: { state: 'confirmed', value: 1 } } } };
const pOther = { id: 3, created_at: 1, fields: { r: { value: { state: 'confirmed', value: 1 } } } };
const run = (p) => { state.warnings = [{ w: 'wr', f: 'r', nav: B(1) }, { w: 'wx', f: null, nav: B(1) }]; said.length = 0; sayWarnings(9, p); return said.map((x) => x[0]); };
const r = { na: run(pNa), val: run(pVal), none: run(null), other: run(pOther), unread: run({ id: 2, created_at: 9, fields: {} }) };
// an answer without warning_fields (an older server): said as before, with no field
state.busy = false; state.batch = null; said.length = 0;
warnOf({ warnings: ['old'] }, B(5));
console.log(JSON.stringify({ k1, k2, dropped, r, old: said }));
""")
        if out is None:
            self.skipTest("node is not installed")
        self.assertEqual(out["k1"], ["wg", "wr"])
        self.assertEqual(out["k2"], ["wr"])
        self.assertEqual(out["dropped"], [["2@9", "e"], ["1@5", "g"], ["2@9", "g"]])
        self.assertEqual(out["r"]["na"], ["wr", "wx"])
        self.assertEqual(out["r"]["val"], ["wx"])                               # a warning without a field is kept
        self.assertEqual(out["r"]["none"], ["wr", "wx"])
        self.assertEqual(out["r"]["other"], ["wr", "wx"])                       # a read of another project decides nothing
        self.assertEqual(out["r"]["unread"], ["wx"])                            # never stored (未取得): no 適用外 to warn about
        self.assertEqual(out["old"], [["old", None, "2@9", 5]])

    # ---- ui-flows#0: a project made late is not opened over the one the user opened ----

    def test_a_late_made_project_does_not_replace_the_project_opened(self):
        r = self.flow("lateMade")
        for kind, name in (("demo", "架空デモ（RC・事務所・seed 4201）"), ("card", "CardLate")):
            x = r[kind]
            self.assertEqual(x["where"], {"view": "screen", "arg": "material", "name": "LateB_" + kind}, (kind, x))
            self.assertEqual((x["concrete"], x["rebar"]), ("300", "30"), (kind, x))     # what was typed stays
            self.assertIn("「%s」" % name + MADE, x["t"], (kind, x))
            self.assertIn(name, x["list"], (kind, x))                                 # it is there to be opened
        # during B's 保存して戻る: the late answer is no press (no warning, no stop): every row is saved
        x = r["batch"]
        self.assertFalse(any("保存の途中です" in t for t in x["t"]), x["t"])
        self.assertFalse(any(STOP in t for t in x["t"]), x["t"])
        self.assertEqual((x["gas"]["value"], x["oil"]["value"], x["water"]["value"]), (5, 7, 300), x)
        self.assertEqual((x["where"]["view"], x["where"]["name"]), ("hub", "LateB_batch"), x)
        self.assertTrue(any("架空デモ（RC・事務所・seed 4201）」" + MADE in t for t in x["t"]), x["t"])
        # control: answered while the user is still where they tapped: it opens
        x = r["control"]
        self.assertEqual((x["where"]["view"], x["where"]["name"]), ("hub", "架空デモ（RC・事務所・seed 4201）"), x)
        self.assertFalse(any(MADE in t for t in x["t"]), x["t"])

    def test_a_late_answer_never_goes_through_blocked(self):
        out = node(TAKE + r"""
var state = { nav: 3, act: 0, openSeq: 0, busy: true, busyWarned: 0, view: 'screen', arg: 'operation', project: { id: 7, name: 'B' }, stack: [], lastImport: null };
let blockedCalls = 0, rendered = 0; const said = [];
function blocked() { blockedCalls++; return true; }
function render() { rendered++; }
function projectKey(p) { return p ? p.id + '@1' : ''; }
function toast(m, act) { said.push([m, act]); }
async function api(path) { return { id: 9, name: '架空デモ' }; }
async function loadProject(id, keep) { const p = { id, name: id === 9 ? '架空デモ' : 'X' }; if (!keep(p)) return false; state.project = p; return true; }
eval(take(/async function openRead[\s\S]*?\n}\n/));
eval(take(/function openProject[\s\S]*?\n}\n/));
eval(take(/async function openMade[\s\S]*?\n}\n/));
(async () => {
  const r = {};
  // tapped at nav 3; the user moves (nav 5) before the answer: nothing opened, no press, said where to find it
  state.act = 1;
  let p = openMade(async () => ({ id: 9 }));
  state.nav = 5; await p;
  r.moved = { blockedCalls, rendered, view: state.view, project: state.project.name, said: said.splice(0) };
  // tapped and answered with nothing changed: opened (a move that is not a press)
  state.busy = false; state.view = 'home'; state.project = null; state.act = 2;
  await openMade(async () => ({ id: 9 }));
  r.opened = { blockedCalls, rendered, view: state.view, project: state.project.name, stack: state.stack, said: said.splice(0) };
  // a later 開く (openSeq) before the answer: not opened
  state.view = 'home'; state.project = null; state.act = 3;
  p = openMade(async () => ({ id: 9 }));
  state.openSeq++; await p;
  r.reopened = { view: state.view, project: state.project, said: said.splice(0) };
  console.log(JSON.stringify(r));
})();
""")
        if out is None:
            self.skipTest("node is not installed")
        self.assertEqual(out["moved"], {"blockedCalls": 0, "rendered": 0, "view": "screen", "project": "B",
                                        "said": [["「架空デモ」" + MADE, 1]]})
        self.assertEqual(out["opened"], {"blockedCalls": 0, "rendered": 1, "view": "hub", "project": "架空デモ",
                                         "stack": [["home", None]], "said": []})
        self.assertEqual(out["reopened"], {"view": "home", "project": None, "said": [["「架空デモ」" + MADE, 3]]})

    # ---- ui-flows#1: a refused この候補を採用 keeps what was typed in its row ----

    def test_refused_accept_keeps_the_typed_value(self):
        r = self.flow("acceptAlone")
        self.assertEqual(r["other"], 200, r)
        self.assertEqual(r["concrete"], "3000", r)                               # it was wiped before
        self.assertTrue(any("その候補はもう無い" in t for t in r["t"]), r["t"])
        self.assertTrue(any(re.search(r"まだ保存していない入力：[^／]*「コンクリート（上部構造）」", t) for t in r["t"]), r["t"])
        self.assertEqual((r["stored"]["state"], r["stored"]["value"]), ("from_drawing", 300), r)   # the other tab's adoption

    def test_refused_accept_during_the_batch_is_saved_or_named(self):
        r = self.flow("acceptBatch")
        self.assertEqual((r["stored"]["state"], r["stored"]["value"], r["stored"]["method"]), ("confirmed", 3000, "user_entered"), r)
        self.assertEqual(r["rebar"]["value"], 30, r)
        self.assertEqual(r["where"]["view"], "hub", r)
        self.assertTrue(any(re.search(r"2 項目を保存しました（[^）]*「コンクリート（上部構造）」", t) for t in r["t"]), r["t"])
        r = self.flow("acceptStop")
        msg = [t for t in r["t"] if STOP in t]
        self.assertEqual(len(msg), 1, r["t"])
        lost = msg[0].split(STOP, 1)[1].split("は保存していません")[0]
        self.assertIn("「コンクリート（上部構造）」", lost, msg[0])
        self.assertIn("「鉄筋」", lost, msg[0])
        self.assertEqual(r["stored"]["value"], 300, r)
        self.assertIsNone(r["rebar"]["value"], r)

    # ---- ui-flows#2: long words stay and scroll; the rows not saved are named first ----

    def test_long_stop_message_names_rows_not_saved_first_and_stays(self):
        r = self.flow("longStop")
        self.assertGreaterEqual(r["rows"], 15, r)
        s = r["said"]
        self.assertTrue(s["shown"] and s["sticky"] and s["close"], s)
        self.assertEqual(s["taps"], "auto", s)
        self.assertTrue(s["text"].startswith(STOP + "「"), s["text"])
        head = s["text"].split(STOP, 1)[1].split("。")[0]
        self.assertTrue(head.endswith("は保存していません"), s["text"])         # the first part, not the hidden end
        self.assertEqual(s["role"], "status", s)                                 # no warning: not an alert
        self.assertTrue(s["scrolls"], s)
        self.assertLessEqual(s["sw"], 320, s)
        self.assertGreaterEqual(s["top"], 0, s)
        self.assertTrue(r["later"]["shown"], r["later"])                         # it went after 6.6 s before
        self.assertGreater(r["scrolled"], 0, r)                                  # it scrolls (it took no taps before)
        self.assertFalse(r["closed"]["shown"], r["closed"])
        # an ordinary message too long for the toast stays; a short one goes after its time
        self.assertTrue(r["plainLong"]["sticky"] and r["plainLong"]["close"] and r["plainLong"]["scrolls"], r["plainLong"])
        self.assertEqual(r["plainLong"]["role"], "status", r["plainLong"])
        self.assertTrue(r["plainLongLater"]["shown"], r["plainLongLater"])
        self.assertLessEqual(r["plainLong"]["sw"], 320, r["plainLong"])
        self.assertFalse(r["plainShort"]["sticky"] or r["plainShort"]["close"], r["plainShort"])
        self.assertEqual(r["plainShort"]["taps"], "none", r["plainShort"])
        self.assertFalse(r["plainShortLater"]["shown"], r["plainShortLater"])

    def test_stay_words_that_name_rows_not_saved_stay(self):
        r = self.flow("stayHolds")
        self.assertEqual(r["where"]["view"], "screen", r)
        self.assertIn("空欄にした「建物の高さ」は保存していません", r["said"]["text"])
        self.assertTrue(r["said"]["sticky"] and r["said"]["close"], r["said"])
        self.assertTrue(r["later"]["shown"], r["later"])

    # ---- ui-flows#3: a failed read of the stored result is said ----

    def test_failed_read_of_the_stored_result_is_said(self):
        r = self.flow("resultRead")
        self.assertEqual(r["offline"]["msg"], "前の結果を読めませんでした：WLC Studio のサーバーに接続できません（サーバーが動いているか確かめてください）", r)
        self.assertEqual(r["offline"]["res"], "", r)
        self.assertEqual(r["fail500"]["msg"], "前の結果を読めませんでした：内部エラー", r)
        self.assertEqual(r["ok"]["msg"], "", r)
        self.assertTrue(r["ok"]["res"].startswith("ホールライフカーボン"), r)
        self.assertEqual((r["none"]["msg"], r["none"]["res"]), ("", ""), r)     # never calculated: nothing to say
        self.assertLessEqual(r["sw"], 390, r)

    # ---- ui-flows#4: a toast that stays is not written again at each view ----

    def test_a_toast_that_stays_is_not_said_again_at_each_view(self):
        r = self.flow("quietViews")
        self.assertEqual(r["counts"], [0, 0, 0, 0, 0], r)                         # one write per view before
        self.assertTrue(r["onA"]["all"].startswith(WARN_GRID), r)
        self.assertTrue(r["onB"]["all"].startswith("「QuietA」：" + WARN_GRID), r)  # another project: named (written)
        self.assertGreater(r["mutB"], 0, r)

    # ---- the fix-up of the round-15 screens: what an attack on the fixes found ----

    def test_words_too_long_on_a_screen_are_never_left_without_close_or_timer(self):
        r = self.flow("stuckToast")
        a = r["a"]
        self.assertEqual(a.pop("errors"), [], "page errors")
        self.assertGreaterEqual(a["rows"], 15, a)
        self.assertEqual(a["first"], {"view": "screen", "over": True}, a)      # too long on 設備 (its bottom bar wraps)
        h = a["hub"]
        self.assertTrue(h["text"].startswith("%d 項目を保存しました（" % a["rows"]), h)
        self.assertTrue(h["shown"] and h["sticky"] and h["close"], h)          # it had neither 閉じる nor a timer on the hub
        self.assertEqual(h["taps"], "auto", h)
        self.assertFalse(a["closed"]["shown"], a)
        b = r["b"]
        self.assertEqual(b.pop("errors"), [], "page errors")
        self.assertTrue(b["onScreen"]["text"].startswith("まだ保存していない入力："), b)
        self.assertTrue(b["onScreen"]["sticky"] and b["onScreen"]["over"], b)
        for k in ("hub", "basic"):
            self.assertTrue(b[k]["shown"] and b[k]["sticky"] and b[k]["close"], (k, b[k]))   # neither 閉じる nor a timer before
            self.assertEqual(b[k]["text"], b["onScreen"]["text"], k)
        self.assertFalse(b["closed"]["shown"], b)                               # Escape in it closes it
        exercised = 0
        for w in ("c320", "c375"):
            c = r[w]
            self.assertEqual(c.pop("errors"), [], "page errors")
            self.assertEqual(c["stuck"], [], (w, c))                             # shown with neither 閉じる nor a timer
            self.assertEqual(c["steps"], 160, c)
            exercised += c["overThenFits"]
        self.assertGreater(exercised, 0, r)                                     # some words were too long, then fitted

    def test_a_late_answer_does_not_replace_words_naming_rows_not_saved(self):
        r = self.flow("lateOverHeld")
        held = "「灯油・重油」「上水の使用量」は保存していません"
        s = r["stop"]
        self.assertTrue(s["text"].startswith(STOP) and held in s["text"], s)
        self.assertTrue(s["sticky"] and s["close"], s)
        a = r["after"]
        made = "「架空デモ（RC・事務所・seed 4201）」" + MADE
        self.assertIn(held, a["text"], a)                                       # it was replaced by the late notice
        self.assertIn(made, a["text"], a)
        self.assertLess(a["text"].index(held), a["text"].index(made), a)
        self.assertNotIn("「HeldB」：「架空デモ", a["all"], a)
        self.assertTrue(a["sticky"] and a["close"], a)
        self.assertEqual((r["stored"]["gas"]["value"], r["stored"]["oil"]["value"], r["stored"]["water"]["value"]), (5, None, None), r)
        HELD = "保存して戻るを途中でやめました：「都市ガス」は保存していません"
        LATE = "「架空デモ」を作りました（開いていません。ホームの「続きから」から開けます）"
        rule = r["rule"]
        self.assertEqual(rule["older"], [HELD + " ／ " + LATE + " ／ まだ保存していない入力：「鉄筋」", True])
        self.assertEqual(rule["newer"], ["変更はありません", False])            # a newer action's words replace them, as before
        self.assertEqual(rule["olderWarn"], [HELD + " ／ 「運用時の電力の排出係数」の「適用外」は、いまの入力では使えない（甲）", True, "alert"])
        self.assertEqual(rule["notHeld"], [LATE])                                # words that are not held: replaced, as before

    def test_a_late_answer_of_an_earlier_save_does_not_take_back_a_warning(self):
        r = self.flow("lateSettle")
        self.assertIn(WARN_GRID, r["warned"]["all"], r)
        self.assertEqual(r["warned"]["role"], "alert", r)
        self.assertEqual(r["factor"]["state"], "not_applicable", r)
        late = r["late"]
        self.assertTrue(late["shown"] and late["sticky"] and late["close"], late)   # the 0.45 answer closed it before
        self.assertIn(WARN_GRID, late["all"], late)
        # the rule: a write stored before the warning's write (an earlier updated_at) does not settle it; a later one, one
        # at the same time and one without times settle it as before; the same for the warnings kept for 保存して戻る
        self.assertEqual({k: v for k, v in r["rule"].items() if not k.endswith("Batch")},
                         {"older": True, "newer": False, "olderUnset": True, "newerUnset": False, "noTime": False, "answerNoTime": False, "same": False})
        self.assertEqual({k: v for k, v in r["rule"].items() if k.endswith("Batch")},
                         {"olderBatch": ["WX"], "newerBatch": [], "olderUnsetBatch": ["WX"], "newerUnsetBatch": [], "noTimeBatch": [],
                          "answerNoTimeBatch": [], "sameBatch": []})

    def test_write_answers_carry_the_time_of_their_write(self):
        td = tempfile.TemporaryDirectory()
        app = App(td.name)
        try:
            def put(pid, fid, body):
                return app.handle("PUT", "/api/projects/%d/fields/%s" % (pid, fid), body)
            pid = app.projects.create("r15t", "RC")
            times = []
            for fid, body in (("o_elec_kwh", {"state": "confirmed", "value": 0}), ("o_grid_value", {"state": "confirmed", "value": 0.45}),
                              ("o_grid_value", {"state": "not_applicable"}), ("o_elec_kwh", {"state": "confirmed", "value": 1000})):
                st, out = put(pid, fid, body)
                self.assertEqual(st, 200, out)
                self.assertIsInstance(out["updated_at"], float, out)
                times.append(out["updated_at"])
            self.assertEqual(out.get("warning_fields"), ["o_grid_value"], out)
            self.assertEqual(times, sorted(times))
            self.assertEqual(len(set(times)), len(times))                       # the screen orders the answers by it
            cid = app.projects.propose(pid, Value("o_gas_m3", "from_drawing", 9.0, "m3/年", method="document",
                                                  source_id="doc1-test.csv", source_detail="Sheet1!B3"), "test")
            st, out = app.handle("POST", "/api/projects/%d/fields/o_gas_m3/accept" % pid, {"id": cid})
            self.assertEqual(st, 200, out)
            self.assertGreater(out["updated_at"], times[-1], out)
        finally:
            app.engine.close()
            app.projects.close()
            td.cleanup()

    def test_words_naming_rows_not_saved_stay_on_another_project_with_a_warning(self):
        r = self.flow("heldNamedElsewhere")
        self.assertEqual(r["where0"]["view"], "settings", r)
        s = r["said"]
        self.assertTrue(s["text"].startswith(STOP) and "「都市ガス」は保存していません" in s["text"], s)
        self.assertIn(WARN_GRID, s["all"], s)
        b = r["onB"]
        self.assertTrue(b["shown"] and b["sticky"] and b["close"], b)
        self.assertTrue(b["text"].startswith("「HeldA」：" + STOP), b)          # it was dropped, only the warning stayed
        self.assertIn("「都市ガス」は保存していません", b["text"], b)
        self.assertIn("「HeldA」：" + WARN_GRID, b["all"], b)
        a = r["onA"]
        self.assertTrue(a["text"].startswith(STOP) and "「都市ガス」は保存していません" in a["text"], a)
        self.assertIsNone(r["gas"]["value"], r)

    def test_service_worker_cache_is_new(self):
        sw = (WEB / "sw.js").read_text(encoding="utf-8")
        m = re.search(r'"wlcstudio-shell-v(\d+)"', sw)
        self.assertTrue(m, sw)
        self.assertGreaterEqual(int(m.group(1)), 14)
        self.assertNotIn('"wlcstudio-shell-v13"', sw)


if __name__ == "__main__":
    unittest.main()
