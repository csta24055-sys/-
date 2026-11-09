// Air Quality Research OS — Service Worker
// ビルド時に vite.config.ts が __VERSION__ と __PRECACHE__ を埋め込む（アプリ本体と公開データを丸ごと事前キャッシュ）
// - アプリ本体: 事前キャッシュから即応答（オフライン起動）。新しい版は利用者が「更新する」を押したときに切り替え
// - サーバー版の /api/ GET: ネットワーク優先、失敗時はキャッシュ
// - 端末内のデータ（IndexedDB）は Service Worker の更新では消えない
const VERSION = '__VERSION__';
const PRECACHE = __PRECACHE__;
const SHELL = 'aqros-shell-' + VERSION;
const RUNTIME = 'aqros-runtime-v1';
const API = 'aqros-api-v2';
const SCOPE = new URL(self.registration.scope).pathname; // 例: '/' または '/aqros/'
const url = (p) => SCOPE + p;

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(SHELL).then((c) => c.addAll(PRECACHE.map(url))));
});
self.addEventListener('message', (e) => { if (e.data === 'skipWaiting') self.skipWaiting(); });
self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k.startsWith('aqros-shell-') && k !== SHELL).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const u = new URL(req.url);
  if (u.origin !== location.origin || !u.pathname.startsWith(SCOPE)) return;
  const rel = u.pathname.slice(SCOPE.length);
  if (rel.startsWith('api/deliverables/')) return; // 大容量の配布ファイルはキャッシュせず、ダウンロード名を保つ
  if (rel.startsWith('api/')) {
    e.respondWith(fetch(req).then((res) => {
      if (res.ok) { const copy = res.clone(); caches.open(API).then((c) => c.put(req, copy)); }
      return res;
    }).catch(() => caches.match(req).then((r) => r || new Response(JSON.stringify({ offline: true }), { status: 503, headers: { 'Content-Type': 'application/json' } }))));
    return;
  }
  if (req.mode === 'navigate') {
    e.respondWith(caches.match(url('index.html'), { cacheName: SHELL }).then((hit) => hit || fetch(req)).catch(() => caches.match(url('index.html'))));
    return;
  }
  e.respondWith(caches.match(req, { ignoreSearch: rel === 'data/seed.json' }).then((hit) => hit || fetch(req).then((res) => {
    if (res.ok && rel.startsWith('deliverables/')) { const copy = res.clone(); caches.open(RUNTIME).then((c) => c.put(req, copy)); }
    return res;
  })));
});
