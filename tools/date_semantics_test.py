#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
from zoneinfo import ZoneInfo


REPO_ROOT = Path(__file__).resolve().parents[1]


def source_function(name: str) -> str:
    source = (REPO_ROOT / "index.html").read_text(encoding="utf-8")
    match = re.search(rf"function {name}\([^)]*\) \{{(?P<body>.*?)\n        \}}", source, re.S)
    if not match:
        raise AssertionError(f"Could not find function {name}")
    return match.group("body")


def local_date_key(iso_value: str, timezone_name: str) -> str:
    instant = datetime.fromisoformat(iso_value.replace("Z", "+00:00"))
    return instant.astimezone(ZoneInfo(timezone_name)).date().isoformat()


def assert_completion_timestamps_use_true_instants() -> None:
    body = source_function("getCompletionDateKey")
    if "utils.utcToLocal(completedAt)" in body:
        raise AssertionError("completedAt must not use due-date wall-time conversion")

    cases = [
        ("America/New_York", "2026-05-10T04:30:00.000Z", "2026-05-10"),
        ("Asia/Shanghai", "2026-05-10T15:30:00.000Z", "2026-05-10"),
        ("Europe/Berlin", "2026-05-10T21:30:00.000Z", "2026-05-10"),
    ]
    for timezone_name, completed_at, expected in cases:
        actual = local_date_key(completed_at, timezone_name)
        if actual != expected:
            raise AssertionError(f"{timezone_name} {completed_at}: expected {expected}, got {actual}")


def main() -> None:
    assert_completion_timestamps_use_true_instants()
    print("Date semantics passed")


if __name__ == "__main__":
    main()
