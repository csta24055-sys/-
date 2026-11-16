"""Round 12 (the screens): a row the user has touched since it was drawn is kept across every redraw whatever its text
(also when it equals the value drawn: the first key of a correction, a revert, an emptied row being retyped);
保存して戻る never writes into a row the user emptied and never saves a value the user did not type; a text quantity
wraps at phone width; the second tap of a double tap on ← is ignored also when the batch has just left; #geo-out shows
only the answer of the latest request; the 自動概算 explanation waits while the user is typing.

The flows are run in a real browser (Playwright for node, against a server started on a free port with a temporary
var directory) when node and Playwright are installed; the functions are also checked one by one with node.

Run: cd whole-life-carbon-jcat-study/23_WLC_STUDIO_APP && python3 -B -m unittest discover -s tests -t .
"""
from __future__ import annotations

import json
import os
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

# the flows of the findings, each in a fresh phone-size page of the fictional demo; prints {flow: result}
FLOWS = r"""
const { chromium, devices } = require('playwright');
const BASE = process.argv[1];
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function open(browser, view = 'demo') {
  const ctx = await browser.newContext({ ...devices['iPhone 13'], deviceScaleFactor: 1, reducedMotion: 'reduce', serviceWorkers: 'block' });
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
  await page.goto(BASE + '/');
  await page.click('#splash');
  await page.waitForSelector('#main:not([hidden]) #demo');
  await page.click('#demo');
  await page.waitForFunction(() => state.view === 'hub' && !!document.querySelector('[data-screen]'));
  return { ctx, page, errors, pid: await page.evaluate(() => state.project.id) };
}
const screen = (page, sid) => page.click(`[data-screen="${sid}"]`).then(() => page.waitForFunction((s) => state.view === 'screen' && state.arg === s && !!document.querySelector('#bb-hub'), sid));
const hold = (page, method, re, ms) => page.route((u) => re.test(u.pathname), async (route) => {
  if (route.request().method() !== method) return route.continue();
  await sleep(ms); return route.continue();
});
const stored = (page, pid, fid) => page.evaluate(async ([pid, fid]) => {
  const f = (await (await fetch('/api/projects/' + pid)).json()).fields[fid] || {};
  return { value: f.value ? f.value.value : null, hist: (f.history || []).map((h) => h.value) };
}, [pid, fid]);
const toasts = (page) => page.evaluate(() => window.__toasts.splice(0));
const val = (page, fid) => page.inputValue('#in-' + fid);
const answered = (page) => page.waitForFunction(() => state.pending.size === 0 && !state.busy, null, { timeout: 30000 }).then(() => page.waitForTimeout(150));
const retype = async (page, fid, text) => { await page.click('#in-' + fid); await page.keyboard.press('Control+A'); await page.keyboard.type(text); };
const F = {};

// ui-flows#0 (a): the late answer of 地上階数's own 保存 (3) comes while the row holds the first key of the correction 12,
// which equals the value drawn (1)
F.equalToDrawn = async (b) => {
  const { page, pid, errors } = await open(b);
  await screen(page, 'basic');
  const drawn = await val(page, 'b_floors_above');
  await hold(page, 'PUT', /\/fields\/b_floors_above$/, 1000);
  await retype(page, 'b_floors_above', '3');
  await page.click('[data-save="b_floors_above"]');
  await page.waitForTimeout(100);
  await retype(page, 'b_floors_above', drawn);
  await answered(page);
  const atAnswer = await val(page, 'b_floors_above');
  await page.keyboard.type('2');
  const typed = await val(page, 'b_floors_above'), t = await toasts(page);
  await page.unrouteAll();
  await page.click('[data-save="b_floors_above"]'); await answered(page);
  return { drawn, atAnswer, typed, t, stored: await stored(page, pid, 'b_floors_above'), errors };
};
// ui-flows#0 (b): ガラス drawn empty; 750 sent, then deleted with Backspace (the row holds '' = what was drawn) when the
// answer comes; 985 typed next
F.emptiedRetyped = async (b) => {
  const { page, pid, errors } = await open(b);
  await screen(page, 'material');
  const drawn = await val(page, 'm_glass');
  await hold(page, 'PUT', /\/fields\/m_glass$/, 1000);
  await page.click('#in-m_glass'); await page.keyboard.type('750');
  await page.click('[data-save="m_glass"]');
  await page.waitForTimeout(100);
  await page.click('#in-m_glass'); await page.keyboard.press('End');
  for (let i = 0; i < 3; i++) await page.keyboard.press('Backspace');
  await answered(page);
  const atAnswer = await val(page, 'm_glass');
  await page.keyboard.type('985');
  const typed = await val(page, 'm_glass'), t = await toasts(page);
  await page.unrouteAll();
  await page.click('[data-save="m_glass"]'); await answered(page);
  return { drawn, atAnswer, typed, t, stored: await stored(page, pid, 'm_glass'), errors };
};
// ui-flows#0 (p1c): 保存して戻る sent 3 for 地上階数; the row is corrected back to the value drawn (1) and 建物の高さ is
// made unreadable (1x), so the batch stays
F.stayKeepsCorrection = async (b) => {
  const { page, pid, errors } = await open(b);
  await screen(page, 'basic');
  const drawn = await val(page, 'b_floors_above');
  await hold(page, 'PUT', /\/fields\//, 900);
  await retype(page, 'b_floors_above', '3'); await retype(page, 'b_height', '11');
  await toasts(page);
  await page.click('#bb-hub');
  await page.waitForTimeout(250);
  await retype(page, 'b_floors_above', drawn); await retype(page, 'b_height', '1x');
  await answered(page);
  return { drawn, shown: await val(page, 'b_floors_above'), height: await val(page, 'b_height'), view: await page.evaluate(() => state.view),
    t: await toasts(page), stored: await stored(page, pid, 'b_floors_above'), errors };
};
// ui-flows#0 (p1d): 地上階数's own 保存 (3) is under way, the row is corrected back to 1, then 保存して戻る is pressed
F.pendingThenBatch = async (b) => {
  const { page, pid, errors } = await open(b);
  await screen(page, 'basic');
  const drawn = await val(page, 'b_floors_above');
  await hold(page, 'PUT', /\/fields\/b_floors_above$/, 1000);
  await retype(page, 'b_floors_above', '3');
  await page.click('[data-save="b_floors_above"]');
  await page.waitForTimeout(150);
  await retype(page, 'b_floors_above', drawn);
  await toasts(page);
  await page.click('#bb-hub');
  await answered(page);
  return { drawn, view: await page.evaluate(() => state.view), t: await toasts(page), stored: await stored(page, pid, 'b_floors_above'), errors };
};
// ui-flows#1: 5, 11 and 900 typed; 保存して戻る; while the first row is saved, 建築面積 (the last of the three) is emptied
// to retype it; 7 is typed once the batch has passed it
F.batchEmptied = async (b) => {
  const { page, pid, errors } = await open(b);
  await screen(page, 'basic');
  await hold(page, 'PUT', /\/fields\//, 700);
  await retype(page, 'b_floors_above', '5'); await retype(page, 'b_height', '11'); await retype(page, 'b_footprint', '900');
  await toasts(page);
  await page.click('#bb-hub');
  await page.waitForTimeout(250);
  await page.click('#in-b_footprint'); await page.keyboard.press('End');
  for (let i = 0; i < 4; i++) await page.keyboard.press('Backspace');
  // every value the row shows from now on
  await page.evaluate(() => { window.__seen = new Set(); window.__iv = setInterval(() => { const x = document.querySelector('#in-b_footprint'); if (x) window.__seen.add(x.value); }, 10); });
  await answered(page);
  const seen = await page.evaluate(() => { clearInterval(window.__iv); return [...window.__seen]; });
  let typed = null;                                                    // (the batch has left: nothing to type in)
  if (await page.evaluate(() => state.view === 'screen')) { await page.keyboard.type('7'); typed = await val(page, 'b_footprint'); }
  await page.waitForTimeout(300);
  return { seen, typed, view: await page.evaluate(() => state.view), t: await toasts(page), stored: await stored(page, pid, 'b_footprint'),
    others: [(await stored(page, pid, 'b_floors_above')).value, (await stored(page, pid, 'b_height')).value], errors };
};
// ui-flows#5: ← tapped during 保存して戻る (the warning), the batch then leaves for the hub, and the second tap of the same
// double tap comes right after
F.doubleTapAfterBatch = async (b) => {
  const { page, errors } = await open(b);
  await screen(page, 'basic');
  let release; const gate = new Promise((r) => (release = r));
  await page.route((u) => /\/fields\/b_height$/.test(u.pathname), async (route) => { if (route.request().method() === 'PUT') await gate; return route.continue(); });
  await retype(page, 'b_height', '11');
  await page.click('#bb-hub');
  await page.waitForTimeout(150);
  await page.click('#btn-back');
  const first = await page.evaluate(() => ({ view: state.view, busy: state.busy }));
  release();
  await page.waitForFunction(() => state.view === 'hub', null, { polling: 'raf', timeout: 30000 });
  const since = await page.evaluate(() => Date.now() - state.busyWarned);
  await page.click('#btn-back');
  await page.waitForTimeout(400);
  return { first, since, view: await page.evaluate(() => state.view), t: await toasts(page), errors };
};
// ui-flows#6: two address searches answered out of order; a PLATEAU read overtaken by a new search; PLATEAU finds
// nothing; the new list's button while the old list's PLATEAU read is under way
F.geo = async (b) => {
  const { page, errors } = await open(b);
  await screen(page, 'basic');
  const A = { 丸の内: ['東京都千代田区丸の内一丁目', 35.681], 大手町: ['東京都千代田区大手町一丁目', 35.686] };
  const cfg = { addrHold: {}, plHold: 0, plEmpty: false, asked: [] };
  await page.route((u) => /\/research\/address$/.test(u.pathname), async (route) => {
    const q = JSON.parse(route.request().postData()).query;
    if (cfg.addrHold[q]) await sleep(cfg.addrHold[q]);
    return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ candidates: [{ title: A[q][0], lat: A[q][1], lon: 139.76, precision: 'town' }], note: 'テスト' }) });
  });
  await page.route((u) => /\/research\/plateau$/.test(u.pathname), async (route) => {
    const a = JSON.parse(route.request().postData()).address; cfg.asked.push(a);
    const empty = cfg.plEmpty, ms = cfg.plHold;
    if (ms) await sleep(ms);
    return route.fulfill({ contentType: 'application/json', body: JSON.stringify(empty ? { candidates: [], note: '近くに建物が見つからなかった' }
      : { candidates: [{ usage: '業務施設', storeys_above: 8, storeys_below: 1, measured_height_m: 33.5, contains_point: true, address: a, structure_code: 'RC', survey_year: '2020', plateau_building_id: 'B-' + a }], note: 'テスト' }) });
  });
  const text = () => page.locator('#geo-out').innerText();
  const search = async (q) => { await page.fill('#addr', q); await page.click('#btn-geo'); };
  const r = {};
  // the first candidate's PLATEAU button of the list shown (said at once when there is none: the list was replaced)
  const plateau0 = async () => {
    if (!(await page.locator('#geo-out [data-geo="0"]').count())) throw new Error('no address list in #geo-out: ' + JSON.stringify({ ...r, now: await text() }));
    await page.click('#geo-out [data-geo="0"]');
  };
  cfg.addrHold = { 丸の内: 800 };
  await search('丸の内'); await page.waitForTimeout(150); await search('大手町'); await page.waitForTimeout(1100);
  r.outOfOrder = await text();
  cfg.addrHold = {}; cfg.plHold = 800;
  await plateau0(); await page.waitForTimeout(150); await search('丸の内'); await page.waitForTimeout(1100);
  r.plateauOvertaken = await text();
  cfg.plHold = 0; cfg.plEmpty = true;
  await plateau0(); await page.waitForTimeout(400);
  r.none = await text();
  cfg.plHold = 1000; cfg.plEmpty = false;
  await plateau0(); await page.waitForTimeout(150); await search('大手町'); await page.waitForTimeout(300);
  const n = cfg.asked.length;
  await plateau0(); await page.waitForTimeout(200);
  r.askedByNewList = cfg.asked.slice(n);
  await page.waitForTimeout(1300);
  r.last = await text();
  return { ...r, errors };
};
// ui-flows#7: 自動概算 on ボード類 is answered while the user types 98500123 in ガラス, one key every 250 ms
F.noteWhileTyping = async (b) => {
  const { page, errors } = await open(b);
  await screen(page, 'material');
  await hold(page, 'POST', /\/estimate$/, 600);
  await page.click('[data-est="m_board"]');
  await page.click('#in-m_glass'); await page.keyboard.press('Control+A');
  let dlgWhileTyping = false;
  for (const k of '98500123') {
    await page.keyboard.type(k); await page.waitForTimeout(250);
    dlgWhileTyping = dlgWhileTyping || await page.evaluate(() => !!document.querySelector('dialog[open]'));
  }
  const typed = await val(page, 'm_glass');
  await page.evaluate(() => document.activeElement.blur());           // the user leaves the field
  await page.waitForFunction(() => !!document.querySelector('dialog[open]'), null, { timeout: 10000 }).catch(() => {});
  const after = await page.evaluate(() => { const d = document.querySelector('dialog[open]'); return d ? d.querySelector('h2').textContent : null; });
  return { typed, dlgWhileTyping, after, errors };
};
// ui-flows#4: a left-out row whose quantity is a text of 26 characters, at 390 px
F.textQuantity = async (b) => {
  const { page, errors } = await open(b);
  await screen(page, 'material');
  await page.evaluate(() => {
    state.project.fields.m_concrete.candidates = [{ id: 99901, value: 300, unit: 'm3', state: 'from_drawing', method: 'document', source_id: 'doc1',
      n_rows: 1, rows: [{ name: '普通コンクリート', trace: 'doc1:csv!R2C3', quantity: 300, unit: 'm3' }], n_excluded: 1, n_maybe: 1,
      excluded: [{ name: 'コンクリート', trace: 'doc1:csv!R3C3', reason: '数量が数値でない', quantity: '設計変更により増減あり別途協議のうえ決定する数量参考値', unit: 'm3', maybe: true }] }];
    return render();
  });
  return { ...(await page.evaluate(() => {
    document.querySelectorAll('#f-m_concrete details').forEach((d) => (d.open = true));
    const q = document.querySelector('#f-m_concrete details[id^="cx-"] li span:not(.muted)');
    return { sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth, hub: Math.round(document.querySelector('#bb-hub').getBoundingClientRect().right),
      cls: q ? q.className : null, text: q ? q.textContent : null };
  })), errors };
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
    // two flows at a time (the server has one worker: more would queue its answers behind each other); the timed
    // double tap runs alone first
    await run('doubleTapAfterBatch');
    const rest = Object.keys(F).filter((k) => k !== 'doubleTapAfterBatch');
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


class TwelfthRoundUiTests(unittest.TestCase):
    """Regression tests for the twelfth verification round, screens (docs/review_fixes.md, round 12)."""

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

    # ---- ui-flows#0: a row touched since the draw is kept, whatever its text ----

    def test_rows_touched_since_the_draw_are_kept(self):
        out = node(TAKE + r"""
