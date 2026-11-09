'use strict';
// Generates a tiny, valid, text-based PDF for tests (no copyrighted content is bundled).
// pages: [[{text,size}], ...]  info: {Title, Author, CreationDate}
function esc(s){return String(s).replace(/[\\()]/g,m=>'\\'+m);}
function makePdf(pages, info={}){
  const objs=[]; // index i -> object body for obj number i+1
  const add=body=>{objs.push(body);return objs.length;};
  const catalog=add(null), pagesObj=add(null), font=add('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>');
  // Non-embedded Japanese CID font with a predefined CMap: exercises PDF.js CMap loading (cmaps/).
  const jpDesc=add('<< /Type /FontDescriptor /FontName /KozMinPr6N-Regular /Flags 6 /FontBBox [-195 -272 1110 1075] /ItalicAngle 0 /Ascent 880 /Descent -120 /CapHeight 740 /StemV 80 >>');
  const jpCid=add(`<< /Type /Font /Subtype /CIDFontType0 /BaseFont /KozMinPr6N-Regular /CIDSystemInfo << /Registry (Adobe) /Ordering (Japan1) /Supplement 6 >> /FontDescriptor ${jpDesc} 0 R /DW 1000 >>`);
  const jpFont=add(`<< /Type /Font /Subtype /Type0 /BaseFont /KozMinPr6N-Regular-UniJIS-UCS2-H /Encoding /UniJIS-UCS2-H /DescendantFonts [${jpCid} 0 R] >>`);
  const kids=[];
  for(const lines of pages){
    let y=760; let stream='BT\n';
    for(const {text,size=11,jp=false} of lines){
      const shown=jp?'<'+[...String(text)].map(ch=>ch.codePointAt(0).toString(16).padStart(4,'0')).join('')+'>':`(${esc(text)})`;
      stream+=`/${jp?'F2':'F1'} ${size} Tf\n1 0 0 1 60 ${y} Tm\n${shown} Tj\n`; y-=size*1.8;
    }
    stream+='ET\n';
    const content=add(`<< /Length ${Buffer.byteLength(stream,'latin1')} >>\nstream\n${stream}endstream`);
    kids.push(add(`<< /Type /Page /Parent ${pagesObj} 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 ${font} 0 R /F2 ${jpFont} 0 R >> >> /Contents ${content} 0 R >>`));
  }
  objs[catalog-1]=`<< /Type /Catalog /Pages ${pagesObj} 0 R >>`;
  objs[pagesObj-1]=`<< /Type /Pages /Kids [${kids.map(k=>k+' 0 R').join(' ')}] /Count ${kids.length} >>`;
  const infoObj=add('<< '+Object.entries(info).map(([k,v])=>`/${k} (${esc(v)})`).join(' ')+' >>');
  let out='%PDF-1.4\n'; const offsets=[];
  objs.forEach((body,i)=>{offsets.push(Buffer.byteLength(out,'latin1'));out+=`${i+1} 0 obj\n${body}\nendobj\n`;});
  const xref=Buffer.byteLength(out,'latin1');
  out+=`xref\n0 ${objs.length+1}\n0000000000 65535 f \n`+offsets.map(o=>String(o).padStart(10,'0')+' 00000 n \n').join('');
  out+=`trailer\n<< /Size ${objs.length+1} /Root ${catalog} 0 R /Info ${infoObj} 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return Buffer.from(out,'latin1');
}
// Sample used by the E2E tests: 4 pages, English words on pages 2-3 and Japanese (CID/CMap) text on page 4.
function samplePdf(){
  return makePdf([
    [{text:'Seismic Damage Evaluation of RC Piloti Columns',size:22},{text:'Taro Test, Hanako Sample',size:12},{text:'Proceedings 2021',size:10},{text:'Abstract placeholder text for automated testing only.',size:10}],
    [{text:'Section 2 Method',size:14},{text:'Nonlinear finite element analysis of the column was performed.',size:10}],
    [{text:'Section 3 Results',size:14},{text:'Shear crack patterns of the piloti column are discussed.',size:10}],
    [{text:'4. 日本語本文の試験',size:14,jp:true},{text:'柱のひび割れと耐震補強について検討した試験用の文章です。',size:11,jp:true}]
  ],{Title:'Seismic Damage Evaluation of RC Piloti Columns',Author:'Taro Test; Hanako Sample',CreationDate:'D:20210405120000'});
}
module.exports={makePdf,samplePdf};
if(require.main===module){const out=process.argv[2]||'sample.pdf';require('node:fs').writeFileSync(out,samplePdf());console.log('wrote',out);}
