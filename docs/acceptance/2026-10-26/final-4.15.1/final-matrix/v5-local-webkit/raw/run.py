from pathlib import Path
from datetime import datetime,timezone
import os,sys,subprocess,json,time,hashlib
ROOT=Path('/workspace/Task-Tracer');OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
from check import source_identity,verification_identity
EXPECTED_COMMIT='6da3c7293f08c5d16ca73c7a63d8ff74e17358db'
EXPECTED_SOURCE='58b724aff838339caf9c9ba0e2d5cff3ff05d20dae43e5c16fe93984f8734e54'
EXPECTED_VERIFICATION='62ec9c75e4045987bfb29df9905d075bbfeb3525558f671c4c26d159aeef0936'
def capture():return {'source':source_identity(),'verification':verification_identity(),'vcs_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'vcs_status':subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True)}
def write(name,d):(OUT/name).write_text(json.dumps(d,indent=2)+'\n')
assert not (OUT/'report.json').exists(),'New verification scope must not overwrite an earlier run'
before=capture()
assert before['vcs_commit']==EXPECTED_COMMIT and before['source']['sha256']==EXPECTED_SOURCE and before['verification']['sha256']==EXPECTED_VERIFICATION
write('inputs-before.json',before)
env=os.environ.copy();env.update(PYTHONDONTWRITEBYTECODE='1',XDG_CACHE_HOME='/workspace/.cache',PLAYWRIGHT_BROWSERS_PATH='/workspace/.cache/ms-playwright',PYTHONUNBUFFERED='1',LD_LIBRARY_PATH='/workspace/.cache/browser-libs/root/usr/lib/x86_64-linux-gnu',PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS='1')
env.pop('TASK_TRACER_BROWSER_EXECUTABLE',None);env.pop('TASK_TRACER_PRODUCTION_HEADERS',None)
command=['python','tools/browser_matrix.py','--browser','webkit','--keep-going','--report',str(OUT/'report.json')]
at=datetime.now(timezone.utc).isoformat();started=time.monotonic()
write('command.json',{'command':command,'cwd':str(ROOT),'started_at':at,'environment':{key:env.get(key) for key in ['PYTHONDONTWRITEBYTECODE','XDG_CACHE_HOME','PLAYWRIGHT_BROWSERS_PATH','PYTHONUNBUFFERED','LD_LIBRARY_PATH','PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS','TASK_TRACER_BROWSER_EXECUTABLE','TASK_TRACER_PRODUCTION_HEADERS']},'scope':'Independent local reproduction of new6da hosted WebKit33 failure; original default full registry, original assertions/timeouts/budgets/HTTP/motion. No retries, group/program filters, global CSP override, or notification mocks.','runtime_note':'Actual prevalidated custom library sysroot; official skip flag omits static host-library preflight only, not browser launch or product tests. Native probe remains required.','runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
with (OUT/'stdout.log').open('wb') as stdout,(OUT/'stderr.log').open('wb') as stderr:
 child=subprocess.Popen(command,cwd=ROOT,env=env,stdout=stdout,stderr=stderr,start_new_session=True)
 write('worker.json',{'pid':child.pid,'process_group':child.pid,'started_at':at})
 print(json.dumps({'native_worker':child.pid,'scope':'all33 WebKit','report':str(OUT/'report.json')}),flush=True)
 code=child.wait()
after=capture();write('inputs-after.json',after)
stable=before['source']==after['source'] and before['verification']==after['verification'] and before['vcs_commit']==after['vcs_commit']
summary={'started_at':at,'finished_at':datetime.now(timezone.utc).isoformat(),'duration_seconds':round(time.monotonic()-started,3),'exit_code':code,'source_and_verification_and_head_unchanged':stable,'native_worker_returned':True}
write('run-summary.json',summary);print(json.dumps(summary),flush=True)
raise SystemExit(code if stable else 2)