var CSS = { escape: (s) => s };
const els = {};
const inp = (id, value, def, touched) => (els[id] = { id, tagName: 'INPUT', value, defaultValue: def, dataset: touched ? { touched: '1' } : {} });
var document = { querySelectorAll: () => ['b_floors_above', 'm_glass', 'b_height', 'b_footprint'].map((f) => ({ dataset: { save: f } })),
  querySelector: (s) => els[s.slice(1)] || null, getElementById: (id) => els[id] || null };
var $ = (s) => document.querySelector(s);
inp('in-b_floors_above', '1', '1', true);       // the first key of the correction 12: equals the value drawn
inp('in-m_glass', '', '', true);                // emptied to be retyped: equals the value drawn (empty)
inp('in-b_height', '11', '11', false);          // not touched
inp('in-b_footprint', '900', '1745', false);    // differs from what was drawn
eval(take(/function drawn\(el\)[\s\S]*?\n}\n/));
eval(take(/const touchedRow = [^\n]*\n/).replace('const touchedRow', 'var touchedRow'));
eval(take(/function typedRows[\s\S]*?\n}\n/));
eval(take(/function restoreTyped[\s\S]*?\n}\n/));
const all = typedRows(), dropped = typedRows(['b_floors_above']);
inp('in-b_floors_above', '3', '3', false);      // a redraw drew the stored 3
restoreTyped({ b_floors_above: all.b_floors_above });
console.log(JSON.stringify({ all: Object.keys(all).sort(), dropped: Object.keys(dropped).sort(), back: els['in-b_floors_above'].value,
  touched: els['in-b_floors_above'].dataset.touched || null }));
