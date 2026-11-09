/* 田嶋研究室 Research Navigator — dependency-free UI shared by the desktop app (Electron),
   the installable web app (PWA on iPhone / Android) and ordinary browsers.
   Bibliography = official public listings; no fabricated abstracts or outcomes. */
(function(){
  'use strict';
  const D=window.TajimaDomain;
  const desktop=window.tajimaDesktop||null;
  // Browser / installed web app persistence (IndexedDB). The desktop app keeps its own JSON file.
  const store=desktop?null:(window.TajimaStore||null);
  const root=document.getElementById('content');
  const modal=document.getElementById('modal');
  const viewer=document.getElementById('viewer');
  const sheet=document.getElementById('sheet');
  const seed=window.TAJIMA_SEED||[];
  const STORAGE_KEY='tajima-app-state';
  const SEED_DATE='2026-11-09';
  const ua=navigator.userAgent||'';
  const isIOS=/iPad|iPhone|iPod/.test(ua)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
  const isAndroid=/Android/i.test(ua);
  const isStandalone=()=>!desktop&&((window.matchMedia&&window.matchMedia('(display-mode: standalone)').matches)||window.navigator.standalone===true);
  let deferredInstall=null;
  let state={schemaVersion:1,papers:structuredClone(seed),plan:[],topic:'',savedAt:null};
  let tab='dashboard';
  let libraryFilter={keyword:'',category:'all',year:'all',collection:'all'};
  let selectedId=seed[0]?.id||null;
  let summaryDirty=false;
  // Fallback only (storage unavailable or full): PDF bytes kept in memory for this session.
  const ephemeralPdfs=new Map();
  const SECTION={dashboard:'ホーム',library:'論文ライブラリ',summary:'要約・研究メモ',analysis:'研究分布・分析',ideas:'先行研究を探す',plan:'研究スケジュール',settings:'設定・使い方'};
  const MORE_TABS=['ideas','plan','settings'];
  const STATUS={biblio:{label:'書誌のみ',color:'#bcc5c3'},pdf:{label:'PDFあり',color:'#8fb2db'},noted:{label:'メモ記入',color:'#2e8b7d'},verified:{label:'本文確認済み',color:'#155c5b'}};
  const COLLECTION={lab:{label:'研究室公式掲載',color:'#155c5b'},faculty:{label:'教授の研究業績（共著含む）',color:'#7fbcb1'},user:{label:'自分で登録',color:'#8fb2db'}};
  const E=s=>String(s??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const P=id=>state.papers.find(p=>p.id===id);
  const sorted=()=>[...state.papers].sort((a,b)=>b.year-a.year||a.id.localeCompare(b.id));
  const fmtCount=n=>Number(n||0).toLocaleString('ja-JP');
  const hasPdf=p=>Boolean(p?.pdfPath)||ephemeralPdfs.has(p?.id);
  // 'idb:<sha256>' = PDF stored inside this browser/phone (IndexedDB); other paths are desktop files.
  const isIdbPath=p=>typeof p?.pdfPath==='string'&&p.pdfPath.startsWith('idb:');
  const hasNotes=p=>{const s=p.summary||{};return ['objective','method','results','conclusion','limitations'].some(k=>String(s[k]||'').trim())||String(p.memo||'').trim().length>0};
  const readingStatus=p=>p.fullTextVerified?'verified':hasNotes(p)?'noted':hasPdf(p)?'pdf':'biblio';
  const scopeOf=p=>p.collectionScope==='lab'?'lab':p.collectionScope==='faculty'?'faculty':'user';
  function toast(msg){const el=document.getElementById('toast');el.textContent=msg;el.classList.add('show');clearTimeout(toast.timeout);toast.timeout=setTimeout(()=>el.classList.remove('show'),3600)}
  function lsGet(k){try{return window.localStorage.getItem(k)}catch(_){return null}}
  function lsSet(k,v){try{window.localStorage.setItem(k,v)}catch(_){/* private mode */}}

  async function load(){
    if(desktop){
      try{const loaded=await desktop.load();if(loaded&&Array.isArray(loaded.papers)){const notice=loaded.notice;delete loaded.notice;state=loaded;if(notice)setTimeout(()=>toast(notice),300)}}
      catch(e){console.error(e);toast('保存データの読み込みに失敗しました')}
    }else{
      try{
        const res=store?await store.loadState():{state:JSON.parse(lsGet(STORAGE_KEY)||'null')};
        const saved=res.state;
        if(saved&&saved.schemaVersion===1&&Array.isArray(saved.papers)&&!D.validatePapers(saved.papers).length){
          const merged=D.mergeSeed(saved.papers,seed);state={...saved,papers:merged.papers};
          if(merged.added)setTimeout(()=>toast(`新しい公開書誌${merged.added}件を追加しました`),300);
        }
        if(store)store.requestPersistence();
      }catch(e){console.error(e)}
    }
    if(!Array.isArray(state.plan))state.plan=[];
    if(D.validatePapers(state.papers).length){console.warn('Saved paper validation failed. Falling back to seed.');state.papers=structuredClone(seed)}
    selectedId=sorted()[0]?.id||null;
    document.getElementById('modePill').textContent=modeLabel();
    document.body.dataset.platform=desktop?'desktop':'web';
    document.body.dataset.display=isStandalone()?'standalone':'browser';
    render();
    document.body.dataset.ready='true';
  }
  async function save(){
    try{
      if(desktop){await desktop.save(state);return true}
      try{if(store)await store.saveState(state);else localStorage.setItem(STORAGE_KEY,JSON.stringify(state))}
      catch(err){
        // Storage full: keep notes/plans and drop the extracted PDF text (search index) if needed.
        if(!/quota/i.test(String(err.name)+String(err.message)))throw err;
        const slim={...state,papers:state.papers.map(p=>{const {pdfText,...rest}=p;return rest})};
        if(store)await store.saveState(slim);else localStorage.setItem(STORAGE_KEY,JSON.stringify(slim));
        toast('保存容量が不足したため、PDF本文の検索用テキストは保存しませんでした');
      }
      return true;
    }catch(err){console.error(err);toast('保存に失敗しました：'+err.message);return false}
  }
  function modeLabel(){return desktop?'DESKTOP · LOCAL':isStandalone()?'WEB APP · LOCAL':'BROWSER · LOCAL'}
  function storageLabel(){return desktop?'PC内のアプリデータ（userData）':store&&store.backend()==='indexeddb'?'この端末の中（IndexedDB）':'この端末のブラウザ（localStorage）'}
  function openExternal(url){
    if(!/^https:\/\//.test(String(url||'')))return;
    if(desktop)return desktop.openSource(url);
    window.open(url,'_blank','noopener,noreferrer');
  }
  // Frees a stored PDF when no paper refers to it any more.
  async function releasePdf(path){
    if(!store||typeof path!=='string'||!path.startsWith('idb:'))return;
    if(state.papers.some(p=>p.pdfPath===path))return;
    try{await store.pdfDelete(path.slice(4))}catch(e){console.warn(e)}
  }
  function ensurePlan(){if(!state.plan.length){state.plan=D.planTemplate();save()}}

  // ---------- small view helpers ----------
  const head=(title,sub)=>`<header class="page-head"><h1 class="page-title">${E(title)}</h1>${sub?`<p class="page-sub">${E(sub)}</p>`:''}</header>`;
  function authorsText(p,sep='・'){return (p.authors||[]).length?p.authors.join(sep):'著者未登録'}
  function status(p){return p?.pdfPath?'PDF登録済み':ephemeralPdfs.has(p?.id)?'PDF仮登録（このセッションのみ）':'全文未登録'}
  function collectionChip(p){const s=scopeOf(p);return `<span class="chip ${s}">${s==='lab'?'研究室公式掲載':s==='faculty'?'教授の研究業績':'自分で登録'}</span>`}
  function categoryChips(p,limit=3){return (p.categoryIds||[]).slice(0,limit).map(id=>`<span class="chip cat">${E(D.TAGS[id]?.label||id)}</span>`).join('')}
  function statusChip(p){const s=readingStatus(p);return `<span class="chip st-${s}">${STATUS[s].label}</span>`}
  function axis(v){const steps=[1,2,3,4,5,10,20,25,50,100,200,500,1000];const step=steps.find(s=>v/s<=5)||Math.ceil(v/5);return {max:Math.max(step,Math.ceil(v/step)*step),step}}
  // Stacked vertical bar chart drawn with HTML/CSS (crisp text, responsive, no library).
  function vchart(groups,series,label){
    const totals=groups.map(g=>series.reduce((s,x)=>s+(g.values[x.key]||0),0));
    const {max,step}=axis(Math.max(1,...totals));
    const ticks=[];for(let t=0;t<=max;t+=step)ticks.push(t);
    const dense=groups.length>9;
    const cols=groups.map((g,i)=>{
      const total=totals[i];
      const segs=series.map(x=>{const v=g.values[x.key]||0;return v?`<i style="height:${v/total*100}%;background:${x.color}"></i>`:''}).join('');
      return `<div class="vcol" title="${E(g.name)}年：${total}件"><div class="vstack" style="height:${total/max*100}%">${segs}</div><span class="vx${dense&&i%2===1?' alt':''}">${E(g.name)}</span></div>`;
    }).join('');
    return `<div class="vchart" role="img" aria-label="${E(label)}"><div class="vchart-y">${ticks.map(t=>`<span style="bottom:${t/max*100}%">${t}</span>`).join('')}</div><div class="vchart-plot">${ticks.slice(1).map(t=>`<div class="vchart-grid" style="bottom:${t/max*100}%"></div>`).join('')}${cols}</div></div><div class="legend">${series.map(x=>`<span><i style="background:${x.color}"></i>${E(x.label)}</span>`).join('')}</div>`;
  }
  function hbars(data){const max=Math.max(1,...data.map(x=>x.value));return data.map(x=>`<div class="hbar"><span>${E(x.name)}</span><div class="hbar-track"><div class="hbar-fill" style="width:${Math.max(1.5,x.value/max*100)}%;background:${E(x.color||'#2e8b7d')}"></div></div><b>${fmtCount(x.value)}</b></div>`).join('')}
  function progRows(rows){return `<div class="prog">${rows.map(r=>{const pct=r.total?Math.round(r.value/r.total*100):0;return `<div class="prog-row"><span>${E(r.name)}</span><div class="prog-track"><div class="prog-fill" style="width:${pct}%"></div><span class="prog-label">${r.value}/${r.total}（${pct}%）</span></div></div>`}).join('')}</div>`}
  function yearGroups(){
    const by={};
    state.papers.forEach(p=>{const y=String(p.year);if(!by[y])by[y]={name:y,values:{lab:0,faculty:0,user:0,biblio:0,pdf:0,noted:0,verified:0}};by[y].values[scopeOf(p)]++;by[y].values[readingStatus(p)]++});
    return Object.values(by).sort((a,b)=>Number(a.name)-Number(b.name));
  }
  const collectionSeries=()=>Object.entries(COLLECTION).map(([key,v])=>({key,...v}));
  const statusSeries=()=>Object.entries(STATUS).map(([key,v])=>({key,...v}));
  function timelineItem(p){return `<div class="tl-item"><div class="tl-year">${E(p.year)}</div><div><button class="tl-title" data-action="paper" data-id="${E(p.id)}">${E(p.title)}</button><div class="tl-sub">${E(authorsText(p))} · ${E(p.venue)}</div><div class="chips">${collectionChip(p)}${categoryChips(p,2)}</div></div></div>`}

  // ---------- install guidance (iPhone Safari / Android Chrome) ----------
  const iosSteps=`<ol class="steps"><li><b>Safari</b> でこのページを開きます（LINEやGoogleアプリ内のブラウザでは追加できません）。</li><li>画面下（iPadは右上）の <span class="kbd">共有 ⬆︎</span> ボタンを押します。</li><li>メニューを下へスクロールして <span class="kbd">ホーム画面に追加</span> を選びます。</li><li>名前が「田嶋研究室」になっていることを確認して <span class="kbd">追加</span> を押します。</li><li>ホーム画面の「田嶋研究室」アイコンから起動すると、独立したアプリ画面で開きます。</li></ol>`;
  const androidSteps=`<ol class="steps"><li><b>Chrome</b> でこのページを開きます。</li><li>右上の <span class="kbd">⋮</span> メニューを開きます。</li><li><span class="kbd">アプリをインストール</span>（表示がない場合は <span class="kbd">ホーム画面に追加</span> → <span class="kbd">インストール</span>）を選びます。</li><li><span class="kbd">インストール</span> を押すと、ホーム画面とアプリ一覧に「田嶋研究室」が追加されます。</li><li>アイコンから起動すると、独立したアプリ画面で開きます。</li></ol>`;
  function installCard(where){
    if(desktop)return '';
    if(isStandalone())return where==='settings'?`<section class="card install-card"><h2>ホーム画面のアプリとして起動中です</h2><p class="description">ホーム画面の「田嶋研究室」アイコンから、独立したアプリ画面で開かれています。データはこの端末の中（IndexedDB）に保存されます。</p></section>`:'';
    const installBtn=deferredInstall?'<button class="btn" data-action="install-app">ホーム画面にインストール</button>':'';
    if(where==='dashboard'){
      if(lsGet('tajima-install-dismissed')==='1')return '';
      const how=isIOS?'Safariの <span class="kbd">共有 ⬆︎</span> → <span class="kbd">ホーム画面に追加</span> で':isAndroid?'Chromeの <span class="kbd">⋮</span> → <span class="kbd">アプリをインストール</span> で':'iPhoneはSafariの「共有 → ホーム画面に追加」、AndroidはChromeの「⋮ → アプリをインストール」で';
      return `<section class="card install-card" id="installCard"><div class="card-head"><h2>ホーム画面に追加してアプリとして使う</h2><button class="link" data-action="dismiss-install">閉じる</button></div><p class="description">${how}ホーム画面に「田嶋研究室」のアイコンが追加され、独立した画面で起動します。App Store・Google Playは不要です。</p><div class="btn-row">${installBtn}<button class="btn-outline small" data-tab="settings">詳しい手順</button></div></section>`;
    }
    return `<section class="card install-card" id="installCard"><h2>ホーム画面に追加する</h2><p class="description">App Store・Google Playでの登録や、コマンド操作は不要です。下の手順で追加すると、ホーム画面に「田嶋研究室」のアイコンができ、独立したアプリ画面で起動します。</p>${installBtn?`<div class="btn-row">${installBtn}</div>`:''}</section>`;
  }

  // ---------- screens ----------
  function renderDashboard(){
    ensurePlan();
    const total=state.papers.length;const count=D.countByCollection(state.papers);
    const st={biblio:0,pdf:0,noted:0,verified:0};state.papers.forEach(p=>st[readingStatus(p)]++);
    const pdfCount=state.papers.filter(hasPdf).length;const noteCount=state.papers.filter(hasNotes).length;
    const planDone=state.plan.filter(x=>x.done).length;const next=state.plan.filter(x=>!x.done).slice(0,3);
    root.innerHTML=head('研究ダッシュボード',`田嶋研究室（RC構造・構造解析研究室）に関する公開書誌 ${total}件。書誌取得日：${SEED_DATE}。研究結果・結論は、本文を読んだ人が記入した内容だけを表示します。`)+
    installCard('dashboard')+
    `<section class="stats">
      <div class="stat"><b id="statTotal">${fmtCount(total)}</b><span>登録論文・研究業績</span></div>
      <div class="stat"><b>${fmtCount(count.lab)}</b><span>研究室公式掲載</span><small>教授業績（共著含む）${fmtCount(count.faculty)}</small></div>
      <div class="stat"><b>${fmtCount(pdfCount)}</b><span>PDF取り込み済み</span><small>端末内に保存</small></div>
      <div class="stat"><b>${fmtCount(noteCount)}</b><span>要約・メモ記入済み</span><small>本文確認済み ${fmtCount(st.verified)}</small></div>
      <div class="stat"><b>${planDone}/${state.plan.length}</b><span>研究計画の完了</span><small>仮スケジュール</small></div>
      <div class="stat"><b>${fmtCount(count.user)}</b><span>自分で登録した資料</span></div>
    </section>`+
    `<section class="card"><div class="card-head"><h2>年度別の論文数</h2><button class="link" data-tab="analysis">グラフで見る →</button></div>${vchart(yearGroups(),collectionSeries(),'年度別の論文数（出典別）')}<p class="note">研究室公式掲載6件と教授の研究業績（共著を含む）46件を区別しています。研究室の全論文ではありません。</p></section>`+
    `<section class="card"><h2>研究の進捗</h2>${progRows([{name:'PDF取り込み',value:pdfCount,total},{name:'要約・メモ',value:noteCount,total},{name:'本文確認',value:st.verified,total},{name:'研究計画',value:planDone,total:state.plan.length}])}<h3>次に実施する作業</h3>${next.length?`<ol class="next-list">${next.map(m=>`<li><b>${E(m.due)}</b>${E(m.title)}</li>`).join('')}</ol>`:'<p class="note">すべての工程が完了しています。</p>'}<div class="btn-row"><button class="btn-outline small" data-tab="plan">研究スケジュール</button><button class="btn-outline small" data-tab="ideas">先行研究を探す</button></div></section>`+
    `<section class="card"><div class="card-head"><h2>新しい研究論文</h2><button class="link" data-tab="library">すべて見る →</button></div><div class="timeline">${sorted().slice(0,5).map(timelineItem).join('')}</div></section>`+
    `<section class="card"><div class="card-head"><h2>研究分野の分布</h2><span class="chip warn">暫定分類</span></div>${hbars(D.countByCategory(state.papers))}<p class="note">1論文が複数分野に該当するため、分野別件数の合計は論文総数を超えることがあります。</p></section>`+
    `<div class="notice cool">この試作品は大学・研究室の公式アプリではありません。論文のタイトル・著者・掲載年は公開情報に基づきます。研究結果・結論は本文を確認するまで空欄です。研究室の正式な日程は収録していません。</div>`;
  }
  function paperRow(p){
    const pages=libraryFilter.keyword?D.fullTextPages(p,libraryFilter.keyword):[];
    const hits=pages.length?`<div class="fulltext-hits">本文一致：${pages.slice(0,8).map(n=>`<button class="link" data-action="view-pdf" data-id="${E(p.id)}" data-page="${n}">p.${n}</button>`).join('')}${pages.length>8?`<span>ほか${pages.length-8}ページ</span>`:''}</div>`:'';
    return `<article class="paper-row" data-paper-id="${E(p.id)}"><div class="row-meta">${statusChip(p)}<span><span class="paper-year">${E(p.year)}</span>年・${E(p.venue)}</span></div><button class="row-title" data-action="paper" data-id="${E(p.id)}">${E(p.title)}</button><div class="row-sub">${E(authorsText(p))}</div><div class="chips">${collectionChip(p)}${categoryChips(p,2)}${hasPdf(p)?`<button class="chip st-pdf" data-action="view-pdf" data-id="${E(p.id)}">PDFを表示</button>`:''}</div>${hits}</article>`;
  }
  function libraryRows(){
    const papers=D.paperSearch(sorted(),libraryFilter.keyword,libraryFilter.category,libraryFilter.year,libraryFilter.collection);
    return {html:papers.map(paperRow).join('')||`<div class="empty"><strong>一致する論文がありません</strong>キーワードや絞り込み条件を変更してください。</div>`,count:papers.length};
  }
  const countNote=c=>c===state.papers.length?`${fmtCount(c)} 件`:`${fmtCount(c)} 件（全${fmtCount(state.papers.length)}件中）`;
  function renderLibrary(){
    const years=[...new Set(state.papers.map(p=>p.year))].sort((a,b)=>b-a);
    const {html,count}=libraryRows();
    const sel=(v,cur)=>String(v)===String(cur)?'selected':'';
    root.innerHTML=head('論文ライブラリ','公開書誌と、自分で取り込んだPDF。本文がない論文は「書誌のみ」と表示します。取り込んだPDFの本文もこの端末内で検索できます。')+
    `<div class="filters"><input class="field search" type="search" id="paperSearch" placeholder="検索（例：ピロティ、FEM、ひび割れ）" value="${E(libraryFilter.keyword)}" aria-label="論文検索" enterkeyhint="search"><select class="field" id="yearFilter" aria-label="年度"><option value="all">全年度</option>${years.map(y=>`<option value="${y}" ${sel(y,libraryFilter.year)}>${y}年</option>`).join('')}</select><select class="field" id="categoryFilter" aria-label="研究分野"><option value="all">全分野</option>${D.CATEGORIES.map(c=>`<option value="${c.id}" ${sel(c.id,libraryFilter.category)}>${E(c.label)}</option>`).join('')}</select><select class="field" id="collectionFilter" aria-label="出典"><option value="all">全資料</option><option value="lab" ${sel('lab',libraryFilter.collection)}>研究室公式掲載</option><option value="faculty" ${sel('faculty',libraryFilter.collection)}>教授の研究業績</option><option value="user" ${sel('user',libraryFilter.collection)}>自分で登録</option></select><button class="btn-outline" data-action="import-pdf">＋ PDFを追加</button></div>`+
    `<p class="count" id="paperResultCount">${countNote(count)}</p><div class="list-card" id="paperRows">${html}</div><p class="note">教授の共著論文を含みます。研究室の全卒業論文・全修士論文の網羅リストではありません。スペース区切りでAND検索、同義語（例：RC＝鉄筋コンクリート、FEM＝有限要素）にも一致します。</p>`;
  }
  function refreshLibraryRows(){const rows=document.getElementById('paperRows');if(!rows)return;const r=libraryRows();rows.innerHTML=r.html;document.getElementById('paperResultCount').textContent=countNote(r.count)}

  function renderSummary(){
    const p=P(selectedId)||sorted()[0];if(!p){root.innerHTML='<div class="empty">論文がありません</div>';return}selectedId=p.id;summaryDirty=false;
    const f=p.summary||{};const pdf=hasPdf(p);
    const field=(key,label,ph)=>`<div><label class="label" for="s-${key}">${label}</label><textarea class="textarea" id="s-${key}" data-summary-field="${key}" placeholder="${E(ph)}">${E(f[key]||'')}</textarea></div>`;
    const options=sorted().map(x=>`<option value="${E(x.id)}" ${x.id===p.id?'selected':''}>${E(x.year)}｜${E(x.title.length>40?x.title.slice(0,40)+'…':x.title)}</option>`).join('');
    root.innerHTML=head('要約・研究メモ','研究目的・方法・結果などを、本文と照合しながら記録します。題名だけから結論を自動生成することはありません。')+
    `<section class="card"><label class="label" for="summaryPaper">対象論文</label><select class="field" id="summaryPaper">${options}</select><h2 style="margin:16px 0 4px">${E(p.title)}</h2><p class="row-sub">${E(authorsText(p))} · ${E(p.venue)} · ${E(p.year)}年</p><div class="chips">${collectionChip(p)}<span class="chip ${p.fullTextVerified?'st-verified':'warn'}" id="verifiedBadge">${p.fullTextVerified?'本文確認済み':'本文未確認'}</span><span class="chip ${pdf?'st-pdf':'st-biblio'}">${E(status(p))}</span></div><label class="check" style="margin-top:14px"><input type="checkbox" id="fullTextVerified" ${p.fullTextVerified?'checked':''} ${pdf?'':'disabled'}> 本文PDFと照合して記入した（自己申告）</label><div class="btn-row">${pdf?`<button class="btn-outline small" data-action="view-pdf" data-id="${E(p.id)}">PDFを表示</button>`:''}<button class="btn-outline small" data-action="attach-pdf" data-id="${E(p.id)}">${pdf?'PDFを差し替える':'PDFを紐づける'}</button></div></section>`+
    `<div class="notice">重要：このアプリには論文の全文・実証結果は含まれていません。「研究目的・結果・結論」はPDFを読んでから記入してください。PDFビューアの「根拠ページに追加」で参照ページを記録できます。</div>`+
    `<section class="card"><div class="card-head"><h2>本文確認ノート</h2><button class="btn small" id="saveSummary" data-action="save-summary">保存</button></div><div class="form-grid">${field('objective','研究目的','論文中に明記された目的')}${field('method','方法・解析条件','FEM・実験など本文で確認した方法')}${field('results','研究結果','数値・条件とあわせて事実のみ')}${field('conclusion','結論','著者の結論を原文と照合して要約')}${field('limitations','研究の限界・今後の課題','本文の記載と自分の推測を分けて')}${field('sourcePages','根拠ページ・図表番号','例：p.4, 図3')}</div><label class="label" for="paperMemo" style="margin-top:16px">自分用の研究メモ</label><textarea class="textarea" id="paperMemo" placeholder="関連研究とのつながり、確認したい点など">${E(p.memo||'')}</textarea><div class="btn-row" style="justify-content:space-between;align-items:center"><span class="note" style="margin:0" id="summaryStatus">保存先：${E(storageLabel())}${p.summaryUpdatedAt?` · 最終保存 ${E(new Date(p.summaryUpdatedAt).toLocaleString('ja-JP'))}`:''}</span><button class="btn" data-action="save-summary">要約・メモを保存</button></div></section>`;
  }
  function collectSummary(p){
    p.summary=p.summary||{};
    document.querySelectorAll('[data-summary-field]').forEach(field=>p.summary[field.dataset.summaryField]=field.value);
    const memo=document.getElementById('paperMemo');if(memo)p.memo=memo.value;
    const verified=document.getElementById('fullTextVerified');if(verified)p.fullTextVerified=Boolean(verified.checked&&hasPdf(p));
    p.summaryUpdatedAt=new Date().toISOString();
  }
  function renderAnalysis(){
    const total=state.papers.length;const years=D.countByYear(state.papers);const categories=D.countByCategory(state.papers);const count=D.countByCollection(state.papers);
    const yearNums=years.map(y=>Number(y.name)).filter(Number.isFinite);const yearSum=years.reduce((s,y)=>s+y.value,0);const groups=yearGroups();
    root.innerHTML=head('研究分布・分析','登録されている書誌データだけを集計します。研究室全体の研究件数や重要度を示すものではありません。')+
    `<section class="stats"><div class="stat"><b>${total}</b><span>集計対象の論文</span></div><div class="stat"><b>${years.length}</b><span>集計年度数</span><small>${yearNums.length?`${Math.min(...yearNums)}〜${Math.max(...yearNums)}年`:'—'}</small></div><div class="stat"><b>${count.lab}</b><span>研究室公式掲載</span></div><div class="stat"><b>${state.papers.filter(hasPdf).length}</b><span>PDF取り込み済み</span></div></section>`+
    `<section class="card"><h2>年度別の論文数（出典別）</h2>${vchart(groups,collectionSeries(),'年度別の論文数（出典別）')}<p class="note" id="yearNote">年度別合計 <b id="yearSum">${yearSum}</b> 件 ＝ 登録件数 ${total} 件。2012〜2025年の一部の著作で、全年度・全論文を網羅しません。</p></section>`+
    `<section class="card"><h2>年度別の読書状況</h2>${vchart(groups,statusSeries(),'年度別の読書状況')}<p class="note">各論文を「書誌のみ → PDFあり → メモ記入 → 本文確認済み」のうち最も進んだ状態で1回だけ数えます。</p></section>`+
    `<section class="card"><div class="card-head"><h2>研究分野別の分布</h2><span class="chip warn">複数分類あり</span></div>${hbars(categories)}<p class="note" id="categoryNote">分類は論文タイトルをもとに付与した暫定タグです。複数分野の重複計上があるため、合計件数（${categories.reduce((s,c)=>s+c.value,0)}）と論文総数（${total}）は一致しません。</p></section>`+
    `<section class="card"><h2>データの出典と範囲</h2><ul class="check-list"><li>研究室公式サイトの「最近の研究論文」6件</li><li>日本大学研究者情報の田嶋教授の業績（共著を含む）46件</li><li>公開書誌情報のみ。各論文の本文PDFおよび研究結果は収録していません</li><li>研究室の卒業論文・修士論文を網羅した資料ではありません</li></ul></section>`;
  }
  function renderIdeas(){
    const topic=state.topic||'旧耐震基準のRC造ピロティ建物の柱崩壊と耐震補強';
    const output=D.recommend(state.papers,topic,8);const cats=D.classify(topic);
    const examples=['旧耐震 RC ピロティ 崩壊','DFRCC 梁 非線形FEM解析','火災後 RC柱 耐震性能','CFRP 補強 梁 曲げ'];
    root.innerHTML=head('新規テーマから先行研究を探す','研究テーマを入力すると、登録済みの論文から関連しそうな先行研究を理由付きで表示します。スコアは検索用の相対値で、研究の新規性や採択可能性は判定しません。')+
    `<section class="card"><label class="label" for="topicInput">研究テーマ・気になる技術</label><textarea class="textarea" id="topicInput" placeholder="例：旧耐震基準のRCピロティ建物の柱崩壊とCFRP補強">${E(topic)}</textarea><div class="example-chips">${examples.map(x=>`<button class="chip cat" data-action="example-topic" data-topic="${E(x)}">${E(x)}</button>`).join('')}</div><div class="btn-row"><button class="btn" data-action="recommend">関連論文を検索</button></div></section>`+
    `<section class="card"><div class="card-head"><h2>推定される関連分野</h2><span class="chip warn">自動分類・暫定</span></div><div class="chips">${cats.map(id=>`<span class="chip">${E(D.TAGS[id]?.label)}</span>`).join('')}</div><p class="note">候補は、登録済み論文の題名・分類タグ・同義語辞書、および自分で取り込んだPDFの本文テキストから検索しています。論文の研究結果を読んで判断した順位ではありません。</p></section>`+
    `<h2 class="section-title">先行研究の候補 <span class="muted" id="recommendCount">${output.length}件</span></h2><div class="list-card" id="recommendList">${output.length?output.map(x=>`<div class="recommend-row"><div class="rec-main"><div style="min-width:0"><button class="row-title" data-action="paper" data-id="${E(x.paper.id)}">${E(x.paper.title)}</button><div class="row-sub">${E(x.paper.year)}年 · ${E(x.paper.venue)}</div><div class="chips">${categoryChips(x.paper,3)}</div><p class="recommend-reason">${E(x.reasons.join(' / '))}</p></div><div class="score">${x.score}<small>検索スコア</small></div></div></div>`).join(''):'<div class="empty">候補が見つかりません。キーワードを変えてください。</div>'}</div>`+
    `<section class="card"><h2>テーマ設計時の確認ポイント</h2><ul class="check-list"><li>対象構造（柱・梁・骨組・建物）を明確にする</li><li>解析・実験の手法と必要な環境を確認する</li><li>既存研究との違いを本文で比較する</li><li>研究室の指導教員と妥当性を相談する</li></ul></section>`;
  }
  function renderPlan(){
    ensurePlan();const done=state.plan.filter(x=>x.done).length;
    root.innerHTML=head('研究スケジュール','研究開始日を基準に作る一般的な研究進行テンプレートです。田嶋研究室の実際のゼミ・中間発表・提出締切を示すものではありません。')+
    `<div class="notice" id="planNotice">以下の日付はすべて仮予定です（田嶋研究室の公式日程ではありません）。研究室の公式日程が分かったら置き換えてください。</div>`+
    `<section class="card"><div class="card-head"><h2>研究進行タスク</h2><span class="chip" id="planProgress">${done}/${state.plan.length} 完了</span></div>${progRows([{name:'進捗',value:done,total:state.plan.length}])}<ol class="plan-list" style="margin-top:16px">${state.plan.map((s,i)=>`<li class="milestone ${s.done?'done':''}"><span class="ms-num">${i+1}</span><span class="ms-title">${E(s.title)}</span><input class="field ms-date" type="date" data-date-id="${E(s.id)}" value="${E(s.due)}" aria-label="${E(s.title)} の日付"><label class="check"><input type="checkbox" data-done-id="${E(s.id)}" ${s.done?'checked':''}> 完了</label></li>`).join('')}</ol><p class="note">日付と完了状態は変更すると自動で保存されます。</p></section>`+
    `<section class="card"><h2>テンプレートを作り直す</h2><div class="plan-reset"><div><label class="label" for="planStart">研究開始日</label><input class="field" type="date" id="planStart" value="${E(state.plan[0]?.due||D.localISODate(new Date()))}"></div><button class="btn-outline" data-action="reset-plan">この日から作り直す</button></div><p class="note">現在の予定と進捗は上書きされます。</p></section>`+
    `<section class="card"><h2>研究室の正式な日程について</h2><p class="description">研究室の年間ゼミ予定、卒業論文・修士論文の提出期限、研究テーマ決定時期などは、公開情報だけでは正確に確認できません。指導教員・研究室の配布資料で確認してください。</p></section>`;
  }
  function renderSettings(){
    root.innerHTML=head('設定・使い方','ホーム画面への追加方法、データの保存場所、バックアップについて。')+
    installCard('settings')+
    (desktop?'':(()=>{const ios=`<section class="card"><h2>iPhone（Safari）でホーム画面に追加</h2>${iosSteps}</section>`;const and=`<section class="card"><h2>Android（Chrome）でホーム画面に追加</h2>${androidSteps}</section>`;return isAndroid?and+ios:ios+and})())+
    `<section class="card"><h2>データの保存場所とプライバシー</h2><dl class="kv"><dt>保存先</dt><dd>${E(storageLabel())}</dd><dt>表示モード</dt><dd id="displayMode">${isStandalone()?'ホーム画面のアプリ（standalone）':desktop?'デスクトップアプリ':'ブラウザ'}</dd><dt>使用容量</dt><dd id="storageUse">確認中…</dd><dt>オフライン</dt><dd id="offlineState">確認中…</dd></dl><p class="note">論文PDF・要約メモ・研究計画はこの端末の中だけに保存され、外部のサーバーへ送信されることはありません。アプリはアクセス解析や広告も使用していません。iPhoneでは、Safariで開いたページとホーム画面のアプリで保存場所が別になります（ホーム画面のアプリで使い続けてください）。</p></section>`+
    `<section class="card"><h2>バックアップと復元</h2><p class="description">機種変更やブラウザのデータ削除に備えて、定期的にバックアップしてください。バックアップ（JSON）には書誌・要約メモ・研究計画・PDF本文の検索用テキストが含まれます。<b>PDFファイル本体は含まれません</b>。</p><div class="btn-row"><button class="btn" data-action="export">バックアップを作成</button><button class="btn-outline" data-action="import-json">バックアップから復元</button></div></section>`+
    `<section class="card"><h2>このアプリについて</h2><ul class="check-list"><li>大学・研究室の公式アプリではない、学生による非公式の試作品です</li><li>初期データは公開されている書誌情報52件のみです（論文PDF・個人情報・研究室内部資料は含みません）</li><li>研究結果・結論は自動生成しません。本文を読んだ利用者が記入します</li><li>推薦スコアは検索用の相対値で、学術的な正しさの確率ではありません</li></ul><p class="note">バージョン 0.3（2026年11月）</p></section>`;
    fillSettings();
  }
  async function fillSettings(){
    const use=document.getElementById('storageUse');const off=document.getElementById('offlineState');
    if(use){
      const est=store?await store.estimate():null;
      use.textContent=est&&est.usage!=null?`${(est.usage/1048576).toFixed(1)} MB 使用${est.quota?`（上限の目安 ${Math.round(est.quota/1048576).toLocaleString('ja-JP')} MB）`:''}`:desktop?'PCのディスク容量の範囲':'不明';
    }
    if(off){
      if(desktop)off.textContent='常にオフラインで動作します';
      else if('serviceWorker' in navigator){const reg=await navigator.serviceWorker.getRegistration().catch(()=>null);off.textContent=reg&&reg.active?'利用できます（アプリのファイルを端末に保存済み）':'準備中（一度オンラインで開くと利用できます）'}
      else off.textContent='このブラウザでは利用できません';
    }
  }
  function render(){
    document.querySelectorAll('.nav-item[data-tab],.tab-item[data-tab],.sheet-item[data-tab]').forEach(x=>x.classList.toggle('active',x.dataset.tab===tab));
    const more=document.querySelector('.tab-item[data-action="open-sheet"]');if(more)more.classList.toggle('active',MORE_TABS.includes(tab));
    ({dashboard:renderDashboard,library:renderLibrary,summary:renderSummary,analysis:renderAnalysis,ideas:renderIdeas,plan:renderPlan,settings:renderSettings}[tab]||renderDashboard)();
  }
  async function navigate(next){
    if(!SECTION[next])return;
    if(tab==='summary'&&summaryDirty&&next!=='summary'){const p=P(selectedId);if(p){collectSummary(p);await save();toast('未保存のメモを自動保存しました')}}
    tab=next;closeModal();closeSheet();render();window.scrollTo({top:0,behavior:'instant'});
  }
  function closeModal(){modal.classList.add('hidden');modal.innerHTML=''}
  function openSheet(){sheet.classList.remove('hidden')}
  function closeSheet(){sheet.classList.add('hidden')}

  function showPaper(id){const p=P(id);if(!p)return;selectedId=id;
    const field=(label,value)=>`<div class="key">${E(label)}</div><div class="val">${E(value||'未登録')}</div>`;
    const c=p.pdfMeta?.candidates;
    const candidates=p.isUserAdded&&c?`<div class="candidate-box" id="candidateBox"><div class="label">PDFから抽出した書誌の候補（自動抽出・未確認）</div><div class="info-grid compact">${field('タイトル候補',c.title?`${c.title}　［根拠：${c.titleSource}］`:'')}${field('著者候補',c.authors?.length?`${c.authors.join(' / ')}　［根拠：${c.authorsSource}］`:'')}${field('年候補',c.year?`${c.year}　［根拠：${c.yearSource}］`:'')}</div><button class="btn-outline small" data-action="apply-candidates" data-id="${E(p.id)}">候補を入力欄に反映</button><p class="note">反映後に内容を確認して「書誌情報を保存」を押してください。</p></div>`:'';
    const textInfo=Array.isArray(p.pdfText)?`${p.pdfText.length}ページの本文を端末内で検索可能${p.pdfTextTruncated?'（一部のみ）':''}`:'';
    const sel=(a,b)=>a===b?'selected':'';
    modal.innerHTML=`<div class="modal-card"><div class="modal-top"><div class="chips" style="margin:0">${collectionChip(p)}${statusChip(p)}</div><button class="close-btn" data-action="close-modal" aria-label="閉じる">× 閉じる</button></div><h2 class="modal-title">${E(p.title)}</h2><div class="info-grid">${field('著者',(p.authors||[]).join(' / '))}${field('発表年',p.year+'年')}${field('掲載先',p.venue)}${field('書誌詳細',p.detail)}${field('資料種別',p.documentType)}${field('研究分野',(p.categoryIds||[]).map(id=>D.TAGS[id]?.label).join(' / '))}${field('全文状態',status(p)+(textInfo?' · '+textInfo:''))}${field('本文照合',p.fullTextVerified?'本文確認済み（利用者の申告）':'未確認')}</div><div class="notice cool">論文本文と研究結果・結論の要約は自動で補完していません。題名から読み取れる範囲と、本文で確かめた内容は分けて保存してください。</div>${p.sourceUrl?`<div class="label">情報源（大学公式ページ）</div><div class="source-url">${E(p.sourceUrl)}</div>`:'<div class="label">情報源：自分で取り込んだPDF（公式書誌ではありません）</div>'}<div class="btn-row"><button class="btn small" data-action="paper-summary" data-id="${E(p.id)}">要約・メモを書く</button><button class="btn-outline small" data-action="attach-pdf" data-id="${E(p.id)}">${hasPdf(p)?'PDFを差し替える':'PDFを紐づける'}</button>${hasPdf(p)?`<button class="btn-outline small" data-action="view-pdf" data-id="${E(p.id)}">PDFを表示</button>`:''}${p.pdfPath&&desktop&&!isIdbPath(p)?`<button class="btn-ghost small" data-action="open-pdf" data-id="${E(p.id)}">OSのビューアで開く</button>`:''}${p.sourceUrl?`<button class="btn-ghost small" data-action="open-source" data-url="${E(p.sourceUrl)}">公式情報を開く</button>`:''}</div>${p.isUserAdded?`<hr class="divider"><h3 style="margin:0 0 12px">自分で登録した資料の書誌情報</h3>${candidates}<div class="form-grid"><div><label class="label" for="localTitle">論文タイトル</label><input class="field" id="localTitle" value="${E(p.title)}"></div><div><label class="label" for="localYear">発表年</label><input class="field" type="number" inputmode="numeric" min="1900" max="2100" id="localYear" value="${E(p.year)}"></div><div><label class="label" for="localAuthors">著者（; 区切り）</label><input class="field" id="localAuthors" value="${E((p.authors||[]).join('; '))}"></div><div><label class="label" for="localCategory">主な研究分野</label><select class="field" id="localCategory">${D.CATEGORIES.map(c=>`<option value="${c.id}" ${sel((p.categoryIds||[])[0],c.id)}>${E(c.label)}</option>`).join('')}</select></div><div><label class="label" for="localType">資料種別</label><select class="field" id="localType">${['未分類の論文・資料','学会論文（査読付き）','大会・会議発表','卒業論文','修士論文','博士論文','技術報告・その他'].map(t=>`<option ${sel(p.documentType,t)}>${E(t)}</option>`).join('')}</select></div><div><label class="label" for="localVenue">掲載先・提出先</label><input class="field" id="localVenue" value="${E(p.venue==='ユーザー登録資料'?'':p.venue)}" placeholder="例：コンクリート工学年次論文集"></div></div><div class="btn-row"><button class="btn small" data-action="save-meta" data-id="${E(p.id)}">書誌情報を保存</button><button class="btn-ghost small" data-action="delete-paper" data-id="${E(p.id)}">この資料を削除</button></div>`:''}</div>`;
    modal.classList.remove('hidden');
  }
  function newPaper(name,storedPath='',hash=''){
    const base=String(name||'').replace(/\.pdf$/i,'');
    const normalized=base.replace(/[_-]+/g,' ').trim();
    const p={id:'user-'+Date.now()+'-'+Math.random().toString(36).slice(2,8),title:normalized||'無題のPDF',year:new Date().getFullYear(),authors:[],venue:'ユーザー登録資料',detail:'ローカルPDF',documentType:'未分類の論文・資料',collection:'ユーザー登録',collectionScope:'user',categoryIds:['other'],keywords:[],sourceUrl:'',bibliographyVerified:false,fullTextVerified:false,pdfPath:storedPath,pdfHash:hash,summary:{objective:'',method:'',results:'',conclusion:'',limitations:'',sourcePages:''},memo:'',createdFrom:'user_pdf',isUserAdded:true};
    state.papers.unshift(p);return p;
  }
  // Extracts page text (for local full-text search) and bibliographic suggestions. Never changes
  // the official bibliography of seed records.
  async function indexPdf(p,bytes,fileName){
    if(!window.TajimaPdf)return;
    try{
      const doc=await window.TajimaPdf.open(bytes);
      const ex=await window.TajimaPdf.extract(doc);
      const capped=D.capPageTexts(ex.pages);
      p.pdfText=capped.pages;p.pdfTextTruncated=capped.truncated;p.pdfPages=ex.numPages;
      const textChars=capped.chars;
      if(p.isUserAdded){
        const c=D.pdfCandidates(ex.info,ex.firstPageItems,ex.pages.join('\n'),fileName);
        p.pdfMeta={fileName,extractedAt:new Date().toISOString(),candidates:c,textChars};
        if(c.title&&p.title===String(fileName||'').replace(/\.pdf$/i,'').replace(/[_-]+/g,' ').trim())p.title=c.title;
        if(!p.authors.length&&c.authors.length)p.authors=c.authors;
        if(c.year&&p.year===new Date().getFullYear())p.year=c.year;
        const cats=D.classify(p.title).filter(x=>x!=='other');if(cats.length)p.categoryIds=cats;
      }else p.pdfMeta={fileName,extractedAt:new Date().toISOString(),textChars};
      if(!textChars)toast('PDFから文字を抽出できませんでした（画像だけのPDFは本文検索できません）');
      doc.destroy();
    }catch(e){console.error(e);toast('PDFの解析に失敗しました（表示はできる場合があります）：'+e.message)}
  }
  async function importPdfs(attachId=''){
    if(desktop){
      try{const files=await desktop.importPdfs();if(!files.length)return;
        toast('PDFを解析しています…');
        for(const [i,file] of files.entries()){
          let p=attachId&&i===0?P(attachId):null;
          if(p){p.pdfPath=file.path;p.pdfHash=file.hash;p.fullTextVerified=false}else p=newPaper(file.name,file.path,file.hash);
          try{await indexPdf(p,await desktop.readPdf(file.path),file.name)}catch(e){console.error(e)}
        }
        await save();toast(`${files.length}件のPDFをPC内に保存しました`);
        if(attachId){render();showPaper(attachId)}else{libraryFilter={keyword:'',category:'all',year:'all',collection:'all'};await navigate('library')}
      }catch(e){console.error(e);toast('PDFの取り込みに失敗しました：'+e.message)}
    }else{const input=document.getElementById('pdfInput');input.dataset.attach=attachId;input.click()}
  }
  async function pdfBytes(p){
    if(ephemeralPdfs.has(p.id))return ephemeralPdfs.get(p.id);
    if(isIdbPath(p)){
      if(!store)throw Error('このPDFはスマートフォン/ブラウザで取り込まれたものです。この端末で再度紐づけてください');
      const bytes=await store.pdfGet(p.pdfPath.slice(4));
      if(!bytes)throw Error('PDFデータが見つかりません（ブラウザのデータが削除された可能性があります）。もう一度紐づけてください');
      return bytes;
    }
    if(desktop&&p.pdfPath){
      if(!(await desktop.pdfExists(p.pdfPath)))throw Error('PDFファイルが見つかりません（別のPCから復元したデータの場合は再度紐づけてください）');
      return desktop.readPdf(p.pdfPath);
    }
    if(p.pdfPath)throw Error('このPDFは別の端末（PC）で取り込まれたものです。この端末で再度紐づけてください');
    throw Error('PDFは未登録です');
  }
  // ---- In-app PDF viewer ----
  const view={doc:null,paperId:null,page:1,scale:1.25,busy:false};
  async function openViewer(id,page=1){
    const p=P(id);if(!p)return;
    try{
      const bytes=await pdfBytes(p);
      if(view.doc){view.doc.destroy();view.doc=null}
      view.doc=await window.TajimaPdf.open(bytes);view.paperId=id;view.page=Math.min(Math.max(1,Number(page)||1),view.doc.numPages);view.scale=1.25;
      viewer.innerHTML=`<div class="viewer-card"><div class="viewer-bar"><div class="viewer-title" title="${E(p.title)}">${E(p.title)}</div><div class="viewer-controls"><button class="vbtn" data-action="pdf-prev" aria-label="前のページ">‹</button><input id="pdfPageInput" type="number" inputmode="numeric" min="1" max="${view.doc.numPages}" value="${view.page}" aria-label="ページ番号"><span class="viewer-meta" id="pdfPageCount">/ ${view.doc.numPages}</span><button class="vbtn" data-action="pdf-next" aria-label="次のページ">›</button><button class="vbtn" data-action="pdf-zoom-out" aria-label="縮小">−</button><span class="viewer-meta" id="pdfZoom">${Math.round(view.scale*100)}%</span><button class="vbtn" data-action="pdf-zoom-in" aria-label="拡大">＋</button><button class="vbtn primary" data-action="pdf-cite">根拠ページに追加</button>${desktop&&p.pdfPath&&!isIdbPath(p)?'<button class="vbtn" data-action="open-pdf" data-id="'+E(p.id)+'">OSで開く</button>':''}<button class="vbtn" data-action="close-viewer">× 閉じる</button></div></div><div class="viewer-body"><canvas id="pdfCanvas"></canvas></div><div class="viewer-foot">PDFはこの端末の中だけで表示しています（外部送信なし）。ページ番号はPDFの物理ページで、論文誌の印刷ページ番号と異なる場合があります。</div></div>`;
      viewer.classList.remove('hidden');
      // Phones / narrow windows: start at "fit to width" so the page is readable without sideways scrolling.
      if(window.innerWidth<820){
        try{const first=await view.doc.getPage(view.page);const w=first.getViewport({scale:1}).width;const avail=(viewer.querySelector('.viewer-body')?.clientWidth||window.innerWidth)-16;view.scale=Math.max(0.4,Math.min(2.5,Math.floor(avail/w*100)/100))}catch(_){/* keep default */}
      }
      await renderViewerPage();
    }catch(e){console.error(e);toast('PDFを表示できません：'+e.message)}
  }
  async function renderViewerPage(){
    if(!view.doc||view.busy)return;view.busy=true;
    try{
      await window.TajimaPdf.render(view.doc,view.page,document.getElementById('pdfCanvas'),view.scale);
      const input=document.getElementById('pdfPageInput');if(input)input.value=view.page;
      const zoom=document.getElementById('pdfZoom');if(zoom)zoom.textContent=Math.round(view.scale*100)+'%';
      viewer.dataset.page=String(view.page);
    }catch(e){console.error(e);toast('ページの描画に失敗しました')}
    finally{view.busy=false}
  }
  function closeViewer(){viewer.classList.add('hidden');viewer.innerHTML='';if(view.doc){view.doc.destroy();view.doc=null}}
  async function citeCurrentPage(){
    const p=P(view.paperId);if(!p)return;
    p.summary=p.summary||{};
    const ref=`p.${view.page}`;
    const parts=String(p.summary.sourcePages||'').split(/[,、]\s*/).map(s=>s.trim()).filter(Boolean);
    if(!parts.includes(ref))parts.push(ref);
    p.summary.sourcePages=parts.join(', ');
    const field=document.getElementById('s-sourcePages');if(field&&selectedId===p.id)field.value=p.summary.sourcePages;
    await save();toast(`根拠ページに ${ref} を追加しました`);
  }
  async function openPdf(p){
    if(ephemeralPdfs.has(p.id)||!desktop){await openViewer(p.id);return}
    if(!p.pdfPath){toast('PDFは未登録です');return}
    try{await desktop.openPdf(p.pdfPath)}catch(e){console.error(e);toast('PDFを開けません：'+e.message)}
  }
  async function shareFile(text,name){
    if(typeof File!=='function'||!navigator.canShare||!navigator.share)return false;
    const file=new File([text],name,{type:'application/json'});
    if(!navigator.canShare({files:[file]}))return false;
    try{await navigator.share({files:[file],title:'田嶋研究室 バックアップ'});toast('バックアップを保存しました（PDF本体は含みません）');return true}
    catch(e){if(e&&e.name==='AbortError')return true;console.warn('[export] share failed',e);return false}
  }
  async function exportData(){
    const text=JSON.stringify({...state,exportedAt:new Date().toISOString(),note:'PDFファイル本体は含まれません。pdfPathは作成した端末でのみ有効です。'},null,2);
    const name='tajima-lab-backup-'+D.localISODate(new Date())+'.json';
    if(desktop){
      try{const where=await desktop.exportBackup(text,name);if(where)toast('バックアップを保存しました（PDF本体は含みません）：'+where)}
      catch(e){toast('書き出しに失敗しました：'+e.message)}
      return;
    }
    // iPhone / Android: share sheet → 「ファイルに保存」/ Googleドライブ など
    const phone=isIOS||isAndroid||((navigator.maxTouchPoints||0)>0&&window.matchMedia&&window.matchMedia('(pointer: coarse)').matches);
    if(phone&&await shareFile(text,name))return;
    const blob=new Blob([text],{type:'application/json'});const u=URL.createObjectURL(blob);const a=document.createElement('a');a.href=u;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),4000);toast('バックアップ（JSON）を保存しました（PDF本体は含みません）');
  }
  async function importJSON(file){
    if(!file)return;
    try{
      const loaded=JSON.parse(await file.text());
      if(!loaded||loaded.schemaVersion!==1||D.validatePapers(loaded.papers).length)throw Error('未対応の形式か不正な論文データです');
      if(!window.confirm(`現在の${state.papers.length}件を、バックアップの${loaded.papers.length}件で置き換えます。よろしいですか？\n（PDFファイル本体はバックアップに含まれません）`))return;
      state={schemaVersion:1,papers:loaded.papers,plan:Array.isArray(loaded.plan)?loaded.plan:[],topic:String(loaded.topic||''),savedAt:null};
      ephemeralPdfs.clear();selectedId=sorted()[0]?.id||null;summaryDirty=false;
      if(await save()){await navigate('dashboard');toast('データを復元しました（PDFファイルは別途必要）')}
    }catch(e){toast('復元失敗：'+e.message)}
  }

  // One delegated click handler; no inline JS in bibliographic records.
  document.addEventListener('click',async e=>{
    if(e.target===modal){closeModal();return}
    if(e.target===viewer){closeViewer();return}
    if(e.target===sheet){closeSheet();return}
    const el=e.target.closest('button[data-tab],button[data-action]');if(!el)return;
    if(el.dataset.tab){await navigate(el.dataset.tab);return}
    const action=el.dataset.action;
    if(['import-pdf','export','import-json'].includes(action))closeSheet();
    if(action==='paper')showPaper(el.dataset.id);
    else if(action==='close-modal')closeModal();
    else if(action==='open-sheet')openSheet();
    else if(action==='close-sheet')closeSheet();
    else if(action==='paper-summary'){if(tab==='summary'&&summaryDirty){const cur=P(selectedId);if(cur){collectSummary(cur);await save()}}selectedId=el.dataset.id;summaryDirty=false;tab='summary';closeModal();render();window.scrollTo({top:0,behavior:'instant'})}
    else if(action==='import-pdf')await importPdfs();
    else if(action==='attach-pdf')await importPdfs(el.dataset.id);
    else if(action==='view-pdf'){closeModal();await openViewer(el.dataset.id,el.dataset.page)}
    else if(action==='open-pdf'){const p=P(el.dataset.id);if(p)await openPdf(p)}
    else if(action==='close-viewer')closeViewer();
    else if(action==='pdf-prev'){if(view.page>1){view.page--;await renderViewerPage()}}
    else if(action==='pdf-next'){if(view.doc&&view.page<view.doc.numPages){view.page++;await renderViewerPage()}}
    else if(action==='pdf-zoom-in'){view.scale=Math.min(4,+(view.scale+0.25).toFixed(2));await renderViewerPage()}
    else if(action==='pdf-zoom-out'){view.scale=Math.max(0.4,+(view.scale-0.25).toFixed(2));await renderViewerPage()}
    else if(action==='pdf-cite')await citeCurrentPage();
    else if(action==='open-source'){if(el.dataset.url)await openExternal(el.dataset.url)}
    else if(action==='export')await exportData();
    else if(action==='import-json')document.getElementById('jsonInput').click();
    else if(action==='example-topic'){const t=document.getElementById('topicInput');if(t){t.value=el.dataset.topic||'';t.focus()}}
    else if(action==='recommend'){state.topic=document.getElementById('topicInput').value.trim();await save();renderIdeas();toast('関連する先行研究を抽出しました')}
    else if(action==='save-summary'){
      const p=P(selectedId);if(!p)return;collectSummary(p);
      if(await save()){summaryDirty=false;renderSummary();toast('要約・研究メモを保存しました')}
    }
    else if(action==='reset-plan'){
      const raw=document.getElementById('planStart')?.value||'';
      if(!/^\d{4}-\d{2}-\d{2}$/.test(raw)){toast('開始日を入力してください');return}
      if(!window.confirm(`開始日 ${raw} で仮スケジュールを作り直します。現在の予定・進捗は上書きされます。よろしいですか？`))return;
      state.plan=D.planTemplate(raw);await save();renderPlan();toast('仮スケジュールを更新しました');
    }
    else if(action==='apply-candidates'){
      const p=P(el.dataset.id);const c=p?.pdfMeta?.candidates;if(!c)return;
      if(c.title)document.getElementById('localTitle').value=c.title;
      if(c.authors?.length)document.getElementById('localAuthors').value=c.authors.join('; ');
      if(c.year)document.getElementById('localYear').value=c.year;
      toast('候補を入力欄に反映しました。確認してから保存してください');
    }
    else if(action==='save-meta'){
      const p=P(el.dataset.id);const title=document.getElementById('localTitle')?.value.trim();const year=Number(document.getElementById('localYear')?.value);const authors=document.getElementById('localAuthors')?.value||'';const category=document.getElementById('localCategory')?.value;const type=document.getElementById('localType')?.value;const venue=document.getElementById('localVenue')?.value.trim();
      if(!p||!p.isUserAdded||!title||!Number.isInteger(year)||year<1900||year>2100||!D.TAGS[category]){toast('入力内容を確認してください');return}
      const others=(p.categoryIds||[]).filter(x=>x!==category);
      Object.assign(p,{title,year,authors:authors.split(/[;；]/).map(v=>v.trim()).filter(Boolean),categoryIds:[category,...others],documentType:type||p.documentType,venue:venue||'ユーザー登録資料'});
      await save();render();showPaper(p.id);toast('書誌情報を保存しました');
    }
    else if(action==='delete-paper'){
      const p=P(el.dataset.id);if(!p||!p.isUserAdded)return;
      if(!window.confirm(`「${p.title}」を削除しますか？要約・メモも削除されます。`))return;
      state.papers=state.papers.filter(x=>x.id!==p.id);ephemeralPdfs.delete(p.id);if(selectedId===p.id)selectedId=sorted()[0]?.id||null;
      await save();await releasePdf(p.pdfPath);closeModal();render();toast('登録資料を削除しました');
    }
    else if(action==='dismiss-install'){lsSet('tajima-install-dismissed','1');render()}
    else if(action==='install-app'){
      if(!deferredInstall){toast('ブラウザのメニューから「アプリをインストール」を選んでください');return}
      deferredInstall.prompt();try{await deferredInstall.userChoice}catch(_){/* ignore */}deferredInstall=null;render();
    }
  });
  document.addEventListener('input',e=>{
    if(e.target.id==='paperSearch'){libraryFilter.keyword=e.target.value;refreshLibraryRows()}
    if(e.target.dataset?.summaryField||e.target.id==='paperMemo')summaryDirty=true;
  });
  document.addEventListener('change',async e=>{
    const target=e.target;
    if(target.id==='categoryFilter'){libraryFilter.category=target.value;refreshLibraryRows()}
    if(target.id==='yearFilter'){libraryFilter.year=target.value;refreshLibraryRows()}
    if(target.id==='collectionFilter'){libraryFilter.collection=target.value;refreshLibraryRows()}
    if(target.id==='fullTextVerified')summaryDirty=true;
    if(target.id==='summaryPaper'){
      if(summaryDirty){const cur=P(selectedId);if(cur){collectSummary(cur);await save();toast('前の論文のメモを自動保存しました')}}
      selectedId=target.value;renderSummary();
    }
    if(target.id==='pdfPageInput'&&view.doc){const n=Math.min(Math.max(1,Number(target.value)||1),view.doc.numPages);view.page=n;await renderViewerPage()}
    if(target.dataset.dateId){const p=state.plan.find(s=>s.id===target.dataset.dateId);if(p&&/^\d{4}-\d{2}-\d{2}$/.test(target.value)){p.due=target.value;await save();toast('仮予定を保存しました')}}
    if(target.dataset.doneId){const p=state.plan.find(s=>s.id===target.dataset.doneId);if(p){p.done=target.checked;await save();renderPlan()}}
  });
  document.getElementById('jsonInput').addEventListener('change',async e=>{await importJSON(e.target.files?.[0]);e.target.value=''});
  document.getElementById('pdfInput').addEventListener('change',async e=>{
    const files=[...(e.target.files||[])].filter(f=>f.name.toLowerCase().endsWith('.pdf')||f.type==='application/pdf');const attach=e.target.dataset.attach||'';
    if(!files.length){e.target.value='';return}
    toast('PDFを解析しています…');
    let sessionOnly=false;
    for(const [i,file] of files.entries()){
      const bytes=new Uint8Array(await file.arrayBuffer());
      let p=attach&&i===0?P(attach):null;
      if(!p)p=newPaper(file.name);else p.fullTextVerified=false;
      let stored=false;
      if(store){
        try{
          const key=await store.digest(bytes);await store.pdfPut(key,bytes,file.name);
          const old=p.pdfPath;p.pdfPath='idb:'+key;p.pdfHash=key;ephemeralPdfs.delete(p.id);stored=true;
          if(old&&old!==p.pdfPath)await releasePdf(old);
        }catch(err){console.error(err);toast(store.isQuota(err)?'端末の保存容量が不足しているためPDFを保存できませんでした':'PDFを端末に保存できませんでした：'+err.message)}
      }
      if(!stored){ephemeralPdfs.set(p.id,bytes);sessionOnly=true}
      await indexPdf(p,bytes,file.name);
    }
    await save();e.target.value='';
    toast(sessionOnly?`${files.length}件取り込みました（PDF本体はこのセッションの間だけ表示できます）`:`${files.length}件のPDFをこの端末に保存しました`);
    if(attach){render();showPaper(attach)}else{libraryFilter={keyword:'',category:'all',year:'all',collection:'all'};await navigate('library')}
  });
  document.addEventListener('keydown',e=>{
    if(e.key==='Escape'){if(!viewer.classList.contains('hidden'))closeViewer();else if(!sheet.classList.contains('hidden'))closeSheet();else closeModal()}
    if(!viewer.classList.contains('hidden')&&e.target.tagName!=='INPUT'){
      if(e.key==='ArrowRight'||e.key==='PageDown')document.querySelector('[data-action=pdf-next]')?.click();
      if(e.key==='ArrowLeft'||e.key==='PageUp')document.querySelector('[data-action=pdf-prev]')?.click();
    }
  });
  // Phones rarely fire beforeunload: save unsaved notes whenever the app goes to the background.
  function flushDirtySummary(){if(tab==='summary'&&summaryDirty){const p=P(selectedId);if(p){collectSummary(p);summaryDirty=false;save()}}}
  document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='hidden')flushDirtySummary()});
  window.addEventListener('pagehide',flushDirtySummary);
  // PDF viewer: swipe left/right to change pages when the page fits the screen.
  let touchX=null;
  viewer.addEventListener('touchstart',e=>{touchX=e.touches.length===1?e.touches[0].clientX:null},{passive:true});
  viewer.addEventListener('touchend',e=>{
    if(touchX===null||!view.doc)return;const dx=e.changedTouches[0].clientX-touchX;touchX=null;
    const body=viewer.querySelector('.viewer-body');if(!body||body.scrollWidth>body.clientWidth+4||Math.abs(dx)<60)return;
    document.querySelector(dx<0?'[data-action=pdf-next]':'[data-action=pdf-prev]')?.click();
  },{passive:true});
  // Install to home screen (Android Chrome / desktop Chrome): keep the prompt for our own button.
  window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();deferredInstall=e;if(tab==='dashboard'||tab==='settings')render()});
  window.addEventListener('appinstalled',()=>{deferredInstall=null;toast('ホーム画面に「田嶋研究室」を追加しました');if(tab==='dashboard'||tab==='settings')render()});
  // Installable web app (PWA): offline cache. Not used by the desktop app (its files are bundled).
  if(!desktop&&'serviceWorker' in navigator&&(location.protocol==='https:'||/^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname))){
    const register=()=>navigator.serviceWorker.register('sw.js').catch(err=>console.warn('[sw] registration failed:',err&&err.message));
    if(document.readyState==='complete')register();else window.addEventListener('load',register);
  }
  load();
})();
