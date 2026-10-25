from pathlib import Path
from datetime import datetime, timezone
import subprocess,json,hashlib,os,time
ROOT=Path('/workspace/Task-Tracer');OUT=Path('/workspace/design-research/task-tracer-materials-2026-10-26/regression/a11y')
files=['index.html','resources/en.json','resources/zh-CN.json','sw.js','vercel.json','tools/accessibility_i18n_audit.py','tools/smoke_playwright.py','tools/security_playwright.py']
snapshot=lambda:{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}
before=snapshot();assert before['index.html']=='3aa235f5f9adae2349440b8995c7a9c1ecb0335111f52d232cc8811e29a37561'
command=['python',str(OUT/'normal_csp_wrapper.py'),'tools/accessibility_i18n_audit.py','--skip-scaled']
start=datetime.now(timezone.utc).isoformat();clock=time.monotonic()
with (OUT/'stdout.log').open('w') as so,(OUT/'stderr.log').open('w') as se:r=subprocess.run(command,cwd=ROOT,stdout=so,stderr=se)
after=snapshot();report={'command':command,'started_at':start,'finished_at':datetime.now(timezone.utc).isoformat(),'duration_seconds':round(time.monotonic()-clock,3),'exit_code':r.returncode,'normal_deployment_csp':True,'csp_bypass':False,'expression_waits_wrapped_as_functions_only':True,'skip_scaled':True,'before':before,'after':after,'unchanged':before==after}
(OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));raise SystemExit(r.returncode if before==after else 1)
