/* WLC Studio – mobile PWA front end. Talks only to the local server's JSON API (/api/...). */
"use strict";
const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const state = { meta: null, project: null, stack: [], view: "home" };

async function api(path, opts = {}) {
  const r = await fetch("/api" + path, { headers: { "Content-Type": "application/json" }, ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined });
  const t = await r.text();
  let j; try { j = t ? JSON.parse(t) : {}; } catch { j = { error: t }; }
  if (!r.ok) throw new Error(j.error || ("HTTP " + r.status));
  return j;
}
function toast(msg) { const t = $("#toast"); t.textContent = msg; t.classList.add("show"); clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.remove("show"), 2600); }
function dialog(title, html) { $("#dlg-title").textContent = title; $("#dlg-content").innerHTML = html; $("#dlg").showModal(); }
function fmt(v, unit) {
  if (v === null || v === undefined || v === "") return "—";
  if (typeof v === "number") return (Math.abs(v) >= 1000 ? v.toLocaleString("ja-JP", { maximumFractionDigits: 1 }) : String(+v.toPrecision(6))) + (unit ? " " + unit : "");
  if (typeof v === "object") return esc(JSON.stringify(v));
  return esc(v) + (unit ? " " + esc(unit) : "");
}
function badge(st) { const L = state.meta.states; return `<span class="badge st-${esc(st)}">${esc(L[st] || st)}</span>`; }

function go(view, arg, push = true) {
  if (push) state.stack.push([state.view, state.arg]);
  state.view = view; state.arg = arg; render();
}
function back() { const p = state.stack.pop(); if (p) { state.view = p[0]; state.arg = p[1]; render(); } else { state.view = "home"; render(); } }

