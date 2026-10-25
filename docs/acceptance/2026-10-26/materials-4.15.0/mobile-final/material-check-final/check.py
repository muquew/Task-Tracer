import json,hashlib,sys,threading,traceback,re
from pathlib import Path
from datetime import datetime,timezone
from playwright.sync_api import sync_playwright
ROOT=Path('/workspace/Task-Tracer');OUT=Path(__file__).parent;EXPECTED=sys.argv[1]
sys.path.insert(0,str(ROOT/'tools'))
from security_playwright import ProductionHeaderHandler
from smoke_playwright import ThreadingHTTPServer,get_task_records
server=ThreadingHTTPServer(('127.0.0.1',0),ProductionHeaderHandler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();url=f'http://127.0.0.1:{server.server_port}/'
actions=[];images=[];errors=[];problem=None;browser=None;context=None;source={};observations={}

def state(page):
 return page.evaluate('''() => {const v=e=>e.checkVisibility({opacityProperty:true,visibilityProperty:true}),box=e=>{const b=e.getBoundingClientRect();return{x:b.x,y:b.y,w:b.width,h:b.height}};const selectors=['header.workspace-topbar','#workspaceMobileDock','#themeToggleBtn','#languageSelect','.modal-content','#taskName','#taskProject','#noDeadline','#submitBtn','#viewTab-stats','.workspace-task-surface','.stats-action-card.overdue'];return{viewport:{w:innerWidth,h:innerHeight},docWidth:document.documentElement.scrollWidth,theme:document.documentElement.dataset.theme,accent:document.documentElement.dataset.accent,active:document.activeElement?.id,media:{reducedTransparency:matchMedia('(prefers-reduced-transparency: reduce)').matches,reducedMotion:matchMedia('(prefers-reduced-motion: reduce)').matches,forcedColors:matchMedia('(forced-colors: active)').matches},buttons:[...document.querySelectorAll('button')].filter(v).map(e=>({id:e.id,text:e.innerText,disabled:e.disabled,...box(e)})),fields:[...document.querySelectorAll('input,textarea,select')].filter(v).map(e=>({id:e.id,value:e.value,checked:e.checked,disabled:e.disabled,...box(e)})),styles:selectors.map(s=>{const e=document.querySelector(s);if(!e)return{selector:s,missing:true};const c=getComputedStyle(e);return{selector:s,visible:v(e),background:c.backgroundColor,backgroundImage:c.backgroundImage,color:c.color,appearance:c.appearance,paddingRight:c.paddingRight,backgroundRepeat:c.backgroundRepeat,backgroundPosition:c.backgroundPosition,shadow:c.boxShadow,backdrop:c.backdropFilter,outline:c.outline,animationDuration:c.animationDuration,transitionDuration:c.transitionDuration,disabled:e.disabled,checked:e.checked,...box(e)}})}}''')
def act(page,action,selector=None,value=None):
 before=state(page)
 if action=='click':page.locator(selector).click()
 elif action=='fill':page.locator(selector).fill(value)
 elif action=='select':page.locator(selector).select_option(value)
 elif action=='check':page.locator(selector).set_checked(value)
 elif action=='press':page.locator(selector).press(value)
 page.wait_for_timeout(180);actions.append({'action':action,'selector':selector,'value':value,'before':before,'after':state(page)})
def capture(page,name):
 page.wait_for_timeout(400);d=state(page);assert d['docWidth']<=d['viewport']['w'];page.screenshot(path=str(OUT/f'{name}.png'),animations='allow');(OUT/f'{name}.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');images.append(name);observations[name]=d;print(json.dumps({'capture':name,'media':d['media']},ensure_ascii=False),flush=True);return d

def styles(d):return {s['selector']:s for s in d['styles']}
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium');context=browser.new_context(viewport={'width':390,'height':844},locale='zh-CN',timezone_id='Asia/Shanghai',color_scheme='dark',reduced_motion='no-preference');page=context.new_page();page.set_default_timeout(6000);page.on('pageerror',lambda e:errors.append(str(e)))
  r=page.goto(url,wait_until='networkidle');sha=hashlib.sha256(r.body()).hexdigest();assert sha==EXPECTED
  source={'sha256':sha,'url':r.url,'status':r.status,'headers':r.all_headers(),'browser':browser.version,'at':datetime.now(timezone.utc).isoformat(),'bypassCSP':False,'fresh_context':True,'protocol':'local HTTP with unmodified ProductionHeaderHandler deployment CSP'};(OUT/'source.json').write_text(json.dumps(source,ensure_ascii=False,indent=2)+'\n')
  act(page,'click','#openModalBtn');act(page,'fill','#taskName','材质偏好检查');act(page,'fill','#taskProject','检查');act(page,'click','#submitBtn')
  if page.locator('#workspaceNotificationClose').is_visible():act(page,'click','#workspaceNotificationClose')
  before=get_task_records(page);assert len(before)==1
  act(page,'click','#openMenuBtn');act(page,'select','#themeToggleBtn','dark');act(page,'check','#workspaceTheme-berry',True)
  native_normal=state(page);(OUT/'native-selects-normal.json').write_text(json.dumps(native_normal,ensure_ascii=False,indent=2)+'\n')
  for selector in ['#themeToggleBtn','#languageSelect']:
   c=styles(native_normal)[selector];assert c['backgroundImage'].startswith('url("data:image/svg+xml'),(selector,c);assert c['backgroundRepeat']=='no-repeat' and c['paddingRight']=='42px'
  act(page,'click','#settingsBackBtn');act(page,'click','#viewTab-stats')
  cdp=context.new_cdp_session(page)
  features=[{'name':'prefers-reduced-transparency','value':'reduce'},{'name':'prefers-reduced-motion','value':'reduce'}];cdp.send('Emulation.setEmulatedMedia',{'features':features})
  d=capture(page,'01-reduced-transparency-and-motion-statistics');assert d['media']['reducedTransparency'] and d['media']['reducedMotion']
  for selector in ['header.workspace-topbar','#workspaceMobileDock']:
   c=styles(d)[selector];assert c['backdrop']=='none' and c['background'].startswith('rgb('),(selector,c)
  assert styles(d)['.stats-action-card.overdue']['disabled'] is True
  for selector in ['#viewTab-stats']:
   c=styles(d)[selector]
   for duration in c['animationDuration'].split(',')+c['transitionDuration'].split(','):
    assert float(duration.strip().removesuffix('s'))<=.000011,(selector,duration)
  features.append({'name':'forced-colors','value':'active'});cdp.send('Emulation.setEmulatedMedia',{'features':features});act(page,'click','#openModalBtn')
  d=capture(page,'02-forced-colors-editor');assert d['media']['forcedColors']
  assert styles(d)['.modal-content']['shadow']=='none' and styles(d)['#submitBtn']['backgroundImage']=='none'
  act(page,'click','#cancelBtn');act(page,'click','#openMenuBtn');act(page,'press','#themeToggleBtn','Tab')
  d=capture(page,'03-forced-colors-system-select-arrow');assert d['media']['forcedColors']
  for selector in ['#themeToggleBtn','#languageSelect']:
   c=styles(d)[selector];assert c['backgroundImage']=='none' and c['appearance']=='auto',(selector,c)
  cdp.send('Emulation.setEmulatedMedia',{'features':[]})
  d=capture(page,'04-normal-theme-select-arrow-restored');assert not d['media']['forcedColors'] and not d['media']['reducedTransparency'] and not d['media']['reducedMotion']
  for selector in ['#themeToggleBtn','#languageSelect']:
   c=styles(d)[selector];assert c['backgroundImage']==styles(native_normal)[selector]['backgroundImage'] and c['appearance']=='none',(selector,c)
  assert styles(d)['header.workspace-topbar']['backdrop']!='none'
  after=get_task_records(page);assert after==before
  (OUT/'records.json').write_text(json.dumps({'before':before,'after':after,'equal':True},ensure_ascii=False,indent=2)+'\n')
  cdp.detach();context.close();context=None;browser.close();browser=None
except Exception as e:
 problem={'type':type(e).__name__,'message':str(e),'traceback':traceback.format_exc()};print(json.dumps({'error':problem},ensure_ascii=False),flush=True)
finally:
 if context:context.close()
 if browser:browser.close()
 server.shutdown();server.server_close();thread.join(timeout=2)
 (OUT/'actions.json').write_text(json.dumps(actions,ensure_ascii=False,indent=2)+'\n')
 (OUT/'session.json').write_text(json.dumps({'source_sha256':source.get('sha256'),'source_end_sha256':hashlib.sha256((ROOT/'index.html').read_bytes()).hexdigest(),'closed':True,'pageErrors':errors,'error':problem,'screenshots':images,'actions':len(actions)},ensure_ascii=False,indent=2)+'\n')
 print('closed',flush=True)
 if problem:sys.exit(1)
