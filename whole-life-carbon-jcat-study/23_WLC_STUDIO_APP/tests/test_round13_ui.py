"""Round 13 (the screens): 保存して戻る pressed while a row's own 未取得に戻す / 適用外 / 計算不能 / この候補を採用 is still
answering no longer saves the text typed in that row over the action (the acted row is owed its stored value, and the
batch's redraw pays it; a row typed into again after the action is kept and saved); a blocked calculation shows why each
missing input is not used (a stored 適用外 that another input no longer allows is named with its reason); the warnings a
save's answer carries are said, also from 保存して戻る and also after it has left for the hub; 保存して戻る names what the
rows' own actions under way stored instead of 「保存する変更はありませんでした」; a calendar year is shown without a thousands
separator; the app that cannot reach its server says so in Japanese with 再読み込み, under the door.

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
async function page0(browser) {
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
  return { ctx, page, errors };
}
async function open(browser) {
  const { ctx, page, errors } = await page0(browser);
  await page.goto(BASE + '/');
  // the door opens once the app has started (/api/meta answered): a tap before that does nothing
  await page.waitForFunction(() => typeof state !== 'undefined' && !!state.meta && !!document.getElementById('splash').onclick);
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
  return { state: f.value ? f.value.state : null, value: f.value ? f.value.value : null, method: f.value ? f.value.method : null,
    hist: (f.history || []).map((h) => [h.state, h.value]) };
}, [pid, fid]);
const put = (page, pid, fid, body) => page.evaluate(async ([pid, fid, body]) => {
  const r = await fetch('/api/projects/' + pid + '/fields/' + fid, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  return r.status;
}, [pid, fid, body]);
const toasts = (page) => page.evaluate(() => window.__toasts.splice(0));
const toastNow = (page) => page.evaluate(() => { const t = document.getElementById('toast'); return t.classList.contains('show') ? t.textContent : ''; });
const answered = (page) => page.waitForFunction(() => state.pending.size === 0 && !state.busy, null, { timeout: 30000 }).then(() => page.waitForTimeout(150));
const retype = async (page, fid, text) => { await page.click('#in-' + fid); await page.keyboard.press('Control+A'); await page.keyboard.type(text); };
const view = (page) => page.evaluate(() => state.view);
const width = (page) => page.evaluate(() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth }));
const F = {};

// ui-flows#0: a row holds typed text; that row's own action is pressed, and 保存して戻る 60 ms later, while the action is
// still answering (held 800 ms)
const actThenBatch = async (b, sid, fid, typed, act, holdM, holdRe, setup) => {
  const { page, pid, errors } = await open(b);
  await screen(page, sid);
  if (setup) await setup(page);
  await retype(page, fid, typed);
  await toasts(page);
  await hold(page, holdM, holdRe, 800);
  await page.locator(act).first().click();
  await page.waitForTimeout(60);
  await page.click('#bb-hub');
  await answered(page);
  return { view: await view(page), t: await toasts(page), stored: await stored(page, pid, fid), errors };
};
F.unsetThenBatch = (b) => actThenBatch(b, 'basic', 'b_height', '77', '[data-unset="b_height"]', 'PUT', /\/fields\/b_height$/);
F.naThenBatch = (b) => actThenBatch(b, 'operation', 'o_grid_value', '0.5', '[data-na="o_grid_value"]', 'PUT', /\/fields\/o_grid_value$/,
  async (page) => { await retype(page, 'o_elec_kwh', '0'); await page.click('[data-save="o_elec_kwh"]'); await answered(page); });
F.ncThenBatch = (b) => actThenBatch(b, 'basic', 'b_floors_above', '9', '[data-nc="b_floors_above"]', 'PUT', /\/fields\/b_floors_above$/);
F.acceptThenBatch = (b) => actThenBatch(b, 'material', 'm_rebar', '12.5', '#f-m_rebar [data-accept]', 'POST', /\/fields\/m_rebar\/accept$/,
  async (page) => {
    await page.setInputFiles('#docfile', { name: 'bill.csv', mimeType: 'text/csv', buffer: Buffer.from('名称,規格,数量,単位\n異形鉄筋,SD345 D19,95.5,t\n') });
    await page.waitForSelector('#f-m_rebar [data-accept]', { timeout: 30000 });
    await answered(page);
  });
// ui-flows#0: the user types into the acted row again after the action was sent: what they typed is kept and saved
F.typedAgain = async (b) => {
  const { page, pid, errors } = await open(b);
  await screen(page, 'basic');
  await retype(page, 'b_height', '77');
  await hold(page, 'PUT', /\/fields\/b_height$/, 800);
  await page.click('[data-unset="b_height"]');
  await page.waitForTimeout(100);
  await retype(page, 'b_height', '55');
  await toasts(page);
  await page.click('#bb-hub');
  await answered(page);
  return { view: await view(page), t: await toasts(page), stored: await stored(page, pid, 'b_height'), errors };
};
// ui-flows#2: a row's own 保存 (held 700 ms) is under way when 保存して戻る is pressed 80 ms later
F.pendingSave = async (b) => {
  const { page, pid, errors } = await open(b);
  await screen(page, 'basic');
  await retype(page, 'b_floors_above', '12');
  await hold(page, 'PUT', /\/fields\/b_floors_above$/, 700);
  await page.click('[data-save="b_floors_above"]');
  await page.waitForTimeout(80);
  await toasts(page);
  await page.click('#bb-hub');
  await answered(page);
  return { view: await view(page), t: await toasts(page), stored: await stored(page, pid, 'b_floors_above'), errors };
};
// ui-flows#1: the grid factor set to 適用外 while 購入電力 is 0; 購入電力 then 1000; 計算する is blocked
const blocked = async (b, setup) => {
  const { page, pid, errors } = await open(b);
  await setup(page, pid);
  await page.click('#to-result');
  await page.waitForFunction(() => state.view === 'result' && !!document.querySelector('#calc'));
  await page.click('#calc');
  await page.waitForFunction(() => /計算していません/.test(document.querySelector('#res').textContent), null, { timeout: 60000 });
  await page.evaluate(() => document.querySelectorAll('#res details').forEach((d) => (d.open = true)));
  const res = await page.locator('#res').innerText();
  return { res, missing: await page.locator('#res .card').first().innerText(), ...(await width(page)), errors };
};
F.blockedGrid = (b) => blocked(b, async (page) => {
  await screen(page, 'operation');
  await retype(page, 'o_elec_kwh', '0'); await page.click('[data-save="o_elec_kwh"]'); await answered(page);
  await page.click('[data-na="o_grid_value"]'); await answered(page);
  await retype(page, 'o_elec_kwh', '1000'); await page.click('[data-save="o_elec_kwh"]'); await answered(page);
  await page.click('#bb-back');
  await page.waitForFunction(() => state.view === 'hub');
});
// the route: 適用外 accepted while the stages are unknown, then the stages are set again (its missing item has another name)
F.blockedRoute = (b) => blocked(b, async (page, pid) => {
  const st = await stored(page, pid, 'a_stages');
  await put(page, pid, 'a_stages', { value: null, state: 'not_obtained', method: 'user_entered' });
  await put(page, pid, 'a_eol_route', { value: null, state: 'not_applicable', method: 'user_entered' });
  await put(page, pid, 'a_stages', { value: st.value, unit: '', state: 'confirmed', method: 'user_entered' });
  await page.evaluate(() => loadProject(state.project.id).then(render));
});
// ui-flows#1: the answer of a save carries `warnings` (added here to the server's answer): a row 保存, a row action, a
// 保存して戻る, and a row action answered while 保存して戻る waits for it
F.warnings = async (b) => {
  const { page, errors } = await open(b);
  const cfg = { hold: {} };
  await page.route((u) => /\/fields\/[^/]+$/.test(u.pathname), async (route) => {
    if (route.request().method() !== 'PUT') return route.continue();
    const fid = new URL(route.request().url()).pathname.split('/').pop();
    if (cfg.hold[fid]) await sleep(cfg.hold[fid]);
    const res = await route.fetch(), j = await res.json();
    if (res.ok()) j.warnings = ['テスト警告（' + fid + '）'];
    return route.fulfill({ response: res, body: JSON.stringify(j), contentType: 'application/json' });
  });
  await screen(page, 'operation');
  const r = {};
  await toasts(page);
  await retype(page, 'o_elec_kwh', '1000'); await page.click('[data-save="o_elec_kwh"]'); await answered(page);
  r.rowSave = await toasts(page);
  await page.click('[data-nc="o_oil_l"]'); await answered(page);
  r.rowAction = await toasts(page);
  await retype(page, 'o_gas_m3', '321'); await page.click('#bb-hub'); await answered(page);
  r.batchView = await view(page); r.batch = await toasts(page); r.batchNow = await toastNow(page);
  await screen(page, 'operation');
  cfg.hold.o_dheat_mj = 700;
  await page.click('[data-nc="o_dheat_mj"]'); await page.waitForTimeout(60);
  await toasts(page);
  await page.click('#bb-hub'); await answered(page);
  r.pendingView = await view(page); r.pending = await toasts(page); r.pendingNow = await toastNow(page);
  return { ...r, errors };
};
// ui-flows#4: the server cannot be reached when the app starts (the request for /api/meta fails, as offline); then it
// can, and 再読み込み starts the app
F.offline = async (b) => {
  const { ctx, page, errors } = await page0(b);
  await page.route('**/api/meta', (route) => route.abort('internetdisconnected'));
  await page.goto(BASE + '/');
  await page.waitForSelector('#boot-reload', { timeout: 30000 });
  const r = await page.evaluate(() => ({ splash: !!document.getElementById('splash'), body: document.body.innerText,
    detail: (document.querySelector('.boot-detail') || {}).textContent || null, focused: document.activeElement && document.activeElement.id,
    sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth,
    btn: Math.round(document.getElementById('boot-reload').getBoundingClientRect().bottom), vh: innerHeight }));
  await page.unroute('**/api/meta');
  await page.click('#boot-reload');
  await page.waitForFunction(() => typeof state !== 'undefined' && !!state.meta && !!document.getElementById('splash').onclick, null, { timeout: 30000 });
  r.afterReload = await page.evaluate(() => ({ error: !!document.querySelector('.boot-error'), splash: !document.getElementById('splash').hidden }));
  await page.click('#splash');
  await page.waitForSelector('#main:not([hidden]) #demo');
  r.started = true;
  await ctx.close();
  return { ...r, errors: errors.filter((e) => !/Failed to fetch/.test(e)) };
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


class ThirteenthRoundUiTests(unittest.TestCase):
    """Regression tests for the thirteenth verification round, screens (docs/review_fixes.md, round 13)."""

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

    # ---- ui-flows#0: 保存して戻る does not save the typed text over the row's own action ----

    def test_batch_keeps_unset_pressed_before_it_unless_retyped(self):
        r = self.flow("unsetThenBatch")
        self.assertEqual(r["stored"]["state"], "not_obtained", r)
        self.assertEqual(len(r["stored"]["hist"]), 2, r)                      # 4, then 未取得: 77 never saved
        self.assertNotIn(77, [h[1] for h in r["stored"]["hist"]], r)
        self.assertEqual(r["view"], "hub", r)
        self.assertTrue(any("「建物の高さ」は「未取得」になりました" in x for x in r["t"]), r["t"])
        # the user types into the row again after 未取得に戻す was sent: what they typed is kept and saved
        r = self.flow("typedAgain")
        self.assertEqual(r["stored"]["value"], 55, r)
        self.assertEqual([h[0] for h in r["stored"]["hist"]], ["confirmed", "not_obtained", "confirmed"], r)
        self.assertNotIn(77, [h[1] for h in r["stored"]["hist"]], r)
        self.assertEqual(r["view"], "hub", r)
        self.assertTrue(any("保存しました" in x and "「建物の高さ」" in x for x in r["t"]), r["t"])

    def test_batch_keeps_not_applicable_pressed_before_it(self):
        r = self.flow("naThenBatch")
        self.assertEqual(r["stored"]["state"], "not_applicable", r)
        self.assertNotIn(0.5, [h[1] for h in r["stored"]["hist"]], r)
        self.assertEqual(r["view"], "hub", r)
        self.assertTrue(any("「運用時の電力の排出係数」は「適用外」になりました" in x for x in r["t"]), r["t"])

    def test_batch_keeps_not_computable_pressed_before_it(self):
        r = self.flow("ncThenBatch")
        self.assertEqual(r["stored"]["state"], "not_computable", r)
        self.assertNotIn(9, [h[1] for h in r["stored"]["hist"]], r)
        self.assertTrue(any("「地上階数」は「計算不能」になりました" in x for x in r["t"]), r["t"])

    def test_batch_keeps_the_adopted_candidate(self):
        r = self.flow("acceptThenBatch")
        self.assertEqual(r["stored"]["state"], "from_drawing", r)
        self.assertEqual(r["stored"]["value"], 95.5, r)
        self.assertNotEqual(r["stored"]["method"], "user_entered", r)
        self.assertNotIn(12.5, [h[1] for h in r["stored"]["hist"]], r)
        self.assertTrue(any("「鉄筋」は「図面から計算」になりました" in x for x in r["t"]), r["t"])

    def test_owed_rows_are_paid_by_every_redraw(self):
        out = node(TAKE + r"""
