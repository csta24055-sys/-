/* 総合商社研究台帳 — company-first static app. No build step, no external libraries.
 * Each company page loads ONLY data/company/<code>.json; the loaded payload is checked so that
 * every record carries that company's ID before anything is rendered (no cross-company leakage). */
"use strict";

const state = { companies: null, company: null, code: null, snapshot: null };
const $view = document.getElementById("view");

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pill = (s) => `<span class="pill s-${esc(s)}">${esc(s)}</span>`;
const TYPE_JA = { FACT: "確認事実", PARTY_CLAIM: "当事者の主張", ANALYSIS: "分析", HYPOTHESIS: "仮説", FORECAST: "予測", UNKNOWN: "不明" };

async function getJSON(path) {
  const r = await fetch(path, { cache: "no-store" });
  if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
  return r.json();
}

// ---------------------------------------------------------------- markdown (small, safe subset)
function inline(s, code) {
  let t = esc(s);
  t = t.replace(/`([^`]+)`/g, "<code>$1</code>");
  t = t.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  t = t.replace(/\[([^\]]+)\]\((https?:[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  t = t.replace(/&lt;(https?:[^&\s]+)&gt;/g, '<a href="$1" target="_blank" rel="noopener">$1</a>');
  if (code) t = linkIds(t, code);
  return t;
}
function linkIds(html, code) {
  // link evidence IDs of THIS company only; other prefixes stay plain text
  const re = new RegExp(`\\b((?:SRC|PSG|OBS|CLM|HYP|REL|MDL|SL)-${code}-[0-9]{4}|Q-${code}-A\\d{2}-T\\d{2}-\\d{2})\\b`, "g");
  return html.replace(re, (m) => `<a href="#/c/${code}/id/${m}">${m}</a>`);
}
function md(src, code) {
  const lines = String(src || "").replace(/<!--.*?-->/g, "").split("\n");
  const out = []; let i = 0;
  while (i < lines.length) {
    const l = lines[i];
    if (/^```/.test(l)) {
      const buf = []; i++;
      while (i < lines.length && !/^```/.test(lines[i])) buf.push(lines[i++]);
      i++; out.push(`<pre class="code">${esc(buf.join("\n"))}</pre>`); continue;
    }
    if (/^\s*\|/.test(l)) {
      const rows = [];
      while (i < lines.length && /^\s*\|/.test(lines[i])) rows.push(lines[i++]);
      const cells = (r) => r.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
      const body = rows.filter((r) => !/^\s*\|[\s:|-]+\|\s*$/.test(r));
      const [h, ...rest] = body;
      out.push(`<div class="tbl"><table><thead><tr>${cells(h).map((c) => `<th>${inline(c, code)}</th>`).join("")}</tr></thead><tbody>${rest.map((r) => `<tr>${cells(r).map((c) => `<td>${inline(c, code)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`);
      continue;
    }
    let m;
    if ((m = l.match(/^(#{1,4})\s+(.*)/))) { const n = Math.min(m[1].length + 1, 4); out.push(`<h${n}>${inline(m[2], code)}</h${n}>`); i++; continue; }
    if (/^>\s?/.test(l)) { const buf = []; while (i < lines.length && /^>\s?/.test(lines[i])) buf.push(lines[i++].replace(/^>\s?/, "")); out.push(`<blockquote>${buf.map((b) => inline(b, code)).join("<br>")}</blockquote>`); continue; }
    if (/^\s*([-*]|\d+\.)\s+/.test(l)) {
      const ordered = /^\s*\d+\./.test(l); const buf = [];
      while (i < lines.length && /^\s*([-*]|\d+\.)\s+/.test(lines[i])) buf.push(lines[i++].replace(/^\s*([-*]|\d+\.)\s+/, ""));
      out.push(`<${ordered ? "ol" : "ul"}>${buf.map((b) => `<li>${inline(b, code)}</li>`).join("")}</${ordered ? "ol" : "ul"}>`); continue;
    }
    if (!l.trim()) { i++; continue; }
    const buf = [];
    while (i < lines.length && lines[i].trim() && !/^(#|```|\s*\||>|\s*([-*]|\d+\.)\s)/.test(lines[i])) buf.push(lines[i++]);
    out.push(`<p>${inline(buf.join(" "), code)}</p>`);
  }
  return `<div class="md">${out.join("\n")}</div>`;
}

// ---------------------------------------------------------------- data
async function loadCompanies() {
  if (!state.companies) state.companies = await getJSON("data/companies.json");
  document.getElementById("asof").textContent = `基準日 ${state.companies.as_of}`;
  return state.companies;
}
async function loadCompany(code) {
  if (state.code === code && state.company) return state.company;
  state.company = null; state.code = null; state.snapshot = null; // drop the previous company entirely
  const p = await getJSON(`data/company/${encodeURIComponent(code)}.json`);
  const cid = p.company.company_id;
  if (p.company.short_code !== code) throw new Error(`会社コード不一致: ${code} ≠ ${p.company.short_code}`);
  for (const key of ["sources", "passages", "observations", "claims", "hypotheses", "relations", "questions", "search_log"]) {
    const bad = (p[key] || []).find((r) => r.company_id !== cid);
    if (bad) throw new Error(`他社データの混入を検出: ${key} に company_id=${bad.company_id}`);
  }
  state.company = p; state.code = code; state.snapshot = `asof_${p.as_of}`;
  return p;
}

// ---------------------------------------------------------------- views
function setNav(name) {
  document.querySelectorAll(".mainnav a").forEach((a) => {
    if (a.dataset.nav === name) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  });
}

function meter(t) {
  const total = Object.values(t || {}).reduce((a, b) => a + b, 0) || 240;
  const w = (n) => `${(100 * (n || 0)) / total}%`;
  return `<div class="meter" role="img" aria-label="テーマ PASS ${t.PASS || 0} / 進行中 ${t.IN_PROGRESS || 0} / ${total}"><i class="m-pass" style="width:${w(t.PASS)}"></i><i class="m-prog" style="width:${w(t.IN_PROGRESS)}"></i></div>`;
}

async function viewHome() {
  setNav("home");
  const d = await loadCompanies();
  $view.innerHTML = `
    <h1>8社の独立研究</h1>
    <p class="lede">研究の最上位は各社です。会社を開くと、その会社だけの総合報告、社内30軸、240テーマ、原資料、モデルを順にたどれます。比較や会社間のつながりは別画面で扱い、各社の研究を上書きしません。</p>
    <div class="row" style="margin-bottom:12px">研究全体 ${pill(d.RESEARCH_STATUS || "UNKNOWN")}<span class="muted">全8社の会社別ゲートと、横断・アプリ・月次更新のゲートがすべてPASSになったときだけ COMPLETE</span></div>
    <div class="grid8">${d.companies.map((c) => `
      <a class="co" href="#/c/${c.short_code}" data-company="${c.short_code}">
        <div class="row" style="justify-content:space-between"><span class="nm">${esc(c.name_ja)}</span>${pill(c.status)}</div>
        <span class="en">${esc(c.name_en)} · ${esc(c.company_id)}</span>
        ${meter(c.topics_by_state)}
        <dl class="kv"><dt>30軸</dt><dd>PASS ${c.axes_pass} · 進行中 ${c.axes_in_progress}</dd>
        <dt>240テーマ</dt><dd>PASS ${c.topics_by_state.PASS || 0} · 進行中 ${c.topics_by_state.IN_PROGRESS || 0} · 未着手 ${c.topics_by_state.NOT_STARTED || 0}</dd>
        <dt>根拠</dt><dd>一次資料 ${c.sources} · 主張 ${c.claims}</dd>
        <dt>報告書</dt><dd>${esc(c.report_status || "NOT_STARTED")}</dd></dl>
      </a>`).join("")}</div>`;
}

const TABS = [["report", "総合報告"], ["axes", "社内30軸"], ["claims", "主張・根拠"], ["sources", "原資料"], ["hypotheses", "競合仮説"], ["relations", "関係"], ["models", "モデル"], ["updates", "ゲート・更新"]];

function companyShell(p, tab, inner) {
  const c = p.company, s = p.status;
  const snaps = p.snapshots.map((x) => `<option value="${esc(x)}" ${x === state.snapshot ? "selected" : ""}>${x.startsWith("asof_") ? `${x.slice(5)}時点（初期）` : `${x.replace("monthly_", "")}月次`}</option>`).join("");
  const hasMonthly = p.snapshots.some((x) => x.startsWith("monthly_"));
  return `
    <div class="crumb"><a href="#/">8社ポータル</a> / ${esc(c.name_ja)}</div>
    <div class="row" style="justify-content:space-between">
      <div><h1>${esc(c.name_ja)}</h1><span class="muted">${esc(c.name_en)} · ${esc(c.company_id)} · 証券コード ${esc(c.securities_code)}</span></div>
      <div class="row">${pill(s.company_research_status || "NOT_STARTED")}<span class="muted">軸PASS ${s.axes_pass ?? 0}/30</span></div>
    </div>
    <div class="snap" style="margin-top:10px"><label for="snapSel">表示時点</label><select id="snapSel">${snaps}</select>
      ${hasMonthly ? "" : '<span class="muted">月次スナップショットはまだありません（初期スナップショットのみ）</span>'}</div>
    <nav class="tabs" aria-label="会社内の画面">${TABS.map(([k, v]) => `<a href="#/c/${c.short_code}/${k}" ${k === tab ? 'aria-current="page"' : ""}>${v}</a>`).join("")}</nav>
    <section class="panel">${inner}</section>`;
}

function recheckIds(p) {
  if (!state.snapshot || !state.snapshot.startsWith("monthly_")) return new Set();
  const m = state.snapshot.replace("monthly_", "");
  return new Set(p.claim_status_events.filter((e) => (e.update_id || "").includes(m)).map((e) => e.claim_id));
}

function claimHTML(p, x, code) {
  const psg = Object.fromEntries(p.passages.map((q) => [q.passage_id, q]));
  const rc = recheckIds(p);
  const warn = x.claim_type === "HYPOTHESIS" || x.claim_type === "ANALYSIS" || x.validity === "NEEDS_RECHECK" || rc.has(x.claim_id);
  return `<div class="claim" id="${esc(x.claim_id)}">
    <div class="hd"><a class="mono" href="#/c/${code}/id/${esc(x.claim_id)}">${esc(x.claim_id)}</a>${pill(TYPE_JA[x.claim_type] ? x.claim_type : "UNKNOWN")}<span class="muted">${esc(TYPE_JA[x.claim_type])}</span>
    <span class="mono muted">${esc(x.topic_id)}</span>${pill(rc.has(x.claim_id) ? "NEEDS_RECHECK" : x.validity)}</div>
    <div>${linkIds(esc(x.statement), code)}</div>
    ${warn ? `<div class="muted" style="font-size:.82rem">${x.claim_type === "ANALYSIS" ? "研究側の推論です。原資料が直接述べた内容ではありません。" : ""}${x.validity === "NEEDS_RECHECK" || rc.has(x.claim_id) ? " 再確認が必要です。" : ""}</div>` : ""}
    <div style="font-size:.82rem">${x.evidence.map((e) => { const q = psg[e.passage_id] || {}; const loc = q.locator ? Object.entries(q.locator).map(([k, v]) => `${k}=${v}`).join(" ") : ""; return `<div>${pill(e.direction)} <a class="mono" href="#/c/${code}/id/${esc(e.passage_id)}">${esc(e.passage_id)}</a> → <a class="mono" href="#/c/${code}/id/${esc(q.source_id)}">${esc(q.source_id)}</a> <span class="muted">${esc(loc)}</span> 「${esc(q.excerpt)}」</div>`; }).join("")}</div>
    ${x.notes ? `<div class="muted" style="font-size:.82rem">注: ${linkIds(esc(x.notes), code)}</div>` : ""}
  </div>`;
}

function exportCSV(p) {
  const rows = [["claim_id", "company_id", "axis_id", "topic_id", "claim_type", "validity", "statement", "passages"]];
  for (const x of p.claims) rows.push([x.claim_id, x.company_id, x.axis_id, x.topic_id, x.claim_type, x.validity, x.statement, x.evidence.map((e) => e.passage_id).join(" ")]);
  const csv = "﻿" + rows.map((r) => r.map((v) => `"${String(v ?? "").replace(/"/g, '""')}"`).join(",")).join("\n");
  download(`${p.company.short_code}_claims.csv`, csv, "text/csv");
}
function download(name, text, type) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([text], { type: `${type};charset=utf-8` }));
  a.download = name; document.body.appendChild(a); a.click(); a.remove();
}

