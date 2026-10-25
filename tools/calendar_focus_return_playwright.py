#!/usr/bin/env python3
"""Protect calendar edit return targets and compact, timezone-correct timelines.

Uses fresh contexts, synthetic tasks and real UI edits/imports. Every run retains
its report and failure screenshots/trace in a unique directory under --output.
"""
from __future__ import annotations

import argparse
import contextlib
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import traceback
import uuid

from playwright.sync_api import expect, sync_playwright

from performance_playwright import read_workspace
from smoke_playwright import (
    REPO_ROOT, add_task, browser_launch_options, clear_app_data,
    get_task_records, import_payload_replace, local_server, select_language,
    select_view, task_locator,
)
from timezone_playwright import fixture


DAY = '2039-01-23'
MOVED_DAY = '2039-02-09'
NAMES = [f'Calendar return task {index}' for index in range(1, 6)]
ZONE_CASES = [
    ('Kiritimati next-day morning', '2039-01-22T10:15:00.000Z',
     'Pacific/Kiritimati', '2039-01-23', '00:15', '12:15 AM'),
    ('New York afternoon', '2039-01-23T18:30:00.000Z',
     'America/New_York', '2039-01-23', '13:30', '01:30 PM'),
]


def records_by_id(page):
    return {task['id']: task for task in get_task_records(page)}


def assert_reachable_focus(page, target):
    expect(target).to_be_focused()
    expect(target).to_be_in_viewport(ratio=1)
    assert target.evaluate("""node => {
        const rect = node.getBoundingClientRect();
        const hit = document.elementFromPoint(rect.left + rect.width / 2,
            rect.top + rect.height / 2);
        return Boolean(hit && (node === hit || node.contains(hit)));
    }"""), 'Return focus is covered by a sticky bar or another visible control'


def agenda_task(page, task_id):
    return page.locator(f'.calendar-detail-task[data-calendar-task-id="{task_id}"]')


def open_agenda(page, width):
    select_view(page, 'calendar')
    # Mobile intentionally starts on Today, while desktop may reveal the first
    # scheduled month. Use real search to reach the fixture month in both cases.
    page.locator('#searchInput').fill('Calendar return task')
    expect(page.locator(f'.calendar-day [data-calendar-detail-date="{DAY}"], '
                        f'.calendar-day [data-calendar-add-date="{DAY}"]')).not_to_have_count(0)
    page.locator('#searchInput').fill('')
    if width < 780:
        opener = page.locator(f'.calendar-date-number[data-calendar-detail-date="{DAY}"]')
    else:
        opener = page.locator(f'.calendar-more[data-calendar-detail-date="{DAY}"]')
    expect(opener).to_be_visible()
    opener.click()
    expect(page.locator('.calendar-detail-task')).to_have_count(5)


def save_description(page, task_id, description):
    before = records_by_id(page)
    page.locator('#taskDesc').fill(description)
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    expected = {identity: ({**task, 'description': description}
                          if identity == task_id else task)
                for identity, task in before.items()}
    assert records_by_id(page) == expected, 'Description edit changed deadline or unrelated task fields'


