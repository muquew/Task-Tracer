from datetime import datetime, timezone
import json, os, signal, subprocess, sys
from pathlib import Path

ROOT = Path('/workspace/Task-Tracer')
sys.path.insert(0, str(ROOT / 'tools'))
from check import atomic_report, source_identity, verification_identity, stop_child

freeze_path = Path('/tmp/task-tracer-4.8.6-freeze.json')
state_path = Path('/tmp/task-tracer-4.8.6-integrated-lane.json')
assert freeze_path.is_file() and not state_path.exists()
freeze = json.loads(freeze_path.read_text())
steps = [
    ('actual-4.8.5-upgrade', ['tools/upgrade_playwright.py', '--baseline-archive', 'dist/task-tracer-4.8.5.zip'], '/tmp/task-tracer-upgrade-4.8.5-to-4.8.6.log'),
    ('complete-58', ['tools/check.py', '--keep-going', '--report', 'dist/check-results-4.8.6.json'], '/tmp/task-tracer-4.8.6-check.log'),
]
env = os.environ.copy()
env.update({'PYTHONDONTWRITEBYTECODE':'1','PYTHONUNBUFFERED':'1','TASK_TRACER_BROWSER_EXECUTABLE':'/usr/bin/chromium'})
state = {'schema_version':1,'status':'initializing','completed':False,'passed':False,'started_at':datetime.now(timezone.utc).isoformat(),'finished_at':None,'current':None,'steps':[],'freeze':str(freeze_path),'error':None}
child = None

def publish(): atomic_report(state_path, state)
def verify():
    assert source_identity() == freeze['source'], 'Frozen source changed'
    assert verification_identity() == freeze['verification'], 'Frozen verification inputs changed'
def interrupted(signum, frame): raise KeyboardInterrupt(f'Signal {signum}')
for sig in (signal.SIGINT,signal.SIGTERM): signal.signal(sig, interrupted)
publish()
try:
    verify()
    for name,args,logfile in steps:
        verify()
        assert not Path(logfile).exists(), f'Refusing to overwrite prior log: {logfile}'
        state.update(status='running',current=name)
        publish()
        print(f'Starting final lane: {name}',flush=True)
        started=datetime.now(timezone.utc).isoformat()
        with Path(logfile).open('x') as output:
            child=subprocess.Popen([sys.executable,*args],cwd=ROOT,env=env,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
            code=child.wait()
            child=None
        verify()
        state['steps'].append({'name':name,'arguments':args,'log':logfile,'started_at':started,'finished_at':datetime.now(timezone.utc).isoformat(),'exit_code':code})
        publish()
        print(f'Finished final lane: {name}, exit={code}',flush=True)
        if code: raise RuntimeError(f'{name} failed: {code}; original report/log preserved')
    state.update(status='passed',completed=True,passed=True,current=None)
except BaseException as error:
    if child is not None: stop_child(child)
    state.update(status='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed',error=f'{type(error).__name__}: {error}',completed=False)
    raise
finally:
    state['finished_at']=datetime.now(timezone.utc).isoformat()
    publish()
