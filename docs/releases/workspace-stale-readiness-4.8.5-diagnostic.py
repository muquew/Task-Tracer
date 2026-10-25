from pathlib import Path
import json
import sys
sys.path.insert(0,'/workspace/Task-Tracer/tools')
from playwright.sync_api import expect
import workspace_failure_playwright as module

observations=[]
ready=module.wait_for_app_ready
def snapshot(page):
    return page.evaluate('''() => ({search:document.getElementById('searchInput')?.value,
        cards:document.querySelectorAll('.task-item').length,
        names:Array.from(document.querySelectorAll('.task-name')).slice(0,4).map(node=>node.textContent),
        targetRendered:Array.from(document.querySelectorAll('.task-name')).some(node=>node.textContent==='Failure workspace 00000 中文'),
        loading:!!document.querySelector('#taskList .loading-state'),
        listVisible:!!document.querySelector('#taskList')?.offsetParent})''')

def diagnosed_ready(page):
    ready(page)
    if observations or len(page.context.pages)<2:
        return
    record={'after_minimal_ready':snapshot(page)}
    observations.append(record)
    page.locator('#searchInput').fill(module.FIRST)
    record['after_first_search_fill']=snapshot(page)
    page.wait_for_function("document.querySelectorAll('.task-item').length > 0")
    record['after_first_render']=snapshot(page)
    record['database_count']=page.evaluate('''() => new Promise((resolve,reject)=>{
        const request=indexedDB.open('TaskTrackerDB',2);
        request.onerror=()=>reject(request.error);
        request.onsuccess=()=>{
            const db=request.result;
            const tx=db.transaction('tasks');
            const count=tx.objectStore('tasks').count();
            tx.oncomplete=()=>{db.close();resolve(count.result);};
            tx.onabort=()=>reject(tx.error);
        };
    })''')
    if not record['after_first_render']['targetRendered']:
        expect(page.locator('.task-item')).to_have_count(100)
        page.locator('#searchInput').fill('')
        page.locator('#searchInput').fill(module.FIRST)
        expect(module.task_locator(page,module.FIRST)).to_have_count(1)
        record['after_resend']=snapshot(page)
        record['lost_search_confirmed']=True
    else:
        record['lost_search_confirmed']=False
    print('STALE_READY_DIAGNOSTIC '+json.dumps(record,ensure_ascii=False),flush=True)

module.wait_for_app_ready=diagnosed_ready
try:
    module.run('chromium',10000,6,['stale-edit'],Path('/tmp/task-tracer-stale-ready-diagnostic-run.json'))
finally:
    Path('/tmp/task-tracer-stale-ready-diagnostic.json').write_text(json.dumps({'observations':observations},indent=2,ensure_ascii=False)+'\n')
