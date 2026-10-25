import json,hashlib,sys
from pathlib import Path
from datetime import datetime,timezone
from playwright.sync_api import sync_playwright
OUT=Path(__file__).parent
errors=[]; actions=[]; images=[]; step=0

def dom(page):
 return page.evaluate('''() => {const v=e=>e.checkVisibility({opacityProperty:true,visibilityProperty:true});const rect=e=>{const b=e.getBoundingClientRect();return{x:b.x,y:b.y,w:b.width,h:b.height}};return {viewport:{width:innerWidth,height:innerHeight},docWidth:document.documentElement.scrollWidth,theme:document.documentElement.dataset.theme,accent:document.documentElement.dataset.accent,headings:[...document.querySelectorAll('h1,h2,h3')].filter(v).map(e=>e.innerText),buttons:[...document.querySelectorAll('button')].filter(v).map(e=>({id:e.id,text:e.innerText,aria:e.getAttribute('aria-label'),class:e.className,...rect(e)})),fields:[...document.querySelectorAll('input,select,textarea')].filter(v).map(e=>({id:e.id,value:e.value,checked:e.checked,...rect(e)})),surfaces:['body','.workspace-header','.workspace-page-header','#workspaceDayStrip','.task-item','#taskModal .modal-content','#taskModal .modal-header','#taskModal .form-actions','.task-editor-properties','.form-control','.task-action-menu','.settings-card','.stats-action-panel','#workspaceMobileDock'].map(s=>{const e=document.querySelector(s);if(!e)return{selector:s,missing:true};const c=getComputedStyle(e);return{selector:s,visible:v(e),background:c.background,backgroundColor:c.backgroundColor,color:c.color,border:c.border,boxShadow:c.boxShadow,backdropFilter:c.backdropFilter,borderRadius:c.borderRadius,...rect(e)}})}}''')

try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium')
  context=browser.new_context(viewport={'width':390,'height':844},locale='zh-CN',timezone_id='Asia/Shanghai',reduced_motion='no-preference')
  page=context.new_page();page.set_default_timeout(6000);page.on('pageerror',lambda e:errors.append(str(e)))
  r=page.goto('https://todo.muquew.com/',wait_until='networkidle');sha=hashlib.sha256(r.body()).hexdigest();assert sha=='e5741f889cb3c8e74d7f5885f36d5030922afa948b397579b759839ffd827f48',sha
  (OUT/'source.json').write_text(json.dumps({'sha256':sha,'status':r.status,'url':r.url,'headers':r.all_headers(),'captured':datetime.now(timezone.utc).isoformat(),'browser':browser.version,'bypassCSP':False,'normalMotion':True,'fresh_context':True,'normal_tls':True},indent=2))
  print(json.dumps(dom(page),ensure_ascii=False),flush=True)
  for line in sys.stdin:
   cmd=json.loads(line);before=dom(page)
   if cmd['action']=='quit':break
   try:
    a=cmd['action'];s=cmd.get('selector')
    if a=='click':page.locator(s).click()
    elif a=='fill':page.locator(s).fill(cmd['value'])
    elif a=='select':page.locator(s).select_option(cmd['value'])
    elif a=='check':page.locator(s).set_checked(cmd['value'])
    elif a=='press':page.locator(s).press(cmd['key'])
    elif a=='viewport':page.set_viewport_size({'width':cmd['width'],'height':cmd['height']})
    elif a=='scroll':page.mouse.wheel(0,cmd['dy'])
    elif a=='capture':pass
    page.wait_for_timeout(400)
    after=dom(page);actions.append({'command':cmd,'before':before,'after':after})
    if a=='capture':
     step+=1;name=f'{step:02d}-{cmd["name"]}';page.screenshot(path=str(OUT/f'{name}.png'),animations='allow');(OUT/f'{name}.json').write_text(json.dumps(after,ensure_ascii=False,indent=2));images.append(name)
    print(json.dumps({'action':cmd,'after':after},ensure_ascii=False),flush=True)
   except Exception as e:
    actions.append({'command':cmd,'error':str(e),'before':before});print(json.dumps({'error':str(e)}),flush=True)
  context.close();browser.close()
finally:
 (OUT/'actions.json').write_text(json.dumps(actions,ensure_ascii=False,indent=2))
 (OUT/'session.json').write_text(json.dumps({'closed':True,'pageErrors':errors,'actionErrors':[a for a in actions if 'error'in a],'screenshots':images,'actions':len(actions)},ensure_ascii=False,indent=2))
 print('closed',flush=True)
