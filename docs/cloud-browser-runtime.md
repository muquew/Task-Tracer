# Browser validation in the prepared cloud machine

Local quality checks do not depend on GitHub publication, Vercel or the production domain. The optional production command in CONTRIBUTING.md is an extra channel after a deployment exists.

The prepared snapshot has Playwright browser binaries under `/workspace/.cache/ms-playwright`, and system Chromium at `/usr/bin/chromium`. All three engines passed their desktop/mobile critical-flow tests. The standard CI uses `playwright install --with-deps` and the system library cache, without the cloud-specific adjustments below.

## Firefox

Use `PLAYWRIGHT_BROWSERS_PATH=/workspace/.cache/ms-playwright XDG_CACHE_HOME=/workspace/.cache python3 tools/compatibility_playwright.py --browser firefox`. This cloud filesystem sandbox makes `/proc/self/uid_map` read-only, which prevented Firefox startup. The successful run used the execution tool's reviewed escalation outside that filesystem sandbox; it did not disable Firefox's content sandbox. Limit it to the synthetic local-server test.

## WebKit

The container lacked GTK4, Graphene, HarfBuzz ICU, Manette, Hyphen, GLES2, WOFF, Cairo script interpreter, HIDAPI and LZO runtime libraries. Their Debian packages were retrieved using signed trixie metadata from `https://deb.debian.org/debian` and extracted under `/workspace/.cache/browser-libs/root`. Package and TLS verification were retained; no system files were replaced. Apt's sources/cache configuration is retained under `/workspace/.cache/browser-apt`.

The downloaded WebKit wrapper resets its own library path, so missing shared-library symlinks were added to `/workspace/.cache/ms-playwright/webkit-2336/minibrowser-wpe/sys/lib`, pointing to these extracted libraries without replacing bundled files. The current runtime uses:

```bash
XDG_CACHE_HOME=/workspace/.cache PLAYWRIGHT_BROWSERS_PATH=/workspace/.cache/ms-playwright PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1 python3 tools/compatibility_playwright.py --browser webkit
```

That supported override bypasses the host checker's system-ldconfig-cache heuristic, which does not see the user-space GLES2 library. The actual libraries were independently loaded and the browser executed all assertions. It does not disable package checksums, TLS, CSP or application assertions. Do not use it to conceal a missing runtime library. Reinstalling WebKit removes the added runtime links; use normal system dependency installation where supported or reproduce the verified library setup first.

The successful engine versions were Chromium 154.0.8037.57, Firefox 153.0 and WebKit 26.5. These results cover desktop/mobile viewport layouts on Linux, not real Safari/iOS devices.
