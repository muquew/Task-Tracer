import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,'/workspace/Task-Tracer-redesign/tools')
from smoke_playwright import local_server,wait_for_app_ready
from playwright.sync_api import sync_playwright,expect
with local_server() as url,sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True)
 c=b.new_context(locale='en-US',viewport={'width':1440,'height':1024},reduced_motion='reduce')
 page=c.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(url);wait_for_app_ready(page)
 print('source',hashlib.sha256(page.request.get(url).body()).hexdigest(),flush=True)
 for width,height in [(1440,1024),(390,844),(320,568)]:
  page.set_viewport_size({'width':width,'height':height})
  page.locator('#searchInput').fill('A long query that should never sit under the search clear or keyboard hint')
  for name in ['quickAddInput','searchInput']:
   data=page.locator('#'+name).evaluate('input=>{const c=getComputedStyle(input),r=input.getBoundingClientRect(),icon=input.parentElement.querySelector("svg.icon"),clear=input.parentElement.querySelector("#clearSearchBtn"),hint=input.parentElement.querySelector(".shortcut-hint");return {id:input.id,padding:[c.paddingTop,c.paddingRight,c.paddingBottom,c.paddingLeft],font:c.fontSize,minHeight:c.minHeight,height:r.height,rect:r.toJSON(),icon:icon?.getBoundingClientRect().toJSON(),clear:clear?.getBoundingClientRect().toJSON(),hint:hint?.getBoundingClientRect().toJSON(),hintDisplay:hint&&getComputedStyle(hint).display}}')
   print(json.dumps({'width':width,'field':data}),flush=True)
  page.keyboard.press('Control+p');expect(page.locator('#commandPalette')).to_be_visible()
  data=page.locator('#commandPaletteInput').evaluate('input=>{const c=getComputedStyle(input),r=input.getBoundingClientRect(),icon=input.parentElement.querySelector("svg.icon");return {id:input.id,padding:[c.paddingTop,c.paddingRight,c.paddingBottom,c.paddingLeft],font:c.fontSize,minHeight:c.minHeight,height:r.height,rect:r.toJSON(),icon:icon.getBoundingClientRect().toJSON()}}')
  print(json.dumps({'width':width,'field':data}),flush=True)
  page.keyboard.press('Escape');expect(page.locator('#commandPalette')).to_be_hidden();page.locator('#searchInput').fill('')
 print('pageerrors',errors);assert not errors
 c.close();b.close()
