"""Shared accessibility i18n audit fixtures and assertions; no test entry point."""
from __future__ import annotations
from tests.support.paths import input_path
import json
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from playwright.sync_api import Page, expect
from tests.support.browser import close_workspace_navigation, select_theme_preference

AXE_FAILURES: list[str] | None = None

def find_axe_source() -> Path:
    source = input_path('node_modules' + '/' + 'axe-core' + '/' + 'axe.min.js')
    if not source.is_file():
        raise AssertionError('Pinned axe-core is missing. Run npm ci --ignore-scripts in the repository root')
    return source

def settle_animations(page: Page, label: str) -> None:
    """Wait for live finite animations, with two stable frames and a deadline."""
    result = page.evaluate('''async () => {
        const describe = animations => animations.map(animation => {
            const effect = animation.effect, target = effect?.target;
            const style = target ? getComputedStyle(target) : null;
            return {type:animation.constructor.name, name:animation.animationName || animation.transitionProperty || '',
                playState:animation.playState, pending:animation.pending, currentTime:animation.currentTime, startTime:animation.startTime,
                timing:effect?.getTiming(), computedTiming:effect?.getComputedTiming(),
                target:{tag:target?.tagName,id:target?.id,className:typeof target?.className==='string'?target.className:target?.className?.baseVal,
                    connected:target?.isConnected,visibility:style?.visibility,display:style?.display,animationPlayState:style?.animationPlayState},
                documentVisibility:document.visibilityState};
        });
        const active = () => document.getAnimations().filter(animation => animation.effect?.getTiming().iterations !== Infinity
            && (animation.pending || !['idle', 'finished'].includes(animation.playState)));
        const before = describe(document.getAnimations()), started = performance.now();
        let timer, done = false, stableFrames = 0, lastActiveCount = active().length;
        const settle = new Promise(resolve => {
            const sample = () => {
                if (done) return;
                lastActiveCount = active().length;
                stableFrames = lastActiveCount === 0 ? stableFrames + 1 : 0;
                if (stableFrames >= 2) resolve(true);
                else requestAnimationFrame(sample);
            };
            requestAnimationFrame(sample);
        });
        let completed;
        try {
            completed = await Promise.race([settle, new Promise(resolve => {timer = setTimeout(() => resolve(false), 10000);})]);
        } finally {done = true; clearTimeout(timer);}
        const result = {completed, waitedMs:performance.now()-started, stableFrames, lastActiveCount,
            before, after:describe(document.getAnimations()), visibility:document.visibilityState};
        return JSON.parse(JSON.stringify(result, (_key,value) => typeof value==='number'&&!Number.isFinite(value)?String(value):value));
    }''')
    if not result['completed']:
        raise AssertionError(f'{label}: finite animations did not settle within 10 seconds:\n{json.dumps(result, ensure_ascii=False, indent=2)}')

def inject_axe(page: Page, axe_source: str) -> None:
    assert find_axe_source().read_text() == axe_source, 'Pinned axe source changed during the audit'
    url = urljoin(page.url, './__task_tracer_audit__/axe.min.js')
    if urlparse(page.url).hostname in {'127.0.0.1', 'localhost'}:
        page.add_script_tag(url=url)
        return
    def serve_audit(route):
        route.fulfill(status=200, content_type='application/javascript', body=axe_source)
    page.context.route(url, serve_audit)
    try:
        page.add_script_tag(url=url)
    finally:
        page.context.unroute(url, serve_audit)

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
                "nodes": [{"target": node.get("target"), "failure": node.get("failureSummary")} for node in item.get("nodes", [])[:8]],
            }
            for item in serious
        ]
        message = f"axe violations during {label}:\n{json.dumps(compact, ensure_ascii=False, indent=2)}"
        if AXE_FAILURES is None:
            raise AssertionError(message)
        AXE_FAILURES.append(message)
        print(message, flush=True)

