import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, '/workspace/Task-Tracer/tools')
spec = importlib.util.spec_from_file_location('repeat_merge_probe_module', '/workspace/Task-Tracer/tools/repeat_merge_playwright.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
results = []
with tempfile.TemporaryDirectory(prefix='repeat-merge-report-') as folder:
    for phase in ('initial-source', 'after-source'):
        output = Path(folder) / f'{phase}.json'
        output.write_text(json.dumps({'status': 'passed', 'passed': True, 'cases': [{'name': 'old-success'}]}))
        calls = []
        def capture():
            current = json.loads(output.read_text())
            assert current['passed'] is False, 'Previous successful report remained visible during a new run'
            assert not any(case.get('name') == 'old-success' for case in current['cases'])
            calls.append(current['status'])
            if len(calls) == 1:
                assert current['status'] == 'running' and current['finished_at'] is None
                if phase == 'initial-source':
                    raise ValueError('Synthetic source contract failure before browser startup')
                return {'files': {'synthetic-input': 'synthetic-fingerprint'}, 'sha256': 'synthetic-aggregate'}
            raise OSError('Synthetic final source capture failure')
        with patch.object(module, 'source_identity', side_effect=capture), \
             patch.object(module, 'local_server', side_effect=RuntimeError('Synthetic server setup failure')) as server, \
             patch.object(module, 'sync_playwright', side_effect=AssertionError('Browser must not start')) as playwright, \
             patch.object(sys, 'argv', ['repeat_merge_playwright.py', '--case', 'replace-roundtrip', '--output', str(output)]):
            try:
                module.main()
                raise AssertionError('A failed startup returned success')
            except (ValueError, RuntimeError) as error:
                expected = 'Synthetic source contract failure before browser startup' if phase == 'initial-source' else 'Synthetic server setup failure'
                assert str(error) == expected, 'Final source failure masked the original failure'
            assert len(calls) == 2 and not playwright.called
            assert server.call_count == (0 if phase == 'initial-source' else 1)
        final = json.loads(output.read_text())
        assert final['status'] == 'failed' and final['passed'] is False and not final['cases']
        assert final['finished_at'] and final['error'].endswith(expected)
        assert final['source_final'] is None and final['source_final_error'].startswith('OSError: Synthetic final')
        results.append({'case': phase, 'passed': True, 'observed_capture_states': calls, 'final_report': final})
result = {'scope': 'Isolated report lifecycle probe using standard-library mocks; no browser or local server started',
          'cases': results, 'passed': True}
Path('/tmp/task-tracer-repeat-merge-report-probe.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'passed': True, 'cases': [entry['case'] for entry in results], 'browser_started': False}))
