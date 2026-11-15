/* WLC Studio – mobile PWA front end. Talks only to the local server's JSON API (/api/...). */
"use strict";
const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
// seq: renders; nav: moves between views (a late answer of the view that was left must not paint into the new one);
// act: user actions (toast messages of one action are joined, a new action starts a new message)
const state = { meta: null, project: null, stack: [], view: "home", seq: 0, nav: 0, act: 0, busy: false };

async function api(path, opts = {}) {
  const r = await fetch("/api" + path, { headers: { "Content-Type": "application/json" }, ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined });
  const t = await r.text();
  let j; try { j = t ? JSON.parse(t) : {}; } catch { j = { error: t }; }
  if (!r.ok) throw new Error(j.error || ("HTTP " + r.status));
  return j;
}
function toast(msg) {
  const t = $("#toast");
  // messages of the same action are joined (a refusal and the "not saved yet" notice); a new action starts afresh
  const prev = t.classList.contains("show") && toast._act === state.act ? t.textContent : "";
  t.textContent = prev && !prev.split(" ／ ").includes(msg) ? prev + " ／ " + msg : (prev || msg);
  toast._act = state.act;
  t.classList.add("show"); clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.remove("show"), 2600 + Math.min(4000, t.textContent.length * 20));
}
/* one request at a time per button: a double tap must not send twice (and focus stays on the button) */
function guard(b, fn) {
  return async (...a) => {
    if (b.dataset.busy) return;
    state.act++;
    b.dataset.busy = "1"; b.setAttribute("aria-disabled", "true");
    try { return await fn(...a); } finally { delete b.dataset.busy; b.removeAttribute("aria-disabled"); }
  };
}
/* an information dialog; focus goes back to `returnTo` (or the element that had it) when it closes */
function dialog(title, html, returnTo) {
  const d = $("#dlg"), back = returnTo || document.activeElement;
  $("#dlg-title").textContent = title; $("#dlg-content").innerHTML = html;
  d.addEventListener("close", () => { if (back && document.contains(back)) back.focus(); }, { once: true });
  d.showModal();
}
/* a question with explicit choices; resolves to the chosen value, or null when cancelled (やめる, Escape) */
function ask(title, text, choices) {
  return new Promise((resolve) => {
    let d = $("#ask");
    if (!d) { d = document.createElement("dialog"); d.id = "ask"; d.setAttribute("aria-labelledby", "ask-title"); document.body.appendChild(d); }
    const back = document.activeElement;
    d.innerHTML = `<form method="dialog" class="dlg-body"><h2 id="ask-title">${esc(title)}</h2><p>${esc(text)}</p>
      <div class="dlg-actions">${choices.map((c) => `<button class="btn${c.primary ? " primary" : ""}" value="${esc(c.value)}">${esc(c.label)}</button>`).join(" ")}
      <button class="btn" value="">やめる</button></div></form>`;
    d.returnValue = "";
    d.addEventListener("close", () => { if (back && document.contains(back)) back.focus(); resolve(d.returnValue || null); }, { once: true });
    d.showModal();
  });
}
function fmt(v, unit) {
  if (v === null || v === undefined || v === "") return "—";
  if (typeof v === "number") return (Math.abs(v) >= 1000 ? v.toLocaleString("ja-JP", { maximumFractionDigits: 1 }) : String(+v.toPrecision(6))) + (unit ? " " + unit : "");
  if (typeof v === "object") return esc(JSON.stringify(v));
  return esc(v) + (unit ? " " + esc(unit) : "");
}
function badge(st) { const L = state.meta.states; return `<span class="badge st-${esc(st)}">${esc(L[st] || st)}</span>`; }

/* while 保存して戻る saves row after row, moving away would leave rows unsaved without notice: the first press says so,
   a second press stops the remaining saves (they are named) and moves */
