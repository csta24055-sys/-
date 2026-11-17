/* WLC Studio – mobile PWA front end. Talks only to the local server's JSON API (/api/...). */
"use strict";
const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
// seq: renders; nav: moves between views (a late answer of the view that was left must not paint into the new one);
// act: user actions (toast messages of one action are joined, a new action starts a new message);
// busy: 保存して戻る is saving row after row; stale: an answer changed this project while another view was shown (it is
// read again before that project is drawn: state.project is always what is drawn); gen: counts such answers;
// running: the buttons whose request is under way (by their identity, so a redrawn button is busy too);
// pending: row actions that change a stored value and are under way (保存して戻る waits for them);
// geo: what #geo-out shows (the address and PLATEAU answers its buttons act on: kept across redraws);
// asking: the row a question is about (drawn marked again after a redraw); cancelRows: what the rows held when the user
// stopped 保存して戻る (taken before the view changed: the stop names each row by what is stored); geoSeq: the number of
// the latest request for #geo-out (an address search or a PLATEAU read: only its answer is shown);
// owed: the acted rows whose redraw was skipped while 保存して戻る ran (fid → what the row held when its action was sent,
// and the view it was sent in): the next drawing of that screen shows their stored value (see owedRows);
// warnings: what the answers of saves said while 保存して戻る ran on their project (said with its message, see warnOf);
// batch: the view (nav), project (key, about) and act of the 保存して戻る that runs; openSeq: the number of the latest
// 開く (only its read opens a project)
const state = { meta: null, project: null, stack: [], view: "home", seq: 0, nav: 0, act: 0, busy: false, stale: null, gen: 0,
  running: new Set(), pending: new Set(), lastImport: null, importing: null, noteLater: null, geo: null, asking: null, cancelRows: null,
  geoSeq: 0, owed: new Map(), warnings: [], batch: null, openSeq: 0 };

/* a request to the server. A request that cannot reach it (the browser's TypeError: the server stopped, no network) is
   said in Japanese wherever errors are shown; the browser's own words are kept as e.detail (shown only as a detail).
   The server answers JSON (its refusals carry `error`, said as they are). An answer that is not JSON (a proxy's or a
   gateway's page, whatever its status) is never shown as it is, nor taken for a success: it is said in Japanese with its
   HTTP status, and at most 200 characters of it are kept as e.detail */
async function api(path, opts = {}) {
  let r, t;
  try {
    r = await fetch("/api" + path, { headers: { "Content-Type": "application/json" }, ...opts,
      body: opts.body ? JSON.stringify(opts.body) : undefined });
    t = await r.text();
  } catch (e) {
    if (!(e instanceof TypeError)) throw e;                   // not a failed connection (an abort): as it is
    const x = new Error("WLC Studio のサーバーに接続できません（サーバーが動いているか確かめてください）");
    x.offline = true; x.detail = String((e && e.message) || e || "");
    throw x;
  }
  let j; try { j = t ? JSON.parse(t) : {}; } catch { j = null; }
  if (j === null || typeof j !== "object" || (!r.ok && !(typeof j.error === "string" && j.error))) {
    const x = new Error(`サーバーから読めない答え（HTTP ${r.status}）`);
    x.unreadable = true; x.detail = String(t || "").slice(0, 4000).replace(/\s+/g, " ").trim().slice(0, 200);
    throw x;
  }
  if (!r.ok) throw new Error(j.error);
  return j;
}
/* `act` is the action the message belongs to: a late answer passes the act of the action that sent its request.
   A warning from the server (an answer's `warnings`, said once: an object { w, key, name } made by sayWarning, or a
   string with `warn`) makes the toast stay until the user closes it (閉じる, or Escape in it). A later action's message is
   shown above the warnings kept, and goes after its time as usual; the warnings stay.
   `about` ({ key, name }): the project the words are about, given by 保存して戻る for its words (its stop is said once its
   read is answered, maybe while another project, or none, is shown). Read while another project is shown, the words
   name it; they stay when the user goes back to it (see retoast). Words joined to earlier words of the same action
   give them their project when those had none. `hold`: words that name rows not saved (a stop or a
   stay of 保存して戻る) stay until 閉じる as well, and so do words too long for the toast (they scroll inside it). A late
   answer (the act of an action older than the held words') does not replace held words: it is said after them, as it
   is (not named by their project) */
function toast(msg, act = state.act, warn = false, about = null, hold = false) {
  const t = $("#toast"), T = toast;
  if (warn && typeof msg === "string") msg = { w: msg, key: shownKey(), name: "" };
  if (!t.classList.contains("show")) { T._cur = null; T._kept = []; }
  // messages of the same action are joined (a refusal and the "not saved yet" notice); a new action starts afresh, and a
  // late answer is never joined to a newer action's message (the old test toast._act === state.act took the act of the
  // newest action for every message). Of the earlier action's words only its warnings stay
  const same = !!T._cur && toast._act === act;
  const under = !same && !!T._cur && T._cur.hold && act < T._cur.act;
  if (!same && !under) {
    if (T._cur) keepWarnings(T._cur);
    T._cur = { act, msgs: [], warns: [], shown: shownKey(), about, hold: false, long: false, plain: [] };
  } else if (same && about && !T._cur.about) T._cur.about = about;   // joined: the words of one action name its project
  // (the earlier words of the same action were said on that project's view)
  if (hold) T._cur.hold = true;
  if (!T._cur.msgs.some((x) => sameItem(x, msg))) { T._cur.msgs.push(msg); if (under && typeof msg === "string") T._cur.plain.push(msg); }
  if (typeof msg !== "string" && !T._cur.warns.some((x) => sameItem(x, msg))) T._cur.warns.push(msg);
  if (!under) T._act = act;
  drawToast(true);
}
/* a toast's item: a message (a string), or a warning { w, key, name }: said as it is while its project is shown, and with
   its project's name while another project (or none) is shown, so that it is never taken for one about the project shown */
const toastText = (x) => (typeof x === "string" ? x : x.key === shownKey() ? x.w : `「${x.name || "別のプロジェクト"}」：${x.w}`);
const sameItem = (a, b) => (typeof a === "string" || typeof b === "string" ? a === b : a.w === b.w && a.key === b.key);
function keepWarnings(cur) { cur.warns.forEach((w) => { if (!toast._kept.some((x) => sameItem(x, w))) toast._kept.push(w); }); }
/* the toast's words as toast() left them: the current action's words (joined), then the warnings kept from earlier
   actions. A toast that carries a warning is an alert with 閉じる; otherwise it is a status, with 閉じる when its words
   stay (hold, or too long for it). `quiet`: the words and marks are put only where they have changed (a toast repainted
   for a new view is not said again by a screen reader; a project's name put before its words is still written).
   `own`: the current words stay until 閉じる (no timer). Words once too long for the toast stay so (`long`): the room
   changes from view to view (the bottom bar of an input screen), and words that fit on the next view would otherwise
   be left with neither 閉じる nor a timer */
function paintToast(quiet = false) {
  const t = $("#toast"), T = toast, a = T._cur && T._cur.about, sk = shownKey();
  // words about a project (about) read while another project is shown name it, as its warnings do
  const named = !!(a && sk && sk !== a.key);
  const word = (x) => (named && typeof x === "string" && !T._cur.plain.includes(x) ? `「${a.name || "別のプロジェクト"}」：${x}` : toastText(x));
  const cur = T._cur ? T._cur.msgs.map(word).join(" ／ ") : "";
  const kept = T._kept.filter((w) => !(T._cur && T._cur.msgs.some((x) => sameItem(x, w)))).map(toastText);
  const warned = !!(T._cur && T._cur.warns.length) || kept.length > 0;
  const put = (el, s) => { if (!quiet || el.textContent !== s) el.textContent = s; };
  const mark = (el, k, v) => { if (el.getAttribute(k) !== v) el.setAttribute(k, v); };
  const hide = (el, h) => { if (el.hidden !== h) el.hidden = h; };
  put($("#toast-text"), cur);
  const k = $("#toast-kept");
  put(k, kept.length ? (cur ? "前の保存の知らせ：" : "") + kept.join(" ／ ") : ""); hide(k, !kept.length);
  const over = toastOverflows();
  if (T._cur && over) T._cur.long = true;
  const own = !!(T._cur && (T._cur.warns.length || T._cur.hold || T._cur.long)) || over, sticky = warned || own;
  if (t.classList.contains("sticky") !== sticky) t.classList.toggle("sticky", sticky);
  mark(t, "role", warned ? "alert" : "status"); mark(t, "aria-live", warned ? "assertive" : "polite");
  hide($("#toast-close"), !sticky);
  return { cur, kept, own };
}
/* the toast's words do not fit in it (its body scrolls): measured as if 閉じる were not shown (it takes room when shown),
   so that the same words give the same answer */
function toastOverflows() {
  const b = $("#toast-body"), c = $("#toast-close");
  const room = b.clientHeight + (c.hidden ? 0 : c.offsetHeight + (parseFloat(getComputedStyle($("#toast")).rowGap) || 0));
  return b.scrollHeight > room + 1;
}
/* the current words go after their time, unless they stay (`own`); when warnings are kept under them, only they go */
function timeToast(r) {
  const T = toast;
  clearTimeout(T._t);
  if (T._cur && !r.own)
    T._t = setTimeout(() => { if (r.kept.length) { T._cur = null; drawToast(false); } else closeToast(); }, 2600 + Math.min(4000, r.cur.length * 20));
}
/* show the toast: a toast with a warning has no timer, nor have words that stay (hold, too long); any other goes after
   its time (and when warnings are kept under it, only its own words go) */
function drawToast(fresh) {
  const t = $("#toast");
  placeToast();                                               // its room first: whether the words fit depends on it
  const r = paintToast();
  t.classList.add("show");
  if (fresh) $("#toast-body").scrollTop = 0;                  // a new message is read from its start
  timeToast(r);
}
/* a view was drawn: a toast that stays (it carries warnings) names each warning's project when another project is shown
   now; when the project shown has changed since its action's words were said, those words go (they were about the
   project shown then) and its warnings stay, named. Words about a project (toast's `about`) stay while that project is
   shown (the user went back to it), and are named while another one is shown (also when they go after their time);
   words that name rows not saved (hold) stay, named, also when warnings were said with them. The toast is repainted
   only where its words change (it is not said again at each view); words that no longer fit (a name put before them)
   stay until 閉じる */
function retoast() {
  const t = $("#toast"), T = toast, sk = shownKey(), a = T._cur && T._cur.about, sticky = t.classList.contains("sticky");
  if (!t.classList.contains("show") || (!sticky && !a)) return;
  if (T._cur && T._cur.warns.length && !T._cur.hold && T._cur.shown !== sk && !(a && a.key === sk)) { keepWarnings(T._cur); T._cur = null; }
  if (paintToast(true).own) clearTimeout(T._t);
}
/* field `f` of project `key` has just been stored with another state than 適用外 (a value, 未取得 …) at `at` (the answer's
   updated_at, the server's time of that write): a warning that its 適用外 cannot be used no longer holds. It goes from
   those kept for 保存して戻る and from the toast (quietly; the toast closes when nothing is left, and words left without a
   warning go after their time, or stay when they are still too long). A write stored before the warning's own write (a
   late answer of an earlier save of the field) does not answer it: the warning was said with the field 適用外 after it */
function settleWarnings(key, f, at = null) {
  const older = (x) => typeof at === "number" && typeof x.at === "number" && at < x.at;
  const T = toast, t = $("#toast"), gone = (x) => typeof x !== "string" && x.key === key && x.f === f && !older(x);
  state.warnings = state.warnings.filter((x) => !(x.f === f && x.nav.key === key && !older(x)));
  if (!t.classList.contains("show") || !(T._kept.some(gone) || (T._cur && T._cur.msgs.some(gone)))) return;
  T._kept = T._kept.filter((x) => !gone(x));
  if (T._cur) { T._cur.msgs = T._cur.msgs.filter((x) => !gone(x)); T._cur.warns = T._cur.warns.filter((x) => !gone(x)); }
  if (T._cur && !T._cur.msgs.length) T._cur = null;
  if (!T._cur && !T._kept.length) return closeToast();
  if (T._cur) T._cur.long = false;                           // fewer words: whether they fit is measured again
  timeToast(paintToast(true));
}
/* the toast stands 12 px above the bottom bar of an input screen (its buttons wrap on a narrow phone: the bar is 64 to
   120 px high), else at the style sheet's 84 px: it never covers the bar's buttons */
function placeToast() {
  const t = $("#toast"), bb = document.querySelector(".bottombar");
  const h = bb && bb.getClientRects().length ? Math.ceil(innerHeight - bb.getBoundingClientRect().top) : 0;
  if (h + 12 > 84) t.style.setProperty("--below", h + 12 + "px"); else t.style.removeProperty("--below");
}
/* the toast goes (its time is over, or the user closed it); focus in it goes back to where it came from */
function closeToast() {
  const t = $("#toast"), T = toast, inside = t.contains(document.activeElement);
  clearTimeout(T._t); T._cur = null; T._kept = [];
  t.classList.remove("show", "sticky"); t.setAttribute("role", "status"); t.setAttribute("aria-live", "polite");
  $("#toast-close").hidden = true;
  if (inside) { const b = T._from; (b && b !== document.body && document.contains(b) ? b : $("#main")).focus({ preventScroll: true }); }
}
/* the toast's parts (made here, so that any index.html serves): its words (they scroll when long) and 閉じる, a button
   without text of its own (its label is drawn by the style sheet: the toast's text is its message only) */
function initToast() {
  const t = $("#toast");
  t.innerHTML = '<div class="toast-body" id="toast-body"><div id="toast-text"></div><div class="toast-kept" id="toast-kept" hidden></div></div>'
    + '<button class="toast-close" id="toast-close" type="button" aria-label="閉じる" hidden></button>';
  $("#toast-close").onclick = closeToast;
  t.addEventListener("keydown", (e) => { if (e.key === "Escape" && t.classList.contains("sticky")) { e.preventDefault(); closeToast(); } });
  t.addEventListener("focusin", (e) => { if (!t.contains(e.relatedTarget)) toast._from = e.relatedTarget; });
  window.addEventListener("resize", placeToast);
}
/* the project the user sees now (its hub, one of its screens, its result), or "" (home, a new project's structure, settings) */
function shownKey() { return state.project && ["hub", "screen", "result"].includes(state.view) ? projectKey(state.project) : ""; }
/* the warnings a write's answer carries (`warnings`: ready-made sentences, e.g. that this save made another field's stored
   適用外 unusable; the server says each one once). `nav` is where the action started (startedAt: its project and act).
   Every one is said, joined to the message of the action that sent it, and stays until the user closes it. While 保存して
   戻る runs on the same project they are kept for its own message (its message would replace them, and it may then leave
   for the hub): see sayWarnings. Said while another project (or none) is shown, a warning names its project: it is never
   joined to a 保存して戻る of another project, nor taken for one about the project shown. Each warning carries the field
   it is about (`warning_fields`, same order): a write answered with another state than 適用外 for that field (a value
   saved later in the same 保存して戻る, 未取得に戻す, a candidate adopted) takes back the warnings about it (settleWarnings),
   when it was stored after the write that said them (each warning keeps its answer's updated_at) */
