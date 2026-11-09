'use strict';
const {app, BrowserWindow, ipcMain, dialog, shell, Menu} = require('electron');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const seed = require('../data/papers.json');
const {mergeSeed, validatePapers} = require('../src/domain.js');

// Tests and portable use can point the app at a separate profile folder.
if (process.env.TAJIMA_USER_DATA) app.setPath('userData', path.resolve(process.env.TAJIMA_USER_DATA));

const MAX_STATE_BYTES = 64 * 1024 * 1024;
const MAX_PDF_BYTES = 200 * 1024 * 1024;
const statePath = () => path.join(app.getPath('userData'),'tajima-state.json');
const backupPath = () => path.join(app.getPath('userData'),'tajima-state.bak.json');
const pdfDir = () => path.join(app.getPath('userData'),'pdfs');
function newState() {return {schemaVersion:1,papers:structuredClone(seed), plan:[],topic:'',savedAt:null};}

function readStateFile(file) {
  const state = JSON.parse(fs.readFileSync(file,'utf8'));
  if (state.schemaVersion!==1 || !Array.isArray(state.papers) || validatePapers(state.papers).length) throw Object.assign(Error('invalid state'),{code:'EINVALID'});
  return state;
}
function loadState() {
  let state = null; let notice = '';
  try { state = readStateFile(statePath()); }
  catch (err) {
    if (err.code !== 'ENOENT') {
      // Keep the unreadable file for manual recovery instead of silently overwriting it.
      const keep = statePath().replace(/\.json$/, `.corrupt-${Date.now()}.json`);
      try { fs.renameSync(statePath(), keep); } catch (_) { /* ignore */ }
      console.error('[state read error]', err.message, '->', keep);
      try { state = readStateFile(backupPath()); notice = '保存データが破損していたため、直前のバックアップから復元しました。'; }
      catch (_) { notice = '保存データを読み込めなかったため初期データで起動しました（元ファイルは保管済み）。'; }
    }
  }
  if (!state) return {...newState(), notice};
  const merged = mergeSeed(state.papers, seed);
  if (merged.added) { state.papers = merged.papers; notice = (notice ? notice + ' ' : '') + `新しい公開書誌${merged.added}件を追加しました。`; }
  return notice ? {...state, notice} : state;
}
function saveState(payload) {
  if (!payload || payload.schemaVersion!==1 || !Array.isArray(payload.papers) || payload.papers.length>10000) throw Error('Invalid state payload');
  const errors = validatePapers(payload.papers);
  if (errors.length) throw Error('論文データが不正です: ' + errors[0]);
  const {notice, ...clean} = payload;
  const text=JSON.stringify({...clean,savedAt:new Date().toISOString()});
  if (Buffer.byteLength(text)>MAX_STATE_BYTES) throw Error('Metadata store too large');
  const folder=path.dirname(statePath()); fs.mkdirSync(folder,{recursive:true});
  if (fs.existsSync(statePath())) { try { fs.copyFileSync(statePath(), backupPath()); } catch (e) { console.error('[backup copy]', e.message); } }
  const tmp=statePath()+'.tmp'; fs.writeFileSync(tmp,text,'utf8'); fs.renameSync(tmp,statePath());
  return true;
}
function isImportedPDF(file) {
  if (typeof file!=='string') return false;
  const full=path.resolve(file); const root=path.resolve(pdfDir())+path.sep;
  return full.startsWith(root) && path.extname(full).toLowerCase()==='.pdf' && fs.existsSync(full);
}
function createWindow() {
  const win=new BrowserWindow({width:1370,height:900,minWidth:940,minHeight:620,backgroundColor:'#0a1420',title:'Tajima Lab Research Navigator (Unofficial)',webPreferences:{preload:path.join(__dirname,'preload.cjs'),contextIsolation:true,nodeIntegration:false,sandbox:true,webSecurity:true}});
  win.loadFile(path.join(__dirname,'../index.html'));
  win.webContents.setWindowOpenHandler(({url}) => {
    if (/^https:\/\//.test(url)) shell.openExternal(url);
    return {action:'deny'};
  });
  // Never navigate the app window away from the bundled UI.
  win.webContents.on('will-navigate', (e, url) => { if (!url.startsWith('file:')) { e.preventDefault(); if (/^https:\/\//.test(url)) shell.openExternal(url); } });
  return win;
}

if (!app.requestSingleInstanceLock()) {
  // A second copy writing the same JSON store could lose data; focus the first window instead.
  app.quit();
} else {
  app.on('second-instance', () => { const w = BrowserWindow.getAllWindows()[0]; if (w) { if (w.isMinimized()) w.restore(); w.focus(); } });
  app.whenReady().then(()=>{
    if (process.platform !== 'darwin') Menu.setApplicationMenu(Menu.buildFromTemplate([
      {label:'ファイル', submenu:[{label:'データフォルダを開く', click:()=>shell.openPath(app.getPath('userData'))},{type:'separator'},{role:'quit', label:'終了'}]},
      {label:'表示', submenu:[{role:'reload', label:'再読み込み'},{role:'toggleDevTools', label:'開発者ツール'},{type:'separator'},{role:'resetZoom', label:'実際のサイズ'},{role:'zoomIn', label:'拡大'},{role:'zoomOut', label:'縮小'},{type:'separator'},{role:'togglefullscreen', label:'全画面'}]}
    ]));
    ipcMain.handle('state-load',()=>loadState());
    ipcMain.handle('state-save',(_evt,payload)=>saveState(payload));
    ipcMain.handle('app-info',()=>({version:app.getVersion(), userData:app.getPath('userData'), pdfDir:pdfDir(), platform:process.platform}));
    ipcMain.handle('pdf-import',async()=>{
      const choice=await dialog.showOpenDialog({title:'研究論文PDFを取り込む',properties:['openFile','multiSelections'],filters:[{name:'PDF documents',extensions:['pdf']}]});
      if (choice.canceled) return [];
      fs.mkdirSync(pdfDir(),{recursive:true});
      const imported=[];
      for (const file of choice.filePaths) {
        if (path.extname(file).toLowerCase()!=='.pdf') continue;
        if (fs.statSync(file).size > MAX_PDF_BYTES) continue;
        const buf=fs.readFileSync(file);if (buf.subarray(0,5).toString()!=='%PDF-') continue;
        const hash=crypto.createHash('sha256').update(buf).digest('hex');
        const target=path.join(pdfDir(),hash+'.pdf');
        if (!fs.existsSync(target)) fs.copyFileSync(file,target);
        imported.push({name:path.basename(file),path:target,hash,size:buf.length});
      }
      return imported;
    });
    ipcMain.handle('pdf-read',async(_evt,filename)=>{
      if (!isImportedPDF(filename)) throw Error('指定されたPDFはアプリ管理下にありません');
      const buf = fs.readFileSync(filename);
      return new Uint8Array(buf.buffer, buf.byteOffset, buf.byteLength);
    });
    ipcMain.handle('pdf-exists',(_evt,filename)=>isImportedPDF(filename));
    ipcMain.handle('pdf-open',async(_evt,filename)=>{
      if (!isImportedPDF(filename)) throw Error('指定されたPDFはアプリ管理下にありません');
      const message=await shell.openPath(filename);
      if (message) throw Error(message);
      return true;
    });
    ipcMain.handle('backup-export',async(_evt,text,suggested)=>{
      if (typeof text!=='string' || Buffer.byteLength(text) > MAX_STATE_BYTES) throw Error('バックアップが大きすぎます');
      const name = String(suggested||'tajima-lab-backup.json').replace(/[^\w.\-]/g,'_');
      const choice = await dialog.showSaveDialog({title:'バックアップを保存', defaultPath:path.join(app.getPath('documents'), name), filters:[{name:'JSON',extensions:['json']}]});
      if (choice.canceled || !choice.filePath) return '';
      fs.writeFileSync(choice.filePath, text, 'utf8');
      return choice.filePath;
    });
    ipcMain.handle('open-source',(_evt,url)=>{
      if (typeof url!=='string' || !url.startsWith('https://')) throw Error('HTTPS URL only');
      return shell.openExternal(url);
    });
    createWindow();
    app.on('activate',()=>{if(BrowserWindow.getAllWindows().length===0)createWindow();});
  });
  app.on('window-all-closed',()=>{if(process.platform!=='darwin')app.quit();});
}
