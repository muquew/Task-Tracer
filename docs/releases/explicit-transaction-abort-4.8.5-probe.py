from pathlib import Path
import json
import sys
sys.path.insert(0,'/workspace/Task-Tracer/tools')
from playwright.sync_api import sync_playwright
from smoke_playwright import browser_launch_options, local_server

with local_server() as url, sync_playwright() as p:
    browser=p.chromium.launch(**browser_launch_options())
    context=browser.new_context()
    page=context.new_page()
    page.goto(url)
    events=page.evaluate('''async () => {
        const db=await new Promise((resolve,reject)=>{
            const request=indexedDB.open('TaskTracerExplicitAbortProbe',1);
            request.onupgradeneeded=()=>request.result.createObjectStore('records',{keyPath:'id'});
            request.onsuccess=()=>resolve(request.result); request.onerror=()=>reject(request.error);
        });
        const events=[];
        let captured=null;
        await new Promise(resolve=>{
            const tx=db.transaction('records','readwrite');
            const store=tx.objectStore('records');
            const read=store.get(1);
            tx.onerror=event=>{
                captured=captured || event.target.error || tx.error;
                events.push({stage:'transaction.error',txError:tx.error?.name || null,
                    targetError:event.target.error?.name || null,captured:captured?.name || null});
            };
            tx.onabort=()=>{
                events.push({stage:'transaction.abort',txError:tx.error?.name || null,captured:captured?.name || null});
                resolve();
            };
            read.onsuccess=()=>{
                const put=store.put({id:1,value:'must roll back'});
                put.onerror=()=>events.push({stage:'request.error',requestError:put.error?.name || null,txError:tx.error?.name || null});
                tx.abort();
            };
        });
        const persisted=await new Promise((resolve,reject)=>{
            const tx=db.transaction('records');const request=tx.objectStore('records').getAll();
            tx.oncomplete=()=>resolve(request.result);tx.onabort=()=>reject(tx.error);
        });
        db.close();
        return {events,persisted};
    }''')
    result={'browser_version':browser.version,'scope':'Actual explicit IDBTransaction.abort with one pending put; no synthetic exception',**events}
    context.close();browser.close()
Path('/tmp/task-tracer-explicit-abort-probe.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
