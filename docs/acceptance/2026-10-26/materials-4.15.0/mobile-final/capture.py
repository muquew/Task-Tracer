import json,hashlib,sys,threading,traceback
from pathlib import Path
from datetime import datetime,timezone
from playwright.sync_api import sync_playwright,expect
ROOT=Path('/workspace/Task-Tracer');OUT=Path(__file__).parent
sys.path.insert(0,str(ROOT/'tools'))
from smoke_playwright import ThreadingHTTPServer,get_task_records
from security_playwright import ProductionHeaderHandler
EXPECTED='3aa235f5f9adae2349440b8995c7a9c1ecb0335111f52d232cc8811e29a37561'
errors=[];action_errors=[];actions=[];screens=[];main_error=None;source_sha=None
server=ThreadingHTTPServer(('127.0.0.1',0),ProductionHeaderHandler)
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();url=f'http://127.0.0.1:{server.server_port}/'

def state(page):
 return page.evaluate('''() => {const v=e=>e.checkVisibility({opacityProperty:true,visibilityProperty:true}); const box=e=>{const b=e.getBoundingClientRect();return{x:b.x,y:b.y,w:b.width,h:b.height}};const selectors=['body','.workspace-task-surface','.tools-drawer','.task-group-header','.task-item','.workspace-mobile-dock','.workspace-topbar','#taskModal .modal-content','#taskModal .modal-header','#taskModal .form-actions','.task-editor-properties','#taskProject','#taskTags','#taskDesc','#taskName','#submitBtn','#cancelBtn','.settings-surface','.workspace-theme-option','.workspace-theme-option:has(input:checked)','.stats-action-grid','.stats-review','.task-action-menu:not([hidden])'];return {viewport:{w:innerWidth,h:innerHeight},docWidth:document.documentElement.scrollWidth,scrollY,accent:document.documentElement.dataset.accent,theme:document.documentElement.dataset.theme,active:{id:document.activeElement?.id,outline:document.activeElement?getComputedStyle(document.activeElement).outline:null},headings:[...document.querySelectorAll('h1,h2')].filter(v).map(e=>e.innerText),buttons:[...document.querySelectorAll('button')].filter(v).map(e=>({id:e.id,text:e.innerText,aria:e.getAttribute('aria-label'),disabled:e.disabled,...box(e)})),fields:[...document.querySelectorAll('input,textarea,select')].filter(v).map(e=>({id:e.id,value:e.value,checked:e.checked,disabled:e.disabled,...box(e)})),surfaces:selectors.map(s=>{const e=document.querySelector(s);if(!e)return{selector:s,missing:true};const c=getComputedStyle(e);return{selector:s,visible:v(e),background:c.backgroundColor,backgroundImage:c.backgroundImage,color:c.color,border:c.border,shadow:c.boxShadow,backdropFilter:c.backdropFilter,radius:c.borderRadius,opacity:c.opacity,...box(e)}})}}''')

def act(page,action,selector=None,value=None):
 before=state(page);cmd={'action':action,'selector':selector,'value':value}
 try:
  if action=='click':page.locator(selector).click()
  elif action=='fill':page.locator(selector).fill(value)
  elif action=='select':page.locator(selector).select_option(value)
  elif action=='check':page.locator(selector).set_checked(value)
  elif action=='viewport':page.set_viewport_size(value)
  elif action=='press':page.locator(selector).press(value)
  page.wait_for_timeout(180)
  actions.append({'command':cmd,'before':before,'after':state(page)})
 except Exception as e:
  action_errors.append({'command':cmd,'error':str(e)});raise

def capture(page,name):
 page.wait_for_timeout(500)
 d=state(page);d['source_index_sha256']=source_sha;d['pageErrors']=list(errors)
 assert d['docWidth']<=d['viewport']['w'],(name,d['docWidth'],d['viewport'])
 page.screenshot(path=str(OUT/f'{name}.png'),animations='allow')
 (OUT/f'{name}.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');screens.append(name)
 print(json.dumps({'capture':name,'accent':d['accent'],'theme':d['theme'],'headings':d['headings'],'fields':[f['id'] for f in d['fields']]},ensure_ascii=False),flush=True)

