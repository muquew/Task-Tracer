const CACHE_NAME = 'task-tracer-v3.10';
const ASSETS_TO_CACHE = [
    './',
    './index.html',
    './manifest.json',
    './resources/en.json?v=2.0',
    './resources/zh-CN.json?v=2.0',
    './fav/android-chrome-192x192.png',
    './fav/android-chrome-512x512.png'
];

self.addEventListener('install', (e) => {
    console.log('[Service Worker] Installing...');
    e.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('[Service Worker] Caching all assets');
                return cache.addAll(ASSETS_TO_CACHE);
            })
            .then(() => {
                // 确保缓存完成后再跳过等待
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

// 2.5 点击通知：回到已打开的应用窗口，或打开首页
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

// 3. 激活阶段 (清理)：删除旧版本的缓存
self.addEventListener('activate', (e) => {
    console.log('[Service Worker] Activating...');
    e.waitUntil(
        caches.keys()
            .then((keyList) => {
                return Promise.all(keyList.map((key) => {
                    if (key !== CACHE_NAME) {
                        console.log('[Service Worker] Removing old cache', key);
                        return caches.delete(key);
                    }
                }));
            })
            .then(() => {
                // 确保清理完成后再接管页面
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
