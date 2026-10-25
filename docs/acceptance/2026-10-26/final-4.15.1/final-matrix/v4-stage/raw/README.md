# Frozen 4.15.1 candidate: complete native three-engine matrix v3

**Overall failed: 99 registered programs invoked, 98 passed, 1 failed.** The original reports remain authoritative and unchanged. This is a complete failed candidate run, not a passed final delivery. A later focused diagnostic or corrected run must retain a separate identity and cannot rewrite this result.

| Actual engine | Invoked | Passed | Failed | Original exit | Engine duration | Native report |
|---|---:|---:|---:|---:|---:|---|
| Chromium 154.0.8037.57 | 33 | 33 | 0 | 0 | 1632.286s | [report](chromium/native-report.json) |
| Firefox 153.0 | 33 | 33 | 0 | 0 | 1712.703s | [report](firefox/native-report.json) |
| WebKit 26.5 | 33 | 32 | 1 | 1 | 2143.829s | [report](webkit/native-report.json) |

All engines used primary HEAD `2771d561181a4f10afeeacdf2e476dcbb754a49b` at start and end. Index `4a7e54f7c02f1a6d39e7568a4dd55cdc0ce1407847655069b8c27eb1f15304f4`, source23 `574778e1e805a7a70fcc808d158461140cb1bf7c9264ac08f163e3df63c18e92`, verification84 `dfbbc08ec28deb0e028f8318b592f6cc1b9cb5c3270f99ba1cbc19866d013df7`. [Frozen maps](frozen-inputs.json) and a complete byte-verified external 107-input `source-snapshot/` identify this cohort. Each original native report and runner summary confirms source and verification unchanged.

All three commands were the original native CLI `python tools/browser_matrix.py --browser <engine> --group all --keep-going --report <independent-engine-path>/native-report.json`. Three engine workers ran concurrently with the separately owned complete checker. No registered programs, assertions, original performance budgets, motion settings, HTTP handlers or CSP scopes were replaced. Native reports retain the non-Chromium CDP timezone exclusions; invoked program counts do not imply those excluded subcases executed. No physical devices, Safari/iOS, native IME, screen readers or real system notification delivery were certified.

WebKit used the actual extracted runtime libraries via `LD_LIBRARY_PATH=/workspace/.cache/browser-libs/root/usr/lib/x86_64-linux-gnu` with official `PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1`. The flag skips a static host precheck that ignores that real library path; all native browser launches, rendering and product assertions still ran. Original failed host probes, the UID1000 normal-install failure, zero-missing-library ldd results and actual render readiness evidence remain in `../baseline-matrix/probes/`. System dependencies were not installed and no fake library/preload/validator was introduced. Per-engine `command.json` records the actual environment.

## Only failed program

WebKit `quick_add_recovery_playwright.py` passed its first four complete sections: exact raw/read-only recovery and one-save behavior, coexistence of full/quick drafts, failed Retry followed by a successful Retry, and actual native refresh cancellation. It then failed in `capture_metadata` -> `fail_quick_add` -> `smoke.ensure_capture` line233: `#captureShelf` remained `inert hidden` for the original 15000ms visibility assertion after a share URL prefilled the input. The original ARIA snapshot includes the capture-ready hint but a hidden shelf. [The entire original program log](webkit/native-report-logs/f1bb1cbf-4b9a-4378-9198-e90dcdeb3f2b/webkit-quick_add_recovery_playwright.log) is retained without truncation. A failure can stop remaining internal cases; the subsequent registered programs continued under original keep-going and all completed.

The candidate's Chromium and Firefox full native quick-add-recovery programs passed. That does not relabel the WebKit failure. Static investigation suggested an asynchronous auto-open versus toggle timing issue; separate diagnostics own its actual diagnosis and any later patch. This run changed no product or verification inputs.

## Completion and provenance

The outer orchestrator exited1, consistent with the failed native report, and both its stdout and stderr are preserved. [Derived summary](final-summary.json) links exact original reports and full failed-program metadata. Native log hashes and byte counts were checked against actual files. Per-engine `raw-files.json` inventories every original engine artifact and excludes itself; [global manifest](manifest.json) covers this external run and excludes itself.

[Worker cleanup](worker-cleanup.json) confirms all three original native matrix process groups no longer existed. [Observed descendants](observed-process-cleanup.json) independently found no active instances among sampled worker/browser descendants, using PID plus start-time identity. Sampling began after early programs and is not a complete process trace. Some exited zombie records remain for container-parent reaping; they are explicitly listed as exited records, not hidden or described as running browsers. No other agent's browser/server processes were stopped.

`launch-plan-prepared-6db088ed-not-started.json` is an earlier preparation-only plan: it launched no matrix and its revoked verification hash is not this run's identity. [Actual launch plan](launch-plan.json) records the explicit full-a11y gate and final-freeze-v4 authorization.