try:
 assert hashlib.sha256((ROOT/'index.html').read_bytes()).hexdigest()==EXPECTED
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium')
  context=browser.new_context(viewport={'width':390,'height':844},locale='zh-CN',timezone_id='Asia/Shanghai',reduced_motion='no-preference')
  page=context.new_page();page.set_default_timeout(8000);page.on('pageerror',lambda e:errors.append(str(e)))
  response=page.goto(url,wait_until='networkidle');source_sha=hashlib.sha256(response.body()).hexdigest();assert source_sha==EXPECTED
  (OUT/'source.json').write_text(json.dumps({'sha256':source_sha,'status':response.status,'url':response.url,'headers':response.all_headers(),'browser':browser.version,'at':datetime.now(timezone.utc).isoformat(),'bypassCSP':False,'normal_motion':True,'fresh_context':True,'http_handler':'unmodified ProductionHeaderHandler serves deployment headers on local HTTP','assets':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['index.html','vercel.json','resources/zh-CN.json','resources/en.json','sw.js']}},ensure_ascii=False,indent=2)+'\n')
  tasks=[('整理首发版本的交付材料','核对说明、截图与备份文件，确保内容保持一致。','Task Tracer','发布, 本周','0'),('准备下一次产品回顾','','产品','','1'),('收集值得参考的界面细节','','设计','',None)]
  for i,(name,desc,project,tags,preset) in enumerate(tasks):
   act(page,'click','#openModalBtn');act(page,'fill','#taskName',name)
   if desc:act(page,'fill','#taskDesc',desc)
   act(page,'fill','#taskProject',project)
   if tags:act(page,'fill','#taskTags',tags)
   if preset is not None:act(page,'click',f'[data-task-date-preset="{preset}"]')
   if i==0:
    act(page,'fill','#dueTime','09:00');act(page,'fill','#subtaskInput','确认发布说明');act(page,'click','#addSubtaskBtn');act(page,'fill','#subtaskInput','核对最后一轮反馈')
   act(page,'click','#submitBtn')
  records_before=get_task_records(page);(OUT/'seed-records.json').write_text(json.dumps(records_before,ensure_ascii=False,indent=2)+'\n')
  assert len(records_before)==3
  # Dismiss the actual transient confirmation before baseline comparison captures.
  if page.locator('.notification:not([hidden]) .notification-dismiss').count() and page.locator('.notification:not([hidden]) .notification-dismiss').first.is_visible():
   act(page,'click','.notification:not([hidden]) .notification-dismiss')
  else:
   page.wait_for_timeout(4500)
  for accent in ['iris','ocean','pine','berry']:
   for theme in ['light','dark']:
    act(page,'click','#openMenuBtn');act(page,'select','#themeToggleBtn',theme);act(page,'check',f'#workspaceTheme-{accent}',True)
    assert page.locator('html').get_attribute('data-accent')==accent and page.locator('html').get_attribute('data-theme')==theme
    act(page,'click','#settingsBackBtn');act(page,'click','#viewTab-list')
    capture(page,f'{len(screens)+1:02d}-390-{accent}-{theme}-list')
    act(page,'click','#openModalBtn')
    capture(page,f'{len(screens)+1:02d}-390-{accent}-{theme}-editor')
    assert page.locator('#taskName').evaluate('(e) => document.activeElement===e')
    act(page,'click','#cancelBtn')
  # Four focused supporting views; preserve exact source and normal animation.
  act(page,'viewport',value={'width':320,'height':500});act(page,'click','#openModalBtn')
  act(page,'fill','#subtaskInput','检查短窗口下当前输入行是否保持可见')
  capture(page,'17-320-berry-dark-short-editor')
  act(page,'click','#cancelBtn')
  if page.locator('#draftDiscardBtn').is_visible():act(page,'click','#draftDiscardBtn')
  act(page,'viewport',value={'width':390,'height':844});act(page,'click','#openMenuBtn')
  act(page,'press','#workspaceTheme-berry','Tab')
  capture(page,'18-390-berry-dark-appearance')
  act(page,'click','#settingsBackBtn')
  act(page,'click','.task-item:has-text("整理首发版本的交付材料") .task-more-toggle')
  capture(page,'19-390-berry-dark-action-menu')
  act(page,'press','.task-action-menu:not([hidden]) [data-action="edit"]','Escape')
  act(page,'click','#viewTab-stats')
  capture(page,'20-390-berry-dark-statistics')
  records_after=get_task_records(page);(OUT/'final-records.json').write_text(json.dumps(records_after,ensure_ascii=False,indent=2)+'\n');assert records_after==records_before,'Pure visual navigation changed tasks'
  context.close();browser.close()
except Exception as e:
 main_error={'type':type(e).__name__,'message':str(e),'traceback':traceback.format_exc()};print(json.dumps({'error':main_error},ensure_ascii=False),flush=True)
finally:
 server.shutdown();server.server_close();thread.join(timeout=2)
 (OUT/'actions.json').write_text(json.dumps(actions,ensure_ascii=False,indent=2)+'\n')
 (OUT/'session.json').write_text(json.dumps({'source_index_sha256':source_sha,'browser_closed':True,'server_closed':True,'source_end_sha256':hashlib.sha256((ROOT/'index.html').read_bytes()).hexdigest(),'pageErrors':errors,'actionErrors':action_errors,'error':main_error,'screenshots':screens,'actions':len(actions)},ensure_ascii=False,indent=2)+'\n')
 print('closed',flush=True)
 if main_error:sys.exit(1)
