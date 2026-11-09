'use strict';
// Copies the PDF.js runtime from node_modules into app/vendor/pdfjs so the UI keeps working
// without a bundler (browser preview + Electron). Run after upgrading pdfjs-dist.
const fs=require('node:fs');const path=require('node:path');
const src=path.dirname(require.resolve('pdfjs-dist/package.json'));
const out=path.join(__dirname,'..','vendor','pdfjs');
fs.mkdirSync(out,{recursive:true});
for(const f of ['build/pdf.min.mjs','build/pdf.worker.min.mjs','LICENSE']) fs.copyFileSync(path.join(src,f),path.join(out,path.basename(f)));
// CMaps are required to read Japanese (CJK) PDFs that use predefined CID encodings.
for(const dir of ['cmaps','standard_fonts']){fs.rmSync(path.join(out,dir),{recursive:true,force:true});fs.cpSync(path.join(src,dir),path.join(out,dir),{recursive:true});}
fs.writeFileSync(path.join(out,'VERSION'),require('pdfjs-dist/package.json').version+'\n');
console.log('PDF.js',require('pdfjs-dist/package.json').version,'->',out);