function warnOf(r, nav) {
  const at = r && typeof r.updated_at === "number" ? r.updated_at : null;
  if (r && typeof r.field_id === "string" && typeof r.state === "string" && r.state !== "not_applicable") settleWarnings(nav.key, r.field_id, at);
  const fs = r && Array.isArray(r.warning_fields) ? r.warning_fields : [];
  const ws = (r && Array.isArray(r.warnings) ? r.warnings : []).map((w, i) => ({ w, f: typeof fs[i] === "string" ? fs[i] : null }))
    .filter((x) => typeof x.w === "string" && x.w.trim());
  if (state.busy && state.batch && state.batch.key === nav.key) state.warnings.push(...ws.map((x) => ({ w: x.w, f: x.f, at, nav })));
  else ws.forEach((x) => sayWarning(x.w, nav, nav.act, x.f, at));
}
function sayWarning(w, nav, act, f = null, at = null) { toast({ w, key: nav.key, name: nav.name, f, at }, act); }
/* the warnings kept while 保存して戻る ran, joined to its message (`act`: the act of that message). `p`: the batch's last
   read of its project (or null): a warning whose field is no longer stored as 適用外 there is not said (see storedNa) */
function sayWarnings(act, p = null) { state.warnings.splice(0).filter((x) => !(p && x.f && x.nav.key === projectKey(p) && !storedNa(p, x.f))).forEach((x) => sayWarning(x.w, x.nav, act, x.f, x.at)); }
/* field `f` is stored as 適用外 in project read `p` */
const storedNa = (p, f) => ((((p && p.fields) || {})[f] || {}).value || {}).state === "not_applicable";
/* a control's identity across redraws: its id, or the data attribute that names its action and row (with the candidate
   it adopts, data-cid, and the #geo-out list it belongs to, data-list); a list's <summary> is known by its list
   (details[id]) and a link by where it leads */
const KEYS = ["data-save", "data-accept", "data-why", "data-est", "data-na", "data-later", "data-unset", "data-nc", "data-screen",
  "data-open", "data-del", "data-geo", "data-b"];
function keyOf(el) {
  if (!el || !el.getAttribute || el === document.body) return null;
  if (el.id) return "#" + CSS.escape(el.id);
  if (el.tagName === "SUMMARY" && el.parentElement && el.parentElement.tagName === "DETAILS" && el.parentElement.id)
    return "#" + CSS.escape(el.parentElement.id) + " > summary";
  if (el.tagName === "A" && el.getAttribute("href")) return `a[href="${CSS.escape(el.getAttribute("href"))}"]`;
  const a = KEYS.find((k) => el.hasAttribute(k));
  return a ? `[${a}="${CSS.escape(el.getAttribute(a))}"]` + (el.hasAttribute("data-cid") ? `[data-cid="${CSS.escape(el.dataset.cid)}"]` : "")
    + (el.hasAttribute("data-list") ? `[data-list="${CSS.escape(el.getAttribute("data-list"))}"]` : "") : null;
}
const busyMark = (b, on) => { if (!b) return; if (on) { b.dataset.busy = "1"; b.setAttribute("aria-disabled", "true"); } else { delete b.dataset.busy; b.removeAttribute("aria-disabled"); } };
/* one request at a time per button: a double tap must not send twice (and focus stays on the button). The button is
   known by its identity, so the same button drawn again by a redraw is busy as well. A failure that its action does not
   say itself carries the action's act and the project shown at the tap (e.act, e.where): it is said as that action's
   words (see the unhandledrejection handler) */
function guard(b, fn) {
  const key = keyOf(b);
  return async (...a) => {
    if (b.dataset.busy || (key && state.running.has(key))) return;
    const act = ++state.act, where = shownKey();
    if (key) state.running.add(key);
    busyMark(b, true);
    try { return await fn(...a); } catch (e) {
      if (e && typeof e === "object" && !("act" in e)) try { e.act = act; e.where = where; } catch { /* frozen: said as a failure of no known action */ }
      throw e;
    } finally { if (key) state.running.delete(key); busyMark(b, false); if (key) busyMark($(key), false); }
  };
}
/* a row action that changes a stored value: 保存して戻る waits until it is answered */
function track(fn) {
  return async (...a) => { const p = fn(...a); state.pending.add(p); try { return await p; } finally { state.pending.delete(p); } };
}
/* while 保存して戻る saves row after row, a row action would change the rows under it: it is refused with a notice */
function idle() {
  if (!state.busy) return true;
  toast("保存して戻るの途中です。終わるまで待ってから操作してください");
  return false;
}
/* a project's identity: its id and the time it was made (SQLite gives a deleted project's id to the next new one). The
   time is created_at when the server sends it, else the first saved value (the structure, saved when it was made) */
function projectKey(p) {
  if (!p) return "";
  const first = Object.values(p.fields || {}).map((f) => (f.history && f.history.length ? f.history[0].updated_at : Infinity));
  return p.id + "@" + (p.created_at ?? Math.min(Infinity, ...first));
}
/* where and when a user action started: the view (nav.n), the project (id and identity) and the toast act. A late answer
   compares it with the present: it must not paint into another view or project, nor join a newer action's message */
function startedAt() {
  return { n: state.nav, pid: state.project ? state.project.id : null, key: projectKey(state.project), act: state.act,
    name: state.project ? state.project.name : "" };
}
/* one dialog at a time: an open one (a 根拠 table being read, a question) is never replaced or covered by a late one;
   `show` runs once no dialog is open */
function whenNoDialog(show) {
  const open = document.querySelector("dialog[open]");
  if (!open) return show();
  open.addEventListener("close", () => setTimeout(() => whenNoDialog(show), 0), { once: true });
}
/* where focus goes back when a dialog closes: the element that had it, or (a redraw has replaced it meanwhile) the
   control with the same identity */
function focusBack(el) {
  const key = keyOf(el);
  return () => { const t = el && document.contains(el) ? el : key && key !== "#main" ? $(key) : null; if (t) t.focus(); };
}
/* an information dialog; focus goes back to `returnTo` (or the element that had it) when it closes */
function dialog(title, html, returnTo) {
  whenNoDialog(() => {
    const d = $("#dlg");
    $("#dlg-title").textContent = title; $("#dlg-content").innerHTML = html;
    d.addEventListener("close", focusBack(returnTo || document.activeElement), { once: true });
    d.showModal();
  });
}
/* a question with explicit choices; resolves to the chosen value, or null when cancelled (やめる, Escape) */
function ask(title, text, choices) {
  return new Promise((resolve) => whenNoDialog(() => {
    let d = $("#ask");
    if (!d) { d = document.createElement("dialog"); d.id = "ask"; d.setAttribute("aria-labelledby", "ask-title"); document.body.appendChild(d); }
    const back = focusBack(document.activeElement);
    d.innerHTML = `<form method="dialog" class="dlg-body"><h2 id="ask-title">${esc(title)}</h2><p>${esc(text)}</p>
      <div class="dlg-actions">${choices.map((c) => `<button class="btn${c.primary ? " primary" : ""}" value="${esc(c.value)}">${esc(c.label)}</button>`).join(" ")}
      <button class="btn" value="">やめる</button></div></form>`;
    d.returnValue = "";
    d.addEventListener("close", () => { back(); resolve(d.returnValue || null); }, { once: true });
    d.showModal();
  }));
}
/* a number of 1000 or more is grouped by thousands, except in years: a calendar year (竣工年 2033) is never 「2,033 年」
   (the other fields in 年 are durations, below 1000 anyway) */
function fmt(v, unit) {
  if (v === null || v === undefined || v === "") return "—";
  if (typeof v === "number") return (Math.abs(v) >= 1000 ? v.toLocaleString("ja-JP", { maximumFractionDigits: 1, useGrouping: unit !== "年" })
    : String(+v.toPrecision(6))) + (unit ? " " + esc(unit) : "");
  if (typeof v === "object") return esc(JSON.stringify(v));
  return esc(v) + (unit ? " " + esc(unit) : "");
}
function badge(st) { const L = state.meta.states; return `<span class="badge st-${esc(st)}">${esc(L[st] || st)}</span>`; }

/* while 保存して戻る saves row after row, moving away would leave rows unsaved without notice: the first press says so,
   a second press stops the remaining saves (they are named) and moves. A second press within 400 ms of the warning is
   the same tap (a double tap on ← or ⚙): it is ignored, so only a deliberate later press stops. That holds also when
   the batch has ended between the two presses (it may have just left for the hub): the second press is still the same
   tap, and is ignored. What every row holds is taken here, before the view changes, so that the stop can name each row
   by what is stored. It is taken by the press that stops, once: a later press before the stop is answered (開く, ← from
   the view the stop led to) is no longer on the screen, and keeps what the stopping press took */
function blocked() {
  if (!state.busy) {
    if (state.busyWarned && Date.now() - state.busyWarned < 400) { state.busyWarned = 0; return true; }
    return false;
  }
  if (state.busyWarned) {
    if (Date.now() - state.busyWarned < 400) return true;
    if (!state.cancel) { state.cancel = true; state.cancelRows = state.view === "screen" ? rowsNow() : null; }
    return false;
  }
  state.busyWarned = Date.now(); state.act++;
  toast("保存の途中です。終わるまで待つか、もう一度押すと残りの行を保存せずに移ります");
  return true;
}
function go(view, arg, push = true) {
  if (push && view === state.view && arg === state.arg) return;     // already there (⚙ twice): nothing is pushed
  if (blocked()) return;
  if (push) state.stack.push([state.view, state.arg]);
  state.nav++; state.act++;
  state.view = view; state.arg = arg; render();
}
/* opening a project starts a fresh history: 戻る must never lead into the screens of another project. `at` is taken at
   the tap ({ n: the view's nav, seq: the number of this 開く }): its read answered after the user has moved, or after a
   later 開く, opens nothing (and replaces nothing). The move to the hub is the answer's, not a press: it never goes
   through blocked() (a late answer is never taken for a tap while 保存して戻る runs). Resolves to { ok, p } (p: the read) */
async function openRead(id, at) {
  let p = null;
  const ok = await loadProject(id, (x) => { p = x; return state.nav === at.n && state.openSeq === at.seq; });
  if (ok) {
    // the kept import result belongs to one project: another one (or a new one with a reused id) does not show it
    if (state.lastImport && state.lastImport.key !== projectKey(state.project)) state.lastImport = null;
    state.stack = [["home", undefined]]; state.nav++; state.act++; state.view = "hub"; state.arg = undefined; render();
  }
  return { ok, p };
}
function openProject(id) {
  if (blocked()) return Promise.resolve();
  return openRead(id, { n: state.nav, seq: ++state.openSeq });
}
/* 架空デモを開く and a structure card make a project (`make`: its request) and open it. Where the user is, and the number
   of this 開く, are taken at the tap: a project made after the user has moved or opened another project is not opened
   over theirs (what they typed stays); it is said where to find it */
async function openMade(make) {
  const at = { n: state.nav, seq: ++state.openSeq }, act = state.act;
  const r = await make(), o = await openRead(r.id, at);
  if (!o.ok) toast(`「${o.p && o.p.name ? o.p.name : "新しいプロジェクト"}」を作りました（開いていません。ホームの「続きから」から開けます）`, act);
}
/* `own`: the move of 保存して戻る itself, once its rows are saved (not a press: never taken for the second press of a tap) */
function back(own = false) {
  if (own !== true && blocked()) return;
  state.nav++; state.act++;
  const p = state.stack.pop(); if (p) { state.view = p[0]; state.arg = p[1]; render(); } else { state.view = "home"; render(); }
}
/* ← and 戻る: a second tap that comes within 400 ms of the first one's move, before its view could be seen (a double
   tap), is ignored; the token is the nav of that move */
function tapBack() {
  if (state.backNav === state.nav && Date.now() - state.backAt < 400) return;
  const n = state.nav; back();
  if (state.nav !== n) { state.backNav = state.nav; state.backAt = Date.now(); }
}

async function render() {
  const seq = ++state.seq;                        // a pending request of the previous view must not paint into this one
  const m = $("#main"); m.innerHTML = ""; window.scrollTo(0, 0);
  $("#btn-back").style.visibility = state.view === "home" ? "hidden" : "visible";
  try {
    if (state.view === "home") await renderHome(m);
    else if (state.view === "structures") await renderStructures(m);
    else if (state.view === "hub") await renderHub(m);
    else if (state.view === "screen") await renderScreen(m, state.arg);
    else if (state.view === "result") await renderResult(m);
    else if (state.view === "settings") await renderSettings(m);
    if (state.seq === seq) state.running.forEach((k) => busyMark($(k), true));
  } catch (e) { if (state.seq === seq) m.innerHTML = `<div class="notice bad">表示できなかった：${esc(e.message)}</div>`; }
  finally {
    if (state.seq === seq) m.focus({ preventScroll: true });   // screen readers start at the new view
    if (state.seq === seq && $("#toast").classList.contains("show")) { placeToast(); retoast(); }   // a toast shown: placed and named for this view
  }
  // drawn from a project that an answer has changed meanwhile: read it again and redraw (what was typed is kept)
  if (state.seq === seq && state.stale && state.project && state.stale.pid === state.project.id && ["hub", "screen"].includes(state.view))
    reloadShown(state.arg, null, true, startedAt());
}
/* a failed request inside any button handler is shown, never silently swallowed. It is said with the act of the action
   that failed (guard's e.act). A failure of no known action is said with the newest act, except while 保存して戻る runs:
   then with an act of its own. So it is never joined to the words of a 保存して戻る of another project (they would name
   it by that project). The one failure said with them is that of a row action of the same project pressed before it and
   answered while it runs (保存して戻る waits for it, as for the warnings of its answer, see warnOf): it is said with the
   batch's act and project, so that the batch's words (also those that replace older words) keep it, named elsewhere */
window.addEventListener("unhandledrejection", (e) => {
  e.preventDefault();
  const x = e.reason, msg = (x && x.message) || String(x), b = state.batch, own = !!x && typeof x.act === "number";
  if (own && state.busy && b && x.where && x.where === b.key && x.act < b.act) toast(msg, b.act, false, b.about);
  else toast(msg, own ? x.act : state.busy ? ++state.act : state.act);
});

