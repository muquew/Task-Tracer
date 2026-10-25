from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,os,subprocess,sys,time,uuid
R=Path('/workspace/Task-Tracer');sys.path.insert(0,str(R/'tools'))
from check import source_identity,verification_identity,atomic_report,stop_child
sha=lambda data:hashlib.sha256(data).hexdigest()
now=lambda:datetime.now(timezone.utc).isoformat()
assert len(sys.argv)==4, 'Arguments: INDEX_SHA SOURCE_IDENTITY_SHA VERIFICATION_IDENTITY_SHA'
I,S,V=sys.argv[1:]
assert all(len(x)==64 and set(x)<=set('0123456789abcdef') for x in (I,S,V))
s=source_identity();v=verification_identity();assert s['sha256']==S and v['sha256']==V and s['files']['index.html']==I
P=Path('/workspace/design-research/task-tracer-final-delivery-2026-10-26/release-proof/scale-10000-full')/str(uuid.uuid4());P.mkdir(parents=True)
args=[sys.executable,'tools/workspace_roundtrip_playwright.py','--size','10000','--subtasks','6','--full-views','--output',str(P/'result.json')]
env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONUNBUFFERED':'1','TASK_TRACER_BROWSER_EXECUTABLE':'/usr/bin/chromium','XDG_CACHE_HOME':'/workspace/.cache','PLAYWRIGHT_BROWSERS_PATH':'/workspace/.cache/ms-playwright'}
record={'started_at':now(),'status':'running','passed':False,'completed':False,'source':s,'verification':v,'command':args,'native_timeouts_unchanged':True,'native_scope':{'http_handler':'normal local_server unless the explicitly recorded existing production-header variable is 1','production_headers_env':env.get('TASK_TRACER_PRODUCTION_HEADERS'),'motion':'native browser context, no wrapper override'},'native_report':'result.json','error':None}
atomic_report(P/'report.json',record);(P/'runner.py').write_bytes(Path(__file__).read_bytes())
child=None;started=time.monotonic();print(json.dumps({'output':str(P),'command':args,'source':S,'verification':V}),flush=True)
try:
 with (P/'stdout.log').open('x') as stdout,(P/'stderr.log').open('x') as stderr:
  child=subprocess.Popen(args,cwd=R,env=env,stdout=stdout,stderr=stderr,start_new_session=True);record['child_pid']=child.pid;atomic_report(P/'report.json',record);record['exit_code']=child.wait(timeout=1800);child=None
 assert record['exit_code']==0,'Native full workspace operation returned nonzero; original logs retained'
 native=json.loads((P/'result.json').read_text())
 assert native['passed'] and native['completed'] and native['status']=='passed'
 assert native['source']==native['source_final']==s and native['source_unchanged'] and native['tool_inputs_unchanged']
 assert not native['page_errors'] and not native['integrity_errors']
 record['native_report_sha256']=sha((P/'result.json').read_bytes());record['native_checks']=native['checks'];record['status']='passed';record['passed']=True
except BaseException as error:
 if child is not None:stop_child(child)
 record['error']=f'{type(error).__name__}: {error}';record['status']='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed'
finally:
 record['duration_seconds']=round(time.monotonic()-started,3);record['finished_at']=now();record['completed']=True;record['source_final']=source_identity();record['verification_final']=verification_identity();record['source_unchanged']=record['source_final']==s;record['verification_unchanged']=record['verification_final']==v
 if not record['source_unchanged'] or not record['verification_unchanged']:record['status']='failed';record['passed']=False;record['integrity_error']='107 input set changed'
 live=[]
 for proc in Path('/proc').iterdir():
  if not proc.name.isdigit():continue
  try:
   st=(proc/'stat').read_text();fields=st[st.rfind(')')+2:].split()
   if int(fields[3])==record.get('child_pid') and fields[0]!='Z':live.append({'pid':int(proc.name),'state':fields[0]})
  except (OSError,ValueError):pass
 record['remaining_live_native_session_processes']=live
 if live:record['status']='failed';record['passed']=False;record['process_cleanup_error']='Live native process group remains'
 atomic_report(P/'report.json',record)
 files={f.relative_to(P).as_posix():{'bytes':f.stat().st_size,'sha256':sha(f.read_bytes())} for f in P.rglob('*') if f.is_file()};atomic_report(P/'files.json',files)
 print(json.dumps({'output':str(P),'status':record['status'],'passed':record['passed'],'duration_seconds':record['duration_seconds'],'source_unchanged':record['source_unchanged'],'verification_unchanged':record['verification_unchanged'],'native_report_sha256':record.get('native_report_sha256'),'error':record.get('error'),'remaining_live_native_session_processes':live}),flush=True)
if not record['passed']:sys.exit(1)
