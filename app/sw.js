/* Offline cache for the installable web app (PWA). Not used by the desktop or phone apps.
   Cache-first: everything the app needs is cached on install, so it opens without a network.
   VERSION and CORE are rewritten by tools/build_web.cjs (content hash + file list) for each deploy,
   so phones pick up new files automatically and old caches are deleted. */
'use strict';
const VERSION = 'dev';
const CACHE = 'tajima-navigator-' + VERSION;
const CORE = [/*CORE_START*/
  './',
  'styles.css',
  'manifest.webmanifest',
  'src/domain.js',
  'src/storage.js',
  'src/pdf.js',
  'src/app.js',
  'data/seed.js',
  'vendor/pdfjs/pdf.min.js',
  'vendor/pdfjs/pdf.worker.min.js',
  // CMaps most Japanese papers need (others are cached the first time they are used)
  'vendor/pdfjs/cmaps/UniJIS-UCS2-H.bcmap',
  'vendor/pdfjs/cmaps/UniJIS-UCS2-V.bcmap',
  'vendor/pdfjs/cmaps/UniJIS-UTF16-H.bcmap',
  'vendor/pdfjs/cmaps/UniJIS-UTF16-V.bcmap',
  'vendor/pdfjs/cmaps/Adobe-Japan1-UCS2.bcmap',
  'vendor/pdfjs/cmaps/90ms-RKSJ-H.bcmap',
  'vendor/pdfjs/cmaps/90ms-RKSJ-V.bcmap',
  'icons/icon-192.png',
  'icons/icon-512.png',
  'icons/maskable-192.png',
  'icons/maskable-512.png',
  'icons/apple-touch-icon.png',
  'icons/favicon-32.png'
/*CORE_END*/];

// Hosts such as Cloudflare Pages redirect /index.html → /. Browsers refuse a *redirected* response for a page
// navigation, so every precached file is stored as a clean (non-redirected) copy.
async function precache(cache, url) {
  const res = await fetch(url, {cache: 'reload'});
  if (!res.ok) throw new Error(`precache ${url}: HTTP ${res.status}`);
  const clean = res.redirected ? new Response(await res.blob(), {status: res.status, statusText: res.statusText, headers: res.headers}) : res;
  await cache.put(url, clean);
}
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => Promise.all(CORE.map(url => precache(cache, url)))).then(() => self.skipWaiting()));
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k.startsWith('tajima-navigator-') && k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return; // the app never loads third-party resources
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    // Navigations (opening the app) always get the cached shell, so old JS and new HTML never mix.
    const key = req.mode === 'navigate' ? './' : req;
    const hit = await cache.match(key, {ignoreSearch: req.mode === 'navigate'});
    if (hit) return hit;
    try {
      const res = await fetch(req);
      if (res.ok && res.type === 'basic') cache.put(req, res.clone());
      return res;
    } catch (err) {
      if (req.mode === 'navigate') {
        const shell = await cache.match('./');
        if (shell) return shell;
      }
      // Offline and not cached yet: answer cleanly instead of failing the fetch event.
      return new Response('offline', {status: 503, statusText: 'Offline', headers: {'content-type': 'text/plain; charset=utf-8'}});
    }
  })());
});
