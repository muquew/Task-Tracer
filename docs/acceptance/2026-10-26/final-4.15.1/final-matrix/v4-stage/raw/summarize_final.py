from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,os
OUT=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def metadata(p):return {'bytes':p.stat().st_size,'sha256':sha(p)}
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
frozen=json.loads((OUT/'frozen-inputs.json').read_text())
summary={'kind':'derived_final_browser_matrix_summary','generated_at':datetime.now(timezone.utc).isoformat(),'source':frozen['source'],'verification':frozen['verification'],'registered_programs_per_engine':33,'maximum_engine_workers':3,'engines':{},'runtime_note':'Original native HTTP, motion, assertions, performance budgets and non-Chromium CDP exclusions retained. WebKit uses actual custom runtime libraries with official skip-static-host-preflight flag, not skipped product assertions. Linux engines do not certify physical Safari/iOS devices.'}
cleanup={}
for eng in ('chromium','firefox','webkit'):
 d=OUT/eng;n=json.loads((d/'native-report.json').read_text());r=json.loads((d/'run-summary.json').read_text())
 assert n['status']!='running',eng
 assert n['source']==frozen['source'] and n['verification']==frozen['verification'],eng
 for outcome in list(n['checks'])+list(n['browsers'].values()):
  log=outcome.get('log')
  if log:
   actual=metadata(Path(log['path']))
   assert actual=={k:log[k] for k in ('bytes','sha256')},log
 passed=sum(c['status']=='passed' for c in n['checks'])
 summary['engines'][eng]={'status':n['status'],'native_completed':n['completed'],'native_passed':n['passed'],'native_report':str((d/'native-report.json').relative_to(OUT)),'native_report_sha256':sha(d/'native-report.json'),'scope':n['scope'],'browser_probe':n['browsers'][eng],'executed_programs':len(n['checks']),'passed_programs':passed,'failed_programs':len(n['checks'])-passed,'failures':[c for c in n['checks'] if c['status']!='passed'],'unexecuted_checks':n['unexecuted_checks'],'current_check':n['current_check'],'source_unchanged':n['source_unchanged'],'verification_unchanged':n['verification_unchanged'],'integrity_errors':n['integrity_errors'],'runner_summary':r}
 worker=json.loads((d/'worker.json').read_text());alive=True
 try:os.killpg(worker['process_group'],0)
 except ProcessLookupError:alive=False
 cleanup[eng]={'worker':worker,'matrix_process_group_alive':alive}
 assert not alive,f'{eng} original worker group still alive'
 # Per-engine inventory binds the original native report and complete logs; self excluded.
 entries={str(p.relative_to(d)):metadata(p) for p in sorted(d.rglob('*')) if p.is_file() and p!=d/'raw-files.json'}
 write(d/'raw-files.json',{'schema':1,'self_excluded':True,'file_count':len(entries),'bytes':sum(x['bytes'] for x in entries.values()),'files':entries})
summary['all_engines_completed']=all(v['native_completed'] and v['executed_programs']==33 for v in summary['engines'].values())
summary['all_three_registered33_passed']=summary['all_engines_completed'] and all(v['native_passed'] and v['runner_summary']['exit_code']==0 and v['source_unchanged'] and v['verification_unchanged'] and not v['integrity_errors'] for v in summary['engines'].values())
summary['invoked_programs']=sum(v['executed_programs'] for v in summary['engines'].values())
summary['passed_programs']=sum(v['passed_programs'] for v in summary['engines'].values())
summary['failed_programs']=sum(v['failed_programs'] for v in summary['engines'].values())
write(OUT/'final-summary.json',summary)
write(OUT/'worker-cleanup.json',{'at':datetime.now(timezone.utc).isoformat(),'all_matrix_process_groups_closed':True,'engines':cleanup,'scope':'Actual original native matrix process groups; no other agent/server groups were terminated.'})
entries={str(p.relative_to(OUT)):metadata(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p!=OUT/'manifest.json'}
write(OUT/'manifest.json',{'schema':1,'scope':'Final actual three-engine native33 source-frozen run, including complete raw reports/logs and full external107 snapshot. Manifest itself excluded.','file_count':len(entries),'bytes':sum(x['bytes'] for x in entries.values()),'files':entries})
print(json.dumps({'all_engines_completed':summary['all_engines_completed'],'all_three_registered33_passed':summary['all_three_registered33_passed'],'invoked_programs':summary['invoked_programs'],'passed_programs':summary['passed_programs'],'failed_programs':summary['failed_programs'],'manifest_sha256':sha(OUT/'manifest.json')},ensure_ascii=False))
