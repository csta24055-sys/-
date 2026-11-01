const {chromium}=require('playwright');
(async()=>{
 const b=await chromium.launch(); const out=[];
 const keys=process.argv.slice(2);
 for (const k of keys){
  const p=await b.newPage();
  await p.goto('https://tepco-career.snar.jp/',{waitUntil:'domcontentloaded',timeout:90000});
  const link=p.locator('h3.tit a',{hasText:k}).first();
  if(await link.count()===0){out.push(`##### ${k}\n(not found)`);await p.close();continue;}
  await Promise.all([p.waitForLoadState('domcontentloaded'),link.click()]);
  await p.waitForTimeout(2500);
  const t=await p.innerText('body');
  out.push(`##### ${k}\n`+t.slice(0,9000));
  await p.close();
 }
 require('fs').writeFileSync(process.env.OUT||'jobdetails.txt',out.join('\n\n'));
 await b.close();
})().catch(e=>{console.error(e);process.exit(1)});
