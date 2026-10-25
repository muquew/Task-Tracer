from contextlib import nullcontext
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, '/workspace/Task-Tracer/tools')
import workspace_failure_playwright as module

results = []
with tempfile.TemporaryDirectory(prefix='workspace-report-lifecycle-') as folder:
    output = Path(folder) / 'report.json'
    output.write_text(json.dumps({'run_id':'older-success','passed':True,'completed':True,'status':'passed'}))
    observed_initial = []
    def broken_source():
        current=json.loads(output.read_text())
        if not observed_initial:
            assert current['run_id'] != 'older-success'
            assert current['status']=='initializing' and not current['passed'] and not current['completed']
            assert current['source'] is None and current['tool_sha256'] is None
            observed_initial.append(current['run_id'])
        raise RuntimeError('Synthetic broken release source contract')
    with patch.object(module, 'source_identity', side_effect=broken_source), \
         patch.object(module, 'sync_playwright', side_effect=AssertionError('Browser must not launch')):
        try:
            module.run('chromium',200,6,['probe'],output)
        except RuntimeError as error:
            assert 'broken release source' in str(error)
        else:
            raise AssertionError('Initialization failure unexpectedly succeeded')
    failed=json.loads(output.read_text())
    assert failed['status']=='failed' and not failed['passed'] and not failed['completed']
    assert failed['source'] is None and failed['source_final'] is None and failed['integrity_errors']
    assert failed['finished_at'] and failed['error']
    results.append({'case':'initial_capture_clears_older_success','passed':True})

    page=SimpleNamespace(on=lambda *args:None)
    context=SimpleNamespace(new_page=lambda:page,close=lambda:None)
    browser=SimpleNamespace(version='mock-no-browser',new_context=lambda **options:context,close=lambda:None)
    playwright=SimpleNamespace(chromium=SimpleNamespace(launch=lambda **options:browser))
    identity={'files':{'synthetic-runtime':'fixed'},'sha256':'same'}
    for label, final in [('final_capture_failure',RuntimeError('Synthetic final capture failure')),
                         ('unchanged_control',identity)]:
        with patch.object(module, 'source_identity', side_effect=[identity,final]), \
             patch.object(module,'local_server',return_value=nullcontext('http://synthetic.invalid/')), \
             patch.object(module,'sync_playwright',return_value=nullcontext(playwright)), \
             patch.object(module,'prepare',return_value={'tasks':[],'config':[]}), \
             patch.dict(module.CASES,{'probe':lambda *args:{'mock_operation':True}}):
            error=None
            try:
                module.run('chromium',200,6,['probe'],output)
            except RuntimeError as exception:
                error=exception
        current=json.loads(output.read_text())
        assert current['completed'] and current['cases'][0]['passed']
        if label=='final_capture_failure':
            assert error and 'final capture' in str(error)
            assert current['status']=='failed' and not current['passed'] and not current['source_unchanged']
            assert current['source_final'] is None and current['integrity_errors'] and current['finished_at']
        else:
            assert error is None and current['status']=='passed' and current['passed']
            assert current['source_unchanged'] and current['tool_unchanged'] and not current['integrity_errors']
        results.append({'case':label,'passed':True})

Path('/tmp/task-tracer-workspace-report-lifecycle-probe.json').write_text(json.dumps({'passed':True,'cases':results},indent=2)+'\n')
print(json.dumps({'passed':True,'cases':results}))
