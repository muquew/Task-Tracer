# Large-workspace validation

## Historical ordinary-list comparison

A synthetic 10,000-task workspace was measured locally in Chromium 154.0.8037.57 on the same cloud machine, without CPU throttling. Each task has a project and tags; no task has a deadline. These are single before/after observations, not a mobile or production guarantee.

| Observation | Before | After |
| --- | ---: | ---: |
| Initial task-card DOM nodes | 10,000 | 100 |
| Reload to task-list readiness | 7,306 ms | 2,167 ms |
| Search for a task at the end of the dataset | 3,444 ms | 356 ms |

Search timing includes the 300 ms debounce. [Raw measurements](performance-baseline.json) retain the actual run values.

Ordinary lists render 100 matching tasks initially, with an explicit Show more control. The visible count explains that search covers all matching tasks. Loading more moves keyboard focus to a newly displayed task. Search parsing is cached per query and task search text is reused within a render. Filtering and searching happen before pagination, so tasks beyond the first page remain discoverable.

Starting with 4.8.5, batch mode starts with 100 matching cards and supports Show more, while Select all matching applies to the entire filtered task set. Manual ordering outside batch mode still renders the full matched list. The recorded 4.6/4.7 workloads used limited calendar cell buttons but full undated/day-detail task sets. The [4.8 record](releases/4.8.md) introduced independent 100-item limits to those sections, with separate focused calendar results recorded below; its complete initial suite remained failed. Historical timings must not be relabeled as later-version measurements. Ordinary timeline rendering is now bounded as described below; its date grouping and matching still process the complete task set. Large descriptions, attachments (not supported), numerous subtasks, slower mobile devices and large recovery histories are not represented by the historical dataset above. Further performance work should measure those cases rather than extrapolate these numbers.

Reproduce with:

```bash
TASK_TRACER_BROWSER_EXECUTABLE=/usr/bin/chromium python3 tools/performance_playwright.py --size 10000 --output /tmp/task-tracer-performance.json
```

The default validation command uses 1,000 tasks, verifies bounded list/timeline rendering, full-workspace search and load-more behavior, and enforces generous 15 s load / 5 s search regression budgets. These budgets detect severe regressions; they are not product service-level commitments.

## Timeline rendering in 4.6

The ordinary timeline initially renders at most 100 task cards and shares the **Show more** control with the list. It sorts date groups chronologically, puts undated tasks last and keeps each displayed date's full matching count even when only part of that group is rendered. Loading more moves keyboard focus to a newly displayed task. Search and filtering apply to the whole workspace before the display limit, so later dates and tasks beyond the first page remain discoverable.

Changing the search, filter, project, sort, Today Plan, batch state or view resets the initial display limit. The original 4.6 behavior retained full matched rendering for manual ordering and batch mode. Starting with 4.8.5, batch mode also uses bounded cards and preserves selection across pages; manual ordering outside batch mode remains unbounded. Bounding cards reduces DOM work; it does not remove full-data search, date sorting, grouping or storage costs. The performance check covers date order/counts, far-end search, focus, limit resets and unchanged stored data. Actual timing evidence belongs with the completed candidate run rather than being inferred from the cap.

## Extended migration and recovery workload

`tools/workspace_roundtrip_playwright.py` uses a separate synthetic workload with dated and undated tasks, tags, projects, descriptions and configurable subtasks. It checks a real downloaded JSON file and its integrity metadata, replacement import, a forced deletion checkpoint and confirmed restoration. It records browser version, task/subtask counts, file bytes and operation durations without printing task contents.

The routine size is 1,000 tasks with six subtasks each. An explicit `--size 10000 --subtasks 6` run covers a larger dataset; its measurements are not directly comparable to the plain no-deadline list/search table above. Date views, serialization, IndexedDB checkpoint copies and many subtasks add work that the earlier comparison did not measure. Record the exact command and completed outcomes in the applicable candidate evidence ([4.6](releases/4.6.md), [4.7](releases/4.7.md)); an interrupted or partially completed run is not a pass.

