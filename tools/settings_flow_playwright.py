#!/usr/bin/env python3
"""Check settings choices and recovery consent through a small real UI flow."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import uuid
from pathlib import Path
import threading
import time
import traceback

from playwright.sync_api import expect, sync_playwright

from security_playwright import ProductionHeaderHandler
from smoke_playwright import (
    ThreadingHTTPServer,
    browser_launch_options,
    delete_task,
    open_settings,
    return_to_task_workspace,
    wait_for_app_ready,
)


REPO = Path(__file__).resolve().parents[1]


def fingerprint() -> dict[str, str]:
    names = ["index.html", "sw.js", "vercel.json", "resources/en.json", "resources/zh-CN.json"]
    return {name: hashlib.sha256((REPO / name).read_bytes()).hexdigest() for name in names}


def stored(page):
    return page.evaluate("""() => new Promise((resolve, reject) => {
      const request = indexedDB.open('TaskTrackerDB', 2);
      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        const db = request.result;
        const tx = db.transaction(['tasks', 'config'], 'readonly');
        const tasks = tx.objectStore('tasks').getAll();
        const config = tx.objectStore('config').getAll();
        tx.oncomplete = () => {db.close(); resolve({tasks:tasks.result,config:config.result});};
        tx.onerror = () => reject(tx.error);
        tx.onabort = () => reject(tx.error);
      };
    })""")


def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def capture(page, path):
    page.wait_for_function("""() => document.getAnimations().every(a =>
      a.playState !== 'running' || a.effect?.getComputedTiming().iterations === Infinity)""")
    page.screenshot(path=str(path), animations="allow")


def quick_task(page, text):
    return_to_task_workspace(page)
    if not page.locator("#quickAddInput").is_visible():
        page.locator("#quickCaptureBtn").click()
    page.locator("#quickAddInput").fill(text)
    page.locator("#quickAddInput").press("Enter")
    expect(page.locator("#quickAddInput")).to_have_value("")
    page.locator("#quickCaptureBtn").click()


def settings_order_and_names(page):
    open_settings(page, "appearance")
    page.locator("#languageSelect").select_option("zh-CN")
    expect(page.locator("html")).to_have_attribute("lang", "zh-CN")
    page.locator("#languageSelect").select_option("en")
    expect(page.locator("html")).to_have_attribute("lang", "en")
    for selector in ["#themeToggleBtn", "#languageSelect"]:
        expect(page.locator(selector)).to_have_attribute("data-native-select", "")
        assert page.locator(selector).evaluate("node => node.tagName === 'SELECT'")
    geometry = page.evaluate("""() => {
      const rect = s => {const r=document.querySelector(s).getBoundingClientRect();
        return {top:r.top,bottom:r.bottom};};
      return {preferences:rect('.settings-preferences'),gallery:rect('#workspaceThemeChoices'),
        language:rect('#languageSelect'),viewport:innerHeight};
    }""")
    assert geometry["preferences"]["bottom"] <= geometry["gallery"]["top"], geometry
    assert 0 <= geometry["language"]["top"] < geometry["language"]["bottom"] <= geometry["viewport"], geometry
    open_settings(page, "cleanup")
    assert page.locator("#settingsCleanupTitle").evaluate("""heading => Boolean(
      heading.compareDocumentPosition(document.querySelector('#maintenanceStatus')) & Node.DOCUMENT_POSITION_FOLLOWING
    )"""), "Maintenance status precedes its heading"
    expect(page.locator("#archiveCompletedBtn")).to_be_disabled()
    expect(page.locator("#clearCompletedBtn")).to_be_disabled()
    open_settings(page, "data")
    label = json.loads((REPO / "resources/en.json").read_text())["settingsRefinement"]["storageTitle"]
    expect(page.locator('[data-i18n="settingsRefinement.storageTitle"]')).to_have_text(label)
    page.locator("#storageHealthBtn").click()
    expect(page.locator("#storagePersistenceStatus")).to_be_visible()
    expect(page.locator("#modalTitle")).to_have_text(label)
    page.locator("#cancelBtn").click()
    return geometry


def import_modes(page, out):
    geometry = settings_order_and_names(page)
    quick_task(page, "Settings import Alpha /Work")
    quick_task(page, "Settings import Beta /Work")
    open_settings(page, "data")
    with page.expect_download() as result:
        page.locator("#backupBtn").click()
    backup = out / result.value.suggested_filename
    result.value.save_as(str(backup))
    assert len(json.loads(backup.read_text())["tasks"]) == 2
    quick_task(page, "Settings current Gamma /Personal")
    open_settings(page, "data")
    before = stored(page)
    save_json(out / "before-preview.json", before)
    page.locator("#importFile").set_input_files(str(backup))
    merge = page.locator("#mergeImportMode")
    replace = page.locator("#replaceImportMode")
    expect(merge).to_have_attribute("type", "radio")
    expect(replace).to_have_attribute("type", "radio")
    assert merge.get_attribute("name") and merge.get_attribute("name") == replace.get_attribute("name")
    expect(merge).not_to_be_checked()
    expect(replace).to_be_checked()
    t = json.loads((REPO / "resources/en.json").read_text())
    replacement = t["dataReview"]["replaceSummary"].format(current=3, incoming=2, after=2)
    merged = t["dataReview"]["mergeSummary"].format(added=2, replaced=0, skipped=0, kept=3, after=5)
    expect(page.locator("#importOutcomeSummary")).to_have_text(replacement)
    expect(page.locator("#submitBtn")).to_have_text(t["messages"]["import"]["downloadSnapshot"])
    capture(page, out / "01-replace-default.png")
    merge.check()
    expect(replace).not_to_be_checked()
    expect(page.locator("#importOutcomeSummary")).to_have_text(merged)
    expect(page.locator("#importConflictDefaultAction")).to_be_enabled()
    expect(page.locator("#importReplaceHint")).to_be_hidden()
    replace.check()
    expect(merge).not_to_be_checked()
    expect(page.locator("#importOutcomeSummary")).to_have_text(replacement)
    expect(page.locator("#importConflictDefaultAction")).to_be_disabled()
    expect(page.locator("#importReplaceHint")).to_be_visible()
    expect(page.locator("#submitBtn")).to_have_text(t["messages"]["import"]["downloadSnapshot"])
    merge.check()
    expect(page.locator("#importOutcomeSummary")).to_have_text(merged)
    capture(page, out / "02-merge-outcome.png")
    page.locator("#cancelBtn").click()
    after = stored(page)
    save_json(out / "after-preview.json", after)
    assert after == before, "Reviewing import modes wrote task or configuration data"
    return {"preferences_geometry": geometry, "current": 3, "incoming": 2,
            "replace_after": 2, "merge_after": 5, "preview_no_database_writes": True}


def recovery_consent(page, out):
    quick_task(page, "Settings recovery first /Work")
    quick_task(page, "Settings recovery second /Personal")
    expected = stored(page)["tasks"]
    delete_task(page, "Settings recovery second")
    delete_task(page, "Settings recovery first")
    quick_task(page, "Settings current-only /Current")
    before = stored(page)
    save_json(out / "before-recovery.json", before)
    history = next(item["value"] for item in before["config"] if item["key"] == "recoveryHistory")
    matching = next(item for item in history if item["tasks"] == expected)
    alternative = next(item for item in history if item["id"] != matching["id"])
    open_settings(page, "data")
    page.locator("#recoveryBtn").click()
    page.locator("#recoverySelect").select_option(str(matching["id"]), force=True)
    expect(page.locator("#recoveryConfirm")).not_to_be_checked()
    expect(page.locator("#submitBtn")).to_be_disabled()
    expect(page.locator("#submitBtn")).to_have_attribute("aria-disabled", "true")
    expect(page.locator("#recoveryPreviewDetails")).to_have_js_property("open", False)
    assert page.locator("#recoveryConfirm").evaluate("""node => {
      const r=node.getBoundingClientRect();const body=node.closest('#confirm-message-text').getBoundingClientRect();
      return r.width>0 && r.height>0 && r.top>=body.top && r.bottom<=body.bottom && r.top>=0 && r.bottom<=innerHeight;
    }"""), "Required recovery consent is outside the initial visible content"
    page.wait_for_timeout(150)
    assert stored(page) == before, "Unconfirmed recovery review wrote tasks or configuration"
    capture(page, out / "01-unchecked-disabled.png")
    page.locator("#recoveryConfirm").check()
    expect(page.locator("#submitBtn")).to_be_enabled()
    expect(page.locator("#submitBtn")).to_have_attribute("aria-disabled", "false")
    page.locator("#recoverySelect").select_option(str(alternative["id"]), force=True)
    expect(page.locator("#recoveryConfirm")).not_to_be_checked()
    expect(page.locator("#submitBtn")).to_be_disabled()
    expect(page.locator("#submitBtn")).to_have_attribute("aria-disabled", "true")
    assert stored(page) == before, "Changing the recovery point wrote task or configuration data"
    page.locator("#recoverySelect").select_option(str(matching["id"]), force=True)
    page.locator("#recoveryConfirm").check()
    page.locator("#submitBtn").click()
    expect(page.locator("#taskModal")).to_be_hidden()
    after = stored(page)
    save_json(out / "after-recovery.json", after)
    assert after["tasks"] == expected, "Confirmed recovery did not restore exactly the selected task records"
    new_history = next(item["value"] for item in after["config"] if item["key"] == "recoveryHistory")
    assert any(item["tasks"] == before["tasks"] for item in new_history), "Recovery lost the state it replaced"
    expect(page.locator("#undoBtn")).to_be_disabled()
    page.locator("#openModalBtn").click()
    expect(page.locator("#submitBtn")).to_be_enabled()
    assert page.locator("#submitBtn").get_attribute("aria-disabled") != "true", "Recovery consent ARIA leaked into a new editor"
    page.locator("#cancelBtn").click()
    return_to_task_workspace(page)
    capture(page, out / "02-restored-exact-records.png")
    return {"unconfirmed_no_database_writes": True, "point_change_resets_consent": True,
            "selected_tasks_restored_exactly": len(expected), "replaced_tasks_checkpointed": len(before["tasks"]),
            "new_editor_not_disabled": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(tempfile.gettempdir()) / "task-tracer-settings-flow" / uuid.uuid4().hex)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    before = fingerprint()
    report = {"kind": "targeted-settings-ui-flow", "source_before": before, "runs": [],
              "tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "helper_sha256": {name: hashlib.sha256((REPO / "tools" / name).read_bytes()).hexdigest()
                                for name in ["smoke_playwright.py", "security_playwright.py"]},
              "normal_motion": True, "production_csp": True, "screenshots_manually_reviewed": False}
    server = ThreadingHTTPServer(("127.0.0.1", 0), ProductionHeaderHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(**browser_launch_options())
            report["browser"] = {"engine": "chromium", "version": browser.version}
            try:
                for width, height in [(1440, 1000), (390, 844)]:
                    for name, check in [("import-modes-and-settings", import_modes), ("recovery-consent", recovery_consent)]:
                        folder = args.output / f"{width}-{name}"
                        folder.mkdir(exist_ok=True)
                        context = browser.new_context(viewport={"width": width, "height": height},
                                                      locale="en", timezone_id="Asia/Shanghai",
                                                      reduced_motion="no-preference", accept_downloads=True)
                        page = context.new_page()
                        page.set_default_timeout(7000)
                        errors = []
                        page.on("pageerror", lambda error: errors.append(str(error)))
                        run = {"width": width, "height": height, "case": name, "page_errors": errors}
                        started = time.monotonic()
                        try:
                            response = page.goto(f"http://127.0.0.1:{server.server_port}/", wait_until="networkidle")
                            assert response.status == 200
                            assert hashlib.sha256(response.body()).hexdigest() == before["index.html"]
                            assert response.header_value("content-security-policy")
                            wait_for_app_ready(page)
                            run["checks"] = check(page, folder)
                            assert not errors, errors
                            run["passed"] = True
                        except Exception:
                            run["passed"] = False
                            run["error"] = traceback.format_exc()
                            page.screenshot(path=str(folder / "failure.png"), animations="allow")
                        finally:
                            run["seconds"] = round(time.monotonic() - started, 3)
                            report["runs"].append(run)
                            context.close()
            finally:
                browser.close()
                report["browser_closed"] = True
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        report["server_closed"] = True
        report["source_after"] = fingerprint()
        report["source_unchanged"] = report["source_after"] == before
        report["passed"] = len(report["runs"]) == 4 and all(run["passed"] for run in report["runs"]) and report["source_unchanged"]
        save_json(args.output / "report.json", report)
        print(json.dumps({"passed": report["passed"], "runs": len(report["runs"]), "report": str(args.output / "report.json")}), flush=True)
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
