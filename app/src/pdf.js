/* Local PDF helper built on the vendored PDF.js (app/vendor/pdfjs). Nothing is sent over the network. */
(function(){
  'use strict';
  const here = document.currentScript ? document.currentScript.src : location.href;
  const libUrl = new URL('../vendor/pdfjs/pdf.min.mjs', here).href;
  const workerUrl = new URL('../vendor/pdfjs/pdf.worker.min.mjs', here).href;
  const cMapUrl = new URL('../vendor/pdfjs/cmaps/', here).href;
  const standardFontDataUrl = new URL('../vendor/pdfjs/standard_fonts/', here).href;
  let libPromise = null;
  function lib() {
    if (!libPromise) libPromise = import(libUrl).then(mod => { mod.GlobalWorkerOptions.workerSrc = workerUrl; return mod; });
    return libPromise;
  }
  async function open(bytes) {
    const pdfjs = await lib();
    // PDF.js transfers the buffer to its worker, so always hand over a copy.
    const data = bytes instanceof Uint8Array ? bytes.slice() : new Uint8Array(bytes).slice();
    return pdfjs.getDocument({data, cMapUrl, cMapPacked:true, standardFontDataUrl, isEvalSupported:false, disableAutoFetch:true, useSystemFonts:true}).promise;
  }
  // Returns {info, numPages, firstPageItems:[{str,height,x,y}], pages:[text per page]}
  async function extract(doc, maxPages = 400) {
    let info = {};
    try { info = (await doc.getMetadata())?.info || {}; } catch (_) { info = {}; }
    const pages = []; let firstPageItems = [];
    const n = Math.min(doc.numPages, maxPages);
    for (let i = 1; i <= n; i++) {
      const page = await doc.getPage(i);
      const content = await page.getTextContent();
      if (i === 1) firstPageItems = content.items.filter(it => typeof it.str === 'string').map(it => ({str: it.str, height: it.height || Math.abs(it.transform?.[3] || 0), x: it.transform?.[4] || 0, y: it.transform?.[5] || 0}));
      let text = ''; for (const it of content.items) { if (typeof it.str !== 'string') continue; text += it.str; text += it.hasEOL ? '\n' : ''; }
      pages.push(text);
      page.cleanup();
    }
    return {info, numPages: doc.numPages, firstPageItems, pages};
  }
  async function render(doc, pageNumber, canvas, scale) {
    const page = await doc.getPage(pageNumber);
    const ratio = window.devicePixelRatio || 1;
    const viewport = page.getViewport({scale});
    canvas.width = Math.floor(viewport.width * ratio);
    canvas.height = Math.floor(viewport.height * ratio);
    canvas.style.width = Math.floor(viewport.width) + 'px';
    canvas.style.height = Math.floor(viewport.height) + 'px';
    const task = page.render({canvasContext: canvas.getContext('2d'), viewport, transform: ratio !== 1 ? [ratio,0,0,ratio,0,0] : null});
    await task.promise;
    return {width: viewport.width, height: viewport.height};
  }
  window.TajimaPdf = Object.freeze({open, extract, render, ready: () => lib().then(() => true)});
})();
