// Service worker: lets the site install and open offline.
//
// Online, every request goes to the network first, so the pages and the data
// files are always current. Each good response is saved. Offline, the saved
// copy is served, so the site opens and shows the last data it loaded.
// Bump VERSION when the list of files below changes.
const VERSION = "v1";
const CACHE = `job-watcher-${VERSION}`;
const SHELL = [
  "./", "index.html", "browse.html", "market.html",
  "style.css", "nav.js", "csv.js", "dedupe.js", "index.js", "browse.js", "market.js",
  "manifest.json", "icons/icon-192.png", "icons/icon-512.png",
  "data/history.csv", "data/status.json",
];

self.addEventListener("install", event => {
  // One missing file (a page not built yet) must not stop the install.
  event.waitUntil(caches.open(CACHE).then(cache =>
    Promise.all(SHELL.map(url => cache.add(url).catch(() => {})))).then(() => self.skipWaiting()));
});

self.addEventListener("activate", event => {
  event.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", event => {
  const req = event.request;
  if (req.method !== "GET" || new URL(req.url).origin !== location.origin) return;
  event.respondWith(
    fetch(req)
      .then(res => {
        if (res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then(cache => cache.put(req, copy));
        }
        return res;
      })
      .catch(() => caches.match(req, { ignoreSearch: true })
        .then(hit => hit || (req.mode === "navigate" ? caches.match("index.html") : undefined))
        .then(hit => hit || Response.error())));
});
