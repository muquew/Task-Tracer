"""Atomic reports, process cleanup and immutable input identities for test runners."""
from __future__ import annotations
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from scripts.project_layout import REPO_ROOT, distribution_sources

def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')

def atomic_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix=f'.{path.name}.', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(report, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

def identity_file(name: str) -> Path:
    if not isinstance(name, str) or not name or any(char in name for char in ('\\', '\x00', ':')):
        raise ValueError(f'Unsafe identity input: {name!r}')
    relative = PurePosixPath(name)
    if relative.is_absolute() or '..' in relative.parts or relative.as_posix() != name or name == '.':
        raise ValueError(f'Unsafe identity input: {name!r}')
    path = REPO_ROOT
    for part in relative.parts:
        path = path / part
        if path.is_symlink():
            raise ValueError(f'Identity input must not be a symbolic link: {name}')
    if not path.is_file():
        raise ValueError(f'Missing identity input: {name}')
    return path

def identity(names: list[str]) -> dict:
    files = {name: hashlib.sha256(identity_file(name).read_bytes()).hexdigest()
             for name in sorted(set(names))}
    serialized = json.dumps(files, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    return {'files': files, 'sha256': hashlib.sha256(serialized).hexdigest()}

def source_identity() -> dict:
    sources = distribution_sources(REPO_ROOT)
    return identity(['config/site-files.json', *sources.values()])


def verification_identity() -> dict:
    suffixes = {'.py', '.js', '.mjs', '.json', '.html', '.css'}
    names = []
    for folder in ('scripts', 'tests', 'src', 'config'):
        directory = REPO_ROOT / folder
        if directory.is_symlink():
            raise ValueError(f'Verification directory must not be a symbolic link: {folder}')
        for path in directory.rglob('*'):
            if '__pycache__' in path.parts:
                continue
            if path.is_symlink():
                raise ValueError('Verification input must not be a symbolic link: '
                                 + path.relative_to(REPO_ROOT).as_posix())
            if path.is_file() and path.suffix in suffixes:
                names.append(path.relative_to(REPO_ROOT).as_posix())
    workflows = REPO_ROOT / '.github' / 'workflows'
    names.extend(path.relative_to(REPO_ROOT).as_posix() for suffix in ('*.yml', '*.yaml')
                 for path in workflows.glob(suffix))
    names.extend(('vercel.json', 'package.json', 'package-lock.json', 'requirements-dev.txt'))
    return identity(names)


class RunInterrupted(BaseException):
    def __init__(self, signum: int):
        self.signum = signum
        super().__init__(f'Interrupted by {signal.Signals(signum).name}')

def stop_child(child: subprocess.Popen | None) -> None:
    if child is None:
        return
    try:
        if os.name == 'posix':
            os.killpg(child.pid, signal.SIGTERM)
        elif child.poll() is None:
            child.terminate()
    except ProcessLookupError:
        pass
    try:
        child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            if os.name == 'posix':
                os.killpg(child.pid, signal.SIGKILL)
            else:
                child.kill()
        except ProcessLookupError:
            pass
        child.wait(timeout=5)
