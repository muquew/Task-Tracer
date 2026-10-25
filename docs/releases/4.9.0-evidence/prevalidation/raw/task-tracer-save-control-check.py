import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,'/workspace/Task-Tracer-redesign/tools')
from smoke_playwright import local_server,wait_for_app_ready
from playwright.sync_api import sync_playwright,expect
with local_server() as url,sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True)
 c=b.new_context(locale='zh-CN',viewport={'width':700,'height':844},reduced_motion='reduce')
 page=c.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(url);wait_for_app_ready(page)
 assert hashlib.sha256(page.request.get(url).body()).hexdigest()==hashlib.sha256(Path('/workspace/Task-Tracer-redesign/index.html').read_bytes()).hexdigest()
 for width in [700,420,390,320]:
  page.set_viewport_size({'width':width,'height':844})
  geometry=page.locator('#saveSmartViewBtn').evaluate('button=>{const r=button.getBoundingClientRect(),c=button.closest(".toolbar-main-row").getBoundingClientRect();const hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return {button:r.toJSON(),row:c.toJSON(),width:innerWidth,scroll:document.documentElement.scrollWidth,hit:hit===button||button.contains(hit)}}')
  r=geometry['button'];row=geometry['row']
  assert r['width']==32 and r['height']==36,geometry
  assert r['left']>=row['left'] and r['right']<=row['right'],geometry
  assert geometry['scroll']==width and geometry['hit'],geometry
  page.locator('#saveSmartViewBtn').click();expect(page.locator('#taskModal')).to_be_visible()
  page.locator('#cancelBtn').click();expect(page.locator('#taskModal')).to_be_hidden()
  print(json.dumps({'viewport':width,'geometry':geometry,'ordinary_pointer_save_cancel':True}),flush=True)
 assert not errors,errors
 print('pageerrors',errors)
 c.close();b.close()