```bash
TASK_TRACER_BROWSER_EXECUTABLE=/usr/bin/chromium python3 tools/workspace_roundtrip_playwright.py --size 10000 --subtasks 6 --full-views --output /tmp/task-tracer-roundtrip.json
```

Task-import conflict rows are constructed only after merge mode is enabled and load in batches of 100. The bulk policy still applies to all conflicts, including rows not rendered yet; individual choices can override it. Changing the bulk policy resets those choices, while toggling merge mode preserves them. This bounds initial conflict-control construction, not the whole import: parsing, normalization, conflict matching, transaction copies and checksums still process the complete file.

## Recorded 4.6 extended-workspace results

Both the 1,000-task and 10,000-task runs completed with six subtasks per task in Chromium 154.0.8037.57 on the cloud machine. Three quarters of tasks have dates spread over 28 local days; one quarter are undated. The downloaded JSON, pre-import snapshot, replacement import and confirmed recovery were checked against canonical full-field task signatures. Timeline load-more, far-end search and resetting to the first page also passed. [The recorded metrics](performance-4.6-workspace.json) retain the raw values and their scope; they report these two workload runs, not the entire release suite.

| Observation | 1,000 tasks × 6 subtasks | 10,000 tasks × 6 subtasks |
| --- | ---: | ---: |
| Reload to bounded-list readiness | 403.5 ms | 1,036.6 ms |
| JSON export operation | 442.0 ms | 3,113.1 ms |
| Replacement import, including safety snapshot | 1,347.4 ms | 7,582.4 ms |
| Deletion with a forced checkpoint | 304.7 ms | 1,942.4 ms |
| Confirmed checkpoint restoration | 451.1 ms | 2,622.7 ms |
| Calendar transition | 368.6 ms | 2,188.7 ms |
| Timeline transition | 215.7 ms | 609.0 ms |
| Initial timeline task cards | 100 | 100 |
| Actual downloaded JSON bytes | 1,725,110 | 17,263,610 |

These are single-run elapsed times around scripted operations, including browser interaction and driver work. They are not pure rendering CPU measurements or guarantees for mobile devices, production hosting or another browser. The workload and verification harness differ from the historical no-deadline comparison; the two tables are not a direct before/after pair. Browser heap and process RSS were not measured. Export bytes describe the downloaded file, not peak memory use.

The 4.6 runtime reuses up to 64 explicit-zone date-part formatters and 128 timezone-validity results. Current-device timezone lookup remains live, and undated tasks skip timezone normalization work. These changes accompany lazy conflict controls and bounded timeline cards; the results do not isolate the contribution of each change.

Calendar preview-button counts do not represent its full DOM: the 10,000-task run still includes 2,500 full undated task cards, and day details also remain unbounded. Manual ordering and batch mode render full matches. Large descriptions, recovery copies, storage quotas and slower hardware can add time and memory pressure beyond this dataset. Further changes should retain field-preserving migration and recovery assertions as well as rendering checks.


## Recorded 4.7 10,000-task run

The frozen 4.7 source completed a separate 10,000-task/six-subtask round trip in Chromium 154.0.8037.57. The dataset again contains 75% dated tasks over 28 local days and 25% undated tasks. Downloaded JSON, the pre-import safety snapshot, replacement import, deletion and confirmed checkpoint restoration preserved canonical full-field task signatures. Timeline paging, far-end search and resetting to 100 cards also passed. [The 4.7 report](performance-4.7-workspace.json) retains the original measurement fields and scopes `passed` to this workload, not the complete release suite.

