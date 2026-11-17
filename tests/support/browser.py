"""Shared browser launch and application interactions; no runnable smoke scenario."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urljoin
from playwright.sync_api import BrowserContext, Locator, Page, expect


from tests.support.paths import REPO_ROOT, source_path

DEFAULT_HOST = "127.0.0.1"

def read_service_worker_cache_name() -> str:
    service_worker = source_path("sw.js").read_text(encoding="utf-8")
    match = re.search(r"const CACHE_NAME = ['\"]([^'\"]+)['\"]", service_worker)
    if not match:
        raise AssertionError("Could not read service worker cache name")
    return match.group(1)

SW_CACHE_NAME = read_service_worker_cache_name()

def ensure_conda_library_path() -> None:
    prefix = os.environ.get("CONDA_PREFIX")
    if not prefix:
        return

    lib_path = str(Path(prefix) / "lib")
    current = os.environ.get("LD_LIBRARY_PATH", "")
    paths = [path for path in current.split(":") if path]
    if lib_path not in paths:
        os.environ["LD_LIBRARY_PATH"] = ":".join([lib_path, *paths])

def browser_launch_options(browser: str = 'chromium') -> dict[str, Any]:
    if browser not in {'chromium', 'firefox', 'webkit'}:
        raise ValueError(f'Unsupported browser engine: {browser}')
    options: dict[str, Any] = {"headless": True}
    if browser == 'chromium':
        options['chromium_sandbox'] = True
    executable = os.environ.get(f'TASK_TRACER_{browser.upper()}_EXECUTABLE')
    if browser == 'chromium' and not executable:
        executable = os.environ.get('TASK_TRACER_BROWSER_EXECUTABLE')
    if executable:
        options["executable_path"] = executable
    elif browser == 'chromium':
        # Full Chromium keeps real notification permission coverage in headless CI.
        options["channel"] = "chromium"
    return options

def iso_minutes_from_now(minutes: int) -> str:
    value = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")

def future_date(days: int = 1) -> str:
    value = datetime.now(timezone.utc) + timedelta(days=days)
    return value.strftime("%Y-%m-%d")

def due_fields_from_now(minutes: int) -> dict[str, str]:
    local_value = datetime.now().astimezone() + timedelta(minutes=minutes)
    instant = local_value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return {
        "dueDate": instant,
        "dueAt": instant,
        "dueLocalDate": local_value.strftime("%Y-%m-%d"),
        "dueLocalTime": local_value.strftime("%H:%M"),
    }

def task_locator(page: Page, task_name: str):
    exact_name = page.locator(".task-name").filter(
        has_text=re.compile(f"^{re.escape(task_name)}$")
    )
    return page.locator(".task-item").filter(has=exact_name)

def is_workbench_v5(page: Page) -> bool:
    """Identify the real five-page shell without changing its initial route."""
    return bool(page.locator('#workspaceTodayBtn').count())

def workbench_screen(page: Page) -> str | None:
    if is_workbench_v5(page):
        return page.locator('body').get_attribute('data-workspace-screen')
    return None

def navigate_workbench(page: Page, screen: str) -> None:
    """Use a visible first-level destination; preserve an already active page."""
    close_mobile_filters(page)
    assert screen in {'today', 'tasks', 'projects', 'review', 'settings'}, screen
    assert is_workbench_v5(page), 'The five-page workbench is not present'
    close_workspace_navigation(page)
    if workbench_screen(page) != screen:
        if screen == 'settings':
            control = reveal_workspace_control(page, '#workspaceSettingsBtn')
        else:
            desktop, mobile = {
                'today': ('#workspaceTodayBtn', '#mobileTodayBtn'),
                'tasks': ('#workspaceAllTasks', '#mobileTasksBtn'),
                'projects': ('#workspaceProjectsBtn', '#mobileProjectsBtn'),
                'review': ('#viewTab-stats', '#mobileReviewBtn'),
            }[screen]
            mobile_control = page.locator(mobile)
            control = mobile_control if mobile_control.is_visible() else reveal_workspace_control(page, desktop)
        expect(control).to_be_visible()
        expect(control).to_be_enabled()
        control.click()
    expect(page.locator('body')).to_have_attribute('data-workspace-screen', screen)
    tasks = page.locator('#tasksWorkspace')
    if screen in {'tasks', 'review'}:
        expect(tasks).to_be_visible()
        expect(tasks).to_have_js_property('inert', False)
    else:
        expect(tasks).to_be_hidden()
        expect(tasks).to_have_js_property('inert', True)

def ensure_task_control_workspace(page: Page) -> None:
    """Keep Review's own scope when operating its shared task/filter controls."""
    if workbench_screen(page) in {'tasks', 'review'}:
        close_workspace_navigation(page)
    else:
        return_to_task_workspace(page)

def open_settings(page: Page, section: str | None = 'data') -> None:
    """Use settings navigation; old archived applications retain their real menu."""
    workspace = page.locator('#settingsWorkspace')
    if workspace.count():
        if is_workbench_v5(page) and workspace.is_visible():
            close_workspace_navigation(page)
        if not workspace.is_visible():
            if is_workbench_v5(page):
                navigate_workbench(page, 'settings')
            elif page.locator('#captureShelf').count():
                close_workspace_navigation(page)
                page.locator('#openMenuBtn').click()
            else:
                page.locator('#openMenuBtn').click()
        expect(workspace).to_be_visible()
        expect(page.locator('#tasksWorkspace')).to_be_hidden()
        expect(page.locator('#tasksWorkspace')).to_have_js_property('inert', True)
        if section is not None:
            target = {
                'appearance': 'settingsAppearance', 'data': 'settingsData',
                'experience': 'settingsExperience', 'cleanup': 'settingsCleanup',
                'help': 'settingsHelp',
            }.get(section, section)
            button = workspace.locator(f'[data-settings-section="{target}"]')
            if button.count():
                button.click()
                expect(page.locator(f'#{target}')).to_be_visible()
                if button.get_attribute('role') == 'tab':
                    expect(button).to_have_attribute('aria-selected', 'true')
    else:
        if not page.locator('#menu').is_visible():
            page.locator('#openMenuBtn').click()
        expect(page.locator('#menu')).to_be_visible()

