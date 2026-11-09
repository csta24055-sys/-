'use strict';
// A13: verifies packaged apps contain no PDF files, no user state, and that the seed data is intact.
const fs=require('node:fs');const path=require('node:path');
const asar=require('@electron/asar');
const dist=path.join(__dirname,'..','dist');
function findAsars(dir,out=[]){if(!fs.existsSync(dir))return out;for(const e of fs.readdirSync(dir,{withFileTypes:true})){const f=path.join(dir,e.name);if(e.isDirectory()&&!e.isSymbolicLink())findAsars(f,out);else if(e.name==='app.asar')out.push(f);}return out;}
const archives=findAsars(dist);
if(!archives.length){console.error('No app.asar found under dist/. Run a dist:* build first.');process.exit(1);}
let failed=false;
for(const a of archives){
  const files=asar.listPackage(a).map(f=>f.replace(/\\/g,'/'));
  const bad=files.filter(f=>/\.pdf$/i.test(f)||/tajima-state/.test(f)||/node_modules\//.test(f)||/\/tests?\//.test(f));
  const papers=JSON.parse(asar.extractFile(a,'data/papers.json').toString('utf8'));
  const required=['/index.html','/src/app.js','/src/pdf.js','/vendor/pdfjs/pdf.min.mjs','/vendor/pdfjs/pdf.worker.min.mjs','/vendor/pdfjs/cmaps/UniJIS-UCS2-H.bcmap'];
  const missing=required.filter(r=>!files.includes(r));
  console.log(`${path.relative(dist,a)}: ${files.length} entries, papers=${papers.length}, forbidden=${bad.length}, missing=${missing.length}`);
  if(bad.length||missing.length||papers.length!==52||papers.some(p=>p.pdfPath||p.fullTextVerified)){failed=true;console.error({bad,missing});}
}
if(failed)process.exit(1);
console.log('OK: no PDFs / user data bundled; PDF.js runtime and 52 seed records present.');
