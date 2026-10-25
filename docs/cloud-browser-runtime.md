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


## Production HTTPS and the session proxy CA

The 2026-10-25 production run initially reached Firefox's `SEC_ERROR_UNKNOWN_ISSUER` before receiving HTML. The inherited proxy's public CA was already trusted by the system/OpenSSL bundle, while the fresh Firefox NSS profile needed that same CA. The [failed attempt](acceptance/2026-10-25/production-compatibility/15fda694-9b0f-4b7d-a695-f52c406c111d/report.json) and [successful Firefox session-trust result](acceptance/2026-10-25/production-compatibility/e33926be-d2b4-467b-8d47-cb3f31510a11/firefox-1280/result.json) are retained separately. The latter suite also records a separate WebKit offline-reload failure; it is not an all-engine success report.

First identify the explicitly configured **public** CA through `NODE_EXTRA_CA_CERTS`; on this machine it was `/usr/local/share/ca-certificates/environment-proxy-ca.crt`. Inspect only its public metadata and verify it against the configured system bundle:

```bash
openssl x509 -in "$NODE_EXTRA_CA_CERTS" -noout -subject -issuer -dates -fingerprint -sha256 -ext basicConstraints
openssl verify -CAfile "$SSL_CERT_FILE" "$NODE_EXTRA_CA_CERTS"
```

This run observed OpenAI, LLC / `CN=openai.com`, `CA:TRUE`, a 2024–2034 validity period and DER SHA-256 `c71b4d1e9d7775c538c688ab10cea9ce417d7312e89838f9d15ff73256cd7fc3`. Record the current configured certificate for each run; this historical fingerprint is not a permanent pin. `certutil` was already installed at `/usr/bin/certutil`; no dependency installation was needed.

Create a new disposable NSS profile, import only that verified platform CA for server trust, and compare its exported DER before launching Firefox:

```python
import os, ssl, subprocess, tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright

ca = Path(os.environ['NODE_EXTRA_CA_CERTS'])
expected_der = ssl.PEM_cert_to_DER_cert(ca.read_text())
with tempfile.TemporaryDirectory(prefix='task-tracer-session-nss-') as profile:
    database = 'sql:' + profile
    nickname = 'Task Tracer session environment proxy CA'
    subprocess.run(['certutil', '-N', '-d', database, '--empty-password'], check=True)
    subprocess.run(['certutil', '-A', '-d', database, '-n', nickname,
                    '-t', 'C,,', '-i', str(ca)], check=True)
    exported = subprocess.check_output(
        ['certutil', '-L', '-d', database, '-n', nickname, '-a'], text=True)
    assert ssl.PEM_cert_to_DER_cert(exported) == expected_der
    with sync_playwright() as playwright:
        context = playwright.firefox.launch_persistent_context(
            profile, headless=True, ignore_https_errors=False,
            proxy={'server': os.environ.get('HTTPS_PROXY', 'http://proxy:8080'),
                   'bypass': '127.0.0.1,localhost'})
        try:
            page = context.new_page()
            page.goto('https://todo.muquew.com/', wait_until='domcontentloaded')
            # Run the synthetic acceptance flow in this isolated context.
        finally:
            context.close()
```

Closing the persistent context stops its browser; the outer context manager then removes the temporary profile. Record the CA path, current public fingerprint, import/export comparison and profile removal with the run. Global trust, personal browser profiles and the application's TLS/CSP settings stay unchanged. This is normal certificate validation using the session's provisioned CA. Linux Firefox/WebKit results continue to have the real-device limits above.


## WebKit network-unavailable controls

This machine's WebKit 26.5 returned an internal error for `context.set_offline(True)` followed by navigation, including an [independent minimal cache-first service worker](acceptance/2026-10-25/production-compatibility/minimal-webkit-control/5efe3ada-b260-4b85-aa3b-67c8ae992bc8/OBSERVATIONS.md). Stopping that fixture's server instead allowed a cache-served HTTP 200 reload. Keep the API failure separate from application acceptance.

A [transport-only control](acceptance/2026-10-25/production-compatibility/transport-control/5762321b-39eb-48d5-9c43-d3e46f2cdb23/OBSERVATIONS.md) verified a disposable local byte relay to the inherited `HTTPS_PROXY`: normal WebKit TLS received the allowed domain's public manifest, then `stop()` closed its listener, all established tunnels and workers. Old sockets reached EOF, new connections were refused, a fresh uncached browser request failed, and upstream counters stopped changing. The relay forwards opaque bytes to the session proxy; it does not decrypt TLS, log headers/body or connect directly to the requested host. Its TCP half-close behavior has a separate [RED/GREEN socketpair control](acceptance/2026-10-25/production-compatibility/transport-control/halfclose-c982215a-301b-4ac9-ba79-75297b4ff937/report.json).

For an application run, give the browser the local URL returned by `SessionProxyForwarder.start()` from the saved module, warm and verify its service worker/cache, and wait for `stop()` to return with zero listener/socket/worker counts before testing cached navigation. Record this transport method independently of Firefox's offline API method. The transport control itself did not load the app or prove a later release's offline flow.


The deployed 4.8.6 application then passed [four fresh production combinations](acceptance/2026-10-25/production-compatibility/59393473-b285-4544-ba78-3b7d8ad8e3da/verification-summary.json), finishing at 2026-10-25 14:15:46 Beijing time: Firefox 153.0 and WebKit 26.5 at 1280×800 and 390×844. Firefox used the temporary public-CA NSS profile and normal offline API. WebKit used the validated relay transport shutdown; its post-reload upstream counters stayed unchanged. Every offline reload returned HTTP 200 from the service worker, with zero page/console/request errors. All eight saved screenshots were opened and inspected, including the visible white check on the repaired green subtask background. These current production results remain separate from the earlier API failure and do not establish real-device or full-WCAG acceptance.
