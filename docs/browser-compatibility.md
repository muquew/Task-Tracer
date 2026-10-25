# Browser support and verification

## Current delivery status

**4.15.1: complete.** The [stable delivery record](stable-delivery.md) and [final evidence](acceptance/2026-10-26/final-4.15.1/final-full/final-delivery.md) identify the application input, actual engine versions, completed scope and limits. Local full-checker result: **passed (73/73)**. Normal remote-CI public result: **passed (checks and Chromium/Firefox/WebKit all succeeded)**. Public remote success and the original local report are separate evidence; remote logs/artifacts requiring login were not downloaded.

Task Tracer is a local-first web application. Its primary task storage uses IndexedDB; offline startup needs a completed initial service-worker cache on HTTPS or a browser-trusted local origin. Chinese/English, four workspace themes and keyboard controls use the same application across browsers. Installation, notifications and persistent-storage permission depend on the browser and platform; unsupported or denied optional capabilities must leave task access and export available.

Chromium, Firefox and WebKit are the declared automated engine targets. Engine tests run on Linux with simulated viewports. A WebKit result does not establish Safari/iOS, an Android phone, a system installation, a native keyboard/IME, a screen reader or reliable OS background notifications. Use the [real-device checklist](manual-device-checklist.md) for those separate observations.

## Run and interpret the matrix

Install the pinned dependencies using [CONTRIBUTING.md](../CONTRIBUTING.md), then install the intended engines:

```bash
python -m playwright install chromium firefox webkit
python3 tools/browser_matrix.py --list
python3 tools/browser_matrix.py --browser chromium --group core --report dist/browser-matrix-core-chromium.json
python3 tools/browser_matrix.py --browser firefox --program compatibility_playwright.py --program imported_text_edit_playwright.py --report dist/browser-matrix-selected-firefox.json
python3 tools/browser_matrix.py --browser all --keep-going --report dist/browser-matrix.json
```

The current explicit registry has **33 programs**. Repeat `--browser`, `--group` or `--program` to select a union; without a selection, all three engines and all registered programs are planned. Groups include `core`, `appearance`, `capture`, `data`, `calendar`, `dates` and `all`. `--list` needs only Python's standard library and does not launch browsers or produce a pass report. Browser runs require the pinned Playwright dependency and installed engines; the driver does not fetch missing browsers.

The core compatibility program covers create/edit/complete, four views, export/restore, persistence, offline reload and horizontal-overflow checks at **1280×800** and **390×844**. Other programs declare their own viewport/fixture scope; 33 passing programs would not mean that every assertion ran at both sizes or that the complete `tools/check.py` suite ran in every engine.

Keep the atomic report and its relative run-ID logs together. Record engine versions, `completed`/`passed`, selected and unexecuted programs, source/verification start/end identities, and coverage exceptions. Missing engines, failed children, interrupted runs and input drift cannot count as passes. Retain initial failures when a new complete rerun succeeds.

Live device-timezone overrides require Chromium CDP. Firefox/WebKit run fixed-zone cases while their live-CDP groups in `timezone_playwright.py` and `calendar_timezone_playwright.py` remain explicitly `not_run`; do not count those exceptions as successful live overrides. State whether an offline test used browser emulation or an unavailable origin. A cached reload while `navigator.onLine` remains true demonstrates transport-loss fallback, not the browser's offline API or a physical device's offline lifecycle.

The [GitHub Actions workflow](../.github/workflows/checks.yml) runs the matrix in separate engine jobs. Actual remote CI, real-domain checks, local engine results and physical-device observations are separate evidence scopes. Prepared cloud machines can also use the [runtime notes](cloud-browser-runtime.md).

## Historical results

The current [4.15.1 record](releases/4.15.1.md) is separate from the historical table below. Earlier records retain their original source, tools, browser and publication identities; their passes are not relabeled for a later release.

| Version | Recorded scope and evidence |
| --- | --- |
| [4.15.0](releases/4.15.0.md) | Published material refinement, targeted Chromium workflows, inspected theme/mobile states, release/upgrade and real-domain verification; not a new full three-engine matrix. |
| [4.10.1](releases/4.10.1.md) | Six affected programs in each of three engines plus separate static/update/release checks. The [patch collection](releases/4.10.1-evidence/final/final-evidence.json) retains the selected 6/33 scope and the inherited 4.10.0 baseline separately. |
| [4.9.0](releases/4.9.0.md) | Full 32-program matrix per engine and separate published-domain core combinations, with the recorded WebKit transport-loss method and live-CDP exclusions. |
| [4.8.6](releases/4.8.6.md) | Full 31-program matrix per engine and separate targeted visibility/published-domain checks. [Strict collection](releases/browser-matrix-4.8.6-integrated-validation.json) retains the original reports and logs. |
| [4.8.5](releases/4.8.5.md) | Full 31-program matrix per engine on its final frozen candidate, with original failures and interrupted attempts preserved. [Integrated validation](releases/browser-matrix-4.8.5-integrated-validation.json) binds those final outcomes. |

The [first integrated Firefox 4.8.5 report](releases/browser-matrix-4.8.5-firefox-integrated-first.json) remains failed after an unexplained reload timeout; an observation-only diagnostic and a new unchanged complete rerun passed without rewriting that failure. Earlier saved-view abort failures and interrupted matrix attempts remain linked from the 4.8.5 release record. Development probes with changing input identities are not release passes.
