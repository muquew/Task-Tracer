import hashlib,json,os,subprocess,sys,time
from pathlib import Path
root=Path('/workspace/Task-Tracer');out=Path('/tmp/task-tracer-4.13.1-regression')/sys.argv[1];out.mkdir(parents=True,exist_ok=True)
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TASK_TRACER_BROWSER_EXECUTABLE='/usr/bin/chromium',XDG_CACHE_HOME='/workspace/.cache',PLAYWRIGHT_BROWSERS_PATH='/workspace/.cache/ms-playwright')
report={'index_sha256':hashlib.sha256((root/'index.html').read_bytes()).hexdigest(),'results':[]}
for item in sys.argv[2:]:
 parts=item.split('|');command=[sys.executable,str(root/'tools'/parts[0]),*parts[1:]]
 if parts[0]=='accessibility_i18n_audit.py':command=[sys.executable,str(root/'docs/acceptance/2026-10-25/themes-4.13.0/protection/csp_wait_bootstrap.py'),str(root/'tools'/parts[0]),*parts[1:]]
 start=time.monotonic();log=out/(parts[0]+'.log')
 with log.open('w') as f:result=subprocess.run(command,cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT)
 record={'command':command,'exit_code':result.returncode,'seconds':round(time.monotonic()-start,3),'log':log.name};report['results'].append(record);report['index_sha256_after']=hashlib.sha256((root/'index.html').read_bytes()).hexdigest();(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(record),flush=True)
 if result.returncode:sys.exit(result.returncode)
assert report['index_sha256_after']==report['index_sha256']