function blocked() {
  if (!state.busy) return false;
  if (state.busyWarned) { state.cancel = true; return false; }
  state.busyWarned = true; state.act++;
  toast("保存の途中です。終わるまで待つか、もう一度押すと残りの行を保存せずに移ります");
  return true;
}
function go(view, arg, push = true) {
  if (blocked()) return;
  if (push) state.stack.push([state.view, state.arg]);
  state.nav++; state.act++;
  state.view = view; state.arg = arg; render();
}
/* opening a project starts a fresh history: 戻る must never lead into the screens of another project */
function openProject(id) {
  if (blocked()) return Promise.resolve();
  return loadProject(id).then(() => { state.stack = [["home", undefined]]; go("hub", undefined, false); });
}
function back() {
  if (blocked()) return;
  state.nav++; state.act++;
  const p = state.stack.pop(); if (p) { state.view = p[0]; state.arg = p[1]; render(); } else { state.view = "home"; render(); }
}

async function render() {
  state.seq++;                                    // a pending request of the previous view must not paint into this one
  const m = $("#main"); m.innerHTML = ""; window.scrollTo(0, 0);
  $("#btn-back").style.visibility = state.view === "home" ? "hidden" : "visible";
  try {
    if (state.view === "home") await renderHome(m);
    else if (state.view === "structures") await renderStructures(m);
    else if (state.view === "hub") await renderHub(m);
    else if (state.view === "screen") await renderScreen(m, state.arg);
    else if (state.view === "result") await renderResult(m);
    else if (state.view === "settings") await renderSettings(m);
  } catch (e) { m.innerHTML = `<div class="notice bad">表示できなかった：${esc(e.message)}</div>`; }
  finally { m.focus({ preventScroll: true }); }   // screen readers start at the new view
}
/* a failed request inside any button handler is shown, never silently swallowed */
window.addEventListener("unhandledrejection", (e) => { e.preventDefault(); toast((e.reason && e.reason.message) || String(e.reason)); });

/* ---------- home ---------- */
async function renderHome(m) {
  $("#title").textContent = state.meta.app_name;
  const projects = await api("/projects");
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
      <div><strong>${esc(p.name)}</strong><br><span class="muted">${esc(p.structure_label)}・入力 ${p.progress.filled}/${p.progress.total}（${p.progress.percent}%）</span></div>
      <button class="btn small" data-open="${p.id}">開く</button></div>`).join("") : '<p class="muted">まだプロジェクトはありません。</p>'}</div>`;
  $("#start").onclick = () => go("structures");
  $("#demo").onclick = guard($("#demo"), async () => { const r = await api("/demo", { method: "POST", body: {} }); await openProject(r.id); });
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
  m.querySelectorAll("[data-s]").forEach((b) => (b.onclick = guard(cards, async () => {
    const r = await api("/projects", { method: "POST", body: { structure: b.dataset.s, name: $("#pname").value.trim() } });
    await openProject(r.id);
  })));
}

