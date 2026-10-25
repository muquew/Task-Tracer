# Product direction and release roadmap

The initial product direction is a local-first personal task workspace, with a possible buyout or professional edition. The core promise is that capture, planning, and review work without an account or a server. Professional positioning must be backed by reliable data handling, clear limitations, and repeatable releases.

The continuing objective is a dependable commercial product: a complete everyday workflow, durable and portable task data, accessible offline operation, recoverable upgrades, and maintainable distribution and support. A candidate version is a progress record, not a request to pause for phase approval. Continue finding, fixing and validating concrete gaps within this direction; publish and commercial-policy decisions still require their own concrete release evidence and owner choices.

This is an implementation roadmap, not a statement that the product is ready for paid distribution. The current [LICENSE](../LICENSE) permits personal non-commercial use; muquew has confirmed ownership and can grant separate commercial rights while retaining that public license. Pricing, actual issued commercial terms, purchase delivery and support terms still need to be defined before selling. See [the commercial offering plan](commercial-plan.md). The [4.8.5 engineering-candidate launch/delivery draft](commercial-launch-draft.md) separates current GOAL acceptance work from historical completed runs and keeps pricing, license and support choices explicit.

## First stage: reliability and release foundation

Implemented in the 4.2 working-tree candidate:

- Pinned development dependencies, a single `tools/check.py` entry point, and a GitHub Actions quality workflow. The workflow is configured; a remote CI run is still required.
- A complete browser smoke run with installability checked in a regular browser profile, plus separate recovery and undo/concurrent-edit regression suites.
- Up to 10 transactional recovery checkpoints, explicit confirmation to replace tasks, and same-device storage guidance. Checkpoints survive page reloads and include empty lists; task writes and checkpoints roll back together on failure.
- Revision checks that refuse stale tab writes, undo scoped to the affected task changes, and an edit-form guard that preserves a stale draft while preventing it from overwriting a newer task.
- Contributor, security, release, and recovery guidance. The [candidate notes](releases/4.2.md) record local validation and checks still outstanding.

Local automated checks have passed with system Chromium. This does not establish published deployment behavior, a successful remote CI run, broad browser support, or readiness to charge customers. Finish the release gates below before publishing or accepting payments.

## Ongoing hardening in the 4.3 candidate

- Bounded ordinary-list rendering and cached search, with a measured 10,000-task comparison and a regression budget.
- Database version-change release, blocked-upgrade guidance, recoverable memory exports, and real old-version upgrade/rollback/re-upgrade tests.
- Data safety status, site quota estimates, explicit persistence requests and denied/unsupported fallbacks.
- Hash-authorized deployment scripts, blocked inline event handlers, no automatic analytics loading, and enforced-CSP browser tests.
- Pinned axe-core and expanded light/dark, desktop/mobile, recovery/data-safety dialog and notification audits.
- Engine-neutral desktop/mobile critical flows, a three-engine CI matrix, and deterministic static artifacts exercised after extraction.

[The completed 4.8.5 candidate evidence](releases/4.8.5.md) distinguishes the five finished engineering acceptance queues from historical local validation and the production-host and real-device checks that still need to run. The three desktop engines passed their 4.3 critical-flow suites and 4.4 CSV checks. Candidate-specific results belong in its release notes. This hardening continues against the same product direction rather than requiring a new phase approval.

## Continued improvements in the 4.4 candidate

- Full-workspace CSV reports with Unicode, multiline values, formula-prefix handling and a clear distinction from JSON restoration.
- Atomic reminder metadata updates that preserve concurrent edits and do not resurrect deleted tasks or clear newer snoozes.
- Dedicated CSV and delayed-notification regression programs; the 4.4 suite registered 16 checks.

## Continued work in the 4.5 candidate

- Start with an empty workspace and make clearly labeled example tasks an explicit, undoable choice. Preserve intentional empty lists, filtered empty results and tasks created in another window.
- Put existing capture, search and keyboard capabilities within reach through in-app help, and provide a previewed local diagnostic file without task content or automatic uploads.
- Preserve nullable repeat-task references correctly, including valid task ID 0, and reserve valid source IDs before allocating import replacements.
- Preserve saved views across concurrent windows and failed configuration writes through atomic per-operation updates. Record reproduction and regression results with the candidate rather than treating implementation as proof that a check passed.

## Continued work in the 4.6 candidate

