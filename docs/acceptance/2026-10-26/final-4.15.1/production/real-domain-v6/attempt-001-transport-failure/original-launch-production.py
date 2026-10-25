"""Launch the original v5 driver only after an explicit matched-deployment signal."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, os, re, signal, subprocess, sys, time, uuid
ROOT=Path('/workspace/Task-Tracer')
BASE=Path(__file__).resolve().parent
DRIVER=BASE/'driver.py'
DRIVER_SHA256='b866dd25c6c27efe0f1ed92d8ac46d54bfa12de605baa4bc319696088376ca91'
ENV={'PYTHONDONTWRITEBYTECODE':'1','TASK_TRACER_BROWSER_EXECUTABLE':'/usr/bin/chromium','XDG_CACHE_HOME':'/workspace/.cache','PLAYWRIGHT_BROWSERS_PATH':'/workspace/.cache/ms-playwright','LD_LIBRARY_PATH':'/workspace/.cache/browser-libs/root/usr/lib/x86_64-linux-gnu','PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS':'1'}
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def head():return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def run():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--deployment-matched',action='store_true');args=parser.parse_args()
 if not args.deployment_matched:raise SystemExit('No execution: parent main/Vercel static-match signal is required.')
 assert sha(DRIVER)==DRIVER_SHA256,'Original v5 driver changed'
 prepared=json.loads((BASE/'preparation-receipt.json').read_text())
 runtime={name:sha(ROOT/name) for name in prepared['runtime_before']}
 helpers={name:sha(ROOT/name) for name in prepared['actual_helpers_before']}
 assert runtime==prepared['runtime_before'] and helpers==prepared['actual_helpers_before'],'Actual runtime/helper bytes differ from six-context green rehearsal'
 assert os.environ.get('NODE_TLS_REJECT_UNAUTHORIZED')!='0' and os.environ.get('PYTHONHTTPSVERIFY')!='0','Normal TLS verification is required'
 out=BASE/f'production-launch-{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")}-{uuid.uuid4().hex[:8]}';out.mkdir()
 command=[sys.executable,str(DRIVER),'--mode','production','--url','https://todo.muquew.com/']
 before=head();clock=time.monotonic();receipt={'started_at_utc':datetime.now(timezone.utc).isoformat(),'command':command,'cwd':str(ROOT),'environment_overrides':ENV,'driver_sha256':DRIVER_SHA256,'actual_head_before':before,'runtime_before':runtime,'helpers_before':helpers,'wrapper_scope':'Only launch/receipt capture. The original driver, argv, six real-UI contexts and assertions are unchanged. HEAD is observed, not fixed to the older6da rehearsal commit.','passed':False}
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
    data=json.loads((native/'report.json').read_text());receipt['native_report_sha256']=sha(native/'report.json');receipt['native_passed']=data['passed'];receipt['contexts']=len(data['runs']);receipt['native_inputs_unchanged']=data['inputs_unchanged'];receipt['passed']=receipt['exit_code']==0 and data['passed'] and len(data['runs'])==6 and data['inputs_unchanged']
 finally:
  receipt['actual_head_after']=head();receipt['head_unchanged']=before==receipt['actual_head_after'];receipt['duration_seconds']=round(time.monotonic()-clock,3);receipt['finished_at_utc']=datetime.now(timezone.utc).isoformat();receipt['stdout']={'path':str(out/'stdout.log'),'sha256':sha(out/'stdout.log')};receipt['stderr']={'path':str(out/'stderr.log'),'sha256':sha(out/'stderr.log')};write(out/'receipt.json',receipt);write(BASE/'latest-production-launch.json',{'directory':str(out),'passed':receipt['passed']});print('RECEIPT',out/'receipt.json','PASS',receipt['passed'],flush=True)
 return 0 if receipt['passed'] else 1
if __name__=='__main__':raise SystemExit(run())