async function viewCompany(code, tab = "report", extra = null) {
  setNav("");
  const p = await loadCompany(code);
  const c = p.company;
  let inner = "";
  if (tab === "report") {
    inner = `<div class="row" style="justify-content:flex-end"><button class="btn" id="dlReport">報告書をMarkdownで保存</button></div>${md(p.report_md, code)}`;
  } else if (tab === "axes") {
    inner = `<p class="muted">この会社の内側に登録された30軸です。状態は研究ゲートの機械判定です。未着手のROOT研究カード：${p.root_questions_not_started}件。</p>
      <div class="axes">${p.axes.map((a) => `<a class="ax" href="#/c/${code}/axis/${a.axis_id}"><span class="id">${a.axis_id.replace("AXIS_", "A")}</span><span>${esc(a.axis_name)}</span>${pill(a.state)}</a>`).join("")}</div>`;
  } else if (tab === "axis") {
    const a = p.axes.find((x) => x.axis_id === extra);
    if (!a) throw new Error(`${extra} はこの会社に登録されていません`);
    const gates = Object.fromEntries(p.topic_gates.map((t) => [t.topic_id, t]));
    const qs = p.questions.filter((q) => q.axis_id === a.axis_id && q.kind !== "ROOT_RESEARCH_CARD");
    const cl = p.claims.filter((x) => x.axis_id === a.axis_id);
    inner = `<div class="crumb"><a href="#/c/${code}/axes">社内30軸</a> / ${a.axis_id}</div><h2>${esc(a.axis_id)} ${esc(a.axis_name)} ${pill(a.state)}</h2>
      <h3>テーマ（8）</h3><div class="tbl"><table><thead><tr><th>topic_id</th><th>テーマ</th><th>状態</th><th>主張</th><th>独立起源</th><th>満たしていない条件</th></tr></thead><tbody>
      ${a.topics.map((t) => { const g = gates[t.topic_id] || {}; const fails = Object.entries(g.checks || {}).filter(([, v]) => !v).map(([k]) => k); return `<tr><td class="mono">${t.topic_id}</td><td>${esc(t.name)}</td><td>${pill(g.state || "NOT_STARTED")}</td><td>${g.claims ?? 0}</td><td>${g.independent_origin_groups ?? 0}</td><td class="muted" style="font-size:.78rem">${g.state === "NOT_STARTED" ? "未着手" : esc(fails.join(", ") || "—")}</td></tr>`; }).join("")}
      </tbody></table></div>
      ${a.synthesis_md.includes("TEMPLATE:NOT_STARTED") ? '<div class="warn">この軸の独立レポートはまだ書かれていません。</div>' : md(a.synthesis_md, code)}
      ${qs.length ? `<h3>原子的な問い</h3><div class="tbl"><table><thead><tr><th>ID</th><th>状態</th><th>問い</th><th>主張</th></tr></thead><tbody>${qs.map((q) => `<tr><td class="mono">${esc(q.question_id)}</td><td>${pill(q.status)}</td><td>${esc(q.question)}</td><td>${linkIds(esc((q.claim_ids || []).join(", ")), code)}</td></tr>`).join("")}</tbody></table></div>` : ""}
      ${cl.length ? `<h3>この軸の主張（${cl.length}）</h3>${cl.map((x) => claimHTML(p, x, code)).join("")}` : ""}`;
  } else if (tab === "claims") {
    inner = `<div class="row" style="justify-content:space-between"><span class="muted">主張 ${p.claims.length}件。確認事実・当事者の主張・分析を区別して表示します。</span><button class="btn" id="dlCsv">主張をCSVで保存</button></div>
      ${p.claims.length ? p.claims.map((x) => claimHTML(p, x, code)).join("") : '<div class="warn">この会社の研究はまだ始まっていません。主張・根拠はありません。</div>'}`;
  } else if (tab === "sources") {
    inner = p.sources.length ? `<div class="tbl"><table><thead><tr><th>SOURCE_ID</th><th>発行主体・文書</th><th>公開日</th><th>種別</th><th>原文確認</th><th>sha256</th></tr></thead><tbody>
      ${p.sources.map((s) => `<tr><td><a class="mono" href="#/c/${code}/id/${s.source_id}">${s.source_id}</a></td><td>${esc(s.publisher)}<br><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)}</a></td><td class="mono">${esc(s.published_at)}</td><td>${esc(s.source_type)}</td><td>${pill(s.access === "DIRECT" ? "PASS" : "IN_PROGRESS")} ${esc(s.access)}</td><td class="mono">${esc((s.sha256 || "").slice(0, 12))}</td></tr>`).join("")}
      </tbody></table></div><h3>検索ログ</h3><div class="tbl"><table><thead><tr><th>LOG</th><th>クエリ</th><th>件数</th><th>採用</th><th>備考・除外</th></tr></thead><tbody>
      ${p.search_log.map((l) => `<tr><td class="mono">${l.log_id}</td><td>${esc(l.query)}</td><td>${l.results}</td><td>${linkIds(esc((l.adopted || []).join(", ")), code)}</td><td style="font-size:.8rem">${esc(l.status || "")} ${esc(l.notes || "")} ${(l.excluded || []).map((e) => `除外: ${esc(e.item)}（${esc(e.reason)}）`).join(" ")}</td></tr>`).join("")}
      </tbody></table></div>` : '<div class="warn">原資料はまだ登録されていません。</div>';
  } else if (tab === "hypotheses") {
    inner = p.hypotheses.length ? p.hypotheses.map((h) => `<div class="claim"><div class="hd"><span class="mono">${h.hypothesis_id}</span>${pill(h.status === "UNRESOLVED" ? "IN_PROGRESS" : h.status === "WEAKENED" ? "FAIL" : "PASS")}<span class="muted">${esc(h.status)}</span></div>
      <div><strong>${esc(h.explanation)}</strong></div><div class="muted" style="font-size:.85rem">現象: ${esc(h.observed_phenomenon)}</div>
      <div style="font-size:.85rem">予測: ${esc(h.expected_observations.join("；"))}<br>反証となる観測: ${esc(h.disconfirming_observations.join("；"))}<br>支持: ${linkIds(esc(h.evidence_for.join(", ") || "—"), code)}／反証: ${linkIds(esc(h.evidence_against.join(", ") || "—"), code)}<br>検討: ${esc(h.counterevidence_notes)}</div></div>`).join("") : '<div class="warn">競合仮説はまだありません。</div>';
  } else if (tab === "relations") {
    inner = p.relations.length ? `${relGraph(p)}<div class="tbl"><table><thead><tr><th>ID</th><th>型</th><th>from → to</th><th>経由</th><th>量</th><th>開始</th><th>確認状態</th><th>根拠</th></tr></thead><tbody>
      ${p.relations.map((r) => `<tr><td class="mono">${r.relation_id}</td><td>${esc(r.type)}</td><td>${esc(r.from_entity)} → ${esc(r.to_entity)}</td><td>${esc(r.via_entity || "")}</td><td>${r.amount ? `${esc(r.amount.value)} ${esc(r.amount.unit)}<br><span class="muted" style="font-size:.75rem">${esc(r.amount.basis)}</span>` : "—"}</td><td class="mono">${esc(r.valid_from || "")}</td><td>${esc(r.status)}</td><td>${linkIds(esc(r.evidence.join(", ")), code)}</td></tr>`).join("")}
      </tbody></table></div>` : '<div class="warn">関係エッジはまだありません。</div>';
  } else if (tab === "models") {
    inner = p.models.length ? p.models.map((m) => `<h3>${esc(m.model_id)} ${esc(m.name)} <span class="muted">v${esc(m.version)}</span></h3><p class="muted">${esc(m.method)}。入力: ${esc(m.inputs)}。スクリプト: <code>models/${esc(m.script)}</code></p>
      <div class="tbl"><table><thead><tr><th>結果キー</th><th>値</th><th>入力観測</th></tr></thead><tbody>${Object.entries(m.outputs_data?.results || {}).filter(([k]) => !k.includes(":")).map(([k, v]) => `<tr><td class="mono">${esc(k)}</td><td class="mono" style="font-size:.78rem">${esc(JSON.stringify(Object.fromEntries(Object.entries(v).filter(([kk]) => kk !== "inputs"))))}</td><td>${linkIds(esc((v.inputs || []).join(", ")), code)}</td></tr>`).join("")}</tbody></table></div>`).join("") : '<div class="warn">モデルはまだありません。表示できる実データがないため、図表も作っていません。</div>';
  } else if (tab === "updates") {
    const s = p.status;
    inner = `<dl class="kv"><dt>会社ゲート</dt><dd>${pill(s.company_research_status || "NOT_STARTED")}</dd><dt>報告書</dt><dd>${esc(s.report_status)}</dd><dt>未記述の章</dt><dd>${esc((s.report_missing_sections || []).join(" ") || "—")}</dd>
      <dt>テーマ</dt><dd>${esc(JSON.stringify(s.topics_by_state))}</dd><dt>整合性エラー</dt><dd>${s.errors ?? 0}</dd><dt>問い</dt><dd>${s.questions_registered}</dd></dl>
      <h3>出典除去テスト（その起源だけに依存する主張）</h3><div class="tbl"><table><tbody>${Object.entries(s.source_ablation_claims_losing_all_support || {}).map(([k, v]) => `<tr><td class="mono" style="font-size:.78rem">${esc(k)}</td><td>${linkIds(esc(v.join(", ") || "—"), code)}</td></tr>`).join("")}</tbody></table></div>
      <h3>月次更新履歴</h3>${md(p.update_history_md, code)}<h3>再確認イベント</h3>${p.claim_status_events.length ? `<ul>${p.claim_status_events.map((e) => `<li class="mono">${esc(e.claim_id)} → ${esc(e.new_validity)} (${esc(e.cause.join(","))}) ${esc(e.update_id)}</li>`).join("")}</ul>` : '<p class="muted">なし</p>'}
      <h3>次回再開手順</h3>${md(p.next_steps_md, code)}`;
  } else if (tab === "id") {
    inner = idView(p, extra, code);
  }
  $view.innerHTML = companyShell(p, tab === "axis" ? "axes" : tab === "id" ? "claims" : tab, inner);
  document.getElementById("snapSel")?.addEventListener("change", (e) => { state.snapshot = e.target.value; route(); });
  document.getElementById("dlCsv")?.addEventListener("click", () => exportCSV(p));
  document.getElementById("dlReport")?.addEventListener("click", () => download(`${c.short_code}_INTEGRATED_COMPANY_REPORT.md`, p.report_md, "text/markdown"));
}