def ensure_capture(page: Page) -> Locator:
    """Open optional quick capture, including the archived shared Add control."""
    shelf = page.locator('#captureShelf')
    if shelf.count():
        close_workspace_navigation(page)
        if not shelf.is_visible():
            quick_entry = page.locator('#quickCaptureBtn')
            (quick_entry if quick_entry.count() else page.locator('#openModalBtn')).click()
        expect(shelf).to_be_visible()
    else:
        return_to_task_workspace(page)
    field = page.locator('#quickAddInput')
    expect(field).to_be_visible()
    assert not field.evaluate('node => Boolean(node.closest("[inert], [hidden]"))')
    return field

def open_task_editor(page: Page, *, independent: bool = False, preserve_context: bool = False) -> None:
    """Use the direct Add task action, with the real archived entry as fallback."""
    if not preserve_context or not is_workbench_v5(page):
        return_to_task_workspace(page)
    if independent and page.locator('#captureShelf').count():
        page.keyboard.press('Control+i')
    elif page.locator('#quickCaptureBtn').count():
        close_workspace_navigation(page)
        page.locator('#openModalBtn').click()
    elif page.locator('#captureShelf').count():
        ensure_capture(page)
        page.locator('#captureDetailsBtn').click()
    else:
        page.locator('#openModalBtn').click()
    expect(page.locator('#taskModal')).to_be_visible()

def help_entry(page: Page) -> Locator:
    """Return the actual Help entry in the current or archived application."""
    footer = page.locator('#helpBtn')
    return footer if footer.count() else page.locator('#helpMenuBtn')

def open_help(page: Page) -> Locator:
    """Reach Help through its actual settings category or archived footer."""
    control = help_entry(page)
    if control.get_attribute('id') == 'helpMenuBtn':
        open_settings(page, 'help')
    control.click()
    expect(page.locator('#taskModal')).to_be_visible()
    return control

def reveal_task_field(page: Page, selector: str) -> Locator:
    """Expand a real progressive-disclosure summary before using its field."""
    field = page.locator(selector)
    closed = field.locator('xpath=ancestor::details[not(@open)]')
    while closed.count():
        closed.first.locator(':scope > summary').click()
    expect(field).to_be_visible()
    return field

def select_visible_option(page: Page, selector: str, value: str) -> None:
    """Use a native select or its real enhanced button and visible option."""
    field = page.locator(selector)
    expect(field).to_have_count(1)
    identifier = field.get_attribute('id')
    button = page.locator(f'#{identifier}-custom-button') if identifier else None
    if button is not None and button.count():
        expect(button).to_be_visible()
        button.click()
        option = page.locator(f'#{identifier}-custom-button-list .custom-select-option[data-value={json.dumps(value)}]:visible')
        expect(option).to_be_visible()
        option.click()
        expect(button).to_have_attribute('aria-expanded', 'false')
    else:
        expect(field).to_be_visible()
        field.select_option(value)
    expect(field).to_have_value(value)

def _preference_origin(page: Page) -> tuple[bool, str | None, str | None]:
    workspace = page.locator('#settingsWorkspace')
    was_settings = bool(workspace.count() and workspace.is_visible())
    selected = workspace.locator('[data-settings-section][aria-selected="true"]')
    section = selected.get_attribute('data-settings-section') if selected.count() else None
    return was_settings, section, workbench_screen(page)

def _return_from_preference(page: Page, origin: tuple[bool, str | None, str | None]) -> None:
    was_settings, section, screen = origin
    if was_settings:
        if section:
            open_settings(page, section)
    elif screen is not None:
        expect(page.locator('#settingsBackBtn')).to_be_visible()
        page.locator('#settingsBackBtn').click()
        expect(page.locator('body')).to_have_attribute('data-workspace-screen', screen)
    else:
        return_to_task_workspace(page)

def return_to_task_workspace(page: Page) -> None:
    """Select the task library, retaining its own active view and scope."""
    close_mobile_filters(page)
    if is_workbench_v5(page):
        navigate_workbench(page, 'tasks')
        return
    workspace = page.locator('#settingsWorkspace')
    if workspace.count() and workspace.is_visible():
        page.locator('#settingsBackBtn').click()
        expect(workspace).to_be_hidden()
        expect(page.locator('#tasksWorkspace')).to_be_visible()
        expect(page.locator('#tasksWorkspace')).to_have_js_property('inert', False)
    elif not workspace.count() and page.locator('#menu').is_visible():
        page.keyboard.press('Escape')

def reveal_workspace_control(page: Page, selector: str | Locator) -> Locator:
    """Reach a global control through the actual navigation drawer when needed."""
    control = page.locator(selector) if isinstance(selector, str) else selector
    if control.count() and not control.evaluate("node => Boolean(node.closest('#workspaceSidebar'))"):
        close_workspace_navigation(page)
    if control.count() and control.evaluate("node => Boolean(node.closest('#tasksWorkspace'))"):
        if is_workbench_v5(page) and control.get_attribute('id') in {'focusModeToggleBtn', 'exitFocusModeBtn'}:
            return_to_task_workspace(page)
        else:
            ensure_task_control_workspace(page)
        if control.evaluate("node => Boolean(node.closest('#toolsDrawerContent'))"):
            reveal_filters(page)
    if control.count() and control.evaluate("node => Boolean(node.closest('#workspaceSidebar'))"):
        hidden = not control.is_visible() or control.evaluate(
            "node => Boolean(node.closest('[inert], [hidden], [aria-hidden=\"true\"]'))"
        )
        if hidden:
            toggle = page.locator('#workspaceNavToggle')
            expect(toggle).to_be_visible()
            if toggle.get_attribute('aria-expanded') != 'true':
                toggle.click()
    expect(control).to_be_visible()
    expect(control).to_be_enabled()
    assert not control.evaluate(
        "node => Boolean(node.closest('[inert], [hidden], [aria-hidden=\"true\"]'))"
    ), f'{selector} remains inside hidden or inert navigation'
    control.click(trial=True)
    expect(control).to_be_in_viewport()
    return control