| Observation | 10,000 tasks × 6 subtasks |
| --- | ---: |
| Reload to bounded-list readiness | 925.1 ms |
| JSON export operation | 3,101.3 ms |
| Replacement import, including safety snapshot | 6,340.5 ms |
| Deletion with a forced checkpoint | 1,589.8 ms |
| Confirmed checkpoint restoration | 2,610.9 ms |
| Calendar transition | 1,680.2 ms |
| Timeline transition | 462.1 ms |
| Initial timeline task cards | 100 |
| Actual downloaded JSON bytes | 17,263,610 |

This was one cloud run while the main quality-check runner was active concurrently. It is not a controlled speed comparison with 4.6 and does not establish mobile or real-device latency. Times include browser/driver work. Browser heap and process RSS were not measured; file bytes do not describe memory use. The calendar's 36 preview buttons still coexist with 2,500 full undated cards, and day details/manual/batch modes remain unbounded. Real-device steps and blank result records are in [the manual device checklist](manual-device-checklist.md); no manual pass is inferred from this run.


## Recorded 4.8 workspace and calendar runs

The frozen 4.8 source passed a separate 10,000-task/six-subtask full workspace round trip in Chromium 154.0.8037.57. Downloaded JSON, pre-import snapshots, replacement import, deletion and confirmed restoration retained canonical full-field signatures. Timeline paging, far-end search and reset checks also passed. [The workspace report](performance-4.8-workspace.json) preserves every original result field and scopes `passed` to this workload, independently of the release suite.

| Observation | 10,000 tasks × 6 subtasks |
| --- | ---: |
| Reload to bounded-list readiness | 868.1 ms |
| JSON export operation | 2,781.6 ms |
| Replacement import, including safety snapshot | 6,381.6 ms |
| Deletion with a forced checkpoint | 2,055.1 ms |
| Confirmed checkpoint restoration | 2,910.3 ms |
| Calendar transition | 1,786.1 ms |
| Timeline transition | 942.1 ms |
| Initial timeline task cards | 100 |
| Actual downloaded JSON bytes | 17,263,610 |

A separate calendar-only Chromium scale run used 5,000 dated and 5,000 undated tasks. It passed initial limits of 100 undated cards and 100 selected-day items, plus tail searches. Its scope is scale boundaries, not a full page walk or JSON/recovery round trip. Separate complete calendar functional runs passed in Chromium 154.0.8037.57, Firefox 153.0 and WebKit 26.5 using 251 dated plus 251 undated tasks per engine. Those runs exercised real clicks, all pages, focus, counts, far-end search, resets, filters and manual ordering. [The scoped calendar report](performance-4.8-calendar.json) keeps these datasets and raw fields separate.

Ordinary calendar undated/day-detail sections now start at 100 each with independent Show more controls. Matching/grouping still processes the full set, and manual ordering/batch mode retains full rendering. Removing card content-visibility avoids the observed scrolling layout shift that displaced actual Firefox/WebKit load-more clicks. These cloud runs were not isolated from concurrent checks; they are single observations, not controlled comparisons with 4.6/4.7 or each other. Browser heap and RSS were not measured, and file bytes are not memory measurements. No real-device or system-notification pass is inferred.


## 4.8.1 targeted quick-add recovery with 10,000 existing tasks

A separate correctness exercise passed on the frozen 4.8.1 source in Chromium 154.0.8037.57. It began with 10,000 tasks, six subtasks per original task, one populated 10,000-task recovery checkpoint and task revision 2. [The raw report](performance-4.8.1-quick-add.json) preserves each phase's task/config/history signatures and original fields, plus the matching frozen source hash.

| Phase | Recorded result |
| --- | --- |
| Genuine task-add quota abort | Exact quick-add text remains read-only/selectable; all task/config/history signatures and revision 2 remain unchanged. |
| Same-document Retry | Original text becomes editable; zero task writes, unchanged complete task/config/history state and revision. |
| Explicit resubmission | Exactly one parsed task is added, revision advances once to 3, all 10,000 original records and the prior history remain intact. |
| Actual JSON download | 10,001 tasks, 17,264,528 bytes; metadata/checksum checks and complete task-field SHA match the database, including the one new task. |