""")
        if out is None:
            self.skipTest("node is not installed")
        self.assertEqual(out["all"], ["b_floors_above", "b_footprint", "m_glass"])
        self.assertEqual(out["dropped"], ["b_footprint", "m_glass"])
        self.assertEqual(out["back"], "1")
        self.assertEqual(out["touched"], "1")                                # still the user's after the redraw

    def test_late_answer_keeps_a_row_equal_to_the_drawn_value(self):
        r = self.flow("equalToDrawn")
        self.assertEqual(r["atAnswer"], r["drawn"], r)                       # not replaced by the stored 3
        self.assertEqual(r["typed"], r["drawn"] + "2", r)                    # 12, never 32
        self.assertEqual(r["stored"]["value"], int(r["drawn"] + "2"), r)
        self.assertTrue(any("まだ保存していない入力" in x and "地上階数" in x for x in r["t"]), r["t"])

    def test_late_answer_keeps_an_emptied_row_being_retyped(self):
        r = self.flow("emptiedRetyped")
        self.assertEqual(r["drawn"], "")
        self.assertEqual(r["atAnswer"], "", r)                               # the sent 750 is not put back
        self.assertEqual(r["typed"], "985", r)                               # never 985750
        self.assertEqual(r["stored"]["value"], 985, r)
        self.assertNotIn(985750, r["stored"]["hist"])
        self.assertTrue(any("ガラス" in x and "空欄" in x for x in r["t"]), r["t"])

    def test_batch_stay_keeps_a_correction_back_to_the_drawn_value(self):
        r = self.flow("stayKeepsCorrection")
        self.assertEqual(r["view"], "screen", r)
        self.assertEqual(r["shown"], r["drawn"], r)                          # the correction is on screen, as the message says
        self.assertEqual(r["height"], "1x", r)
        self.assertEqual(r["stored"]["value"], 3, r)
        self.assertTrue(any("直す前の値を保存しました" in x and "地上階数" in x for x in r["t"]), r["t"])

    def test_batch_after_a_pending_save_keeps_a_correction_back_to_the_drawn_value(self):
        r = self.flow("pendingThenBatch")
        self.assertEqual(r["stored"]["value"], int(r["drawn"]), r)          # what the screen showed is what is stored
        self.assertEqual(r["view"], "hub", r)
        self.assertTrue(any("地上階数" in x and "保存しました" in x for x in r["t"]), r["t"])

    # ---- ui-flows#1: 保存して戻る never refills an emptied row ----

    def test_batch_never_refills_an_emptied_row(self):
        r = self.flow("batchEmptied")
        self.assertNotIn(900, r["stored"]["hist"], r)                        # the withdrawn 900 is not saved
        self.assertEqual(r["seen"], [""], r)                                 # nothing was written into the row
        self.assertEqual(r["view"], "screen", r)                             # the emptied row is named, the batch stays
        self.assertTrue(any("空欄にした「建築面積」は保存していません" in x and "「地上階数」「建物の高さ」は保存しました" in x
                            for x in r["t"]), r["t"])
        self.assertEqual(r["typed"], "7", r)                                 # never 9007
        self.assertEqual(r["stored"]["value"], 1745, r)
        self.assertEqual(r["others"], [5, 11], r)

    def test_the_batch_does_not_restore_typed_text(self):
        self.assertNotIn("restoreTyped({ [fid]: snap[fid] })", self.js)
        self.assertIn("if (inputValue(fid).empty) continue;", self.js)
        # an emptied value is shown again only outside the input the user is in
        self.assertIn("if (!el || el === document.activeElement) return;", self.js)

    # ---- ui-flows#4: a text quantity wraps ----

    def test_text_quantity_wraps(self):
        out = node(TAKE + r"""
