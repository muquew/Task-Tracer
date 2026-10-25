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
        const effect=animation.effect,target=effect?.target,style=target?getComputedStyle(target):null;
        return {type:animation.constructor.name,name:animation.animationName||animation.transitionProperty||'',
            playState:animation.playState,pending:animation.pending,currentTime:animation.currentTime,startTime:animation.startTime,
            timing:effect?.getTiming(),computedTiming:effect?.getComputedTiming(),
            target:{tag:target?.tagName,id:target?.id,className:typeof target?.className==='string'?target.className:target?.className?.baseVal,
                connected:target?.isConnected,visibility:style?.visibility,display:style?.display,animationPlayState:style?.animationPlayState},
            documentVisibility:document.visibilityState};
    });
    const current = () => document.getAnimations().filter(animation => animation.effect?.getTiming().iterations !== Infinity
        && (animation.pending || !['idle','finished'].includes(animation.playState)));
    const before=describe(document.getAnimations()),started=performance.now();
    let timer,done=false,stableFrames=0,lastActiveCount=current().length;
    const settle=new Promise(resolve=>{
        const sample=()=>{
            if(done)return;
            lastActiveCount=current().length;
            stableFrames=lastActiveCount===0?stableFrames+1:0;
            if(stableFrames>=2)resolve(true);
            else requestAnimationFrame(sample);
        };
        requestAnimationFrame(sample);
    });
    let completed;
    try {
        completed=await Promise.race([settle,new Promise(resolve=>{timer=setTimeout(()=>resolve(false),10000);})]);
    } finally {done=true;clearTimeout(timer);}
    const result={completed,limit_ms:10000,waited_ms:performance.now()-started,stableFrames,lastActiveCount,
        before,after:describe(document.getAnimations()),visibility:document.visibilityState};
    return JSON.parse(JSON.stringify(result,(_key,value)=>typeof value==='number'&&!Number.isFinite(value)?String(value):value));
}'''

def diagnostic_evaluate(self, expression, arg=None):
    if isinstance(expression,str) and 'getAnimations()' in expression and 'Promise.all' in expression and '.finished.catch' in expression:
        print('SETTLE_START '+stage['label'],flush=True)
        result = native_evaluate(self,BOUNDED_ANIMATIONS)
        print(('SETTLE_DONE ' if result['completed'] else 'SETTLE_TIMEOUT ')+json.dumps({'label':stage['label'],**({key:result[key] for key in ('completed','waited_ms','stableFrames','lastActiveCount')} if result['completed'] else result)},ensure_ascii=False),flush=True)
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
            if phase in ('audit_page_state','run_axe'): print('AUDIT_PHASE_START '+phase+' '+label,flush=True)
            result=function(*args,**kwargs)
            if phase in ('audit_page_state','run_axe'): print('AUDIT_PHASE_DONE '+phase+' '+label+' '+str(round(time.monotonic()-started,3))+'s',flush=True)
            return result
        return wrapped
    globals_[name]=wrap(original,name)
print('External settle harness: live finite running/pending/paused animations, two stable frames, 10s deadline; original assertions/CSP/SW retained',flush=True)
raise SystemExit(namespace['main']())
