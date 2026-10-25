import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import uuid

ROOT = Path('/workspace/Task-Tracer')
sys.path.insert(0, str(ROOT / 'tools'))
from accessibility_i18n_audit import audit_subtask_checkbox_visibility, seed_tasks
from check import atomic_report, source_identity, verification_identity
from smoke_playwright import local_server, browser_launch_options, clear_app_data
from validate_static import app_version
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument('--phase', required=True, choices=['red','green'])
args = parser.parse_args()
run_id = str(uuid.uuid4())
output = ROOT / 'docs/releases' / f'checkbox-visibility-4.8.6-{args.phase}' / run_id
output.mkdir(parents=True)
(output/'runner.py').write_bytes(Path(__file__).read_bytes())
(output/'accessibility_i18n_audit.py').write_bytes((ROOT/'tools/accessibility_i18n_audit.py').read_bytes())
now = lambda: datetime.now(timezone.utc).isoformat()
source, verification = source_identity(), verification_identity()
planned = [{'engine':e,'width':w,'height':800 if w==1280 else 844} for e in ('chromium','firefox','webkit') for w in (1280,390)] if args.phase=='green' else [{'engine':'chromium','width':1280,'height':800}]
report = {'run_id':run_id,'phase':args.phase,'started_at':now(),'status':'initializing','completed':False,'passed':False,'source':source,'verification':verification,'source_final':None,'verification_final':None,'source_unchanged':False,'verification_unchanged':False,'app_version':app_version((ROOT/'index.html').read_text()),'base_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'planned':planned,'checks':[],'current':None,'error':None,'scope':'Actual rendered SVG mark/background contrast, checked-vs-unchecked fill distinction, light/dark resting/hover/keyboard focus, Space completion and reversal. Not full WCAG compliance or physical-device acceptance.'}
path=output/'report.json'
atomic_report(path,report)
print(f'OUTPUT {output}',flush=True)
failure=None
try:
    with local_server() as url, sync_playwright() as pw:
        for spec in planned:
            report['status']='running';report['current']=spec;atomic_report(path,report)
            label=f"{spec['engine']}-{spec['width']}"
            directory=output/label;directory.mkdir()
            observations=[];errors=[]
            item={'engine':spec['engine'],'width':spec['width'],'height':spec['height'],'status':'running','passed':False,'started_at':now(),'observations':observations,'page_errors':errors,'error':None}
            started=time.monotonic()
            options=browser_launch_options() if spec['engine']=='chromium' else {'headless':True}
            browser=getattr(pw,spec['engine']).launch(timeout=30000,**options)
            item['browser_version']=browser.version
            context=browser.new_context(locale='en-US',reduced_motion='reduce',viewport={'width':spec['width'],'height':spec['height']})
            page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            try:
                clear_app_data(page,url)
                seed_tasks(page)
                audit_subtask_checkbox_visibility(page,label,observations,directory)
                assert len(observations)==6 and not errors
                item.update(status='passed',passed=True)
            except BaseException as error:
                item.update(status='failed',error=f'{type(error).__name__}: {error}',traceback=traceback.format_exc())
                failure=error
            finally:
                context.close();browser.close()
                item.update(finished_at=now(),duration_seconds=round(time.monotonic()-started,3))
                report['checks'].append(item)
                atomic_report(path,report)
            if failure: raise failure
    report.update(status='passed',passed=True)
except BaseException as error:
    report.update(status='failed',error=f'{type(error).__name__}: {error}')
    print(traceback.format_exc(),flush=True)
    failure=error
finally:
    report.update(completed=True,current=None,finished_at=now(),source_final=source_identity(),verification_final=verification_identity())
    report['source_unchanged']=report['source']==report['source_final']
    report['verification_unchanged']=report['verification']==report['verification_final']
    if not report['source_unchanged'] or not report['verification_unchanged']:
        report.update(status='failed',passed=False,error='Source or verification input changed during this attempt')
        failure=RuntimeError(report['error'])
    report['unexecuted']=planned[len(report['checks']):]
    atomic_report(path,report)
    inventory={}
    for file in output.rglob('*'):
        if file.is_file():
            data=file.read_bytes();inventory[file.relative_to(output).as_posix()]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    (output/'files.json').write_text(json.dumps(inventory,indent=2)+'\n')
    print(json.dumps({'report':str(path),'status':report['status'],'checks':len(report['checks']),'observations':sum(len(x['observations']) for x in report['checks']),'source_unchanged':report['source_unchanged'],'verification_unchanged':report['verification_unchanged']},ensure_ascii=False),flush=True)
sys.exit(1 if failure else 0)
