"""Round 16 (the screens): the words of 保存して戻る joined to earlier words of the same action name its project on
another project's view; a press of 住所を検索 is an action of its own, and a failure of an action is said with the act of
that action (a row action of the same project that 保存して戻る waited for is said with the batch's words, named; a
failure is never joined to the words of another project's 保存して戻る);
a read of the project that fails in the middle of 保存して戻る
(the connection is lost, or the answer cannot be read) keeps the batch on its screen and says, held, the rows saved,
the row refused and the reason, without drawing the rows again (what was typed stays), and the project is read again
at its next drawing; a text row takes at most 500 characters, says how much of an insertion it left out, never sends a
longer text, and compares a stored text as the server keeps it (a text stored as sent is never called corrected after it
was sent); an answer that is not JSON (a proxy's page) is said in Japanese with its HTTP status, never shown as it is
nor taken for a success.

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
  return { state: f.value ? f.value.state : null, value: f.value ? f.value.value : null };
}, [pid, fid]);
const answered = (page) => page.waitForFunction(() => state.pending.size === 0 && !state.busy, null, { timeout: 30000 }).then(() => page.waitForTimeout(300));
const retype = async (page, fid, text) => { await page.click('#in-' + fid); await page.keyboard.press('Control+A'); await page.keyboard.type(text); };
const value = (page, fid) => page.evaluate((f) => { const e = document.getElementById('in-' + f); return e ? e.value : null; }, fid);
const badge = (page, fid) => page.evaluate((f) => { const e = document.querySelector('#f-' + f + ' .badge'); return e ? e.textContent : null; }, fid);
// the toast now, and where it stands in the page
const box = (page) => page.evaluate(() => {
  const t = document.getElementById('toast'), r = t.getBoundingClientRect(), c = document.getElementById('toast-close').getBoundingClientRect();
  const shown = t.classList.contains('show');
  return { shown, sticky: t.classList.contains('sticky'), close: !document.getElementById('toast-close').hidden, hold: !!(toast._cur && toast._cur.hold),
    text: shown ? document.getElementById('toast-text').textContent : '', act: toast._cur ? toast._cur.act : null,
    left: r.left, right: r.right, top: r.top, closeBottom: c.bottom, ih: innerHeight, iw: innerWidth, sw: document.documentElement.scrollWidth,
    view: state.view, stale: !!state.stale };
});
const F = {};

// ui-flows#0: the words of 保存して戻る joined to earlier words of the same act lose their project's name. (geo) an empty
// 住所を検索 pressed while 保存して戻る saves (its PUTs held back), the batch stays (地上階数 2.5 refused), B is opened;
// (na) 適用外 refused (400) and answered while 保存して戻る waits for it, the batch stays (都市ガス abc), B is opened
F.joinNamed = async (b) => {
  const out = {};
  {
    const { page, errors } = await home(b);
    const a = await newProject(page, 'JoinA'), other = await newProject(page, 'JoinB');
    await openP(page, a); await screen(page, 'basic');
    await retype(page, 'b_gfa', '3000'); await retype(page, 'b_floors_above', '2.5');
    await hold(page, 'PUT', /\/fields\//, 1200);
    const act0 = await page.evaluate(() => state.act);
    await page.click('#bb-hub'); await page.waitForTimeout(150);
    await page.fill('#addr', ''); await page.click('#btn-geo');
    out.geoSaid = await box(page);
    out.geoActs = [act0 + 1, await page.evaluate(() => state.act)];       // the batch's act, the act after the press
    await answered(page);
    out.geoOnA = await box(page);
    await openP(page, other); await page.waitForTimeout(300);
    out.geoOnB = await box(page);
    out.geoErrors = errors;
  }
  {
    const { page, errors } = await home(b);
    const a = await newProject(page, 'JoinNa'), other = await newProject(page, 'JoinNaB');
    await put(page, a, 'o_elec_kwh', { value: 1000, unit: 'kWh/年', state: 'confirmed', method: 'user_entered' });
    await openP(page, a); await screen(page, 'operation');
    await retype(page, 'o_water_m3', '300'); await retype(page, 'o_gas_m3', 'abc');
    await hold(page, 'PUT', /fields\/o_water_m3$/, 1200); await hold(page, 'PUT', /fields\/o_grid_value$/, 300);
    await page.click('[data-save="o_water_m3"]'); await page.click('[data-na="o_grid_value"]'); await page.click('#bb-hub');
    await page.waitForTimeout(700);
    out.naRefused = await box(page);
    await answered(page);
    out.naOnA = await box(page);
    await openP(page, other); await page.waitForTimeout(300);
    out.naOnB = await box(page);
    out.naGrid = await stored(page, a, 'o_grid_value');
    out.naErrors = errors;
  }
  {
    // the functions on made-up projects: words joined to unnamed words of the same act; a failure of a guarded action
    // answered after a later action (保存して戻る of the same project, of another one, or none) began
    const { page, errors } = await home(b);
    out.fn = await page.evaluate(async () => {
      const A = { id: 901, name: 'A', created_at: 1, fields: {} }, B = { id: 902, name: 'B', created_at: 2, fields: {} };
      const aboutA = { key: projectKey(A), name: 'A' }, r = {};
      const text = () => document.getElementById('toast-text').textContent;
      closeToast(); state.project = A; state.view = 'hub'; state.act = 10;
      toast('前の文', 10); toast('後の文', 10, false, aboutA, true);
      state.project = B; retoast(); r.joined = text();
      closeToast(); state.project = A; state.act = 10;
      toast('前の文', 10); toast('別の操作の文', 11, false, aboutA, true);
      state.project = B; retoast(); r.newer = text();
      // a failure of a guarded action pressed on a project's view, answered after a later act: (a) no 保存して戻る runs:
      // said as that action's words; (b) the 保存して戻る of the same project (pressed after it) runs: said with the
      // batch's words, named by its project elsewhere; (c) the 保存して戻る of another project runs: an act of its own
      const fail = async (on, batch) => {
        closeToast(); state.project = on; state.view = 'hub'; state.act = 10; state.busy = false; state.batch = null;
        let go; const p = new Promise((res) => { go = res; });
        const btn = document.createElement('button'); btn.setAttribute('data-geo', 'probe' + Math.random()); document.body.appendChild(btn);
        guard(btn, async () => { toast('この操作の文', state.act); await p; throw new Error('失敗した'); })();   // act 11
        state.act++;                                                          // a later act (12)
        if (batch) { state.project = A; state.busy = true; state.batch = { n: state.nav, key: projectKey(A), act: 12, about: aboutA }; }
        go(); await new Promise((res) => setTimeout(res, 50));
        const at = { text: text(), act: toast._cur.act };
        if (batch) toast('保存して戻るの文', 12, false, aboutA, true);          // then the batch's words
        state.project = B; state.view = 'hub'; retoast(); at.onB = text();
        state.busy = false; state.batch = null; btn.remove(); state.project = null; state.view = 'home';
        return at;
      };
      r.failure = await fail(A, false);
      r.failureSameBatch = await fail(A, true);
      r.failureOtherBatch = await fail(B, true);
      // a failure of no known action while 保存して戻る runs: an act of its own
      closeToast(); state.act = 20; state.busy = true; toast('保存して戻るの文', 20);
      Promise.reject(new Error('どこかの失敗'));
      await new Promise((res) => setTimeout(res, 50));
      r.bare = { text: text(), act: toast._cur.act, stateAct: state.act };
      state.busy = false; closeToast();
      return r;
    });
    out.fnErrors = errors;
  }
  return { ...out, errors: [...out.geoErrors, ...out.naErrors, ...out.fnErrors] };
};

// ui-flows#1: the connection is lost in the middle of 保存して戻る (運用: 都市ガス 5, 灯油・重油 7, 上水 300).
// stay: from the 2nd PUT on, every request fails; then the connection comes back and 戻る is pressed.
// end: every PUT is stored, the read before leaving fails. pre: the project is stale at the press, the read fails.
// json: the read answers 502 with a page that is not JSON. stay320: stay at 320 x 568
F.offline = async (b) => {
  const out = {};
  for (const mode of ['stay', 'end', 'pre', 'json', 'stay320']) {
    const { page, errors } = await home(b, mode === 'stay320' ? { width: 320, height: 568 } : null);
    const pid = await newProject(page, 'Offline_' + mode);
    await openP(page, pid); await screen(page, 'operation');
    await retype(page, 'o_gas_m3', '5'); await retype(page, 'o_oil_l', '7'); await retype(page, 'o_water_m3', '300');
    let puts = 0;
    const all = (u) => u.pathname.startsWith('/api/');
    await page.route(all, async (route) => {
      const m = route.request().method(), path = new URL(route.request().url()).pathname;
      if (m === 'PUT') puts++;
      const read = m === 'GET' && path === '/api/projects/' + pid;
      if ((mode === 'stay' || mode === 'stay320') && puts >= 2) return route.abort('failed');
      if (mode === 'end' && read && puts >= 3) return route.abort('failed');
      if (mode === 'pre' && read) return route.abort('failed');
      if (mode === 'json' && read && puts >= 3) return route.fulfill({ status: 502, contentType: 'text/html', body: '<html><body><h1>502 Bad Gateway</h1>' + 'x'.repeat(3000) + '</body></html>' });
      return route.continue();
    });
    if (mode === 'pre') await page.evaluate((pid) => { state.stale = { pid, gen: ++state.gen }; }, pid);
    await page.click('#bb-hub');
    await answered(page); await page.waitForTimeout(4000);                 // longer than a timed toast stays
    const r = { said: await box(page), rows: {}, badges: {} };
    for (const f of ['o_gas_m3', 'o_oil_l', 'o_water_m3']) { r.rows[f] = await value(page, f); r.badges[f] = await badge(page, f); }
    await page.unroute(all);
    r.stored = {};
    for (const f of ['o_gas_m3', 'o_oil_l', 'o_water_m3']) r.stored[f] = (await stored(page, pid, f)).value;
    if (mode === 'stay') {
      await page.click('#bb-back'); await page.waitForFunction(() => state.view === 'hub'); await page.waitForTimeout(800);
      r.hub = await box(page);
      r.hubProgress = await page.evaluate(() => state.project.progress.filled);
      await page.click('#toast-close');                                    // the words stay until 閉じる (they cover the hub)
      await screen(page, 'operation'); await page.waitForTimeout(500);
      r.again = { gas: await value(page, 'o_gas_m3'), badge: await badge(page, 'o_gas_m3') };
    }
    r.errors = errors;
    out[mode] = r;
  }
  return { ...out, errors: Object.values(out).flatMap((x) => x.errors) };
};

// ui-flows#2: a text over 500 characters. (fill) 690 characters put into 近くのボーリング調査 at once; (stop) the same
// with 解体材の運搬距離 30 held back, 保存して戻る stopped after the note is saved; (script) a text of 1000 characters put
// into 建物名称 by a script, then its 保存 and 保存して戻る
F.longText = async (b) => {
  const out = {};
  const NOTE = Array.from({ length: 23 }, (_, i) => `地点${String(i + 1).padStart(2, '0')}：N値は深さ5mまで10未満、以深は砂礫で30以上。`).join('');   // 690
  {
    const { page, errors } = await home(b);
    const pid = await newProject(page, 'Long');
    await openP(page, pid); await screen(page, 'basic');
    out.maxlength = await page.evaluate(() => ['b_name', 'b_address', 'g_borehole', 'b_gfa'].map((f) => document.getElementById('in-' + f).getAttribute('maxlength')));
    await page.fill('#in-g_borehole', NOTE);
    out.fill = { len: (await value(page, 'g_borehole')).length, said: await box(page) };
    await page.evaluate(() => closeToast());
    await page.focus('#in-g_borehole'); await page.keyboard.press('End'); await page.keyboard.type('X');   // the row is full
    await page.waitForTimeout(100);
    out.fullKey = { len: (await value(page, 'g_borehole')).length, said: await box(page) };
    await page.fill('#in-a_eol_haul_km', '30');
    await hold(page, 'PUT', /fields\/a_eol_haul_km$/, 2500);
    await page.click('#bb-hub');
    await page.waitForResponse((r) => /g_borehole$/.test(new URL(r.url()).pathname) && r.request().method() === 'PUT');
    await page.waitForTimeout(300);
    await page.click('#btn-settings'); await page.waitForTimeout(600); await page.click('#btn-settings');
    await answered(page); await page.waitForTimeout(500);
    out.stop = { said: await box(page), stored: ((await stored(page, pid, 'g_borehole')).value || '').length };
    out.longErrors = errors;
  }
  {
    const { page, errors } = await home(b);
    const pid = await newProject(page, 'LongScript');
    await openP(page, pid); await screen(page, 'basic');
    const put1000 = () => page.evaluate(() => { const e = document.getElementById('in-b_name'); e.value = '名'.repeat(1000); e.dispatchEvent(new Event('input', { bubbles: true })); });
    await put1000();
    await page.click('[data-save="b_name"]'); await page.waitForTimeout(600);
    out.script = { said: await box(page), stored: (await stored(page, pid, 'b_name')).value };
    await page.evaluate(() => closeToast());
    await put1000();
    await page.click('#bb-hub'); await answered(page);
    out.scriptBatch = { said: await box(page), stored: (await stored(page, pid, 'b_name')).value, view: await page.evaluate(() => state.view) };
    out.scriptErrors = errors;
  }
  return { ...out, errors: [...out.longErrors, ...out.scriptErrors] };
};

// ui-flows#3: answers that are not JSON. (result) the stored result read answers 502 with a page; (put) a row's 保存
// answered 200 with a page; (boot) /api/meta answers 502 with a page
F.unreadable = async (b) => {
  const out = {};
  {
    const { page, errors } = await home(b, { width: 320, height: 568 });
    const pid = await newProject(page, 'Unreadable');
    await openP(page, pid);
    const isResult = (u) => u.pathname === `/api/projects/${pid}/result`;
    await page.route(isResult, (r) => r.fulfill({ status: 502, contentType: 'text/html', body: '<html><head><title>502 Bad Gateway</title></head><body><h1>502 Bad Gateway</h1>' + 'x'.repeat(3000) + '</body></html>' }));
    await page.click('#to-result'); await page.waitForTimeout(800);
    out.result = await page.evaluate(() => ({ msg: document.getElementById('res-msg').textContent, sw: document.documentElement.scrollWidth, h: document.getElementById('res-msg').getBoundingClientRect().height }));
    await page.unroute(isResult);
    await page.click('#btn-back'); await page.waitForFunction(() => state.view === 'hub');
    await screen(page, 'operation');
    await retype(page, 'o_gas_m3', '5');
    const isPut = (u) => u.pathname === `/api/projects/${pid}/fields/o_gas_m3`;
    await page.route(isPut, (r) => (r.request().method() === 'PUT' ? r.fulfill({ status: 200, contentType: 'text/html', body: '<html><body>Captive portal</body></html>' }) : r.continue()));
    await page.click('[data-save="o_gas_m3"]'); await page.waitForTimeout(800);
    out.put = { said: await box(page), stored: (await stored(page, pid, 'o_gas_m3')).value, row: await value(page, 'o_gas_m3') };
    out.pageErrors = errors;
  }
  {
    const { page, errors } = await page0(b);
    await page.route((u) => u.pathname === '/api/meta', (r) => r.fulfill({ status: 502, contentType: 'text/html', body: '<html><body><h1>502 Bad Gateway</h1>' + 'y'.repeat(3000) + '</body></html>' }));
    await page.goto(BASE + '/'); await page.waitForSelector('.boot-error');
    out.boot = await page.evaluate(() => ({ text: document.querySelector('.boot-error').textContent, detail: (document.querySelector('.boot-detail') || {}).textContent || '' }));
    out.bootErrors = errors;
  }
  return { ...out, errors: [...out.pageErrors, ...out.bootErrors] };
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


OFFLINE = "WLC Studio のサーバーに接続できません（サーバーが動いているか確かめてください）"
OLD = "行の状態の表示は古いままです"


class SixteenthRoundUiTests(unittest.TestCase):
    """Regression tests for the sixteenth verification round, screens (docs/review_fixes.md, round 16)."""

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

    # ---- ui-flows#0: held words of 保存して戻る joined to earlier words of the same act name their project ----

    def test_an_empty_address_search_during_the_batch_is_an_action_of_its_own(self):
        r = self.flow("joinNamed")
        self.assertEqual(r["geoSaid"]["text"], "住所を入力してください", r["geoSaid"])
        self.assertGreater(r["geoActs"][1], r["geoActs"][0], r["geoActs"])      # not the batch's act
        b = r["geoOnB"]
        self.assertTrue(b["shown"] and b["sticky"] and b["close"] and b["hold"], b)
        self.assertEqual(b["text"], "「JoinA」：「地上階数」：「地上階数」は整数で入れる。戻りません（「延床面積」は保存しました）", b)

    def test_a_refusal_answered_while_the_batch_waits_is_said_with_it_and_named(self):
        r = self.flow("joinNamed")
        self.assertIn("「適用外」にできない", r["naRefused"]["text"], r["naRefused"])
        self.assertNotEqual(r["naGrid"]["state"], "not_applicable", r)
        b = r["naOnB"]
        self.assertTrue(b["sticky"] and b["hold"], b)
        self.assertTrue(b["text"].startswith("「JoinNa」：「運用時の電力の排出係数」は、いまの入力では「適用外」にできない"), b)
        self.assertTrue(b["text"].endswith(" ／ 「JoinNa」：「都市ガス」は数値で入力してください（使えない文字があります）。保存していません"), b)
        for part in b["text"].split(" ／ "):                                     # nothing on B reads as B's
            self.assertTrue(part.startswith("「JoinNa」："), b)

    def test_joined_words_take_the_project_of_the_later_words(self):
        fn = self.flow("joinNamed")["fn"]
        self.assertEqual(fn["joined"], "「A」：前の文 ／ 「A」：後の文", fn)
        self.assertEqual(fn["newer"], "「A」：別の操作の文", fn)                  # a newer act replaces, as before

    def test_a_failure_is_said_with_the_act_of_its_own_action(self):
        fn = self.flow("joinNamed")["fn"]
        # a guarded action's failure answered after a later act: said with the action's own words (act 11)
        self.assertEqual((fn["failure"]["text"], fn["failure"]["act"]), ("この操作の文 ／ 失敗した", 11), fn)
        # the 保存して戻る of the same project runs (it waited for the action): said with its words, named elsewhere
        self.assertEqual(fn["failureSameBatch"]["act"], 12, fn)
        self.assertEqual(fn["failureSameBatch"]["onB"], "「A」：失敗した ／ 「A」：保存して戻るの文", fn)
        # the 保存して戻る of another project runs: never joined to its words, never named by its project
        self.assertEqual((fn["failureOtherBatch"]["text"], fn["failureOtherBatch"]["act"]), ("この操作の文 ／ 失敗した", 11), fn)
        self.assertEqual(fn["failureOtherBatch"]["onB"], "「A」：保存して戻るの文", fn)
        # a failure of no known action while 保存して戻る runs: an act of its own
        self.assertEqual(fn["bare"], {"text": "どこかの失敗", "act": 21, "stateAct": 21}, fn)

    # ---- ui-flows#1: a read that fails in the middle of 保存して戻る ----

    def test_lost_connection_in_the_batch_names_saved_and_refused_rows(self):
        r = self.flow("offline")
        s = r["stay"]
        said = s["said"]
        self.assertTrue(said["shown"] and said["sticky"] and said["close"] and said["hold"], said)   # held: still shown after 4 s
        self.assertEqual(said["text"], "「灯油・重油」：" + OFFLINE + "。戻りません（「都市ガス」は保存しました）。同じ理由で画面を読み直せませんでした。" + OLD, said)
        self.assertEqual(said["view"], "screen", said)
        self.assertEqual(s["rows"], {"o_gas_m3": "5", "o_oil_l": "7", "o_water_m3": "300"}, s)          # not drawn again
        self.assertTrue(said["stale"], said)                                     # read again at the next drawing
        self.assertEqual(s["stored"], {"o_gas_m3": 5, "o_oil_l": None, "o_water_m3": None}, s)
        # the connection is back: 戻る draws the hub from a new read, the words stay; the screen shows what is stored
        self.assertTrue(s["hub"]["shown"] and s["hub"]["hold"], s["hub"])
        self.assertFalse(s["hub"]["stale"], s["hub"])
        self.assertEqual(s["again"], {"gas": "5", "badge": "取得・確認済み"}, s)

    def test_a_failed_read_before_leaving_keeps_the_batch_here(self):
        r = self.flow("offline")
        e = r["end"]["said"]
        self.assertTrue(e["hold"] and e["sticky"], e)
        self.assertEqual(e["text"], "保存のあと画面を読み直せませんでした：" + OFFLINE + "。戻りません（「都市ガス」「灯油・重油」「上水の使用量」は保存しました）。" + OLD, e)
        self.assertEqual(e["view"], "screen", e)
        self.assertEqual(r["end"]["stored"], {"o_gas_m3": 5, "o_oil_l": 7, "o_water_m3": 300}, r["end"])
        j = r["json"]["said"]
        self.assertEqual(j["text"], "保存のあと画面を読み直せませんでした：サーバーから読めない答え（HTTP 502）。戻りません（「都市ガス」「灯油・重油」「上水の使用量」は保存しました）。" + OLD, j)
        p = r["pre"]
        self.assertEqual(p["said"]["text"], "保存の前に画面を読み直せませんでした：" + OFFLINE + "。どの行も保存していません。戻りません。" + OLD, p)
        self.assertEqual(p["stored"], {"o_gas_m3": None, "o_oil_l": None, "o_water_m3": None}, p)
        self.assertEqual(p["rows"], {"o_gas_m3": "5", "o_oil_l": "7", "o_water_m3": "300"}, p)

    def test_the_held_words_of_a_lost_connection_fit_320_px(self):
        s = self.flow("offline")["stay320"]["said"]
        self.assertTrue(s["hold"] and s["close"], s)
        self.assertLessEqual(s["sw"], 320, s)
        self.assertGreaterEqual(s["left"], 0, s)
        self.assertLessEqual(s["right"], s["iw"], s)
        self.assertGreaterEqual(s["top"], 0, s)
        self.assertLessEqual(s["closeBottom"], s["ih"], s)

    # ---- ui-flows#2: a text over 500 characters ----

    def test_a_text_row_takes_500_characters_and_says_what_it_left_out(self):
        r = self.flow("longText")
        self.assertEqual(r["maxlength"], ["500", "500", "500", None], r)
        self.assertEqual(r["fill"]["len"], 500, r)
        self.assertEqual(r["fill"]["said"]["text"], "「近くのボーリング調査（国土地盤情報）」は 500 字までです。入れた文の終わりの 190 字は入っていません", r)
        # a key typed into the full row: the browser takes nothing (no input event), and that is said too
        self.assertEqual(r["fullKey"]["len"], 500, r)
        self.assertEqual(r["fullKey"]["said"]["text"], "「近くのボーリング調査（国土地盤情報）」は 500 字までです。入れた文の終わりの 1 字は入っていません", r)

    def test_a_text_stored_as_sent_is_not_called_corrected_by_a_stop(self):
        r = self.flow("longText")
        said = r["stop"]["said"]["text"]
        self.assertNotIn("直す前の値", said, said)
        self.assertEqual(said, "「近くのボーリング調査（国土地盤情報）」「解体材の運搬距離」を保存しました", said)
        self.assertEqual(r["stop"]["stored"], 500, r)

    def test_a_text_over_500_characters_is_never_sent(self):
        r = self.flow("longText")
        self.assertEqual(r["script"]["said"]["text"], "「建物名称」は 500 字までにしてください（いま 1000 字）", r)
        self.assertIsNone(r["script"]["stored"], r)
        b = r["scriptBatch"]
        self.assertEqual(b["said"]["text"], "「建物名称」は 500 字までにしてください（いま 1000 字）。保存していません", b)
        self.assertTrue(b["said"]["hold"], b)
        self.assertEqual(b["view"], "screen", b)
        self.assertIsNone(b["stored"], b)

    def test_stored_texts_are_compared_as_the_server_keeps_them(self):
        out = node(TAKE + r"""
