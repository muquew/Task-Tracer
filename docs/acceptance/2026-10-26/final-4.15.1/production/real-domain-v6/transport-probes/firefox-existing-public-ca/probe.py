from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlsplit,unquote
import os,sys,json,hashlib,argparse
from playwright.sync_api import sync_playwright
O=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['enterprise-roots','nss-profile'],required=True);parser.add_argument('--profile',type=Path);a=parser.parse_args()
D=O/a.mode;D.mkdir(exist_ok=True)
u=urlsplit(os.environ.get('HTTPS_PROXY') or os.environ['HTTP_PROXY']);proxy={'server':f'{u.scheme}://{u.hostname}:{u.port or (443 if u.scheme=="https" else 80)}'}
if u.username is not None:proxy['username']=unquote(u.username)
if u.password is not None:proxy['password']=unquote(u.password)
bypass=os.environ.get('NO_PROXY') or os.environ.get('no_proxy')
if bypass:proxy['bypass']=bypass
ca=Path(os.environ['NODE_EXTRA_CA_CERTS']);prefs={'security.enterprise_roots.enabled':True}
result={'at':datetime.now(timezone.utc).isoformat(),'mode':a.mode,'configured_ca_path':str(ca),'configured_ca_sha256':hashlib.sha256(ca.read_bytes()).hexdigest(),'configured_ca_is_existing_enterprise_root_not_site_leaf':True,'tls_validation_enabled':True,'ignore_https_errors':False,'firefox_user_prefs':prefs,'explicit_managed_launch_and_context_proxy':True,'proxy_credentials_present':u.username is not None or u.password is not None,'proxy_and_pem_values_recorded':False,'headless':True,'page_url':'https://todo.muquew.com/','browser_closed':False,'application_crud_or_fullsuite_run':False}
browser=None;context=None
try:
 with sync_playwright() as p:
  if a.mode=='enterprise-roots':
   browser=p.firefox.launch(headless=True,firefox_user_prefs=prefs,proxy=proxy)
   result['browser_version']=browser.version
   context=browser.new_context(proxy=proxy,ignore_https_errors=False,viewport={'width':1280,'height':800})
  else:
   assert a.profile and a.profile.is_dir()
   context=p.firefox.launch_persistent_context(str(a.profile),headless=True,firefox_user_prefs=prefs,proxy=proxy,ignore_https_errors=False,viewport={'width':1280,'height':800})
   result['browser_version']=context.browser.version;result['isolated_user_profile']=str(a.profile)
  try:
   page=context.new_page();response=page.goto('https://todo.muquew.com/',wait_until='domcontentloaded',timeout=45000)
   assert response is not None
   result['status']=response.status;result['security_details']=response.security_details();result['source_sha256']=hashlib.sha256(response.body()).hexdigest();result['csp_present']=bool(response.header_value('content-security-policy'));result['page_title']=page.title()
   assert response.status==200 and result['source_sha256']=='89b5081b6fe1610c54cd5bab5f87196aad6ff04ecb02a1f30d8bcf0b67d0bc30'
   api=context.request.get('https://todo.muquew.com/',timeout=45000)
   result['context_request_homepage_status']=api.status;result['context_request_homepage_source_sha256']=hashlib.sha256(api.body()).hexdigest()
   assert api.status==200 and result['context_request_homepage_source_sha256']==result['source_sha256']
   result['passed']=True
  finally:
   context.close();result['context_closed']=True
   if browser:browser.close();result['browser_closed']=not browser.is_connected()
   else:result['browser_closed']=not context.browser.is_connected()
except Exception as error:
 message=str(error)
 for secret in (u.username,u.password):
  if secret:message=message.replace(secret,'[redacted]')
 result['passed']=False;result['error_type']=type(error).__name__;result['error']=message
(D/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
raise SystemExit(0 if result.get('passed') else 1)