- Migrate saved searches, filters and layouts with a separate validated JSON file. Preserve existing views, show duplicate/capacity skips and require another review when the preview becomes stale. Keep task JSON version 2.4 compatible.
- Bind task-import previews and destructive confirmations to their reviewed revision, and capture each write's expected revision before asynchronous callbacks can refresh state.
- Make pending task-file reads cancellable and prevent earlier reads from replacing a newer form or import preview.
- Bound ordinary timeline task cards while preserving chronological groups, full matching counts, search and keyboard load-more. Keep manual/batch rendering and calendar undated/detail limits explicit.
- Bound explicit-zone formatter/validation caches while keeping live local-zone fallback. Preserve the exact due instant when editing unchanged wall time, and allow valid past-date backfill and overdue edits.
- Extend synthetic-workspace checks to exported/imported task fields, subtasks and checkpoint restoration. Record measured outcomes and limits in [the candidate evidence](releases/4.6.md); registration of a check does not establish that it passed.

Local development and validation proceed without publishing to GitHub or waiting for the production domain. The owner's GitHub-to-Vercel workflow and `todo.muquew.com` provide supplementary deployment evidence when available.

## Continued hardening in the 4.7 candidate

The [4.7 candidate notes](releases/4.7.md) track backup coverage tied to the exported task revision/date, atomic saved-view capacity refusal, unambiguous project scopes with view-file 1.1/legacy 1.0 compatibility, unsaved task-form closure/departure protection with memory-only storage-failure draft recovery, and preserving a complete offline version through an interrupted upgrade. The reproducible 4.7 candidate package is prepared with 23 files and an honest modified-working-tree manifest. Startup-reminder priority passed all six focused cases in all three engines, and the formerly failing Chromium project-scope program passed again. A separate current-version 10,000-task/six-subtask round trip passed with full-field checks; its [raw measurements](performance-4.7-workspace.json) remain a single concurrent cloud run. The final 33-program Chromium run and reproducible extracted-artifact checks passed, with [machine-readable results](releases/check-results-4.7.json) retained for review. This completes local candidate validation; real-device/manual checks, hosted verification and remote CI remain unexecuted, and actual paid-launch terms remain undecided.

## Recorded 4.8 candidate and follow-up

The [4.8 record](releases/4.8.md) covers calendar pagination/navigation, input-method composition, revision-bound Undo and recovery-history preview/export/clear controls. Its initial 38-program run completed with 37 passes and an IME test-setup failure; the corrected focused setup later passed, but the [original report](releases/check-results-4.8-initial.json) remains failed. Its reproducible artifact passed extraction/offline checks independently. A new quick-add text-loss reproduction prompted the immediate 4.8.1 correction rather than treating the candidate as a stopping point or commercial-ready product.

## Locally validated 4.8.1 candidate

The [4.8.1 candidate record](releases/4.8.1.md) documents the corrected quick-add storage-failure gap: read-only copyable text, same-document Retry, departure protection, retained capture details and explicit resubmission. All six quick-add groups passed in Chromium/Firefox/WebKit, as did capture smoke and expanded mobile accessibility checks. The actual 4.8-archive upgrade path also passed. The final Chromium run completed with all 39 programs passing in a summed 817.629 seconds, with the [machine report](releases/check-results-4.8.1.json) retained; two independent artifact builds and extracted persistence/offline checks passed. The default workspace round trip uses 1,000 tasks with six subtasks each. A separate [10,000-task quick-add recovery exercise](performance-4.8.1-quick-add.json) verifies the current fix and one explicit save/export, rather than a new full import/restoration benchmark. The [4.8 initial 38-program result](releases/check-results-4.8-initial.json) remains failed. This completes local candidate validation; engineering continues toward the same product goal, while real-device, remote CI, hosted verification and actual paid-launch terms remain outstanding.

## Locally validated 4.8.2 candidate

The [4.8.2 candidate](releases/4.8.2.md) corrects device-dependent recurrence and legacy weekdays, gap/fold deadline conversion, ongoing-overdue statistics, stale time-dependent views, accidental saved-view deletion and focus return, recursive distribution inclusion and incomplete deployment-resource checks. The first complete run failed English accessible-name consistency (45/46, 792.137 seconds); its [failed report](releases/check-results-4.8.2-initial.json) and initial artifact remain unchanged. After using the visible name/metadata for the native button name and expanding the audit to both languages, the second complete Chromium run passed 46/46 in a summed 904.491 seconds, with the [final report](releases/check-results-4.8.2.json) retained. Two independent 23-file builds produced identical bytes, and extracted persistence/offline checks passed.

