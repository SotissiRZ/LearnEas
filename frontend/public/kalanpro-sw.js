const OFFLINE_CACHE = "kalanpro-offline-shell-v2";
const OFFLINE_ASSETS = ["/offline-player.html", "/offline-player.js"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(OFFLINE_CACHE).then((cache) => cache.addAll(OFFLINE_ASSETS.map((url) => new Request(url, { cache: "reload" })))))
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((key) => key.startsWith("kalanpro-offline-shell-") && key !== OFFLINE_CACHE).map((key) => caches.delete(key))))
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin || !OFFLINE_ASSETS.includes(url.pathname)) return;

  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response.ok) {
          const clone = response.clone();
          void caches.open(OFFLINE_CACHE).then((cache) => cache.put(url.pathname, clone));
        }
        return response;
      })
      .catch(async () => (await caches.match(url.pathname)) || new Response("Ressource hors connexion indisponible.", { status: 503 }))
  );
});
