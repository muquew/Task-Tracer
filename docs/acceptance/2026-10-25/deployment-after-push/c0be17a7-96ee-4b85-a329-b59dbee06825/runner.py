from __future__ import annotations
from contextlib import redirect_stdout,redirect_stderr
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import hashlib,io,json,os,subprocess,sys,time,uuid,urllib.request
from pathlib import Path
R=Path('/workspace/Task-Tracer');sys.path.insert(0,str(R/'tools'))
from check import atomic_report,source_identity,verification_identity
import verify_deployment
sha=lambda b:hashlib.sha256(b).hexdigest()
now=lambda:datetime.now(timezone.utc).isoformat()
run_id=str(uuid.uuid4());P=R/'docs/acceptance/2026-10-25/deployment-after-push'/run_id;P.mkdir(parents=True,exist_ok=False);(P/'assets').mkdir()
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip();assert commit=='d9b2a58d8359aa27c087f3da809d7de27ee398f0',commit
report={'schema_version':1,'run_id':run_id,'site':'https://todo.muquew.com/','commit':commit,'started_at':now(),'started_at_beijing':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'status':'waiting_for_matching_deployment','completed':False,'passed':False,'source':source_identity(),'verification':verification_identity(),'attempts':[],'observation_requests':[],'error':None,'policy':'Default inherited TLS and proxy; no cache query/header override; native CLI unchanged'}
def publish():atomic_report(P/'report.json',report)
publish();print(json.dumps({'output':str(P),'commit':commit,'started_at':report['started_at']}),flush=True)
start=time.monotonic();progress_sent=False
try:
 while True:
  index=len(report['attempts'])+1;prefix=f'attempt-{index:02d}';started=now();result=subprocess.run([sys.executable,str(R/'tools/verify_deployment.py'),'--url',report['site']],cwd=R,capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=360)
  (P/f'{prefix}.stdout.log').write_text(result.stdout);(P/f'{prefix}.stderr.log').write_text(result.stderr)
  item={'attempt':index,'started_at':started,'finished_at':now(),'exit_code':result.returncode,'stdout':f'{prefix}.stdout.log','stderr':f'{prefix}.stderr.log','state':'matched' if result.returncode==0 else 'pending_or_mismatch','duration_seconds':round(time.monotonic()-start,3)}
  if result.returncode==0:item['result']=json.loads(result.stdout)
  else:item['diagnostic']=result.stderr.strip()
  report['attempts'].append(item);publish();print(json.dumps({'attempt':index,'exit_code':result.returncode,'state':item['state'],'diagnostic':item.get('diagnostic'),'finished_at':item['finished_at']}),flush=True)
  if result.returncode==0:
   report['first_native_pass_at']=item['finished_at'];report['first_native_pass_at_beijing']=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat();break
  elapsed=time.monotonic()-start
  if elapsed>=180 and not progress_sent:print('STILL_PENDING_AFTER_THREE_MINUTES',flush=True);progress_sent=True
  if elapsed>=600:report['status']='waiting_timeout';report['completed']=True;break
  time.sleep(min(25,max(0,600-elapsed)))
 if report.get('first_native_pass_at'):
  original_open=verify_deployment.urlopen
  class ObservedResponse:
   def __init__(self,url,*args,**kwargs):self.url=url;self.args=args;self.kwargs=kwargs
   def __enter__(self):
    self.response=original_open(self.url,*self.args,**self.kwargs);self.response.__enter__();self.headers=self.response.headers;return self
   def __exit__(self,*args):return self.response.__exit__(*args)
   def read(self):
    data=self.response.read();rel='assets/'+f"{len(report['observation_requests'])+1:02d}-"+sha(self.url.encode())[:12]+'.bin';(P/rel).write_bytes(data)
    report['observation_requests'].append({'url':self.url,'final_url':self.response.geturl(),'status':self.response.status,'at':now(),'bytes':len(data),'sha256':sha(data),'body_file':rel,'headers':{key:self.headers.get(key) for key in ['date','age','cache-control','content-type','content-security-policy','referrer-policy','x-content-type-options','x-frame-options','permissions-policy','strict-transport-security','x-vercel-cache','x-vercel-id','etag'] if self.headers.get(key) is not None}});return data
  verify_deployment.urlopen=ObservedResponse
  try:report['observed_original_verify']=verify_deployment.verify(report['site'])
  finally:verify_deployment.urlopen=original_open
  expected_paths={'':R/'index.html',**verify_deployment.deployment_assets()}
  requests=report['observation_requests'];assert len(requests)==len(expected_paths)
  for request,(path,local) in zip(requests,expected_paths.items()):assert request['sha256']==sha(local.read_bytes()),path
  report['source_final']=source_identity();report['verification_final']=verification_identity();report['source_unchanged']=report['source_final']==report['source'];report['verification_unchanged']=report['verification_final']==report['verification'];assert report['source_unchanged'] and report['verification_unchanged'];assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()==commit
  report['passed']=True;report['completed']=True;report['status']='passed'
except BaseException as e:report['status']='failed';report['completed']=True;report['error']=f'{type(e).__name__}: {e}'
finally:
 report['finished_at']=now();report['finished_at_beijing']=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat();publish();(P/'runner.py').write_bytes(Path(__file__).read_bytes());files={p.relative_to(P).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in P.rglob('*') if p.is_file()};atomic_report(P/'files.json',files)
 print(json.dumps({'output':str(P),'status':report['status'],'passed':report['passed'],'attempts':len(report['attempts']),'first_native_pass_at':report.get('first_native_pass_at'),'observed_requests':len(report['observation_requests']),'error':report['error']}),flush=True)