def select_language(page: Page, language: str) -> None:
    origin = _preference_origin(page)
    if page.locator('#captureShelf').count():
        open_settings(page, 'appearance')
    select = reveal_workspace_control(page, '#languageSelect')
    select.select_option(language)
    expect(select).to_have_value(language)
    expect(select.locator('option:checked')).to_have_attribute('value', language)
    expect(page.locator('html')).to_have_attribute('lang', language)
    expect(page.locator('html')).to_have_attribute('dir', 'ltr')
    _return_from_preference(page, origin)

def close_workspace_navigation(page: Page) -> None:
    """Return to the main workspace through the navigation drawer's Escape path."""
    toggle = page.locator('#workspaceNavToggle')
    if toggle.get_attribute('aria-expanded') == 'true':
        page.keyboard.press('Escape')
        expect(toggle).to_have_attribute('aria-expanded', 'false')
        expect(toggle).to_be_focused()
        expect(page.locator('#workspaceSidebar')).to_have_attribute('aria-hidden', 'true')
    assert not page.locator('.workspace-stage').evaluate('node => node.inert'), 'Main workspace remains inert after navigation closes'

def select_theme_preference(page: Page, preference: str) -> str:
    assert preference in {'light', 'dark', 'system'}, preference
    origin = _preference_origin(page)
    if page.locator('#captureShelf').count():
        open_settings(page, 'appearance')
    select = reveal_workspace_control(page, '#themeToggleBtn')
    select.select_option(preference)
    resolved = preference if preference != 'system' else page.evaluate(
        "matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'"
    )
    expect(select).to_have_value(preference)
    expect(page.locator('html')).to_have_attribute('data-theme', resolved)
    expect(select).to_be_enabled()
    _return_from_preference(page, origin)
    return resolved

def select_accent_preference(page: Page, preference: str) -> None:
    """Choose a workspace theme through its visible native radio tile."""
    assert preference in {'iris', 'ocean', 'pine', 'berry'}, preference
    origin = _preference_origin(page)
    open_settings(page, 'appearance')
    radio = page.locator(f'input[type="radio"][name="workspaceTheme"][value="{preference}"]')
    if radio.count():
        expect(radio).to_be_visible()
        expect(radio).to_be_enabled()
        radio.check()
        expect(radio).to_be_checked()
        expect(page.locator('input[name="workspaceTheme"]:checked')).to_have_count(1)
    else:
        legacy = page.locator('#accentSelect')
        expect(legacy).to_be_visible()
        legacy.select_option(preference)
        expect(legacy).to_have_value(preference)
    expect(page.locator('html')).to_have_attribute('data-accent', preference)
    _return_from_preference(page, origin)

def enter_batch_mode(page: Page) -> None:
    """Enter selection mode after exposing the actual filter toolbar."""
    return_to_task_workspace(page)
    reveal_filters(page)
    close_mobile_filters(page)
    button = page.locator('#batchModeBtn')
    if button.get_attribute('aria-pressed') != 'true':
        button.click()
    expect(page.locator('#batchToolbar')).to_be_visible()

def reveal_batch_action(page: Page, action: str) -> Locator:
    """Reach a batch action through the actual progressive More menu."""
    selector = {
        'focus': '#batchFocusBtn', 'complete': '#batchCompleteBtn',
        'archive': '#batchArchiveBtn', 'delete': '#batchDeleteBtn',
        'move-project': '#batchMoveProjectBtn',
    }[action]
    return_to_task_workspace(page)
    control = page.locator(selector)
    more = control.locator('xpath=ancestor::details')
    if more.count() and more.get_attribute('open') is None:
        summary = more.locator(':scope > summary')
        summary.scroll_into_view_if_needed()
        page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
        summary.click()
        page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
    expect(control).to_be_visible()
    return control

def click_batch_action(page: Page, action: str) -> None:
    reveal_batch_action(page, action).click()

def reveal_task_action(task: Locator, action: str) -> Locator:
    """Expose a secondary action through its row menu, including negative checks."""
    return_to_task_workspace(task.page)
    expect(task).to_be_visible()
    control = task.locator(f'[data-action={json.dumps(action)}]')
    if control.is_visible():
        return control
    toggle = task.locator('.task-more-toggle')
    if toggle.count() and toggle.is_visible() and toggle.get_attribute('aria-expanded') != 'true':
        toggle.click()
        expect(toggle).to_have_attribute('aria-expanded', 'true')
    return control

def click_task_action(task: Locator, action: str) -> None:
    reveal_task_action(task, action).click()

def assert_task_action_focus_visible(page: Page) -> None:
    target = page.locator('.task-item:focus, .task-item :focus, #openModalBtn:focus')
    expect(target).to_have_count(1)
    expect(target).to_be_visible()
    expect(target).to_be_in_viewport()
    assert not target.evaluate(
        "node => Boolean(node.closest('.task-action-menu, [inert], [hidden], [aria-hidden=\"true\"]'))"
    ), 'A non-modal task action left focus in a menu or hidden region'

def wait_for_app_ready(page: Page) -> None:
    # Read the shell, route and loader in one browser sample. A reload between
    # separate locator calls must not select the archived-app branch for 5.0.
    page.wait_for_function("""() => {
        const visible = element => {
            if (!element) return false;
            const style = getComputedStyle(element);
            const box = element.getBoundingClientRect();
            return box.width > 0 && box.height > 0 && style.visibility !== 'hidden'
                && style.display !== 'none';
        };
        const tasks = document.getElementById('taskList');
        if (!visible(document.getElementById('openModalBtn')) || !tasks
            || tasks.querySelector('.loading-state')) return false;
        if (document.getElementById('workspaceTodayBtn')) {
            return document.getElementById('workspaceSidebar')?.hasAttribute('aria-hidden')
                && ['today','tasks','projects','review','settings'].includes(document.body?.dataset.workspaceScreen);
        }
        return visible(tasks);
    }""", timeout=10_000)

