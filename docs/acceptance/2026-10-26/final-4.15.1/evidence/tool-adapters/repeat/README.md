# Repeat tool contract adapters

This is a separate run from the settings review and baseline matrix. Application code is not changed here. The only repository edits owned by this audit are `tools/repeat_merge_playwright.py` and `tools/repeat_delete_playwright.py`.

## Retained originals

The byte-for-byte `.before` copies were saved before editing. Their SHA-256 values and the final tool hashes are recorded in `diff-scope.json`. The AST comparison in `run-native.py` requires every module statement except merge's `keep_or_skip` and deletion's `abort_delete` / `stale_delete` to remain identical. Original CLI case lists, fault injections, database/configuration/revision/history assertions, success cases, reload checks, recurrence round-trip checks, and timeouts are retained. `intermediate-v1/` preserves the first adapter patch and AST proof before the stale-delete finding was reached.

The earlier failures remain in the untouched baseline matrix, including:

- `../../baseline-matrix/firefox/native-report-logs/dd2fd23b-343a-460d-aeb8-cbf2a3760293/firefox-repeat_delete_playwright.log`
- `../../baseline-matrix/firefox/native-report-logs/dd2fd23b-343a-460d-aeb8-cbf2a3760293/firefox-repeat_merge_playwright.log`
- `../../baseline-matrix/chromium/native-report-logs/185b9453-47f4-4670-a63f-6b1dffb5e2d7/chromium-repeat_delete_playwright.log`

## Evidence before adapting the two tools

`focused-before.py` imported the original, untouched repeat tools' actual preparation and navigation helpers. It ran four fresh synthetic-data Firefox contexts against current primary runtime `b3cfe5642f93a067e6c2ab3c2373fd4b5e8e7944c835b7a78ca8d441bcb5d8eb`.

`focused-before/report.json` records all four passes, no page errors, and exact start/end fingerprints for five runtime assets, both original tools, and their actual UI/database helpers. This uses the original tools' native `StaticHandler` headers and reduced-motion context. It does not claim production CSP or normal-motion coverage.

The actual four PNGs were opened and visually reviewed:

- `focused-before/single.png`: a real metadata `put` was reached and its transaction aborted. The dialog stays open with a red error and an enabled retry button. This is a usable retry state.
- `focused-before/batch.png`: the same real abort closes the confirmation; selected tasks and the visible error remain available for retry.
- `focused-before/clear.png`: a real abort retains the maintenance confirmation with an error and enabled retry.
- `focused-before/skip.png`: all incoming records are explicitly skipped; the preview reports zero additions/replacements and its submit has `data-no-import-changes="true"` and is disabled.

For every abort, the entire IndexedDB `tasks` and `config` stores exactly match the pre-operation snapshot after the error, after any retained dialog is explicitly cancelled, and after reload. `config` includes revision, recovery history, backup metadata, and unrelated preferences. The actual abort flag is required. For all-skip, the same exact equality holds for preview, cancellation, and reload. The original timeout failures are not relabelled as these passes.

## Minimal changes

`repeat_merge_playwright.py`: for the all-skip case, require the explicit no-change marker, disabled submit, and exact full-store equality; close using Cancel and require equality again. Continue all original existing-record, added-record, backup/import round-trip, and recompletion assertions.

`repeat_delete_playwright.py`: require the error class, real fault-injection flag, and exact whole-store equality first. Accept either observed UI completion: closed confirmation, or retained confirmation with an enabled retry button. Explicitly cancel a retained confirmation. Require exact equality after this UI cleanup and preserve the existing exact equality after reload. Do not force a particular confirmation lifecycle when both real paths preserve data and show the error.

The first full native Firefox run (`native-firefox/`) preserves the second discovered old lifecycle assumption. Merge passed all 11 cases with native source identity checks, while deletion passed all six success/abort cases and then failed at `stale-single` because the original `confirm_delete` success helper required the retained stale confirmation to close. The combined report correctly remains failed; distribution/tool/helper inputs remained identical.

Before adapting that separate stale path, `focused-stale.py` exercised all three modes using real direct IndexedDB writes from another connection. It first verifies the remote fixture changed exactly one task's description and incremented the revision, with everything else unchanged. Each operation shows the exact translated `storage.conflict` text and leaves the entire newer tasks/configuration state identical after conflict, confirmation cleanup, and reload. Single retains an enabled confirmation; batch and maintenance close it. `focused-stale/report.json` records three passes, no page errors, and unchanged runtime/tool/helper fingerprints. All three corresponding PNGs were opened and visually reviewed. The resulting `stale_delete` adapter clicks the submit button, retains the exact conflict and full-store equality checks, explicitly cancels a retained confirmation, and adds exact newer-state checks after cleanup and reload. The successful `confirm_delete` helper remains unchanged.

## Full original CLI runs

`run-native.py <engine>` runs both original `--case all` CLIs, without changing assertions or timeouts. The native merge program still produces its own source-bound report; the delete program retains its original stdout summary. `native-<engine>/report.json` binds each command and exit code to start/end distribution-source and actual-tool/helper fingerprints. Consult that report for pass/fail and source stability; this README does not substitute for the machine results.

The new-candidate run is **`native-firefox-final-54c87195-9fb4-4b0a-a269-f1b24953f66c/`**, a distinct evidence directory. Both original complete CLIs passed: deletion **12/12**, merge **11/11**. Native merge source checks and the wrapper's complete start/end identity checks passed. Its 23-file distribution identity is `fb2cce2cc4253721a14c0a39ea017890b6daa3c143637fe5880e8361b506aec3`; its application entry hash is `976cae6020b6f5478c72708242a577ee75b6efb0b5f71ba8094fa2bd43e51feb`; its shared UI helper hash is `40d5dc01ae2f2e5b55bb9de45f9037f62f09dfa96802aa4b1cd715b4bc9f535e`. Actual engine version: Firefox 153.0. Both command exit codes are zero. The run also requires no uncaught page errors for every original case. This is the original CLI's native static-header/reduced-motion coverage, separate from production-header/normal-motion browser acceptance. All contexts, browsers, and local HTTP servers closed after completion.

Only the two assigned repository tools were edited by this audit. Their final hashes are merge `2986ed19218980de274a92b12710a668cca68a19b085d963e8362a2bb679bb56` and deletion `7ea49a5dd819b9d13561717b12399ef8fd30a311aa85c71e33c1013ad84ee3c0`.
