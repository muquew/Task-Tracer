import argparse,hashlib,json,sys,threading,subprocess
from datetime import datetime,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright,expect
ROOT=Path('/workspace/Task-Tracer')
OUT=Path(__file__).parent
sys.path.insert(0,str(ROOT/'tools'))
from security_playwright import ProductionHeaderHandler
from smoke_playwright import ThreadingHTTPServer,wait_for_app_ready,select_language,open_task_editor,select_visible_option,task_locator,click_task_action,reveal_task_field,select_filter,select_theme_preference
parser=argparse.ArgumentParser()
parser.add_argument('--expected-index-sha256',required=True)
args=parser.parse_args()
assert hashlib.sha256((ROOT/'index.html').read_bytes()).hexdigest()==args.expected_index_sha256
source_metadata={name:{'sha256':hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),'bytes':(ROOT/name).stat().st_size} for name in ['index.html','sw.js','resources/en.json','resources/zh-CN.json','vercel.json','package.json']}
(OUT/'source-metadata.json').write_text(json.dumps({'captured_at_beijing':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'root':str(ROOT.resolve()),'git_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'git_status':subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).splitlines(),'code_snapshot_sha256':hashlib.sha256(json.dumps(source_metadata,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'driver_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'argv':sys.argv,'sources':source_metadata},ensure_ascii=False,indent=2)+'\n')
server=ThreadingHTTPServer(('127.0.0.1',0),ProductionHeaderHandler)
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
base=f'http://127.0.0.1:{server.server_port}/'
index_before=hashlib.sha256((ROOT/'index.html').read_bytes()).hexdigest()
now=datetime.now(ZoneInfo('Asia/Shanghai'))
def day(offset):return (now+timedelta(days=offset)).strftime('%Y-%m-%d')
errors=[];records=[];steps=[]
def add(page,name,project,tags,offset=None,time='23:59',subtasks=()):
 open_task_editor(page)
 page.locator('#taskName').fill(name)
 page.locator('#taskDesc').fill(('走完记录、安排、执行和备份的完整流程。' if '体验' in name else 'Walk through capture, planning, completion and backup.') if subtasks else '')
 page.locator('#taskProject').fill(project)
 if offset is None:page.locator('#noDeadline').check()
 else:
  page.locator('#noDeadline').uncheck();page.locator('#dueDate').fill(day(offset));page.locator('#dueTime').fill(time)
 reveal_task_field(page,'#taskTags').fill(', '.join(tags))
 if offset is not None:
  reveal_task_field(page,'#reminderOffset')
  select_visible_option(page,'#reminderOffset','-1')
 for text in subtasks:
  page.locator('#subtaskInput').fill(text);page.locator('#addSubtaskBtn').click()
 page.locator('#submitBtn').click();expect(task_locator(page,name)).to_have_count(1)
 steps.append({'action':'create-task-via-direct-full-editor','language':page.locator('html').get_attribute('lang'),'name':name,'project':project,'tags':tags,'due':None if offset is None else {'date':day(offset),'time':time},'subtasks':list(subtasks)})
