"""Launch the six-context environment-adapted production driver after matched-deployment and transport preflight signals."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, os, re, signal, subprocess, sys, time, uuid
ROOT=Path('/workspace/Task-Tracer')
BASE=Path(__file__).resolve().parent
DRIVER=BASE/'driver.py'
DRIVER_SHA256='7916c766d2be8f2d7c707ed054966a6f8a3e89d495cf28f7734b9ed3067b25ff'
ENV={'PYTHONDONTWRITEBYTECODE':'1','TASK_TRACER_BROWSER_EXECUTABLE':'/usr/bin/chromium','XDG_CACHE_HOME':'/workspace/.cache','PLAYWRIGHT_BROWSERS_PATH':'/workspace/.cache/ms-playwright','LD_LIBRARY_PATH':'/workspace/.cache/browser-libs/root/usr/lib/x86_64-linux-gnu','PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS':'1'}
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def head():return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def run():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--deployment-matched',action='store_true');args=parser.parse_args()
 if not args.deployment_matched:raise SystemExit('No execution: parent main/Vercel static-match signal is required.')
 assert sha(DRIVER)==DRIVER_SHA256,'Environment-adapted production driver changed'
 prepared=json.loads((BASE.parent/'production-final-v5'/'preparation-receipt.json').read_text())
 transport=json.loads((BASE.parent/'production-final-v6-env'/'transport-preflight-20261025T224824Z-35cab002'/'report.json').read_text());assert transport['passed'] and len(transport['runs'])==3 and transport['inputs_unchanged'],'Three-engine normal-TLS transport preflight is required'
 assert transport['before']['runtime']==runtime and transport['before']['helpers']==helpers,'Transport preflight runtime/helper bytes differ'
 identity_path=BASE.parent/'production-final-v6-env'/'firefox-identity-pref-probe-20261025T225244Z-39ff025d'/'report.json';assert sha(identity_path)=='646de44cfa749025fe1b15c8b5f77e6dd784b05741e772257dcb560365c94884'
 identity=json.loads(identity_path.read_text());assert identity['observations_completed'] and identity['response_body_read_succeeded'] and identity['reload_every_task_field_unchanged'] and identity['cache_shells_all_exact_frozen_index'] and identity['inputs_unchanged'] and not identity['page_errors'],'Strict original-body/cache/DB identity preflight is required'
 assert identity['initial']['index_sha256']==runtime['index.html'] and identity['reloaded_original_document_check']['index_sha256']==runtime['index.html'] and identity['before']['runtime']==runtime and identity['before']['helpers']==helpers,'Identity preflight input/source hashes differ'
 runtime={name:sha(ROOT/name) for name in prepared['runtime_before']}
 helpers={name:sha(ROOT/name) for name in prepared['actual_helpers_before']}
 assert runtime==prepared['runtime_before'] and helpers==prepared['actual_helpers_before'],'Actual runtime/helper bytes differ from six-context green rehearsal'
 assert os.environ.get('NODE_TLS_REJECT_UNAUTHORIZED')!='0' and os.environ.get('PYTHONHTTPSVERIFY')!='0','Normal TLS verification is required'
 out=BASE/f'production-launch-{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")}-{uuid.uuid4().hex[:8]}';out.mkdir()
 command=[sys.executable,str(DRIVER),'--mode','production','--url','https://todo.muquew.com/']
 before=head();clock=time.monotonic();receipt={'started_at_utc':datetime.now(timezone.utc).isoformat(),'command':command,'cwd':str(ROOT),'environment_overrides':ENV,'driver_sha256':DRIVER_SHA256,'actual_head_before':before,'runtime_before':runtime,'helpers_before':helpers,'wrapper_scope':'Only launch/receipt capture. Production proxy, normal existing-CA trust and Firefox-only standard identity HTTP negotiation adaptation is external; original exercise and all other assertion functions are byte-identical. Six fresh real-UI contexts and assertions retained. Firefox uses two unique temporary trusted-CA profiles and two browser launches, Chromium/WebKit one browser launch each (four total); no profile/NSS databases archived. HEAD is observed, not hardcoded.','passed':False}
 env=os.environ.copy();env.update(ENV);child=None
 write(out/'started.json',receipt);print('LAUNCH_DIRECTORY',out,flush=True)
 try:
  with (out/'stdout.log').open('w') as stdout,(out/'stderr.log').open('w') as stderr:
   child=subprocess.Popen(command,cwd=ROOT,env=env,stdout=stdout,stderr=stderr,start_new_session=True)
   try:receipt['exit_code']=child.wait()
   except BaseException:
    os.killpg(child.pid,signal.SIGTERM);child.wait();receipt['interrupted']=True;raise
  match=re.search(r'^RUN_DIRECTORY (.+)$',(out/'stdout.log').read_text(),re.M)
  if match:
   native=Path(match.group(1));assert native.is_relative_to(BASE) and native.name.startswith('production-')
   receipt['native_report']=str(native/'report.json')
   if (native/'report.json').is_file():
    data=json.loads((native/'report.json').read_text());receipt['native_report_sha256']=sha(native/'report.json');receipt['native_passed']=data['passed'];receipt['contexts']=len(data['runs']);receipt['native_inputs_unchanged']=data['inputs_unchanged'];receipt['firefox_browser_launches']=data['firefox_browser_launches'];receipt['actual_browser_launch_count']=2+len(data['firefox_browser_launches']);receipt['all_browser_launches_closed']=all(data['browsers_closed'].values()) and all(x['closed'] for x in data['firefox_browser_launches']);receipt['all_temporary_profiles_removed']=all(x['firefox_isolated_normal_ca_trust']['temporary_profile_removed'] for x in data['runs'] if x['engine']=='firefox');receipt['passed']=receipt['exit_code']==0 and data['passed'] and len(data['runs'])==6 and data['inputs_unchanged'] and receipt['all_browser_launches_closed'] and receipt['all_temporary_profiles_removed']
 finally:
  receipt['actual_head_after']=head();receipt['head_unchanged']=before==receipt['actual_head_after'];receipt['duration_seconds']=round(time.monotonic()-clock,3);receipt['finished_at_utc']=datetime.now(timezone.utc).isoformat();receipt['stdout']={'path':str(out/'stdout.log'),'sha256':sha(out/'stdout.log')};receipt['stderr']={'path':str(out/'stderr.log'),'sha256':sha(out/'stderr.log')};write(out/'receipt.json',receipt);write(BASE/'latest-production-launch.json',{'directory':str(out),'passed':receipt['passed']});print('RECEIPT',out/'receipt.json','PASS',receipt['passed'],flush=True)
 return 0 if receipt['passed'] else 1
if __name__=='__main__':raise SystemExit(run())
