#!/usr/bin/env python3
"""Instrument unchanged audit stages and fail a finite-animation wait after 10s."""
import json
from pathlib import Path
import re
import runpy
import sys
import time

from playwright.sync_api import Page

entry, *arguments = sys.argv[1:]
sys.path.insert(0, str(Path(entry).parent))
sys.argv = [entry, *arguments]
native_wait = Page.wait_for_function
native_evaluate = Page.evaluate
stage = {'label': 'setup'}

def function_wait(self, expression, *, arg=None, polling=None, timeout=None):
    function = re.match(r'^\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>', expression)
    if not function and not re.match(r'^\s*(?:async\s+)?function\b', expression):
        expression = '() => (' + expression + ')'
    return native_wait(self, expression, arg=arg, polling=polling, timeout=timeout)

BOUNDED_ANIMATIONS = '''async () => {
    const describe = animations => animations.map(animation => {
        const effect = animation.effect;
        const target = effect?.target;
        const style = target ? getComputedStyle(target) : null;
        const box = target?.getBoundingClientRect();
        return {type:animation.constructor.name, name:animation.animationName || animation.transitionProperty || '',
            playState:animation.playState,pending:animation.pending,currentTime:animation.currentTime,startTime:animation.startTime,
            playbackRate:animation.playbackRate,timing:effect?.getTiming(),computedTiming:effect?.getComputedTiming(),
            target:{tag:target?.tagName,id:target?.id,className:typeof target?.className==='string'?target.className:target?.className?.baseVal,
                pseudoElement:effect?.pseudoElement,connected:target?.isConnected,hidden:target?.hidden,inert:target?.inert,
                visibility:style?.visibility,display:style?.display,animationPlayState:style?.animationPlayState,
                width:box?.width,height:box?.height},documentVisibility:document.visibilityState};
    });
    const all = document.getAnimations();
    const finite = all.filter(animation => animation.effect?.getTiming().iterations !== Infinity);
    const before = describe(all);
    let timer;
    let completed;
    try {
        completed = await Promise.race([
            Promise.all(finite.map(animation => animation.finished.catch(() => {}))).then(() => true),
            new Promise(resolve => {timer=setTimeout(() => resolve(false),10000);})
        ]);
    } finally {clearTimeout(timer);}
    const result={completed,limit_ms:10000,finiteCount:finite.length,before,after:describe(document.getAnimations()),visibility:document.visibilityState};
    return JSON.parse(JSON.stringify(result,(_key,value)=>typeof value==='number'&&!Number.isFinite(value)?String(value):value));
}'''

def diagnostic_evaluate(self, expression, arg=None):
    if isinstance(expression,str) and 'getAnimations()' in expression and 'Promise.all' in expression and '.finished.catch' in expression:
        print('ANIMATION_WAIT_START '+stage['label'],flush=True)
        result = native_evaluate(self,BOUNDED_ANIMATIONS)
        print('ANIMATION_WAIT_RESULT '+json.dumps({'label':stage['label'],**result},ensure_ascii=False),flush=True)
        if not result['completed']:
            raise AssertionError('Finite-animation wait exceeded 10 seconds; exact animation state printed above')
        return None
    return native_evaluate(self,expression,arg)

Page.wait_for_function = function_wait
Page.evaluate = diagnostic_evaluate
namespace = runpy.run_path(entry,run_name='__protection_diagnostic__')
globals_ = namespace['main'].__globals__
for name in ('audit_page_state','run_axe','assert_accessibility_baseline','assert_focus_baseline','assert_layout'):
    original = globals_[name]
    def wrap(function, phase):
        def wrapped(*args,**kwargs):
            label = args[-1] if args and isinstance(args[-1],str) else stage['label']
            if phase=='audit_page_state': stage['label']=label
            started=time.monotonic()
            print('AUDIT_PHASE_START '+phase+' '+label,flush=True)
            result=function(*args,**kwargs)
            print('AUDIT_PHASE_DONE '+phase+' '+label+' '+str(round(time.monotonic()-started,3))+'s',flush=True)
            return result
        return wrapped
    globals_[name]=wrap(original,name)
print('External diagnostic: original rules and assertions retained; no animation finish/cancel and no CSP/SW changes',flush=True)
raise SystemExit(namespace['main']())