eval(take(/const esc = [^\n]*\n/).replace('const esc', 'var esc'));
eval(take(/function fmt[\s\S]*?\n}\n/));
eval(take(/function candRows[\s\S]*?\n}\n/));
const TXT = '設計変更により増減あり別途協議のうえ決定する数量参考値';
console.log(JSON.stringify(candRows('m_concrete', { id: 7, value: 300, unit: 'm3', n_rows: 1, rows: [{ name: '普通コンクリート', trace: 'R2C3', quantity: 300, unit: 'm3' }],
  n_excluded: 2, n_maybe: 1, excluded: [{ name: 'コンクリート', trace: 'R3C3', reason: '数量が数値でない', quantity: TXT, unit: 'm3', maybe: true },
  { name: 'コンクリート打設手間', trace: 'R4C3', reason: '作業の行', quantity: 1034, unit: 'm3' }] })));
""")
        if out is None:
            self.skipTest("node is not installed")
        rows = out["rows"]
        self.assertIn('<span class="qtext">設計変更により増減あり別途協議のうえ決定する数量参考値 m3</span>', rows)
        self.assertIn('<span class="num">1,034 m3</span>', rows)                 # a number stays on one line
        self.assertIn('<span class="num">300 m3</span>', rows)
        rule = next((ln for ln in self.css.splitlines() if ln.startswith("ul.crows .qtext")), "")
        self.assertIn("white-space: normal", rule)
        self.assertIn("overflow-wrap: anywhere", rule)

    def test_text_quantity_fits_390(self):
        r = self.flow("textQuantity")
        self.assertEqual(r["cls"], "qtext", r)
        self.assertLessEqual(r["sw"], r["cw"], r)
        self.assertLessEqual(r["hub"], r["cw"], r)                           # 保存して戻る is on screen

    # ---- ui-flows#5: a double tap on ← after the batch left ----

    def test_second_tap_after_the_batch_ended_is_ignored(self):
        out = node(TAKE + r"""
