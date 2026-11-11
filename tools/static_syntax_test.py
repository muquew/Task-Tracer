#!/usr/bin/env python3
"""Exercise JavaScript comment scanning and scoped civil-date static guards."""
from __future__ import annotations

from pathlib import Path
import json
import re
import tempfile
from unittest.mock import patch

from translation_fallback import main_script
import validate_static as validation
from validate_static import contains_css_comment, contains_js_comment, validate_due_date_semantics


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


def check_stylesheet_guards() -> None:
    license_comment = '/*! tailwindcss | MIT License */'
    assert contains_css_comment(license_comment), 'Inline CSS must continue rejecting license comments'
    assert not contains_css_comment(license_comment, allow_license=True), 'External compiler/license comments must be preserved'
    assert contains_css_comment(license_comment + '\n/* ordinary comment */', allow_license=True)
    assert contains_css_comment('/*! unterminated license comment', allow_license=True)
    assert not contains_css_comment('a::after { content: "/* literal text */"; }')

    source = (ROOT / 'index.html').read_text(encoding='utf-8')
    delivered = (ROOT / 'resources/workspace.css').read_text(encoding='utf-8')
    href = f'./resources/workspace.css?v={validation.app_version(source)}'
    assert f'href="{href}"' in source, 'The app must link its versioned delivered stylesheet'
    with tempfile.TemporaryDirectory(prefix='task-tracer-stylesheet-guards-') as folder:
        root = Path(folder)
        css = root / 'resources/workspace.css'
        css.parent.mkdir()
        css.write_text(delivered, encoding='utf-8')
        with patch.object(validation, 'REPO_ROOT', root):
            assets = validation.stylesheet_assets(source)
            assert assets[href] == css
            assert validation.loaded_stylesheet_source(source).endswith(delivered)

            def errors_for(validator, html=source):
                errors = []
                validator(html, errors)
                return errors

            for validator in (validation.validate_task_state_styles, validation.validate_accessibility_styles,
                              validation.validate_loaded_code_is_comment_free):
                assert not errors_for(validator), errors_for(validator)

            decoy = source.replace('</head>', '<script type="application/json">' + json.dumps(delivered) + '</script></head>', 1)
            mutations = (
                ('task status selector', delivered.replace('.task-item.status-safe', '.task-item.missing-status'),
                 validation.validate_task_state_styles, 'Missing task status CSS selector for status-safe'),
                ('completed task decoration', re.sub(r'text-decoration-line:\s*line-through', 'text-decoration-line:none', delivered),
                 validation.validate_task_state_styles, 'Completed task names must be struck through'),
                ('keyboard focus selector', delivered.replace(':focus-visible', ':hover'),
                 validation.validate_accessibility_styles, 'Interactive controls must expose a visible keyboard focus style'),
                ('keyboard focus token', delivered.replace('--focus-ring', '--missing-ring'),
                 validation.validate_accessibility_styles, 'Interactive controls must expose a visible keyboard focus style'),
                ('reduced motion', delivered.replace('prefers-reduced-motion', 'removed-reduced-motion'),
                 validation.validate_accessibility_styles, 'CSS must respect prefers-reduced-motion'),
            )
            for label, changed, validator, expected in mutations:
                assert changed != delivered, f'Missing stylesheet regression fixture target: {label}'
                css.write_text(changed, encoding='utf-8')
                errors = errors_for(validator, decoy)
                assert any(expected in error for error in errors), f'Linked stylesheet guard accepted {label}: {errors}'
            css.write_text(delivered + '\n' + license_comment, encoding='utf-8')
            assert not errors_for(validation.validate_loaded_code_is_comment_free)
            css.write_text(delivered + '\n/* ordinary external comment */', encoding='utf-8')
            assert any('Linked stylesheet' in error for error in errors_for(validation.validate_loaded_code_is_comment_free))
            css.write_text(delivered, encoding='utf-8')
            inline = source.replace('</head>', '<style>' + license_comment + '</style></head>', 1)
            assert any('style blocks' in error for error in errors_for(validation.validate_loaded_code_is_comment_free, inline))

            for href in ('https://outside.invalid/style.css', '//outside.invalid/style.css', '../outside.css',
                         './%2e%2e/outside.css', './resources/../outside.css', './resources\\outside.css',
                         '/absolute.css', './resources/missing.css'):
                try:
                    validation.stylesheet_assets(f'<link rel="stylesheet" href="{href}">')
                except AssertionError:
                    pass
                else:
                    raise AssertionError(f'Unsafe or missing stylesheet source was accepted: {href}')
            css.unlink()
            css.symlink_to(ROOT / 'resources/workspace.css')
            try:
                validation.stylesheet_assets(source)
            except AssertionError:
                pass
            else:
                raise AssertionError('Linked stylesheet source symbolic link was accepted')
    print('Static syntax passed: preserved CSS licenses, linked-asset safety, and five real stylesheet regression mutations')


def date_errors(source: str) -> list[str]:
    errors: list[str] = []
    validate_due_date_semantics(source, errors)
    return errors


def check_script_guards() -> None:
    with tempfile.TemporaryDirectory(prefix='task-tracer-script-guards-') as folder:
        root = Path(folder)
        script = root / 'resources/workbench.js'
        script.parent.mkdir()
        script.write_text('window.syntheticWorkbench = true;\n', encoding='utf-8')
        reference = './resources/workbench.js?v=5.0.0'
        tag = f'<script src="{reference}"></script>'
        with patch.object(validation, 'REPO_ROOT', root):
            assert validation.script_assets(tag) == {reference: script}
            broken = [
                '<script src=""></script>',
                '<script src="./resources/workbench.js" src="./resources/workbench.js"></script>',
                tag.replace('<script ', '<script type="module" type="text/javascript" ', 1),
                tag + tag,
                *[tag.replace('<script ', f'<script {attribute} ', 1) for attribute in ('async', 'defer', 'nomodule', 'type="module"')],
                *[f'<script src="{source}"></script>' for source in (
                    'https://outside.invalid/workbench.js', '//outside.invalid/workbench.js',
                    '../outside.js', './%2e%2e/outside.js', './resources/../outside.js',
                    './resources\\outside.js', '/absolute.js', './resources/missing.js',
                    './resources/workbench.js#fragment', 'data:text/javascript,alert(1)',
                )],
            ]
            for html in broken:
                try:
                    validation.script_assets(html)
                except AssertionError:
                    pass
                else:
                    raise AssertionError(f'Unsafe, repeated or unordered linked script was accepted: {html!r}')
            script.unlink()
            script.symlink_to(ROOT / 'index.html')
            try:
                validation.script_assets(tag)
            except AssertionError:
                pass
            else:
                raise AssertionError('A linked script source symbolic link was accepted')
    print('Static syntax passed: ordered classic workbench and linked-script source safety guards')


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
    check_stylesheet_guards()
    check_script_guards()
    check_due_date_guard()


if __name__ == '__main__':
    run()
