# Original 4.15.0 complete baseline check

The original checker executed all 73 registered programs: 64 passed and 9 failed. This baseline remains failed and is not final-delivery acceptance.

Native elapsed time: 2280.523 seconds; per-program duration sum: 2279.131 seconds.

The detached 54b95cce baseline stayed clean. All 23 source and 84 verification inputs are unchanged. No tracked files, original assertions, thresholds or cases were edited. The ignored development dependency directory points to the shared pinned axe package.

See `full.json` for the original atomic checker report; `stdout.log` / `stderr.log` preserve the original streams. `run.json` records the exact command, environment selectors, timings and input identities. `summary.json` is explicitly derived.

| Program | Exit | Observed failure |
| --- | ---: | --- |
| project_scope_playwright.py | 1 | Direct click on hidden project filter without exposing collapsed filters. |
| onboarding_playwright.py | 1 | Expected old exact Add 3 example tasks label; actual Try example tasks. |
| help_playwright.py | 1 | Expected old Capture and plan heading; actual native details/group. |
| settings_flow_playwright.py | 2 | Registered no-argument invocation rejected because argparse requires --output; zero browser cases ran. |
| repeat_delete_playwright.py | 1 | Batch-delete action remained invisible after old reveal helper; single case passed before failure. |
| repeat_merge_playwright.py | 1 | Skip-all scenario clicks intentionally disabled data-no-import-changes submit. |
| time_refresh_playwright.py | 1 | Old .stats-mini:nth(4) locator absent after current statistics redesign. |
| calendar_performance_playwright.py | 1 | Old sort helper clicked hidden sort button after earlier pagination/search/navigation stages passed. |
| accessibility_i18n_audit.py | 1 | Real serious axe label-content-name-mismatch in scaled calendar day details: visible time omitted by explicit aria-label. |

The last accessibility failure is a real scaled calendar label defect, not a waived tool assertion. `calendar-label-diagnostic/` retains a bounded reproduction with original axe rules, DOM values and a screenshot. Its browser and server are closed.

The original invocation does not force deployment CSP on every tool. Each tool retains its original HTTP and motion settings. The default upgrade program used its 4.1 fixture; this does not substitute for an actual previous-release ZIP upgrade. Performance records include the original 1,000-task program. Failed programs can have passed earlier internal scenarios; those are not counted as whole-program passes.

No final candidate was mutated or accepted by this baseline run. The checker process group was absent at final receipt inspection.
