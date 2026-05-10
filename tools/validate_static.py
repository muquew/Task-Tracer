#!/usr/bin/env python3
"""Static consistency checks for the Task Tracer PWA."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = REPO_ROOT / "index.html"
MANIFEST_PATH = REPO_ROOT / "manifest.json"
SW_PATH = REPO_ROOT / "sw.js"
RESOURCE_DIR = REPO_ROOT / "resources"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> Any:
    try:
        return json.loads(read_text(path))
    except json.JSONDecodeError as error:
        raise AssertionError(f"{path.relative_to(REPO_ROOT)} is not valid JSON: {error}") from error


def flatten_translations(source: dict[str, Any], prefix: str = "") -> dict[str, str]:
    flattened: dict[str, str] = {}
    for key, value in source.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flattened.update(flatten_translations(value, path))
        elif isinstance(value, str):
            flattened[path] = value
        else:
            raise AssertionError(f"Translation value {path!r} must be a string, got {type(value).__name__}")
    return flattened


def first_match(pattern: str, source: str, label: str) -> re.Match[str]:
    match = re.search(pattern, source, re.DOTALL)
    if not match:
        raise AssertionError(f"Could not find {label}")
    return match


def configured_languages(index_html: str) -> list[str]:
    block = first_match(r"LANGUAGES:\s*\[(.*?)\]", index_html, "CONFIG.LANGUAGES").group(1)
    codes = re.findall(r"code:\s*['\"]([^'\"]+)['\"]", block)
    if not codes:
        raise AssertionError("CONFIG.LANGUAGES has no language codes")
    return codes


def default_language(index_html: str) -> str:
    block = first_match(r"DEFAULTS:\s*{(.*?)}", index_html, "CONFIG.DEFAULTS").group(1)
    return first_match(r"LANG:\s*['\"]([^'\"]+)['\"]", block, "CONFIG.DEFAULTS.LANG").group(1)


def resource_version(index_html: str) -> str:
    block = first_match(r"I18N:\s*{(.*?)}", index_html, "CONFIG.I18N").group(1)
    return first_match(r"RESOURCE_VERSION:\s*['\"]([^'\"]+)['\"]", block, "CONFIG.I18N.RESOURCE_VERSION").group(1)


def translation_references(index_html: str) -> set[str]:
    references = set(re.findall(r"data-i18n(?:-[\w-]+)?=['\"]([^'\"]+)['\"]", index_html))
    references.update(re.findall(r"translate\(\s*['\"]([A-Za-z0-9_.-]+)['\"]", index_html))
    references.update(re.findall(r"\[\s*['\"]([A-Za-z0-9_.-]+\.[A-Za-z0-9_.-]+)['\"]\s*\]", index_html))
    return references


def tag_blocks(source: str, tag: str) -> list[str]:
    return re.findall(rf"<{tag}\b[^>]*>(.*?)</{tag}>", source, re.DOTALL | re.IGNORECASE)


def contains_js_comment(source: str) -> bool:
    state = "normal"
    escape = False
    i = 0
    while i < len(source):
        char = source[i]
        next_char = source[i + 1] if i + 1 < len(source) else ""
        if state == "normal":
            if char == "/" and next_char in {"/", "*"}:
                return True
            if char in {"'", '"', "`"}:
                state = char
                escape = False
            i += 1
            continue
        if escape:
            escape = False
        elif char == "\\":
            escape = True
        elif char == state:
            state = "normal"
        i += 1
    return False


def contains_css_comment(source: str) -> bool:
    state = "normal"
    escape = False
    i = 0
    while i < len(source):
        char = source[i]
        next_char = source[i + 1] if i + 1 < len(source) else ""
        if state == "normal":
            if char == "/" and next_char == "*":
                return True
            if char in {"'", '"'}:
                state = char
                escape = False
            i += 1
            continue
        if escape:
            escape = False
        elif char == "\\":
            escape = True
        elif char == state:
            state = "normal"
        i += 1
    return False


def validate_translations(index_html: str, errors: list[str]) -> None:
    try:
        languages = configured_languages(index_html)
        default_lang = default_language(index_html)
        resource_files = {path.stem: path for path in RESOURCE_DIR.glob("*.json")}

        missing_files = [code for code in languages if code not in resource_files]
        extra_files = sorted(set(resource_files) - set(languages))
        if missing_files:
            errors.append(f"Missing language resource files for: {', '.join(missing_files)}")
        if extra_files:
            errors.append(f"Language resource files are not configured: {', '.join(extra_files)}")

        flattened = {
            code: flatten_translations(load_json(resource_files[code]))
            for code in languages
            if code in resource_files
        }
        if default_lang not in flattened:
            errors.append(f"Default language {default_lang!r} has no resource file")
            return

        base_keys = set(flattened[default_lang])
        for code, values in flattened.items():
            keys = set(values)
            missing = sorted(base_keys - keys)
            extra = sorted(keys - base_keys)
            if missing or extra:
                errors.append(
                    f"{code} translation keys differ from {default_lang}: "
                    f"missing={missing[:8]} extra={extra[:8]}"
                )

        unknown_refs = sorted(translation_references(index_html) - base_keys)
        if unknown_refs:
            errors.append(f"Unknown i18n references in index.html: {unknown_refs[:12]}")
    except AssertionError as error:
        errors.append(str(error))


def service_worker_assets(sw_source: str) -> set[str]:
    block = first_match(r"ASSETS_TO_CACHE\s*=\s*\[(.*?)\]", sw_source, "ASSETS_TO_CACHE").group(1)
    return set(re.findall(r"['\"]([^'\"]+)['\"]", block))


def manifest_icon_paths(manifest: dict[str, Any]) -> list[str]:
    icons = manifest.get("icons")
    if not isinstance(icons, list) or not icons:
        raise AssertionError("manifest.json must define at least one icon")
    paths: list[str] = []
    for icon in icons:
        if not isinstance(icon, dict) or not isinstance(icon.get("src"), str):
            raise AssertionError("manifest.json icons must include string src values")
        paths.append(icon["src"])
    return paths


def validate_pwa(index_html: str, errors: list[str]) -> None:
    try:
        sw_source = read_text(SW_PATH)
        manifest = load_json(MANIFEST_PATH)
        languages = configured_languages(index_html)
        version = resource_version(index_html)
        assets = service_worker_assets(sw_source)

        required_assets = {"./", "./index.html", "./manifest.json"}
        required_assets.update(f"./resources/{code}.json?v={version}" for code in languages)
        for icon_path in manifest_icon_paths(manifest):
            icon_file = REPO_ROOT / icon_path
            if not icon_file.is_file():
                errors.append(f"Manifest icon is missing: {icon_path}")
            required_assets.add(f"./{icon_path}")

        missing_assets = sorted(required_assets - assets)
        if missing_assets:
            errors.append(f"Service worker does not precache required assets: {missing_assets}")

        if not re.search(r"const CACHE_NAME = ['\"]task-tracer-v\d+\.\d+['\"]", sw_source):
            errors.append("Service worker cache name must be versioned as task-tracer-v<major>.<minor>")
        if "networkFirst(e.request, './index.html')" not in sw_source:
            errors.append("App shell requests must use networkFirst with an index.html fallback")
        if "url.pathname.includes('/resources/')" not in sw_source:
            errors.append("Language resources must have an explicit service worker fetch strategy")
        if "cacheFirst(e.request)" not in sw_source:
            errors.append("Static assets should keep a cacheFirst fallback strategy")
    except AssertionError as error:
        errors.append(str(error))


def validate_loaded_code_is_comment_free(index_html: str, errors: list[str]) -> None:
    sw_source = read_text(SW_PATH)
    if "<!--" in index_html:
        errors.append("Loaded index.html must not contain HTML comments")
    if any(contains_css_comment(block) for block in tag_blocks(index_html, "style")):
        errors.append("Loaded index.html style blocks must not contain CSS comments")
    if any(contains_js_comment(block) for block in tag_blocks(index_html, "script")):
        errors.append("Loaded index.html script blocks must not contain JavaScript comments")
    if contains_js_comment(sw_source):
        errors.append("Loaded sw.js must not contain JavaScript comments")


def validate_task_state_styles(index_html: str, errors: list[str]) -> None:
    try:
        status_block = first_match(
            r"STATUS:\s*{(.*?)}\s*,\s*THEME:",
            index_html,
            "CONFIG.UI.STATUS",
        ).group(1)
        status_classes = set(re.findall(r"['\"](status-[^'\"]+)['\"]", status_block))
        active_statuses = status_classes - {"status-completed"}

        for status_class in sorted(active_statuses):
            if f".task-item.{status_class}" not in index_html:
                errors.append(f"Missing task status CSS selector for {status_class}")

        if "completed-task" not in index_html:
            errors.append("Completed tasks must render the completed-task class")
        if not re.search(
            r"\.completed-task\s+\.task-name\s*{[^}]*text-decoration-line:\s*line-through",
            index_html,
            re.DOTALL,
        ):
            errors.append("Completed task names must be struck through with text-decoration-line: line-through")
        if "document.querySelectorAll('.task-item:not(.completed-task)')" not in index_html:
            errors.append("Timer refresh should skip completed tasks")
    except AssertionError as error:
        errors.append(str(error))


def validate_accessibility_styles(index_html: str, errors: list[str]) -> None:
    if ":focus-visible" not in index_html or "--focus-ring" not in index_html:
        errors.append("Interactive controls must expose a visible keyboard focus style")
    if "@media (prefers-reduced-motion: reduce)" not in index_html:
        errors.append("CSS must respect prefers-reduced-motion")
    if "setButtonLabel(toggleButton," not in index_html or "renderTaskToggleButton(toggleButton" not in index_html:
        errors.append("Task action icon buttons must receive accessible labels")
    if "summaryBar.setAttribute('aria-expanded'" not in index_html:
        errors.append("Subtask expand controls must expose aria-expanded")
    if 'aria-controls="filterMenu"' not in index_html or 'aria-controls="sortMenu"' not in index_html:
        errors.append("Dropdown triggers must expose aria-controls for their menus")
    if 'id="filterMenu" role="listbox" aria-labelledby="filterBtn"' not in index_html:
        errors.append("Filter dropdown must expose a labelled listbox menu")
    if 'id="sortMenu" role="listbox" aria-labelledby="sortBtn"' not in index_html:
        errors.append("Sort dropdown must expose a labelled listbox menu")
    if 'role="option" aria-selected=' not in index_html or "option.setAttribute('aria-selected'" not in index_html:
        errors.append("Dropdown options must expose and synchronize aria-selected")
    if re.search(r"<label\b[^>]*for=['\"][^'\"]+['\"][^>]*>\s*</label>", index_html, re.DOTALL):
        errors.append("Form labels must not be empty")
    if '<html lang="zh-CN" dir="ltr">' not in index_html or "document.documentElement.dir = getLanguageDirection" not in index_html:
        errors.append("Document language and direction must be initialized and synchronized")
    if 'data-i18n-aria-label="app.toolbar"' not in index_html:
        errors.append("Toolbar accessible label must be localized")
    if '<title data-i18n="app.title">' not in index_html:
        errors.append("Document title must be localized")
    if 'aria-controls="langSubmenu"' not in index_html or "setAttribute('role', 'menuitemradio')" not in index_html:
        errors.append("Language menu must expose submenu controls and checked language state")
    if "DOM.modal.setAttribute('aria-describedby', 'confirm-message-text')" not in index_html:
        errors.append("Confirmation dialogs must expose aria-describedby")
    if 'id="srStatus" class="sr-only" aria-live="polite" aria-atomic="true"' not in index_html:
        errors.append("Keyboard-only status updates must use a screen-reader live region")
    if "handleTaskReorderKeydown" not in index_html or "task.actions.reorder" not in index_html:
        errors.append("Manual task ordering must support keyboard reordering")


def main() -> int:
    errors: list[str] = []
    index_html = read_text(INDEX_PATH)

    validate_translations(index_html, errors)
    validate_pwa(index_html, errors)
    validate_loaded_code_is_comment_free(index_html, errors)
    validate_task_state_styles(index_html, errors)
    validate_accessibility_styles(index_html, errors)

    if errors:
        print("Static validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Static validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