The recorded [10,000-task quick-add correctness exercise](performance-4.8.2-quick-add.json) and actual 4.8.1 archive upgrade/rollback/re-upgrade also passed on that corrected frozen source. The default full-suite round trip uses 1,000 tasks with six subtasks; the additional 10,000-task run does not establish a new full import/restoration or latency benchmark. Those completed checks record that batch’s evidence; the product goal in [GOAL.md](../GOAL.md) continues through the work below. The file is not a background runner. Real-device, remote CI and hosted verification remain unexecuted, and commercial price/payment/support/license terms remain undecided.

## Validated 4.8.3 batch within the continuing product goal

The [4.8.3 candidate notes](releases/4.8.3.md) separate new source from the preceding completed result. This batch addresses foreign-zone wall times being normalized in an edit form and moving the deadline on a description-only save; calendar civil-date/month drift after a device-zone change; version-like translation text confusing release metadata; and a Python checksum helper's Unicode code-point mismatch with JavaScript UTF-16 semantics. The six foreign-wall-time cases passed in all three engines. The new calendar-timezone program passed Chromium including real CDP timezone changes, and its static civil-date cases passed Firefox/WebKit; the earlier calendar suites also passed all three engines. Five static programs and enhanced Unicode CSV/real JSON clean-profile round trips passed. Runtime and tool inputs are frozen, two builds are byte-identical and standalone extracted persistence/offline and actual prior-archive upgrades passed. The complete Chromium run passed 49/49 in a summed 925.720 seconds, including final repeatable builds and extracted persistence/offline. The [machine report](releases/check-results-4.8.3.json) and [79-input fingerprint record](releases/inputs-4.8.3.json) bind the evidence to unchanged frozen sources and tools. This records the completed batch within the continuing product goal; it is not a background runner or a claim that every check ran in three engines. DB/task/view formats remain unchanged, and old incorrectly saved instants cannot be automatically mapped back to the user's intent. Engineering continues without a new phase approval or a claim of real-device, remote CI, deployment or paid-launch completion.

## Validated 4.8.4 batch within the continuing goal

The [4.8.4 candidate notes](releases/4.8.4.md) track valid imported text/quoted tags being changed by unrelated edits, unsupported saved reminder values becoming invalid, quick-add leap/skipped-date parsing, duplicate recurrence descendants after deletion, and reused check reports retaining an old successful result during a new blocked/interrupted run. All final imported-text/reminder/quick-date/lineage/deletion focused suites passed all three engines. Runner lifecycle and static syntax/date mutation regressions passed, with seven static programs passing in total. The runtime payload is frozen, the runner captured/checked verification inputs at startup, and a reproducible standalone-tested artifact is prepared. The actual 4.8.3 archive upgrade/rollback/re-upgrade also passed. The complete Chromium run passed 56/56 in a summed 1081.277 seconds, including final repeated builds and extracted persistence/offline. Its [schema-2 report](releases/check-results-4.8.4.json) and [87-input provenance record](releases/inputs-4.8.4.json) retain the run ID, unchanged input fingerprints, artifact and original logs. Runtime sources were frozen before the run; verification inputs were captured at runner startup and then independently checked. Focused three-engine passes do not imply all 56 programs ran in each engine. Task/database/view formats stay unchanged. This continued engineering uses the preceding validated batch as evidence, without recasting its report as proof for new source or waiting on undecided commercial terms.

## Completed five GOAL queues for 4.8.5

All five [GOAL engineering acceptance queues](../GOAL.md) completed on 2026-10-24 Beijing for the same frozen 4.8.5/resources 4.36 candidate. The complete Chromium run passed 58/58 programs, summed 1301.444 seconds; [its native report](releases/check-results-4.8.5.json) and [91-input provenance](releases/inputs-4.8.5.json) bind the environment, original outcomes and artifact. Source/verification start/end/current maps match the fourth freeze, captured before the final acceptance runs. The 23-file/812,056-byte ZIP has SHA-256 `08bf9fafc2ebeb7bf905ebc105a7d08ad571ba91eb65eaf8a3b2a3cdcbff5a0d`; two independent builds match, extracted persistence/offline and actual 4.8.4 archive upgrade/rollback/re-upgrade passed.

