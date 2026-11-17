# Development

Use Node.js 22+ and Python 3.12+ from the repository root. The application itself has no runtime package dependencies.

## Preview the source checkout

```bash
npm run dev
```

This builds the explicit site into `dist/site` and serves that directory at http://127.0.0.1:8080/. It does not serve the repository root or provide hot reload. Re-run the command after source changes. If an installed development service worker serves an earlier copy, unregister it for this local origin and reload.

For Windows without a `python3` alias, run `npm run site`, then `py -3 -m http.server 8080 --bind 127.0.0.1 --directory dist/site`.

## Set up verification tools

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
npm ci --ignore-scripts
python -m playwright install --with-deps chromium
npm run check
```

In Windows PowerShell use `py -3 -m venv .venv` and `.venv\Scripts\Activate.ps1`. If `python3` is unavailable, use the activated environment's `python` with the module command shown in `package.json`, for example `python -m scripts.check --static-only`.

| Command | Responsibility |
| --- | --- |
| `npm run site` | Build the deployable static site in `dist/site`, using only Node standard libraries. |
| `npm run dev` / `npm run preview` | Build and serve the static site locally. |
| `npm run styles` / `npm run styles:check` | Generate or check `public/resources/workspace.css` from `src/styles/workspace.css`. |
| `npm run icons` / `npm run icons:check` | Generate or check raster icons and their receipt against the original SVG. Generation needs Chromium; checking does not launch a browser. |
| `npm run check` | Static, date, build, security, release and runner checks without a browser launch. |
| `npm test` | All registered checks, including Chromium workflows; stop at the first failure. |
| `npm run test:report` | Continue registered checks after failures and retain `dist/check-results.json`; failures still return a nonzero status. |
| `npm run test:browsers` | Registered Chromium, Firefox and WebKit workflows with per-program logs. |
| `npm run test:a11y` | Accessibility and language audit using Chromium and the local axe-core dependency. |
| `npm run build` | Build a portable ZIP, integrity manifest and SHA-256 checksum in `dist/`. It does not deploy. |

Tests and their order are defined in `tests/registry.py`. Use the registry instead of creating a second list in CI. Shared interactions and fixtures belong in `tests/support/`; executable browser scenarios belong in `tests/browser/`. The optional workload under `tests/browser/manual/` is not part of the default coverage.

To run a focused browser group:

```bash
python -m playwright install --with-deps chromium firefox webkit
npm run test:browsers -- --browser chromium --group capture --report dist/capture-chromium.json
```

Add `--list` to inspect scope without launching a browser. An installed browser can be selected through `TASK_TRACER_CHROMIUM_EXECUTABLE`, `TASK_TRACER_FIREFOX_EXECUTABLE` or `TASK_TRACER_WEBKIT_EXECUTABLE`; the legacy `TASK_TRACER_BROWSER_EXECUTABLE` alias affects Chromium only. Supply native-library paths required by custom executables in the test process environment. Simulated viewports are not physical mobile or Safari/iOS coverage.

## Source ownership

See [architecture and responsibilities](docs/architecture.md) before introducing a module. Input and date rules belong in the domain layer; database operations belong in the repository; view modules receive data and action ports. Do not pass the entire application state to a new feature.

After changing translations, run `python -m scripts.translation_fallback --write`. After changing inline startup code, run `python -m scripts.security_policy --write`; both deployment configurations must remain in sync. After changing runtime assets, update the single site-file contract and matching offline-cache entries.

Use disposable profiles and synthetic data for imports, recovery and browser testing. Review changed flows in Chinese and English, with keyboard navigation and a narrow viewport. Preserve the existing database and backup formats unless a deliberate migration is part of the change.

## Publish

Validate the relevant checks and generated assets, then push the completed changes to `main`; Vercel builds and deploys the static site automatically. Confirm the deployment and run `python -m scripts.verify_deployment --url https://todo.muquew.com/` against the resulting source revision. A portable ZIP uses its own standalone deployment configuration and can be served directly after extraction.

Keep app/cache/package versions and resource versions aligned. Published download bytes and checksums must not be overwritten by temporary builds. Generated reports, local research, private sessions and credentials do not belong in the repository or site output.