function idView(p, id, code) {
  const pools = [["主張", p.claims, "claim_id"], ["原文位置", p.passages, "passage_id"], ["出典", p.sources, "source_id"], ["観測値", p.observations, "observation_id"], ["仮説", p.hypotheses, "hypothesis_id"], ["関係", p.relations, "relation_id"], ["問い", p.questions, "question_id"], ["検索ログ", p.search_log, "log_id"], ["モデル", p.models.map((m) => ({ ...m, outputs_data: undefined })), "model_id"]];
  let kind = null, rec = null;
  for (const [k, arr, f] of pools) { const r = arr.find((x) => x[f] === id); if (r) { kind = k; rec = r; break; } }
  if (!rec) return `<div class="warn">${esc(id)} はこの会社の台帳にありません。他社のIDはこの画面では開けません。</div>`;
  const s = JSON.stringify;
  const back = [];
  for (const [k, arr, f] of pools) for (const r of arr) if (r[f] !== id && s(r).includes(`"${id}"`)) back.push(`<li>${k}: <a class="mono" href="#/c/${code}/id/${esc(r[f])}">${esc(r[f])}</a></li>`);
  if (kind === "出典") for (const q of p.passages.filter((q) => q.source_id === id)) back.push(`<li>原文位置: <a class="mono" href="#/c/${code}/id/${q.passage_id}">${q.passage_id}</a> 「${esc(q.excerpt)}」</li>`);
  return `<div class="crumb"><a href="#/c/${code}/claims">主張・根拠</a> / ${esc(id)}</div><h2>${esc(kind)} <span class="mono">${esc(id)}</span></h2>
    ${kind === "主張" ? claimHTML(p, rec, code) : ""}
    <pre class="code">${linkIds(esc(JSON.stringify(rec, null, 2)), code)}</pre>
    <h3>この項目を参照しているもの</h3>${back.length ? `<ul>${back.join("")}</ul>` : '<p class="muted">なし</p>'}`;
}