const rows = { b_height: { v: '77', u: 'm', s: 'confirmed' }, b_floors_above: { v: '3', u: null, s: 'confirmed' }, b_footprint: { v: '9', u: 'm2', s: null } };
var state = { nav: 5, view: 'screen', owed: new Map() };
function rowNow(f) { return rows[f] || null; }
eval(take(/const sameRow = [^\n]*\n/).replace('const sameRow', 'var sameRow'));
eval(take(/function owedRows\(\)[\s\S]*?\n}\n/));
state.owed.set('b_height', { row: { v: '77', u: 'm', s: 'confirmed' }, n: 5 });         // unchanged since its action: shows the stored value
state.owed.set('b_floors_above', { row: { v: '2', u: null, s: 'confirmed' }, n: 5 });   // typed into since: kept
state.owed.set('b_footprint', { row: { v: '9', u: 'm2', s: null }, n: 4 });             // a view left since
const first = owedRows(), second = owedRows();
console.log(JSON.stringify({ first, second, left: state.owed.size }));
""")
        if out is None:
            self.skipTest("node is not installed")
        self.assertEqual(out, {"first": ["b_height"], "second": [], "left": 0})
        self.assertIn(".concat(owed)", self.js)                               # redraw drops them, whoever redraws
        self.assertIn("if (!shows()) return owe();", self.js)

    # ---- ui-flows#2: 保存して戻る names what a row's own 保存 stored ----

    def test_batch_names_a_row_saved_by_its_own_save(self):
        r = self.flow("pendingSave")
        self.assertEqual(r["stored"]["value"], 12, r)
        self.assertEqual(len(r["stored"]["hist"]), 2, r)                      # one PUT
        self.assertEqual(r["view"], "hub", r)
        self.assertIn("1 項目を保存しました（「地上階数」）", r["t"], r["t"])
        self.assertFalse(any("保存する変更はありませんでした" in x for x in r["t"]), r["t"])

    # ---- ui-flows#1: a blocked calculation says why; the warnings of a save are said ----

    def test_blocked_result_gives_the_reason_of_a_refused_not_applicable(self):
        r = self.flow("blockedGrid")
        self.assertIn("運用時の電力の排出係数", r["missing"], r)
        self.assertIn("適用外にはできない（購入電力があるので", r["missing"], r)    # in the missing card, next to the item
        self.assertIn("入力ごとの反映", r["res"], r)                                 # and every input's row
        self.assertLessEqual(r["sw"], r["cw"], r)

    def test_blocked_result_names_the_route_set_to_not_applicable(self):
        r = self.flow("blockedRoute")
        self.assertIn("解体後の処理シナリオ（材料の行ごとに必須）", r["missing"], r)
        self.assertIn("適用外にした必須の入力", r["missing"], r)
        self.assertIn("解体後の処理（シナリオ）", r["missing"], r)
        self.assertIn("適用外にはできない（解体時の質量が分かる材料の行があり", r["missing"], r)
        self.assertLessEqual(r["sw"], r["cw"], r)

    def test_missing_inputs_show_their_reason(self):
        out = node(TAKE + r"""
