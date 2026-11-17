/* Offline shell. Static files: network first (always the current version when the server is reachable), the cache
   only as an offline fallback. API answers are never cached (no stale results). A new version of this file takes
   over at once (skipWaiting / clients.claim) and deletes the caches of earlier versions. */
const V = "wlcstudio-shell-v14";
const SHELL = ["./", "index.html", "style.css", "app.js", "manifest.webmanifest", "assets/door.svg", "assets/akabeko-placeholder.svg",
  "assets/structure-s.svg", "assets/structure-rc.svg", "assets/structure-src.svg", "assets/structure-w.svg"];
self.addEventListener("install", (e) => { self.skipWaiting(); e.waitUntil(caches.open(V).then((c) => c.addAll(SHELL)).catch(() => {})); });
self.addEventListener("activate", (e) => e.waitUntil(
  caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== V).map((k) => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener("fetch", (e) => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET" || u.origin !== self.location.origin || u.pathname.startsWith("/api/")) return;
  e.respondWith(fetch(e.request).then((r) => {
    if (r.ok) { const copy = r.clone(); caches.open(V).then((c) => c.put(e.request, copy)); }
    return r;
  }).catch(() => caches.match(e.request)));
});
