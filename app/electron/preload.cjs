'use strict';
const {contextBridge,ipcRenderer}=require('electron');
contextBridge.exposeInMainWorld('tajimaDesktop', Object.freeze({
  load:()=>ipcRenderer.invoke('state-load'),
  save:state=>ipcRenderer.invoke('state-save',state),
  info:()=>ipcRenderer.invoke('app-info'),
  importPdfs:()=>ipcRenderer.invoke('pdf-import'),
  readPdf:pdfPath=>ipcRenderer.invoke('pdf-read',pdfPath),
  pdfExists:pdfPath=>ipcRenderer.invoke('pdf-exists',pdfPath),
  openPdf:pdfPath=>ipcRenderer.invoke('pdf-open',pdfPath),
  exportBackup:(text,name)=>ipcRenderer.invoke('backup-export',text,name),
  openSource:url=>ipcRenderer.invoke('open-source',url)
}));