This standalone reproducer is additional to the unified 39-program command. It verifies the current fix against a populated workspace; it does not rerun the 4.8.1 large-file replacement-import/checkpoint-restoration path or establish a performance benchmark. Earlier 4.8 full round-trip results remain historical. This was a single synthetic cloud exercise with potentially concurrent checks. Its total elapsed time is not a speed claim; heap/RSS and real-device behavior were not measured.

## 4.8.2 time-dependent view work

The [4.8.2 candidate work](releases/4.8.2.md) adds boundary-aware refresh for overdue/status membership, relative dates, Today Plan and statistics. Minute checks update ordinary time labels; a full view rebuild is requested at relevant deadlines, status thresholds, local midnight or observed clock/offset changes. Dialogs, inline editing, selected task text, dragging and selected batch work defer a disruptive rebuild until interaction permits it. Ordinary minute ticks should not recreate task controls, and loaded pagination/focus must remain usable.

The new virtual-clock browser program passed all 12 focused groups in Chromium, Firefox and WebKit, including read-only persisted state and stable controls/paging. Its visibility case controls `document.hidden` and explicitly dispatches `visibilitychange`, rather than reproducing real OS suspension. Virtual time and DOM-node identity assertions are not measurements of long-running CPU, battery, memory or background timing. No new 4.8.2 performance benchmark is claimed; the separate [complete 46-program run](releases/check-results-4.8.2.json) passed after the accessible-name correction. The earlier 4.8/4.8.1 datasets above remain versioned evidence, and full matching/grouping, manual/batch rendering and storage costs remain relevant.

## 4.8.2 targeted quick-add recovery with 10,000 existing tasks

The corrected frozen 4.8.2 source, after the English accessible-name correction, passed a new populated-workspace correctness exercise in Chromium 154.0.8037.57. [The report](performance-4.8.2-quick-add.json) retains its original fields and source hash: 10,000 original tasks and 60,000 subtasks, one populated 10,000-task checkpoint and baseline revision 2. Both genuine task-add quota abort and same-document Retry kept complete task/config/history signatures and revision unchanged. One explicit resubmission added only one task, advanced revision once to 3 and preserved every original record and previous checkpoint. The actual JSON download contained 10,001 tasks and 17,264,528 bytes with complete task signatures matching the database; no page errors were observed.

This standalone program is additional to the 46 registered checks. Its optional expected app/resource arguments asserted 4.8.2/4.34, and source hashing confirmed the frozen HTML remained unchanged through the run. The recorded 23.379 seconds are total correctness-exercise duration, not latency evidence. It was one synthetic cloud run which may have overlapped other checks, not a new complete import/restoration benchmark, memory measurement, controlled comparison or real-device guarantee. The [initial-source report](performance-4.8.2-quick-add-initial.json) preserves its earlier 24.37-second run; neither is a controlled speed comparison. The first complete 46-program run failed accessibility, and the corrected second run passed all 46 programs; that integrated result remains separate from this scoped workload.

## 4.8.3 calendar pagination after civil-date correction

The existing calendar performance program passed with 251 dated and 251 undated tasks in each engine, initially rendering 100 undated cards and exercising complete pagination/navigation. Exact reports are retained for [Chromium](performance-4.8.3-calendar-chromium.json), [Firefox](performance-4.8.3-calendar-firefox.json) and [WebKit](performance-4.8.3-calendar-webkit.json). Recorded calendar transitions were 484.8, 791.2 and 1,080.9 milliseconds respectively. These are individual, possibly concurrent cloud correctness runs, without a controlled comparison, latency guarantee or mobile-device claim.

The new timezone program separately verifies consecutive civil dates, leap-day navigation and add-form dates; Chromium additionally exercises live CDP timezone changes. Firefox and WebKit cover static timezone contexts. These results do not replace the historical 10,000-task datasets or establish a new 4.8.3 full-workspace import/restoration benchmark. Integrated check status and the candidate identity belong in the [4.8.3 record](releases/4.8.3.md).