async function loadProject(id) { state.project = await api("/projects/" + id); }

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
    : `<input id="in-${fid}" aria-label="${esc(F.label)}" ${F.type === "number" ? 'inputmode="decimal"' : ""} value="${v && v.value !== null && typeof v.value !== "object" ? esc(v.value) : ""}" placeholder="${F.unit ? "単位：" + esc(F.unit) : ""}">`;
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
  const cands = (f.candidates || []).map((c, i) => `<li><div>${fmt(c.value, c.unit)} ${badge(c.state)} <span class="muted">${ml(c.method)}</span></div>
      ${c.uncertainty && c.uncertainty.kind === "unknown" ? `<div class="muted">範囲は不明</div>` : ""}
      ${c.uncertainty && c.uncertainty.kind !== "none" && c.uncertainty.kind !== "unknown" ? `<div class="muted">範囲 ${fmt(c.uncertainty.low, c.unit)} 〜 ${fmt(c.uncertainty.high, c.unit)}${c.uncertainty.calibrated ? "" : "（仮の範囲）"}</div>` : ""}
      <div class="muted">${c.source_id ? "出典 " + esc(c.source_id) + (c.source_detail ? "：" + esc(c.source_detail) : "") : ""}</div>
      ${dependsHtml(c.depends)}
      <div class="muted">${esc(c.note || "")}</div><button class="btn small" data-accept="${fid}" data-cid="${c.id}">この候補を採用</button></li>`).join("");
  return `<div class="field" id="f-${fid}">
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
      <input type="file" id="docfile" accept=".csv,.xlsx,.ifc,.pdf" aria-label="資料ファイル"><div id="doc-out">${
        state.lastImport && state.lastImport.pid === state.project.id && state.lastImport.sid === sid ? state.lastImport.html : ""}</div>
      <p class="muted">原本は既定では保存しません（読んだ数値の候補と、ファイルの指紋だけを残します）。メーカーの BIM データは各社の利用条件（設計検討の目的に限る・使用後は消去など）に従ってください。製品の性能値（質量・冷媒量）は製造時の CO2 ではありません。</p></div>` : "";
  m.innerHTML = extra + S.groups.map((g) => {
    const fids = [...g.fields].sort((a, b) => (pri[b] || 0) - (pri[a] || 0));
    return `<div class="card group"><h3>${esc(g.label)}</h3>${fids.map(fieldHtml).join("")}</div>`;
  }).join("") + `<div class="bottombar"><button class="btn" id="bb-back">戻る</button><button class="btn" id="bb-est">この画面を自動概算</button><button class="btn" id="bb-hub">保存して戻る</button></div>`;
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
  return { value: raw };
}
/* the input was emptied although a value is stored: say that it was not removed, and show the stored value again */
function clearedInput(fid) {
  const el = $("#in-" + fid), cur = (state.project.fields[fid] || {}).value;
  return !!(el && el.value.trim() === "" && cur && cur.value !== null && cur.value !== undefined && typeof cur.value !== "object");
}
function restoreInput(fid) {
  const el = $("#in-" + fid), cur = (state.project.fields[fid] || {}).value;
  if (el && cur) el.value = cur.value;
}
function ownValue(cur) {
  return cur && ["user_entered", "initial_setting", "structure_card"].includes(cur.method) && !["statistical", "from_drawing"].includes(cur.state);
}
function isDirty(fid) {
  const F = state.meta.fields[fid], cur = (state.project.fields[fid] || {}).value, iv = inputValue(fid);
  if (iv.empty || iv.bad) return false;
  const us = $("#unit-" + fid), st = $("#st-" + fid);
  if (!cur || cur.value !== iv.value) return true;
  if (F.type === "number" && us && cur.unit && us.value !== cur.unit) return true;
  return ownValue(cur) && st && st.value !== cur.state;          // a state-only change of one's own value
}
/* save one row: "saved" | "unchanged" | "refused" | "cancelled". With batch=true nothing is re-rendered (the other rows
   keep what was typed) and a refusal's reason is returned in saveField.reason */
