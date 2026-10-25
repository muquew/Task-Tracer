from pathlib import Path
import json,sys,time,os
ROOT=Path('/workspace/Task-Tracer-craft')
sys.path.insert(0,str(ROOT/'tools'))
from playwright.sync_api import Page,sync_playwright
from smoke_playwright import local_server,browser_launch_options,clear_app_data,exercise_workspace_navigation
import accessibility_i18n_audit as audit
original_evaluate=Page.evaluate
original_wait=Page.wait_for_function

def wait(self, expression, **kwargs):
 import re
 if not re.match(r'^\s*(?:(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>|(?:async\s+)?function\b)',expression): expression='() => ('+expression+')'
 return original_wait(self,expression,**kwargs)
Page.wait_for_function=wait
DUMP='''() => ({visibility:document.visibilityState,focus:document.hasFocus(),animations:document.getAnimations().map(a=>({playState:a.playState,currentTime:a.currentTime,startTime:a.startTime,pending:a.pending,id:a.id,type:a.constructor.name,timing:a.effect?.getTiming(),computed:a.effect?.getComputedTiming(),target:a.effect?.target?.outerHTML?.slice(0,250),style:a.effect?.target?{display:getComputedStyle(a.effect.target).display,visibility:getComputedStyle(a.effect.target).visibility}:null}))})'''
count=0

def evaluate(self,expression,arg=None):
 global count
 special=('getAnimations()' in expression and '.finished' in expression) or 'axe.run(' in expression
 if not special: return original_evaluate(self,expression,arg)
 count+=1
 kind='animation' if 'getAnimations()' in expression else 'axe'
 print('BEGIN',count,kind,flush=True)
 before=original_evaluate(self,DUMP)
 print('BEFORE',json.dumps(before),flush=True)
 wrapped='''async () => {
 const source = SOURCE;
 let timer;
 try {return await Promise.race([source(),new Promise((resolve,reject)=>{timer=setTimeout(()=>reject(new Error('DIAGNOSTIC 10s timeout')),10000)})]);}
 finally {clearTimeout(timer);}
}'''.replace('SOURCE','('+expression+')')
 started=time.monotonic()
 try:
  result=original_evaluate(self,wrapped)
  print('END',count,kind,round(time.monotonic()-started,3),flush=True)
  return result
 except Exception:
  print('TIMEOUT/ERROR',count,kind,json.dumps(original_evaluate(self,DUMP)),flush=True)
  raise
Page.evaluate=evaluate
OUT=Path(__file__).parent
with local_server() as url,sync_playwright() as p:
 browser=p.chromium.launch(**browser_launch_options())
 context=browser.new_context(viewport={'width':1280,'height':720},reduced_motion='no-preference')
 page=context.new_page();page.set_default_timeout(6000)
 try:
  print('CLEAR',flush=True);clear_app_data(page,url)
  print('NAV',flush=True);exercise_workspace_navigation(page)
  print('EMPTY AUDIT',flush=True);audit.audit_page_state(page,audit.find_axe_source().read_text(),'empty task list')
  print('SEED',flush=True);audit.seed_tasks(page)
  print('CHECKBOX AUDIT',flush=True);audit.audit_subtask_checkbox_visibility(page,'1280 diagnostic')
  print('POST CHECKBOX',json.dumps(original_evaluate(page,DUMP)),flush=True)
  print('TASK LIST AUDIT',flush=True);audit.audit_page_state(page,audit.find_axe_source().read_text(),'task list')
  print('PREFIX COMPLETE',flush=True)
 finally:
  page.screenshot(path=str(OUT/'final.png'))
  (OUT/'final-state.json').write_text(json.dumps(original_evaluate(page,DUMP),indent=2))
  context.close();browser.close()
