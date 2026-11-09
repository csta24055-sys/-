'use strict';
const test=require('node:test');const assert=require('node:assert/strict');
const fs=require('node:fs');const path=require('node:path');const vm=require('node:vm');
const d=require('../src/domain.js');const papers=require('../data/papers.json');

test('seed.js はpapers.jsonと同一データ（ブラウザ版とデスクトップ版の初期値が一致）',()=>{
  const ctx={window:{}};vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../data/seed.js'),'utf8'),ctx);
  assert.deepEqual(JSON.parse(JSON.stringify(ctx.window.TAJIMA_SEED)),papers);
});
test('papers.csv の行数・IDがJSONと一致',()=>{
  const lines=fs.readFileSync(path.join(__dirname,'../data/papers.csv'),'utf8').replace(/^﻿/,'').trim().split(/\r?\n/);
  assert.equal(lines.length-1,papers.length);
  assert.deepEqual(lines.slice(1).map(l=>l.split(',')[0]),papers.map(p=>p.id));
});
test('同義語展開：RC検索で「鉄筋コンクリート」の題名にも一致',()=>{
  const rc=d.paperSearch(papers,'RC');
  assert.ok(rc.some(p=>p.title.includes('鉄筋コンクリート')&&!/rc/i.test(p.title)));
});
test('スペース区切りはAND検索',()=>{
  const both=d.paperSearch(papers,'ピロティ 柱');
  assert.ok(both.length>=1);
  assert.ok(both.every(p=>p.title.includes('ピロティ')&&p.title.includes('柱')));
  assert.equal(d.paperSearch(papers,'ピロティ 存在しない語XYZ').length,0);
});
test('A03: 「ピロティ」で2023・2024の論文が見つかる',()=>{
  const years=new Set(d.paperSearch(papers,'ピロティ').map(p=>p.year));
  assert.ok(years.has(2023)&&years.has(2024));
});
test('A08: 旧耐震 RC ピロティ 崩壊 → 実在する登録論文と理由を返す',()=>{
  const ids=new Set(papers.map(p=>p.id));
  const out=d.recommend(papers,'旧耐震 RC ピロティ 崩壊',8);
  assert.ok(out.length>0);
  assert.ok(out.every(x=>ids.has(x.paper.id)&&x.reasons.length>0));
  assert.ok(out[0].paper.title.includes('ピロティ'));
});
test('本文テキスト検索：該当ページ番号を返す（1始まり）',()=>{
  const p={id:'x',title:'t',year:2020,authors:[],pdfText:['intro','有限要素解析を実施','ひび割れ と せん断']};
  assert.deepEqual(d.fullTextPages(p,'FEM'),[2]);
  assert.deepEqual(d.fullTextPages(p,'crack'),[3]);
  assert.deepEqual(d.fullTextPages(p,''),[]);
  assert.equal(d.paperSearch([p],'せん断').length,1);
});
test('推薦は取り込んだPDF本文の一致を理由として示す',()=>{
  const p={id:'u1',title:'無関係な題名',year:2020,authors:[],categoryIds:['other'],pdfText:['RC柱のせん断破壊について','']};
  const out=d.recommend([p],'RC柱 せん断');
  assert.ok(out.length===1&&out[0].reasons.some(r=>r.includes('PDF本文')&&r.includes('p.1')));
});
test('mergeSeed：新しい書誌だけ追加し利用者の編集を保持',()=>{
  const saved=[{...papers[0],memo:'私のメモ'}];
  const r=d.mergeSeed(saved,papers);
  assert.equal(r.added,papers.length-1);
  assert.equal(r.papers.find(p=>p.id===papers[0].id).memo,'私のメモ');
  assert.equal(d.mergeSeed(r.papers,papers).added,0);
});
test('仮スケジュールの日付はローカル日付（タイムゾーンでずれない）',()=>{
  const out=d.planTemplate('2026-04-01');
  assert.equal(out[0].due,'2026-04-01');assert.equal(out[1].due,'2026-04-15');assert.equal(out[8].due,'2026-10-14');
  assert.throws(()=>d.planTemplate('not-a-date'));
});
test('PDF候補：メタデータTitle/Authorを優先し、根拠を明示',()=>{
  const c=d.pdfCandidates({Title:'Seismic Study',Author:'A Taro; B Hanako',CreationDate:'D:20190101'},[],'Proceedings 2021 ... 2021','file.pdf');
  assert.equal(c.title,'Seismic Study');assert.match(c.titleSource,/メタデータ/);
  assert.deepEqual(c.authors,['A Taro','B Hanako']);
  assert.equal(c.year,2021);assert.match(c.yearSource,/本文/);
});
test('PDF候補：Titleが無ければ1ページ目の最大文字の行、無ければファイル名',()=>{
  const items=[{str:'Small text',height:10,x:0,y:500},{str:'Big Title',height:24,x:0,y:700},{str:'Part 2',height:24,x:120,y:700}];
  assert.equal(d.pdfCandidates({Title:'Microsoft Word - draft.docx'},items,'','f.pdf').title,'Big Title Part 2');
  const c=d.pdfCandidates({},[],'','my_paper-2020.pdf');
  assert.equal(c.title,'my paper 2020');assert.equal(c.titleSource,'ファイル名');assert.equal(c.year,null);
});
test('西暦候補：未来年や電話番号様の数字を除外',()=>{
  assert.equal(d.yearCandidate('2018年 2018 3000 12345 2018'),2018);
  assert.equal(d.yearCandidate('no year'),null);
});
test('本文テキストの容量上限',()=>{
  const r=d.capPageTexts(['a'.repeat(60),'b'.repeat(60)],100);
  assert.equal(r.chars,100);assert.ok(r.truncated);assert.equal(r.pages[1].length,40);
});
test('validatePapers：authorsが配列でないデータを拒否',()=>{
  assert.ok(d.validatePapers([{id:'a',title:'t',year:2020,authors:'x'}]).length>0);
});
