from pathlib import Path
import hashlib,json,os,subprocess,sys,time,traceback
ROOT=Path('/workspace/Task-Tracer-redesign')
OUT=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'tools'))
from check import source_identity,verification_identity,atomic_report,timestamp
name=sys.argv[1]
assert name in ('upgrade-archive-4.8.6','workspace-10000')
freeze_path=OUT/'frozen-inputs.json';freeze_bytes=freeze_path.read_bytes()
assert hashlib.sha256(freeze_bytes).hexdigest()=='da74449f278e4633a9be1e5d91a291a98fa7cee55c14bdd1f1c16bd44b230ae4'
f=json.loads(freeze_bytes)
command=[sys.executable,'tools/upgrade_playwright.py','--baseline-archive','dist/task-tracer-4.8.6.zip'] if name=='upgrade-archive-4.8.6' else [sys.executable,'tools/workspace_roundtrip_playwright.py','--size','10000','--subtasks','6','--full-views','--output',str(OUT/'workspace-10000-program.json')]
report_path=OUT/(name+'.json');log_path=OUT/(name+'.log')
assert not report_path.exists() and not log_path.exists()
r={'scope':name,'status':'initializing','passed':False,'completed':False,'started_at':timestamp(),'command':command,'cwd':str(ROOT),'environment':{k:os.environ.get(k) for k in ['PYTHONDONTWRITEBYTECODE','TASK_TRACER_BROWSER_EXECUTABLE','XDG_CACHE_HOME','PLAYWRIGHT_BROWSERS_PATH']},'freeze_sha256':hashlib.sha256(freeze_bytes).hexdigest(),'source':source_identity(),'verification':verification_identity(),'parallel_correctness_run':True,'error':None}
assert r['source']==f['source'] and r['verification']==f['verification']
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==f['application_commit']
if name=='upgrade-archive-4.8.6':
 archive=ROOT/'dist/task-tracer-4.8.6.zip';raw=archive.read_bytes();digest=hashlib.sha256(raw).hexdigest()
 assert len(raw)==812059 and digest=='7a54122aae730cc566ef7e7b4040183842e02b8aa4f27d1b73ddd3bddafff895'
 r['baseline_archive']={'path':str(archive),'bytes':len(raw),'sha256':digest}
atomic_report(report_path,r);start=time.monotonic()
try:
 r['status']='running';atomic_report(report_path,r)
 with log_path.open('xb') as log:
  result=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy())
 r['exit_code']=result.returncode
except BaseException as exc:
 r['error']=f'{type(exc).__name__}: {exc}';r['traceback']=traceback.format_exc()
finally:
 r['finished_at']=timestamp();r['elapsed_seconds']=round(time.monotonic()-start,3)
 try:
  r['source_final']=source_identity();r['verification_final']=verification_identity()
  r['source_unchanged']=r['source_final']==r['source']==f['source'];r['verification_unchanged']=r['verification_final']==r['verification']==f['verification']
  assert freeze_path.read_bytes()==freeze_bytes
  assert r['source_unchanged'] and r['verification_unchanged']
 except BaseException as exc:
  r['integrity_error']=f'{type(exc).__name__}: {exc}'
 if log_path.exists():r['log']={'path':str(log_path),'bytes':log_path.stat().st_size,'sha256':hashlib.sha256(log_path.read_bytes()).hexdigest()}
 r['completed']=True;r['passed']=r.get('exit_code')==0 and not r.get('error') and not r.get('integrity_error')
 r['status']='passed' if r['passed'] else 'failed';atomic_report(report_path,r)
print(json.dumps({k:r.get(k) for k in ['scope','status','exit_code','elapsed_seconds','source_unchanged','verification_unchanged','error','integrity_error']},indent=2),flush=True)
sys.exit(0 if r['passed'] else 1)
