"""Canonical repository paths and the explicit source-to-public-file contract."""
from __future__ import annotations

from html.parser import HTMLParser
import json
from pathlib import Path, PurePosixPath
import subprocess
from urllib.parse import unquote, urlsplit

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPO_ROOT / 'src'
SOURCE_HTML = SOURCE_ROOT / 'index.html'
APP_RUNTIME = SOURCE_ROOT / 'app/application.js'
PUBLIC_ROOT = REPO_ROOT / 'public'
SITE_ROOT = REPO_ROOT / 'dist/site'


def relative_path(name: str) -> str:
    if not isinstance(name, str) or not name or any(char in name for char in ('\\', '\x00', ':', '?', '#')):
        raise ValueError(f'Expected a safe relative file path: {name!r}')
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or path.as_posix() != name or name == '.':
        raise ValueError(f'Expected a canonical relative file path: {name!r}')
    return name


def site_config(root: Path | None = None) -> dict:
    base = REPO_ROOT if root is None else Path(root)
    data = json.loads((base / 'config/site-files.json').read_text(encoding='utf-8'))
    if not isinstance(data, dict) or data.get('schema_version') != 1:
        raise ValueError('Expected site-files schema_version 1')
    targets: set[str] = set()
    for group in ('application', 'downloads'):
        entries = data.get(group)
        if not isinstance(entries, dict) or (group == 'application' and not entries):
            raise ValueError(f'Site file group must be a source-to-URL mapping: {group}')
        for source, target in entries.items():
            relative_path(source)
            relative_path(target)
            if target.split('/')[0] in {'src', 'scripts', 'tests', 'tools', 'config', 'node_modules', '.git', '.github', 'styles', 'dist'}:
                raise ValueError(f'Developer path cannot be published: {target}')
            if target in targets:
                raise ValueError(f'Duplicate site file target: {target}')
            targets.add(target)
    return data


def distribution_sources(root: Path | None = None) -> dict[str, str]:
    return {target: source for source, target in site_config(root)['application'].items()}


def site_sources(root: Path | None = None) -> dict[str, str]:
    config = site_config(root)
    return {target: source for group in ('application', 'downloads') for source, target in config[group].items()}


def source_path(url: str, root: Path | None = None) -> Path:
    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc or parsed.fragment:
        raise ValueError(f'Expected a local asset URL: {url!r}')
    target = unquote(parsed.path).removeprefix('./')
    relative_path(target)
    mapping = site_sources(root)
    if target not in mapping:
        raise ValueError(f'Asset is missing from config/site-files.json: {target}')
    return (REPO_ROOT if root is None else Path(root)) / mapping[target]


def read_source_html(root: Path | None = None) -> str:
    return source_path('index.html', root).read_text(encoding='utf-8')


def ordered_script_urls(html: str) -> list[str]:
    class Scripts(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.urls: list[str] = []

        def handle_starttag(self, tag, attributes):
            if tag == 'script':
                attrs = dict(attributes)
                if attrs.get('src'):
                    self.urls.append(attrs['src'])

    parser = Scripts()
    parser.feed(html)
    return parser.urls


def read_application_source(root: Path | None = None) -> str:
    html = read_source_html(root)
    return '\n'.join([html, *(source_path(url, root).read_text(encoding='utf-8')
                             for url in ordered_script_urls(html))])


def ensure_site(root: Path | None = None) -> Path:
    base = REPO_ROOT if root is None else Path(root)
    subprocess.run(['node', str(base / 'scripts/build-site.mjs')], cwd=base, check=True)
    return base / 'dist/site'
