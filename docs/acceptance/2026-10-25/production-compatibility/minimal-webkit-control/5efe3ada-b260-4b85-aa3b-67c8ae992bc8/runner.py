from datetime import datetime, timezone
import functools
import hashlib
import http.server
import json
import os
from pathlib import Path
import threading
import time
import traceback
import uuid
from playwright.sync_api import sync_playwright

OUT = Path('/workspace/Task-Tracer/docs/acceptance/2026-10-25/production-compatibility/minimal-webkit-control') / str(uuid.uuid4())
OUT.mkdir(parents=True, exist_ok=False)
(OUT/'runner.py').write_bytes(Path(__file__).read_bytes())
FIXTURE = OUT/'fixture'
FIXTURE.mkdir()
MARKER = 'MINIMAL-SW-CONTROL-' + OUT.name
(FIXTURE/'index.html').write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><title>Minimal offline control</title><style>body{font:24px system-ui;padding:40px;background:#eef5ff;color:#172642}main{border:2px solid #2473df;background:white;padding:24px}small{display:block;font-size:16px;margin-top:20px}</style><main id="marker">''' + MARKER + '''<small>This is an independent cache-first service-worker control, not Task Tracer.</small></main><script>navigator.serviceWorker.register('./sw.js');</script></html>''')
(FIXTURE/'sw.js').write_text('''const CACHE='minimal-offline-v1';
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(['./','./index.html'])).then(()=>self.skipWaiting())));
self.addEventListener('activate',event=>event.waitUntil(self.clients.claim()));
self.addEventListener('fetch',event=>{if(event.request.method==='GET')event.respondWith(caches.match(event.request).then(cached=>cached||fetch(event.request)));});
''')
def now():return datetime.now(timezone.utc).isoformat(timespec='milliseconds')
state={'schema_version':1,'run_id':OUT.name,'started_at':now(),'finished_at':None,'status':'running','completed':False,'engine':'webkit','actual_version':None,'fixture_marker':MARKER,'fixture_files':{p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in FIXTURE.iterdir()},'cases':[],'error':None,'scope':'Independent minimal localhost HTTP cache-first SW fixture. Does not change/read product source and cannot replace production-domain failed acceptance.'}
def save():(OUT/'report.json').write_text(json.dumps(state,indent=2)+'\n')
def record(kind,**kw):
 item={'at':now(),'kind':kind,**kw};print(json.dumps(item),flush=True);return item
class Handler(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass

def server():
 srv=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(FIXTURE)))
 th=threading.Thread(target=srv.serve_forever,daemon=True);th.start()
 return srv,th,f'http://127.0.0.1:{srv.server_port}/'

def response_info(response):
 return {'status':response.status,'from_service_worker':response.from_service_worker,'url':response.url,'body_sha256':hashlib.sha256(response.body()).hexdigest()} if response else None

def observe(page):
 try:return page.evaluate("() => ({readyState:document.readyState,online:navigator.onLine,controlled:!!navigator.serviceWorker.controller,url:location.href,text:document.querySelector('#marker')?.textContent})")
 except BaseException as exc:return {'observation_error':repr(exc),'url':page.url}

print('EVIDENCE_DIRECTORY='+str(OUT),flush=True);save()
try:
 with sync_playwright() as p:
  browser=p.webkit.launch(headless=True,timeout=30000,proxy={'server':os.environ.get('HTTPS_PROXY','http://proxy:8080'),'bypass':'127.0.0.1,localhost'})
  state['actual_version']=browser.version
  try:
   for mode in ('context_offline','server_unavailable'):
    srv,th,url=server();stopped=False
    context=browser.new_context(viewport={'width':1280,'height':800},ignore_https_errors=False)
    page=context.new_page();case={'mode':mode,'url':url,'events':[],'navigations':[],'screenshots':[]}
    state['cases'].append(case)
    page.on('pageerror',lambda error:case['events'].append({'kind':'pageerror','error':str(error)}))
    page.on('requestfailed',lambda request:case['events'].append({'kind':'requestfailed','url':request.url,'failure':request.failure}))
    try:
     first=page.goto(url,wait_until='domcontentloaded')
     page.wait_for_function("async () => navigator.serviceWorker.controller && (await caches.keys()).includes('minimal-offline-v1')")
     online=page.reload(wait_until='domcontentloaded')
     case['online_warm']={'response':response_info(online),'observation':observe(page)}
     assert online and online.from_service_worker
     assert MARKER in page.locator('#marker').inner_text()
     if mode=='context_offline':context.set_offline(True)
     else:
      srv.shutdown();srv.server_close();th.join(timeout=2);stopped=True
     try:
      response=page.reload(wait_until='domcontentloaded')
      result={'operation':'reload','status':'completed','response':response_info(response),'observation':observe(page)}
      assert MARKER in page.locator('#marker').inner_text()
      result['fixture_marker_asserted']=True
     except BaseException as exc:
      result={'operation':'reload','status':'failed','error':repr(exc),'observation':observe(page)}
     case['navigations'].append(result);record('navigation',mode=mode,**result)
     image=OUT/(mode+'-after-reload.png');page.screenshot(path=image,timeout=5000);case['screenshots'].append(image.name)
     if mode=='context_offline':
      other=context.new_page()
      try:
       response=other.goto(url,wait_until='domcontentloaded')
       result={'operation':'new_page_goto','status':'completed','response':response_info(response),'observation':observe(other)}
       assert MARKER in other.locator('#marker').inner_text();result['fixture_marker_asserted']=True
      except BaseException as exc:result={'operation':'new_page_goto','status':'failed','error':repr(exc),'observation':observe(other)}
      case['navigations'].append(result);record('navigation',mode=mode,**result)
      image=OUT/'context_offline-new-page.png';other.screenshot(path=image,timeout=5000);case['screenshots'].append(image.name)
     save()
    finally:
     context.close()
     if not stopped:srv.shutdown();srv.server_close();th.join(timeout=2)
  finally:browser.close()
 state['status']='observed'
except BaseException as exc:
 state['status']='failed';state['error']=repr(exc);state['traceback']=traceback.format_exc();print(state['traceback'],flush=True)
finally:
 state['completed']=True;state['finished_at']=now();save()
 inventory={}
 for item in sorted(OUT.rglob('*')):
  if item.is_file():
   raw=item.read_bytes();inventory[item.relative_to(OUT).as_posix()]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
 (OUT/'evidence-sha256.json').write_text(json.dumps(inventory,indent=2)+'\n')
 print('FINAL_STATUS='+state['status'],flush=True)
raise SystemExit(1 if state['status']=='failed' else 0)