/* ---------- home ---------- */
async function renderHome(m) {
  $("#title").textContent = state.meta.app_name;
  const seq = state.seq, projects = await api("/projects");
  if (state.seq !== seq) return;                  // the user has moved meanwhile
  m.innerHTML = `
  <div class="hero"><img id="hero-img" src="${esc(state.meta.hero.src)}" alt="${esc(state.meta.hero.alt)}">
    ${state.meta.hero.placeholder ? '<span class="ph" id="ph">プレースホルダー画像</span>' : ""}</div>
  <div class="card lift">
    <h2 style="margin-top:0">建物のホールライフカーボンを、かんたんに</h2>
    <p class="muted">住所から公開データを調べ、足りないところは根拠つきの概算で補い、研究用の 70 評価単位のモデルで計算します。</p>
    <button class="btn primary" id="start">かんたん入力スタート</button>
    <p class="muted" style="margin:10px 0 0">試しに見るなら：<button class="btn small" id="demo">架空デモを開く</button>（実在の建物ではありません）</p>
  </div>
  <div class="notice">${esc(state.meta.disclaimer)}</div>
  <div class="card"><h3 style="margin-top:0">続きから</h3>${projects.length ? projects.map((p) => `
    <div class="row" style="justify-content:space-between;border-top:1px solid var(--line);padding:8px 0">
      <div class="lname"><strong>${esc(p.name)}</strong><br><span class="muted">${esc(p.structure_label)}・入力 ${p.progress.filled}/${p.progress.total}（${p.progress.percent}%）</span></div>
      <button class="btn small" data-open="${p.id}">開く</button></div>`).join("") : '<p class="muted">まだプロジェクトはありません。</p>'}</div>`;
  $("#start").onclick = () => go("structures");
  $("#demo").onclick = guard($("#demo"), () => openMade(() => api("/demo", { method: "POST", body: {} })));
  m.querySelectorAll("[data-open]").forEach((b) => (b.onclick = guard(b, () => openProject(+b.dataset.open))));
}

/* ---------- structure select ---------- */
function renderStructures(m) {
  $("#title").textContent = "構造を選ぶ";
  m.innerHTML = `<div class="card"><label for="pname"><strong>プロジェクト名</strong>（任意）</label>
    <input id="pname" placeholder="例：〇〇ビル" maxlength="80"></div>
  <p class="muted">建物の主な構造を選んでください（あとから変えられます）。</p>
  <div class="structures" role="list">${state.meta.structures.map((s) => `
    <button class="structure" role="listitem" data-s="${s.id}" aria-label="${esc(s.label)}：${esc(s.desc)}">
      <img src="${s.img}" alt=""><h3>${esc(s.label)}</h3><p>${esc(s.desc)}</p></button>`).join("")}</div>`;
  // one project per choice: the cards share one guard (a double tap, or a tap on a second card, creates one project)
  const cards = $(".structures", m);
  m.querySelectorAll("[data-s]").forEach((b) => (b.onclick = guard(cards, () =>
    openMade(() => api("/projects", { method: "POST", body: { structure: b.dataset.s, name: $("#pname").value.trim() } })))));
}

/* a read that started after the last answer that changed the project is current: the project is no longer stale. `keep`
   decides when the answer comes whether it may still be taken (state.project is what is drawn): false discards it */
async function loadProject(id, keep = () => true) {
  const gen = state.gen, p = await api("/projects/" + id);
  if (!keep(p)) return false;
  state.project = p;
  if (state.stale && state.stale.pid === id && state.stale.gen <= gen) state.stale = null;
  return true;
}

/* ---------- project hub ---------- */
function renderHub(m) {
  const p = state.project; $("#title").textContent = p.name;
  const sc = state.meta.screens, pr = p.progress;
  m.innerHTML = `
  <div class="card"><div class="row" style="justify-content:space-between"><strong>${esc(p.structure_label)}</strong>
    <span class="muted">入力の進み具合 ${pr.filled}/${pr.total}（${pr.percent}%）</span></div>
    <div class="progress" aria-label="入力の進み具合 ${pr.percent}%"><span style="width:${pr.percent}%"></span></div>
    <p class="muted" style="margin:6px 0 0">これは入力が埋まった割合で、計算の精度ではありません。確定値 ${pr.confirmed}、図面 ${pr.from_drawing}、統計推定 ${pr.statistical}、仮定 ${pr.assumption}、あとで確認 ${pr.later}。</p></div>
  <div class="hub">${sc.map((s) => `<button class="hub-btn ${s.id}" data-screen="${s.id}">${esc(s.label)}<small>${pr.by_screen[s.id].filled}/${pr.by_screen[s.id].total} 入力済み</small></button>`).join("")}
    <button class="hub-btn result" id="to-result">結果を見る</button></div>`;
  m.querySelectorAll("[data-screen]").forEach((b) => (b.onclick = () => go("screen", b.dataset.screen)));
  $("#to-result").onclick = () => go("result");
}

/* ---------- input screens ---------- */
function fieldHtml(fid) {
  const F = state.meta.fields[fid], f = state.project.fields[fid] || {}, v = f.value;
  const st = v ? v.state : "not_obtained";
  const input = F.type === "enum"
    ? `<select id="in-${fid}" aria-label="${esc(F.label)}"><option value="">選ぶ</option>${F.enum.map((e) => `<option value="${esc(e.value)}" ${v && v.value === e.value ? "selected" : ""}>${esc(e.label)}</option>`).join("")}</select>`
    : `<input id="in-${fid}" aria-label="${esc(F.label)}" ${F.type === "number" ? 'inputmode="decimal"' : F.type === "text" ? `maxlength="${TEXT_MAX}"` : ""} value="${v && v.value !== null && typeof v.value !== "object" ? esc(v.value) : ""}" placeholder="${F.unit ? "単位：" + esc(F.unit) : ""}">`;
  const curUnit = (v && v.unit) || F.unit;
  const unitSel = F.type === "number" && (F.units || []).filter((u) => u).length > 1
    ? `<select id="unit-${fid}" aria-label="${esc(F.label)}の単位">${F.units.map((u) => `<option ${u === curUnit ? "selected" : ""}>${esc(u)}</option>`).join("")}</select>`
    : (F.unit ? `<span class="muted unit">${esc(curUnit)}</span>` : "");
  const estimated = v && (v.state === "assumption" || v.state === "statistical");
  const locked = v && v.value !== null && v.value !== undefined && !ownValue(v);
  const stateSel = `<select id="st-${fid}" aria-label="${esc(F.label)}の状態" ${locked ? `disabled title="${esc(state.meta.states[v.state])}の値の状態は、値を入れ直したときだけ変わります"` : ""}><option value="confirmed" ${estimated ? "" : "selected"}>確認済み</option><option value="assumption" ${estimated ? "selected" : ""}>仮定</option></select>`;
  const naLabel = F.na_note ? `適用外（${F.na_note}）` : F.na === "zero" ? "適用外（0 として計算）" : F.na === "absent" ? "適用外（無い）" : "適用外（渡さない）";
  const unc = v && v.uncertainty && v.uncertainty.kind === "unknown" ? `<div class="muted">範囲は不明（根拠のある幅を付けられない推定）</div>`
    : v && v.uncertainty && v.uncertainty.kind !== "none"
    ? `<div class="muted">範囲 ${fmt(v.uncertainty.low, v.unit)} 〜 ${fmt(v.uncertainty.high, v.unit)}${v.uncertainty.kind === "interval" ? (v.uncertainty.calibrated ? "（校正済みの予測区間）" : "（仮の範囲）") : "（シナリオ）"}</div>` : "";
  const ml = (m) => esc((state.meta.methods || {})[m] || m);
  const cands = (f.candidates || []).map((c) => { const d = candRows(fid, c); return `<li><div>${fmt(c.value, c.unit)} ${badge(c.state)} <span class="muted">${ml(c.method)}</span></div>
      ${c.uncertainty && c.uncertainty.kind === "unknown" ? `<div class="muted">範囲は不明</div>` : ""}
      ${c.uncertainty && c.uncertainty.kind !== "none" && c.uncertainty.kind !== "unknown" ? `<div class="muted">範囲 ${fmt(c.uncertainty.low, c.unit)} 〜 ${fmt(c.uncertainty.high, c.unit)}${c.uncertainty.calibrated ? "" : "（仮の範囲）"}</div>` : ""}
      <div class="muted">${c.source_id ? "出典 " + esc(c.source_id) + (c.source_detail ? "：" + esc(c.source_detail) : "") : ""}</div>
      ${dependsHtml(c.depends)}
      <div class="muted">${esc(c.note || "")}</div>${d.rows}${d.warn}<button class="btn small" data-accept="${esc(fid)}" data-cid="${esc(c.id)}">この候補を採用</button></li>`; }).join("");
  return `<div class="field${state.asking === fid ? " asking" : ""}" id="f-${fid}">
    <div class="field-head"><label for="in-${fid}">${esc(F.label)}${F.required ? ' <span class="muted">（計算に必須）</span>' : ""}</label>${badge(st)}</div>
    <div class="value">${v ? fmt(v.value, v.unit) : '<span class="muted">未取得</span>'}${f.later ? ' <span class="badge st-statistical">あとで確認</span>' : ""}</div>${unc}
    ${F.help ? `<div class="muted">${esc(F.help)}</div>` : ""}
    ${F.type === "table" ? `<div class="muted">表の入力は「資料の読み込み」か自動概算で行います（${(v && Array.isArray(v.value)) ? v.value.length + " 行" : "未入力"}）。</div>` :
      `<div class="edit">${input}<div class="row">${unitSel}${stateSel}<button class="btn small" data-save="${fid}">保存</button></div></div>`}
    <div class="actions">
      <button class="btn small" data-why="${fid}">根拠を表示</button>
      ${F.estimable ? `<button class="btn small" data-est="${fid}">自動概算</button>` : ""}
      ${F.na_never ? "" : `<button class="btn small" data-na="${fid}">${naLabel}</button>`}
      <button class="btn small" data-later="${fid}">${f.later ? "確認済みにする" : "あとで確認"}</button>
      ${v && v.state !== "not_obtained" ? `<button class="btn small" data-unset="${fid}">未取得に戻す</button>` : ""}
      <button class="btn small" data-nc="${fid}">計算不能</button>
    </div>${cands ? `<ul class="cands" aria-label="候補">${cands}</ul>` : ""}</div>`;
}

/* a candidate read from a document: the rows it adds up, and the rows naming this field's material that it left out with
   their reason (at most 200 of each are sent). When some were left out for a reason that may be wrong (n_maybe), the
   candidate may be too low: that is said next to 採用. Candidates without these keys (older ones, estimates) show nothing.
   A left-out row may carry its quantity and unit (shown like the added rows) and `maybe` (it may belong in the total:
   marked in words and listed first); older left-out rows without these keys show their name, place and reason only.
   A number is kept on one line (class num); a quantity that is text (a note in the quantity column, up to 40 characters)
   wraps like the name (class qtext), so it cannot push the card or the bottom bar past a phone's width */
function candRows(fid, c) {
  const has = (x) => x !== undefined && x !== null && x !== "";
  const qty = (x, u) => (typeof x === "number" ? `<span class="num">${fmt(x, "")}` : `<span class="qtext">${esc(x ?? "")}`) + (u ? " " + esc(u) : "") + "</span>";
  const count = (n, xs) => (Number.isInteger(n) && n >= xs.length ? n : xs.length);
  const more = (n, xs) => (n <= xs.length ? "" : xs.length ? `<li class="muted">ほか ${n - xs.length} 行（記録は最初の ${xs.length} 行まで）</li>`
    : `<li class="muted">行の一覧は記録されていません</li>`);
  const rows = Array.isArray(c.rows) ? c.rows : [], ex0 = Array.isArray(c.excluded) ? c.excluded.filter((r) => r && typeof r === "object") : [];
  const ex = ex0.filter((r) => r.maybe === true).concat(ex0.filter((r) => r.maybe !== true));
  const nr = count(c.n_rows, rows), ne = count(c.n_excluded, ex), maybe = Number.isInteger(c.n_maybe) && c.n_maybe > 0 ? c.n_maybe : 0;
  const id = (k) => `${k}-${esc(fid)}-${esc(c.id)}`;
  let h = "";
  if (nr) h += `<details id="${id("cr")}"><summary>足した行（${nr} 行）</summary><ul class="crows">${rows.map((r) =>
    `<li>${esc(r.name)} <span class="muted">${esc(r.trace)}</span> ${qty(r.quantity, r.unit)}</li>`).join("")}${more(nr, rows)}</ul></details>`;
  if (ne) h += `<details id="${id("cx")}"${maybe && ex.length <= 8 ? " open" : ""}><summary>この欄の材料の行で足さなかった行（${ne} 行）</summary><ul class="crows">${ex.map((r) =>
    `<li>${esc(r.name)} <span class="muted">${esc(r.trace)}</span>${has(r.quantity) ? ` ${qty(r.quantity, r.unit)}` : ""}${
      r.maybe === true ? ' <strong class="maybe">足すべきかもしれない</strong>' : ""}<div class="muted">${esc(r.reason)}</div></li>`).join("")}${more(ne, ex)}</ul></details>`;
  else if (c.n_excluded === 0) h += `<div class="muted">この欄の材料の行で足さなかった行：なし</div>`;
  // the quantity those rows would add, when every one of them is listed with a number in the candidate's unit
  const mq = ex.filter((r) => r.maybe === true);
  const sum = maybe && mq.length === maybe && mq.every((r) => typeof r.quantity === "number" && Number.isFinite(r.quantity) && r.unit === c.unit)
    ? `。その ${maybe} 行の数量は計 ${fmt(mq.reduce((a, r) => a + r.quantity, 0), c.unit)}` : "";
  const warn = maybe ? `<div class="notice bad">足さなかった行のうち ${maybe} 行は、足すべき行かもしれません（理由を確かめてください${sum}）。この候補は少なめのことがあります</div>` : "";
  return { rows: h, warn };
}

/* the premises an estimate was made from (floor area, structure, use group): shown so that a stale one is visible */
function dependsHtml(dep) {
  if (!dep || !Object.keys(dep).length) return "";
  const name = { b_use_group: "用途の区分" };
  const valueLabel = { residential: "住宅", non_residential: "住宅以外" };
  const parts = Object.entries(dep).map(([k, x]) => {
    const F = state.meta.fields[k];
    const label = name[k] || (F ? F.label : k);
    const shown = F && F.type === "enum" ? ((F.enum.find((e) => e.value === x) || {}).label || x)
      : (typeof x === "number" ? fmt(x, F ? F.unit : "") : (valueLabel[x] || x));
    return `${esc(label)} ${typeof shown === "string" && typeof x !== "number" ? esc(shown) : shown}`;
  });
  return `<div class="muted">前提：${parts.join("・")}</div>`;
}

