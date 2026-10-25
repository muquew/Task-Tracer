# Task Tracer 4.10.1 patch evidence

Status: **passed**. Candidate `39c3411685fe8ac037c8206ce7b561e3003bd4c1`.

- Seven static programs passed on the frozen 4.10.1 inputs.
- Chromium, Firefox and WebKit each passed the six explicitly selected affected workflows (18 program runs); native probe/program logs are byte/hash-verified.
- Service-worker update, extracted release persistence/offline and actual 4.10.0 ZIP upgrade/rollback/re-upgrade passed as separate retained wrapper runs.
- Two clean builds are byte-identical; every archive member and integrity-manifest hash matches the frozen source and application commit.
- All 23 application and 71 verification inputs match report start/end, current clean HEAD and the pinned freeze.
- The 4.10.0 original 59/60 plus targeted recheck and Firefox/WebKit 33-program matrices remain the historical baseline. The recorded 4.10.0 production-language failure remains failed. This patch did not rerun the full 60-program suite or all 33 workflows per engine.

Scope remains Linux browser engines and synthetic viewports. The compatibility workflow uses 1280×800 and 390×844; other affected workflows keep their own viewports. No physical Safari/iOS, real-device keyboard, installation, system notifications, assistive technology, remote CI or production deployment is claimed by this collector.