def wait_for_notification(page: Page, pattern: str | re.Pattern[str]) -> None:
    expect(page.locator("#notificationText")).to_have_text(pattern)

def clear_app_data(page: Page, url: str) -> None:
    page.goto(url, wait_until="domcontentloaded")
    wait_for_app_ready(page)
    page.evaluate(
        """async () => {
            localStorage.clear();
            sessionStorage.clear();

            if ('serviceWorker' in navigator) {
                const registrations = await navigator.serviceWorker.getRegistrations();
                await Promise.all(registrations.map((registration) => registration.unregister()));
            }

            if ('caches' in window) {
                const keys = await caches.keys();
                await Promise.all(keys.map((key) => caches.delete(key)));
            }

            await new Promise((resolve, reject) => {
                const request = indexedDB.open('TaskTrackerDB', 2);
                request.onerror = () => reject(request.error);
                request.onsuccess = () => {
                    const db = request.result;
                    const tx = db.transaction(['tasks', 'config'], 'readwrite');
                    const taskStore = tx.objectStore('tasks');
                    const configStore = tx.objectStore('config');

                    taskStore.clear();
                    configStore.clear();
                    configStore.put({ key: 'sampleTasksAdded', value: true });
                    configStore.put({ key: 'language', value: 'zh-CN' });
                    configStore.put({ key: 'notifications_enabled', value: false });

                    tx.oncomplete = () => {
                        db.close();
                        resolve();
                    };
                    tx.onerror = () => reject(tx.error);
                    tx.onabort = () => reject(tx.error);
                };
            });
        }"""
    )
    page.reload(wait_until="domcontentloaded")
    page.wait_for_load_state("load")
    wait_for_app_ready(page)

def assert_empty_task_list(page: Page) -> None:
    return_to_task_workspace(page)
    expect(page.locator(".task-item")).to_have_count(0)
    expect(page.locator("#taskList .empty-state")).to_be_visible()

