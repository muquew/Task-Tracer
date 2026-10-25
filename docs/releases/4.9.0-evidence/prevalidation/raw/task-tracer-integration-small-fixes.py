import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,'/workspace/Task-Tracer-redesign/tools')
from smoke_playwright import local_server,wait_for_app_ready,clear_app_data,exercise_task_action_menu_viewport,add_task
from playwright.sync_api import sync_playwright,expect
with local_server() as url,sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True)
 context=browser.new_context(locale='en-US',viewport={'width':1280,'height':720},reduced_motion='reduce')
 page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 clear_app_data(page,url)
 print("sha",hashlib.sha256(page.request.get(url).body()).hexdigest(),hashlib.sha256(Path("/workspace/Task-Tracer-redesign/index.html").read_bytes()).hexdigest(),flush=True)
 print("function_loaded","positionTaskActionMenu(button, menu);" in page.content(),flush=True)
 try:
  exercise_task_action_menu_viewport(page)
 except Exception:
  print("DEBUG_MENU",page.locator(".task-action-menu:not([hidden])").evaluate('node=>({style:node.getAttribute("style"), parent:node.offsetParent?.className,computedTop:getComputedStyle(node).top,position:getComputedStyle(node).position,transform:getComputedStyle(node).transform,rect:node.getBoundingClientRect().toJSON(),parentRect:node.offsetParent.getBoundingClientRect().toJSON(),animations:node.getAnimations().map(a=>({type:a.constructor.name,frames:a.effect.getKeyframes()}))})'),"errors",errors,flush=True)
  raise
 clear_app_data(page,url)
 add_task(page,'Geometry one',project='Project name with a long literal label and extra words to fill the menu',no_deadline=True)
 add_task(page,'Geometry two',project='{"kind":"all"}',no_deadline=True)
 for width,height in [(390,844),(320,568)]:
  page.set_viewport_size({'width':width,'height':height});page.evaluate('scrollTo(0,0)')
  for trigger,menu in [('projectFilterBtn','projectFilterMenu'),('filterBtn','filterMenu'),('sortBtn','sortMenu')]:
   page.locator('#'+trigger).click();expect(page.locator('#'+menu)).to_be_visible()
   page.locator('#'+menu).evaluate('node=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
   rect=page.locator('#'+menu).evaluate('node=>{const r=node.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:innerWidth,height:innerHeight}}')
   assert rect['left']>=0 and rect['right']<=width and rect['top']>=0 and rect['bottom']<=height,rect
   print(json.dumps({'viewport':width,'menu':menu,'rect':rect}),flush=True)
   page.keyboard.press('Escape')
 print('storage description foreground',page.locator('#storageUnavailableMessage').evaluate('node=>getComputedStyle(node).color'))
 print('pageerrors',errors);assert not errors
 context.close();browser.close()
