const CACHE_PREFIX = 'task-tracer-';
const CACHE_NAME = 'task-tracer-v4.10.1';
const ASSETS_TO_CACHE = [
    './',
    './index.html',
    './manifest.json',
    './THIRD_PARTY_NOTICES.md',
    './resources/en.json?v=4.38',
    './resources/zh-CN.json?v=4.38',
    './fav/favicon-16x16.png',
    './fav/favicon-32x32.png',
    './fav/favicon.ico',
    './fav/apple-touch-icon.png',
    './fav/android-chrome-192x192.png',
    './fav/android-chrome-512x512.png'
];
const SCOPE_URL = new URL('./', self.registration.scope);
const INDEX_URL = new URL('./index.html', self.registration.scope);
const ASSET_URLS = new Set(ASSETS_TO_CACHE.map(asset => new URL(asset, self.registration.scope).href));
const LANGUAGE_PATHS = new Set(ASSETS_TO_CACHE.filter(asset => asset.startsWith('./resources/')).map(asset => new URL(asset, self.registration.scope).pathname));
const clientBundles = new Map();
const requestedClientVersions = new Set();
self.addEventListener('install', e => {
    e.waitUntil((async () => {
        const existed = (await caches.keys()).includes(CACHE_NAME);
        try {
            const cache = await caches.open(CACHE_NAME);
            if (existed) {
                try {
                    await validateInstalledBundle(cache);
                    await self.skipWaiting();
                    return;
                } catch (error) {}
            }
            await cache.addAll(ASSETS_TO_CACHE.map(asset => new Request(new URL(asset, self.registration.scope), { cache: 'reload' })));
            await validateInstalledBundle(cache);
            await self.skipWaiting();
        } catch (error) {
            if (!existed) await caches.delete(CACHE_NAME);
            throw error;
        }
    })());
});
async function validateInstalledBundle(cache) {
    for (const asset of ASSETS_TO_CACHE) {
        if (!await cache.match(new URL(asset, self.registration.scope).href)) throw new Error('Incomplete installed bundle');
    }
    const resourceVersions = new Set(ASSETS_TO_CACHE.filter(asset => asset.startsWith('./resources/')).map(asset => new URL(asset, self.registration.scope).searchParams.get('v')));
    if (resourceVersions.size !== 1 || resourceVersions.has(null)) throw new Error('Invalid bundle resource version');
    const resourceVersion = [...resourceVersions][0];
    const appVersion = CACHE_NAME.slice(CACHE_PREFIX.length + 1);
    for (const url of [SCOPE_URL.href, INDEX_URL.href]) {
        const html = await (await cache.match(url)).text();
        const scripts = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script\s*>/gi)];
        const main = scripts.filter(script => /^\s*\(function\s*\(\s*\)\s*\{\s*const\s+CONFIG\s*=/.test(script[1]));
        const bundled = scripts.filter(script => /\bid=["']bundledTranslations["']/.test(script[0].slice(0, script[0].indexOf('>'))));
        if (main.length !== 1 || bundled.length !== 1) throw new Error('Missing bundle metadata');
        const declaredAppVersion = main[0][1].match(/\bAPP\s*:\s*\{\s*VERSION\s*:\s*["']([^"']+)["']/)?.[1];
        const declaredResourceVersion = main[0][1].match(/\bRESOURCE_VERSION\s*:\s*["']([^"']+)["']/)?.[1];
        if (declaredAppVersion !== appVersion || declaredResourceVersion !== resourceVersion || JSON.parse(bundled[0][1]).resourceVersion !== resourceVersion) {
            throw new Error('Inconsistent installed bundle versions');
        }
    }
}
self.addEventListener('fetch', e => {
    if (e.request.method !== 'GET') return;
    const url = new URL(e.request.url);
    if (url.origin !== self.location.origin) return;
    const response = serveRequest(e, url);
    e.respondWith(response);
    e.waitUntil(response.then(() => cleanupOldBundleCaches()).catch(() => {}));
});
self.addEventListener('notificationclick', e => {
    e.notification.close();
    e.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then(clientList => {
                for (const client of clientList) {
                    if ('focus' in client) return client.focus();
                }
                if (clients.openWindow) return clients.openWindow('./index.html');
            })
    );
});
self.addEventListener('message', e => {
    if (e.data?.type === 'SKIP_WAITING') self.skipWaiting();
    if (e.data?.type !== 'CLIENT_VERSION' || typeof e.data.version !== 'string') return;
    if (!/^\d+(?:\.\d+)*$/.test(e.data.version) || !e.source?.id || e.source.type !== 'window') return;
    clientBundles.set(e.source.id, `${CACHE_PREFIX}v${e.data.version}`);
    requestedClientVersions.delete(e.source.id);
    e.waitUntil(cleanupOldBundleCaches());
});
self.addEventListener('activate', e => {
    e.waitUntil((async () => {
        await self.clients.claim();
        await cleanupOldBundleCaches();
    })());
});
function isAppShellRequest(url) {
    return url.pathname === SCOPE_URL.pathname || url.pathname === INDEX_URL.pathname;
}
async function installedShell() {
    const cache = await caches.open(CACHE_NAME);
    return await cache.match(INDEX_URL.href) || await cache.match(SCOPE_URL.href);
}
function rememberClient(e, cacheName) {
    const clientId = e.resultingClientId || e.clientId;
    if (clientId && (e.resultingClientId || !clientBundles.has(clientId))) clientBundles.set(clientId, cacheName);
}
async function serveRequest(e, url) {
    if (isAppShellRequest(url)) {
        const shell = await installedShell();
        if (shell) {
            if (e.request.mode === 'navigate') rememberClient(e, CACHE_NAME);
            return shell;
        }
        return fetch(e.request);
    }
    if (ASSET_URLS.has(url.href)) {
        const cache = await caches.open(CACHE_NAME);
        const response = await cache.match(e.request);
        if (response) return response;
    }
    if (LANGUAGE_PATHS.has(url.pathname)) {
        for (const name of await caches.keys()) {
            if (!isBundleCache(name)) continue;
            const response = await (await caches.open(name)).match(e.request);
            if (response) {
                rememberClient(e, name);
                return response;
            }
        }
    }
    try {
        return await fetch(e.request);
    } catch (error) {
        if (e.request.mode === 'navigate') {
            const fallback = await installedShell();
            if (fallback) {
                rememberClient(e, CACHE_NAME);
                return fallback;
            }
        }
        throw error;
    }
}
function isBundleCache(name) {
    return name.startsWith(`${CACHE_PREFIX}v`) && /^\d+(?:\.\d+)*$/.test(name.slice(CACHE_PREFIX.length + 1));
}
function isOlderBundle(name) {
    if (!isBundleCache(name)) return false;
    const candidate = name.slice(CACHE_PREFIX.length + 1).split('.').map(Number);
    const current = CACHE_NAME.slice(CACHE_PREFIX.length + 1).split('.').map(Number);
    for (let index = 0; index < Math.max(candidate.length, current.length); index++) {
        const difference = (candidate[index] || 0) - (current[index] || 0);
        if (difference !== 0) return difference < 0;
    }
    return false;
}
async function cleanupOldBundleCaches() {
    const windows = (await self.clients.matchAll({ type: 'window', includeUncontrolled: true })).filter(client => {
        const url = new URL(client.url);
        return url.origin === SCOPE_URL.origin && url.pathname.startsWith(SCOPE_URL.pathname);
    });
    const liveIds = new Set(windows.map(client => client.id));
    for (const clientId of clientBundles.keys()) if (!liveIds.has(clientId)) clientBundles.delete(clientId);
    for (const clientId of requestedClientVersions) if (!liveIds.has(clientId)) requestedClientVersions.delete(clientId);
    let unknown = false;
    for (const client of windows) {
        if (clientBundles.has(client.id)) continue;
        unknown = true;
        if (!requestedClientVersions.has(client.id)) {
            requestedClientVersions.add(client.id);
            try { client.postMessage({ type: 'REPORT_CLIENT_VERSION' }); } catch (error) {}
        }
    }
    if (unknown) return;
    const inUse = new Set([CACHE_NAME, ...windows.map(client => clientBundles.get(client.id))]);
    await Promise.all((await caches.keys()).filter(name => isOlderBundle(name) && !inUse.has(name)).map(name => caches.delete(name)));
}
