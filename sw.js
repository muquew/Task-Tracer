const CACHE_NAME = 'task-tracer-v3.16';
const ASSETS_TO_CACHE = [
    './',
    './index.html',
    './manifest.json',
    './resources/en.json?v=2.4',
    './resources/zh-CN.json?v=2.4',
    './fav/android-chrome-192x192.png',
    './fav/android-chrome-512x512.png'
];
self.addEventListener('install', (e) => {
    e.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                return cache.addAll(ASSETS_TO_CACHE);
            })
            .then(() => {
                return self.skipWaiting();
            })
    );
});
self.addEventListener('fetch', (e) => {
    if (e.request.method !== 'GET') return;
    const url = new URL(e.request.url);
    if (url.origin !== self.location.origin) return;
    if (e.request.mode === 'navigate' || isAppShellRequest(url)) {
        e.respondWith(networkFirst(e.request, './index.html'));
        return;
    }
    if (url.pathname.includes('/resources/')) {
        e.respondWith(networkFirst(e.request));
        return;
    }
    e.respondWith(cacheFirst(e.request));
});
self.addEventListener('notificationclick', (e) => {
    e.notification.close();
    e.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then((clientList) => {
                for (const client of clientList) {
                    if ('focus' in client) {
                        return client.focus();
                    }
                }
                if (clients.openWindow) {
                    return clients.openWindow('./index.html');
                }
            })
    );
});
self.addEventListener('activate', (e) => {
    e.waitUntil(
        caches.keys()
            .then((keyList) => {
                return Promise.all(keyList.map((key) => {
                    if (key !== CACHE_NAME) {
                        return caches.delete(key);
                    }
                }));
            })
            .then(() => {
                return self.clients.claim();
            })
    );
});
function isAppShellRequest(url) {
    return url.pathname === '/' || url.pathname.endsWith('/index.html');
}
async function networkFirst(request, fallbackUrl) {
    try {
        const networkResponse = await fetch(request);
        cacheResponse(request, networkResponse).catch((error) => {
            console.warn('[Service Worker] Cache update failed:', error);
        });
        return networkResponse;
    } catch (error) {
        const cachedResponse = await caches.match(request);
        if (cachedResponse) return cachedResponse;
        if (fallbackUrl) {
            const fallbackResponse = await caches.match(fallbackUrl);
            if (fallbackResponse) return fallbackResponse;
        }
        throw error;
    }
}
async function cacheFirst(request) {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) return cachedResponse;
    const networkResponse = await fetch(request);
    cacheResponse(request, networkResponse).catch((error) => {
        console.warn('[Service Worker] Cache update failed:', error);
    });
    return networkResponse;
}
async function cacheResponse(request, response) {
    if (!response || response.status !== 200 || response.type !== 'basic') return;
    const cache = await caches.open(CACHE_NAME);
    await cache.put(request, response.clone());
}
