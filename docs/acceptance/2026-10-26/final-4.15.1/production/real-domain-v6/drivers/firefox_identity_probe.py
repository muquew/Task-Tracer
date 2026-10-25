"""One standard Accept-Encoding identity Firefox transport preflight; exact original body assertions retained."""
from pathlib import Path
from datetime import datetime,timezone
import importlib.util,json,subprocess,time,traceback,uuid
BASE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('driver',BASE/'driver.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
from playwright.sync_api import sync_playwright
OUT=BASE/f'firefox-identity-probe-{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")}-{uuid.uuid4().hex[:8]}';OUT.mkdir()
CACHE_JS="""async () => {const names=await caches.keys();const result=[];for(const name of names){const cache=await caches.open(name);for(const key of await cache.keys()){if(!['/','/index.html'].includes(new URL(key.url).pathname))continue;const r=await cache.match(key);const bytes=await r.arrayBuffer();const h=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(v=>v.toString(16).padStart(2,'0')).join('');result.push({cache:name,url:key.url,status:r.status,headers:Object.fromEntries(r.headers.entries()),body_sha256:h,decoded_body_bytes:bytes.byteLength});}}return result;}"""
report={'scope':'Independent single Firefox normal-TLS/proxy/trust SW reload observation. Does not replace original failed six-context acceptance.','actual_head_before':subprocess.check_output(['git','rev-parse','HEAD'],cwd=d.ROOT,text=True).strip(),'before':d.identities(),'exercise_or_original_assertions_changed':False,'automatic_retry':False,'standard_http_accept_encoding':'identity','observations_completed':False,'context_closed':False,'browser_closed':False}
profile=context=browser=None;errors=[];print('RUN_DIRECTORY',OUT,flush=True)
try:
 proxy,transport=d.production_transport();report['transport']=transport
 profile,trust=d.fresh_firefox_trust_profile();report['firefox_trust']=trust
 with sync_playwright() as pw:
  context=pw.firefox.launch_persistent_context(profile.name,headless=True,proxy=proxy,firefox_user_prefs={'security.enterprise_roots.enabled':True},viewport={'width':390,'height':844},locale='zh-CN',timezone_id='Asia/Shanghai',reduced_motion='no-preference',color_scheme='light',accept_downloads=True,ignore_https_errors=False,extra_http_headers={'Accept-Encoding':'identity'})
  browser=context.browser;report['browser_version']=browser.version;page=context.new_page();page.set_default_timeout(10000);page.on('pageerror',lambda e:errors.append(str(e)))
  initial=page.goto('https://todo.muquew.com/',wait_until='domcontentloaded');report['initial']=d.check_document(initial,'production',OUT,'document-initial');d.wait_for_app_ready(page)
  d.select_language(page,'en');d.add_task(page,'Independent Firefox reload evidence',description='Created through the actual UI for one isolated reload diagnostic.',no_deadline=True)
  before=d.read_workspace(page);d.write_json(OUT/'before-reload-db.json',before);assert len(before['tasks'])==1
  report['sw_ready']=page.evaluate("async () => {const r=await navigator.serviceWorker.ready;return {scope:r.scope,active:r.active?.state,controller:navigator.serviceWorker.controller?.scriptURL||null};}")
  page.wait_for_function('navigator.serviceWorker.controller !== null')
  report['sw_controller_before_reload']=page.evaluate('navigator.serviceWorker.controller.scriptURL')
  report['cache_before_reload']=page.evaluate(CACHE_JS)
  reloaded=page.reload(wait_until='domcontentloaded')
  report['reloaded_response']={'url':reloaded.url,'status':reloaded.status,'headers':reloaded.all_headers(),'security_details':reloaded.security_details(),'from_service_worker':reloaded.from_service_worker}
  try:
   report['reloaded_original_document_check']=d.check_document(reloaded,'production',OUT,'document-reloaded')
   report['response_body_read_succeeded']=True
  except Exception:
   report['response_body_read_succeeded']=False;report['original_body_exception']=traceback.format_exc();print(report['original_body_exception'],flush=True)
  d.wait_for_app_ready(page)
  report['original_app_ready_helper_passed_after_reload']=True
  report['actual_page']=page.evaluate("() => ({url:location.href,title:document.title,readyState:document.readyState,appReady:window.__TASK_TRACER_APP_READY__??null,taskListPresent:!!document.querySelector('#taskList'),visibleTaskNames:[...document.querySelectorAll('.task-item .task-name')].filter(n=>n.getClientRects().length).map(n=>n.innerText),controller:navigator.serviceWorker.controller?.scriptURL||null})")
  after=d.read_workspace(page);d.write_json(OUT/'after-reload-db.json',after);report['reload_every_task_field_unchanged']=d.records_by_id(before['tasks'])==d.records_by_id(after['tasks'])
  report['visible_original_task_count']=d.task_locator(page,'Independent Firefox reload evidence').count();d.expect(d.task_locator(page,'Independent Firefox reload evidence')).to_be_visible()
  report['cache_after_reload']=page.evaluate(CACHE_JS)
  report['cache_shells_all_exact_frozen_index']=bool(report['cache_after_reload']) and all(x['body_sha256']==d.EXPECTED_INDEX for x in report['cache_after_reload'])
  page.screenshot(path=str(OUT/'reloaded-normal-application.png'),animations='allow');(OUT/'reloaded-normal-application-dom.html').write_text(page.content())
  report['page_errors']=errors;report['observations_completed']=True
  context.close();report['context_closed']=True;report['browser_closed']=not browser.is_connected();context=None
except Exception:
 report['probe_exception']=traceback.format_exc();print(report['probe_exception'],flush=True)
finally:
 if context is not None:
  context.close();report['context_closed']=True;report['browser_closed']=not browser.is_connected()
 if profile is not None:
  profile.cleanup();report['firefox_trust']['temporary_profile_removed']=not Path(profile.name).exists()
 report['after']=d.identities();report['inputs_unchanged']=report['before']==report['after'];report['actual_head_after']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=d.ROOT,text=True).strip();d.write_json(OUT/'report.json',report);print('REPORT',OUT/'report.json','OBSERVATIONS_COMPLETED',report['observations_completed'],flush=True)
raise SystemExit(0 if report['observations_completed'] else 1)
