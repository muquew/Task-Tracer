from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from urllib.request import Request,urlopen
import hashlib,json,re,sys
ROOT=Path('/workspace/Task-Tracer');sys.path.insert(0,str(ROOT/'tools'))
from validate_static import app_version
P=ROOT/'docs/acceptance/2026-10-25/deployment/a8155697-f6ef-4eb5-908f-9cc6d23e6a57'
paths=['/?acceptance=20261025-a8155697','/index.html?acceptance=20261025-a8155697','/sw.js?acceptance=20261025-a8155697']
def read(path):
 item={'url':'https://todo.muquew.com'+path,'request_headers':{'Cache-Control':'no-cache'},'started_at':datetime.now(timezone.utc).isoformat()}
 try:
  with urlopen(Request(item['url'],headers=item['request_headers']),timeout=20) as r:
   b=r.read();name='fresh-'+hashlib.sha256(path.encode()).hexdigest()[:12]+'.bin';(P/'assets'/name).write_bytes(b);item.update(status=r.status,final_url=r.geturl(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),body_file='assets/'+name,headers={k:r.headers.get(k) for k in ['date','age','cache-control','x-vercel-cache','x-vercel-id','etag','last-modified','content-security-policy']})
   t=b.decode('utf-8')
   if path.startswith('/sw.js'):item['cache_names']=re.findall(r"CACHE_NAME\s*=\s*['\"]([^'\"]+)",t)
   else:item['app_version']=app_version(t);item['resource_versions']=re.findall(r"RESOURCE_VERSION:\s*['\"]([^'\"]+)",t)
 except Exception as e:item['error']=f'{type(e).__name__}: {e}'
 item['finished_at']=datetime.now(timezone.utc).isoformat();return item
with ThreadPoolExecutor(max_workers=3) as pool:items=list(pool.map(read,paths))
d={'kind':'supplementary-cache-observation','run_id':'a8155697-f6ef-4eb5-908f-9cc6d23e6a57','captured_at':datetime.now(timezone.utc).isoformat(),'captured_at_beijing':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'source':'additional read-only no-cache, nonce-query fetches; original verification report unchanged','requests':items}
(P/'fresh-cache-observation.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
(P/'cachecheck-runner.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps(d,ensure_ascii=False))
