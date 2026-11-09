/* Pure, dependency-free research functions shared by browser and Node tests. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.TajimaDomain = api;
})(typeof window !== 'undefined' ? window : null, function () {
  'use strict';
  const CATEGORIES = [
    { id: 'seismic', label: '耐震性能・崩壊', color: '#389a96', hints: ['耐震','地震','崩壊','軸破壊','ピロティ','復元力','耐力','ねじれ','曲げ','seismic','collapse','shear','torsion'] },
    { id: 'damage', label: '地震損傷評価', color: '#6785d5', hints: ['損傷','被災','damage','crack','ひび割れ','損傷指標','残余','損傷スペクトル'] },
    { id: 'retrofit', label: '補修・耐震補強', color: '#c69662', hints: ['補修','補強','ブレース','cfrp','frp','retrofit','耐震改修'] },
    { id: 'time', label: '時間依存・耐久', color: '#9985c7', hints: ['クリープ','収縮','若材齢','時間依存','腐食','火災','加熱','耐久','長期','creep','shrinkage'] },
    { id: 'materials', label: '新材料・数値解析', color: '#cf8180', hints: ['dfrcc','fem','有限要素','有限要素法','非線形','3次元','三次元','数値解析','fiber','ファイバー','モデル','新材料','cfrp','コンクリート','3d'] },
    { id: 'other', label: '関連・横断研究', color: '#8c9ba7', hints: ['施工','支保工','施工荷重','型枠'] }
  ];
  // Small hand-written synonym groups for Japanese/English structural-engineering terms.
  // A query term from one group also matches the other members. This is a retrieval aid only.
  const SYNONYMS = [
    ['rc', '鉄筋コンクリート', 'reinforcedconcrete'],
    ['fem', '有限要素', '有限要素法', 'finiteelement'],
    ['三次元', '3次元', '3d'],
    ['非線形', 'nonlinear'],
    ['補強', '耐震補強', '耐震改修', 'retrofit'],
    ['損傷', 'damage'],
    ['ひび割れ', 'ひび割', 'crack', 'cracking'],
    ['崩壊', 'collapse', '倒壊'],
    ['せん断', 'shear'],
    ['ねじれ', 'torsion'],
    ['クリープ', 'creep'],
    ['乾燥収縮', '収縮', 'shrinkage'],
    ['火災', '加熱', 'fire'],
    ['腐食', '鉄筋腐食', 'corrosion'],
    ['柱', 'column'],
    ['梁', 'はり', 'beam'],
    ['耐震壁', '壁', 'wall'],
    ['ピロティ', 'piloti', 'pilotis'],
    ['地震', 'seismic', 'earthquake']
  ];
  const NORMALIZE = s => String(s == null ? '' : s).normalize('NFKC').toLowerCase().replace(/\s+/g, '');
  const TAGS = Object.fromEntries(CATEGORIES.map(c => [c.id,c]));
  const SYN_NORMALIZED = SYNONYMS.map(group => group.map(NORMALIZE));
  const MAX_TEXT_CHARS_PER_PAPER = 400000;

  function classify(text) {
    const q = NORMALIZE(text);
    const hits = CATEGORIES.filter(c => c.hints.some(h => q.includes(NORMALIZE(h)))).map(c => c.id);
    return hits.length ? hits : ['other'];
  }
  // Returns the alternative spellings of a single (already normalized) term, including itself.
  function expandTerm(term) {
    const t = NORMALIZE(term);
    const out = new Set([t]);
    for (const group of SYN_NORMALIZED) if (group.includes(t)) group.forEach(x => out.add(x));
    return [...out];
  }
  // Space-separated query → list of terms (each term is an OR-group of synonyms; terms are ANDed).
  function queryTerms(keyword) {
    return String(keyword == null ? '' : keyword).normalize('NFKC').split(/[\s、,，;；]+/).map(NORMALIZE).filter(Boolean).map(expandTerm);
  }
  function matchesTerms(text, terms) {
    const t = NORMALIZE(text);
    return terms.every(group => group.some(v => t.includes(v)));
  }
  function countByYear(papers) {
    const tally = {};
    papers.forEach(p => { const y = String(p.year || '不明'); tally[y] = (tally[y] || 0) + 1; });
    return Object.entries(tally).sort((a,b) => String(b[0]).localeCompare(String(a[0]))).map(([name,value]) => ({name,value}));
  }
  function countByCategory(papers) {
    return CATEGORIES.map(c => ({id:c.id,name:c.label,color:c.color,value:papers.filter(p => (p.categoryIds || []).includes(c.id)).length}));
  }
  function countByCollection(papers) {
    return { lab: papers.filter(p => p.collectionScope === 'lab').length, faculty: papers.filter(p => p.collectionScope === 'faculty').length, user: papers.filter(p => p.isUserAdded).length };
  }
  function metaText(p) {
    return [p.title, (p.authors || []).join(' '), p.venue, p.detail, p.memo, (p.keywords || []).join(' '), (p.categoryIds||[]).map(id => TAGS[id]?.label).join(' ')].join(' ');
  }
  // Pages (1-based) of the locally extracted PDF text that contain every query term.
  function fullTextPages(paper, keyword) {
    const terms = queryTerms(keyword);
    if (!terms.length || !Array.isArray(paper?.pdfText)) return [];
    const pages = [];
    paper.pdfText.forEach((txt, i) => { if (matchesTerms(txt, terms)) pages.push(i + 1); });
    return pages;
  }
  function paperSearch(papers, keyword='', category='all', year='all', collection='all') {
    const terms = queryTerms(keyword);
    return papers.filter(p => {
      if (category !== 'all' && !(p.categoryIds || []).includes(category)) return false;
      if (year !== 'all' && String(p.year) !== String(year)) return false;
      if (collection !== 'all' && p.collectionScope !== collection) return false;
      if (!terms.length) return true;
      return matchesTerms(metaText(p), terms) || fullTextPages(p, keyword).length > 0;
    });
  }
  // Explainable retrieval heuristic. Relative relevance score; NEVER probability of correctness/success.
  function recommend(papers, subject, limit=6) {
    const q = NORMALIZE(subject);
    if (!q) return [];
    const inferred = classify(subject).filter(id => id !== 'other');
    const qBigrams = [...new Set(Array.from({length: Math.max(0,q.length-1)},(_,i) => q.slice(i,i+2)).filter(s=>s.length===2))];
    // Synonym groups present in the topic (e.g. "RC" also looks for "鉄筋コンクリート").
    const synGroups = SYN_NORMALIZED.filter(g => g.some(v => v.length >= 2 && q.includes(v)));
    return papers.map(p => {
      const t = NORMALIZE(p.title);
      const tags = p.categoryIds || [];
      const matched = inferred.filter(id => tags.includes(id));
      const common = qBigrams.filter(b => t.includes(b));
      const synHits = synGroups.filter(g => g.some(v => t.includes(v)) && !g.some(v => q.includes(v) && t.includes(v)));
      const titleBonus = (q.length > 3 && t.includes(q)) ? 30 : 0;
      // pages of the user's own imported PDF text that mention at least two of the topic's term groups
      const textPages = Array.isArray(p.pdfText) && synGroups.length ? p.pdfText.map((txt,i) => {
        const n = NORMALIZE(txt); return synGroups.filter(g => g.some(v => n.includes(v))).length >= Math.min(2, synGroups.length) ? i+1 : 0;
      }).filter(Boolean) : [];
      const score = Math.min(99, matched.length * 13 + Math.min(42,common.length * 3) + synHits.length * 4 + titleBonus + (textPages.length ? 6 : 0));
      const reasons = [];
      if (matched.length) reasons.push('分野一致：'+matched.map(id=>TAGS[id]?.label).join('・'));
      if (common.length) reasons.push('題名との文字列一致（'+common.length+'件）');
      if (synHits.length) reasons.push('同義語一致：'+synHits.map(g=>g[0]).join('・'));
      if (textPages.length) reasons.push('取り込んだPDF本文に一致（p.'+textPages.slice(0,5).join(', p.')+'）');
      if (!reasons.length) reasons.push('直接一致を確認できず');
      return {paper:p,score,reasons};
    }).filter(p=>p.score>0).sort((a,b) => b.score-a.score || b.paper.year-a.paper.year).slice(0,limit);
  }
  function localISODate(date) {
    const pad = n => String(n).padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth()+1)}-${pad(date.getDate())}`;
  }
  function planTemplate(start='') {
    const base = start ? new Date(start+'T12:00:00') : new Date();
    if (Number.isNaN(base.getTime())) throw new Error('開始日が不正です');
    const phases = [
      ['問題意識・研究テーマの整理',0],['先行研究の収集と読み込み',2],['研究計画・検証方法の作成',5],['解析・実験環境の準備',8],['予備解析・予備実験',11],['本解析・本実験',15],['データ整理と考察',20],['論文・発表資料の作成',24],['最終レビュー・修正',28]
    ];
    return phases.map(([title,weeks],i) => {
      const date = new Date(base); date.setDate(date.getDate()+7*weeks);
      return {id:'milestone-'+i,title,due:localISODate(date),done:false,note:''};
    });
  }
  function validatePapers(papers) {
    const errors = [];
    if (!Array.isArray(papers)) return ['論文データは配列でなければなりません'];
    const seen = new Set();
    for (const [i,p] of papers.entries()) {
      if (!p || typeof p.id!=='string' || !p.id) errors.push(`papers[${i}]: idがありません`);
      if (!p || typeof p.title!=='string' || !p.title) errors.push(`papers[${i}]: titleがありません`);
      if (!p || !Number.isInteger(Number(p.year)) || Number(p.year)<1900 || Number(p.year)>2100) errors.push(`papers[${i}]: yearが不正です`);
      if (p && !Array.isArray(p.authors)) errors.push(`papers[${i}]: authorsは配列でなければなりません`);
      if (p && seen.has(p.id)) errors.push(`重複ID: ${p.id}`);
      if (p) seen.add(p.id);
      for (const id of (p?.categoryIds || [])) if (!TAGS[id]) errors.push(`未知の分類: ${id}`);
    }
    return errors;
  }
  // Adds bibliography records that exist in a newer seed but not in the saved state.
  // Never overwrites or removes the user's records (notes, PDFs, edits are preserved).
  function mergeSeed(saved, seed) {
    const have = new Set(saved.map(p => p.id));
    const added = seed.filter(p => !have.has(p.id)).map(p => JSON.parse(JSON.stringify(p)));
    return {papers: saved.concat(added), added: added.length};
  }
  // ---- PDF metadata candidates (all results are suggestions for the user to confirm) ----
  function yearCandidate(text) {
    const now = new Date().getFullYear();
    const years = (String(text || '').normalize('NFKC').match(/(?<!\d)(19[5-9]\d|20\d\d)(?!\d)/g) || []).map(Number).filter(y => y <= now + 1);
    if (!years.length) return null;
    const freq = {};
    years.forEach(y => { freq[y] = (freq[y] || 0) + 1; });
    return Number(Object.entries(freq).sort((a,b) => b[1]-a[1] || b[0]-a[0])[0][0]);
  }
  // items: [{str, height, y}] from the first PDF page. Returns the line set in the largest font.
  function titleCandidate(items) {
    const usable = (items || []).filter(it => it && String(it.str || '').trim() && Number(it.height) > 0);
    if (!usable.length) return '';
    const maxH = Math.max(...usable.map(it => Number(it.height)));
    const big = usable.filter(it => Number(it.height) >= maxH * 0.92);
    // keep reading order: top to bottom (PDF y grows upwards), then left to right
    big.sort((a,b) => (Number(b.y)||0) - (Number(a.y)||0) || (Number(a.x)||0) - (Number(b.x)||0));
    const text = big.map(it => String(it.str)).join(' ').replace(/\s+/g, ' ').trim();
    return text.length > 200 ? text.slice(0, 200) : text;
  }
  function splitAuthors(s) {
    return String(s || '').normalize('NFKC').split(/\s*(?:[;；,，、・]|\band\b|\/)\s*/).map(x => x.trim()).filter(x => x && x.length <= 60);
  }
  function pdfCandidates(info, firstPageItems, allText, fileName) {
    const c = {title: '', titleSource: '', authors: [], authorsSource: '', year: null, yearSource: ''};
    const infoTitle = String(info?.Title || '').trim();
    if (infoTitle && !/^(untitled|microsoft word|無題)/i.test(infoTitle) && !/\.(docx?|pdf|tex)$/i.test(infoTitle)) { c.title = infoTitle; c.titleSource = 'PDFメタデータ（Title）'; }
    else { const t = titleCandidate(firstPageItems); if (t) { c.title = t; c.titleSource = '1ページ目の最大文字サイズの行'; } }
    if (!c.title && fileName) { c.title = String(fileName).replace(/\.pdf$/i, '').replace(/[_-]+/g, ' ').trim(); c.titleSource = 'ファイル名'; }
    const infoAuthor = String(info?.Author || '').trim();
    if (infoAuthor) { c.authors = splitAuthors(infoAuthor); c.authorsSource = 'PDFメタデータ（Author）'; }
    const created = String(info?.CreationDate || '').match(/D:(\d{4})/);
    const textYear = yearCandidate(String(allText || '').slice(0, 6000));
    if (textYear) { c.year = textYear; c.yearSource = '本文冒頭に出現する西暦'; }
    else if (created) { c.year = Number(created[1]); c.yearSource = 'PDF作成日（発表年と異なる場合あり）'; }
    return c;
  }
  // Keeps extracted page texts within a size budget so the local JSON store stays small.
  function capPageTexts(pages, maxChars = MAX_TEXT_CHARS_PER_PAPER) {
    const out = []; let total = 0; let truncated = false;
    for (const raw of pages || []) {
      const s = String(raw || '').replace(/\s+/g, ' ').trim();
      if (total + s.length > maxChars) { out.push(s.slice(0, Math.max(0, maxChars - total))); truncated = true; total = maxChars; continue; }
      out.push(s); total += s.length;
    }
    return {pages: out, truncated, chars: total};
  }
  return {CATEGORIES,TAGS,SYNONYMS,NORMALIZE,classify,expandTerm,queryTerms,countByYear,countByCategory,countByCollection,paperSearch,fullTextPages,recommend,planTemplate,localISODate,validatePapers,mergeSeed,yearCandidate,titleCandidate,splitAuthors,pdfCandidates,capPageTexts,MAX_TEXT_CHARS_PER_PAPER};
});
