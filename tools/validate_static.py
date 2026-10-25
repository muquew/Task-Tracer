#!/usr/bin/env python3
"""Static consistency checks for the Task Tracer PWA."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from translation_fallback import check as check_translation_fallback, main_script


REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = REPO_ROOT / "index.html"
MANIFEST_PATH = REPO_ROOT / "manifest.json"
SW_PATH = REPO_ROOT / "sw.js"
RESOURCE_DIR = REPO_ROOT / "resources"
VERCEL_PATH = REPO_ROOT / "vercel.json"
ROBOTS_PATH = REPO_ROOT / "robots.txt"
SITEMAP_PATH = REPO_ROOT / "sitemap.xml"
SEO_URL = "https://todo.muquew.com/"
SEO_DESCRIPTION = "Task Tracer is a local-first PWA for tasks, routines, reminders, calendar planning, statistics, import/export backups, and offline use."


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
    runtime = main_script(index_html).group('content')
    block = first_match(r"LANGUAGES:\s*\[(.*?)\]", runtime, "CONFIG.LANGUAGES").group(1)
    codes = re.findall(r"code:\s*['\"]([^'\"]+)['\"]", block)
    if not codes:
        raise AssertionError("CONFIG.LANGUAGES has no language codes")
    return codes


def default_language(index_html: str) -> str:
    runtime = main_script(index_html).group('content')
    block = first_match(r"DEFAULTS:\s*{(.*?)}", runtime, "CONFIG.DEFAULTS").group(1)
    return first_match(r"LANG:\s*['\"]([^'\"]+)['\"]", block, "CONFIG.DEFAULTS.LANG").group(1)


def resource_version(index_html: str) -> str:
    runtime = main_script(index_html).group('content')
    block = first_match(r"I18N:\s*{(.*?)}", runtime, "CONFIG.I18N").group(1)
    return first_match(r"RESOURCE_VERSION:\s*['\"]([^'\"]+)['\"]", block, "CONFIG.I18N.RESOURCE_VERSION").group(1)


def app_version(index_html: str) -> str:
    runtime = main_script(index_html).group('content')
    block = first_match(r"APP:\s*{(.*?)}", runtime, "CONFIG.APP").group(1)
    return first_match(r"VERSION:\s*['\"]([^'\"]+)['\"]", block, "CONFIG.APP.VERSION").group(1)


def translation_references(index_html: str) -> set[str]:
    references = set(re.findall(r"data-i18n(?:-[\w-]+)?=['\"]([^'\"]+)['\"]", index_html))
    references.update(re.findall(r"translate\(\s*['\"]([A-Za-z0-9_.-]+)['\"]", index_html))
    references.update(re.findall(r"\[\s*['\"]([A-Za-z0-9_.-]+\.[A-Za-z0-9_.-]+)['\"]\s*\]", index_html))
    return references


def contains_in_order(source: str, fragments: tuple[str, ...]) -> bool:
    position = 0
    for fragment in fragments:
        next_position = source.find(fragment, position)
        if next_position == -1:
            return False
        position = next_position + len(fragment)
    return True


def tag_blocks(source: str, tag: str) -> list[str]:
    return re.findall(rf"<{tag}\b[^>]*>(.*?)</{tag}>", source, re.DOTALL | re.IGNORECASE)


def contains_js_comment(source: str) -> bool:
    expression_start = True
    previous = ''
    parentheses = []
    braces = []
    template_text = False
    interpolations = []
    pending_function = None
    pending_class = None
    function_body = None
    async_expression = False
    control_keywords = {'if', 'while', 'for', 'with', 'switch', 'catch'}
    expression_keywords = {'return', 'throw', 'case', 'delete', 'void', 'typeof', 'new',
                           'in', 'instanceof', 'of', 'yield', 'await', 'else', 'do'}
    i = 0
    while i < len(source):
        char = source[i]
        next_char = source[i + 1] if i + 1 < len(source) else ""
        if template_text:
            if char == '\\':
                i += 2
                continue
            if char == '`':
                template_text = False
                expression_start = False
                previous = 'literal'
            elif char == '$' and next_char == '{':
                interpolations.append(len(braces))
                braces.append(None)
                template_text = False
                expression_start = True
                previous = '{'
                i += 2
                continue
            i += 1
            continue
        if char.isspace():
            i += 1
            continue
        if char == '/' and next_char in {'/', '*'}:
            return True
        if char == '`':
            template_text = True
            i += 1
            continue
        if char in {"'", '"'}:
            quote = char
            i += 1
            while i < len(source):
                if source[i] == '\\':
                    i += 2
                    continue
                if source[i] == quote:
                    i += 1
                    break
                i += 1
            expression_start = False
            previous = 'literal'
            continue
        if char == '/' and expression_start:
            end = i + 1
            character_class = False
            while end < len(source) and source[end] not in '\r\n':
                current = source[end]
                if current == '\\':
                    end += 2
                    continue
                if current == '[':
                    character_class = True
                elif current == ']':
                    character_class = False
                elif current == '/' and not character_class:
                    end += 1
                    while end < len(source) and (source[end].isalnum() or source[end] in '_$'):
                        end += 1
                    i = end
                    expression_start = False
                    previous = 'literal'
                    break
                end += 1
            else:
                i += 1
                previous = '/'
            continue
        if char.isalpha() or char in '_$':
            end = i + 1
            while end < len(source) and (source[end].isalnum() or source[end] in '_$'):
                end += 1
            token = source[i:end]
            property_name = previous in {'.', '?.'}
            if token in {'function', 'class'} and not property_name:
                is_expression = (async_expression if previous == 'async' else expression_start) and previous not in {'', ';', '{', '}', 'export', 'default'}
                if token == 'function':
                    pending_function = (len(parentheses), is_expression)
                else:
                    pending_class = (len(parentheses), is_expression)
            if token == 'async':
                async_expression = expression_start and previous not in {'', ';', '{', '}'}
            expression_start = token in expression_keywords and not property_name
            previous = 'property' if property_name else token
            i = end
            continue
        if char.isdigit():
            i += 1
            while i < len(source) and (source[i].isalnum() or source[i] in '._'):
                i += 1
            expression_start = False
            previous = 'literal'
            continue
        if char == '(':
            function = None
            if pending_function is not None and pending_function[0] == len(parentheses):
                function = pending_function[1]
                pending_function = None
            parentheses.append((previous in control_keywords, function))
            expression_start = True
        elif char == ')':
            expression_start, function_body = parentheses.pop() if parentheses else (False, None)
        elif char == '{':
            block = not expression_start or previous in {'', ';', '{', '}', 'else', 'do', 'try', 'finally', '=>', ')'}
            if function_body is not None:
                block = not function_body
                function_body = None
            elif pending_class is not None and pending_class[0] == len(parentheses):
                block = not pending_class[1]
                pending_class = None
            elif previous == '=>':
                block = False
            braces.append(block)
            expression_start = True
        elif char == '}':
            if interpolations and len(braces) == interpolations[-1] + 1:
                interpolations.pop()
                braces.pop()
                template_text = True
                i += 1
                continue
            expression_start = braces.pop() if braces else True
        elif char == ']':
            expression_start = False
        elif char == '.' and source[i:i + 3] != '...':
            expression_start = False
        elif source[i:i + 2] in {'++', '--'}:
            previous = source[i:i + 2]
            i += 2
            continue
        else:
            expression_start = True
        if source[i:i + 2] in {'=>', '?.'}:
            previous = source[i:i + 2]
            i += 2
            continue
        previous = char
        i += 1
    return False


def validate_due_date_semantics(index_html: str, errors: list[str]) -> None:
    try:
        runtime = main_script(index_html).group('content')
        body = first_match(r'(?m)^([ \t]*)function\s+normalizeDueDateValue\s*\([^)]*\)\s*\{(?P<body>.*?)^\1\}',
                           runtime, 'normalizeDueDateValue').group('body')
        required = ("new Date(`${text}T12:00:00.000Z`)", 'date.getUTCFullYear() !== year',
                    'date.getUTCMonth() !== month - 1', 'date.getUTCDate() !== day')
        if not all(fragment in body for fragment in required):
            errors.append('Due-date normalization must reject rolled-over calendar dates in neutral UTC')
    except AssertionError as error:
        errors.append(str(error))


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
        if "app.subtitle" in base_keys or 'data-i18n="app.subtitle"' in index_html:
            errors.append("The header subtitle must remain removed; app.subtitle should not be used")
    except AssertionError as error:
        errors.append(str(error))


def service_worker_assets(sw_source: str) -> set[str]:
    block = first_match(r"ASSETS_TO_CACHE\s*=\s*\[(.*?)\]", sw_source, "ASSETS_TO_CACHE").group(1)
    return set(re.findall(r"['\"]([^'\"]+)['\"]", block))


def service_worker_cache_name(sw_source: str) -> str:
    return first_match(r"const CACHE_NAME = ['\"]([^'\"]+)['\"]", sw_source, "CACHE_NAME").group(1)


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
        runtime_version = app_version(index_html)
        assets = service_worker_assets(sw_source)
        cache_name = service_worker_cache_name(sw_source)

        if (REPO_ROOT / "fav" / "site.webmanifest").exists():
            errors.append("Use only manifest.json; fav/site.webmanifest must not exist")
        if not re.search(r"<link\s+rel=\"manifest\"\s+id=\"manifestLink\"\s+href=\"\./manifest\.json\"", index_html):
            errors.append("index.html must link the canonical ./manifest.json")
        if "application/manifest+json" in index_html or "__TASK_TRACER_MANIFEST_URL__" in index_html:
            errors.append("Manifest must remain a stable static file, not a runtime blob")
        if re.search(r"<link\s+rel=\"(?:icon|shortcut icon|apple-touch-icon)\"[^>]+href=\"data:", index_html):
            errors.append("Icon links must use stable files instead of data URI fallbacks")

        for key in ("id", "name", "short_name", "description", "start_url", "scope", "display", "theme_color", "background_color"):
            if not manifest.get(key):
                errors.append(f"manifest.json is missing required field: {key}")
        if "orientation" in manifest:
            errors.append("manifest.json must not force a screen orientation")

        required_assets = {"./", "./index.html", "./manifest.json"}
        required_assets.update(f"./resources/{code}.json?v={version}" for code in languages)
        for icon_path in manifest_icon_paths(manifest):
            icon_file = REPO_ROOT / icon_path
            if not icon_file.is_file():
                errors.append(f"Manifest icon is missing: {icon_path}")
            required_assets.add(f"./{icon_path}")

        shortcuts = manifest.get("shortcuts")
        if not isinstance(shortcuts, list) or not shortcuts:
            errors.append("manifest.json must expose a Quick Capture shortcut")
        else:
            quick_capture = next((item for item in shortcuts if isinstance(item, dict) and item.get("url") == "./?capture=1"), None)
            if not quick_capture:
                errors.append("manifest.json shortcuts must include ./?capture=1")
            elif quick_capture.get("name") != "Quick Capture":
                errors.append("Quick Capture shortcut must use the expected name")

        share_target = manifest.get("share_target")
        if not isinstance(share_target, dict):
            errors.append("manifest.json must define share_target")
        else:
            if share_target.get("action") != "./?capture=1" or share_target.get("method") != "GET":
                errors.append("share_target must use GET ./?capture=1")
            if share_target.get("enctype") != "application/x-www-form-urlencoded":
                errors.append("share_target must declare application/x-www-form-urlencoded enctype")
            params = share_target.get("params") or {}
            for key in ("title", "text", "url"):
                if params.get(key) != key:
                    errors.append(f"share_target params must map {key} to {key}")

        capture_fragments = [
            "CAPTURE:",
            "INBOX_PROJECT: 'Inbox'",
            "MAX_TEXT_LENGTH: 300",
            "quickAddCaptureDraft: null",
            "await handleLaunchCapture();",
            "function handleLaunchCapture()",
            "function getLaunchCaptureRequest()",
            "function getSharedCapturePayload(params)",
            "function normalizeCaptureDescription(value)",
            "function getQuickAddCaptureOptions(options = {})",
            "description: normalizeCaptureDescription(options.description)",
            "function clearLaunchCaptureParams()",
            "project: parsed.project || CONFIG.CAPTURE.INBOX_PROJECT",
        ]
        for fragment in capture_fragments:
            if fragment not in index_html:
                errors.append(f"Quick capture runtime is missing: {fragment}")

        missing_assets = sorted(required_assets - assets)
        if missing_assets:
            errors.append(f"Service worker does not precache required assets: {missing_assets}")

        if not re.search(r"const CACHE_NAME = ['\"]task-tracer-v\d+\.\d+(?:\.\d+)?['\"]", sw_source):
            errors.append("Service worker cache name must be versioned as task-tracer-v<major>.<minor>[.<patch>]")
        if cache_name != f"task-tracer-v{runtime_version}":
            errors.append("CONFIG.APP.VERSION must match the service worker CACHE_NAME suffix")
        if "isOlderBundle(name) && !inUse.has(name)" not in sw_source or "if (unknown) return;" not in sw_source:
            errors.append("Cache cleanup must preserve active, unknown-client and future-installing bundles")
        if "async function installedShell()" not in sw_source or "ASSET_URLS.has(url.href)" not in sw_source:
            errors.append("App shell and versioned assets must use the installed bundle")
        if "LANGUAGE_PATHS.has(url.pathname)" not in sw_source or "await caches.open(name)).match(e.request)" not in sw_source:
            errors.append("Open older clients need exact-query language fallbacks")
        if "REPORT_CLIENT_VERSION" not in sw_source or "reportServiceWorkerClientVersion" not in index_html:
            errors.append("Cache cleanup needs the app/worker version handshake")
    except AssertionError as error:
            errors.append(str(error))


def validate_seo(index_html: str, errors: list[str]) -> None:
    required_head_fragments = [
        f'<meta name="description" content="{SEO_DESCRIPTION}">',
        '<meta name="robots" content="index,follow">',
        f'<link rel="canonical" href="{SEO_URL}">',
        '<meta property="og:type" content="website">',
        '<meta property="og:site_name" content="Task Tracer">',
        f'<meta property="og:url" content="{SEO_URL}">',
        '<meta property="og:image" content="https://todo.muquew.com/screenshots/task-list-en.png">',
        '<meta property="og:image:width" content="1440">',
        '<meta property="og:image:height" content="1024">',
        '<meta property="og:locale" content="en_US">',
        '<meta property="og:locale:alternate" content="zh_CN">',
        '<meta name="twitter:card" content="summary_large_image">',
        '<meta name="twitter:image" content="https://todo.muquew.com/screenshots/task-list-en.png">',
    ]
    for fragment in required_head_fragments:
        if fragment not in index_html:
            errors.append(f"Missing SEO head fragment: {fragment}")

    try:
        ld_match = first_match(
            r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
            index_html,
            "SoftwareApplication JSON-LD",
        )
        data = json.loads(ld_match.group(1))
        required_values = {
            "@context": "https://schema.org",
            "@type": "SoftwareApplication",
            "name": "Task Tracer",
            "url": SEO_URL,
            "softwareVersion": app_version(index_html),
        }
        for key, expected in required_values.items():
            if data.get(key) != expected:
                errors.append(f"JSON-LD {key} changed: expected {expected!r}, got {data.get(key)!r}")
        if data.get("applicationCategory") != "ProductivityApplication":
            errors.append("JSON-LD applicationCategory must be ProductivityApplication")
        if not isinstance(data.get("featureList"), list) or len(data["featureList"]) < 5:
            errors.append("JSON-LD featureList must describe the app capabilities")
    except (AssertionError, json.JSONDecodeError) as error:
        errors.append(str(error))

    if not ROBOTS_PATH.is_file():
        errors.append("robots.txt must exist")
    else:
        robots = read_text(ROBOTS_PATH)
        if "User-agent: *" not in robots or "Allow: /" not in robots:
            errors.append("robots.txt must allow crawling")
        if f"Sitemap: {SEO_URL}sitemap.xml" not in robots:
            errors.append("robots.txt must reference the canonical sitemap")

    if not SITEMAP_PATH.is_file():
        errors.append("sitemap.xml must exist")
    else:
        sitemap = read_text(SITEMAP_PATH)
        if f"<loc>{SEO_URL}</loc>" not in sitemap:
            errors.append("sitemap.xml must include the canonical app URL")
        if "http://www.sitemaps.org/schemas/sitemap/0.9" not in sitemap:
            errors.append("sitemap.xml must use the standard sitemap namespace")


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
        if "statusObj: { cls: CONFIG.UI.STATUS.NO_DEADLINE" not in index_html:
            errors.append("No-deadline tasks must render the status-no-deadline class")
        if "document.querySelectorAll('.task-item:not(.completed-task):not(.archived-task)')" not in index_html:
            errors.append("Timer refresh should skip completed and archived tasks")
        if "task.completed || task.archived || !hasTaskDueDate(task)" not in index_html:
            errors.append("Timer refresh must guard completed and archived records")
        validate_due_date_semantics(index_html, errors)
        if "pendingTaskActions: new Set()" not in index_html or "isGuardedTaskAction(action)" not in index_html:
            errors.append("Task actions must guard against duplicate in-flight writes")
        if "taskFormSaving" not in index_html or "quickAddSaving" not in index_html:
            errors.append("Task creation forms must guard against duplicate submissions")
        if "const activeScopeTasks = tasks.filter(task => !task.archived)" not in index_html:
            errors.append("Stats total must exclude archived tasks")
        if "const completionHistoryTasks = activeScopeTasks.filter(task => task.completed)" not in index_html:
            errors.append("Stats completion history must exclude archived tasks")
        if not contains_in_order(index_html, ("function shiftCalendarMonth(delta)", "date.setUTCDate(1);", "date.setUTCMonth(date.getUTCMonth() + delta);", "state.calendarDetailDateKey = '';")):
            errors.append("Calendar month navigation must clamp its civil date to day one and clear stale day details")
        state_consistency_checks = {
            "Task transactions must compare a revision captured before opening the transaction": ("writeTaskTransaction: (write, abortMessage, forceCheckpoint = false)", "const expectedRevision = state.taskRevision;", "const tx = state.db.transaction", "if (currentRevision !== expectedRevision)"),
            "Import approval must be tied to its preview revision": ("function openTaskImportPreview(", "if (preview.taskRevision !== state.taskRevision)", "openTaskImportPreview(importPayload, importedTasks);", "return false;"),
            "Cancelled task file reads must not reopen a newer flow": ("function importTasks(file)", "state.pendingTaskImportReader = reader;", "reader.onload = e =>", "state.pendingTaskImportReader !== reader", "!status.isConnected"),
            "Archive completed must write cloned archived records": ("const archivedTasks = completed.map(task => ({ ...task, archived: true, archivedAt }))",),
            "Snooze must persist before mutating the in-memory task": ("const updatedTask = {", "snoozedUntil: snoozedUntilAt", "await dbActions.updateTask(updatedTask);"),
            "Notification delivery must refresh the full committed snapshot before recording session delivery": ("const recorded = await dbActions.recordReminderDelivery(expected, lastReminderAt);", "await refreshTasks();", "if (!recorded) return;", "state.notifiedTasks.add(notificationKey);"),
            "Reminder persistence must patch a current matching record": ("recordReminderDelivery: (expected, lastReminderAt)", "const request = store.get(expected.id);", "if (!current || current.completed || current.archived) return;", "if (getTaskNotificationKey(current) !== expected.key) return;", "if ((current.snoozedUntil || null) !== expected.snoozedUntil) return;", "if ((current.lastReminderAt || null) !== expected.lastReminderAt) return;", "store.put({ ...current, lastReminderAt, snoozedUntil: null });"),
            "Subtask toggles must persist cloned subtasks before updating memory": ("const updatedSubtasks = task.subtasks.map", "completed: nextCompleted", "await dbActions.updateTask(updatedTask);"),
            "Manual reordering must avoid mutating state before persistence succeeds": ("return mergedTasks.map((task, index) => ({ ...task, order: index * CONFIG.DEFAULTS.MANUAL_ORDER_STEP }))",),
            "Manual reordering must restore the rendered order after save failure": ("catch (err)", "renderTaskList();", "messages.task.saveError"),
            "Editing mode must accept task id 0": ("function isEditingTask()", "state.editingTaskId !== null"),
            "Reminder delivery state must be cleared only after task update succeeds": ("await dbActions.updateTask(updatedTask);", "if (shouldClearNotificationDelivery) clearTaskNotificationDeliveryState(original.id);"),
            "Missed reminders must surface outside the normal delivery window": ("function checkNotifications()", "if ((!dueState.due && !dueState.missed) || !shouldDeliverTaskReminder(task, notificationKey, dueState) || state.pendingNotificationKeys.has(notificationKey)) return;"),
            "One-time reminders must use persisted delivery state across reloads": ("function shouldDeliverTaskReminder(task, notificationKey, dueState)", "const deliveredInSession = state.notifiedTasks.has(notificationKey);", "if (repeat === -1) return false;"),
            "Reminder icons must reflect persisted one-time delivery": ("function renderReminderIcon(el, task)", "hasTaskReminderBeenDelivered(task)", "function hasTaskReminderBeenDelivered(task)", "if (repeat === -1) return true;"),
            "Vibration feedback must require user activation when browsers expose it": ("function vibrateNotification()", "navigator.userActivation", "!navigator.userActivation.hasBeenActive"),
            "Status search must keep archived records isolated unless archived is explicit": ("function isTaskVisible(task)", "if (hasSearchStatusFilter()) return shouldShowTaskForStatusSearch(task);", "function shouldShowTaskForStatusSearch(task)", "return !task.archived || searchStatusIncludesArchived();"),
            "Stats status search must keep archived records isolated unless archived is explicit": ("function getStatsScopeTasks()", ".filter(matchesTaskSearch)", ".filter(task => !hasSearchStatusFilter() || shouldShowTaskForStatusSearch(task));"),
            "Notification toggle must handle persistence failures": ("toggleNotifications().catch(handleNotificationToggleError)",),
            "Notification setting must persist before mutating in-memory state": ("await dbActions.setConfig(CONFIG.STORAGE.NOTIFICATIONS, enabled);", "state.notificationsEnabled = enabled"),
            "Language setting must roll back after persistence failure": ("state.currentLanguage = previousLanguage;", "initLanguage();"),
            "Single IndexedDB operations must resolve after transaction completion": ("tx.oncomplete = () => resolve(result);", "req.onsuccess = () => { result = req.result; };"),
            "Historical completed fields must normalize to real booleans": ("function normalizeTaskRecords(tasks)", "const completed = normalizeBoolean(normalizedTask.completed);", "normalizedTask.completed = completed;", "function normalizeBoolean(value, defaultValue = false)"),
            "Historical subtask completed fields must normalize to real booleans": ("function normalizeSubtasksForTask(subtasks)", "const completed = normalizeBoolean(sourceSubtask.completed);", "return { ...sourceSubtask, id: normalizedId, completed };"),
            "Imported task boolean fields must normalize to real booleans": ("function normalizeImportedTask(rawTask, index, normalizeId)", "repeatPaused: normalizeBoolean(task.repeatPaused)", "completed: normalizeBoolean(task.completed)", "archived: normalizeBoolean(task.archived)"),
            "Imported subtask completed fields must normalize to real booleans": ("function normalizeImportedSubtasks(rawSubtasks)", "completed: normalizeBoolean(subtask.completed)"),
            "Today plan markers must be normalized and exported": ("function normalizeFocusDate(value)", "const focusDate = normalizeFocusDate(normalizedTask.focusDate);", "'todayPlan'", "focusDate: normalizeFocusDate(task.focusDate)"),
            "Backup payloads must carry export identity and integrity checksum": ("function createTaskDataPayload(mode, date, tasks, storage = 'indexeddb')", "exportId: createTaskDataExportId(mode, date)", "payload.checksum = createTaskDataChecksum(payload);", "function stableStringify(value)"),
            "Saved smart views must persist to config storage": ("SAVED_VIEWS: 'savedViews'", "function restoreSavedViews()", "updateSavedViews: change => new Promise", "tx.oncomplete = () => resolve(committed);", "const request = store.get(CONFIG.STORAGE.SAVED_VIEWS);", "store.put({ key: CONFIG.STORAGE.SAVED_VIEWS, value: committed });"),
            "Batch mode must avoid drag reordering and support undo": ("function applyBatchTaskUpdate(action, selectedTasks)", "registerUndoSnapshot(utils.translate(`batch.undo.${action}`), beforeTasks);", "function canReorderTasks()", "!state.batchMode"),
            "Undo must bind snapshots to revisions and reject newer conflicting edits": ("function captureUndoSnapshot()", "const persistedSnapshot = dbActions.readTaskSnapshot();", "function registerUndoSnapshot(label, beforeTasks)", "const after = dbActions.readTaskSnapshot();", "previous.taskRevision !== previousRevision || saved.taskRevision !== revision || revision !== state.taskRevision", "await dbActions.undoTaskChanges(previous.tasks, saved.tasks);", "function performUndo()", "undoTaskChanges: (beforeTasks, afterTasks)", "JSON.stringify(request.result) !== JSON.stringify(after.get(id))", "TaskConflictError"),
            "Focus mode must be a separate visible task scope": ("function enterFocusMode()", "state.focusMode = true;", "if (state.focusMode && !isTaskInTodayPlan(task)) return false;"),
            "Focus mode entry must be independent of the overflow menu": ('id="focusModeToggleBtn"', 'aria-pressed="false"', 'id="focusModeToggleText"', "DOM.focusModeToggleBtn.addEventListener('click', () => runAppAction('focus.toggle'))", "function syncFocusModeButton()"),
            "Due dates must format and group by the task timezone": ("function getTaskDueDateKey(task)", "getInstantWallPartsInTimeZone(dueAt, getTaskDueTimeZone(task))", "function formatTaskDueDate(task)"),
            "Imported duplicate IDs must not produce ambiguous repeat links": ("const duplicateIds = new Set(getDuplicateImportIds(rawTasks));", "sanitizeAmbiguousImportedReferences", "if (duplicateIds.has(normalizeTaskReferenceId(sanitizedTask[key]))) sanitizedTask[key] = null;"),
            "Imported repeat links must only point to final imported tasks": ("function sanitizeDanglingTaskReferences(tasks)", "const ids = new Set(tasks.map(task => Number(task.id)).filter(Number.isFinite));", "sanitizedTask[key] = value !== null && ids.has(value) ? value : null;"),
            "Merged imports must clear repeat links to skipped conflicts": ("function prepareImportedTasksForMerge(importedTasks, conflictActions = new Map(), conflictDefault = 'keep')", "const tasksToImport = importedTasks.filter", "const tasks = sanitizeDanglingTaskReferences(remapped.map(task => {"),
            "Import preview must include template restore checks": ("downloadPreImportSnapshot(beforeTasks)", "sourceInfo: getImportSourceInfo(sourceData, compatibilitySteps)", "function getImportSourceInfo(sourceData, compatibilitySteps = [])", "checksumStatus", "function createImportRestoreChecklist(preview, t)", "messages.import.restoreCheckTitle", "function createImportDiffPreview(preview, t)", "return false;"),
            "Startup must verify IndexedDB is writable before normal app mode": ("if (!(await initializeStorageOrFallback())) return;", "function initPersistentStorage()", "await verifyPersistentStorage();", "function verifyPersistentStorage()", "await dbActions.deleteConfig(CONFIG.STORAGE.PROBE);"),
            "Storage fallback must be scoped to the storage initialization stage": ("function initializeStorageOrFallback()", "await initPersistentStorage();", "if (!shouldUseStorageUnavailableMode(error)) throw error;", "handleStorageUnavailable(error);"),
            "Storage-unavailable mode must pause task-writing actions": ("function handleStorageUnavailable(error)", "function syncStorageAvailabilityUI()", "function ensureStorageAvailable(options = {})", "storage.unavailable.actionsDisabled"),
            "Interactive entrypoints must route through a central action guard": ("const STORAGE_GATED_ACTIONS = new Set([", "function canRunAppAction(action", "function runAppAction(action", "DOM.openModalBtn.addEventListener('click', () => runAppAction('task.new'))", "DOM.menu.backupBtn.addEventListener('click', () => runAppAction('data.backup'))", "if (meta && key === 'm') { e.preventDefault(); runAppAction('menu.toggle'); return; }"),
            "Web Storage access must be guarded for privacy modes": ("function safeGetStorageItem(kind, key)", "function safeSetStorageItem(kind, key, value)", "function safeRemoveStorageItem(kind, key)"),
            "Runtime storage failures must route through storage-unavailable fallback": ("function handleStorageOperationError(error", "if (shouldUseStorageUnavailableMode(error))", "handleStorageUnavailable(error);", "return true;"),
            "Background backup health reads must route storage failures through fallback": ("scheduleBackupReminder().catch(handleBackgroundStorageFailure)", "function handleBackgroundStorageFailure(error)", "handleStorageOperationError(error);", "updateBackupHealthStatus().catch(handleBackgroundStorageFailure)"),
            "Task write failures must route storage errors through fallback": ("catch (err)", "handleStorageOperationError(err, 'messages.task.saveError');", "handleStorageOperationError(err);"),
            "Backup status must compare a coherent snapshot and preserve known results": ("async function updateBackupHealthStatus(knownStatus)", "arguments.length > 0 ? knownStatus : await dbActions.getTaskBackupStatus()", "lastTaskBackup.date === lastBackupAt", "lastTaskBackup.taskRevision !== taskRevision"),
            "Storage fallback events must avoid duplicate theme handlers after normal init": ("essentialEventsBound: false", "function bindEssentialEvents()", "if (state.essentialEventsBound) return;", "state.essentialEventsBound = true;"),
            "Storage fallback must preserve the active language after normal init": ("function getStorageUnavailableLanguage()", "if (state.eventsBound && isSupportedLanguage(state.currentLanguage)) return state.currentLanguage;", "state.currentLanguage = getStorageUnavailableLanguage();"),
            "Runtime storage fallback must preserve an emergency export snapshot": ("storageFallbackTasks: []", "function captureStorageFallbackSnapshot()", "state.storageFallbackTasks = cloneTaskSnapshot(state.tasks);", "function downloadEmergencyBackup()", "memory-fallback"),
        }
        for message, fragments in state_consistency_checks.items():
            if not contains_in_order(index_html, fragments):
                errors.append(message)
    except AssertionError as error:
        errors.append(str(error))


def validate_native_language_control(index_html: str, errors: list[str]) -> None:
    try:
        select = first_match(r'<select\b[^>]*\sid="languageSelect"[^>]*>', index_html,
                             'native language select').group()
        if not re.search(r'\sdata-native-select(?:\s|=|>)', select):
            errors.append('Language select must retain its native-control marker')
        if ('data-i18n-aria-label="workspace.language"' not in select
                or not re.search(r'\saria-label="[^"]+"', select)):
            errors.append('Native language select must expose a localized accessible name')

        runtime = main_script(index_html).group('content')
        functions = {
            name: first_match(
                rf'(?m)^([ \t]*)function\s+{name}\s*\([^)]*\)\s*\{{(?P<body>.*?)^\1\}}',
                runtime, name).group('body')
            for name in ('createLangButtons', 'syncLanguageSelect', 'initLanguage',
                         'bindEssentialEvents', 'enhanceSelectControls')
        }
        option_fragments = (
            "DOM.languageSelect.textContent = '';",
            'CONFIG.LANGUAGES.forEach(language => {',
            "const option = document.createElement('option');",
            'option.value = language.code;',
            'option.textContent = language.name;',
            'DOM.languageSelect.appendChild(option);',
        )
        if not contains_in_order(functions['createLangButtons'], option_fragments):
            errors.append('Native language options must use every configured language code and name')
        if ('DOM.languageSelect.value = state.currentLanguage;' not in functions['syncLanguageSelect']
                or 'syncLanguageSelect();' not in functions['initLanguage']):
            errors.append('Language initialization and rollback must synchronize the native select value')

        handler = first_match(
            r"DOM\.languageSelect\.addEventListener\('change', \(\) => \{(?P<body>.*?)\n\s*\}\);",
            functions['bindEssentialEvents'], 'native language change handler').group('body')
        if not contains_in_order(handler, (
            "runAppAction('language.switch', { code: DOM.languageSelect.value });",
            'syncLanguageSelect();',
        )):
            errors.append('Native language changes must use the action guard and restore the displayed value')
        gated_actions = first_match(r'const STORAGE_GATED_ACTIONS = new Set\(\[(.*?)\]\);',
                                    runtime, 'STORAGE_GATED_ACTIONS').group(1)
        if "'language.switch'" not in gated_actions:
            errors.append('Language changes must remain gated when storage is unavailable')
        if "select:not([data-custom-select-ready]):not([data-native-select])" not in functions['enhanceSelectControls']:
            errors.append('Native preference selects must be excluded from custom-select enhancement')
    except AssertionError as error:
        errors.append(str(error))


def validate_accessibility_styles(index_html: str, errors: list[str]) -> None:
    if ":focus-visible" not in index_html or "--focus-ring" not in index_html:
        errors.append("Interactive controls must expose a visible keyboard focus style")
    if "@media (prefers-reduced-motion: reduce)" not in index_html:
        errors.append("CSS must respect prefers-reduced-motion")
    if "getMotionAwareScrollBehavior" not in index_html or "prefersReducedMotion()" not in index_html:
        errors.append("JavaScript scrolling must respect prefers-reduced-motion")
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
    if "handleDropdownButtonKeydown" not in index_html or "handleDropdownMenuKeydown" not in index_html:
        errors.append("Custom dropdowns must support keyboard navigation")
    if "openCustomSelect(select, (e.key === 'Enter' || e.key === ' ') ? 'selected' : e.key)" not in index_html:
        errors.append("Custom select buttons must focus the selected option when opened with Enter or Space")
    if not contains_in_order(index_html, ("function handleCustomSelectMenuKeydown(e)", "if (e.key === 'Escape') {", "e.stopPropagation();", "closeCustomSelect(option.closest('.custom-select'), true);")):
        errors.append("Custom select Escape handling must stop propagation before closing the menu")
    if not contains_in_order(index_html, ("if (isTaskDialogOpen())", "else if (e.key === 'Escape') {", "if (!closeOpenCustomSelect(DOM.modal)) requestCloseTaskDialog();", "function closeOpenCustomSelect(root = document)")):
        errors.append("Dialog Escape handling must close an open custom select before closing the dialog")
    if "handleViewSwitcherKeydown" not in index_html or 'role="tab" aria-selected="true" aria-controls="taskList" tabindex="0"' not in index_html:
        errors.append("View tabs must use a roving keyboard tablist model")
    if 'id="taskList" role="tabpanel"' not in index_html:
        errors.append("Task view content must be exposed as the selected tab panel")
    if re.search(r'id="taskList"[^>]*aria-live=', index_html):
        errors.append("Task view content must not be a broad live region")
    if "function announceTaskViewSummary()" not in index_html or "messages.view.summary" not in index_html:
        errors.append("Task view changes must announce a concise summary through the screen-reader status region")
    if 'id="menu" role="menu"' not in index_html or "handleMenuKeydown" not in index_html:
        errors.append("Main app menu must expose menu semantics and keyboard navigation")
    if 'id="focusModeBtn"' in index_html:
        errors.append("Today Plan must not be hidden inside the overflow menu")
    if "inFocus ? '#icon-check' : '#icon-target'" in index_html:
        errors.append("Today Plan task action must not reuse the completion check icon")
    if re.search(r"<label\b[^>]*for=['\"][^'\"]+['\"][^>]*>\s*</label>", index_html, re.DOTALL):
        errors.append("Form labels must not be empty")
    if '<html lang="zh-CN" dir="ltr">' not in index_html or "document.documentElement.dir = getLanguageDirection" not in index_html:
        errors.append("Document language and direction must be initialized and synchronized")
    if 'data-i18n-aria-label="app.toolbar"' not in index_html:
        errors.append("Toolbar accessible label must be localized")
    if '<title data-i18n="app.title">' not in index_html:
        errors.append("Document title must be localized")
    validate_native_language_control(index_html, errors)
    if "DOM.modal.setAttribute('aria-describedby', 'confirm-message-text')" not in index_html:
        errors.append("Confirmation dialogs must expose aria-describedby")
    if 'id="srStatus" class="sr-only" aria-live="polite" aria-atomic="true"' not in index_html:
        errors.append("Keyboard-only status updates must use a screen-reader live region")
    if "formatControlAccessibleValue(getSelectAccessibleName(select), selectedOption?.textContent || '')" not in index_html:
        errors.append("Custom select accessible labels must include the current selected value")
    if "function getDropdownAccessibleName(btn)" not in index_html or "formatControlAccessibleValue(baseLabel, span.textContent)" not in index_html:
        errors.append("Custom dropdown accessible labels must include their current selected value")
    if "handleTaskReorderKeydown" not in index_html or "task.actions.reorder" not in index_html:
        errors.append("Manual task ordering must support keyboard reordering")
    if "syncTaskAccessibility(el, task)" not in index_html or "role', 'article'" not in index_html:
        errors.append("Task cards must expose structured article labels and descriptions")
    if "markDecorativeIcons" not in index_html:
        errors.append("Decorative SVG icons must be hidden from the accessibility tree")
    if "notificationHideTimer" not in index_html or "clearTimeout(state.notificationHideTimer)" not in index_html:
        errors.append("Toast notifications must clear the previous hide timer before showing a new message")
    if "syncImportConflictControls" not in index_html or "data-import-conflict-section" not in index_html:
        errors.append("Import conflict controls must be scoped to merge import mode")
    if "id: createTaskId()" not in index_html or "function createTaskId(" not in index_html:
        errors.append("New task records must use the unique task id generator")
    if "id: Date.now()" in index_html:
        errors.append("New task records must not use raw Date.now() as the task id")


def validate_security_headers(errors: list[str]) -> None:
    if not VERCEL_PATH.is_file():
        errors.append("vercel.json must configure production security headers")
        return

    try:
        config = load_json(VERCEL_PATH)
    except AssertionError as error:
        errors.append(str(error))
        return

    if config.get('framework', 'auto') is not None or config.get('buildCommand') != '' or config.get('installCommand') != '' or config.get('outputDirectory') != '.':
        errors.append('Vercel must deploy the static root without installing or building development-only tools')

    headers: dict[str, str] = {}
    for route in config.get("headers", []):
        for header in route.get("headers", []):
            key = header.get("key")
            value = header.get("value")
            if isinstance(key, str) and isinstance(value, str):
                headers[key.lower()] = value

    required = [
        "content-security-policy",
        "referrer-policy",
        "x-content-type-options",
        "x-frame-options",
        "permissions-policy",
    ]
    for key in required:
        if key not in headers:
            errors.append(f"Missing production security header: {key}")

    csp = headers.get("content-security-policy", "")
    for directive in [
        "default-src 'self'",
        "base-uri 'self'",
        "object-src 'none'",
        "frame-ancestors 'none'",
        "form-action 'none'",
    ]:
        if directive not in csp:
            errors.append(f"Content-Security-Policy is missing directive: {directive}")


def validate_package_versions(index_html: str, errors: list[str]) -> None:
    numeric = r'(?:0|[1-9]\d*)'
    try:
        runtime_version = app_version(index_html)
        if not re.fullmatch(rf'{numeric}\.{numeric}(?:\.{numeric})?', runtime_version):
            raise AssertionError('CONFIG.APP.VERSION must contain two or three numeric components')
        components = runtime_version.split('.')
        expected = '.'.join(components + ['0'] * (3 - len(components)))
        package = load_json(REPO_ROOT / 'package.json')
        lock = load_json(REPO_ROOT / 'package-lock.json')
        if not isinstance(package, dict) or not isinstance(lock, dict):
            raise AssertionError('package.json and package-lock.json must contain objects')
        packages = lock.get('packages')
        if not isinstance(packages, dict) or not isinstance(packages.get(''), dict):
            raise AssertionError('package-lock.json must contain root package metadata in packages[\'\']')
        versions = {
            'package.json version': package.get('version'),
            'package-lock.json version': lock.get('version'),
            'package-lock.json packages[\'\'] version': packages[''].get('version'),
        }
        for label, value in versions.items():
            if not isinstance(value, str) or not re.fullmatch(rf'{numeric}\.{numeric}\.{numeric}', value):
                errors.append(f'{label} must contain a three-component numeric version')
            elif value != expected:
                errors.append(f'{label} must match CONFIG.APP.VERSION {runtime_version} (npm version {expected})')
    except (AssertionError, OSError, UnicodeError) as error:
        errors.append(str(error))


def main() -> int:
    errors: list[str] = []
    index_html = read_text(INDEX_PATH)
    try:
        check_translation_fallback()
    except AssertionError as error:
        errors.append(str(error))

    validate_translations(index_html, errors)
    validate_pwa(index_html, errors)
    validate_package_versions(index_html, errors)
    validate_seo(index_html, errors)
    validate_loaded_code_is_comment_free(index_html, errors)
    validate_task_state_styles(index_html, errors)
    validate_accessibility_styles(index_html, errors)
    validate_security_headers(errors)

    if errors:
        print("Static validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Static validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
