#!/usr/bin/env python3
"""最終パック（Markdown）から、スマホで使う面接練習ページ（単一 HTML・外部通信なし）を作る。

使い方: python3 build_trainer.py <final_pack.md> <out.html> [--title "…"]
- 台本・質問・追質問・短答・グループワーク・持ち物を Markdown から機械的に取り出すだけで、文面は変えない。
- 練習記録（言えた／詰まった、チェック、面接後メモ）は端末内（localStorage）にだけ保存する。
"""
from __future__ import annotations

import html
import json
import re
import sys


def parse(md: str) -> dict:
    sec = {}
    parts = re.split(r"^## (\d+)\. (.*)$", md, flags=re.M)
    head = parts[0]
    for i in range(1, len(parts), 3):
        sec[int(parts[i])] = (parts[i + 1].strip(), parts[i + 2])
    data = {"title": (re.search(r"^# (.*)$", head, re.M) or [None, "面接練習"])[1], "pillars": [], "script": [],
            "memo": "", "timing": "", "overrun": "", "qa": [], "spec": [], "short": [], "unknown": "",
            "rephrase": [], "gw": [], "closing": [], "logistics": [], "practice": []}
    if 1 in sec:
        data["pillars"] = [re.sub(r"^\d+\.\s*", "", ln).strip() for ln in sec[1][1].splitlines() if re.match(r"^\d+\.", ln)]
    if 2 in sec:
        body = sec[2][1]
        blocks = re.split(r"^【(\d) ([^】]*)】$", body, flags=re.M)
        for i in range(1, len(blocks), 3):
            text = blocks[i + 2]
            text = re.split(r"^\*\*時間\*\*", text, flags=re.M)[0].strip()
            data["script"].append({"no": int(blocks[i]), "name": blocks[i + 1], "text": text})
        m = re.search(r"^\*\*時間\*\*(.*)$", body, re.M)
        data["timing"] = m.group(1).strip("：: ") if m else ""
        m = re.search(r"^\*\*時間が押したとき\*\*：(.*)$", body, re.M)
        data["overrun"] = m.group(1).strip() if m else ""
        m = re.search(r"```\n(.*?)```", body, re.S)
        data["memo"] = m.group(1).strip() if m else ""
    if 3 in sec:
        body = sec[3][1]
        main, _, rest = body.partition("**専門の確認")
        for blk in re.split(r"^(?=\*\*Q\d+ )", main, flags=re.M):
            m = re.match(r"\*\*(Q\d+) (.*?)\*\*(（.*?）)?\n(.*)", blk, re.S)
            if not m:
                continue
            lines = [ln for ln in m.group(4).strip().splitlines() if ln.strip()]
            first, answer, follows, notes = "", "", [], []
            for ln in lines:
                fm = re.match(r"\*\*「(.*?)」\*\*\s*(.*)", ln)
                if fm and not first:
                    first, answer = fm.group(1), fm.group(2)
                elif ln.startswith("→"):
                    q, _, ans = ln[1:].partition("：")
                    follows.append({"q": q.strip("「」 "), "a": ans.strip()})
                else:
                    notes.append(ln.strip())
            data["qa"].append({"id": m.group(1), "q": m.group(2), "refs": (m.group(3) or "").strip("（）"),
                               "first": first, "answer": answer, "follows": follows, "notes": notes})
        spec, _, short = rest.partition("**短く答える")
        data["spec"] = [ln[2:].strip() for ln in spec.splitlines() if ln.startswith("- ")]
        short_body, _, unknown = short.partition("分からない質問")
        data["short"] = [ln[2:].strip() for ln in short_body.splitlines() if ln.startswith("- ")]
        data["unknown"] = ("分からない質問" + unknown).strip() if unknown else ""
    for key, n in (("rephrase", 4), ("gw", 5), ("closing", 6), ("logistics", 7), ("practice", 8)):
        if n in sec:
            data[key] = [ln.strip() for ln in sec[n][1].strip().splitlines() if ln.strip()]
    data["sections"] = {str(k): v[0] for k, v in sec.items()}
    return data


