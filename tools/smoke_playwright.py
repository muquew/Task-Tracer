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
import os
import socket
import socketserver
import sys
import threading
import time
from pathlib import Path
from typing import Iterator
from urllib.parse import urlparse

from playwright.sync_api import Page, TimeoutError, expect, sync_playwright


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


def add_task(page: Page, task_name: str) -> None:
    page.locator("#openModalBtn").click()
    expect(page.locator("#taskModal")).to_be_visible()
    page.locator("#taskName").fill(task_name)
    page.locator("#taskDesc").fill("Created by Playwright smoke test.")
    page.locator("#submitBtn").click()

    task = page.locator(".task-item").filter(has_text=task_name)
    expect(task).to_have_count(1)
    expect(task.first.locator(".task-name")).to_contain_text(task_name)


def search_task(page: Page, task_name: str) -> None:
    page.locator("#searchInput").fill(task_name)
    task = page.locator(".task-item").filter(has_text=task_name)
    expect(task).to_have_count(1)


def delete_task(page: Page, task_name: str) -> None:
    task = page.locator(".task-item").filter(has_text=task_name)
    task.first.locator('[data-action="delete"]').click()
    expect(page.locator("#taskModal")).to_be_visible()
    page.locator("#submitBtn").click()
    expect(task).to_have_count(0)


def smoke(url: str) -> None:
    errors: list[str] = []
    console_errors: list[str] = []
    bad_resources: list[str] = []
    failed_requests: list[str] = []
    task_name = f"Smoke Task {int(time.time())}"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context()
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
            lambda request: failed_requests.append(
                f"{request.failure['errorText']} {request.url}"
            )
            if request.failure and not is_ignored_resource(request.url)
            else None,
        )

        page.goto(url, wait_until="domcontentloaded")
        expect(page.locator("#openModalBtn")).to_be_visible()
        page.locator("#taskList .loading-state").wait_for(state="detached", timeout=10_000)
        page.locator("#taskList").wait_for(state="visible")

        add_task(page, task_name)
        search_task(page, task_name)
        delete_task(page, task_name)

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
