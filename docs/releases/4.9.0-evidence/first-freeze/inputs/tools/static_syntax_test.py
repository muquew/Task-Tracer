#!/usr/bin/env python3
"""Exercise JavaScript comment scanning and scoped civil-date static guards."""
from __future__ import annotations

from pathlib import Path
import re

from translation_fallback import main_script
from validate_static import contains_js_comment, validate_due_date_semantics


ROOT = Path(__file__).resolve().parents[1]
COMMENT_FREE = {
    'plain expression': 'const value = 1 + 2;',
    'single-quoted URL': "const url = 'https://example.test/path';",
    'double-quoted comment text': 'const source = "/* text */ // text";',
    'escaped quote in string': r"const source = 'can\'t // become a comment';",
    'template text': 'const url = `https://example.test/*path*/`;',
    'regex apostrophe': "const expression = /'/;",
    'regex double quote': 'const expression = /"/;',
    'regex backtick': 'const expression = /`/;',
    'regex slash character class': 'const expression = /[//]/;',
    'regex quote character class': '''const expression = /["'`/]+/g;''',
    'regex escaped slash': r'const expression = /https?:\/\/[^/]+\/path/;',
    'regex escaped backslash': r'const expression = /\\["\']/;',
    'regex escaped closing bracket': r'const expression = /[\]/"\']/;',
    'division': 'const value = total / count / 2;',
    'division followed by regex': '''const value = total / /[/'"]/.exec(text).length;''',
    'regex followed by division': '''const value = /[/'"]/.exec(text).length / 2;''',
    'division assignment followed by regex': '''total /= /[/'"]/.exec(text).length;''',
    'return regex': 'function match(text) { return /[//]/.test(text); }',
    'arrow regex': 'const match = text => /[//]/.test(text);',
    'regex argument': 'const value = match(/[//]/, text);',
    'regex statement after if condition': '''if (ready) /["'`/]/.test(text);''',
    'object then division': 'const value = {count: 1} / 2;',
    'function expression then division': 'const value = function () {} / 2;',
    'async function expression then division': 'const value = async function () {} / 2;',
    'class expression then division': 'const value = class {} / 2;',
    'arrow block then division': 'const value = (() => {}) / 2;',
    'regex after function declaration': 'function match() {} /[//]/.test(text);',
    'regex after class declaration': 'class Example {} /[//]/.test(text);',
    'template interpolation regex': 'const value = `https://${/[//]/.test(text)}/path`;',
    'nested template interpolation': 'const value = `https://${`inner ${value}`}/path`;',
}
COMMENTS = {
    'line comment': '// actual comment\nconst value = 1;',
    'block comment': '/* actual comment */ const value = 1;',
    'division then line comment': 'const value = total / count; // actual comment',
    'division then block comment': 'const value = total / count; /* actual comment */',
    'regex apostrophe then line comment': "const expression = /'/; // actual comment",
    'regex quote then block comment': 'const expression = /"/; /* actual comment */',
    'regex quote with flag then line comment': 'const expression = /"/g; // actual comment',
    'regex slash class then line comment': 'const expression = /[//]/; // actual comment',
    'regex escaped slash then block comment': r'const expression = /https?:\/\//; /* actual comment */',
    'block comment in template interpolation': 'const value = `text ${1 /* actual comment */}`;',
    'line comment in template interpolation': 'const value = `text ${1 // actual comment\n}`;',
    'comment in nested template interpolation': 'const value = `text ${`inner ${1 /* actual */}`}`;',
}


def check_comments() -> None:
    for label, source in COMMENT_FREE.items():
        assert not contains_js_comment(source), f'Legal JavaScript was mistaken for a comment: {label}'
        for suffix in ('\n// actual comment', '\n/* actual comment */'):
            assert contains_js_comment(source + suffix), f'Comment after legal JavaScript was missed: {label}'
    for label, source in COMMENTS.items():
        assert contains_js_comment(source), f'Real JavaScript comment was missed: {label}'
    print(f'Static syntax passed: {len(COMMENT_FREE)} legal JavaScript samples and explicit comment rejection')


def date_errors(source: str) -> list[str]:
    errors: list[str] = []
    validate_due_date_semantics(source, errors)
    return errors


def check_due_date_guard() -> None:
    source = (ROOT / 'index.html').read_text(encoding='utf-8')
    runtime = main_script(source).group('content')
    matches = list(re.finditer(r'(?ms)^([ \t]*)function normalizeDueDateValue\(value\) \{\n.*?^\1\}', runtime))
    assert len(matches) == 1, 'Expected one current civil-date normalization implementation'
    implementation = matches[0].group()
    assert source.count(implementation) == 1
    assert not date_errors(source), 'The current neutral-UTC date implementation must pass'

    decoy = implementation.replace('function normalizeDueDateValue(', 'function unrelatedDueDateExample(', 1)
    mutations = {
        'local year getter': ('date.getUTCFullYear()', 'date.getFullYear()'),
        'local month getter': ('date.getUTCMonth()', 'date.getMonth()'),
        'local day getter': ('date.getUTCDate()', 'date.getDate()'),
        'missing year comparison': ('date.getUTCFullYear() !== year || ', ''),
        'missing month comparison': ('date.getUTCMonth() !== month - 1 || ', ''),
        'missing day comparison': (' || date.getUTCDate() !== day', ''),
        'local date construction': ('`${text}T12:00:00.000Z`', '`${text}T12:00:00.000`'),
    }
    for label, (original, replacement) in mutations.items():
        assert implementation.count(original) == 1, f'Expected one fixture target: {label}'
        changed = implementation.replace(original, replacement, 1) + '\n' + decoy
        broken = source.replace(implementation, changed, 1)
        assert date_errors(broken), f'The scoped date guard accepted {label} despite the unrelated complete UTC example'

    missing = source.replace(implementation, decoy, 1)
    assert date_errors(missing), 'An unrelated UTC function must not satisfy a missing date normalizer'
    print(f'Static syntax passed: neutral-UTC normalization and {len(mutations) + 1} scoped regression mutations')


def run() -> None:
    check_comments()
    check_due_date_guard()


if __name__ == '__main__':
    run()
