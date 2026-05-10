#!/usr/bin/env python3
"""Browser smoke test for the Task Tracer single-file PWA.

Run with:
    conda run -n task python tools/smoke_playwright.py

Set TASK_TRACER_URL to test an already-running server. Without it, this script
starts a temporary static server from the repository root.
"""

from __future__ import annotations

import contextlib
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


def task_locator(page: Page, task_name: str):
    exact_name = page.locator(".task-name").filter(
        has_text=re.compile(f"^{re.escape(task_name)}$")
    )
    return page.locator(".task-item").filter(has=exact_name)


def wait_for_app_ready(page: Page) -> None:
    expect(page.locator("#openModalBtn")).to_be_visible()
    page.locator("#taskList .loading-state").wait_for(state="detached", timeout=10_000)
    page.locator("#taskList").wait_for(state="visible")


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
    wait_for_app_ready(page)


def assert_empty_task_list(page: Page) -> None:
    expect(page.locator(".task-item")).to_have_count(0)
    expect(page.locator("#taskList .empty-state")).to_be_visible()


def add_task(
    page: Page,
    task_name: str,
    description: str = "Created by Playwright smoke test.",
    no_deadline: bool = False,
    subtasks: list[str] | None = None,
) -> None:
    page.locator("#openModalBtn").click()
    expect(page.locator("#taskModal")).to_be_visible()
    page.locator("#taskName").fill(task_name)
    page.locator("#taskDesc").fill(description)

    if no_deadline:
        page.locator("#noDeadline").check()

    for subtask in subtasks or []:
        page.locator("#subtaskInput").fill(subtask)
        page.locator("#addSubtaskBtn").click()
        expect(page.locator("#subtaskListPreview .subtask-preview-item")).to_have_count(
            (subtasks or []).index(subtask) + 1
        )

    page.locator("#submitBtn").click()

    task = task_locator(page, task_name)
    expect(task).to_have_count(1)
    expect(task.first.locator(".task-name")).to_contain_text(task_name)


def search_task(page: Page, task_name: str) -> None:
    page.locator("#searchInput").fill(task_name)
    expect(task_locator(page, task_name)).to_have_count(1)


def clear_search(page: Page) -> None:
    page.locator("#searchInput").fill("")
    page.wait_for_timeout(350)


def delete_task(page: Page, task_name: str) -> None:
    task = task_locator(page, task_name)
    task.first.locator('[data-action="delete"]').click()
    expect(page.locator("#taskModal")).to_be_visible()
    page.locator("#submitBtn").click()
    expect(task).to_have_count(0)


def select_filter(page: Page, value: str) -> None:
    page.locator("#filterBtn").click()
    page.locator(f'#filterDropdown .dropdown-option[data-filter="{value}"]').click()
    expect(page.locator(f'#filterDropdown .dropdown-option[data-filter="{value}"]')).to_have_class(
        re.compile(r"(^|\s)selected(\s|$)")
    )


def select_sort(page: Page, value: str) -> None:
    page.locator("#sortBtn").click()
    page.locator(f'#sortDropdown .dropdown-option[data-sort="{value}"]').click()
    expect(page.locator(f'#sortDropdown .dropdown-option[data-sort="{value}"]')).to_have_class(
        re.compile(r"(^|\s)selected(\s|$)")
    )


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


def exercise_theme(page: Page) -> None:
    before = page.evaluate("document.documentElement.getAttribute('data-theme')")
    page.locator("#themeToggleBtn").click()
    after = page.evaluate("document.documentElement.getAttribute('data-theme')")
    stored = page.evaluate("localStorage.getItem('theme')")
    if before == after or after not in {"light", "dark"} or stored != after:
        raise AssertionError(f"Theme toggle failed: before={before}, after={after}, stored={stored}")


def exercise_language(page: Page) -> None:
    page.locator("#openMenuBtn").click()
    page.locator("#langMenuToggle").click()
    page.locator('#lang-container .lang-btn[data-lang="en"]').click()
    expect(page.locator("h1")).to_have_text("Task Tracker")
    expect(page.locator("#currentFilterLabel")).to_have_text("Active")

    page.locator('#lang-container .lang-btn[data-lang="zh-CN"]').click()
    expect(page.locator("h1")).to_have_text("任务跟踪器")
    expect(page.locator("#currentFilterLabel")).to_have_text("进行中")
    page.keyboard.press("Escape")


