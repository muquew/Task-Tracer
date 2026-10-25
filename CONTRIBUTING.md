# Contributing

Task Tracer is a static, local-first PWA. It needs no application build or backend.

## Development

- Use Python 3.12+ and Node.js 22+; npm dependencies are development-only.
- Test with disposable profiles and synthetic tasks, especially imports and recovery.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
npm ci --ignore-scripts
python -m playwright install chromium firefox webkit
python -m http.server 8080 --bind 127.0.0.1
```

- Open `http://127.0.0.1:8080`. Browser tests normally start their own temporary server.
- Linux may need Playwright's official system dependencies: `python -m playwright install --with-deps`.
- A system Chromium can be selected with `TASK_TRACER_BROWSER_EXECUTABLE=/usr/bin/chromium`; record its actual version.

## Validation

```bash
python tools/check.py --static-only
python tools/check.py --keep-going --report dist/check-results.json
python tools/browser_matrix.py --list
python tools/browser_matrix.py --browser all --keep-going --report dist/browser-matrix.json
```

- Static checks run 7 programs; the full registry currently has 73. The selected report's `planned_checks` defines the actual scope.
- The matrix registers 33 programs per engine. Only core repeats 1280×800 and 390×844; other programs define their own viewports.
- Firefox/WebKit live-CDP timezone cases are explicitly unexecuted. Linux engines and simulated sizes do not prove Safari/iPhone, native input methods, screen readers or OS notifications.
- Require successful exits, complete/passed reports and unchanged source/tool fingerprints. Keep failed attempts; `--keep-going` does not turn failures into passes.
- Use a new report filename when retaining a previous attempt. Preserve each matrix report with its run-ID log directory.
- For interface changes, also inspect real screenshots and use the keyboard: long text, empty/error states, focus, dialogs and narrow screens.

Large-workspace checks are separate from the routine registry; run the scope required by the change:

```bash
python tools/workspace_roundtrip_playwright.py --size 10000 --subtasks 6 --full-views --output dist/workspace.json
python tools/workspace_failure_playwright.py --size 10000 --subtasks 6 --output dist/storage-failures.json
python tools/performance_playwright.py --size 10000 --output dist/performance.json
```

- Compare complete task/config/revision/history data, not only visible cards. Injected faults differ from real quota exhaustion or eviction.
- Performance reports must state dataset, viewport, CPU conditions and repetitions; shared-load timings are not controlled benchmarks.

## Change rules

- Preserve DB2, task JSON2.4 and view JSON1.1 with 1.0 import compatibility. Task and view backups remain separate.
- Match JavaScript UTF-16 checksum semantics when validating task/view files, including emoji.
- Keep writes atomic, confirmations revision-aware and concurrent newer work protected. Retain drafts when validation or saving fails.
- Preserve untouched imported text/reminders and existing deadline instants. New clock gaps move forward and folds use the first occurrence; recurrence uses the task's stored timezone and explicit lineage.
- Keep new workspaces empty until the user adds tasks or chooses examples. Diagnostics stay previewed, allowlisted and manually downloaded.
- Add interface text to both language files; update the resource version and service-worker resource queries together.
- After translation changes, run `python tools/translation_fallback.py --write`, then `python tools/security_policy.py --write` and review the generated changes.
- After inline-script changes, regenerate CSP hashes with `python tools/security_policy.py --write`. Keep runtime HTML/scripts comment-free for the static checks.
- When runtime or cached assets change, align app/cache versions, SoftwareApplication metadata, `package.json` and both lockfile version fields.
- Never commit browser profiles, private exports, caches or credentials. Report vulnerabilities through [SECURITY.md](SECURITY.md).

## Build and publish

```bash
python tools/build_release.py
python tools/release_playwright.py
python tools/upgrade_playwright.py --baseline-archive downloads/task-tracer-4.15.1.zip
python tools/verify_deployment.py --url https://todo.muquew.com/
```

- Packaging uses 23 explicit source files plus generated `integrity.json`: 24 archive entries. Preserve the allowlist; never recursively include whole directories.
- The builder writes a ZIP and `.sha256` under ignored `dist/`; it does not publish. Use the actual generated checksum and manifest commit/dirty state.
- Published 4.15.1 ZIP `0540eca3…` is frozen to clean commit `6a3b8e61ba0699cc316fd92a247cc9c917a7521d`. A later build must not inherit that checksum or overwrite the published file.
- Verify repeated builds, extracted persistence/offline use, and upgrade/rollback/re-upgrade using the actual retained previous ZIP. Never rebuild an old version from new source.
- Close old app windows before upgrading or downgrading; export tasks and views first. Default upgrade fixtures do not replace an actual previous-archive check.
- After GitHub → Vercel publication, verify exact HTTPS assets/headers, then exercise the real site and inspect an actual downloaded backup.
- In a managed proxy environment, explicitly pass its proxy to Playwright launch/context requests. Node's extra CA does not configure Firefox's NSS store; use only the provided public CA in fresh temporary profiles, keep TLS/CSP checks enabled, then delete profiles.
- Historical acceptance and detailed environment examples remain in [the frozen evidence](https://github.com/muquew/Task-Tracer/tree/bafbf1663c4d36836774a6a5319fbcef20c8cbfc/docs/acceptance).

Contributions follow the [personal non-commercial license](LICENSE); separate commercial rights require the owner's agreement.
