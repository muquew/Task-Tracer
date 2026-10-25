import sys,json,threading,traceback
from pathlib import Path
sys.path.insert(0,'/workspace/Task-Tracer/tools')
from playwright.sync_api import sync_playwright,expect
from security_playwright import ProductionHeaderHandler
from smoke_playwright import ThreadingHTTPServer,clear_app_data,add_task,task_locator,get_task_records,select_view,open_settings,return_to_task_workspace,reveal_workspace_control,close_workspace_navigation
OUT=Path('/workspace/design-research/task-tracer-direct-2026-10-25/independent-detail-review')
server=ThreadingHTTPServer(('127.0.0.1',0),ProductionHeaderHandler)
threading.Thread(target=server.serve_forever,daemon=True).start()
url=f'http://127.0.0.1:{server.server_port}/'
pw=sync_playwright().start()
browser=pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
context=browser.new_context(viewport={'width':1440,'height':1000},locale='zh-CN',timezone_id='Asia/Shanghai')
page=context.new_page()
errors=[]
page.on('pageerror',lambda e:errors.append(str(e)))
clear_app_data(page,url)
def snap():
    return page.locator('body').aria_snapshot()
def shot(name):
    page.screenshot(path=str(OUT/name),full_page=True)
    return str(OUT/name)
def cards():
    return page.locator('.task-item').all_text_contents()
print(json.dumps({'ready':url,'title':page.title(),'snapshot':snap()},ensure_ascii=False),flush=True)
for line in sys.stdin:
    try:
        cmd=json.loads(line)
        result=eval(compile(cmd['code'],'<audit>','eval'),globals()) if cmd.get('mode','eval')=='eval' else exec(compile(cmd['code'],'<audit>','exec'),globals())
        print(json.dumps({'ok':True,'result':result},ensure_ascii=False,default=str),flush=True)
    except Exception as e:
        print(json.dumps({'ok':False,'error':str(e),'trace':traceback.format_exc()},ensure_ascii=False),flush=True)
try: browser.close();pw.stop();server.shutdown()
except: pass
