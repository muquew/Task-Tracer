"""Shared ime input fixtures and assertions; no test entry point."""
from __future__ import annotations

def key(locator, value, mode, event_type='keydown'):
    result = locator.evaluate("""(input, options) => {
        const event = new KeyboardEvent(options.type, {
            key: options.key, bubbles: true, cancelable: true,
            isComposing: options.mode === 'flag',
            keyCode: options.mode === 'legacy' ? 229 : 0
        });
        input.dispatchEvent(event);
        return {prevented: event.defaultPrevented, composing: event.isComposing, keyCode: event.keyCode};
    }""", {'key': value, 'mode': mode, 'type': event_type})
    if mode == 'flag':
        assert result['composing']
    if mode == 'legacy':
        assert result['keyCode'] == 229
    assert not result['prevented'], f'Application consumed composition key {value}: {result}'

def compose(locator, active):
    locator.dispatch_event('compositionstart' if active else 'compositionend', {'data': '中文'})
