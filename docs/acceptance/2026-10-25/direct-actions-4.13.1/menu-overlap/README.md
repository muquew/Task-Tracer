# Task menu overlap diagnosis

Reproduced against the unmodified 4.13.1 source, index SHA-256 `e3a0d79e5c0eb044ee5c94207862117e1934bd8f21465793958792440f2a0de4`, Chromium at 1280 × 720. The source HTML is preserved in `source-snapshot/index.html`.

The scenario matches the first `quick_add_date_playwright.py --case weekday` input: UTC clock at 2026-10-25 12:00, quick-add `周三 14:00 Weekday civil capture 0`, then open the new task's action menu and click Edit.

The original native Edit click times out. The menu is visible to layout but lies behind the filter toolbar:

| Element | Bounds on opening | z-index |
| --- | --- | ---: |
| Task menu trigger | y 485–529 | auto |
| Action menu, placed above trigger | y 259–481 | 500 |
| Edit action | y 386–426, center (847, 406) | auto |
| Filter toolbar (`toolsDrawer`) | y 373–440 | 690 |
| Sticky quick capture | y 62–227 | 998 |
| Sticky top bar | y 0–62 | 999 |

At the Edit center, `elementsFromPoint()` returns the filter label and `toolsDrawerToggleBtn` before the Edit action. The original click log also records `captureShelf` intercepting pointer events during its scroll-and-retry attempts.

`positionTaskActionMenu()` chooses above because the complete 222px menu does not fit below the trigger. Its coordinates are within the viewport; the direct failure is the menu's lower paint order. The menu's ancestors have no stacking context that prevents the menu itself from being raised.

The minimum source fix is `.task-action-menu { z-index: 1000; }`. In a clearly separated browser-only trial, this single override preserved the menu's size and coordinates, made Edit the first hit, and allowed an ordinary pointer click to open the correct task. No product file was modified. Level 1000 stays below the navigation backdrop (1001), update prompt (1002), and modal layers (1005/1010).

Avoid raising the whole task list or moving the menu DOM: the former changes task/list layering, and the latter breaks existing event delegation and trigger/focus lookup. Optional positioning improvements can subtract the visible sticky chrome from available space above, but they are not needed for this reproduced one-line paint-order fix.

Evidence:

- [Original hidden Edit action](02-open-menu-overlapped.png)
- [Failed native Edit click](03-failed-edit-click.png)
- [Browser-only z-index 1000 trial](04-browser-only-zindex-1000.png)
- [Successful native Edit click after trial](05-trial-native-edit-click-success.png)
- [Geometry, hit-test chains, source identity, and full click trace](report.json)
- [Standalone diagnostic script](reproduce.py)
