// 改了代码要来这里改缓存名字
const CACHE_NAME = 'task-tracer-v4';
const ASSETS_TO_CACHE = [
    './',
    './index.html',
    './manifest.json',
    './fav/android-chrome-192x192.png',
    './fav/android-chrome-512x512.png'
];

// 1. 安装阶段 (进货)：下载并缓存所有文件
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

// 2. 拦截请求 (发货)：优先使用缓存
self.addEventListener('fetch', (e) => {
    e.respondWith(
        caches.match(e.request).then((cachedResponse) => {
            // A. 如果缓存里有，直接返回缓存 (离线可用)
            if (cachedResponse) {
                return cachedResponse;
            }
            // B. 如果缓存没有，去网络请求
            return fetch(e.request).then((networkResponse) => {
                // 检查请求是否有效
                if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== 'basic') {
                    return networkResponse;
                }

                // === 动态缓存资源文件 (仅缓存本站的 resources 文件夹) ===
                if (e.request.url.includes('/resources/')) {
                    const responseToCache = networkResponse.clone();
                    // 这里不需要等待缓存完成才返回数据给用户，但为了消除警告，我们加上 return
                    caches.open(CACHE_NAME).then((cache) => {
                        console.log('[Service Worker] Caching new resource:', e.request.url);
                        return cache.put(e.request, responseToCache);
                    });
                }
                return networkResponse;
            });
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