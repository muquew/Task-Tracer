# Task Tracer 4.10.0 frozen engineering evidence

Status: **passed**. Collected at 2026-10-25T11:25:24.891+00:00.

Candidate commit: `4573ec3fe17698ee052b4496f923c7cdb022a226`. Frozen input SHA-256: `06525372d83f39b3b97d33eab050f8d2c63d03d276c79724903722aada34a2da`.

- Original full native checker: 59/60 passed, all 60 completed, native status remains failed. Its sole workspace test-navigation failure is retained.
- Targeted complete workspace recheck passed after exactly one inserted `return_to_task_workspace(page)` test-navigation call. The 59 unchanged native passes plus this recheck complete the 60 required programs; this is not a single native 60/60 passed run.
- Chromium 154.0.8037.57: all 33 registered browser workflows are contained in that full run; no duplicate Chromium matrix was run or counted.
- Firefox 153.0: 33/33 native matrix programs passed; one probe plus 33 program logs byte/hash-verified.
- Webkit 26.5: 33/33 native matrix programs passed; one probe plus 33 program logs byte/hash-verified.
- Application source 23 files remain frozen. Original full/matrix report start/end identities match the original 71-file freeze; the clean QA HEAD and targeted recheck use the strictly pinned single-file verification overlay. No other source, tool, registry or assertion changed.
- Two builds are byte-identical: 24 files, 801,987 bytes, SHA-256 `2d2d290daf76256eca9fe6f12d59d4f81182b8c60633b2f5fd998da46023380b`. Manifest commit matches and `working_tree_dirty=false`; every payload hash and current source byte was checked.
- Actual previous 4.9.0 ZIP SHA-256 `197bc587145d65f986320ce4b69bd0a2937ce8d48ca3ceb3183a49dfc8849b7b` was verified. Upgrade, rollback, re-upgrade, task/view equality, CRUD and offline markers are bound to its retained successful wrapper/log.

All native reports, native matrix logs, wrapper logs, freeze and archive/checksum files are indexed with byte counts and SHA-256 in `final-evidence.json`. No application checks, builds, browsers, network requests or publication actions are executed by this collector.

Scope: Linux desktop browser engines and synthetic viewports. Only the compatibility program claims both 1280×800 and 390×844; other workflow programs retain their own viewport scope. Firefox and WebKit live device-timezone overrides in timezone/calendar-timezone remain `not_run` because they require Chromium CDP; fixed-zone cases are retained. This is not physical-device, Safari/iOS, system notification, installation, assistive-technology, remote-CI or production-deployment acceptance.
