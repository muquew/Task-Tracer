#!/usr/bin/env python3
"""Verify or refresh the non-executable translation fallback embedded in HTML."""
from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_ID = 'bundledTranslations'
SCRIPTS = re.compile(r'<script\b[^>]*>(?P<content>.*?)</script\s*>', re.DOTALL | re.IGNORECASE)
MAIN_PREFIX = re.compile(r'\s*\(function\s*\(\s*\)\s*\{\s*const\s+CONFIG\s*=')


class ScriptAttributes(HTMLParser):
    def __init__(self, opening_tag: str):
        super().__init__()
        self.attributes: dict[str, str | None] = {}
        self.feed(opening_tag)

    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            self.attributes = dict(attrs)


def script_attributes(match: re.Match[str]) -> dict[str, str | None]:
    opening = match.group(0).split('>', 1)[0] + '>'
    return ScriptAttributes(opening).attributes


def main_script(source: str) -> re.Match[str]:
    matches = [match for match in SCRIPTS.finditer(source) if MAIN_PREFIX.match(match.group('content'))]
    if len(matches) != 1:
        raise AssertionError('Expected exactly one main application IIFE containing CONFIG')
    return matches[0]


def validate_translation_tree(value, label: str) -> None:
    if not isinstance(value, dict):
        raise AssertionError(f'{label} must be a translation object')
    for key, item in value.items():
        if isinstance(item, dict):
            validate_translation_tree(item, f'{label}.{key}')
        elif not isinstance(item, str):
            raise AssertionError(f'{label}.{key} must contain strings or translation objects')


def expected_bundle(source: str) -> dict:
    runtime = main_script(source).group('content')
    versions = re.findall(r'\bRESOURCE_VERSION\s*:\s*[\'"]([^\'"]+)[\'"]', runtime)
    if len(versions) != 1:
        raise AssertionError('Expected exactly one CONFIG.I18N.RESOURCE_VERSION declaration')
    configured = re.search(r'\bLANGUAGES\s*:\s*\[(.*?)\]', runtime, re.DOTALL)
    if configured is None:
        raise AssertionError('Could not find CONFIG.LANGUAGES')
    languages = re.findall(r'\bcode\s*:\s*[\'"]([^\'"]+)[\'"]', configured.group(1))
    if not {'en', 'zh-CN'}.issubset(languages) or len(languages) != len(set(languages)):
        raise AssertionError('Configured languages must include unique en and zh-CN entries')
    resources = {}
    for code in languages:
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9-]*', code):
            raise AssertionError(f'Invalid configured language code: {code}')
        path = ROOT / 'resources' / f'{code}.json'
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as error:
            raise AssertionError(f'Could not read translation resource {code}: {error}') from error
        validate_translation_tree(data, code)
        resources[code] = data
    return {'resourceVersion': versions[0], 'languages': resources}


def serialize_bundle(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(',', ':'), allow_nan=False).replace('<', '\\u003c')


def bundled_script(source: str) -> re.Match[str] | None:
    matches = [match for match in SCRIPTS.finditer(source) if script_attributes(match).get('id') == BUNDLE_ID]
    if len(matches) > 1:
        raise AssertionError('Bundled translations must have exactly one data block')
    return matches[0] if matches else None


def check(write: bool = False) -> None:
    index = ROOT / 'index.html'
    source = index.read_text(encoding='utf-8')
    expected = expected_bundle(source)
    block = bundled_script(source)
    if write:
        rendered = f'<script type="application/json" id="{BUNDLE_ID}">{serialize_bundle(expected)}</script>'
        if block is not None and block.end() <= main_script(source).start():
            source = source[:block.start()] + rendered + source[block.end():]
        else:
            if block is not None:
                end = block.end() + (1 if source[block.end():].startswith('\n') else 0)
                source = source[:block.start()] + source[end:]
            insertion = main_script(source).start()
            source = source[:insertion] + rendered + '\n' + source[insertion:]
        index.write_text(source, encoding='utf-8')
        block = bundled_script(source)
    if block is None:
        raise AssertionError('Bundled translations are missing. Run python3 tools/translation_fallback.py --write')
    attributes = script_attributes(block)
    if attributes.get('type') != 'application/json' or 'src' in attributes:
        raise AssertionError('Bundled translations must be inline non-executable application/json data')
    if block.end() > main_script(source).start():
        raise AssertionError('Bundled translations must appear before the main application IIFE')
    text = block.group('content')
    if '<' in text:
        raise AssertionError('Bundled translation data must encode every < as \\u003c')
    try:
        actual = json.loads(text)
    except json.JSONDecodeError as error:
        raise AssertionError(f'Bundled translations are not valid JSON: {error}') from error
    if not isinstance(actual, dict) or set(actual) != {'resourceVersion', 'languages'}:
        raise AssertionError('Bundled translations must contain only resourceVersion and languages')
    if actual['resourceVersion'] != expected['resourceVersion']:
        raise AssertionError('Bundled translation resource version is stale. Run python3 tools/translation_fallback.py --write')
    if not isinstance(actual['languages'], dict) or set(actual['languages']) != set(expected['languages']):
        raise AssertionError('Bundled languages must match CONFIG.LANGUAGES')
    for code, data in expected['languages'].items():
        if actual['languages'][code] != data:
            raise AssertionError(f'Bundled {code} differs from resources/{code}.json. Run python3 tools/translation_fallback.py --write')
    print('Bundled translation fallback matches resource files and version')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='Generate or replace the compact translation data block')
    check(parser.parse_args().write)
