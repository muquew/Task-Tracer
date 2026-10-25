from pathlib import Path
import hashlib,inspect,json,sys,traceback
sys.dont_write_bytecode=True
ROOT=Path('/workspace/Task-Tracer-redesign');OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
from check import source_identity,verification_identity,timestamp
import smoke_playwright as smoke
import views_delete_playwright as original
freeze_path=Path('/tmp/task-tracer-4.9.0-final-pu_nzs6d/frozen-inputs.json')
freeze_raw=freeze_path.read_bytes();freeze=json.loads(freeze_raw)
assert hashlib.sha256(freeze_raw).hexdigest()=='da74449f278e4633a9be1e5d91a291a98fa7cee55c14bdd1f1c16bd44b230ae4'
source=inspect.getsource(smoke.reveal_workspace_control)
assert source.count('control.scroll_into_view_if_needed()')==1
modified=source.replace('control.scroll_into_view_if_needed()','control.click(trial=True)')
(OUT/'reveal.original.py').write_text(source)
(OUT/'reveal.trial.py').write_text(modified)
namespace=dict(smoke.__dict__)
exec(compile(modified,str(OUT/'reveal.trial.py'),'exec'),namespace)
trial_reveal=namespace['reveal_workspace_control']
r={'scope':'External diagnostic of original views_delete session/late_completion only, with exact global-control helper clone replacing explicit scroll by normal Locator.click(trial=True). Not an original unmodified program or matrix pass.','status':'running','passed':False,'started_at':timestamp(),'source':source_identity(),'verification':verification_identity(),'wrapper_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'original_views_delete_sha256':hashlib.sha256((ROOT/'tools/views_delete_playwright.py').read_bytes()).hexdigest(),'original_smoke_helper_sha256':hashlib.sha256((ROOT/'tools/smoke_playwright.py').read_bytes()).hexdigest(),'original_function_sha256':hashlib.sha256(source.encode()).hexdigest(),'modified_function_sha256':hashlib.sha256(modified.encode()).hexdigest(),'change':'Exactly control.scroll_into_view_if_needed() -> control.click(trial=True)','preserved':'Sidebar opening, visible, enabled, inert/hidden ancestor check, viewport assertion, original late_completion injection/later draft/metadata/focus checks and timeouts','selected_case':'session','original_cli':['--browser','chromium','--case','session'],'timeout_changed':False,'force_click_used':False,'fixed_sleep_added':False,'trial_click_dispatches_action':False,'error':None}
assert r['source']==freeze['source'] and r['verification']==freeze['verification']
(OUT/'diagnostic.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
original_reveal=original.reveal_workspace_control
original_argv=sys.argv[:]
original.reveal_workspace_control=trial_reveal
sys.argv=['views_delete_playwright.py','--browser','chromium','--case','session']
failure=None
try:
    original.main()
    r['status']='passed';r['passed']=True
except BaseException as error:
    failure=error;r['status']='failed';r['error']=f'{type(error).__name__}: {error}';r['traceback']=traceback.format_exc()
finally:
    original.reveal_workspace_control=original_reveal;sys.argv=original_argv
    r['finished_at']=timestamp();r['source_final']=source_identity();r['verification_final']=verification_identity()
    r['source_unchanged']=r['source']==r['source_final']==freeze['source'];r['verification_unchanged']=r['verification']==r['verification_final']==freeze['verification'];r['freeze_unchanged']=freeze_path.read_bytes()==freeze_raw
    r['passed']=r['passed'] and r['source_unchanged'] and r['verification_unchanged'] and r['freeze_unchanged']
    if not r['passed']:r['status']='failed'
    (OUT/'diagnostic.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'diagnostic_status':r['status'],'passed':r['passed'],'source_unchanged':r['source_unchanged'],'verification_unchanged':r['verification_unchanged'],'output':str(OUT)},ensure_ascii=False),flush=True)
if failure:raise failure
assert r['passed']