def photo(page,name):
 page.wait_for_timeout(650)
 page.screenshot(path=str(OUT/name),animations='allow')
 records.append({'file':name,'captured_at_beijing':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'sha256':hashlib.sha256((OUT/name).read_bytes()).hexdigest(),'viewport':page.viewport_size,'language':page.locator('html').get_attribute('lang'),'index_sha256':index_before,'real_browser_csp':True,'workspace_theme':page.locator('html').get_attribute('data-accent'),'appearance':page.locator('html').get_attribute('data-theme'),'native_date_time':page.locator('#dueDate, #dueTime').evaluate_all('items => items.map(item => ({id:item.id,value:item.value,width:item.getBoundingClientRect().width,clientWidth:item.clientWidth,scrollWidth:item.scrollWidth}))')})
 print('Captured',name,flush=True)
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium')
  browser_version=browser.version
  for lang in ('zh-CN','en'):
   context=browser.new_context(viewport={'width':1440,'height':1000},locale=lang,timezone_id='Asia/Shanghai',reduced_motion='no-preference')
   page=context.new_page();page.set_default_timeout(7000)
   page.on('pageerror',lambda e:errors.append(str(e)))
   page.goto(base,wait_until='networkidle');wait_for_app_ready(page);select_language(page,lang);select_theme_preference(page,'light')
   if lang=='zh-CN':
    entries=[('核对本周交付清单','产品迭代',['交付'],-1,'18:00',()),('完成任务工作台体验复查','产品迭代',['体验'],0,'23:59',('检查任务与视图衔接','复查备份和恢复')),('整理本周用户反馈','产品迭代',['沟通'],1,'10:00',()),('更新个人作品集','个人计划',['设计'],3,'18:00',()),('阅读《设计中的设计》并记笔记','个人计划',['阅读'],None,'23:59',()),('梳理备份与恢复流程','产品迭代',['资料'],None,'23:59',())]
    draft=('准备下轮产品迭代计划','整理反馈，确定下轮交付范围。\n安排复查时间，确认备份与恢复流程。','产品迭代',('归纳关键用户反馈','安排本周交付顺序'))
   else:
    entries=[('Review this week’s delivery checklist','Product',['Delivery'],-1,'18:00',()),('Walk through the task workspace','Product',['Experience'],0,'23:59',('Check tasks and view transitions','Review backup and recovery')),('Organize recent user feedback','Product',['Research'],1,'10:00',()),('Update my design portfolio','Personal',['Design'],3,'18:00',()),('Read and collect notes on design','Personal',['Reading'],None,'23:59',()),('Map the backup and recovery flow','Product',['Reference'],None,'23:59',())]
    draft=('Plan the next product iteration','Review feedback and choose the next delivery scope.\nLeave time to check the workflow and backup.','Product',('Summarize the key user feedback','Arrange the delivery priorities'))
   for entry in entries:add(page,*entry)
   task_locator(page,entries[-1][0]).locator('[data-action="toggle"]').click()
   steps.append({'action':'complete-task-via-completion-control','language':lang,'name':entries[-1][0]})
   click_task_action(task_locator(page,entries[1][0]),'focus')
   steps.append({'action':'add-to-today-plan-via-real-menu','language':lang,'name':entries[1][0]})
   select_filter(page,'all')
   steps.append({'action':'select-all-status-via-real-filter-menu','language':lang})
   if page.locator('#toolsDrawerContent').is_visible():page.locator('#toolsDrawerToggleBtn').click()
   if page.locator('#captureShelf').is_visible():page.locator('#captureCloseBtn').click()
   if page.locator('#notification.show').count():page.locator('#workspaceNotificationClose').click()
   page.locator('#workspaceTitle').click()
   photo(page,'task-list.png' if lang=='zh-CN' else 'task-list-en.png')
   open_task_editor(page)
   page.locator('#taskName').fill(draft[0]);page.locator('#taskDesc').fill(draft[1]);page.locator('#taskProject').fill(draft[2])
   page.locator('[data-task-date-preset="1"]').click();page.locator('#dueTime').fill('17:30')
   page.locator('#taskTags').fill('体验, 迭代' if lang=='zh-CN' else 'Experience, Iteration')
   for text in draft[3]:page.locator('#subtaskInput').fill(text);page.locator('#addSubtaskBtn').click()
   page.locator('#taskName').focus()
   steps.append({'action':'fill-unsaved-direct-editor','language':lang,'name':draft[0],'description':draft[1],'project':draft[2],'date':day(1),'time':'17:30','subtasks':list(draft[3])})
   photo(page,'add-task.png' if lang=='zh-CN' else 'add-task-en.png')
   context.close()
  browser.close()
finally:
 server.shutdown();server.server_close();thread.join(timeout=2)
assert not errors,errors
assert hashlib.sha256((ROOT/'index.html').read_bytes()).hexdigest()==index_before
assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==meta['sha256'] for name,meta in source_metadata.items()), 'Captured source files changed during capture'
(OUT/'capture.json').write_text(json.dumps({'version':'4.15.0','time':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'capture_started_at_beijing':now.isoformat(),'fixtures':'Small illustrative tasks created through real editor controls; names match each screenshot language. Dates use actual capture day. No task records injected.','index_sha256':index_before,'browser_version':browser_version,'steps':steps,'screenshots':records,'errors':errors},ensure_ascii=False,indent=2)+'\n')
print('Four screenshots captured; source unchanged; no page errors.',flush=True)
