from pathlib import Path
import sys,json,hashlib,traceback
ROOT=Path('/workspace/Task-Tracer');OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
import accessibility_i18n_audit as audit
from smoke_playwright import local_server,browser_launch_options
from playwright.sync_api import sync_playwright
index_sha=hashlib.sha256((ROOT/'index.html').read_bytes()).hexdigest()
helper=(ROOT/'tools/accessibility_i18n_audit.py').read_bytes();(OUT/'helper-at-import.py').write_bytes(helper)
original=audit.assert_focus_visible
seen=[]
def observed(page,selector,label):
    failure=None
    try:
        original(page,selector,label)
    except AssertionError:
        failure=traceback.format_exc()
    if selector=='#quickAddInput':
        value=page.locator(selector).evaluate("""e=>{const w=e.closest('.quick-add-input-wrap'),details=n=>{const c=getComputedStyle(n),b=n.getBoundingClientRect();return {background:c.backgroundColor,outline:c.outline,outlineWidth:c.outlineWidth,outlineStyle:c.outlineStyle,outlineColor:c.outlineColor,boxShadow:c.boxShadow,opacity:c.opacity,visibility:c.visibility,display:c.display,visible:n.checkVisibility({opacityProperty:true,visibilityProperty:true}),hiddenAncestor:!!n.closest('[hidden],[inert],[aria-hidden=true]'),rect:{x:b.x,y:b.y,w:b.width,h:b.height}}};return {inputFocused:document.activeElement===e,readOnly:e.readOnly,inputFocusVisible:e.matches(':focus-visible'),wrapperFocusWithin:w.matches(':focus-within'),input:details(e),wrapper:details(w),viewport:{w:innerWidth,h:innerHeight}}}""")
        value.update({'label':label,'source_index_sha256':index_sha,'helper_at_import_sha256':hashlib.sha256(helper).hexdigest(),'original_assertion_passed':failure is None,'original_assertion_error':failure})
        seen.append(value);(OUT/'focused-input-and-wrapper.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');page.screenshot(path=str(OUT/'visible-wrapper-focus.png'),animations='allow')
    if failure:raise AssertionError(failure)
audit.assert_focus_visible=observed
with local_server() as url:
    with sync_playwright() as p:
        browser=p.chromium.launch(**browser_launch_options())
        try:
            audit.audit_scaled_surfaces(browser,url,audit.find_axe_source().read_text(),{'width':1280,'height':720})
        except AssertionError:
            (OUT/'original-error.txt').write_text(traceback.format_exc())
            print('Original focus assertion failure retained; actual wrapper captured.')
        finally:browser.close()
(OUT/'session.json').write_text(json.dumps({'browser_closed':True,'server_closed':True,'observations':len(seen),'scope':'Original scaled function and assertions retained; wrapper observes exact input focus failure, no threshold bypass.'},indent=2)+'\n')
