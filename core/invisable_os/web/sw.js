// INVISABLE OS service worker — caches the app shell for offline/installable use.
// API calls (/v1, /health) always go to the network so data is never stale.
const CACHE = "invisable-os-v2";
const SHELL = ["./", "index.html", "styles.css", "app.js", "manifest.webmanifest", "icon.svg"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  // Never cache API responses.
  if (url.pathname.startsWith("/v1") || url.pathname === "/health") {
    e.respondWith(fetch(e.request).catch(() => new Response("{}", { headers: { "content-type": "application/json" } })));
    return;
  }
  // Cache-first for the shell.
  e.respondWith(caches.match(e.request).then((hit) => hit || fetch(e.request)));
});
