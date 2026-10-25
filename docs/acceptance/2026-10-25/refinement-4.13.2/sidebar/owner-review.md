# Sidebar acceptance — Task Tracer 4.13.2

Final result: PASS.

Final application SHA-256: `ec60ab40b209a15f7d86431d0599a4f8e200129f2909646323a17f531f41e508`.

Final report: `final-run/report.json`. The previous `fb59…` report and screenshots remain in `pointer-run/`; its original summary is `fb59-acceptance-README.md`. Earlier diagnostic directories also remain unchanged.

Command:

```sh
PYTHONDONTWRITEBYTECODE=1 python tools/sidebar_scroll_playwright.py --output /tmp/task-tracer-4.13.2-sidebar/final-run --executable /usr/bin/chromium
```

Forty projects were created by forty actual quick-capture submissions; four saved views were created by ordinary save-view forms. Workload creation took 3.13 seconds. No workload records, product limits, CSP settings or worker states were injected or changed.

| Viewport | Middle pane height | Keyboard projects reached | Notice during Settings click | Result |
|---|---:|---:|---|---|
| 1280×720 | 332 px | 40 | Active; moved into main column | PASS |
| 1280×500 | 112 px | 40 | Active; moved into main column | PASS |
| 390×844 | 644 px | 40 | Active; hidden behind open drawer | PASS |
| 320×640 | 440 px | 40 | Active; hidden behind open drawer | PASS |

Every project and saved-view entry was reached with physical pointer-wheel scrolling. First, middle and final project clicks opened the exact task scope. Sidebar wheel scrolling preserved the main-page position and fixed brand, desktop view navigation, Settings and footer geometry. Long project names wrapped without horizontal overflow. Keyboard focus stayed visible through forty project controls and reached Settings; Enter opened Settings. All four task views remained actionable. Mobile reopen focused and revealed the selected final project, and Escape/backdrop closure restored toggle focus.

The new overlay case applies a real saved view and checks its success notice is active, hits the fixed Settings center with `elementFromPoint`, and immediately opens Settings using `page.mouse.click`. At desktop widths the notice begins at x=252 while Settings ends at x=212. In both mobile drawers the active notice retains its `show` state but has `visibility:hidden`, and the Settings center remains directly clickable. The fixture then returns through real All Tasks navigation, clears search, waits for forty task rows, and confirms exact task and saved-view records are unchanged.

All twelve final screenshots were visually inspected, including four notice/settings overlap cases. Browser page errors and console errors are empty. The test script and application source remained unchanged during the final run. Desktop 1280×500 has a 112 px middle pane; all reachability and keyboard checks pass.

The early trial-click diagnostic issue is documented in `fb59-acceptance-README.md`. No extra ready-update-prompt state was mocked; the tested overlay is the genuine saved-view success notice.
