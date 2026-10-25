from __future__ import annotations
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import hashlib, io, json, os, runpy, sys, uuid
from pathlib import Path
import urllib.request
ROOT=Path('/workspace/Task-Tracer')
sys.path.insert(0,str(ROOT/'tools'))
from check import source_identity, verification_identity
import verify_deployment
run_id=str(uuid.uuid4())
OUT=ROOT/'docs/acceptance/2026-10-25/deployment'/run_id
OUT.mkdir(parents=True,exist_ok=False)
(OUT/'assets').mkdir()
sha=lambda b:hashlib.sha256(b).hexdigest()
base='https://todo.muquew.com/'
report={'schema_version':1,'run_id':run_id,'site':base,'started_at':datetime.now(timezone.utc).isoformat(),'started_at_beijing':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'status':'running','passed':False,'tls_verification':'inherited default, unchanged','proxy':'inherited, unchanged','source':source_identity(),'verification':verification_identity(),'requests':[],'original_cli':None,'assets':[],'error':None}
original_open=urllib.request.urlopen
phase='original-cli'
safe_headers=['content-type','content-length','content-security-policy','x-content-type-options','referrer-policy','permissions-policy','strict-transport-security','x-frame-options','cache-control','etag','last-modified','server','x-vercel-cache','x-vercel-id']
def record_response(path):
    started=datetime.now(timezone.utc).isoformat()
    try:
        with original_open(path,timeout=20) as r:
            b=r.read();item={'phase':phase,'url':str(path),'final_url':r.geturl(),'status':r.status,'started_at':started,'finished_at':datetime.now(timezone.utc).isoformat(),'bytes':len(b),'sha256':sha(b),'headers':{k:r.headers.get(k) for k in safe_headers if r.headers.get(k) is not None}}
            name=f"{len(report['requests'])+1:02d}-{sha(str(path).encode())[:12]}.bin"
            (OUT/'assets'/name).write_bytes(b);item['body_file']='assets/'+name
            report['requests'].append(item)
            return b,r.headers,item
    except Exception as e:
        item={'phase':phase,'url':str(path),'started_at':started,'finished_at':datetime.now(timezone.utc).isoformat(),'error':f'{type(e).__name__}: {e}'};report['requests'].append(item);raise
class Observed:
    def __init__(self,url,*args,**kwargs):self.url=url
    def __enter__(self):self.data,self.headers,self.item=record_response(self.url);return self
    def __exit__(self,*args):return False
    def read(self):return self.data
stdout=io.StringIO();stderr=io.StringIO()
try:
    urllib.request.urlopen=Observed
    saved_argv=sys.argv[:];sys.argv=[str(ROOT/'tools/verify_deployment.py'),'--url',base]
    code=0
    try:
        with redirect_stdout(stdout),redirect_stderr(stderr):runpy.run_path(str(ROOT/'tools/verify_deployment.py'),run_name='__main__')
    except SystemExit as e:
        if e.code is None:code=0
        elif isinstance(e.code,int):code=e.code
        else:code=1;stderr.write(str(e.code)+'\n')
    except BaseException as e:code=1;stderr.write(f'{type(e).__name__}: {e}\n')
    finally:sys.argv=saved_argv;urllib.request.urlopen=original_open
    (OUT/'original-cli.stdout.log').write_text(stdout.getvalue());(OUT/'original-cli.stderr.log').write_text(stderr.getvalue())
    report['original_cli']={'program':'tools/verify_deployment.py','arguments':['--url',base],'exit_code':code,'stdout':'original-cli.stdout.log','stderr':'original-cli.stderr.log','observed_requests':[i+1 for i,r in enumerate(report['requests']) if r['phase']=='original-cli']}
    phase='diagnostic-complete-asset-inventory'
    targets={'':ROOT/'index.html',**verify_deployment.deployment_assets()}
    for request_path,local in targets.items():
        url=base+request_path
        try:
            data,headers,request=record_response(url)
            report['assets'].append({'request_path':request_path or '/','local_file':local.relative_to(ROOT).as_posix(),'remote_sha256':sha(data),'local_sha256':sha(local.read_bytes()),'bytes_equal':data==local.read_bytes(),'request_number':len(report['requests'])})
        except Exception as e:report['assets'].append({'request_path':request_path or '/','local_file':local.relative_to(ROOT).as_posix(),'error':f'{type(e).__name__}: {e}'})
    report['source_final']=source_identity();report['verification_final']=verification_identity();report['source_unchanged']=report['source_final']==report['source'];report['verification_unchanged']=report['verification_final']==report['verification']
    report['passed']=code==0 and all(a.get('bytes_equal') for a in report['assets']) and report['source_unchanged'] and report['verification_unchanged'];report['status']='passed' if report['passed'] else 'failed'
except BaseException as e:report['status']='failed';report['error']=f'{type(e).__name__}: {e}'
finally:
    urllib.request.urlopen=original_open
    report['finished_at']=datetime.now(timezone.utc).isoformat();report['finished_at_beijing']=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
    (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (OUT/'runner.py').write_bytes(Path(__file__).read_bytes())
    manifest={p.relative_to(OUT).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in OUT.rglob('*') if p.is_file()}
    (OUT/'files.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'output':str(OUT),'status':report['status'],'original_cli':report['original_cli'],'requests':len(report['requests']),'assets':len(report['assets']),'mismatches':[a for a in report['assets'] if not a.get('bytes_equal')],'error':report['error']},ensure_ascii=False))