def assert_focus_visible(page: Page, selector: str, label: str) -> None:
    control = page.locator(selector)
    control.focus()
    if control.evaluate('node => node.matches("input[type=radio][name=workspaceTheme]") && Number(getComputedStyle(node).opacity) === 0'):
        control.press('Tab')
        page.keyboard.press('Shift+Tab')
    expect(control).to_be_focused()
    visible = page.evaluate(
        """() => {
            const el = document.activeElement;
            const style = getComputedStyle(el);
            if (el.matches('input[type=radio][name=workspaceTheme]') && Number(style.opacity) === 0) {
                return el.matches(':focus-visible') && [...el.labels].some(label => {
                    const paint = getComputedStyle(label);
                    const box = label.getBoundingClientRect();
                    return !label.closest('[hidden],[inert],[aria-hidden="true"]')
                        && paint.display !== 'none' && paint.visibility !== 'hidden' && Number(paint.opacity) > 0
                        && box.width > 0 && box.height > 0
                        && Number.parseFloat(paint.outlineWidth || '0') > 0 && paint.outlineStyle !== 'none';
                });
            }
            if (el.id === 'quickAddInput') {
                const wrapper = el.closest('.quick-add-input-wrap');
                if (!wrapper || document.activeElement !== el || !wrapper.matches(':focus-within')) return false;
                const paint = getComputedStyle(wrapper);
                const box = wrapper.getBoundingClientRect();
                if (wrapper.closest('[hidden],[inert],[aria-hidden="true"]')
                    || !wrapper.checkVisibility({opacityProperty: true, visibilityProperty: true})
                    || paint.display === 'none' || paint.visibility === 'hidden' || Number(paint.opacity) <= 0
                    || box.width <= 0 || box.height <= 0) return false;
                const canvas = document.createElement('canvas');
                canvas.width = canvas.height = 1;
                const context = canvas.getContext('2d');
                context.fillStyle = paint.outlineColor;
                context.fillRect(0, 0, 1, 1);
                const opaque = context.getImageData(0, 0, 1, 1).data[3] > 0;
                return Number.parseFloat(paint.outlineWidth || '0') > 0
                    && !['none', 'hidden'].includes(paint.outlineStyle) && opaque;
            }
            const outline = Number.parseFloat(style.outlineWidth || '0');
            const boxShadow = style.boxShadow && style.boxShadow !== 'none';
            return outline > 0 || boxShadow;
        }"""
    )
    if not visible:
        raise AssertionError(f"Focused control has no visible focus treatment: {label}")

def assert_layout(page: Page, label: str) -> None:
    metrics = page.evaluate(
        """() => {
            const doc = document.documentElement;
            const viewportWidth = window.innerWidth;
            const visibleControls = [...document.querySelectorAll('button:not([hidden]), input:not([type="hidden"]), select, textarea, a[href]')]
                .filter((el) => {
                    if (el.closest('[inert], [hidden], [aria-hidden="true"]') || el.classList.contains('native-select-hidden')) return false;
                    const rect = el.getBoundingClientRect();
                    const style = getComputedStyle(el);
                    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
                })
                .map((el) => {
                    const rect = el.getBoundingClientRect();
                    let scrollsWithinViewport = false;
                    for (let parent = el.parentElement; parent && parent !== document.body; parent = parent.parentElement) {
                        const style = getComputedStyle(parent);
                        const box = parent.getBoundingClientRect();
                        if (['auto', 'scroll'].includes(style.overflowX) && parent.scrollWidth > parent.clientWidth + 1
                            && box.left >= -1 && box.right <= viewportWidth + 1) {
                            scrollsWithinViewport = true;
                            break;
                        }
                    }
                    return {
                        tag: el.tagName.toLowerCase(),
                        id: el.id,
                        className: typeof el.className === 'string' ? el.className : '',
                        width: rect.width,
                        height: rect.height,
                        left: rect.left,
                        right: rect.right,
                        scrollsWithinViewport
                    };
                });
            return {
                viewportWidth,
                scrollWidth: doc.scrollWidth,
                smallControls: visibleControls.filter((item) => item.width < 24 || item.height < 24),
                overflowingControls: visibleControls.filter((item) => (item.left < -1 || item.right > viewportWidth + 1) && !item.scrollsWithinViewport)
            };
        }"""
    )
    if metrics["scrollWidth"] - metrics["viewportWidth"] > 1:
        raise AssertionError(f"{label} has horizontal overflow: {metrics}")
    if metrics["smallControls"]:
        raise AssertionError(f"{label} has undersized controls: {metrics['smallControls'][:8]}")
    if metrics["overflowingControls"]:
        raise AssertionError(f"{label} has controls outside viewport: {metrics['overflowingControls'][:8]}")

