"""Canonical repository and built-site paths shared by tests."""
from pathlib import Path
from urllib.parse import urlsplit
from scripts.project_layout import (REPO_ROOT, SOURCE_HTML, SITE_ROOT, APP_RUNTIME,
    ensure_site, read_application_source, read_source_html, source_path,
    site_sources, relative_path, ordered_script_urls)


def input_path(name: str, root: Path | None = None) -> Path:
    """Resolve a runtime URL to its source, or an explicit repository test input."""
    relative_path(name)
    base = REPO_ROOT if root is None else Path(root)
    return base / site_sources(base).get(name, name)


def application_input_names(root: Path | None = None) -> tuple[str, ...]:
    """Source-map targets for the shell and every ordered application script."""
    scripts = (urlsplit(url).path.removeprefix('./')
               for url in ordered_script_urls(read_source_html(root)))
    return tuple(dict.fromkeys(('index.html', *scripts)))
