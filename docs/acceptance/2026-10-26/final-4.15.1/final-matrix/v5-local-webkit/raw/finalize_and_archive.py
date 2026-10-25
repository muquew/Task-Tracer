from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,os,shutil,re
O=Path(__file__).resolve().parent;R=Path('/workspace/Task-Tracer');D=R/'docs/acceptance/2026-10-26/final-4.15.1';A=D/'final-matrix/v5-local-webkit'
def meta(p):return {'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def js(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
native=json.loads((O/'report.json').read_text());run=json.loads((O/'run-summary.json').read_text());before=json.loads((O/'inputs-before.json').read_text());after=json.loads((O/'inputs-after.json').read_text())
assert native['status'] not in ('running','initializing') and native['completed'] and len(native['checks'])==33
assert native['scope']['all_registered_programs'] and native['scope']['registry_program_count']==33 and len(native['planned_checks'])==33
assert native['source_unchanged'] and native['verification_unchanged'] and run['source_and_verification_and_head_unchanged']
assert before['source']==after['source']==native['source']==native['source_final'] and before['verification']==after['verification']==native['verification']==native['verification_final']
assert before['vcs_commit']==after['vcs_commit']=='6da3c7293f08c5d16ca73c7a63d8ff74e17358db'
for item in list(native['checks'])+list(native['browsers'].values()):
 log=item.get('log')
 if log:assert meta(Path(log['path']))=={k:log[k] for k in ('bytes','sha256')}
worker=json.loads((O/'worker.json').read_text());group_alive=True
try:os.killpg(worker['process_group'],0)
except ProcessLookupError:group_alive=False
assert not group_alive,'Original native matrix worker group remains alive'
seen={}
for line in (O/'process-observations.jsonl').read_text().splitlines():
 for row in json.loads(line)['processes']:seen[(row['pid'],row['start_ticks'])]=row
active=[];zombies=[];gone=0
for (pid,start),row in seen.items():
 try:
  raw=(Path('/proc')/str(pid)/'stat').read_text();v=raw[raw.rfind(')')+2:].split()
  if int(v[19])!=start:gone+=1;continue
  present={'pid':pid,'start_ticks':start,'comm':row['comm'],'state':v[0],'ppid':int(v[1])}
  (zombies if v[0]=='Z' else active).append(present)
 except (OSError,ValueError,IndexError):gone+=1
assert not active,active
js(O/'worker-cleanup.json',{'at':datetime.now(timezone.utc).isoformat(),'matrix_worker':worker,'matrix_process_group_alive':False,'observed_process_instances':len(seen),'active_observed_instances':active,'exited_zombie_instances':zombies,'gone_instances':gone,'scope_note':'PID+start_ticks sampled actual native descendants starting after early programs; not a complete process trace. Exited Z records await container parent reaping and are not active browsers/servers. No other worker was signaled.'})
passed=sum(c['status']=='passed' for c in native['checks']);failures=[c for c in native['checks'] if c['status']!='passed']
summary={'kind':'derived_independent_local_6da_webkit_full33_result','at':datetime.now(timezone.utc).isoformat(),'status':native['status'],'completed':native['completed'],'passed':native['passed'],'invoked_programs':33,'passed_programs':passed,'failed_programs':len(failures),'failures':failures,'native_report_sha256':meta(O/'report.json')['sha256'],'source':native['source'],'verification':native['verification'],'head':before['vcs_commit'],'browser':native['browsers']['webkit'],'native_scope':native['scope'],'runner_summary':run,'remote_ci_verdict_replaced':False,'complete_project_acceptance_claim':False}
js(O/'summary.json',summary)
(O/'README.md').write_text(f'''# 6da 独立本地 WebKit 完整33复核\n\n**本地原生结果：{native['status']}，{passed}/33通过，{len(failures)}失败，exit {run['exit_code']}，{run['duration_seconds']:.3f}秒。** 本次由原标准CI的WebKit失败触发；只独立记录本地结果，不覆盖远端原失败、不推断远端根因或全项目验收通过。后续远端诊断由父任务另行记录。\n\n原命令 `python tools/browser_matrix.py --browser webkit --keep-going --report <此独立目录>/report.json` 使用默认全部登记33，无group/program过滤，无重试；全部原断言、性能预算、HTTP/动画及CSP范围保留。开始时与唯一原local73并行，未启动第三个本地浏览器worker。[原报告](report.json)、[全命令与实际环境](command.json)、[runner](run.py)、全部 `report-logs/`、stdout/stderr均原字节保留。\n\nHEAD `6da3c7293f08c5d16ca73c7a63d8ff74e17358db`；source23 `58b724aff838339caf9c9ba0e2d5cff3ff05d20dae43e5c16fe93984f8734e54`；verification84 `62ec9c75e4045987bfb29df9905d075bbfeb3525558f671c4c26d159aeef0936`。原报告和before/after均确认107及HEAD起末一致。实际WebKit26.5 probe与原全部产品程序均执行；仅使用真实sysroot库路径及官方跳静态宿主预检flag，没有安装成功、断言跳过或通知mock声明。原非Chromium CDP时区子用例例外保留，Linux引擎不代表实体Safari/iOS。\n\n[派生汇总](summary.json)绑定原报告SHA与每程序真实终态；[清理收据](worker-cleanup.json)确认原worker组已消失、采样后代无活动实例，并明确列出已退出Z记录。所有原日志SHA/bytes已重新匹配，没有截断traceback或重写原失败。没有复制重复107源码或额外trace树。\n\n[外部清单](manifest.json)覆盖本独立外部scope并排除自身；正式归档另有自己的复制来源清单，保留所有原绝对路径。\n''')
entries={str(p.relative_to(O)):meta(p) for p in sorted(O.rglob('*')) if p.is_file() and p!=O/'manifest.json'}
js(O/'manifest.json',{'schema':1,'scope':'Actual independent local6da WebKit original full33 run, not replacement for failed hosted CI; self excluded.','file_count':len(entries),'bytes':sum(x['bytes'] for x in entries.values()),'files':entries})
# The native source107 is read-only; only this new acceptance documentation scope is writable.
A.mkdir(parents=True,exist_ok=True);assert not any(A.iterdir()),'Do not overwrite an earlier archive'
protected={str(p.relative_to(D)):meta(p) for p in [D/'stage-manifest.json',D/'README.md',D/'original-files.json',D/'coverage.json',D/'archive-verification.json'] if p.is_file()}
original_rows=[]
for p in sorted(O.rglob('*')):
 if not p.is_file():continue
 target=A/'raw'/p.relative_to(O);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target);assert meta(target)==meta(p)
 original_rows.append({'original_path':str(p),**meta(p),'archived':True,'archive_path':str(target.relative_to(D))})
