// print.html から A4縦・2ページのPDFを生成し、ページ数・はみ出しを検査する。
// usage: node build_pdf.js <font_dir> <out.pdf>
//   font_dir: @fontsource/noto-sans-jp の files ディレクトリ
//   （npm pack @fontsource/noto-sans-jp@5.0.19 で取得。無ければ IPAGothic にフォールバック）
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path'), { pathToFileURL } = require('url');
const { execFileSync } = require('child_process');
(async () => {
  const [fontDir, out] = process.argv.slice(2);
  let html = fs.readFileSync(path.join(__dirname, 'print.html'), 'utf8');
  let ff = '';
  for (const w of [400, 700]) {
    const f = path.join(fontDir, `noto-sans-jp-japanese-${w}-normal.woff2`);
    if (fs.existsSync(f)) ff += `@font-face{font-family:"Noto Sans JP";font-weight:${w};src:url("${pathToFileURL(f)}") format("woff2")}\n`;
  }
  html = html.replace('/*FONTFACE*/', ff);
  const tmp = path.join(__dirname, '_print_build.html');
  fs.writeFileSync(tmp, html);
  const b = await chromium.launch();
  const pg = await b.newPage();
  await pg.goto(pathToFileURL(tmp).href, { waitUntil: 'networkidle' });
  await pg.evaluate(() => document.fonts.ready);
  const rep = await pg.evaluate(() => [...document.querySelectorAll('.page')].map(p => {
    const foot = p.querySelector('.foot').getBoundingClientRect();
    const cols = [...p.querySelectorAll('.col')].map(c => c.lastElementChild.getBoundingClientRect().bottom);
    const fonts = [...document.fonts].filter(f => f.status === 'loaded').map(f => f.family + f.weight);
    return { id: p.id, slack: cols.map(c => +(foot.top - c).toFixed(1)), overflow: cols.some(c => c > foot.top), fonts };
  }));
  await pg.pdf({ path: out, format: 'A4', printBackground: true, preferCSSPageSize: true, margin: { top: 0, bottom: 0, left: 0, right: 0 } });
  await b.close(); fs.unlinkSync(tmp);
  for (const r of rep) console.log(`${r.id}: overflow=${r.overflow} 列ごとのフッターまでの余白(px)=${r.slack.join(', ')}`);
  console.log('fonts:', rep[0].fonts.join(' '));
  console.log(execFileSync('pdfinfo', [out]).toString().split('\n').filter(l => /^(Pages|Page size)/.test(l)).join(' | '));
})();
