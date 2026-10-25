# Sidebar acceptance — Task Tracer 4.13.2

Final result: PASS.

Application SHA-256: `fb59cc194636eba12251839860d4e42a1d1e60daf3b4b009a30ac68b91b1f1cd`.

Command:

```sh
PYTHONDONTWRITEBYTECODE=1 python tools/sidebar_scroll_playwright.py --output /tmp/task-tracer-4.13.2-sidebar/pointer-run --executable /usr/bin/chromium
```

The workload contains forty projects created by forty actual quick-capture submissions and four saved views created by the ordinary save-view form. No workload records, product limits, or CSP settings were injected or changed.

| Viewport | Middle pane height | Keyboard project controls reached | Result |
|---|---:|---:|---|
| 1280×720 | 332 px | 40 | PASS |
| 1280×500 | 112 px | 40 | PASS |
| 390×844 | 644 px | 40 | PASS |
| 320×640 | 440 px | 40 | PASS |

All project and saved-view entries were reached with actual pointer-wheel scrolling. First, middle, and final project clicks opened the exact corresponding task. Sidebar wheel scrolling preserved the main-page scroll position and fixed brand, desktop view navigation, Settings and footer geometry. The long project label wrapped without horizontal overflow. All keyboard focus positions remained visible; Enter opened Settings. All four views remained actionable. Mobile reopen focused and revealed the selected final project, while Escape and backdrop closure restored toggle focus. Task records and saved-view count remained unchanged; browser page and console errors were empty.

The eight final sidebar/workspace screenshots were visually inspected. Desktop 1280×500 retains a 112 px middle pane; the complete reachability and keyboard checks pass at that height.

Earlier first-run, diagnostic-run, ready-run and geometry-run directories are preserved. Their scroll failure was caused by a Playwright trial-click on the fixed Settings entry: Playwright auto-scrolled the outer document before the wheel action. geometry-run explicitly records outer scroll movement at `after_footer_trial`, followed by no outer movement during the actual wheel action. The final script removes this artificial trial-click and uses physical pointer-wheel movement to reveal sidebar items.
