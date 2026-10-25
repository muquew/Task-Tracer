from pathlib import Path
import sys,json,os,subprocess,time,hashlib,importlib.metadata
ROOT=Path('/workspace/Task-Tracer-redesign')
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
from check import source_identity,verification_identity,timestamp,atomic_report
FREEZE_SHA='f5dea27060897a52d01637416b735ea1716b9b1b354b86655aaa4e73f9cf94be'
HEAD='e7d58e2ce27798253d69b0dd9723cd55dc5c15c2'
freeze_path=OUT/'frozen-inputs.json'
def git(*args): return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
command=[sys.executable,'tools/check.py','--keep-going','--report',str(OUT/'check-results.json')]
report={'purpose':'formal complete 59-program correctness queue on the frozen committed candidate; concurrent matrix means elapsed timings are not an isolated benchmark','status':'initializing','completed':False,'passed':False,'started_at':timestamp(),'command':command,'display_command':'python tools/check.py --keep-going --report '+str(OUT/'check-results.json'),'working_directory':str(ROOT),'stdout_stderr_log':str(OUT/'check-output.log'),'freeze_sha256':hashlib.sha256(freeze_path.read_bytes()).hexdigest(),'application_commit':git('rev-parse','HEAD'),'working_tree_status':git('status','--porcelain'),'source':source_identity(),'verification':verification_identity(),'environment':{key:os.environ.get(key) for key in ('PYTHONDONTWRITEBYTECODE','TASK_TRACER_BROWSER_EXECUTABLE','XDG_CACHE_HOME','PLAYWRIGHT_BROWSERS_PATH','PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS')},'python_version':sys.version,'playwright_version':importlib.metadata.version('playwright')}
axe=ROOT/'node_modules'/'axe-core'/'package.json'
report['axe_core']={'version':json.loads(axe.read_text())['version'],'resolved_package':str(axe.resolve())}
path=OUT/'full-run.json';atomic_report(path,report)
start=time.monotonic();code=None;error=None
try:
 assert report['freeze_sha256']==FREEZE_SHA,'Frozen metadata changed before launch'
 frozen=json.loads(freeze_path.read_text())
 assert report['application_commit']==HEAD and not report['working_tree_status'],'Commit or clean status changed before launch'
 assert report['source']==frozen['source'] and report['verification']==frozen['verification'],'Inputs do not match the formal freeze'
 count=0
 for group in ('source','verification'):
  for relative,digest in frozen[group]['files'].items():
   assert hashlib.sha256((OUT/'inputs'/relative).read_bytes()).hexdigest()==digest,relative
   count+=1
 report['snapshot_verified_input_count']=count;report['status']='running';atomic_report(path,report)
 with (OUT/'check-output.log').open('w') as log:
  code=subprocess.run(command,cwd=ROOT,env=os.environ.copy(),stdout=log,stderr=subprocess.STDOUT).returncode
except BaseException as exc:
 error=f'{type(exc).__name__}: {exc}'
finally:
 report.update(finished_at=timestamp(),elapsed_seconds=round(time.monotonic()-start,3),exit_code=code,error=error,source_final=source_identity(),verification_final=verification_identity(),application_commit_final=git('rev-parse','HEAD'),working_tree_status_final=git('status','--porcelain'),freeze_sha256_final=hashlib.sha256(freeze_path.read_bytes()).hexdigest(),completed=True)
 report['source_unchanged']=report['source_final']==report['source'];report['verification_unchanged']=report['verification_final']==report['verification']
 report['commit_unchanged']=report['application_commit_final']==HEAD
 report['working_tree_clean_final']=not report['working_tree_status_final']
 report['freeze_unchanged']=report['freeze_sha256_final']==FREEZE_SHA
 report['passed']=code==0 and error is None and all(report[k] for k in ('source_unchanged','verification_unchanged','commit_unchanged','working_tree_clean_final','freeze_unchanged'))
 report['status']='passed' if report['passed'] else 'failed';atomic_report(path,report)
 print(json.dumps({k:report.get(k) for k in ('status','passed','exit_code','error','elapsed_seconds','source_unchanged','verification_unchanged','commit_unchanged','working_tree_clean_final','freeze_unchanged')},ensure_ascii=False),flush=True)
 print('Full queue report:',OUT/'check-results.json',flush=True)
 print('Outer execution report:',path,flush=True)
raise SystemExit(0 if report['passed'] else 1)