eval(take(/const esc = [^\n]*\n/).replace('const esc', 'var esc'));
var state = { meta: { states: { not_applicable: '適用外', not_obtained: '未取得' }, fields: { o_grid_value: { required: true }, a_eol_route: { required: true }, o_note: {} } } };
eval(take(/function badge[^\n]*\n/));
eval(take(/function missingHtml[\s\S]*?\n}\n/));
const r = { missing_required: ['運用時の電力の排出係数', '解体後の処理シナリオ（材料の行ごとに必須）'], unconnected: [],
  fields: [{ field: 'o_grid_value', label: '運用時の電力の排出係数', state: 'not_applicable', reflected: false, detail: '適用外にはできない（理由A）：渡していない' },
           { field: 'a_eol_route', label: '解体後の処理（シナリオ）', state: 'not_applicable', reflected: false, detail: '適用外にはできない（理由B）' },
           { field: 'o_note', label: 'メモ', state: 'not_applicable', reflected: false, detail: '適用外：渡していない' },
           { field: 'b_gfa', label: '延床面積', state: 'confirmed', reflected: true, detail: '渡した' }] };
console.log(JSON.stringify({ blocked: missingHtml(r, true), ok: missingHtml({ ...r, missing_required: [] }) }));
""")
        if out is None:
            self.skipTest("node is not installed")
        b = out["blocked"]
        self.assertIn("運用時の電力の排出係数", b)
        self.assertIn("適用外にはできない（理由A）：渡していない", b)
        self.assertIn("適用外にはできない（理由B）", b)                       # the route, though its missing item has another name
        self.assertNotIn("メモ", b)                                           # not required: not named
        self.assertNotIn("渡した", b)
        self.assertNotIn("適用外にはできない", out["ok"])

    def test_warnings_of_a_save_are_said(self):
        r = self.flow("warnings")
        self.assertTrue(any("テスト警告（o_elec_kwh）" in x for x in r["rowSave"]), r)
        self.assertTrue(any("テスト警告（o_oil_l）" in x for x in r["rowAction"]), r)
        # 保存して戻る: said with its message, and still shown on the hub
        self.assertEqual(r["batchView"], "hub", r)
        self.assertIn("テスト警告（o_gas_m3）", r["batchNow"], r)
        self.assertIn("項目を保存しました", r["batchNow"], r)
        # a row action answered while 保存して戻る waited for it
        self.assertEqual(r["pendingView"], "hub", r)
        self.assertIn("テスト警告（o_dheat_mj）", r["pendingNow"], r)
        self.assertIn("「地域熱供給」は「計算不能」になりました", r["pendingNow"], r)

    def test_warn_of_keeps_warnings_while_the_batch_runs(self):
        out = node(TAKE + r"""
