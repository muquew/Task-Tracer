"""Explicit source closure for disposable release-validation repositories."""
from __future__ import annotations
from tests.support.paths import REPO_ROOT, SOURCE_HTML, SITE_ROOT, input_path, source_path, read_application_source, read_source_html

import json
from pathlib import Path
import shutil

from scripts.project_layout import REPO_ROOT, distribution_sources


RELEASE_SUPPORT_FILES = (
    'scripts/__init__.py',
    'scripts/project_layout.py',
    'scripts/build-site.mjs',
    'scripts/build_release.py',
    'scripts/validate_static.py',
    'scripts/translation_fallback.py',
    'scripts/security_policy.py',
    'config/site-files.json',
    'config/standalone-vercel.json',
    'vercel.json',
    'package.json',
    'package-lock.json',
)


def application_file(root: Path, target: str) -> Path:
    return root / distribution_sources(root)[target]


def copy_release_repository(destination: Path, source_root: Path = REPO_ROOT) -> set[str]:
    from scripts.build_release import validated_source

    sources = set(distribution_sources(source_root).values()) | set(RELEASE_SUPPORT_FILES)
    for name in sorted(sources):
        source = validated_source(source_root, name)
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    config_path = destination / 'config/site-files.json'
    config = json.loads(config_path.read_text(encoding='utf-8'))
    config['downloads'] = {}
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return sources
