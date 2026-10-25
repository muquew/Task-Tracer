# Candidate v5 editor safety acceptance

Fresh original CLI runs on candidate commit `6da3c7293f08c5d16ca73c7a63d8ff74e17358db passed **Firefox 10/10**, then **WebKit 10/10**, in strict sequence. Both original processes exited zero; no case, assertion, native command, width, normal-CSP/motion setting or time budget was changed. Only evidence routing and the native expected-index guard were supplied. No repository file was edited by this task and no additional browser matrix was run.

Each program independently locks the full 23 release sources, 84 verification inputs and HEAD before and after. All exact matches pass: source `58b724aff838339caf9c9ba0e2d5cff3ff05d20dae43e5c16fe93984f8734e54`, verification `62ec9c75e4045987bfb29df9905d075bbfeb3525558f671c4c26d159aeef0936`, index `89b5081b6fe1610c54cd5bab5f87196aad6ff04ecb02a1f30d8bcf0b67d0bc30`. Both fresh source snapshots and the original v5 freeze receipt are retained. `final-v5-summary.json` links the two unique native reports, full before/after identities, all database records, traces, screenshots and browser-event evidence. These results are independent of the earlier v4 runs, which remain untouched under their own original identities.

| Width | Original case | Firefox | WebKit |
| --- | --- | --- | --- |
| 1280 | date-roundtrip | Passed | Passed |
| 1280 | empty-weekdays | Passed | Passed |
| 1280 | subtask-delete | Passed | Passed |
| 1280 | missing-date | Passed | Passed |
| 1280 | empty-custom-interval | Passed | Passed |
| 390 | date-roundtrip | Passed | Passed |
| 390 | empty-weekdays | Passed | Passed |
| 390 | subtask-delete | Passed | Passed |
| 390 | missing-date | Passed | Passed |
| 390 | empty-custom-interval | Passed | Passed |

Actual browser versions: Firefox 153.0 (128.409 s), WebKit 26.5 (157.691 s). Every one of the 20 cases has zero page errors and zero console errors. The programs use their original production CSP header server and default normal-motion contexts, with default widths 1280 and390. All original contexts, browsers and servers closed when the CLIs completed.

WebKit used the already-verified library sysroot `/workspace/.cache/browser-libs/root/usr/lib/x86_64-linux-gnu` and official `PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1` dependency-precheck setting. Its only stderr is the expected host-validator notice. Every actual product case still executed; no product check was skipped or weakened.
