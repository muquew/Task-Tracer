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


def local_wall_time_to_utc_iso(date_value: str, time_value: str, timezone_name: str) -> str:
    local = datetime.fromisoformat(f"{date_value}T{time_value}").replace(tzinfo=ZoneInfo(timezone_name))
    return local.astimezone(timezone.utc).isoformat(timespec="minutes").replace("+00:00", "Z")


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


def assert_due_dates_keep_wall_time_and_store_true_instants() -> None:
    source = (REPO_ROOT / "index.html").read_text(encoding="utf-8")
    required_fragments = [
        "function createDueFields(dateValue, timeValue, timeZoneName",
        "dueLocalDate",
        "dueLocalTime",
        "dueAt",
        "dueTimeZone",
        "getInstantWallPartsInTimeZone",
        "getTaskDueDateKey(task)",
        "getTaskDueTimeValue(task)",
        "utils.localDateTimeToInstantISO(dueLocalDate, dueLocalTime, dueTimeZone)",
        "legacyStoredDueDateToLocalDate",
        "const dueFields = normalizeTaskDueFields(task);",
        "formatTaskDueDate(task)",
        "calculateTaskTimeLeft(task)",
    ]
    for fragment in required_fragments:
        if fragment not in source:
            raise AssertionError(f"Missing due-date semantic fragment: {fragment}")

    forbidden_fragments = [
        "utils.calculateTimeLeft(task.dueDate)",
        "utils.utcToLocal(",
        "utils.localToUTC(",
        "utils.dateToStoredISO(",
        "utils.formatDate(task.dueDate)",
        "new Date(`${dateValue}T${timeValue}`)",
    ]
    for fragment in forbidden_fragments:
        if fragment in source:
            raise AssertionError(f"Old due-date semantic path remains: {fragment}")

    wall_date = "2026-05-10"
    wall_time = "23:30"
    new_york_instant = local_wall_time_to_utc_iso(wall_date, wall_time, "America/New_York")
    shanghai_instant = local_wall_time_to_utc_iso(wall_date, wall_time, "Asia/Shanghai")
    if new_york_instant == shanghai_instant:
        raise AssertionError("Different time zones must produce different exact instants")
    if (new_york_instant, shanghai_instant) != ("2026-05-11T03:30Z", "2026-05-10T15:30Z"):
        raise AssertionError(f"Unexpected wall-time conversion: {new_york_instant}, {shanghai_instant}")


def main() -> None:
    assert_completion_timestamps_use_true_instants()
    assert_due_dates_keep_wall_time_and_store_true_instants()
    print("Date semantics passed")


if __name__ == "__main__":
    main()