async function saveField(fid, quiet = false, batch = false) {
  saveField.reason = "";
  const nav = state.nav;
  const refuse = async (msg, reload = true) => {
    saveField.reason = msg;
    if (!batch) { toast(msg); if (reload) await refresh("screen", fid, true, nav); }
    return "refused";
  };
  // a question is about one row: it names the row and the values, and the row is brought into view and marked
  const askRow = async (title, text, choices) => {
    const row = $("#f-" + fid);
    row?.scrollIntoView({ block: "center" }); row?.classList.add("asking");
    try { return await ask(`「${state.meta.fields[fid].label}」：${title}`, text, choices); } finally { row?.classList.remove("asking"); }
  };
  const shown = (x, u) => `${x}${u ? " " + u : ""}`;
  const F = state.meta.fields[fid], iv = inputValue(fid);
  if (iv.empty && clearedInput(fid)) {
    restoreInput(fid);
    return refuse(`「${F.label}」の空欄は保存していません（値は消えていません）。値を消すときは「未取得に戻す」を押してください`, false);
  }
  if (iv.empty) {
    const cur0 = (state.project.fields[fid] || {}).value;
    if (!quiet) toast(cur0 && cur0.state !== "not_obtained" ? `空欄は保存しません（今の「${state.meta.states[cur0.state]}」のまま）`
      : "空欄は保存しません（未取得のまま。0 にはしません）");
    return "unchanged";
  }
  if (iv.bad) return refuse("「" + F.label + "」は数値で入力してください" + (iv.why ? "（" + iv.why + "）" : ""), false);
  const value = iv.value;
  const cur = (state.project.fields[fid] || {}).value;
  const us = $("#unit-" + fid), unit = us ? us.value : ((cur && cur.unit) || F.unit);
  const st = $("#st-" + fid).value;
  const body = { value, unit: F.type === "number" ? unit : "", state: st, method: "user_entered" };
  if (cur && cur.value === value) {
    const sameUnit = F.type !== "number" || !cur.unit || cur.unit === unit;
    if (!ownValue(cur)) {
      if (!sameUnit) return refuse(`${state.meta.states[cur.state]}の値の単位は付け直せません（候補を採用し直すか、「未取得に戻す」のあと入れ直す）`);
      if (!quiet) toast(`値が変わっていないので保存しません（${state.meta.states[cur.state]}の出典・範囲を残します）`);
      return "unchanged";
    }
    if (sameUnit && cur.state === st) { if (!quiet) toast("変更はありません"); return "unchanged"; }
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
  try {
    await api(`/projects/${state.project.id}/fields/${fid}`, { method: "PUT", body });
    return "saved";
  } catch (e) { return refuse(`「${F.label}」：${e.message}`); }
}

function bindScreen(m, sid) {
  $("#bb-back").onclick = back;
  // a double click must not save twice or go back twice; while it runs, moving away waits (see blocked())
  $("#bb-hub").onclick = guard($("#bb-hub"), async () => {
    state.busy = true; state.busyWarned = false; state.cancel = false;
    try { await saveAndBack(); } finally { state.busy = false; }
  });
  const label = (f) => "「" + state.meta.fields[f].label + "」";
  const saveAndBack = async () => {
    // 保存して戻る: every row whose input differs from the stored value is saved like its own 保存 button
    const rows = [...m.querySelectorAll("[data-save]")].map((b) => b.dataset.save);
    const cleared = rows.filter(clearedInput);
    if (cleared.length) {
      cleared.forEach(restoreInput);
      toast(`空欄にした${cleared.map((f) => "「" + state.meta.fields[f].label + "」").join("")}は保存していません（値は消えていません）。消すときは「未取得に戻す」を押してください。ほかの行も保存していません。戻りません`);
      $("#in-" + cleared[0])?.focus();
      return;
    }
    // a number that cannot be read is said before anything is saved (it is never silently dropped)
    const bad = rows.filter((f) => inputValue(f).bad);
    if (bad.length) {
      const iv = inputValue(bad[0]);
      toast(`「${state.meta.fields[bad[0]].label}」は数値で入力してください${iv.why ? "（" + iv.why + "）" : ""}。保存していません`);
      $("#in-" + bad[0]).focus();
      return;
    }
    const dirty = rows.filter(isDirty);
    const saved = [], nav0 = state.nav, pid = state.project.id;
    const snap = typedRows(null);                      // what was typed, before the first request (a redraw keeps it)
    const moved = () => state.cancel || state.nav !== nav0 || !state.project || state.project.id !== pid;
    const stopNote = (rest) => `保存して戻るを途中でやめました：${saved.length ? saved.map(label).join("") + "は保存しました。" : ""}`
      + `${rest.map(label).join("")}は保存していません`;
    for (const [i, fid] of dirty.entries()) {
      if (moved()) { state.act++; toast(stopNote(dirty.slice(i))); return; }
      if (inputValue(fid).empty && snap[fid]) restoreTyped({ [fid]: snap[fid] });
      const r = await saveField(fid, true, true);
      if (moved()) { state.act++; toast(stopNote(dirty.slice(i + (r === "saved" ? 1 : 0)))); if (r === "saved") saved.push(fid); return; }
      if (r === "refused" || r === "cancelled") {
        // redraw: the saved rows, badges and candidates become current; what was typed in the others stays
        const keep = typedRows(null);
        saved.forEach((f) => delete keep[f]);
        await loadProject(state.project.id);
        await render(); restoreTyped(keep);
        const done = saved.length ? `（${saved.map((f) => "「" + state.meta.fields[f].label + "」").join("")}は保存しました）` : "";
        toast((r === "refused" ? saveField.reason : `「${state.meta.fields[fid].label}」の保存をやめました`) + "。戻りません" + done);
        $("#in-" + fid)?.focus();
        return;
      }
      if (r === "saved") saved.push(fid);
    }
    await loadProject(pid);
    if (moved()) { state.act++; toast(saved.length ? `${saved.map(label).join("")}を保存しました` : "保存する変更はありませんでした"); return; }
    toast(saved.length ? `${saved.length} 項目を保存しました（${saved.map(label).join("")}）` : "保存する変更はありませんでした");
    state.busy = false; back();
  };
  $("#bb-est").onclick = guard($("#bb-est"), () => estimate(sid, null));
  m.querySelectorAll("[data-save]").forEach((b) => (b.onclick = guard(b, async () => {
    const nav = state.nav;
    if ((await saveField(b.dataset.save)) === "saved") await refresh(sid, b.dataset.save, false, nav);
  })));
  m.querySelectorAll("[data-na]").forEach((b) => (b.onclick = guard(b, async () => {
    const F = state.meta.fields[b.dataset.na];
    if (F.na === "zero" && !F.na_note && !confirm(`「${F.label}」を 0 として計算します。本当に無い（0）と分かっていますか？分からないときは「未取得」のままにしてください。`)) return;
    if (F.na_note && !confirm(`「${F.label}」を「${F.na_note}」として計算します（その分の排出は数えません）。本当にそうだと分かっていますか？分からないときは「未取得」のままにしてください。`)) return;
    const nav = state.nav;
    await api(`/projects/${state.project.id}/fields/${b.dataset.na}`, { method: "PUT", body: { value: null, state: "not_applicable", method: "user_entered" } });
    await refresh(sid, b.dataset.na, false, nav);
  })));
  m.querySelectorAll("[data-unset]").forEach((b) => (b.onclick = guard(b, async () => {
    const nav = state.nav;
    await api(`/projects/${state.project.id}/fields/${b.dataset.unset}`, { method: "PUT", body: { value: null, state: "not_obtained", method: "user_entered" } });
    await refresh(sid, b.dataset.unset, false, nav);
  })));
  m.querySelectorAll("[data-nc]").forEach((b) => (b.onclick = guard(b, async () => {
    const nav = state.nav;
    await api(`/projects/${state.project.id}/fields/${b.dataset.nc}`, { method: "PUT", body: { value: null, state: "not_computable", method: "user_entered" } });
    await refresh(sid, b.dataset.nc, false, nav);
  })));
  m.querySelectorAll("[data-later]").forEach((b) => (b.onclick = guard(b, async () => {
    const f = state.project.fields[b.dataset.later] || {}, nav = state.nav;
    await api(`/projects/${state.project.id}/fields/${b.dataset.later}/later`, { method: "POST", body: { later: !f.later } });
    await refresh(sid, b.dataset.later, true, nav);              // the flag does not use the input: what was typed stays
  })));
  // a candidate is adopted by its id (a position could point at another candidate after a repeat tap)
  m.querySelectorAll("[data-accept]").forEach((b) => (b.onclick = guard(b, async () => {
    const nav = state.nav;
    try {
      await api(`/projects/${state.project.id}/fields/${b.dataset.accept}/accept`, { method: "POST", body: { id: +b.dataset.cid } });
    } finally { await refresh(sid, b.dataset.accept, false, nav); }
  })));
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
  const geo = $("#btn-geo");
  if (geo) geo.onclick = async () => {
    const q = $("#addr").value.trim(); if (!q) return toast("住所を入力してください");
    $("#geo-out").innerHTML = '<p class="muted">検索中…</p>';
    try {
      const r = await api(`/projects/${state.project.id}/research/address`, { method: "POST", body: { query: q } });
      $("#geo-out").innerHTML = r.candidates.length ? `<ul class="cands">${r.candidates.map((c, i) => `<li>${esc(c.title)} <span class="muted">（${c.lat.toFixed(5)}, ${c.lon.toFixed(5)}・${c.precision === "town" ? "町・丁目まで" : c.precision === "lot" ? "番地まで" : "地域"}）</span>
          <div class="actions"><button class="btn small" data-geo="${i}">この地点の建物を PLATEAU で探す</button></div></li>`).join("")}</ul><p class="muted">${esc(r.note)}</p>` : '<p class="muted">候補が見つかりませんでした。</p>';
      $("#geo-out").querySelectorAll("[data-geo]").forEach((g) => (g.onclick = () => plateau(r.candidates[+g.dataset.geo])));
    } catch (e) { $("#geo-out").innerHTML = `<div class="notice bad">${esc(e.message)}</div>`; }
  };
  const df = $("#docfile");
  if (df) df.onchange = async () => {
    const file = df.files[0]; if (!file) return;
    if (file.size > 30e6) return toast("30 MB までのファイルにしてください");
    $("#doc-out").innerHTML = '<p class="muted">読み込み中…</p>';
    const b64 = await new Promise((res) => { const fr = new FileReader(); fr.onload = () => res(fr.result.split(",")[1]); fr.readAsDataURL(file); });
    const nav = state.nav, pid = state.project.id;
    try {
      const r = await api(`/projects/${pid}/documents`, { method: "POST", body: { name: file.name, data_b64: b64 } });
      // the summary, the warnings and EVERY row not used, with its reason; kept for this screen until the next import
      const unused = r.unused || [];
      state.lastImport = { pid, sid, html: `<p>${esc(r.summary)}</p>${(r.warnings || []).map((w) => `<div class="notice">${esc(w)}</div>`).join("")}`
        + (unused.length ? `<details${unused.length <= 8 ? " open" : ""}><summary>使わなかった行 ${r.n_unused ?? unused.length} 件と理由</summary>`
          + `<ul class="unused">${unused.map((w) => `<li>${esc(w)}</li>`).join("")}</ul></details>` : "") };
      await refresh(sid, undefined, false, nav);
      if (state.nav !== nav) toast(r.summary);
    } catch (e) { if (state.nav === nav && $("#doc-out")) $("#doc-out").innerHTML = `<div class="notice bad">${esc(e.message)}</div>`; else toast(e.message); }
  };
}

async function plateau(c) {
  $("#geo-out").innerHTML += '<p class="muted">PLATEAU の建物データを読んでいます（初回は数十秒かかることがあります）…</p>';
  try {
    const r = await api(`/projects/${state.project.id}/research/plateau`, { method: "POST", body: { lat: c.lat, lon: c.lon, address: c.title } });
    if (!r.candidates.length) { $("#geo-out").innerHTML += `<div class="notice">${esc(r.note || "建物が見つかりませんでした")}</div>`; return; }
    $("#geo-out").innerHTML = `<h4>近くの建物（PLATEAU）</h4><ul class="cands">${r.candidates.map((b, i) => `<li>
      <strong>${esc(b.usage || "用途不明")}</strong>・地上 ${b.storeys_above ?? "?"} 階 / 地下 ${b.storeys_below ?? "?"} 階・高さ ${b.measured_height_m ?? "?"} m・${b.contains_point ? "地点を含む" : b.distance_m + " m"}
      <div class="muted">${esc(b.address || "")}・${esc(b.structure_code || "")}・調査年 ${esc(b.survey_year || "")}・ID ${esc(b.plateau_building_id || "")}</div>
      <button class="btn small" data-b="${i}">この建物を選ぶ</button></li>`).join("")}</ul><p class="muted">${esc(r.note)}</p>`;
    $("#geo-out").querySelectorAll("[data-b]").forEach((x) => (x.onclick = async () => {
      await api(`/projects/${state.project.id}/research/plateau/select`, { method: "POST", body: { candidate: r.candidates[+x.dataset.b], lat: c.lat, lon: c.lon, address: c.title } });
      toast("候補を各項目に入れました。確認して採用してください"); await refresh("basic");
    }));
  } catch (e) { $("#geo-out").innerHTML += `<div class="notice bad">${esc(e.message)}</div>`; }
}

async function estimate(sid, fid) {
  const nav = state.nav;
  try {
    const r = await api(`/projects/${state.project.id}/estimate`, { method: "POST", body: { screen: sid, field: fid } });
    toast(r.n_proposals ? `${r.n_proposals} 件の候補を作りました（採用するまで計算には使いません）` : (r.message || "概算できる項目がありません"));
    await refresh(sid, fid, true, nav);              // the estimate does not use the input: what was typed stays
    if (r.messages && r.messages.length && state.view === "screen" && state.nav === nav) {
      await new Promise((res) => setTimeout(res, 40));          // after refresh() has placed its focus
      const opener = fid ? $(`[data-est="${fid}"]`) : $("#bb-est");
      opener?.focus({ preventScroll: true });
      dialog("自動概算の説明", r.messages.map((x) => `<p>${esc(x)}</p>`).join(""), opener);
    }
  } catch (e) { toast(e.message); }
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

/* what was typed (and not saved) in the rows of the screen, except `except` — kept across a re-render */
function typedRows(except) {
  const out = {};
  document.querySelectorAll("[data-save]").forEach((b) => {
    const f = b.dataset.save;
    if (f === except) return;
    const inp = $("#in-" + f);
    if (!inp) return;
    const us = $("#unit-" + f), st = $("#st-" + f);
    const rendered = (sel) => { const o = [...sel.options].find((x) => x.defaultSelected) || sel.options[0]; return o ? o.value : ""; };
    const initial = inp.tagName === "SELECT" ? rendered(inp) : inp.defaultValue;      // enum fields are selects
    const changed = inp.value !== initial || (us && us.value !== rendered(us)) || (st && !st.disabled && st.value !== rendered(st));
    if (changed) out[f] = { v: inp.value, u: us ? us.value : null, s: st ? st.value : null, unlocked: st ? !st.disabled : false };
  });
  return out;
}
function restoreTyped(saved) {
  for (const [f, x] of Object.entries(saved)) {
    const inp = $("#in-" + f); if (!inp) continue;
    inp.value = x.v;
    if (x.u !== null && $("#unit-" + f)) $("#unit-" + f).value = x.u;
    const st = $("#st-" + f);
    if (st && x.s !== null) { if (x.unlocked) st.disabled = false; st.value = x.s; }
  }
}
/* after a row action: reload and redraw the screen, keeping what was typed. `nav` is the view the action started on: when
   the user has moved since, nothing is redrawn and no focus is taken (only the data is reloaded) */
async function refresh(sid, fid, keepActed = false, nav = state.nav) {
  if (state.nav !== nav) { if (state.project) await loadProject(state.project.id); return; }
  const keep = state.view === "screen" ? typedRows(keepActed ? null : fid) : {};
  await loadProject(state.project.id);
  if (state.nav !== nav) return;
  if (state.view === "screen") {
    const y = window.scrollY; await render(); restoreTyped(keep); setTimeout(() => window.scrollTo(0, y), 0);
    const typed = Object.keys(keep);
    if (typed.length) toast(`まだ保存していない入力：${typed.map((f) => "「" + state.meta.fields[f].label + "」").join("")}`);
  }
  if (fid) setTimeout(() => { if (state.nav !== nav) return; const el = $("#f-" + fid); if (el) { const b = el.querySelector("[data-save]") || el.querySelector("button"); b?.focus({ preventScroll: true }); el.scrollIntoView({ block: "center" }); } }, 30);
}

/* ---------- result ---------- */
async function renderResult(m) {
  $("#title").textContent = "結果";
  m.innerHTML = `<div class="card"><label for="period"><strong>評価期間（年）</strong></label>
    <div class="edit"><input id="period" inputmode="decimal" value="${state.project.last_period || 60}"><button class="btn small" id="calc">計算する</button></div>
    <p class="muted">評価期間だけを変えた再計算は、準備した計算を使い回すので速くなります。</p></div><div id="res-msg" role="status"></div><div id="res"></div>`;
  const seq = state.seq, pid = state.project.id;
  const here = () => state.seq === seq && state.view === "result" && state.project && state.project.id === pid;
  $("#calc").onclick = guard($("#calc"), async () => {
    const p = parseNumber($("#period").value.trim()), T = p.value;
    // checked here as on the server; an error is shown above the last result instead of replacing it
    if (p.bad) { $("#res-msg").innerHTML = `<div class="notice bad">評価期間は数値で入力してください（${esc(p.why || "数値として読めません")}）</div>`; return; }
    if (!(T > 0 && T <= 130)) { $("#res-msg").innerHTML = `<div class="notice bad">評価期間は 0 より大きく 130 年以下で入力してください（エンジンの年表の長さが 130 年）</div>`; return; }
    $("#res-msg").innerHTML = '<p class="muted">計算中…</p>';
    try {
      const r = await api(`/projects/${pid}/calculate`, { method: "POST", body: { period: T } });
      if (state.project && state.project.id === pid) state.project.last_period = r.period;
      if (!here()) return;                                   // the user went elsewhere: do not paint into that view
      $("#res-msg").innerHTML = ""; showResult(r);
    } catch (e) { if (here()) $("#res-msg").innerHTML = `<div class="notice bad">${esc(e.message)}</div>`; }
  });
  try { const r = await api(`/projects/${pid}/result`); if (r && r.status && here()) showResult(r); } catch { /* no result yet */ }
}

function showResult(r) {
  const el = $("#res");
  if (r.period && $("#period")) $("#period").value = r.period;   // the period shown is the period of this result
  if (r.status !== "ok") {
    el.innerHTML = r.stale ? `<div class="notice bad"><strong>入力が変わっています。</strong>前の計算では「${esc(r.message)}」でした。「計算する」を押して計算し直してください。</div>`
      : `<div class="notice bad"><strong>計算していません</strong>：${esc(r.message)}</div>${missingHtml(r)}`;
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

function missingHtml(r) {
  const u = r.unconnected || [], miss = r.missing_required || [];
  return `${miss.length ? `<div class="card"><h3 style="margin-top:0">計算に必須で足りない入力</h3><ul>${miss.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>` : ""}
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
  const projects = await api("/projects");
  m.innerHTML = `<div class="card"><h3 style="margin-top:0">プロジェクト</h3>${projects.map((p) => `<div class="row" style="justify-content:space-between;padding:6px 0">
     <span>${esc(p.name)}（${esc(p.structure_label)}）</span><span class="row"><button class="btn small" data-open="${p.id}">開く</button>
     <button class="btn small" data-del="${p.id}">削除</button></span></div>`).join("") || '<p class="muted">ありません</p>'}</div>
   <div class="card"><h3 style="margin-top:0">このアプリについて</h3><p>${esc(state.meta.app_name)} ${esc(state.meta.version)}</p><p class="muted">${esc(state.meta.disclaimer)}</p>
   <p class="muted">${esc(state.meta.privacy)}</p><p class="muted">データの出典：${esc(state.meta.attribution)}</p></div>`;
  m.querySelectorAll("[data-open]").forEach((b) => (b.onclick = guard(b, () => openProject(+b.dataset.open))));
  m.querySelectorAll("[data-del]").forEach((b) => (b.onclick = guard(b, async () => {
    if (!confirm("このプロジェクトと、その入力・候補・資料の記録、計算用に変換した入力と計算の記録を削除します。元に戻せません。")) return;
    const id = +b.dataset.del;
    await api("/projects/" + id, { method: "DELETE" }); toast("削除しました");
    if (state.project && state.project.id === id) { state.project = null; state.stack = []; }
    if (state.view === "settings") render();
  })));
}

/* ---------- boot ---------- */
async function boot() {
  state.meta = await api("/meta");
  $("#btn-back").onclick = back;
  $("#btn-settings").onclick = () => go("settings");
  const sp = $("#splash");
  const open = () => {
    if (sp.classList.contains("open")) return;
    sp.classList.add("open");
    const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    setTimeout(() => { sp.hidden = true; $("#appbar").hidden = false; $("#main").hidden = false; render(); }, reduce ? 0 : 1200);
  };
  sp.onclick = open; sp.onkeydown = (e) => { if (e.key === "Enter" || e.key === " ") open(); };
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});
}
boot().catch((e) => { document.body.innerHTML = `<p style="padding:16px">起動できませんでした：${esc(e.message)}</p>`; });
