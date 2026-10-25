from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys,uuid
sys.path.insert(0,'/workspace/Task-Tracer/tools')
from playwright.sync_api import sync_playwright,expect
from pending_subtask_playwright import deployment_server
from smoke_playwright import browser_launch_options,get_task_records
from accessibility_i18n_audit import audit_page_state,find_axe_source,settle_animations
R=Path('/workspace/Task-Tracer');O=Path('/tmp/task-tracer-4.14.0-final-form')/str(uuid.uuid4());O.mkdir(parents=True)
asset_names=('index.html','resources/en.json','resources/zh-CN.json','vercel.json','sw.js')
assets=lambda:{n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in asset_names}
report={'started_at':datetime.now(timezone.utc).isoformat(),'assets_start':assets(),'normal_csp':True,'bypass_csp':False,'normal_motion':True,'checks':[],'passed':False,'page_errors':[]}
assert report['assets_start']['index.html']=='e5741f889cb3c8e74d7f5885f36d5030922afa948b397579b759839ffd827f48'
axe=find_axe_source().read_text();print(str(O),flush=True)
def save(name,data):(O/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def observe(page,label):
 settle_animations(page,label)
 audit_page_state(page,axe,label)
 geometry=page.evaluate('''() => { const r=e=>{const b=e.getBoundingClientRect();return {x:b.x,y:b.y,w:b.width,h:b.height,right:b.right,bottom:b.bottom}};const el=document.activeElement,foot=document.querySelector('.form-actions');const b=r(el),hit=document.elementFromPoint(b.x+b.w/2,b.y+b.h/2);return {active:el.id,activeBox:b,footer:r(foot),form:r(document.querySelector('#taskForm')),viewport:{w:innerWidth,h:innerHeight},scrollWidth:document.documentElement.scrollWidth,activeCenterHit:hit===el||el.contains(hit),presetRows:[...document.querySelectorAll('.editor-date-presets button')].map(e=>({text:e.textContent,...r(e)}))};}''')
 page.screenshot(path=str(O/(label+'.png')))
 save(label+'.json',geometry);report['checks'].append({'label':label,'axe_passed':True,'geometry':geometry});save('report.json',report);return geometry
try:
 with deployment_server() as url,sync_playwright() as p:
  browser=p.chromium.launch(**browser_launch_options());report['browser']=browser.version
  try:
   for width,theme in ((320,'dark'),(390,'light'),(800,'light')):
    context=browser.new_context(viewport={'width':width,'height':844},locale='en-US',timezone_id='Asia/Shanghai',reduced_motion='no-preference')
    try:
     page=context.new_page();page.set_default_timeout(7000);page.on('pageerror',lambda e:report['page_errors'].append(str(e)))
     response=page.goto(url,wait_until='networkidle');assert hashlib.sha256(response.body()).hexdigest()==report['assets_start']['index.html'];save(str(width)+'-response-headers.json',response.all_headers())
     page.locator('#openMenuBtn').click();page.locator('#languageSelect').select_option('en');page.locator('#themeToggleBtn').select_option(theme);page.locator('#settingsBackBtn').click();page.locator('#openModalBtn').click()
     initial=observe(page,str(width)+'-new-editor');rows=initial['presetRows'];assert len({round(x['y']) for x in rows})==1,rows
     page.locator('#taskName').fill('Review the launch plan');page.locator('#taskDesc').fill('Confirm owners, dates, and next steps.');page.locator('[data-task-date-preset="1"]').click();page.locator('#taskTags').fill('launch, review');page.locator('#subtaskInput').fill('Check the final checklist')
     page.set_viewport_size({'width':width,'height':500});page.wait_for_timeout(200);g=observe(page,str(width)+'-short-focused-editor');assert g['active']=='subtaskInput' and g['activeCenterHit'] and g['activeBox']['bottom']<=g['footer']['y']-1,g
     page.set_viewport_size({'width':width,'height':844});page.locator('#taskAdvancedDetails > summary').click();page.locator('#repeatType-custom-button').click();page.locator('.custom-select:has(#repeatType) [data-value="weekly-days"]').click()
     for day in range(7):page.locator('#repeatWeekday'+str(day)).uncheck()
     page.locator('#submitBtn').click();expect(page.locator('#repeatWeekdaysError')).to_be_visible();g=observe(page,str(width)+'-invalid-weekdays');assert not get_task_records(page)
     rect=page.locator('#repeatWeekdaysError').bounding_box();assert rect['y']>=g['form']['y'] and rect['y']+rect['height']<=g['footer']['y']-1
     page.locator('#repeatWeekday4').check();page.locator('#submitBtn').click();expect(page.locator('#taskModal')).to_be_hidden();tasks=get_task_records(page);assert len(tasks)==1 and tasks[0]['repeatWeekdays']==[4] and tasks[0]['subtasks'][0]['text']=='Check the final checklist';save(str(width)+'-saved-records.json',tasks)
     observe(page,str(width)+'-saved-record')
    finally:context.close()
  finally:browser.close()
 report['assets_end']=assets();assert report['assets_end']==report['assets_start'];assert not report['page_errors'];report['passed']=True
finally:
 report['finished_at']=datetime.now(timezone.utc).isoformat();save('report.json',report);print(json.dumps({'passed':report['passed'],'observations':len(report['checks']),'output':str(O),'page_errors':report['page_errors']}),flush=True)
assert report['passed']
