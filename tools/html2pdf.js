// 使い方: node tools/html2pdf.js in.html out.pdf
const {chromium} = require('playwright');
(async () => {
  const [inp, out] = process.argv.slice(2);
  const b = await chromium.launch(); const p = await b.newPage();
  await p.goto('file://' + require('path').resolve(inp), {waitUntil: 'load'});
  await p.pdf({path: out, format: 'A4', margin: {top: '15mm', bottom: '15mm', left: '12mm', right: '12mm'}, printBackground: true});
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
