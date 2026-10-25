#!/usr/bin/env python3
"""Print only newly generated, allowlisted WebKit outcome metadata."""
import ast
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

REPORT = Path("dist/browser-matrix-webkit.json")
module = ast.parse(Path("tools/browser_matrix.py").read_text())
PROGRAMS = next(ast.literal_eval(node.value) for node in module.body
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "PROGRAMS" for t in node.targets))
assert isinstance(PROGRAMS, tuple) and len(PROGRAMS) == 33 and len(set(PROGRAMS)) == 33
assert all(isinstance(p, str) and p.endswith("_playwright.py") and p.replace("_", "").replace(".py", "").isalnum() for p in PROGRAMS)
STATUSES = {"initializing", "running", "passed", "failed", "interrupted", "error"}

def read_report():
    try:
        value = json.loads(REPORT.read_text())
        return value if isinstance(value, dict) else None
    except (OSError, ValueError):
        return None

def rows(value):
    checks = value.get("checks", []) if value else []
    if not isinstance(checks, list):
        checks = []
    result = []
    for program in PROGRAMS:
        matches = [item for item in checks if isinstance(item, dict)
                   and item.get("browser") == "webkit" and item.get("program") == program]
        item = matches[0] if len(matches) == 1 else None
        code = item.get("exit_code") if item else None
        code = code if type(code) is int and -255 <= code <= 255 else None
        duration = item.get("duration_seconds") if item else None
        valid_duration = type(duration) in (int, float) and math.isfinite(duration) and 0 <= duration <= 604800
        duration_text = f"{duration:.3f}" if valid_duration else "unknown"
        status = "not_run" if not matches else "invalid"
        if item and code is not None and item.get("status") in ("passed", "failed"):
            status = "passed" if code == 0 else "failed"
        result.append((program, status, code, duration_text))
    return result

def emit_failures(value, emitted):
    for program, status, code, _ in rows(value):
        if status == "failed" and program not in emitted:
            print(f"::error::{program} exit={code}", flush=True)
            emitted.add(program)

def run():
    # This report must be new; never inspect a prior run's report or logs.
    if REPORT.exists():
        print("::error::browser_matrix.py status=invalid_report", flush=True)
        return 1
    child = subprocess.Popen([sys.executable, "tools/browser_matrix.py", "--browser", "webkit",
                              "--keep-going", "--report", str(REPORT)])
    def forward(signum, frame):
        if child.poll() is None:
            child.send_signal(signum)
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, forward)
    emitted = set()
    while child.poll() is None:
        emit_failures(read_report(), emitted)
        time.sleep(5)
    emit_failures(read_report(), emitted)
    return child.returncode

def summary():
    value = read_report()
    status = value.get("status") if value else "missing_report"
    status = status if status in STATUSES or status == "missing_report" else "invalid_report"
    result = rows(value)
    counts = {name: sum(row[1] == name for row in result) for name in ("passed", "failed", "not_run", "invalid")}
    header = f"matrix status={status} passed={counts['passed']} failed={counts['failed']} not_run={counts['not_run']} invalid={counts['invalid']} planned=33"
    print(header, flush=True)
    lines = [header, "", "| program | status | exit | duration_seconds |", "| --- | --- | --- | --- |"]
    for program, state, code, duration in result:
        code_text = str(code) if code is not None else "unknown"
        print(f"{program} status={state} exit={code_text} duration={duration}", flush=True)
        lines.append(f"| {program} | {state} | {code_text} | {duration} |")
    emit_failures(value, set())
    if status in ("missing_report", "invalid_report", "error", "interrupted"):
        print(f"::error::browser_matrix.py status={status}", flush=True)
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if target:
        with open(target, "a", encoding="utf-8") as stream:
            stream.write("\n".join(lines) + "\n")
    return 0

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("run", "summary"):
        raise SystemExit(2)
    raise SystemExit(run() if sys.argv[1] == "run" else summary())
