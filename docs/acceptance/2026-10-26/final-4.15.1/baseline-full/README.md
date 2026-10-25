# Complete baseline and accessibility gate evidence

This directory preserves the original failed 4.15.0 baseline and the subsequent accessibility diagnostics. It is not the final 4.15.1 full-regression verdict. Final delivery gates are recorded separately.

## Original full baseline

The unchanged native command `python tools/check.py --keep-going --report <external full.json>` executed all 73 registered programs: **64 passed, 9 failed**, in 2,280.523 seconds. The detached checkout remained clean at `54b95cce891d167617d42bc489cdc801317f00c5`; all 23 source and 84 verification inputs remained identical from start to finish. Native exit status, complete stdout/stderr, command, selected environment, timestamps and both input maps are retained in [the original report](baseline-run/full.json), [runner receipt](baseline-run/run.json), and [failure summary](baseline-run/summary.json). No case, viewport, budget or threshold was removed. Each tool retained its original HTTP and motion behavior; no global production-CSP override was applied.

The failures included outdated UI entry/label contracts, a settings tool that rejected its registered no-argument invocation, and a real calendar accessibility defect. The baseline's registered upgrade program used its default 4.1 fixture; it does not establish compatibility with an actual previous release ZIP.

The real defect was a calendar detail task button whose visible content included `12:00`, its task name and status, but whose explicit accessible name omitted the time. Axe reported serious `label-content-name-mismatch` on eight visible buttons. [Actual DOM](baseline-run/calendar-label-diagnostic/nodes.json), [native axe error](baseline-run/calendar-label-diagnostic/native-error.txt), [accessibility snapshot](baseline-run/calendar-label-diagnostic/aria-snapshot.txt) and [screenshot](baseline-run/calendar-label-diagnostic/calendar-day-label-mismatch.png) preserve the evidence. The product fix removed the redundant explicit label so the visible time, name and status provide the natural accessible name.

## Full accessibility gate and narrow helper corrections

Each full run below used the original default `python tools/accessibility_i18n_audit.py`, including both default viewports and scaled surfaces. Neither `--skip-scaled` nor `--collect-axe` was used.

| Stage | Native result | What the evidence establishes |
| --- | --- | --- |
| [Original helper after product label fix](scaled-a11y-first/run.json) | Failed; 54 observations; 113.195 s | Calendar labels passed; the generic focus helper did not read the real quick-add wrapper focus ring. |
| [Quick-add wrapper focus adapter](scaled-a11y-after-focus/run.json) | Failed; 111 observations; 166.246 s | Desktop workflow completed. Mobile calendar day lookup found two legitimate DOM entries, only one of which was rendered. |
| [Universal date-number locator attempt](scaled-a11y-adapters/after-calendar-entry-adapter/run.json) | Failed; 50 observations; 99.903 s | Desktop date numbers add tasks; the details entry is the separate overflow button. This failed attempt is retained unchanged. |
| [Universal overflow-button preflight](scaled-a11y-adapters/after-more-entry-adapter/scaled-preflight.json) | Failed; 51.196 s | Desktop light/dark details opened normally; mobile overflow is hidden. No full default run was started with this failed locator. |
| [Unique rendered entry preflight](scaled-a11y-adapters/after-visible-entry-adapter/scaled-preflight.json) | Passed; 4 viewport/theme groups; 87.359 s | Each group had exactly one visible entry, normal click opened 100 detail rows, and the entire tasks/config database stayed unchanged. |
| [Final full default accessibility gate](scaled-a11y-adapters/after-visible-entry-adapter/run.json) | **Passed; 122 observations; 190.427 s; exit 0** | Both 1280px and 390px reduced-motion workflows completed, including original scaled states, with empty stderr. |

The quick-add correction is limited to `#quickAddInput` and its direct matching `.quick-add-input-wrap`. It still requires the actual input to hold focus, the wrapper to match `:focus-within`, be rendered and outside hidden/inert/aria-hidden ancestors, have a nonzero bounding box, and paint a nontransparent nonzero outline. The original radio and generic branches remain unchanged. [Exact patch](quick-add-focus-diagnostic/focus-helper.patch), [scope proof](quick-add-focus-diagnostic/applied-scope.json), [actual focused styles](quick-add-focus-diagnostic/focused-input-and-wrapper.json), and [visible focus screenshot](quick-add-focus-diagnostic/visible-wrapper-focus.png) are retained. The screenshot and style JSON record the final dark observation of that diagnostic, not two separate style captures. The isolated diagnostic could pass the old helper during a transient input shadow; the earlier full-run failure remains the original failure evidence.

The final calendar lookup selects `[data-calendar-detail-date="<day>"]` with `filter(visible=True)`, explicitly requires exactly one match and visibility, then performs an ordinary click. It uses neither `first` nor `force`. Original 100-row, focus, axe and data assertions remain intact. [Exact final locator patch and scope](scaled-a11y-adapters/after-visible-entry-adapter/change.patch) preserve this narrow change. Desktop renders one overflow entry; mobile has two DOM entries but renders the date-number entry alone.

The final helper SHA-256 is `8d13b408d5b41541b4210d1a74fc762dd3965c57e60d486f56412aebcae4b333`. Its full gate locked five runtime files, all 80 tool files and the pinned axe bytes from start to finish. This lock is distinct from the later complete 23-source/84-verification final-delivery freeze. Runtime `index.html` stayed `4a7e54f7c02f1a6d39e7568a4dd55cdc0ce1407847655069b8c27eb1f15304f4` throughout these post-fix runs.

## Provenance and limits

[original-files.json](original-files.json) maps each retained byte-for-byte copy to its original absolute path, size and SHA-256, and records the hashes and reasons for excluded duplicate full helper sources. Every retained copy was compared with its original. [files.json](files.json) inventories this archive, excluding itself. Native failed reports were never relabeled as passing.

The calendar-label screenshot, actual wrapper-focus screenshot, and final preflight's [desktop](scaled-a11y-adapters/after-visible-entry-adapter/scaled-1280-detail.png) and [mobile](scaled-a11y-adapters/after-visible-entry-adapter/scaled-390-detail.png) screenshots were opened and inspected. The intermediate overflow-only desktop image is raw diagnostic evidence. These checks establish the recorded browser/software states; they do not claim real-device testing or a complete WCAG certification. Diagnostic browser and server contexts were closed; the original full-baseline checker process group was absent after completion.
