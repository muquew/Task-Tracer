from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess,sys,time,uuid
from urllib.error import HTTPError
from urllib.parse import urljoin
parser=argparse.ArgumentParser();parser.add_argument('--commit',required=True);args=parser.parse_args();assert re.fullmatch('[a-f0-9]{40}',args.commit)
R=Path('/workspace/Task-Tracer-themes');P=Path('/tmp/task-tracer-4.13.0-production');P.mkdir(parents=True,exist_ok=True);assert not (P/'verification.json').exists(),'Preserve existing production verification'
(P/'responses').mkdir(exist_ok=False);(P/'attempts').mkdir(exist_ok=False)
sys.path.insert(0,str(R/'tools'));from check import atomic_report,source_identity,verification_identity
from validate_static import app_version
import verify_deployment
sha=lambda b:hashlib.sha256(b).hexdigest();now=lambda:datetime.now(timezone.utc).isoformat();bj=lambda:datetime.now(ZoneInfo('Asia/Shanghai')).isoformat();base='https://todo.muquew.com/'
source=source_identity();verification=verification_identity();assert source['sha256']=='ec90af64e257a5e808addbb658fb887c789730773d94452cdbaa8b4bd446ddce';assert app_version((R/'index.html').read_text())=='4.13.0'
extras=['screenshots/add-task-en.png','screenshots/add-task.png','screenshots/task-list-en.png','screenshots/task-list.png','docs/distribution.md','docs/distribution_zh_cn.md']
record={'schema_version':1,'run_id':str(uuid.uuid4()),'site':base,'pushed_commit':args.commit,'started_at':now(),'started_at_beijing':bj(),'status':'waiting_for_matching_deployment','completed':False,'passed':False,'core_passed':False,'extra_assets_passed':False,'source':source,'verification':verification,'attempts':[],'core_requests':[],'extra_requests':[],'error':None,'scope':'Original native deployment CLI, followed by observational reverify plus four screenshots and two distribution docs. No browser or user data accessed.','policy':'Default TLS/proxy preserved; no cache override/query; no source edits or Git operations.'}
log=P/'verification.log'
def emit(value):
 line=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False)
 with log.open('a') as f:f.write(line+'\n')
 print(line,flush=True)
def publish():atomic_report(P/'verification.json',record)
publish();emit({'started_at':record['started_at'],'output':str(P),'commit':record['pushed_commit'],'source_sha':source['sha256'],'verification_sha':verification['sha256']})
original_open=verify_deployment.urlopen;safe_headers=['date','age','cache-control','content-type','content-length','content-security-policy','referrer-policy','x-content-type-options','x-frame-options','permissions-policy','strict-transport-security','x-vercel-cache','x-vercel-id','etag']
def save_response(response,data,phase,path):
 number=len(record['core_requests'])+len(record['extra_requests'])+1;name='responses/'+f'{number:02d}-'+sha(path.encode())[:12]+'.bin';(P/name).write_bytes(data)
 return {'path':path,'url':response.geturl(),'phase':phase,'status':response.status,'at':now(),'bytes':len(data),'sha256':sha(data),'body_file':name,'headers':{key:response.headers.get(key) for key in safe_headers if response.headers.get(key) is not None}}
