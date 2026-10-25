from pathlib import Path
import sys,json,threading,traceback
ROOT=Path('/workspace/Task-Tracer-redesign')
SNAPSHOT=Path('/tmp/task-tracer-redesign-affected-rerun-q1339v85/inputs')
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
import smoke_playwright as smoke
import security_playwright as security
from playwright.sync_api import sync_playwright,expect
smoke.REPO_ROOT=SNAPSHOT;security.ROOT=SNAPSHOT
server=smoke.ThreadingHTTPServer(('127.0.0.1',0),security.ProductionHeaderHandler)
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
report={'phase':'original frozen source task-menu geometry diagnostic, not candidate acceptance','snapshot':str(SNAPSHOT),'index_sha256':'5ffc00400907898394e838a6ee2743c628a897f0c72b020da0fa98838468c6ed','observations':[]}
def geometry(locator):
 return locator.evaluate('node => { const r=node.getBoundingClientRect();return {left:r.left,top:r.top,right:r.right,bottom:r.bottom,width:r.width,height:r.height,viewportWidth:innerWidth,viewportHeight:innerHeight}; }')
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(**smoke.browser_launch_options())
  report['browser']=browser.version
  for viewport in [{'width':1280,'height':720},{'width':390,'height':844}]:
   context=browser.new_context(viewport=viewport,reduced_motion='reduce')
   page=context.new_page();errors=[];console=[]
   page.on('pageerror',lambda e:errors.append(str(e)))
   page.on('console',lambda m:console.append(m.text) if m.type=='error' else None)
   smoke.clear_app_data(page,f'http://127.0.0.1:{server.server_port}/')
   for count in (4,18):
    start=1 if count==4 else 5
    for i in range(start,count+1): smoke.add_task(page,f'Bottom task {i:02}',no_deadline=True)
    task=page.locator('#taskList .task-item').last; name=task.locator('.task-name').inner_text();toggle=task.locator('.task-more-toggle')
    toggle.scroll_into_view_if_needed()
    toggle.evaluate('node => window.scrollBy(0,node.getBoundingClientRect().bottom-innerHeight+6)')
    page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
    item={'viewport':viewport,'count':count,'lastVisibleTask':name,'toggle_before':geometry(toggle),'tasks_before':smoke.get_task_records(page)}
    try:
     item['scroll_before']=page.evaluate('scrollY')
     toggle.click();menu=task.locator('.task-action-menu');expect(menu).to_be_visible()
     item['menu_first_frame']=geometry(menu)
     page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
     item['scroll_after_focus']=page.evaluate('scrollY')
     item['menu_open']=geometry(menu);item['active_element']=page.locator(':focus').evaluate('node => ({tag:node.tagName,action:node.dataset.action,cls:node.className})')
     item['open_screenshot']=str(OUT/f'{viewport["width"]}-{count}-open.png');page.screenshot(path=item['open_screenshot'],full_page=False,animations='disabled')
     delete=task.locator('[data-action="delete"]');item['delete_before']=geometry(delete)
     item['delete_pointer_hit']=delete.evaluate('node => { const r=node.getBoundingClientRect();const x=r.left+r.width/2,y=r.top+r.height/2;const target=document.elementFromPoint(x,y);return Boolean(target && (node===target || node.contains(target))); }')
     delete.click();expect(page.locator('#taskModal')).to_be_visible()
     item['delete_confirm_pointer']=True
     item['confirm_screenshot']=str(OUT/f'{viewport["width"]}-{count}-confirm.png');page.screenshot(path=item['confirm_screenshot'],full_page=False,animations='disabled')
     page.locator('#cancelBtn').click();expect(page.locator('#taskModal')).to_be_hidden()
     item['tasks_unchanged']=smoke.get_task_records(page)==item['tasks_before']
     assert item['tasks_unchanged']
    except BaseException as exc:
     item['error']=str(exc);item['traceback']=traceback.format_exc()
     try:
      item['failure_screenshot']=str(OUT/f'{viewport["width"]}-{count}-failure.png');page.screenshot(path=item['failure_screenshot'],full_page=False,animations='disabled')
      item['menu_final']=geometry(task.locator('.task-action-menu'));item['menu_hidden']=task.locator('.task-action-menu').get_attribute('hidden')
     except BaseException as capture: item['capture_error']=str(capture)
    item.pop('tasks_before',None);report['observations'].append(item)
    if item.get('error'): break
   report.setdefault('errors',[]).append({'viewport':viewport,'page':errors,'console':console});context.close()
  browser.close()
finally:
 server.shutdown();server.server_close();thread.join(timeout=2)
 (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