function renderScreen(m, sid) {
  const S = state.meta.screens.find((s) => s.id === sid);
  $("#title").textContent = S.label;
  const pri = state.meta.priority[state.project.structure] || {};
  const key = projectKey(state.project), importing = state.importing && state.importing.key === key && state.importing.sid === sid;
  const extra = sid === "basic" ? `<div class="card"><h3 style="margin-top:0">住所から調べる</h3>
      <div class="edit"><input id="addr" placeholder="住所または建物名" aria-label="住所または建物名"><button class="btn small" id="btn-geo">住所を検索</button></div>
      <div id="geo-out"></div><p class="muted">国土地理院の住所検索と、PLATEAU（国土交通省）の公開建物データを使います。候補は確認してから採用してください。住所は検索のときだけ国土地理院に送ります。</p></div>
      <div class="card"><h3 style="margin-top:0">地盤（参考）</h3>
      <p class="muted">近くのボーリング調査の記録は、国土地盤情報検索サイト（KuniJiban）で見られます。アプリは自動では取得しません。
      見つけた地点の<strong>距離・調査年・孔番号</strong>を「近くのボーリング調査」に書き留めてください。近くの記録は敷地の地盤そのものではなく、
      基礎の形式（直接基礎・杭・地盤改良）を決めるものでもありません。</p>
      <div class="row"><a class="btn small" href="https://www.kunijiban.pwri.go.jp/" target="_blank" rel="noopener noreferrer">KuniJiban を開く</a>
      <a class="btn small" href="https://www.kunijiban.pwri.go.jp/jp/terms.html" target="_blank" rel="noopener noreferrer">利用規約</a></div></div>`
    : sid === "material" ? `<div class="card"><h3 style="margin-top:0">資料を読み込む</h3>
      <p class="muted">数量表（CSV・Excel）、IFC、PDF（文字のあるもの）。読んだ数値は候補になり、原本の場所（シート・セル、部材 ID、ページ）を記録します。</p>
      <input type="file" id="docfile" accept=".csv,.xlsx,.ifc,.pdf" aria-label="資料ファイル"${importing ? ' disabled aria-busy="true"' : ""}><div id="doc-out">${
        importing ? '<p class="muted">読み込み中…</p>' : state.lastImport && state.lastImport.key === key && state.lastImport.sid === sid ? state.lastImport.html : ""}</div>
      <p class="muted">原本は既定では保存しません（読んだ数値の候補と、ファイルの指紋だけを残します）。メーカーの BIM データは各社の利用条件（設計検討の目的に限る・使用後は消去など）に従ってください。製品の性能値（質量・冷媒量）は製造時の CO2 ではありません。</p></div>` : "";
  m.innerHTML = extra + S.groups.map((g) => {
    const fids = [...g.fields].sort((a, b) => (pri[b] || 0) - (pri[a] || 0));
    return `<div class="card group"><h3>${esc(g.label)}</h3>${fids.map(fieldHtml).join("")}</div>`;
  }).join("") + `<div class="bottombar"><button class="btn" id="bb-back">戻る</button><button class="btn" id="bb-est">この画面を自動概算</button><button class="btn" id="bb-hub"${state.busy ? ' data-busy="1" aria-disabled="true"' : ""}>保存して戻る</button></div>`;
  bindScreen(m, sid);
}

/* a typed number: full-width digits allowed; a comma only as a thousands separator ("12,500"), never as a decimal
   point ("1,5" is refused instead of becoming 15) */
function parseNumber(raw) {
  raw = raw.trim();
  if (raw.length > 100) return { bad: true, why: "数値として長すぎます" };
  if (/[^0-9+\-.,eE \u3000\u2212\uff0b\uff0d\uff0e\uff0c\uff25\uff45\uff10-\uff19]/.test(raw)) return { bad: true, why: "使えない文字があります" };
  let t = raw.normalize("NFKC").replace(/\u2212/g, "-");
  if (/\s/.test(t)) return { bad: true, why: "数の中に空白があります（3 桁の区切りはカンマ）" };
  if (t.includes(",")) { if (!/^[+-]?\d{1,3}(,\d{3})+(\.\d+)?$/.test(t)) return { bad: true, why: "カンマは 3 桁ごとの区切りだけに使ってください（小数点はピリオド）" }; t = t.replace(/,/g, ""); }
  if (!/^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$/.test(t)) return { bad: true };
  const v = Number(t);
  if (!Number.isFinite(v)) return { bad: true };
  if (v === 0 && /[1-9]/.test(t.split(/[eE]/)[0])) return { bad: true, why: "小さすぎて 0 になってしまう数です" };
  return { value: v };
}
function inputValue(fid) {
  const F = state.meta.fields[fid], el = $("#in-" + fid);
  if (!el) return { empty: true };
  const raw = el.value.trim();
  if (raw === "") return { empty: true };
  if (F.type === "number") return parseNumber(raw);
  // a text keeps at most TEXT_MAX characters, counted as the server counts them (after its trimming, see storedText):
  // a longer one is never sent (it would be refused, or cut without a word). The input takes no more (maxlength); this
  // holds whatever put the text there
  if (F.type === "text") { const n = [...storedText(raw)].length; if (n > TEXT_MAX) return { bad: true, long: n }; }
  return { value: raw };
}
/* a text row keeps at most this many characters (the server keeps no more) */
const TEXT_MAX = 500;
/* what the server keeps of a text sent (it strips the ends as Python's str.strip() does: also U+001C–U+001F and U+0085,
   which JavaScript's trim() leaves; U+FEFF, which trim() strips, is gone before it is sent). The same characters as
   in storedAs */