js(A/'original-files.json',{'schema':1,'scope':'Only final-matrix/v5-local-webkit independent local reproduction; original native bytes not rewritten.','original_manifest':{'path':str(O/'manifest.json'),**meta(O/'manifest.json')},'original_files':original_rows})
(A/'README.md').write_text(f'''# v5：独立本地 WebKit 原完整33\n\n**本地结果 {native['status']}：{passed}/33通过，{len(failures)}失败，exit {run['exit_code']}，{run['duration_seconds']:.3f}秒。** 这是对6da原标准CI WebKit失败的独立复核；保留原远端失败，不把本地结果改写成远端通过或全项目完成。\n\n[原完整说明](raw/README.md)、[原native报告](raw/report.json)、[派生汇总](raw/summary.json)及[命令/环境](raw/command.json)保留真实全部33原registry、无重试/过滤、原断言/预算/HTTP/动画/CSP范围。完整原日志与stderr在raw，未截断traceback。实际WebKit26.5使用真实sysroot与官方仅跳静态宿主预检flag，实际launch/render与全部产品断言保留；原CDP例外、实体设备未测边界不变。\n\nHEAD6da、source23 `58b724aff838339caf9c9ba0e2d5cff3ff05d20dae43e5c16fe93984f8734e54`、verification84 `62ec9c75e4045987bfb29df9905d075bbfeb3525558f671c4c26d159aeef0936`起末一致。[输入before](raw/inputs-before.json)、[输入after](raw/inputs-after.json)与native本身均有完整107地图，未重复复制源码树。\n\n[worker清理](raw/worker-cleanup.json)列出原进程组消失、采样后代无活动实例与容器已退出Z记录的准确范围。[原文件清单](original-files.json)逐项给出外部原路径/SHA/bytes及实际复制项，原路径字段保持原值。[本范围清单](manifest.json)排除自身；未修改初始stage-manifest和其它组件。\n''')
archive_entries={str(p.relative_to(A)):meta(p) for p in sorted(A.rglob('*')) if p.is_file() and p!=A/'manifest.json'}
js(A/'manifest.json',{'schema':1,'scope':'final-matrix/v5-local-webkit only','self_excluded':True,'file_count':len(archive_entries),'bytes':sum(x['bytes'] for x in archive_entries.values()),'files':archive_entries})
for name,item in archive_entries.items():assert meta(A/name)==item
for name,item in protected.items():assert meta(D/name)==item
for p in [O/'README.md',A/'README.md']:
 for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)',p.read_text()):assert (p.parent/link).exists(),link
print(json.dumps({'status':native['status'],'passed_programs':passed,'failed_programs':len(failures),'native_sha256':meta(O/'report.json')['sha256'],'external_manifest_sha256':meta(O/'manifest.json')['sha256'],'archive_manifest_sha256':meta(A/'manifest.json')['sha256'],'archive_files':len(archive_entries)+1,'archive_bytes':sum(p.stat().st_size for p in A.rglob('*') if p.is_file())},ensure_ascii=False))
