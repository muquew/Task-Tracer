# Contributing to Task Tracer

Task Tracer is a static, local-first PWA. Python serves the files and runs the checks; there is no application build or backend. Read [the internal code guide](docs/internal-code-guide.md) before changing storage, imports, recurrence, or service worker behavior.

The [personal non-commercial license](LICENSE) applies to contributions and evaluation. This guide does not grant commercial distribution rights.

## Development

Use Python 3.12 or newer and Node.js 22 or newer for the pinned accessibility checker. The application itself still needs only a static server. From the repository root:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
npm ci --ignore-scripts
python -m playwright install chromium
python -m http.server 8080 --bind 127.0.0.1
```

The application is available on port 8080. The browser checks start their own temporary static server unless `TASK_TRACER_URL` selects an existing one. Use disposable browser profiles for testing imports and recovery; do not test destructive flows against your personal task data.

## Current delivery

Use [the stable delivery record](docs/stable-delivery.md) for the current version, acceptance status, artifact and evidence, and [GOAL.md](GOAL.md) for execution. The 4.15.1 delivery target requires whole-product acceptance; a planned or running check is not a pass. The published [4.15.0 baseline](docs/releases/4.15.0.md) and earlier results retain the source and scope of their named release.

## Validation

```bash
python tools/check.py --static-only
python tools/check.py --keep-going --report dist/check-results.json
```

The static command runs seven programs for consistency, date semantics, deployment CSP hashes, release payload/version contracts, runner lifecycle and syntax guards. The full registry currently contains **73 programs**: those seven plus 66 browser and deployment-fixture programs. The report's `planned_checks` is the authoritative list for the selected revision. It covers capture/editing, recovery/import/concurrency, recurrence/timezones, views/batching, storage failures, updates/offline execution, performance, accessibility and packaging. Install the pinned Python and npm dependencies first.

Each command must exit successfully. `--keep-going` collects later outcomes after a failure but does not turn that failure into a pass. The atomic schema-2 report records a fresh run ID, commands, durations, completion state and source/verification identities. `completed: false`, `passed: false`, interrupted runs or input drift do not satisfy release acceptance. Keep native failures and interrupted attempts beside fresh reruns, with their original identities and logs.

CI installs the Playwright-managed Chromium for the pinned dependency and uses its full headless channel so notification permissions are exercised in the complete browser. To select a system browser explicitly, use `TASK_TRACER_BROWSER_EXECUTABLE=/usr/bin/chromium python tools/check.py --report dist/check-results.json` and record its actual version. A running development server or an old release's successful report does not validate a new candidate.

The CI job summary lists executed programs, exit codes and durations, and failed programs receive an annotation. Missing, interrupted or incomplete reports retain that state; unexecuted programs are not counted as passes.

Changes to interaction structure, focus, colors or translations also need the [accessibility/i18n audit](docs/accessibility-i18n-audit.md) and real keyboard/visual review. Keep checked-state glyph visibility, readable errors and fixed action bars in the inspected screenshots; semantic state or a clean axe scan alone is insufficient. Record unexecuted screen-reader or physical-device checks instead of inferring complete accessibility compliance.

## Change boundaries


- Keep new UI strings in both `resources/en.json` and `resources/zh-CN.json`.
- Update `CONFIG.I18N.RESOURCE_VERSION` and the language resource queries in `sw.js` together. After changing translations, configured languages or their resource version, run `python3 tools/translation_fallback.py --write` and then `python3 tools/security_policy.py --write`. Review both generated changes. The first synchronizes the non-executable JSON fallback embedded in the same HTML; static validation rejects a mismatch with the external resource files. This maintenance command does not add an application build requirement.
- After modifying inline scripts, run `python3 tools/security_policy.py --write` and review `vercel.json`; the readonly check fails if hashes are stale.
- Bump `CONFIG.APP.VERSION` and the `CACHE_NAME` suffix together when runtime code or cached assets change. Keep SoftwareApplication metadata consistent.
- Keep new workspaces empty until the user adds tasks or explicitly chooses examples. Keep Help and diagnostic preview/download usable in storage protection; diagnostic payloads must exclude user content, saved views, app settings, URLs and raw error messages, and must never upload automatically.
- Preserve task JSON version 2.4 compatibility and stored data. Saved-view migration exports a separate version 1.1 file and imports 1.0 or 1.1; validate its checksum, schema, size and capacity before writing, and preserve existing views. Use typed project scopes (`all`, `unassigned`, or `project` with an exact name) for new views, retain legacy string semantics when reading older views, and never expand a missing named project to all projects. Cover migrations, malformed imports, transaction aborts and recovery behavior when changing persistence.
- Capture task revisions when a write is invoked and when a destructive confirmation opens. A background refresh must not make an old write or approval current. Import previews must reset safety approvals when rebuilt, and canceled or superseded file reads must not reopen over a newer draft.
- Keep existing due instants when a task edit leaves its date/time unchanged, including ambiguous DST clock times. Keep current-zone lookup live while bounding explicit-zone formatter caches, and permit valid past deadlines for backfill and overdue edits.
- Resolve new wall times with gap-forward/first-fold semantics and derive canonical saved date/time fields from the chosen instant. Perform recurring date arithmetic using UTC date-only calendar fields, then resolve in the task's stored timezone; the device zone must not alter the next occurrence or a legacy weekday fallback.
- Keep task civil date/time strings intact across a device-zone gap or skipped date. Fill edited deadline controls from the task's date key and wall-time string; do not reconstruct them through a device-local `Date`. Exact-date search compares keys, while timeline/calendar date-only arithmetic and labels use a neutral UTC carrier without changing the task's saved timezone or instant.
- Read application/i18n metadata from the selected main runtime IIFE and its CONFIG blocks, not the first matching version-like text anywhere in HTML. Translation/help content can legitimately contain such text. Keep `package.json`, `package-lock.json` and its `packages['']` version aligned to the app version (two-component app X.Y maps to npm X.Y.0).
- Match JavaScript UTF-16 code-unit iteration when verifying the existing task/view checksum in Python. Cover astral emoji, ZWJ sequences and long Unicode fields with actual downloaded files and import/CSV parsing; a Python code-point mismatch does not by itself establish corrupt runtime exports.
- Keep time-driven view refresh read-only and boundary-aware. Defer disruptive rebuilds during drafts, selected task text, drags and selected batch work; retain pagination/focus, and cover actual minute/visibility events without inferring reliable background execution.
- Preserve untouched imported text/project/tag fields using the original task snapshot and the actual form baseline. Apply normalizers only to fields the user changes; retained quota drafts and stale-edit protection must keep those baselines. Full-form tags quote comma/quote-bearing values, preserving the JSON tag-array schema and quick-add syntax.
- Preserve finite imported reminder values, including fractions and inactive values, through form display/save, draft recovery and downloaded JSON. A select without a predefined option needs a temporary saved-value option; it must not turn a valid value into NaN/null or silently truncate it.
- Test quick-add month/day tokens against civil-date validation, including leap centuries, the supported year limit and submission across midnight. Recurrence duplicate guards must use explicit links/root evidence; deletion reconnection must be atomic and reject ambiguous/stale cases rather than guess from dates or creation order.
- Keep detailed explanations in documentation; the published `index.html` and `sw.js` follow the repository's comment-free runtime convention, which static validation checks.
- Keep changes focused. Explain the user-visible result, compatibility impact, and validation in a pull request. Do not commit browser profiles, exported personal task data, caches, or credentials.

See [the product and release roadmap](docs/product-roadmap.md) for release gates and planned work, and [SECURITY.md](SECURITY.md) for responsible vulnerability reporting.

## Browser matrix and large workspaces

Install the engines you intend to exercise, then inspect and run the declared scope:

```bash
python -m playwright install chromium firefox webkit
python3 tools/browser_matrix.py --list
python3 tools/browser_matrix.py --browser all --keep-going --report dist/browser-matrix.json
```

The current matrix registry contains **33 programs per selected engine**. `--browser firefox` selects one engine; `--group core` selects the critical workflow at 1280×800 and 390×844. Specialized programs retain their own viewports and conditions. Preserve the report together with its relative run-ID log directory. Missing engines fail rather than count as a skip/pass, and source/tool drift invalidates the overall result. [Browser compatibility](docs/browser-compatibility.md) explains capability limits and historical evidence; a configured CI job is not evidence that its remote execution passed.

For a focused core run, use `python3 tools/compatibility_playwright.py --browser firefox` (or `webkit`). For explicit large-workspace work:

```bash
python3 tools/performance_playwright.py --size 10000 --output /tmp/task-tracer-performance.json
python3 tools/workspace_failure_playwright.py --size 10000 --subtasks 6 --output /tmp/task-tracer-workspace-failure.json
```

Keep full task/config/revision/history comparisons, not just visible card counts. Injected quota/abort failures are distinct from actual browser eviction or native quota enforcement. Controlled measurements must state dataset, viewport, CPU conditions, repetitions, operation boundaries and budgets; CDP heap is not peak process memory. [Performance evidence](docs/performance.md) keeps prior measurements and their limits. Routine-size checker programs do not replace an explicitly required large run.

## Packaging and upgrades

```bash
python3 tools/build_release.py
python3 tools/release_playwright.py
python3 tools/upgrade_playwright.py --baseline-archive dist/task-tracer-4.15.0.zip
python3 tools/service_worker_update_playwright.py
```

The builder writes a verified ZIP and checksum under ignored `dist/`; it does not publish. `DISTRIBUTION_SOURCES` currently maps **23 required sources** to 23 entries, plus generated `integrity.json` for a **24-file archive**. Add intended assets deliberately; never replace the mapping with recursive directory inclusion. Mapped source paths must be local regular files/directories without symlinks. The payload test rejects unsafe/missing inputs and unrelated-file inclusion; the release program verifies independent byte-for-byte builds and executes the extracted PWA for persistence/offline checks.

For release acceptance, retain and verify the actual previous archive before using `--baseline-archive`; the example above targets the published 4.15.0 artifact when validating 4.15.1. Do not rebuild old version numbers from new code. The default git-baseline regression instead uses `1c3bacb0ca8015fb5840c6b5d1d5efa0937e6e28`, or `TASK_TRACER_UPGRADE_BASE`; keep the required history available (`git fetch --unshallow` for a shallow checkout). Record which method ran. Same-schema task compatibility does not establish compatibility for a future database migration or all older configuration formats.

Close or refresh older clients before editing typed project scopes. Keep a view-file 1.1 export before downgrading; interfaces before 4.7 cannot safely interpret those scopes, despite DB2/task-JSON2.4 compatibility. The service-worker update program uses self-contained interrupted-update fixtures; `--legacy-archive` can additionally select an actual verified earlier bundle. Synthetic and real-archive results remain separate.

## Production verification

The owner's existing flow publishes GitHub `main` and Vercel serves `https://todo.muquew.com/`. Local checks run independently of that domain. Once the intended version has deployed:

```bash
python3 tools/verify_deployment.py --url https://todo.muquew.com/
```

This read-only verifier compares actual response bodies and configured security headers, including exact precache URLs and versioned language queries. HTTP errors and stale HTTP 200 bodies fail. Its local fixture program does not verify the live site. The verifier does not open personal browser profiles or change tasks. GitHub Actions also exposes it through the optional `verify_site` dispatch input.

Complete a fresh real-domain browser workflow and actual backup download as complementary acceptance. Record whether offline behavior used the browser offline API or an unavailable origin; neither method proves physical-device installation or OS background delivery. Vercel serves the static directory without the development-only npm build or Python archive step. Preserve `vercel.json`, deploy files together and verify the response headers on the chosen host.

The [stable delivery record](docs/stable-delivery.md) holds current outcomes. Historical acceptance remains in the named [4.15.0](docs/releases/4.15.0.md), [4.10.1](docs/releases/4.10.1.md), [4.9.0](docs/releases/4.9.0.md), [4.8.6](docs/releases/4.8.6.md) and [4.8.5](docs/releases/4.8.5.md) records, including original failed or partial attempts.