def color_contrast(first: list[int], second: list[int]) -> float:
    def luminance(color: list[int]) -> float:
        channels = [value / 255 for value in color[:3]]
        linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
                  for value in channels]
        return sum(value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722)))
    light, dark = sorted((luminance(first), luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)

def subtask_checkbox_paint(checkbox) -> dict:
    return checkbox.evaluate("""element => {
        const pixel = color => {
            const canvas = document.createElement('canvas');
            canvas.width = canvas.height = 1;
            const context = canvas.getContext('2d');
            context.fillStyle = color;
            context.fillRect(0, 0, 1, 1);
            return [...context.getImageData(0, 0, 1, 1).data];
        };
        const style = getComputedStyle(element);
        const result = {
            checked: element.checked,
            background: pixel(style.backgroundColor),
            marker: null,
            image: style.backgroundImage,
            focusVisible: element.matches(':focus-visible'),
            outlineWidth: Number.parseFloat(style.outlineWidth),
            outlineStyle: style.outlineStyle,
            outline: pixel(style.outlineColor)
        };
        if (element.checked) {
            if (!style.backgroundImage.startsWith('url(') || !style.backgroundImage.endsWith(')')) throw new Error('Checked subtask has no renderable SVG marker');
            let image = style.backgroundImage.slice(4, -1).trim();
            if (image[0] === '"' || image[0] === "'") image = image.slice(1, -1);
            if (!image.startsWith('data:image/svg+xml')) throw new Error('Checked subtask marker is not an SVG image');
            const separator = image.indexOf(',');
            const metadata = image.slice(0, separator);
            const data = image.slice(separator + 1);
            const source = metadata.endsWith(';base64') ? atob(data) : decodeURIComponent(data);
            const svg = new DOMParser().parseFromString(source, 'image/svg+xml');
            const stroke = svg.querySelector('[stroke]:not([stroke="none"])');
            if (!svg.querySelector('path[d]') || !stroke) throw new Error('Checked subtask SVG has no visible check stroke');
            result.marker = pixel(stroke.getAttribute('stroke'));
        }
        return result;
    }""")

def audit_subtask_checkbox_visibility(page: Page, label: str,
                                      observations: list | None = None,
                                      evidence_directory: Path | None = None) -> None:
    task = page.locator('.task-item').filter(has=page.locator('.subtasks-wrapper')).first
    task.locator('.subtask-summary-bar').click()
    checkbox = task.locator('.subtask-checkbox').first
    expect(checkbox).to_be_visible()
    expect(checkbox).to_have_role('checkbox')
    expect(checkbox).not_to_be_checked()
    for theme in ('light', 'dark'):
        if page.locator('html').get_attribute('data-theme') != theme:
            select_theme_preference(page, theme)
        close_workspace_navigation(page)
        page.locator('#searchInput').focus()
        page.mouse.move(0, 0)
        settle_animations(page, f'{label} {theme} unchecked subtask')
        unchecked = subtask_checkbox_paint(checkbox)
        checkbox.focus()
        checkbox.press('Space')
        expect(checkbox).to_be_checked()
        expect(task.locator('.subtask-display-item.completed')).to_have_count(1)
        for interaction in ('resting', 'hover', 'keyboard-focus'):
            if interaction == 'resting':
                page.locator('#searchInput').focus()
                page.mouse.move(0, 0)
            elif interaction == 'hover':
                checkbox.hover()
            else:
                page.mouse.move(0, 0)
                checkbox.focus()
                checkbox.press('Tab')
                page.keyboard.press('Shift+Tab')
                expect(checkbox).to_be_focused()
            settle_animations(page, f'{label} {theme} {interaction} subtask')
            paint = subtask_checkbox_paint(checkbox)
            observation = {'label': label, 'theme': theme, 'interaction': interaction,
                           'unchecked': unchecked, 'checked': paint,
                           'marker_contrast': color_contrast(paint['marker'], paint['background']),
                           'state_contrast': color_contrast(paint['background'], unchecked['background'])}
            if evidence_directory is not None:
                evidence_directory.mkdir(parents=True, exist_ok=True)
                image = evidence_directory / f'{theme}-{interaction}.png'
                assert not image.exists(), image
                page.screenshot(path=image, full_page=True, animations='disabled')
                observation['screenshot'] = str(image)
            if observations is not None:
                observations.append(observation)
            print('Subtask checkbox visibility: ' + json.dumps(observation, ensure_ascii=False), flush=True)
            assert paint['checked'] and paint['marker'][3] == paint['background'][3] == 255, observation
            assert observation['marker_contrast'] >= 3, f'Checked subtask mark is not distinguishable: {observation}'
            assert observation['state_contrast'] >= 3, f'Checked and unchecked subtask states are not distinguishable: {observation}'
            if interaction == 'keyboard-focus':
                assert paint['focusVisible'] and paint['outlineWidth'] > 0 and paint['outlineStyle'] != 'none', observation
        checkbox.focus()
        checkbox.press('Space')
        expect(checkbox).not_to_be_checked()
        expect(task.locator('.subtask-display-item.completed')).to_have_count(0)
    task.locator('.subtask-summary-bar').click()
    if page.locator('html').get_attribute('data-theme') != 'light':
        select_theme_preference(page, 'light')
    close_workspace_navigation(page)

def assert_workspace_theme_gallery(page: Page) -> None:
    choices = page.locator('#workspaceThemeChoices')
    expect(choices).to_be_visible()
    expect(choices).to_have_role('group')
    expect(choices.locator('legend')).to_be_visible()
    radios = choices.locator('input[type="radio"][name="workspaceTheme"]')
    expect(radios).to_have_count(4)
    checked = choices.locator('input[type="radio"][name="workspaceTheme"]:checked')
    expect(checked).to_have_count(1)
    expect(checked).to_have_value(page.locator('html').get_attribute('data-accent'))
    for radio in radios.all():
        expect(radio).to_be_visible()
        expect(radio).to_be_enabled()
        expect(radio).to_have_role('radio')
        assert radio.evaluate('node => [...node.labels].some(label => label.textContent.trim())'), 'Workspace theme radio has no real label'
    expect(page.locator('#accentSelect')).to_be_hidden()
