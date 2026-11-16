"""Round 11 (the screens): a late answer of a row's own 保存 keeps what the user retyped in that row (and the caret); rows
typed or corrected while 保存して戻る saves are saved in another pass or named; a stop names each row by what is stored;
a double tap on ← / ⚙ during the batch is one tap; focus inside #main (a list's summary, a link) keeps the view; the
自動概算 explanation waits for an open dialog; the address results survive a redraw; left-out rows show their quantity
and whether they may belong in the total; long names wrap at phone width.

Run: cd whole-life-carbon-jcat-study && python3 -B -m unittest discover -s 23_WLC_STUDIO_APP/tests -q
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
WEB = HERE / "web"


def node(script: str):
    """Run `script` with node (app.js's path is process.argv[1]); the parsed JSON it prints, or None without node."""
    try:
        proc = subprocess.run(["node", "-e", script, str(WEB / "app.js")], capture_output=True, text=True, timeout=60)
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


class EleventhRoundUiTests(unittest.TestCase):
    """Regression tests for the eleventh verification round, screens (docs/review_fixes.md, round 11)."""

    @classmethod
    def setUpClass(cls):
        cls.js = (WEB / "app.js").read_text(encoding="utf-8")
        cls.css = (WEB / "style.css").read_text(encoding="utf-8")

    def test_ui_has_the_round11_guards(self):
        for needle in (
                # ui-flows#0: the row a late answer acts on is kept when it changed since it was sent; the caret comes back
                "nav.row = rowNow(", "!sameRow(rowNow(fid), nav.row)", "target === el && caret",
                # ui-flows#1: what each row held when it was sent; checked again before leaving, another pass
                "saveField.sent = rowNow(fid)", "const late = rows.filter(", "pass >= 2",
                # (round 12: stay() keeps the screen through redraw(), still after the read)
                "await redraw(nav, null, true, true, { drop, focus: fid });    // kept after the read",
                # ui-flows#2: a stop names each row by what is stored, from what the rows held when the user stopped
                'state.cancelRows = state.view === "screen" ? rowsNow() : null', "storedAs(p, f, x)",
                # ui-flows#5: a double tap is one tap
                "Date.now() - state.busyWarned < 400",
                # ui-flows#6: focus anywhere in #main is the user's place; a <summary> has an identity
                '" > summary"', 'const nowhere = !had || had === document.body || had === $("#main")',
                # ui-flows#7: one dialog at a time
                "function whenNoDialog(", "whenNoDialog(() => estimateNote(n))", "return new Promise((resolve) => whenNoDialog(",
                # ui-flows#8: the address results are kept and their buttons bound again
                "function bindGeo(", 'geo: $("#geo-out") ? $("#geo-out").innerHTML : null', "bindGeo(g)", 'insertAdjacentHTML("beforeend"',
                # ui-flows#4: the quantity and the 'maybe' mark of left-out rows
                "has(r.quantity)", "r.maybe === true", "足すべきかもしれない", "c.n_maybe > 0 ? c.n_maybe : 0",
                # a question's row stays marked across a redraw; focus back by identity after a redraw
                "state.asking = fid", "function focusBack(",
        ):
            self.assertIn(needle, self.js, needle)

    def test_long_names_wrap(self):
        rule = next((ln for ln in self.css.splitlines() if "overflow-wrap: anywhere" in ln and "#doc-out" in ln), "")
        for sel in ("#doc-out", "ul.unused", "#geo-out", ".cands li", ".notice", ".dlg-body", "table.t td", "#res li", ".lname", ".toast"):
            self.assertIn(sel, rule, sel)
        self.assertIn(".lname { min-width: 0; }", self.css)
        self.assertIn("ul.crows .maybe", self.css)
        self.assertIn('class="lname"', self.js)

    def test_service_worker_cache_is_new(self):
        # v10 in round 11; a later round moves it on (round 12: v11, checked in test_round12_ui)
        sw = (WEB / "sw.js").read_text(encoding="utf-8")
        m = re.search(r'"wlcstudio-shell-v(\d+)"', sw)
        self.assertTrue(m and int(m.group(1)) >= 10, sw[:300])
        self.assertNotIn('"wlcstudio-shell-v9"', sw)

    def test_left_out_rows_show_quantity_and_maybe(self):
        out = node(TAKE + r"""
eval(take(/const esc = [^\n]*\n/).replace('const esc', 'var esc'));
eval(take(/function fmt[\s\S]*?\n}\n/));
eval(take(/function candRows[\s\S]*?\n}\n/));
const base = { id: 7, value: 1034, unit: 'm3', n_rows: 2, rows: [{ name: '普通コンクリート', trace: 'R2C3', quantity: 820, unit: 'm3' }, { name: '普通コンクリート', trace: 'R3C3', quantity: 214, unit: 'm3' }] };
const neu = candRows('m_concrete', { ...base, n_excluded: 3, n_maybe: 1, excluded: [
  { name: 'コンクリート 小計', trace: 'R5C3', reason: '合計の行', quantity: '1,034', unit: 'm3', maybe: false },
  { name: 'コンクリート打設手間', trace: 'R4C3', reason: '作業の行', quantity: 1034, unit: 'm3', maybe: true },
  { name: 'コンクリート（数量なし）', trace: 'R6C1', reason: '数量が無い' }] });
const old = candRows('m_concrete', { ...base, n_excluded: 1, n_maybe: 1, excluded: [{ name: 'コンクリート打設手間', trace: 'R4C3', reason: '作業の行' }] });
const none = candRows('m_concrete', { id: 8, value: 5, unit: 'm3' });
console.log(JSON.stringify({ neu, old, none }));
""")
        if out is None:
            self.skipTest("node is not installed")
        neu, old, none = out["neu"]["rows"], out["old"]["rows"], out["none"]
        items = neu.split('<details id="cx-m_concrete-7"')[1].split("<li>")[1:]
        self.assertIn("コンクリート打設手間", items[0])                       # the row that may belong is listed first
        self.assertIn('<span class="num">1,034 m3</span>', items[0])           # a number, shown like an added row
        self.assertIn('<strong class="maybe">足すべきかもしれない</strong>', items[0])
        # a string quantity, escaped as it is (round 12: in a span that wraps, class qtext, not the one-line num)
        self.assertIn('<span class="qtext">1,034 m3</span>', items[1])
        self.assertNotIn("足すべきかもしれない", items[1] + items[2])
        self.assertNotIn('class="num"', items[2])                              # no quantity: nothing shown
        self.assertIn("足さなかった行のうち 1 行は、足すべき行かもしれません", out["neu"]["warn"])   # n_maybe, as before
        self.assertIn("その 1 行の数量は計 1,034 m3", out["neu"]["warn"])
        # an older candidate: no quantity, no mark, the notice from n_maybe without a sum
        self.assertNotIn('class="num"', old.split('<details id="cx-')[1])
        self.assertNotIn("足すべきかもしれない", old)
        self.assertNotIn("undefined", old + neu)
        self.assertIn("足すべき行かもしれません（理由を確かめてください）", out["old"]["warn"])
        self.assertEqual(none, {"rows": "", "warn": ""})

    def test_row_snapshots_and_stored_values(self):
        out = node(TAKE + r"""
eval(take(/const sameRow = [^\n]*\n/).replace('const sameRow', 'var sameRow'));
eval(take(/function storedAs[\s\S]*?\n}\n/));
const p = { fields: { b_height: { value: { value: 11, unit: 'm', state: 'confirmed' } }, b_footprint: { value: { value: 1745, unit: 'm2', state: 'confirmed' } } } };
const typed = (v, n, u = null, s = 'confirmed') => ({ v, u, s, typed: true, iv: { value: n } });
console.log(JSON.stringify([
  sameRow({ v: '11', u: null, s: 'confirmed' }, { v: '11', u: null, s: 'confirmed' }),
  sameRow({ v: '12', u: null, s: 'confirmed' }, { v: '11', u: null, s: 'confirmed' }),
  sameRow({ v: '11', u: 't', s: null }, { v: '11', u: 'kg', s: null }),
  sameRow(null, { v: '' }),
  storedAs(p, 'b_height', typed('11', 11)),
  storedAs(p, 'b_footprint', typed('900', 900)),
  storedAs(p, 'b_height', typed('11', 11, 'mm')),
  storedAs(p, 'b_height', typed('11', 11, null, 'assumption')),
  storedAs(p, 'b_height', { v: 'x', u: null, s: null, iv: { bad: true } }),
  storedAs(p, 'b_name', typed('a', 'a'))]));
""")
        if out is None:
            self.skipTest("node is not installed")
        self.assertEqual(out, [True, False, False, False, True, False, False, False, False, False])

    def test_double_tap_during_the_batch_is_one_tap(self):
        out = node(TAKE + r"""
var state = { busy: true, busyWarned: 0, act: 0, view: 'screen', cancel: false, cancelRows: null };
var said = [];
function toast(m) { said.push(m); }
function rowsNow() { return { b_height: { v: '11' } }; }
eval(take(/function blocked\(\)[\s\S]*?\n}\n/));
const r = [blocked(), blocked(), state.cancel];
state.busyWarned = Date.now() - 600;                // a deliberate press later on
r.push(blocked(), state.cancel, !!state.cancelRows, said.length);
state.busy = false; r.push(blocked());
console.log(JSON.stringify(r));
""")
        if out is None:
            self.skipTest("node is not installed")
        self.assertEqual(out, [True, True, False, False, True, True, 1, False])

    def test_a_summary_and_a_link_have_an_identity(self):
        out = node(TAKE + r"""
var CSS = { escape: (s) => String(s).replace(/[^\w-]/g, (c) => '\\' + c) };
var document = { body: {} };
eval(take(/const KEYS = [\s\S]*?\];\n/).replace('const KEYS', 'var KEYS'));
eval(take(/function keyOf[\s\S]*?\n}\n/));
const el = (tag, extra = {}) => ({ tagName: tag, id: '', getAttribute: (k) => (extra.attrs || {})[k] ?? null, hasAttribute: (k) => k in (extra.attrs || {}), dataset: {}, ...extra });
console.log(JSON.stringify([
  keyOf(el('SUMMARY', { parentElement: { tagName: 'DETAILS', id: 'cr-m_concrete-7' } })),
  keyOf(el('SUMMARY', { parentElement: { tagName: 'DETAILS', id: '' } })),
  keyOf(el('A', { attrs: { href: 'https://www.kunijiban.pwri.go.jp/' } })),
  keyOf(el('BUTTON', { attrs: { 'data-why': 'm_rebar' } }))]));
""")
        if out is None:
            self.skipTest("node is not installed")
        self.assertEqual(out[0], "#cr-m_concrete-7 > summary")
        self.assertIsNone(out[1])
        self.assertTrue(out[2].startswith('a[href="https'))
        self.assertEqual(out[3], '[data-why="m_rebar"]')


if __name__ == "__main__":
    unittest.main()
