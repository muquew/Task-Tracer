# Browser compatibility evidence

The integrated 4.8.5 matrix passed all 31 registered programs in Chromium, Firefox and WebKit, for 93 program executions against the same frozen candidate. The results below support queue 3 in [GOAL.md](../GOAL.md). Only the core compatibility program repeats its scenarios at both required viewports; four Firefox/WebKit engine/program live-CDP coverage groups remain explicitly `not_run`. The completed [4.8.4 record](releases/4.8.4.md) retains its separate historical scope.

`tools/browser_matrix.py` runs an explicit registry of browser-parameterized programs used by the CI compatibility job. The selected report records the actual registry count and program list; newly integrated workflow regressions join that registry. The driver does not install browsers or fetch dependencies. Follow [CONTRIBUTING.md](../CONTRIBUTING.md) and, for the prepared cloud machine, [the runtime notes](cloud-browser-runtime.md).

```bash
python3 tools/browser_matrix.py --list
python3 tools/browser_matrix.py --browser chromium --group core --report dist/browser-matrix-core-chromium.json
python3 tools/browser_matrix.py --browser firefox --program compatibility_playwright.py --program imported_text_edit_playwright.py --report dist/browser-matrix-selected-firefox.json
python3 tools/browser_matrix.py --browser all --keep-going --report dist/browser-matrix.json
```

Repeat `--browser`, `--group` or `--program` to select a union. Without a selection, all three engines and all registered programs are planned. Groups are `core`, `capture`, `data`, `calendar`, `dates` and `all`. `--list` works with Python's standard library and does not launch a browser or write a validation report.

## Scope and interpretation

| Coverage | Actual scope |
| --- | --- |
| Core CRUD, persistence, layouts, JSON export/restoration and offline reload | `compatibility_playwright.py` runs both 1280×800 and 390×844 viewports in each selected engine. |
| Capture, drafts and imported values | Selected capture programs exercise their own form, recovery, input-method and date cases; their viewport coverage follows those programs. |
| Backup, recurrence, batch operations and saved views | Selected data programs exercise their own atomicity, conflicts and data assertions. |
| Calendar and timezone behavior | Selected calendar/date programs retain their individual platform scope and any explicit platform limitations. |
| Live device-timezone changes | `timezone_playwright.py` and `calendar_timezone_playwright.py` use Chromium CDP for live overrides. Firefox/WebKit execute fixed-zone cases; their live-override case is explicitly `not_run` in `scope.coverage_exceptions`. |
| Storage failures | The default workspace-failure cases cover injected abort/quota errors and an actual asynchronous duplicate-key request `ConstraintError`. They do not establish real browser eviction or actual engine-quota behavior; any separate native-quota case needs its own record. |
| Real devices and operating-system behavior | Not established by Linux browser engines, synthetic viewports, DOM composition events or automated notification fixtures. |

Each engine is launched for a real version probe with the same Playwright launcher/options used by its programs. Missing binaries or runtime dependencies fail the probe; the engine's workflow programs remain explicitly unexecuted. A selected-program pass applies only to the `scope` written in that report. Passing the core group does not establish that the remaining registry passed, and passing this matrix does not establish that all programs in `tools/check.py` ran in every engine.

The driver publishes a new `initializing`/`running` report with `completed: false` and `passed: false` before executing programs. It reuses the release runner's atomic report writer, input fingerprints and child cleanup. Reports retain a UUID, timestamps, actual engine versions, program exit codes, durations and per-program raw log paths/hashes. Runtime and verification fingerprints are checked at program boundaries and at completion. Any observed input drift prevents a pass, even if a changed file is subsequently restored. SIGINT/SIGTERM retain an interrupted, incomplete result and stop the child process group. An uncatchable kill can leave the new running report incomplete; it cannot establish a pass.

Raw logs are saved next to the report in `<report-stem>-logs/<run-id>/`. The report records both their original absolute paths and portable paths relative to its parent directory, plus hashes/bytes. Retain that directory with its report when collecting release evidence. Failed, interrupted, unexecuted and unsupported cases must retain their actual status. Do not replace them with historical success records or lower correctness assertions to complete a matrix.

## Integrated 4.8.5 results

All three native reports have `status: passed`, `completed: true` and `passed: true`, with 31 checks in exact registry order, no failed or unexecuted programs and no integrity errors. Each report's source/verification start and end maps, and the current files at collection, match the [fourth frozen input map](releases/frozen-inputs-4.8.5-integrated.json): source `588b005638b004e721a6913d5fde40b615e3915782fadae8ed1e9ec29bd5a5a0` and verification `79561466af29cb7342dc758e0fc42aea027485db0703e5805e34a0123e50bb98` (22 + 69 = 91 inputs).