def assert_accessibility_baseline(page: Page, label: str) -> None:
    issues = page.evaluate(
        """() => {
            const issues = [];
            const normalize = (value) => String(value || '').replace(/\\s+/g, ' ').trim();
            const isHidden = (el) => {
                if (!el || el.closest('template,[hidden],[aria-hidden="true"]')) return true;
                const style = window.getComputedStyle(el);
                if (style.display === 'none' || style.visibility === 'hidden') return true;
                const rect = el.getBoundingClientRect();
                return rect.width === 0 && rect.height === 0 && style.position !== 'fixed';
            };
            const describe = (el) => {
                const bits = [el.tagName.toLowerCase()];
                if (el.id) bits.push(`#${el.id}`);
                if (el.className && typeof el.className === 'string') {
                    bits.push(`.${el.className.trim().split(/\\s+/).join('.')}`);
                }
                if (el.getAttribute('role')) bits.push(`[role="${el.getAttribute('role')}"]`);
                return bits.join('');
            };
            const textByIds = (ids) => normalize(ids.split(/\\s+/).map((id) => document.getElementById(id)?.textContent || '').join(' '));
            const labelText = (el) => {
                if (el.id) {
                    const direct = normalize(Array.from(document.querySelectorAll(`label[for="${CSS.escape(el.id)}"]`)).map((label) => label.textContent).join(' '));
                    if (direct) return direct;
                }
                const wrapping = el.closest('label');
                return wrapping ? normalize(wrapping.textContent) : '';
            };
            const textAllowed = (el) => el.matches('button,a,[role="button"],[role="option"],[role="menuitemradio"],[role="img"]');
            const accessibleName = (el) => {
                const ariaLabel = normalize(el.getAttribute('aria-label'));
                if (ariaLabel) return ariaLabel;
                const labelledby = normalize(el.getAttribute('aria-labelledby'));
                if (labelledby) {
                    const labelledText = textByIds(labelledby);
                    if (labelledText) return labelledText;
                }
                const label = labelText(el);
                if (label) return label;
                return textAllowed(el) ? normalize(el.textContent) : '';
            };

            const controls = Array.from(document.querySelectorAll('button,input,select,textarea,a[href],[role="button"],[role="option"],[role="menuitemradio"],[role="img"]'));
            controls.forEach((el) => {
                if (isHidden(el)) return;
                const type = (el.getAttribute('type') || '').toLowerCase();
                if (type === 'hidden' || type === 'file') return;
                if (!accessibleName(el)) issues.push(`${describe(el)} has no accessible name`);
            });

            document.querySelectorAll('label[for]').forEach((label) => {
                const target = document.getElementById(label.getAttribute('for'));
                if (target && !isHidden(target) && !normalize(label.textContent)) {
                    issues.push(`${describe(label)} labels #${target.id} with empty text`);
                }
            });

            const ids = new Map();
            document.querySelectorAll('[id]').forEach((el) => {
                const id = el.id;
                ids.set(id, (ids.get(id) || 0) + 1);
            });
            ids.forEach((count, id) => {
                if (count > 1) issues.push(`Duplicate id #${id}`);
            });

            const html = document.documentElement;
            if (!normalize(html.lang)) issues.push('documentElement.lang is empty');
            if (!['ltr', 'rtl', 'auto'].includes(normalize(html.dir))) issues.push('documentElement.dir is invalid or empty');

            const taskList = document.getElementById('taskList');
            if (taskList?.hasAttribute('aria-live')) issues.push('#taskList must not be a broad live region');

            document.querySelectorAll('.custom-select').forEach((wrapper) => {
                if (isHidden(wrapper)) return;
                const select = wrapper.querySelector('select');
                const button = wrapper.querySelector('.custom-select-btn');
                const selectedText = normalize(select?.options?.[select.selectedIndex]?.textContent || '');
                const name = accessibleName(button);
                if (selectedText && name && !name.includes(selectedText)) {
                    issues.push(`${describe(button)} accessible name does not include selected value`);
                }
            });
            const projectButton = document.getElementById('projectFilterBtn');
            const currentProject = normalize(document.getElementById('currentProjectLabel')?.textContent || '');
            if (projectButton && currentProject && !accessibleName(projectButton).includes(currentProject)) {
                issues.push('#projectFilterBtn accessible name does not include selected project');
            }

            document.querySelectorAll('[role="listbox"]').forEach((listbox) => {
                if (!listbox.getAttribute('aria-labelledby') && !listbox.getAttribute('aria-label')) {
                    issues.push(`${describe(listbox)} listbox is not labelled`);
                }
                const options = Array.from(listbox.querySelectorAll('[role="option"]'));
                if (!options.length) issues.push(`${describe(listbox)} has no options`);
                options.forEach((option) => {
                    if (!['true', 'false'].includes(option.getAttribute('aria-selected'))) {
                        issues.push(`${describe(option)} option has no aria-selected state`);
                    }
                });
            });

            document.querySelectorAll('[role="menuitemradio"]').forEach((item) => {
                if (!['true', 'false'].includes(item.getAttribute('aria-checked'))) {
                    issues.push(`${describe(item)} menuitemradio has no aria-checked state`);
                }
            });

            document.querySelectorAll('[aria-controls]').forEach((el) => {
                const targetId = el.getAttribute('aria-controls');
                if (targetId && !document.getElementById(targetId)) {
                    issues.push(`${describe(el)} aria-controls points to missing #${targetId}`);
                }
            });

            document.querySelectorAll('[aria-labelledby]').forEach((el) => {
                const labelledby = normalize(el.getAttribute('aria-labelledby'));
                if (labelledby && !textByIds(labelledby)) {
                    issues.push(`${describe(el)} aria-labelledby points to empty text`);
                }
            });

            document.querySelectorAll('[aria-describedby]').forEach((el) => {
                const describedby = normalize(el.getAttribute('aria-describedby'));
                if (describedby && !textByIds(describedby)) {
                    issues.push(`${describe(el)} aria-describedby points to empty text`);
                }
            });

            document.querySelectorAll('[role="tablist"]').forEach((tablist) => {
                const tabs = Array.from(tablist.querySelectorAll('[role="tab"]'));
                const selectedTabs = tabs.filter((tab) => tab.getAttribute('aria-selected') === 'true');
                if (selectedTabs.length !== 1) issues.push(`${describe(tablist)} must have exactly one selected tab`);
                tabs.forEach((tab) => {
                    if (!tab.id) issues.push(`${describe(tab)} tab has no id`);
                    if (!tab.getAttribute('aria-controls')) issues.push(`${describe(tab)} tab has no aria-controls`);
                    if (!['0', '-1'].includes(tab.getAttribute('tabindex'))) issues.push(`${describe(tab)} tab has no roving tabindex`);
                });
            });

            document.querySelectorAll('.drag-handle').forEach((handle) => {
                if (handle.tagName.toLowerCase() !== 'button') issues.push(`${describe(handle)} is not a button`);
                if (!accessibleName(handle)) issues.push(`${describe(handle)} has no reorder label`);
            });

            document.querySelectorAll('svg.icon').forEach((svg) => {
                if (isHidden(svg)) return;
                if (svg.getAttribute('role') === 'img') return;
                if (svg.getAttribute('aria-hidden') !== 'true' || svg.getAttribute('focusable') !== 'false') {
                    issues.push(`${describe(svg)} decorative icon is not aria-hidden`);
                }
            });

            const visibleDialog = Array.from(document.querySelectorAll('[role="dialog"]')).find((dialog) => !isHidden(dialog));
            if (visibleDialog) {
                const blockingEditorLayer = ['draftDiscardPrompt', 'taskDraftSavingStatus'].some(id => {
                    const layer = document.getElementById(id);
                    return layer && !isHidden(layer);
                });
                const contextual = visibleDialog.id === 'taskModal' && visibleDialog.dataset.dialogMode === 'editor'
                    && visibleDialog.dataset.layout === 'floating' && !blockingEditorLayer;
                const expectedModal = contextual ? 'false' : 'true';
                if (visibleDialog.getAttribute('aria-modal') !== expectedModal) {
                    issues.push(`visible dialog must set aria-modal=${expectedModal} for its actual interaction mode`);
                }
                if (contextual && (document.querySelector('.container')?.inert || document.querySelector('.workspace-stage')?.inert)) {
                    issues.push('contextual task editor leaves its background workspace inert');
                }
                const titleId = visibleDialog.getAttribute('aria-labelledby');
                if (!titleId || !normalize(document.getElementById(titleId)?.textContent)) {
                    issues.push('visible dialog must be labelled by visible title text');
                }
                const describedBy = visibleDialog.getAttribute('aria-describedby');
                if (describedBy && !normalize(document.getElementById(describedBy)?.textContent)) {
                    issues.push('visible dialog aria-describedby points to empty text');
                }
            }

            return issues;
        }"""
    )
    if issues:
        joined = "\n".join(f"- {issue}" for issue in issues)
        raise AssertionError(f"Accessibility baseline failed during {label}:\n{joined}")