var state = { busy: false, warnings: [] };
const said = [];
function toast(msg, act) { said.push([msg, act]); }
eval(take(/function warnOf[\s\S]*?\n}\n/));
eval(take(/function sayWarnings[^\n]*\n/));
warnOf({ warnings: ['A', '', 3] }, 7);
warnOf({}, 7); warnOf(null, 7);
state.busy = true; warnOf({ warnings: ['B', 'C'] }, 8);
const kept = state.warnings.slice(), before = said.length;
sayWarnings(9);
console.log(JSON.stringify({ said, kept, before, left: state.warnings.length }));
""")
        if out is None:
            self.skipTest("node is not installed")
        self.assertEqual(out["kept"], ["B", "C"])
        self.assertEqual(out["before"], 1)
        self.assertEqual(out["said"], [["A", 7], ["B", 9], ["C", 9]])
        self.assertEqual(out["left"], 0)

    # ---- ui-flows#3: a year is not grouped ----

    def test_year_has_no_thousands_separator(self):
        out = node(TAKE + r"""
eval(take(/const esc = [^\n]*\n/).replace('const esc', 'var esc'));
eval(take(/function fmt[\s\S]*?\n}\n/));
console.log(JSON.stringify([fmt(2033, '年'), fmt(1999, '年'), fmt(60, '年'), fmt(12500, 'm2'), fmt(1034.25, 't'), fmt(2033, '')]));
""")
        if out is None:
            self.skipTest("node is not installed")
        self.assertEqual(out, ["2033 年", "1999 年", "60 年", "12,500 m2", "1,034.3 t", "2,033"])

    # ---- ui-flows#4: the server cannot be reached ----

    def test_unreachable_server_is_said_in_japanese_with_reload(self):
        r = self.flow("offline")
        self.assertTrue(r["splash"], r)                                       # the door stays
        self.assertIn("WLC Studio のサーバーに接続できません", r["body"], r)
        self.assertIn("サーバーが動いているか、ネットワークを確かめてください", r["body"], r)
        self.assertIn("再読み込み", r["body"], r)
        self.assertNotIn("起動できませんでした：", r["body"], r)
        self.assertTrue(r["detail"] and r["detail"].startswith("詳細："), r)  # the browser's words only as a detail
        self.assertEqual(r["focused"], "boot-reload", r)
        self.assertLessEqual(r["sw"], r["cw"], r)
        self.assertLessEqual(r["btn"], r["vh"], r)                            # 再読み込み is on screen
        self.assertEqual(r["afterReload"], {"error": False, "splash": True}, r)
        self.assertTrue(r["started"], r)

    def test_service_worker_cache_is_new(self):
        sw = (WEB / "sw.js").read_text(encoding="utf-8")
        self.assertIn('"wlcstudio-shell-v12"', sw)
        self.assertNotIn('"wlcstudio-shell-v11"', sw)


if __name__ == "__main__":
    unittest.main()