var state = { busy: false, busyWarned: Date.now() - 150, act: 0, view: 'hub' };
function toast() {}
eval(take(/function blocked\(\)[\s\S]*?\n}\n/));
const r = [blocked(), state.busyWarned];
r.push(blocked());                                   // the next press is a press of its own
state.busyWarned = Date.now() - 600; r.push(blocked());
console.log(JSON.stringify(r));
""")
        if out is None:
            self.skipTest("node is not installed")
        self.assertEqual(out, [True, 0, False, False])
        self.assertIn("state.busy = false; back(true);", self.js)              # the batch's own move is not a press

    def test_double_tap_on_back_after_the_batch_ends_on_the_hub(self):
        r = self.flow("doubleTapAfterBatch")
        self.assertEqual(r["first"], {"view": "screen", "busy": True}, r)
        if r["since"] > 300:
            self.skipTest("the batch took %d ms to leave: too slow to tap within 400 ms of the warning" % r["since"])
        self.assertEqual(r["view"], "hub", r)

    # ---- ui-flows#6: #geo-out shows the latest answer ----

    def test_geo_buttons_are_known_by_their_list(self):
        out = node(TAKE + r"""
var CSS = { escape: (s) => String(s) };
var document = { body: {} };
eval(take(/const KEYS = [\s\S]*?\];\n/).replace('const KEYS', 'var KEYS'));
eval(take(/function keyOf[\s\S]*?\n}\n/));
const b = (attrs) => ({ tagName: 'BUTTON', id: '', getAttribute: (k) => attrs[k] ?? null, hasAttribute: (k) => k in attrs, dataset: {} });
console.log(JSON.stringify([keyOf(b({ 'data-geo': '0', 'data-list': '3' })), keyOf(b({ 'data-b': '1', 'data-list': '4' }))]));
""")
        if out is None:
            self.skipTest("node is not installed")
        self.assertEqual(out, ['[data-geo="0"][data-list="3"]', '[data-b="1"][data-list="4"]'])
        self.assertIn('data-geo="${i}" data-list="${seq}"', self.js)
        self.assertIn("state.geoSeq === seq", self.js)

    def test_geo_shows_only_the_latest_answer(self):
        r = self.flow("geo")
        self.assertIn("大手町", r["outOfOrder"], r)                          # the newer search, not the late 丸の内
        self.assertNotIn("丸の内", r["outOfOrder"], r)
        self.assertIn("丸の内一丁目", r["plateauOvertaken"], r)              # the newer address list stays
        self.assertNotIn("近くの建物", r["plateauOvertaken"], r)
        self.assertNotIn("読んでいます", r["none"], r)                       # the reading line goes on every outcome
        self.assertIn("近くに建物が見つからなかった", r["none"], r)
        self.assertEqual(r["askedByNewList"], ["東京都千代田区大手町一丁目"], r)   # the new list's button works
        self.assertIn("B-東京都千代田区大手町一丁目", r["last"], r)
        self.assertNotIn("読んでいます", r["last"], r)

    # ---- ui-flows#7: the explanation waits while the user types ----

    def test_estimate_note_waits_while_typing(self):
        r = self.flow("noteWhileTyping")
        self.assertFalse(r["dlgWhileTyping"], r)
        self.assertEqual(r["typed"], "98500123", r)                          # every key reached the field
        self.assertEqual(r["after"], "自動概算の説明", r)                      # shown once the field is left

    def test_service_worker_cache_is_new(self):
        sw = (WEB / "sw.js").read_text(encoding="utf-8")
        self.assertIn('"wlcstudio-shell-v11"', sw)
        self.assertNotIn('"wlcstudio-shell-v10"', sw)


if __name__ == "__main__":
    unittest.main()