var state = { meta: { fields: { b_name: { type: 'text', label: '建物名称' }, b_gfa: { type: 'number', label: '延床面積' } } } };
var el = { value: '' }; var $ = () => el;
eval(take(/function parseNumber[\s\S]*?\n}\n/));
eval(take(/function inputValue[\s\S]*?\n}\n/));
eval(take(/const TEXT_MAX = [^\n]*\n/).replace('const ', 'var '));
eval(take(/const storedText = [^\n]*\n/).replace('const ', 'var '));
eval(take(/function storedAs[\s\S]*?\n}\n/));
const row = (typed) => { el.value = typed; return { v: typed, u: null, s: 'confirmed', typed: true, iv: inputValue('b_name') }; };
const p = (v) => ({ fields: { b_name: { value: { value: v, unit: '', state: 'confirmed' } } } });
const iv = (typed) => { el.value = typed; return inputValue('b_name'); };
console.log(JSON.stringify({
  sep: [storedAs(p('abc'), 'b_name', row('\x1cabc\x85')), storedAs(p('abc'), 'b_name', row('\u3000abc ')), storedAs(p('\ufeffabc'), 'b_name', row('\x1c\ufeffabc'))],
  other: [storedAs(p('abc'), 'b_name', row('abd')), storedAs(p('ab c'), 'b_name', row('abc'))],
  num: storedAs({ fields: { b_gfa: { value: { value: 12, unit: 'm2', state: 'confirmed' } } } }, 'b_gfa', { v: '12', u: 'm2', s: 'confirmed', iv: { value: 12 } }),
  len: [iv('a'.repeat(500)), iv('a'.repeat(501)), iv('\x1c' + 'a'.repeat(500) + '\x85'), iv('\ud83d\ude00'.repeat(500)), iv('\ud83d\ude00'.repeat(501))].map((x) => (x.bad ? 'bad:' + x.long : x.value.length)),
}));
""")
        if out is None:
            self.skipTest("node is not installed")
        self.assertEqual(out["sep"], [True, True, True])
        self.assertEqual(out["other"], [False, False])
        self.assertTrue(out["num"])
        # 500 characters as the server counts them (code points, after its trimming): a longer text is never sent
        self.assertEqual(out["len"], [500, "bad:501", 502, 1000, "bad:501"])

    # ---- ui-flows#3: an answer that is not JSON ----

    def test_an_answer_that_is_not_json_is_said_with_its_status(self):
        r = self.flow("unreadable")
        self.assertEqual(r["result"]["msg"], "前の結果を読めませんでした：サーバーから読めない答え（HTTP 502）", r["result"])
        self.assertLessEqual(r["result"]["sw"], 320, r["result"])
        self.assertLess(r["result"]["h"], 200, r["result"])
        # a 200 that is not JSON is not a success: the row's 保存 is refused, nothing is stored, the typed value stays
        self.assertEqual(r["put"]["said"]["text"], "「都市ガス」：サーバーから読めない答え（HTTP 200） ／ まだ保存していない入力：「都市ガス」", r["put"])
        self.assertIsNone(r["put"]["stored"], r["put"])
        self.assertEqual(r["put"]["row"], "5", r["put"])
        # at the start: said in Japanese; at most 200 characters of the page are kept as a small detail
        self.assertIn("WLC Studio を起動できませんでした", r["boot"]["text"], r["boot"])
        self.assertTrue(r["boot"]["detail"].startswith("詳細：サーバーから読めない答え（HTTP 502）：<html>"), r["boot"])
        self.assertLessEqual(len(r["boot"]["detail"]), len("詳細：サーバーから読めない答え（HTTP 502）：") + 200, r["boot"])

    def test_api_says_every_answer_that_is_not_json_with_its_status(self):
        out = node(TAKE + r"""
