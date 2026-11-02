// 使い方: node tools/render_page.js URL [リンク抽出の正規表現]
// JavaScriptで描画されるページの本文（innerText）と、条件に合うリンクを出力する
const {chromium}=require('playwright');
(async()=>{const [u,pat]=process.argv.slice(2);const b=await chromium.launch();const p=await b.newPage();
try{await p.goto(u,{waitUntil:'networkidle',timeout:60000});}catch(e){}
await p.waitForTimeout(1500);
const t=await p.evaluate(()=>document.body?document.body.innerText:'');console.log(t);
if(pat){const re=new RegExp(pat);const ls=await p.$$eval('a',as=>as.map(a=>[a.href,(a.innerText||'').trim().replace(/\s+/g,' ')]));
console.log('#### LINKS');for(const [h,x] of ls){if(re.test(h+' '+x))console.log(h,' | ',x.slice(0,60));}}
await b.close();})();
