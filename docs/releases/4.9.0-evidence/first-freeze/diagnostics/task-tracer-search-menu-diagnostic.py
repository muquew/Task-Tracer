import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,'/workspace/Task-Tracer-redesign/tools')
from smoke_playwright import local_server,wait_for_app_ready,task_locator,reveal_task_action
from workspace_failure_playwright import prepare,FIRST
from playwright.sync_api import sync_playwright,expect
with local_server() as url,sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True)
 context=browser.new_context(locale='en-US',viewport={'width':1280,'height':800},reduced_motion='reduce')
 page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 prepare(page,url,200,4)
 assert hashlib.sha256(page.request.get(url).body()).hexdigest()==hashlib.sha256(Path('/workspace/Task-Tracer-redesign/index.html').read_bytes()).hexdigest()
 page.evaluate('''()=>{
 window.__race=[];window.__tracked=null;
 window.__record=phase=>{const node=document.querySelector('[data-task-id="100000"]'),more=node?.querySelector('.task-more-toggle'),menu=node?.querySelector('.task-action-menu');window.__race.push({phase,time:performance.now(),search:document.querySelector('#searchInput').value,count:document.querySelectorAll('#taskList .task-item').length,same:window.__tracked===node,trackedConnected:window.__tracked?.isConnected,hidden:menu?.hidden,expanded:more?.getAttribute('aria-expanded'),focus:document.activeElement?.className,focusedTask:document.activeElement?.closest('.task-item')?.dataset.taskId,rect:menu&&!menu.hidden?menu.getBoundingClientRect().toJSON():null});};
 document.querySelector('#searchInput').addEventListener('input',()=>window.__record('input'));
 document.addEventListener('click',event=>{const more=event.target.closest('.task-more-toggle');if(more){window.__tracked=more.closest('.task-item');window.__record('more-capture');}},{capture:true});
 document.addEventListener('click',event=>{if(event.target.closest('.task-more-toggle'))window.__record('more-bubble');});
 new MutationObserver(records=>{if(records.some(record=>record.type==='childList'&&record.target.id==='taskList'||record.type==='attributes'&&(record.target.matches('.task-action-menu,.task-more-toggle'))))window.__record('mutations');}).observe(document.querySelector('#taskList'),{subtree:true,childList:true,attributes:true,attributeFilter:['hidden','aria-expanded']});
 }''')
 page.locator('#searchInput').fill(FIRST)
 control=reveal_task_action(task_locator(page,FIRST),'edit')
 page.evaluate('window.__record("after-reveal")')
 expect(page.locator('#taskList .task-item')).to_have_count(1)
 page.evaluate('window.__record("result-count-one")')
 print(json.dumps({'phase':'read-only local diagnostic, not candidate acceptance','source':hashlib.sha256(Path('/workspace/Task-Tracer-redesign/index.html').read_bytes()).hexdigest(),'events':page.evaluate('window.__race'),'edit_visible':control.is_visible(),'pageerrors':errors},ensure_ascii=False,indent=2),flush=True)
 context.close();browser.close()
