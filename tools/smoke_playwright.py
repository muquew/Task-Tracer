#!/usr/bin/env python3
"""Browser smoke test for the Task Tracer single-file PWA.

Run with:
    conda run -n task python tools/smoke_playwright.py

Set TASK_TRACER_URL to test an already-running server. Without it, this script
starts a temporary static server from the repository root.
"""

from __future__ import annotations

import contextlib
from datetime import datetime, timedelta, timezone
import http.server
import json
import os
import re
import socket
import socketserver
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urljoin, urlparse

from playwright.sync_api import BrowserContext, Page, Request, TimeoutError, expect, sync_playwright


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HOST = "127.0.0.1"


def read_service_worker_cache_name() -> str:
    service_worker = (REPO_ROOT / "sw.js").read_text(encoding="utf-8")
    match = re.search(r"const CACHE_NAME = ['\"]([^'\"]+)['\"]", service_worker)
    if not match:
        raise AssertionError("Could not read service worker cache name")
    return match.group(1)


SW_CACHE_NAME = read_service_worker_cache_name()


class StaticHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

    def log_message(self, format: str, *args: object) -> None:
        return


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def reserve_port() -> int:
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind((DEFAULT_HOST, 0))
        return int(sock.getsockname()[1])


@contextlib.contextmanager
def local_server() -> Iterator[str]:
    port = reserve_port()
    server = ThreadingHTTPServer((DEFAULT_HOST, port), StaticHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        yield f"http://{DEFAULT_HOST}:{port}/"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def ensure_conda_library_path() -> None:
    prefix = os.environ.get("CONDA_PREFIX")
    if not prefix:
        return

    lib_path = str(Path(prefix) / "lib")
    current = os.environ.get("LD_LIBRARY_PATH", "")
    paths = [path for path in current.split(":") if path]
    if lib_path not in paths:
        os.environ["LD_LIBRARY_PATH"] = ":".join([lib_path, *paths])


def assert_no_page_errors(errors: list[str]) -> None:
    if errors:
        joined = "\n".join(f"- {error}" for error in errors)
        raise AssertionError(f"Browser page errors were raised:\n{joined}")


def is_ignored_resource(url: str) -> bool:
    path = urlparse(url).path
    return path.startswith("/_vercel/") or path == "/favicon.ico"


def describe_request_failure(request: Request) -> str:
    failure = request.failure
    if isinstance(failure, str):
        error_text = failure
    elif isinstance(failure, dict):
        error_text = str(failure.get("errorText", "unknown"))
    else:
        error_text = "unknown"

    return f"{error_text} {request.url}"


def get_origin(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


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


def wait_for_class(page: Page, selector: str, class_name: str, present: bool = True) -> None:
    page.wait_for_function(
        """({ selector, className, present }) => {
            const el = document.querySelector(selector);
            return Boolean(el) && el.classList.contains(className) === present;
        }""",
        arg={"selector": selector, "className": class_name, "present": present},
    )


def task_locator(page: Page, task_name: str):
    exact_name = page.locator(".task-name").filter(
        has_text=re.compile(f"^{re.escape(task_name)}$")
    )
    return page.locator(".task-item").filter(has=exact_name)


def wait_for_app_ready(page: Page) -> None:
    expect(page.locator("#openModalBtn")).to_be_visible()
    page.locator("#taskList .loading-state").wait_for(state="detached", timeout=10_000)
    page.locator("#taskList").wait_for(state="visible")


def wait_for_notification(page: Page, pattern: str | re.Pattern[str]) -> None:
    expect(page.locator("#notificationText")).to_have_text(pattern)


def press_control_shortcut(page: Page, key: str) -> None:
    page.keyboard.down("Control")
    page.keyboard.press(key)
    page.keyboard.up("Control")


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
                if (visibleDialog.getAttribute('aria-modal') !== 'true') issues.push('visible dialog must set aria-modal=true');
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


def exercise_shortcuts_and_modal_closing(page: Page) -> None:
    page.locator("body").click(position={"x": 10, "y": 10})
    press_control_shortcut(page, "k")
    expect(page.locator("#searchInput")).to_be_focused()
    page.locator("#searchInput").fill("temporary query")
    expect(page.locator("#clearSearchBtn")).to_be_visible()
    page.keyboard.press("Escape")
    expect(page.locator("#searchInput")).to_have_value("")
    expect(page.locator("#clearSearchBtn")).to_be_hidden()
    page.keyboard.press("Escape")

    press_control_shortcut(page, "i")
    expect(page.locator("#taskModal")).to_be_visible()
    page.keyboard.press("Escape")
    expect(page.locator("#taskModal")).to_be_hidden()

    page.locator("#openModalBtn").click()
    expect(page.locator("#taskModal")).to_be_visible()
    assert_accessibility_baseline(page, "new-task modal")
    exercise_modal_focus_trap(page)
    page.locator("#cancelBtn").click()
    expect(page.locator("#taskModal")).to_be_hidden()

    page.locator("#openModalBtn").click()
    expect(page.locator("#taskModal")).to_be_visible()
    page.locator("#closeModalBtn").click()
    expect(page.locator("#taskModal")).to_be_hidden()

    page.locator("#openModalBtn").click()
    expect(page.locator("#taskModal")).to_be_visible()
    page.locator("#taskModal").click(position={"x": 5, "y": 5})
    expect(page.locator("#taskModal")).to_be_hidden()

    press_control_shortcut(page, "m")
    wait_for_class(page, "#menu", "show")
    page.keyboard.press("Escape")
    wait_for_class(page, "#menu", "show", present=False)


def exercise_keyboard_navigation_patterns(page: Page) -> None:
    page.locator("#viewTab-list").focus()
    page.keyboard.press("ArrowRight")
    expect(page.locator("#viewTab-calendar")).to_be_focused()
    expect(page.locator("#viewTab-calendar")).to_have_attribute("aria-selected", "true")
    expect(page.locator("#taskList")).to_have_attribute("aria-labelledby", "viewTab-calendar")
    page.keyboard.press("End")
    expect(page.locator("#viewTab-stats")).to_be_focused()
    expect(page.locator("#viewTab-stats")).to_have_attribute("aria-selected", "true")
    page.keyboard.press("Home")
    expect(page.locator("#viewTab-list")).to_be_focused()
    expect(page.locator("#viewTab-list")).to_have_attribute("aria-selected", "true")

    page.locator("#sortBtn").focus()
    page.keyboard.press("ArrowDown")
    wait_for_class(page, "#sortDropdown", "show")
    expect(page.locator('#sortDropdown .dropdown-option[data-sort="smart"]')).to_be_focused()
    page.keyboard.press("ArrowDown")
    expect(page.locator('#sortDropdown .dropdown-option[data-sort="created-desc"]')).to_be_focused()
    page.keyboard.press("Enter")
    expect(page.locator("#sortBtn")).to_be_focused()
    expect(page.locator("#sortBtn")).to_have_attribute("aria-expanded", "false")
    expect(page.locator('#sortDropdown .dropdown-option[data-sort="created-desc"]')).to_have_attribute("aria-selected", "true")

    page.locator("#filterBtn").focus()
    page.keyboard.press("ArrowDown")
    wait_for_class(page, "#filterDropdown", "show")
    page.keyboard.press("Escape")
    expect(page.locator("#filterBtn")).to_be_focused()
    expect(page.locator("#filterBtn")).to_have_attribute("aria-expanded", "false")

    page.locator("#openMenuBtn").focus()
    page.keyboard.press("Enter")
    wait_for_class(page, "#menu", "show")
    expect(page.locator("#exportBtn")).to_be_focused()
    page.keyboard.press("ArrowDown")
    expect(page.locator("#backupBtn")).to_be_focused()
    page.keyboard.press("End")
    expect(page.locator("#langMenuToggle")).to_be_focused()
    page.keyboard.press("ArrowRight")
    expect(page.locator('#lang-container .lang-btn[data-lang="zh-CN"]')).to_be_focused()
    page.keyboard.press("ArrowLeft")
    expect(page.locator("#langMenuToggle")).to_be_focused()
    page.keyboard.press("Escape")
    wait_for_class(page, "#menu", "show", present=False)
    expect(page.locator("#openMenuBtn")).to_be_focused()
    select_sort(page, "smart")


def exercise_modal_focus_trap(page: Page) -> None:
    expect(page.locator("#taskName")).to_be_focused()
    page.keyboard.press("Shift+Tab")
    expect(page.locator("#closeModalBtn")).to_be_focused()
    page.keyboard.press("Tab")
    expect(page.locator("#taskName")).to_be_focused()

    page.locator("#submitBtn").focus()
    page.keyboard.press("Tab")
    expect(page.locator("#closeModalBtn")).to_be_focused()

    page.locator("#taskName").focus()
    press_control_shortcut(page, "k")
    expect(page.locator("#taskName")).to_be_focused()
    page.locator("#taskName").fill("Shortcut selection source")
    press_control_shortcut(page, "a")
    page.keyboard.type("Shortcut selection target")
    expect(page.locator("#taskName")).to_have_value("Shortcut selection target")


def exercise_task_name_validation(page: Page) -> None:
    page.locator("#openModalBtn").click()
    expect(page.locator("#taskModal")).to_be_visible()
    page.locator("#taskName").fill("   ")
    page.locator("#submitBtn").click()
    wait_for_notification(page, re.compile("请输入任务名称|enter a task name", re.I))
    expect(page.locator("#taskModal")).to_be_visible()
    expect(page.locator("#taskName")).to_be_focused()
    expect(page.locator(".task-item")).to_have_count(0)
    page.locator("#cancelBtn").click()
    expect(page.locator("#taskModal")).to_be_hidden()


def exercise_empty_state_actions(page: Page) -> None:
    page.locator("#openMenuBtn").click()
    page.locator("#clearCompletedBtn").click()
    wait_for_notification(page, re.compile("没有已完成的任务可清除|no completed tasks", re.I))
    page.keyboard.press("Escape")


def exercise_search_empty_state(page: Page, query: str) -> None:
    page.locator("#searchInput").fill(query)
    page.wait_for_timeout(350)
    expect(page.locator("#taskList .empty-state")).to_be_visible()
    expect(page.locator(".task-item")).to_have_count(0)
    clear_search(page)


def exercise_subtask_draft_editor(page: Page) -> None:
    page.locator("#openModalBtn").click()
    expect(page.locator("#taskModal")).to_be_visible()
    page.locator("#subtaskInput").fill("Draft subtask")
    page.locator("#addSubtaskBtn").click()
    page.locator("#subtaskInput").fill("Subtask to delete")
    page.locator("#addSubtaskBtn").click()
    expect(page.locator("#subtaskListPreview .subtask-preview-item")).to_have_count(2)
    assert_accessibility_baseline(page, "subtask draft editor")

    page.locator("#subtaskListPreview .subtask-preview-text").first.focus()
    page.keyboard.press("Enter")
    page.locator("#subtaskListPreview .subtask-edit-input").fill("Edited draft subtask")
    page.keyboard.press("Enter")
    expect(page.locator("#subtaskListPreview .subtask-preview-text").first).to_have_text("Edited draft subtask")

    page.locator("#subtaskListPreview .subtask-delete-btn").last.click()
    expect(page.locator("#subtaskListPreview .subtask-preview-item")).to_have_count(1)
    page.locator("#cancelBtn").click()
    expect(page.locator("#taskModal")).to_be_hidden()


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
    project: str | None = None,
    tags: list[str] | None = None,
    subtasks: list[str] | None = None,
) -> None:
    page.locator("#openModalBtn").click()
    expect(page.locator("#taskModal")).to_be_visible()
    page.locator("#taskName").fill(task_name)
    page.locator("#taskDesc").fill(description)
    if project:
        page.locator("#taskProject").fill(project)
    if tags:
        page.locator("#taskTags").fill(", ".join(tags))

    if no_deadline:
        page.locator("#noDeadline").check()
        expect(page.locator("#dueDate")).to_be_disabled()
        expect(page.locator("#dueTime")).to_be_disabled()
        expect(page.locator("#reminderOffset")).to_be_disabled()
        expect(page.locator("#reminderRepeat")).to_be_disabled()
        expect(page.locator("#repeatType")).to_be_disabled()
    else:
        if due_date:
            page.locator("#dueDate").fill(due_date)
        if due_time:
            page.locator("#dueTime").fill(due_time)
        if reminder_offset is not None:
            page.locator("#reminderOffset").select_option(reminder_offset)
            if reminder_offset == "-1":
                expect(page.locator("#reminderRepeat")).to_be_disabled()
            else:
                expect(page.locator("#reminderRepeat")).to_be_enabled()
        if repeat_type:
            page.locator("#repeatType").select_option(repeat_type)
            if repeat_type == "custom":
                expect(page.locator("#repeatCustomRow")).to_be_visible()
                page.locator("#repeatInterval").fill(repeat_interval or "1")

    for index, subtask in enumerate(subtasks or [], start=1):
        page.locator("#subtaskInput").fill(subtask)
        page.locator("#addSubtaskBtn").click()
        expect(page.locator("#subtaskListPreview .subtask-preview-item")).to_have_count(index)

    page.locator("#submitBtn").click()

    task = task_locator(page, task_name)
    expect(task).to_have_count(1)
    expect(task.first.locator(".task-name")).to_contain_text(task_name)


def exercise_quick_add(page: Page, task_name: str) -> None:
    page.locator("#quickAddInput").fill(f"tomorrow 20:00 {task_name} #quick /SmokeQuick")
    page.locator("#quickAddInput").press("Enter")
    expect(task_locator(page, task_name)).to_have_count(1)
    record = page.evaluate(
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
                        resolve(task || null);
                    };
                    getAll.onerror = () => reject(getAll.error);
                };
            });
        }""",
        task_name,
    )
    if not record:
        raise AssertionError("Quick add did not create a task record")
    if record["project"] != "SmokeQuick" or "quick" not in record["tags"]:
        raise AssertionError(f"Quick add did not parse project/tags: {record}")
    if record["dueLocalTime"] != "20:00" or not record["dueLocalDate"]:
        raise AssertionError(f"Quick add did not parse due date/time: {record}")
    delete_task_records_by_name(page, task_name)


def exercise_project_tags(page: Page, alpha_name: str, beta_name: str) -> None:
    alpha = task_locator(page, alpha_name)
    expect(alpha.locator(".project-chip")).to_contain_text("Smoke Work")
    expect(alpha.locator(".tag-chip").first).to_contain_text("#focus")
    page.locator("#searchInput").fill("focus")
    expect(task_locator(page, alpha_name)).to_have_count(1)
    expect(task_locator(page, beta_name)).to_have_count(0)
    clear_search(page)
    page.locator("#searchInput").fill("  Smoke Work focus  ")
    expect(task_locator(page, alpha_name)).to_have_count(1)
    expect(task_locator(page, beta_name)).to_have_count(0)
    clear_search(page)
    page.locator("#searchInput").fill("tag:focus")
    expect(task_locator(page, alpha_name)).to_have_count(1)
    expect(task_locator(page, beta_name)).to_have_count(0)
    clear_search(page)
    page.locator("#searchInput").fill("#docs project:work")
    expect(task_locator(page, alpha_name)).to_have_count(1)
    expect(task_locator(page, beta_name)).to_have_count(0)
    clear_search(page)
    page.locator("#searchInput").fill("due:tomorrow")
    expect(task_locator(page, alpha_name)).to_have_count(0)
    expect(task_locator(page, beta_name)).to_have_count(1)
    clear_search(page)
    select_project(page, "Smoke Work")
    expect(task_locator(page, alpha_name)).to_have_count(1)
    expect(task_locator(page, beta_name)).to_have_count(0)
    select_project(page, "all")


def snooze_task_reminder(page: Page, task_name: str) -> None:
    task = task_locator(page, task_name)
    expect(task.locator('[data-action="snooze"]')).to_be_visible()
    task.locator('[data-action="snooze"]').click()
    wait_for_notification(page, re.compile("提醒|snoozed", re.I))
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


def search_task(page: Page, task_name: str) -> None:
    page.locator("#searchInput").fill(task_name)
    expect(task_locator(page, task_name)).to_have_count(1)


def clear_search(page: Page) -> None:
    if page.locator("#clearSearchBtn").is_visible():
        page.locator("#clearSearchBtn").click()
    else:
        page.locator("#searchInput").fill("")
    page.wait_for_timeout(350)


def put_task_record(page: Page, task: dict[str, Any]) -> None:
    page.evaluate(
        """async (task) => {
            await new Promise((resolve, reject) => {
                const request = indexedDB.open('TaskTrackerDB', 2);
                request.onerror = () => reject(request.error);
                request.onsuccess = () => {
                    const db = request.result;
                    const tx = db.transaction(['tasks'], 'readwrite');
                    tx.objectStore('tasks').put(task);
                    tx.oncomplete = () => {
                        db.close();
                        resolve();
                    };
                    tx.onerror = () => reject(tx.error);
                    tx.onabort = () => reject(tx.error);
                };
            });
        }""",
        task,
    )
    page.reload(wait_until="domcontentloaded")
    wait_for_app_ready(page)


def add_overdue_task_record(page: Page, task_name: str, order: int) -> None:
    now_ms = int(time.time() * 1000)
    put_task_record(
        page,
        {
            "id": now_ms + order,
            "name": task_name,
            "description": "Created directly to cover overdue state.",
            **due_fields_from_now(-90),
            "reminderOffset": -1,
            "subtasks": [],
            "completed": False,
            "createdAt": iso_minutes_from_now(0),
            "order": order,
        },
    )


def delete_task(page: Page, task_name: str) -> None:
    task = task_locator(page, task_name)
    task.first.locator('[data-action="delete"]').click()
    expect(page.locator("#taskModal")).to_be_visible()
    assert_accessibility_baseline(page, "delete confirmation")
    page.locator("#submitBtn").click()
    expect(task).to_have_count(0)


def cancel_delete_task(page: Page, task_name: str) -> None:
    task = task_locator(page, task_name)
    task.first.locator('[data-action="delete"]').click()
    expect(page.locator("#taskModal")).to_be_visible()
    page.locator("#cancelBtn").click()
    expect(task_locator(page, task_name)).to_have_count(1)


def select_filter(page: Page, value: str) -> None:
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


def select_project(page: Page, value: str) -> None:
    project_btn = page.locator("#projectFilterBtn")
    selected_option = page.locator(f'#projectDropdown .dropdown-option[data-project="{value}"]')
    expect(project_btn).to_have_attribute("aria-controls", "projectFilterMenu")
    project_btn.click()
    selected_option.click()
    expect(project_btn).to_have_attribute("aria-expanded", "false")
    expect(project_btn).to_be_focused()
    expect(selected_option).to_have_attribute("aria-selected", "true")
    expect(selected_option).to_have_class(
        re.compile(r"(^|\s)selected(\s|$)")
    )


def select_sort(page: Page, value: str) -> None:
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


def select_view(page: Page, value: str) -> None:
    tab = page.locator(f'#viewSwitcher .view-tab[data-view="{value}"]')
    tab.click()
    expect(tab).to_have_attribute("aria-selected", "true")
    expect(tab).to_have_class(re.compile(r"(^|\s)selected(\s|$)"))


def visible_task_names(page: Page) -> list[str]:
    return page.locator(".task-item .task-name").all_text_contents()


def assert_task_order(page: Page, expected_names: list[str]) -> None:
    actual_names = visible_task_names(page)
    if actual_names != expected_names:
        raise AssertionError(f"Expected task order {expected_names}, got {actual_names}")


def edit_task(page: Page, task_name: str, updated_name: str) -> None:
    task = task_locator(page, task_name)
    task.first.locator('[data-action="edit"]').click()
    expect(page.locator("#taskModal")).to_be_visible()
    page.locator("#taskName").fill(updated_name)
    page.locator("#taskDesc").fill("Updated by Playwright smoke test.")
    page.locator("#submitBtn").click()
    expect(task_locator(page, updated_name)).to_have_count(1)
    expect(task_locator(page, task_name)).to_have_count(0)


def exercise_subtasks(page: Page, task_name: str) -> None:
    task = task_locator(page, task_name)
    expect(task.locator(".subtasks-wrapper .progress-text")).to_contain_text("0/2")
    task.locator(".subtask-summary-bar").click()
    expect(task.locator(".subtasks-wrapper")).to_have_class(re.compile(r"(^|\s)expanded(\s|$)"))
    expect(task.locator(".subtasks-wrapper .subtask-display-item")).to_have_count(2)
    task.locator(".subtasks-wrapper .subtask-display-item").first.click()
    expect(task.locator(".subtasks-wrapper .progress-text")).to_contain_text("1/2")
    page.locator("#searchInput").fill("  Second   smoke subtask  ")
    expect(task_locator(page, task_name)).to_have_count(1)
    clear_search(page)


def exercise_theme(page: Page) -> None:
    before = page.evaluate("document.documentElement.getAttribute('data-theme')")
    theme_button = page.locator("#themeToggleBtn")
    theme_button.click()
    expect(theme_button).to_be_disabled()
    page.wait_for_function(
        "before => document.documentElement.getAttribute('data-theme') !== before",
        arg=before,
    )
    page.wait_for_function(
        "() => !document.documentElement.classList.contains('theme-transitioning')"
    )
    expect(theme_button).to_be_enabled()
    after = page.evaluate("document.documentElement.getAttribute('data-theme')")
    stored = page.evaluate("localStorage.getItem('theme')")
    theme_color = page.locator('meta[name="theme-color"]').get_attribute("content")
    expected_theme_color = "#0f1117" if after == "dark" else "#2563eb"
    manifest_path = page.evaluate(
        """async () => {
            const href = document.querySelector('#manifestLink').href;
            return new URL(href).pathname;
        }"""
    )
    if (
        before == after
        or after not in {"light", "dark"}
        or stored != after
        or theme_color != expected_theme_color
        or not manifest_path.endswith("/manifest.json")
    ):
        raise AssertionError(
            "Theme toggle failed: "
            f"before={before}, after={after}, stored={stored}, "
            f"theme_color={theme_color}, manifest_path={manifest_path}"
        )


def exercise_theme_fallback_transition(page: Page) -> None:
    result = page.evaluate(
        """async () => {
            const html = document.documentElement;
            const originalStartViewTransition = document.startViewTransition;
            Object.defineProperty(document, 'startViewTransition', {
                configurable: true,
                value: undefined
            });

            const body = document.body;
            const controls = document.querySelector('.controls-bar');
            const task = document.querySelector('.task-item');
            const button = document.querySelector('#themeToggleBtn');
            const beforeTheme = html.getAttribute('data-theme');

            const readState = () => ({
                theme: html.getAttribute('data-theme'),
                isTransitioning: html.classList.contains('theme-transitioning'),
                buttonDisabled: button.disabled,
                bodyTransition: getComputedStyle(body).transitionProperty,
                bodyBackgroundImage: getComputedStyle(body).backgroundImage,
                controlsTransition: getComputedStyle(controls).transitionProperty,
                taskTransition: getComputedStyle(task).transitionProperty
            });

            button.click();
            await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
            const during = readState();
            await new Promise(resolve => setTimeout(resolve, 330));
            const after = readState();

            Object.defineProperty(document, 'startViewTransition', {
                configurable: true,
                value: originalStartViewTransition
            });

            return { beforeTheme, during, after };
        }"""
    )

    if result["during"]["theme"] == result["beforeTheme"]:
        raise AssertionError(f"Fallback theme did not switch during transition: {result}")
    if not result["during"]["isTransitioning"] or not result["during"]["buttonDisabled"]:
        raise AssertionError(f"Fallback theme transition did not expose in-flight state: {result}")
    if result["after"]["isTransitioning"] or result["after"]["buttonDisabled"]:
        raise AssertionError(f"Fallback theme transition did not clean up: {result}")

    for label, property_name in (
        ("body", "bodyTransition"),
        ("controls", "controlsTransition"),
        ("task", "taskTransition"),
    ):
        if "background-color" not in result["during"][property_name]:
            raise AssertionError(f"{label} is missing a background-color transition: {result}")

    if "linear-gradient(135deg" in result["during"]["bodyBackgroundImage"]:
        raise AssertionError(f"Body fallback still depends on non-interpolable theme gradient: {result}")


def exercise_language(page: Page) -> None:
    page.locator("#openMenuBtn").click()
    page.locator("#langMenuToggle").click()
    page.locator('#lang-container .lang-btn[data-lang="en"]').click()
    expect(page.locator("h1")).to_have_text("Task Tracker")
    expect(page.locator("#currentFilterLabel")).to_have_text("Active")
    if page.title() != "Task Tracker":
        raise AssertionError(f"Expected English document title, got {page.title()!r}")
    expect(page.locator("html")).to_have_attribute("lang", "en")
    expect(page.locator("html")).to_have_attribute("dir", "ltr")
    expect(page.locator(".controls-bar")).to_have_attribute("aria-label", "Task toolbar")
    expect(page.locator('#lang-container .lang-btn[data-lang="en"]')).to_have_attribute("aria-checked", "true")

    page.locator('#lang-container .lang-btn[data-lang="zh-CN"]').click()
    expect(page.locator("h1")).to_have_text("任务跟踪器")
    expect(page.locator("#currentFilterLabel")).to_have_text("进行中")
    if page.title() != "任务跟踪器":
        raise AssertionError(f"Expected Chinese document title, got {page.title()!r}")
    expect(page.locator("html")).to_have_attribute("lang", "zh-CN")
    expect(page.locator("html")).to_have_attribute("dir", "ltr")
    expect(page.locator(".controls-bar")).to_have_attribute("aria-label", "任务工具栏")
    expect(page.locator('#lang-container .lang-btn[data-lang="zh-CN"]')).to_have_attribute("aria-checked", "true")
    assert_accessibility_baseline(page, "language menu")
    page.keyboard.press("Escape")


def exercise_filters_and_sort(page: Page, alpha_name: str, beta_name: str, overdue_name: str) -> None:
    select_filter(page, "all")
    select_sort(page, "alpha-asc")
    assert_task_order(page, [alpha_name, beta_name, overdue_name])

    select_sort(page, "created-desc")
    expect(page.locator('#sortDropdown .dropdown-option[data-sort="created-desc"]')).to_have_class(
        re.compile(r"(^|\s)selected(\s|$)")
    )

    select_sort(page, "due-asc")
    assert_task_order(page, [overdue_name, beta_name, alpha_name])

    select_filter(page, "no-deadline")
    expect(task_locator(page, alpha_name)).to_have_count(1)
    expect(task_locator(page, beta_name)).to_have_count(0)
    expect(task_locator(page, overdue_name)).to_have_count(0)

    select_filter(page, "overdue")
    expect(task_locator(page, overdue_name)).to_have_count(1)
    expect(task_locator(page, alpha_name)).to_have_count(0)
    expect(task_locator(page, beta_name)).to_have_count(0)

    select_filter(page, "active")
    expect(page.locator(".task-item")).to_have_count(3)

    select_filter(page, "all")


def exercise_date_views(page: Page, alpha_name: str, beta_name: str, overdue_name: str) -> None:
    extra_names = [f"Calendar Overflow Extra {index} {int(time.time())}" for index in range(1, 4)]
    for index, extra_name in enumerate(extra_names, start=1):
        put_task_record(
            page,
            {
                "id": int(time.time() * 1000) + 40_000 + index,
                "name": extra_name,
                "description": "Extra same-day task for calendar overflow.",
                "dueDate": None,
                "dueAt": None,
                "dueLocalDate": future_date(1),
                "dueLocalTime": f"13:{index:02d}",
                "dueTimeZone": None,
                "reminderOffset": -1,
                "subtasks": [],
                "completed": False,
                "createdAt": iso_minutes_from_now(index),
                "order": 40_000 + index,
            },
        )

    select_filter(page, "all")
    select_view(page, "calendar")
    expect(page.locator(".calendar-view")).to_be_visible()
    expect(page.locator(".calendar-day")).to_have_count(42)
    expect(page.locator(".calendar-task").filter(has_text=beta_name)).to_have_count(1)
    expect(page.locator(".calendar-task").filter(has_text=overdue_name)).to_have_count(1)
    expect(page.locator(".date-view-undated")).to_contain_text(alpha_name)
    month_title = page.locator(".calendar-title").inner_text()
    page.locator('[data-calendar-action="next-year"]').click()
    next_year_title = page.locator(".calendar-title").inner_text()
    if next_year_title == month_title:
        raise AssertionError("Calendar next-year navigation did not change the visible month title")
    page.locator('[data-calendar-action="prev-year"]').click()
    expect(page.locator(".calendar-title")).to_have_text(month_title)
    calendar_task_style = page.locator(".calendar-task").filter(has_text=beta_name).first.evaluate(
        """(element) => {
            const style = getComputedStyle(element);
            return {
                overflow: style.overflow,
                textOverflow: style.textOverflow,
                whiteSpace: style.whiteSpace,
                title: element.getAttribute('title')
            };
        }"""
    )
    if calendar_task_style != {"overflow": "hidden", "textOverflow": "ellipsis", "whiteSpace": "nowrap", "title": beta_name}:
        raise AssertionError(f"Calendar task title is not constrained to one-line ellipsis: {calendar_task_style}")
    page.locator(".calendar-more-btn").click()
    expect(page.locator(".calendar-day-detail")).to_be_visible()
    expect(page.locator(".calendar-detail-task")).to_have_count(4)
    expect(page.locator(".calendar-day-detail")).to_contain_text(beta_name)
    expect(page.locator(".calendar-day-detail")).to_contain_text(extra_names[0])
    page.locator(".calendar-detail-task").filter(has_text=extra_names[0]).click()
    expect(page.locator("#taskModal")).to_be_visible()
    expect(page.locator("#taskName")).to_have_value(extra_names[0])
    page.locator("#cancelBtn").click()
    page.locator(".calendar-more-btn").click()
    expect(page.locator(".calendar-day-detail")).to_be_visible()
    page.locator(".calendar-detail-close").click()
    expect(page.locator(".calendar-day-detail")).to_have_count(0)
    add_button = page.locator(".calendar-day:not(.outside-month) .calendar-date-number[data-calendar-add-date]").first
    selected_date = add_button.get_attribute("data-calendar-add-date")
    add_button.click()
    expect(page.locator("#taskModal")).to_be_visible()
    expect(page.locator("#dueDate")).to_have_value(selected_date)
    page.locator("#cancelBtn").click()
    page.locator(".calendar-task").filter(has_text=beta_name).first.click()
    expect(page.locator("#taskModal")).to_be_visible()
    expect(page.locator("#taskName")).to_have_value(beta_name)
    page.locator("#cancelBtn").click()

    for extra_name in extra_names:
        delete_task_records_by_name(page, extra_name)

    select_filter(page, "all")
    select_view(page, "timeline")
    expect(page.locator(".timeline-view")).to_be_visible()
    expect(page.locator(".timeline-group")).to_have_count(3)
    expect(task_locator(page, alpha_name)).to_have_count(1)
    expect(task_locator(page, beta_name)).to_have_count(1)
    expect(task_locator(page, overdue_name)).to_have_count(1)
    assert_accessibility_baseline(page, "date views")

    select_view(page, "list")
    expect(page.locator(".task-item")).to_have_count(3)


def exercise_stats_view(page: Page, completed_name: str) -> None:
    select_view(page, "stats")
    expect(page.locator(".stats-view")).to_be_visible()
    expect(page.locator(".stat-card").nth(0).locator(".stat-value")).to_have_text("33%")
    expect(page.locator(".stat-card").nth(1).locator(".stat-value")).to_have_text("50%")
    expect(page.locator(".stat-card").nth(2).locator(".stat-value")).to_contain_text("1")
    expect(page.locator(".stats-mini")).to_have_count(5)
    expect(page.locator(".stats-trend")).to_be_visible()
    expect(page.locator(".stats-trend-bar")).to_have_count(7)
    trend_counts = page.locator(".stats-trend-bar").evaluate_all(
        "bars => bars.map((bar) => Number(bar.dataset.trendCount || 0))"
    )
    if sum(trend_counts) != 1:
        raise AssertionError(f"Completion trend did not reflect the completed task: {trend_counts}")
    assert_accessibility_baseline(page, "stats view")
    page.locator('.stats-mini[data-stats-filter="completed"]').click()
    expect(page.locator("#currentFilterLabel")).to_have_text(re.compile("已完成|Completed", re.I))
    expect(task_locator(page, completed_name)).to_have_count(1)
    expect(page.locator("#filterBtn")).to_be_focused()


def complete_task(page: Page, task_name: str) -> None:
    active_task = task_locator(page, task_name).first
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
    expect(task.locator('[data-action="toggle"] use')).to_have_attribute("href", "#icon-undo")
    decoration = task.locator(".task-name").evaluate(
        "element => getComputedStyle(element).textDecorationLine"
    )
    if "line-through" not in decoration:
        raise AssertionError(f"Completed task name is not struck through: {decoration}")
    select_filter(page, "no-deadline")
    expect(task_locator(page, task_name)).to_have_count(1)
    expect(page.locator("#count-no-deadline")).to_have_text("(1)")
    select_filter(page, "completed")


def exercise_repeating_task(page: Page, task_name: str) -> None:
    add_task(
        page,
        task_name,
        description="Repeating task smoke test.",
        due_date=future_date(1),
        due_time="08:45",
        repeat_type="custom",
        repeat_interval="3",
        project="Smoke Routine",
        tags=["routine"],
    )
    expect(task_locator(page, task_name).locator(".repeat-chip")).to_contain_text(re.compile("3"))
    task_locator(page, task_name).locator('[data-action="toggle"]').click()
    wait_for_notification(page, re.compile("下一期|next occurrence", re.I))
    records = page.evaluate(
        """async (taskName) => {
            const request = indexedDB.open('TaskTrackerDB', 2);
            return await new Promise((resolve, reject) => {
                request.onerror = () => reject(request.error);
                request.onsuccess = () => {
                    const db = request.result;
                    const tx = db.transaction(['tasks'], 'readonly');
                    const getAll = tx.objectStore('tasks').getAll();
                    getAll.onsuccess = () => {
                        const tasks = getAll.result
                            .filter((item) => item.name === taskName)
                            .map((item) => ({
                                completed: item.completed,
                                repeatType: item.repeatType,
                                repeatInterval: item.repeatInterval,
                                repeatCreatedFrom: item.repeatCreatedFrom,
                                dueDate: item.dueDate,
                                dueAt: item.dueAt,
                                dueLocalDate: item.dueLocalDate,
                                dueLocalTime: item.dueLocalTime,
                                dueTimeZone: item.dueTimeZone,
                                nextRepeatTaskId: item.nextRepeatTaskId
                            }));
                        db.close();
                        resolve(tasks);
                    };
                    getAll.onerror = () => reject(getAll.error);
                };
            });
        }""",
        task_name,
    )
    completed = [record for record in records if record["completed"]]
    active = [record for record in records if not record["completed"]]
    if len(records) != 2 or len(completed) != 1 or len(active) != 1:
        raise AssertionError(f"Repeating completion did not create exactly one next task: {records}")
    if active[0]["repeatType"] != "custom" or active[0]["repeatInterval"] != 3 or not active[0]["repeatCreatedFrom"]:
        raise AssertionError(f"Next repeating task did not preserve repeat metadata: {records}")
    if active[0]["dueDate"] <= completed[0]["dueDate"] or completed[0]["nextRepeatTaskId"] is None:
        raise AssertionError(f"Next repeating task did not advance due date/linkage: {records}")
    if active[0]["dueDate"] != active[0]["dueAt"] or completed[0]["dueDate"] != completed[0]["dueAt"]:
        raise AssertionError(f"Repeating tasks did not keep dueDate/dueAt compatibility: {records}")
    if active[0]["dueLocalTime"] != completed[0]["dueLocalTime"] or not active[0]["dueTimeZone"]:
        raise AssertionError(f"Repeating tasks did not preserve local due time metadata: {records}")
    completed_due = datetime.strptime(completed[0]["dueLocalDate"], "%Y-%m-%d").date()
    active_due = datetime.strptime(active[0]["dueLocalDate"], "%Y-%m-%d").date()
    if active_due != completed_due + timedelta(days=3):
        raise AssertionError(f"Repeating task did not advance the local due date by 3 days: {records}")
    delete_task_records_by_name(page, task_name)


def delete_task_records_by_name(page: Page, task_name: str) -> None:
    page.evaluate(
        """async (taskName) => {
            await new Promise((resolve, reject) => {
                const request = indexedDB.open('TaskTrackerDB', 2);
                request.onerror = () => reject(request.error);
                request.onsuccess = () => {
                    const db = request.result;
                    const tx = db.transaction(['tasks'], 'readwrite');
                    const store = tx.objectStore('tasks');
                    const getAll = store.getAll();
                    getAll.onsuccess = () => {
                        getAll.result
                            .filter((item) => item.name === taskName)
                            .forEach((item) => store.delete(item.id));
                    };
                    tx.oncomplete = () => {
                        db.close();
                        resolve();
                    };
                    tx.onerror = () => reject(tx.error);
                    tx.onabort = () => reject(tx.error);
                };
            });
        }""",
        task_name,
    )
    page.reload(wait_until="domcontentloaded")
    wait_for_app_ready(page)


def clear_completed_tasks(page: Page, completed_name: str) -> None:
    page.locator("#openMenuBtn").click()
    page.locator("#clearCompletedBtn").click()
    expect(page.locator("#taskModal")).to_be_visible()
    page.locator("#submitBtn").click()
    expect(task_locator(page, completed_name)).to_have_count(0)


def archive_and_restore_task(page: Page, completed_name: str) -> None:
    select_filter(page, "completed")
    task = task_locator(page, completed_name)
    expect(task.locator('[data-action="archive"]')).to_be_visible()
    task.locator('[data-action="archive"]').click()
    wait_for_notification(page, re.compile("已归档|archived", re.I))
    select_view(page, "stats")
    archived_shortcut = page.locator('.stats-mini[data-stats-filter="archived"]')
    expect(archived_shortcut.locator("strong")).to_have_text("1")
    archived_shortcut.click()
    expect(page.locator("#currentFilterLabel")).to_have_text(re.compile("已归档|Archived", re.I))
    archived = task_locator(page, completed_name)
    expect(archived).to_have_count(1)
    expect(archived.locator(".status-text")).to_have_text(re.compile("已归档|Archived", re.I))
    expect(archived.locator('[data-action="toggle"]')).to_be_hidden()
    select_filter(page, "active")
    page.locator("#searchInput").fill("status:archived")
    expect(task_locator(page, completed_name)).to_have_count(1)
    clear_search(page)
    select_filter(page, "archived")
    archived = task_locator(page, completed_name)
    archived.locator('[data-action="archive"]').click()
    wait_for_notification(page, re.compile("恢复|restored", re.I))
    select_filter(page, "completed")
    expect(task_locator(page, completed_name)).to_have_count(1)


def exercise_manual_reorder(page: Page, first_name: str, second_name: str, third_name: str) -> None:
    select_filter(page, "all")
    select_sort(page, "manual")
    expect(page.locator(".task-item.draggable-item .drag-handle")).to_have_count(3)
    assert_task_order(page, [first_name, second_name, third_name])
    page.wait_for_timeout(150)

    drag_task_before(page, third_name, first_name)
    page.wait_for_timeout(500)
    assert_task_order(page, [third_name, first_name, second_name])

    page.reload(wait_until="domcontentloaded")
    wait_for_app_ready(page)
    select_filter(page, "all")
    select_sort(page, "manual")
    assert_task_order(page, [third_name, first_name, second_name])
    task_locator(page, first_name).locator(".drag-handle").focus()
    page.keyboard.press("ArrowUp")
    expect(page.locator("#srStatus")).to_contain_text("第 1 位")
    assert_task_order(page, [first_name, third_name, second_name])
    assert_accessibility_baseline(page, "manual reorder")


def drag_task_before(page: Page, source_name: str, target_name: str) -> None:
    task_locator(page, source_name).scroll_into_view_if_needed()
    task_locator(page, target_name).scroll_into_view_if_needed()
    handle_box = task_locator(page, source_name).locator(".drag-handle").bounding_box()
    target_box = task_locator(page, target_name).bounding_box()
    if not handle_box or not target_box:
        raise AssertionError("Could not resolve task drag geometry")
    page.mouse.move(handle_box["x"] + handle_box["width"] / 2, handle_box["y"] + handle_box["height"] / 2)
    page.mouse.down()
    page.mouse.move(target_box["x"] + 20, target_box["y"] + 5, steps=12)
    page.mouse.up()


def exercise_filtered_manual_reorder_guard(page: Page, completed_name: str, first_active: str, second_active: str) -> None:
    select_filter(page, "active")
    select_sort(page, "manual")
    expect(page.locator(".task-item.draggable-item .drag-handle")).to_have_count(2)
    assert_task_order(page, [first_active, second_active])
    drag_task_before(page, second_active, first_active)
    page.wait_for_timeout(500)
    assert_task_order(page, [second_active, first_active])
    select_filter(page, "all")
    expect(page.locator(".task-item.draggable-item .drag-handle")).to_have_count(3)
    assert_task_order(page, [completed_name, second_active, first_active])


def exercise_back_to_top(page: Page) -> None:
    page.evaluate(
        """() => {
            const spacer = document.createElement('div');
            spacer.id = 'smoke-scroll-spacer';
            spacer.style.height = '1200px';
            document.body.appendChild(spacer);
        }"""
    )
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    wait_for_class(page, "#backToTopBtn", "show")
    page.locator("#backToTopBtn").click()
    page.wait_for_function("() => window.scrollY === 0")
    page.evaluate("document.getElementById('smoke-scroll-spacer')?.remove()")


def exercise_notifications(page: Page) -> None:
    page.locator("#notificationToggleBtn").click()
    expect(page.locator("#notificationToggleBtn")).to_have_attribute("aria-label", "关闭通知")
    expect(page.locator("#notificationToggleBtn")).to_have_class(re.compile(r"(^|\s)notifications-enabled(\s|$)"))
    page.locator("#notificationToggleBtn").click()
    expect(page.locator("#notificationToggleBtn")).to_have_attribute("aria-label", "开启通知")
    expect(page.locator("#notificationToggleBtn")).not_to_have_class(re.compile(r"(^|\s)notifications-enabled(\s|$)"))


def exercise_import_error(page: Page) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as temp_file:
        json.dump({"notTasks": []}, temp_file)
        temp_path = temp_file.name

    try:
        page.locator("#openMenuBtn").click()
        with page.expect_file_chooser() as chooser_info:
            page.locator("#importBtn").click()
        chooser_info.value.set_files(temp_path)
        wait_for_notification(page, re.compile("导入失败|Import failed", re.I))
    finally:
        Path(temp_path).unlink(missing_ok=True)
    page.keyboard.press("Escape")


def exercise_export(page: Page) -> dict[str, Any]:
    page.locator("#openMenuBtn").click()
    with page.expect_download() as download_info:
        page.locator("#exportBtn").click()
    download = download_info.value
    path = download.path()
    if not path:
        raise AssertionError("Export did not produce a readable download file")

    exported = json.loads(Path(path).read_text(encoding="utf-8"))
    if exported.get("version") != "2.1" or not exported.get("date") or not exported.get("versionNotes"):
        raise AssertionError(f"Export payload metadata is incomplete: {exported}")
    if not isinstance(exported.get("tasks"), list) or not exported["tasks"]:
        raise AssertionError(f"Export payload did not include tasks: {exported}")
    return exported


def exercise_backup(page: Page) -> dict[str, Any]:
    page.locator("#openMenuBtn").click()
    with page.expect_download() as download_info:
        page.locator("#backupBtn").click()
    download = download_info.value
    path = download.path()
    if not path:
        raise AssertionError("Backup did not produce a readable download file")
    backup = json.loads(Path(path).read_text(encoding="utf-8"))
    if backup.get("version") != "2.1" or backup.get("type") != "backup" or not backup.get("schema"):
        raise AssertionError(f"Backup payload metadata is incomplete: {backup}")
    last_backup = page.evaluate(
        """async () => {
            return await new Promise((resolve, reject) => {
                const request = indexedDB.open('TaskTrackerDB', 2);
                request.onerror = () => reject(request.error);
                request.onsuccess = () => {
                    const db = request.result;
                    const tx = db.transaction(['config'], 'readonly');
                    const get = tx.objectStore('config').get('lastBackupAt');
                    get.onsuccess = () => {
                        db.close();
                        resolve(get.result ? get.result.value : null);
                    };
                    get.onerror = () => reject(get.error);
                };
            });
        }"""
    )
    if not last_backup:
        raise AssertionError("Backup did not record the last backup timestamp")
    page.locator("#openMenuBtn").click()
    expect(page.locator("#backupHealthText")).to_contain_text(re.compile("今天|today", re.I))
    page.keyboard.press("Escape")
    return backup


def exercise_import_preview_details(page: Page, existing_name: str) -> None:
    payload = [
        {"id": 91001, "name": existing_name, "createdAt": "2025-05-10T00:00:00.000Z"},
        {"id": 91002, "name": "Preview Duplicate", "createdAt": "2025-05-10T00:00:00.000Z"},
        {"id": 91003, "name": "Preview Duplicate", "createdAt": "2025-05-10T00:00:00.000Z"},
    ]

    with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as temp_file:
        json.dump(payload, temp_file)
        temp_path = temp_file.name

    try:
        page.locator("#openMenuBtn").click()
        with page.expect_file_chooser() as chooser_info:
            page.locator("#importBtn").click()
        chooser_info.value.set_files(temp_path)
        expect(page.locator("#taskModal")).to_be_visible()
        expect(page.locator("#modalTitle")).to_have_text(re.compile("导入预览|Import Preview", re.I))
        expect(page.locator("#mergeImportMode")).not_to_be_checked()
        expect(page.locator("#confirm-message-text")).to_contain_text(re.compile("合并到当前任务|Merge into current tasks", re.I))
        rows = page.locator(".confirm-row").all_inner_texts()
        if not any(re.search(r"(文件内重复|Repeated inside file)[\s\S]*1", row, re.I) for row in rows):
            raise AssertionError(f"Import preview did not report file duplicates: {rows}")
        if not any(re.search(r"(匹配当前任务|Matches current tasks)[\s\S]*1", row, re.I) for row in rows):
            raise AssertionError(f"Import preview did not report current task matches: {rows}")
        expect(page.locator(".confirm-list")).to_have_count(2)
        expect(page.locator(".import-conflict-select")).to_have_count(1)
        expect(page.locator(".import-conflict-select")).to_have_value("keep")
        expect(page.locator("#confirm-message-text")).to_contain_text("Preview Duplicate")
        expect(page.locator("#confirm-message-text")).to_contain_text(existing_name)
        page.locator("#cancelBtn").click()
        expect(page.locator("#taskModal")).to_be_hidden()
    finally:
        Path(temp_path).unlink(missing_ok=True)


def exercise_import_merge(page: Page, merged_name: str, existing_name: str) -> None:
    existing_id = page.evaluate(
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
                        resolve(task ? task.id : null);
                    };
                    getAll.onerror = () => reject(getAll.error);
                };
            });
        }""",
        existing_name,
    )
    if existing_id is None:
        raise AssertionError(f"Could not find existing task id for {existing_name}")

    payload = [
        {
            "id": existing_id,
            "name": merged_name,
            "description": "Merged by Playwright smoke test.",
            "dueDate": None,
            "createdAt": "2025-05-10T00:00:00.000Z",
            "completed": False,
            "order": 1000,
        }
    ]

    with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as temp_file:
        json.dump(payload, temp_file)
        temp_path = temp_file.name

    try:
        page.locator("#openMenuBtn").click()
        with page.expect_file_chooser() as chooser_info:
            page.locator("#importBtn").click()
        chooser_info.value.set_files(temp_path)
        expect(page.locator("#taskModal")).to_be_visible()
        page.locator("#mergeImportMode").check()
        page.locator("#submitBtn").click()
        wait_for_notification(page, re.compile("合并|merged", re.I))
        select_filter(page, "all")
        expect(task_locator(page, existing_name)).to_have_count(1)
        expect(task_locator(page, merged_name)).to_have_count(1)
        expect(page.locator(".task-item")).to_have_count(3)
        merged_id = page.evaluate(
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
                            resolve(task ? task.id : null);
                        };
                        getAll.onerror = () => reject(getAll.error);
                    };
                });
            }""",
            merged_name,
        )
        if merged_id == existing_id:
            raise AssertionError("Merged import reused an existing task id")
    finally:
        Path(temp_path).unlink(missing_ok=True)
    delete_task_records_by_name(page, merged_name)
    select_filter(page, "all")


def exercise_import(page: Page, imported_name: str) -> None:
    payload = [
        {
            "id": 10001,
            "name": imported_name,
            "description": "Imported by Playwright smoke test.",
            "dueDate": None,
            "createdAt": "2025-05-10T00:00:00.000Z",
            "completed": False,
            "order": 1000,
            "subtasks": [
                {"id": 20001, "text": "Imported subtask A", "completed": False},
                {"id": 20001, "text": "Imported subtask B", "completed": False},
            ],
        }
    ]

    with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as temp_file:
        json.dump(payload, temp_file)
        temp_path = temp_file.name

    try:
        page.locator("#openMenuBtn").click()
        with page.expect_file_chooser() as chooser_info:
            page.locator("#importBtn").click()
        chooser_info.value.set_files(temp_path)
        expect(page.locator("#taskModal")).to_be_visible()
        expect(page.locator("#modalTitle")).to_have_text(re.compile("导入预览|Import Preview", re.I))
        expect(page.locator("#confirm-message-text")).to_contain_text(re.compile("1"))
        expect(page.locator("#confirm-message-text")).to_contain_text(re.compile("替换|replace", re.I))
        expect(page.locator("#confirm-message-text")).to_contain_text(re.compile("文件内重复|Repeated inside file", re.I))
        expect(page.locator("#confirm-message-text")).to_contain_text(re.compile("匹配当前任务|Matches current tasks", re.I))
        page.locator("#submitBtn").click()
        select_filter(page, "all")
        imported_task = task_locator(page, imported_name)
        expect(imported_task).to_have_count(1)
        expect(page.locator(".task-item")).to_have_count(1)
        expect(imported_task.locator(".subtasks-wrapper .progress-text")).to_contain_text("0/2")
        imported_task.locator(".subtask-summary-bar").click()
        expect(imported_task.locator(".subtask-display-item")).to_have_count(2)
        imported_task.locator(".subtask-display-item").nth(1).click()
        expect(imported_task.locator(".subtasks-wrapper .progress-text")).to_contain_text("1/2")
        expect(imported_task.locator(".subtask-display-item").first.locator(".subtask-checkbox")).not_to_be_checked()
        expect(imported_task.locator(".subtask-display-item").nth(1).locator(".subtask-checkbox")).to_be_checked()
    finally:
        Path(temp_path).unlink(missing_ok=True)


def assert_pwa_resources(context: BrowserContext, base_url: str) -> None:
    required_paths = ["index.html", "manifest.json", "sw.js", "resources/en.json", "resources/zh-CN.json"]
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


def assert_pwa_installability(page: Page) -> None:
    session = page.context.new_cdp_session(page)
    manifest_result = session.send("Page.getAppManifest")
    manifest_errors = manifest_result.get("errors", [])
    if manifest_errors:
        raise AssertionError(f"Manifest has browser parse errors: {manifest_errors}")

    manifest_data = json.loads(manifest_result.get("data") or "{}")
    required_values = {
        "id": "./",
        "start_url": "./",
        "scope": "./",
        "display": "standalone",
    }
    for key, expected in required_values.items():
        if manifest_data.get(key) != expected:
            raise AssertionError(f"Manifest {key} changed: expected {expected!r}, got {manifest_data.get(key)!r}")

    installability_result = session.send("Page.getInstallabilityErrors")
    installability_errors = installability_result.get("installabilityErrors", [])
    if installability_errors:
        raise AssertionError(f"PWA installability errors: {installability_errors}")


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


def assert_visual_layout(context: BrowserContext, base_url: str, errors: list[str]) -> None:
    visual_page = context.new_page()
    visual_page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        for label, viewport in (
            ("desktop", {"width": 1280, "height": 720}),
            ("mobile", {"width": 390, "height": 844}),
            ("compact mobile", {"width": 320, "height": 568}),
        ):
            visual_page.set_viewport_size(viewport)
            visual_page.goto(base_url, wait_until="domcontentloaded")
            wait_for_app_ready(visual_page)
            select_filter(visual_page, "all")
            expect(visual_page.locator(".task-item")).to_have_count(3)
            visual_page.locator(".task-item").first.scroll_into_view_if_needed()

            metrics = visual_page.evaluate(
                """(label) => {
                    const viewportWidth = window.innerWidth;
                    const doc = document.documentElement;
                    const selectors = ['header', '.controls-bar', '.task-item', '.task-actions'];
                    const boxes = selectors.map((selector) => {
                        const el = document.querySelector(selector);
                        if (!el) return { selector, missing: true };
                        const rect = el.getBoundingClientRect();
                        return {
                            selector,
                            left: rect.left,
                            right: rect.right,
                            top: rect.top,
                            bottom: rect.bottom,
                            width: rect.width,
                            height: rect.height
                        };
                    });

                    return {
                        label,
                        viewportWidth,
                        scrollWidth: doc.scrollWidth,
                        boxes,
                        hasTaskName: Boolean(document.querySelector('.task-name')?.textContent.trim()),
                        hasVisibleActions: [...document.querySelectorAll('.task-actions .action-btn')]
                            .filter((button) => !button.hidden && button.offsetParent !== null)
                            .every((button) => button.getBoundingClientRect().width >= 30)
                    };
                }""",
                label,
            )

            overflow = metrics["scrollWidth"] - metrics["viewportWidth"]
            if overflow > 1:
                raise AssertionError(f"{label} layout has horizontal overflow: {metrics}")

            bad_boxes = [
                box for box in metrics["boxes"]
                if box.get("missing")
                or box["width"] <= 0
                or box["height"] <= 0
                or box["left"] < -1
                or box["right"] > metrics["viewportWidth"] + 1
            ]
            if bad_boxes or not metrics["hasTaskName"] or not metrics["hasVisibleActions"]:
                raise AssertionError(f"{label} layout metrics failed: {metrics}")

            screenshot = visual_page.screenshot(full_page=True)
            if len(screenshot) < 10_000:
                raise AssertionError(f"{label} screenshot looks unexpectedly small")

            if label == "compact mobile":
                visual_page.locator("#openModalBtn").click()
                expect(visual_page.locator("#taskModal")).to_be_visible()
                visual_page.wait_for_timeout(350)
                modal_box = visual_page.locator(".modal-content").bounding_box()
                if not modal_box:
                    raise AssertionError("Compact mobile modal did not render")
                if modal_box["y"] < -1 or modal_box["y"] + modal_box["height"] > viewport["height"] + 1:
                    raise AssertionError(f"Compact mobile modal is clipped: {modal_box}")
                visual_page.locator("#cancelBtn").click()
    finally:
        visual_page.close()


def smoke(url: str) -> None:
    errors: list[str] = []
    console_errors: list[str] = []
    bad_resources: list[str] = []
    failed_requests: list[str] = []
    task_name = f"Smoke Task {int(time.time())}"
    alpha_name = f"{task_name} Alpha"
    alpha_edited = f"{task_name} Alpha Edited"
    beta_name = f"{task_name} Beta"
    overdue_name = f"{task_name} Overdue"
    imported_name = f"{task_name} Imported"
    quick_name = f"{task_name} Quick"
    repeat_name = f"{task_name} Repeat"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        context.grant_permissions(["notifications"], origin=get_origin(url))
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            and not message.text.startswith("Failed to load resource")
            else None,
        )
        page.on(
            "response",
            lambda response: bad_resources.append(
                f"{response.status} {response.url}"
            )
            if response.status >= 400 and not is_ignored_resource(response.url)
            else None,
        )
        page.on(
            "requestfailed",
            lambda request: failed_requests.append(describe_request_failure(request))
            if request.failure and not is_ignored_resource(request.url)
            else None,
        )

        assert_pwa_resources(context, url)
        clear_app_data(page, url)
        assert_empty_task_list(page)
        assert_accessibility_baseline(page, "empty task list")

        exercise_shortcuts_and_modal_closing(page)
        exercise_keyboard_navigation_patterns(page)
        exercise_task_name_validation(page)
        exercise_empty_state_actions(page)
        exercise_import_error(page)
        exercise_theme(page)
        exercise_language(page)
        exercise_notifications(page)
        assert_service_worker_and_offline_load(context, page)
        assert_pwa_installability(page)

        exercise_quick_add(page, quick_name)
        exercise_subtask_draft_editor(page)
        exercise_repeating_task(page, repeat_name)
        add_task(page, alpha_name, no_deadline=True, project="Smoke Work", tags=["focus", "docs"], subtasks=["First smoke subtask", "Second smoke subtask"])
        add_task(page, beta_name, due_date=future_date(1), due_time="12:30", reminder_offset="15", project="Smoke Personal", tags=["deadline"])
        expect(task_locator(page, beta_name).locator(".task-reminder-icon")).to_be_visible()
        snooze_task_reminder(page, beta_name)
        add_overdue_task_record(page, overdue_name, order=30_000)
        exercise_project_tags(page, alpha_name, beta_name)
        exercise_theme_fallback_transition(page)
        exercise_search_empty_state(page, f"{task_name} Missing")
        exercise_subtasks(page, alpha_name)
        assert_visual_layout(context, url, errors)

        edit_task(page, alpha_name, alpha_edited)
        search_task(page, alpha_edited)
        clear_search(page)

        exercise_filters_and_sort(page, alpha_edited, beta_name, overdue_name)
        exercise_date_views(page, alpha_edited, beta_name, overdue_name)
        exercise_manual_reorder(page, alpha_edited, beta_name, overdue_name)
        exercise_back_to_top(page)
        complete_task(page, alpha_edited)
        exercise_stats_view(page, alpha_edited)
        select_filter(page, "active")
        expect(task_locator(page, beta_name)).to_have_count(1)
        expect(task_locator(page, overdue_name)).to_have_count(1)
        exercise_filtered_manual_reorder_guard(page, alpha_edited, overdue_name, beta_name)
        archive_and_restore_task(page, alpha_edited)
        clear_completed_tasks(page, alpha_edited)

        select_filter(page, "all")
        expect(task_locator(page, beta_name)).to_have_count(1)
        expect(task_locator(page, overdue_name)).to_have_count(1)
        exported = exercise_export(page)
        exported_names = {task["name"] for task in exported["tasks"]}
        if exported_names != {beta_name, overdue_name}:
            raise AssertionError(f"Exported tasks did not match remaining tasks: {exported}")
        backup = exercise_backup(page)
        backup_names = {task["name"] for task in backup["tasks"]}
        if backup_names != {beta_name, overdue_name}:
            raise AssertionError(f"Backup tasks did not match remaining tasks: {backup}")

        exercise_import_merge(page, f"{task_name} Merged", beta_name)
        exercise_import_preview_details(page, beta_name)
        exercise_import(page, imported_name)
        cancel_delete_task(page, imported_name)
        delete_task(page, imported_name)
        assert_empty_task_list(page)

        context.close()
        browser.close()

    assert_no_page_errors(errors)
    if bad_resources:
        joined = "\n".join(f"- {resource}" for resource in bad_resources)
        raise AssertionError(f"Unexpected HTTP errors were loaded:\n{joined}")
    if failed_requests:
        joined = "\n".join(f"- {request}" for request in failed_requests)
        raise AssertionError(f"Unexpected browser requests failed:\n{joined}")
    if console_errors:
        joined = "\n".join(f"- {error}" for error in console_errors)
        raise AssertionError(f"Browser console errors were logged:\n{joined}")

    print(f"Smoke passed: {url}")


def main() -> int:
    ensure_conda_library_path()
    url = os.environ.get("TASK_TRACER_URL")

    try:
        if url:
            smoke(url)
        else:
            with local_server() as local_url:
                smoke(local_url)
    except TimeoutError as error:
        print(f"Smoke failed: timed out waiting for UI state\n{error}", file=sys.stderr)
        return 1
    except Exception as error:
        print(f"Smoke failed: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