function relGraph(p) {
  const ents = new Set(); p.relations.forEach((r) => { ents.add(r.from_entity); ents.add(r.to_entity); });
  const list = [...ents]; const center = `ENT-${p.company.company_id}`;
  const others = list.filter((e) => e !== center);
  const W = 640, H = 360, cx = W / 2, cy = H / 2, R = 140;
  const pos = { [center]: [cx, cy] };
  others.forEach((e, i) => { const a = (2 * Math.PI * i) / others.length - Math.PI / 2; pos[e] = [cx + R * 1.6 * Math.cos(a), cy + R * Math.sin(a)]; });
  const edges = p.relations.map((r) => { const [x1, y1] = pos[r.from_entity], [x2, y2] = pos[r.to_entity]; return `<line class="edge" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"><title>${esc(r.relation_id)} ${esc(r.type)}</title></line>`; }).join("");
  const nodes = list.map((e) => { const [x, y] = pos[e]; const c = e === center; return `<circle class="${c ? "node-c" : "node-e"}" cx="${x}" cy="${y}" r="${c ? 9 : 6}"></circle><text x="${x}" y="${y - 12}" text-anchor="middle">${esc(c ? p.company.name_ja : e.replace("ENT-", ""))}</text>`; }).join("");
  return `<div class="tbl"><svg viewBox="0 0 ${W} ${H}" width="100%" style="min-width:520px;max-width:${W}px" role="img" aria-label="${esc(p.company.name_ja)}の関係エッジ">${edges}${nodes}</svg></div>`;
}

