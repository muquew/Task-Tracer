# Browser validation in the prepared cloud machine

Local quality checks do not depend on GitHub publication, Vercel or the production domain. The optional production command in CONTRIBUTING.md is an extra channel after a deployment exists.

The prepared snapshot has Playwright browser binaries under `/workspace/.cache/ms-playwright`, and system Chromium at `/usr/bin/chromium`. All three engines passed their desktop/mobile critical-flow tests. The standard CI uses `playwright install --with-deps` and the system library cache, without the cloud-specific adjustments below.

## Firefox

Use `PLAYWRIGHT_BROWSERS_PATH=/workspace/.cache/ms-playwright XDG_CACHE_HOME=/workspace/.cache python3 tools/compatibility_playwright.py --browser firefox`. This cloud filesystem sandbox makes `/proc/self/uid_map` read-only, which prevented Firefox startup. The successful run used the execution tool's reviewed escalation outside that filesystem sandbox; it did not disable Firefox's content sandbox. Use isolated synthetic profiles for local checks and the explicitly authorized production acceptance; do not reuse a personal browser profile.

## WebKit

The container lacked GTK4, Graphene, HarfBuzz ICU, Manette, Hyphen, GLES2, WOFF, Cairo script interpreter, HIDAPI and LZO runtime libraries. Their Debian packages were retrieved using signed trixie metadata from `https://deb.debian.org/debian` and extracted under `/workspace/.cache/browser-libs/root`. Package and TLS verification were retained; no system files were replaced. Apt's sources/cache configuration is retained under `/workspace/.cache/browser-apt`.

The downloaded WebKit wrapper resets its own library path, so missing shared-library symlinks were added to `/workspace/.cache/ms-playwright/webkit-2336/minibrowser-wpe/sys/lib`, pointing to these extracted libraries without replacing bundled files. The current runtime uses:

```bash
XDG_CACHE_HOME=/workspace/.cache PLAYWRIGHT_BROWSERS_PATH=/workspace/.cache/ms-playwright PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1 python3 tools/compatibility_playwright.py --browser webkit
```

That supported override bypasses the host checker's system-ldconfig-cache heuristic, which does not see the user-space GLES2 library. The actual libraries were independently loaded and the browser executed all assertions. It does not disable package checksums, TLS, CSP or application assertions. Do not use it to conceal a missing runtime library. Reinstalling WebKit removes the added runtime links; use normal system dependency installation where supported or reproduce the verified library setup first.

The successful engine versions were Chromium 154.0.8037.57, Firefox 153.0 and WebKit 26.5. These results cover desktop/mobile viewport layouts on Linux, not real Safari/iOS devices.


## Current 4.15.1 production transport and trust

The [final real-domain run](acceptance/2026-10-26/final-4.15.1/production/real-domain-v6/README.md) passed all six fresh desktop/narrow-screen combinations with normal TLS, CSP and motion. The [archived final driver](acceptance/2026-10-26/final-4.15.1/production/real-domain-v6/final-identity/driver.py) retains the verified setup; its original application exercise and assertions did not change. The accepted application remains6a3b8e; publication7a0a0f only adds the ZIP/checksum, with all107 inputs unchanged.

In this restricted machine, pass the already configured session proxy explicitly to Playwright **browser launch and browser context** options. A Python HTTP request inheriting `HTTPS_PROXY` does not prove that Playwright's Node `context.request` uses it. Use the context proxy for both page traffic and that context's API requests; for Firefox's official `launch_persistent_context`, pass the proxy there. Read the existing configured proxy only, and retain local bypasses. Do not print proxy credentials or create a new network route. The [initial transport failure](acceptance/2026-10-26/final-4.15.1/production/real-domain-v6/attempt-001-transport-failure/README.md) remains separate from application failures.

`NODE_EXTRA_CA_CERTS` configures Node trust and does not establish trust in a new Firefox NSS profile. Verify that the configured file is a publicCA (`CA:TRUE`) already trusted by `SSL_CERT_FILE`; record its current public fingerprint instead of assuming a historical pin. Use a unique `TemporaryDirectory`, initialize its `sql:` NSS store with `certutil -N --empty-password`, and import only that provisioned public root using `certutil -A ... -t C,, -i <configured-public-CA>`. Launch Firefox with that temporary directory via official `launch_persistent_context`, keeping `ignore_https_errors=False`. The earlier example below shows the public-CA import/export check. Close every context/browser in `finally`, remove the temporary profile even on launch failure, and verify removal. Do not change system trust or archive profiles, NSS/key databases, passwords or private keys; the [final configuration receipt](acceptance/2026-10-26/final-4.15.1/production/real-domain-v6/final-identity/existing-transport-config.json) contains only bounded public metadata.

For the final Firefox production capture, both native preferences `network.http.accept-encoding` and `network.http.accept-encoding.secure` were `identity`, covering worker requests as well as page requests. Chromium and WebKit retained default negotiation. An identity header only on the context did not cover the worker and its [original failed preflight](acceptance/2026-10-26/final-4.15.1/production/real-domain-v6/transport-probes/firefox-context-header-identity-incomplete/report.json) remains failed. The [native-preference preflight](acceptance/2026-10-26/final-4.15.1/production/real-domain-v6/transport-probes/firefox-networking-prefs-identity/report.json) and full final flow passed strict response-body SHA, cached body, task fields and actual backup checks. The [independent default-br result](acceptance/2026-10-26/final-4.15.1/production/real-domain-v6/transport-probes/firefox-default-br/report.json) established correct UI/IndexedDB/cache while Playwright's `Response.body()` still failed; that API result is not called passed. This is ordinary HTTP representation negotiation for evidence capture, not an application change, response rewrite or TLS/CSP bypass.

The [final report](acceptance/2026-10-26/final-4.15.1/production/real-domain-v6/final-identity/native/report.json) records four closed browser launches, six closed contexts and removal of both temporary Firefox profiles. Earlier two CI WebKit failures retain unknown causes; this observed cloud transport issue does not explain them. Standard CI uses its normal runner setup and does not need this cloud-specific profile procedure.

## Historical production HTTPS and the session proxy CA

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


The deployed 4.8.6 application then passed [four fresh production combinations](acceptance/2026-10-25/production-compatibility/59393473-b285-4544-ba78-3b7d8ad8e3da/verification-summary.json), finishing at 2026-10-25 14:15:46 Beijing time: Firefox 153.0 and WebKit 26.5 at 1280×800 and 390×844. Firefox used the temporary public-CA NSS profile and normal offline API. WebKit used the validated relay transport shutdown; its post-reload upstream counters stayed unchanged. Every offline reload returned HTTP 200 from the service worker, with zero page/console/request errors. All eight saved screenshots were opened and inspected, including the visible white check on the repaired green subtask background. Those4.8.6 production results remain separate from the earlier API failure and do not establish real-device or full-WCAG acceptance.
