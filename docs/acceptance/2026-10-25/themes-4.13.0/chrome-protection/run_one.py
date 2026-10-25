#!/usr/bin/env python3
"""Run one authorized small check and record identities without source copies."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path('/workspace/Task-Tracer-themes')
OUT = Path('/tmp/task-tracer-4.13.0-chrome-protection')
sys.path.insert(0, str(ROOT / 'tools'))
from build_release import DISTRIBUTION_SOURCES, validated_source
from validate_static import app_version, resource_version

SCOPES = {
 'craft_accent_playwright.py': {
   'chrome':['eight real radio/light-dark pairs and refreshes: meta theme-color equals computed opaque chrome-solid','invalid legacy preference fallback and one trusted cross-tab colour change','exact IndexedDB/task-node preservation and canonical manifest URL'],
   'roundtrip':['four real native-radio palette preferences, independent light/dark/System, refresh and unchanged task nodes/IndexedDB','eight actual light/dark skins across desktop list/sidebar, mobile list/dock, mobile drawer, full editor and appearance:40 original-rule axe states'],
   'keyboard':['native radio arrows/Space, exclusive selection and one Tab stop','320/390/1280px gallery layout, visible label focus, persisted choice and unchanged task selection/IndexedDB'],
   'controls':['all eight skins: actual parent task, subtask and batch checked/unchecked and marker contrast at least3, alpha255','resting/hover/keyboard states, real completion Undo and exact task data restoration'],
   'sync-draft':['trusted cross-tab storage events, removal and clear','exact unsaved draft values/focus/selection, saved task nodes and IndexedDB preserved; subsequent real save'],
   'fallback':['legacy invalid preference fallback and genuine blocked accent Storage read/write','live radio choice remains usable without task/config/history changes']
 },
 'accessibility_i18n_audit.py': {'all':['normal native bounded settling and original axe/focus/layout assertions','real gallery, navigation, views, editor, settings and related normal surfaces; scaled workload excluded']}
}

def digest(data):
    return hashlib.sha256(data).hexdigest()

def manifest(kind, files):
    fingerprint = digest(json.dumps(files, sort_keys=True, separators=(',', ':')).encode())
    folder = OUT / 'fingerprints'
    folder.mkdir(exist_ok=True)
    path = folder / f'{kind}-{fingerprint}.json'
    if not path.exists():
        path.write_text(json.dumps(files, sort_keys=True, indent=2) + '\n')
    return {'sha256':fingerprint,'count':len(files),'manifest':str(path)}

def inputs(program):
    payload = {}
    for target, source in sorted(DISTRIBUTION_SOURCES.items()):
        data = validated_source(ROOT, source).read_bytes()
        if target in ('README.md','README_zh_cn.md'):
            data = data.replace(b'](../LICENSE)', b'](LICENSE)')
        payload[target] = digest(data)
    assert len(payload) == 23
    tools = {str(path.relative_to(ROOT)):digest(path.read_bytes()) for path in sorted((ROOT/'tools').glob('*.py'))}
    runtime = {name:value for name,value in payload.items() if name not in ('README.md','README_zh_cn.md') and not name.startswith('screenshots/')}
    return {'program_sha256':digest(program.read_bytes()),'index_sha256':payload['index.html'],
            'payload23':manifest('payload23',payload),'runtime_payload':manifest('runtime',runtime),
            'tools':manifest('tools',tools)}, payload, tools

name, entry, *arguments = sys.argv[1:]
program = ROOT / entry
log = OUT / f'{name}.log'
result_path = OUT / f'{name}.result.json'
assert program.is_file() and not log.exists() and not result_path.exists(), 'Use a new run name; never overwrite a first failure'
before, before_payload, before_tools = inputs(program)
started = datetime.now(timezone.utc).isoformat()
timer = time.monotonic()
env = dict(os.environ)
env.update({'PYTHONDONTWRITEBYTECODE':'1','XDG_CACHE_HOME':'/workspace/.cache',
            'PLAYWRIGHT_BROWSERS_PATH':'/workspace/.cache/ms-playwright',
            'TASK_TRACER_BROWSER_EXECUTABLE':'/usr/bin/chromium','TASK_TRACER_PRODUCTION_HEADERS':'1'})
bootstrap = OUT / 'csp_wait_bootstrap.py'
argv = [sys.executable,'-u',str(bootstrap),str(program),*arguments]
with log.open('w') as output:
    try:
        completed = subprocess.run(argv,cwd=ROOT,env=env,stdout=output,stderr=subprocess.STDOUT,timeout=600)
        status = completed.returncode
    except subprocess.TimeoutExpired:
        status = 124
        output.write('\nProtection runner timeout after 600 seconds\n')
elapsed = round(time.monotonic()-timer,3)
after, after_payload, after_tools = inputs(program)
case = arguments[arguments.index('--case')+1] if '--case' in arguments else 'all'
scope = SCOPES.get(program.name,{}).get(case,[f'explicit case {case}'])
source = (ROOT/'index.html').read_text()
result = {'name':name,'argv':argv,'exit':status,'elapsed_seconds':elapsed,'started_at_utc':started,
          'finished_at_utc':datetime.now(timezone.utc).isoformat(),'scope':scope,'case':case,
          'viewport':arguments[arguments.index('--viewport')+1] if '--viewport' in arguments else None,
          'log':str(log),'external_wait_adapter_sha256':digest(bootstrap.read_bytes()),'app_version_at_finish':app_version(source),'resource_version_at_finish':resource_version(source),
          'production_headers':True,'native_animation_settler':True,'external_animation_override':False,'axe_injection':'pinned real same-origin local file; no CSP relaxation or service-worker blocking',
          'inputs_before':before,'inputs_after':after,
          'changed_payload_files':[key for key in before_payload if before_payload[key]!=after_payload[key]],
          'changed_tool_files':[key for key in set(before_tools)|set(after_tools) if before_tools.get(key)!=after_tools.get(key)]}
result_path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'name':name,'exit':status,'elapsed_seconds':elapsed,'result':str(result_path)},ensure_ascii=False),flush=True)
sys.exit(status)