start=time.monotonic();three_minute_notified=False
try:
 while True:
  attempt=len(record['attempts'])+1;prefix=f'attempts/{attempt:02d}';begin=now();tick=time.monotonic()
  try:
   result=subprocess.run([sys.executable,str(R/'tools/verify_deployment.py'),'--url',base],cwd=R,capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=60);code=result.returncode;stdout=result.stdout;stderr=result.stderr
  except subprocess.TimeoutExpired as error:code=None;stdout=error.stdout.decode() if isinstance(error.stdout,bytes) else error.stdout or '';stderr=error.stderr.decode() if isinstance(error.stderr,bytes) else error.stderr or '';stderr+='Native CLI exceeded 60 seconds; attempt interrupted and recorded, not a successful verification.\n'
  (P/(prefix+'.stdout.log')).write_text(stdout);(P/(prefix+'.stderr.log')).write_text(stderr)
  outcome={'attempt':attempt,'started_at':begin,'finished_at':now(),'duration_seconds':round(time.monotonic()-tick,3),'exit_code':code,'stdout':prefix+'.stdout.log','stderr':prefix+'.stderr.log','state':'matched' if code==0 else 'pending_or_mismatch','diagnostic':stderr.strip()}
  if code==0:outcome['result']=json.loads(stdout)
  record['attempts'].append(outcome);publish();emit(outcome)
  if code==0:
   assert outcome['result']['version']=='4.13.0' and outcome['result']['passed'];record['first_native_pass_at']=outcome['finished_at'];record['first_native_pass_at_beijing']=datetime.fromisoformat(outcome['finished_at']).astimezone(ZoneInfo('Asia/Shanghai')).isoformat();record['core_passed']=True;publish();emit('FIRST_NATIVE_CLI_FULL_PASS');break
  elapsed=time.monotonic()-start
  if elapsed>=180 and not three_minute_notified:emit('STILL_PENDING_AFTER_THREE_MINUTES');three_minute_notified=True
  if elapsed>=600:record['status']='waiting_timeout';record['completed']=True;break
  time.sleep(min(20,max(0,600-elapsed)))
 if record['core_passed']:
  class Observed:
   def __init__(self,url,*args,**kwargs):self.url=url;self.args=args;self.kwargs=kwargs
   def __enter__(self):self.response=original_open(self.url,*self.args,**self.kwargs);self.response.__enter__();self.headers=self.response.headers;return self
   def __exit__(self,*args):return self.response.__exit__(*args)
   def read(self):
    data=self.response.read();path=self.url.removeprefix(base) or '/';item=save_response(self.response,data,'core-original-verify',path);record['core_requests'].append(item);return data
  verify_deployment.urlopen=Observed
  try:record['observed_core_result']=verify_deployment.verify(base)
  finally:verify_deployment.urlopen=original_open
  expected={'':R/'index.html',**verify_deployment.deployment_assets()};assert len(record['core_requests'])==len(expected)
  for item,(path,local) in zip(record['core_requests'],expected.items()):item['local_file']=local.relative_to(R).as_posix();item['local_sha256']=sha(local.read_bytes());item['bytes_equal']=item['sha256']==item['local_sha256'];assert item['bytes_equal'],path
  for path in extras:
   local=R/path
   try:
    with original_open(urljoin(base,path),timeout=20) as response:data=response.read();item=save_response(response,data,'extra-screenshot-or-distribution',path)
   except HTTPError as error:
    data=error.read();item=save_response(error,data,'extra-screenshot-or-distribution',path);item['error']=f'HTTPError: {error.code} {error.reason}'
   except Exception as error:item={'path':path,'url':urljoin(base,path),'phase':'extra-screenshot-or-distribution','at':now(),'status':None,'error':f'{type(error).__name__}: {error}'}
   item['local_file']=path;item['local_sha256']=sha(local.read_bytes());item['bytes_equal']=item.get('sha256')==item['local_sha256'];item['passed']=item.get('status')==200 and item['bytes_equal'];record['extra_requests'].append(item);publish();emit({'extra_path':path,'status':item.get('status'),'bytes_equal':item['bytes_equal'],'passed':item['passed'],'error':item.get('error')})
  record['extra_assets_passed']=len(record['extra_requests'])==6 and all(item['passed'] for item in record['extra_requests'])
  record['source_final']=source_identity();record['verification_final']=verification_identity();record['source_unchanged']=record['source_final']==source;record['verification_unchanged']=record['verification_final']==verification;assert record['source_unchanged'] and record['verification_unchanged']
  archive=R/'dist/task-tracer-4.13.0.zip';record['distribution_archive']={'path':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive.read_bytes()),'scope':'Identity only; no local build or test rerun.'};assert record['distribution_archive']['sha256']=='cc5c4d16262af9f0b7d6dddbc28844620e5ccbcee3d6e8b897aff6fa424858bc'
  record['passed']=record['core_passed'] and record['extra_assets_passed'];record['status']='passed' if record['passed'] else 'failed_extra_assets';record['completed']=True
except BaseException as error:record['status']='failed';record['completed']=True;record['error']=f'{type(error).__name__}: {error}'
finally:
 verify_deployment.urlopen=original_open;record['finished_at']=now();record['finished_at_beijing']=bj();publish();(P/'runner.py').write_bytes(Path(__file__).read_bytes());files={p.relative_to(P).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in P.rglob('*') if p.is_file() and p.name!='files.json'};atomic_report(P/'files.json',files);emit({'status':record['status'],'passed':record['passed'],'core_passed':record['core_passed'],'extra_assets_passed':record['extra_assets_passed'],'attempts':len(record['attempts']),'core_responses':len(record['core_requests']),'extra_responses':len(record['extra_requests']),'error':record['error']})
 # Final log line is included in a refreshed manifest; verification report itself stays native.
 files={p.relative_to(P).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in P.rglob('*') if p.is_file() and p.name!='files.json'};atomic_report(P/'files.json',files)
