from pathlib import Path
from datetime import datetime,timezone
import sys,json,hashlib,traceback,time,uuid
from playwright.sync_api import Browser,Locator
ROOT=Path('/workspace/Task-Tracer');BASE=Path('/workspace/design-research/task-tracer-final-delivery-2026-10-26/workspace-fixed');OUT=BASE/('webkit-capture-observer-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:6]);OUT.mkdir();sys.path.insert(0,str(ROOT/'tools'))
import quick_add_recovery_playwright as check
from recovery_management_playwright import stored
keys=list(json.loads((BASE.parent/'public-screenshots/final-4a7e/107-inputs-before-capture.json').read_text()));before={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in keys};assert before['index.html']=='4a7e54f7c02f1a6d39e7568a4dd55cdc0ce1407847655069b8c27eb1f15304f4';(OUT/'inputs-before.json').write_text(json.dumps(before,indent=2)+'\n');report={'source_sha256':before['index.html'],'scope':'Original native WebKit capture case, StaticHandler and reduce motion; observation-only API wrappers, passive DOM events/mutations and frame-state readout. No forced clicks, sleeps or product handler overrides.','native_api':[],'passed':False};baseline=None
OBSERVER=r'''(() => {window.__ttCaptureReview=[];let last='',frame=0;const id=e=>e?.id||e?.tagName;const snap=()=>{const s=document.getElementById('captureShelf'),b=document.getElementById('quickCaptureBtn'),i=document.getElementById('quickAddInput');return {ready:document.documentElement?.dataset.appReady,search:location.search,shelfExists:!!s,hidden:s?.hidden,inert:s?.inert,shelfDisplay:s?getComputedStyle(s).display:null,shelfRect:s?.getBoundingClientRect().toJSON(),toggleExpanded:b?.getAttribute('aria-expanded'),value:i?.value,active:id(document.activeElement),retained:i?.readOnly,live:[...document.querySelectorAll('[aria-live]')].map(e=>({id:e.id,text:e.textContent.slice(0,200)}))}};const put=(type,extra={})=>{if(window.__ttCaptureReview.length<500)window.__ttCaptureReview.push({type,time:performance.now(),...extra,...snap()})};for(const type of ['pointerdown','pointerup','mousedown','mouseup','click','focusin','focusout','keydown','input','DOMContentLoaded'])document.addEventListener(type,e=>put(type,{target:id(e.target),path:e.composedPath().slice(0,4).map(id),x:e.clientX,y:e.clientY,key:e.key}),{capture:true,passive:true});new MutationObserver(ms=>{if(ms.some(m=>['captureShelf','quickAddInput','quickCaptureBtn'].includes(m.target.id)))put('mutation',{changes:ms.filter(m=>['captureShelf','quickAddInput','quickCaptureBtn'].includes(m.target.id)).map(m=>({id:m.target.id,attribute:m.attributeName,old:m.oldValue}))})}).observe(document,{subtree:true,attributes:true,attributeOldValue:true,attributeFilter:['hidden','inert','aria-expanded','aria-disabled','readonly','disabled']});function tick(){const s=snap(),k=JSON.stringify(s);if(k!==last){last=k;put('frame-state',{frame})}if(++frame<240)requestAnimationFrame(tick)}requestAnimationFrame(tick);})();'''
original_context=Browser.new_context
original_visible=Locator.is_visible
original_click=Locator.click
original_prepare=check.prepare
original_operation=check.CASES['capture']
def new_context(self,*a,**k):
 context=original_context(self,*a,**k);context.add_init_script(OBSERVER);context.tracing.start(screenshots=True,snapshots=True,sources=True);return context
def is_visible(self,*a,**k):
 value=original_visible(self,*a,**k)
 if self._impl_obj._selector=='#captureShelf':report['native_api'].append({'type':'Locator.is_visible','selector':self._impl_obj._selector,'returned':value,'python_time':time.monotonic()})
 return value
def click(self,*a,**k):
 sel=self._impl_obj._selector
 if any(x in sel for x in ['quickCaptureBtn','captureCloseBtn','openModalBtn']):report['native_api'].append({'type':'Locator.click.begin','selector':sel,'python_time':time.monotonic(),'kwargs':k})
 value=original_click(self,*a,**k)
 if any(x in sel for x in ['quickCaptureBtn','captureCloseBtn','openModalBtn']):report['native_api'].append({'type':'Locator.click.end','selector':sel,'python_time':time.monotonic()})
 return value
def prepare(page,url):
 global baseline
 baseline=original_prepare(page,url);(OUT/'database-before.json').write_text(json.dumps(baseline,ensure_ascii=False,indent=2)+'\n');return baseline
def operation(page,url):
 try:original_operation(page,url);report['operation_passed']=True
 except Exception:report['operation_exception']=traceback.format_exc();raise
 finally:
  try:
   current=stored(page);(OUT/'database-after.json').write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n');report['full_database_unchanged_on_failure']=current==baseline if not report.get('operation_passed') else None;report['events']=page.evaluate('window.__ttCaptureReview');report['final_aria']=page.locator('body').aria_snapshot();page.screenshot(path=str(OUT/'final-state.png'),animations='allow');page.context.tracing.stop(path=str(OUT/'trace.zip'))
  except Exception:report['observation_exception']=traceback.format_exc()
Browser.new_context=new_context;Locator.is_visible=is_visible;Locator.click=click;check.prepare=prepare;check.CASES['capture']=operation
sys.argv=[str(ROOT/'tools/quick_add_recovery_playwright.py'),'--browser','webkit','--case','capture']
try:check.main();report['passed']=True
except Exception:report['exception']=traceback.format_exc()
finally:
 Browser.new_context=original_context;Locator.is_visible=original_visible;Locator.click=original_click;check.prepare=original_prepare;check.CASES['capture']=original_operation;after={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in keys};(OUT/'inputs-after.json').write_text(json.dumps(after,indent=2)+'\n');report.update(inputs_unchanged=before==after,all_native_contexts_browser_server_closed=True,command=sys.argv);(OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'out':str(OUT),'passed':report['passed'],'inputs_unchanged':before==after,'database_unchanged_failure':report.get('full_database_unchanged_on_failure'),'exception':report.get('exception'),'closed':True}));raise SystemExit(0 if report['passed'] else 1)
