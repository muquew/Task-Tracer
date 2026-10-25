# Final v4 editor safety across engines

The two unchanged original `tools/editor_safety_playwright.py --browser <engine> --case all` CLIs completed in sequence: Firefox **10/10**, then WebKit **10/10**. Both native processes exited zero. The default two widths, all five cases, assertions and timeouts were retained. Only evidence routing and the native expected-index safety flag were supplied. No repository file was edited by this task.

Each run locks the full **23 release sources + 84 verification inputs** before and after, including public screenshots. Both identities remain exact: source `574778e1e805a7a70fcc808d158461140cb1bf7c9264ac08f163e3df63c18e92`, verification `dfbbc08ec28deb0e028f8318b592f6cc1b9cb5c3270f99ba1cbc19866d013df7`, index `4a7e54f7c02f1a6d39e7568a4dd55cdc0ce1407847655069b8c27eb1f15304f4`. The native timeframe was declared fixed to commit `2771d561181a4f10afeeacdf2e476dcbb754a49b`; the observed HEAD after both runs is `2771d561181a4f10afeeacdf2e476dcbb754a49b`. The original v4 freeze receipt is copied to `v4-freeze-inputs.json`.

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

Both engines used their original production-header server and normal-motion contexts, without a CSP bootstrap, forced actions, added sleep or relaxed assertions. Every native case has zero page errors. Browser versions: Firefox 153.0 and WebKit 26.5. Native traces, screenshots, stored database records, browser events, original stdout/stderr and source snapshots are retained under each unique directory. All browser/server contexts closed when their original programs completed.

WebKit used the explicitly verified library sysroot `/workspace/.cache/browser-libs/root/usr/lib/x86_64-linux-gnu` and the official `PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1` launch setting. Its stderr records that expected host-validator message. Every product case still executed and passed; none was skipped.

`final-v4-summary.json` links the individual source-bound summaries and native reports. The earlier Firefox run under old 61ce/6fc inputs remains in `firefox-eea52eba-8aec-4d86-bd32-8ac49f5deaad`: it was explicitly interrupted by the parent before a separate accessibility-verifier edit, remains marked failed/interrupted, and contributes no passing cases to this result. The separate 10-image manually viewed theme audit remains valid under its explicitly narrower unchanged runtime/helper fingerprint.
