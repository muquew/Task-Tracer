python - <<'PY'
import json, os, re, sys
from pathlib import Path

try:
    path = Path('dist/check-results.json')
    if path.is_symlink() or path.stat().st_size > 2_000_000:
        raise ValueError
    checks = json.loads(path.read_text(encoding='utf-8'))['checks']
    failed = isinstance(checks, list) and any(isinstance(item, dict)
        and item.get('program') == 'smoke_playwright.py'
        and type(item.get('exit_code')) is int and -255 <= item['exit_code'] <= 255
        and item['exit_code'] != 0 for item in checks)
except (OSError, ValueError, TypeError, KeyError):
    failed = False
if not failed:
    raise SystemExit(0)

tools = Path('tools').resolve()
known = {path.name for path in tools.glob('*.py')
         if re.fullmatch(r'[a-z][a-z0-9_]{0,79}\.py', path.name)}
def identifier(value):
    return value if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,79}', value) else 'unknown'
def outcome(phase, error=None):
    if error is None:
        print(f'::notice::{phase} pass')
        return
    kind = identifier(type(error).__name__)
    location, frame = None, error.__traceback__
    while frame is not None:
        code = frame.tb_frame.f_code
        source = Path(code.co_filename).resolve()
        if source.parent == tools and source.name in known and 0 < frame.tb_lineno <= 1_000_000:
            location = (source.name, frame.tb_lineno, identifier(code.co_name))
        frame = frame.tb_next
    if location is None:
        print(f'::error::{phase} fail {kind} source=unavailable')
    else:
        name, line, function = location
        print(f'::error file=tools/{name},line={line}::{phase} fail {kind} {name}:{line}:{function}')

sys.path.insert(0, str(tools))
try:
    import smoke_playwright as smoke
    from playwright.sync_api import sync_playwright
except Exception as error:
    outcome('smoke_setup', error)
    raise

def capabilities(page, phase, stage):
    language = page.locator('html').get_attribute('lang')
    language = language if language in {'en', 'zh-CN'} else 'other'
    labels = json.loads(Path(f'resources/{language}.json').read_text())['notifications'] if language != 'other' else {}
    data = page.evaluate("""labels => {
        const exists = 'Notification' in window;
        let permission = exists ? window.Notification?.permission : 'unsupported';
        const button = document.getElementById('notificationToggleBtn');
        return {exists, permission, state:button?.dataset.notificationState,
            pressed:button?.getAttribute('aria-pressed') === 'true',
            enabled:button?.classList.contains('notifications-enabled') === true,
            label_disable:typeof labels.disable === 'string' && button?.getAttribute('aria-label') === labels.disable,
            label_enable:typeof labels.enable === 'string' && button?.getAttribute('aria-label') === labels.enable};
    }""", {'enable':labels.get('enable'), 'disable':labels.get('disable')})
    permission = data.get('permission')
    permission = permission if permission in {'granted', 'default', 'denied', 'unsupported'} else 'other'
    state = data.get('state')
    state = state if state in {'notificationUnsupported', 'notificationBlocked', 'notificationEnabled', 'notificationDisabled'} else 'other'
    fields = {'Notification':data.get('exists') is True, 'permission':permission,
        'lang':language, 'state':state, 'pressed':data.get('pressed') is True,
        'enabled':data.get('enabled') is True, 'label_disable':data.get('label_disable') is True,
        'label_enable':data.get('label_enable') is True}
    rendered = ' '.join(f'{name}={str(value).lower() if type(value) is bool else value}' for name,value in fields.items())
    print(f'::notice::{phase} {stage} {rendered}')

key = 'TASK_TRACER_BROWSER_EXECUTABLE'
present, saved = key in os.environ, os.environ.get(key)
def restore():
    if present:
        os.environ[key] = saved
    else:
        os.environ.pop(key, None)
full_executable = None
try:
    smoke.ensure_conda_library_path()
    with smoke.local_server() as url, sync_playwright() as playwright:
        full_executable = playwright.chromium.executable_path
        for phase, executable in [('notification_default', None), ('notification_full', full_executable)]:
            browser = context = None
            try:
                if executable is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = executable
                browser = playwright.chromium.launch(**smoke.browser_launch_options())
                context = browser.new_context(accept_downloads=True)
                context.grant_permissions(['notifications'], origin=smoke.get_origin(url))
                page = context.new_page()
                smoke.clear_app_data(page, url)
                try:
                    capabilities(page, phase, 'before_helper')
                except Exception as error:
                    outcome(phase + '_before', error)
                try:
                    smoke.exercise_notifications(page)
                except Exception as error:
                    outcome(phase, error)
                else:
                    outcome(phase)
                finally:
                    try:
                        capabilities(page, phase, 'after_helper')
                    except Exception as error:
                        outcome(phase + '_after', error)
            except Exception as error:
                outcome(phase + '_setup', error)
            finally:
                try:
                    if context is not None:
                        context.close()
                finally:
                    try:
                        if browser is not None:
                            browser.close()
                    finally:
                        restore()
except Exception as error:
    outcome('notification_setup', error)
finally:
    restore()
try:
    smoke.ensure_conda_library_path()
    if full_executable is None:
        with sync_playwright() as playwright:
            full_executable = playwright.chromium.executable_path
    os.environ[key] = full_executable
    with smoke.local_server() as url:
        smoke.smoke(url)
except Exception as error:
    outcome('smoke_full', error)
    raise
else:
    outcome('smoke_full')
finally:
    restore()
PY
