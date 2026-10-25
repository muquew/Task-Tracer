# Manual update browser evidence

The candidates are synthetic in-memory next-version bundles. The application inputs retain their recorded source identities.

| Run | Result | Passed checks | Index SHA-256 | Notes |
| --- | --- | ---: | --- | --- |
| [run1](run1/report.json) | failed | 0 | `48d729a29281135b0bb1fb756d6b2019b5025bfeedc89792db2a61cd7817859c` | Environment failure: Chromium socket operation denied before a page opened. |
| [run2](run2/report.json) | failed | 5 | `48d729a29281135b0bb1fb756d6b2019b5025bfeedc89792db2a61cd7817859c` | Test assertion corrected: request-history scope included the preceding expected resource 503. |
| [run3](run3/report.json) | failed | 13 | `48d729a29281135b0bb1fb756d6b2019b5025bfeedc89792db2a61cd7817859c` | Test cleanup corrected: ordinary storage Retry reloads when no memory draft remains. |
| [run4](run4/report.json) | passed | 16 | `48d729a29281135b0bb1fb756d6b2019b5025bfeedc89792db2a61cd7817859c` | Original frozen source: all 16 update checks passed. |
| [run5](run5/report.json) | passed | 20 | `e3a0d79e5c0eb044ee5c94207862117e1934bd8f21465793958792440f2a0de4` | Final frozen source: all 20 checks passed, including initial storage fallback. |

Final inputs and the exact test script are preserved in [run5/source-snapshot](run5/source-snapshot). The final run recorded no page errors or native unload dialogs.

Command:

```sh
PYTHONDONTWRITEBYTECODE=1 TASK_TRACER_BROWSER_EXECUTABLE=/usr/bin/chromium python3 tools/manual_update_playwright.py --report-dir /tmp/task-tracer-4.13.1-manual-update/run5
```
