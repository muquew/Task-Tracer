from pathlib import Path
import sys,json,subprocess,os,time,hashlib
ROOT=Path('/workspace/Task-Tracer-redesign')
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
from check import source_identity,verification_identity,timestamp,atomic_report
scope=sys.argv[1]; command=[sys.executable,*sys.argv[2:]]
expected=json.loads((OUT/'frozen-inputs.json').read_text())
report={'scope':scope,'phase':'targeted browser correctness after save-control CSS and navigation precondition fixes','command':command,'status':'running','started_at':timestamp(),'completed':False,'passed':False,'source':source_identity(),'verification':verification_identity(),'input_snapshot':'inputs/'}
path=OUT/(scope+'.json');log_path=OUT/(scope+'.log')
atomic_report(path,report)
started=time.monotonic();error=None;code=None
try:
    assert report['source']==expected['source'] and report['verification']==expected['verification'],'Inputs changed before this affected program started'
    with log_path.open('w') as log:
        result=subprocess.run(command,cwd=ROOT,env=os.environ.copy(),stdout=log,stderr=subprocess.STDOUT)
        code=result.returncode
except BaseException as exc:
    error=f'{type(exc).__name__}: {exc}'
finally:
    report.update(finished_at=timestamp(),elapsed_seconds=round(time.monotonic()-started,3),exit_code=code,error=error,source_final=source_identity(),verification_final=verification_identity(),completed=True)
    report['source_unchanged']=report['source']==report['source_final'];report['verification_unchanged']=report['verification']==report['verification_final']
    report['passed']=code==0 and error is None and report['source_unchanged'] and report['verification_unchanged']
    report['status']='passed' if report['passed'] else 'failed'
    atomic_report(path,report)
    print(json.dumps({'scope':scope,'passed':report['passed'],'exit_code':code,'error':error,'source_unchanged':report['source_unchanged'],'verification_unchanged':report['verification_unchanged'],'report':str(path)}),flush=True)
    if log_path.exists(): print(log_path.read_text()[-8000:],flush=True)
raise SystemExit(0 if report['passed'] else 1)