def check_calendar_focus(page, url, width, scope_dir, checks):
    clear_app_data(page, url)
    for index, name in enumerate(NAMES):
        add_task(page, name, description='Synthetic calendar return regression',
                 due_date=DAY, due_time=f'{9 + index:02d}:15', reminder_offset='-1')
    before = records_by_id(page)
    identities = {task['name']: identity for identity, task in before.items()}
    task_id = identities[NAMES[2]]
    open_agenda(page, width)
    source = agenda_task(page, task_id)
    source.click()
    expect(page.locator('#taskName')).to_have_value(NAMES[2])
    save_description(page, task_id, 'Saved description without moving the deadline')
    assert_reachable_focus(page, agenda_task(page, task_id))
    assert page.evaluate('scrollY > 100'), 'Saving an agenda edit returned to the top of the month'
    checks.append('Same-date description save returns to its visible agenda task; exact deadline and other records survive')
    page.screenshot(path=str(scope_dir / '01-agenda-save-return.png'))

    # Clean cancellation and explicitly discarded edits must both preserve data.
    cancellation_baseline = read_workspace(page)
    agenda_task(page, task_id).click()
    page.locator('#cancelBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    assert_reachable_focus(page, agenda_task(page, task_id))
    assert read_workspace(page) == cancellation_baseline, 'Clean cancellation wrote task/config data'
    agenda_task(page, task_id).click()
    page.locator('#taskDesc').fill('Discard this unsaved description')
    page.locator('#cancelBtn').click()
    expect(page.locator('#draftDiscardPrompt')).to_be_visible()
    page.locator('#draftDiscardBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    assert_reachable_focus(page, agenda_task(page, task_id))
    assert read_workspace(page) == cancellation_baseline, 'Discarding a calendar draft wrote task/config data'
    checks.append('Clean cancel and dirty-draft discard retain agenda focus and never write task/config data')

    date_heading = page.locator('.calendar-detail-title').inner_text().rsplit(' · ', 1)[0]
    move_before = records_by_id(page)
    agenda_task(page, task_id).click()
    page.locator('#dueDate').fill(MOVED_DAY)
    page.locator('#submitBtn').click()
    expect(page.locator('#taskModal')).to_be_hidden()
    expect(agenda_task(page, task_id)).to_have_count(0)
    expect(page.locator('.calendar-detail-task')).to_have_count(4)
    page.wait_for_function("""({day, heading}) => {
        const active = document.activeElement;
        return Boolean(active && (
            (active.matches('.calendar-detail-title') && active.textContent.startsWith(heading)) ||
            active.dataset.calendarDetailDate === day || active.dataset.calendarAddDate === day));
    }""", arg={'day': DAY, 'heading': date_heading})
    assert_reachable_focus(page, page.locator(':focus'))
    move_after = records_by_id(page)
    expected_instant = f'{MOVED_DAY}T{move_before[task_id]["dueLocalTime"]}:00.000Z'
    expected_task = {**move_before[task_id], 'dueAt': expected_instant,
                     'dueDate': expected_instant, 'dueLocalDate': MOVED_DAY}
    assert move_after == {**move_before, task_id: expected_task}, 'Moving a deadline changed unrelated fields/records'
    checks.append('Cross-month move retains a reachable original-day fallback and changes only the selected deadline')
    page.screenshot(path=str(scope_dir / '02-cross-month-fallback.png'))

    # Desktop month previews are distinct return targets from the agenda rows.
    if width >= 780:
        month_id = identities[NAMES[0]]
        preview = page.locator(f'.calendar-task[data-calendar-task-id="{month_id}"]')
        preview.click()
        save_description(page, month_id, 'Month-preview edit keeps its return target')
        assert_reachable_focus(page, page.locator(f'.calendar-task[data-calendar-task-id="{month_id}"]'))
        checks.append('Desktop month-preview save restores the preview rather than an agenda duplicate or Add task')


def expected_full_deadline(page, instant, zone):
    return page.evaluate("""({instant, zone}) => new Intl.DateTimeFormat('en-US', {
        year:'numeric', month:'short', day:'numeric', hour:'2-digit', minute:'2-digit',
        timeZone:zone
    }).format(new Date(instant))""", {'instant': instant, 'zone': zone})


def check_timeline(page, url, width, scope_dir, checks):
    clear_app_data(page, url)
    payload = [fixture(500 + index, name, instant, zone)
               for index, (name, instant, zone, *_rest) in enumerate(ZONE_CASES)]
    import_payload_replace(page, payload)
    expect(page.locator('#taskModal')).to_be_hidden()
    select_language(page, 'en')
    baseline = get_task_records(page)
    for name, instant, zone, day, clock, _display in ZONE_CASES:
        record = next(task for task in baseline if task['name'] == name)
        assert (record['dueAt'], record['dueDate'], record['dueTimeZone'],
                record['dueLocalDate'], record['dueLocalTime']) == (instant, instant, zone, day, clock), record
    full_labels = {name: task_locator(page, name).locator('.task-date').inner_text()
                   for name, *_rest in ZONE_CASES}
    for name, instant, zone, *_rest in ZONE_CASES:
        assert expected_full_deadline(page, instant, zone) in full_labels[name]
    select_view(page, 'timeline')
    expect(page.locator('.timeline-group')).to_have_count(1)
    group_title = page.evaluate("""day => new Intl.DateTimeFormat('en-US', {
        weekday:'long', month:'short', day:'numeric', year:'numeric', timeZone:'UTC'
    }).format(new Date(day+'T12:00:00Z'))""", DAY)
    expect(page.locator('.timeline-date-title > span').first).to_have_text(group_title)

    for name, instant, zone, _day, _clock, display in ZONE_CASES:
        task = task_locator(page, name)
        date = task.locator('.task-date')
        # Normalize locale-specific spaces, retaining the AM/PM distinction.
        visible_clock = date.locator('.task-clock')
        expect(visible_clock).to_be_visible()
        expect(visible_clock).to_have_attribute('aria-hidden', 'true')
        assert ' '.join(visible_clock.inner_text().split()) == display
        expect(date).to_have_attribute('title', full_labels[name])
        expect(date.locator('.sr-only')).to_have_text(full_labels[name])
        described_ids = (task.get_attribute('aria-describedby') or '').split()
        assert date.get_attribute('id') in described_ids, 'Full deadline was removed from the task accessible description'
        visible = date.evaluate("""node => {
            const copy = node.cloneNode(true);
            copy.querySelectorAll('.sr-only').forEach(child => child.remove());
            return copy.textContent;
        }""")
        assert ' '.join(visible.split()) == display, f'Timeline repeats a date/label next to its clock: {visible!r}'
        assert visible_clock.evaluate("""node => {
            const range = document.createRange(); range.selectNodeContents(node);
            return range.getClientRects().length === 1;
        }"""), 'AM/PM or the clock split across lines'
        relative = task.locator('.status-time-left')
        assert relative.evaluate("""node => {
            const rect = node.getBoundingClientRect();
            return node.classList.contains('sr-only') && rect.width <= 1 && rect.height <= 1;
        }"""), 'Timeline still displays the repeated relative countdown'
        status = task.locator('.status-text')
        expect(status).to_be_visible()
        assert status.inner_text().strip(), 'Timeline removed the short visible deadline status'
    assert get_task_records(page) == baseline, 'Compact timeline formatting rewrote raw deadlines or zones'
    checks.append('Different source zones share their correct civil-day group; compact 12-hour clocks retain AM/PM without wrapping')
    checks.append('Full timezone-correct dates remain in title and the task accessible description; raw instant/time/zone fields stay exact')
    page.screenshot(path=str(scope_dir / '03-timeline-compact-clocks.png'))

    select_view(page, 'list')
    for name, instant, zone, *_rest in ZONE_CASES:
        date = task_locator(page, name).locator('.task-date')
        expect(date).to_contain_text(expected_full_deadline(page, instant, zone))
        assert date.evaluate("""node => {
            const copy = node.cloneNode(true);
            copy.querySelectorAll('.sr-only').forEach(child => child.remove());
            return /2039/.test(copy.textContent);
        }"""), 'Normal list lost its visible full deadline date'
    assert get_task_records(page) == baseline, 'Switching timeline/list changed stored task deadlines'
    checks.append('Normal list still displays full dates; view changes preserve every imported task field')
    page.screenshot(path=str(scope_dir / '04-list-full-dates.png'))


def diagnostics(page):
    return page.evaluate("""() => ({
        active:document.activeElement?.outerHTML, scrollY, viewport:[innerWidth,innerHeight],
        month:document.querySelector('.calendar-title')?.textContent,
        agenda:document.querySelector('.calendar-day-detail')?.innerText,
        taskCount:document.querySelectorAll('.task-item').length,
        timeline:document.querySelector('.timeline-view')?.innerText,
        dialogVisible:document.querySelector('#taskModal')?.style.display
    })""")


def run(args):
    expect.set_options(timeout=10000)
    run_dir = args.output / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8])
    run_dir.mkdir(parents=True)
    inputs = ('index.html', 'vercel.json', 'tools/calendar_focus_return_playwright.py',
              'tools/smoke_playwright.py', 'tools/performance_playwright.py', 'tools/timezone_playwright.py')
    source_hashes = {name: hashlib.sha256((REPO_ROOT / name).read_bytes()).hexdigest() for name in inputs}
    for name in inputs:
        destination = run_dir / 'source-snapshot' / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((REPO_ROOT / name).read_bytes())
    report = {'started_at': datetime.now(timezone.utc).isoformat(), 'source_hashes': source_hashes,
              'passed': False, 'runs': [], 'output': str(run_dir)}
    os.environ['TASK_TRACER_PRODUCTION_HEADERS'] = '1'
    url_override = args.url or os.environ.get('TASK_TRACER_URL')
    server = contextlib.nullcontext(url_override) if url_override else local_server()
    try:
        with server as url, sync_playwright() as playwright:
            options = browser_launch_options() if args.browser == 'chromium' else {'headless': True}
            if args.executable:
                options['executable_path'] = args.executable
            browser = getattr(playwright, args.browser).launch(**options)
            report['browser'] = {'engine': args.browser, 'version': browser.version}
            try:
                for width in args.widths:
                    for case in (['focus', 'timeline'] if args.case == 'all' else [args.case]):
                        scope_dir = run_dir / f'{width}-{case}'
                        scope_dir.mkdir()
                        context = browser.new_context(viewport={'width': width, 'height': 1000 if width >= 780 else 844},
                            locale='en-US', timezone_id='America/Los_Angeles' if case == 'timeline' else 'UTC',
                            reduced_motion='reduce', accept_downloads=True)
                        context.tracing.start(screenshots=True, snapshots=True, sources=False)
                        page = context.new_page()
                        errors = []
                        page.on('pageerror', lambda error: errors.append(str(error)))
                        entry = {'width': width, 'case': case, 'passed': False, 'checks': [], 'page_errors': errors}
                        report['runs'].append(entry)
                        try:
                            check = check_calendar_focus if case == 'focus' else check_timeline
                            check(page, url, width, scope_dir, entry['checks'])
                            assert not errors, errors
                            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Horizontal page overflow'
                            entry['passed'] = True
                            print(f'Calendar return {width}px {case} passed: ' + '; '.join(entry['checks']), flush=True)
                        except Exception:
                            entry['error'] = traceback.format_exc()
                            entry['state'] = diagnostics(page)
                            page.screenshot(path=str(scope_dir / 'failure.png'))
                            (scope_dir / 'failure-state.json').write_text(json.dumps(entry, ensure_ascii=False, indent=2) + '\n')
                            print(f'Calendar return {width}px {case} FAILED:\n{entry["error"]}', flush=True)
                        finally:
                            context.tracing.stop(path=str(scope_dir / 'trace.zip'))
                            context.close()
            finally:
                browser.close()
        current = {name: hashlib.sha256((REPO_ROOT / name).read_bytes()).hexdigest() for name in inputs}
        assert current == source_hashes, 'Source changed during the run; retained scope must be rerun after freeze'
        report['passed'] = all(entry['passed'] for entry in report['runs'])
    except Exception:
        report['error'] = traceback.format_exc()
        raise
    finally:
        report['completed_at'] = datetime.now(timezone.utc).isoformat()
        (run_dir / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({'passed': report['passed'], 'output': str(run_dir)}, ensure_ascii=False), flush=True)
    assert report['passed'], f'Calendar focus/timeline regression failed; retained report: {run_dir / "report.json"}'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=('chromium', 'firefox', 'webkit'), default='chromium')
    parser.add_argument('--case', choices=('all', 'focus', 'timeline'), default='all')
    parser.add_argument('--widths', type=int, nargs='+', default=[1440, 390])
    parser.add_argument('--output', type=Path, default=Path('/tmp/task-tracer-4.13.2-calendar'))
    parser.add_argument('--url')
    parser.add_argument('--executable')
    run(parser.parse_args())
