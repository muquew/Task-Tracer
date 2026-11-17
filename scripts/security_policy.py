#!/usr/bin/env python3
"""Verify or refresh deployment CSP hashes after changing inline application code."""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
from pathlib import Path
from .translation_fallback import SCRIPTS, script_attributes

ROOT = Path(__file__).resolve().parents[1]


def expected_script_policy() -> str:
    source = (ROOT / 'src/index.html').read_text(encoding='utf-8')
    scripts = [match.group('content') for match in SCRIPTS.finditer(source) if 'src' not in script_attributes(match)]
    if not scripts:
        raise AssertionError('No application scripts were found')
    hashes = ["'sha256-" + base64.b64encode(hashlib.sha256(script.encode()).digest()).decode() + "'" for script in scripts]
    return "script-src 'self' " + ' '.join(hashes)


def check(write: bool = False) -> None:
    path = ROOT / 'vercel.json'
    config = json.loads(path.read_text())
    matches = [header for route in config['headers'] if route['source'] == '/(.*)'
               for header in route['headers'] if header['key'].lower() == 'content-security-policy']
    if len(matches) != 1:
        raise AssertionError('Expected one catch-all deployment CSP header')
    header = matches[0]
    directives = [part.strip() for part in header['value'].split(';') if part.strip()]
    expected = expected_script_policy()
    actual = next((part for part in directives if part.startswith('script-src ')), '')
    standalone_path = ROOT / 'config/standalone-vercel.json'
    standalone = json.loads(standalone_path.read_text())
    if (standalone.get('framework', 'auto') is not None or standalone.get('outputDirectory') != '.'
            or standalone.get('buildCommand') != '' or standalone.get('installCommand') != ''):
        raise AssertionError('Standalone Vercel configuration must serve the extracted app directly')
    if not write:
        if actual != expected or "script-src-attr 'none'" not in directives:
            raise AssertionError('Deployment CSP is stale. Run python3 -m scripts.security_policy --write and review both Vercel configs')
        if standalone.get('headers') != config.get('headers'):
            raise AssertionError('Hosting and standalone security headers must match')
    else:
        directives = [part for part in directives if not part.startswith(('script-src ', 'script-src-attr '))]
        directives.extend([expected, "script-src-attr 'none'"])
        header['value'] = '; '.join(directives)
        path.write_text(json.dumps(config, indent=2) + '\n')
        standalone['headers'] = config['headers']
        standalone_path.write_text(json.dumps(standalone, indent=2) + '\n')
    print('Deployment CSP hashes match application scripts')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='Refresh script hashes in vercel.json')
    check(parser.parse_args().write)
