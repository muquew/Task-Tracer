"""Small transport-only check through existing managed proxy, with normal TLS; no task operations."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,importlib.util,json,sys,time,traceback,uuid
BASE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('acceptance_driver',BASE/'driver.py');driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
from playwright.sync_api import sync_playwright

def run(args):
 proxy,metadata=driver.production_transport()
 out=BASE/f'transport-preflight-{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")}-{uuid.uuid4().hex[:8]}';out.mkdir()
 before=driver.identities();report={'scope':'Transport-only normal TLS/CSP/source checks; no task operations, no production business acceptance.','before':before,'transport':metadata,'runs':[],'browsers_closed':{},'passed':False,'automatic_retry':False}
 print('RUN_DIRECTORY',out,flush=True)
 try:
  with sync_playwright() as pw:
   for engine in args.engines:
    browser=context=profile=None;trust_metadata=None;item={'engine':engine,'passed':False,'context_closed':False};start=time.monotonic()
    try:
     options=driver.browser_launch_options() if engine=='chromium' else {'headless':True}
     options['proxy']=proxy
     common=dict(viewport={'width':1280,'height':900},locale='zh-CN',timezone_id='Asia/Shanghai',reduced_motion='no-preference',color_scheme='light',ignore_https_errors=False)
     if engine=='firefox':
      profile,trust_metadata=driver.fresh_firefox_trust_profile()
      context=pw.firefox.launch_persistent_context(profile.name,**options,firefox_user_prefs={'security.enterprise_roots.enabled':True},**common)
      browser=context.browser
     else:
      browser=getattr(pw,engine).launch(**options)
      context=browser.new_context(**common,proxy=proxy)
     item['browser_version']=browser.version
     item['firefox_normal_ca_trust']=trust_metadata
     page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
     response=page.goto('https://todo.muquew.com/',wait_until='domcontentloaded')
     item['document']=driver.check_document(response,'production',out,engine+'-document')
     driver.wait_for_app_ready(page)
     item['runtime_assets']=driver.check_served_runtime(context,'https://todo.muquew.com/')
     item['page_errors']=errors
     assert not errors
     item['passed']=True
    except Exception:
     item['exception']=traceback.format_exc();print(item['exception'],flush=True)
    finally:
     if context:context.close();item['context_closed']=True
     if browser:browser.close();report['browsers_closed'][engine]=True
     if profile:
      profile.cleanup();trust_metadata['temporary_profile_removed']=not Path(profile.name).exists()
     item['duration_seconds']=round(time.monotonic()-start,3);report['runs'].append(item)
     driver.write_json(out/(engine+'-report.json'),item);print(json.dumps({'engine':engine,'passed':item['passed'],'seconds':item['duration_seconds']}),flush=True)
 finally:
  report['after']=driver.identities();report['inputs_unchanged']=before==report['after'];report['passed']=len(report['runs'])==len(args.engines) and all(x['passed'] for x in report['runs']) and report['inputs_unchanged'];driver.write_json(out/'report.json',report);print('REPORT',out/'report.json','PASS',report['passed'],flush=True)
 return 0 if report['passed'] else 1
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engines',nargs='+',choices=('chromium','firefox','webkit'),default=['chromium','firefox','webkit']);raise SystemExit(run(p.parse_args()))