def exercise_filters_and_sort(page: Page, alpha_name: str, beta_name: str) -> None:
    select_filter(page, "all")
    select_sort(page, "alpha-asc")
    assert_task_order(page, [alpha_name, beta_name])

    select_filter(page, "no-deadline")
    expect(task_locator(page, alpha_name)).to_have_count(1)
    expect(task_locator(page, beta_name)).to_have_count(0)

    select_filter(page, "all")


def complete_task(page: Page, task_name: str) -> None:
    task_locator(page, task_name).first.locator('[data-action="toggle"]').click()
    select_filter(page, "completed")
    expect(task_locator(page, task_name)).to_have_count(1)


def clear_completed_tasks(page: Page, completed_name: str) -> None:
    page.locator("#openMenuBtn").click()
    page.locator("#clearCompletedBtn").click()
    expect(page.locator("#taskModal")).to_be_visible()
    page.locator("#submitBtn").click()
    expect(task_locator(page, completed_name)).to_have_count(0)


def exercise_export(page: Page) -> dict[str, Any]:
    page.locator("#openMenuBtn").click()
    with page.expect_download() as download_info:
        page.locator("#exportBtn").click()
    download = download_info.value
    path = download.path()
    if not path:
        raise AssertionError("Export did not produce a readable download file")

    exported = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(exported.get("tasks"), list) or not exported["tasks"]:
        raise AssertionError(f"Export payload did not include tasks: {exported}")
    return exported


def exercise_import(page: Page, imported_name: str) -> None:
    payload = {
        "version": "1.0",
        "date": "2026-05-10T00:00:00.000Z",
        "tasks": [
            {
                "id": 10001,
                "name": imported_name,
                "description": "Imported by Playwright smoke test.",
                "dueDate": None,
                "createdAt": "2026-05-10T00:00:00.000Z",
                "completed": False,
                "order": 1000,
                "subtasks": [
                    {"id": 20001, "text": "Imported subtask", "completed": False}
                ],
            }
        ],
    }

    with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as temp_file:
        json.dump(payload, temp_file)
        temp_path = temp_file.name

    try:
        page.set_input_files("#importFile", temp_path)
        expect(page.locator("#taskModal")).to_be_visible()
        page.locator("#submitBtn").click()
        select_filter(page, "all")
        expect(task_locator(page, imported_name)).to_have_count(1)
        expect(page.locator(".task-item")).to_have_count(1)
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


def smoke(url: str) -> None:
    errors: list[str] = []
    console_errors: list[str] = []
    bad_resources: list[str] = []
    failed_requests: list[str] = []
    task_name = f"Smoke Task {int(time.time())}"
    alpha_name = f"{task_name} Alpha"
    alpha_edited = f"{task_name} Alpha Edited"
    beta_name = f"{task_name} Beta"
    imported_name = f"{task_name} Imported"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
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

        exercise_theme(page)
        exercise_language(page)

        add_task(page, alpha_name, no_deadline=True, subtasks=["First smoke subtask", "Second smoke subtask"])
        add_task(page, beta_name)
        exercise_subtasks(page, alpha_name)

        edit_task(page, alpha_name, alpha_edited)
        search_task(page, alpha_edited)
        clear_search(page)

        exercise_filters_and_sort(page, alpha_edited, beta_name)
        complete_task(page, alpha_edited)
        select_filter(page, "active")
        expect(task_locator(page, beta_name)).to_have_count(1)
        clear_completed_tasks(page, alpha_edited)

        select_filter(page, "all")
        expect(task_locator(page, beta_name)).to_have_count(1)
        exported = exercise_export(page)
        if exported["tasks"][0]["name"] != beta_name:
            raise AssertionError(f"Exported task did not match remaining task: {exported}")

        exercise_import(page, imported_name)
        delete_task(page, imported_name)

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