| Engine | Actual probed version | Registered programs | Native report | Original console |
| --- | --- | --- | --- | --- |
| Chromium | 154.0.8037.57 | 31 passed | [JSON](releases/browser-matrix-4.8.5-chromium.json) | [Log](releases/browser-matrix-4.8.5-chromium.log) |
| Firefox | 153.0 | 31 passed | [JSON](releases/browser-matrix-4.8.5-firefox.json) | [Log](releases/browser-matrix-4.8.5-firefox.log) |
| WebKit | 26.5 | 31 passed | [JSON](releases/browser-matrix-4.8.5-webkit.json) | [Log](releases/browser-matrix-4.8.5-webkit.log) |

Versions came from actual browser probes using the same launch options as the programs. Reports and all 96 referenced probe/program logs are retained byte for byte; their relative `<report-stem>-logs/<run-id>/` trees preserve portable lookup, and every referenced log was checked against its native byte count and SHA-256. Original absolute paths remain evidence of the execution location.

| Registered program | Chromium | Firefox | WebKit |
| --- | --- | --- | --- |
| [compatibility_playwright.py](../tools/compatibility_playwright.py) | Passed | Passed | Passed |
| [csv_playwright.py](../tools/csv_playwright.py) | Passed | Passed | Passed |
| [backup_freshness_playwright.py](../tools/backup_freshness_playwright.py) | Passed | Passed | Passed |
| [backup_reminder_priority_playwright.py](../tools/backup_reminder_priority_playwright.py) | Passed | Passed | Passed |
| [project_scope_playwright.py](../tools/project_scope_playwright.py) | Passed | Passed | Passed |
| [task_draft_playwright.py](../tools/task_draft_playwright.py) | Passed | Passed | Passed |
| [quick_add_recovery_playwright.py](../tools/quick_add_recovery_playwright.py) | Passed | Passed | Passed |
| [quick_add_date_playwright.py](../tools/quick_add_date_playwright.py) | Passed | Passed | Passed |
| [imported_text_edit_playwright.py](../tools/imported_text_edit_playwright.py) | Passed | Passed | Passed |
| [imported_reminder_edit_playwright.py](../tools/imported_reminder_edit_playwright.py) | Passed | Passed | Passed |
| [repeat_lineage_playwright.py](../tools/repeat_lineage_playwright.py) | Passed | Passed | Passed |
| [repeat_delete_playwright.py](../tools/repeat_delete_playwright.py) | Passed | Passed | Passed |
| [repeat_merge_playwright.py](../tools/repeat_merge_playwright.py) | Passed | Passed | Passed |
| [dialog_lifecycle_playwright.py](../tools/dialog_lifecycle_playwright.py) | Passed | Passed | Passed |
| [onboarding_playwright.py](../tools/onboarding_playwright.py) | Passed | Passed | Passed |
| [help_playwright.py](../tools/help_playwright.py) | Passed | Passed | Passed |
| [ime_input_playwright.py](../tools/ime_input_playwright.py) | Passed | Passed | Passed |
| [batch_selection_playwright.py](../tools/batch_selection_playwright.py) | Passed | Passed | Passed |
| [workspace_failure_playwright.py](../tools/workspace_failure_playwright.py) | Passed | Passed | Passed |
| [calendar_performance_playwright.py](../tools/calendar_performance_playwright.py) | Passed | Passed | Passed |
| [calendar_navigation_playwright.py](../tools/calendar_navigation_playwright.py) | Passed | Passed | Passed |
| [calendar_timezone_playwright.py](../tools/calendar_timezone_playwright.py) | Passed | Passed; live CDP `not_run` | Passed; live CDP `not_run` |
| [recovery_management_playwright.py](../tools/recovery_management_playwright.py) | Passed | Passed | Passed |
| [views_portability_playwright.py](../tools/views_portability_playwright.py) | Passed | Passed | Passed |
| [views_delete_playwright.py](../tools/views_delete_playwright.py) | Passed | Passed | Passed |
| [timezone_playwright.py](../tools/timezone_playwright.py) | Passed | Passed; live CDP `not_run` | Passed; live CDP `not_run` |
| [dst_wall_time_playwright.py](../tools/dst_wall_time_playwright.py) | Passed | Passed | Passed |
| [foreign_wall_time_playwright.py](../tools/foreign_wall_time_playwright.py) | Passed | Passed | Passed |
| [recurrence_timezone_playwright.py](../tools/recurrence_timezone_playwright.py) | Passed | Passed | Passed |
| [time_refresh_playwright.py](../tools/time_refresh_playwright.py) | Passed | Passed | Passed |
| [stats_scope_playwright.py](../tools/stats_scope_playwright.py) | Passed | Passed | Passed |

The four `not_run` entries represent engine/program coverage groups, not four individual assertions: each non-Chromium calendar group excludes several live timezone/navigation scenarios. Fixed-zone cases ran and passed. These exclusions are also recorded in each report’s `scope.coverage_exceptions` and are not counted as successful live-CDP coverage.

