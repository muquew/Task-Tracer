import json
import sys
import tempfile
sys.path.insert(0, '/workspace/Task-Tracer/tools')
from playwright.sync_api import expect, sync_playwright
from workspace_failure_playwright import prepare, stored, local_server, browser_launch_options

with local_server() as url, sync_playwright() as p, tempfile.TemporaryDirectory(prefix='workspace-native-quota-') as profile:
    context=p.chromium.launch_persistent_context(profile,accept_downloads=True, reduced_motion='reduce', timezone_id='UTC', **browser_launch_options())
    page=context.new_page()
    before=prepare(page,url,200,6)
    origin=url.rstrip('/')
    cdp=context.new_cdp_session(page)
    print('usage_before',json.dumps(cdp.send('Storage.getUsageAndQuota',{'origin':origin})),flush=True)
    cdp.send('Storage.overrideQuotaForOrigin',{'origin':origin,'quotaSize':1024})
    print('usage_limited',json.dumps(cdp.send('Storage.getUsageAndQuota',{'origin':origin})),flush=True)
    page.evaluate('''() => {
        window.nativeQuotaAborts=[];
        const transaction=IDBDatabase.prototype.transaction;
        IDBDatabase.prototype.transaction=function(...args) {
            const tx=transaction.apply(this,args);
            if(tx.mode==='readwrite') tx.addEventListener('abort',()=>window.nativeQuotaAborts.push(tx.error?.name || null));
            return tx;
        };
    }''')
    page.locator('#openModalBtn').click()
    page.locator('#taskName').fill('Native browser quota probe')
    page.locator('#taskDesc').fill('Synthetic native quota payload ' + 'Q' * (4 * 1024 * 1024))
    page.locator('#noDeadline').check()
    page.locator('#submitBtn').click()
    try:
        expect(page.locator('#storageUnavailableBanner')).to_be_visible(timeout=10000)
        print('native_errors',page.evaluate('window.nativeQuotaAborts'),flush=True)
        assert stored(page)==before
        print('PASS: native engine quota failure rolled back exact tasks/config',flush=True)
    finally:
        print('notification',page.locator('#notificationText').inner_text(),flush=True)
        print('native_errors_final',page.evaluate('window.nativeQuotaAborts'),flush=True)
        cdp.send('Storage.overrideQuotaForOrigin',{'origin':origin})
        context.close()
