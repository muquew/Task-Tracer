from pathlib import Path
from datetime import datetime,timezone
from html.parser import HTMLParser
import ast,hashlib,json,re,subprocess,sys
R=Path('/workspace/Task-Tracer');C=Path('/tmp/task-tracer-ci-webkit-outcomes-c8mbe0wb/repo');P=Path('/workspace/design-research/task-tracer-final-delivery-2026-10-26/ci-webkit-outcomes/85ab7611-74ef-450e-b012-9e8447a397ae');D=R/'docs/acceptance/2026-10-26/final-4.15.1/final-matrix/remote-ci-webkit-diagnostic-cfe'
sys.path.insert(0,str(R/'tools'));from check import source_identity,verification_identity
s0=source_identity();v0=verification_identity();HEAD='6da3c7293f08c5d16ca73c7a63d8ff74e17358db';COMMIT='cfe8d6de236fa6e771934379c67efd711df5c029';sha=lambda b:hashlib.sha256(b).hexdigest()
assert s0['sha256']=='58b724aff838339caf9c9ba0e2d5cff3ff05d20dae43e5c16fe93984f8734e54' and v0['sha256']=='62ec9c75e4045987bfb29df9905d075bbfeb3525558f671c4c26d159aeef0936'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()==HEAD
status=json.loads((P/'monitor/status.json').read_text());assert status['job_status']=='succeeded' and status['known_failed_programs']==[] and status['safe_summary'] is None
assert not D.exists();D.mkdir(parents=True);origins={};derived={}
def copy(src,name):
 b=src.read_bytes();dest=D/name;dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();dest.write_bytes(b);assert b==src.read_bytes();origins[name]={'source':str(src),'bytes':len(b),'sha256':sha(b),'byte_identical':True}
def write(name,data,sources):
 (D/name).parent.mkdir(parents=True,exist_ok=True);assert not (D/name).exists();(D/name).write_text((json.dumps(data,ensure_ascii=False,indent=2)+'\n') if not isinstance(data,str) else data);derived[name]={'derived_from':[str(x) for x in sources]}
for src,name in [(C/'.github/workflows/checks.yml','diagnostic-workflow.yml'),(C/'.github/scripts/webkit_outcomes.py','safe-webkit-outcomes.py'),(P/'report.json','preparation-report.json'),(P/'push-receipt.json','push-receipt.json'),(P/'monitor/status.json','public-terminal-status.json'),(P/'monitor/events.jsonl','public-observation-events.jsonl'),(P.parent/'monitor_public.py','public-monitor-driver.py'),(Path(__file__),'archive-driver.py')]:copy(src,name)
for file in ('.github/workflows/checks.yml','.github/scripts/webkit_outcomes.py'):
 committed=subprocess.check_output(['git','show',COMMIT+':'+file],cwd=C);assert committed==(C/file).read_bytes()
changes=set(subprocess.check_output(['git','diff','--name-only',HEAD,COMMIT],cwd=C,text=True).splitlines());assert changes=={'.github/workflows/checks.yml','.github/scripts/webkit_outcomes.py'}
comparison=[]
for kind,group in (('distribution_source',s0),('verification_input',v0)):
 for name,digest in group['files'].items():
  if name=='.github/workflows/checks.yml':continue
  a=(R/name).read_bytes();b=(C/name).read_bytes();assert a==b and sha(a)==digest
  comparison.append({'name':name,'kind':kind,'bytes':len(a),'primary_sha256':digest,'diagnostic_sha256':sha(b),'byte_identical':True})
