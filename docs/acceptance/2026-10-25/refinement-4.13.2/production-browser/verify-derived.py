"""Recheck archived JSON and downloaded backup without opening a browser."""

from collections import Counter
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
EXPECTED_INDEX = "79693a476cd75b46df78b71890f9a3a89aef2eb08aa8a2af701c07c4b801c1ad"


def read(name):
    return json.loads((ROOT / name).read_text())


def stable_json(value):
    if isinstance(value, dict):
        return "{" + ",".join(
            json.dumps(key, ensure_ascii=False) + ":" + stable_json(value[key])
            for key in sorted(value)
        ) + "}"
    if isinstance(value, list):
        return "[" + ",".join(stable_json(item) for item in value) + "]"
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def backup_checksum(payload):
    unsigned = {key: value for key, value in payload.items() if key != "checksum"}
    units = stable_json(unsigned).encode("utf-16-le", errors="surrogatepass")
    result = 2166136261
    for index in range(0, len(units), 2):
        result ^= units[index] | (units[index + 1] << 8)
        result = (result * 16777619) & 0xFFFFFFFF
    return f"fnv1a32:{result:08x}"


def verify():
    source = read("source.json")
    session = read("session-report.json")
    operator_checks = read("derived-checks.json")
    paths = sorted(ROOT.glob("[0-9][0-9]-*.json"))
    assert [int(path.name[:2]) for path in paths] == list(range(1, 68))
    observations = {int(path.name[:2]): read(path.name) for path in paths}
    assert source["url"] == "https://todo.muquew.com/"
    assert source["status"] == 200 and source["normal_tls"] is True
    assert source["bypass_csp"] is False and source["fresh_context"] is True
    assert source["index_sha256"] == session["source_index_sha256"] == EXPECTED_INDEX
    assert source["headers"]["content-security-policy"]
    assert session["observations"] == 67 and session["page_errors"] == []
    assert session["browser_closed"] is True
    assert len(session["action_errors"]) == 2
    assert [item["command"]["selector"] for item in session["action_errors"]] == [
        "#dueDate", "#dueTime"
    ]
    assert all(item["pageErrors"] == [] for item in observations.values())
    assert all(item["source_index_sha256"] == EXPECTED_INDEX for item in observations.values())
    assert all(item["docWidth"] <= item["viewport"]["w"] for item in observations.values())
    assert observations[29]["scrollY"] == observations[30]["scrollY"] == 0
    assert not any(field["id"] in {"dueDate", "dueTime"} for field in observations[5]["fields"])
    assert observations[21]["active"]["id"] == "noDeadline"

    def field(step, name):
        return next(item["value"] for item in observations[step]["fields"] if item["id"] == name)

    assert field(22, "dueDate") == "2026-10-26"
    assert field(23, "dueTime") == "09:30"
    assert field(54, "taskName") == "筛选外新增"
    assert field(54, "searchInput") == field(55, "searchInput") == "不存在的过滤"
    assert "calendar-detail-task" in observations[61]["active"]["className"].split()
    backup_paths = list(ROOT.glob("task-tracer_backup_*.json"))
    assert len(backup_paths) == 1
    backup = read(backup_paths[0].name)
    assert backup["type"] == "backup" and backup["version"] == "2.4"
    assert backup["checksum"] == backup_checksum(backup)
    tasks = backup["tasks"]
    assert len(tasks) == 7 and len({task["id"] for task in tasks}) == 7
    assert sum(task["completed"] for task in tasks) == 1
    assert sum(len(task["subtasks"]) for task in tasks) == 1
    first = next(task for task in tasks if task["name"] == "线上复查：保存子任务")
    assert all(first[key] is None for key in ["dueDate", "dueAt", "dueLocalDate", "dueLocalTime", "dueTimeZone"])
    assert first["subtasks"][0]["text"] == "未点加号也要保留"
    assert first["subtasks"][0]["completed"] is False
    dated = next(task for task in tasks if task["name"] == "线上复查：日程编辑")
    assert dated["dueLocalDate"] == "2026-10-26" and dated["dueLocalTime"] == "09:30"
    assert dated["dueTimeZone"] == "Asia/Shanghai"
    assert dated["dueDate"] == dated["dueAt"] == "2026-10-26T01:30:00.000Z"
    assert dated["description"] == "保存后仍回到同一天日程"
    assert operator_checks["passed"] is True
    assert len(operator_checks["observations"]) == 67
    assert operator_checks["task_count"] == 7 and operator_checks["completed_count"] == 1
    assert operator_checks["subtask_count"] == 1 and operator_checks["operator_errors"] == 2
    counts = Counter(f'{item["viewport"]["w"]}x{item["viewport"]["h"]}' for item in observations.values())
    return {
        "kind": "derived-archive-recheck",
        "passed": True,
        "browser_rerun": False,
        "observations": 67,
        "observations_are_independent_tests": False,
        "source_index_sha256": EXPECTED_INDEX,
        "browser": source["browser"],
        "normal_tls": True,
        "bypass_csp": False,
        "viewport_observation_counts": dict(sorted(counts.items())),
        "page_error_arrays_empty": True,
        "horizontal_overflow_observations": 0,
        "operator_action_errors": 2,
        "browser_closed": True,
        "sidebar_scroll_document_y_before_after": [0, 0],
        "saved_task_editor_and_search_preservation": True,
        "calendar_saved_active_class": "calendar-detail-task",
        "backup": backup_paths[0].name,
        "backup_checksum": backup["checksum"],
        "backup_checksum_verified": True,
        "backup_tasks": 7,
        "backup_completed_tasks": 1,
        "backup_pending_subtasks": 1,
        "first_task_remains_without_deadline": True,
        "second_task_local_deadline": "2026-10-26 09:30 Asia/Shanghai",
        "second_task_description": dated["description"],
    }


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False, indent=2))
