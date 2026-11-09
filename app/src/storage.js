/* Local persistence for the browser / installed web app / Android & iOS app.
   (The Electron desktop app keeps using its JSON file in userData via IPC.)

   IndexedDB stores the app state and the bytes of imported PDFs, so PDFs and notes survive
   restarts on phones. Falls back to localStorage (state only) when IndexedDB is unavailable.
   Nothing here talks to a network. */
(function(){
  'use strict';
  const DB_NAME = 'tajima-research-navigator';
  const DB_VERSION = 1;
  const LEGACY_KEY = 'tajima-app-state';
  let dbPromise = null;
  let backend = 'indexeddb';

  function openDb() {
    if (dbPromise) return dbPromise;
    dbPromise = new Promise((resolve, reject) => {
      let req;
      try {
        if (!('indexedDB' in window) || !window.indexedDB) throw new Error('IndexedDB is not available');
        req = window.indexedDB.open(DB_NAME, DB_VERSION);
      } catch (e) { reject(e); return; }
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains('kv')) db.createObjectStore('kv');
        if (!db.objectStoreNames.contains('pdfs')) db.createObjectStore('pdfs');
      };
      req.onsuccess = () => {
        const db = req.result;
        db.onversionchange = () => db.close();
        resolve(db);
      };
      req.onerror = () => reject(req.error || new Error('IndexedDB open failed'));
      req.onblocked = () => reject(new Error('IndexedDB is blocked by another tab'));
    });
    dbPromise.catch(() => { dbPromise = null; });
    return dbPromise;
  }
  // Runs fn(store) inside one transaction and resolves with the value of the last request it returns.
  function run(storeName, mode, fn) {
    return openDb().then(db => new Promise((resolve, reject) => {
      const tx = db.transaction(storeName, mode);
      let out;
      const req = fn(tx.objectStore(storeName));
      if (req) req.onsuccess = () => { out = req.result; };
      tx.oncomplete = () => resolve(out);
      tx.onerror = () => reject(tx.error || new Error('IndexedDB transaction failed'));
      tx.onabort = () => reject(tx.error || new Error('IndexedDB transaction aborted'));
    }));
  }
  function readLegacy() {
    try { return JSON.parse(window.localStorage.getItem(LEGACY_KEY) || 'null'); } catch (_) { return null; }
  }

  async function loadState() {
    try {
      const saved = await run('kv', 'readonly', s => s.get('state'));
      if (saved) { backend = 'indexeddb'; return {state: saved, backend}; }
      // One-time migration from the v0.1 browser preview (localStorage).
      const legacy = readLegacy();
      if (legacy) {
        await run('kv', 'readwrite', s => s.put(legacy, 'state'));
        try { window.localStorage.removeItem(LEGACY_KEY); } catch (_) { /* ignore */ }
      }
      backend = 'indexeddb';
      return {state: legacy, backend, migrated: Boolean(legacy)};
    } catch (e) {
      console.warn('[storage] IndexedDB unavailable, using localStorage:', e && e.message);
      backend = 'localStorage';
      return {state: readLegacy(), backend};
    }
  }
  // Keeps the previous version under 'state-prev' (one-generation backup), like the desktop app.
  async function saveState(state) {
    if (backend === 'indexeddb') {
      try {
        await run('kv', 'readwrite', s => {
          const cur = s.get('state');
          cur.onsuccess = () => { if (cur.result) s.put(cur.result, 'state-prev'); s.put(state, 'state'); };
          return null;
        });
        return;
      } catch (e) {
        if (isQuota(e)) throw e;
        console.warn('[storage] IndexedDB write failed, falling back to localStorage:', e && e.message);
        backend = 'localStorage';
      }
    }
    window.localStorage.setItem(LEGACY_KEY, JSON.stringify(state));
  }
  async function loadPreviousState() {
    try { return (await run('kv', 'readonly', s => s.get('state-prev'))) || null; } catch (_) { return null; }
  }
  function isQuota(e) { return /quota/i.test(String(e && (e.name + ' ' + e.message))); }

  // ---- PDF bytes, keyed by SHA-256 (or a random id where crypto.subtle is unavailable) ----
  async function pdfPut(key, bytes, name) {
    const u8 = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
    // Store a plain ArrayBuffer copy (Blob support in IndexedDB differs between WebViews).
    const buf = u8.buffer.slice(u8.byteOffset, u8.byteOffset + u8.byteLength);
    await run('pdfs', 'readwrite', s => s.put({bytes: buf, name: String(name || ''), size: u8.byteLength, addedAt: new Date().toISOString()}, key));
    return key;
  }
  async function pdfGet(key) {
    const rec = await run('pdfs', 'readonly', s => s.get(key));
    return rec && rec.bytes ? new Uint8Array(rec.bytes) : null;
  }
  async function pdfHas(key) {
    try { return Boolean(await run('pdfs', 'readonly', s => s.getKey(key))); } catch (_) { return false; }
  }
  async function pdfDelete(key) { await run('pdfs', 'readwrite', s => s.delete(key)); }
  async function pdfKeys() { return (await run('pdfs', 'readonly', s => s.getAllKeys())) || []; }
  async function digest(bytes) {
    try {
      if (window.crypto && window.crypto.subtle) {
        const h = await window.crypto.subtle.digest('SHA-256', bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes));
        return Array.from(new Uint8Array(h), b => b.toString(16).padStart(2, '0')).join('');
      }
    } catch (_) { /* insecure context (e.g. http://192.168.x.x) */ }
    return 'rnd-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10);
  }
  // Asks the browser not to evict our data under storage pressure (best effort; may be ignored).
  async function requestPersistence() {
    try { if (navigator.storage && navigator.storage.persist) return await navigator.storage.persist(); } catch (_) { /* ignore */ }
    return false;
  }
  async function estimate() {
    try { if (navigator.storage && navigator.storage.estimate) return await navigator.storage.estimate(); } catch (_) { /* ignore */ }
    return null;
  }

  window.TajimaStore = Object.freeze({
    loadState, saveState, loadPreviousState, pdfPut, pdfGet, pdfHas, pdfDelete, pdfKeys, digest,
    requestPersistence, estimate, isQuota, backend: () => backend
  });
})();
