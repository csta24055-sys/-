// 研究書の2パス組版：Mermaid描画 → 図表番号・目次・図表目次 → 1パス目PDFでページ番号を取得 → 目次・索引を確定 → しおり付きPDF
// 使い方: node tools/book_print.js build/<book>.json
const {chromium} = require('playwright');
const fs = require('fs'), path = require('path'), {execFileSync} = require('child_process');

(async () => {
  const cfg = JSON.parse(fs.readFileSync(process.argv[2], 'utf-8'));
  const browser = await chromium.launch();
  const page = await browser.newPage({viewport: {width: 900, height: 1200}});
  await page.goto('file://' + path.resolve(cfg.html), {waitUntil: 'load', timeout: 180000});

  // 1) Mermaid
  const nMer = await page.evaluate(() => document.querySelectorAll('.mermaid').length);
  if (nMer > 0) {
    await page.addScriptTag({url: 'https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js'});
    await page.evaluate(async () => {
      mermaid.initialize({startOnLoad: false, theme: 'neutral', fontFamily: 'IPAGothic', flowchart: {useMaxWidth: true}, securityLevel: 'loose'});
      for (const el of document.querySelectorAll('.mermaid')) {
        try { await mermaid.run({nodes: [el]}); } catch (e) { el.innerHTML = '<pre>図の描画に失敗：' + (e.message || e) + '</pre>'; }
      }
    });
  }

  // 2) 番号付け・目次・マーカー
  const info = await page.evaluate(() => {
    const body = document.getElementById('body');
    let ch = 0, fig = 0, tab = 0, mk = 0, lastHead = '';
    const marks = {}, tocItems = [], figs = [], tabs = [];
    const addMark = (el, id) => { mk++; const s = document.createElement('span'); s.className = 'mk'; s.textContent = 'QQK' + mk + 'QQ'; el.appendChild(s); marks[mk] = id; };
    const all = body.querySelectorAll('h1, h2, h3, table, div.mermaid');
    let uid = 0;
    all.forEach(el => {
      const tag = el.tagName.toLowerCase();
      if (tag.match(/^h[123]$/)) {
        if (!el.id) el.id = 'h-auto-' + (++uid);
        const txt = el.textContent.trim();
        if (tag === 'h1') {
          if (el.classList.contains('part')) { tocItems.push({lv: 0, id: el.id, t: txt}); }
          else { ch++; fig = 0; tab = 0; tocItems.push({lv: 1, id: el.id, t: txt}); }
        } else { tocItems.push({lv: tag === 'h2' ? 2 : 3, id: el.id, t: txt}); }
        lastHead = txt.replace(/^図\d+\s*/, '');
        addMark(el, el.id);
      } else if (tag === 'table') {
        tab++; const id = 'tbl-' + ch + '-' + tab; el.id = id;
        const cap = document.createElement('caption'); cap.textContent = '表' + ch + '-' + tab + '　' + lastHead.slice(0, 60);
        el.insertBefore(cap, el.firstChild); tabs.push({id, t: cap.textContent}); addMark(cap, id);
      } else {
        fig++; const id = 'fig-' + ch + '-' + fig; el.id = id;
        const cap = document.createElement('div'); cap.className = 'figcap'; cap.textContent = '図' + ch + '-' + fig + '　' + lastHead.slice(0, 60);
        el.after(cap); figs.push({id, t: cap.textContent}); addMark(cap, id);
      }
    });
    const line = (lv, id, t) => `<div class="toc-line toc-l${lv}"><a href="#${id}">${t.replace(/</g,'&lt;')}</a><span class="dots"></span><span class="pg" data-id="${id}">000</span></div>`;
    const anchor = document.getElementById('toc-anchor');
    const toc = document.createElement('section'); toc.id = 'toc';
    toc.innerHTML = '<h1 id="toc-title">目次</h1>' + tocItems.filter(i => i.lv <= 3).map(i => line(i.lv, i.id, i.t)).join('');
    const lof = document.createElement('section'); lof.id = 'lof';
    lof.innerHTML = '<h1 id="lof-title">図表目次</h1><h2>図</h2>' + figs.map(f => line(2, f.id, f.t)).join('') + '<h2>表</h2>' + tabs.map(f => line(2, f.id, f.t)).join('');
    anchor.after(toc); toc.after(lof);
    // 目次・図表目次の見出し自体はしおり対象のままにする
    const fb = tocItems.find(i => i.lv === 0) || tocItems[0]; const firstBody = fb ? fb.id : null;
    return {marks, firstBody, nfig: figs.length, ntab: tabs.length};
  });

  // 3) Mermaid図をPNG化（Word用）
  const els = await page.$$('div.mermaid');
  let k = 0;
  for (const e of els) { k++; try { await e.screenshot({path: path.join(cfg.figdir, 'fig-' + String(k).padStart(3, '0') + '.png')}); } catch (_) {} }

  const pdfOpts = (p) => ({path: p, format: 'A4', printBackground: true, outline: true, tagged: true,
    margin: {top: '20mm', bottom: '18mm', left: '16mm', right: '16mm'}, displayHeaderFooter: true,
    headerTemplate: `<div style="font-family:IPAGothic;font-size:7px;color:#666;width:100%;padding:0 16mm;text-align:right">${cfg.title}</div>`,
    footerTemplate: `<div style="font-family:IPAGothic;font-size:8px;color:#333;width:100%;text-align:center"><span class="pageNumber"></span> / <span class="totalPages"></span></div>`});

  // 4) 1パス目
  const tmp = cfg.pdf.replace(/\.pdf$/, '.pass1.pdf');
  await page.pdf(pdfOpts(tmp));
  const txt = execFileSync('pdftotext', ['-layout', tmp, '-'], {maxBuffer: 1 << 30}).toString('utf-8');
  const pages = txt.split('\f');
  const pageOf = {};
  pages.forEach((pt, i) => { for (const m of pt.matchAll(/QQK(\d+)QQ/g)) { const id = info.marks[m[1]]; if (id && !(id in pageOf)) pageOf[id] = i + 1; } });
  const bodyStart = pageOf[info.firstBody] || 1;
  const index = [];
  for (const term of cfg.terms) {
    const hits = [];
    pages.forEach((pt, i) => { if (i + 1 >= bodyStart && pt.includes(term)) hits.push(i + 1); });
    if (hits.length) index.push([term, hits.length > 15 ? hits.slice(0, 15).concat(['…']) : hits]);
  }
  index.sort((a, b) => a[0].localeCompare(b[0], 'ja'));

  // 5) 目次のページ番号と索引を確定
  await page.evaluate(({pageOf, index}) => {
    document.querySelectorAll('.pg').forEach(s => { const p = pageOf[s.dataset.id]; s.textContent = p ? String(p) : '–'; });
    const ia = document.getElementById('index-anchor');
    if (ia) ia.innerHTML = '<p style="font-size:8.5pt">（用語集・主要な固有名詞の出現ページ。本文の開始ページ以降を自動集計。15ページを超える語は先頭15件）</p><div class="idx">' +
      index.map(([t, ps]) => `<div><b>${t}</b>　${ps.join(', ')}</div>`).join('') + '</div>';
    document.querySelectorAll('.mk').forEach(m => m.remove());
  }, {pageOf, index});
  await page.pdf(pdfOpts(cfg.pdf));
  fs.unlinkSync(tmp);
  await browser.close();
  console.log(JSON.stringify({pdf: cfg.pdf, figures: info.nfig, tables: info.ntab, pages1: pages.length - 1}));
})().catch(e => { console.error(e); process.exit(1); });