## 4.8.5 integrated-source controlled full-workspace observations

The [desktop report](releases/performance-4.8.5-desktop-integrated.json), [390px report](releases/performance-4.8.5-mobile-resumed.json) and [ten-checkpoint report](releases/performance-4.8.5-history10-integrated.json) retain completed, source-bound observations from Chromium 154.0.8037.57 in the managed Linux cloud environment. The desktop and narrow-layout workloads each completed three fresh browser contexts and 14 measured operations per context. The additional history workload completed three fresh contexts with one measured edit each. All asserted task-integrity and functional conditions passed, and the source/tool fingerprints remained unchanged within every run. These results do not establish the complete release-suite or three-engine result; those have separate records.

The desktop workload completed before a managed-environment interruption. The first narrow-layout attempt stopped during its second context; its [unaltered partial report](releases/performance-4.8.5-mobile-integrated-interrupted.json), [log](releases/performance-4.8.5-mobile-integrated-interrupted.log) and [interruption record](releases/performance-4.8.5-environment-interruption.json) remain separate and are not a pass. The completed narrow-layout report uses three wholly new contexts after environment recovery, followed by the three history edits. Chromium remained 154.0.8037.57 and all 91 frozen inputs matched; [resumption conditions](releases/performance-4.8.5-environment-resumption.json) record a cgroup quota of four CPUs, a 32 GiB memory limit and five exposed logical CPUs. The table combines only the completed desktop and resumed narrow-layout runs, never samples from the interrupted attempt. These are separate controlled execution windows and do not establish a speed comparison across the recovery.

The fixed fixture contains 10,000 distinct synthetic tasks, six subtasks each, mixed dated/undated records, projects, tags, Unicode descriptions and a valid three-occurrence repeat chain with root ID 0. Its canonical full-task SHA-256 is `c4cc526b7da0d8bf28c35f6ab763523bf15e7bfa99ce8ba25fb0a8f64c4e3442` in every context and all three reports. Locale is `en-US`, timezone is UTC, the page clock is fixed at `2039-01-01T12:00:00Z`, and reduced motion is enabled. The two layouts use 1280×900 and 390×900 desktop Chromium contexts; the narrow context does not enable a mobile device profile or touch input.

Fixture installation runs at CPU rate 1 and is excluded from timings. Measured UI operations run with Chromium CDP CPU rate 4. Each repetition starts in a fresh context; repeated page loads within it use warm caches. The task fixture is restored before independent write phases, and the Undo phase follows the known batch change it must reverse. Full-field digest checks and Python download/checksum verification occur outside measured intervals. Timings use real elapsed time around UI/driver operations, including waits for the specified readiness conditions. Reload ends when the default active-filter page has its 100 cards; remaining phases explicitly select all tasks. Calendar transition includes the January 2039 title, the exact dated-preview count and undated-card readiness, without navigation to another month. During each execution window, other browser checks and CPU-heavy validation were paused; light document/file reads continued.

All values below are milliseconds, written as **median [minimum, maximum]** over the three contexts. The existing 15,000ms list-load and 5,000ms search regression ceilings come from [the ordinary-list program](../tools/performance_playwright.py) and the historical validation policy above. They were applied unchanged to this heavier workload and passed in all six full-workspace contexts. They are generous regression detectors, not user-facing latency guarantees. The other twelve operations are `baseline_only`: this controlled sample records their costs and variation without inventing performance thresholds from three observations.

