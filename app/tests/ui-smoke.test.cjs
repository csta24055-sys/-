'use strict';
const test=require('node:test');const assert=require('node:assert/strict');
const fs=require('node:fs');const path=require('node:path');const vm=require('node:vm');
const papers=require('../data/papers.json');const d=require('../src/domain.js');

test('UI render smoke: all main screens render without JS exceptions (virtual DOM; not a real browser test)', async()=>{
  const elements=new Map();const handlers={};
  function el(id){if(!elements.has(id))elements.set(id,{id,innerHTML:'',textContent:'',value:'',dataset:{},classList:{add(){},remove(){},toggle(){},contains:()=>true},addEventListener(){},click(){}});return elements.get(id)}
  const document={getElementById:el,querySelectorAll:()=>[],querySelector:()=>null,readyState:'complete',body:{dataset:{}},addEventListener:(name,fn)=>{handlers[name]=fn}};
  const store=new Map();
  const localStorage={getItem:k=>store.has(k)?store.get(k):null,setItem:(k,v)=>store.set(k,v),removeItem:k=>store.delete(k)};
  const window={TajimaDomain:d,TAJIMA_SEED:papers,scrollTo(){},confirm:()=>true,addEventListener(){},matchMedia:()=>({matches:false}),localStorage,navigator:{}};
  const navigator={userAgent:'node-test',platform:'Linux',maxTouchPoints:0};
  const location={protocol:'file:',hostname:''};
  const source=fs.readFileSync(path.join(__dirname,'../src/app.js'),'utf8');
  vm.runInNewContext(source,{window,document,navigator,location,localStorage,structuredClone,console,setTimeout,clearTimeout,Date,Number,Map,Math,JSON,Promise},{filename:'app.js'});
  await new Promise(r=>setTimeout(r,0));
  assert.match(el('content').innerHTML,/登録論文・研究業績/);
  assert.match(el('content').innerHTML,/年度別の論文数/);
  for(const [section,expected] of [['library','論文ライブラリ'],['summary','本文確認ノート'],['analysis','研究分野別の分布'],['ideas','先行研究の候補'],['plan','研究進行タスク'],['settings','データの保存場所'],['dashboard','研究ダッシュボード']]){
    await handlers.click({target:{closest:()=>({dataset:{tab:section}})}});
    assert.ok(el('content').innerHTML.includes(expected),`Missing ${expected} in ${section}`);
  }
});
