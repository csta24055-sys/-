/* Tajima Lab Research Navigator — locally runnable, dependency-free UI.
   Bibliography = official listings; no fabricated abstracts or outcomes.
*/
(function(){
  'use strict';
  const D=window.TajimaDomain;
  const desktop=window.tajimaDesktop || null;
  const root=document.getElementById('content');
  const modal=document.getElementById('modal');
  const viewer=document.getElementById('viewer');
  const seed=window.TAJIMA_SEED || [];
  const STORAGE_KEY='tajima-app-state';
  let state={schemaVersion:1,papers:structuredClone(seed),plan:[],topic:'',savedAt:null};
  let tab='dashboard';
  let libraryFilter={keyword:'',category:'all',year:'all',collection:'all'};
  let selectedId=seed[0]?.id || null;
  let summaryDirty=false;
  // Browser preview only: PDF bytes live in memory for this session (never written to localStorage).
  const ephemeralPdfs=new Map();
  const SECTION={dashboard:['OVERVIEW','ダッシュボード'],library:['PAPER LIBRARY','論文ライブラリ'],summary:['RESEARCH NOTES','論文要約・ノート'],analysis:['ANALYTICS','研究分布・分析'],ideas:['RESEARCH EXPLORER','新規研究テーマ'],plan:['RESEARCH TIMELINE','研究スケジュール']};
  const E=s=>String(s??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const P=id=>state.papers.find(p=>p.id===id);
  const sorted=()=>[...state.papers].sort((a,b)=>b.year-a.year||a.id.localeCompare(b.id));
  const fmtCount=n=>Number(n||0).toLocaleString('ja-JP');
  const hasPdf=p=>Boolean(p?.pdfPath)||ephemeralPdfs.has(p?.id);
  function toast(msg){const el=document.getElementById('toast');el.textContent=msg;el.classList.add('show');clearTimeout(toast.timeout);toast.timeout=setTimeout(()=>el.classList.remove('show'),3500)}

  async function load(){
    if(desktop){
      try{const loaded=await desktop.load();if(loaded&&Array.isArray(loaded.papers)){const notice=loaded.notice;delete loaded.notice;state=loaded;if(notice)setTimeout(()=>toast(notice),300)}}
      catch(e){console.error(e);toast('保存データの読み込みに失敗しました')}
    }else{
      try{
        const saved=JSON.parse(localStorage.getItem(STORAGE_KEY)||'null');
        if(saved&&saved.schemaVersion===1&&Array.isArray(saved.papers)&&!D.validatePapers(saved.papers).length){
          const merged=D.mergeSeed(saved.papers,seed);state={...saved,papers:merged.papers};
          if(merged.added)setTimeout(()=>toast(`新しい公開書誌${merged.added}件を追加しました`),300);
        }
      }catch(e){console.error(e)}
    }
    if(!Array.isArray(state.plan))state.plan=[];
    if(D.validatePapers(state.papers).length){console.warn('Saved paper validation failed. Falling back to seed.');state.papers=structuredClone(seed)}
    selectedId=sorted()[0]?.id||null;
    document.getElementById('modePill').textContent=desktop?'DESKTOP · LOCAL':'BROWSER · PREVIEW';
    render();
    document.body.dataset.ready='true';
  }
  async function save(){
    try{
      if(desktop){await desktop.save(state);return true}
      try{localStorage.setItem(STORAGE_KEY,JSON.stringify(state))}
      catch(err){
        // Browser storage is small (~5MB). Keep notes/plans and drop the extracted PDF text if needed.
        if(!/quota/i.test(String(err.name)+String(err.message)))throw err;
        const slim={...state,papers:state.papers.map(p=>{const {pdfText,...rest}=p;return rest})};
        localStorage.setItem(STORAGE_KEY,JSON.stringify(slim));
        toast('ブラウザの保存容量が不足したため、PDF本文の検索用テキストは保存しませんでした');
      }
      return true;
    }catch(err){console.error(err);toast('保存に失敗しました：'+err.message);return false}
  }
  function heading(top,title,description,right=''){
    return `<div class="heading-row"><div><p class="eyebrow">${E(top)}</p><h1 class="page-title">${E(title)}</h1><p class="subtitle">${E(description)}</p></div>${right}</div>`;
  }
  function categoryPills(p,limit=3){return (p.categoryIds||[]).slice(0,limit).map(id=>`<span class="category-pill">${E(D.TAGS[id]?.label||id)}</span>`).join('')}
  function status(p){return p?.pdfPath?'PDF登録済み':ephemeralPdfs.has(p?.id)?'PDF仮登録（このセッションのみ）':'全文未登録'}
  function publicBadge(p){return p.collectionScope==='lab'?'<span class="badge">研究室公式掲載</span>':p.collectionScope==='faculty'?'<span class="badge muted">教授の研究業績</span>':'<span class="badge outline">ユーザー登録</span>'}
  function authorsText(p,sep='・'){return (p.authors||[]).length?p.authors.join(sep):'著者未登録'}
  function paperLine(p){return `<div class="paper-item"><div><button class="paper-title paper-title-btn" data-action="paper" data-id="${E(p.id)}">${E(p.title)}</button><div class="meta">${E(authorsText(p))} &nbsp;·&nbsp; ${E(p.venue)}</div><div class="paper-tags">${publicBadge(p)}${categoryPills(p,2)}</div></div><span class="year-pill">${E(p.year)}</span></div>`}
  function barRows(data,maxValue=0){const max=maxValue||Math.max(1,...data.map(x=>x.value));return data.map(x=>`<div class="bar-row"><div class="bar-label">${E(x.name)}</div><div class="bar-bg"><div class="bar-fill" style="width:${Math.max(1,Math.min(100,100*x.value/max))}%;background:${E(x.color||'#64b9aa')}"></div></div><div class="bar-value">${fmtCount(x.value)}</div></div>`).join('')}

  function renderDashboard(){
    const count=D.countByCollection(state.papers);
    const recent=sorted().slice(0,5);
    const summaryCount=state.papers.filter(p=>p.summary?.results?.trim() || p.summary?.conclusion?.trim()).length;
    root.innerHTML=heading('RESEARCH OVERVIEW','研究の蓄積を、次の発見へ。','田嶋教授に関する公開研究業績を検索し、分野の動向と先行研究を一つの画面で探索できます。',`<span class="tagline">● PUBLIC DATA · ${new Date().getFullYear()}</span>`)+
    `<div class="hero"><div><span class="eyebrow">T A J I M A &nbsp; L A B O R A T O R Y</span><h2>RC構造の「なぜ？」を、<br>研究のつながりから解き明かす。</h2><p>耐震性能・地震損傷・補強・時間依存性・新材料など、研究の入口から先行研究まで。公式ページの書誌データから出発する研究ナビゲーターです。</p></div><div class="hero-stamp">RC</div></div>`+
    `<div class="stat-grid"><div class="stat green"><div class="label">登録論文・研究業績</div><strong id="statTotal">${fmtCount(state.papers.length)}</strong><small>書誌データ（全文とは別）</small></div><div class="stat"><div class="label">研究室公式ページ掲載</div><strong>${fmtCount(count.lab)}</strong><small>最近の研究論文リスト</small></div><div class="stat coral"><div class="label">教授業績・共著（追加）</div><strong>${fmtCount(count.faculty)}</strong><small>研究室全体の全成果ではありません</small></div><div class="stat purple"><div class="label">研究結果を入力済み</div><strong>${fmtCount(summaryCount)}</strong><small>未登録の結果は生成しません</small></div></div>`+
    `<div class="two-col"><section class="panel"><div class="panel-head"><h3 class="section-title">新しい研究論文</h3><button class="link-btn" data-tab="library">すべて表示 →</button></div>${recent.map(paperLine).join('')}</section><section class="panel"><div class="panel-head"><h3 class="section-title">研究分野の分布</h3><button class="link-btn" data-tab="analysis">詳しく分析 →</button></div>${barRows(D.countByCategory(state.papers))}<p class="panel-note">※ 1論文が複数分野に該当するため、分野別件数の合計は論文総数を超えることがあります。</p><hr class="divider"><div class="row-between"><span class="meta">研究テーマに迷ったら</span><button class="btn small" data-tab="ideas">先行研究を探す ↗</button></div></section></div>`+
    `<div class="section-title-row"><div><h3 class="section-title">利用時の注意</h3></div></div><div class="notice cool">この試作品は大学・研究室の公式アプリではありません。論文のタイトル・著者・掲載年は公開情報に基づきますが、研究結果・結論の全文要約は本文を確認するまで空欄です。大学や研究室の正式な研究スケジュールも未収録です。</div>`;
  }
  function libraryRows(){
    const papers=D.paperSearch(sorted(),libraryFilter.keyword,libraryFilter.category,libraryFilter.year,libraryFilter.collection);
    const table=papers.map(p=>{
      const pages=libraryFilter.keyword?D.fullTextPages(p,libraryFilter.keyword):[];
      const hits=pages.length?`<div class="fulltext-hits">本文一致：${pages.slice(0,8).map(n=>`<button class="link-btn" data-action="view-pdf" data-id="${E(p.id)}" data-page="${n}">p.${n}</button>`).join(' ')}${pages.length>8?` 他${pages.length-8}ページ`:''}</div>`:'';
      return `<tr data-paper-id="${E(p.id)}"><td><button class="paper-title paper-title-btn" data-action="paper" data-id="${E(p.id)}">${E(p.title)}</button><div class="meta">${E(authorsText(p))}</div>${hits}</td><td>${E(p.year)}</td><td>${categoryPills(p,1)}</td><td>${hasPdf(p)?`<button class="badge badge-btn" data-action="view-pdf" data-id="${E(p.id)}">PDFあり</button>`:'<span class="badge muted">未登録</span>'}</td></tr>`;
    }).join('');
    return {html:table||`<tr><td colspan="4"><div class="empty"><strong>一致する論文がありません</strong>キーワードや絞り込み条件を変更してください。</div></td></tr>`,count:papers.length};
  }
  const countNote=c=>`${fmtCount(c)} 件表示 / ${fmtCount(state.papers.length)} 件登録。教授の共著論文を含みます。研究室の全卒業論文・全修士論文の網羅リストではありません。スペース区切りでAND検索、同義語（例：RC＝鉄筋コンクリート、FEM＝有限要素）にも一致します。`;
  function renderLibrary(){
    const years=[...new Set(state.papers.map(p=>p.year))].sort((a,b)=>b-a);
    const {html,count}=libraryRows();
    root.innerHTML=heading('RESEARCH LIBRARY','論文ライブラリ','公開書誌情報を探す、PDFを登録する、研究概要を記録する。論文本文がないものは「全文未登録」と表示します。取り込んだPDFの本文もこの端末内で検索できます。',`<button class="btn" data-action="import-pdf">＋ PDFを追加</button>`)+
    `<div class="controls"><input class="input search" type="search" id="paperSearch" placeholder="論文タイトル・著者・キーワード・取り込んだPDF本文で検索" value="${E(libraryFilter.keyword)}" aria-label="論文検索"><select class="select" id="categoryFilter" aria-label="研究分野"><option value="all">すべての分野</option>${D.CATEGORIES.map(c=>`<option value="${c.id}" ${libraryFilter.category===c.id?'selected':''}>${E(c.label)}</option>`).join('')}</select><select class="select" id="yearFilter" aria-label="年度"><option value="all">すべての年度</option>${years.map(y=>`<option value="${y}" ${String(libraryFilter.year)===String(y)?'selected':''}>${y}年</option>`).join('')}</select><select class="select" id="collectionFilter" aria-label="資料の出典分類"><option value="all">全資料</option><option value="lab" ${libraryFilter.collection==='lab'?'selected':''}>研究室公式掲載</option><option value="faculty" ${libraryFilter.collection==='faculty'?'selected':''}>教授の研究業績</option><option value="user" ${libraryFilter.collection==='user'?'selected':''}>自分で登録</option></select></div>`+
    `<div class="table-wrap"><table class="paper-table"><thead><tr><th>研究タイトル / 著者</th><th>年度</th><th>主な分野</th><th>本文</th></tr></thead><tbody id="paperRows">${html}</tbody></table></div><p class="count-note" id="paperResultCount">${countNote(count)}</p>`;
  }
  function refreshLibraryRows(){const rows=document.getElementById('paperRows');if(!rows)return;const result=libraryRows();rows.innerHTML=result.html;document.getElementById('paperResultCount').textContent=countNote(result.count)}

  function renderSummary(){
    const p=P(selectedId)||sorted()[0];if(!p){root.innerHTML='<div class="empty">論文がありません</div>';return}selectedId=p.id;summaryDirty=false;
    const f=p.summary||{};
    const field=(key,label,placeholder)=>`<div class="field"><label class="small-label" for="s-${key}">${label}</label><textarea class="textarea" id="s-${key}" data-summary-field="${key}" placeholder="${E(placeholder)}">${E(f[key]||'')}</textarea></div>`;
    const paperOptions=sorted().map(x=>`<option value="${E(x.id)}" ${x.id===p.id?'selected':''}>${E(x.year)}｜${E(x.title.length>54?x.title.slice(0,54)+'…':x.title)}</option>`).join('');
    const pdf=hasPdf(p);
    root.innerHTML=heading('RESEARCH NOTES','論文要約・ノート','研究目的・方法・結果などを本文と照合しながら保存する専用画面。題名だけから結論を自動生成することはありません。')+
    `<div class="panel"><label class="small-label" for="summaryPaper">対象論文を選択</label><select class="select" id="summaryPaper" style="width:100%;margin-bottom:14px">${paperOptions}</select><h3 class="section-title" style="line-height:1.7">${E(p.title)}</h3><p class="meta" style="margin-top:8px">${E(authorsText(p))} · ${E(p.venue)} · ${E(p.year)}</p><div class="paper-tags">${publicBadge(p)}<span class="badge ${p.fullTextVerified?'':'amber'}" id="verifiedBadge">${p.fullTextVerified?'本文確認済み':'本文未確認'}</span><span class="badge ${pdf?'':'muted'}">${E(status(p))}</span></div><div class="row-between" style="margin-top:14px;flex-wrap:wrap"><label class="check" title="${pdf?'':'PDFを紐づけると選択できます'}"><input type="checkbox" id="fullTextVerified" ${p.fullTextVerified?'checked':''} ${pdf?'':'disabled'}> 本文PDFと照合して記入した（利用者の自己申告）</label><span style="display:flex;gap:8px">${pdf?`<button class="btn small secondary" data-action="view-pdf" data-id="${E(p.id)}">PDFを表示</button>`:''}<button class="btn small secondary" data-action="attach-pdf" data-id="${E(p.id)}">PDFを紐づける</button></span></div></div>`+
    `<div class="content-section notice">重要：このデータには論文の全文・実証結果が含まれていません。「研究目的・結果・結論」はPDFを読んでから記入してください。入力内容の正確性は利用者が確認する必要があります。PDFビューアの「根拠ページに追加」で参照ページを記録できます。</div>`+
    `<div class="panel"><div class="panel-head"><h3 class="section-title">本文確認ノート</h3><button class="btn small" data-action="save-summary">内容を保存</button></div><div class="edit-grid">${field('objective','研究目的','論文中に明記された目的を記入')}${field('method','方法・解析条件','FEM・実験など、本文で確認した方法を記入')}${field('results','研究結果','数値・条件とあわせて事実のみ記入')}${field('conclusion','結論','著者の結論を原文と照合して要約')}${field('limitations','研究の限界・今後の課題','本文の記載と自身の推測を分けて記入')}${field('sourcePages','根拠ページ・図表番号','例：p.4, 図3（本文を入手後に記入）')}</div><hr class="divider"><label class="small-label" for="paperMemo">自分用の読書メモ</label><textarea class="textarea" id="paperMemo" placeholder="関連研究とのつながり、確認したい点など">${E(p.memo||'')}</textarea><div class="row-between" style="margin-top:14px"><span class="meta" id="summaryStatus">保存先：${desktop?'PC内のアプリデータ':'このブラウザのローカルストレージ'}${p.summaryUpdatedAt?` · 最終保存 ${E(new Date(p.summaryUpdatedAt).toLocaleString('ja-JP'))}`:''}</span><button class="btn" data-action="save-summary">要約・ノートを保存</button></div></div>`;
  }
  function collectSummary(p){
    p.summary=p.summary||{};
    document.querySelectorAll('[data-summary-field]').forEach(field=>p.summary[field.dataset.summaryField]=field.value);
    const memo=document.getElementById('paperMemo');if(memo)p.memo=memo.value;
    const verified=document.getElementById('fullTextVerified');if(verified)p.fullTextVerified=Boolean(verified.checked&&hasPdf(p));
    p.summaryUpdatedAt=new Date().toISOString();
  }
  function renderAnalysis(){
    const years=D.countByYear(state.papers);const categories=D.countByCategory(state.papers);const count=D.countByCollection(state.papers);
    const yearNums=years.map(y=>Number(y.name)).filter(Number.isFinite);
    const yearSum=years.reduce((s,y)=>s+y.value,0);
    root.innerHTML=heading('RESEARCH ANALYTICS','研究分布・分析','現在登録されている書誌データだけを集計します。実際の研究室全体の研究件数や重要度を示すものではありません。')+
    `<div class="stat-grid"><div class="stat green"><div class="label">集計対象論文</div><strong>${state.papers.length}</strong><small>メタデータ登録件数</small></div><div class="stat"><div class="label">集計年度数</div><strong>${years.length}</strong><small>${yearNums.length?`${Math.min(...yearNums)}年〜${Math.max(...yearNums)}年`:'—'}</small></div><div class="stat coral"><div class="label">研究室掲載</div><strong>${count.lab}</strong><small>限定公開リストとは別</small></div><div class="stat purple"><div class="label">PDF登録済み</div><strong>${state.papers.filter(hasPdf).length}</strong><small>ローカルPDF</small></div></div>`+
    `<div class="two-col"><section class="panel"><div class="panel-head"><h3 class="section-title">研究分野別分布</h3><span class="tagline">複数分類あり</span></div>${barRows(categories)}<p class="panel-note" id="categoryNote">分類は論文タイトルをもとに付与した暫定タグです。複数分野の重複計上があるため、合計件数（${categories.reduce((s,c)=>s+c.value,0)}）と論文総数（${state.papers.length}）は一致しません。</p></section><section class="panel"><div class="panel-head"><h3 class="section-title">年度別の登録件数</h3><span class="tagline">書誌情報ベース</span></div>${barRows(years)}<p class="panel-note" id="yearNote">年度別合計 <b id="yearSum">${yearSum}</b> 件 ＝ 登録件数 ${state.papers.length} 件。このデータセットには2012～2025年の一部の著作を含みます。全年度・全論文を網羅しません。</p></section></div>`+
    `<div class="section-title-row"><h3 class="section-title">データの出典と範囲</h3></div><div class="panel"><ul class="list-check"><li>研究室公式サイトの「最近の研究論文」6件</li><li>日本大学研究者情報の田嶋教授の業績（共著を含む）46件</li><li>公開書誌情報を対象。各論文の本文PDFおよび研究結果は未収録</li><li>研究室の所属学生による卒業論文・修士論文を網羅した資料ではない</li></ul></div>`;
  }
  function renderIdeas(){
    const topic=state.topic||'旧耐震基準のRC造ピロティ建物の柱崩壊と耐震補強';
    const output=D.recommend(state.papers,topic,8);
    const cats=D.classify(topic);
    root.innerHTML=heading('RESEARCH EXPLORER','新規研究テーマを探る','研究テーマの候補を入力すると、既登録の論文から関連しそうな先行研究を説明付きで提示します。独自の検索スコアであり、研究の新規性・採択可能性は判定しません。')+
    `<section class="panel"><label class="small-label" for="topicInput">研究テーマ・気になる技術を入力</label><textarea class="textarea" id="topicInput" style="min-height:92px" placeholder="例：旧耐震基準のRCピロティ建物の柱崩壊とCFRP補強">${E(topic)}</textarea><div class="row-between" style="margin-top:13px"><span class="meta">例：「DFRCC 梁 非線形FEM解析」「火災後 RC柱 耐震性能」</span><button class="btn" data-action="recommend">関連論文を検索 ↗</button></div></section>`+
    `<div class="two-col content-section"><section class="panel"><div class="panel-head"><h3 class="section-title">推定される関連分野</h3><span class="badge amber">自動分類・暫定</span></div><div class="paper-tags">${cats.map(id=>`<span class="category-pill">${E(D.TAGS[id]?.label)}</span>`).join('')}</div><p class="description">以下の候補は、登録済み論文の題名・分類タグ・同義語辞書、および自分で取り込んだPDFの本文テキストを使って検索したものです。論文の研究結果を読んで判断したランキングではありません。</p></section><section class="panel"><div class="panel-head"><h3 class="section-title">テーマ設計時の確認ポイント</h3></div><ul class="list-check"><li>対象構造（柱・梁・骨組・建物）の明確化</li><li>解析・実験の手法と必要な環境</li><li>既存研究との違いを本文で比較</li><li>研究室の指導教員と妥当性を相談</li></ul></section></div>`+
    `<div class="section-title-row"><h3 class="section-title">先行研究の候補 <span class="meta" id="recommendCount">${output.length}件</span></h3><span class="tagline">関連度は検索用の相対指標</span></div><section class="panel" id="recommendList">${output.length?output.map(x=>`<div class="recommend-row"><div class="row-between"><div style="min-width:0"><button class="paper-title paper-title-btn" data-action="paper" data-id="${E(x.paper.id)}">${E(x.paper.title)}</button><div class="meta">${E(x.paper.year)} · ${E(x.paper.venue)}</div><div class="paper-tags">${categoryPills(x.paper,3)}</div><p class="panel-note recommend-reason">${E(x.reasons.join(' / '))}</p></div><div class="score">${x.score}<small>検索スコア</small></div></div></div>`).join(''):'<div class="empty">候補が見つかりません。キーワードを変えてください。</div>'}</section>`;
  }
  function renderPlan(){
    if(!state.plan.length){state.plan=D.planTemplate();save();}
    root.innerHTML=heading('RESEARCH TIMELINE','研究スケジュール','研究開始日を基準に作る一般的な研究進行テンプレートです。田嶋研究室の実際のゼミ・中間発表・提出締切を示すものではありません。',`<div class="plan-reset"><label class="small-label" for="planStart">開始日</label><input class="input small-input" type="date" id="planStart" value="${E(state.plan[0]?.due||D.localISODate(new Date()))}"><button class="btn secondary" data-action="reset-plan">テンプレートを作り直す</button></div>`)+
    `<div class="notice" id="planNotice">以下のすべての日付は仮予定です（田嶋研究室の公式日程ではありません）。研究室の公式日程が判明したら置き換えてください。「作り直す」は現在の予定・進捗を上書きします。</div><div class="panel"><div class="panel-head"><h3 class="section-title">研究進行タスク</h3><span class="tagline" id="planProgress">${state.plan.filter(x=>x.done).length}/${state.plan.length} 完了</span></div>${state.plan.map((step,i)=>`<div class="milestone ${step.done?'done':''}"><div class="timeline-number">${i+1}</div><div class="milestone-name">${E(step.title)}</div><input class="input small-input" type="date" data-date-id="${E(step.id)}" value="${E(step.due)}" aria-label="${E(step.title)} の日付"><label class="check"><input type="checkbox" data-done-id="${E(step.id)}" ${step.done?'checked':''}> 完了</label></div>`).join('')}<div class="row-between" style="margin-top:23px"><span class="meta">日付と完了状態は変更時に自動保存されます</span><button class="btn small" data-action="export">データを書き出す</button></div></div><div class="section-title-row"><h3 class="section-title">研究室の正式な日程について</h3></div><div class="panel"><p class="description">研究室の年間ゼミ予定、卒業論文・修士論文の提出期限、研究テーマ決定時期等は、公開情報だけでは正確に確認できません。指導教員・研究室配布資料で確認したデータを、このアプリの次の版で取り込めるよう拡張してください。</p></div>`;
  }
  function render(){document.getElementById('crumb').textContent=SECTION[tab][0];document.querySelectorAll('[data-tab]').forEach(x=>x.classList.toggle('active',x.classList.contains('nav-item')&&x.dataset.tab===tab));if(tab==='dashboard')renderDashboard();if(tab==='library')renderLibrary();if(tab==='summary')renderSummary();if(tab==='analysis')renderAnalysis();if(tab==='ideas')renderIdeas();if(tab==='plan')renderPlan();}
  async function navigate(next){
    if(!SECTION[next])return;
    if(tab==='summary'&&summaryDirty&&next!=='summary'){const p=P(selectedId);if(p){collectSummary(p);await save();toast('未保存のノートを自動保存しました')}}
    tab=next;closeModal();render();window.scrollTo({top:0,behavior:'instant'});
  }
  function closeModal(){modal.classList.add('hidden');modal.innerHTML=''}

  function showPaper(id){const p=P(id);if(!p)return;selectedId=id;
    const field=(label,value)=>`<div class="key">${E(label)}</div><div class="val">${E(value||'未登録')}</div>`;
    const c=p.pdfMeta?.candidates;
    const candidates=p.isUserAdded&&c?`<div class="candidate-box" id="candidateBox"><div class="small-label">PDFから抽出した書誌の候補（自動抽出・未確認）</div><div class="info-grid compact">${field('タイトル候補',c.title?`${c.title}　［根拠：${c.titleSource}］`:'')}${field('著者候補',c.authors?.length?`${c.authors.join(' / ')}　［根拠：${c.authorsSource}］`:'')}${field('年候補',c.year?`${c.year}　［根拠：${c.yearSource}］`:'')}</div><button class="btn small secondary" data-action="apply-candidates" data-id="${E(p.id)}">候補を下の入力欄に反映</button><span class="meta"> 反映後に内容を確認して「書誌情報を保存」を押してください。</span></div>`:'';
    const textInfo=Array.isArray(p.pdfText)?`${p.pdfText.length}ページの本文テキストを端末内に索引化${p.pdfTextTruncated?'（一部のみ）':''}`:'';
    modal.innerHTML=`<div class="modal-card"><div class="row-between"><div class="paper-tags">${publicBadge(p)}<span class="badge ${hasPdf(p)?'':'amber'}">${E(status(p))}</span></div><button class="close-btn" data-action="close-modal" aria-label="閉じる">× 閉じる</button></div><h2 class="modal-title">${E(p.title)}</h2><div class="info-grid">${field('著者',(p.authors||[]).join(' / '))}${field('発表年',p.year+'年')}${field('掲載先',p.venue)}${field('書誌詳細',p.detail)}${field('資料種別',p.documentType)}${field('研究分野',(p.categoryIds||[]).map(id=>D.TAGS[id]?.label).join(' / '))}${field('全文状態',status(p)+(textInfo?' · '+textInfo:''))}${field('本文照合',p.fullTextVerified?'本文確認済み（利用者の申告）':'未確認')}</div><div class="notice cool">論文本文と結果・結論の要約は自動補完していません。タイトルから読み取れる範囲と、本文から確かめた内容は分けて保存してください。</div>${p.sourceUrl?`<div class="small-label">情報源（大学公式ページ）</div><div class="source-url">${E(p.sourceUrl)}</div>`:'<div class="small-label">情報源：ユーザーが取り込んだローカルPDF（公式書誌ではありません）</div>'}<div class="modal-footer"><button class="btn small" data-action="paper-summary" data-id="${E(p.id)}">要約・ノートを編集</button><button class="btn small secondary" data-action="attach-pdf" data-id="${E(p.id)}">${hasPdf(p)?'PDFを差し替える':'PDFを紐づける'}</button>${hasPdf(p)?`<button class="btn small secondary" data-action="view-pdf" data-id="${E(p.id)}">PDFを表示</button>`:''}${p.pdfPath&&desktop?`<button class="btn small ghost" data-action="open-pdf" data-id="${E(p.id)}">OSのビューアで開く</button>`:''}${p.sourceUrl?`<button class="btn small ghost" data-action="open-source" data-url="${E(p.sourceUrl)}">公式情報を開く</button>`:''}</div>${p.isUserAdded?`<hr class="divider"><div class="section-title" style="margin-bottom:15px">ユーザー登録資料の書誌情報を編集</div>${candidates}<div class="edit-grid"><div><label class="small-label" for="localTitle">論文タイトル</label><input class="input" style="width:100%" id="localTitle" value="${E(p.title)}"></div><div><label class="small-label" for="localYear">発表年</label><input class="input" style="width:100%" type="number" min="1900" max="2100" id="localYear" value="${E(p.year)}"></div><div><label class="small-label" for="localAuthors">著者（; 区切り）</label><input class="input" style="width:100%" id="localAuthors" value="${E((p.authors||[]).join('; '))}"></div><div><label class="small-label" for="localCategory">主な研究分野</label><select class="select" id="localCategory" style="width:100%">${D.CATEGORIES.map(c=>`<option value="${c.id}" ${(p.categoryIds||[])[0]===c.id?'selected':''}>${E(c.label)}</option>`).join('')}</select></div><div><label class="small-label" for="localType">資料種別</label><select class="select" id="localType" style="width:100%">${['未分類の論文・資料','学会論文（査読付き）','大会・会議発表','卒業論文','修士論文','博士論文','技術報告・その他'].map(t=>`<option ${p.documentType===t?'selected':''}>${E(t)}</option>`).join('')}</select></div><div><label class="small-label" for="localVenue">掲載先・提出先</label><input class="input" style="width:100%" id="localVenue" value="${E(p.venue==='ユーザー登録資料'?'':p.venue)}" placeholder="例：コンクリート工学年次論文集"></div></div><button class="btn small secondary" style="margin-top:15px" data-action="save-meta" data-id="${E(p.id)}">書誌情報を保存</button> <button class="btn small ghost" style="margin-top:15px" data-action="delete-paper" data-id="${E(p.id)}">この登録資料を削除</button>`:''}</div>`;
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
      if(!textChars)toast('PDFから文字を抽出できませんでした（画像のみのPDFはOCRが必要です）');
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
    if(desktop&&p.pdfPath){
      if(!(await desktop.pdfExists(p.pdfPath)))throw Error('PDFファイルが見つかりません（別のPCから復元したデータの場合は再度紐づけてください）');
      return desktop.readPdf(p.pdfPath);
    }
    throw Error(desktop?'PDFは未登録です':'ブラウザプレビューではPDF本体を再起動後に保持しません。再度取り込んでください');
  }
  // ---- In-app PDF viewer ----
  const view={doc:null,paperId:null,page:1,scale:1.25,busy:false};
  async function openViewer(id,page=1){
    const p=P(id);if(!p)return;
    try{
      const bytes=await pdfBytes(p);
      if(view.doc){view.doc.destroy();view.doc=null}
      view.doc=await window.TajimaPdf.open(bytes);view.paperId=id;view.page=Math.min(Math.max(1,Number(page)||1),view.doc.numPages);
      viewer.innerHTML=`<div class="viewer-card"><div class="viewer-bar"><div class="viewer-title" title="${E(p.title)}">${E(p.title)}</div><div class="viewer-controls"><button class="btn small ghost" data-action="pdf-prev" aria-label="前のページ">‹</button><input class="input small-input" id="pdfPageInput" type="number" min="1" max="${view.doc.numPages}" value="${view.page}" aria-label="ページ番号"><span class="meta" id="pdfPageCount">/ ${view.doc.numPages}</span><button class="btn small ghost" data-action="pdf-next" aria-label="次のページ">›</button><button class="btn small ghost" data-action="pdf-zoom-out" aria-label="縮小">−</button><span class="meta" id="pdfZoom">${Math.round(view.scale*100)}%</span><button class="btn small ghost" data-action="pdf-zoom-in" aria-label="拡大">＋</button><button class="btn small secondary" data-action="pdf-cite">根拠ページに追加</button>${desktop&&p.pdfPath?'<button class="btn small ghost" data-action="open-pdf" data-id="'+E(p.id)+'">OSで開く</button>':''}<button class="close-btn" data-action="close-viewer">× 閉じる</button></div></div><div class="viewer-body"><canvas id="pdfCanvas"></canvas></div><div class="viewer-foot meta">PDFはこの端末内だけで表示しています（外部送信なし）。ページ番号はPDFの物理ページで、論文誌の印刷ページ番号と異なる場合があります。</div></div>`;
      viewer.classList.remove('hidden');
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
  async function exportData(){
    const text=JSON.stringify({...state,exportedAt:new Date().toISOString(),note:'PDFファイル本体は含まれません。pdfPathは作成したPCでのみ有効です。'},null,2);
    const name='tajima-lab-backup-'+D.localISODate(new Date())+'.json';
    if(desktop){
      try{const where=await desktop.exportBackup(text,name);if(where)toast('バックアップを保存しました（PDF本体は含みません）：'+where)}
      catch(e){toast('書き出しに失敗しました：'+e.message)}
      return;
    }
    const blob=new Blob([text],{type:'application/json'});const u=URL.createObjectURL(blob);const a=document.createElement('a');a.href=u;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),2000);toast('バックアップJSONを出力しました（PDF本体は含みません）');
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

  // One delegated click handler; no inline JS in downloaded bibliographic records.
  document.addEventListener('click',async e=>{
    if(e.target===modal){closeModal();return}
    if(e.target===viewer){closeViewer();return}
    const el=e.target.closest('button[data-tab],button[data-action]');if(!el)return;
    if(el.dataset.tab){await navigate(el.dataset.tab);return}
    const action=el.dataset.action;
    if(action==='paper')showPaper(el.dataset.id);
    else if(action==='close-modal')closeModal();
    else if(action==='paper-summary'){if(tab==='summary'&&summaryDirty){const cur=P(selectedId);if(cur){collectSummary(cur);await save()}}selectedId=el.dataset.id;summaryDirty=false;tab='summary';closeModal();render();window.scrollTo({top:0,behavior:'instant'})}
    else if(action==='import-pdf')await importPdfs();
    else if(action==='attach-pdf')await importPdfs(el.dataset.id);
    else if(action==='view-pdf'){closeModal();await openViewer(el.dataset.id,el.dataset.page)}
    else if(action==='open-pdf'){const p=P(el.dataset.id);if(p)await openPdf(p)}
    else if(action==='close-viewer')closeViewer();
    else if(action==='pdf-prev'){if(view.page>1){view.page--;await renderViewerPage()}}
    else if(action==='pdf-next'){if(view.doc&&view.page<view.doc.numPages){view.page++;await renderViewerPage()}}
    else if(action==='pdf-zoom-in'){view.scale=Math.min(4,+(view.scale+0.25).toFixed(2));await renderViewerPage()}
    else if(action==='pdf-zoom-out'){view.scale=Math.max(0.5,+(view.scale-0.25).toFixed(2));await renderViewerPage()}
    else if(action==='pdf-cite')await citeCurrentPage();
    else if(action==='open-source'){if(el.dataset.url){if(desktop)await desktop.openSource(el.dataset.url);else window.open(el.dataset.url,'_blank','noopener,noreferrer')}}
    else if(action==='export')await exportData();
    else if(action==='import-json')document.getElementById('jsonInput').click();
    else if(action==='recommend'){state.topic=document.getElementById('topicInput').value.trim();await save();renderIdeas();toast('関連する先行研究を抽出しました')}
    else if(action==='save-summary'){
      const p=P(selectedId);if(!p)return;collectSummary(p);
      if(await save()){summaryDirty=false;renderSummary();toast('論文要約・読書メモを保存しました')}
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
      if(!window.confirm(`「${p.title}」を削除しますか？要約・メモも削除されます（PC内のPDFファイル自体は残ります）。`))return;
      state.papers=state.papers.filter(x=>x.id!==p.id);ephemeralPdfs.delete(p.id);if(selectedId===p.id)selectedId=sorted()[0]?.id||null;
      await save();closeModal();render();toast('登録資料を削除しました');
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
      if(summaryDirty){const cur=P(selectedId);if(cur){collectSummary(cur);await save();toast('前の論文のノートを自動保存しました')}}
      selectedId=target.value;renderSummary();
    }
    if(target.id==='pdfPageInput'&&view.doc){const n=Math.min(Math.max(1,Number(target.value)||1),view.doc.numPages);view.page=n;await renderViewerPage()}
    if(target.dataset.dateId){const p=state.plan.find(s=>s.id===target.dataset.dateId);if(p&&/^\d{4}-\d{2}-\d{2}$/.test(target.value)){p.due=target.value;await save();toast('仮予定を保存しました')}}
    if(target.dataset.doneId){const p=state.plan.find(s=>s.id===target.dataset.doneId);if(p){p.done=target.checked;await save();renderPlan()}}
  });
  document.getElementById('jsonInput').addEventListener('change',async e=>{await importJSON(e.target.files?.[0]);e.target.value=''});
  document.getElementById('pdfInput').addEventListener('change',async e=>{
    const files=[...(e.target.files||[])].filter(f=>f.name.toLowerCase().endsWith('.pdf'));const attach=e.target.dataset.attach||'';
    if(!files.length){e.target.value='';return}
    toast('PDFを解析しています…');
    for(const [i,file] of files.entries()){
      const bytes=new Uint8Array(await file.arrayBuffer());
      let p=attach&&i===0?P(attach):null;
      if(!p)p=newPaper(file.name);
      ephemeralPdfs.set(p.id,bytes);
      await indexPdf(p,bytes,file.name);
    }
    await save();e.target.value='';toast(`${files.length}件取り込みました。ブラウザプレビューのPDF本体は再起動後に保持されません。`);
    if(attach){render();showPaper(attach)}else{libraryFilter={keyword:'',category:'all',year:'all',collection:'all'};await navigate('library')}
  });
  document.addEventListener('keydown',e=>{
    if(e.key==='Escape'){if(!viewer.classList.contains('hidden'))closeViewer();else closeModal()}
    if(!viewer.classList.contains('hidden')&&e.target.tagName!=='INPUT'){
      if(e.key==='ArrowRight'||e.key==='PageDown')document.querySelector('[data-action=pdf-next]')?.click();
      if(e.key==='ArrowLeft'||e.key==='PageUp')document.querySelector('[data-action=pdf-prev]')?.click();
    }
  });
  window.addEventListener('beforeunload',()=>{if(tab==='summary'&&summaryDirty){const p=P(selectedId);if(p){collectSummary(p);if(!desktop)try{localStorage.setItem(STORAGE_KEY,JSON.stringify(state))}catch(_){}else desktop.save(state)}}});
  load();
})();
