#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, expect, sync_playwright

from smoke_playwright import (
    add_task,
    assert_accessibility_baseline,
    clear_app_data,
    ensure_conda_library_path,
    future_date,
    local_server,
    select_view,
    wait_for_app_ready,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def find_axe_source() -> Path:
    candidates = [
        REPO_ROOT / "node_modules" / "axe-core" / "axe.min.js",
        *Path.home().glob(".npm/_npx/*/node_modules/axe-core/axe.min.js"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate

    subprocess.run(
        ["npx", "--yes", "@axe-core/cli", "--version"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for candidate in [REPO_ROOT / "node_modules" / "axe-core" / "axe.min.js", *Path.home().glob(".npm/_npx/*/node_modules/axe-core/axe.min.js")]:
        if candidate.is_file():
            return candidate
    raise AssertionError("axe-core source was not found after npx bootstrap")


def inject_axe(page: Page, axe_source: str) -> None:
    page.add_script_tag(content=axe_source)


def run_axe(page: Page, axe_source: str, label: str) -> None:
    inject_axe(page, axe_source)
    results: dict[str, Any] = page.evaluate(
        """async () => {
            return await axe.run(document, {
                runOnly: {
                    type: 'tag',
                    values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice']
                }
            });
        }"""
    )
    violations = results.get("violations", [])
    serious = [
        violation for violation in violations
        if violation.get("impact") in {"critical", "serious", "moderate"}
    ]
    if serious:
        compact = [
            {
                "id": item.get("id"),
                "impact": item.get("impact"),
                "help": item.get("help"),
                "nodes": [node.get("target") for node in item.get("nodes", [])[:4]],
            }
            for item in serious
        ]
        raise AssertionError(f"axe violations during {label}:\n{json.dumps(compact, ensure_ascii=False, indent=2)}")


def assert_focus_visible(page: Page, selector: str, label: str) -> None:
    page.locator(selector).focus()
    visible = page.evaluate(
        """() => {
            const el = document.activeElement;
            const style = getComputedStyle(el);
            const outline = Number.parseFloat(style.outlineWidth || '0');
            const boxShadow = style.boxShadow && style.boxShadow !== 'none';
            return outline > 0 || boxShadow;
        }"""
    )
    if not visible:
        raise AssertionError(f"Focused control has no visible focus treatment: {label}")


def assert_focus_baseline(page: Page, label: str) -> None:
    selectors = ["#taskName", "#cancelBtn", "#submitBtn"] if page.locator("#taskModal").is_visible() else [
        "#openModalBtn",
        "#searchInput",
        "#filterBtn",
        "#sortBtn",
        '#viewSwitcher .view-tab[aria-selected="true"]',
    ]
    for selector in selectors:
        locator = page.locator(selector).first
        if locator.count() and locator.is_visible() and locator.is_enabled():
            assert_focus_visible(page, selector, label)


def assert_layout(page: Page, label: str) -> None:
    metrics = page.evaluate(
        """() => {
            const doc = document.documentElement;
            const viewportWidth = window.innerWidth;
            const visibleControls = [...document.querySelectorAll('button:not([hidden]), input:not([type="hidden"]), select, textarea, a[href]')]
                .filter((el) => {
                    const rect = el.getBoundingClientRect();
                    const style = getComputedStyle(el);
                    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
                })
                .map((el) => {
                    const rect = el.getBoundingClientRect();
                    return {
                        tag: el.tagName.toLowerCase(),
                        id: el.id,
                        className: typeof el.className === 'string' ? el.className : '',
                        width: rect.width,
                        height: rect.height,
                        left: rect.left,
                        right: rect.right
                    };
                });
            return {
                viewportWidth,
                scrollWidth: doc.scrollWidth,
                smallControls: visibleControls.filter((item) => item.width < 24 || item.height < 24),
                overflowingControls: visibleControls.filter((item) => item.left < -1 || item.right > viewportWidth + 1)
            };
        }"""
    )
    if metrics["scrollWidth"] - metrics["viewportWidth"] > 1:
        raise AssertionError(f"{label} has horizontal overflow: {metrics}")
    if metrics["smallControls"]:
        raise AssertionError(f"{label} has undersized controls: {metrics['smallControls'][:8]}")
    if metrics["overflowingControls"]:
        raise AssertionError(f"{label} has controls outside viewport: {metrics['overflowingControls'][:8]}")


def switch_to_english(page: Page) -> None:
    page.locator("#openMenuBtn").click()
    page.locator("#langMenuToggle").click()
    page.locator('#lang-container .lang-btn[data-lang="en"]').click()
    expect(page.locator("html")).to_have_attribute("lang", "en")
    page.keyboard.press("Escape")


def audit_page_state(page: Page, axe_source: str, label: str) -> None:
    assert_accessibility_baseline(page, label)
    run_axe(page, axe_source, label)
    assert_focus_baseline(page, label)
    assert_layout(page, label)


def seed_tasks(page: Page) -> None:
    stamp = int(time.time())
    add_task(page, f"A11y Audit No Deadline {stamp}", no_deadline=True, project="Audit Project", tags=["keyboard", "screen reader"])
    add_task(
        page,
        f"A11y Audit Deadline {stamp}",
        due_date=future_date(1),
        due_time="12:30",
        reminder_offset="15",
        project="Audit Project",
        tags=["deadline"],
        subtasks=["Review focus order", "Check translation length"],
    )


def audit_context(url: str, axe_source: str, reduced_motion: bool = False) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            reduced_motion="reduce" if reduced_motion else "no-preference",
            viewport={"width": 390, "height": 844} if reduced_motion else {"width": 1280, "height": 720},
        )
        page = context.new_page()
        clear_app_data(page, url)
        audit_page_state(page, axe_source, "empty task list")
        seed_tasks(page)
        audit_page_state(page, axe_source, "task list")

        page.locator("#openModalBtn").click()
        expect(page.locator("#taskModal")).to_be_visible()
        audit_page_state(page, axe_source, "task modal")
        page.locator("#cancelBtn").click()

        select_view(page, "calendar")
        audit_page_state(page, axe_source, "calendar view")
        select_view(page, "stats")
        audit_page_state(page, axe_source, "stats view")

        switch_to_english(page)
        select_view(page, "list")
        audit_page_state(page, axe_source, "english task list")

        context.close()
        browser.close()


def main() -> int:
    ensure_conda_library_path()
    axe_source = find_axe_source().read_text(encoding="utf-8")
    url = os.environ.get("TASK_TRACER_URL")
    if url:
        audit_context(url, axe_source)
        audit_context(url, axe_source, reduced_motion=True)
    else:
        with local_server() as local_url:
            audit_context(local_url, axe_source)
            audit_context(local_url, axe_source, reduced_motion=True)
    print("Accessibility/i18n audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
