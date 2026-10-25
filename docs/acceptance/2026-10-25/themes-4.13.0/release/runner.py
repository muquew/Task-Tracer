from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,os,re,subprocess,sys,time,uuid
R=Path('/workspace/Task-Tracer-themes');sys.path.insert(0,str(R/'tools'))
from check import atomic_report,source_identity,verification_identity,stop_child
from build_release import expected_distribution_files
distribution_count=len(expected_distribution_files())
sha=lambda b:hashlib.sha256(b).hexdigest()
now=lambda:datetime.now(timezone.utc).isoformat()
run_id=str(uuid.uuid4());P=Path('/tmp/task-tracer-4.13.0-release')/run_id;P.mkdir(parents=True,exist_ok=False)
source=source_identity();verification=verification_identity()
def vcs_identity():
 return {'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'working_tree_dirty':bool(subprocess.check_output(['git','status','--porcelain'],cwd=R,text=True).strip())}
vcs_initial=vcs_identity()
base=R/'dist/task-tracer-4.12.0.zip';baseline_sha=sha(base.read_bytes());assert baseline_sha=='0b392b6efe58ae94f40901b02cf612a533904889b3f941f015bb7b1a9f9475e8'
record={'schema_version':1,'run_id':run_id,'repository':str(R),'started_at':now(),'status':'initializing','completed':False,'passed':False,'current':None,'source':source,'verification':verification,'vcs_initial':vcs_initial,'source_final':None,'verification_final':None,'source_unchanged':False,'verification_unchanged':False,'steps':[],'baseline_archive':{'path':str(base),'bytes':base.stat().st_size,'sha256':baseline_sha},'error':None}
atomic_report(P/'report.json',record);atomic_report(P/'frozen-inputs.json',{'source':source,'verification':verification});(P/'runner.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps({'output':str(P),'source_files':len(source['files']),'source_sha':source['sha256'],'verification_files':len(verification['files']),'verification_sha':verification['sha256']}),flush=True)
steps=[('static7',['tools/check.py','--static-only','--keep-going','--report',str(P/'static7.json')]),('release',['tools/release_playwright.py']),('actual-4.12.0-upgrade',['tools/upgrade_playwright.py','--baseline-archive','dist/task-tracer-4.12.0.zip'])]
env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONUNBUFFERED':'1','TASK_TRACER_BROWSER_EXECUTABLE':'/usr/bin/chromium'}
child=None
try:
 for name,args in steps:
  assert source_identity()==source,'Frozen distribution source changed before '+name
  assert verification_identity()==verification,'Frozen verification inputs changed before '+name
  record['status']='running';record['current']=name;atomic_report(P/'report.json',record);start=time.monotonic();started=now();print('Starting '+name,flush=True)
  with (P/(name+'.stdout.log')).open('x') as stdout,(P/(name+'.stderr.log')).open('x') as stderr:
   child=subprocess.Popen([sys.executable,*args],cwd=R,env=env,stdout=stdout,stderr=stderr,start_new_session=True);code=child.wait();child=None
  item={'name':name,'arguments':args,'started_at':started,'finished_at':now(),'duration_seconds':round(time.monotonic()-start,3),'exit_code':code,'stdout':name+'.stdout.log','stderr':name+'.stderr.log'};record['steps'].append(item);atomic_report(P/'report.json',record);print(f'Finished {name}: exit={code}',flush=True)
  assert source_identity()==source,'Frozen distribution source changed during '+name
  assert verification_identity()==verification,'Frozen verification inputs changed during '+name
  if code:raise RuntimeError(name+' returned exit '+str(code)+'; original stdout/stderr preserved')
 static=json.loads((P/'static7.json').read_text());assert static['status']=='passed' and static['passed'] and static['completed'] and len(static['checks'])==7 and all(x['exit_code']==0 for x in static['checks']);assert static['source']==static['source_final']==source and static['verification']==static['verification_final']==verification
 output=(P/'release.stdout.log').read_text();hashes=re.findall(rf'Built and verified .*?\({distribution_count} files, SHA-256 ([a-f0-9]{{64}})\)',output);assert len(hashes)==2 and len(set(hashes))==1,hashes;assert 'Release passed: reproducible bytes, verified manifest, safe file set, extracted PWA persistence and offline reload' in output
 upgrade=(P/'actual-4.12.0-upgrade.stdout.log').read_text();assert 'actual task-tracer-4.12.0.zip SHA256='+baseline_sha in upgrade
 for phrase in ('Actual 4.12.0 → 4.13.0:','Actual rollback to 4.12.0:','Actual re-upgrade to 4.13.0:'):assert phrase in upgrade,phrase
 record['reproducible_archive_sha256']=hashes[0];record['distribution_file_count']=distribution_count;record['status']='passed';record['passed']=True;record['completed']=True;record['current']=None
except BaseException as error:
 if child is not None:stop_child(child)
 record['status']='failed';record['completed']=True;record['error']=f'{type(error).__name__}: {error}'
finally:
 record['vcs_final']=vcs_identity();record['vcs_unchanged']=record['vcs_final']==vcs_initial;record['source_final']=source_identity();record['verification_final']=verification_identity();record['source_unchanged']=record['source_final']==source;record['verification_unchanged']=record['verification_final']==verification;record['finished_at']=now();atomic_report(P/'report.json',record)
 files={p.relative_to(P).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in P.rglob('*') if p.is_file()};atomic_report(P/'files.json',files);print(json.dumps({'output':str(P),'status':record['status'],'passed':record['passed'],'steps':record['steps'],'error':record['error'],'source_unchanged':record['source_unchanged'],'verification_unchanged':record['verification_unchanged'],'archive_sha':record.get('reproducible_archive_sha256')}),flush=True)
