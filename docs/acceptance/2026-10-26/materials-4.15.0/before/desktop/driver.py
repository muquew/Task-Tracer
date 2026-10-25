import json, sys, threading, hashlib
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path('/workspace/Task-Tracer')
OUT = Path('/workspace/design-research/task-tracer-materials-2026-10-26/desktop-before')
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT / 'tools'))
from security_playwright import ProductionHeaderHandler
from smoke_playwright import ThreadingHTTPServer

server = None
thread = None
step = 0
page_errors = []
action_errors = []
source_sha = None

def observe(page, name):
    global step
    step += 1
    page.wait_for_timeout(500)
    path = OUT / f'{step:02d}-{name}.png'
    page.screenshot(path=str(path), animations='allow')
    data = page.evaluate('''() => {
      const box = e => {const r=e.getBoundingClientRect();return {x:Math.round(r.x),y:Math.round(r.y),w:Math.round(r.width),h:Math.round(r.height)}};
      const visible = e => e.checkVisibility({opacityProperty:true,visibilityProperty:true});
      const selectors=['#openModalBtn','#quickAddForm','#quickAddInput','#toolsDrawer','#workspaceOverview','#workspaceWeekIndex','#taskList','#workspaceTitle','#settingsWorkspace'];
      return {viewport:{w:innerWidth,h:innerHeight},scrollY,docHeight:document.documentElement.scrollHeight,docWidth:document.documentElement.scrollWidth,
        active:{id:document.activeElement?.id,className:document.activeElement?.className},title:document.title,themeColor:document.querySelector('meta[name=theme-color]')?.content,skin:{accent:document.documentElement.dataset.accent,theme:document.documentElement.dataset.theme,chromeSolid:getComputedStyle(document.documentElement).getPropertyValue('--chrome-solid').trim()},headings:[...document.querySelectorAll('h1,h2')].filter(visible).map(e=>e.innerText),
        surfaces:selectors.map(s=>{const e=document.querySelector(s);return {selector:s,visible:!!e&&visible(e),text:e?.innerText?.slice(0,80),...(e?box(e):{})}}),
        buttons:[...document.querySelectorAll('button')].filter(visible).map(e=>({id:e.id,text:e.innerText||e.getAttribute('aria-label')||e.title,...box(e)})).slice(0,65),
        fields:[...document.querySelectorAll('input,select,textarea')].filter(visible).map(e=>({id:e.id,type:e.type,value:e.value,placeholder:e.placeholder,...box(e)}))};
    }''')
    data['pageErrors'] = list(page_errors)
    data['source_index_sha256']=source_sha
    data['editor']=page.evaluate('''() => {const modal=document.querySelector('#taskModal'), body=modal.querySelector('.modal-body'), form=document.querySelector('#taskForm');const rect=e=>{const b=e.getBoundingClientRect();return {x:b.x,y:b.y,w:b.width,h:b.height}};return {modalVisible:modal.checkVisibility({opacityProperty:true,visibilityProperty:true}),modal:rect(modal.querySelector('.modal-content')),body:{...rect(body),scrollTop:form.scrollTop,scrollHeight:form.scrollHeight,clientHeight:form.clientHeight},advanced:document.querySelector('#taskAdvancedDetails').open,fields:[...form.querySelectorAll('input,textarea,select')].map(e=>({id:e.id,visible:e.checkVisibility({opacityProperty:true,visibilityProperty:true}),disabled:e.disabled,checked:e.checked,required:e.required,value:e.value,...rect(e)})),footer:rect(form.querySelector('.form-actions'))}}''')
    (OUT / f'{step:02d}-{name}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
    print(json.dumps({'step':step,'screenshot':str(path),'headings':data['headings'],'fields':[{'id':f['id'],'value':f['value']} for f in data['fields']]},ensure_ascii=False),flush=True)

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path='/usr/bin/chromium')
        context = browser.new_context(viewport={'width':1440,'height':900},locale='zh-CN',timezone_id='Asia/Shanghai',reduced_motion='no-preference',accept_downloads=True)
        page = context.new_page()
        page.set_default_timeout(6000)
        page.on('pageerror',lambda e: page_errors.append(str(e)))
        response=page.goto('https://todo.muquew.com/',wait_until='networkidle')
        source_sha=hashlib.sha256(response.body()).hexdigest()
        assert source_sha == 'e5741f889cb3c8e74d7f5885f36d5030922afa948b397579b759839ffd827f48',source_sha
        (OUT/'source.json').write_text(json.dumps({'index_sha256':source_sha,'response_headers':response.all_headers(),'browser':browser.version,'at':datetime.now(timezone.utc).isoformat(),'normal_motion':True,'bypassCSP':False,'normal_tls':True,'fresh_context':True,'url':response.url,'status':response.status},indent=2))
        observe(page,'empty-desktop')
        for line in sys.stdin:
            try:
                cmd=json.loads(line)
                action=cmd['action']
                if action=='quit': break
                if action=='reload': page.reload(wait_until='networkidle')
                elif action=='click': page.locator(cmd['selector']).click()
                elif action=='hover': page.locator(cmd['selector']).hover()
                elif action=='check': page.locator(cmd['selector']).set_checked(cmd['value'])
                elif action=='fill': page.locator(cmd['selector']).fill(cmd['value'])
                elif action=='press': page.locator(cmd['selector']).press(cmd['key'])
                elif action=='select': page.locator(cmd['selector']).select_option(cmd['value'])
                elif action=='download':
                    with page.expect_download() as pending:
                        page.locator(cmd['selector']).click()
                    item=pending.value
                    item.save_as(str(OUT / item.suggested_filename))
                    print(json.dumps({'download':str(OUT / item.suggested_filename)},ensure_ascii=False),flush=True)
                elif action=='upload': page.locator(cmd['selector']).set_input_files(cmd['path'])
                elif action=='scroll': page.mouse.wheel(0,cmd['dy'])
                elif action=='viewport': page.set_viewport_size({'width':cmd['width'],'height':cmd['height']})
                elif action=='seed':
                    for title in cmd['titles']:
                        field=page.locator('#quickAddInput')
                        field.fill(title)
                        field.press('Enter')
                        page.wait_for_function("() => document.querySelector('#quickAddInput').value === ''", timeout=6000)
                observe(page,cmd.get('name',action))
            except Exception as e:
                action_errors.append({'command':cmd,'error':str(e)})
                print(json.dumps({'error':str(e)},ensure_ascii=False),flush=True)
                observe(page,'action-error')
        context.close()
        browser.close()
finally:
    if server:
        server.shutdown();server.server_close();thread.join(timeout=2)
    (OUT/'session.json').write_text(json.dumps({'closed':True,'source_index_sha256':source_sha,'page_errors':page_errors,'action_errors':action_errors,'steps':step},ensure_ascii=False,indent=2))
    print('Browser session closed.',flush=True)
