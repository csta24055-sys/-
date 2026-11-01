// 使い方: node tools/html2pdf.js in.html out.pdf  （ページ番号付きA4）
const {chromium} = require('playwright');
(async () => {
  const [inp, out] = process.argv.slice(2);
  const b = await chromium.launch(); const p = await b.newPage();
  await p.goto('file://' + require('path').resolve(inp), {waitUntil: 'load'});
  await p.pdf({path: out, format: 'A4', printBackground: true, displayHeaderFooter: true,
    headerTemplate: '<span></span>',
    footerTemplate: '<div style="font-size:8px;width:100%;text-align:center;color:#555"><span class="pageNumber"></span> / <span class="totalPages"></span></div>',
    margin: {top: '16mm', bottom: '16mm', left: '14mm', right: '14mm'}});
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
