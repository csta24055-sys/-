// print.html から A4縦・2ページのPDFを生成し、ページ数・はみ出しを検査する。
// usage: node build_pdf.js <font_dir> <out.pdf> [source.html=print.html]
//   source.html 内の /*COMMONCSS*/ は common.css、<!--INCLUDE:x.svg--> は figs/x.svg の内容で置換される
//   font_dir: @fontsource/noto-sans-jp の files ディレクトリ
//   （npm pack @fontsource/noto-sans-jp@5.0.19 で取得。無ければ IPAGothic にフォールバック）
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path'), { pathToFileURL } = require('url');
const { execFileSync } = require('child_process');
(async () => {
  const [fontDir, out, src = 'print.html'] = process.argv.slice(2);
  let html = fs.readFileSync(path.join(__dirname, src), 'utf8');
  html = html.replace(/<!--INCLUDE:([\w./-]+)-->/g, (_, f) => fs.readFileSync(f.includes('/') ? path.join(__dirname, f) : path.join(__dirname, 'figs', f), 'utf8'));
  const css = path.join(__dirname, 'common.css');
  if (html.includes('/*COMMONCSS*/')) html = html.replace('/*COMMONCSS*/', fs.readFileSync(css, 'utf8'));
  if (html.includes('/*COMMONCSS3*/')) html = html.replace('/*COMMONCSS3*/', fs.readFileSync(path.join(__dirname, 'common3.css'), 'utf8'));
  let ff = '';
  for (const w of [400, 700]) {
    const f = path.join(fontDir, `noto-sans-jp-japanese-${w}-normal.woff2`);
    if (fs.existsSync(f)) ff += `@font-face{font-family:"Noto Sans JP";font-weight:${w};src:url("${pathToFileURL(f)}") format("woff2")}\n`;
  }
  html = html.replace('/*FONTFACE*/', ff);
  const tmp = path.join(__dirname, '_build_' + path.basename(src));
  fs.writeFileSync(tmp, html);
  const b = await chromium.launch();
  const pg = await b.newPage();
  await pg.goto(pathToFileURL(tmp).href, { waitUntil: 'networkidle' });
  await pg.evaluate(() => document.fonts.ready);
  const rep = await pg.evaluate(() => [...document.querySelectorAll('.page')].map(p => {
    const foot = p.querySelector('.foot').getBoundingClientRect();
    const cols = [...p.querySelectorAll('.col')].filter(c => c.lastElementChild).map(c => c.lastElementChild.getBoundingClientRect().bottom).concat([Math.max(...[...p.querySelectorAll('.sec,.concl')].map(e => e.getBoundingClientRect().bottom))]);
    const fonts = [...document.fonts].filter(f => f.status === 'loaded').map(f => f.family + f.weight);
    const minFs = Math.min(...[...p.querySelectorAll('td,li,p,span,b,div')].filter(e => e.childNodes.length && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())).map(e => parseFloat(getComputedStyle(e).fontSize)));
    return { id: p.id, minPt: +(minFs * 0.75).toFixed(2), slack: cols.map(c => +(foot.top - c).toFixed(1)), overflow: cols.some(c => c > foot.top), fonts };
  }));
  await pg.pdf({ path: out, format: 'A4', printBackground: true, preferCSSPageSize: true, margin: { top: 0, bottom: 0, left: 0, right: 0 } });
  await b.close(); fs.unlinkSync(tmp);
  for (const r of rep) console.log(`${r.id}: overflow=${r.overflow} 最小本文=${r.minPt}pt 列ごとのフッターまでの余白(px)=${r.slack.join(', ')}`);
  console.log('fonts:', rep[0].fonts.join(' '));
  console.log(execFileSync('pdfinfo', [out]).toString().split('\n').filter(l => /^(Pages|Page size)/.test(l)).join(' | '));
})();
