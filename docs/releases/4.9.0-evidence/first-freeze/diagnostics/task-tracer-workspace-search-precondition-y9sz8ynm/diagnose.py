from pathlib import Path
import hashlib,json,subprocess,sys,traceback,time
sys.dont_write_bytecode=True
ROOT=Path('/workspace/Task-Tracer-redesign')
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
from check import source_identity,verification_identity,timestamp
from playwright.sync_api import expect
import workspace_failure_playwright as original
freeze_path=Path('/tmp/task-tracer-4.9.0-final-pu_nzs6d/frozen-inputs.json')
freeze_raw=freeze_path.read_bytes(); freeze=json.loads(freeze_raw)
assert hashlib.sha256(freeze_raw).hexdigest()=='da74449f278e4633a9be1e5d91a291a98fa7cee55c14bdd1f1c16bd44b230ae4'
r={'scope':'External single-case diagnostic; original edit-task-abort with explicit actual filtered-result count=1 precondition; not an original workspace_failure or matrix pass','status':'running','passed':False,'started_at':timestamp(),'source':source_identity(),'verification':verification_identity(),'wrapper_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'original_workspace_failure_sha256':hashlib.sha256((ROOT/'tools/workspace_failure_playwright.py').read_bytes()).hexdigest(),'original_smoke_helper_sha256':hashlib.sha256((ROOT/'tools/smoke_playwright.py').read_bytes()).hexdigest(),'freeze_path':str(freeze_path),'freeze_sha256':hashlib.sha256(freeze_raw).hexdigest(),'selected_case':'edit-task-abort','tasks':200,'subtasks_per_task':6,'timeout_changed':False,'force_click_used':False,'fixed_sleep_added':False,'observations':[],'error':None}
assert r['source']==freeze['source'] and r['verification']==freeze['verification']
(OUT/'diagnostic.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
original_click=original.click_task_action
def wait_for_filtered_task_then_original_action(task,action):
    assert action=='edit',f'Unexpected diagnostic action: {action}'
    page=task.page
    before=page.locator('.task-item').count()
    expect(page.locator('.task-item')).to_have_count(1)
    r['observations'].append({'action':action,'visible_task_rows_before_precondition':before,'visible_task_rows_after_precondition':page.locator('.task-item').count(),'search':page.locator('#searchInput').input_value()})
    print('External precondition: '+json.dumps(r['observations'][-1],ensure_ascii=False),flush=True)
    return original_click(task,action)
original.click_task_action=wait_for_filtered_task_then_original_action
failure=None
try:
    original.run('chromium',200,6,['edit-task-abort'],OUT/'original-case-result.json')
    r['status']='passed';r['passed']=True
except BaseException as error:
    failure=error;r['status']='failed';r['error']=f'{type(error).__name__}: {error}';r['traceback']=traceback.format_exc()
finally:
    original.click_task_action=original_click
    r['finished_at']=timestamp();r['source_final']=source_identity();r['verification_final']=verification_identity()
    r['source_unchanged']=r['source']==r['source_final']==freeze['source'];r['verification_unchanged']=r['verification']==r['verification_final']==freeze['verification']
    r['freeze_unchanged']=freeze_path.read_bytes()==freeze_raw
    r['passed']=r['passed'] and r['source_unchanged'] and r['verification_unchanged'] and r['freeze_unchanged']
    if not r['passed']:r['status']='failed'
    (OUT/'diagnostic.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'diagnostic_status':r['status'],'passed':r['passed'],'source_unchanged':r['source_unchanged'],'verification_unchanged':r['verification_unchanged'],'output':str(OUT)},ensure_ascii=False),flush=True)
if failure:raise failure
assert r['passed']
