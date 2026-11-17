"""Shared workspace failure fixtures and assertions; no test entry point."""
from __future__ import annotations

def inject(page, method, store_name, key=None, occurrence=1, quota=False, queued=True):
    page.evaluate("""options => {
        const original = IDBObjectStore.prototype[options.method];
        window.workspaceFailureInjection = {matched:0, fired:false, queued:false};
        IDBObjectStore.prototype[options.method] = function(value, ...rest) {
            const matches = this.name === options.store
                && (options.key === null || value?.key === options.key);
            if (!matches) return original.call(this, value, ...rest);
            const observation = window.workspaceFailureInjection;
            observation.matched++;
            if (observation.matched !== options.occurrence) return original.call(this, value, ...rest);
            IDBObjectStore.prototype[options.method] = original;
            observation.fired = true;
            let request;
            if (options.queued) {
                request = original.call(this, value, ...rest);
                observation.queued = true;
            }
            if (options.quota) throw new DOMException('Injected synthetic quota failure', 'QuotaExceededError');
            this.transaction.abort();
            return request;
        };
    }""", {'method': method, 'store': store_name, 'key': key, 'occurrence': occurrence,
             'quota': quota, 'queued': queued})

def injection_seen(page, queued):
    observation = page.evaluate('window.workspaceFailureInjection')
    assert observation['fired'] and observation['queued'] == queued, observation
    return observation