PAGE = r"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex,nofollow">
<title>__TITLE__</title>
<style>
:root{--bg:#f6f5f1;--card:#fff;--ink:#1d2327;--sub:#5b656d;--line:#dcd9d0;--acc:#0b5d4d;--warn:#a04a00;--bad:#9b1c1c;--ok:#1d6b34}
@media(prefers-color-scheme:dark){:root{--bg:#14181a;--card:#1e2427;--ink:#e9ecee;--sub:#a4adb3;--line:#353d42;--acc:#58c2ac;--warn:#f0a35e;--bad:#f08a8a;--ok:#7fd29a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.75 -apple-system,"Hiragino Sans","Noto Sans JP",sans-serif;padding:0 0 calc(74px + env(safe-area-inset-bottom))}
header{padding:14px 16px 6px}h1{font-size:17px;margin:0}h2{font-size:16px;margin:18px 0 8px}.sub{color:var(--sub);font-size:13px}
main{padding:0 16px;max-width:760px;margin:auto}section{display:none}section.on{display:block}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px;margin:10px 0}
nav{position:fixed;left:0;right:0;bottom:0;background:var(--card);border-top:1px solid var(--line);display:flex;padding-bottom:env(safe-area-inset-bottom);z-index:5}
nav button{flex:1;border:0;background:none;color:var(--sub);font-size:12px;padding:10px 2px;min-height:56px}nav button.on{color:var(--acc);font-weight:700}
button.b{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:10px;padding:10px 14px;font-size:15px;min-height:44px}
button.p{background:var(--acc);border-color:var(--acc);color:#fff}@media(prefers-color-scheme:dark){button.p{color:#06231d}}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}.timer{font:700 44px/1 ui-monospace,Menlo,monospace;font-variant-numeric:tabular-nums}
.blk{border-left:4px solid var(--line);padding:2px 0 2px 12px;margin:12px 0}.blk.now{border-color:var(--acc)}.blk h3{font-size:13px;color:var(--sub);margin:0 0 2px}
.first{font-weight:700}.hide{display:none}.tag{display:inline-block;font-size:12px;border:1px solid var(--line);border-radius:99px;padding:1px 8px;color:var(--sub);margin-right:6px}
.ok{color:var(--ok)}.ng{color:var(--bad)}.warnc{color:var(--warn)}pre{white-space:pre-wrap;font:13px/1.6 ui-monospace,Menlo,monospace;margin:0}
ul{padding-left:1.2em;margin:6px 0}li{margin:6px 0}textarea{width:100%;min-height:90px;border:1px solid var(--line);border-radius:10px;background:var(--card);color:var(--ink);font:15px/1.6 inherit;padding:10px}
label.ck{display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:1px solid var(--line)}label.ck input{width:22px;height:22px;margin-top:3px}
.bar{height:6px;background:var(--line);border-radius:3px;overflow:hidden;margin-top:8px}.bar i{display:block;height:100%;background:var(--acc);width:0}
</style></head><body>
<header><h1>__TITLE__</h1><div class="sub">この端末の中だけで動きます（通信なし）。記録はこの端末にだけ保存されます。</div></header>
<main>
<section id="s-pres" class="on"></section><section id="s-qa"></section><section id="s-spec"></section><section id="s-gw"></section><section id="s-day"></section><section id="s-log"></section>
</main>
<nav id="nav"></nav>
<script>
const D=__DATA__;
const $=(s,r=document)=>r.querySelector(s),E=(t,c,h)=>{const e=document.createElement(t);if(c)e.className=c;if(h!=null)e.innerHTML=h;return e};
const esc=s=>String(s).replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[m]));
const md=s=>esc(s).replace(/\*\*(.+?)\*\*/g,'<b>$1</b>');
const store={get(k,d){try{return JSON.parse(localStorage.getItem('trainer:'+k))??d}catch(e){return d}},set(k,v){try{localStorage.setItem('trainer:'+k,JSON.stringify(v))}catch(e){}}};
const tabs=[['pres','プレゼン'],['qa',D.qa.length+'問'],['spec','短答'],['gw','グループ'],['day','当日'],['log','記録']];
const nav=$('#nav');tabs.forEach(([id,label],i)=>{const b=E('button',i?'':'on',label);b.onclick=()=>{document.querySelectorAll('section').forEach(s=>s.classList.remove('on'));$('#s-'+id).classList.add('on');nav.querySelectorAll('button').forEach(x=>x.classList.remove('on'));b.classList.add('on');scrollTo(0,0)};nav.appendChild(b)});
const fmt=t=>{t=Math.max(0,Math.floor(t));return Math.floor(t/60)+':'+String(t%60).padStart(2,'0')};
function makeTimer(host,marks,limit){let t0=null,acc=0,h=null;const disp=E('div','timer','0:00'),st=E('div','sub','');const bar=E('div','bar','<i></i>');
 const bS=E('button','b p','開始'),bR=E('button','b','リセット'),bL=E('button','b','記録して終了');const row=E('div','row');row.append(bS,bR,bL);host.append(disp,bar,st,row);
 const now=()=>acc+(t0?(Date.now()-t0)/1000:0);
 const tick=()=>{const t=now();disp.textContent=fmt(t);bar.firstChild.style.width=Math.min(100,t/limit*100)+'%';let m=marks.filter(x=>t>=x.t).pop();st.innerHTML=m?('いま: <b>'+esc(m.label)+'</b>'):'';disp.className='timer'+(t>=limit?' ng':(t>=limit-30?' warnc':''));host.dispatchEvent(new CustomEvent('tick',{detail:t}))};
 bS.onclick=()=>{if(t0){acc=now();t0=null;clearInterval(h);bS.textContent='再開'}else{t0=Date.now();h=setInterval(tick,250);bS.textContent='一時停止'}};
 bR.onclick=()=>{t0=null;acc=0;clearInterval(h);bS.textContent='開始';tick()};
 bL.onclick=()=>{const t=now();if(t<1)return;const a=store.get('times',[]);a.push({at:new Date().toLocaleString('ja-JP'),sec:Math.round(t)});store.set('times',a);bR.onclick();host.dispatchEvent(new CustomEvent('logged'))};
 return {now}}
// ---- プレゼン
(function(){const s=$('#s-pres');const marks=[];const tm=(D.timing.match(/[①②③④]\s*(\d+):(\d+)/g)||[]).map(x=>{const m=x.match(/(\d+):(\d+)/);return +m[1]*60+ +m[2]});
 D.script.forEach((b,i)=>marks.push({t:i===0?0:(tm[i-1]??i*50),label:b.no+' '+b.name}));
 const c=E('div','card');c.append(E('h2','', 'プレゼン練習（3〜5分）'));const th=E('div');c.append(th);makeTimer(th,marks,300);
 const tl=E('div','sub');c.append(tl);const renderTimes=()=>{const a=store.get('times',[]);tl.innerHTML=a.length?('計測記録: '+a.slice(-5).map(x=>'<b>'+fmt(x.sec)+'</b>（'+esc(x.at)+'）').join(' / ')):'計測記録: まだありません（声に出して2回計る）'};renderTimes();th.addEventListener('logged',renderTimes);
 s.append(c);const tg=E('div','row');const b1=E('button','b','台本を隠す（メモだけで話す）');tg.append(b1);s.append(tg);
 const sc=E('div','card');D.script.forEach(b=>{const d=E('div','blk');d.dataset.no=b.no;d.append(E('h3','', esc(b.no+' '+b.name)),E('div','',md(b.text).replace(/\n/g,'<br>')));sc.append(d)});s.append(sc);
 th.addEventListener('tick',e=>{const t=e.detail;let cur=0;marks.forEach((m,i)=>{if(t>=m.t)cur=i});sc.querySelectorAll('.blk').forEach((d,i)=>d.classList.toggle('now',i===cur&&t>0))});
 b1.onclick=()=>{sc.classList.toggle('hide');b1.textContent=sc.classList.contains('hide')?'台本を表示':'台本を隠す（メモだけで話す）'};
 if(D.timing)s.append(E('div','card','<b>時間の目安</b><br>'+md(D.timing)+(D.overrun?'<br><br><b>時間が押したとき</b><br>'+md(D.overrun):'')));
 if(D.memo){const m=E('div','card');m.append(E('h2','', '手持ちメモ'),E('pre','',esc(D.memo)));s.append(m)}
 if(D.pillars.length)s.append(E('div','card','<h2>柱3本</h2><ul>'+D.pillars.map(p=>'<li>'+md(p)+'</li>').join('')+'</ul>'))})();
// ---- 13問
(function(){const s=$('#s-qa');let order=D.qa.map((_,i)=>i),pos=0,weakOnly=false;const res=store.get('qa',{});
 const head=E('div','card');const stat=E('div','sub');const row=E('div','row');const bSh=E('button','b','順番を混ぜる'),bWk=E('button','b','詰まった問いだけ'),bAll=E('button','b','一覧');row.append(bSh,bWk,bAll);head.append(E('h2','', '最重要の質問'),stat,row);s.append(head);
 const card=E('div','card');s.append(card);const list=E('div','hide');s.append(list);
 const upd=()=>{const ok=Object.values(res).filter(x=>x==='ok').length,ng=Object.values(res).filter(x=>x==='ng').length;stat.innerHTML='言えた <b class="ok">'+ok+'</b> ／ 詰まった <b class="ng">'+ng+'</b> ／ 全 '+D.qa.length+'問'};
 function show(){upd();if(!order.length){card.innerHTML='該当する問いがありません。';return}const q=D.qa[order[pos%order.length]];let step=0;card.innerHTML='';
  card.append(E('div','', '<span class="tag">'+esc(q.id)+'</span><span class="tag">'+(pos%order.length+1)+' / '+order.length+'</span>'+(res[q.id]?'<span class="tag '+(res[q.id]==='ok'?'ok':'ng')+'">前回: '+(res[q.id]==='ok'?'言えた':'詰まった')+'</span>':'')));
  card.append(E('h2','', esc(q.q)));const a1=E('div','first hide','「'+md(q.first)+'」'),a2=E('div','hide',md(q.answer)),a3=E('div','hide');
  q.follows.forEach(f=>a3.append(E('div','blk','<h3>追質問: '+esc(f.q)+'</h3>'+md(f.a))));q.notes.forEach(n=>a3.append(E('div','sub',md(n))));if(q.refs)a3.append(E('div','sub','根拠: '+esc(q.refs)));
  const bN=E('button','b p','最初の1文を見る');const r2=E('div','row');const bOk=E('button','b','言えた'),bNg=E('button','b','詰まった'),bSk=E('button','b','次へ');r2.append(bOk,bNg,bSk);
  bN.onclick=()=>{step++;if(step===1){a1.classList.remove('hide');bN.textContent='30秒の答えを見る'}else if(step===2){a2.classList.remove('hide');bN.textContent='追質問を見る'}else{a3.classList.remove('hide');bN.classList.add('hide')}};
  const nx=v=>{if(v){res[q.id]=v;store.set('qa',res)}pos++;if(weakOnly)order=D.qa.map((_,i)=>i).filter(i=>res[D.qa[i].id]==='ng');show()};bOk.onclick=()=>nx('ok');bNg.onclick=()=>nx('ng');bSk.onclick=()=>nx();
  card.append(E('div','sub','まず声に出して答える → 答え合わせ'),a1,a2,a3,E('div','row').appendChild(bN).parentNode,r2)}
 bSh.onclick=()=>{for(let i=order.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[order[i],order[j]]=[order[j],order[i]]}pos=0;show()};
 bWk.onclick=()=>{weakOnly=!weakOnly;bWk.classList.toggle('p',weakOnly);order=D.qa.map((_,i)=>i).filter(i=>!weakOnly||res[D.qa[i].id]==='ng');pos=0;show()};
 bAll.onclick=()=>{list.classList.toggle('hide');card.classList.toggle('hide')};
 D.qa.forEach(q=>list.append(E('div','card','<span class="tag">'+esc(q.id)+'</span><b>'+esc(q.q)+'</b><div class="first">「'+md(q.first)+'」</div><div>'+md(q.answer)+'</div>'+q.follows.map(f=>'<div class="blk"><h3>追質問: '+esc(f.q)+'</h3>'+md(f.a)+'</div>').join('')+q.notes.map(n=>'<div class="sub">'+md(n)+'</div>').join(''))));
 show()})();
// ---- 短答
(function(){const s=$('#s-spec');const mk=(t,arr)=>{if(!arr.length)return;const c=E('div','card','<h2>'+t+'</h2>');arr.forEach(x=>{const i=x.indexOf('：');const q=i>0?x.slice(0,i):x,a=i>0?x.slice(i+1):'';const d=E('div','blk','<h3>'+md(q)+'</h3>');const body=E('div','hide',md(a));const b=E('button','b','答えを見る');b.onclick=()=>{body.classList.toggle('hide')};d.append(b,body);c.append(d)});s.append(c)};
 mk('専門の確認（最初の1文で答える）',D.spec);mk('短く答える',D.short);if(D.unknown)s.append(E('div','card',md(D.unknown)));
 if(D.rephrase.length)s.append(E('div','card','<h2>言い直す語／言わないこと</h2>'+D.rephrase.map(x=>'<div>'+md(x)+'</div>').join('')))})();
// ---- グループワーク
(function(){const s=$('#s-gw');const c=E('div','card');c.append(E('h2','', 'グループワーク（50分の目安）'));const th=E('div');c.append(th);
 makeTimer(th,[{t:0,label:'読解・進め方の合意（〜6分）'},{t:360,label:'論点出し（〜15分）'},{t:900,label:'取組と絞り込み（〜30分）'},{t:1800,label:'板の完成（〜42分）'},{t:2520,label:'読み合わせ（〜50分）'}],3000);s.append(c);
 s.append(E('div','card',D.gw.map(x=>'<div>'+md(x)+'</div>').join('')));if(D.closing.length)s.append(E('div','card','<h2>逆質問と締め</h2>'+D.closing.map(x=>'<div>'+md(x)+'</div>').join('')))})();
// ---- 当日
(function(){const s=$('#s-day');const ck=store.get('ck',{});const mk=(t,arr,key)=>{if(!arr.length)return;const c=E('div','card','<h2>'+t+'</h2>');arr.forEach((x,i)=>{const id=key+i;const l=E('label','ck');const inp=E('input');inp.type='checkbox';inp.checked=!!ck[id];inp.onchange=()=>{ck[id]=inp.checked;store.set('ck',ck)};l.append(inp,E('span','',md(x.replace(/^[-\d.]+\s*/,''))));c.append(l)});s.append(c)};
 mk('持ち物と段取り',D.logistics,'l');mk('今夜の練習',D.practice,'p')})();
// ---- 記録
(function(){const s=$('#s-log');const c=E('div','card','<h2>面接のあとに記録する</h2><div class="sub">聞かれた質問・自分の答え・詰まった点を、当日中に。下のボタンで文章にまとめてコピーできます。</div>');
 const f=[['q1','午前：プレゼンの出来（時間・詰まった所）'],['q2','午前：聞かれた質問と自分の答え'],['q3','午後：グループワークの題・自分の役割・効いた発言'],['q4','午後：個別面接で聞かれた質問と答え'],['q5','用意していなかった質問／答えに詰まった点'],['q6','次に変えること']];
 const v=store.get('log',{});f.forEach(([k,l])=>{c.append(E('h2','',l));const t=E('textarea');t.value=v[k]||'';t.oninput=()=>{v[k]=t.value;store.set('log',v)};c.append(t)});
 const out=E('textarea');out.readOnly=true;out.className='hide';const b=E('button','b p','まとめてコピー');b.onclick=async()=>{const times=store.get('times',[]).map(x=>fmt(x.sec)+'（'+x.at+'）').join(' / ');const qa=store.get('qa',{});
  const txt='【面接デブリーフ】\n'+f.map(([k,l])=>'■'+l+'\n'+(v[k]||'（未記入）')).join('\n\n')+'\n\n■練習の記録\nプレゼン計測: '+(times||'なし')+'\n詰まった問い: '+(Object.keys(qa).filter(k=>qa[k]==='ng').join(', ')||'なし');
  out.value=txt;out.classList.remove('hide');try{await navigator.clipboard.writeText(txt);b.textContent='コピーしました'}catch(e){out.select();b.textContent='下の文を選択してコピー'}};
 c.append(E('div','row').appendChild(b).parentNode,out);s.append(c);
 const r=E('button','b','この端末の記録を消す');r.onclick=()=>{if(confirm('練習記録と面接後メモを消します。よろしいですか？')){Object.keys(localStorage).filter(k=>k.startsWith('trainer:')).forEach(k=>localStorage.removeItem(k));location.reload()}};s.append(E('div','card').appendChild(r).parentNode)})();
</script></body></html>
"""


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    md = open(sys.argv[1], encoding="utf-8").read()
    data = parse(md)
    title = sys.argv[sys.argv.index("--title") + 1] if "--title" in sys.argv else data["title"]
    page = PAGE.replace("__TITLE__", html.escape(title)).replace(
        "__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    open(sys.argv[2], "w", encoding="utf-8").write(page)
    print(json.dumps({"script_blocks": len(data["script"]), "qa": len(data["qa"]),
                      "follows": sum(len(q["follows"]) for q in data["qa"]), "spec": len(data["spec"]),
                      "short": len(data["short"]), "bytes": len(page.encode())}, ensure_ascii=False))


if __name__ == "__main__":
    main()
