from pathlib import Path
import sys,json,threading
ROOT=Path('/workspace/Task-Tracer-redesign')
SNAPSHOT=Path('/tmp/task-tracer-redesign-affected-rerun-q1339v85/inputs')
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
import smoke_playwright as smoke
import security_playwright as security
from playwright.sync_api import sync_playwright,expect
smoke.REPO_ROOT=SNAPSHOT
security.ROOT=SNAPSHOT
server=smoke.ThreadingHTTPServer(('127.0.0.1',0),security.ProductionHeaderHandler)
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
report={'phase':'original frozen source geometry diagnostic, not candidate acceptance','snapshot':str(SNAPSHOT),'index_sha256':'5ffc00400907898394e838a6ee2743c628a897f0c72b020da0fa98838468c6ed','observations':[]}
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(**smoke.browser_launch_options())
  page=browser.new_page(viewport={'width':390,'height':844},reduced_motion='reduce')
  errors=[];console=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.on('console',lambda m:console.append(m.text) if m.type=='error' else None)
  smoke.clear_app_data(page,f'http://127.0.0.1:{server.server_port}/')
  smoke.add_task(page,'Menu geometry diagnostic',no_deadline=True,project='Sidebar full project')
  for name,button,menu in [('project','#projectFilterBtn','#projectFilterMenu'),('status','#filterBtn','#filterMenu'),('sort','#sortBtn','#sortMenu')]:
   page.locator(button).click();expect(page.locator(menu)).to_be_visible()
   box=page.locator(menu).bounding_box();button_box=page.locator(button).bounding_box()
   shot=OUT/f'{name}-390.png';page.screenshot(path=shot,full_page=True,animations='disabled')
   report['observations'].append({'menu':name,'button':button_box,'box':box,'viewport':page.viewport_size,'screenshot':str(shot)})
   page.keyboard.press('Escape');expect(page.locator(menu)).to_be_hidden()
  report.update(browser=browser.version,page_errors=errors,console_errors=console)
  browser.close()
finally:
 server.shutdown();server.server_close();thread.join(timeout=2)
 (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
