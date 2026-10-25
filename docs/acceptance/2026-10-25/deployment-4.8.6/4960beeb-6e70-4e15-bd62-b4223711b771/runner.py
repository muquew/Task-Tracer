from __future__ import annotations
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import hashlib,json,os,subprocess,sys,time,uuid
from pathlib import Path
R=Path('/workspace/Task-Tracer');sys.path.insert(0,str(R/'tools'))
from check import atomic_report,source_identity,verification_identity
from validate_static import app_version
import verify_deployment
sha=lambda b:hashlib.sha256(b).hexdigest()
now=lambda:datetime.now(timezone.utc).isoformat()
beijing=lambda:datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
F=json.loads(Path('/tmp/task-tracer-4.8.6-freeze.json').read_text());commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip();assert commit=='f13d7e11111a1ee321363dec875c8899146dffa6'
assert source_identity()==F['source'];assert verification_identity()==F['verification']
run_id=str(uuid.uuid4());P=R/'docs/acceptance/2026-10-25/deployment-4.8.6'/run_id;P.mkdir(parents=True,exist_ok=False);(P/'assets').mkdir()
report={'schema_version':1,'run_id':run_id,'site':'https://todo.muquew.com/','expected_app_version':'4.8.6','expected_resource_version':'4.36','pushed_commit':commit,'started_at':now(),'started_at_beijing':beijing(),'status':'waiting_for_matching_deployment','completed':False,'passed':False,'source':source_identity(),'verification':verification_identity(),'freeze':F,'attempts':[],'pending_index_observations':[],'observation_requests':[],'error':None,'policy':'Unmodified native CLI plus observational reverify. Default inherited TLS and proxy; no cache query/header overrides.'}
def publish():atomic_report(P/'report.json',report)
safe_headers=['date','age','cache-control','content-type','content-security-policy','referrer-policy','x-content-type-options','x-frame-options','permissions-policy','strict-transport-security','x-vercel-cache','x-vercel-id','etag']
original_open=verify_deployment.urlopen

def archive_response(response,data,rel):
 (P/rel).write_bytes(data)
 return {'url':response.geturl(),'status':response.status,'at':now(),'bytes':len(data),'sha256':sha(data),'body_file':rel,'headers':{key:response.headers.get(key) for key in safe_headers if response.headers.get(key) is not None}}

publish();print(json.dumps({'output':str(P),'commit':commit,'started_at':report['started_at']}),flush=True)
start=time.monotonic();progress_sent=False
try:
 while True:
  index=len(report['attempts'])+1;prefix=f'attempt-{index:02d}';started=now();before=time.monotonic();result=subprocess.run([sys.executable,str(R/'tools/verify_deployment.py'),'--url',report['site']],cwd=R,capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=360)
  (P/f'{prefix}.stdout.log').write_text(result.stdout);(P/f'{prefix}.stderr.log').write_text(result.stderr)
  item={'attempt':index,'started_at':started,'finished_at':now(),'exit_code':result.returncode,'stdout':f'{prefix}.stdout.log','stderr':f'{prefix}.stderr.log','state':'matched' if result.returncode==0 else 'pending_or_mismatch','duration_seconds':round(time.monotonic()-before,3),'elapsed_seconds_since_start':round(time.monotonic()-start,3)}
  if result.returncode==0:item['result']=json.loads(result.stdout)
  else:
   item['diagnostic']=result.stderr.strip()
   try:
    with original_open(report['site'],timeout=20) as response:
     data=response.read();observed=archive_response(response,data,'assets/'+prefix+'-pending-index.bin');observed['app_version']=app_version(data.decode());observed['attempt']=index;observed['scope']='Independent follow-up observation after native CLI, not interception of its request';report['pending_index_observations'].append(observed)
   except Exception as error:report['pending_index_observations'].append({'attempt':index,'error':f'{type(error).__name__}: {error}','at':now()})
  report['attempts'].append(item);publish();print(json.dumps({'attempt':index,'exit_code':result.returncode,'state':item['state'],'diagnostic':item.get('diagnostic'),'finished_at':item['finished_at']}),flush=True)
  if result.returncode==0:
   assert item['result']['version']=='4.8.6' and item['result']['passed'];report['first_native_pass_at']=item['finished_at'];report['first_native_pass_at_beijing']=beijing();publish();break
  elapsed=time.monotonic()-start
  if elapsed>=180 and not progress_sent:print('STILL_PENDING_AFTER_THREE_MINUTES',flush=True);progress_sent=True
  if elapsed>=600:report['status']='waiting_timeout';report['completed']=True;break
  time.sleep(min(25,max(0,600-elapsed)))
 if report.get('first_native_pass_at'):
  class ObservedResponse:
   def __init__(self,url,*args,**kwargs):self.url=url;self.args=args;self.kwargs=kwargs
   def __enter__(self):self.response=original_open(self.url,*self.args,**self.kwargs);self.response.__enter__();self.headers=self.response.headers;return self
   def __exit__(self,*args):return self.response.__exit__(*args)
   def read(self):
    data=self.response.read();rel='assets/'+f"matched-{len(report['observation_requests'])+1:02d}-"+sha(self.url.encode())[:12]+'.bin';item=archive_response(self.response,data,rel);item['request_url']=self.url;report['observation_requests'].append(item);return data
  verify_deployment.urlopen=ObservedResponse
  try:report['observed_original_verify']=verify_deployment.verify(report['site'])
  finally:verify_deployment.urlopen=original_open
  expected_paths={'':R/'index.html',**verify_deployment.deployment_assets()}
  assert len(report['observation_requests'])==len(expected_paths)==14
  for request,(path,local) in zip(report['observation_requests'],expected_paths.items()):
   request['local_file']=local.relative_to(R).as_posix();request['local_sha256']=sha(local.read_bytes());request['bytes_equal']=request['sha256']==request['local_sha256'];assert request['bytes_equal'],path
  html=(P/report['observation_requests'][0]['body_file']).read_text();sw=next(x for x in report['observation_requests'] if x['request_url'].endswith('/sw.js'));sw_text=(P/sw['body_file']).read_text();assert app_version(html)=='4.8.6';assert "RESOURCE_VERSION: '4.36'" in html;assert 'task-tracer-v4.8.6' in sw_text
  report['actual_app_version']='4.8.6';report['actual_resource_version']='4.36';report['actual_cache_name']='task-tracer-v4.8.6'
  report['source_final']=source_identity();report['verification_final']=verification_identity();report['source_unchanged']=report['source_final']==report['source']==F['source'];report['verification_unchanged']=report['verification_final']==report['verification']==F['verification'];assert report['source_unchanged'] and report['verification_unchanged'];assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()==commit
  report['passed']=True;report['completed']=True;report['status']='passed'
except BaseException as error:report['status']='failed';report['completed']=True;report['error']=f'{type(error).__name__}: {error}'
finally:
 report['finished_at']=now();report['finished_at_beijing']=beijing();publish();(P/'runner.py').write_bytes(Path(__file__).read_bytes());files={p.relative_to(P).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in P.rglob('*') if p.is_file()};atomic_report(P/'files.json',files)
 print(json.dumps({'output':str(P),'status':report['status'],'passed':report['passed'],'attempts':len(report['attempts']),'first_native_pass_at':report.get('first_native_pass_at'),'observed_requests':len(report['observation_requests']),'error':report['error']}),flush=True)
