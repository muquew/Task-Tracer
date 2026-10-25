# Original 4.15.0 diagnostic browser matrix

This is the isolated original `54b95cce891d167617d42bc489cdc801317f00c5` / index `bfb0a142fb4c813e17af52267062c6faa63a7a56bd5e41feb335728c1999e9c5` baseline. It is not the final fixed candidate. Each original registered program was invoked through the unchanged native matrix CLI, with native keep-going. A failed program can stop its own internal cases. All three native engine reports remain **failed**; wrapper completion never means product tests passed.

| Actual engine | Invoked programs | Passed | Failed | Engine wall duration |
|---|---:|---:|---:|---:|
| chromium 154.0.8037.57 | 33 | 26 | 7 | 1107.31s |
| firefox 153.0 | 33 | 25 | 8 | 1102.032s |
| webkit 26.5 | 33 | 26 | 7 | 1228.276s |

Source23 aggregate `131121b361e13fce65d1df18bcc1873478b41098fabf5803620334721e7ff221` and verification84 aggregate `a207e5cfd27f752382036e35f15fd62c5dc8fee330b1699ad09aa270262b0a63` remained identical before and after all engines. Original report/log paths and byte/hash inventories are inside each engine directory. `baseline-summary.json` is derived, not a replacement for native reports. `worker-cleanup.json` confirms all three original matrix process groups no longer existed after completion.

## Preserved failures

- `project_scope`: directly clicked the collapsed project's filter control.
- `repeat_delete`: Chromium's batch More exposure failed; Firefox and WebKit completed single/batch/clear before an older abort test expected the confirmation dialog to close.
- `repeat_merge`: the no-change branch attempted to click the disabled no-import-changes submit control.
- `onboarding`: the previous exact accessible button name differed from current Try example tasks wording.
- `help`: previous heading locators differed from current disclosure/group semantics.
- `calendar_performance`: initial paging/search/navigation assertions passed before direct selection of a collapsed sort control failed.
- `time_refresh`: earlier state/dueToday/TodayPlan date-boundary cases passed before an obsolete stats-mini index selector failed.
- Firefox additionally failed imported reminder selection at the 60-minute option. The full original imported-reminder program passed on Chromium and WebKit; the Firefox original failure is preserved, not relabeled a pass or dismissed as harmless.

Root independently owns product diagnosis and fixes. This baseline does not assert whether any current primary implementation fixes these problems.

## WebKit real nonstandard runtime

Initial original host validation failed for `libGLESv2.so.2`. The existing cached Debian package and real library were inspected; normal `dpkg -i` with executor escalation still failed because UID1000 lacks superuser privilege. This was a runtime privilege error, not an automatic approval rejection. No system package was installed and no validator or product file was modified.

The actual MiniBrowser, WPEWebProcess, WPEGPUProcess and WPENetworkProcess dependencies were checked with `ldd`; every command returned0 and every missing-library list was empty. See `probes/webkit-sysroot.json` and four original ldd logs. The existing browser bundle already links its sys/lib to the real extracted runtime libraries. The original Playwright static DLOPEN check reads global `/sbin/ldconfig -p` and does not consider the valid sysroot library path.

Only WebKit therefore uses the officially supported environment `LD_LIBRARY_PATH=/workspace/.cache/browser-libs/root/usr/lib/x86_64-linux-gnu` and `PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1`. That flag skips static host preflight only. Actual launch, rendering and all33 original product programs and assertions remain required. `probes/webkit-actual-render.json` records HTTP200, actual WebKit26.5, exact baseline source, real form creation and no page errors; `webkit-render-review.json` binds the screenshot that was actually opened and accepted.

No global deployment-CSP or motion override was added. Native handlers, program viewports, budgets and assertion logic were kept. Individual native reports declare the non-Chromium CDP timezone exclusions. Linux browser engines/simulated viewports do not certify physical devices, Safari/iOS, native IME, screen readers or system notification delivery.