Core scenarios ran in every engine at 1280×800 and 390×844: create/edit/complete, list/timeline/calendar/statistics, JSON export/restoration, persistence, offline reload and horizontal-overflow checks. Specialized programs used their own declared viewports and fixtures. The matrix is not the full `tools/check.py` suite in every engine, a native quota/eviction claim, or real Safari/iPhone/IME/assistive-technology acceptance. Remote CI and production deployment remain separate records.

## First integrated Firefox timeout and revalidation

The first freeze-four Firefox matrix completed all 31 programs with 30 passed and one failed: the second `page.reload()` in `onboarding_playwright.py` line 38 exceeded its original 30-second wait for `load`, after the first reload and three persisted example-task records had passed. The [unaltered failed report](releases/browser-matrix-4.8.5-firefox-integrated-first.json), [console](releases/browser-matrix-4.8.5-firefox-integrated-first.log) and all 32 referenced logs remain retained under run ID `a97aee8a-a48b-449c-9e06-a828646fa173`. Its source and verification identities stayed equal to freeze four. This failure is separate from the earlier saved-view manual-abort product regression below.

After that worker exited, an [observation-only diagnostic](releases/browser-matrix-4.8.5-firefox-onboarding-diagnostic.py) called the unchanged onboarding program with all original assertions and reload parameters. It passed in 11.598 seconds; its four reload calls took 0.332, 0.161, 0.149 and 0.229 seconds. The [observations](releases/browser-matrix-4.8.5-firefox-onboarding-diagnostic.json), [raw output](releases/browser-matrix-4.8.5-firefox-onboarding-diagnostic.log) and [byte/hash inventory for four context traces and the diagnostic files](releases/browser-matrix-4.8.5-firefox-onboarding-diagnostic-files.json) are retained. The diagnostic did not reproduce the original timeout; its additional observation timing cannot establish the original cause.

The final Firefox result above comes from a new complete 31-program rerun, run ID `5c0761b1-bdcc-49fb-ba9e-de3b9c85463c`, using separate report/log paths with the same 91 frozen inputs. No runtime code, test timeout or correctness assertion changed between the failed matrix, diagnostic and complete rerun. The first timeout remains unexplained; the later passes are revalidation evidence, not proof of a fixed environment or product defect.

## Earlier interrupted 4.8.5 run

The first frozen 4.8.5 matrix was stopped with SIGINT after a real manual-abort product regression appeared in Chromium saved-view import. All three reports are `interrupted`, `completed: false`, `passed: false`; their 22 runtime and 69 verification input identities remained unchanged. Original reports, completed and interrupted raw logs, console output and the [input snapshot](releases/browser-matrix-4.8.5-initial-inputs.json) are retained. The integrated reruns above use the corrected fourth freeze and separate report/log paths; these original partial outcomes remain unchanged.

| Engine | Completed program outcomes before interruption | Original report |
| --- | --- | --- |
| Chromium | 23 passed, 1 failed; 7 unexecuted | [Initial report](releases/browser-matrix-4.8.5-initial-chromium.json) |
| Firefox | 20 passed; 11 unexecuted | [Initial report](releases/browser-matrix-4.8.5-initial-firefox.json) |
| WebKit | 18 passed; 13 unexecuted | [Initial report](releases/browser-matrix-4.8.5-initial-webkit.json) |

The Chromium failure was in the saved-view import atomic-abort/retry case: a real `config.savedViews` put was queued, then the transaction was manually aborted. The expected retained preview instead closed and protected storage mode appeared. The [complete original failure output](releases/task-tracer-4.8.5-matrix-chromium-logs/555e2b1f-9275-4237-8621-8351d3a42c1b/chromium-views_portability_playwright.log) preserves the stack and accessibility snapshot. This failure is separate from the large-workspace tool's other-page initialization timeout. Failed and unexecuted cases are not counted as passes.

After distinguishing canceled-request `AbortError` events from the transaction's actual failure and waiting for abort completion, the original unmodified view-portability program passed all eight groups in [Chromium](releases/abort-preview-4.8.5-green-chromium.log), [Firefox](releases/abort-preview-4.8.5-green-firefox.log) and [WebKit](releases/abort-preview-4.8.5-green-webkit.log). The [focused input/log record](releases/abort-preview-4.8.5-green-inputs.json) binds the batch's unchanged runtime/verification identities and actual versions. These targeted results remain separate from both the failed/interrupted initial reports and the complete integrated matrix above. The integrated matrix started after the corrected-source controlled-performance exclusive window ended.

The development Chromium core program passed both viewports, but that [development matrix report](releases/browser-matrix-development-2026-10-24-chromium.json) remained failed because runtime and verification inputs changed during the run. Its raw logs are retained separately; it is not a release-quality matrix pass. Isolated [driver-lifecycle probes](releases/browser-matrix-lifecycle-probe.json), with their [original fixture](releases/browser-matrix-lifecycle-probe.py), passed child exit-code propagation, SIGINT/SIGTERM cleanup and replacement of old successful reports on initialization errors. Their fixture engine is explicitly synthetic and supplies no browser/application compatibility evidence.