| Measured operation | 1280×900 | 390×900 | Budget |
| --- | ---: | ---: | --- |
| Single description save, initially empty history | 3486.6 [3357.8, 3517.3] | 3471.6 [3372.7, 3775.7] | Baseline only |
| Reload to list readiness | 2624.9 [2407.1, 2697.5] | 3173.4 [2644.7, 3344.9] | 15,000ms ceiling |
| Full-workspace tail search | 808.5 [606.6, 856.8] | 792.7 [749.1, 841.0] | 5,000ms ceiling |
| Timeline transition | 1824.4 [1742.3, 2025.9] | 2138.4 [2122.8, 2370.7] | Baseline only |
| Calendar transition | 2448.8 [2427.0, 2766.7] | 2458.6 [2434.7, 2611.2] | Baseline only |
| Enter bounded batch mode | 1538.0 [1501.9, 1741.4] | 1669.0 [1464.2, 1740.5] | Baseline only |
| Select all matching tasks | 1744.1 [1683.0, 1932.2] | 1911.6 [1682.6, 2166.0] | Baseline only |
| Load the next selected batch page | 2035.8 [1931.6, 2261.2] | 2035.9 [1921.5, 2188.5] | Baseline only |
| Add all 10,000 matches to Today Plan | 6823.3 [5236.8, 7691.7] | 6322.7 [5523.9, 6390.3] | Baseline only |
| Undo that full-workspace batch change | 9300.9 [6438.8, 10804.9] | 8766.3 [8762.7, 14296.9] | Baseline only |
| Actual JSON backup download | 2682.0 [2653.5, 2755.1] | 2748.2 [2628.9, 3818.2] | Baseline only |
| Replacement import with safety download | 11066.9 [10312.3, 11404.5] | 11390.3 [11090.9, 17013.0] | Baseline only |
| Delete one task with a checkpoint | 3122.4 [3056.5, 3343.6] | 3281.0 [3264.4, 3316.4] | Baseline only |
| Confirmed checkpoint restoration | 5795.7 [4886.4, 8538.5] | 5238.8 [5151.4, 5246.5] | Baseline only |

List/timeline readiness sampled 100 connected task cards. Calendar sampled 100 undated cards and 81 dated preview buttons. Batch entry and Select all matching sampled 100 cards, with the selection summary representing all 10,000 matches; Show more then sampled 200 cards and 200 selected checkboxes. The actual batch write changed only `focusDate` on all 10,000 stored tasks, and Undo restored their complete original task signature. The observed connected element counts were 7,928 for the ready list, 7,916 for timeline, 7,915 for calendar, 8,128 for the initial batch page and 15,528 after its next page, in both layouts. These samples describe those specific phases; users can load additional pages. They do not imply that full matching, sorting, storage or whole-workspace writes became constant-cost.

The history variant starts with ten separately cloned, full-workspace recovery points and a newest timestamp equal to the fixed clock, so an ordinary edit falls inside the checkpoint interval. Single-save samples were **5620.9, 5176.3 and 5986.6ms**, with median **5620.9ms**; all are baseline-only observations. One explicit description changed, every other task field remained intact and the revision advanced once. The ten points retained their order, IDs, task counts and complete task-field signatures. This performance helper does not separately digest extra point metadata such as `createdAt`; whole-configuration atomicity belongs to the storage-failure regression evidence. The empty-history edit above creates its initial checkpoint, so this is a comparison of different history conditions, not an isolated measurement of a single history-read implementation cost.

The reports sample `Performance.getMetrics` JS heap sizes, `Memory.getDOMCounters`, and connected document elements after each operation. Across the full-workspace samples, observed JS used heap ranged from 31,671,840 to 333,810,336 bytes for desktop and from 21,542,732 to 250,746,232 bytes for the narrow layout. The three ten-checkpoint edit samples were 205,015,908, 209,736,860 and 204,901,092 bytes. Collection timing varies; fixture installation and integrity checks also allocate JavaScript data outside measured intervals. These are post-operation observations, without forced collection or continuous sampling. Their largest value is not a peak, process RSS or a memory budget, and lower readings do not establish lower device memory use. Browser DOM counters can include detached documents/nodes, while the connected counts above come from the live document.