function crossGraph(companies, rel) {
  // one line per company pair; solid = both companies' own disclosures, dashed = one side only, thick = third-party confirmation as well
  const W = 440, R = 130, cx = W / 2, cy = W / 2, pos = {}, ang = {};
  companies.forEach((c, i) => { const a = -Math.PI / 2 + (2 * Math.PI * i) / companies.length; ang[c.company_id] = a; pos[c.company_id] = [cx + R * Math.cos(a), cy + R * Math.sin(a)]; });
  const pairs = {};
  rel.forEach((r) => { const k = [r.company_a, r.company_b].sort().join("|"); (pairs[k] = pairs[k] || []).push(r); });
  const lines = Object.entries(pairs).map(([k, rs]) => {
    const [a, b] = k.split("|"); if (!pos[a] || !pos[b]) return "";
    const both = rs.some((r) => r.status === "VERIFIED_BOTH_SIDES"), tp = rs.some((r) => (r.evidence_level || "").endsWith("+THIRD_PARTY"));
    const [x1, y1] = pos[a], [x2, y2] = pos[b];
    return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="var(--accent)" stroke-opacity=".7" stroke-width="${tp ? 3 : 1.5}" ${both ? "" : 'stroke-dasharray="5 4"'}><title>${esc(rs.map((r) => `${r.relation_id} ${r.type} ${r.evidence_level || r.status}`).join("\n"))}</title></line>`
      + `<text x="${(x1 + x2) / 2}" y="${(y1 + y2) / 2}" font-size="10" fill="var(--muted)" text-anchor="middle">${rs.length}</text>`;
  }).join("");
  const nodes = companies.map((c) => {
    const [x, y] = pos[c.company_id], a = ang[c.company_id], co = Math.cos(a);
    const lx = cx + (R + 16) * co, ly = cy + (R + 16) * Math.sin(a) + 4, anchor = co > 0.3 ? "start" : co < -0.3 ? "end" : "middle";
    return `<circle cx="${x}" cy="${y}" r="7" class="node-c"></circle><text x="${lx}" y="${ly + (Math.abs(co) <= 0.3 ? (Math.sin(a) < 0 ? -4 : 8) : 0)}" font-size="11" fill="var(--fg)" text-anchor="${anchor}">${esc(c.name_ja)}</text>`;
  }).join("");
  return `<figure style="margin:1rem 0;max-width:460px"><svg viewBox="0 0 ${W} ${W}" role="img" aria-label="会社間エッジの図">${lines}${nodes}</svg><figcaption class="muted" style="font-size:.8rem">線は会社の組。数字はその組のエッジ数。実線＝両側確認を含む、破線＝片側確認のみ、太線＝第三者確認つきを含む。線の有無は関係の存在だけを示し、影響の強さではない。</figcaption></figure>`;
}

async function viewNetwork() {
  setNav("network");
  const [d, x] = await Promise.all([loadCompanies(), getJSON("data/cross_company.json")]);
  $view.innerHTML = `<h1>会社間ネットワーク</h1><p class="lede">8社それぞれの独立研究の上に、出資・JV・共通株主・同一市場への参加などを各社の原資料IDで接続する層です。証拠水準（片側確認・両側確認・第三者確認）は引用した原文の出所からゲートが計算します。</p>
    <div class="row">状態 ${pill(x.layers.cross_company || "NOT_STARTED")}<span class="muted">会社間エッジ: 両側確認 ${x.relations.filter((r) => r.status === "VERIFIED_BOTH_SIDES").length}件・片側のみ ${x.relations.filter((r) => r.status === "ONE_SIDED").length}件・うち第三者確認つき ${x.relations.filter((r) => (r.evidence_level || "").endsWith("+THIRD_PARTY")).length}件（存在の記録で、因果は主張しない）</span></div>
    ${x.relations.length ? crossGraph(d.companies, x.relations) : '<div class="warn">会社間エッジはまだ0件です。推測でエッジは作りません。</div>'}
    ${x.report_md ? md(x.report_md) : ""}
    <h2>各社が自社の台帳で確認した外部関係</h2><div class="tbl"><table><thead><tr><th>会社</th><th>会社ゲート</th><th>主張</th><th>開く</th></tr></thead><tbody>${d.companies.map((c) => `<tr><td>${esc(c.name_ja)}</td><td>${pill(c.status)}</td><td>${c.claims}</td><td><a href="#/c/${c.short_code}/relations">関係を見る</a></td></tr>`).join("")}</tbody></table></div>`;
}
async function viewWorld() {
  setNav("world");
  const w = await getJSON("data/world.json");
  $view.innerHTML = `<h1>世界統合</h1><div class="row">状態 ${pill(w.layers.world_model || "NOT_STARTED")}</div>${w.report_md ? md(w.report_md) : ""}`;
}
async function viewGates() {
  setNav("gates");
  const g = await getJSON("data/gates.json");
  $view.innerHTML = `<h1>研究ゲート</h1><div class="row">RESEARCH_STATUS ${pill(g.RESEARCH_STATUS)}<span class="muted">基準日 ${esc(g.as_of)}</span></div>
    <h2>会社別</h2><div class="tbl"><table><thead><tr><th>会社</th><th>COMPANY_RESEARCH_STATUS</th><th>報告書</th><th>軸PASS</th><th>テーマ</th><th>一次資料</th><th>独立起源</th><th>エラー</th></tr></thead><tbody>
    ${g.companies.map((c) => `<tr><td><a href="#/c/C${c.company_id.slice(-2)}/updates">${esc(c.company_name)}</a></td><td>${pill(c.company_research_status)}</td><td>${esc(c.report_status)}</td><td>${c.axes_pass}/30</td><td style="font-size:.8rem">${esc(JSON.stringify(c.topics_by_state))}</td><td>${c.sources_direct}</td><td>${c.independent_origin_groups}</td><td>${c.errors}</td></tr>`).join("")}</tbody></table></div>
    <h2>横断レイヤー</h2><dl class="kv">${Object.entries(g.layers).filter(([k]) => !["monthly_update_runs", "scheduler"].includes(k)).map(([k, v]) => `<dt>${esc(k)}</dt><dd>${pill(v)}</dd>`).join("")}
    <dt>月次実行</dt><dd class="mono">${esc((g.layers.monthly_update_runs || []).join(", ") || "なし")}</dd><dt>スケジューラ</dt><dd>${g.layers.scheduler?.verified_running ? "稼働を確認済み" : "稼働は未確認（自動稼働中とは表示しません）"}</dd></dl>
    <h2>整合性エラー</h2>${g.errors.length ? `<ul>${g.errors.map((e) => `<li>${esc(e.code)} ${esc(e.company_id)}: ${esc(e.message)}</li>`).join("")}</ul>` : '<p class="muted">0件</p>'}`;
}

// ---------------------------------------------------------------- router
async function route() {
  const h = location.hash.replace(/^#\/?/, "");
  const parts = h.split("/").filter(Boolean);
  try {
    await loadCompanies();
    if (!parts.length) await viewHome();
    else if (parts[0] === "c" && parts[1]) {
      const code = parts[1];
      if (!/^C\d{2}$/.test(code)) throw new Error("会社コードが不正です");
      if (parts[2] === "axis") await viewCompany(code, "axis", parts[3]);
      else if (parts[2] === "id") await viewCompany(code, "id", decodeURIComponent(parts[3] || ""));
      else await viewCompany(code, parts[2] || "report");
    } else if (parts[0] === "network") await viewNetwork();
    else if (parts[0] === "world") await viewWorld();
    else if (parts[0] === "gates") await viewGates();
    else await viewHome();
  } catch (e) {
    $view.innerHTML = `<div class="warn"><strong>表示できません。</strong> ${esc(e.message)}。データを再生成するには <code>python3 research/tools/build_app.py</code> を実行してください。</div>`;
  }
  $view.focus({ preventScroll: true });
}
window.addEventListener("hashchange", route);
route();