The completed evidence includes the full-view 10,000-task/six-subtask round trip with recurrence references and full-match batch actions, all nine failure-recovery cases at that scale, [31 programs in each of Chromium 154.0.8037.57/Firefox 153.0/WebKit 26.5](browser-compatibility.md), and [87 controlled performance observations](performance.md). Only core compatibility repeats both 1280×800/390×844; four Firefox/WebKit live-CDP coverage groups remain explicitly not_run. Performance uses separate 1280×900/390×900 contexts: 42 observations each plus three ten-checkpoint edits. Reload/search passed the unchanged 15s/5s ceilings; other operations retain baseline-only status, and post-operation heap is not peak/RSS or real-phone performance.

The code repairs atomic merge-replacement recurrence links, asynchronous IndexedDB first-error delivery after rollback and secondary request AbortError handling that had closed manual-abort previews. Batch rendering starts at 100 plus Show more while Select all matching and persisted actions retain complete matching scope; non-batch manual ordering remains full. Final affected suites passed in all three engines and the complete checker. Database/task/view formats remain unchanged.

All 314 raw evidence files are bound by bytes/SHA in the provenance record, including prior successful, failed and interrupted candidates. The first integrated mobile attempt stays running/incomplete/false in its original report and its 25 partial observations are excluded from the completed 87. The first complete Firefox matrix passed 30 programs and failed one reload whose cause remains unexplained; an unchanged diagnostic did not reproduce it and a separate complete 31-program rerun passed, without changing runtime, timeout or correctness assertions. The [release notes](releases/4.8.5.md) preserve these histories and exact scopes. This closes the current engineering goal; real-device, remote CI, hosted deployment and commercial terms retain their independently recorded status, with no background-runner claim.

## Next: professional edition readiness

| Work | Acceptance evidence |
| --- | --- |
| Storage durability | Extend the transactional and concurrent-edit regressions with large-workspace quota/eviction scenarios and real-device recovery exercises; document the outcomes. |
| Privacy and data portability | In-app explanations match actual network/storage behavior; users can export and restore their data without payment or an account. |
| Large workspaces | Extend the documented 10,000-task cloud comparison to slow/mobile devices, many subtasks, timeline/manual/batch modes, import/export and recovery-history memory use. |
| Cross-browser support | Publish an explicit tested browser/version matrix covering Chromium, Firefox, and Safari/WebKit; run the [real-device checklist](manual-device-checklist.md) for mobile install/offline/keyboard paths and retain actual records. |
| Support and upgrades | Provide a private support route, release notes, an upgrade policy, and recovery guidance. State actual reminder and browser-storage limitations. |
| Paid distribution | With owner identity confirmed, choose a payment provider and receipt/license model, and document price, refunds, support scope, and privacy terms before accepting payments. |

Keep task capture, export, and recovery available when a purchase check cannot reach the network. A paid edition should not put existing personal data behind an online license check. Do not embed private payment keys or signing secrets in the static app.

## Later, only with an explicit product decision

Accounts, cloud sync, collaboration, and subscriptions are not implemented or implied by the current plan. They introduce authentication, authorization, conflict resolution, hosting costs, retention/deletion policies, and operational support. Evaluate them as a separate architecture and business decision after the local product is dependable.

## Release gates

1. Run the documented checks in [CONTRIBUTING.md](../CONTRIBUTING.md). Record the commit, browser versions, commands, outcomes, and any skipped checks in the release notes; investigate failures rather than labelling them passed.
2. Export a realistic synthetic workspace. Test the candidate with existing-version data, verify editing and recurrence, then restore the export in a clean profile. For persistence changes, verify rollback compatibility before release.
3. Close or refresh older windows before editing new saved views; keep a views 1.1 export before any downgrade, because old interfaces do not understand typed project scopes. Update the app/cache version and, when translations change, the language resource version. Publish the static files as one artifact so HTML, service worker, and resources stay consistent.
4. Verify HTTPS, security response headers, asset status codes, manifest parsing, fresh install, update from the previous release, and cached offline reload on the deployed candidate. Include manual keyboard, mobile, and screen reader checks appropriate to the change.
5. Promote the tested artifact and retain the previous artifact and release evidence. On failure, redeploy the previous artifact and verify service worker/cache behavior. A code rollback cannot undo an incompatible IndexedDB migration; never claim it restores user data without a tested recovery path.

Use synthetic task data in CI, screenshots, release evidence, and support reports. The app should remain usable while an optional service is unavailable, and release notes must identify limitations that affect users' data or reminders.