The observations bind to source aggregate `588b005638b004e721a6913d5fde40b615e3915782fadae8ed1e9ec29bd5a5a0`, `index.html` SHA-256 `1ad3ab9d34fb020624d75cb9b5861731d2a819d0b9cefb046cb61306329f98eb`, and measurement-tool aggregate `c7492c1095db0d58dbcaaaee26dc97fc97502aeecf701f4e85da7add69ddf330`. The native reports retain their complete file maps and final equality flags. A later source or tool correction requires its own evidence; these numbers must not be relabeled as measurements of changed code. Historical unthrottled or concurrent cloud runs, including the earlier full-batch DOM probe, are not controlled before/after comparisons with this dataset and cannot establish a speedup ratio. CPU throttling and a narrow viewport also do not establish real-phone latency, memory, installation or notification behavior.

Earlier successful [desktop](performance-4.8.5-desktop.json), [390px](performance-4.8.5-mobile.json) and [ten-checkpoint](performance-4.8.5-history10.json) reports retain 87 measured operations on the preceding frozen source `e9aed46a55dfce35f6dd662b73dcb862dfa4677454329578bad75e0669641734` (`index.html` `08fc4b2d510c8660070893a25be08e454d52ef3fa9639b572ec0f15bbae5be1a`). A subsequently reproduced asynchronous IndexedDB-error problem required a source correction. The table above comes from the three newly executed integrated-source reports, with the same task fixture, method and measured-operation scope; the earlier reports remain unchanged and do not substitute for final-source evidence.

A second completed set of [desktop](releases/performance-4.8.5-desktop-final.json), [390px](releases/performance-4.8.5-mobile-final.json) and [ten-checkpoint](releases/performance-4.8.5-history10-final.json) reports retains another 87 observations on source `a52c118e05103e02cd74bce558902b8d8b8bbe765cd6cf1dee5d45bebc86a413`. A subsequent browser-matrix failure exposed a secondary request `AbortError` being mistaken for the cause of an explicit transaction abort. After correcting that regression and completing preflight checks, all three conditions were rerun on the integrated source shown above. Both preceding successful sets retain their exact original source scope and bytes.

The [first desktop attempt](performance-4.8.5-desktop-initial.json) failed during fixture preparation, before any measured operation: the initial refresh closed a filter menu before its option could be clicked. Its [original failure log](releases/performance-4.8.5-desktop-initial.log) remains unchanged. Waiting for the initial active task-card count before opening the menu corrected that setup race without extending timeouts or changing budgets. The successful [desktop](releases/performance-4.8.5-desktop-integrated.log), [narrow-layout](releases/performance-4.8.5-mobile-resumed.log) and [history](releases/performance-4.8.5-history10-integrated.log) logs are retained separately.

Reproduce using new output filenames; the tool refuses to overwrite earlier reports:

```bash
TASK_TRACER_BROWSER_EXECUTABLE=/usr/bin/chromium PYTHONDONTWRITEBYTECODE=1 python3 tools/workspace_performance_playwright.py --size 10000 --subtasks 6 --cpu-rate 4 --runs 3 --width 1280 --output /tmp/task-tracer-controlled-desktop-integrated-new.json
TASK_TRACER_BROWSER_EXECUTABLE=/usr/bin/chromium PYTHONDONTWRITEBYTECODE=1 python3 tools/workspace_performance_playwright.py --size 10000 --subtasks 6 --cpu-rate 4 --runs 3 --width 390 --output /tmp/task-tracer-controlled-narrow-integrated-new.json
TASK_TRACER_BROWSER_EXECUTABLE=/usr/bin/chromium PYTHONDONTWRITEBYTECODE=1 python3 tools/workspace_performance_playwright.py --size 10000 --subtasks 6 --cpu-rate 4 --runs 3 --width 1280 --history-points 10 --history-edit-only --output /tmp/task-tracer-controlled-history-integrated-new.json
```