assert len(comparison)==106
module=ast.parse((R/'tools/browser_matrix.py').read_text());programs=next(ast.literal_eval(n.value) for n in module.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PROGRAMS' for t in n.targets));assert len(programs)==33
push=json.loads((P/'push-receipt.json').read_text())
write('byte-comparison-proof.json',{'base_commit':HEAD,'diagnostic_commit':COMMIT,'source_sha256_both':s0['sha256'],'primary_verification_sha256':v0['sha256'],'diagnostic_verification_sha256':push['diagnostic_verification']['sha256'],'verification_changed_paths':['.github/workflows/checks.yml'],'added_metadata_script':'.github/scripts/webkit_outcomes.py','added_script_is_outside_original84_input_contract':True,'all_106_other_original_inputs_identical':True,'files':comparison,'all_33_original_programs_identical':True,'registered_programs':list(programs),'diagnostic_scope_is_not_standard_release_gate':True},[P/'push-receipt.json',R/'tools/browser_matrix.py'])
class Text(HTMLParser):
 def __init__(self):super().__init__();self.ignore=0;self.items=[];self.times=[]
 def handle_starttag(self,tag,attrs):
  if tag in ('script','style'):self.ignore+=1
  a=dict(attrs)
  if tag in ('relative-time','time') and a.get('datetime'):self.times.append({'at_line':len(self.items),'datetime':a['datetime']})
 def handle_endtag(self,tag):
  if tag in ('script','style') and self.ignore:self.ignore-=1
 def handle_data(self,data):
  if not self.ignore:self.items.extend(x.strip() for x in data.splitlines() if x.strip())
def parse(path):
 p=Text();p.feed(path.read_text());return p,'\n'.join(p.items)
terminal_job=next((P/'monitor').glob('*-job.html'));terminal_run=next((P/'monitor').glob('*-run.html'))
jp,jt=parse(terminal_job);rp,rt=parse(terminal_run);startp,starttext=parse(P/'job-initial.html')
job_match=re.search(r'\nwebkit\n(?:webkit\n)?(succeeded|failed|cancelled)\nin ([0-9hms ]+)\n',jt)
run_match=re.search(r'\nStatus\n(Success|Failure|Cancelled|In progress|Queued|Waiting)\nTotal duration\n([0-9hms ]+|-)',rt)
assert (job_match and job_match.group(1)=='succeeded') or (run_match and run_match.group(1)=='Success')
started=[i for i,x in enumerate(startp.items) if x=='Started'];start_times=[t['datetime'] for t in startp.times if any(i<=t['at_line']<=i+4 for i in started)]
known_annotations=[]
for program in programs:
 for match in re.finditer(re.escape(program)+r'\s+exit=(-?\d{1,3})(?!\d)',jt+'\n'+rt):
  if int(match.group(1))!=0:known_annotations.append({'program':program,'exit_code':int(match.group(1))})
assert known_annotations==[]
write('public-terminal-witness.json',{'run_url':status['run_url'],'job_url':status['job_url'],'diagnostic_commit':COMMIT,'observed_at':status['recorded_at'],'started_timestamp_observed':start_times,'public_job_footer_status':job_match.group(1) if job_match else None,'public_job_duration':job_match.group(2) if job_match else None,'public_run_status':run_match.group(1) if run_match else None,'public_run_duration':run_match.group(2) if run_match else None,'failed_known_basename_annotations_observed':known_annotations,'observed_safe_native_table':False,'protected_report_or_logs_or_artifact_read':False,'native_all33_pass_is_an_inference_from_success_and_unmodified_return_contract':True,'inference_contract':['Diagnostic workflow has exactly one WebKit job and runs the original default all33 native matrix with --keep-going.','Observer starts the original command without scope, assertion or budget changes and returns its actual native exit code.','Original native matrix returns0 only when all planned programs completed with no failing code or integrity error.','The public job succeeded. This is not a claim of reading the protected native JSON or summary table.']},[terminal_job,terminal_run,P/'monitor/status.json',C/'.github/scripts/webkit_outcomes.py',R/'tools/browser_matrix.py'])
htmls=[P/'actions-initial.html',P/'run-initial.html',P/'job-initial.html',terminal_job,terminal_run]
write('unretained-public-page-index.json',{'public_page_contents_copied':False,'reason':'Retain only approved safe metadata/status witnesses. Original public HTML includes unrelated website bootstrap fields and is indexed by SHA/bytes rather than copied.','pages':[{'source_path':str(p),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes()),'copied':False} for p in htmls]},htmls)
readme='''# 独立WebKit安全诊断：cfe

本目录是**独立NEW正常CI诊断旁证**，不是exact6da标准发布门槛，不覆盖首次标准WebKit失败。诊断提交 `cfe8d6de236fa6e771934379c67efd711df5c029` 基于应用提交 `6da3c7293f08c5d16ca73c7a63d8ff74e17358db`，独立分支 `codex/ci-webkit-outcomes-20261026`。主仓HEAD及107输入没有改变。

[公开run](https://github.com/muquew/Task-Tracer/actions/runs/40235171022)／[唯一WebKit job](https://github.com/muquew/Task-Tracer/actions/runs/40235171022/job/121295077000)已公开succeeded。起始观察为2026-10-25 21:22:16 UTC，首次终态观察为21:44:18.776288 UTC。各次公开观察未见failed basename／exit annotation。原[终态metadata](public-terminal-status.json)与[观察事件](public-observation-events.jsonl)保留原字节；[公开状态见证](public-terminal-witness.json)明确区分原metadata与派生判断。

## 原范围与安全输出

- [Workflow原字节](diagnostic-workflow.yml)只有一个WebKit job，保留ubuntu-latest、Python3.12、固定requirements／Playwright及原 `install --with-deps webkit`，预算90分钟。
- [Metadata helper原字节](safe-webkit-outcomes.py)启动原 `tools/browser_matrix.py --browser webkit --keep-going --report dist/browser-matrix-webkit.json`，没有过滤33程序、弱化断言或改预算；观察者每5秒只读取本次NEW原生report，输出已知basename、有限数值exit／duration、固定enum和通过数。最终always summary采用同样白名单，不读取／转发原子程序stdout、日志、任务内容、环境或token。
- helper原样返回native退出码。原matrix只有全部33计划完成、无失败退出码／输入完整性错误时返回0。因此公开job成功支持“本次原33全scope native exit0”的判断；**未读取受保护native JSON、原日志或最终table，不声称实际取得或归档这些文件**。

## 与最终源码的关系

[逐文件反证](byte-comparison-proof.json)核对23发行源码及其余83验证输入，106个原文件逐字相同，全部33原程序也逐字相同。诊断仅修改`.github/workflows/checks.yml`并新增metadata helper；后者不在既有84输入合同内。两者均绑定cfe提交原字节。

23源码aggregate仍为 `58b724aff838339caf9c9ba0e2d5cff3ff05d20dae43e5c16fe93984f8734e54`；最终标准84验证aggregate是 `62ec9c75e4045987bfb29df9905d075bbfeb3525558f671c4c26d159aeef0936`，诊断因workflow改变为 `831991ef8562a8b4cb51b4570014eb8ad5e273f1e0c485be4b2b10c63bd611de`，不能把诊断aggregate转标为标准原输入。

首次标准6da run40233014544中的WebKit job121288575649曾Failure，根代理已另行保存原状态。其原日志受保护，后续同源多轮未复现，**根因仍未确定，不能声称已定位或修复**。本次cfe green只保留独立结论；exact6da标准repeat40235376686由主代理另行收口。

本目录没有读取旧受限日志、绕过artifact保护／网络策略，或把其他host作为转发通道。[未复制页面索引](unretained-public-page-index.json)记录原公开HTML捕获路径、SHA和字节，仅保留安全metadata／状态提取，不复制无关站点bootstrap字段。[来源](source-origins.json)与manifest只覆盖本目录实际文件，原绝对路径保持捕获身份。没有提交、发布或复制正式ZIP到主发行目录。
'''
write('README.md',readme,[P/'push-receipt.json',P/'monitor/status.json',terminal_job,terminal_run])
write('source-origins.json',{'copied_files':origins,'derived_files':derived,'scope':'Only this diagnostic evidence directory was written; existing stages/root manifests, primary HEAD and all107 inputs remain unchanged.'},[Path(__file__)])
entries={f.relative_to(D).as_posix():{'bytes':f.stat().st_size,'sha256':sha(f.read_bytes())} for f in D.rglob('*') if f.is_file()}
write('manifest.json',{'schema_version':1,'status':'independent_diagnostic_public_success_not_standard_gate','diagnostic_commit':COMMIT,'base_commit':HEAD,'manifest_excludes_only_itself':True,'files':entries},[Path(__file__)])
assert {f.relative_to(D).as_posix() for f in D.rglob('*') if f.is_file()}==set(entries)|{'manifest.json'}
for name,meta in entries.items():assert sha((D/name).read_bytes())==meta['sha256'] and (D/name).stat().st_size==meta['bytes']
for name,meta in origins.items():assert (D/name).read_bytes()==Path(meta['source']).read_bytes()
assert source_identity()==s0 and verification_identity()==v0 and subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()==HEAD
print(json.dumps({'archive':str(D),'files':len(entries)+1,'bytes':sum(f.stat().st_size for f in D.rglob('*') if f.is_file()),'manifest_sha256':sha((D/'manifest.json').read_bytes()),'source_origins_sha256':sha((D/'source-origins.json').read_bytes()),'public_terminal_status':'succeeded','direct_private_report_or_table_read':False,'all106_original_files_byte_identical':True,'primary107_and_HEAD_unchanged':True}),flush=True)