def discard_task_draft(page: Page) -> None:
    expect(page.locator('#taskModal')).to_be_visible()
    expect(page.locator('#draftDiscardPrompt')).to_be_visible()
    page.locator('#draftDiscardBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()

def add_task(
    page: Page,
    task_name: str,
    description: str = "Created by Playwright smoke test.",
    no_deadline: bool = False,
    due_date: str | None = None,
    due_time: str | None = None,
    reminder_offset: str | None = None,
    repeat_type: str | None = None,
    repeat_interval: str | None = None,
    repeat_weekdays: list[str] | None = None,
    repeat_paused: bool = False,
    project: str | None = None,
    tags: list[str] | None = None,
    subtasks: list[str] | None = None,
) -> None:
    return_to_task_workspace(page)
    open_task_editor(page)
    expect(page.locator("#taskModal")).to_be_visible()
    page.locator("#taskName").fill(task_name)
    page.locator("#taskDesc").fill(description)
    if project:
        reveal_task_field(page, "#taskProject").fill(project)
    if tags:
        reveal_task_field(page, "#taskTags").fill(", ".join(tags))

    if no_deadline:
        reveal_task_field(page, "#noDeadline").check()
        expect(page.locator("#dueDate")).to_be_disabled()
        expect(page.locator("#dueTime")).to_be_disabled()
        expect(page.locator("#reminderOffset")).to_be_disabled()
        expect(page.locator("#reminderRepeat")).to_be_disabled()
        expect(page.locator("#repeatType")).to_be_disabled()
    else:
        reveal_task_field(page, '#noDeadline').uncheck()
        if due_date:
            reveal_task_field(page, "#dueDate").fill(due_date)
        if due_time:
            reveal_task_field(page, "#dueTime").fill(due_time)
        if reminder_offset is not None:
            reveal_task_field(page, "#reminderOffset").select_option(reminder_offset)
            if reminder_offset == "-1":
                expect(page.locator("#reminderRepeat")).to_be_disabled()
            else:
                expect(page.locator("#reminderRepeat")).to_be_enabled()
        if repeat_type:
            reveal_task_field(page, "#repeatType").select_option(repeat_type)
            if repeat_type == "custom":
                expect(page.locator("#repeatCustomRow")).to_be_visible()
                reveal_task_field(page, "#repeatInterval").fill(repeat_interval or "1")
            if repeat_type == "weekly-days":
                expect(page.locator("#repeatWeekdaysRow")).to_be_visible()
                if repeat_weekdays:
                    for value in ("0", "1", "2", "3", "4", "5", "6"):
                        page.locator(f"#repeatWeekday{value}").uncheck()
                    for value in repeat_weekdays:
                        page.locator(f"#repeatWeekday{value}").check()
            if repeat_paused:
                expect(page.locator("#repeatPauseRow")).to_be_visible()
                reveal_task_field(page, "#repeatPaused").check()

    for index, subtask in enumerate(subtasks or [], start=1):
        reveal_task_field(page, '#subtaskInput').fill(subtask)
        page.locator("#addSubtaskBtn").click()
        expect(page.locator("#subtaskListPreview .subtask-preview-item")).to_have_count(index)

    page.locator("#submitBtn").click()

    task = task_locator(page, task_name)
    expect(task).to_have_count(1)
    expect(task.first.locator(".task-name")).to_contain_text(task_name)

def snooze_task_reminder(page: Page, task_name: str) -> None:
    task = task_locator(page, task_name)
    expect(reveal_task_action(task, 'snooze')).to_be_visible()
    click_task_action(task, 'snooze')
    wait_for_notification(page, re.compile("提醒|snoozed", re.I))
    assert_task_action_focus_visible(page)
    snoozed_until = page.evaluate(
        """async (taskName) => {
            const request = indexedDB.open('TaskTrackerDB', 2);
            return await new Promise((resolve, reject) => {
                request.onerror = () => reject(request.error);
                request.onsuccess = () => {
                    const db = request.result;
                    const tx = db.transaction(['tasks'], 'readonly');
                    const getAll = tx.objectStore('tasks').getAll();
                    getAll.onsuccess = () => {
                        const task = getAll.result.find((item) => item.name === taskName);
                        db.close();
                        resolve(task ? task.snoozedUntil : null);
                    };
                    getAll.onerror = () => reject(getAll.error);
                };
            });
        }""",
        task_name,
    )
    if not snoozed_until:
        raise AssertionError("Task reminder was not snoozed")

def get_task_records(page: Page) -> list[dict[str, Any]]:
    return page.evaluate(
        """async () => {
            return await new Promise((resolve, reject) => {
                const request = indexedDB.open('TaskTrackerDB', 2);
                request.onerror = () => reject(request.error);
                request.onsuccess = () => {
                    const db = request.result;
                    const tx = db.transaction(['tasks'], 'readonly');
                    const getAll = tx.objectStore('tasks').getAll();
                    getAll.onsuccess = () => {
                        db.close();
                        resolve(getAll.result);
                    };
                    getAll.onerror = () => reject(getAll.error);
                };
            });
        }"""
    )

def delete_task(page: Page, task_name: str) -> None:
    task = task_locator(page, task_name)
    click_task_action(task.first, 'delete')
    expect(page.locator("#taskModal")).to_be_visible()
    assert_accessibility_baseline(page, "delete confirmation")
    page.locator("#submitBtn").click()
    expect(task).to_have_count(0)

def close_mobile_filters(page: Page) -> None:
    dialog = page.locator('#mobileFiltersDialog')
    if dialog.count() and dialog.is_visible():
        page.locator('#mobileFiltersDoneBtn').click()
        expect(dialog).to_be_hidden()

def reveal_filters(page: Page) -> None:
    content = page.locator('#toolsDrawerContent')
    if content.count() and not content.is_visible():
        page.locator('#toolsDrawerToggleBtn').click()
        expect(content).to_be_visible()

def select_filter(page: Page, value: str) -> None:
    ensure_task_control_workspace(page)
    reveal_filters(page)
    filter_btn = page.locator("#filterBtn")
    selected_option = page.locator(f'#filterDropdown .dropdown-option[data-filter="{value}"]')
    expect(filter_btn).to_have_attribute("aria-controls", "filterMenu")
    filter_btn.click()
    selected_option.click()
    expect(filter_btn).to_have_attribute("aria-expanded", "false")
    expect(filter_btn).to_be_focused()
    expect(selected_option).to_have_attribute("aria-selected", "true")
    expect(selected_option).to_have_class(
        re.compile(r"(^|\s)selected(\s|$)")
    )
    close_mobile_filters(page)

def select_project(page: Page, value: str) -> None:
    ensure_task_control_workspace(page)
    reveal_filters(page)
    project_btn = page.locator("#projectFilterBtn")
    scope = {'kind': 'all'} if value == 'all' else {'kind': 'unassigned'} if value == '__none__' else {'kind': 'project', 'name': value}
    encoded = json.dumps(scope, ensure_ascii=False, separators=(',', ':'))
    selected_option = page.locator(f'#projectDropdown .dropdown-option[data-project={json.dumps(encoded, ensure_ascii=False)}]')
    expect(project_btn).to_have_attribute("aria-controls", "projectFilterMenu")
    project_btn.click()
    selected_option.click()
    expect(project_btn).to_have_attribute("aria-expanded", "false")
    expect(project_btn).to_be_focused()
    expect(selected_option).to_have_attribute("aria-selected", "true")
    expect(selected_option).to_have_class(
        re.compile(r"(^|\s)selected(\s|$)")
    )
    selected_text = selected_option.locator("span").first.text_content() or ""
    expect(project_btn).to_have_attribute("aria-label", re.compile(re.escape(selected_text.strip())))
    close_mobile_filters(page)

def select_sort(page: Page, value: str) -> None:
    """Sort the task library, returning to Review when that was the origin."""
    origin_screen = workbench_screen(page)
    return_to_task_workspace(page)
    previous_view = page.locator('body').get_attribute('data-task-view')
    restore_view = previous_view in ('calendar', 'timeline', 'stats') and page.locator('#sortDropdown').is_hidden()
    if restore_view:
        select_view(page, 'list')
    reveal_filters(page)
    sort_btn = page.locator("#sortBtn")
    selected_option = page.locator(f'#sortDropdown .dropdown-option[data-sort="{value}"]')
    expect(sort_btn).to_have_attribute("aria-controls", "sortMenu")
    sort_btn.click()
    selected_option.click()
    expect(sort_btn).to_have_attribute("aria-expanded", "false")
    expect(sort_btn).to_be_focused()
    expect(selected_option).to_have_attribute("aria-selected", "true")
    expect(selected_option).to_have_class(
        re.compile(r"(^|\s)selected(\s|$)")
    )
    close_mobile_filters(page)
    if restore_view:
        select_view(page, previous_view)
    if origin_screen == 'review':
        navigate_workbench(page, 'review')

def select_view(page: Page, value: str) -> None:
    if is_workbench_v5(page) and value == 'stats':
        navigate_workbench(page, 'review')
        mobile = page.locator('#mobileReviewBtn')
        current = mobile if mobile.is_visible() else page.locator('#viewTab-stats')
        expect(current).to_have_attribute('aria-current', 'page')
        expect(page.locator('.stats-view')).to_be_visible()
        return
    return_to_task_workspace(page)
    tab = page.locator(f'#viewSwitcher .view-tab[data-view="{value}"]')
    tab.click()
    if page.locator('#settingsWorkspace').count():
        expect(tab).to_have_attribute("aria-current", "page")
    else:
        expect(tab).to_have_attribute("aria-selected", "true")
    expect(tab).to_have_class(re.compile(r"(^|\s)selected(\s|$)"))

def visible_task_names(page: Page) -> list[str]:
    return page.locator(".task-item .task-name").all_text_contents()

def calendar_month_title(page: Page, year: int, month_index: int) -> str:
    return page.evaluate(
        """([year, monthIndex]) => new Intl.DateTimeFormat(
            document.documentElement.lang || 'zh-CN',
            { year: 'numeric', month: 'long' }
        ).format(new Date(year, monthIndex, 1))""",
        [year, month_index],
    )

def edit_task(page: Page, task_name: str, updated_name: str) -> None:
    task = task_locator(page, task_name)
    click_task_action(task.first, 'edit')
    expect(page.locator("#taskModal")).to_be_visible()
    page.locator("#taskName").fill(updated_name)
    page.locator("#taskDesc").fill("Updated by Playwright smoke test.")
    page.locator("#submitBtn").click()
    expect(task_locator(page, updated_name)).to_have_count(1)
    expect(task_locator(page, task_name)).to_have_count(0)

def assert_theme_chrome(page: Page) -> dict[str, Any]:
    expected = page.evaluate("""() => {
        const root = document.documentElement;
        return getComputedStyle(root).getPropertyValue('--chrome-solid').trim()
            || (root.getAttribute('data-theme') === 'dark' ? '#151925' : '#f4f5f9');
    }""")
    expect(page.locator('meta[name="theme-color"]')).to_have_attribute('content', expected)
    chrome = page.evaluate("""() => {
        const meta = document.querySelector('meta[name="theme-color"]')?.content || '';
        const canvas = document.createElement('canvas');
        canvas.width = canvas.height = 1;
        const context = canvas.getContext('2d');
        const pixel = value => {
            context.clearRect(0, 0, 1, 1);
            context.fillStyle = value;
            context.fillRect(0, 0, 1, 1);
            return Array.from(context.getImageData(0, 0, 1, 1).data);
        };
        const root = document.documentElement;
        const solid = getComputedStyle(root).getPropertyValue('--chrome-solid').trim();
        const background = solid || (root.getAttribute('data-theme') === 'dark' ? '#151925' : '#f4f5f9');
        return {meta, metaColor: pixel(meta), background, chromeColor: pixel(background),
            metaValid: CSS.supports('color', meta), chromeValid: CSS.supports('color', background),
            usedLegacyFallback: !solid,
            manifestPath: new URL(document.querySelector('#manifestLink').href).pathname};
    }""")
    assert chrome['meta'] and chrome['metaValid'] and chrome['chromeValid'] and chrome['metaColor'][3] == 255, chrome
    assert chrome['chromeColor'][3] == 255 and chrome['metaColor'] == chrome['chromeColor'], chrome
    assert chrome['manifestPath'].endswith('/manifest.json'), chrome
    return chrome

def complete_task(page: Page, task_name: str) -> None:
    return_to_task_workspace(page)
    active_task = task_locator(page, task_name).first
    expect(active_task.locator('[data-action="toggle"]')).to_have_attribute('aria-pressed', 'false')
    expect(active_task.locator('[data-action="toggle"]')).to_have_attribute(
        "aria-label", re.compile("标记为已完成|Mark as complete", re.I)
    )
    expect(active_task.locator('[data-action="toggle"] use')).to_have_attribute("href", "#icon-check")

    active_task.locator('[data-action="toggle"]').click()
    select_filter(page, "completed")
    task = task_locator(page, task_name)
    expect(task).to_have_count(1)
    expect(task.locator('[data-action="toggle"]')).to_have_attribute(
        "aria-label", re.compile("标记为未完成|Mark as incomplete", re.I)
    )
    expect(task.locator('[data-action="toggle"]')).to_have_attribute('aria-pressed', 'true')
    expect(task.locator('[data-action="toggle"] use')).to_have_attribute("href", "#icon-check")
    decoration = task.locator(".task-name").evaluate(
        "element => getComputedStyle(element).textDecorationLine"
    )
    if "line-through" not in decoration:
        raise AssertionError(f"Completed task name is not struck through: {decoration}")
    select_filter(page, "no-deadline")
    expect(task_locator(page, task_name)).to_have_count(1)
    expect(page.locator("#count-no-deadline")).to_have_text("(1)")
    select_filter(page, "completed")

def assert_backup_payload_integrity(payload: dict[str, Any], expected_type: str) -> None:
    if payload.get("type") != expected_type or not payload.get("exportId"):
        raise AssertionError(f"Backup payload identity is incomplete: {payload}")
    checksum = payload.get("checksum")
    if not isinstance(checksum, str) or not re.fullmatch(r"fnv1a32:[0-9a-f]{8}", checksum):
        raise AssertionError(f"Backup payload checksum is missing or malformed: {payload}")
    clone = dict(payload)
    clone.pop("checksum", None)
    expected = f"fnv1a32:{stable_fnv1a32(stable_json(clone))}"
    if checksum != expected:
        raise AssertionError(f"Backup payload checksum mismatch: {checksum} != {expected}")

def stable_json(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, list):
        return "[" + ",".join(stable_json(item) for item in value) + "]"
    if isinstance(value, dict):
        return "{" + ",".join(
            json.dumps(key, ensure_ascii=False, separators=(",", ":")) + ":" + stable_json(value[key])
            for key in sorted(value)
        ) + "}"
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

def stable_fnv1a32(text: str) -> str:
    value = 2166136261
    # JavaScript charCodeAt hashes UTF-16 code units, including surrogate pairs.
    encoded = text.encode("utf-16-le", errors="surrogatepass")
    for index in range(0, len(encoded), 2):
        value ^= encoded[index] | (encoded[index + 1] << 8)
        value = (value * 16777619) & 0xFFFFFFFF
    return f"{value:08x}"

def import_payload_replace(page: Page, payload: list[dict[str, Any]]) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as temp_file:
        json.dump(payload, temp_file)
        temp_path = temp_file.name

    try:
        open_settings(page)
        with page.expect_file_chooser() as chooser_info:
            page.locator("#importBtn").click()
        chooser_info.value.set_files(temp_path)
        expect(page.locator("#taskModal")).to_be_visible()
        expects_snapshot = len(get_task_records(page)) > 0
        if expects_snapshot:
            with page.expect_download() as snapshot_info:
                page.locator("#submitBtn").click()
            snapshot_path = snapshot_info.value.path()
            if not snapshot_path:
                raise AssertionError("Replace import did not download a pre-import snapshot")
            snapshot = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
            assert_backup_payload_integrity(snapshot, "pre-import-backup")
            expect(page.locator("#taskModal")).to_be_visible()
            page.locator("#submitBtn").click()
        else:
            page.locator("#submitBtn").click()
        wait_for_notification(page, re.compile("导入|import", re.I))
        select_filter(page, "all")
    finally:
        Path(temp_path).unlink(missing_ok=True)

def assert_pwa_resources(context: BrowserContext, base_url: str) -> None:
    required_paths = ["index.html", "manifest.json", "sw.js", "robots.txt", "sitemap.xml", "resources/en.json", "resources/zh-CN.json"]
    responses = []
    for path in required_paths:
        response = context.request.get(urljoin(base_url, path))
        responses.append(f"{response.status} {path}")
        if not response.ok:
            raise AssertionError(f"PWA resource failed: {response.status} {path}")

    manifest_response = context.request.get(urljoin(base_url, "manifest.json"))
    manifest = manifest_response.json()
    for icon in manifest.get("icons", []):
        src = icon.get("src")
        if not src:
            raise AssertionError(f"Manifest icon is missing src: {icon}")
        response = context.request.get(urljoin(base_url, src))
        responses.append(f"{response.status} {src}")
        if not response.ok:
            raise AssertionError(f"Manifest icon failed: {response.status} {src}")
    for screenshot in manifest.get("screenshots", []):
        src = screenshot.get("src")
        if not src:
            raise AssertionError(f"Manifest screenshot is missing src: {screenshot}")
        response = context.request.get(urljoin(base_url, src))
        responses.append(f"{response.status} {src}")
        if not response.ok:
            raise AssertionError(f"Manifest screenshot failed: {response.status} {src}")

def assert_service_worker_and_offline_load(context: BrowserContext, page: Page) -> None:
    page.wait_for_load_state("load")
    worker_state = page.evaluate(
        """async (expectedCacheName) => {
            if (!('serviceWorker' in navigator)) return { supported: false };

            const registration = await Promise.race([
                navigator.serviceWorker.ready,
                new Promise((_, reject) => setTimeout(() => reject(new Error('service worker timeout')), 10000))
            ]);
            const keys = 'caches' in window ? await caches.keys() : [];
            return {
                supported: true,
                hasRegistration: Boolean(registration),
                cacheNames: keys,
                hasExpectedCache: keys.includes(expectedCacheName)
            };
        }""",
        SW_CACHE_NAME,
    )

    if not worker_state.get("supported"):
        raise AssertionError("Service worker is not supported in this browser context")
    if not worker_state.get("hasRegistration") or not worker_state.get("hasExpectedCache"):
        raise AssertionError(f"Service worker did not prepare the expected cache: {worker_state}")

    page.reload(wait_until="load")
    wait_for_app_ready(page)
    if not page.evaluate("Boolean(navigator.serviceWorker && navigator.serviceWorker.controller)"):
        page.reload(wait_until="load")
        wait_for_app_ready(page)

    context.set_offline(True)
    try:
        page.reload(wait_until="domcontentloaded")
        wait_for_app_ready(page)
    finally:
        context.set_offline(False)
