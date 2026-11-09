'use strict';
// Copies the PDF.js runtime from node_modules into app/vendor/pdfjs so the UI keeps working
// without a bundler (browser preview + Electron). Run after upgrading pdfjs-dist.
const fs=require('node:fs');const path=require('node:path');
const src=path.dirname(require.resolve('pdfjs-dist/package.json'));
const out=path.join(__dirname,'..','vendor','pdfjs');
fs.mkdirSync(out,{recursive:true});
// Saved with a .js extension: some static servers and app WebViews do not send a JavaScript MIME type for
// .mjs, which breaks module loading. The files are still ES modules.
// The *legacy* build is used on purpose: it carries polyfills (e.g. Promise.withResolvers) so PDF import also
// works on older iPhones/iPads (iOS < 17.4) and older Android WebViews.
for(const [from,to] of [['legacy/build/pdf.min.mjs','pdf.min.js'],['legacy/build/pdf.worker.min.mjs','pdf.worker.min.js'],['LICENSE','LICENSE']]) fs.copyFileSync(path.join(src,from),path.join(out,to));
// CMaps are required to read Japanese (CJK) PDFs that use predefined CID encodings.
for(const dir of ['cmaps','standard_fonts']){fs.rmSync(path.join(out,dir),{recursive:true,force:true});fs.cpSync(path.join(src,dir),path.join(out,dir),{recursive:true});}
fs.writeFileSync(path.join(out,'VERSION'),require('pdfjs-dist/package.json').version+'\nbuild=legacy\n');
console.log('PDF.js',require('pdfjs-dist/package.json').version,'->',out);
