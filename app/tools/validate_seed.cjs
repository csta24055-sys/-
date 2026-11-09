'use strict';
const papers=require('../data/papers.json');
const d=require('../src/domain.js');
const errors=d.validatePapers(papers);
const lab=papers.filter(p=>p.collectionScope==='lab');
if(lab.length!==6) errors.push('公式研究室の直近6本の掲載件数が変更されています');
if(papers.some(p=>p.fullTextVerified===true && !p.pdfPath)) errors.push('PDF未確認なのに全文確認済みの項目があります');
if(papers.some(p=>!p.sourceUrl.startsWith('https://'))) errors.push('出典URLが不正です');
if(errors.length) {console.error(errors.join('\n'));process.exit(1);}
console.log(`OK: ${papers.length}件（研究室掲載 ${lab.length}、教授業績 ${papers.length-lab.length}）、出典・分類・識別子を検証`);
