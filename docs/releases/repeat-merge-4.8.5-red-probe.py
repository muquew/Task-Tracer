import json
from pathlib import Path
import sys
sys.path.insert(0, '/workspace/Task-Tracer/tools')
from playwright.sync_api import expect, sync_playwright
from repeat_lineage_playwright import prepare, edit_future, reopen, row, record
from import_reference_playwright import finish_occurrence
from smoke_playwright import browser_launch_options, local_server, get_task_records, exercise_export_backup, import_payload_replace, select_filter

with local_server() as url, sync_playwright() as p:
    browser=p.chromium.launch(**browser_launch_options())
    context=browser.new_context(accept_downloads=True, reduced_motion='reduce')
    page=context.new_page()
    expect.set_options(timeout=20000)
    errors=[]
    page.on('pageerror', lambda e: errors.append(str(e)))
    try:
        root,old,middle,future=prepare(page,url,length=4,root_zero=True)
        edit_future(page,future)
        row(page,middle).locator('[data-action="edit"]').click()
        page.locator('#taskName').fill('Unique middle occurrence')
        page.locator('#submitBtn').click()
        expect(page.locator('#taskModal')).to_be_hidden()
        reopen(page,old)
        before=get_task_records(page)
        incoming={**record(page,middle),'description':'Imported replacement description'}
        page.locator('#openMenuBtn').click()
        with page.expect_file_chooser() as chooser:
            page.locator('#importBtn').click()
        chooser.value.set_files({'name':'synthetic-merge-middle.json','mimeType':'application/json',
                                'buffer':json.dumps([incoming]).encode()})
        expect(page.locator('#mergeImportMode')).to_be_visible()
        page.locator('#mergeImportMode').check()
        expect(page.locator('.import-conflict-select')).to_have_count(1)
        page.locator('.import-conflict-select').select_option('replace')
        page.locator('#submitBtn').click()
        expect(page.locator('#taskModal')).to_be_hidden()
        merged=get_task_records(page)
        assert len(merged)==len(before) and all(t['id']!=middle for t in merged)
        backup=exercise_export_backup(page)
        import_payload_replace(page,backup)
        select_filter(page,'all')
        roundtrip=get_task_records(page)
        finish_occurrence(page,old)
        after=get_task_records(page)
        out={'root':root,'old':old,'replaced_middle':middle,'future':future,
             'before':before,'after_merge':merged,'after_roundtrip':roundtrip,
             'after_complete':after,'count_before_complete':len(roundtrip),
             'count_after_complete':len(after),'pageerrors':errors,
             'passed':len(after)==len(roundtrip)}
        Path('/tmp/task-tracer-merge-chain-probe.json').write_text(json.dumps(out,indent=2))
        print(json.dumps({k:out[k] for k in ('root','old','replaced_middle','future','count_before_complete','count_after_complete','pageerrors','passed')}))
        assert out['passed'],'Reopening/completing older nonroot occurrence created a duplicate future after merge replacement roundtrip'
    finally:
        context.close()
        browser.close()
