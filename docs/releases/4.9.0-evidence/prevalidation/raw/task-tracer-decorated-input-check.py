import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,'/workspace/Task-Tracer-redesign/tools')
from smoke_playwright import local_server,wait_for_app_ready
from playwright.sync_api import sync_playwright,expect
with local_server() as url,sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True)
 context=browser.new_context(locale='en-US',viewport={'width':1440,'height':1024},reduced_motion='reduce')
 page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(url);wait_for_app_ready(page)
 disk=hashlib.sha256(Path('/workspace/Task-Tracer-redesign/index.html').read_bytes()).hexdigest()
 assert hashlib.sha256(page.request.get(url).body()).hexdigest()==disk
 print('source',disk,flush=True)
 longtext='A long English input value with punctuation and several words to inspect the text boundary. '*8
 def measure(name):
  return page.locator('#'+name).evaluate('input=>{const c=getComputedStyle(input),r=input.getBoundingClientRect(),leading=input.parentElement.querySelector(\":scope > svg.icon\"),clear=input.parentElement.querySelector(\"#clearSearchBtn\"),hint=input.parentElement.querySelector(\".shortcut-hint\");return {id:input.id,padding:[c.paddingTop,c.paddingRight,c.paddingBottom,c.paddingLeft],font:c.fontSize,minHeight:c.minHeight,height:r.height,start:r.left+parseFloat(c.borderLeftWidth)+parseFloat(c.paddingLeft),end:r.right-parseFloat(c.borderRightWidth)-parseFloat(c.paddingRight),leading:leading?.getBoundingClientRect().toJSON(),clear:clear?.getBoundingClientRect().toJSON(),hint:hint?.getBoundingClientRect().toJSON(),hintDisplay:hint&&getComputedStyle(hint).display,scrollLeft:input.scrollLeft}}')
 for width,height in [(1440,1024),(779,844),(390,844),(320,568)]:
  page.set_viewport_size({'width':width,'height':height})
  page.locator('#quickAddInput').fill(longtext)
  quick=measure('quickAddInput');assert quick['padding'][3]=='40px' and quick['start']>=quick['leading']['right']+8,quick
  page.locator('#searchInput').fill(longtext)
  expect(page.locator('#clearSearchBtn')).to_be_visible()
  search=measure('searchInput');assert search['end']<=search['clear']['left']-4,search
  if width<=779:
   assert search['padding'][1]=='40px' and search['padding'][3]=='9px' and search['minHeight']=='36px' and search['font']=='12px' and search['hintDisplay']=='none',search
  else:
   assert search['padding'][1]=='86px' and search['end']<=search['hint']['left']-4,search
  page.locator('#clearSearchBtn').click();expect(page.locator('#searchInput')).to_have_value('');expect(page.locator('#clearSearchBtn')).to_be_hidden()
  page.keyboard.press('Control+p');expect(page.locator('#commandPalette')).to_be_visible()
  page.locator('#commandPaletteInput').fill('task');expect(page.locator('#commandPaletteInput')).to_have_value('task')
  command=measure('commandPaletteInput');assert command['padding'][3]=='40px' and command['minHeight']=='44px' and command['start']>=command['leading']['right']+8,command
  page.keyboard.press('Escape');expect(page.locator('#commandPalette')).to_be_hidden()
  expect(page.locator('#quickAddInput')).to_have_value(longtext)
  page.locator('#quickAddInput').fill('')
  print(json.dumps({'viewport':width,'quick':quick,'search':search,'command':command,'clear_and_palette_interactions':True}),flush=True)
 assert not errors,errors
 print('pageerrors',errors)
 context.close();browser.close()
