/* Offline shell: static files cache-first, API always from the network (no stale results). */
const V = "wlcstudio-v1";
const SHELL = ["./", "index.html", "style.css", "app.js", "manifest.webmanifest", "assets/door.svg", "assets/akabeko-placeholder.svg",
  "assets/structure-s.svg", "assets/structure-rc.svg", "assets/structure-src.svg", "assets/structure-w.svg"];
self.addEventListener("install", (e) => e.waitUntil(caches.open(V).then((c) => c.addAll(SHELL))));
self.addEventListener("activate", (e) => e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== V).map((k) => caches.delete(k))))));
self.addEventListener("fetch", (e) => {
  const u = new URL(e.request.url);
  if (u.pathname.startsWith("/api/")) return;            // never cache API answers
  e.respondWith(caches.match(e.request).then((r) => r || fetch(e.request)));
});