async function render() {
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
  $("#demo").onclick = async () => { const r = await api("/demo", { method: "POST", body: {} }); await loadProject(r.id); go("hub"); };
  m.querySelectorAll("[data-open]").forEach((b) => (b.onclick = async () => { await loadProject(+b.dataset.open); go("hub"); }));
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
  m.querySelectorAll("[data-s]").forEach((b) => (b.onclick = async () => {
    const r = await api("/projects", { method: "POST", body: { structure: b.dataset.s, name: $("#pname").value.trim() } });
    await loadProject(r.id); go("hub");
  }));
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
  const stateSel = `<select id="st-${fid}" aria-label="${esc(F.label)}の状態"><option value="confirmed" ${estimated ? "" : "selected"}>確認済み</option><option value="assumption" ${estimated ? "selected" : ""}>仮定</option></select>`;
  const naLabel = F.na_note ? `適用外（${F.na_note}）` : F.na === "zero" ? "適用外（0 として計算）" : F.na === "absent" ? "適用外（無い）" : "適用外（渡さない）";
  const unc = v && v.uncertainty && v.uncertainty.kind === "unknown" ? `<div class="muted">範囲は不明（根拠のある幅を付けられない推定）</div>`
    : v && v.uncertainty && v.uncertainty.kind !== "none"
    ? `<div class="muted">範囲 ${fmt(v.uncertainty.low, v.unit)} 〜 ${fmt(v.uncertainty.high, v.unit)}${v.uncertainty.kind === "interval" ? (v.uncertainty.calibrated ? "（校正済みの予測区間）" : "（仮の範囲）") : "（シナリオ）"}</div>` : "";
  const ml = (m) => esc((state.meta.methods || {})[m] || m);
  const cands = (f.candidates || []).map((c, i) => `<li><div>${fmt(c.value, c.unit)} ${badge(c.state)} <span class="muted">${ml(c.method)}</span></div>
      ${c.uncertainty && c.uncertainty.kind === "unknown" ? `<div class="muted">範囲は不明</div>` : ""}
      ${c.uncertainty && c.uncertainty.kind !== "none" && c.uncertainty.kind !== "unknown" ? `<div class="muted">範囲 ${fmt(c.uncertainty.low, c.unit)} 〜 ${fmt(c.uncertainty.high, c.unit)}${c.uncertainty.calibrated ? "" : "（仮の範囲）"}</div>` : ""}
      <div class="muted">${c.source_id ? "出典 " + esc(c.source_id) + (c.source_detail ? "：" + esc(c.source_detail) : "") : ""}</div>
      <div class="muted">${esc(c.note || "")}</div><button class="btn small" data-accept="${fid}" data-i="${i}">この候補を採用</button></li>`).join("");
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
      <input type="file" id="docfile" accept=".csv,.xlsx,.ifc,.pdf" aria-label="資料ファイル"><div id="doc-out"></div>
      <p class="muted">原本は既定では保存しません（読んだ数値の候補と、ファイルの指紋だけを残します）。メーカーの BIM データは各社の利用条件（設計検討の目的に限る・使用後は消去など）に従ってください。製品の性能値（質量・冷媒量）は製造時の CO2 ではありません。</p></div>` : "";
  m.innerHTML = extra + S.groups.map((g) => {
    const fids = [...g.fields].sort((a, b) => (pri[b] || 0) - (pri[a] || 0));
    return `<div class="card group"><h3>${esc(g.label)}</h3>${fids.map(fieldHtml).join("")}</div>`;
  }).join("") + `<div class="bottombar"><button class="btn" id="bb-back">戻る</button><button class="btn" id="bb-est">この画面を自動概算</button><button class="btn" id="bb-hub">保存して戻る</button></div>`;
  bindScreen(m, sid);
}

function inputValue(fid) {
  const F = state.meta.fields[fid], el = $("#in-" + fid);
  if (!el) return { empty: true };
  const raw = el.value.trim();
  if (raw === "") return { empty: true };
  if (F.type === "number") { const v = Number(raw.replace(/,/g, "")); return Number.isFinite(v) ? { value: v } : { bad: true }; }
  return { value: raw };
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
/* save one row: "saved" | "unchanged" | "refused" */
async function saveField(fid, quiet = false) {
  const F = state.meta.fields[fid], iv = inputValue(fid);
  if (iv.empty) { if (!quiet) toast("空欄は保存しません（未取得のまま。0 にはしません）"); return "unchanged"; }
  if (iv.bad) { toast("「" + F.label + "」は数値で入力してください"); return "refused"; }
  const value = iv.value;
  const cur = (state.project.fields[fid] || {}).value;
  const us = $("#unit-" + fid), unit = us ? us.value : ((cur && cur.unit) || F.unit);
  const st = $("#st-" + fid).value;
  const body = { value, unit: F.type === "number" ? unit : "", state: st, method: "user_entered" };
  if (cur && cur.value === value) {
    const sameUnit = F.type !== "number" || !cur.unit || cur.unit === unit;
    if (!ownValue(cur)) {
      if (!sameUnit) { toast(`${state.meta.states[cur.state]}の値の単位は付け直せません（候補を採用し直すか、「未取得に戻す」のあと入れ直す）`); await refresh("screen", fid); return "refused"; }
      if (!quiet) toast(`値が変わっていないので保存しません（${state.meta.states[cur.state]}の出典・範囲を残します）`);
      return "unchanged";
    }
    if (sameUnit && cur.state === st) { if (!quiet) toast("変更はありません"); return "unchanged"; }
    if (!sameUnit) {
      if (!confirm(`数値 ${value} はそのままで、単位を ${cur.unit} から ${unit} に付け直します（自分で入れた値の単位の付け間違いを直すとき）。よろしいですか？換算したいときは、換算した数値を入れてください。`)) return "refused";
      body.relabel = true;
    }
    if (cur.scope) body.scope = cur.scope;                       // what the value covers stays with it
  } else if (cur && cur.state === "statistical") {
    if (confirm(`今の値は統計の推定（${(state.meta.methods || {})[cur.method] || cur.method}）でした。新しい値は、その推定を手で直したものですか？\n（はい＝同じ範囲・前提を引き継ぐ。統計の範囲は使わず「範囲は不明」になる／いいえ＝別に調べた値）`)) body.from_estimate = true;
  } else if (cur && cur.scope) {
    const what = cur.scope === "whole_building" ? "基礎・杭を含む建物全体の量" : "鉄筋と鉄骨を合わせた鉄の全量";
    if (confirm(`今の値は「${what}」でした。新しい値も${what}ですか？（はい＝もう一方の欄と二重に数えない／いいえ＝この欄だけの量）`)) body.scope = cur.scope;
  }
  try {
    await api(`/projects/${state.project.id}/fields/${fid}`, { method: "PUT", body });
    return "saved";
  } catch (e) { toast(e.message); await refresh("screen", fid); return "refused"; }
}

function bindScreen(m, sid) {
  $("#bb-back").onclick = back;
  $("#bb-hub").onclick = async () => {
    // 保存して戻る: every row whose input differs from the stored value is saved like its own 保存 button
    const dirty = [...m.querySelectorAll("[data-save]")].map((b) => b.dataset.save).filter(isDirty);
    let saved = 0;
    for (const fid of dirty) {
      const r = await saveField(fid, true);
      if (r === "refused") { toast("「" + state.meta.fields[fid].label + "」を保存できなかったので戻りません"); return; }
      if (r === "saved") saved++;
    }
    await loadProject(state.project.id); toast(saved ? `${saved} 項目を保存しました` : "保存する変更はありませんでした"); back();
  };
  $("#bb-est").onclick = () => estimate(sid, null);
  m.querySelectorAll("[data-save]").forEach((b) => (b.onclick = async () => { if ((await saveField(b.dataset.save)) === "saved") await refresh(sid, b.dataset.save); }));
  m.querySelectorAll("[data-na]").forEach((b) => (b.onclick = async () => {
    const F = state.meta.fields[b.dataset.na];
    if (F.na === "zero" && !F.na_note && !confirm(`「${F.label}」を 0 として計算します。本当に無い（0）と分かっていますか？分からないときは「未取得」のままにしてください。`)) return;
    if (F.na_note && !confirm(`「${F.label}」を「${F.na_note}」として計算します（その分の排出は数えません）。本当にそうだと分かっていますか？分からないときは「未取得」のままにしてください。`)) return;
    await api(`/projects/${state.project.id}/fields/${b.dataset.na}`, { method: "PUT", body: { value: null, state: "not_applicable", method: "user_entered" } });
    await refresh(sid, b.dataset.na);
  }));
  m.querySelectorAll("[data-unset]").forEach((b) => (b.onclick = async () => {
    await api(`/projects/${state.project.id}/fields/${b.dataset.unset}`, { method: "PUT", body: { value: null, state: "not_obtained", method: "user_entered" } });
    await refresh(sid, b.dataset.unset);
  }));
  m.querySelectorAll("[data-nc]").forEach((b) => (b.onclick = async () => {
    await api(`/projects/${state.project.id}/fields/${b.dataset.nc}`, { method: "PUT", body: { value: null, state: "not_computable", method: "user_entered" } });
    await refresh(sid, b.dataset.nc);
  }));
  m.querySelectorAll("[data-later]").forEach((b) => (b.onclick = async () => {
    const f = state.project.fields[b.dataset.later] || {};
    await api(`/projects/${state.project.id}/fields/${b.dataset.later}/later`, { method: "POST", body: { later: !f.later } });
    await refresh(sid, b.dataset.later);
  }));
  m.querySelectorAll("[data-accept]").forEach((b) => (b.onclick = async () => {
    await api(`/projects/${state.project.id}/fields/${b.dataset.accept}/accept`, { method: "POST", body: { index: +b.dataset.i } });
    await refresh(sid, b.dataset.accept);
  }));
  m.querySelectorAll("[data-est]").forEach((b) => (b.onclick = () => estimate(sid, b.dataset.est)));
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
    try {
      const r = await api(`/projects/${state.project.id}/documents`, { method: "POST", body: { name: file.name, data_b64: b64 } });
      $("#doc-out").innerHTML = `<p>${esc(r.summary)}</p>${r.warnings.map((w) => `<div class="notice">${esc(w)}</div>`).join("")}`;
      await refresh(sid);
    } catch (e) { $("#doc-out").innerHTML = `<div class="notice bad">${esc(e.message)}</div>`; }
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
  try {
    const r = await api(`/projects/${state.project.id}/estimate`, { method: "POST", body: { screen: sid, field: fid } });
    toast(r.n_proposals ? `${r.n_proposals} 件の候補を作りました（採用するまで計算には使いません）` : (r.message || "概算できる項目がありません"));
    if (r.messages && r.messages.length) dialog("自動概算の説明", r.messages.map((x) => `<p>${esc(x)}</p>`).join(""));
    await refresh(sid, fid);
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

async function refresh(sid, fid) {
  await loadProject(state.project.id);
  if (state.view === "screen") { const y = window.scrollY; render(); setTimeout(() => window.scrollTo(0, y), 0); }
  if (fid) setTimeout(() => { const el = $("#f-" + fid); if (el) { const b = el.querySelector("[data-save]") || el.querySelector("button"); b?.focus({ preventScroll: true }); el.scrollIntoView({ block: "center" }); } }, 30);
}

/* ---------- result ---------- */
async function renderResult(m) {
  $("#title").textContent = "結果";
  m.innerHTML = `<div class="card"><label for="period"><strong>評価期間（年）</strong></label>
    <div class="edit"><input id="period" inputmode="decimal" value="${state.project.last_period || 60}"><button class="btn small" id="calc">計算する</button></div>
    <p class="muted">評価期間だけを変えた再計算は、準備した計算を使い回すので速くなります。</p></div><div id="res"></div>`;
  $("#calc").onclick = async () => {
    const T = Number($("#period").value); if (!(T > 0)) return toast("評価期間は正の数で入力してください");
    $("#res").innerHTML = '<p class="muted">計算中…</p>';
    try { showResult(await api(`/projects/${state.project.id}/calculate`, { method: "POST", body: { period: T } })); }
    catch (e) { $("#res").innerHTML = `<div class="notice bad">${esc(e.message)}</div>`; }
  };
  try { const r = await api(`/projects/${state.project.id}/result`); if (r && r.status) showResult(r); } catch { /* no result yet */ }
}

function showResult(r) {
  const el = $("#res");
  if (r.status !== "ok") {
    el.innerHTML = r.stale ? `<div class="notice bad"><strong>入力が変わっています。</strong>前の計算では「${esc(r.message)}」でした。「計算する」を押して計算し直してください。</div>`
      : `<div class="notice bad"><strong>計算していません</strong>：${esc(r.message)}</div>${missingHtml(r)}`;
    return;
  }
  const s = r.summary, maxStage = Math.max(...s.stages.map((x) => Math.abs(x.value || 0)), 1);
  const tot = s.total_t === null ? null : s.total_t.toLocaleString("ja-JP", { maximumFractionDigits: 1 });
  const head = s.nothing_counted ? "未計算（計算に入った量がありません）" : tot === null ? "未計算" : (s.lower_bound ? `少なくとも ${tot} tCO2e` : `${tot} tCO2e`);
  const miss = (r.missing_inputs || []);
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
      ${s.engine_complete ? "" : `<li>エンジンが合計できなかった単位：${esc(s.incomplete_units.join("、"))}</li>`}</ul></div>` : ""}
    ${(r.double_count || []).map((x) => `<div class="notice">二重計上の防止：${esc(x)}</div>`).join("")}
    ${(r.stale_estimates || []).map((x) => `<div class="notice bad">「${esc(x.label)}」の推定は、前提が変わっています（${esc(x.changes.join("、"))}）。材料の画面で概算し直してください。</div>`).join("")}</div>
  <div class="card"><h3 style="margin-top:0">推定値の影響</h3><p>${esc(r.reflection.summary)}</p>
    <table class="t"><tr><th>状態</th><th>計算に入った入力</th></tr>${Object.entries(r.reflection.by_state).map(([k, n]) => `<tr><td>${badge(k)}</td><td class="num">${n}</td></tr>`).join("")}</table></div>
  <div class="card"><h3 style="margin-top:0">段階別</h3><table class="t">${s.stages.map((x) => `<tr><td>${esc(x.stage)}</td>
    <td style="width:45%"><div class="bar" style="width:${Math.max(1, Math.abs(x.value || 0) / maxStage * 100)}%"></div></td><td class="num">${fmt(x.value, "")}${x.complete ? "" : ' <span class="badge st-not_computable">不完全</span>'}</td></tr>`).join("")}</table>
    ${(s.hints || []).length ? `<h4>不完全な段階を埋めるには</h4><ul>${s.hints.map((h) => `<li><strong>${esc(h.stage)}</strong>（${esc(h.unit)}）：${esc(h.note)}</li>`).join("")}</ul>` : ""}
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
  m.querySelectorAll("[data-open]").forEach((b) => (b.onclick = async () => { await loadProject(+b.dataset.open); go("hub"); }));
  m.querySelectorAll("[data-del]").forEach((b) => (b.onclick = async () => {
    if (!confirm("このプロジェクトと、その入力・候補・資料の記録、計算用に変換した入力と計算の記録を削除します。元に戻せません。")) return;
    const id = +b.dataset.del;
    await api("/projects/" + id, { method: "DELETE" }); toast("削除しました");
    if (state.project && state.project.id === id) { state.project = null; state.stack = []; }
    render();
  }));
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