eval(take(/async function api[\s\S]*?\n}\n/));
const res = (status, body) => ({ ok: status < 400, status, text: async () => body });
const big = '<html><head><title>502 Bad Gateway</title></head><body>' + 'x'.repeat(3000) + '</body></html>';
const runs = [['502 html', 502, big], ['200 html', 200, big], ['500 text', 500, 'Internal'], ['400 empty', 400, ''],
  ['500 no error', 500, '{"a":1}'], ['200 null', 200, 'null'], ['200 string', 200, '"x"'], ['refused', 400, '{"error":"理由"}'],
  ['ok', 200, '{"a":1}'], ['list', 200, '[1]'], ['empty', 200, '']];
(async () => {
  const out = {};
  for (const [k, s, b] of runs) {
    global.fetch = () => Promise.resolve(res(s, b));
    try { out[k] = { ok: await api('/x') }; } catch (e) { out[k] = { message: e.message, detail: e.detail ?? null }; }
  }
  console.log(JSON.stringify(out));
})();
""")
        if out is None:
            self.skipTest("node is not installed")
        self.assertEqual(out["502 html"]["message"], "サーバーから読めない答え（HTTP 502）")
        self.assertEqual(len(out["502 html"]["detail"]), 200)
        self.assertEqual(out["200 html"]["message"], "サーバーから読めない答え（HTTP 200）")
        self.assertEqual(out["500 text"], {"message": "サーバーから読めない答え（HTTP 500）", "detail": "Internal"})
        self.assertEqual(out["400 empty"], {"message": "サーバーから読めない答え（HTTP 400）", "detail": ""})
        self.assertEqual(out["500 no error"]["message"], "サーバーから読めない答え（HTTP 500）")
        self.assertEqual(out["200 null"]["message"], "サーバーから読めない答え（HTTP 200）")
        self.assertEqual(out["200 string"]["message"], "サーバーから読めない答え（HTTP 200）")
        self.assertEqual(out["refused"], {"message": "理由", "detail": None})
        self.assertEqual(out["ok"], {"ok": {"a": 1}})
        self.assertEqual(out["list"], {"ok": [1]})
        self.assertEqual(out["empty"], {"ok": {}})

    def test_service_worker_cache_is_new(self):
        sw = (WEB / "sw.js").read_text(encoding="utf-8")
        m = re.search(r'"wlcstudio-shell-v(\d+)"', sw)                     # v15 or later (a later round bumps it again)
        self.assertTrue(m, sw)
        self.assertGreaterEqual(int(m.group(1)), 15)
        self.assertNotIn('"wlcstudio-shell-v14"', sw)


if __name__ == "__main__":
    unittest.main()