const storedText = (s) => s.replace(/^[\t-\r\x1c-\x20\x85\xa0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+|[\t-\r\x1c-\x20\x85\xa0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+$/g, "");
/* the words for a row that cannot be saved as it is (inputValue's `bad`): a number that cannot be read, or a text longer
   than the server keeps */
const badWords = (fid, iv) => `「${state.meta.fields[fid].label}」は` + (iv.long ? ` ${TEXT_MAX} 字までにしてください（いま ${iv.long} 字）`
  : `数値で入力してください${iv.why ? "（" + iv.why + "）" : ""}`);
/* what a control showed when the screen was drawn (the stored value then): typed / changed always means "differs from
   what was drawn", never "differs from state.project", so a reload can never turn a drawn value into a typed one */
function drawn(el) {
  if (el.tagName !== "SELECT") return el.defaultValue;
  const o = [...el.options].find((x) => x.defaultSelected) || el.options[0];
  return o ? o.value : "";
}
/* the input was emptied although a value was drawn: say that it was not removed, and show the drawn value again */
function clearedInput(fid) {
  const el = $("#in-" + fid);
  return !!(el && el.value.trim() === "" && drawn(el).trim() !== "");
}
/* …but never into the input the user is in: a key typed next would be added to the value put there (they may be
   retyping the row). That input stays as the user left it; the message says the value was not removed */
function restoreInput(fid) {
  const el = $("#in-" + fid);
  if (!el || el === document.activeElement) return;
  el.value = drawn(el);
  delete el.dataset.touched;                       // it shows the drawn value again, as if untouched
}
/* a row the user has changed since it was drawn: an input or change event on its text, unit or state (dataset.touched,
   set in bindScreen and kept across redraws by putBack), whatever its text is now. Its text may equal the value drawn
   (the first key of a correction, a revert, an emptied row being retyped): it is the user's all the same */
const touchedRow = (f) => ["in-", "unit-", "st-"].some((p) => { const el = document.getElementById(p + f); return !!(el && el.dataset.touched); });
function ownValue(cur) {
  return cur && ["user_entered", "initial_setting", "structure_card"].includes(cur.method) && !["statistical", "from_drawing"].includes(cur.state);
}
/* the one test of "not saved yet", for the notice after a redraw and for 保存して戻る alike: the row holds a readable value,
   and it, its unit or its state (when the state can be changed) differs from what was drawn. A unit or state chosen on an
   empty row is no change to save (nothing would be sent); it is kept across redraws all the same */
function isDirty(fid) {
  const F = state.meta.fields[fid], inp = $("#in-" + fid), iv = inputValue(fid);
  if (!inp || iv.empty || iv.bad) return false;
  const was = drawn(inp).trim(), us = $("#unit-" + fid), st = $("#st-" + fid);
  const wv = F.type === "number" ? parseNumber(was) : { value: was };
  if (was === "" || wv.bad || wv.value !== iv.value) return true;
  if (us && us.value !== drawn(us)) return true;
  return !!(st && !st.disabled && st.value !== drawn(st));       // a state-only change (one's own value: the select is open)
}
/* what a row's controls hold now: its text, its unit, and its state when the state can be chosen. An action records it
   when it is sent, so that a late answer (or 保存して戻る) can tell whether the user has changed the row since */
function rowNow(fid) {
  const inp = $("#in-" + fid);
  if (!inp) return null;
  const us = $("#unit-" + fid), st = $("#st-" + fid);
  return { v: inp.value, u: us ? us.value : null, s: st && !st.disabled ? st.value : null };
}
const sameRow = (a, b) => !!a && !!b && a.v === b.v && a.u === b.u && a.s === b.s;
/* every row of the screen as it is now, with whether it is typed and what it reads as (for a stop, before the view goes) */
function rowsNow() {
  const out = {};
  document.querySelectorAll("#main [data-save]").forEach((b) => {
    const f = b.dataset.save, x = rowNow(f);
    if (x) out[f] = { ...x, typed: isDirty(f), iv: inputValue(f) };
  });
  return out;
}
/* the stored value of row `f` in project `p` is what row snapshot `x` reads as (value, unit, and the chosen state). A
   text is compared as the server keeps it (its ends stripped as Python's str.strip() strips them: see storedText), so
   that a text stored as sent is never taken for one corrected after it was sent */
function storedAs(p, f, x) {
  const v = p && p.fields && (p.fields[f] || {}).value;
  const kept = (s) => (typeof s === "string" ? s.replace(/^[\t-\r\x1c-\x20\x85\xa0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+|[\t-\r\x1c-\x20\x85\xa0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+$/g, "") : s);
  return !!(v && x && x.iv && !x.iv.bad && !x.iv.empty && v.value === kept(x.iv.value)
    && (x.u === null || !v.unit || v.unit === x.u) && (x.s === null || v.state === x.s));
}
/* save one row: "saved" | "unchanged" | "refused" | "cancelled". With batch=true nothing is re-rendered (the other rows
   keep what was typed) and a refusal's reason is returned in saveField.reason */
async function saveField(fid, quiet = false, batch = false) {
  saveField.reason = "";
  saveField.sent = rowNow(fid);               // what the row held when it was read (the value sent, or found unchanged)
  const nav = startedAt(), sid = state.arg;
  const say = (msg) => toast(msg, nav.act);
  // `offline`: the refusal is that the server cannot be reached (api() said so). The reload after it is still tried (the
  // server may be back; the project is read again at its next drawing all the same), but its failure for the same reason
  // is not said a second time in the same message
  const refuse = async (msg, reload = true, offline = false) => {
    saveField.reason = msg;
    if (!batch) {
      say(msg);
      if (reload) await refresh(sid, fid, true, nav).catch((e) => { if (!(offline && e && e.offline)) throw e; });
    }
    return "refused";
  };
  // a question is about one row: it names the row and the values, and the row is brought into view and marked
  // (the mark is kept in state.asking: a late redraw while the question is open draws the row marked again)
  const askRow = async (title, text, choices) => {
    const row = $("#f-" + fid);
    row?.scrollIntoView({ block: "center" }); row?.classList.add("asking"); state.asking = fid;
    try { return await ask(`「${state.meta.fields[fid].label}」：${title}`, text, choices); }
    finally { if (state.asking === fid) state.asking = null; $("#f-" + fid)?.classList.remove("asking"); }
  };
  const shown = (x, u) => `${x}${u ? " " + u : ""}`;
  const F = state.meta.fields[fid], iv = inputValue(fid);
  if (iv.empty && clearedInput(fid)) {
    restoreInput(fid);
    return refuse(`「${F.label}」の空欄は保存していません（値は消えていません）。値を消すときは「未取得に戻す」を押してください`, false);
  }
  if (iv.empty) {
    const cur0 = (state.project.fields[fid] || {}).value;
    if (!quiet) say(cur0 && cur0.state !== "not_obtained" ? `空欄は保存しません（今の「${state.meta.states[cur0.state]}」のまま）`
      : "空欄は保存しません（未取得のまま。0 にはしません）");
    return "unchanged";
  }
  if (iv.bad) return refuse(badWords(fid, iv), false);
  const value = iv.value;
  const cur = (state.project.fields[fid] || {}).value;
  const us = $("#unit-" + fid), unit = us ? us.value : ((cur && cur.unit) || F.unit);
  const st = $("#st-" + fid).value;
  const body = { value, unit: F.type === "number" ? unit : "", state: st, method: "user_entered" };
  if (cur && cur.value === value) {
    const sameUnit = F.type !== "number" || !cur.unit || cur.unit === unit;
    if (!ownValue(cur)) {
      if (!sameUnit) return refuse(`${state.meta.states[cur.state]}の値の単位は付け直せません（候補を採用し直すか、「未取得に戻す」のあと入れ直す）`);
      if (!quiet) say(`値が変わっていないので保存しません（${state.meta.states[cur.state]}の出典・範囲を残します）`);
      return "unchanged";
    }
    if (sameUnit && cur.state === st) { if (!quiet) say("変更はありません"); return "unchanged"; }
    if (!sameUnit) {
      const a = await askRow("単位の付け直し", `数値 ${value} はそのままで、単位を ${cur.unit} から ${unit} に付け直します（自分で入れた値の単位の付け間違いを直すとき）。換算したいときは、換算した数値を入れてください。`,
        [{ value: "yes", label: "付け直す", primary: true }]);
      if (!a) return "cancelled";
      body.relabel = true;
    }
    if (cur.scope) body.scope = cur.scope;                       // what the value covers stays with it
  } else {
    const carriesEstimate = cur && (cur.state === "statistical" || (cur.depends && Object.keys(cur.depends).length)
      || (cur.uncertainty && cur.uncertainty.kind === "unknown" && cur.source_id));
    if (carriesEstimate) {
      const what = cur.state === "statistical" ? `統計の推定（${(state.meta.methods || {})[cur.method] || cur.method}）` : `推定（${cur.source_id || "出典つき"}）を手で直した値`;
      const a = await askRow("推定を直した値ですか", `今の値 ${shown(cur.value, cur.unit)} は${what}でした。新しい値 ${shown(value, F.type === "number" ? unit : "")} も、その推定を手で直したものですか？`,
        [{ value: "fix", label: "推定を手で直した（範囲・前提を引き継ぐ。範囲は「不明」になる）", primary: true },
         { value: "new", label: "別に調べた値" }]);
      if (!a) return "cancelled";
      if (a === "fix") body.from_estimate = true;
    }
    if (cur && cur.scope && !body.from_estimate) {
      // what the new value covers must be said: the server refuses to guess (it decides the double-counting guard)
      const what = cur.scope === "whole_building" ? "基礎・杭を含む建物全体の量" : "鉄筋と鉄骨を合わせた鉄の全量";
      const a = await askRow("新しい値の範囲", `今の値 ${shown(cur.value, cur.unit)} は「${what}」でした。新しい値 ${shown(value, unit)} も${what}ですか？`,
        [{ value: "same", label: `${what}（もう一方の欄と二重に数えない）`, primary: true }, { value: "field", label: "この欄だけの量" }]);
      if (!a) return "cancelled";
      body.scope = a === "same" ? cur.scope : "field_only";
    }
  }
  let r;
  try { r = await api(`/projects/${nav.pid}/fields/${fid}`, { method: "PUT", body }); } catch (e) { return refuse(`「${F.label}」：${e.message}`, true, !!e.offline); }
  warnOf(r, nav);
  return "saved";
}

function bindScreen(m, sid) {
  $("#bb-back").onclick = tapBack;
  // one 保存して戻る at a time, whatever was redrawn meanwhile: the guard is state.busy, not the button (a redraw draws a
  // new button, drawn busy too). While it runs, moving away waits (see blocked()) and row actions are refused (idle())
  $("#bb-hub").onclick = async () => {
    if (state.busy) return;
    state.act++; state.busy = true; state.busyWarned = 0; state.cancel = false; state.cancelRows = null; busyMark($("#bb-hub"), true);
    state.batch = { n: state.nav, key: projectKey(state.project), act: state.act, about: { key: projectKey(state.project), name: state.project.name } };
    let after = null;
    // a warning still kept (saveAndBack failed before saying its words) is said as the server said it
    try { after = await saveAndBack(); } finally { state.busy = false; busyMark($("#bb-hub"), false); sayWarnings(toast._act); state.batch = null; }
    if (after) await after();
    // an estimate's explanation that came while the rows were saved is shown when its screen is still there
    const n = state.noteLater; state.noteLater = null;
    if (n) estimateNote(n);
  };
  const label = (f) => "「" + state.meta.fields[f].label + "」";
  const names = (fs) => [...new Set(fs)].map(label).join("");
  // 保存して戻る: every row whose input differs from what was drawn is saved like its own 保存 button. What each row held
  // when it was sent is recorded: a row typed or corrected while the batch was saving is saved in another pass (or, when
  // it cannot be saved as it is, the batch stays and names it), so it never leaves with a row not saved as shown.
  // Resolves to what is to be done once state.busy is off (after a stop: read the project again and redraw what shows it)
  const saveAndBack = async () => {
    const nav = startedAt(), pid = nav.pid;
    // its messages are not joined to a later tap's; they are about its project (named when read on another one)
    const about = { key: nav.key, name: nav.name };
    // `hold`: the words name rows not saved (the batch stays): they stay until 閉じる. The warnings kept are said with
    // them, except those whose field is no longer stored as 適用外 in the batch's last read (state.project, when it is
    // still the batch's project, and when the batch's latest read has not failed: `fresh`; else every one is said)
    const say = (msg, hold = false, fresh = true) => {
      toast(msg, nav.act, false, about, hold);
      sayWarnings(nav.act, fresh && projectKey(state.project) === nav.key ? state.project : null);
    };
    const moved = () => state.cancel || state.nav !== nav.n || !state.project || state.project.id !== pid;
    // the batch's reads of its project: taken only while its view is still there and shows its project. One answered
    // after the user has stopped it, left, or opened another project is discarded (the stop reads what is stored itself)
    const read = () => loadProject(pid, (p) => !moved() && projectKey(p) === nav.key && projectKey(state.project) === nav.key);
    // a read that failed (the server cannot be reached, or its answer cannot be read): the batch stays and says so with
    // its words, held (see stay). Nothing is drawn again (every row keeps what is typed in it; the rows' marks are those
    // of the last read) and the project is read again at its next drawing (state.stale)
    const unread = (e) => { state.stale = { pid, gen: ++state.gen }; return e; };
    const unreadWords = (e, msg) => (e.message && msg.includes(e.message) ? "。同じ理由で画面を読み直せませんでした" : `。画面を読み直せませんでした：${e.message}`)
      + "。行の状態の表示は古いままです";
    const saved = [], same = [], refused = [], refusedRows = [], sent = {};
    // at the press: what is drawn (state.project) and what every row holds. The rows' own actions still under way (a 保存,
    // 適用外, 未取得に戻す, 計算不能, この候補を採用 just pressed) are answered while the batch runs, and their redraw is
    // skipped: the batch names what they stored (stored by their own action below), so that the user is told. A row
    // typed at the press and stored as typed is named saved; any other row stored since the press is named by its new state
    const p0 = state.project, at0 = rowsNow();
    const fieldsHere = state.meta.screens.find((s) => s.id === sid).groups.flatMap((g) => g.fields);
    const histLen = (p, f) => (((p && p.fields && p.fields[f]) || {}).history || []).length;
    const byOwn = (p, skip) => {
      const ok = [], to = {};
      for (const f of fieldsHere) {
        if (skip.includes(f) || histLen(p, f) <= histLen(p0, f)) continue;
        if (at0[f] && at0[f].typed && storedAs(p, f, at0[f])) { ok.push(f); continue; }
        const st = ((p.fields[f] || {}).value || {}).state || "not_obtained";
        (to[st] = to[st] || []).push(f);
      }
      return { ok, to: Object.entries(to).map(([st, fs]) => `${names(fs)}は「${state.meta.states[st] || st}」になりました`) };
    };
    // a stop names every row's outcome: saved, refused (with the reason), unchanged, not sent. When the user stopped,
    // blocked() took what each row held: that is compared with what is stored now, so a row stored by its own 保存 is
    // named saved, a row corrected after it was sent is said to keep its earlier value, and a row typed meanwhile is named.
    // A row its own action decided (owed its stored value, unchanged since the action was sent: also when the action was
    // answered after the stop) is named by what is stored. Any row stored since the press by a write the batch did not send
    // is named by what is stored; when it holds what was never sent (typed after its action) it is also named not saved,
    // and when that write stored what it held at the press (its own 保存) it is said to keep its earlier value: also when
    // the row, still to be saved by the batch (rest), was put back to the value drawn, emptied or made unreadable after the
    // press (it is no longer typed, and it is named once). Said while another project is shown (a 開く before the stop was
    // answered), the words name their project (see toast's `about`)
    const stop = async (rest) => {
      const at = state.cancelRows;
      let p = null;
      if (at) try { p = await api("/projects/" + pid); } catch { p = null; }
      let ok = saved, early = [], lost = rest, to = [];
      if (p) {
        ok = []; lost = [];
        const decided = (f, x) => { const o = state.owed.get(f); return !!(o && o.n === nav.n && sameRow(x, o.row)); };
        const ownSave = (f) => !saved.includes(f) && histLen(p, f) > histLen(p0, f) && !!at0[f] && at0[f].typed && storedAs(p, f, at0[f]);
        for (const [f, x] of Object.entries(at)) {
          if (same.includes(f) || refusedRows.includes(f) || decided(f, x)) continue;
          if (x.typed && storedAs(p, f, x)) ok.push(f);
          else if (saved.includes(f) || ((x.typed || rest.includes(f)) && ownSave(f))) early.push(f);
          else if (x.typed || rest.includes(f)) lost.push(f);
        }
        const own = byOwn(p, ok.concat(early, same, refusedRows, saved));
        ok = ok.concat(own.ok); to = own.to;
      }
      const act = ++state.act;
      // the rows not saved are named first (a long message is read from its start), and words that name rows not saved
      // stay until 閉じる
      const short = !lost.length && !early.length && !refused.length;
      toast(short
        ? ([ok.length ? `${names(ok)}を保存しました` : "", ...to].filter(Boolean).join("。") || "保存する変更はありませんでした")
        : "保存して戻るを途中でやめました：" + [lost.length ? names(lost) + "は保存していません" : "", ok.length ? names(ok) + "は保存しました" : "",
          early.length ? names(early) + "は直す前の値を保存しました（あとで直した値は保存していません）" : "", ...refused, ...to,
          same.length ? names(same) + "は変わっていないので送っていません" : ""]
          .filter(Boolean).join("。"), act, false, about, !short);
      sayWarnings(act, p && projectKey(p) === nav.key ? p : null);
      // the next drawing shows what is stored; when that read fails, its reason is said with the stop's words
      return () => refresh(sid, null, true, nav).catch((e) => toast(e.message, act, false, about));
    };
    // the batch stays on the screen, drawn from what is stored now: a saved row that still holds what was sent shows its
    // stored value, and so does an emptied row in `cleared` (its value was not removed) unless the user is in it. Every
    // other row the user has touched stays as it is, whatever its text (a saved row corrected after it was sent, also
    // back to the value drawn before: it was not saved as shown). The focus and caret stay where the user is; the named
    // row `fid` is focused only when the user is on no control of their own. The reason is said. When the read fails
    // (or `failed`, a read that has failed just before), nothing is drawn again: the words are said all the same, with the
    // read's reason (`told`: `msg` says it already), and an emptied row in `cleared` shows again what it held (what the
    // batch sent in it, else the value drawn)
    const stay = async (msg, fid, rest, cleared = [], failed = null, told = false) => {
      if (!failed) try { await read(); } catch (e) { failed = unread(e); }
      if (moved()) return stop(rest);
      const early = saved.filter((f) => !sameRow(rowNow(f), sent[f]) && !cleared.includes(f));
      const refill = cleared.filter((f) => $("#in-" + f) !== document.activeElement);
      if (!failed) {
        const drop = saved.filter((f) => !early.includes(f) && !cleared.includes(f)).concat(refill);
        await redraw(nav, null, true, true, { drop, focus: fid });    // kept after the read: what was typed meanwhile is kept too
      } else {
        refill.forEach((f) => { const el = $("#in-" + f); if (el && sent[f]) el.value = sent[f].v; else restoreInput(f); });
        if (fid && atStart()) $("#in-" + fid)?.focus();
      }
      const ok = saved.filter((f) => !early.includes(f));
      say(msg + "。戻りません" + (ok.length ? `（${names(ok)}は保存しました）` : "")
        + (early.length ? `（${names(early)}は直す前の値を保存しました。直した値はまだ保存していません）` : "")
        + (failed ? (told ? "。行の状態の表示は古いままです" : unreadWords(failed, msg)) : ""), true, !failed);
      return null;
    };
    // the user is on no control of their own: nowhere, or on 保存して戻る (a named row may then be focused)
    const atStart = () => { const a = document.activeElement; return !a || a === document.body || a === m || a.id === "bb-hub"; };
    const typedNow = () => [...m.querySelectorAll("[data-save]")].map((b) => b.dataset.save).filter(isDirty);
    // a row action still under way (a 保存 just pressed …) is answered first, and the screen is drawn from what it stored;
    // a row the user has touched since it was drawn stays as it is (also when its text is back to the value drawn before:
    // that is what the screen shows, and what is saved when it differs from what is stored now), except the acted rows
    // unchanged since their action was sent: they show what their action stored, as their own redraw would have
    // (redraw pays state.owed), so the text typed before 未取得に戻す / 適用外 / 採用 is not saved over it
    if (state.pending.size) {
      const before = typedNow();
      await Promise.allSettled([...state.pending]);
      if (moved()) return stop(before);
    }
    if ((state.stale && state.stale.pid === pid) || [...state.owed.values()].some((x) => x.n === nav.n)) {
      const before = typedNow();
      let failed = null;
      try { await read(); } catch (e) { failed = unread(e); }
      if (moved()) return stop(before);
      if (failed) return stay(`保存の前に画面を読み直せませんでした：${failed.message}。どの行も保存していません`, null, before, [], failed, true);
      await redraw(nav, null, true, true);
    }
    const rows = [...m.querySelectorAll("[data-save]")].map((b) => b.dataset.save);
    const cleared = rows.filter(clearedInput);
    if (cleared.length) {
      cleared.forEach(restoreInput);                   // not into the input the user is in (see restoreInput)
      say(`空欄にした${names(cleared)}は保存していません（値は消えていません）。消すときは「未取得に戻す」を押してください。ほかの行も保存していません。戻りません`, true);
      if (atStart()) $("#in-" + cleared[0])?.focus();
      return null;
    }
    // a number that cannot be read is said before anything is saved (it is never silently dropped)
    const bad = rows.filter((f) => inputValue(f).bad);
    if (bad.length) {
      const iv = inputValue(bad[0]);
      say(`${badWords(bad[0], iv)}。保存していません`, true);
      if (atStart()) $("#in-" + bad[0]).focus();
      return null;
    }
    let dirty = rows.filter(isDirty);
    for (let pass = 0; ; pass++) {
      for (const [i, fid] of dirty.entries()) {
        if (moved()) return stop(dirty.slice(i));
        // a row emptied before its turn is not sent, and nothing is written into it (the user may be retyping it, or
        // withdrawing it): the check before leaving saves what is typed in it by then, or names it when a value was
        // drawn in it (an emptied row does not remove a value)
        if (inputValue(fid).empty) continue;
        const r = await saveField(fid, true, true);
        if (r === "saved" || r === "unchanged") sent[fid] = saveField.sent;
        if (r === "saved") { if (!saved.includes(fid)) saved.push(fid); if (same.includes(fid)) same.splice(same.indexOf(fid), 1); }
        else if (r === "unchanged") { if (!saved.includes(fid) && !same.includes(fid)) same.push(fid); }
        else if (r === "refused") { refused.push(saveField.reason); refusedRows.push(fid); }
        // the row that was under way is named by its outcome; the rows after it were not sent
        if (moved()) return stop((r === "cancelled" ? [fid] : []).concat(dirty.slice(i + 1)));
        // redraw: the saved rows, badges and candidates become current; what was typed in the others stays
        if (r === "refused" || r === "cancelled")
          return stay(r === "refused" ? saveField.reason : `「${state.meta.fields[fid].label}」の保存をやめました`, fid, dirty.slice(i + 1));
      }
      if (moved()) return stop([]);
      // the read before leaving: when it fails, the batch stays (what the screens would show cannot be told), and its
      // words name the rows saved, and those changed meanwhile as not saved (no other pass is tried)
      let failed = null;
      try { await read(); } catch (e) { failed = unread(e); }
      if (moved()) return stop([]);
      // checked again just before leaving: a row typed, corrected or emptied while the rows were saved holds what was not
      // sent. It is saved in another pass; one that cannot be saved as it is (emptied, unreadable) keeps the batch here
      const late = rows.filter((f) => (sent[f] ? !sameRow(rowNow(f), sent[f]) : isDirty(f) || clearedInput(f) || inputValue(f).bad));
      if (failed && !late.length) return stay(`保存のあと画面を読み直せませんでした：${failed.message}`, null, [], [], failed, true);
      if (!late.length) break;
      const lateCleared = late.filter((f) => clearedInput(f) || (sent[f] && inputValue(f).empty)), lateBad = late.filter((f) => inputValue(f).bad);
      if (lateCleared.length)
        return stay(`保存して戻るの間に空欄にした${names(lateCleared)}は保存していません（値は消えていません）。消すときは「未取得に戻す」を押してください`, lateCleared[0], [], lateCleared, failed);
      if (lateBad.length) {
        const iv = inputValue(lateBad[0]);
        return stay(`保存して戻るの間に入力した${badWords(lateBad[0], iv)}。保存していません`, lateBad[0], [], [], failed);
      }
      if (failed || pass >= 2) return stay(`保存して戻るの間に入力が変わった${names(late)}は保存していません`, late[0], [], [], failed);
      dirty = late;
    }
    // what the batch saved, and what the rows' own actions answered meanwhile stored ("nothing to save" only when neither)
    const own = byOwn(state.project, saved), ok = saved.concat(own.ok);
    say([ok.length ? `${ok.length} 項目を保存しました（${names(ok)}）` : "", ...own.to].filter(Boolean).join("。") || "保存する変更はありませんでした");
    state.busy = false; back(true);
    return null;
  };
  $("#bb-est").onclick = guard($("#bb-est"), () => estimate(sid, null));
  // a row action: refused while 保存して戻る runs; `nav` is where it started (a late answer must not paint elsewhere) and
  // nav.row what the row held when it was sent (its late answer keeps the row when the user has typed in it since)
  const rowAct = (b, fn, changesValue = true) => (b.onclick = guard(b, (changesValue ? track : (f) => f)(async () => {
    if (!idle()) return;
    const nav = startedAt(), row = b.closest(".field");
    if (row) nav.row = rowNow(row.id.slice(2));
    await fn(nav);
  })));
  m.querySelectorAll("[data-save]").forEach((b) => rowAct(b, async (nav) => {
    if ((await saveField(b.dataset.save)) === "saved") await refresh(sid, b.dataset.save, false, nav);
  }));
  m.querySelectorAll("[data-na]").forEach((b) => rowAct(b, async (nav) => {
    const F = state.meta.fields[b.dataset.na];
    if (F.na === "zero" && !F.na_note && !confirm(`「${F.label}」を 0 として計算します。本当に無い（0）と分かっていますか？分からないときは「未取得」のままにしてください。`)) return;
    if (F.na_note && !confirm(`「${F.label}」を「${F.na_note}」として計算します（その分の排出は数えません）。本当にそうだと分かっていますか？分からないときは「未取得」のままにしてください。`)) return;
    warnOf(await api(`/projects/${nav.pid}/fields/${b.dataset.na}`, { method: "PUT", body: { value: null, state: "not_applicable", method: "user_entered" } }), nav);
    await refresh(sid, b.dataset.na, false, nav);
  }));
  m.querySelectorAll("[data-unset]").forEach((b) => rowAct(b, async (nav) => {
    warnOf(await api(`/projects/${nav.pid}/fields/${b.dataset.unset}`, { method: "PUT", body: { value: null, state: "not_obtained", method: "user_entered" } }), nav);
    await refresh(sid, b.dataset.unset, false, nav);
  }));
  m.querySelectorAll("[data-nc]").forEach((b) => rowAct(b, async (nav) => {
    warnOf(await api(`/projects/${nav.pid}/fields/${b.dataset.nc}`, { method: "PUT", body: { value: null, state: "not_computable", method: "user_entered" } }), nav);
    await refresh(sid, b.dataset.nc, false, nav);
  }));
  m.querySelectorAll("[data-later]").forEach((b) => rowAct(b, async (nav) => {
    const f = state.project.fields[b.dataset.later] || {};
    warnOf(await api(`/projects/${nav.pid}/fields/${b.dataset.later}/later`, { method: "POST", body: { later: !f.later } }), nav);
    await refresh(sid, b.dataset.later, true, nav);              // the flag does not use the input: what was typed stays
  }, false));
  // a candidate is adopted by its id (a position could point at another candidate after a repeat tap). The row is decided
  // by the adoption only when it was adopted: refused or failed, what was typed in it stays (the redraw keeps it, it is
  // not owed its stored value, 保存して戻る saves it and its stop names it)
  m.querySelectorAll("[data-accept]").forEach((b) => rowAct(b, async (nav) => {
    let done = false;
    try {
      warnOf(await api(`/projects/${nav.pid}/fields/${b.dataset.accept}/accept`, { method: "POST", body: { id: +b.dataset.cid } }), nav);
      done = true;
    } finally { await refresh(sid, b.dataset.accept, !done, nav); }
  }));
  m.querySelectorAll("[data-est]").forEach((b) => (b.onclick = guard(b, () => estimate(sid, b.dataset.est))));
  // the state select of an estimate / drawing value opens once a new value is typed
  m.querySelectorAll("select[id^='st-'][disabled]").forEach((sel) => {
    const f = sel.id.slice(3), inp = $("#in-" + f), cur = (state.project.fields[f] || {}).value;
    const lockTitle = sel.getAttribute("title"), stored = sel.value;
    if (inp) inp.addEventListener("input", () => {
      const iv = inputValue(f);
      const same = !iv.empty && !iv.bad && cur && iv.value === cur.value;
      sel.disabled = same || iv.empty;                 // the same value cannot change an estimate's state
      if (sel.disabled) { sel.value = stored; sel.setAttribute("title", lockTitle || ""); } else sel.removeAttribute("title");
    });
  });
  m.querySelectorAll("[data-why]").forEach((b) => (b.onclick = () => why(b.dataset.why)));
  // a row's text, unit or state changed by the user is marked touched (see touchedRow): a redraw keeps the row as it is
  const touch = (e) => { e.currentTarget.dataset.touched = "1"; };
  m.querySelectorAll(".field [id^='in-'], .field [id^='unit-'], .field [id^='st-']").forEach((el) => {
    el.addEventListener("input", touch); el.addEventListener("change", touch);
  });
  // a text row takes at most TEXT_MAX characters (maxlength): when the browser has cut an insertion (a paste, a drop, a
  // text put in at once) to fit, how much it left out is said (an action of its own), never dropped without a word. It
  // is measured from what the insertion would have made (beforeinput) and what it made (input); a line break counts as
  // one character (an input turns it into a space). Text typed through an input method (composing) is not measured
  m.querySelectorAll(".field input[maxlength]").forEach((el) => {
    let want = -1;
    const cut = () => {
      const n = want - el.value.length; want = -1;
      if (n > 0 && el.value.length >= el.maxLength - 1)
        toast(`「${state.meta.fields[el.id.slice(3)].label}」は ${el.maxLength} 字までです。入れた文の終わりの ${n} 字は入っていません`, ++state.act);
    };
    el.addEventListener("beforeinput", (e) => {
      want = -1;
      const s = el.selectionStart, t = el.selectionEnd;
      if (e.isComposing || !/^insert/.test(e.inputType || "") || typeof s !== "number" || typeof t !== "number") return;
      const add = typeof e.data === "string" ? e.data : e.dataTransfer ? e.dataTransfer.getData("text/plain") : "";
      want = el.value.length - (t - s) + add.replace(/\r\n?/g, "\n").length;
      // an insertion the browser refused whole (the row is full) has no input event: it is measured once the event is over
      setTimeout(() => { if (want >= 0) cut(); }, 0);
    });
    el.addEventListener("input", () => { if (want >= 0) cut(); });
  });
  const geo = $("#btn-geo");
  if (geo) geo.onclick = async () => {
    // a press is an action of its own (as a guarded button's): its words are never joined to another action's (保存して戻る
    // may be running: they would be read as its words, and named by its project)
    state.act++;
    const q = $("#addr").value.trim(); if (!q) return toast("住所を入力してください");
    // only the answer of the latest request is shown (geoSeq): an older search answered late is dropped
    const nav = startedAt(), seq = ++state.geoSeq, out = () => (state.geoSeq === seq && onScreen(nav, sid) ? $("#geo-out") : null);
    out().innerHTML = '<p class="muted">検索中…</p>';
    try {
      const r = await api(`/projects/${nav.pid}/research/address`, { method: "POST", body: { query: q } });
      const o = out(); if (!o) return;                 // the screen was left, or a newer request was made: nothing is painted
      state.geo = { sid, seq, addr: r.candidates, bld: null };   // what the buttons act on (kept across redraws with the list)
      // a button is known by its place and its list (data-list: see keyOf): a request of an older list does not make the
      // same place of a new list busy
      o.innerHTML = r.candidates.length ? `<ul class="cands">${r.candidates.map((c, i) => `<li>${esc(c.title)} <span class="muted">（${c.lat.toFixed(5)}, ${c.lon.toFixed(5)}・${c.precision === "town" ? "町・丁目まで" : c.precision === "lot" ? "番地まで" : "地域"}）</span>
          <div class="actions"><button class="btn small" data-geo="${i}" data-list="${seq}">この地点の建物を PLATEAU で探す</button></div></li>`).join("")}</ul><p class="muted">${esc(r.note)}</p>` : '<p class="muted">候補が見つかりませんでした。</p>';
      bindGeo(o);
    } catch (e) { const o = out(); if (o) o.innerHTML = `<div class="notice bad">${esc(e.message)}</div>`; else if (state.geoSeq === seq) toast(e.message, nav.act); }
  };
  const df = $("#docfile");
  if (df) df.onchange = async () => {
    const file = df.files[0]; if (!file) return;
    state.act++;
    // where the import started is taken BEFORE the file is read: a project opened meanwhile must not receive it
    const nav = startedAt(), say = (msg) => toast(msg, nav.act);
    const done = () => { state.importing = null; const d = $("#docfile"); if (d) { d.disabled = false; d.removeAttribute("aria-busy"); d.value = ""; } };
    if (!idle() || state.importing) { df.value = ""; if (state.importing) say("資料の読み込みの途中です。終わってから選んでください"); return; }
    if (file.size > 30e6) { df.value = ""; return say("30 MB までのファイルにしてください"); }
    state.importing = { key: nav.key, sid };           // the input is drawn busy (disabled) until the answer
    df.disabled = true; df.setAttribute("aria-busy", "true");
    $("#doc-out").innerHTML = '<p class="muted">読み込み中…</p>';
    let r = null, err = null;
    try {
      const b64 = await new Promise((res, rej) => {
        const fr = new FileReader(); fr.onload = () => res(fr.result.split(",")[1]);
        fr.onerror = () => rej(new Error("ファイルを読めませんでした")); fr.readAsDataURL(file);
      });
      if (!state.project || projectKey(state.project) !== nav.key) {
        done();
        return say(`「${file.name}」は読み込んでいません（ファイルを読んでいる間に別のプロジェクトを開いたため）。読み込むプロジェクトの画面で、もう一度選んでください`);
      }
      r = await api(`/projects/${nav.pid}/documents`, { method: "POST", body: { name: file.name, data_b64: b64 } });
    } catch (e) { err = e; }
    done();
    if (err) {
      // the refusal is this screen's latest outcome: it is kept (the earlier success is not drawn again in its place)
      state.lastImport = { pid: nav.pid, key: nav.key, sid, html: `<div class="notice bad">「${esc(file.name)}」：${esc(err.message)}</div>` };
      if (onScreen(nav, sid) && $("#doc-out")) $("#doc-out").innerHTML = state.lastImport.html; else say(err.message);
      return;
    }
    // the summary, the warnings and EVERY row not used, with its reason; kept for this screen until the next import
    const unused = r.unused || [];
    state.lastImport = { pid: nav.pid, key: nav.key, sid, html: `<p>${esc(r.summary)}</p>${(r.warnings || []).map((w) => `<div class="notice">${esc(w)}</div>`).join("")}`
      + (unused.length ? `<details id="doc-unused"${unused.length <= 8 ? " open" : ""}><summary>使わなかった行 ${r.n_unused ?? unused.length} 件と理由</summary>`
        + `<ul class="unused">${unused.map((w) => `<li>${esc(w)}</li>`).join("")}</ul></details>` : "") };
    const drew = await refresh(sid, undefined, true, nav);
    if (!(drew && onScreen(nav, sid))) say(r.summary);   // not drawn on its screen: said instead (no redraw, no focus taken)
  };
}

/* the user is on screen `sid` of the project the action started in */
function onScreen(nav, sid) {
  return state.view === "screen" && state.arg === sid && !!state.project && projectKey(state.project) === nav.key;
}

/* the buttons of #geo-out act on the answers kept in state.geo: bound when the list is drawn, and again when a redraw puts
   the list back (keepScreen / putBack). One request per button (a double tap does not search twice) */
function bindGeo(o) {
  const g = state.geo;
  if (!g || !o) return;
  o.querySelectorAll("[data-geo]").forEach((b) => (b.onclick = guard(b, () => (g.addr[+b.dataset.geo] ? plateau(g.addr[+b.dataset.geo], g.sid) : null))));
  o.querySelectorAll("[data-b]").forEach((x) => (x.onclick = guard(x, async () => {
    if (!idle() || !g.bld) return;
    const s = startedAt(), c = g.bld.c;
    await api(`/projects/${s.pid}/research/plateau/select`, { method: "POST", body: { candidate: g.bld.list[+x.dataset.b], lat: c.lat, lon: c.lon, address: c.title } });
    toast("候補を各項目に入れました。確認して採用してください", s.act); await refresh(g.sid, undefined, true, s);
  })));
}

/* a PLATEAU read for an address candidate. Like an address search it is a new request for #geo-out: only the answer of
   the latest one is shown (an older search or read answered late is dropped). The 「読んでいます」 line is one line,
   removed on every outcome (buildings, none found, an error) */
async function plateau(c, sid) {
  const nav = startedAt(), seq = ++state.geoSeq, out = () => (state.geoSeq === seq && onScreen(nav, sid) ? $("#geo-out") : null);
  const lines = (o) => o && o.querySelectorAll("#geo-reading, #geo-note").forEach((x) => x.remove());
  const o0 = out(); lines(o0);
  // added after the list (insertAdjacentHTML, not innerHTML +=: the list's buttons keep their handlers)
  o0?.insertAdjacentHTML("beforeend", '<p class="muted" id="geo-reading">PLATEAU の建物データを読んでいます（初回は数十秒かかることがあります）…</p>');
  try {
    const r = await api(`/projects/${nav.pid}/research/plateau`, { method: "POST", body: { lat: c.lat, lon: c.lon, address: c.title } });
    const o = out(); if (!o) return;
    lines(o);
    if (!r.candidates.length) { o.insertAdjacentHTML("beforeend", `<div class="notice" id="geo-note">${esc(r.note || "建物が見つかりませんでした")}</div>`); return; }
    state.geo = { sid, seq, addr: (state.geo && state.geo.addr) || [], bld: { c, list: r.candidates } };
    o.innerHTML = `<h4>近くの建物（PLATEAU）</h4><ul class="cands">${r.candidates.map((b, i) => `<li>
      <strong>${esc(b.usage || "用途不明")}</strong>・地上 ${b.storeys_above ?? "?"} 階 / 地下 ${b.storeys_below ?? "?"} 階・高さ ${b.measured_height_m ?? "?"} m・${b.contains_point ? "地点を含む" : b.distance_m + " m"}
      <div class="muted">${esc(b.address || "")}・${esc(b.structure_code || "")}・調査年 ${esc(b.survey_year || "")}・ID ${esc(b.plateau_building_id || "")}</div>
      <button class="btn small" data-b="${i}" data-list="${seq}">この建物を選ぶ</button></li>`).join("")}</ul><p class="muted">${esc(r.note)}</p>`;
    bindGeo(o);
  } catch (e) {
    const o = out();
    if (o) { lines(o); o.insertAdjacentHTML("beforeend", `<div class="notice bad" id="geo-note">${esc(e.message)}</div>`); }
    else if (state.geoSeq === seq) toast(e.message, nav.act);
  }
}

async function estimate(sid, fid) {
  if (!idle()) return;
  const nav = startedAt();
  try {
    const r = await api(`/projects/${nav.pid}/estimate`, { method: "POST", body: { screen: sid, field: fid } });
    toast(r.n_proposals ? `${r.n_proposals} 件の候補を作りました（採用するまで計算には使いません）` : (r.message || "概算できる項目がありません"), nav.act);
    await refresh(sid, fid, true, nav);              // the estimate does not use the input: what was typed stays
    if (r.messages && r.messages.length && onScreen(nav, sid)) estimateNote({ nav, sid, fid, html: r.messages.map((x) => `<p>${esc(x)}</p>`).join("") });
  } catch (e) { toast(e.message, nav.act); }
}
/* the explanation of an estimate (its gist is in the toast already); closing it gives focus back to 自動概算, or to where
   the user has gone meanwhile. It is never put over what the user has open: while 保存して戻る saves rows it waits for
   the end of the batch (state.noteLater), and while a dialog is open (a 根拠 table, a question) it waits until that one
   is closed. While the user is in a field (typing or choosing: a modal would take the next keys) it waits until the
   focus has been out of every field for 400 ms (checked every 200 ms: the tap that moved the focus lands first). It
   is shown only while its screen is still there */
function estimateNote(n) {
  if (state.busy) { state.noteLater = n; return; }
  if (!onScreen(n.nav, n.sid)) return;
  if (document.querySelector("dialog[open]")) return whenNoDialog(() => estimateNote(n));
  const a = document.activeElement;
  if (a && a.closest && a.closest("#main") && /^(INPUT|SELECT|TEXTAREA)$/.test(a.tagName) && a.type !== "file") {
    n.out = 0; setTimeout(() => estimateNote(n), 200); return;
  }
  if (n.out === 0) n.out = Date.now();
  if (n.out && Date.now() - n.out < 400) { setTimeout(() => estimateNote(n), 200); return; }
  const opener = n.fid ? $(`[data-est="${CSS.escape(n.fid)}"]`) : $("#bb-est"), cur = document.activeElement;
  const away = cur && cur !== document.body && cur !== $("#main") && cur !== opener && !(n.fid && cur.closest("#f-" + CSS.escape(n.fid)));
  dialog("自動概算の説明", n.html, away ? cur : opener);
}

async function why(fid) {
  const F = state.meta.fields[fid], f = state.project.fields[fid] || {};
  const rows = (f.history || []).slice().reverse().map((v) => `<tr><td>${badge(v.state)}</td><td>${fmt(v.value, v.unit)}</td>
    <td>${esc((state.meta.methods || {})[v.method] || v.method)}${v.source_id ? "<br><span class='muted'>出典 " + esc(v.source_id) + (v.source_detail ? "・" + esc(v.source_detail) : "") + "</span>" : ""}
    ${v.factor_version ? "<br><span class='muted'>版 " + esc(v.factor_version) + "</span>" : ""}${v.note ? "<br>" + esc(v.note) : ""}</td>
    <td class="muted">${new Date(v.updated_at * 1000).toLocaleString("ja-JP")}</td></tr>`).join("");
  dialog(F.label, `<p class="muted">エンジンの入力：${esc((F.engine || []).join("、") || "（エンジンに対応する入力なし：計算には反映されない）")}</p>
    <table class="t"><tr><th>状態</th><th>値</th><th>根拠</th><th>日時</th></tr>${rows || '<tr><td colspan="4">記録はまだありません</td></tr>'}</table>`);
}

/* what the user has in the rows of the screen, except the rows in `drop` (they are to show their stored value) — kept
   across a re-render. One rule: every row the user has touched since it was drawn (touchedRow), whatever its text, and
   every row whose controls differ from what was drawn (see drawn()). A row whose text equals the value drawn is kept
   all the same when it was touched (the first key of a correction, a revert, an emptied row being retyped): the UI
   never writes into a row the user may be editing. A unit or state chosen on an empty row is kept too */
function typedRows(drop = []) {
  const out = {};
  document.querySelectorAll("[data-save]").forEach((b) => {
    const f = b.dataset.save;
    if (drop.includes(f)) return;
    const inp = $("#in-" + f);
    if (!inp) return;
    const us = $("#unit-" + f), st = $("#st-" + f);
    const changed = touchedRow(f) || inp.value !== drawn(inp) || (us && us.value !== drawn(us)) || (st && !st.disabled && st.value !== drawn(st));
    if (changed) out[f] = { v: inp.value, u: us ? us.value : null, s: st ? st.value : null, unlocked: st ? !st.disabled : false };
  });
  return out;
}
/* the acted rows owed their stored value (state.owed: their action was answered while 保存して戻る ran, and its redraw was
   skipped): the rows of the screen shown now that are unchanged since their action was sent. Taken once: the next
   drawing pays them, whichever it is. A row the user has typed into since keeps what they typed (and 保存して戻る saves it);
   an entry of a view left since (another nav) is dropped */
function owedRows() {
  const out = [];
  state.owed.forEach((x, f) => { if (x.n === state.nav && state.view === "screen" && sameRow(rowNow(f), x.row)) out.push(f); });
  state.owed.clear();
  return out;
}
/* put kept rows back after a re-render; they stay touched (a later redraw keeps them too) */
function restoreTyped(saved) {
  for (const [f, x] of Object.entries(saved)) {
    const inp = $("#in-" + f); if (!inp) continue;
    inp.value = x.v; inp.dataset.touched = "1";
    if (x.u !== null && $("#unit-" + f)) $("#unit-" + f).value = x.u;
    const st = $("#st-" + f);
    if (st && x.s !== null) { if (x.unlocked) st.disabled = false; st.value = x.s; }
  }
}
/* everything the user has on a screen beyond the stored values: typed rows, the address being searched and its results
   (the address / PLATEAU answers in #geo-out: drawn again with their buttons bound), open lists */
function keepScreen(drop = []) {
  return { rows: typedRows(drop), addr: $("#addr") ? $("#addr").value : null, geo: $("#geo-out") ? $("#geo-out").innerHTML : null,
    open: [...document.querySelectorAll("#main details[id]")].map((d) => [d.id, d.open]) };
}
function putBack(k) {
  restoreTyped(k.rows);
  if (k.addr !== null && $("#addr")) $("#addr").value = k.addr;
  const g = $("#geo-out");
  if (k.geo && g) { g.innerHTML = k.geo; bindGeo(g); }
  k.open.forEach(([id, o]) => { const d = document.getElementById(id); if (d) d.open = o; });
  state.running.forEach((key) => busyMark($(key), true));      // a button put back whose request is under way is busy
}
/* after an action changed the project on the server; `nav` is where it started (startedAt). The project is read again and
   the view redrawn when it shows that project: the same screen (also after leaving and re-entering it) or the hub. Any
   other view, and any view while 保存して戻る runs, is left alone (no redraw, no focus taken): the project is read again
   when it is next drawn (state.stale), so state.project never differs from what is drawn. True when it redrew */
async function refresh(sid, fid, keepActed = false, nav = startedAt()) {
  // another project is open: none of it is shown (an action of the screen 保存して戻る runs on is still owed: see oweRow)
  if (!state.project || projectKey(state.project) !== nav.key) return oweRow(sid, fid, keepActed, nav);
  state.stale = { pid: nav.pid, gen: ++state.gen };
  return reloadShown(sid, fid, keepActed, nav);
}
/* a redraw skipped while 保存して戻る saves rows on this screen: the acted row is owed what this redraw would have shown
   (its stored value, unless the user changes it since its action was sent). The next drawing of the screen (the batch's,
   once its row actions are answered) pays it: see owedRows. An action sent on the screen 保存して戻る runs on is owed
   also when the user has stopped it and left meanwhile, also when another project is open by then: its stop names the
   row by what is stored (the entry is not drawn anywhere else: owedRows drops an entry of a view left). False (nothing
   was redrawn) */
function oweRow(sid, fid, keepActed, nav) {
  if (state.busy && fid && !keepActed && nav.row && ((state.nav === nav.n && onScreen(nav, sid)) || (state.batch && state.batch.n === nav.n)))
    state.owed.set(fid, { row: nav.row, n: nav.n });
  return false;
}
async function reloadShown(sid, fid, keepActed, nav) {
  const shows = () => !state.busy && !!state.project && projectKey(state.project) === nav.key
    && (state.view === "hub" || (state.view === "screen" && state.arg === sid));
  const owe = () => oweRow(sid, fid, keepActed, nav);
  if (!shows()) return owe();
  const gen = state.gen, p = await api("/projects/" + nav.pid);
  if (!shows() || projectKey(p) !== nav.key) return owe();     // moved meanwhile: the next drawing reads it again
  state.project = p;
  if (state.stale && state.stale.pid === p.id && state.stale.gen <= gen) state.stale = null;
  await redraw(nav, fid, keepActed);
  return true;
}
/* draw the current view again from state.project, keeping what the user has on it (every row touched since it was drawn,
   the address, the address results, open lists, the scroll) and the focus. The acted row shows its new stored value,
   unless the user has changed it since the action was sent (nav.row): then it stays as they left it, whatever its text
   (also when it equals the value drawn before). The acted row is brought into view and focused only when the user was on
   that row (not typing in it) or nowhere (body / main) and has not left the view since; focus anywhere else (a control,
   a list's summary, a link, a dialog) is where the user is: the scroll stays and the focus goes back to the element that
   had it (the same control, found by its identity, with the caret). All in one task: no keystroke is lost.
   `opt.drop`: the rows that show their stored value (in place of the acted row); `opt.focus`: a row to bring into view and
   focus when the user is on no control of their own (nowhere, or on 保存して戻る). The acted rows whose own redraw was
   skipped while 保存して戻る ran show their stored value too, by the same rule (owedRows) */
async function redraw(nav, fid, keepActed, quiet = false, opt = {}) {
  const same = state.nav === nav.n, had = document.activeElement, key = keyOf(had);
  let caret = null;
  try { if (had && typeof had.selectionStart === "number") caret = [had.selectionStart, had.selectionEnd]; } catch { /* no caret */ }
  const nowhere = !had || had === document.body || had === $("#main");
  const inRow = !!(same && fid && had && had.closest && had.closest("#f-" + CSS.escape(fid)));
  const typing = inRow && /^(INPUT|SELECT|TEXTAREA)$/.test(had.tagName);     // in the acted row's own field: no jump
  const toRow = (inRow && !typing) || !!(same && fid && nowhere);
  const changedSince = !!(fid && nav.row && !sameRow(rowNow(fid), nav.row));
  const owed = owedRows();
  const keep = state.view === "screen" ? keepScreen((opt.drop || (same && !keepActed && !changedSince && fid ? [fid] : [])).concat(owed)) : null;
  const y = window.scrollY;
  await render();
  if (keep) putBack(keep);
  const el = key && key !== "#main" ? $(key) : null, usable = el && !el.disabled;
  const named = opt.focus && (nowhere || key === "#bb-hub") ? $("#f-" + CSS.escape(opt.focus)) : null;
  const row = named || (toRow && $("#f-" + CSS.escape(fid)));
  const target = named ? $("#in-" + CSS.escape(opt.focus)) || named.querySelector("button")
    : row ? (inRow && usable ? el : row.querySelector("[data-save]") || row.querySelector("button")) : usable ? el : null;
  if (row) setTimeout(() => row.scrollIntoView({ block: "center" }), 0);
  else { window.scrollTo(0, y); setTimeout(() => window.scrollTo(0, y), 0); }
  if (target) {
    target.focus({ preventScroll: true });
    if (target === el && caret) try { el.setSelectionRange(caret[0], caret[1]); } catch { /* not a text field */ }
  }
  if (keep && !quiet) {
    // the same test as 保存して戻る; a kept row emptied while a value is stored is named too (its value is not removed)
    const typed = Object.keys(keep.rows).filter((f) => isDirty(f) || clearedInput(f));
    if (typed.length) toast(`まだ保存していない入力：${typed.map((f) => "「" + state.meta.fields[f].label + "」"
      + (clearedInput(f) ? "（空欄：値は消えていません）" : "")).join("")}`, nav.act);
  }
}

/* ---------- result ---------- */
async function renderResult(m) {
  $("#title").textContent = "結果";
  m.innerHTML = `<div class="card"><label for="period"><strong>評価期間（年）</strong></label>
    <div class="edit"><input id="period" inputmode="decimal" value="${state.project.last_period || 60}"><button class="btn small" id="calc">計算する</button></div>
    <p class="muted">評価期間だけを変えた再計算は、準備した計算を使い回すので速くなります。</p></div><div id="res-msg" role="status"></div><div id="res"></div>`;
  const seq = state.seq, pid = state.project.id, key = projectKey(state.project);
  const here = () => state.seq === seq && state.view === "result" && state.project && state.project.id === pid;
  $("#calc").onclick = guard($("#calc"), async () => {
    const p = parseNumber($("#period").value.trim()), T = p.value;
    // checked here as on the server; an error is shown above the last result instead of replacing it
    if (p.bad) { $("#res-msg").innerHTML = `<div class="notice bad">評価期間は数値で入力してください（${esc(p.why || "数値として読めません")}）</div>`; return; }
    if (!(T > 0 && T <= 130)) { $("#res-msg").innerHTML = `<div class="notice bad">評価期間は 0 より大きく 130 年以下で入力してください（エンジンの年表の長さが 130 年）</div>`; return; }
    $("#res-msg").innerHTML = '<p class="muted">計算中…</p>';
    const sent = $("#period").value;                         // a period typed during the calculation is kept
    try {
      const r = await api(`/projects/${pid}/calculate`, { method: "POST", body: { period: T } });
      if (state.project && projectKey(state.project) === key) state.project.last_period = r.period;   // not another project with its id
      if (!here()) return;                                   // the user went elsewhere: do not paint into that view
      $("#res-msg").innerHTML = ""; showResult(r, sent);
    } catch (e) { if (here()) $("#res-msg").innerHTML = `<div class="notice bad">${esc(e.message)}</div>`; }
  });
  // the stored result (the server answers {} when nothing has been calculated): a failed read is said where a
  // calculation's error is (in Japanese when the server cannot be reached), unless a calculation has been asked for since
  try { const r = await api(`/projects/${pid}/result`); if (r && r.status && here()) showResult(r, $("#period").defaultValue); } catch (e) {
    if (here() && !$("#res-msg").innerHTML && !$("#res").innerHTML) $("#res-msg").innerHTML = `<div class="notice bad">前の結果を読めませんでした：${esc(e.message)}</div>`;
  }
}

/* `base`: what #period held when the result was asked for (the drawn value for the stored result) */
function showResult(r, base) {
  const el = $("#res"), pe = $("#period");
  // the period shown is the period of this result, unless the user has typed another since (kept for the next 計算する)
  if (r.period && pe && pe.value === base) { pe.value = r.period; pe.defaultValue = String(r.period); }
  // not calculated: each missing input with the calculation's reason (fields[].detail: e.g. why a stored 適用外 is no longer
  // accepted after another input changed), and every input's row as for a result
  if (r.status !== "ok") {
    el.innerHTML = r.stale ? `<div class="notice bad"><strong>入力が変わっています。</strong>前の計算では「${esc(r.message)}」でした。「計算する」を押して計算し直してください。</div>`
      : `<div class="notice bad"><strong>計算していません</strong>：${esc(r.message)}</div>${missingHtml(r, true)}${fieldsHtml(r.fields)}`;
    return;
  }
  const s = r.summary, maxStage = Math.max(...s.stages.map((x) => Math.abs(x.value || 0)), 1);
  const tot = s.total_t === null ? null : s.total_t.toLocaleString("ja-JP", { maximumFractionDigits: 1 });
  const head = s.nothing_counted ? "未計算（計算に入った量がありません）" : tot === null ? "未計算" : (s.lower_bound ? `少なくとも ${tot} tCO2e` : `${tot} tCO2e`);
  const miss = (r.omitted_inputs || (r.missing_inputs || []).filter((x) => (x.gap || "omitted") === "omitted"));
  const assumed = (r.assumed_inputs || (r.missing_inputs || []).filter((x) => x.gap === "assumed"));
  el.innerHTML = `
  ${r.stale ? `<div class="notice bad"><strong>入力が変わっています。</strong>下は前の入力での結果です。「計算する」を押して計算し直してください。</div>` : ""}
  <div class="card${r.stale ? " stale" : ""}"><div class="muted">ホールライフカーボン（評価期間 ${r.period} 年）</div>
    <div class="big">${esc(head)}</div>
    ${s.nothing_counted ? "" : `<div class="muted">${s.lower_bound ? "<strong>下限</strong>（入っていない分がある）・" : ""}延床面積あたり ${fmt(s.per_area, "kgCO2e/m²")}・年あたり ${fmt(s.per_area_year, "kgCO2e/(m²·年)")}</div>`}
    ${r.range ? (r.range.low_t === null ? `<div class="muted">範囲：${esc(r.range.note)}</div>`
      : `<div class="muted">${r.range.lower_bound ? "範囲（両端とも下限）" : "範囲"}：${r.range.low_t.toLocaleString("ja-JP", { maximumFractionDigits: 1 })} 〜 ${r.range.high_t.toLocaleString("ja-JP", { maximumFractionDigits: 1 })} tCO2e（${esc(r.range.note)}）</div>`) : ""}
    <div class="notice">${esc(r.factor_note)}</div>
    ${s.lower_bound ? `<div class="notice bad">この合計は<strong>下限</strong>です。次の分は合計に入っていません：
      <ul>${miss.slice(0, 12).map((x) => `<li>${esc(x.label)}（${esc(x.stages.join("・"))}）：${esc(x.reason)}</li>`).join("")}${miss.length > 12 ? `<li>ほか ${miss.length - 12} 件</li>` : ""}
      ${(s.incomplete_units || []).length ? `<li>エンジンが合計できなかった単位：${esc(s.incomplete_units.join("、"))}</li>` : ""}</ul></div>` : ""}
    ${(r.inconsistent_inputs || []).map((x) => `<div class="notice bad">入力の矛盾：${esc(x)}</div>`).join("")}
    ${assumed.length ? `<div class="notice">次の分は、合計には入っていますが<strong>決まった値ではありません</strong>（仮定で計算した分・段階の内訳が決まらない分）：
      <ul>${assumed.map((x) => `<li>${esc(x.label)}（${esc(x.stages.join("・"))}）：${esc(x.reason)}</li>`).join("")}</ul></div>` : ""}
    ${(r.double_count || []).map((x) => `<div class="notice">二重計上の防止：${esc(x)}</div>`).join("")}
    ${(r.stale_estimates || []).map((x) => `<div class="notice bad">「${esc(x.label)}」の推定は、前提が変わっています（${esc(x.changes.join("、"))}）。材料の画面で概算し直してください。</div>`).join("")}</div>
  <div class="card"><h3 style="margin-top:0">推定値の影響</h3><p>${esc(r.reflection.summary)}</p>
    <table class="t"><tr><th>状態</th><th>計算に入った入力</th></tr>${Object.entries(r.reflection.by_state).map(([k, n]) => `<tr><td>${badge(k)}</td><td class="num">${n}</td></tr>`).join("")}</table></div>
  <div class="card"><h3 style="margin-top:0">段階別</h3><table class="t">${s.stages.map((x) => `<tr><td>${esc(x.stage)}</td>
    <td style="width:45%"><div class="bar" style="width:${Math.max(1, Math.abs(x.value || 0) / maxStage * 100)}%"></div></td><td class="num">${fmt(x.value, "")}${x.complete ? "" : ' <span class="badge st-not_computable">不完全</span>'}${x.assumed ? ' <span class="badge st-assumption">一部は仮定</span>' : ""}${x.split ? ' <span class="badge st-assumption">内訳が未定</span>' : ""}</td></tr>`).join("")}</table>
    ${(s.hints || []).length ? `<h4>不完全な段階を埋めるには</h4><ul>${s.hints.map((h) => `<li><strong>${esc(h.stage)}</strong>（${esc(h.unit)}）：${esc(h.note)}${(h.also || []).length ? `<div class="muted">別に：${esc(h.also.join("。"))}</div>` : ""}</li>`).join("")}</ul>` : ""}
    <p class="muted">単位 kgCO2e。出所：エンジンの結果のキー（${esc(s.source_keys)}）。</p></div>
  <div class="card"><h3 style="margin-top:0">時間の変化</h3>${curve(s.by_year)}<p class="muted">年ごとの排出（研究のモデルの X-07）。評価期間の関数 C(T) の傾きを、そのまま実際の排出率と読まないでください。</p></div>
  ${missingHtml(r)}
  ${fieldsHtml(r.fields)}
  ${checksHtml(r.checks)}
  <div class="card"><h3 style="margin-top:0">計算の記録</h3><table class="t">${Object.entries(r.trace).map(([k, v]) => `<tr><td>${esc(k)}</td><td>${esc(typeof v === "object" ? JSON.stringify(v) : v)}</td></tr>`).join("")}</table></div>`;
}

/* the required inputs that are missing, each with the calculation's reason when an input of that name is not used
   (fields[].detail, with its state). `blocked`: the calculation did not run for them; then every required input set to
   適用外 that the calculation does not use is named with how it was treated as well, also when the missing item has
   another name (the route, the floor area: their missing item names more than the input) */
function missingHtml(r, blocked = false) {
  const u = r.unconnected || [], miss = r.missing_required || [], rows = (Array.isArray(r.fields) ? r.fields : []).filter((x) => x && !x.reflected && x.detail);
  const why = (x) => `${x.state ? " " + badge(x.state) : ""}<div class="muted">${esc(x.detail)}</div>`;
  const na = blocked ? rows.filter((x) => x.state === "not_applicable" && !miss.includes(x.label) && (state.meta.fields[x.field] || {}).required) : [];
  return `${miss.length ? `<div class="card"><h3 style="margin-top:0">計算に必須で足りない入力</h3><ul>${miss.map((m) => `<li>${esc(m)}${rows.filter((x) => x.label === m).map(why).join("")}</li>`).join("")}</ul>${
    na.length ? `<h4>適用外にした必須の入力（計算での扱い）</h4><ul>${na.map((x) => `<li>${esc(x.label)}${why(x)}</li>`).join("")}</ul>` : ""}</div>` : ""}
  <div class="card"><h3 style="margin-top:0">計算に反映されない入力（${u.length} 件）</h3>${u.length ? `<ul>${u.slice(0, 40).map((x) => `<li>${esc(x.label)}：${esc(x.reason)}</li>`).join("")}</ul>` : '<p class="muted">ありません</p>'}</div>`;
}

function fieldsHtml(rows) {
  if (!rows || !rows.length) return "";
  const n = rows.filter((x) => x.reflected).length;
  return `<div class="card"><details><summary><strong>入力ごとの反映</strong>（計算に入った ${n} / ${rows.length} 項目）</summary>
    <table class="t"><tr><th>項目</th><th>状態</th><th>計算</th><th>どう渡したか・理由</th></tr>${rows.map((x) => `<tr><td>${esc(x.label)}</td><td>${badge(x.state)}</td>
    <td>${x.reflected ? "入った" : "入っていない"}</td><td class="muted">${esc(x.detail)}</td></tr>`).join("")}</table></details></div>`;
}

function checksHtml(checks) {
  if (!checks || !checks.length) return "";
  return `<div class="card"><h3 style="margin-top:0">エンジンの点検</h3><table class="t"><tr><th>点検</th><th>結果</th><th>例</th></tr>${checks.map((c) => `<tr><td>${esc(c.id)}</td>
    <td>${c.ok === true ? "問題なし" : c.ok === false ? "指摘 " + c.n_violations + " 件" : "—"}</td><td class="muted">${esc((c.examples || []).join("、"))}</td></tr>`).join("")}</table>
    <p class="muted">SYS-01 は値の状態（実測・推定・明示のゼロ・欠損・導出）を数え、欠損を一覧にします。欠損は 0 として計算していません。</p></div>`;
}

function curve(rows) {
  if (!rows || !rows.length) return '<p class="muted">データなし</p>';
  const W = 640, H = 200, P = 34, mx = Math.max(...rows.map((r) => r[1]), 1), n = rows.length;
  const pts = rows.map((r, i) => `${P + (i / Math.max(1, n - 1)) * (W - 2 * P)},${H - P - (r[1] / mx) * (H - 2 * P)}`).join(" ");
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="年ごとの排出のグラフ" style="width:100%;height:auto">
    <line x1="${P}" y1="${H - P}" x2="${W - P}" y2="${H - P}" stroke="currentColor" stroke-opacity=".4"/>
    <polyline points="${pts}" fill="none" stroke="var(--c-result)" stroke-width="2"/>
    <text x="${P}" y="${H - 8}" font-size="12">${rows[0][0]}</text><text x="${W - P - 30}" y="${H - 8}" font-size="12">${rows[n - 1][0]}</text>
    <text x="${P}" y="${P - 8}" font-size="12">${Math.round(mx).toLocaleString("ja-JP")} kgCO2e/年</text></svg>`;
}

/* ---------- settings / project management ---------- */
async function renderSettings(m) {
  $("#title").textContent = "設定とプロジェクト";
  const seq = state.seq, projects = await api("/projects");
  if (state.seq !== seq) return;                  // the user has moved meanwhile
  m.innerHTML = `<div class="card"><h3 style="margin-top:0">プロジェクト</h3>${projects.map((p) => `<div class="row" style="justify-content:space-between;padding:6px 0">
     <span class="lname">${esc(p.name)}（${esc(p.structure_label)}）</span><span class="row"><button class="btn small" data-open="${p.id}">開く</button>
     <button class="btn small" data-del="${p.id}">削除</button></span></div>`).join("") || '<p class="muted">ありません</p>'}</div>
   <div class="card"><h3 style="margin-top:0">このアプリについて</h3><p>${esc(state.meta.app_name)} ${esc(state.meta.version)}</p><p class="muted">${esc(state.meta.disclaimer)}</p>
   <p class="muted">${esc(state.meta.privacy)}</p><p class="muted">データの出典：${esc(state.meta.attribution)}</p></div>`;
  m.querySelectorAll("[data-open]").forEach((b) => (b.onclick = guard(b, () => openProject(+b.dataset.open))));
  m.querySelectorAll("[data-del]").forEach((b) => (b.onclick = guard(b, async () => {
    if (!confirm("このプロジェクトと、その入力・候補・資料の記録、計算用に変換した入力と計算の記録を削除します。元に戻せません。")) return;
    const id = +b.dataset.del;
    // the deleted project's identity when it is the one open (a new project may get its id later)
    const key = state.project && state.project.id === id ? projectKey(state.project) : null;
    await api("/projects/" + id, { method: "DELETE" }); toast("削除しました");
    if (state.project && state.project.id === id && (key === null || projectKey(state.project) === key)) {
      state.project = null; state.stack = [];
      // the user went back to its hub, a screen or its result while the delete was on its way: a view of a project that
      // is gone is not left on screen (it would fail at the next tap); home is shown, as after ← from a project's hub
      if (["hub", "screen", "result"].includes(state.view)) { state.nav++; state.act++; state.view = "home"; state.arg = undefined; render(); }
    }
    // nothing of the deleted project is kept: a new project may get its id
    if (state.lastImport && state.lastImport.pid === id) state.lastImport = null;
    if (state.stale && state.stale.pid === id) state.stale = null;
    if (state.view === "settings") render();
  })));
}

/* ---------- boot ---------- */
/* the door is a button from the start: a tap while the app is still starting (/api/meta on its way) is kept, the door
   says 「読み込み中…」, and it opens once the app has started (or the start's failure is said under it) */
async function boot() {
  const sp = $("#splash");
  let ready = false, wanted = false;
  const open = () => {
    if (sp.classList.contains("open")) return;
    sp.classList.add("open");
    const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    setTimeout(() => { sp.hidden = true; $("#appbar").hidden = false; $("#main").hidden = false; render(); }, reduce ? 0 : 1200);
  };
  const tap = () => {
    if (ready) return open();
    if (wanted) return;
    wanted = true; sp.setAttribute("aria-busy", "true");
    const sub = sp.querySelector(".splash-sub"); if (sub) sub.textContent = "読み込み中…";
  };
  sp.onclick = tap; sp.onkeydown = (e) => { if (e.key === "Enter" || e.key === " ") tap(); };
  state.meta = await api("/meta");
  $("#btn-back").onclick = tapBack;
  $("#btn-settings").onclick = () => go("settings");
  ready = true; sp.removeAttribute("aria-busy");
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});
  if (wanted) open();
}
/* the app could not start: said in words, under the door (the offline shell keeps it), with a way to try again. The
   server cannot be reached when the request itself failed (api() says so: offline, the server stopped); any other
   failure is the server's answer. The browser's own wording stays only as a small detail, and so does the start of an
   answer that could not be read (a proxy's page) */
function bootFailed(e) {
  const sp = $("#splash"), off = !!(e && (e.offline || e instanceof TypeError));
  const msg = e && e.offline ? String(e.detail || "") : String((e && e.message) || e || "") + (e && e.unreadable && e.detail ? "：" + e.detail : "");
  const head = off ? "WLC Studio のサーバーに接続できません" : "WLC Studio を起動できませんでした";
  const hint = off ? "サーバーが動いているか、ネットワークを確かめてください。" : "しばらくしてから、もう一度読み込んでください。";
  const html = `<div class="boot-error" role="alert"><p><strong>${esc(head)}</strong></p><p>${esc(hint)}</p>
    <button class="btn primary" id="boot-reload" type="button">再読み込み</button>${msg ? `<p class="boot-detail">詳細：${esc(msg)}</p>` : ""}</div>`;
  if (!sp) { document.body.innerHTML = html; } else {
    // the door is no longer a button: nothing opens it
    sp.onclick = null; sp.onkeydown = null; sp.removeAttribute("role"); sp.removeAttribute("tabindex"); sp.removeAttribute("aria-label");
    sp.removeAttribute("aria-busy");
    sp.classList.add("failed"); sp.hidden = false;
    const sub = sp.querySelector(".splash-sub"); if (sub) sub.remove();
    sp.insertAdjacentHTML("beforeend", html);
  }
  const b = $("#boot-reload");
  if (b) { b.onclick = () => location.reload(); b.focus(); }
}
initToast();
boot().catch(bootFailed);
