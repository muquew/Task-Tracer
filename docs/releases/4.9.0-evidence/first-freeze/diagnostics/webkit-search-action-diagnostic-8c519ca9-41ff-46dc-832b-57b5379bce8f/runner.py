from pathlib import Path
import hashlib,json,traceback,uuid
from check import source_identity,verification_identity,timestamp
from playwright.sync_api import sync_playwright,expect
from workspace_failure_playwright import prepare,FIRST,stored
from smoke_playwright import local_server,task_locator,reveal_task_action
out=Path('/tmp/task-tracer-4.9.0-final-pu_nzs6d')/('webkit-search-action-diagnostic-'+str(uuid.uuid4()));out.mkdir()
f=json.loads(Path('/tmp/task-tracer-4.9.0-final-pu_nzs6d/frozen-inputs.json').read_text())
r={'scope':'Read-only failure diagnosis with fresh synthetic browser storage; original matrix failure remains unchanged','started_at':timestamp(),'source':source_identity(),'verification':verification_identity(),'observations':{},'page_errors':[],'cleanup':{}}
assert r['source']==f['source'] and r['verification']==f['verification']
try:
 with local_server() as url,sync_playwright() as p:
  browser=p.webkit.launch(headless=True);r['browser_version']=browser.version
  try:
   context=browser.new_context(accept_downloads=True,reduced_motion='reduce',timezone_id='UTC');page=context.new_page();page.on('pageerror',lambda e:r['page_errors'].append(str(e)))
   try:
    before=prepare(page,url,200,6)
    task=task_locator(page,FIRST)
    def observe():
     return {'row_count':task.count(),'row_visible':task.is_visible(),'more_count':task.locator('.task-more-toggle').count(),'visible_task_count':page.locator('.task-item').count(),'query':page.locator('#searchInput').input_value()}
    r['observations']['before_search']=observe()
    page.locator('#searchInput').fill(FIRST)
    r['observations']['immediately_after_search_fill']=observe()
    action=reveal_task_action(task,'edit')
    r['observations']['after_original_reveal_helper']=observe()
    expect(task).to_be_visible()
    r['observations']['after_match_renders']=observe()
    r['observations']['closed_menu_after_match']={'hidden':task.locator('.task-action-menu').get_attribute('hidden'),'expanded':task.locator('.task-more-toggle').get_attribute('aria-expanded'),'edit_visible':action.is_visible()}
    page.screenshot(path=str(out/'after-match-menu-state.png'),full_page=False,animations='disabled')
    reveal_task_action(task,'edit').click()
    expect(page.locator('#taskModal')).to_be_visible()
    r['observations']['same_helper_after_row_visible_opens_edit']=True
    page.locator('#cancelBtn').click();expect(page.locator('#taskModal')).to_be_hidden()
    r['data_unchanged']=stored(page)==before
   finally:
    context.close();r['cleanup']['context_closed']=True
  finally:
   browser.close();r['cleanup']['browser_closed']=True
 r['status']='diagnosed'
except BaseException as e:
 r['status']='diagnostic_failed';r['error']=str(e);r['traceback']=traceback.format_exc()
finally:
 r['source_final']=source_identity();r['verification_final']=verification_identity();r['source_unchanged']=r['source']==r['source_final']==f['source'];r['verification_unchanged']=r['verification']==r['verification_final']==f['verification'];r['finished_at']=timestamp();(out/'report.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print(str(out/'report.json'));print(json.dumps({k:r[k] for k in ['status','observations','source_unchanged','verification_unchanged','cleanup']},ensure_ascii=False,indent=2))
