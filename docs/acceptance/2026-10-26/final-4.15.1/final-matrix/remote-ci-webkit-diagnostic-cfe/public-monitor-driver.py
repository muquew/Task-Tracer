"""Read only the NEW run/job's public SSR metadata and safe annotations."""
from pathlib import Path
from datetime import datetime,timezone
from html.parser import HTMLParser
import ast,hashlib,json,re,subprocess,time
P=Path('/workspace/design-research/task-tracer-final-delivery-2026-10-26/ci-webkit-outcomes/85ab7611-74ef-450e-b012-9e8447a397ae');OUT=P/'monitor';OUT.mkdir(exist_ok=False)
RUN='https://github.com/muquew/Task-Tracer/actions/runs/40235171022';JOB=RUN+'/job/121295077000'
module=ast.parse(Path('/workspace/Task-Tracer/tools/browser_matrix.py').read_text());PROGRAMS=next(ast.literal_eval(n.value) for n in module.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PROGRAMS' for t in n.targets));assert len(PROGRAMS)==33
class Text(HTMLParser):
 def __init__(self):super().__init__();self.ignore=0;self.items=[]
 def handle_starttag(self,tag,attrs):
  if tag in ('script','style'):self.ignore+=1
 def handle_endtag(self,tag):
  if tag in ('script','style') and self.ignore:self.ignore-=1
 def handle_data(self,data):
  if not self.ignore:self.items.extend(x.strip() for x in data.splitlines() if x.strip())
def text(html):
 p=Text();p.feed(html);return '\n'.join(p.items)
def emit(value):
 with (OUT/'events.jsonl').open('a') as stream:stream.write(json.dumps(value)+'\n')
 print(json.dumps(value),flush=True)
seen=set();start=time.monotonic();errors=0
emit({'event':'monitor_started','run_url':RUN,'job_url':JOB,'only_new_public_metadata':True})
for poll in range(196):
 pages={};bad=False
 for label,url in (('job',JOB),('run',RUN)):
  f=OUT/(label+'-latest.html');r=subprocess.run(['curl','--silent','--show-error','--max-time','25','--output',str(f),url],capture_output=True)
  if r.returncode:bad=True;errors+=1;continue
  pages[label]=f.read_text(errors='replace')
 if 'job' in pages:
  jt=text(pages['job']);rt=text(pages.get('run',''))
  discovered=[]
  for program in PROGRAMS:
   for match in re.finditer(re.escape(program)+r'\s+exit=(-?\d{1,3})(?!\d)',jt+'\n'+rt):
    code=int(match.group(1))
    if -255<=code<=255 and code!=0 and (program,code) not in seen:
     seen.add((program,code));discovered.append({'program':program,'exit_code':code})
  terminal=re.search(r'\nwebkit\n(?:webkit\n)?(succeeded|failed|cancelled)\n',jt)
  job_status=terminal.group(1) if terminal else 'in_progress_or_unknown'
  run_match=re.search(r'\nStatus\n(Success|Failure|Cancelled|In progress|Queued|Waiting)\nTotal duration\n([0-9hms ]+|-)',rt)
  if job_status=='in_progress_or_unknown' and run_match and run_match.group(1) in ('Success','Failure','Cancelled'):job_status={'Success':'succeeded','Failure':'failed','Cancelled':'cancelled'}[run_match.group(1)]
  summary_match=re.search(r'matrix status=(passed|failed|running|initializing|interrupted|error|invalid_report|missing_report) passed=(\d{1,2}) failed=(\d{1,2}) not_run=(\d{1,2}) invalid=(\d{1,2}) planned=33',jt+'\n'+rt)
  summary=None
  if summary_match:
   values=list(map(int,summary_match.groups()[1:]));
   if all(0<=x<=33 for x in values) and sum(values)==33:summary={'status':summary_match.group(1),'passed':values[0],'failed':values[1],'not_run':values[2],'invalid':values[3],'planned':33}
  timestamp=datetime.now(timezone.utc).isoformat()
  if discovered or job_status!='in_progress_or_unknown':
   safe_stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
   evidence={}
   for label,html in pages.items():
    path=OUT/(safe_stamp+'-'+label+'.html');path.write_text(html);evidence[label]={'path':str(path),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
   for item in discovered:emit({'event':'failed_program','recorded_at':timestamp,'run_url':RUN,**item,'evidence':evidence})
  status={'recorded_at':timestamp,'poll':poll,'job_status':job_status,'safe_summary':summary,'known_failed_programs':[{'program':p,'exit_code':c} for p,c in sorted(seen)],'elapsed_seconds':round(time.monotonic()-start,1),'read_errors':errors,'run_url':RUN,'job_url':JOB,'protected_logs_or_artifacts_requested':False}
  (OUT/'status.json').write_text(json.dumps(status,indent=2)+'\n')
  if job_status!='in_progress_or_unknown':emit({'event':'job_terminal',**status});break
  if poll%5==0:emit({'event':'heartbeat','job_status':job_status,'poll':poll,'known_failed_count':len(seen),'elapsed_seconds':status['elapsed_seconds']})
 else:
  if poll%5==0:emit({'event':'read_unavailable','poll':poll,'read_errors':errors})
 time.sleep(30)
else:emit({'event':'monitor_timeout','run_url':RUN,'known_failed_programs':[{'program':p,'exit_code':c} for p,c in sorted(seen)]})
